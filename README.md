# Instagram Reel Downloader with GUI

A modern, user-friendly Instagram reel downloader with a graphical interface built using Python, Selenium, and Tkinter.

## Features

### 🎯 Core Functionality
- Download Instagram reels from any public profile
- Batch downloading with configurable limits
- Multi-threaded downloads for better performance
- Real-time progress tracking and logging

### 🖥️ Modern GUI Interface
- Clean, intuitive user interface using Tkinter
- Real-time progress bars and status updates
- Scrollable log window for detailed feedback
- Settings persistence (save/load configurations)

### ⚡ Advanced Controls
- **Pause/Resume**: Pause downloads and resume later
- **Stop**: Cancel downloads at any time
- **Custom Output Directory**: Choose where to save files
- **Configurable Limits**: Set maximum number of videos to download
- **Parallel Downloads**: Adjust concurrent download threads

### 🛡️ Improved Security & Reliability
- Better error handling and recovery
- No hardcoded credentials (secure input)
- Automatic popup handling
- Mobile emulation for better compatibility
- Optimized Chrome driver settings

## Installation

### Prerequisites
- Python 3.7 or higher
- Google Chrome browser
- ChromeDriver (will be managed automatically)

### Setup Steps

1. **Clone or download the project files**
   ```bash
   git clone <repository-url>
   cd instagram-scraper-python
   ```

2. **Install required dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install ChromeDriver (automatic)**
   The application will automatically manage ChromeDriver, but you can also install it manually:
   ```bash
   pip install webdriver-manager
   ```

## Usage

### Running the GUI Application

1. **Start the application**
   ```bash
   python instagram_scraper_gui.py
   ```

2. **Configure settings**
   - **Username**: Your Instagram username
   - **Password**: Your Instagram password
   - **Target Profile**: The profile to download reels from (without @)
   - **Video Limit**: Maximum number of videos (leave empty for no limit)
   - **Parallel Downloads**: Number of concurrent downloads (1-20)
   - **Output Directory**: Where to save files (optional)

3. **Start downloading**
   - Click "Start Download" to begin
   - Use "Pause" to pause/resume downloads
   - Use "Stop" to cancel the process
   - Monitor progress in real-time

4. **Save settings**
   - Click "Save Settings" to persist your configuration
   - Settings are automatically loaded on next startup

### Running the Original CLI Version

If you prefer the command-line interface:
```bash
python "Instagram Scraper Python.py"
```

## File Structure

```
instagram-scraper-python/
├── instagram_scraper_gui.py      # Main GUI application
├── Instagram Scraper Python.py   # Original CLI version
├── requirements.txt               # Python dependencies
├── README.md                     # This file
├── settings.json                 # Saved GUI settings (created after first save)
└── [profile]_reels_[timestamp]/  # Downloaded videos folder
```

## Key Improvements Over Original

### 🔧 Technical Improvements
- **Thread-safe GUI**: Proper separation of UI and download logic
- **Better error handling**: Comprehensive exception handling and recovery
- **Memory optimization**: Improved Chrome driver settings
- **Pause/Resume functionality**: Can pause and resume downloads
- **Progress tracking**: Real-time progress updates and logging

### 🎨 User Experience
- **No hardcoded credentials**: Secure credential input
- **Visual feedback**: Progress bars, status updates, and detailed logs
- **Settings persistence**: Save and load configurations
- **Flexible output**: Choose custom output directories
- **Better organization**: Timestamped folders for downloads

### 🛡️ Security & Reliability
- **No credential exposure**: Passwords are not stored in code
- **Better popup handling**: Improved Instagram popup management
- **Graceful shutdown**: Proper cleanup on stop/exit
- **Partial download cleanup**: Removes incomplete files on cancellation

## Troubleshooting

### Common Issues

1. **ChromeDriver not found**
   - Install webdriver-manager: `pip install webdriver-manager`
   - Or download ChromeDriver manually and add to PATH

2. **Login fails**
   - Check username/password
   - Try logging in manually first to handle any security checks
   - Instagram may require 2FA or additional verification

3. **No reels found**
   - Ensure the target profile exists and is public
   - Check if the profile has any reels posted
   - Try with a different profile

4. **Download failures**
   - Check internet connection
   - Reduce parallel downloads if experiencing issues
   - Some videos may be protected or unavailable

### Performance Tips

- **Optimal parallel downloads**: 3-5 threads work best for most systems
- **Video limits**: Set reasonable limits for large profiles
- **Output directory**: Use local drives for better performance
- **System resources**: Close other applications if experiencing slowdowns

## Dependencies

- **selenium**: Web automation and browser control
- **requests**: HTTP requests for video downloads
- **tkinter**: GUI framework (included with Python)
- **webdriver-manager**: Automatic ChromeDriver management

## Legal Notice

This tool is for educational purposes only. Please respect Instagram's Terms of Service and only download content you have permission to download. The developers are not responsible for any misuse of this software.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool.

## License

This project is open source and available under the MIT License.