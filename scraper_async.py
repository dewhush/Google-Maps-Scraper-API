"""
AsyncGoogleMapsCrawler - Playwright-based async scraper for FastAPI backend
Designed to work seamlessly with FastAPI's async event loop
"""

import asyncio
import random
import json
import re
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Browser, Page, Playwright


class AsyncGoogleMapsCrawler:
    """
    Async Google Maps crawler using Playwright.
    Compatible with FastAPI background tasks.
    """
    
    def __init__(self, headless: bool = True, output_file: str = "data.json", config: Dict[str, Any] = None):
        self.headless = headless
        self.output_file = output_file
        self.config = config or {}
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.results: List[Dict[str, Any]] = []
        
        # Progress callback for status updates
        self.on_progress: Optional[callable] = None
    
    async def setup_browser(self) -> None:
        """Initialize Playwright browser"""
        print("[INFO] Setting up Playwright browser...")
        
        self.playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-notifications",
                "--disable-popup-blocking",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        }
        
        # Check for VPS environment
        is_vps = os.path.exists("/snap/bin/chromium") or os.environ.get("RENDER")
        
        if is_vps:
            print("[INFO] Detected server environment")
            # Use system chromium if available
            if os.path.exists("/snap/bin/chromium"):
                launch_options["executable_path"] = "/snap/bin/chromium"
        
        try:
            self.browser = await self.playwright.chromium.launch(**launch_options)
        except Exception as e:
            print(f"[WARN] Failed with custom options, trying default: {e}")
            # Fallback to default launch
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
        
        # Create a new page with realistic viewport and user agent
        context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.page = await context.new_page()
        
        # Block unnecessary resources for faster loading
        await self.page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())
        
        print("[OK] Playwright browser ready")
    
    async def search_places(self, query: str, max_results: int = 50) -> List[Dict[str, str]]:
        """Search for places on Google Maps"""
        print(f"[+] Searching for: {query}")
        
        if not self.page:
            raise RuntimeError("Browser not initialized. Call setup_browser() first.")
        
        # Navigate to Google Maps
        await self.page.goto("https://www.google.com/maps", wait_until="networkidle")
        await asyncio.sleep(random.uniform(2, 3))
        
        try:
            # Accept cookies if dialog appears
            try:
                accept_btn = self.page.locator("button:has-text('Accept')")
                if await accept_btn.count() > 0:
                    await accept_btn.first.click()
                    await asyncio.sleep(1)
            except:
                pass
            
            # Find and fill search box
            search_box = self.page.locator("#searchboxinput")
            await search_box.wait_for(state="visible", timeout=10000)
            await search_box.clear()
            
            # Type query with human-like delay
            await search_box.type(query, delay=50)
            await asyncio.sleep(random.uniform(0.5, 1))
            
            # Press Enter to search
            await search_box.press("Enter")
            
            # Wait for results to load
            await asyncio.sleep(random.uniform(3, 4))
            
            # Scroll to load more results
            await self.scroll_for_results(max_results)
            
            # Extract place URLs
            place_urls = await self.extract_place_urls()
            
            print(f"[+] Found {len(place_urls)} places for query: {query}")
            return place_urls
            
        except Exception as e:
            print(f"[!] Error during search: {str(e)}")
            return []
    
    async def scroll_for_results(self, max_results: int) -> None:
        """Scroll the results panel to load more places"""
        try:
            # Find results panel (feed container)
            results_panel = self.page.locator("div[role='feed']")
            
            if await results_panel.count() == 0:
                print("[!] Results panel not found")
                return
            
            last_count = 0
            max_scrolls = 10
            
            for scroll in range(max_scrolls):
                # Count current results
                current_count = await self.page.locator("a[href*='/place/']").count()
                
                if current_count >= max_results:
                    print(f"[+] Loaded {current_count} results")
                    break
                
                if current_count == last_count and scroll > 2:
                    print(f"[+] No more results to load ({current_count} total)")
                    break
                
                # Scroll the results panel
                await results_panel.evaluate("el => el.scrollTop = el.scrollHeight")
                
                # Wait for new content
                await asyncio.sleep(random.uniform(1.5, 2.5))
                
                last_count = current_count
                print(f"[...] Scroll {scroll + 1}: Loaded {current_count} results")
            
        except Exception as e:
            print(f"[!] Error during scrolling: {str(e)}")
    
    async def extract_place_urls(self) -> List[Dict[str, str]]:
        """Extract place URLs from search results"""
        place_urls = []
        
        try:
            # Find all place links
            place_elements = self.page.locator("a[href*='/place/']")
            count = await place_elements.count()
            
            seen_urls = set()
            
            for i in range(count):
                try:
                    element = place_elements.nth(i)
                    url = await element.get_attribute("href")
                    
                    if url and "/place/" in url and url not in seen_urls:
                        seen_urls.add(url)
                        
                        # Try to get place name
                        name = await element.get_attribute("aria-label") or ""
                        if not name:
                            name = await element.inner_text() or "Unknown"
                        
                        place_urls.append({
                            "url": url,
                            "name": name[:100]
                        })
                        
                except Exception:
                    continue
            
            return place_urls
            
        except Exception as e:
            print(f"[!] Error extracting URLs: {str(e)}")
            return []
    
    async def scrape_place_details(self, place_url: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Scrape detailed information from a place page"""
        try:
            url = place_url["url"]
            print(f"[→] Scraping: {place_url.get('name', 'Unknown')[:40]}...")
            
            await self.page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 3))
            
            place_data = {
                "name": "",
                "address": "",
                "phone": "",
                "website": "",
                "rating": "",
                "reviews": "",
                "category": "",
                "hours": "",
                "source_url": url,
                "lat": None,
                "lng": None
            }
            
            # Extract name
            try:
                name_elem = self.page.locator("h1.DUwDvf").first
                if await name_elem.count() > 0:
                    place_data["name"] = await name_elem.inner_text()
                else:
                    place_data["name"] = place_url.get("name", "Unknown")
            except:
                place_data["name"] = place_url.get("name", "Unknown")
            
            # Extract phone number
            try:
                # Method 1: Look for phone button
                phone_btn = self.page.locator("button[data-item-id='phone']")
                if await phone_btn.count() > 0:
                    phone_text = await phone_btn.inner_text()
                    phone_numbers = re.findall(r'[\d\s\+\(\)\-]+', phone_text)
                    if phone_numbers:
                        place_data["phone"] = phone_numbers[0].strip()
                
                # Method 2: Look for aria-label containing phone
                if not place_data["phone"]:
                    phone_elem = self.page.locator("[aria-label*='Phone'], [aria-label*='Telepon']")
                    if await phone_elem.count() > 0:
                        phone_text = await phone_elem.first.inner_text()
                        phone_numbers = re.findall(r'[\d\s\+\(\)\-]+', phone_text)
                        if phone_numbers:
                            place_data["phone"] = phone_numbers[0].strip()
            except:
                pass
            
            # Extract address
            try:
                addr_btn = self.page.locator("button[data-item-id='address']")
                if await addr_btn.count() > 0:
                    place_data["address"] = await addr_btn.inner_text()
            except:
                pass
            
            # Extract rating
            try:
                rating_elem = self.page.locator("div.F7nice span[aria-hidden='true']").first
                if await rating_elem.count() > 0:
                    place_data["rating"] = await rating_elem.inner_text()
            except:
                pass
            
            # Extract category
            try:
                category_btn = self.page.locator("button[jsaction*='category']").first
                if await category_btn.count() > 0:
                    place_data["category"] = await category_btn.inner_text()
            except:
                pass
            
            # Extract coordinates from URL
            try:
                current_url = self.page.url
                coord_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
                if coord_match:
                    place_data["lat"] = float(coord_match.group(1))
                    place_data["lng"] = float(coord_match.group(2))
            except:
                pass
            
            # 1. Check Filters
            phone_req = self.config.get("phone_required", True)
            web_req = self.config.get("website_required", False)
            
            has_phone = bool(place_data["phone"])
            has_web = bool(place_data["website"])
            
            if phone_req and not has_phone:
                print(f"[SKIP] No Phone: {place_data['name']}")
                return None
                
            if web_req and not has_web:
                print(f"[SKIP] No Website: {place_data['name']}")
                return None

            # 2. Clean Phone
            if has_phone:
                place_data["phone"] = self._clean_phone_number(place_data["phone"])
                # If cleaning failed but phone was required, skip
                if not place_data["phone"] and phone_req:
                    print(f"[SKIP] Invalid Phone: {place_data['name']}")
                    return None
            
            print(f"[OK] {place_data['name']} | Phone: {place_data['phone']}")
            self.results.append(place_data)
            return place_data
            
        except Exception as e:
            print(f"[!] Error scraping {place_url.get('url', 'unknown')}: {str(e)}")
            return None
    
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean and standardize phone number based on country code"""
        if not phone:
            return ""
        
        # Remove non-digit characters except plus
        cleaned = re.sub(r'[^\d\+]', '', phone)
        country = self.config.get("country_code", "ID").upper()
        
        if country == "ID":
            # Standardize Indonesian numbers
            if cleaned.startswith('0'):
                cleaned = '62' + cleaned[1:]
            elif cleaned.startswith('8') and not cleaned.startswith('+'):
                cleaned = '62' + cleaned
            elif cleaned.startswith('+62'):
                cleaned = cleaned[1:]  # Remove the plus
        elif country == "US":
            # Standardize US numbers
            cleaned = re.sub(r'^(\+1|1)', '', cleaned)
            if len(cleaned) == 10:
                cleaned = '1' + cleaned
        
        # General validation: length should be between 7 and 15
        if len(cleaned) < 7 or len(cleaned) > 15:
            return ""
        
        return cleaned
    
    async def crawl(self, query: str, max_results: int = 20, 
                    progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Main crawl function - search and scrape places.
        
        Args:
            query: Search query (e.g., "coffee shop jakarta")
            max_results: Maximum number of results to scrape
            progress_callback: Optional async callback(status, progress, total)
        """
        self.on_progress = progress_callback
        
        async def report_progress(status: str, progress: int, total: int):
            if self.on_progress:
                await self.on_progress(status, progress, total)
        
        await report_progress("Searching...", 10, 100)
        
        # Generate search queries
        search_queries = [query]
        if "jakarta" in query.lower():
            base = query.lower().replace("jakarta", "").strip()
            if base:
                search_queries.extend([
                    f"{base} jakarta selatan",
                    f"{base} jakarta pusat",
                    f"{base} jakarta barat",
                ])
        
        all_place_urls = []
        
        # Search phase
        for i, search_query in enumerate(search_queries):
            progress = 10 + int((i / len(search_queries)) * 40)
            await report_progress(f"Searching: {search_query}", progress, 100)
            
            place_urls = await self.search_places(search_query, max_results)
            
            for place_url in place_urls:
                if place_url["url"] not in [p["url"] for p in all_place_urls]:
                    all_place_urls.append(place_url)
            
            await asyncio.sleep(random.uniform(1, 2))
        
        # Scrape phase
        total_places = min(len(all_place_urls), max_results * 2)
        await report_progress(f"Scraping {total_places} places...", 50, 100)
        
        for i, place_url in enumerate(all_place_urls[:total_places]):
            progress = 50 + int((i / total_places) * 45)
            await report_progress(
                f"Scraping {i+1}/{total_places}: {place_url.get('name', 'Unknown')[:30]}...",
                progress, 100
            )
            
            await self.scrape_place_details(place_url)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        await report_progress("Completed!", 100, 100)
        
        print(f"[DONE] Scraped {len(self.results)} coffee shops with phone numbers")
        return self.results
    
    async def save_results(self, filename: Optional[str] = None) -> bool:
        """Save results to JSON file"""
        if not self.results:
            print("[!] No results to save")
            return False
        
        filename = filename or self.output_file
        
        # Prepare simple format
        simple_data = {"contacts": []}
        seen_phones = set()
        
        for result in self.results:
            phone = result.get("phone", "")
            name = result.get("name", "").strip()
            
            if phone and name and phone not in seen_phones:
                seen_phones.add(phone)
                simple_data["contacts"].append({
                    "name": name,
                    "phone": phone,
                    "address": result.get("address", ""),
                    "lat": result.get("lat"),
                    "lng": result.get("lng")
                })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(simple_data, f, indent=2, ensure_ascii=False)
        
        print(f"[SAVE] Saved {len(simple_data['contacts'])} contacts to {filename}")
        return True
    
    async def close(self) -> None:
        """Close browser and cleanup resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print("[CLOSE] Browser closed")
        except Exception as e:
            print(f"[!] Error closing browser: {e}")


# Standalone test
async def main():
    """Test the async crawler"""
    print("=" * 60)
    print("Async Google Maps Crawler - Test")
    print("=" * 60)
    
    crawler = AsyncGoogleMapsCrawler(headless=True)
    
    try:
        await crawler.setup_browser()
        results = await crawler.crawl("coffee shop jakarta", max_results=5)
        await crawler.save_results("test_output.json")
        
        print(f"\n[RESULT] Found {len(results)} coffee shops")
        for r in results[:5]:
            print(f"  - {r['name']}: {r['phone']}")
            
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())
