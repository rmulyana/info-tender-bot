import os
import re
import requests
import pytesseract
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

load_dotenv()

# Global Session agar login tetap bertahan
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# Status Login
is_logged_in = False
last_login_time = None

# Dictionary untuk menyimpan query sementara (untuk callback)
user_queries = {}

async def login_tender():
    global is_logged_in, last_login_time
    print("🕵️‍♂️ [Sistem Login] Memulai penyusupan tunggal...")
    url_login_page = "https://tender-indonesia.com/tender_home/info-proyek.php"
    url_captcha = "https://tender-indonesia.com/tender_home/captchalogin.php"
    url_valid = "https://tender-indonesia.com/Project_room/valid.php"
    
    try:
        session.get(url_login_page, timeout=15)
        img_resp = session.get(url_captcha, timeout=15)
        img = Image.open(BytesIO(img_resp.content))
        
        angka_captcha = pytesseract.image_to_string(img, config='--psm 7').strip()
        angka_captcha = "".join(filter(str.isdigit, angka_captcha))
        print(f"✅ [Sistem Login] Captcha Terbaca: '{angka_captcha}'")
        
        if not angka_captcha:
            print("❌ [Sistem Login] Gagal membaca captcha")
            return False
        
        payload = {
            "SIGNUN": os.getenv("TENDER_USER"),
            "SIGNPASS": os.getenv("TENDER_PASS"),
            "code": angka_captcha
        }
        
        response = session.post(url_valid, data=payload, timeout=15, allow_redirects=True)
        
        cek_login = session.get("https://tender-indonesia.com/Project_room/Index_info.php", timeout=15)
        
        if "Logout" in cek_login.text or "SIGNUN" not in cek_login.text:
            print("🎉 [Sistem Login] Berhasil Masuk Markas!")
            is_logged_in = True
            last_login_time = datetime.now()
            return True
        else:
            print("❌ [Sistem Login] Login ditolak!")
            return False
            
    except Exception as e:
        print(f"❌ [Sistem Login] Error: {e}")
        return False

def extract_tender_titles_with_links(soup, keywords):
    """Fungsi untuk mengekstrak judul tender beserta link-nya dengan multiple keywords"""
    hasil = []
    base_detail_url = "https://tender-indonesia.com/pengumuman_tender/details.php"
    
    # Split keywords menjadi list
    keyword_list = [k.lower() for k in keywords.split()]
    print(f"🔑 Mencari dengan {len(keyword_list)} keyword: {keyword_list}")
    
    # Cari semua link
    semua_link = soup.find_all('a', href=True)
    print(f"🔗 Total link ditemukan: {len(semua_link)}")
    
    for link in semua_link:
        href = link['href']
        teks = link.get_text().strip()
        
        # Skip link yang terlalu pendek atau kosong
        if not teks or len(teks) < 10:
            continue
            
        # Skip link menu/navigasi
        if any(x in href.lower() for x in ['logout', 'login', 'home', 'menu', 'statistic', 'store']):
            continue
        
        # Cek apakah SEMUA keyword ada dalam teks (AND logic)
        teks_lower = teks.lower()
        semua_keyword_ditemukan = all(k in teks_lower for k in keyword_list)
        
        if semua_keyword_ditemukan:
            print(f"✅ Link mengandung semua keyword: {teks[:50]}...")
            
            # Ekstrak parameter dari href asli
            params_match = re.search(r'\?(.+)$', href)
            if params_match:
                params = params_match.group(1)
                full_url = f"{base_detail_url}?{params}"
            else:
                # Fallback
                if href.startswith('http'):
                    full_url = href
                else:
                    clean_href = href.replace('../', '').replace('./', '')
                    if not clean_href.startswith('/'):
                        clean_href = '/' + clean_href
                    full_url = "https://tender-indonesia.com" + clean_href
            
            # Cari tanggal di sekitar link
            tanggal = datetime.now().strftime("%Y-%m-%d")
            parent = link.find_parent('td') or link.find_parent('tr') or link.find_parent('div')
            if parent:
                parent_text = parent.get_text()
                tanggal_match = re.search(r'(\d{4}-\d{2}-\d{2})', parent_text)
                if tanggal_match:
                    tanggal = tanggal_match.group(1)
            
            hasil.append({
                'tanggal': tanggal,
                'judul': teks,
                'url': full_url,
                'keyword_matches': keyword_list
            })
    
    return hasil

