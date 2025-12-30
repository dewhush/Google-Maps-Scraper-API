# 🚀 Lead Maps - Frontend Integration Guide (All-in-One)

This document contains everything needed to connect the frontend to the simplified backend and fix the "Failed to fetch" error.

---

## 🛑 1. CRITICAL: Fix "Failed to fetch"
If you are seeing "Failed to fetch" in the register/login screens:
*   **Mixed Content Block**: If the frontend is hosted on **HTTPS** (e.g., `leadmaps.web.id`), you **CANNOT** call a backend on **HTTP** (e.g., `http://3.25.177.97:8000`). The browser will block it.
*   **Fix**: You must either:
    1.  Host the backend behind SSL (HTTPS).
    2.  Set up a Cloudflare Tunnel or Reverse Proxy.
    3.  Temporarily test the site on HTTP if the backend is on HTTP.
*   **Firewall**: Ensure Port **8000** is open for Inbound traffic on the VPS provider dashboard (AWS/DigitalOcean/etc).

---

## 🔑 2. Authentication Flow

### A. Send OTP (Post-Registration/Forgot Password)
*   **Path**: `POST /auth/send-otp`
*   **Body**: `{ "email": "user@example.com" }`

### B. Register New Account
*   **Path**: `POST /auth/register`
*   **Body**:
    ```json
    {
      "name": "Full Name",
      "email": "user@example.com",
      "password": "securepassword",
      "otp": "123456"
    }
    ```

### C. Login
*   **Path**: `POST /auth/login`
*   **Body**: `{ "email": "...", "password": "..." }`
*   **Response**: Returns `access_token` and `user` object.

---

## 🛰️ 3. Scraping & Dashboard

### A. Start Scrape
*   **Path**: `POST /api/scrape`
*   **Header**: `Authorization: Bearer <token>`
*   **Response**: Returns a **`history_id`**. Save this to filter results for only the current session!

### B. Live Results (Current Session Only)
*   **Path**: `GET /api/contacts?history_id=<history_id>`
*   **Header**: `Authorization: Bearer <token>`
*   **Note**: Always pass the `history_id` returned by the `/scrape` endpoint to avoid showing mixed data from old runs.

### C. Dashboard Stats
*   **Path**: `GET /api/dashboard/stats`
*   **Header**: `Authorization: Bearer <token>`
*   **Alternative**: `GET /api/dashboard/stats?token=<token>` (For simple browser tests)

---

## 📊 4. Export & History

### A. Download Results (JSON/CSV)
*   **Paths**: `/api/download/json` or `/api/download/csv`
*   **Query Params**: `?history_id=<id>&token=<token>`
*   **Note**: Use the `token` in the query string for easier `<a>` tag downloads.

### B. History List
*   **Path**: `GET /api/history`
*   **Header**: `Authorization: Bearer <token>`
*   **Response**: List of previous scraping runs with `results_count` and `query`.

---

## 🛠️ Summary for the Developer
1.  **CORS**: Currently set to `*` (Allow All).
2.  **API Version**: v2.0 (Playwright Async).
3.  **Port**: 8000 (Default).
4.  **Logging**: The backend now logs all incoming requests. If you don't see logs in the VPS console when you click a button, the request never left your browser!
