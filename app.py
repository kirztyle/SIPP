import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
import random
import json
from urllib.parse import urlparse, urljoin, quote
import os
from datetime import datetime
import cloudscraper
import undetected_chromedriver as uc  # Untuk bypass anti-bot yang canggih
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import threading

# =============================
# KONFIGURASI LANJUT
# =============================
class Config:
    RATE_LIMIT = 3.0
    MAX_RETRIES = 5
    TIMEOUT = 40
    SELENIUM_TIMEOUT = 30
    USE_PROXY = False
    
    # Proxy list (jika diperlukan)
    PROXIES = [
        # 'http://user:pass@proxy:port',
        # Tambahkan proxy jika ada
    ]

# =============================
# USER AGENT ROTATION ADVANCED
# =============================
class UserAgentManager:
    @staticmethod
    def get_random():
        agents = [
            # Chrome latest
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36",
            # Chrome dengan berbagai build
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Whale/3.21.192.22 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
        ]
        return random.choice(agents)
    
    @staticmethod
    def get_for_domain(domain):
        """Return appropriate user agent based on domain pattern."""
        if 'go.id' in domain:
            # SIPP sites often expect desktop browsers
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        return UserAgentManager.get_random()

# =============================
# HEADERS MANAGEMENT
# =============================
class HeadersManager:
    @staticmethod
    def get_headers(domain=None, referer=None):
        """Generate complete headers with fingerprint."""
        ua = UserAgentManager.get_for_domain(domain) if domain else UserAgentManager.get_random()
        
        # Generate accept headers based on user agent
        if 'Chrome' in ua:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        elif 'Firefox' in ua:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        else:
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        
        # Generate random viewport width
        viewport_width = random.choice([1920, 1536, 1366, 1280])
        
        headers = {
            "User-Agent": ua,
            "Accept": accept,
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "DNT": "1",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Viewport-Width": str(viewport_width),
            "Width": str(viewport_width),
        }
        
        if referer:
            headers["Referer"] = referer
        elif domain:
            headers["Referer"] = "https://www.google.com/"
        
        # Add more headers untuk bypass WAF
        headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            "TE": "trailers",
        })
        
        return headers

# =============================
# SESSION FACTORY - MULTI STRATEGY
# =============================
class SessionFactory:
    @staticmethod
    def create_session(strategy="auto"):
        """
        Create session based on strategy:
        - auto: Try all methods
        - cloudscraper: Use cloudscraper only
        - selenium: Use Selenium WebDriver
        - requests: Use requests only
        """
        
        if strategy == "selenium":
            return SeleniumSession()
        elif strategy == "cloudscraper":
            try:
                scraper = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False,
                    },
                    delay=10,
                    interpreter='nodejs',
                )
                st.success("✅ Created Cloudscraper session")
                return scraper
            except Exception as e:
                st.warning(f"Cloudscraper failed: {e}, falling back to requests")
                return SessionFactory.create_session("requests")
        
        elif strategy == "requests":
            session = requests.Session()
            session.headers.update(HeadersManager.get_headers())
            
            # Add common SIPP cookies
            session.cookies.update({
                'PHPSESSID': f'sipp_{random.randint(100000,999999)}',
                'cookieconsent_status': 'dismiss',
                'ci_session': f'{random.randint(1000000000,9999999999)}',
            })
            
            # Add request hooks untuk logging
            def response_hook(r, *args, **kwargs):
                if hasattr(r, 'from_cache'):
                    st.write(f"Request to {r.url} - Status: {r.status_code}")
            
            session.hooks['response'].append(response_hook)
            return session
        
        else:  # auto - try all
            try:
                return SessionFactory.create_session("cloudscraper")
            except:
                try:
                    return SessionFactory.create_session("selenium")
                except:
                    return SessionFactory.create_session("requests")

