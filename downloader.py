import os
import re
import time
import requests
import urllib.parse
from PyQt6.QtCore import QThread, pyqtSignal

# Default Headers to simulate a real browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def clean_filename(filename):
    """Remove characters that are invalid in Windows filenames."""
    filename = urllib.parse.unquote(filename)
    # Replace invalid chars: \ / : * ? " < > |
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def extract_filename(url, headers=None):
    """
    Extracts filename from Content-Disposition header, URL fragment, or URL path.
    """
    if headers:
        cd = headers.get('Content-Disposition') or headers.get('content-disposition')
        if cd:
            # Try UTF-8 filename format (filename*=UTF-8''name)
            utf8_match = re.search(r"filename\*=\s*utf-8''([^;\n]+)", cd, re.IGNORECASE)
            if utf8_match:
                return clean_filename(utf8_match.group(1))
            # Try normal filename format (filename="name")
            fn_match = re.search(r'filename="?([^";\n]+)"?', cd, re.IGNORECASE)
            if fn_match:
                return clean_filename(fn_match.group(1))

    # Fallback to URL fragment (hash)
    parsed = urllib.parse.urlparse(url)
    if parsed.fragment:
        # Check if the fragment resembles a filename (e.g. ends with an extension or contains dots)
        fragment = parsed.fragment
        # Remove any leading slashes/dashes
        fragment = fragment.lstrip('/')
        if '.' in fragment:
            return clean_filename(fragment)

    # Fallback to URL path basename
    path = parsed.path
    if path:
        basename = os.path.basename(path)
        if basename and '.' in basename:
            return clean_filename(basename)

    return "downloaded_file.bin"

class LinkResolver:
    @staticmethod
    def resolve(url):
        """
        Resolves a URL. If it's a fuckingfast.co link, scrapes the HTML to find
        the direct download URL. Otherwise, treats it as a direct link.
        Returns a tuple: (direct_url, filename, total_size)
        """
        try:
            is_fuckingfast = 'fuckingfast.co' in url or 'fuckingfast.net' in url
            direct_url = url
            filename = None
            total_size = 0

            if is_fuckingfast:
                # 1. Fetch landing page
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()
                html = response.text

                # 2. Extract direct link using regex
                dl_match = re.search(r'https?://dl\.fuckingfast\.[a-z0-9]+/dl/[^"]+', html)
                if not dl_match:
                    raise Exception("Could not find the direct download URL in fuckingfast.co landing page.")
                direct_url = dl_match.group(0)

            # 3. Always request headers using a GET request with Range: bytes=0-0 and stream=True
            headers_with_range = HEADERS.copy()
            headers_with_range['Range'] = 'bytes=0-0'
            
            # Use stream=True to prevent loading body content
            resp = requests.get(direct_url, headers=headers_with_range, stream=True, allow_redirects=True, timeout=15)
            try:
                resp.raise_for_status()
                
                # Check for Content-Range
                cr = resp.headers.get('Content-Range') or resp.headers.get('content-range')
                if cr:
                    size_match = re.search(r'/(\d+)', cr)
                    if size_match:
                        total_size = int(size_match.group(1))
                
                # If Content-Range not present, check Content-Length
                if total_size == 0:
                    cl = resp.headers.get('Content-Length') or resp.headers.get('content-length')
                    if cl:
                        total_size = int(cl)
                        
                filename = extract_filename(direct_url, resp.headers)
                if not filename or filename == "downloaded_file.bin":
                    filename = extract_filename(url, resp.headers)
            finally:
                resp.close()

            return direct_url, filename, total_size

        except Exception as e:
            raise Exception(f"Failed to resolve URL: {str(e)}")

