"""
LeadMaps FastAPI Backend Server
Provides REST API for Google Maps scraping and user authentication
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
import secrets
import resend
from dotenv import load_dotenv

# Load environment variables
# Load environment variables
load_dotenv()
print("=" * 60)
print(f"STARTUP CONFIG:")
print(f"MAIL_FROM: {os.getenv('MAIL_FROM')}")
print(f"RESEND_API_KEY (Set): {'Yes' if os.getenv('RESEND_API_KEY') else 'No'}")
print(f"MAIL_PASSWORD (Set): {'Yes' if os.getenv('MAIL_PASSWORD') else 'No'}")
print("=" * 60)

# ... (Environment logging) ...

# ... (Environment logging) ...

# Import Supabase Client
from database import supabase
# Use async Playwright scraper instead of Selenium
from scraper_async import AsyncGoogleMapsCrawler

# Password hashing (using sha256_crypt for better Windows compatibility)
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "leadmaps-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Security
security = HTTPBearer()

# Users storage file
USERS_FILE = "users.json"

app = FastAPI(
    title="LeadMaps API",
    description="Google Maps Business Data Extraction API with Authentication",
    version="2.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for tracking scraping progress
scraping_state = {
    "is_running": False,
    "progress": 0,
    "total": 0,
    "current_query": "",
    "status": "idle",
    "results_count": 0,
    "history_id": None,
    "started_at": None,
    "error": None
}

# OTP Storage (Persistent file-based storage)
OTP_FILE = "otp_storage.json"

def load_otp_storage() -> dict:
    """Load OTP storage from JSON file"""
    if not os.path.exists(OTP_FILE):
        return {}
    try:
        with open(OTP_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Clean expired OTPs on load
            now = datetime.now()
            cleaned = {}
            for email, otp_data in data.items():
                expires = datetime.fromisoformat(otp_data["expires"])
                if now < expires:
                    cleaned[email] = otp_data
            return cleaned
    except Exception as e:
        print(f"Error loading OTP storage: {e}")
        return {}

def save_otp_storage(data: dict):
    """Save OTP storage to JSON file"""
    try:
        # Convert datetime to ISO string for JSON serialization
        serializable = {}
        for email, otp_data in data.items():
            serializable[email] = {
                "otp": otp_data["otp"],
                "expires": otp_data["expires"].isoformat() if isinstance(otp_data["expires"], datetime) else otp_data["expires"]
            }
        with open(OTP_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"Error saving OTP storage: {e}")

# Load existing OTPs on startup
otp_storage = load_otp_storage()

# Email Configuration (Resend SDK)
resend.api_key = os.getenv("RESEND_API_KEY") or os.getenv("MAIL_PASSWORD", "re_gigGS3mx_CX8pyx9utdRahVhVeFtJhGXn")

# Global crawler instance (async Playwright)
active_crawler: Optional[AsyncGoogleMapsCrawler] = None


# ==================== AUTH MODELS ====================


# ==================== AUTH MODELS ====================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    otp: str  # Required as per contract


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class EmailRequest(BaseModel):
    email: EmailStr


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse



# ==================== AUTH HELPERS ====================

def generate_numeric_otp(length=6) -> str:
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])

def load_users() -> dict:
    """Load users from JSON file"""
    if not os.path.exists(USERS_FILE):
        return {"users": []}
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_users(data: dict):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    return verify_token(token)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Determine if ID is int or str based on previous migration
        # Try to find user
        response = supabase.table("users").select("*").eq("email", email).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="User not found")
            
        user = response.data[0]
        # Ensure ID is string for consistency
        user['id'] = str(user['id'])
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = Query(None)
) -> dict:
    """Get active user from Header OR Query param (for downloads)"""
    if credentials:
        return verify_token(credentials.credentials)
    if token:
        return verify_token(token)
    raise HTTPException(status_code=401, detail="Not authenticated")


# ==================== AUTH ENDPOINTS ====================


def get_otp_email_html(otp: str) -> str:
    """Generate aesthetic HTML email content"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verification Code</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f6f9fc;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                overflow: hidden;
            }}
            .header {{
                background-color: #4285F4;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
                text-align: center;
            }}
            .description {{
                color: #555555;
                font-size: 16px;
                line-height: 1.5;
                margin-bottom: 30px;
            }}
            .otp-box {{
                background-color: #f0f7ff;
                border: 2px dashed #4285F4;
                border-radius: 8px;
                padding: 20px;
                margin: 0 auto 30px;
                display: inline-block;
            }}
            .otp-code {{
                font-family: 'Courier New', monospace;
                font-size: 32px;
                font-weight: bold;
                color: #4285F4;
                letter-spacing: 4px;
                margin: 0;
            }}
            .warning {{
                background-color: #fff8e1;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                text-align: left;
                font-size: 14px;
                color: #856404;
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 20px;
                text-align: center;
                color: #888888;
                font-size: 12px;
                border-top: 1px solid #eeeeee;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Lead Maps</h1>
            </div>
            <div class="content">
                <h2>Verify your email address</h2>
                <p class="description">
                    Thanks for starting your registration. Please use the following verification code to complete your signup procedure.
                </p>
                
                <div class="otp-box">
                    <p class="otp-code">{otp}</p>
                </div>

                <div class="warning">
                    <strong>Security Notice:</strong> Please do not share this code with anyone. Lead Maps employees will never ask for your password or verification code.
                </div>
                
                <p class="description" style="font-size: 14px; margin-top: 30px;">
                    This code is valid for 10 minutes. If you didn't request this, you can safely ignore this email.
                </p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} Lead Maps. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/api/auth/send-otp")
async def send_otp(email_req: EmailRequest):
    """Send OTP to email"""
    email = email_req.email
    
    # Generate OTP
    otp = generate_numeric_otp(6)
    otp_storage[email] = {
        "otp": otp,
        "expires": datetime.now() + timedelta(minutes=10)
    }
    # Save to persistent storage
    save_otp_storage(otp_storage)
    
    # Send Email via Resend
    try:
        sender_email = os.getenv("MAIL_FROM") or "onboarding@resend.dev"
        api_key_status = "Present" if resend.api_key else "Missing"
        
        print(f"--- OTP DEBUG ---")
        print(f"To: {email}")
        print(f"OTP: {otp}")
        print(f"-----------------")
        
        params: resend.Emails.SendParams = {
            "from": f"Lead Maps Team <{sender_email}>",
            "to": [email],
            "subject": "Verification Code",
            "html": get_otp_email_html(otp)
        }
        
        email_resp = resend.Emails.send(params)
        print(f"Resend Response: {email_resp}")
        return {"message": "OTP sent successfully"}
        
    except Exception as e:
        print(f"Resend Error: {str(e)}")
        # For development, print to console as fallback
        print(f"DEV OTP for {email}: {otp}")
        return {"message": "OTP sent (Dev Mode: Check Console)"}


@app.post("/api/auth/verify-otp")
async def verify_otp(otp_data: OTPVerify):
    """Verify OTP code"""
    email = otp_data.email
    if email not in otp_storage:
        raise HTTPException(status_code=400, detail="OTP expired or invalid")
        
    stored_data = otp_storage[email]
    # Handle both datetime and string formats
    expires = stored_data["expires"]
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    if datetime.now() > expires:
        del otp_storage[email]
        save_otp_storage(otp_storage)
        raise HTTPException(status_code=400, detail="OTP expired")
        
    if stored_data["otp"] != otp_data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    return {"message": "OTP verified successfully"}


@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: RegisterRequest):
    """Register a new user"""
    # Check if user exists
    existing = supabase.table("users").select("id").eq("email", user_data.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Verify OTP (From persistent OTP storage)
    email = user_data.email
    if email not in otp_storage:
        raise HTTPException(status_code=400, detail="OTP expired or invalid (request new one)")
        
    stored_data = otp_storage[email]
    if stored_data["otp"] != user_data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Create new user
    new_user_data = {
        "name": user_data.name,
        "email": user_data.email,
        "password_hash": pwd_context.hash(user_data.password),
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        response = supabase.table("users").insert(new_user_data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create user")
        new_user = response.data[0]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Cleanup OTP and save
    if email in otp_storage:
        del otp_storage[email]
        save_otp_storage(otp_storage)
    
    # Create token
    access_token = create_access_token({"sub": new_user["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(new_user["id"]),
            "name": new_user["name"],
            "email": new_user["email"]
        }
    }


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and get access token"""
    response = supabase.table("users").select("*").eq("email", credentials.email).execute()
    
    if not response.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user = response.data[0]
    
    if not pwd_context.verify(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token({"sub": user["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"]
        }
    }


@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Generate reset OTP and send email"""
    email = request.email
    
    # Check if user exists (Silent Check)
    user_exists = False
    try:
        user_check = supabase.table("users").select("id").eq("email", email).execute()
        if user_check.data:
            user_exists = True
    except Exception as e:
        print(f"DB Error checking user: {e}")
        # Proceed as if user not found to avoid erroring out
    
    if not user_exists:
        # Return 200 OK to prevent user enumeration
        # Delay slightly to mimic processing time
        time.sleep(1) 
        return {"message": "If this email is registered, a reset code has been sent."}

    # Generate OTP
    otp = generate_numeric_otp(6)
    otp_storage[email] = {
        "otp": otp,
        "expires": datetime.now() + timedelta(minutes=10)
    }
    save_otp_storage(otp_storage)
    
    # Send Email
    try:
        sender_email = os.getenv("MAIL_FROM") or "onboarding@resend.dev"
        html_content = get_otp_email_html(otp).replace("Verify Your Account", "Reset Your Password")
        
        params: resend.Emails.SendParams = {
            "from": f"Lead Maps Team <{sender_email}>",
            "to": [email],
            "subject": "Reset Your Password",
            "html": html_content
        }
        
        resend.Emails.send(params)
        return {"message": "Password reset email sent"}
        
    except Exception as e:
        print(f"Email error: {e}")
        # On localhost without Resend, we might want to print OTP
        print(f"DEV OTP for {email}: {otp}")
        return {"message": "Password reset email sent (check logs if dev)"}


@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Verify OTP and update password"""
    email = request.email
    
    if email not in otp_storage:
        raise HTTPException(status_code=400, detail="OTP expired or invalid")
        
    stored_data = otp_storage[email]
    expires = stored_data["expires"]
    if isinstance(expires, str):
        expires = datetime.fromisoformat(expires)
    
    if datetime.now() > expires:
        del otp_storage[email]
        save_otp_storage(otp_storage)
        raise HTTPException(status_code=400, detail="OTP expired")
        
    if stored_data["otp"] != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Valid OTP, update password
    new_hash = pwd_context.hash(request.new_password)
    
    try:
        response = supabase.table("users").update({"password_hash": new_hash}).eq("email", email).execute()
        if not response.data:
            # Maybe user doesn't exist?
            raise HTTPException(status_code=404, detail="User not found")
            
        # Clear OTP
        del otp_storage[email]
        save_otp_storage(otp_storage)
        
        return {"message": "Password reset successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/api/auth/token", response_model=TokenResponse)
async def login_token(credentials: UserLogin):
    """Alias for login (Frontend compatibility)"""
    return await login(credentials)


# --- Compatibility Routes (No /api prefix) ---
@app.post("/auth/login", response_model=TokenResponse)
async def login_compat(credentials: UserLogin):
    return await login(credentials)


@app.post("/auth/token", response_model=TokenResponse)
async def token_compat(form_data: OAuth2PasswordRequestForm = Depends()):
    # Contract specifies form-data with username/password
    # Map username -> email
    credentials = UserLogin(email=form_data.username, password=form_data.password)
    return await login(credentials)


@app.post("/auth/register", response_model=TokenResponse)
async def register_compat(user_data: RegisterRequest):
    return await register(user_data)


@app.get("/auth/me", response_model=UserResponse)
async def me_compat(current_user: dict = Depends(get_current_user)):
    return {
        "id": str(current_user["id"]),
        "name": current_user["name"],
        "email": current_user["email"]
    }

@app.post("/auth/forgot-password")
async def forgot_compat(request: ForgotPasswordRequest):
    return await forgot_password(request)

@app.post("/auth/reset-password")
async def reset_compat(request: ResetPasswordRequest):
    return await reset_password(request)
# --------------------------------------------


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"]
    }


# ==================== AUTH ALIASES (without /api prefix) ====================
# These are aliases to support frontend calls without the /api prefix

@app.post("/auth/send-otp")
async def send_otp_alias(email_req: EmailRequest):
    """Alias for /api/auth/send-otp"""
    return await send_otp(email_req)

@app.post("/auth/verify-otp")
async def verify_otp_alias(otp_data: OTPVerify):
    """Alias for /api/auth/verify-otp"""
    return await verify_otp(otp_data)

@app.post("/auth/register", response_model=TokenResponse)
async def register_alias(user_data: RegisterRequest):
    """Alias for /api/auth/register"""
    return await register(user_data)

@app.post("/auth/login", response_model=TokenResponse)
async def login_alias(credentials: UserLogin):
    """Alias for /api/auth/login"""
    return await login(credentials)

@app.post("/auth/token", response_model=TokenResponse)
async def token_alias(credentials: UserLogin):
    """Alias for /api/auth/login (frontend uses /auth/token)"""
    return await login(credentials)

@app.get("/auth/me", response_model=UserResponse)
async def get_me_alias(current_user: dict = Depends(get_current_user)):
    """Alias for /api/auth/me"""
    return await get_me(current_user)


# ==================== SCRAPING MODELS ====================

class ScrapeRequest(BaseModel):
    query: str = "coffee shop jakarta"
    max_results: int = 20
    headless: bool = True
    phone_required: bool = True
    website_required: bool = False
    use_sub_areas: bool = False
    country_code: str = "ID"
    min_rating: float = 0.0
    min_reviews: int = 0


class ScrapeResponse(BaseModel):
    message: str
    status: str
    history_id: Optional[str] = None


class ContactResponse(BaseModel):
    id: str = ""
    business_name: str
    phone: str
    address: str = ""
    rating: float = 0.0
    reviews: int = 0
    category: str = ""
    verified: bool = False
    website: Optional[str] = None
    hours: Optional[str] = None
    description: Optional[str] = None
    coordinates: Optional[dict] = None


class ContactsListResponse(BaseModel):
    contacts: list[ContactResponse]
    total: int


class StatusResponse(BaseModel):
    is_running: bool
    progress: int
    total: int
    current_query: str
    status: str
    results_count: int
    history_id: Optional[str] = None
    started_at: Optional[str]
    error: Optional[str]


class DashboardStatsResponse(BaseModel):
    total_leads: int
    this_month: int
    total_exports: int
    last_activity: Optional[str] = "Never"


class ScrapeHistoryResponse(BaseModel):
    id: str
    query: str
    results_count: int
    created_at: str


class HistoryDetailResponse(BaseModel):
    id: str
    query: str
    results_count: int
    created_at: str
    contacts: list[ContactResponse]


def update_state(**kwargs):
    """Update scraping state (async-safe since we're single-threaded in asyncio)"""
    for key, value in kwargs.items():
        if key in scraping_state:
            scraping_state[key] = value


async def run_scraper(
    history_id: str,
    query: str, 
    max_results: int, 
    headless: bool, 
    user_id: int,
    phone_required: bool = True,
    website_required: bool = False,
    use_sub_areas: bool = False,
    country_code: str = "ID",
    min_rating: float = 0.0,
    min_reviews: int = 0
):
    """Async background task to run the Playwright scraper"""
    global active_crawler
    found_contact_ids = []
    
    config = {
        "phone_required": phone_required,
        "website_required": website_required,
        "country_code": country_code,
        "min_rating": min_rating,
        "min_reviews": min_reviews
    }
    
    try:
        update_state(
            is_running=True,
            progress=0,
            total=100,
            results_count=0, # Reset count for new run
            history_id=history_id,
            current_query=query,
            status="Initializing browser...",
            started_at=datetime.now().isoformat(),
            error=None
        )
        
        # Use async Playwright scraper
        active_crawler = AsyncGoogleMapsCrawler(
            headless=headless, 
            output_file="debug_1.json",
            config=config
        )
        await active_crawler.setup_browser()
        
        update_state(status="Browser ready, starting search...", progress=10)
        
        # Build search queries
        search_queries = [query] if query else ["coffee shop jakarta"]
        
        # If use_sub_areas is enabled, automatically expand the search
        if use_sub_areas:
            # Common sub-area expanding (Generic)
            if "jakarta" in query.lower():
                base = query.lower().replace("jakarta", "").strip()
                if base:
                    search_queries.extend([
                        f"{base} jakarta selatan",
                        f"{base} jakarta pusat",
                        f"{base} jakarta barat",
                        f"{base} jakarta timur",
                        f"{base} jakarta utara",
                    ])
        
        all_place_urls = []
        total_queries = len(search_queries)
        
        # Search phase
        for i, search_query in enumerate(search_queries):
            if not scraping_state["is_running"]:
                break
            
            progress = 10 + int((i / total_queries) * 40)
            update_state(
                current_query=search_query,
                status=f"Searching: {search_query}",
                progress=progress
            )
            
            place_urls = await active_crawler.search_places(search_query, max_results=max_results)
            for p in place_urls:
                if p["url"] not in [url["url"] for url in all_place_urls]:
                    all_place_urls.append(p)
            
            await asyncio.sleep(2)
        
        total_places = len(all_place_urls)
        update_state(
            status=f"Scraping details for {total_places} places...",
            total=total_places,
            progress=50
        )
        
        # Scrape details phase
        for i, place_url in enumerate(all_place_urls):
            if not scraping_state["is_running"]:
                break
            
            progress = 50 + int((i / max(total_places, 1)) * 45)
            update_state(
                status=f"Scraping {i+1}/{total_places}: {place_url.get('name', 'Unknown')[:30]}...",
                progress=progress
            )
            
            try:
                result = await active_crawler.scrape_place_details(place_url)
                if result:
                    new_contact = {
                        "user_id": user_id,
                        "business_name": result.get("name", "Unknown"),
                        "phone": result.get("phone", ""),
                        "address": result.get("address", ""),
                        "rating": float(result.get("rating", 0) or 0),
                        "reviews": int(result.get("reviews", 0) or 0),
                        "category": result.get("category", ""),
                        "verified": False,
                        "website": result.get("website", ""),
                        "hours": result.get("hours", ""),
                        "description": "",
                        "raw_data": result
                    }
                    
                    save_resp = supabase.table("contacts").insert(new_contact).execute()
                    if save_resp.data:
                        found_contact_ids.append(save_resp.data[0]["id"])
                        
                        # 1. Update live count based ONLY on current session
                        update_state(results_count=len(found_contact_ids))
                        
                        # 2. Update history record incrementally so frontend can see results via history_id
                        if history_id:
                            supabase.table("scrape_history").update({
                                "results_count": len(found_contact_ids),
                                "leads": found_contact_ids
                            }).eq("id", history_id).execute()
                    
            except Exception as e:
                print(f"Error scraping/saving {place_url}: {e}")
            
            await asyncio.sleep(1)
        
        # 1. Update History Record (Finally)
        if history_id:
            supabase.table("scrape_history").update({
                "results_count": len(found_contact_ids),
                "leads": found_contact_ids
            }).eq("id", history_id).execute()
            
        update_state(
            is_running=False,
            progress=100,
            status="Completed!"
        )
        
    except Exception as e:
        print(f"Scraper error: {e}")
        update_state(
            is_running=False,
            status="Error occurred",
            error=str(e)
        )
    finally:
        if active_crawler:
            try:
                await active_crawler.close()
            except:
                pass
            active_crawler = None


# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "LeadMaps API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }



@app.post("/api/scrape", response_model=ScrapeResponse)
async def start_scraping(
    request: ScrapeRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Start a new scraping job (protected)"""
    
    if scraping_state["is_running"]:
        raise HTTPException(status_code=409, detail="A scraping job is already running")
    
    user_id = current_user["id"]
    
    # 1. Create History Record First
    history_resp = supabase.table("scrape_history").insert({
        "user_id": user_id,
        "query": request.query,
        "results_count": 0,
        "leads": []
    }).execute()
    
    history_id = None
    if history_resp.data:
        history_id = history_resp.data[0]["id"]
    
    # 2. Start background task with history_id
    asyncio.create_task(
        run_scraper(
            history_id,
            request.query,
            request.max_results,
            request.headless,
            user_id,
            request.phone_required,
            request.website_required,
            request.use_sub_areas,
            request.country_code,
            request.min_rating,
            request.min_reviews
        )
    )
    
    return {
        "message": f"Scraping started for: {request.query}",
        "status": "started",
        "history_id": history_id
    }


@app.get("/api/contacts", response_model=ContactsListResponse)
async def get_contacts(
    history_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get contacts - optionally filtered by history_id (protected)"""
    user_id = current_user["id"]
    
    if history_id:
        # Fetch specific leads from history
        hist_resp = supabase.table("scrape_history").select("leads").eq("id", history_id).eq("user_id", user_id).execute()
        if not hist_resp.data:
            return {"contacts": [], "total": 0}
        
        lead_ids = hist_resp.data[0].get("leads", [])
        if not lead_ids:
            return {"contacts": [], "total": 0}
            
        contacts_resp = supabase.table("contacts").select("*").in_("id", lead_ids).execute()
        contacts = contacts_resp.data
    else:
        # Fetch all contacts for user
        contacts_resp = supabase.table("contacts").select("*").eq("user_id", user_id).execute()
        contacts = contacts_resp.data
    
    result = []
    for c in contacts:
        result.append({
            "id": str(c.get("id")),
            "business_name": c.get("business_name", ""),
            "phone": c.get("phone", ""),
            "address": c.get("address", "") or "",
            "rating": float(c.get("rating", 0) or 0.0),
            "reviews": int(c.get("reviews", 0) or 0),
            "category": c.get("category", "") or "",
            "verified": c.get("verified", False),
            "website": c.get("website", "") or "",
            "hours": c.get("hours", "") or "",
            "description": c.get("description", "") or "",
            "coordinates": c.get("raw_data", {}).get("coordinates", {"lat": 0, "lng": 0})
        })
            
    return {"contacts": result, "total": len(result)}


@app.get("/api/scrape/status", response_model=StatusResponse)
async def get_scrape_status(current_user: dict = Depends(get_current_user_token)):
    """Get current scraping job status (protected)"""
    return StatusResponse(**scraping_state)


@app.get("/api/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user_token)):
    """Get dashboard overview statistics (protected)"""
    user_id = current_user["id"]
    
    try:
        # 1. Total Leads
        total_resp = supabase.table("contacts").select("*", count="exact", head=True).eq("user_id", user_id).execute()
        total_leads = total_resp.count or 0
        
        # 2. Leads This Month
        first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        month_resp = supabase.table("contacts").select("*", count="exact", head=True).eq("user_id", user_id).gte("created_at", first_of_month).execute()
        this_month = month_resp.count or 0
        
        # 3. Last Activity (Latest contact)
        last_resp = supabase.table("contacts").select("business_name, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
        
        last_activity = "Never"
        if last_resp.data:
            last_activity = f"Scraped {last_resp.data[0]['business_name']}"
            
        return {
            "total_leads": total_leads,
            "this_month": this_month,
            "total_exports": 0, # Could track in a separate table later
            "last_activity": last_activity
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {
            "total_leads": 0,
            "this_month": 0,
            "total_exports": 0,
            "last_activity": "Error fetching stats"
        }


@app.get("/api/history", response_model=list[ScrapeHistoryResponse])
async def get_history(current_user: dict = Depends(get_current_user_token)):
    """List all past scraping extractions (protected)"""
    user_id = current_user["id"]
    response = supabase.table("scrape_history").select("id, query, results_count, created_at").eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data


@app.get("/api/history/{history_id}", response_model=HistoryDetailResponse)
async def get_history_detail(history_id: str, current_user: dict = Depends(get_current_user_token)):
    """Get details of a specific past extraction including contacts (protected)"""
    user_id = current_user["id"]
    
    # 1. Get history record
    history_resp = supabase.table("scrape_history").select("*").eq("id", history_id).eq("user_id", user_id).execute()
    if not history_resp.data:
        raise HTTPException(status_code=404, detail="History record not found")
    
    history_data = history_resp.data[0]
    lead_ids = history_data.get("leads", [])
    
    # 2. Fetch associated contacts
    contacts = []
    if lead_ids:
        contacts_resp = supabase.table("contacts").select("*").in_("id", lead_ids).execute()
        contacts = contacts_resp.data
        
    return {
        "id": history_data["id"],
        "query": history_data["query"],
        "results_count": history_data["results_count"],
        "created_at": history_data["created_at"],
        "contacts": contacts
    }


@app.delete("/api/history/{history_id}")
async def delete_history(history_id: str, current_user: dict = Depends(get_current_user_token)):
    """Delete a past extraction record (protected)"""
    user_id = current_user["id"]
    
    # Check ownership
    check_resp = supabase.table("scrape_history").select("id").eq("id", history_id).eq("user_id", user_id).execute()
    if not check_resp.data:
        raise HTTPException(status_code=404, detail="History record not found")
    
    supabase.table("scrape_history").delete().eq("id", history_id).execute()
    return {"message": "History record deleted successfully"}


@app.post("/api/scrape/stop")
async def stop_scraping(current_user: dict = Depends(get_current_user_token)):
    """Stop the current scraping job (protected)"""
    global active_crawler
    
    if not scraping_state["is_running"]:
        return {"message": "No scraping job is currently running"}
    
    update_state(
        is_running=False,
        status="Stopping..."
    )
    
    if active_crawler:
        try:
            await active_crawler.close()
        except:
            pass
        active_crawler = None
        
    return {"message": "Scraping stop command sent"}

# Compatibility route for stop
@app.post("/scrape/stop")
async def stop_compat(current_user: dict = Depends(get_current_user_token)):
    return await stop_scraping(current_user)

@app.get("/api/download/json")
async def download_json(
    history_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user_token)
):
    """Download contacts as JSON file - optionally filtered by history_id (protected)"""
    user_id = current_user["id"]
    
    contacts = []
    filename_prefix = "leadmaps_all_contacts"
    
    if history_id:
        # Fetch specific leads from history
        hist_resp = supabase.table("scrape_history").select("leads").eq("id", history_id).eq("user_id", user_id).execute()
        if not hist_resp.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        lead_ids = hist_resp.data[0].get("leads", [])
        if not lead_ids:
            raise HTTPException(status_code=404, detail="No contacts found for this session")
            
        contacts_resp = supabase.table("contacts").select("*").in_("id", lead_ids).execute()
        contacts = contacts_resp.data
        filename_prefix = f"leadmaps_session_{history_id[:8]}"
    else:
        # Fetch all contacts for user
        contacts_resp = supabase.table("contacts").select("*").eq("user_id", user_id).execute()
        contacts = contacts_resp.data
    
    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts to download")
    
    json_str = json.dumps({"contacts": contacts}, indent=2, default=str)
    
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/download/csv")
async def download_csv(
    history_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user_token)
):
    """Download contacts as CSV file - optionally filtered by history_id (protected)"""
    import csv
    import io
    
    user_id = current_user["id"]
    contacts = []
    filename_prefix = "leadmaps_all_contacts"
    
    if history_id:
        # Fetch specific leads from history
        hist_resp = supabase.table("scrape_history").select("leads").eq("id", history_id).eq("user_id", user_id).execute()
        if not hist_resp.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        lead_ids = hist_resp.data[0].get("leads", [])
        if not lead_ids:
            raise HTTPException(status_code=404, detail="No contacts found for this session")
            
        contacts_resp = supabase.table("contacts").select("*").in_("id", lead_ids).execute()
        contacts = contacts_resp.data
        filename_prefix = f"leadmaps_session_{history_id[:8]}"
    else:
        # Fetch all contacts for user
        contacts_resp = supabase.table("contacts").select("*").eq("user_id", user_id).execute()
        contacts = contacts_resp.data
    
    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts to download")

    output = io.StringIO()
    # Use keys from first contact
    fieldnames = contacts[0].keys()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(contacts)
    
    output.seek(0)
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# --- More Compatibility Routes ---
@app.get("/contacts", response_model=ContactsListResponse)
async def contacts_compat(
    history_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user_token)
):
    return await get_contacts(history_id, current_user)

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_compat(request: ScrapeRequest, current_user: dict = Depends(get_current_user_token)):
    return await start_scraping(request, current_user)

@app.get("/scrape/status", response_model=StatusResponse)
async def scrape_status_compat(current_user: dict = Depends(get_current_user_token)):
    return await get_scrape_status(current_user)

@app.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def dashboard_stats_compat(current_user: dict = Depends(get_current_user_token)):
    return await get_dashboard_stats(current_user)

@app.get("/history", response_model=list[ScrapeHistoryResponse])
async def history_compat(current_user: dict = Depends(get_current_user_token)):
    return await get_history(current_user)

@app.get("/history/{history_id}", response_model=HistoryDetailResponse)
async def history_detail_compat(history_id: str, current_user: dict = Depends(get_current_user_token)):
    return await get_history_detail(history_id, current_user)

@app.delete("/history/{history_id}")
async def history_delete_compat(history_id: str, current_user: dict = Depends(get_current_user_token)):
    return await delete_history(history_id, current_user)

@app.get("/download/json")
async def dl_json_compat(
    history_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user_token)
):
    return await download_json(history_id, current_user)

@app.get("/download/csv")
async def dl_csv_compat(
    history_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user_token)
):
    return await download_csv(history_id, current_user)
# -------------------------------



if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("LeadMaps API Server v2.0 (with Authentication)")
    print("=" * 60)
    print("Starting server at http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
