# 🗺️ Google Maps Scraper API

A powerful FastAPI-based REST API for extracting high-quality business leads from Google Maps. Features intelligent scraping, full authentication system, and real-time progress tracking.

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/dewhush/Google-Maps-Scraper-API.git
cd Google-Maps-Scraper-API

# 2. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 3. Run API (Windows)
run_api.bat

# OR manually:
pip install -r requirements.txt
playwright install chromium
uvicorn server:app --reload
```

API will be available at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

---

## 📋 Features

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Scraping** | Automated Google Maps crawling with anti-detection |
| 📱 **Phone Extraction** | Normalized phone numbers with country code support |
| ⭐ **Rating Filter** | Filter by minimum rating and review count |
| 🔐 **JWT Authentication** | Secure API access with email verification |
| 📊 **Real-time Progress** | Track scraping status via API |
| 💾 **Export Options** | Download results as JSON or CSV |
| 🛡️ **Security Hardened** | Rate limiting, IP banning, XSS protection |

---

## 🔌 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/send-otp` | Send OTP to email |
| `POST` | `/api/auth/verify-otp` | Verify OTP code |
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Login & get token |
| `POST` | `/api/auth/forgot-password` | Request password reset |
| `POST` | `/api/auth/reset-password` | Reset password with OTP |

### Scraping

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scrape` | Start scraping job |
| `GET` | `/scrape/status` | Get current progress |
| `POST` | `/scrape/stop` | Stop running scrape |

### Data & History

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/history` | List all scrape sessions |
| `GET` | `/history/{id}` | Get session details |
| `DELETE` | `/history/{id}` | Delete session |
| `GET` | `/contacts` | Get all extracted leads |
| `GET` | `/download/json` | Export as JSON |
| `GET` | `/download/csv` | Export as CSV |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/dashboard/stats` | Dashboard statistics |

---

## 🔐 Authentication

All endpoints (except auth routes) require a Bearer token:

```bash
# Header method
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/health

# Query parameter method (for downloads)
curl "http://localhost:8000/download/csv?token=YOUR_TOKEN"
```

### Getting a Token

```bash
# 1. Request OTP
curl -X POST http://localhost:8000/api/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com"}'

# 2. Register (with OTP from email)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your Name",
    "email": "your@email.com",
    "password": "your_password",
    "otp": "123456"
  }'

# 3. Login (returns token)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "your_password"}'
```

---

## 📝 Example: Start Scraping

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "coffee shop jakarta",
    "max_results": 50,
    "headless": true,
    "phone_required": true,
    "min_rating": 4.0,
    "min_reviews": 10
  }'
```

### Scrape Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query |
| `max_results` | int | 20 | Max businesses to scrape |
| `headless` | bool | true | Run browser headless |
| `phone_required` | bool | true | Skip if no phone |
| `website_required` | bool | false | Skip if no website |
| `min_rating` | float | 0.0 | Minimum rating filter |
| `min_reviews` | int | 0 | Minimum reviews filter |
| `country_code` | string | "ID" | Phone format |

---

## ⚙️ Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `RESEND_API_KEY` | ✅ | Resend.com API key for emails |
| `MAIL_FROM` | ✅ | Verified sender email |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon key |
| `SECRET_KEY` | ✅ | JWT signing secret |
| `TELEGRAM_BOT_TOKEN` | ❌ | For monitoring alerts |
| `TELEGRAM_CHAT_ID` | ❌ | Telegram chat for alerts |

---

## 🛠️ Installation

### Prerequisites

- Python 3.10+
- Chrome/Chromium (installed by Playwright)

### Manual Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install browser
playwright install chromium

# Run server
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔒 Security Features

- **Rate Limiting**: 10 requests/minute on auth endpoints
- **IP Auto-Ban**: Blocks malicious IPs automatically
- **Security Headers**: XSS, CSRF, Clickjacking protection
- **Input Sanitization**: Prevents SQL injection & XSS
- **Argon2 Hashing**: Secure password storage
- **JWT Tokens**: Secure API authentication

---

## 📦 Tech Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Web framework |
| Playwright | Browser automation |
| BeautifulSoup4 | HTML parsing |
| Supabase | Database |
| Resend | Email delivery |
| slowapi | Rate limiting |
| Argon2 | Password hashing |

---

## 📄 License

This project is private and proprietary.

---

## 🙋 Support

For issues or questions, open an issue on GitHub.
