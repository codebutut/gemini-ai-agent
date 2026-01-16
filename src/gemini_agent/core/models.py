from datetime import datetime
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    text: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    images: Optional[List[str]] = None

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        # Ensure backward compatibility with older Pydantic or specific needs
        return super().model_dump(**kwargs)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class Session(BaseModel):
    title: str = "New Chat"
    messages: List[Message] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    plan: str = ""
    specs: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    usage: Usage = Field(default_factory=Usage)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        return super().model_dump(**kwargs)
