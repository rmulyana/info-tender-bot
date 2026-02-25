# Bot Tender Indonesia

A Telegram bot for searching and monitoring tenders from [tender-indonesia.com](https://tender-indonesia.com). The bot automatically logs in, handles captcha using Tesseract OCR, and allows users to search for tenders by keywords across different dates.

## Features

- 🔍 **Search Tenders** - Search for tenders by keywords
- 📅 **Date Navigation** - Browse tenders across different dates with interactive buttons
- 🔗 **Clickable Links** - Direct links to tender details
- 🤖 **Auto Login** - Automatic login with captcha handling
- 🧠 **Smart Search** - Multiple keyword search (AND logic)
- 📱 **User-Friendly** - Inline keyboard for easy navigation
- 🔒 **Session Management** - Auto re-login when session expires

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/cari [keywords]` | Search today's tenders | `/cari konstruksi jalan` |
| `/cari YYYY-MM-DD [keywords]` | Search tenders on specific date | `/cari 2026-02-24 bahan kimia` |
| `/status` | Check login status | `/status` |
| `/login` | Force re-login | `/login` |

## How It Works

1. **Login Automation**: Bot logs in using credentials from `.env` file
2. **Captcha Solving**: Uses Tesseract OCR to read captcha images
3. **Session Persistence**: Maintains login session for multiple requests
4. **Tender Search**: Scrapes tender data and filters by keywords
5. **Result Presentation**: Shows results with clickable links and date navigation

## Installation

### Prerequisites
- Python 3.7+
- Tesseract OCR ([Installation Guide](https://github.com/tesseract-ocr/tesseract))
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/rmulyana/info-tender-bot.git
cd info-tender-bot 
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Install Tesseract OCR**
   - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
   - **macOS**: `brew install tesseract`
   - **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Run the bot**
```bash
python bot_tender.py
```

## Environment Variables

Create a `.env` file with the following variables:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
TENDER_USER=your_tender_username_here
TENDER_PASS=your_tender_password_here
```

## Requirements

```
python-telegram-bot>=20.0
requests>=2.31.0
beautifulsoup4>=4.12.0
pytesseract>=0.3.10
Pillow>=10.0.0
python-dotenv>=1.0.0
```

## Project Structure

```
bot-tender-indonesia/
├── bot_tender.py          # Main bot application
├── requirements.txt       # Python dependencies
├── .env.example          # Template for environment variables
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Usage Examples

### Search for "construction" today
```
/cari konstruksi
```

### Search for "chemical" on specific date
```
/cari 2026-02-24 bahan kimia
```

### When no results found
If no tenders are found, the bot provides interactive buttons to:
- ⬅️ Search previous day
- ➡️ Search next day
- 📅 Choose another date manually

## Features in Detail

### Smart Search Logic
- **Multiple keywords**: `/cari engineering construction` finds tenders containing BOTH words
- **Exact phrase**: Use quotes: `/cari "pipe seamless"` for exact phrase matching
- **Date-specific**: Add date prefix for historical search

### Result Display
- Shows total number of results
- Displays tender date and title
- Provides clickable link to tender details
- Includes link to the search results page

### Session Management
- Automatic login on bot startup
- Session refresh every 30 minutes
- Automatic re-login on session expiry

## Troubleshooting

### Common Issues

1. **Login Failed**
   - Check credentials in `.env`
   - Ensure Tesseract OCR is properly installed
   - Try `/login` command to force re-login

2. **No Results Found**
   - Try different keywords
   - Check if there are tenders on that date
   - Use the date navigation buttons

3. **Captcha Reading Errors**
   - Ensure Tesseract is installed correctly
   - Check Tesseract path in system
   - Try reinstalling Tesseract

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This bot is for educational purposes. Please respect the website's terms of service and use responsibly. The developers are not responsible for any misuse or violations of the website's terms.

## Contact

Ruzia Mulyana - [@Papagenics](https://t.me/Papagenics)

Project Link: [https://github.com/rmulyana/info-tender-bot](https://github.com/rmulyana/info-tender-bot)

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)

---

**⭐ Star this repo if you find it useful!**
