import json
import zipfile
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class Exporter:
    """
    Handles exporting sessions to Markdown and managing history backups in ZIP format.
    """

    @staticmethod
    def session_to_markdown(session_data: Dict[str, Any]) -> str:
        """
        Converts a single session's data to a Markdown string.

        Args:
            session_data: The session data dictionary.

        Returns:
            str: The session data formatted as Markdown.
        """
        title = session_data.get("title", "Untitled Session")
        created_at = session_data.get("created_at", "Unknown")
        messages = session_data.get("messages", [])
        plan = session_data.get("plan", "")
        specs = session_data.get("specs", "")

        md = f"# {title}\n\n"
        md += f"*Created at: {created_at}*\n\n"

        if plan:
            md += "## Plan\n\n"
            md += f"{plan}\n\n"

        if specs:
            md += "## Specifications\n\n"
            md += f"{specs}\n\n"

        md += "## Chat History\n\n"
        for msg in messages:
            role = msg.get("role", "unknown").capitalize()
            text = msg.get("text", "")
            timestamp = msg.get("timestamp", "")
            
            md += f"### {role} ({timestamp})\n\n"
            md += f"{text}\n\n"
            
            if "images" in msg and msg["images"]:
                md += "**Attachments (Images):**\n"
                for img in msg["images"]:
                    md += f"- {img}\n"
                md += "\n"

        return md

    @staticmethod
    def export_to_file(session_data: Dict[str, Any], filepath: Path) -> bool:
        """
        Exports a session to a Markdown file.

        Args:
            session_data: The session data dictionary.
            filepath: The destination Path.

        Returns:
            bool: True if export was successful, False otherwise.
        """
        try:
            content = Exporter.session_to_markdown(session_data)
            filepath.write_text(content, encoding="utf-8")
            return True
        except OSError as e:
            logger.error(f"Error exporting to file: {e}")
            return False

    @staticmethod
    def create_backup(sessions: Dict[str, Any], backup_path: Path) -> bool:
        """
        Creates a ZIP backup of all sessions, including raw JSON and individual Markdown files.

        Args:
            sessions: Dictionary of all session data.
            backup_path: The destination Path for the ZIP backup.

        Returns:
            bool: True if backup was successful, False otherwise.
        """
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Save the raw JSON
                zipf.writestr("history.json", json.dumps(sessions, indent=4, ensure_ascii=False))
                
                # Save individual markdown files for convenience
                for session_id, session_data in sessions.items():
                    # Sanitize title for filename
                    safe_title = "".join([c for c in session_data.get("title", "session") if c.isalnum() or c in (' ', '_')]).rstrip()
                    safe_title = safe_title.replace(" ", "_")
                    filename = f"sessions/{safe_title}_{session_id[:8]}.md"
                    md_content = Exporter.session_to_markdown(session_data)
                    zipf.writestr(filename, md_content)
            return True
        except (zipfile.BadZipFile, OSError) as e:
            logger.error(f"Error creating backup: {e}")
            return False

    @staticmethod
    def restore_backup(backup_path: Path) -> Dict[str, Any]:
        """
        Restores sessions from a ZIP backup.

        Args:
            backup_path: The Path to the ZIP backup.

        Returns:
            Dict[str, Any]: The restored session data, or an empty dict if it failed.
        """
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                if "history.json" in zipf.namelist():
                    with zipf.open("history.json") as f:
                        return json.load(f)
        except (zipfile.BadZipFile, json.JSONDecodeError, OSError) as e:
            logger.error(f"Error restoring backup: {e}")
        return {}