# =============================
# SELENIUM SESSION (Untuk bypass paling kuat)
# =============================
class SeleniumSession:
    def __init__(self):
        self.driver = None
        self.init_driver()
        
    def init_driver(self):
        """Initialize undetected Chrome driver."""
        try:
            options = uc.ChromeOptions()
            
            # Add arguments to mimic real browser
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument(f'--window-size={random.randint(1200,1920)},{random.randint(800,1080)}')
            
            # Remove automation flags
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Random user data dir
            user_data_dir = f"./chrome_data_{random.randint(1000,9999)}"
            options.add_argument(f'--user-data-dir={user_data_dir}')
            
            # Create driver
            self.driver = uc.Chrome(
                options=options,
                use_subprocess=True,
                driver_executable_path=None,  # Auto-detect
            )
            
            # Execute CDP commands to hide automation
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": UserAgentManager.get_random(),
                "platform": "Win32"
            })
            
            # Hide webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Override permissions
            self.driver.execute_cdp_cmd('Browser.grantPermissions', {
                'origin': 'https://sipp.pn-*.go.id',
                'permissions': ['geolocation', 'notifications', 'clipboardReadWrite']
            })
            
            st.success("✅ Selenium session created (most powerful for bypass)")
            
        except Exception as e:
            st.error(f"Failed to create Selenium session: {e}")
            raise
    
    def get(self, url, timeout=Config.SELENIUM_TIMEOUT):
        """GET request using Selenium."""
        try:
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Check for Cloudflare challenge
            if self.check_cloudflare():
                st.warning("Cloudflare detected, waiting for challenge...")
                time.sleep(5)
                if self.check_cloudflare():
                    st.error("Cloudflare challenge not resolved")
                    return None
            
            return self.driver.page_source
            
        except TimeoutException:
            st.error(f"Timeout loading {url}")
            return None
        except Exception as e:
            st.error(f"Error in Selenium GET: {e}")
            return None
    
    def post(self, url, data=None, timeout=Config.SELENIUM_TIMEOUT):
        """POST request using Selenium."""
        try:
            # Convert data to JavaScript execution
            if data:
                # We'll need to navigate to form and submit
                self.driver.get(url)
                
                # Wait for form
                time.sleep(2)
                
                # Fill form (simplified - need adjustment based on actual form)
                for key, value in data.items():
                    try:
                        element = self.driver.find_element(By.NAME, key)
                        element.clear()
                        element.send_keys(value)
                    except:
                        pass
                
                # Submit form
                submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit']")
                submit_button.click()
                
                # Wait for response
                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                
                return self.driver.page_source
            else:
                return self.get(url)
                
        except Exception as e:
            st.error(f"Error in Selenium POST: {e}")
            return None
    
    def check_cloudflare(self):
        """Check if Cloudflare challenge is present."""
        try:
            page_source = self.driver.page_source.lower()
            cloudflare_indicators = [
                'cloudflare',
                'ray id',
                'checking your browser',
                'just a moment',
                'ddos protection',
                'jschl_vc',
                'challenge-form'
            ]
            
            for indicator in cloudflare_indicators:
                if indicator in page_source:
                    return True
            return False
        except:
            return False
    
    def close(self):
        """Close the driver."""
        if self.driver:
            self.driver.quit()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# =============================
