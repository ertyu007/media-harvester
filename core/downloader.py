import os
import asyncio
import hashlib
from typing import List, Optional, Callable
import httpx
from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn, DownloadColumn
from core.models import MediaItem
from core.extractor import DEFAULT_HEADERS

class MediaDownloader:
    def __init__(
        self,
        concurrency: int = 6,
        timeout: float = 25.0,
        min_size_bytes: int = 0,
        headers: Optional[dict] = None,
        overwrite: bool = False
    ):
        self.concurrency = concurrency
        self.timeout = timeout
        self.min_size_bytes = min_size_bytes
        self.headers = headers or DEFAULT_HEADERS
        self.overwrite = overwrite
        self.seen_content_hashes = set()

    async def _download_single(
        self,
        client: httpx.AsyncClient,
        item: MediaItem,
        dest_path: str,
        progress: Progress,
        task_id: int
    ) -> MediaItem:
        # Check if file already exists on disk and is not empty
        if not self.overwrite and os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            item.download_status = "skipped"
            item.saved_path = dest_path
            item.file_size = os.path.getsize(dest_path)
            item.error_message = "File already exists"
            progress.update(task_id, description=f"[yellow]Exists[/yellow] {item.original_filename[:20]}", advance=1)
            return item

        req_headers = dict(self.headers)
        if item.source_page_url:
            req_headers["Referer"] = item.source_page_url

        ua_candidates = [
            req_headers.get("User-Agent"),
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "MediaHarvester/1.0 (https://github.com/user/media-harvester; contact@example.com)",
            "curl/8.7.1"
        ]

        last_error = ""
        for ua in ua_candidates:
            if not ua:
                continue
            req_headers["User-Agent"] = ua
            try:
                async with client.stream("GET", item.url, headers=req_headers, timeout=self.timeout) as response:
                    if response.status_code in [401, 403]:
                        last_error = f"HTTP {response.status_code}"
                        continue
                    if response.status_code >= 400:
                        item.download_status = "failed"
                        item.error_message = f"HTTP {response.status_code}"
                        progress.update(task_id, description=f"[red]Failed ({response.status_code})[/red] {item.original_filename[:20]}", advance=1)
                        return item
                    
                    # Check Content-Length if available
                    content_length = response.headers.get("Content-Length")
                    if content_length:
                        total_bytes = int(content_length)
                        if self.min_size_bytes > 0 and total_bytes < self.min_size_bytes:
                            item.download_status = "skipped"
                            item.error_message = f"Size {total_bytes}B < min {self.min_size_bytes}B"
                            progress.update(task_id, description=f"[yellow]Skipped (small)[/yellow] {item.original_filename[:20]}", advance=1)
                            return item

                    # Stream to temp file
                    temp_path = dest_path + ".tmp"
                    hasher = hashlib.sha256()
                    downloaded_size = 0

                    with open(temp_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=16384):
                            if chunk:
                                f.write(chunk)
                                hasher.update(chunk)
                                downloaded_size += len(chunk)

                    # Check actual downloaded size
                    if self.min_size_bytes > 0 and downloaded_size < self.min_size_bytes:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        item.download_status = "skipped"
                        item.error_message = f"Size {downloaded_size}B < min {self.min_size_bytes}B"
                        progress.update(task_id, description=f"[yellow]Skipped (too small)[/yellow] {item.original_filename[:20]}", advance=1)
                        return item

                    # Deduplicate by file content hash
                    content_hash = hasher.hexdigest()
                    if content_hash in self.seen_content_hashes:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        item.download_status = "skipped"
                        item.error_message = "Duplicate content detected"
                        progress.update(task_id, description=f"[yellow]Duplicate[/yellow] {item.original_filename[:20]}", advance=1)
                        return item

                    self.seen_content_hashes.add(content_hash)
                    
                    # Rename temp to destination
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    os.rename(temp_path, dest_path)

                    item.download_status = "success"
                    item.saved_path = dest_path
                    item.file_size = downloaded_size
                    progress.update(task_id, description=f"[green]Done[/green] {item.original_filename[:20]}", advance=1)
                    return item

            except Exception as e:
                last_error = str(e)
                if os.path.exists(dest_path + ".tmp"):
                    try:
                        os.remove(dest_path + ".tmp")
                    except OSError:
                        pass
                continue

        item.download_status = "failed"
        item.error_message = last_error or "Download failed"
        progress.update(task_id, description=f"[red]Failed[/red] {item.original_filename[:20]}", advance=1)
        return item

    async def download_all(
        self,
        items: List[MediaItem],
        get_dest_path_fn: Callable[[MediaItem, int], str]
    ) -> List[MediaItem]:
        if not items:
            return []

        limits = httpx.Limits(max_keepalive_connections=self.concurrency, max_connections=self.concurrency * 2)
        semaphore = asyncio.Semaphore(self.concurrency)

        with Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            total_task = progress.add_task(f"Downloading {len(items)} media files...", total=len(items))

            async with httpx.AsyncClient(limits=limits, follow_redirects=True, timeout=self.timeout) as client:
                async def worker(item: MediaItem, idx: int):
                    async with semaphore:
                        dest_path = get_dest_path_fn(item, idx)
                        return await self._download_single(client, item, dest_path, progress, total_task)

                tasks = [worker(item, i + 1) for i, item in enumerate(items)]
                results = await asyncio.gather(*tasks)

        return results

    def run_download(
        self,
        items: List[MediaItem],
        get_dest_path_fn: Callable[[MediaItem, int], str]
    ) -> List[MediaItem]:
        return asyncio.run(self.download_all(items, get_dest_path_fn))
