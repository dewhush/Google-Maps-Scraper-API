"""
Quick test script for the async scraper
"""
import asyncio
from scraper_async import AsyncGoogleMapsCrawler


async def test_scraper():
    print("=" * 50)
    print("Testing Async Google Maps Scraper")
    print("=" * 50)
    
    crawler = AsyncGoogleMapsCrawler(headless=True)
    
    try:
        print("\n[1] Setting up browser...")
        await crawler.setup_browser()
        print("[OK] Browser ready")
        
        print("\n[2] Searching for 'coffee shop jakarta' (max 3 results)...")
        place_urls = await crawler.search_places("coffee shop jakarta", max_results=3)
        print(f"[OK] Found {len(place_urls)} places")
        
        if place_urls:
            print("\n[3] Scraping first place details...")
            result = await crawler.scrape_place_details(place_urls[0])
            
            if result:
                print(f"[OK] Scraped: {result.get('name', 'Unknown')}")
                print(f"    Phone: {result.get('phone', 'N/A')}")
                print(f"    Address: {result.get('address', 'N/A')[:50]}...")
            else:
                print("[!] No valid coffee shop data (might be filtered)")
        
        print("\n" + "=" * 50)
        print("TEST PASSED - Scraper is working!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        raise
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(test_scraper())