# REQUEST MANAGER WITH FALLBACK
# =============================
class RequestManager:
    def __init__(self, use_selenium=False):
        self.use_selenium = use_selenium
        self.sessions = {}
        self.current_strategy = "requests"
        
    def get_session(self, domain):
        """Get or create session for domain."""
        if domain not in self.sessions:
            if self.use_selenium:
                try:
                    self.sessions[domain] = SeleniumSession()
                    self.current_strategy = "selenium"
                except:
                    self.sessions[domain] = SessionFactory.create_session("cloudscraper")
                    self.current_strategy = "cloudscraper"
            else:
                self.sessions[domain] = SessionFactory.create_session("auto")
                self.current_strategy = "auto"
        
        return self.sessions[domain]
    
    def request(self, method, url, **kwargs):
        """Make request with strategy fallback."""
        domain = urlparse(url).netloc
        session = self.get_session(domain)
        
        # Try with current strategy
        try:
            if isinstance(session, SeleniumSession):
                if method.upper() == 'GET':
                    html = session.get(url, timeout=Config.SELENIUM_TIMEOUT)
                    if html:
                        return MockResponse(html, url)
                elif method.upper() == 'POST':
                    html = session.post(url, data=kwargs.get('data'), timeout=Config.SELENIUM_TIMEOUT)
                    if html:
                        return MockResponse(html, url)
            else:
                # For requests/cloudscraper session
                response = session.request(method, url, **kwargs)
                
                # Check for 403
                if response.status_code == 403:
                    st.warning(f"403 Forbidden with {self.current_strategy}, trying different strategy...")
                    
                    # Close current session and try different strategy
                    if isinstance(session, SeleniumSession):
                        session.close()
                    
                    # Try next strategy
                    if self.current_strategy == "requests":
                        self.sessions[domain] = SessionFactory.create_session("cloudscraper")
                        self.current_strategy = "cloudscraper"
                    elif self.current_strategy == "cloudscraper":
                        try:
                            self.sessions[domain] = SeleniumSession()
                            self.current_strategy = "selenium"
                        except:
                            # Fallback to requests dengan headers berbeda
                            self.sessions[domain] = requests.Session()
                            self.sessions[domain].headers.update(HeadersManager.get_headers(domain))
                            self.current_strategy = "requests_alt"
                    
                    # Retry with new session
                    session = self.sessions[domain]
                    response = session.request(method, url, **kwargs)
                
                return response
                
        except Exception as e:
            st.error(f"Request failed: {e}")
            raise
        
        return None
    
    def close_all(self):
        """Close all sessions."""
        for domain, session in self.sessions.items():
            if isinstance(session, SeleniumSession):
                session.close()
        self.sessions.clear()

# Mock response untuk Selenium
class MockResponse:
    def __init__(self, text, url):
        self.text = text
        self.url = url
        self.status_code = 200
        self.headers = {}

# =============================
# UTILITY FUNCTIONS
# =============================
def normalize_domain(domain):
    """Normalize domain."""
    domain = str(domain).strip()
    
    # Remove protocol if already there
    if domain.startswith("http://"):
        domain = "https://" + domain[7:]
    elif not domain.startswith("https://"):
        domain = "https://" + domain
    
    # Remove trailing slash
    domain = domain.rstrip("/")
    
    # Ensure proper go.id format
    if 'pn-' not in domain and 'go.id' in domain:
        # Try to insert pn- if missing
        parts = domain.split('.go.id')[0].split('//')
        if len(parts) > 1:
            domain = f"{parts[0]}//sipp.pn-{parts[1]}.go.id"
    
    return domain

def extract_nama_pn(domain):
    """Extract PN name from domain."""
    try:
        # Pattern matching untuk berbagai format
        patterns = [
            r"pn-([a-z\-]+)\.go\.id",
            r"sipp\.pn-([a-z\-]+)\.go\.id",
            r"pn([a-z]+)\.go\.id",
            r"//([a-z\-]+)\.pn\.go\.id",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, domain.lower())
            if match:
                name = match.group(1).replace('-', ' ').title()
                return name.upper()
        
        return "UNKNOWN"
    except:
        return "UNKNOWN"

def clean_text(html_text):
    """Clean HTML text."""
    if not html_text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', str(html_text))
    # Replace multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep Indonesian letters
    text = re.sub(r'[^\w\s.,\-:()/]', '', text)
    
    return text.strip()

