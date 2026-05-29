def get_stylesheet():
    return """
    /* Main App Background */
    QMainWindow {
        background-color: #0d0d12;
    }
    
    QWidget {
        color: #e2e2e9;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, sans-serif;
        font-size: 13px;
    }

    /* Scrollbars styling */
    QScrollBar:vertical {
        background-color: #0f0f15;
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background-color: #2e2e3a;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #4b4b5e;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }

    QScrollBar:horizontal {
        background-color: #0f0f15;
        height: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background-color: #2e2e3a;
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #4b4b5e;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    /* Header Area */
    #HeaderFrame {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a1a2e, stop:1 #0d0d12);
        border-bottom: 2px solid #3c1e70;
        min-height: 80px;
    }
    #AppTitle {
        color: #ffffff;
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 1px;
    }
    #AppSubtitle {
        color: #9e9eb3;
        font-size: 11px;
        font-weight: 500;
    }

    /* Left Control Sidebar or Main Input Container */
    #InputPanel {
        background-color: #12121a;
        border: 1px solid #222230;
        border-radius: 12px;
    }
    
    /* Standard Labels */
    QLabel {
        font-weight: 500;
    }
    #SectionTitle {
        font-size: 14px;
        font-weight: 700;
        color: #bf8eff;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Text Edits and Inputs */
    QTextEdit, QLineEdit {
        background-color: #171722;
        border: 1px solid #2b2b3d;
        border-radius: 8px;
        padding: 8px;
        color: #f0f0f5;
        selection-background-color: #8b5cf6;
        selection-color: #ffffff;
    }
    QTextEdit:focus, QLineEdit:focus {
        border: 1px solid #7c3aed;
        background-color: #1a1a26;
    }
    QLineEdit::placeholder, QTextEdit::placeholder {
        color: #62627a;
    }

    /* Buttons */
    QPushButton {
        background-color: #6d28d9;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #7c3aed;
    }
    QPushButton:pressed {
        background-color: #5b21b6;
    }
    QPushButton:disabled {
        background-color: #2b2b3d;
        color: #71718a;
    }

    /* Outline / Accent Buttons (Secondary) */
    QPushButton#SecondaryBtn {
        background-color: #1f1f2e;
        border: 1px solid #3b3b54;
        color: #e2e2e9;
    }
    QPushButton#SecondaryBtn:hover {
        background-color: #2b2b3d;
        border-color: #555577;
    }
    QPushButton#SecondaryBtn:pressed {
        background-color: #151522;
    }

    /* Success / Green Button */
    QPushButton#SuccessBtn {
        background-color: #059669;
        color: #ffffff;
    }
    QPushButton#SuccessBtn:hover {
        background-color: #10b981;
    }
    QPushButton#SuccessBtn:pressed {
        background-color: #047857;
    }

    /* Danger / Stop / Cancel Button */
    QPushButton#DangerBtn {
        background-color: #dc2626;
        color: #ffffff;
    }
    QPushButton#DangerBtn:hover {
        background-color: #ef4444;
    }
    QPushButton#DangerBtn:pressed {
        background-color: #b91c1c;
    }

    /* Spinboxes / Sliders */
    QSpinBox {
        background-color: #171722;
        border: 1px solid #2b2b3d;
        border-radius: 8px;
        padding: 6px;
        color: #ffffff;
        min-width: 60px;
    }
    QSpinBox:focus {
        border: 1px solid #7c3aed;
    }
    
    QSlider::groove:horizontal {
        height: 6px;
        background: #252538;
        border-radius: 3px;
    }
    QSlider::sub-page:horizontal {
        background: #8b5cf6;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #ffffff;
        width: 16px;
        margin-top: -5px;
        margin-bottom: -5px;
        border-radius: 8px;
        border: 1px solid #7c3aed;
    }
    QSlider::handle:horizontal:hover {
        background: #bf8eff;
    }

    /* Stats Panel Card */
    #StatsPanel {
        background-color: #13131c;
        border: 1px solid #222230;
        border-radius: 12px;
        padding: 12px;
    }
    #StatValue {
        font-size: 20px;
        font-weight: 700;
        color: #ffffff;
    }
    #StatLabel {
        font-size: 11px;
        color: #9e9eb3;
        text-transform: uppercase;
        font-weight: 600;
    }

    /* Queue Container */
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    #QueueViewport {
        background-color: transparent;
    }

    /* Download Card Widget */
    #DownloadCard {
        background-color: #14141e;
        border: 1px solid #252538;
        border-radius: 12px;
        padding: 14px;
    }
    #DownloadCard[status="Downloading"] {
        border: 1px solid #5b21b6;
        background-color: #161424;
    }
    #DownloadCard[status="Completed"] {
        border: 1px solid #065f46;
        background-color: #101916;
    }
    #DownloadCard[status="Failed"] {
        border: 1px solid #7f1d1d;
        background-color: #1a1010;
    }
    #DownloadCard[status="Paused"] {
        border: 1px solid #854d0e;
        background-color: #181510;
    }

    /* Download Card Details */
    #CardTitle {
        font-size: 13px;
        font-weight: 700;
        color: #ffffff;
    }
    #CardProgressText {
        font-size: 11px;
        color: #a1a1aa;
    }
    #CardSpeedText {
        font-size: 11px;
        font-weight: 600;
        color: #8b5cf6;
    }
    #CardStatusText {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        padding: 2px 6px;
        border-radius: 4px;
        background-color: #27273a;
        color: #e2e2e9;
    }
    #CardStatusText[status="Downloading"] {
        background-color: #3b0764;
        color: #d8b4fe;
    }
    #CardStatusText[status="Completed"] {
        background-color: #064e3b;
        color: #6ee7b7;
    }
    #CardStatusText[status="Failed"] {
        background-color: #7f1d1d;
        color: #fca5a5;
    }
    #CardStatusText[status="Paused"] {
        background-color: #713f12;
        color: #fde047;
    }

    /* Progress Bars */
    QProgressBar {
        border: 1px solid #27273a;
        border-radius: 6px;
        text-align: center;
        background-color: #1b1b29;
        height: 16px;
        font-size: 10px;
        font-weight: 700;
        color: #ffffff;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #bf8eff);
        border-radius: 5px;
    }
    
    /* Specific Progress Bar Color Overrides */
    QProgressBar[status="Completed"]::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
    }
    QProgressBar[status="Failed"]::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b91c1c, stop:1 #ef4444);
    }
    QProgressBar[status="Paused"]::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d97706, stop:1 #f59e0b);
    }

    /* Small Circular Buttons inside Cards */
    QPushButton#CardActionBtn {
        background-color: #27273a;
        border: 1px solid #3f3f56;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: 600;
    }
    QPushButton#CardActionBtn:hover {
        background-color: #3b3b54;
        border-color: #626280;
    }
    QPushButton#CardActionBtn[accent="danger"] {
        color: #fca5a5;
    }
    QPushButton#CardActionBtn[accent="danger"]:hover {
        background-color: #dc2626;
        color: #ffffff;
        border-color: #ef4444;
    }
    QPushButton#CardActionBtn[accent="success"] {
        color: #6ee7b7;
    }
    QPushButton#CardActionBtn[accent="success"]:hover {
        background-color: #059669;
        color: #ffffff;
        border-color: #10b981;
    }

    /* Console Panel */
    #ConsoleLog {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11px;
        background-color: #0a0a0f;
        border: 1px solid #1c1c28;
        border-radius: 8px;
        color: #a1a1aa;
    }
    """