async def cari_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE, query, tanggal_str):
    """Fungsi internal untuk mencari di tanggal tertentu"""
    try:
        # Format URL dengan tanggal yang diminta
        url_target = f"https://tender-indonesia.com/Project_room/Index_info.php?DATE={tanggal_str}"
        print(f"🔗 Mengakses: {url_target}")
        
        response = session.get(url_target, timeout=20)
        
        # Cek apakah masih di halaman login
        if "SIGNIN" in response.text or "SIGNUN" in response.text:
            print("⚠️ Masih di halaman login, coba login ulang...")
            await login_tender()
            response = session.get(url_target, timeout=20)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ekstrak judul tender
        hasil_tender = extract_tender_titles_with_links(soup, query)
        
        # Hapus duplikat berdasarkan URL
        unique_results = []
        seen = set()
        for item in hasil_tender:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique_results.append(item)
        
        return unique_results
        
    except Exception as e:
        print(f"❌ Error di cari_tanggal: {e}")
        return []

async def cari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_logged_in, last_login_time, user_queries
    
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text(
            "💡 *Cara Penggunaan:*\n"
            "• `/cari electrical` - cari kata 'electrical' di hari ini\n"
            "• `/cari mechanical electrical` - cari semua kata (AND)\n"
            "• `/cari 2026-02-24 electrical` - cari di tanggal tertentu\n",
            parse_mode='Markdown'
        )
        return

    # Cek apakah ada tanggal di awal query
    tanggal_pattern = r'^(\d{4}-\d{2}-\d{2})\s+(.+)$'
    tanggal_match = re.match(tanggal_pattern, query)
    
    if tanggal_match:
        # Format: /cari 2026-02-24 electrical
        tanggal_str = tanggal_match.group(1)
        query = tanggal_match.group(2)
        custom_date = True
    else:
        # Format: /cari electrical (pakai tanggal hari ini)
        tanggal_str = datetime.now().strftime("%Y-%m-%d")
        custom_date = False

    # Cek apakah menggunakan quote untuk frasa persis
    use_exact_phrase = False
    if query.startswith('"') and query.endswith('"'):
        use_exact_phrase = True
        query = query[1:-1]
        print(f"🔍 Mode frasa persis: '{query}'")

    # Simpan query user untuk callback
    user_id = update.effective_user.id
    user_queries[user_id] = {
        'query': query,
        'use_exact_phrase': use_exact_phrase,
        'tanggal': tanggal_str
    }

    # Cek login
    perlu_login = False
    if not is_logged_in:
        perlu_login = True
    elif last_login_time and (datetime.now() - last_login_time) > timedelta(minutes=30):
        print("⏰ Sesi expired, login ulang...")
        perlu_login = True
    
    if perlu_login:
        await update.message.reply_text("🔑 Sedang login ke sistem...")
        berhasil = await login_tender()
        if not berhasil:
            await update.message.reply_text("❌ Gagal login. Coba lagi nanti.")
            return

    # Tampilkan info pencarian
    if custom_date:
        await update.message.reply_text(f"🔍 Mencari tender tanggal {tanggal_str} dengan keyword: '{query}'")
    else:
        await update.message.reply_text(f"🔍 Mencari tender hari ini ({tanggal_str}) dengan keyword: '{query}'")

    # Lakukan pencarian
    hasil_tender = await cari_tanggal(update, context, query, tanggal_str)

    if hasil_tender:
        # Kirim header
        header = f"📑 *HASIL TENDER ({tanggal_str})*\n"
        if len(query.split()) > 1:
            header += f"🔎 Keyword: `{'` `'.join(query.split())}` (semua kata)\n"
        else:
            header += f"🔎 Keyword: `{query}`\n"
        header += f"📊 Total: {len(hasil_tender)} hasil\n"
        header += f"🔗 [Buka Halaman Pencarian](https://tender-indonesia.com/Project_room/Index_info.php?DATE={tanggal_str})\n"
        
        await update.message.reply_text(header, parse_mode='Markdown', disable_web_page_preview=True)
        
        # Kirim setiap hasil sebagai pesan terpisah
        for i, item in enumerate(hasil_tender[:10], 1):
            judul_bersih = re.sub(r'[\r\n\t]+', ' ', item['judul'])
            judul_bersih = re.sub(r'\s+', ' ', judul_bersih).strip()
            
            pesan = (
                f"*{i}. {item['tanggal']}*\n"
                f"🔗 [{judul_bersih}]({item['url']})"
            )
            
            await update.message.reply_text(
                pesan,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        
        if len(hasil_tender) > 10:
            await update.message.reply_text(
                f"📌 Ada {len(hasil_tender) - 10} hasil lagi. Gunakan kata kunci lebih spesifik."
            )
    else:
        # TIDAK DITEMUKAN - Tawarkan opsi tanggal lain
        keyboard = [
            [
                InlineKeyboardButton("⬅️ Kemarin", callback_data=f"date_prev_{user_id}"),
                InlineKeyboardButton("➡️ Besok", callback_data=f"date_next_{user_id}")
            ],
            [
                InlineKeyboardButton("📅 Pilih Tanggal Lain", callback_data=f"date_choose_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        pesan = (
            f"⚠️ *Tidak ditemukan* tender dengan keyword '{query}' "
            f"pada tanggal {tanggal_str}.\n\n"
            f"🔍 [Buka Halaman Pencarian](https://tender-indonesia.com/Project_room/Index_info.php?DATE={tanggal_str})\n\n"
            f"💡 *Ingin mencari di tanggal lain?*"
        )
        
        await update.message.reply_text(
            pesan,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback dari inline keyboard"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # Parse callback data
    if data.startswith('date_prev_'):
        # Cari tanggal kemarin
        user_data = user_queries.get(user_id, {})
        if not user_data:
            await query.edit_message_text("❌ Sesi expired. Silakan cari lagi dengan /cari")
            return
        
        current_date = datetime.strptime(user_data.get('tanggal', datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
        prev_date = current_date - timedelta(days=1)
        tanggal_str = prev_date.strftime("%Y-%m-%d")
        
        # Update user data
        user_data['tanggal'] = tanggal_str
        user_queries[user_id] = user_data
        
        await query.edit_message_text(f"🔍 Mencari di tanggal {tanggal_str}...")
        
        # Cari di tanggal baru
        hasil = await cari_tanggal(update, context, user_data['query'], tanggal_str)
        
        if hasil:
            header = f"📑 *HASIL TENDER ({tanggal_str})*\n"
            header += f"🔎 Keyword: `{user_data['query']}`\n"
            header += f"📊 Total: {len(hasil)} hasil\n"
            header += f"🔗 [Buka Halaman Pencarian](https://tender-indonesia.com/Project_room/Index_info.php?DATE={tanggal_str})\n"
            
            await query.edit_message_text(header, parse_mode='Markdown', disable_web_page_preview=True)
            
            # Kirim hasil
            for i, item in enumerate(hasil[:5], 1):  # Batasi 5 hasil di callback
                judul_bersih = re.sub(r'[\r\n\t]+', ' ', item['judul'])
                judul_bersih = re.sub(r'\s+', ' ', judul_bersih).strip()
                
                pesan = f"*{i}. {item['tanggal']}*\n🔗 [{judul_bersih}]({item['url']})"
                await query.message.reply_text(pesan, parse_mode='Markdown', disable_web_page_preview=True)
            
            if len(hasil) > 5:
                await query.message.reply_text(f"📌 Ada {len(hasil) - 5} hasil lagi.")
        else:
            # Tetap tidak ditemukan, tawarkan lagi
            keyboard = [
                [
                    InlineKeyboardButton("⬅️ Kemarin", callback_data=f"date_prev_{user_id}"),
                    InlineKeyboardButton("➡️ Besok", callback_data=f"date_next_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⚠️ Masih tidak ditemukan di tanggal {tanggal_str}.\n\nCoba tanggal lain?",
                reply_markup=reply_markup
            )
    
    elif data.startswith('date_next_'):
        # Cari tanggal besok
        user_data = user_queries.get(user_id, {})
        if not user_data:
            await query.edit_message_text("❌ Sesi expired. Silakan cari lagi dengan /cari")
            return
        
        current_date = datetime.strptime(user_data.get('tanggal', datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
        next_date = current_date + timedelta(days=1)
        tanggal_str = next_date.strftime("%Y-%m-%d")
        
        # Update user data
        user_data['tanggal'] = tanggal_str
        user_queries[user_id] = user_data
        
        await query.edit_message_text(f"🔍 Mencari di tanggal {tanggal_str}...")
        
        # Cari di tanggal baru
        hasil = await cari_tanggal(update, context, user_data['query'], tanggal_str)
        
        if hasil:
            header = f"📑 *HASIL TENDER ({tanggal_str})*\n"
            header += f"🔎 Keyword: `{user_data['query']}`\n"
            header += f"📊 Total: {len(hasil)} hasil\n"
            header += f"🔗 [Buka Halaman Pencarian](https://tender-indonesia.com/Project_room/Index_info.php?DATE={tanggal_str})\n"
            
            await query.edit_message_text(header, parse_mode='Markdown', disable_web_page_preview=True)
            
            for i, item in enumerate(hasil[:5], 1):
                judul_bersih = re.sub(r'[\r\n\t]+', ' ', item['judul'])
                judul_bersih = re.sub(r'\s+', ' ', judul_bersih).strip()
                
                pesan = f"*{i}. {item['tanggal']}*\n🔗 [{judul_bersih}]({item['url']})"
                await query.message.reply_text(pesan, parse_mode='Markdown', disable_web_page_preview=True)
            
            if len(hasil) > 5:
                await query.message.reply_text(f"📌 Ada {len(hasil) - 5} hasil lagi.")
        else:
            keyboard = [
                [
                    InlineKeyboardButton("⬅️ Kemarin", callback_data=f"date_prev_{user_id}"),
                    InlineKeyboardButton("➡️ Besok", callback_data=f"date_next_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⚠️ Masih tidak ditemukan di tanggal {tanggal_str}.\n\nCoba tanggal lain?",
                reply_markup=reply_markup
            )
    
    elif data.startswith('date_choose_'):
        # Minta user input tanggal
        await query.edit_message_text(
            "📅 *Format Input Tanggal*\n\n"
            "Ketik: `/cari YYYY-MM-DD keyword`\n"
            "Contoh: `/cari 2026-02-24 electrical`\n\n"
            "Atau gunakan tombol di atas untuk navigasi.",
            parse_mode='Markdown'
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek status login"""
    global is_logged_in, last_login_time
    
    status_text = "🔑 *Status Login*\n\n"
    status_text += f"Status: {'✅ Aktif' if is_logged_in else '❌ Tidak Aktif'}\n"
    
    if last_login_time:
        waktu = last_login_time.strftime("%H:%M:%S")
        selisih = datetime.now() - last_login_time
        menit = int(selisih.total_seconds() / 60)
        status_text += f"Login terakhir: {waktu} ({menit} menit yang lalu)\n"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force login ulang"""
    await update.message.reply_text("🔄 Mencoba login ulang...")
    if await login_tender():
        await update.message.reply_text("✅ Login berhasil!")
    else:
        await update.message.reply_text("❌ Login gagal!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan panduan penggunaan bot"""
    help_text = (
        "🤖 *BOT TENDER INDONESIA* 🤖\n\n"
        "*CARA PENGGUNAAN:*\n\n"
        "🔍 *Mencari Tender*\n"
        "• `/cari [kata kunci]`\n"
        "  Cari tender hari ini\n"
        "  Contoh: `/cari konstruksi`\n\n"
        "• `/cari YYYY-MM-DD [kata kunci]`\n"
        "  Cari tender di tanggal tertentu\n"
        "  Contoh: `/cari 2026-02-24 detail engineering`\n\n"
        "• `/cari \"frasa persis\"`\n"
        "  Cari frasa persis (pakai tanda kutip)\n"
        "  Contoh: `/cari \"mechanical electrical\"`\n\n"
        "🧠 *Tips Pencarian*\n"
        "• Bisa pakai multiple kata: `/cari mechanical electrical`\n"
        "• Semua kata harus ada di judul tender\n"
        "• Gunakan kata kunci yang spesifik\n\n"
        "📅 *Navigasi Tanggal*\n"
        "• Jika tidak ditemukan, akan muncul tombol:\n"
        "  ⬅️ Kemarin | ➡️ Besok | 📅 Pilih tanggal\n\n"
        "🔗 *Hasil Pencarian*\n"
        "• Setiap judul tender bisa diklik\n"
        "• Link langsung ke halaman detail\n"
        "• Ada link ke halaman pencarian website\n\n"
        "⚙️ *Perintah Lain*\n"
        "• `/status` - Cek status login\n"
        "• `/login` - Force login ulang\n"
        "• `/help` - Tampilkan panduan ini\n\n"
        "⚠️ *Catatan*\n"
        "• Bot perlu login dengan akun Tender Indonesia\n"
        "• Session login bertahan ~30 menit\n"
        "• File `.env` berisi credentials (jangan dishare!)\n\n"
        "---\n"
        "Dibuat dengan ❤️ untuk memudahkan pencarian tender"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sambutan ketika user pertama kali mulai bot"""
    welcome_text = (
        "👋 *Selamat datang di Bot Tender Indonesia!*\n\n"
        "Saya akan membantu Anda mencari tender di "
        "[tender-indonesia.com](https://tender-indonesia.com)\n\n"
        "Ketik `/help` untuk melihat panduan penggunaan."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("❌ TELEGRAM_TOKEN tidak ditemukan di .env file")
        exit(1)
    
    app = ApplicationBuilder().token(token).build()
    
    # Tambahkan handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cari", cari))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Login awal
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(login_tender())
    
    print("🤖 Bot Tender siap digunakan!")
    print("📌 Commands:")
    print("   /start - Mulai bot")
    print("   /cari [keyword] - Cari di hari ini")
    print("   /cari YYYY-MM-DD [keyword] - Cari di tanggal tertentu")
    print("   /status - Cek status login")
    print("   /login - Force login ulang")
    print("   /help - Tampilkan panduan penggunaan")
    app.run_polling()