# =============================
# TOKEN EXTRACTION ADVANCED
# =============================
def get_enc_token_advanced(request_manager, base_domain):
    """Advanced token extraction with multiple attempts."""
    
    # Try multiple endpoints
    endpoints = [
        "/list_perkara",
        "/",
        "/index.php",
        "/home",
        "/beranda",
        ""
    ]
    
    for endpoint in endpoints:
        url = f"{base_domain}{endpoint}"
        
        try:
            # Try GET request
            response = request_manager.request('GET', url, timeout=Config.TIMEOUT)
            
            if not response:
                continue
            
            # Check if we got valid HTML
            if not response.text or len(response.text) < 100:
                continue
            
            # Look for enc token in multiple ways
            enc_token = None
            
            # Method 1: BeautifulSoup parsing
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check various input elements
            enc_inputs = [
                soup.find('input', {'name': 'enc'}),
                soup.find('input', {'id': 'enc'}),
                soup.find('input', {'type': 'hidden', 'name': 'enc'}),
            ]
            
            for enc_input in enc_inputs:
                if enc_input and enc_input.get('value'):
                    enc_token = enc_input['value']
                    break
            
            # Method 2: Regex search in HTML
            if not enc_token:
                enc_matches = re.findall(r'name=["\']enc["\']\s+value=["\']([^"\']+)["\']', response.text)
                if enc_matches:
                    enc_token = enc_matches[0]
            
            # Method 3: Look in JavaScript variables
            if not enc_token:
                js_matches = re.findall(r'enc\s*[:=]\s*["\']([^"\']+)["\']', response.text)
                if js_matches:
                    enc_token = js_matches[0]
            
            # Method 4: Look in form data
            if not enc_token:
                forms = soup.find_all('form')
                for form in forms:
                    inputs = form.find_all('input')
                    for inp in inputs:
                        if inp.get('name') == 'enc':
                            enc_token = inp.get('value')
                            break
                    if enc_token:
                        break
            
            if enc_token:
                st.success(f"✅ Token found for {extract_nama_pn(base_domain)}")
                return enc_token
            
        except Exception as e:
            st.warning(f"⚠️ Failed to get token from {url}: {str(e)[:50]}")
            continue
    
    # Last resort: Try to extract from page with JavaScript execution simulation
    st.warning(f"🔍 Trying JavaScript simulation for {base_domain}")
    
    try:
        # This would require actual browser execution
        # For now, return None
        return None
    except:
        return None

# =============================
# MAIN SCRAPING FUNCTION
# =============================
def scrape_single_entry(request_manager, domain, enc_token, nama, nama_pn):
    """Scrape single name from single domain."""
    
    search_url = f"{domain}/list_perkara/search"
    
    # Prepare payload
    payload = {
        'search_keyword': nama,
        'enc': enc_token,
    }
    
    # Add additional fields that might be required
    additional_fields = {
        'submit': 'Cari',
        'search': 'true',
        'action': 'search',
    }
    
    payload.update(additional_fields)
    
    try:
        # Make POST request
        response = request_manager.request(
            'POST', 
            search_url, 
            data=payload,
            timeout=Config.TIMEOUT,
            headers=HeadersManager.get_headers(domain, referer=f"{domain}/list_perkara")
        )
        
        if not response or not response.text:
            return create_error_result(nama, nama_pn, domain, "Empty response")
        
        # Parse results
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for "no results" messages
        no_result_texts = [
            'data tidak ditemukan',
            'tidak ada data',
            'no data found',
            'hasil tidak ditemukan',
            'belum ada data',
            'data tidak tersedia',
        ]
        
        page_text = soup.get_text().lower()
        if any(text in page_text for text in no_result_texts):
            return create_not_found_result(nama, nama_pn, domain)
        
        # Find results table
        tables = soup.find_all('table')
        if not tables:
            return create_not_found_result(nama, nama_pn, domain)
        
        # Find the right table (look for one with many rows)
        target_table = None
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 1:  # More than just header
                target_table = table
                break
        
        if not target_table:
            return create_not_found_result(nama, nama_pn, domain)
        
        # Process table rows
        results = []
        rows = target_table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cols = row.find_all('td')
            
            if not cols:
                continue
            
            # Determine format and parse
            result = parse_table_row(cols, nama, nama_pn, domain)
            if result:
                results.append(result)
        
        if results:
            return results
        else:
            return create_not_found_result(nama, nama_pn, domain)
        
    except Exception as e:
        return create_error_result(nama, nama_pn, domain, str(e))

