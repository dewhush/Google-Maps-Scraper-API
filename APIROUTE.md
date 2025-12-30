# Lead Maps API Documentation

## Base URL
`http://3.25.177.97` or `http://localhost:8000`

---

## 🔐 Authentication
All routes except `/auth/login`, `/auth/register`, and `/auth/send-otp` require a Bearer Token in the header OR a `token` query parameter.

### Send OTP
`POST /auth/send-otp`
- **Body**: `{"email": "user@example.com"}`

### Verify OTP
`POST /auth/verify-otp`
- **Body**: `{"email": "user@example.com", "otp": "123456"}`

### Register
`POST /auth/register`
- **Body**: `{"name": "Name", "email": "email", "password": "pass", "otp": "123456"}`

### Login (Get Token)
`POST /auth/login`
- **Body**: `{"email": "user@example.com", "password": "yourpassword"}`
- **Response**: Returns `access_token`

---

## 📊 Dashboard Statistics
Used to populate the main dashboard cards.

### Get Dashboard Stats
`GET /dashboard/stats`
- **Auth Required**: Yes
- **Query Param Support**: `?token=YOUR_TOKEN`
- **Response**:
  ```json
  {
    "total_leads": 150,
    "this_month": 24,
    "total_exports": 0,
    "last_activity": "Scraped Cafe Batavia"
  }
  ```

---

## 🕸️ Scraping

### Start Scraping
`POST /scrape`
- **Auth Required**: Yes
- **Body**:
  ```json
  {
    "query": "coffee shop jakarta",
    "max_results": 20,
    "headless": true
  }
  ```

### Get Scraping Status
`GET /scrape/status`
- **Auth Required**: Yes
- **Query Param Support**: `?token=YOUR_TOKEN`
- **Response**:
  ```json
  {
    "is_running": true,
    "progress": 45,
    "total": 100,
    "current_query": "coffee shop jakarta selatan",
    "status": "Scraping 5/20...",
    "results_count": 5,
    "started_at": "2023-12-30T..."
  }
  ```

### Stop Scraping
`POST /scrape/stop`
- **Auth Required**: Yes

---

## 💾 Data & Downloads

### Get All Contacts
`GET /contacts`
- **Auth Required**: Yes
- **Query Param Support**: `?token=YOUR_TOKEN`

### Download JSON
`GET /download/json`
- **Auth Required**: Yes
- **Query Param Support**: `?token=YOUR_TOKEN`

### Download CSV
`GET /download/csv`
- **Auth Required**: Yes
- **Query Param Support**: `?token=YOUR_TOKEN`
