import sys
import os
import threading
from typing import Optional, Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QMessageBox, QFileDialog, QScrollArea, 
                             QFrame, QListWidgetItem, QSplitter, QMenu, QInputDialog, 
                             QDialog, QDockWidget) 
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QMetaObject, Q_ARG

from gemini_agent.config.app_config import AppConfig, ModelRegistry, Theme, Role, setup_logging
from gemini_agent.ui.widgets import MessageBubble, AutoResizingTextEdit, AttachmentItem
from gemini_agent.core.worker import GeminiWorker, GeminiWorkerThread, WorkerConfig
from gemini_agent.core.session_manager import SessionManager
from gemini_agent.core.tools import TOOL_REGISTRY
from gemini_agent.core.attachment_manager import AttachmentManager
from gemini_agent.core.conductor_manager import ConductorManager
from gemini_agent.core.exporter import Exporter
from gemini_agent.core.indexer import Indexer
from gemini_agent.core.plugins import PluginManager
from gemini_agent.core.checkpoint_manager import CheckpointManager
from gemini_agent.ui.settings_dialog import SettingsDialog
from gemini_agent.ui.deep_review import DeepReviewDialog
from gemini_agent.ui.components import SidebarContainer, ChatHeader
from gemini_agent.ui.status_widget import StatusWidget
from gemini_agent.ui.project_explorer import ProjectExplorer
from gemini_agent.ui.symbol_browser import SymbolBrowser
from gemini_agent.ui.theme_manager import ThemeManager
from gemini_agent.ui.plugin_dialog import PluginDialog
from gemini_agent.ui.terminal_widget import TerminalWidget
from gemini_agent.ui.conductor_dialog import ConductorDialog

class ChatController(QObject):
    """
    Controller handling the business logic of the chat application.
    Separates UI from gemini_agent.core logic and worker coordination.
    """
    status_updated = pyqtSignal(str)
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    usage_updated = pyqtSignal(str, int, int)
    terminal_output = pyqtSignal(str, str)
    tool_confirmation_requested = pyqtSignal(str, dict, str)

    def __init__(self, app_config: AppConfig, session_manager: SessionManager, 
                 attachment_manager: AttachmentManager, conductor_manager: ConductorManager,
                 indexer: Indexer, plugin_manager: PluginManager, 
                 checkpoint_manager: CheckpointManager):
        super().__init__()
        self.app_config = app_config
        self.session_manager = session_manager
        self.attachment_manager = attachment_manager
        self.conductor_manager = conductor_manager
        self.indexer = indexer
        self.plugin_manager = plugin_manager
        self.checkpoint_manager = checkpoint_manager
        self.worker: Optional[GeminiWorker] = None
        self.worker_thread: Optional[GeminiWorkerThread] = None

    def stop_worker(self) -> None:
        """Safely stops any running worker thread."""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(3000) # Wait up to 3 seconds
            if self.worker_thread.isRunning():
                self.worker_thread.terminate()
        
        self.worker = None
        self.worker_thread = None

    def send_message(self, prompt: str, system_instruction_override: Optional[str] = None) -> None:
        """Starts the Gemini worker to process the user request."""
        # Ensure previous worker is stopped
        self.stop_worker()
        
        attachments = self.attachment_manager.get_attachments()
        
        if not self.app_config.api_key:
            self.error_occurred.emit("Enter API Key in Settings.")
            return

        session_id = self.session_manager.current_session_id
        session_data = self.session_manager.get_session(session_id)
        
        if not session_data["messages"]:
            new_title = prompt[:25] if prompt else "Analysis"
            self.session_manager.update_session_title(session_id, new_title)
            
        self.session_manager.add_message(session_id, Role.USER.value, prompt or "[Files]")

        history_context = session_data["messages"][:-1]
        
        # Get session-specific config
        sess_config = session_data.get("config", {})
        model = sess_config.get("model", self.app_config.model)
        temp = sess_config.get("temperature", self.app_config.get("temperature", 0.8))
        top_p = sess_config.get("top_p", self.app_config.get("top_p", 0.95))
        max_turns = sess_config.get("max_turns", self.app_config.get("max_turns", 20))
        thinking_enabled = sess_config.get("thinking_enabled", self.app_config.get("thinking_enabled", False))
        thinking_budget = sess_config.get("thinking_budget", self.app_config.get("thinking_budget", 4096))

        config = WorkerConfig(
            api_key=self.app_config.api_key,
            prompt=prompt,
            model=model,
            file_paths=list(attachments),
            history_context=history_context,
            use_grounding=self.app_config.get("use_search", False),
            system_instruction=system_instruction_override or self.app_config.get("system_instruction"),
            temperature=temp,
            top_p=top_p,
            max_turns=max_turns,
            thinking_enabled=thinking_enabled,
            thinking_budget=thinking_budget,
            session_id=session_id,
            initial_plan=session_data.get("plan", ""),
            initial_specs=session_data.get("specs", ""),
            plugin_manager=self.plugin_manager
        )

        self.worker = GeminiWorker(config)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self.error_occurred.emit)
        self.worker.status_update.connect(self.status_updated.emit)
        self.worker.terminal_output.connect(self.terminal_output.emit)
        self.worker.request_confirmation.connect(self.tool_confirmation_requested.emit)
        self.worker.plan_updated.connect(lambda p: self.session_manager.update_session_plan(session_id, p))
        self.worker.specs_updated.connect(lambda s: self.session_manager.update_session_specs(session_id, s))
        self.worker.usage_updated.connect(self.usage_updated.emit)
        
        try:
            self.worker_thread = GeminiWorkerThread(self.worker)
            # Use a member variable to keep the thread alive
            self.worker_thread.finished.connect(self._on_thread_finished)
            self.worker_thread.start()
        except Exception as e:
            self.error_occurred.emit(f"Failed to start worker: {str(e)}")

    def _on_thread_finished(self) -> None:
        """Cleanup when the thread finishes."""
        finished_thread = self.sender()
        if finished_thread:
            finished_thread.deleteLater()
            
            # Only clear the reference if it still points to the finished thread
            if self.worker_thread == finished_thread:
                self.worker_thread = None

    def _on_worker_finished(self, text: str) -> None:
        self.session_manager.add_message(self.session_manager.current_session_id, Role.MODEL.value, text)
        self.attachment_manager.clear_attachments()
        self.response_received.emit(text)

    def confirm_tool(self, confirmation_id: str, allowed: bool, modified_args: Optional[Dict[str, Any]] = None) -> None:
        if self.worker:
            self.worker.confirm_tool(confirmation_id, allowed, modified_args)


