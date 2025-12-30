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
    "headless": true,
    "phone_required": true,
    "website_required": false,
    "use_sub_areas": false,
    "country_code": "ID",
    "min_rating": 4.5,
    "min_reviews": 10
  }
  ```
- **Fields**:
  - `phone_required`: (bool) Skip businesses with no phone (Default: true)
  - `website_required`: (bool) Skip businesses with no website (Default: false)
  - `use_sub_areas`: (bool) Expand search to nearby Jakarta districts (Default: false)
  - `country_code`: (str) Phone format (Default: "ID")
  - `min_rating`: (float) Minimum rating (e.g. 4.5) to keep (Default: 0.0)
  - `min_reviews`: (int) Minimum total reviews to keep (Default: 0)

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

## 🕒 Extraction History
Track and retrieve past scraping results.

### Get Extraction History
`GET /history`
- **Auth Required**: Yes
- **Response**: List of past runs (id, query, count, date)

### Get History Details (with Leads)
`GET /history/{id}`
- **Auth Required**: Yes
- **Response**: Full details of a specific run including all contacts found.

### Delete History Record
`DELETE /history/{id}`
- **Auth Required**: Yes

---

## 💾 Data & Downloads

### Get All Contacts
`GET /contacts`
- **Auth Required**: Yes
- **Query Params**:
  - `token`: (optional) Bearer token
  - `history_id`: (optional) Filter results by a specific scrape session ID.
- **Note**: If `history_id` is NOT provided, it returns ALL leads ever scraped by the user.

### Download JSON
`GET /download/json`
- **Auth Required**: Yes
- **Query Params**:
  - `token`: (optional) Bearer token
  - `history_id`: (optional) ID of the session to export. If omitted, downloads ALL user leads.

### Download CSV
`GET /download/csv`
- **Auth Required**: Yes
- **Query Params**:
  - `token`: (optional) Bearer token
  - `history_id`: (optional) ID of the session to export. If omitted, downloads ALL user leads.
