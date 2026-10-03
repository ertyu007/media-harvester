import os
import json
import re
import datetime
import urllib.parse
from typing import List, Dict, Any, Optional
from core.models import MediaItem, MediaType, ScrapeResult

def sanitize_filename(filename: str, max_length: int = 120) -> str:
    """Remove invalid filesystem characters and truncate long names."""
    name, ext = os.path.splitext(filename)
    clean_name = re.sub(r'[\\/*?:"<>|]', '_', name).strip()
    clean_name = re.sub(r'\s+', '_', clean_name)
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    if len(clean_name) > max_length:
        clean_name = clean_name[:max_length]
    if not clean_name:
        clean_name = "media"
    return f"{clean_name}{ext}"


def resolve_collision(dest_path: str) -> str:
    """
    If dest_path already exists on disk, append _2, _3, ... before the extension
    until we find a path that does NOT exist.
    e.g.  image.jpg -> image_2.jpg -> image_3.jpg
    """
    if not os.path.exists(dest_path):
        return dest_path

    base, ext = os.path.splitext(dest_path)
    counter = 2
    while True:
        candidate = f"{base}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


class MediaOrganizer:
    def __init__(self, base_output_dir: str = "downloads"):
        self.base_output_dir = base_output_dir
        # Track (media_type_dir, clean_stem) -> counter for in-memory collision avoidance
        # key: (type_dir, stem_lower)  value: next counter to use
        self._name_counters: Dict[str, int] = {}

    def create_destination_structure(
        self,
        source_url: str,
        custom_folder_name: Optional[str] = None,
        use_timestamp: bool = False
    ) -> str:
        parsed = urllib.parse.urlparse(source_url)
        domain = parsed.netloc.replace(":", "_").replace("www.", "")

        if custom_folder_name:
            folder_name = custom_folder_name
        elif use_timestamp:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"{domain}_{timestamp}"
        else:
            folder_name = domain

        target_dir = os.path.join(self.base_output_dir, folder_name)

        # Create subdirectories for each media type
        for m_type in MediaType:
            os.makedirs(os.path.join(target_dir, m_type.value), exist_ok=True)

        return target_dir

    def get_destination_filepath(
        self,
        target_dir: str,
        item: MediaItem,
        index: int = 1,
        prefix_index: bool = False
    ) -> str:
        """
        Return a collision-free destination path for *item* inside *target_dir*.

        Strategy (in order):
          1. Sanitize original filename.
          2. Optionally prefix with zero-padded index (--prefix flag).
          3. Resolve in-memory naming collision (two different URLs that map to
             the same sanitized name within the same session).
          4. Resolve on-disk collision (file written by a previous session).
        """
        clean_name = sanitize_filename(item.original_filename)
        if prefix_index:
            clean_name = f"{index:03d}_{clean_name}"

        ext = os.path.splitext(clean_name)[1].lower().lstrip(".") or "other"
        type_dir = os.path.join(target_dir, item.media_type.value, ext)
        os.makedirs(type_dir, exist_ok=True)
        stem, ext = os.path.splitext(clean_name)

        # --- In-memory dedup key ---
        dedup_key = os.path.join(type_dir, stem.lower() + ext.lower())

        if dedup_key not in self._name_counters:
            # First time seeing this stem: reserve counter=1 (no suffix yet)
            self._name_counters[dedup_key] = 1
            candidate_name = clean_name
        else:
            # Already seen: bump counter and add suffix
            self._name_counters[dedup_key] += 1
            n = self._name_counters[dedup_key]
            candidate_name = f"{stem}_{n}{ext}"

        dest_path = os.path.join(type_dir, candidate_name)

        # --- On-disk dedup (previous sessions) ---
        dest_path = resolve_collision(dest_path)

        return dest_path

    def write_manifest(self, target_dir: str, result: ScrapeResult, downloaded_items: List[MediaItem]):
        manifest_path = os.path.join(target_dir, "manifest.json")
        summary_md_path = os.path.join(target_dir, "summary.md")

        # Load existing manifest if present to merge
        existing_items = []
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    existing_items = old_data.get("items", [])
            except Exception:
                existing_items = []

        seen_paths = set()
        combined_items = []

        # Add new items first
        for item in downloaded_items:
            rel_path = os.path.relpath(item.saved_path, target_dir) if item.saved_path else None
            if rel_path:
                seen_paths.add(rel_path)
            combined_items.append({
                "url": item.url,
                "type": item.media_type.value,
                "status": item.download_status,
                "saved_path": rel_path,
                "file_size": item.file_size,
                "error": item.error_message
            })

        # Append previous unique items
        for old_item in existing_items:
            p = old_item.get("saved_path")
            if p and p not in seen_paths:
                seen_paths.add(p)
                combined_items.append(old_item)

        manifest_data = {
            "source_url": result.source_url,
            "last_updated": datetime.datetime.now().isoformat(),
            "page_title": result.title,
            "total_items": len(combined_items),
            "total_downloaded": len([i for i in combined_items if i.get("status") == "success"]),
            "items": combined_items
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        # Write Markdown summary
        with open(summary_md_path, "w", encoding="utf-8") as f:
            f.write(f"# Media Harvest Report\n\n")
            f.write(f"- **Source URL:** {result.source_url}\n")
            f.write(f"- **Page Title:** {result.title}\n")
            f.write(f"- **Last Updated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Total Saved Files:** {manifest_data['total_downloaded']}\n\n")

            f.write("## Downloaded Media\n\n")
            f.write("| # | Type | Filename | Size (KB) |\n")
            f.write("|---|------|----------|-----------|\n")

            success_list = [i for i in combined_items if i.get("status") == "success"]
            for idx, item_data in enumerate(success_list, 1):
                size_kb = f"{(item_data.get('file_size') or 0) / 1024:.1f}" if item_data.get('file_size') else "N/A"
                f.write(f"| {idx} | {item_data.get('type')} | `{os.path.basename(item_data.get('saved_path') or '')}` | {size_kb} |\n")

    def create_zip_archive(self, target_dir: str, output_zip_path: Optional[str] = None) -> str:
        """
        Compress the target_dir directory into a .zip file.
        Returns the path to the created zip file.
        """
        import zipfile
        if not output_zip_path:
            output_zip_path = f"{target_dir.rstrip(r'\/')}.zip"

        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(target_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, target_dir)
                    zipf.write(full_path, rel_path)

        return output_zip_path
