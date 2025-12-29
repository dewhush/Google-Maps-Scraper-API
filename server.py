"""
LeadMaps FastAPI Backend Server
Provides REST API for Google Maps scraping and user authentication
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
print(f"MAIL_PASSWORD (Set): {'Yes' if os.getenv('MAIL_PASSWORD') else 'No'}")
print("=" * 60)

# Import the crawler
from main import GoogleMapsCrawler

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "leadmaps-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing (using sha256_crypt for better Windows compatibility)
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

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
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
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
    "started_at": None,
    "error": None
}

# OTP Storage (In-memory for simplicity, use Redis/DB in production)
otp_storage = {}

# Email Configuration (Resend SDK)
resend.api_key = os.getenv("MAIL_PASSWORD", "re_gigGS3mx_CX8pyx9utdRahVhVeFtJhGXn")

# Lock for thread-safe state updates

# Lock for thread-safe state updates
state_lock = threading.Lock()

# Global crawler instance
active_crawler: Optional[GoogleMapsCrawler] = None


# ==================== AUTH MODELS ====================

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    otp: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str



class EmailRequest(BaseModel):
    email: EmailStr


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ==================== AUTH HELPERS ====================

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


def get_user_by_email(email: str) -> Optional[dict]:
    """Find user by email"""
    data = load_users()
    for user in data["users"]:
        if user["email"] == email:
            return user
    return None


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = get_user_by_email(email)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


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
    otp = secrets.token_hex(3).upper() # 6 chars
    otp_storage[email] = {
        "otp": otp,
        "expires": datetime.now() + timedelta(minutes=10)
    }
    
    # Send Email via Resend
    try:
        # Default to onboarding@resend.dev (Testing)
        # NOTE: When using onboarding@resend.dev, you can ONLY send to verified "Test Users" in Resend default
        sender_email = os.getenv("MAIL_FROM")
        api_key_status = "Present" if resend.api_key else "Missing"
        masked_key = f"{resend.api_key[:5]}..." if resend.api_key else "None"
        
        print(f"--- OTP DEBUG ---")
        print(f"API Key: {api_key_status} ({masked_key})")
        print(f"Sender: {sender_email}")
        print(f"Recipient: {email}")
        print(f"-----------------")
        
        params: resend.Emails.SendParams = {
            "from": f"Lead Maps Team <{sender_email}>",
            "to": [email],
            "subject": "Verification Code",
            "html": get_otp_email_html(otp)
        }
        
        email_resp = resend.Emails.send(params)
        print(f"Resend Response: {email_resp}")
        return {"message": "OTP sent successfully", "debug": str(email_resp)}
        
    except Exception as e:
        print(f"Resend Error: {str(e)}")
        # For development, print to console as fallback
        print(f"DEV OTP for {email}: {otp}")
        # Return the actual error to help debugging
        raise HTTPException(status_code=500, detail=f"Email failed: {str(e)}")


@app.post("/api/auth/verify-otp")
async def verify_otp(otp_data: OTPVerify):
    """Verify OTP code"""
    email = otp_data.email
    if email not in otp_storage:
        raise HTTPException(status_code=400, detail="OTP expired or invalid")
        
    stored_data = otp_storage[email]
    if datetime.now() > stored_data["expires"]:
        del otp_storage[email]
        raise HTTPException(status_code=400, detail="OTP expired")
        
    if stored_data["otp"] != otp_data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    return {"message": "OTP verified successfully"}


@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    # Check if user exists
    if get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Verify OTP
    if not user_data.otp:
        raise HTTPException(status_code=400, detail="OTP required")
        
    email = user_data.email
    if email not in otp_storage:
        raise HTTPException(status_code=400, detail="OTP expired or invalid (request new one)")
        
    stored_data = otp_storage[email]
    if stored_data["otp"] != user_data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Create new user
    data = load_users()
    new_user = {
        "id": f"user_{len(data['users']) + 1}_{int(time.time())}",
        "name": user_data.name,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "created_at": datetime.now().isoformat()
    }
    data["users"].append(new_user)
    
    # Cleanup OTP
    del otp_storage[email]
    
    save_users(data)
    
    # Create token
    access_token = create_access_token({"sub": new_user["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user["id"],
            "name": new_user["name"],
            "email": new_user["email"]
        }
    }


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and get access token"""
    user = get_user_by_email(credentials.email)
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token({"sub": user["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }


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
async def register_alias(user_data: UserRegister):
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


class ScrapeResponse(BaseModel):
    message: str
    status: str


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
    started_at: Optional[str]
    error: Optional[str]


def update_state(**kwargs):
    """Thread-safe state update"""
    with state_lock:
        for key, value in kwargs.items():
            if key in scraping_state:
                scraping_state[key] = value


def run_scraper(query: str, max_results: int, headless: bool, user_id: str):
    """Background task to run the scraper"""
    global active_crawler
    
    # User-specific output file
    output_file = f"data_{user_id}.json"
    
    try:
        update_state(
            is_running=True,
            progress=0,
            total=100,
            current_query=query,
            status="Initializing browser...",
            started_at=datetime.now().isoformat(),
            error=None
        )
        
        # Create and setup crawler with user-specific output file
        active_crawler = GoogleMapsCrawler(headless=headless, output_file=output_file)
        active_crawler.setup_driver()
        
        update_state(status="Browser ready, starting search...", progress=10)
        
        # Define search queries based on input
        if query:
            search_queries = [query]
            if "jakarta" in query.lower():
                base = query.replace("jakarta", "").strip()
                if base:
                    search_queries.extend([
                        f"{base} jakarta selatan",
                        f"{base} jakarta pusat",
                        f"{base} jakarta barat",
                    ])
        else:
            search_queries = [
                "coffee shop jakarta",
                "kedai kopi jakarta",
                "cafe jakarta"
            ]
        
        all_place_urls = []
        total_queries = len(search_queries)
        
        for i, search_query in enumerate(search_queries):
            if not scraping_state["is_running"]:
                update_state(status="Scraping stopped by user")
                break
            
            progress = 10 + int((i / total_queries) * 40)
            update_state(
                current_query=search_query,
                status=f"Searching: {search_query}",
                progress=progress
            )
            
            place_urls = active_crawler.search_places(search_query, max_results=max_results)
            
            for place_url in place_urls:
                if place_url not in all_place_urls:
                    all_place_urls.append(place_url)
            
            time.sleep(2)
        
        total_places = len(all_place_urls)
        update_state(
            status=f"Scraping details for {total_places} places...",
            total=total_places,
            progress=50
        )
        
        for i, place_url in enumerate(all_place_urls):
            if not scraping_state["is_running"]:
                update_state(status="Scraping stopped by user")
                break
            
            progress = 50 + int((i / max(total_places, 1)) * 45)
            update_state(
                status=f"Scraping {i+1}/{total_places}: {place_url.get('name', 'Unknown')[:30]}...",
                progress=progress,
                results_count=len(active_crawler.results)
            )
            
            try:
                active_crawler.scrape_place_details(place_url)
            except Exception as e:
                print(f"Error scraping {place_url}: {e}")
            
            time.sleep(1)
        
        update_state(status="Saving results...", progress=95)
        active_crawler.save_simple_format("data.json")
        
        update_state(
            is_running=False,
            progress=100,
            status="Completed!",
            results_count=len(active_crawler.results)
        )
        
    except Exception as e:
        update_state(
            is_running=False,
            status="Error occurred",
            error=str(e)
        )
    finally:
        if active_crawler:
            try:
                active_crawler.close()
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
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Start a new scraping job (protected)"""
    
    if scraping_state["is_running"]:
        raise HTTPException(status_code=409, detail="A scraping job is already running")
    
    background_tasks.add_task(
        run_scraper,
        request.query,
        request.max_results,
        request.headless,
        current_user["id"]
    )
    
    return {
        "message": f"Scraping started for: {request.query}",
        "status": "started"
    }


@app.get("/api/contacts", response_model=ContactsListResponse)
async def get_contacts(current_user: dict = Depends(get_current_user)):
    """Get all scraped contacts (protected)"""
    user_id = current_user["id"]
    data_file = f"data_{user_id}.json"
    
    if not os.path.exists(data_file):
        return {"contacts": [], "total": 0}
        
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        contacts = []
        for i, item in enumerate(raw_data.get("contacts", [])):
            contacts.append({
                "id": str(i),
                "business_name": item.get("name", ""),
                "phone": item.get("phone", ""),
                "address": item.get("address", ""),
                "rating": float(item.get("rating", 0) or 0),
                "reviews": int(item.get("reviews", 0) or 0),
                "category": item.get("category", ""),
                "verified": bool(item.get("verified", False)),
                "website": item.get("website", ""),
                "hours": item.get("hours", ""),
                "description": item.get("description", "")
            })
            
        return {"contacts": contacts, "total": len(contacts)}
    except Exception as e:
        print(f"Error reading data: {e}")
        return {"contacts": [], "total": 0}


@app.get("/api/scrape/status", response_model=StatusResponse)
async def get_scrape_status(current_user: dict = Depends(get_current_user)):
    """Get current scraping job status (protected)"""
    with state_lock:
        return StatusResponse(**scraping_state)

# ... (stop_scraping endpoint remains same) ...

@app.get("/api/download/json")
async def download_json(current_user: dict = Depends(get_current_user)):
    """Download contacts as JSON file (protected)"""
    user_id = current_user["id"]
    data_file = f"data_{user_id}.json"
    
    if not os.path.exists(data_file):
        raise HTTPException(status_code=404, detail="No data file found")
    
    return FileResponse(
        data_file,
        media_type="application/json",
        filename=f"leadmaps_contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

@app.get("/api/download/csv")
async def download_csv(current_user: dict = Depends(get_current_user)):
    """Download contacts as CSV file (protected)"""
    import csv
    import io
    
    user_id = current_user["id"]
    data_file = f"data_{user_id}.json"
    
    if not os.path.exists(data_file):
        raise HTTPException(status_code=404, detail="No data file found")

    # Convert JSON to CSV on the fly
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        contacts = data.get("contacts", [])

    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts to download")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=contacts[0].keys())
    writer.writeheader()
    writer.writerows(contacts)
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leadmaps_contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )



if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("LeadMaps API Server v2.0 (with Authentication)")
    print("=" * 60)
    print("Starting server at http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
