# LeadMaps Backend

LeadMaps Backend is a powerful FastAPI-based application designed to extract high-quality business leads from Google Maps. It features an intelligent scraping engine customized for finding coffee shops (customizable) and includes a full authentication system with OTP verification.

## 🚀 Features

### 🔍 Smart Scraping Engine
- **Automated Crawling**: Navigates Google Maps to find businesses based on search queries.
- **Intelligent Filtering**: specifically tuned to identify coffee shops, cafes, and roasteries.
- **Data Extraction**: Captures business name, phone number (normalized), address, rating, and reviews.
- **Anti-Detection**: Uses `undetected-chromedriver` locally and optimized Chrome options for cloud deployment to avoid blocking.
- **Headless Support**: Runs efficiently in the background without a visible UI.

### 🔐 Authentication System
- **Secure Signup**: User registration with email verification via OTP (One-Time Password).
- **JWT Authentication**: Secure API access using JSON Web Tokens.
- **User Management**: Profile data handling and secure password hashing.

### 🛠 API Capabilities
- **Job Management**: Start, monitor, and stop scraping jobs asynchronously.
- **Data Export**: Download scraped leads as JSON or CSV.
- **Real-time Status**: Track scraping progress via API endpoints.

## 🛠️ Technology Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Scraping**: Selenium Webdriver, BeautifulSoup4
- **Browser Automation**: Chrome (supporting both local and Render.com environments)
- **Deployment**: Ready for [Render.com](https://render.com/)
- **Email**: Resend API for OTP delivery

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/dewhush/Back-End-Lead-Maps.git
   cd Back-End-Lead-Maps
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**
   Create a `.env` file based on `.env.example`:
   ```env
   MAIL_FROM=onboarding@resend.dev
   MAIL_PASSWORD=re_your_api_key
   SECRET_KEY=your_secret_key
   ```

## 🚀 Usage

### Running Locally
Start the server using `uvicorn`:
```bash
python server.py
# OR
uvicorn server:app --reload
```
The API will be available at `http://localhost:8000`.
Access the interactive API docs at `http://localhost:8000/docs`.

### Running the Crawler Standalone
You can also run the crawler script directly without the API:
```bash
python main.py
```

## 🌐 Deployment

This project is configured for seamless deployment on **Render.com**.
See [DEPLOY.md](DEPLOY.md) for detailed deployment instructions.

## 📝 License

This project is private and proprietary.
