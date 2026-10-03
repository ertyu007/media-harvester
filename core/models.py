from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

class MediaType(str, Enum):
    IMAGE = "images"
    VIDEO = "videos"
    AUDIO = "audio"
    DOCUMENT = "documents"
    OTHER = "other"

@dataclass
class MediaItem:
    url: str
    media_type: MediaType
    source_tag: str
    original_filename: str
    extension: str
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    estimated_size: Optional[int] = None
    source_page_url: str = ""
    download_status: str = "pending" # pending, success, failed, skipped
    saved_path: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None

@dataclass
class ScrapeResult:
    source_url: str
    title: str
    items: List[MediaItem] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