class DownloadWorker(QThread):
    # Signals to communicate with the GUI thread
    resolved = pyqtSignal(str, str, int)  # worker_id, filename, total_size
    progress = pyqtSignal(str, int, int, float, float)  # worker_id, downloaded_bytes, total_bytes, speed (bytes/sec), eta (seconds)
    status_changed = pyqtSignal(str, str, str)  # worker_id, status_string, message
    error = pyqtSignal(str, str)  # worker_id, error_message

    def __init__(self, worker_id, original_url, download_dir):
        super().__init__()
        self.worker_id = worker_id
        self.original_url = original_url
        self.download_dir = download_dir
        
        self.direct_url = None
        self.filename = None
        self.total_size = 0
        
        # Thread-safe control flags
        self._is_paused = False
        self._is_cancelled = False
        self._resuming = False

    def pause(self):
        self._is_paused = True

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            # 1. Resolve Link (if not already resolved)
            if not self.direct_url or not self.filename:
                self.status_changed.emit(self.worker_id, "Resolving", "Scraping landing page...")
                self.direct_url, self.filename, self.total_size = LinkResolver.resolve(self.original_url)
                self.resolved.emit(self.worker_id, self.filename, self.total_size)
            
            # Ensure download directory exists
            os.makedirs(self.download_dir, exist_ok=True)
            file_path = os.path.join(self.download_dir, self.filename)
            part_path = file_path + ".part"

            # Determine starting byte position (for pause/resume)
            start_byte = 0
            if os.path.exists(part_path):
                start_byte = os.path.getsize(part_path)
                self._resuming = True

            # If we've already downloaded the whole file (or more) in the .part file
            if self.total_size > 0 and start_byte >= self.total_size:
                # File is complete, rename it
                if os.path.exists(file_path):
                    os.remove(file_path)
                os.rename(part_path, file_path)
                self.progress.emit(self.worker_id, self.total_size, self.total_size, 0.0, 0.0)
                self.status_changed.emit(self.worker_id, "Completed", "Download complete!")
                return

            self.status_changed.emit(self.worker_id, "Downloading", "Connecting to download server...")

            # 2. Establish connection to direct URL
            dl_headers = HEADERS.copy()
            if start_byte > 0:
                dl_headers['Range'] = f'bytes={start_byte}-'

            response = None
            try:
                response = requests.get(self.direct_url, headers=dl_headers, stream=True, timeout=20)
                
                # Check for link expiration (403 Forbidden or 410 Gone or 404 Not Found)
                if response.status_code in [403, 410, 404]:
                    self.status_changed.emit(self.worker_id, "Resolving", "Link expired. Re-resolving...")
                    # Re-scrape original page to get fresh direct link
                    self.direct_url, _, _ = LinkResolver.resolve(self.original_url)
                    response = requests.get(self.direct_url, headers=dl_headers, stream=True, timeout=20)
                
                response.raise_for_status()

            except Exception as e:
                # If range request fails, try downloading from scratch (if server does not support range)
                if start_byte > 0:
                    self.status_changed.emit(self.worker_id, "Downloading", "Range request failed, restarting from scratch...")
                    start_byte = 0
                    if 'Range' in dl_headers:
                        del dl_headers['Range']
                    response = requests.get(self.direct_url, headers=dl_headers, stream=True, timeout=20)
                    response.raise_for_status()
                else:
                    raise e

            # Check if server actually accepted Range header (Status Code 206)
            is_range_accepted = response.status_code == 206
            write_mode = 'ab' if (start_byte > 0 and is_range_accepted) else 'wb'
            
            if not is_range_accepted:
                start_byte = 0

            # 3. Start reading chunks
            downloaded = start_byte
            
            # Speed calculation variables
            start_time = time.time()
            bytes_since_last_calc = 0
            last_calc_time = start_time
            speed = 0.0
            
            # Smooth speed average
            alpha = 0.3  # Smoothing factor (0.3 = 30% weight to new speed reading)

            # Open file and pipe stream
            with open(part_path, write_mode) as f:
                for chunk in response.iter_content(chunk_size=65536): # 64KB chunks
                    # Check control flags
                    if self._is_cancelled:
                        self.status_changed.emit(self.worker_id, "Cancelled", "Download cancelled.")
                        break
                    
                    if self._is_paused:
                        self.status_changed.emit(self.worker_id, "Paused", "Download paused.")
                        break

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        bytes_since_last_calc += len(chunk)

                        # Update progress metrics every 0.5s or so
                        current_time = time.time()
                        time_diff = current_time - last_calc_time
                        if time_diff >= 0.5:
                            # Calculate current speed
                            inst_speed = bytes_since_last_calc / time_diff
                            speed = (alpha * inst_speed) + ((1 - alpha) * speed) if speed > 0 else inst_speed
                            
                            # Calculate ETA
                            eta = 0.0
                            if self.total_size > 0 and speed > 0:
                                eta = (self.total_size - downloaded) / speed

                            # Reset tracking variables
                            bytes_since_last_calc = 0
                            last_calc_time = current_time

                            self.progress.emit(self.worker_id, downloaded, self.total_size, speed, eta)

            # 4. Finalize
            if self._is_cancelled:
                # If cancelled, we delete the partial download
                if os.path.exists(part_path):
                    try:
                        os.remove(part_path)
                    except Exception:
                        pass
            elif not self._is_paused:
                # Completed successfully! Rename to final filename
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                os.rename(part_path, file_path)
                
                # Emit final completion
                self.progress.emit(self.worker_id, self.total_size, self.total_size, 0.0, 0.0)
                self.status_changed.emit(self.worker_id, "Completed", "Download complete!")

        except Exception as e:
            self.error.emit(self.worker_id, str(e))
            self.status_changed.emit(self.worker_id, "Failed", f"Error: {str(e)}")