# =============================
# TABLE PARSING
# =============================
def parse_table_row(cols, nama, nama_pn, domain):
    """Parse a table row into structured data."""
    
    try:
        # Initialize result dict
        result = {
            'Nama Pencarian': nama,
            'Nama PN': nama_pn,
            'Domain': domain,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Try to detect column format
        if len(cols) >= 8:
            # Format: No | Nomor Perkara | Tanggal Register | Klasifikasi | Para Pihak | Status | Lama Proses | Link
            result.update({
                'Nomor Perkara': cols[1].get_text(strip=True) if len(cols) > 1 else '-',
                'Tanggal Register': cols[2].get_text(strip=True) if len(cols) > 2 else '-',
                'Klasifikasi': cols[3].get_text(strip=True) if len(cols) > 3 else '-',
                'Para Pihak': clean_text(str(cols[4])) if len(cols) > 4 else '-',
                'Status': cols[5].get_text(strip=True) if len(cols) > 5 else '-',
                'Lama Proses': cols[6].get_text(strip=True) if len(cols) > 6 else '-',
                'Link': cols[7].find('a')['href'] if len(cols) > 7 and cols[7].find('a') else '-',
            })
        elif len(cols) >= 6:
            # Older format
            result.update({
                'Nomor Perkara': cols[0].get_text(strip=True) if len(cols) > 0 else '-',
                'Jenis Perkara': cols[1].get_text(strip=True) if len(cols) > 1 else '-',
                'Para Pihak': clean_text(str(cols[2])) if len(cols) > 2 else '-',
                'Tanggal Register': cols[3].get_text(strip=True) if len(cols) > 3 else '-',
                'Status': cols[4].get_text(strip=True) if len(cols) > 4 else '-',
                'Tanggal Status': cols[5].get_text(strip=True) if len(cols) > 5 else '-',
                'Link': '-',
            })
        else:
            # Minimal format
            result.update({
                'Nomor Perkara': cols[0].get_text(strip=True) if len(cols) > 0 else '-',
                'Info': clean_text(' '.join([col.get_text(strip=True) for col in cols[1:]])) if len(cols) > 1 else '-',
                'Link': '-',
            })
        
        return result
        
    except Exception as e:
        st.warning(f"Error parsing row: {e}")
        return None

def create_not_found_result(nama, nama_pn, domain):
    return [{
        'Nama Pencarian': nama,
        'Nama PN': nama_pn,
        'Domain': domain,
        'Nomor Perkara': 'TIDAK DITEMUKAN',
        'Tanggal Register': '-',
        'Klasifikasi': '-',
        'Para Pihak': '-',
        'Status': '-',
        'Lama Proses': '-',
        'Link': '-',
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Keterangan': 'Data tidak ditemukan'
    }]

def create_error_result(nama, nama_pn, domain, error_msg):
    return [{
        'Nama Pencarian': nama,
        'Nama PN': nama_pn,
        'Domain': domain,
        'Nomor Perkara': 'ERROR',
        'Tanggal Register': '-',
        'Klasifikasi': '-',
        'Para Pihak': '-',
        'Status': '-',
        'Lama Proses': '-',
        'Link': '-',
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Keterangan': f'Error: {str(error_msg)[:100]}'
    }]

# =============================
# STREAMLIT APP
# =============================
def main():
    st.set_page_config(
        page_title="SIPP Scraper Ultra",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stProgress > div > div > div > div {
        background-color: #2196F3;
    }
    .success-box {
        background-color: #d4edda;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #ffeaa7;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("⚖️ SIPP Scraper Ultra - Bypass 403 Edition")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Advanced Settings")
        
        # Bypass method
        bypass_method = st.selectbox(
            "Bypass Method",
            ["Automatic (Recommended)", "Selenium (Most Powerful)", "Cloudscraper", "Requests Only"]
        )
        
        # Request settings
        delay = st.slider("Request Delay (seconds)", 2.0, 10.0, 3.0, 0.5)
        retries = st.slider("Max Retries", 1, 10, 3)
        
        # Advanced options
        st.subheader("🔧 Advanced Options")
        use_random_ua = st.checkbox("Randomize User Agents", value=True)
        use_referer_spoof = st.checkbox("Spoof Referer", value=True)
        simulate_human = st.checkbox("Simulate Human Behavior", value=True)
        
        # Debug options
        st.subheader("🐛 Debug")
        debug_mode = st.checkbox("Enable Debug Mode", value=False)
        test_single = st.checkbox("Test Single Domain First", value=True)
        
        st.markdown("---")
        st.caption("v3.0 - Advanced Bypass Technology")
    
    # Main content
    st.header("📁 Data Input")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Domain input
        st.subheader("🌐 Domains")
        
        # Load domains from file
        try:
            if os.path.exists("domain.xlsx"):
                df_domains = pd.read_excel("domain.xlsx")
                df_domains.columns = [str(col).strip().lower() for col in df_domains.columns]
                
                # Find domain column
                domain_col = None
                for col in df_domains.columns:
                    if 'domain' in col or 'url' in col or 'link' in col:
                        domain_col = col
                        break
                
                if domain_col:
                    domains = [normalize_domain(d) for d in df_domains[domain_col].dropna().unique()]
                    st.success(f"✅ Loaded {len(domains)} domains")
                    
                    # Test domains if requested
                    if test_single and domains:
                        st.info(f"First domain to test: {domains[0]}")
                else:
                    st.error("❌ No domain column found")
                    domains = []
            else:
                st.error("❌ domain.xlsx not found")
                domains = []
                
        except Exception as e:
            st.error(f"❌ Error loading domains: {e}")
            domains = []
    
    with col2:
        # Names input
        st.subheader("👤 Names")
        uploaded_file = st.file_uploader(
            "Upload Excel with names",
            type=["xlsx", "xls", "csv"],
            help="File should contain a column with names"
        )
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_names = pd.read_csv(uploaded_file)
                else:
                    df_names = pd.read_excel(uploaded_file)
                
                df_names.columns = [str(col).strip().lower() for col in df_names.columns]
                
                # Find name column
                name_col = None
                for col in df_names.columns:
                    if 'nama' in col or 'name' in col:
                        name_col = col
                        break
                
                if name_col:
                    names = df_names[name_col].dropna().astype(str).unique()
                    st.success(f"✅ Loaded {len(names)} names")
                    
                    with st.expander("Preview Names"):
                        st.dataframe(df_names.head(), use_container_width=True)
                else:
                    st.error("❌ No name column found")
                    names = []
                    
            except Exception as e:
                st.error(f"❌ Error loading names: {e}")
                names = []
        else:
            names = []
    
    # Start scraping button
    if len(domains) > 0 and len(names) > 0:
        total_tasks = len(domains) * len(names)
        est_time = (total_tasks * delay) / 60
        
        st.info(f"""
        **Ready to scrape:**
        - Domains: {len(domains)}
        - Names: {len(names)}
        - Total requests: {total_tasks}
        - Estimated time: {est_time:.1f} minutes
        - Method: {bypass_method}
        """)
        
        if st.button("🚀 START SCRAPING", type="primary", use_container_width=True):
            # Initialize
            request_manager = RequestManager(use_selenium=(bypass_method == "Selenium (Most Powerful)"))
            all_results = []
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_placeholder = st.empty()
            
            # Statistics
            stats = {
                'total': 0,
                'success': 0,
                'not_found': 0,
                'error': 0
            }
            
            # Process each domain
            for domain_idx, domain in enumerate(domains):
                nama_pn = extract_nama_pn(domain)
                
                # Get enc token for this domain
                with st.spinner(f"🔑 Getting token for {nama_pn}..."):
                    enc_token = get_enc_token_advanced(request_manager, domain)
                
                if not enc_token:
                    st.warning(f"⚠️ Could not get token for {nama_pn}. Skipping domain.")
                    # Add error results for all names
                    for nama in names:
                        all_results.extend(create_error_result(
                            nama, nama_pn, domain, "Could not get enc token"
                        ))
                        stats['total'] += 1
                        stats['error'] += 1
                        progress_bar.progress(stats['total'] / total_tasks)
                    continue
                
                # Process each name
                for name_idx, nama in enumerate(names):
                    stats['total'] += 1
                    current_task = stats['total']
                    
                    # Update status
                    status_text.text(
                        f"🔍 [{current_task}/{total_tasks}] Searching: {nama[:30]}... in {nama_pn}"
                    )
                    
                    # Scrape
                    try:
                        results = scrape_single_entry(
                            request_manager, domain, enc_token, nama, nama_pn
                        )
                        
                        if results:
                            # Check if results contain actual data or errors
                            if results[0]['Nomor Perkara'] == 'ERROR':
                                stats['error'] += 1
                            elif results[0]['Nomor Perkara'] == 'TIDAK DITEMUKAN':
                                stats['not_found'] += 1
                            else:
                                stats['success'] += len(results)
                            
                            all_results.extend(results)
                        else:
                            stats['error'] += 1
                            all_results.extend(create_error_result(
                                nama, nama_pn, domain, "No results returned"
                            ))
                        
                    except Exception as e:
                        stats['error'] += 1
                        all_results.extend(create_error_result(
                            nama, nama_pn, domain, str(e)
                        ))
                    
                    # Update progress
                    progress_bar.progress(current_task / total_tasks)
                    
                    # Delay
                    time.sleep(delay)
            
            # Complete
            progress_bar.progress(1.0)
            status_text.text("✅ Scraping complete!")
            
            # Display results
            if all_results:
                result_df = pd.DataFrame(all_results)
                
                # Display statistics
                st.subheader("📊 Results Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Searches", stats['total'])
                col2.metric("Data Found", stats['success'])
                col3.metric("Not Found", stats['not_found'])
                col4.metric("Errors", stats['error'])
                
                # Display data
                st.subheader("📋 Detailed Results")
                st.dataframe(result_df, use_container_width=True, height=500)
                
                # Export
                st.subheader("💾 Export Results")
                
                # Excel export
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                excel_filename = f"sipp_results_{timestamp}.xlsx"
                result_df.to_excel(excel_filename, index=False)
                
                with open(excel_filename, "rb") as f:
                    st.download_button(
                        "📥 Download Excel",
                        f,
                        file_name=excel_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                # CSV export
                csv_filename = f"sipp_results_{timestamp}.csv"
                result_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                
                with open(csv_filename, "rb") as f:
                    st.download_button(
                        "📥 Download CSV",
                        f,
                        file_name=csv_filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                
                st.success(f"🎉 Successfully scraped {stats['success']} data points!")
                
            else:
                st.warning("⚠️ No results were collected.")
            
            # Cleanup
            request_manager.close_all()
    
    else:
        st.info("👆 Please load both domains and names to begin scraping.")
        
        # Instructions
        with st.expander("📖 Instructions"):
            st.markdown("""
            ### Setup Instructions:
            
            1. **Prepare `domain.xlsx`** in the same folder:
               ```csv
               domain
               https://sipp.pn-jakartaselatan.go.id
               https://sipp.pn-bandung.go.id
               ```
            
            2. **Prepare names file** (Excel/CSV):
               ```csv
               nama
               PT CIMB NIAGA AUTO FINANCE
               NANA MULYANA
               ```
            
            3. **Select bypass method** in sidebar:
               - **Automatic**: Tries all methods
               - **Selenium**: Most powerful (requires Chrome)
               - **Cloudscraper**: Good for Cloudflare
               - **Requests**: Simple but may fail
            
            4. **Adjust settings**:
               - Increase delay if getting blocked
               - Use Selenium for toughest sites
               - Enable debug mode for troubleshooting
            """)
    
    # Footer
    st.markdown("---")
    st.caption("Note: This tool is for legitimate research purposes only. Respect website terms of service.")

# =============================
# INSTALLATION CHECK
# =============================
def check_installation():
    """Check if all required packages are installed."""
    missing_packages = []
    
    try:
        import cloudscraper
    except:
        missing_packages.append("cloudscraper")
    
    try:
        import undetected_chromedriver
    except:
        missing_packages.append("undetected-chromedriver")
    
    if missing_packages:
        st.sidebar.warning(f"Missing packages: {', '.join(missing_packages)}")
        st.sidebar.code(f"pip install {' '.join(missing_packages)}")

# =============================
# RUN APPLICATION
# =============================
if __name__ == "__main__":
    # Check installation
    check_installation()
    
    # Run main app
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {e}")
        st.exception(e)
