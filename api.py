"""
Google Maps Scraper API
A lightweight FastAPI wrapper for Google Maps business data extraction.

Created by: dewhush

Endpoints:
- GET  /health           - Simple health check
- GET  /status           - Detailed service status
- POST /v1/scrape        - Start scraping
- GET  /v1/scrape/status - Get scraping progress
- POST /v1/scrape/stop   - Stop current scrape
- GET  /v1/results       - Get scraping results
- DELETE /v1/results     - Clear results
"""

import asyncio
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import scraper
from scraper_async import AsyncGoogleMapsCrawler

# ===========================================
# Configuration
# ===========================================

API_KEY = os.getenv("API_KEY", "")  # Set in .env
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# ===========================================
# FastAPI App
# ===========================================

app = FastAPI(
    title="Google Maps Scraper API",
    description="Extract business leads from Google Maps. Created by dewhush.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# Startup Banner
# ===========================================

@app.on_event("startup")
async def startup_event():
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║     GOOGLE MAPS SCRAPER API                       ║
    ║     Created by: dewhush                           ║
    ╠═══════════════════════════════════════════════════╣
    ║  Docs:   http://localhost:8000/docs               ║
    ╚═══════════════════════════════════════════════════╝
    """)

# ===========================================
# Global State
# ===========================================

scraping_state = {
    "is_running": False,
    "progress": 0,
    "total": 100,
    "status": "idle",
    "current_query": "",
    "results_count": 0,
    "started_at": None,
    "error": None
}

results_storage: List[Dict[str, Any]] = []
active_crawler: Optional[AsyncGoogleMapsCrawler] = None

# ===========================================
# Request/Response Models
# ===========================================

class ScrapeRequest(BaseModel):
    keyword: str
    location: Optional[str] = None
    limit: int = 20
    headless: bool = True
    phone_required: bool = True
    website_required: bool = False
    min_rating: float = 0.0
    country_code: str = "ID"

class ScrapeStatus(BaseModel):
    is_running: bool
    progress: int
    total: int
    status: str
    current_query: str
    results_count: int
    started_at: Optional[str]
    error: Optional[str]

class BusinessLead(BaseModel):
    name: str
    phone: str
    address: Optional[str]
    website: Optional[str]
    rating: Optional[str]
    category: Optional[str]
    lat: Optional[float]
    lng: Optional[float]

# ===========================================
# Authentication
# ===========================================

async def verify_api_key(
    api_key: Optional[str] = Depends(API_KEY_HEADER),
    key: Optional[str] = Query(None, alias="api_key")
) -> bool:
    """Verify API key from header or query parameter"""
    if not API_KEY:
        return True
    
    provided_key = api_key or key
    if not provided_key or provided_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

# ===========================================
# Health & Status Endpoints
# ===========================================

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/status")
async def get_status():
    """Detailed service status"""
    return {
        "status": "online",
        "service": "Google Maps Scraper API",
        "version": "1.0.0",
        "author": "dewhush",
        "scraper_running": scraping_state["is_running"],
        "timestamp": datetime.utcnow().isoformat()
    }

# ===========================================
# Scraping Endpoints (v1)
# ===========================================

@app.post("/v1/scrape", dependencies=[Depends(verify_api_key)])
async def start_scraping(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Start a new scraping job.
    
    - **keyword**: Search keyword (e.g., "coffee shop")
    - **location**: Location to search (e.g., "jakarta")
    - **limit**: Maximum results to collect
    """
    global active_crawler, scraping_state, results_storage
    
    if scraping_state["is_running"]:
        raise HTTPException(status_code=409, detail="Scraping already in progress")
    
    # Build query from keyword + location
    query = request.keyword
    if request.location:
        query = f"{request.keyword} {request.location}"
    
    # Reset state
    scraping_state.update({
        "is_running": True,
        "progress": 0,
        "total": 100,
        "status": "Starting...",
        "current_query": query,
        "results_count": 0,
        "started_at": datetime.utcnow().isoformat(),
        "error": None
    })
    results_storage = []
    
    # Start scraping in background
    background_tasks.add_task(run_scraper, request, query)
    
    return {
        "message": "Scraping started",
        "query": query,
        "limit": request.limit
    }


async def run_scraper(request: ScrapeRequest, query: str):
    """Background task to run the scraper"""
    global active_crawler, scraping_state, results_storage
    
    try:
        # Initialize crawler
        config = {
            "phone_required": request.phone_required,
            "website_required": request.website_required,
            "min_rating": request.min_rating,
            "country_code": request.country_code,
            "concurrency": 3
        }
        
        active_crawler = AsyncGoogleMapsCrawler(
            headless=request.headless,
            config=config
        )
        
        await active_crawler.setup_browser()
        
        # Progress callback
        async def update_progress(status: str, progress: int, total: int):
            scraping_state.update({
                "status": status,
                "progress": progress,
                "total": total,
                "results_count": len(active_crawler.results)
            })
        
        # Run crawl
        results = await active_crawler.crawl(
            query=query,
            max_results=request.limit,
            progress_callback=update_progress
        )
        
        # Store results
        results_storage = results
        
        scraping_state.update({
            "is_running": False,
            "progress": 100,
            "status": "Completed",
            "results_count": len(results)
        })
        
    except Exception as e:
        scraping_state.update({
            "is_running": False,
            "status": "Error",
            "error": str(e)
        })
    finally:
        if active_crawler:
            await active_crawler.close()
            active_crawler = None


@app.get("/v1/scrape/status", response_model=ScrapeStatus, dependencies=[Depends(verify_api_key)])
async def get_scraping_status():
    """Get current scraping progress"""
    return ScrapeStatus(**scraping_state)


@app.post("/v1/scrape/stop", dependencies=[Depends(verify_api_key)])
async def stop_scraping():
    """Stop the current scraping job"""
    global active_crawler, scraping_state
    
    if not scraping_state["is_running"]:
        raise HTTPException(status_code=400, detail="No scraping in progress")
    
    try:
        if active_crawler:
            await active_crawler.close()
            active_crawler = None
    except:
        pass
    
    scraping_state.update({
        "is_running": False,
        "status": "Stopped by user"
    })
    
    return {"message": "Scraping stopped", "results_count": scraping_state["results_count"]}


@app.get("/v1/results", dependencies=[Depends(verify_api_key)])
async def get_results(
    limit: int = Query(100, description="Max results to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get scraped results"""
    global results_storage
    
    total = len(results_storage)
    data = results_storage[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "count": len(data),
        "data": data
    }


@app.delete("/v1/results", dependencies=[Depends(verify_api_key)])
async def clear_results():
    """Clear stored results"""
    global results_storage
    count = len(results_storage)
    results_storage = []
    return {"message": "Results cleared", "cleared_count": count}


# ===========================================
# Main Entry Point
# ===========================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    print(f"""
    ╔═══════════════════════════════════════════════════╗
    ║     GOOGLE MAPS SCRAPER API                       ║
    ║     Created by: dewhush                           ║
    ╠═══════════════════════════════════════════════════╣
    ║  Local:  http://localhost:{port}                    ║
    ║  Docs:   http://localhost:{port}/docs               ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
