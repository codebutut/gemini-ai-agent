import json
import logging
import uuid
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class SessionManager:
    """
    Manages chat sessions, including loading, saving, and creating new sessions.
    """
    def __init__(self, history_file: Path):
        self.history_file = history_file
        self._lock = threading.RLock() # Use RLock to prevent deadlocks
        self.sessions: Dict[str, Any] = self._load_history()
        self.current_session_id: Optional[str] = None
        
        self._save_timer: Optional[threading.Timer] = None
        self._last_save_time = 0
        self._save_interval = 2.0 # Minimum seconds between saves

    def _load_history(self) -> Dict[str, Any]:
        """Loads chat history from JSON file."""
        if not self.history_file.exists():
            return {}
        try:
            with self.history_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logging.error(f"Failed to load history: {e}")
            return {}

    def save_history(self, sync: bool = False) -> None:
        """Saves current sessions to JSON file with throttling."""
        if sync:
            self._perform_save()
            return

        with self._lock:
            if self._save_timer is not None:
                return # Already scheduled

            now = time.time()
            elapsed = now - self._last_save_time
            if elapsed >= self._save_interval:
                # Run in a separate thread to avoid blocking the caller
                threading.Thread(target=self._perform_save_async, daemon=True).start()
            else:
                delay = self._save_interval - elapsed
                self._save_timer = threading.Timer(delay, self._perform_save_async)
                self._save_timer.daemon = True
                self._save_timer.start()

    def _perform_save_async(self) -> None:
        with self._lock:
            self._save_timer = None
            self._perform_save()

    def _perform_save(self) -> None:
        """Performs the actual save operation."""
        try:
            with self._lock:
                # Serialize to string while holding the lock to ensure consistency
                # This is much faster than json.loads(json.dumps(self.sessions))
                data_str = json.dumps(self.sessions, indent=4, ensure_ascii=False)
                self._last_save_time = time.time()

            # Write to file outside the lock to avoid blocking other threads during I/O
            with self.history_file.open("w", encoding="utf-8") as f:
                f.write(data_str)
        except Exception as e:
            logging.error(f"Failed to save history: {e}")

    def create_session(self, title: str = "New Chat", config: Optional[Dict[str, Any]] = None, sync: bool = False) -> str:
        """Creates a new session and returns its ID."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "title": title,
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "plan": "",
            "specs": "",
            "config": config or {},
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        }
        self.current_session_id = session_id
        self.save_history(sync=sync)
        return session_id

    def delete_session(self, session_id: str, sync: bool = False) -> bool:
        """Deletes a session by ID."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.save_history(sync=sync)
            if self.current_session_id == session_id:
                self.current_session_id = None
            return True
        return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Returns session data."""
        return self.sessions.get(session_id)

    def get_all_sessions(self) -> Dict[str, Any]:
        """Returns all sessions."""
        return self.sessions

    def _update_session_field(self, session_id: str, field: str, value: Any, sync: bool = False) -> None:
        """Generic method to update a session field."""
        if session_id in self.sessions:
            self.sessions[session_id][field] = value
            self.save_history(sync=sync)

    def add_message(self, session_id: str, role: str, text: str, images: Optional[List[str]] = None, sync: bool = False) -> None:
        """Adds a message to a session."""
        if session_id not in self.sessions:
            return
        
        message = {
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        if images:
            message["images"] = images
            
        self.sessions[session_id]["messages"].append(message)
        self.save_history(sync=sync)

    def update_session_title(self, session_id: str, new_title: str, sync: bool = False) -> None:
        """Updates the title of a session."""
        self._update_session_field(session_id, "title", new_title, sync)

    def update_session_plan(self, session_id: str, plan: str, sync: bool = False) -> None:
        """Updates the plan of a session."""
        self._update_session_field(session_id, "plan", plan, sync)

    def update_session_specs(self, session_id: str, specs: str, sync: bool = False) -> None:
        """Updates the specs of a session."""
        self._update_session_field(session_id, "specs", specs, sync)

    def update_session_config(self, session_id: str, config: Dict[str, Any], sync: bool = False) -> None:
        """Updates the configuration overrides for a session."""
        if session_id in self.sessions:
            if "config" not in self.sessions[session_id]:
                self.sessions[session_id]["config"] = {}
            self.sessions[session_id]["config"].update(config)
            self.save_history(sync=sync)

    def update_session_usage(self, session_id: str, input_tokens: int, output_tokens: int, sync: bool = False) -> None:
        """Updates the cumulative token usage for a session."""
        if session_id in self.sessions:
            if "usage" not in self.sessions[session_id]:
                self.sessions[session_id]["usage"] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            
            usage = self.sessions[session_id]["usage"]
            usage["input_tokens"] += input_tokens
            usage["output_tokens"] += output_tokens
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
            self.save_history(sync=sync)

    def clear_current_session(self, sync: bool = False) -> None:
        """Clears messages, plan, and specs in the current session."""
        if self.current_session_id and self.current_session_id in self.sessions:
            session = self.sessions[self.current_session_id]
            session["messages"] = []
            session["plan"] = ""
            session["specs"] = ""
            self.save_history(sync=sync)
