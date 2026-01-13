from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QMovie
from pathlib import Path
from gemini_agent.config.app_config import AppConfig

class StatusWidget(QWidget):
    """
    Widget to display status text and a 'Thinking' GIF animation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.status_label)

        # GIF Label
        self.gif_label = QLabel()
        self.gif_label.setFixedSize(30, 30)
        self.gif_label.setScaledContents(True)
        self.gif_label.hide() # Hidden by default
        layout.addWidget(self.gif_label)
        
        # Load Movie
        gif_path = AppConfig.RESOURCES_DIR / "thinking.gif"
        if gif_path.exists():
            self.movie = QMovie(str(gif_path))
            self.movie.setScaledSize(QSize(30, 30))
            self.gif_label.setMovie(self.movie)
        else:
            self.movie = None

        layout.addStretch()

    def set_status(self, text: str):
        """Updates the status text safely."""
        try:
            # Check if the label still exists before trying to set text
            if hasattr(self, 'status_label') and self.status_label:
                # In PyQt6, we can also check if the underlying C++ object is deleted
                # but a try-except block is often more portable and robust for this specific error.
                self.status_label.setText(text)
        except (RuntimeError, AttributeError):
            # This happens if the C++ object has been deleted
            pass

    def start_loading(self):
        """Shows and starts the GIF animation."""
        try:
            if self.movie and self.gif_label:
                self.gif_label.show()
                self.movie.start()
        except (RuntimeError, AttributeError):
            pass

    def stop_loading(self):
        """Stops and hides the GIF animation."""
        try:
            if self.movie and self.gif_label:
                self.movie.stop()
                self.gif_label.hide()
        except (RuntimeError, AttributeError):
            pass
