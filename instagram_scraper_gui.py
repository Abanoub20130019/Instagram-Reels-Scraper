import os
import time
import json
import threading
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
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from tkinter.font import Font
import queue
import sys

class InstagramReelDownloader:
    def __init__(self, username=None, password=None, target_profile=None, 
                 video_limit=None, max_workers=5, output_dir=None, progress_callback=None):
        self.username = username
        self.password = password
        self.target_profile = target_profile
        self.video_limit = video_limit
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.stop_requested = False
        self.paused = False
        
        # Create output directory with timestamp
        if output_dir:
            self.output_dir = output_dir
        else:
            current_time = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self.output_dir = f"{target_profile}_reels_{current_time}" if target_profile else f"reels_{current_time}"
        
        self.session = requests.Session()
        self.total_downloaded = 0
        self.failed_downloads = []
        
        # Create output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def log_message(self, message):
        """Send log message to GUI if callback is available"""
        if self.progress_callback:
            self.progress_callback('log', message)
        else:
            print(message)

    def update_progress(self, current, total, status="Processing"):
        """Update progress in GUI"""
        if self.progress_callback:
            self.progress_callback('progress', {'current': current, 'total': total, 'status': status})

    def setup_driver(self):
        """Setup Chrome driver with optimized options"""
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
        
        try:
            driver = webdriver.Chrome(options=options)
            return driver
        except Exception as e:
            self.log_message(f"❌ Failed to setup Chrome driver: {str(e)}")
            raise

    def handle_popups(self, driver):
        """Handle Instagram popups"""
        popup_buttons = {
            "save_info": ["Not Now", "Not now"],
            "notifications": ["Not Now", "Not now"],
            "add_to_home": ["Not Now", "Cancel"],
            "generic": ["Skip", "Maybe Later", "No Thanks"]
        }

        for popup_type, button_texts in popup_buttons.items():
            if self.stop_requested:
                return
            for text in button_texts:
                try:
                    button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, 
                            f"//button[contains(text(), '{text}')] | "
                            f"//div[contains(text(), '{text}') and @role='button']"))
                    )
                    button.click()
                    self.log_message(f"✓ Handled {popup_type} popup")
                    time.sleep(1)
                    break
                except:
                    continue

    def instagram_login(self, driver):
        """Login to Instagram"""
        self.log_message(f"🔐 Logging in as {self.username}...")
        driver.get("https://www.instagram.com/accounts/login/")
        wait = WebDriverWait(driver, 30)
        
        try:
            if self.stop_requested:
                return False
                
            # Enter login credentials
            user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            pass_input = driver.find_element(By.NAME, "password")
            user_input.send_keys(self.username)
            pass_input.send_keys(self.password)
            pass_input.send_keys(Keys.RETURN)
            
            # Wait for login to complete
            time.sleep(5)
            
            # Handle popups
            self.handle_popups(driver)
            
            # Verify login success
            if "login" in driver.current_url:
                self.log_message("❌ Login failed - still on login page")
                return False
                
            self.log_message("✅ Login successful!")
            return True
            
        except Exception as e:
            self.log_message(f"❌ Login failed: {str(e)}")
            return False

    def collect_reel_links(self, driver):
        """Collect reel links from target profile"""
        self.log_message(f"🔍 Collecting reels from profile: {self.target_profile}")
        profile_url = f"https://www.instagram.com/{self.target_profile}/reels/"
        driver.get(profile_url)
        time.sleep(5)

        links = []
        last_height = driver.execute_script("return document.body.scrollHeight")
        attempts_without_new = 0
        
        while len(links) < (self.video_limit or float('inf')) and not self.stop_requested:
            # Handle pause
            while self.paused and not self.stop_requested:
                time.sleep(0.5)
            
            if self.stop_requested:
                break
                
            current_len = len(links)
            
            elements = driver.find_elements(By.TAG_NAME, "a")
            for elem in elements:
                href = elem.get_attribute("href")
                if href and "/reel/" in href and href not in links:
                    links.append(href)
                    self.log_message(f"📱 Found {len(links)} reels...")
                    self.update_progress(len(links), self.video_limit or 100, "Collecting reels")
                    if self.video_limit and len(links) >= self.video_limit:
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

        return links[:self.video_limit] if self.video_limit else links

    def extract_video_url(self, driver, reel_url, max_retries=3):
        """Extract video URL from reel page"""
        for attempt in range(max_retries):
            if self.stop_requested:
                return None
                
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
                    self.log_message(f"❌ Failed to extract video URL: {str(e)}")
                else:
                    time.sleep(2)
        return None

    def download_video(self, video_url, filename, max_retries=3):
        """Download video from URL"""
        if self.stop_requested:
            return False
            
        filepath = os.path.join(self.output_dir, filename)
        
        for attempt in range(max_retries):
            if self.stop_requested:
                return False
                
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
                                if chunk and not self.stop_requested:
                                    f.write(chunk)
                        
                        if not self.stop_requested:
                            self.log_message(f"✅ Downloaded: {filename}")
                            return True
                        else:
                            # Clean up partial download
                            if os.path.exists(filepath):
                                os.remove(filepath)
                            return False
                    else:
                        self.log_message(f"⚠️ Download failed (HTTP {response.status_code}), attempt {attempt + 1}/{max_retries}")
                        
            except Exception as e:
                if attempt == max_retries - 1:
                    self.log_message(f"❌ Failed to download {filename}: {str(e)}")
                else:
                    time.sleep(2)
        return False

    def stop_download(self):
        """Stop the download process"""
        self.stop_requested = True
        self.log_message("🛑 Stop requested...")

    def pause_download(self):
        """Pause the download process"""
        self.paused = True
        self.log_message("⏸️ Download paused")

    def resume_download(self):
        """Resume the download process"""
        self.paused = False
        self.log_message("▶️ Download resumed")

    def run(self):
        """Main execution method"""
        start_time = time.time()
        driver = None
        
        try:
            driver = self.setup_driver()
            
            if not self.instagram_login(driver):
                return False
                
            reel_links = self.collect_reel_links(driver)
            if not reel_links:
                self.log_message("❌ No reels found!")
                return False

            self.log_message(f"📱 Found {len(reel_links)} reels to download")
            
            total_successful = 0
            total_failed = 0

            # Process each reel
            for idx, reel_url in enumerate(reel_links, 1):
                if self.stop_requested:
                    break
                    
                # Handle pause
                while self.paused and not self.stop_requested:
                    time.sleep(0.5)
                
                if self.stop_requested:
                    break
                
                self.log_message(f"📥 Processing reel {idx}/{len(reel_links)}")
                self.update_progress(idx, len(reel_links), f"Processing reel {idx}")
                
                video_url = self.extract_video_url(driver, reel_url)
                if video_url:
                    filename = f"reel_{idx:03d}.mp4"
                    if self.download_video(video_url, filename):
                        total_successful += 1
                    else:
                        total_failed += 1
                        self.failed_downloads.append(reel_url)
                else:
                    total_failed += 1
                    self.failed_downloads.append(reel_url)

            # Final summary
            elapsed_time = time.time() - start_time
            self.log_message(f"\n=== 📑 Download Summary ===")
            self.log_message(f"🎯 Total reels found: {len(reel_links)}")
            self.log_message(f"✅ Successfully downloaded: {total_successful}")
            self.log_message(f"❌ Failed downloads: {total_failed}")
            self.log_message(f"⏱️ Time taken: {elapsed_time:.2f} seconds")
            if total_successful > 0:
                self.log_message(f"⚡ Average time per video: {elapsed_time/total_successful:.2f} seconds")
            self.log_message(f"📁 Files saved in: {os.path.abspath(self.output_dir)}")
            
            return True

        except Exception as e:
            self.log_message(f"❌ An error occurred: {str(e)}")
            return False
        finally:
            if driver:
                driver.quit()


class InstagramScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Reel Downloader")
        self.root.geometry("800x700")
        self.root.minsize(600, 500)
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Variables
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.target_profile_var = tk.StringVar()
        self.video_limit_var = tk.StringVar(value="10")
        self.max_workers_var = tk.StringVar(value="5")
        self.output_dir_var = tk.StringVar()
        
        # Download control
        self.downloader = None
        self.download_thread = None
        self.is_downloading = False
        self.is_paused = False
        
        # Message queue for thread communication
        self.message_queue = queue.Queue()
        
        self.setup_ui()
        self.load_settings()
        self.check_messages()

    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Instagram Reel Downloader", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # Username
        ttk.Label(config_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(config_frame, textvariable=self.username_var, width=30).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Password
        ttk.Label(config_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(config_frame, textvariable=self.password_var, show="*", width=30).grid(
            row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Target Profile
        ttk.Label(config_frame, text="Target Profile:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(config_frame, textvariable=self.target_profile_var, width=30).grid(
            row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Video Limit
        ttk.Label(config_frame, text="Video Limit:").grid(row=3, column=0, sticky=tk.W, pady=2)
        limit_frame = ttk.Frame(config_frame)
        limit_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        ttk.Entry(limit_frame, textvariable=self.video_limit_var, width=10).pack(side=tk.LEFT)
        ttk.Label(limit_frame, text="(leave empty for no limit)").pack(side=tk.LEFT, padx=(10, 0))
        
        # Max Workers
        ttk.Label(config_frame, text="Parallel Downloads:").grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Entry(config_frame, textvariable=self.max_workers_var, width=10).grid(
            row=4, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Output Directory
        ttk.Label(config_frame, text="Output Directory:").grid(row=5, column=0, sticky=tk.W, pady=2)
        dir_frame = ttk.Frame(config_frame)
        dir_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        dir_frame.columnconfigure(0, weight=1)
        ttk.Entry(dir_frame, textvariable=self.output_dir_var).grid(
            row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).grid(
            row=0, column=1, padx=(5, 0))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Download", 
                                      command=self.start_download)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = ttk.Button(button_frame, text="Pause", 
                                      command=self.pause_download, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", 
                                     command=self.stop_download, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Save Settings", 
                  command=self.save_settings).pack(side=tk.LEFT, padx=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.StringVar(value="Ready to start")
        ttk.Label(progress_frame, textvariable=self.progress_var).grid(
            row=0, column=0, sticky=tk.W, pady=2)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear log button
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).grid(
            row=1, column=0, pady=(5, 0))

    def browse_directory(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def clear_log(self):
        """Clear the log text"""
        self.log_text.delete(1.0, tk.END)

    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def progress_callback(self, msg_type, data):
        """Callback for progress updates from downloader"""
        self.message_queue.put((msg_type, data))

    def check_messages(self):
        """Check for messages from downloader thread"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == 'log':
                    self.log_message(data)
                elif msg_type == 'progress':
                    current = data['current']
                    total = data['total']
                    status = data['status']
                    
                    if total > 0:
                        progress_percent = (current / total) * 100
                        self.progress_bar['value'] = progress_percent
                        self.progress_var.set(f"{status}: {current}/{total} ({progress_percent:.1f}%)")
                    else:
                        self.progress_var.set(status)
                elif msg_type == 'finished':
                    self.download_finished()
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_messages)

    def validate_inputs(self):
        """Validate user inputs"""
        if not self.username_var.get().strip():
            messagebox.showerror("Error", "Please enter your Instagram username")
            return False
        
        if not self.password_var.get().strip():
            messagebox.showerror("Error", "Please enter your Instagram password")
            return False
        
        if not self.target_profile_var.get().strip():
            messagebox.showerror("Error", "Please enter the target profile username")
            return False
        
        try:
            limit = self.video_limit_var.get().strip()
            if limit and int(limit) <= 0:
                messagebox.showerror("Error", "Video limit must be a positive number")
                return False
        except ValueError:
            messagebox.showerror("Error", "Video limit must be a valid number")
            return False
        
        try:
            workers = int(self.max_workers_var.get())
            if workers <= 0 or workers > 20:
                messagebox.showerror("Error", "Parallel downloads must be between 1 and 20")
                return False
        except ValueError:
            messagebox.showerror("Error", "Parallel downloads must be a valid number")
            return False
        
        return True

    def start_download(self):
        """Start the download process"""
        if not self.validate_inputs():
            return
        
        if self.is_downloading:
            return
        
        # Get values
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        target_profile = self.target_profile_var.get().strip()
        video_limit = self.video_limit_var.get().strip()
        video_limit = int(video_limit) if video_limit else None
        max_workers = int(self.max_workers_var.get())
        output_dir = self.output_dir_var.get().strip() or None
        
        # Create downloader
        self.downloader = InstagramReelDownloader(
            username=username,
            password=password,
            target_profile=target_profile,
            video_limit=video_limit,
            max_workers=max_workers,
            output_dir=output_dir,
            progress_callback=self.progress_callback
        )
        
        # Update UI
        self.is_downloading = True
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        
        # Clear log and reset progress
        self.clear_log()
        self.progress_bar['value'] = 0
        self.progress_var.set("Starting download...")
        
        # Start download in separate thread
        self.download_thread = threading.Thread(target=self.run_download)
        self.download_thread.daemon = True
        self.download_thread.start()

    def run_download(self):
        """Run download in separate thread"""
        try:
            success = self.downloader.run()
            self.message_queue.put(('finished', success))
        except Exception as e:
            self.message_queue.put(('log', f"❌ Download failed: {str(e)}"))
            self.message_queue.put(('finished', False))

    def pause_download(self):
        """Pause/resume download"""
        if not self.downloader:
            return
        
        if self.is_paused:
            self.downloader.resume_download()
            self.pause_button.config(text="Pause")
            self.is_paused = False
        else:
            self.downloader.pause_download()
            self.pause_button.config(text="Resume")
            self.is_paused = True

    def stop_download(self):
        """Stop download"""
        if self.downloader:
            self.downloader.stop_download()

    def download_finished(self):
        """Handle download completion"""
        self.is_downloading = False
        self.is_paused = False
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="Pause")
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set("Download completed")

    def save_settings(self):
        """Save current settings to file"""
        settings = {
            'username': self.username_var.get(),
            'target_profile': self.target_profile_var.get(),
            'video_limit': self.video_limit_var.get(),
            'max_workers': self.max_workers_var.get(),
            'output_dir': self.output_dir_var.get()
        }
        
        try:
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            messagebox.showinfo("Success", "Settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
                
                self.username_var.set(settings.get('username', ''))
                self.target_profile_var.set(settings.get('target_profile', ''))
                self.video_limit_var.set(settings.get('video_limit', '10'))
                self.max_workers_var.set(settings.get('max_workers', '5'))
                self.output_dir_var.set(settings.get('output_dir', ''))
        except Exception as e:
            print(f"Failed to load settings: {str(e)}")


def main():
    root = tk.Tk()
    app = InstagramScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()