class GeminiBrowser(QMainWindow):
    """
    Main window for the Gemini AI Agent application.
    Handles UI layout and delegates logic to ChatController.
    """
    def __init__(self, app_config: AppConfig, theme_manager: ThemeManager, 
                 session_manager: SessionManager, attachment_manager: AttachmentManager,
                 conductor_manager: ConductorManager, indexer: Indexer,
                 plugin_manager: PluginManager, checkpoint_manager: CheckpointManager):
        super().__init__()
        self.app_config = app_config
        self.theme_manager = theme_manager
        self.session_manager = session_manager
        self.attachment_manager = attachment_manager
        self.conductor_manager = conductor_manager
        self.indexer = indexer
        self.plugin_manager = plugin_manager
        self.checkpoint_manager = checkpoint_manager
        
        self.controller = ChatController(
            app_config, session_manager, attachment_manager, 
            conductor_manager, indexer, plugin_manager, checkpoint_manager
        )
        
        self.status_widget: Optional[StatusWidget] = None

        self.init_ui()
        self._connect_controller()
        self.update_sidebar()
        self.create_new_session()
        self.refresh_index()
        
        # Apply initial theme
        self.theme_manager.apply_theme(self.app_config.theme)

    def _connect_controller(self) -> None:
        self.controller.status_updated.connect(self.on_status_update)
        self.controller.response_received.connect(self.on_response_success)
        self.controller.error_occurred.connect(self.on_response_error)
        self.controller.usage_updated.connect(self.on_usage_updated)
        self.controller.terminal_output.connect(self.on_terminal_output)
        self.controller.tool_confirmation_requested.connect(self.show_tool_confirmation)

    def init_ui(self) -> None:
        """Initializes the main user interface components."""
        self.setWindowTitle("Gemini AI Agent - Professional Edition")
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._setup_sidebar()
        self._setup_chat_area()
        self._setup_terminal()

        # Splitter for Sidebar and Chat Area
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar_container)
        self.splitter.addWidget(self.chat_area)
        self.splitter.setStretchFactor(1, 4)
        self.splitter.setHandleWidth(1)

        main_layout.addWidget(self.splitter)
        self.header.set_mode(self.app_config.get("use_search", False))
        
        self.setup_settings_menu()

    def _setup_sidebar(self) -> None:
        """Initializes the sidebar components."""
        self.sidebar_container = SidebarContainer()
        self.sidebar = self.sidebar_container.chat_sidebar
        self.sidebar.new_chat_requested.connect(self.create_new_session)
        self.sidebar.session_selected.connect(self.load_session_from_list)
        self.sidebar.context_menu_requested.connect(self.show_context_menu)
        
        # Project Explorer
        self.project_explorer = ProjectExplorer(root_path=".")
        self.project_explorer.file_attached.connect(self.add_attachment)
        self.project_explorer.folder_attached.connect(self.add_attachment)
        self.sidebar_container.tabs.addTab(self.project_explorer, "📁 Project")

        # Symbol Browser
        self.symbol_browser = SymbolBrowser()
        self.symbol_browser.btn_refresh.clicked.connect(self.refresh_index)
        self.symbol_browser.symbol_selected.connect(self.on_symbol_selected)
        self.sidebar_container.tabs.addTab(self.symbol_browser, "🔍 Symbols")

    def _setup_chat_area(self) -> None:
        """Initializes the central chat area."""
        self.chat_area = QWidget()
        self.chat_area.setObjectName("ChatArea")
        chat_layout = QVBoxLayout(self.chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Header
        self.header = ChatHeader()
        self.header.toggle_sidebar_requested.connect(self.toggle_sidebar)
        self.header.terminal_toggle_requested.connect(self.toggle_terminal)
        chat_layout.addWidget(self.header)

        # Splitter for Messages
        self.chat_splitter = QSplitter(Qt.Orientation.Vertical)
        self.chat_splitter.setHandleWidth(1)

        # Messages Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("ScrollArea")

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSpacing(20)
        self.messages_layout.setContentsMargins(50, 20, 50, 20)

        self.scroll_area.setWidget(self.messages_container)
        self.chat_splitter.addWidget(self.scroll_area)

        chat_layout.addWidget(self.chat_splitter, 1)

        self._setup_input_area(chat_layout)

    def _setup_terminal(self) -> None:
        """Initializes the terminal dock."""
        self.terminal = TerminalWidget()
        self.terminal_dock = QDockWidget("Terminal", self)
        self.terminal_dock.setWidget(self.terminal)
        self.terminal_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.terminal_dock)
        self.terminal_dock.hide()
        self.terminal_dock.visibilityChanged.connect(self.on_terminal_visibility_changed)

    def _setup_input_area(self, layout: QVBoxLayout) -> None:
        """Initializes the bottom input area."""
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(20, 10, 20, 30)

        # Attachment List
        self.attachment_list_layout = QHBoxLayout()
        self.attachment_list_layout.setContentsMargins(10, 0, 10, 5)
        self.attachment_list_layout.setSpacing(5)
        self.attachment_list_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        bottom_layout.addLayout(self.attachment_list_layout)

        self.input_frame = QFrame()
        self.input_frame.setObjectName("InputFrame")
        pill_layout = QHBoxLayout(self.input_frame)
        pill_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_file = QPushButton("+")
        self.btn_file.setFixedSize(36, 36)
        self.btn_file.clicked.connect(self.show_attach_menu)

        self.input_field = AutoResizingTextEdit(self) 
        self.input_field.returnPressed.connect(self.send_message)

        # Populate completer with tools, commands, and files
        keywords = ["/clear", "/help", "/reset", "/conductor"]
        keywords.extend(list(TOOL_REGISTRY.keys()))
        keywords.extend(self.conductor_manager.get_available_commands())
        try:
            keywords.extend([f for f in os.listdir(".") if not f.startswith(".")])
        except OSError:
            pass
        self.input_field.update_keywords(keywords)

        btn_send = QPushButton("➤")
        btn_send.setFixedSize(36, 36)
        btn_send.clicked.connect(self.send_message)

        pill_layout.addWidget(self.btn_file)
        pill_layout.addWidget(self.input_field)
        pill_layout.addWidget(btn_send)

        bottom_layout.addWidget(self.input_frame)
        layout.addWidget(bottom_container, 0)

    def setup_settings_menu(self) -> None:
        """Sets up the unified settings menu on the header button."""
        self.settings_menu = QMenu(self)
        
        # 1. Settings Dialog
        self.settings_menu.addAction("⚙️ Application Settings").triggered.connect(self.open_settings)
        self.settings_menu.addSeparator()
        
        # 2. Conductor Orchestrator
        self.settings_menu.addAction("🚀 Conductor Orchestrator").triggered.connect(self.open_conductor)
        
        # 3. Conductor Submenu
        conductor_submenu = self.settings_menu.addMenu("📋 Conductor Commands")
        self._populate_conductor_menu(conductor_submenu)
        
        self.settings_menu.addSeparator()
        
        # 4. Plugins
        self.settings_menu.addAction("🔌 Manage Plugins").triggered.connect(self.open_plugins)
        
        self.settings_menu.addSeparator()
        
        # 5. History
        history_menu = self.settings_menu.addMenu("📜 History Management")
        history_menu.addAction("Backup History").triggered.connect(self.backup_history)
        history_menu.addAction("Restore History").triggered.connect(self.restore_history)
        
        # Attach menu to button
        self.header.btn_settings.setMenu(self.settings_menu)

    def _populate_conductor_menu(self, menu: QMenu) -> None:
        """Populates a QMenu with conductor commands."""
        menu.clear()
        commands = self.conductor_manager.get_available_commands()
        if not commands:
            action = menu.addAction("No commands found")
            action.setEnabled(False)
            return
            
        for cmd in commands:
            action = menu.addAction(cmd.capitalize())
            action.triggered.connect(lambda checked, c=cmd: self.run_conductor_command(c))

    def toggle_terminal(self) -> None:
        """Toggles the visibility of the terminal dock."""
        if self.terminal_dock.isVisible():
            self.terminal_dock.hide()
        else:
            self.terminal_dock.show()

    def on_terminal_visibility_changed(self, visible: bool) -> None:
        """Updates the terminal button state when dock visibility changes."""
        self.header.btn_terminal.setChecked(visible)

    def refresh_index(self) -> None:
        """Refreshes the project index for symbol browsing in a background thread."""
        def _bg_index():
            self.indexer.index_project()
            # Use QMetaObject to safely update UI from background thread
            QMetaObject.invokeMethod(self.symbol_browser, "set_symbols", 
                                     Qt.ConnectionType.QueuedConnection, 
                                     Q_ARG(list, self.indexer.get_all_symbols()))

        threading.Thread(target=_bg_index, daemon=True).start()

    def on_symbol_selected(self, symbol: Any) -> None:
        """Handles symbol selection from the symbol browser."""
        full_path = os.path.join(self.indexer.root_dir, symbol.file_path)
        self.add_attachment(full_path)
        QMessageBox.information(self, "Symbol Selected", f"Attached {symbol.file_path}\nSymbol: {symbol.name} (line {symbol.line})")

    def run_conductor_command(self, command_name: str) -> None:
        """Executes a specific conductor command."""
        prompt = f"Execute Conductor command: {command_name}"
        system_instruction = self.conductor_manager.get_command_prompt(command_name)
        
        if not system_instruction:
            QMessageBox.warning(self, "Error", f"Command {command_name} not found.")
            return

        self.create_new_session()
        self.session_manager.update_session_title(self.session_manager.current_session_id, f"Conductor: {command_name}")
        self.update_sidebar()
        
        self._start_worker(prompt, system_instruction_override=system_instruction)

    def toggle_sidebar(self) -> None:
        """Toggles the visibility of the sidebar."""
        is_visible = self.sidebar_container.isVisible()
        self.sidebar_container.setVisible(not is_visible)
        self.header.btn_toggle_sidebar.setText("≡" if is_visible else "✕")

    def show_attach_menu(self) -> None:
        """Shows the attachment menu."""
        menu = QMenu(self)
        menu.addAction("Attach Files").triggered.connect(self.attach_files_dialog)
        menu.addAction("Attach Folder").triggered.connect(self.attach_folder_dialog)
        menu.exec(self.btn_file.mapToGlobal(self.btn_file.rect().topLeft()))

    def attach_files_dialog(self) -> None:
        """Opens a dialog to select files for attachment."""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*)")
        if files: 
            for f in files:
                self.add_attachment(f)

    def attach_folder_dialog(self) -> None:
        """Opens a dialog to select a folder for attachment."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.add_attachment(folder)

    def add_attachment(self, path: str) -> None:
        """Adds a file or folder to the current session's attachments."""
        self.attachment_manager.add_attachment(path)
        self._update_attachment_ui()

    def remove_attachment(self, path: str) -> None:
        """Removes an attachment from the current session."""
        if path in self.attachment_manager.attachments:
            self.attachment_manager.attachments.remove(path)
            self._update_attachment_ui()

    def _update_attachment_ui(self) -> None:
        """Updates the attachment list UI."""
        # Clear current list
        while self.attachment_list_layout.count():
            child = self.attachment_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            
        # Add items
        attachments = self.attachment_manager.get_attachments()
        # Limit display to first 5 to avoid clutter
        for path in attachments[:5]:
            item = AttachmentItem(path, self.app_config.theme)
            item.remove_requested.connect(self.remove_attachment)
            self.attachment_list_layout.addWidget(item)
            
        if len(attachments) > 5:
            more_lbl = QLabel(f"+{len(attachments) - 5} more")
            more_lbl.setStyleSheet("color: #888; font-size: 11px;")
            self.attachment_list_layout.addWidget(more_lbl)

    def apply_theme(self) -> None:
        """Applies the current theme to the entire application."""
        theme = self.app_config.theme
        self.theme_manager.apply_theme(theme)
        
        # Custom styling for specific buttons that don't follow palette perfectly
        btn_style = """
            QPushButton { 
                background-color: transparent; 
                border: 1px solid %s; 
                border-radius: 8px; 
                color: %s; 
                font-size: 20px;
            }
            QPushButton:hover { background-color: %s; }
        """
        if theme == Theme.DARK.value:
            self.header.btn_toggle_sidebar.setStyleSheet(btn_style % ("#555", "#888", "#333"))
            self.header.btn_settings.setStyleSheet("QPushButton { background-color: transparent; border: 1px solid #555; border-radius: 4px; color: #888; } QPushButton:hover { background-color: #333; color: #EEE; }")
        else:
            self.header.btn_toggle_sidebar.setStyleSheet(btn_style % ("#CCC", "#555", "#EEE"))
            self.header.btn_settings.setStyleSheet("QPushButton { background-color: transparent; border: 1px solid #CCC; border-radius: 4px; color: #555; } QPushButton:hover { background-color: #F0F0F0; color: #000; }")

        self.project_explorer.apply_theme(theme)
        self._update_attachment_ui()

        if self.session_manager.current_session_id: 
            self.load_session_from_list(None) # Reload current session UI

    def create_new_session(self) -> None:
        """Creates a new chat session."""
        # Use global default model for new sessions
        config = {"model": self.app_config.model}
        self.session_manager.create_session(config=config)
        self.clear_chat_ui()
        self.attachment_manager.clear_attachments()
        self._update_attachment_ui()
        self.update_sidebar()
        
        self._refresh_usage_display()

    def update_sidebar(self) -> None:
        """Updates the sidebar with the latest session list."""
        self.sidebar.populate_sessions(
            self.session_manager.get_all_sessions(), 
            self.session_manager.current_session_id
        )

    def load_session_from_list(self, item: Optional[QListWidgetItem]) -> None:
        """Loads a session from the sidebar list."""
        session_id = None
        if item:
            session_id = item.data(Qt.ItemDataRole.UserRole)
        else:
            session_id = self.session_manager.current_session_id
            
        if not session_id:
            return 
        
        self.session_manager.current_session_id = session_id
        
        self.clear_chat_ui()
        session_data = self.session_manager.get_session(session_id)
        if session_data:
            messages = session_data.get("messages", [])
            # Limit to last 50 messages for performance
            display_messages = messages[-50:] if len(messages) > 50 else messages
            
            if len(messages) > 50:
                info_lbl = QLabel(f"Showing last 50 of {len(messages)} messages.")
                info_lbl.setStyleSheet("color: #888; font-style: italic; margin-left: 50px;")
                self.messages_layout.addWidget(info_lbl)

            for msg in display_messages:
                self.messages_layout.addWidget(MessageBubble(msg['text'], is_user=(msg['role'] == Role.USER.value), theme_mode=self.app_config.theme))
            
            self._refresh_usage_display()
            
        self.scroll_to_bottom()

    def clear_chat_ui(self) -> None:
        """Clears all message bubbles from the chat area."""
        while self.messages_layout.count():
            child = self.messages_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.status_widget = None

    def show_context_menu(self, pos: Qt.AlignmentFlag) -> None:
        """Shows the context menu for a session in the sidebar."""
        item = self.sidebar.chat_list.itemAt(pos)
        if not item:
            return
        if not item.data(Qt.ItemDataRole.UserRole):
            return
        
        menu = QMenu()
        menu.addAction("Rename").triggered.connect(lambda: self.rename_session(item))
        menu.addAction("Export to Markdown").triggered.connect(lambda: self.export_session_to_markdown(item))
        menu.addSeparator()
        menu.addAction("Delete").triggered.connect(lambda: self.delete_session(item))
        menu.exec(self.sidebar.chat_list.mapToGlobal(pos))

    def delete_session(self, item: QListWidgetItem) -> None:
        """Deletes a session."""
        sess_id = item.data(Qt.ItemDataRole.UserRole)
        if self.session_manager.delete_session(sess_id):
            self.update_sidebar()
            if not self.session_manager.current_session_id: 
                self.create_new_session()

    def rename_session(self, item: QListWidgetItem) -> None:
        """Renames a session."""
        sess_id = item.data(Qt.ItemDataRole.UserRole)
        current_name = item.text().strip()
        new_name, ok = QInputDialog.getText(self, "Rename", "Chat Title:", text=current_name)
        if ok and new_name:
            self.session_manager.update_session_title(sess_id, new_name)
            self.update_sidebar()


    def export_session_to_markdown(self, item: QListWidgetItem) -> None:
        """Exports a session to a Markdown file."""
        sess_id = item.data(Qt.ItemDataRole.UserRole)
        session_data = self.session_manager.get_session(sess_id)
        if not session_data:
            return

        safe_title = "".join([c for c in session_data.get("title", "session") if c.isalnum() or c in (' ', '_')]).rstrip()
        default_name = f"{safe_title}.md"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Session", default_name, "Markdown Files (*.md)")
        
        if file_path:
            if Exporter.export_to_file(session_data, Path(file_path)):
                QMessageBox.information(self, "Export Successful", f"Session exported to {file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export session.")

    def backup_history(self) -> None:
        """Creates a backup of all chat history."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Backup History", "conductor_backup.zip", "ZIP Files (*.zip)")
        if file_path:
            if Exporter.create_backup(self.session_manager.get_all_sessions(), Path(file_path)):
                QMessageBox.information(self, "Backup Successful", f"History backed up to {file_path}")
            else:
                QMessageBox.critical(self, "Backup Failed", "Failed to create backup.")

    def restore_history(self) -> None:
        """Restores chat history from a backup file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Restore History", "", "ZIP Files (*.zip)")
        if file_path:
            sessions = Exporter.restore_backup(Path(file_path))
            if sessions:
                reply = QMessageBox.question(self, "Restore History", 
                                           "This will replace your current history. Continue?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.session_manager.sessions = sessions
                    self.session_manager.save_history()
                    self.update_sidebar()
                    self.create_new_session()
                    QMessageBox.information(self, "Restore Successful", "History restored successfully.")
            else:
                QMessageBox.critical(self, "Restore Failed", "Failed to restore backup or backup is empty.")

    def open_settings(self) -> None:
        """Opens the settings dialog."""
        settings_dialog = SettingsDialog(self, self.app_config._config)
        settings_dialog.exec()
        self.app_config.save()
        self.header.set_mode(self.app_config.get("use_search", False))
        self.apply_theme()

    def open_conductor(self) -> None:
        """Opens the conductor orchestrator dialog."""
        dialog = ConductorDialog(self, self.conductor_manager)
        dialog.exec()

    def open_plugins(self) -> None:
        """Opens the plugin management dialog."""
        dialog = PluginDialog(self.plugin_manager, self, self.app_config.theme)
        dialog.exec()

    def send_message(self) -> None:
        """Sends the user message to the AI model."""
        prompt = self.input_field.toPlainText().strip()
        if not prompt and not self.attachment_manager.get_attachments():
            return
        self._start_worker(prompt)
        self.input_field.clear()

    def _start_worker(self, prompt: str, system_instruction_override: Optional[str] = None) -> None:
        """Starts the Gemini worker to process the user request."""
        attachments = self.attachment_manager.get_attachments()
        
        display_text = prompt + (f" [Files: {len(attachments)}]" if attachments else "")
        self.messages_layout.addWidget(MessageBubble(display_text, is_user=True, theme_mode=self.app_config.theme))
        self.scroll_to_bottom()

        self.status_widget = StatusWidget()
        self.status_widget.set_status("Gemini is thinking...")
        self.status_widget.start_loading()
        self.messages_layout.addWidget(self.status_widget)

        self.controller.send_message(prompt, system_instruction_override)

    def on_terminal_output(self, text: str, output_type: str) -> None:
        """Handles terminal output from the worker."""
        if output_type == "error":
            self.terminal.append_error(text)
        elif output_type == "success":
            self.terminal.append_success(text)
        elif output_type == "info":
            self.terminal.append_info(text)
        else:
            self.terminal.append_text(text)

    def show_tool_confirmation(self, tool_name: str, args: dict, confirmation_id: str) -> None:
        """Shows a confirmation dialog for dangerous tool execution."""
        dialog = DeepReviewDialog(tool_name, args, parent=self, theme_mode=self.app_config.theme)
        result = dialog.exec()
        allowed = (result == QDialog.DialogCode.Accepted)
        # Pass modified args if approved
        modified_args = dialog.get_args() if allowed else None
        self.controller.confirm_tool(confirmation_id, allowed, modified_args)

    def on_response_success(self, text: str) -> None:
        """Handles successful AI response."""
        if self.status_widget:
            self.status_widget.stop_loading()
            self.status_widget.deleteLater()
            self.status_widget = None
            
        self.messages_layout.addWidget(MessageBubble(text, is_user=False, theme_mode=self.app_config.theme))
        self.scroll_to_bottom()
        
        self._update_attachment_ui()

    def on_response_error(self, err: str) -> None:
        """Handles AI response error."""
        if self.status_widget:
            self.status_widget.stop_loading()
            self.status_widget.deleteLater()
            self.status_widget = None
            
        self.messages_layout.addWidget(MessageBubble(f"**Error:** {err}", is_user=False, theme_mode=self.app_config.theme))
        self.scroll_to_bottom()

    def on_status_update(self, status_message: str) -> None:
        """Updates the status widget with the latest worker status."""
        if self.status_widget:
            try:
                self.status_widget.set_status(status_message)
            except RuntimeError:
                # Handle case where C++ object is deleted but Python reference remains
                self.status_widget = None

    def on_usage_updated(self, session_id: str, input_tokens: int, output_tokens: int) -> None:
        """Updates the session usage data."""
        self.session_manager.update_session_usage(session_id, input_tokens, output_tokens)
        if session_id == self.session_manager.current_session_id:
            self._refresh_usage_display()

    def _refresh_usage_display(self) -> None:
        """Refreshes the usage display in the header."""
        session_id = self.session_manager.current_session_id
        if not session_id:
            return
            
        session_data = self.session_manager.get_session(session_id)
        if not session_data:
            return
            
        usage = session_data.get("usage", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        
        # Calculate cost
        sess_config = session_data.get("config", {})
        model_id = sess_config.get("model", self.app_config.model)
        
        pricing = ModelRegistry.MODEL_PRICING.get(model_id, (0.0, 0.0))
        input_cost = (usage["input_tokens"] / 1_000_000) * pricing[0]
        output_cost = (usage["output_tokens"] / 1_000_000) * pricing[1]
        total_cost = input_cost + output_cost
        
        self.header.update_usage(usage["total_tokens"], total_cost)

    def scroll_to_bottom(self) -> None:
        """Scrolls the chat area to the bottom."""
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def closeEvent(self, event: Any) -> None:
        """Handles the window close event."""
        self.controller.stop_worker()
        self.attachment_manager.cleanup()
        event.accept()

def main():
    setup_logging()
    app = QApplication(sys.argv)
    
    # Initialize services (Dependency Injection)
    config = AppConfig()
    theme_mgr = ThemeManager(app)
    session_mgr = SessionManager(AppConfig.HISTORY_FILE)
    attachment_mgr = AttachmentManager()
    conductor_mgr = ConductorManager(extension_path=config.conductor_path)
    indexer = Indexer(root_dir=".")
    plugin_mgr = PluginManager()
    plugin_mgr.discover_plugins()
    checkpoint_mgr = CheckpointManager()
    
    # Inject into main window
    window = GeminiBrowser(
        config, theme_mgr, session_mgr, attachment_mgr, 
        conductor_mgr, indexer, plugin_mgr, checkpoint_mgr
    )
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
