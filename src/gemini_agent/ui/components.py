from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                             QPushButton, QLabel, QListWidget, QSpacerItem, 
                             QSizePolicy, QScrollArea, QLineEdit, QListWidgetItem,
                             QTabWidget, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal

class Sidebar(QFrame):
    """
    Sidebar widget displaying chat history and providing search/filter functionality.
    """
    new_chat_requested = pyqtSignal()
    session_selected = pyqtSignal(object)
    context_menu_requested = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.sessions: Dict[str, Any] = {}
        self.current_session_id: Optional[str] = None
        self.init_ui()

    def init_ui(self) -> None:
        """Initializes the sidebar user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.btn_new_chat = QPushButton(" +  New chat")
        self.btn_new_chat.setObjectName("BtnNewChat")
        self.btn_new_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_chat.clicked.connect(self.new_chat_requested.emit)
        layout.addWidget(self.btn_new_chat)

        layout.addSpacing(5)
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search chats...")
        self.search_input.textChanged.connect(self.filter_sessions)
        layout.addWidget(self.search_input)

        layout.addWidget(QLabel("Recent"))

        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self._on_item_clicked)
        self.chat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_list.customContextMenuRequested.connect(self.context_menu_requested.emit)
        layout.addWidget(self.chat_list)

    def populate_sessions(self, sessions: Dict[str, Any], current_session_id: Optional[str] = None) -> None:
        """
        Populates the sidebar with session items.
        
        Args:
            sessions: Dictionary of session data.
            current_session_id: The ID of the currently active session.
        """
        self.sessions = sessions
        self.current_session_id = current_session_id
        self.filter_sessions(self.search_input.text())

    def filter_sessions(self, text: str) -> None:
        """
        Filters and displays sessions based on search text and date categories.
        
        Args:
            text: The search query text.
        """
        self.chat_list.clear()
        text = text.lower()
        
        # Sort sessions by date
        sorted_sessions = sorted(self.sessions.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)
        
        groups = {
            "Today": [],
            "Yesterday": [],
            "Previous 7 Days": [],
            "Older": []
        }
        
        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)

        for sess_id, sess_data in sorted_sessions:
            title = sess_data.get("title", "Untitled")
            if text and text not in title.lower():
                continue
                
            created_at_str = sess_data.get("created_at", "")
            try:
                # Handle ISO format with potential Z or offset
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')).date()
                else:
                    created_at = today
            except ValueError:
                created_at = today # Fallback

            if created_at == today:
                groups["Today"].append((sess_id, title))
            elif created_at == yesterday:
                groups["Yesterday"].append((sess_id, title))
            elif created_at >= last_week:
                groups["Previous 7 Days"].append((sess_id, title))
            else:
                groups["Older"].append((sess_id, title))

        for group_name, items in groups.items():
            if items:
                # Add Header
                header = QListWidgetItem(group_name)
                header.setFlags(Qt.ItemFlag.NoItemFlags) # Non-selectable
                header.setForeground(Qt.GlobalColor.gray)
                font = header.font()
                font.setBold(True)
                font.setPointSize(10)
                header.setFont(font)
                self.chat_list.addItem(header)
                
                for sess_id, title in items:
                    item = QListWidgetItem(f"  {title}")
                    item.setData(Qt.ItemDataRole.UserRole, sess_id)
                    self.chat_list.addItem(item)
                    if sess_id == self.current_session_id:
                        self.chat_list.setCurrentItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handles item click in the session list."""
        sess_id = item.data(Qt.ItemDataRole.UserRole)
        if sess_id:
            self.session_selected.emit(item)

class SidebarContainer(QFrame):
    """
    Container for the sidebar that uses tabs to switch between 
    Chat History and Project Explorer.
    """
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setObjectName("SidebarContainer")
        self.init_ui()

    def init_ui(self) -> None:
        """Initializes the container with tabbed navigation."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("SidebarTabs")
        
        self.chat_sidebar = Sidebar()
        self.tabs.addTab(self.chat_sidebar, "💬 Chats")
        
        # Project Explorer will be added from main.py
        
        layout.addWidget(self.tabs)

class ChatHeader(QWidget):
    """
    Header widget for the chat area, containing session-level controls and status.
    """
    toggle_sidebar_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    terminal_toggle_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initializes the header UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 20, 0)
        
        self.btn_toggle_sidebar = QPushButton("≡")
        self.btn_toggle_sidebar.setFixedSize(40, 40)
        self.btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar_requested.emit)
        layout.addWidget(self.btn_toggle_sidebar)
        
        layout.addSpacing(10)
        title_lbl = QLabel("Gemini AI Agent")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_lbl)
        
        layout.addSpacing(15)
        
        self.mode_indicator = QLabel("🔧 Local Tools")
        self.mode_indicator.setStyleSheet("color: #0B57D0; font-size: 12px; padding: 4px 8px; background-color: rgba(11, 87, 208, 0.1); border-radius: 4px;")
        layout.addWidget(self.mode_indicator)
        
        # Usage Label
        self.usage_label = QLabel("Usage: 0 tokens ($0.00)")
        self.usage_label.setStyleSheet("color: #888; font-size: 11px; margin-left: 10px;")
        layout.addWidget(self.usage_label)
        
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Terminal Toggle Button
        self.btn_terminal = QPushButton("💻 Terminal")
        self.btn_terminal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_terminal.setCheckable(True)
        self.btn_terminal.clicked.connect(self.terminal_toggle_requested.emit)
        layout.addWidget(self.btn_terminal)

        layout.addSpacing(10)

        # Settings Button (Restored)
        self.btn_settings = QPushButton("⚙️ Settings")
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setFixedWidth(100)
        self.btn_settings.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.btn_settings)

    def set_mode(self, use_search: bool) -> None:
        """
        Updates the mode indicator (Web Search vs Local Tools).
        
        Args:
            use_search: True if web search is enabled.
        """
        if use_search:
            self.mode_indicator.setText("🔍 Web Search")
            self.mode_indicator.setStyleSheet("color: #ff9800; font-size: 12px; padding: 4px 8px; background-color: rgba(255, 152, 0, 0.1); border-radius: 4px;")
        else:
            self.mode_indicator.setText("🔧 Local Tools")
            self.mode_indicator.setStyleSheet("color: #0B57D0; font-size: 12px; padding: 4px 8px; background-color: rgba(11, 87, 208, 0.1); border-radius: 4px;")

    def update_usage(self, total_tokens: int, estimated_cost: float) -> None:
        """
        Updates the usage label with token count and cost.
        
        Args:
            total_tokens: Total tokens used.
            estimated_cost: Estimated cost in USD.
        """
        self.usage_label.setText(f"Usage: {total_tokens:,} tokens (${estimated_cost:.4f})")
