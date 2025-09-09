import os
import time
import requests
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

class InstagramReelDownloader:
    def __init__(self, username="AbanoubHakim1995", password=None, target_profile=None, video_limit=None, max_workers=5):
        self.username = username
        self.password = password
        self.target_profile = target_profile
        self.video_limit = video_limit
        self.max_workers = max_workers
        
        # Use provided UTC time for folder naming
        current_time = "2025-08-03_215329"  # Current UTC time formatted
        self.output_dir = f"{target_profile}_reels_{current_time}"
        
        self.session = requests.Session()
        self.cookies = {}
        self.total_downloaded = 0
        self.failed_downloads = []
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"\n📁 Videos will be saved to: {os.path.abspath(self.output_dir)}")

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        
        # Performance optimizations
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-webgl')
        options.add_argument('--disable-software-rasterizer')
        
        # Disable unnecessary features
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--silent')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Memory optimizations
        options.add_argument('--disable-dev-tools')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--no-first-run')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-translate')
        
        # Mobile emulation for better compatibility
        mobile_emulation = {
            "deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0_1 like Mac OS X) AppleWebKit/605.1.15"
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        # Disable logging and automation flags
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        return driver

    def handle_popups(self, driver):
        """Handle all Instagram popups including 'Save Login Info'"""
        popup_buttons = {
            "save_info": ["Not Now", "Not now"],  # Save login info popup
            "notifications": ["Not Now", "Not now"],  # Turn on notifications popup
            "add_to_home": ["Not Now", "Cancel"],  # Add to home screen
            "generic": ["Skip", "Maybe Later", "No Thanks"]  # Other popups
        }

        for popup_type, button_texts in popup_buttons.items():
            for text in button_texts:
                try:
                    button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, 
                            f"//button[contains(text(), '{text}')] | "
                            f"//div[contains(text(), '{text}') and @role='button']"))
                    )
                    button.click()
                    print(f"✓ Handled {popup_type} popup")
                    time.sleep(1)
                    break
                except:
                    continue

    def instagram_login(self, driver):
        print(f"\n🔐 Logging in as {self.username}...")
        driver.get("https://www.instagram.com/accounts/login/")
        wait = WebDriverWait(driver, 30)
        
        try:
            # Enter login credentials
            user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            pass_input = driver.find_element(By.NAME, "password")
            user_input.send_keys(self.username)
            pass_input.send_keys(self.password)
            pass_input.send_keys(Keys.RETURN)
            
            # Wait for login to complete
            time.sleep(5)
            
            # Handle "Save Login Info" popup first
            try:
                save_info_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//button[contains(text(), 'Not Now')] | "
                        "//div[contains(text(), 'Not Now') and @role='button']"))
                )
                save_info_button.click()
                print("✓ Skipped saving login info")
                time.sleep(1)
            except:
                print("No 'Save Login Info' prompt found")
            
            # Handle other popups
            self.handle_popups(driver)
            
            # Verify login success
            if "login" in driver.current_url:
                print("❌ Login failed - still on login page")
                return False
                
            print("✅ Login successful!")
            return True
            
        except Exception as e:
            print(f"❌ Login failed: {str(e)}")
            return False

    def collect_reel_links(self, driver):
        print(f"\n🔍 Collecting reels from profile: {self.target_profile}")
        profile_url = f"https://www.instagram.com/{self.target_profile}/reels/"
        driver.get(profile_url)
        time.sleep(5)

        links = []
        last_height = driver.execute_script("return document.body.scrollHeight")
        attempts_without_new = 0
        
        while len(links) < (self.video_limit or float('inf')):
            current_len = len(links)
            
            elements = driver.find_elements(By.TAG_NAME, "a")
            for elem in elements:
                href = elem.get_attribute("href")
                if href and "/reel/" in href and href not in links:
                    links.append(href)
                    print(f"\r📱 Found {len(links)} reels...", end="", flush=True)
                    if self.video_limit and len(links) >= self.video_limit:
                        print()
                        return links[:self.video_limit]

            if len(links) == current_len:
                attempts_without_new += 1
                if attempts_without_new >= 3:
                    break
            else:
                attempts_without_new = 0

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        print()
        return links[:self.video_limit] if self.video_limit else links

    def extract_video_url(self, driver, reel_url, max_retries=3):
        for attempt in range(max_retries):
            try:
                driver.get(reel_url)
                time.sleep(2)

                # Try multiple methods
                for _ in range(2):
                    try:
                        video = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.TAG_NAME, "video"))
                        )
                        video_url = video.get_attribute("src")
                        if video_url and video_url.startswith("http"):
                            return video_url
                    except:
                        pass

                    page_source = driver.page_source
                    patterns = [
                        r'https://[^"]+\.mp4[^"]*',
                        r'https://[^"]+\.m3u8[^"]*',
                        r'"video_url":"([^"]+)"'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, page_source)
                        if matches:
                            url = matches[0]
                            if isinstance(url, tuple):
                                url = url[0]
                            return url.replace('\\u0026', '&')

                    time.sleep(1)

            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Failed to extract video URL: {str(e)}")
                else:
                    print(f"⚠️ Retry {attempt + 1}/{max_retries}")
                    time.sleep(2)
        return None

    def download_video(self, video_url, filename, max_retries=3):
        filepath = os.path.join(self.output_dir, filename)
        
        for attempt in range(max_retries):
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0_1 like Mac OS X) AppleWebKit/605.1.15",
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br",
                }
                
                with self.session.get(video_url, headers=headers, stream=True, timeout=30) as response:
                    if response.status_code == 200:
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        print(f"✅ Downloaded: {filename}")
                        return True
                    else:
                        print(f"⚠️ Download failed (HTTP {response.status_code}), attempt {attempt + 1}/{max_retries}")
                        
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Failed to download {filename}: {str(e)}")
                else:
                    print(f"⚠️ Retry {attempt + 1}/{max_retries}")
                    time.sleep(2)
        return False

    def process_batch(self, driver, reel_urls, start_idx):
        results = []
        for idx, url in enumerate(reel_urls, start_idx):
            print(f"\n📥 Processing reel {idx}")
            video_url = self.extract_video_url(driver, url)
            if video_url:
                results.append((idx, video_url))
        return results

    def download_batch(self, video_info_batch):
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.download_video, 
                    video_url, 
                    f"reel_{idx}.mp4"
                ): (idx, video_url) 
                for idx, video_url in video_info_batch
            }
            
            for future in as_completed(futures):
                try:
                    success = future.result()
                    if success:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"❌ Download failed: {str(e)}")
                    failed += 1
                    
        return successful, failed

    def run(self):
        start_time = time.time()
        driver = self.setup_driver()
        
        try:
            if not self.instagram_login(driver):
                return
                
            reel_links = self.collect_reel_links(driver)
            if not reel_links:
                print("❌ No reels found!")
                return

            total_successful = 0
            total_failed = 0
            batch_size = 5

            # Process in batches
            for i in range(0, len(reel_links), batch_size):
                batch = reel_links[i:i + batch_size]
                print(f"\n📦 Processing batch {i//batch_size + 1}/{(len(reel_links) + batch_size - 1)//batch_size}")
                
                video_info_batch = self.process_batch(driver, batch, i + 1)
                if video_info_batch:
                    successful, failed = self.download_batch(video_info_batch)
                    total_successful += successful
                    total_failed += failed
                
                print(f"\n📊 Progress: {i + len(batch)}/{len(reel_links)} "
                      f"(✅ Success: {total_successful}, ❌ Failed: {total_failed})")

            # Final summary
            elapsed_time = time.time() - start_time
            print(f"\n=== 📑 Download Summary ===")
            print(f"🎯 Total reels found: {len(reel_links)}")
            print(f"✅ Successfully downloaded: {total_successful}")
            print(f"❌ Failed downloads: {total_failed}")
            print(f"⏱️ Time taken: {elapsed_time:.2f} seconds")
            if total_successful > 0:
                print(f"⚡ Average time per video: {elapsed_time/total_successful:.2f} seconds")
            print(f"📁 Files saved in: {os.path.abspath(self.output_dir)}")

        except Exception as e:
            print(f"❌ An error occurred: {str(e)}")
        finally:
            driver.quit()

def main():
    # Configuration
    INSTAGRAM_USERNAME = "abanobhakim"
    INSTAGRAM_PASSWORD = "Mylime@2025"
    TARGET_PROFILE = "netflixnmovies"
    VIDEO_LIMIT = 10    # Set to None for no limit
    MAX_WORKERS = 5      # Number of concurrent downloads
    
    # Print session info
    print(f"\n=== Session Information ===")
    print(f"Start Time (UTC): 2025-08-03 21:53:29")
    print(f"Username: {INSTAGRAM_USERNAME}")
    print(f"Target Profile: {TARGET_PROFILE}")
    print(f"Video Limit: {'Unlimited' if VIDEO_LIMIT is None else VIDEO_LIMIT}")
    print(f"Parallel Downloads: {MAX_WORKERS}")
    print("="*25 + "\n")
    
    downloader = InstagramReelDownloader(
        username=INSTAGRAM_USERNAME,
        password=INSTAGRAM_PASSWORD,
        target_profile=TARGET_PROFILE,
        video_limit=VIDEO_LIMIT,
        max_workers=MAX_WORKERS
    )
    
    downloader.run()

if __name__ == "__main__":
    main()