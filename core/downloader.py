import os
import asyncio
import hashlib
import time
import mimetypes
from typing import List, Optional, Callable, Dict
import httpx
from rich.progress import (
    Progress, BarColumn, TextColumn, TransferSpeedColumn,
    TimeRemainingColumn, DownloadColumn, TaskID, MofNCompleteColumn
)
from core.models import MediaItem
from core.extractor import DEFAULT_HEADERS

# Map MIME types to file extensions for Content-Type validation
MIME_TO_EXT: Dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/svg+xml": ".svg",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
    "video/x-msvideo": ".avi",
    "video/quicktime": ".mov",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "application/pdf": ".pdf",
}

VALID_MEDIA_MIMES = set(MIME_TO_EXT.keys()) | {
    # broader groups
    "application/octet-stream",  # allow through; let extension decide
}


def resolve_extension_from_mime(content_type: str, current_ext: str) -> Optional[str]:
    """
    Given a Content-Type header (e.g. 'image/webp; charset=...') and the
    current file extension, return the correct extension to use.
    Returns None if the MIME type is clearly not a media file (e.g. text/html).
    """
    if not content_type:
        return current_ext  # keep as-is if unknown

    mime = content_type.split(";")[0].strip().lower()

    if mime == "application/octet-stream":
        # Ambiguous; trust the URL extension
        return current_ext

    if mime.startswith(("image/", "video/", "audio/", "application/pdf")):
        # Valid media: return the proper extension
        return MIME_TO_EXT.get(mime, current_ext)

