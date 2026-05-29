import os
import sys
import re
import time
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QProgressBar, 
    QScrollArea, QFileDialog, QSlider, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSlot

# Import local modules
import styles
from downloader import DownloadWorker, HEADERS

def format_size(bytes_val):
    if bytes_val is None or bytes_val < 0:
        return "Unknown"
    val = float(bytes_val)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} PB"

def format_speed(bytes_per_sec):
    if bytes_per_sec is None or bytes_per_sec < 0:
        return "0.0 B/s"
    val = float(bytes_per_sec)
    for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} PB/s"

def format_time(seconds):
    if seconds is None or seconds < 0:
        return "--:--:--"
    if seconds > 3600 * 24:
        return "24h+"
    
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    else:
        return f"{m:02d}:{s:02d}"

class DownloadCardWidget(QFrame):
    """
    A custom widget representing a single file download card in the queue.
    """
    def __init__(self, worker_id, original_url, filename, total_size, on_pause, on_resume, on_cancel, parent=None):
        super().__init__(parent)
        self.worker_id = worker_id
        self.original_url = original_url
        self.filename = filename
        self.total_size = total_size
        self.downloaded_bytes = 0
        self.status = "Pending"  # Pending, Resolving, Downloading, Paused, Completed, Failed
        
        self.on_pause_cb = on_pause
        self.on_resume_cb = on_resume
        self.on_cancel_cb = on_cancel

        self.setObjectName("DownloadCard")
        self.setProperty("status", self.status)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header Row: Filename + Status Badge
        header_layout = QHBoxLayout()
        
        # Shorten filename visually if too long
        display_name = self.filename if self.filename else self.original_url
        if len(display_name) > 60:
            display_name = display_name[:35] + "..." + display_name[-20:]
            
        self.title_label = QLabel(display_name, self)
        self.title_label.setObjectName("CardTitle")
        self.title_label.setToolTip(self.filename or self.original_url)
        header_layout.addWidget(self.title_label, 1)

        self.status_badge = QLabel(self.status, self)
        self.status_badge.setObjectName("CardStatusText")
        self.status_badge.setProperty("status", self.status)
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.status_badge)
        
        layout.addLayout(header_layout)

        # Middle Row: Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setProperty("status", self.status)
        layout.addWidget(self.progress_bar)

        # Bottom Row: Size Tracker + Speed + ETA + Buttons
        bottom_layout = QHBoxLayout()
        
        self.size_label = QLabel("0 B / 0 B", self)
        self.size_label.setObjectName("CardProgressText")
        bottom_layout.addWidget(self.size_label)

        self.speed_label = QLabel("0.0 B/s", self)
        self.speed_label.setObjectName("CardSpeedText")
        bottom_layout.addWidget(self.speed_label)

        self.eta_label = QLabel("--:--:--", self)
        self.eta_label.setObjectName("CardProgressText")
        bottom_layout.addWidget(self.eta_label)

        bottom_layout.addStretch(1)

        # Control Buttons
        self.pause_resume_btn = QPushButton("Pause", self)
        self.pause_resume_btn.setObjectName("CardActionBtn")
        self.pause_resume_btn.clicked.connect(self.pause_resume_clicked)
        bottom_layout.addWidget(self.pause_resume_btn)

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setObjectName("CardActionBtn")
        self.cancel_btn.setProperty("accent", "danger")
        self.cancel_btn.clicked.connect(self.cancel_clicked)
        bottom_layout.addWidget(self.cancel_btn)

        layout.addLayout(bottom_layout)
        self.update_ui_state()

    def update_ui_state(self):
        """Update visual properties based on current status."""
        self.status_badge.setText(self.status)
        self.status_badge.setProperty("status", self.status)
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        
        self.setProperty("status", self.status)
        self.style().unpolish(self)
        self.style().polish(self)

        self.progress_bar.setProperty("status", self.status)
        self.progress_bar.style().unpolish(self.progress_bar)
        self.progress_bar.style().polish(self.progress_bar)

        # Enable/Disable/Rename buttons based on status
        if self.status == "Downloading":
            self.pause_resume_btn.setText("Pause")
            self.pause_resume_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
        elif self.status == "Paused":
            self.pause_resume_btn.setText("Resume")
            self.pause_resume_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
        elif self.status == "Resolving":
            self.pause_resume_btn.setText("Pause")
            self.pause_resume_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
        elif self.status == "Completed":
            self.pause_resume_btn.setText("Done")
            self.pause_resume_btn.setEnabled(False)
            self.cancel_btn.setText("Remove")
            self.cancel_btn.setEnabled(True)
            self.speed_label.setText("")
            self.eta_label.setText("")
        elif self.status == "Failed":
            self.pause_resume_btn.setText("Retry")
            self.pause_resume_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.speed_label.setText("")
            self.eta_label.setText("Error")
        else:  # Pending
            self.pause_resume_btn.setText("Start")
            self.pause_resume_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)

    def update_progress(self, downloaded, total, speed, eta):
        self.downloaded_bytes = downloaded
        self.total_size = total
        
        # Calculate percentage
        pct = 0
        if total > 0:
            pct = int((downloaded / total) * 100)
            self.progress_bar.setValue(pct)
            self.progress_bar.setFormat(f"{pct}%")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Downloading...")
            
        self.size_label.setText(f"{format_size(downloaded)} / {format_size(total)}")
        self.speed_label.setText(format_speed(speed))
        self.eta_label.setText(f"{format_time(eta)} left" if eta > 0 else "--:--:--")

    def update_status(self, new_status, message=""):
        self.status = new_status
        self.update_ui_state()
        if message:
            self.title_label.setToolTip(f"{self.filename or self.original_url}\nMessage: {message}")

    def update_resolved_details(self, filename, total_size):
        self.filename = filename
        self.total_size = total_size
        
        display_name = filename
        if len(display_name) > 60:
            display_name = display_name[:35] + "..." + display_name[-20:]
        self.title_label.setText(display_name)
        self.title_label.setToolTip(filename)
        self.size_label.setText(f"0 B / {format_size(total_size)}")

    def pause_resume_clicked(self):
        if self.status == "Downloading":
            self.on_pause_cb(self.worker_id)
        elif self.status in ["Paused", "Pending", "Failed"]:
            self.on_resume_cb(self.worker_id)

    def cancel_clicked(self):
        self.on_cancel_cb(self.worker_id)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FITGIRL concurrent downloader")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(styles.get_stylesheet())

        # Queue and Config State
        self.download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download")
        self.max_concurrency = 3
        self.queue_items = {}  # worker_id -> dict representing data
        self.active_workers = {}  # worker_id -> DownloadWorker thread
        self.card_widgets = {}  # worker_id -> DownloadCardWidget
        self.id_counter = 0

        self.init_ui()
        self.log("System", f"Application started. Output folder: {self.download_dir}")

    def init_ui(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ------------------ LEFT COLUMN: Control & Inputs ------------------
        left_column = QVBoxLayout()
        left_column.setSpacing(15)

        # Header Frame
        header_frame = QFrame(self)
        header_frame.setObjectName("HeaderFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        title_label = QLabel("FITGIRL DOWNLOADER", self)
        title_label.setObjectName("AppTitle")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("NATIVE WINDOWS CONCURRENT DOWNLOAD MANAGER", self)
        subtitle_label.setObjectName("AppSubtitle")
        header_layout.addWidget(subtitle_label)
        left_column.addWidget(header_frame)

        # Link Input Section
        input_panel = QFrame(self)
        input_panel.setObjectName("InputPanel")
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setSpacing(10)

        section_title = QLabel("Paste Game Links Here", self)
        section_title.setObjectName("SectionTitle")
        input_layout.addWidget(section_title)

        self.links_input = QTextEdit(self)
        self.links_input.setPlaceholderText(
            "Paste direct links or fuckingfast.co links here...\n"
            "Examples:\n"
            "https://fuckingfast.co/zsc47eju4igy#Game.part01.rar\n"
            "https://fuckingfast.co/yq1k8tv3lnbg#Game.part02.rar"
        )
        input_layout.addWidget(self.links_input)

        # Concurrency Limit Selector
        concurrency_layout = QHBoxLayout()
        concurrency_label = QLabel("Concurrency Limit:", self)
        concurrency_layout.addWidget(concurrency_label)

        self.concurrency_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.concurrency_slider.setRange(1, 10)
        self.concurrency_slider.setValue(self.max_concurrency)
        self.concurrency_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.concurrency_slider.setTickInterval(1)
        self.concurrency_slider.valueChanged.connect(self.concurrency_slider_changed)
        concurrency_layout.addWidget(self.concurrency_slider, 1)

        self.concurrency_val_label = QLabel(f"{self.max_concurrency}", self)
        self.concurrency_val_label.setFixedWidth(20)
        self.concurrency_val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        concurrency_layout.addWidget(self.concurrency_val_label)
        input_layout.addLayout(concurrency_layout)

        # Resolve & Add Button
        self.add_links_btn = QPushButton("Resolve && Add Links", self)
        self.add_links_btn.clicked.connect(self.resolve_and_add_links)
        input_layout.addWidget(self.add_links_btn)

        left_column.addWidget(input_panel, 1) # Expand links input panel

        # Settings Box
        settings_panel = QFrame(self)
        settings_panel.setObjectName("InputPanel")
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setSpacing(10)

        settings_title = QLabel("Download Location", self)
        settings_title.setObjectName("SectionTitle")
        settings_layout.addWidget(settings_title)

        dir_h_layout = QHBoxLayout()
        self.dir_input = QLineEdit(self.download_dir, self)
        self.dir_input.setReadOnly(True)
        dir_h_layout.addWidget(self.dir_input, 1)

        browse_btn = QPushButton("Browse", self)
        browse_btn.setObjectName("SecondaryBtn")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self.select_download_dir)
        dir_h_layout.addWidget(browse_btn)
        settings_layout.addLayout(dir_h_layout)

        dir_action_layout = QHBoxLayout()
        open_folder_btn = QPushButton("Open Download Folder", self)
        open_folder_btn.setObjectName("SecondaryBtn")
        open_folder_btn.clicked.connect(self.open_download_folder)
        dir_action_layout.addWidget(open_folder_btn)
        settings_layout.addLayout(dir_action_layout)

        left_column.addWidget(settings_panel)

        main_layout.addLayout(left_column, 35) # Left pane is 35% width

        # ------------------ RIGHT COLUMN: Queue & Stats ------------------
        right_column = QVBoxLayout()
        right_column.setSpacing(15)

        # Stats Dashboard Row
        stats_panel = QFrame(self)
        stats_panel.setObjectName("StatsPanel")
        stats_layout = QHBoxLayout(stats_panel)
        stats_layout.setContentsMargins(15, 12, 15, 12)

        # Speed Stat
        speed_stat_layout = QVBoxLayout()
        speed_title = QLabel("Total Download Speed", self)
        speed_title.setObjectName("StatLabel")
        speed_stat_layout.addWidget(speed_title)
        self.total_speed_lbl = QLabel("0.0 B/s", self)
        self.total_speed_lbl.setObjectName("StatValue")
        speed_stat_layout.addWidget(self.total_speed_lbl)
        stats_layout.addLayout(speed_stat_layout)
        
        stats_layout.addSpacing(20)

        # Progress Stat
        progress_stat_layout = QVBoxLayout()
        progress_title = QLabel("Aggregate Progress", self)
        progress_title.setObjectName("StatLabel")
        progress_stat_layout.addWidget(progress_title)
        self.overall_progress_bar = QProgressBar(self)
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        progress_stat_layout.addWidget(self.overall_progress_bar)
        stats_layout.addLayout(progress_stat_layout, 1)

        stats_layout.addSpacing(20)

        # Completed Counter
        counter_layout = QVBoxLayout()
        counter_title = QLabel("Files Completed", self)
        counter_title.setObjectName("StatLabel")
        counter_layout.addWidget(counter_title)
        self.completed_ratio_lbl = QLabel("0 / 0", self)
        self.completed_ratio_lbl.setObjectName("StatValue")
        counter_layout.addWidget(self.completed_ratio_lbl)
        stats_layout.addLayout(counter_layout)

        right_column.addWidget(stats_panel)

        # Control Panel for the Queue
        queue_actions_layout = QHBoxLayout()
        
        self.start_all_btn = QPushButton("Start All", self)
        self.start_all_btn.setObjectName("SuccessBtn")
        self.start_all_btn.clicked.connect(self.start_all_downloads)
        queue_actions_layout.addWidget(self.start_all_btn)

        self.pause_all_btn = QPushButton("Pause All", self)
        self.pause_all_btn.setObjectName("SecondaryBtn")
        self.pause_all_btn.clicked.connect(self.pause_all_downloads)
        queue_actions_layout.addWidget(self.pause_all_btn)

        self.clear_completed_btn = QPushButton("Clear Completed", self)
        self.clear_completed_btn.setObjectName("SecondaryBtn")
        self.clear_completed_btn.clicked.connect(self.clear_completed_downloads)
        queue_actions_layout.addWidget(self.clear_completed_btn)

        self.clear_all_btn = QPushButton("Clear Queue", self)
        self.clear_all_btn.setObjectName("DangerBtn")
        self.clear_all_btn.clicked.connect(self.clear_all_downloads)
        queue_actions_layout.addWidget(self.clear_all_btn)

        right_column.addLayout(queue_actions_layout)

        # Queue Scroll Area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("QueueScroll")
        
        self.queue_widget = QWidget()
        self.queue_widget.setObjectName("QueueViewport")
        self.queue_layout = QVBoxLayout(self.queue_widget)
        self.queue_layout.setContentsMargins(0, 0, 10, 0)
        self.queue_layout.setSpacing(10)
        self.queue_layout.addStretch(1)  # Keeps cards pushed to the top
        
        scroll_area.setWidget(self.queue_widget)
        right_column.addWidget(scroll_area, 1)

        # Collapsible Developer Log
        log_panel_layout = QVBoxLayout()
        log_panel_layout.setSpacing(5)
        
        log_title = QLabel("System Log Console", self)
        log_title.setObjectName("SectionTitle")
        log_panel_layout.addWidget(log_title)
        
        self.log_console = QTextEdit(self)
        self.log_console.setObjectName("ConsoleLog")
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(120)
        log_panel_layout.addWidget(self.log_console)
        
        right_column.addLayout(log_panel_layout)

        main_layout.addLayout(right_column, 65) # Right pane is 65% width

    # ------------------ EVENT LOGGING ------------------
    def log(self, category, message):
        t_str = time.strftime("%H:%M:%S")
        log_text = f"[{t_str}] [{category}] {message}"
        self.log_console.append(log_text)
        
        # Scroll to bottom
        cursor = self.log_console.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_console.setTextCursor(cursor)

    # ------------------ DIRECTORY & CONCURRENCY SETTINGS ------------------
    def select_download_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.download_dir)
        if folder:
            self.download_dir = folder
            self.dir_input.setText(folder)
            self.log("Settings", f"Download directory changed to: {folder}")

    def open_download_folder(self):
        os.makedirs(self.download_dir, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(self.download_dir)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', self.download_dir])
        else:
            subprocess.Popen(['xdg-open', self.download_dir])
        self.log("System", "Opened download folder in file explorer.")

    def concurrency_slider_changed(self, value):
        self.max_concurrency = value
        self.concurrency_val_label.setText(f"{value}")
        self.log("Settings", f"Concurrency limit changed to: {value}")
        # Process queue in case limit went up
        self.process_download_queue()

    # ------------------ QUEUE PROCESSOR ------------------
    def process_download_queue(self):
        """
        Manages downloads based on concurrency limits. Starts pending items.
        """
        # Count active running workers
        active_count = len(self.active_workers)
        
        if active_count >= self.max_concurrency:
            return

        # Find items that are ready/pending and need to start
        for w_id, item in self.queue_items.items():
            if active_count >= self.max_concurrency:
                break
            
            # Start items in "Pending" status (user clicked start or auto-started)
            if item["status"] == "Pending":
                self.start_worker(w_id)
                active_count += 1
        
        self.update_overall_stats()

    def start_worker(self, worker_id):
        item = self.queue_items[worker_id]
        
        # Create background thread worker
        worker = DownloadWorker(worker_id, item["url"], self.download_dir)
        
        # Copy resolved details if we already resolved them
        if item["direct_url"]:
            worker.direct_url = item["direct_url"]
            worker.filename = item["filename"]
            worker.total_size = item["total_size"]

        # Connect signals
        worker.resolved.connect(self.on_worker_resolved)
        worker.progress.connect(self.on_worker_progress)
        worker.status_changed.connect(self.on_worker_status_changed)
        worker.error.connect(self.on_worker_error)
        worker.finished.connect(lambda: self.on_worker_finished(worker_id))

        self.active_workers[worker_id] = worker
        self.queue_items[worker_id]["status"] = "Downloading"
        self.card_widgets[worker_id].update_status("Downloading", "Starting download...")
        
        self.log("Queue", f"Starting download for: {item['filename'] or item['url']}")
        worker.start()

    # ------------------ WORKER CALLBACK SLOTS ------------------
    @pyqtSlot(str, str, int)
    def on_worker_resolved(self, worker_id, filename, total_size):
        if worker_id in self.queue_items:
            item = self.queue_items[worker_id]
            item["filename"] = filename
            item["total_size"] = total_size
            item["direct_url"] = self.active_workers[worker_id].direct_url
            
            self.card_widgets[worker_id].update_resolved_details(filename, total_size)
            self.log("Resolver", f"Resolved '{filename}' ({format_size(total_size)})")
            self.update_overall_stats()

    @pyqtSlot(str, int, int, float, float)
    def on_worker_progress(self, worker_id, downloaded, total, speed, eta):
        if worker_id in self.queue_items:
            item = self.queue_items[worker_id]
            item["downloaded_bytes"] = downloaded
            item["total_size"] = total
            item["speed"] = speed
            item["eta"] = eta
            
            self.card_widgets[worker_id].update_progress(downloaded, total, speed, eta)
            self.update_overall_stats()

    @pyqtSlot(str, str, str)
    def on_worker_status_changed(self, worker_id, status, message):
        if worker_id in self.queue_items:
            self.queue_items[worker_id]["status"] = status
            self.card_widgets[worker_id].update_status(status, message)
            
            self.log("Worker", f"[{self.queue_items[worker_id]['filename'] or worker_id}] Status: {status} ({message})")
            
            if status in ["Paused", "Completed", "Failed", "Cancelled"]:
                # Stop tracking speed
                self.queue_items[worker_id]["speed"] = 0.0
                
            self.update_overall_stats()

    @pyqtSlot(str, str)
    def on_worker_error(self, worker_id, err_msg):
        self.log("Error", f"Worker {worker_id} encountered error: {err_msg}")

    def on_worker_finished(self, worker_id):
        # Remove from active workers list
        if worker_id in self.active_workers:
            self.active_workers[worker_id].deleteLater()
            del self.active_workers[worker_id]
            
        self.log("Queue", f"Worker thread finished: {worker_id}")
        
        # Process next in queue
        self.process_download_queue()
        self.update_overall_stats()

    # ------------------ FRONTEND CARD CONTROLS ------------------
    def pause_download(self, worker_id):
        if worker_id in self.active_workers:
            self.active_workers[worker_id].pause()
            self.log("Action", f"Pausing download for: {self.queue_items[worker_id]['filename']}")

    def resume_download(self, worker_id):
        if worker_id in self.queue_items:
            item = self.queue_items[worker_id]
            item["status"] = "Pending"
            self.card_widgets[worker_id].update_status("Pending", "Waiting in queue...")
            self.log("Action", f"Queued resume for: {item['filename']}")
            self.process_download_queue()

    def cancel_download(self, worker_id):
        # 1. Stop background thread if active
        if worker_id in self.active_workers:
            self.active_workers[worker_id].cancel()
            self.active_workers[worker_id].wait() # Wait for thread exit to release file locks

        item = self.queue_items.get(worker_id)
        if item:
            filename = item["filename"] or item["url"]
            self.log("Action", f"Removing download card: {filename}")
            
            # 2. Remove widget from UI layout
            widget = self.card_widgets.get(worker_id)
            if widget:
                self.queue_layout.removeWidget(widget)
                widget.deleteLater()
                del self.card_widgets[worker_id]
            
            # 3. Remove entry from queue list
            del self.queue_items[worker_id]
            
        self.process_download_queue()
        self.update_overall_stats()

    # ------------------ GLOBAL QUEUE OPERATIONS ------------------
    def start_all_downloads(self):
        self.log("Action", "Starting all pending downloads.")
        for w_id, item in self.queue_items.items():
            if item["status"] in ["Paused", "Failed", "Pending", "Resolved"]:
                item["status"] = "Pending"
                self.card_widgets[w_id].update_status("Pending", "Queued...")
        self.process_download_queue()

    def pause_all_downloads(self):
        self.log("Action", "Pausing all active downloads.")
        # Trigger pause on all active threads
        for worker in list(self.active_workers.values()):
            worker.pause()

    def clear_completed_downloads(self):
        self.log("Action", "Clearing completed downloads from view.")
        completed_ids = [w_id for w_id, item in self.queue_items.items() if item["status"] == "Completed"]
        for w_id in completed_ids:
            self.cancel_download(w_id) # Cancel/Remove handles clean UI removal

    def clear_all_downloads(self):
        self.log("Action", "Clearing entire download queue.")
        # Copy keys to list to avoid runtime mutation errors
        all_ids = list(self.queue_items.keys())
        for w_id in all_ids:
            self.cancel_download(w_id)

    # ------------------ STATS AGGREGATOR ------------------
    def update_overall_stats(self):
        total_speed = 0.0
        total_downloaded = 0
        total_size = 0
        completed_count = 0
        total_count = len(self.queue_items)

        for item in self.queue_items.values():
            total_speed += item["speed"]
            total_downloaded += item["downloaded_bytes"]
            total_size += item["total_size"]
            if item["status"] == "Completed":
                completed_count += 1

        self.total_speed_lbl.setText(format_speed(total_speed))
        self.completed_ratio_lbl.setText(f"{completed_count} / {total_count}")

        # Compute overall progress
        if total_size > 0:
            progress_pct = int((total_downloaded / total_size) * 100)
            self.overall_progress_bar.setValue(progress_pct)
        else:
            self.overall_progress_bar.setValue(0)

    # ------------------ LINK PARSING & ADDING ------------------
    def resolve_and_add_links(self):
        text = self.links_input.toPlainText().strip()
        if not text:
            self.log("Warning", "No links pasted.")
            return

        # Extract all URLs using regex (robust against bullet points, list numbers, quotes, etc.)
        valid_links = re.findall(r'https?://[^\s,\;\"\'\<\>]+', text)

        if not valid_links:
            self.log("Warning", "No valid HTTP/HTTPS URLs found in pasted text.")
            return

        self.log("Input", f"Found {len(valid_links)} URLs. Adding to queue...")

        for url in valid_links:
            # Check if this link is already in queue to avoid duplicates
            duplicate = False
            for item in self.queue_items.values():
                if item["url"] == url:
                    duplicate = True
                    break
            
            if duplicate:
                self.log("Queue", f"Skipping duplicate link: {url}")
                continue

            self.id_counter += 1
            worker_id = f"dl_{self.id_counter}"

            # Create entry state
            self.queue_items[worker_id] = {
                "url": url,
                "direct_url": None,
                "filename": None,
                "total_size": 0,
                "downloaded_bytes": 0,
                "status": "Pending",
                "speed": 0.0,
                "eta": 0.0
            }

            # Create UI Card Widget
            card = DownloadCardWidget(
                worker_id=worker_id,
                original_url=url,
                filename=None,
                total_size=0,
                on_pause=self.pause_download,
                on_resume=self.resume_download,
                on_cancel=self.cancel_download
            )
            
            # Add to UI layout list
            # Insert at the second to last position (before the layout spacer stretch)
            self.queue_layout.insertWidget(self.queue_layout.count() - 1, card)
            self.card_widgets[worker_id] = card
            card.show() # CRITICAL: Ensure widget is visible after adding to layout dynamically!

        # Clear text edit
        self.links_input.clear()
        
        # Refresh and auto-process
        self.update_overall_stats()
        self.process_download_queue()

    # ------------------ APP SHUTDOWN CLEANUP ------------------
    def closeEvent(self, event):
        """Ensure all background worker threads are canceled and completed before quitting."""
        active_count = len(self.active_workers)
        if active_count > 0:
            self.log("System", "Application closing. Safely shutting down active download streams...")
            # Cancel all workers
            for worker in list(self.active_workers.values()):
                worker.cancel()
            
            # Wait for thread loops to clean up file handles
            for worker in list(self.active_workers.values()):
                worker.wait()
                
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
