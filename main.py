import time
import random
import json
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

class GoogleMapsCrawler:
    def __init__(self, headless=True, output_file="data.json"):
        self.headless = headless
        self.output_file = output_file
        self.driver = None
        self.wait = None
        self.results = []
        
        # Keywords for coffee shops in Indonesian
        self.coffee_keywords = [
            "coffee shop", "kedai kopi", "kafe", "cafe", "kopi",
            "coffee house", "rumah kopi", "coffee roaster", "kopi jakarta",
            "warkop", "warung kopi", "kafe jakarta"
        ]
        
        # Jakarta areas
        self.jakarta_areas = [
            # Main regions
            "Jakarta", "Jakarta Barat", "Jakarta Timur", "Jakarta Selatan", "Jakarta Utara", "Jakarta Pusat",
            # Jakarta Selatan
            "Kemang", "Senopati", "Blok M", "Fatmawati", "Cipete", "Cilandak", "Pondok Indah", 
            "Tebet", "Pancoran", "Pasar Minggu", "Kebayoran Baru", "Kebayoran Lama", "Mampang",
            "Pejaten", "Kalibata", "Warung Buncit", "Radio Dalam", "Gandaria", "Jeruk Purut",
            "Bangka", "Pela Mampang", "Ampera", "Bintaro", "Pesanggrahan", "Lebak Bulus",
            "Ciputat", "Cinere", "Ragunan", "TB Simatupang", "Antasari",
            # Jakarta Pusat
            "Menteng", "Sudirman", "Thamrin", "Cikini", "Sarinah", "Tanah Abang", "Senen", 
            "Gondangdia", "Gambir", "Monas", "Kebon Sirih", "Wahid Hasyim", "Pecenongan",
            "Sawah Besar", "Mangga Besar", "Pasar Baru", "Kemayoran", "Gunung Sahari",
            "Johar Baru", "Cempaka Putih", "Kramat", "Matraman",
            # Jakarta Utara
            "Kelapa Gading", "PIK", "Pantai Indah Kapuk", "Sunter", "Pluit", "Ancol", "Tanjung Priok",
            "Pademangan", "Penjaringan", "Cilincing", "Koja", "PIK 2", "Golf Island",
            "Muara Karang", "Kapuk", "Mangga Dua",
            # Jakarta Barat
            "Grogol", "Tanjung Duren", "Kebon Jeruk", "Puri Indah", "Green Ville", "Cengkareng",
            "Tomang", "Slipi", "Kota Tua", "Glodok", "Palmerah", "Meruya", "Joglo",
            "Kembangan", "Pos Pengumben", "Duri Kepa", "Jelambar", "Tambora", "Kalideres",
            "Citra Garden", "Puri Kembangan", "Green Garden", "Intercon",
            # Jakarta Timur
            "Cawang", "Kalimalang", "Rawamangun", "Pulomas", "Cipinang", "Jatinegara", 
            "Duren Sawit", "Pondok Kelapa", "Cibubur", "Kelapa Dua Wetan", "Buaran",
            "Klender", "Malakasari", "Kampung Melayu", "Bidara Cina", "Utan Kayu",
            "Pisangan", "Pulo Gadung", "Cakung", "Pondok Bambu", "Lubang Buaya",
            "Condet", "Kramat Jati", "Makasar", "Halim", "Ciracas", "Pasar Rebo",
            # Popular spots & Business districts
            "Kuningan", "Setiabudi", "Rasuna Said", "Gatot Subroto", "SCBD", "Mega Kuningan",
            "Sudirman Central", "Casablanca", "Epicentrum", "Karet", "Setia Budi",
            # Malls & Commercial areas
            "Grand Indonesia", "Plaza Indonesia", "Pacific Place", "Senayan City", "FX Sudirman",
            "Central Park", "Neo Soho", "Lippo Mall Puri", "Pondok Indah Mall", "Gandaria City",
            "Kota Kasablanka", "Mall Kelapa Gading", "Summarecon Mall Kelapa Gading", "Emporium Pluit"
        ]
    
    def setup_driver(self):
        """Setup Chrome driver with options - works on local, Render, and Ubuntu VPS"""
        is_render = os.environ.get("RENDER") is not None
        is_ubuntu_vps = os.path.exists("/snap/bin/chromium")  # Detect snap chromium on Ubuntu
        
        if is_render:
            # Render.com hosting - use pre-installed Chrome and ChromeDriver
            print("[INFO] Detected Render environment")
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless=new")
            
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--single-process")
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("--remote-debugging-port=9222")
            
            # Render's Chrome binary location
            chrome_options.binary_location = "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome"
            
            user_agents = [
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
            chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
            
            # Use Render's pre-installed chromedriver
            service = Service("/opt/render/project/.render/chromedriver/chromedriver")
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("[OK] Chrome driver initialized on Render")
            
        elif is_ubuntu_vps:
            # Ubuntu VPS with snap chromium
            print("[INFO] Detected Ubuntu VPS with snap chromium")
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless=new")
            
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Use snap chromium binary
            chrome_options.binary_location = "/snap/bin/chromium"
            
            user_agents = [
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            ]
            chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
            
            # Use snap chromedriver (matches snap chromium version)
            service = Service("/snap/chromium/current/usr/lib/chromium-browser/chromedriver")
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("[OK] Chrome driver initialized on Ubuntu VPS")
            
        else:
            # Local development - use undetected-chromedriver
            print("[INFO] Local development environment")
            try:
                import undetected_chromedriver as uc
                
                options = uc.ChromeOptions()
                
                if self.headless:
                    options.add_argument("--headless=new")
                
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-notifications")
                options.add_argument("--disable-popup-blocking")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                
                self.driver = uc.Chrome(options=options, use_subprocess=True)
                print("[OK] Using undetected-chromedriver")
                
            except Exception as e:
                print(f"[!] undetected-chromedriver failed: {e}")
                print("[...] Falling back to standard Selenium with webdriver-manager...")
                
                chrome_options = Options()
                
                if self.headless:
                    chrome_options.add_argument("--headless=new")
                
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--disable-popup-blocking")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ]
                chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
                
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": user_agents[0]
                })
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                print("[OK] Using standard Selenium with webdriver-manager")
        
        self.wait = WebDriverWait(self.driver, 15)
        return self.driver
    
    def search_places(self, query, max_results=50):
        """Search for places on Google Maps"""
        print(f"[+] Searching for: {query}")
        
        # Navigate to Google Maps
        self.driver.get("https://www.google.com/maps")
        time.sleep(random.uniform(2, 4))
        
        try:
            # Accept cookies if appears
            try:
                accept_button = self.driver.find_elements(By.XPATH, "//button[contains(., 'Accept')]")
                if accept_button:
                    accept_button[0].click()
                    time.sleep(1)
            except:
                pass
            
            # Find search box
            search_box = self.wait.until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            # Clear and enter search query
            search_box.clear()
            time.sleep(random.uniform(0.5, 1.5))
            
            # Type slowly to mimic human
            for char in query:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
            
            time.sleep(random.uniform(0.5, 1))
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results to load
            time.sleep(random.uniform(3, 5))
            
            # Scroll to load more results
            self.scroll_for_results(max_results)
            
            # Extract place URLs
            place_urls = self.extract_place_urls()
            
            print(f"[+] Found {len(place_urls)} places for query: {query}")
            return place_urls
            
        except Exception as e:
            print(f"[!] Error during search: {str(e)}")
            return []
    
    def scroll_for_results(self, max_results):
        """Scroll to load more results"""
        try:
            # Find results panel
            results_panel = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
            )
            
            last_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", results_panel
            )
            
            loaded_results = 0
            max_scrolls = 10
            
            for scroll in range(max_scrolls):
                # Count current results
                current_results = len(self.driver.find_elements(By.XPATH, "//a[contains(@href, '/place/')]"))
                
                if current_results >= max_results:
                    print(f"[+] Loaded {current_results} results")
                    break
                
                # Scroll down
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", results_panel
                )
                
                # Random delay
                time.sleep(random.uniform(2, 4))
                
                # Check if new content loaded
                new_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight", results_panel
                )
                
                if new_height == last_height:
                    # Try to click "More results" if exists
                    try:
                        more_button = self.driver.find_elements(
                            By.XPATH, "//button[contains(., 'More results') or contains(., 'See more')]"
                        )
                        if more_button:
                            more_button[0].click()
                            time.sleep(random.uniform(2, 3))
                    except:
                        pass
                
                last_height = new_height
                loaded_results = current_results
                
                print(f"[...] Scroll {scroll + 1}: Loaded {loaded_results} results")
            
            time.sleep(random.uniform(2, 3))
            
        except Exception as e:
            print(f"[!] Error during scrolling: {str(e)}")
    
    def extract_place_urls(self):
        """Extract place URLs from search results"""
        place_urls = []
        
        try:
            # Find all place links
            place_elements = self.driver.find_elements(
                By.XPATH, "//a[contains(@href, '/place/') and @href!='']"
            )
            
            for element in place_elements:
                try:
                    url = element.get_attribute("href")
                    if url and "/place/" in url and url not in place_urls:
                        # Get place name from href or text
                        place_name = element.text.strip()
                        if not place_name:
                            # Try to get from aria-label
                            place_name = element.get_attribute("aria-label") or ""
                        
                        place_urls.append({
                            "url": url,
                            "name": place_name[:100] if place_name else "Unknown"
                        })
                        
                except Exception as e:
                    continue
            
            # Remove duplicates
            seen_urls = set()
            unique_place_urls = []
            
            for place in place_urls:
                if place["url"] not in seen_urls:
                    seen_urls.add(place["url"])
                    unique_place_urls.append(place)
            
            return unique_place_urls
            
        except Exception as e:
            print(f"[!] Error extracting URLs: {str(e)}")
            return []
    
    def scrape_place_details(self, place_url):
        """Scrape detailed information from a place page"""
        try:
            print(f"[→] Scraping: {place_url['url']}")
            
            self.driver.get(place_url["url"])
            time.sleep(random.uniform(3, 5))
            
            place_data = {
                "name": "",
                "address": "",
                "phone": "",
                "website": "",
                "rating": "",
                "reviews": "",
                "category": "",
                "hours": "",
                "source_url": place_url["url"]
            }
            
            # Wait for page to load
            time.sleep(random.uniform(2, 4))
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract name
            try:
                name_elem = soup.find('h1', {'class': 'DUwDvf'})
                if name_elem:
                    place_data["name"] = name_elem.text.strip()
                else:
                    # Alternative name extraction
                    name_elem = soup.find('h1')
                    if name_elem:
                        place_data["name"] = name_elem.text.strip()
            except:
                pass
            
            if not place_data["name"]:
                place_data["name"] = place_url.get("name", "Unknown")
            
            # Extract phone number
            try:
                phone_elem = soup.find('button', {'data-item-id': 'phone'})
                if phone_elem:
                    phone_text = phone_elem.text.strip()
                    # Extract only numbers
                    phone_numbers = re.findall(r'[\d\s\+\(\)\-]+', phone_text)
                    if phone_numbers:
                        place_data["phone"] = phone_numbers[0].strip()
                
                # Alternative phone extraction
                if not place_data["phone"]:
                    # Try multiple selectors
                    selectors = [
                        'div[data-tooltip*="Telepon"]',
                        'div[data-tooltip*="phone"]',
                        'button[aria-label*="Telepon"]',
                        'button[aria-label*="phone"]',
                        'div[class*="phone"]',
                        'span[class*="phone"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            phone_elem = soup.select_one(selector)
                            if phone_elem:
                                phone_text = phone_elem.text.strip()
                                phone_numbers = re.findall(r'[\d\s\+\(\)\-]+', phone_text)
                                if phone_numbers:
                                    place_data["phone"] = phone_numbers[0].strip()
                                    break
                        except:
                            continue
            except:
                pass
            
            # Check if it's a coffee shop
            is_coffee_shop = self.is_coffee_shop(place_data)
            
            if is_coffee_shop and place_data["phone"]:
                # Clean phone number
                place_data["phone"] = self.clean_phone_number(place_data["phone"])
                print(f"[OK] Coffee Shop: {place_data['name']} | Phone: {place_data['phone']}")
                self.results.append(place_data)
                return place_data
            else:
                reason = "Not Coffee Shop" if not is_coffee_shop else "No Phone Number"
                print(f"[SKIP] {reason}: {place_data['name']}")
                return None
            
        except Exception as e:
            print(f"[!] Error scraping {place_url['url']}: {str(e)}")
            return None
    
    def is_coffee_shop(self, place_data):
        """Check if place is a coffee shop"""
        name = place_data["name"].lower()
        category = place_data["category"].lower() if place_data["category"] else ""
        
        coffee_indicators = [
            "coffee", "kopi", "cafe", "kafe", "roaster", "roasting",
            "espresso", "latte", "cappuccino", "arabica", "robusta",
            "warkop", "warung kopi", "coffee shop", "kedai kopi",
            "coffee house", "rumah kopi", "coffee &", "kopi &"
        ]
        
        # Check name and category
        for indicator in coffee_indicators:
            if indicator in name or indicator in category:
                return True
        
        # Additional check for Jakarta coffee shops
        jakarta_indicators = ["jakarta", "jkt", "kemang", "senopati", "menteng", "sudirman"]
        for indicator in jakarta_indicators:
            if indicator in name.lower():
                # If in Jakarta, more likely to be coffee shop
                return True
        
        return False
    
    def clean_phone_number(self, phone):
        """Clean and standardize phone number"""
        if not phone:
            return ""
        
        # Remove non-digit characters except plus
        cleaned = re.sub(r'[^\d\+]', '', phone)
        
        # Standardize Indonesian numbers
        if cleaned.startswith('0'):
            cleaned = '62' + cleaned[1:]
        elif cleaned.startswith('8') and not cleaned.startswith('+'):
            cleaned = '62' + cleaned
        
        # Ensure it's a valid length
        if len(cleaned) < 10 or len(cleaned) > 15:
            return ""
        
        return cleaned
    
    def crawl_jakarta_coffee_shops(self, max_per_area=20):
        """Main crawl function for Jakarta coffee shops"""
        print("[START] Starting Jakarta Coffee Shop Crawler")
        print("[INFO] Target areas: Jakarta and surrounding areas")
        print("[INFO] Focus: Coffee Shops with Phone Numbers\n")
        
        all_place_urls = []
        
        # Define search queries
        search_queries = [
            "coffee shop jakarta",
            "kedai kopi jakarta",
            "cafe jakarta",
            "kafe jakarta",
            "kopi jakarta",
            "coffee house jakarta",
            "rumah kopi jakarta",
            "coffee roaster jakarta",
            "warkop jakarta",
            "warung kopi jakarta",
            "coffee shop jakarta barat",
            "coffee shop jakarta timur",
            "coffee shop jakarta selatan",
            "coffee shop jakarta utara",
            "kedai kopi jakarta pusat",
            "cafe kemang",
            "kopi senopati",
            "coffee shop menteng",
            "kafe sudirman",
            "kopi kuningan",
            "coffee shop kelapa gading",
            "cafe PIK"
        ]
        
        # Search for each query
        for i, query in enumerate(search_queries):
            print(f"\n{'='*60}")
            print(f"Search [{i+1}/{len(search_queries)}]: {query}")
            print('='*60)
            
            place_urls = self.search_places(query, max_per_area)
            
            for place_url in place_urls:
                if place_url not in all_place_urls:
                    all_place_urls.append(place_url)
            
            # Random delay between searches
            if i < len(search_queries) - 1:  # No delay after last query
                delay = random.uniform(4, 8)
                print(f"[WAIT] Waiting {delay:.1f}s before next search...")
                time.sleep(delay)
            
            # Limit total URLs
            if len(all_place_urls) >= 100:
                print(f"[!] Reached maximum limit of 100 places")
                break
        
        # Scrape details for each place
        print(f"\n{'='*60}")
        print(f"Scraping details for {len(all_place_urls)} places")
        print('='*60)
        
        successful_scrapes = 0
        
        for i, place_url in enumerate(all_place_urls):
            try:
                place_data = self.scrape_place_details(place_url)
                
                if place_data and place_data.get("phone"):
                    successful_scrapes += 1
                
                # Save progress every 10 places
                if (i + 1) % 10 == 0:
                    self.save_simple_format(self.output_file)
                
                # Random delay to avoid detection
                delay = random.uniform(5, 10)
                print(f"[WAIT] Waiting {delay:.1f}s before next...")
                time.sleep(delay)
                
            except Exception as e:
                print(f"[!] Failed to scrape {place_url['url']}: {str(e)}")
                time.sleep(random.uniform(10, 15))
                continue
        
        print(f"\n[DONE] Crawling completed!")
        print(f"[STATS] Total places found: {len(all_place_urls)}")
        print(f"[STATS] Coffee shops with phone numbers: {successful_scrapes}")
        
        return self.results
    
    def save_simple_format(self, filename="data.json"):
        """Save in simple format {contacts: [{name, phone}]}"""
        if not self.results:
            print("[!] No results to save")
            return False
        
        # Prepare data in simple format
        simple_data = {"contacts": []}
        
        for result in self.results:
            if result.get("phone") and result.get("name"):
                # Clean phone number again
                phone = self.clean_phone_number(result["phone"])
                name = result["name"].strip()
                
                if phone and name:
                    contact = {
                        "name": name,
                        "phone": phone
                        # NOTES FIELD REMOVED as requested
                    }
                    simple_data["contacts"].append(contact)
        
        # Remove duplicates based on phone number
        seen_phones = set()
        unique_contacts = []
        
        for contact in simple_data["contacts"]:
            phone = contact["phone"]
            if phone not in seen_phones:
                seen_phones.add(phone)
                unique_contacts.append(contact)
        
        simple_data["contacts"] = unique_contacts
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(simple_data, f, indent=2, ensure_ascii=False)
        
        print(f"[SAVE] Simple format saved to {filename}")
        print(f"[STATS] Total unique contacts: {len(unique_contacts)}")
        
        return True
    
    def save_results(self, format='json', filename=None):
        """Save results to file"""
        if not self.results:
            print("[!] No results to save")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == 'json':
            if not filename:
                filename = f"coffee_shops_jakarta_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            print(f"[SAVE] Detailed results saved to {filename}")
            
            # Always save in simple format
            # Always save in simple format
            self.save_simple_format(self.output_file)
            
        elif format == 'csv':
            if not filename:
                filename = f"coffee_shops_jakarta_{timestamp}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if self.results:
                    writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                    writer.writeheader()
                    writer.writerows(self.results)
            
            print(f"[SAVE] CSV results saved to {filename}")
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()
            print("[CLOSE] Browser closed")

def main():
    """Main function to run the crawler"""
    print("="*70)
    print("GOOGLE MAPS COFFEE SHOP CRAWLER - JAKARTA, INDONESIA")
    print("="*70)
    print("\n[INFO] This script will:")
    print("  1. Search for coffee shops in Jakarta areas")
    print("  2. Extract business names and phone numbers")
    print("  3. Save results in format for WhatsApp campaign")
    print("  4. Output file: data.json (simple format)\n")
    
    # Configuration
    max_results = input("Maximum results per area (default 15): ").strip()
    max_results = int(max_results) if max_results.isdigit() else 15
    
    headless = input("Run in headless mode? (y/n, default y): ").strip().lower()
    headless = headless != 'n'
    
    print(f"\n[CONFIG] Configuration:")
    print(f"  Max results per area: {max_results}")
    print(f"  Headless mode: {'Yes' if headless else 'No'}")
    print(f"  Output file: data.json")
    print(f"  Estimated time: ~{max_results * 2} minutes\n")
    
    confirm = input("Start crawling? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("[!] Crawling cancelled")
        return
    
    # Initialize crawler
    crawler = GoogleMapsCrawler(headless=headless)
    
    try:
        # Setup driver
        print("\n[START] Setting up browser...")
        crawler.setup_driver()
        
        # Start crawling
        results = crawler.crawl_jakarta_coffee_shops(max_per_area=max_results)
        
        # Save final results
        print("\n" + "="*70)
        print("[SAVE] SAVING RESULTS")
        print("="*70)
        
        crawler.save_results(format='json')
        
        # Show summary
        print("\n" + "="*70)
        print("[STATS] FINAL SUMMARY")
        print("="*70)
        
        # Load and show the simple format
        try:
            with open("data.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            total_contacts = len(data["contacts"])
            
            print(f"\n[OK] Total coffee shops found: {len(results)}")
            print(f"[OK] With valid phone numbers: {total_contacts}")
            print(f"[OK] Saved to: data.json")
            
            if total_contacts > 0:
                print("\n[LIST] First 10 contacts:")
                for i, contact in enumerate(data["contacts"][:10]):
                    print(f"  {i+1}. {contact['name']} - {contact['phone']}")
                
                print("\n[SAMPLE] Sample of data.json format:")
                sample = {
                    "contacts": data["contacts"][:3] if len(data["contacts"]) >= 3 else data["contacts"]
                }
                print(json.dumps(sample, indent=2, ensure_ascii=False))
        
        except Exception as e:
            print(f"[!] Error reading data.json: {str(e)}")
        
        print("\n[NEXT] NEXT STEPS:")
        print("  1. Review data.json file")
        print("  2. Add 'notes' field manually if needed")
        print("  3. Run WhatsApp campaign: python coffee_shop_campaign.py")
        
    except KeyboardInterrupt:
        print("\n\n[!] Crawling interrupted by user")
        # Save partial results
        if crawler.results:
            print("[SAVE] Saving partial results...")
            crawler.save_simple_format("data_partial.json")
    except Exception as e:
        print(f"\n[!] Error during crawling: {str(e)}")
    finally:
        crawler.close()

def quick_crawl():
    """Quick crawl function with default settings"""
    print("[START] Starting quick crawl with default settings...")
    print("[INFO] Output will be saved to data.json\n")
    
    crawler = GoogleMapsCrawler(headless=True)
    
    try:
        crawler.setup_driver()
        
        # Quick search for popular coffee shops
        queries = [
            "coffee shop jakarta",
            "kedai kopi jakarta",
            "cafe jakarta",
            "kopi jakarta selatan",
            "kopi jakarta timur"
        ]
        
        all_results = []
        
        for query in queries:
            print(f"\n[SEARCH] Searching: {query}")
            place_urls = crawler.search_places(query, max_results=10)
            
            for place_url in place_urls:
                place_data = crawler.scrape_place_details(place_url)
                if place_data and place_data.get("phone"):
                    place_data["phone"] = crawler.clean_phone_number(place_data["phone"])
                    all_results.append(place_data)
                
                time.sleep(random.uniform(3, 5))
        
        crawler.results = all_results
        
        # Save results
        crawler.save_simple_format("data.json")
        
        print(f"\n[DONE] Quick crawl completed!")
        print(f"[STATS] Found {len(all_results)} coffee shops with phone numbers")
        
    finally:
        crawler.close()

if __name__ == "__main__":
    # Create requirements file
    requirements = """selenium>=4.15.0
beautifulsoup4>=4.12.0
webdriver-manager>=4.0.0
requests>=2.28.0
"""
    
    with open("requirements_crawler.txt", "w") as f:
        f.write(requirements)
    
    print("[PKG] Dependencies file created: requirements_crawler.txt")
    print("[PKG] Install with: pip install -r requirements_crawler.txt\n")
    
    # Check if dependencies are installed
    try:
        from selenium import webdriver
        from bs4 import BeautifulSoup
    except ImportError:
        print("[ERROR] Required packages not installed!")
        print("[PKG] Please run: pip install selenium beautifulsoup4 webdriver-manager")
        exit(1)
    
    # Menu
    print("="*70)
    print("GOOGLE MAPS CRAWLER FOR JAKARTA COFFEE SHOPS")
    print("="*70)
    print("1. Full Crawl (All Jakarta areas, more results)")
    print("2. Quick Crawl (Popular coffee shops only, faster)")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        main()
    elif choice == "2":
        quick_crawl()
    else:
        print("[EXIT] Exiting")