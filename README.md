# 🗺️ Google Maps Scraper API

A lightweight REST API for extracting business leads from Google Maps using Playwright.

## 🚀 Quick Start

```bash
# Windows
run_api.bat

# Manual
pip install -r requirements.txt
playwright install chromium
python api.py
```

API: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Service health check |
| `POST` | `/api/scrape` | Start scraping job |
| `GET` | `/api/scrape/status` | Get scraping progress |
| `POST` | `/api/scrape/stop` | Stop current scrape |
| `GET` | `/api/results` | Get scraped results |
| `DELETE` | `/api/results` | Clear stored results |

---

## 🔐 Authentication

Set `API_KEY` in `.env`, then include in requests:

```bash
# Header method
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/status

# Query parameter
curl "http://localhost:8000/api/status?api_key=YOUR_KEY"
```

Leave `API_KEY` empty to disable authentication (dev only).

---

## 📝 Example: Scraping

### Start Scraping
```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "coffee shop jakarta",
    "max_results": 20,
    "phone_required": true,
    "min_rating": 4.0
  }'
```

### Check Progress
```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/scrape/status
```

### Get Results
```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/results
```

---

## ⚙️ Scrape Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query (e.g., "coffee shop jakarta") |
| `max_results` | int | 20 | Max businesses to scrape |
| `headless` | bool | true | Run browser in headless mode |
| `phone_required` | bool | true | Skip results without phone |
| `website_required` | bool | false | Skip results without website |
| `min_rating` | float | 0.0 | Minimum rating filter |
| `country_code` | string | "ID" | Phone number format |

---

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Chrome/Chromium (auto-installed by Playwright)

### Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure
cp .env.example .env
# Edit .env and set your API_KEY

# Run
python api.py
```

---

## 📦 Dependencies

```
fastapi
uvicorn
python-dotenv
playwright
pydantic
beautifulsoup4
```

---

## 📄 License

Private and proprietary.
