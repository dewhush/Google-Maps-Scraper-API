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
        self.context = None
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
            if os.path.exists("/snap/bin/chromium"):
                launch_options["executable_path"] = "/snap/bin/chromium"
        
        try:
            self.browser = await self.playwright.chromium.launch(**launch_options)
        except Exception as e:
            print(f"[WARN] Failed with custom options, trying default: {e}")
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
        
        # Main context for searching
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.page = await self.context.new_page()
        
        # Block unnecessary resources for faster loading
        await self.page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())
        
        print("[OK] Playwright browser ready")

    async def _get_new_page(self) -> Page:
        """Create a new page with optimized settings"""
        page = await self.context.new_page()
        # Fast loading: block images and other heavy resources
        await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())
        return page

    async def search_places(self, query: str, max_results: int = 50) -> List[Dict[str, str]]:
        """Search for places on Google Maps"""
        print(f"[+] Searching for: {query}")
        
        if not self.page:
            raise RuntimeError("Browser not initialized. Call setup_browser() first.")
        
        # Navigate to Google Maps
        await self.page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(1, 2))
        
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
            
            # Type query
            await search_box.type(query, delay=30)
            await search_box.press("Enter")
            
            # Wait for results panel
            await self.page.wait_for_selector("div[role='feed']", timeout=15000)
            
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
            results_panel = self.page.locator("div[role='feed']")
            if await results_panel.count() == 0:
                return
            
            last_count = 0
            for scroll in range(15): # Max scrolls
                current_count = await self.page.locator("a[href*='/place/']").count()
                if current_count >= max_results:
                    break
                
                if current_count == last_count and scroll > 5:
                    break
                
                # Scroll the results panel
                await results_panel.evaluate("el => el.scrollTop = el.scrollHeight")
                await asyncio.sleep(random.uniform(1, 2))
                last_count = current_count
                
        except Exception as e:
            print(f"[!] Error during scrolling: {str(e)}")

    async def extract_place_urls(self) -> List[Dict[str, str]]:
        """Extract place URLs from search results"""
        place_urls = []
        try:
            place_elements = self.page.locator("a[href*='/place/']")
            count = await place_elements.count()
            seen_urls = set()
            
            for i in range(count):
                try:
                    element = place_elements.nth(i)
                    url = await element.get_attribute("href")
                    if url and "/place/" in url and url not in seen_urls:
                        seen_urls.add(url)
                        name = await element.get_attribute("aria-label") or await element.inner_text() or "Unknown"
                        place_urls.append({"url": url, "name": name[:100]})
                except: continue
            return place_urls
        except Exception as e:
            print(f"[!] Error extracting URLs: {str(e)}")
            return []

    async def scrape_place_details(self, place_url: Dict[str, str], use_new_page: bool = True) -> Optional[Dict[str, Any]]:
        """Scrape detailed information from a place page"""
        page = self.page
        if use_new_page:
            page = await self._get_new_page()
            
        try:
            url = place_url["url"]
            print(f"[→] Scraping: {place_url.get('name', 'Unknown')[:40]}...")
            
            # Use domcontentloaded for speed
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Minimal wait for core elements
            try:
                await page.wait_for_selector("h1.DUwDvf", timeout=5000)
            except: pass
            
            place_data = {
                "name": "", "address": "", "phone": "", "website": "",
                "rating": "", "reviews": "", "category": "", "hours": "",
                "source_url": url, "lat": None, "lng": None
            }
            
            # Extract data
            try:
                name_elem = page.locator("h1.DUwDvf").first
                place_data["name"] = await name_elem.inner_text() if await name_elem.count() > 0 else place_url.get("name", "Unknown")
            except: place_data["name"] = place_url.get("name", "Unknown")
            
            try:
                phone_btn = page.locator("button[data-item-id='phone']")
                if await phone_btn.count() > 0:
                    text = await phone_btn.inner_text()
                    nums = re.findall(r'[\d\s\+\(\)\-]+', text)
                    if nums: place_data["phone"] = nums[0].strip()
            except: pass
            
            try:
                addr_btn = page.locator("button[data-item-id='address']")
                if await addr_btn.count() > 0: place_data["address"] = await addr_btn.inner_text()
            except: pass
            
            try:
                rating_elem = page.locator("div.F7nice span[aria-hidden='true']").first
                if await rating_elem.count() > 0: place_data["rating"] = await rating_elem.inner_text()
            except: pass

            try:
                category_btn = page.locator("button[jsaction*='category']").first
                if await category_btn.count() > 0: place_data["category"] = await category_btn.inner_text()
            except: pass
            
            try:
                web_btn = page.locator("a[data-item-id='authority']").first
                if await web_btn.count() > 0:
                    place_data["website"] = await web_btn.get_attribute("href")
            except: pass
            
            try:
                curr_url = page.url
                match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', curr_url)
                if match:
                    place_data["lat"] = float(match.group(1))
                    place_data["lng"] = float(match.group(2))
            except: pass
            
            # Filters
            phone_req = self.config.get("phone_required", True)
            web_req = self.config.get("website_required", False)
            min_rating = float(self.config.get("min_rating", 0.0))
            
            has_phone = bool(place_data["phone"])
            rating_str = (place_data["rating"] or "0").replace(",", ".")
            rating_val = float(re.findall(r'\d+\.\d+|\d+', rating_str)[0]) if re.findall(r'\d+\.\d+|\d+', rating_str) else 0.0
            
            if phone_req and not has_phone: return None
            if web_req and not place_data["website"]: return None
            if rating_val < min_rating: return None
            
            # Clean Phone
            if has_phone:
                place_data["phone"] = self._clean_phone_number(place_data["phone"])
                if not place_data["phone"] and phone_req: return None
            
            print(f"[OK] {place_data['name']} | {place_data['phone']}")
            self.results.append(place_data)
            return place_data
            
        except Exception as e:
            print(f"[!] Error scraping {place_url.get('url', 'unknown')}: {str(e)}")
            return None
        finally:
            if use_new_page:
                await page.close()

    def _clean_phone_number(self, phone: str) -> str:
        """Clean and standardize phone number based on country code"""
        if not phone: return ""
        cleaned = re.sub(r'[^\d\+]', '', phone)
        country = self.config.get("country_code", "ID").upper()
        
        if country == "ID":
            if cleaned.startswith('0'): cleaned = '62' + cleaned[1:]
            elif cleaned.startswith('8') and not cleaned.startswith('+'): cleaned = '62' + cleaned
            elif cleaned.startswith('+62'): cleaned = cleaned[1:]
        elif country == "US":
            cleaned = re.sub(r'^(\+1|1)', '', cleaned)
            if len(cleaned) == 10: cleaned = '1' + cleaned
        
        return cleaned if 7 <= len(cleaned) <= 15 else ""
    
    async def crawl(self, query: str, max_results: int = 20, 
                    progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        self.on_progress = progress_callback
        async def report_progress(status, progress, total):
            if self.on_progress: await self.on_progress(status, progress, total)
        
        await report_progress("Searching...", 10, 100)
        search_queries = [query]
        if "jakarta" in query.lower():
            base = query.lower().replace("jakarta", "").strip()
            if base:
                search_queries.extend([f"{base} jakarta selatan", f"{base} jakarta pusat", f"{base} jakarta barat"])
        
        all_place_urls = []
        for i, sq in enumerate(search_queries):
            await report_progress(f"Searching: {sq}", 10 + int((i/len(search_queries))*30), 100)
            urls = await self.search_places(sq, max_results)
            seen = {p["url"] for p in all_place_urls}
            for u in urls:
                if u["url"] not in seen:
                    all_place_urls.append(u)
                    seen.add(u["url"])
            if len(all_place_urls) >= max_results * 1.5: break
            await asyncio.sleep(random.uniform(0.5, 1.0))
        
        target_places = all_place_urls[:min(len(all_place_urls), max_results * 2)]
        await report_progress(f"Found {len(target_places)} places. Scraping...", 40, 100)
        
        semaphore = asyncio.Semaphore(self.config.get("concurrency", 3))
        processed = 0
        
        async def scrape_task(url):
            nonlocal processed
            async with semaphore:
                res = await self.scrape_place_details(url)
                processed += 1
                if processed % 2 == 0 or processed == len(target_places):
                    await report_progress(f"Scraped {processed}/{len(target_places)}: {url['name'][:20]}...", 40 + int((processed/len(target_places))*55), 100)
                return res

        await asyncio.gather(*[scrape_task(u) for u in target_places])
        await report_progress("Completed!", 100, 100)
        return self.results
    
    async def save_results(self, filename: Optional[str] = None) -> bool:
        if not self.results: return False
        filename = filename or self.output_file
        simple_data = {"contacts": []}
        seen_phones = set()
        for r in self.results:
            p = r.get("phone", "")
            if p and p not in seen_phones:
                seen_phones.add(p)
                simple_data["contacts"].append({"name": r["name"], "phone": p, "address": r.get("address", ""), "lat": r.get("lat"), "lng": r.get("lng")})
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(simple_data, f, indent=2, ensure_ascii=False)
        return True
    
    async def close(self) -> None:
        try:
            if self.page: await self.page.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass

async def main():
    crawler = AsyncGoogleMapsCrawler(headless=True)
    try:
        await crawler.setup_browser()
        results = await crawler.crawl("coffee shop jakarta", max_results=5)
        print(f"Found {len(results)} results")
    finally: await crawler.close()

if __name__ == "__main__":
    asyncio.run(main())