def sniff_ext_from_magic(filepath: str) -> Optional[str]:
    """Read magic bytes and return the true image extension, or None if unknown."""
    try:
        with open(filepath, "rb") as f:
            head = f.read(16)
    except OSError:
        return None
    if head[0:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head[0:3] == b"\xff\xd8\xff":
        return ".jpg"
    if head[0:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if head[0:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if head[0:2] == b"BM":
        return ".bmp"
    return None

def _move_to_ext_dir(dest_path: str, old_ext: str, new_ext: str) -> str:
    """
    Relocate dest_path into the sibling <new_ext> folder when it currently
    sits in the <old_ext> folder (layout: <type>/<ext>/file). Falls back to
    a plain extension swap otherwise. Creates the target dir if needed.
    """
    parent = os.path.dirname(dest_path)
    stem = os.path.splitext(os.path.basename(dest_path))[0]
    if os.path.basename(parent).lower() == old_ext.lstrip(".").lower():
        new_dir = os.path.join(os.path.dirname(parent), new_ext.lstrip(".").lower())
        os.makedirs(new_dir, exist_ok=True)
        return os.path.join(new_dir, stem + new_ext)
    return os.path.join(parent, stem + new_ext)

def compute_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def is_duplicate_content(filepath: str, seen_hashes: set) -> bool:
    """Check if file hash has already been seen; if not, add to seen_hashes."""
    f_hash = compute_file_hash(filepath)
    if f_hash in seen_hashes:
        return True
    seen_hashes.add(f_hash)
    return False


class MediaDownloader:
    def __init__(
        self,
        concurrency: int = 6,
        timeout: float = 30.0,
        min_size_bytes: int = 0,
        min_width: int = 0,
        min_height: int = 0,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        overwrite: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.5,   # seconds; doubles each attempt (exponential backoff)
    ):
        self.concurrency = concurrency
        self.timeout = timeout
        self.min_size_bytes = min_size_bytes
        self.min_width = min_width
        self.min_height = min_height
        self.headers = headers or DEFAULT_HEADERS
        self.cookies = cookies or {}
        self.overwrite = overwrite
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.seen_content_hashes: set = set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _should_skip_existing(self, dest_path: str) -> bool:
        return (
            not self.overwrite
            and os.path.exists(dest_path)
            and os.path.getsize(dest_path) > 0
        )

    async def _attempt_download(
        self,
        client: httpx.AsyncClient,
        item: MediaItem,
        dest_path: str,
        headers: dict,
    ) -> Optional[MediaItem]:
        """
        Try to download *item* to *dest_path* with the given headers.
        Returns the populated MediaItem on success, or None to signal a
        retryable failure (403/401/429/network error).
        Raises ValueError for permanent failures (wrong Content-Type, too small).
        """
        async with client.stream("GET", item.url, headers=headers, timeout=self.timeout) as response:
            status = response.status_code

            # Retryable auth / rate-limit errors
            if status in (401, 403, 429):
                return None

            # Hard HTTP failure → permanent fail, no retry
            if status >= 400:
                item.download_status = "failed"
                item.error_message = f"HTTP {status}"
                return item

            # --- Content-Type check ---
            raw_ct = response.headers.get("content-type", "")
            correct_ext = resolve_extension_from_mime(raw_ct, item.extension or "")
            if correct_ext is None:
                # Server returned HTML/JSON/etc. — not a real media file
                item.download_status = "skipped"
                item.error_message = f"Non-media Content-Type: {raw_ct.split(';')[0]}"
                return item

            # Fix extension mismatch (e.g. URL says .jpg but server says image/webp)
            if correct_ext and correct_ext != item.extension:
                dest_path = _move_to_ext_dir(dest_path, item.extension, correct_ext)
                item.extension = correct_ext

            # --- Content-Length pre-check ---
            content_length = response.headers.get("content-length")
            if content_length:
                if self.min_size_bytes > 0 and int(content_length) < self.min_size_bytes:
                    item.download_status = "skipped"
                    item.error_message = f"Size {content_length}B < min {self.min_size_bytes}B"
                    return item

            # --- Stream to temp file ---
            temp_path = dest_path + ".tmp"
            hasher = hashlib.sha256()
            downloaded_size = 0

            try:
                with open(temp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                            hasher.update(chunk)
                            downloaded_size += len(chunk)
            except Exception:
                _safe_remove(temp_path)
                raise

            # --- Actual-size check ---
            if self.min_size_bytes > 0 and downloaded_size < self.min_size_bytes:
                _safe_remove(temp_path)
                item.download_status = "skipped"
                item.error_message = f"Size {downloaded_size}B < min {self.min_size_bytes}B"
                return item

            # --- Magic-byte extension fix (server may mislabel Content-Type) ---
            sniffed = sniff_ext_from_magic(temp_path)
            if sniffed and sniffed != (item.extension or "").lower():
                new_dest = _move_to_ext_dir(dest_path, item.extension or "", sniffed)
                new_temp = new_dest + ".tmp"
                os.rename(temp_path, new_temp)
                temp_path = new_temp
                dest_path = new_dest
                item.extension = sniffed

            # --- Deduplication by content hash ---
            content_hash = hasher.hexdigest()
            if content_hash in self.seen_content_hashes:
                _safe_remove(temp_path)
                item.download_status = "skipped"
                item.error_message = "Duplicate content"
                return item

            self.seen_content_hashes.add(content_hash)

            # --- Image Resolution Filter ---
            if self.min_width > 0 or self.min_height > 0:
                if item.extension.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.avif', '.tiff'):
                    try:
                        from PIL import Image
                        with Image.open(temp_path) as img:
                            w, h = img.size
                        if (self.min_width > 0 and w < self.min_width) or \
                           (self.min_height > 0 and h < self.min_height):
                            _safe_remove(temp_path)
                            item.download_status = "skipped"
                            item.error_message = f"Resolution {w}x{h} < min {self.min_width}x{self.min_height}"
                            return item
                        item.width = w
                        item.height = h
                    except Exception:
                        pass  # Non-image or corrupt — let it through

            # --- Commit ---
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(temp_path, dest_path)

            item.download_status = "success"
            item.saved_path = dest_path
            item.file_size = downloaded_size
            return item

    async def _download_single(
        self,
        client: httpx.AsyncClient,
        item: MediaItem,
        dest_path: str,
        progress: Progress,
        task_id: TaskID,
    ) -> MediaItem:
        short_name = item.original_filename[:28]

        # --- Skip if file already present ---
        if self._should_skip_existing(dest_path):
            item.download_status = "skipped"
            item.saved_path = dest_path
            item.file_size = os.path.getsize(dest_path)
            item.error_message = "File already exists"
            progress.update(task_id, description=f"[yellow]Exists  [/] {short_name}", advance=1)
            return item

        # --- Build list of User-Agents to try ---
        ua_candidates = [
            self.headers.get("User-Agent"),
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "MediaHarvester/1.1 (+https://github.com/ertyu007/media-harvester)",
            "curl/8.7.1",
        ]
        ua_candidates = [u for u in ua_candidates if u]  # drop Nones

        last_error = "Download failed"
        delay = self.retry_delay

        for attempt in range(self.max_retries):
            for ua in ua_candidates:
                req_headers = {**self.headers, "User-Agent": ua}
                if item.source_page_url:
                    req_headers["Referer"] = item.source_page_url

                try:
                    result = await self._attempt_download(client, item, dest_path, req_headers)

                    if result is not None:
                        # Either success, permanent-fail, or intentional skip
                        status_map = {
                            "success": f"[green]Done    [/] {short_name}",
                            "skipped": f"[yellow]Skipped [/] {short_name}",
                            "failed":  f"[red]Failed  [/] {short_name}",
                        }
                        progress.update(
                            task_id,
                            description=status_map.get(result.download_status, short_name),
                            advance=1,
                        )
                        return result

                    # result is None → retryable (403/401/429)
                    last_error = f"HTTP 403/401/429 (attempt {attempt + 1})"

                except Exception as e:
                    last_error = str(e)
                    _safe_remove(dest_path + ".tmp")

            # --- Exponential backoff before next attempt ---
            if attempt < self.max_retries - 1:
                progress.update(task_id, description=f"[dim]Retry {attempt + 2}/{self.max_retries}[/] {short_name}")
                await asyncio.sleep(delay)
                delay *= 2  # exponential backoff

        item.download_status = "failed"
        item.error_message = last_error
        progress.update(task_id, description=f"[red]Failed  [/] {short_name}", advance=1)
        return item

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def download_all(
        self,
        items: List[MediaItem],
        get_dest_path_fn: Callable[[MediaItem, int], str],
    ) -> List[MediaItem]:
        if not items:
            return []

        limits = httpx.Limits(
            max_keepalive_connections=self.concurrency,
            max_connections=self.concurrency * 2,
        )
        semaphore = asyncio.Semaphore(self.concurrency)

        with Progress(
            TextColumn("[bold cyan]{task.description:<35}"),
            BarColumn(bar_width=36),
            MofNCompleteColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            overall = progress.add_task(
                f"[bold]Downloading {len(items)} files…", total=len(items)
            )

            async with httpx.AsyncClient(
                limits=limits,
                follow_redirects=True,
                timeout=self.timeout,
                cookies=self.cookies,
            ) as client:

                async def worker(item: MediaItem, idx: int):
                    async with semaphore:
                        dest_path = get_dest_path_fn(item, idx)
                        result = await self._download_single(
                            client, item, dest_path, progress, overall
                        )
                        return result

                tasks = [worker(item, i + 1) for i, item in enumerate(items)]
                results = await asyncio.gather(*tasks)

        return list(results)

    def run_download(
        self,
        items: List[MediaItem],
        get_dest_path_fn: Callable[[MediaItem, int], str],
    ) -> List[MediaItem]:
        return asyncio.run(self.download_all(items, get_dest_path_fn))


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def load_cookies_file(cookie_file: str) -> dict:
    """
    Load a Netscape-format cookies.txt file and return a dict of {name: value}.
    Lines starting with '#' or empty lines are skipped.
    Fields: domain, flag, path, secure, expiry, name, value
    """
    cookies: dict = {}
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#HttpOnly_'):
                    line = line[len('#HttpOnly_'):]
                elif line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    name, value = parts[5], parts[6]
                    cookies[name] = value
    except Exception:
        pass
    return cookies

