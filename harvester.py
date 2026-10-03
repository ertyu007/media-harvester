#!/usr/bin/env python3
"""
Media Harvester CLI
Universal Media Scraper & High-Speed Batch Downloader
"""

import sys
import os
import re
import json
import urllib.parse
from typing import List, Optional, Set

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box

from core.extractor import MediaExtractor
from core.organizer import MediaOrganizer
from core.downloader import MediaDownloader, load_cookies_file
from core.models import MediaItem, MediaType, ScrapeResult

console = Console()

BANNER = r"""[bold cyan]
  __  __          _ _         _   _                               _            
 |  \/  |        | (_)       | | | |                             | |           
 | \  / | ___  __| |_  __ _  | |_| | __ _ _ ____   _____  ___ ___| |_ ___ _ __ 
 | |\/| |/ _ \/ _` | |/ _` | |  _  |/ _` | '__\ \ / / _ \/ __/ __| __/ _ \ '__|
 | |  | |  __/ (_| | | (_| | | | | | (_| | |   \ V /  __/\__ \__ \ ||  __/ |   
 |_|  |_|\___|\__,_|_|\__,_| |_| |_|\__,_|_|    \_/ \___||___/___/\__\___|_|   
[/bold cyan]
[bold bright_black]  ⚡ Universal Media Scraper & Batch Downloader v1.3.0[/bold bright_black]
"""

def print_help_guide():
    """Display a comprehensive, beautifully formatted Help Guide."""
    help_text = Text()
    help_text.append("📖 Media Harvester - คู่มือการใช้งาน & คำสั่งทั้งหมด\n\n", style="bold yellow")
    
    help_text.append("📌 รูปแบบการใช้งานมี 2 แบบ:\n", style="bold cyan")
    help_text.append("  1. สั่งรันใน Terminal พร้อม Options ทันที (Direct CLI):\n", style="bold white")
    help_text.append("     python harvester.py <URL> [OPTIONS]\n\n", style="green")
    help_text.append("  2. โหมด Interactive (เปิดโปรแกรมแล้ววางเฉพาะ URL):\n", style="bold white")
    help_text.append("     python harvester.py\n", style="yellow")
    help_text.append("     Enter Webpage URL: https://example.com\n\n", style="dim")

    opts_table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold magenta")
    opts_table.add_column("Flag / Option", style="bold green", width=22)
    opts_table.add_column("ความหมาย & การใช้งาน", style="white")
    opts_table.add_column("ตัวอย่าง", style="dim cyan", width=26)

    opts_table.add_row("-e, --ext", "กรองตามสกุลไฟล์ที่ต้องการ (เช่น webp, jpg, png, mp4)", "-e webp,jpg")
    opts_table.add_row("-t, --type", "กรองประเภทไฟล์ (images, videos, audio, documents)", "-t images,videos")
    opts_table.add_row("-s, --min-size", "กรองขนาดไฟล์ขั้นต่ำ (ตัดไอคอน/พิกเซลจิ๋วทิ้ง)", "-s 50kb  หรือ  -s 1mb")
    opts_table.add_row("-o, --output", "กำหนดโฟลเดอร์ปลายทางสำหรับบันทึกไฟล์ (ค่าเริ่มต้น: ./downloads/{domain})", "-o D:\\MyImages")
    opts_table.add_row("-c, --concurrency", "จำนวนดาวน์โหลดพร้อมกัน (Workers ขนาน)", "-c 10")
    opts_table.add_row("-f, --file", "ระบุไฟล์ .txt รวมรายการ URL สำหรับดูดแบบ Batch", "-f urls.txt")
    opts_table.add_row("-y, --yes", "ข้ามการกดยืนยัน โหลดรายการที่เลือกทันที", "-y")
    opts_table.add_row("--prefix", "ใส่ตัวเลขลำดับ 001_, 002_ หน้าชื่อไฟล์", "--prefix")
    opts_table.add_row("--timestamp", "สร้างโฟลเดอร์แยกตามวันเวลาทุกรอบ (เช่น domain_20261003_130000)", "--timestamp")
    opts_table.add_row("--overwrite", "ดาวน์โหลดทับไฟล์เดิมที่มีอยู่แล้ว", "--overwrite")
    opts_table.add_row("--dry-run", "สแกนและโชว์รายการไฟล์ในหน้าเว็บโดยยังไม่โหลดจริง", "--dry-run")
    opts_table.add_row("help / --help / -h", "แสดงคู่มือการใช้งานนี้", "python harvester.py help")

    console.print(Panel(help_text, border_style="cyan", padding=(1, 2)))
    console.print(opts_table)

    examples_table = Table(title="[bold yellow]💡 ตัวอย่างคำสั่งยอดนิยม (พิมพ์ใน Terminal)[/bold yellow]", box=box.ROUNDED)
    examples_table.add_column("โจทย์การใช้งาน", style="bold white", width=36)
    examples_table.add_column("คำสั่งที่ใช้", style="bold cyan")

    examples_table.add_row(
        "เปิดโหมด Interactive (มีเมนูให้กดเลือก)",
        "python harvester.py"
    )
    examples_table.add_row(
        "กรองเฉพาะสกุลไฟล์ .webp และ .jpg เท่านั้น",
        "python harvester.py https://example.com -e webp,jpg -y"
    )
    examples_table.add_row(
        "ดูดเฉพาะรูปภาพขนาดใหญ่ (> 50KB)",
        "python harvester.py https://example.com -t images -s 50kb -y"
    )
    examples_table.add_row(
        "ดูดแบบ Batch จากไฟล์รายการเว็บหลาย ๆ เว็บ",
        "python harvester.py -f urls.txt -e webp,jpg -s 50kb -y"
    )
    examples_table.add_row(
        "สแกนเช็กรายการไฟล์ก่อน (ยังไม่ดาวน์โหลด)",
        "python harvester.py https://example.com --dry-run"
    )

    console.print(examples_table)
    console.print("\n[dim]ℹ️ ในระหว่างหน้าเลือกไฟล์ สามารถพิมพ์ช่วงตัวเลขได้ เช่น [bold]1,3,5-10[/bold] หรือ [bold]all[/bold] เพื่อเลือกทั้งหมด หรือพิมพ์ [bold]q[/bold] เพื่อยกเลิก[/dim]\n")

def parse_size_str(size_str: str) -> int:
    """Parse string like '50kb', '2mb', '500b' to bytes."""
    if not size_str:
        return 0
    size_str = size_str.strip().lower()
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([a-z]+)?$', size_str)
    if not match:
        return 0
    val, unit = match.groups()
    val = float(val)
    if not unit or unit in ['b', 'bytes']:
        return int(val)
    elif unit in ['k', 'kb']:
        return int(val * 1024)
    elif unit in ['m', 'mb']:
        return int(val * 1024 * 1024)
    elif unit in ['g', 'gb']:
        return int(val * 1024 * 1024 * 1024)
    return int(val)

def parse_selection_indices(selection_str: str, items: List[MediaItem]) -> List[int]:
    """Parse comma/range input like '1,3,5-8' or extension keywords into 0-indexed integer list."""
    selection_str = selection_str.strip().lower()
    total_count = len(items)
    if selection_str in ['all', 'a', '*']:
        return list(range(total_count))
    if selection_str in ['q', 'quit', 'exit']:
        return []
    
    # Check if input is filtering by extension e.g. "webp,jpg"
    possible_exts = [p.strip().lstrip('.') for p in selection_str.split(',') if not p.strip().isdigit() and '-' not in p]
    if possible_exts:
        matched = []
        for idx, item in enumerate(items):
            ext_clean = item.extension.lstrip('.').lower()
            if ext_clean in possible_exts or item.media_type.value in possible_exts:
                matched.append(idx)
        if matched:
            return matched

    indices = set()
    parts = selection_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            try:
                start = max(1, int(start_s.strip()))
                end = min(total_count, int(end_s.strip()))
                for i in range(start, end + 1):
                    indices.add(i - 1)
            except ValueError:
                pass
        else:
            try:
                idx = int(part)
                if 1 <= idx <= total_count:
                    indices.add(idx - 1)
            except ValueError:
                pass
    return sorted(list(indices))

def display_scrape_summary(result: ScrapeResult):
    stats_text = Text()
    for m_type, count in result.stats.items():
        color = {
            "images": "green",
            "videos": "magenta",
            "audio": "yellow",
            "documents": "cyan"
        }.get(m_type, "white")
        stats_text.append(f" {m_type.capitalize()}: ", style="bold")
        stats_text.append(f"{count}  ", style=f"bold {color}")

    # Calculate extension breakdown
    ext_counts = {}
    for item in result.items:
        ext = item.extension or '.unknown'
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        
    ext_text = Text("\n 📂 สกุลไฟล์ที่พบ: ", style="dim bold")
    sorted_exts = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)
    for ext, count in sorted_exts:
        ext_text.append(f"{ext} ", style="bold cyan")
        ext_text.append(f"({count})  ", style="dim")

    full_content = Text()
    full_content.append(stats_text)
    full_content.append(ext_text)

    panel = Panel(
        full_content,
        title=f"[bold]Page:[/] [underline cyan]{result.title[:60]}[/]",
        subtitle=f"[dim]Total media found: {len(result.items)}[/dim]",
        border_style="cyan"
    )
    console.print(panel)

def display_items_table(items: List[MediaItem], max_display: int = 30):
    table = Table(
        title="[bold yellow]Discovered Media Assets[/bold yellow]",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=False
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Type", width=10)
    table.add_column("Ext", width=8, style="bold cyan")
    table.add_column("Filename", width=32)
    table.add_column("Media URL", style="blue")

    type_styles = {
        MediaType.IMAGE: "[green]Image[/green]",
        MediaType.VIDEO: "[magenta]Video[/magenta]",
        MediaType.AUDIO: "[yellow]Audio[/yellow]",
        MediaType.DOCUMENT: "[cyan]Doc[/cyan]"
    }

    display_list = items[:max_display]
    for idx, item in enumerate(display_list, 1):
        type_badge = type_styles.get(item.media_type, item.media_type.value)
        short_name = item.original_filename if len(item.original_filename) <= 30 else item.original_filename[:27] + "..."
        short_url = item.url if len(item.url) <= 45 else item.url[:42] + "..."
        table.add_row(str(idx), type_badge, item.extension, short_name, short_url)

    console.print(table)
    if len(items) > max_display:
        console.print(f"[italic dim]... and {len(items) - max_display} more items (use -e <ext> or select ranges)[/italic dim]\n")

def parse_pasted_command(raw_input: str):
    cleaned = raw_input.strip()
    cleaned = re.sub(r'^(?:python3?|py)?\s*(?:harvester(?:\.py)?)?\s*', '', cleaned, flags=re.IGNORECASE).strip()
    
    url_match = re.search(r'(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)', cleaned)
    extracted_url = url_match.group(1) if url_match else cleaned
    
    extensions = None
    ext_match = re.search(r'(?:-e|--ext)\s+([^\s]+)', cleaned)
    if ext_match:
        extensions = ext_match.group(1)

    media_type = None
    type_match = re.search(r'(?:-t|--type)\s+([^\s]+)', cleaned)
    if type_match:
        media_type = type_match.group(1)
        
    min_size = None
    size_match = re.search(r'(?:-s|--min-size)\s+([^\s]+)', cleaned)
    if size_match:
        min_size = size_match.group(1)
        
    auto_confirm = bool(re.search(r'(?:-y|--yes)\b', cleaned))
    
    return extracted_url, extensions, media_type, min_size, auto_confirm

def filter_media_items(
    items: List[MediaItem],
    extensions: Optional[str] = None,
    media_types: Optional[str] = None
) -> List[MediaItem]:
    filtered = items
    if media_types and media_types.lower() != 'all':
        targets = [t.strip().lower() for t in media_types.split(',')]
        filtered = [i for i in filtered if i.media_type.value in targets]
        
    if extensions and extensions.lower() != 'all':
        ext_set = {('.' + e.strip().lstrip('.').lower()) for e in extensions.split(',')}
        filtered = [i for i in filtered if i.extension.lower() in ext_set]
        
    return filtered

def process_single_url(
    url: str,
    output_dir: str,
    extensions: Optional[str],
    media_type_filter: Optional[str],
    min_size_bytes: int,
    concurrency: int,
    auto_confirm: bool,
    dry_run: bool,
    prefix_index: bool,
    use_timestamp: bool,
    overwrite: bool,
    show_stats: bool = False,
    max_retries: int = 3,
    json_mode: bool = False,
    min_width: int = 0,
    min_height: int = 0,
    cookies: Optional[dict] = None,
    depth: int = 0,
    create_zip: bool = False
):
    if not json_mode:
        depth_note = f" [dim](depth={depth})[/dim]" if depth > 0 else ""
        console.print(f"\n[bold green]► Scanning:[/] [cyan]{url}[/cyan]{depth_note}")

    extractor = MediaExtractor(cookies=cookies or {})
    try:
        if depth > 0:
            result = extractor.extract_recursive(url, depth=depth)
        else:
            result = extractor.extract(url)
    except Exception as e:
        if json_mode:
            print(json.dumps({"status": "error", "message": f"Failed to fetch/parse URL: {e}", "url": url}, ensure_ascii=False))
        else:
            console.print(f"[bold red]❌ Failed to fetch/parse URL:[/] {e}")
        return

    if not result.items:
        if json_mode:
            print(json.dumps({"status": "empty", "message": "No media items found", "url": url, "items": []}, ensure_ascii=False))
        else:
            console.print("[yellow]⚠ No media items found on this page.[/yellow]")
        return

    if not json_mode:
        display_scrape_summary(result)
        if show_stats:
            stats_table = Table(title="[bold]Media Statistics[/bold]", box=box.SIMPLE_HEAD)
            stats_table.add_column("Type", style="cyan")
            stats_table.add_column("Count", justify="right", style="bold yellow")
            for mtype, cnt in sorted(result.stats.items()):
                stats_table.add_row(mtype.capitalize(), str(cnt))
            stats_table.add_row("[bold]Total[/bold]", f"[bold green]{len(result.items)}[/bold green]")
            console.print(stats_table)

    # Initial filtering if provided via flags
    filtered_items = filter_media_items(result.items, extensions=extensions, media_types=media_type_filter)

    if not filtered_items:
        if json_mode:
            print(json.dumps({"status": "empty", "message": "No media items matched criteria", "url": url, "items": []}, ensure_ascii=False))
        else:
            console.print(f"[yellow]⚠ No media items matched criteria (ext: {extensions}, type: {media_type_filter}).[/yellow]")
        return

    if not json_mode:
        display_items_table(filtered_items)

    # Selection in interactive mode
    selected_items = filtered_items
    if not auto_confirm and not json_mode:
        selection_input = Prompt.ask(
            "\n[bold cyan]Select items or filter extension[/bold cyan] [dim](e.g. 'all', 'webp,jpg', '1,3,5-10', 'q' to cancel)[/dim]",
            default="all"
        )
        if selection_input.strip().lower() in ['q', 'quit', 'exit']:
            console.print("[yellow]Cancelled by user.[/yellow]")
            return
            
        chosen_indices = parse_selection_indices(selection_input, filtered_items)
        selected_items = [filtered_items[i] for i in chosen_indices]

    if not selected_items:
        if json_mode:
            print(json.dumps({"status": "empty", "message": "No items selected", "url": url, "items": []}, ensure_ascii=False))
        else:
            console.print("[yellow]No items selected. Skipping.[/yellow]")
        return

    if dry_run:
        if json_mode:
            payload = {
                "status": "dry_run",
                "source_url": url,
                "title": result.title,
                "stats": result.stats,
                "total_items": len(selected_items),
                "items": [
                    {
                        "url": it.url,
                        "type": it.media_type.value,
                        "extension": it.extension,
                        "filename": it.original_filename
                    }
                    for it in selected_items
                ]
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            console.print(f"[bold magenta]⚡ Dry-run complete:[/] Would download {len(selected_items)} files.")
        return

    # Setup directories (default: downloads/<domain>/)
    organizer = MediaOrganizer(base_output_dir=output_dir)
    target_folder = organizer.create_destination_structure(url, use_timestamp=use_timestamp)
    if not json_mode:
        console.print(f"\n[bold]📁 Saving to:[/] [green]{os.path.abspath(target_folder)}[/green]\n")

    # Start Downloader
    downloader = MediaDownloader(
        concurrency=concurrency,
        min_size_bytes=min_size_bytes,
        min_width=min_width,
        min_height=min_height,
        cookies=cookies or {},
        overwrite=overwrite,
        max_retries=max_retries
    )

    def path_resolver(item: MediaItem, idx: int) -> str:
        return organizer.get_destination_filepath(target_folder, item, idx, prefix_index=prefix_index)

    downloaded = downloader.run_download(selected_items, path_resolver)

    # Write Manifest & Summary
    organizer.write_manifest(target_folder, result, downloaded)

    # Create Zip Archive if requested
    zip_path = None
    if create_zip:
        zip_path = organizer.create_zip_archive(target_folder)
        if not json_mode:
            console.print(f"[bold]🗜 Archive:[/] [green]{os.path.abspath(zip_path)}[/green]")

    # Summary calculations
    success_count = sum(1 for i in downloaded if i.download_status == "success")
    failed_count = sum(1 for i in downloaded if i.download_status == "failed")
    skipped_count = sum(1 for i in downloaded if i.download_status == "skipped")
    already_exist_count = sum(1 for i in downloaded if i.error_message == "File already exists")
    total_bytes = sum(i.file_size or 0 for i in downloaded if i.download_status == "success")
    total_mb = total_bytes / (1024 * 1024)

    if json_mode:
        payload = {
            "status": "completed",
            "source_url": url,
            "target_folder": os.path.abspath(target_folder),
            "manifest_file": os.path.abspath(os.path.join(target_folder, "manifest.json")),
            "summary_file": os.path.abspath(os.path.join(target_folder, "summary.md")),
            "total_items": len(downloaded),
            "success": success_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "total_mb": round(total_mb, 2)
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        summary_panel = Panel(
            f"[bold green]✔ Download Complete![/bold green]\n\n"
            f"• [bold]New Saved Files:[/] [green]{success_count}[/green] files ({total_mb:.2f} MB)\n"
            f"• [bold]Skipped:[/] [yellow]{skipped_count}[/yellow] ({already_exist_count} already existed on disk)\n"
            f"• [bold]Failed:[/] [red]{failed_count}[/red]\n"
            f"• [bold]Destination:[/] [underline cyan]{os.path.abspath(target_folder)}[/underline cyan]\n"
            f"• [bold]Manifest:[/] [dim]{os.path.join(target_folder, 'manifest.json')}[/dim]",
            title="[bold green]Harvest Summary[/bold green]",
            border_style="green"
        )
        console.print(summary_panel)

@click.option("--stats", is_flag=True, help="Show per-type statistics table after scanning")
@click.option("--retry", default=3, help="Number of retry attempts per file (default: 3)")
@click.option("--config", "config_file", default=None, help="Load defaults from a JSON config file")
@click.option("--json", "json_output", is_flag=True, help="Output machine-readable JSON format for AI agents and scripts")
@click.option("--min-width", default=0, help="Minimum image width in pixels (e.g. 1920)")
@click.option("--min-height", default=0, help="Minimum image height in pixels (e.g. 1080)")
@click.option("--cookies", "cookie_file", default=None, help="Netscape-format cookies.txt file for authenticated sites")
@click.option("--depth", default=0, help="Recursively crawl same-domain links up to N levels deep (default: 0 = single page)")
@click.option("--zip", "create_zip", is_flag=True, help="Compress downloaded folder into a .zip archive after completion")
@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument("target_url", required=False)
@click.option("-e", "--ext", default=None, help="Filter by file extension(s), e.g. webp, jpg, png, mp4")
@click.option("-t", "--type", "media_type", default=None, help="Filter media type (images, videos, audio, documents)")
@click.option("-s", "--min-size", default=None, help="Minimum file size to download (e.g., 50kb, 1mb, 500b)")
@click.option("-o", "--output", default="downloads", help="Output directory path (default: ./downloads)")
@click.option("-c", "--concurrency", default=6, help="Number of concurrent downloads (default: 6)")
@click.option("-f", "--file", "url_file", default=None, help="Path to text file containing list of URLs")
@click.option("-y", "--yes", is_flag=True, help="Auto-confirm all downloads without interactive prompt")
@click.option("--prefix", is_flag=True, help="Prefix index numbers (001_, 002_) to filenames")
@click.option("--timestamp", is_flag=True, help="Create a new timestamped folder per download session")
@click.option("--overwrite", is_flag=True, help="Overwrite files if they already exist on disk")
@click.option("--dry-run", is_flag=True, help="Scan and list media without downloading")
def main(
    target_url: Optional[str],
    ext: Optional[str],
    media_type: Optional[str],
    min_size: Optional[str],
    output: str,
    concurrency: int,
    url_file: Optional[str],
    yes: bool,
    prefix: bool,
    timestamp: bool,
    overwrite: bool,
    dry_run: bool,
    stats: bool,
    retry: int,
    config_file: Optional[str],
    json_output: bool,
    min_width: int,
    min_height: int,
    cookie_file: Optional[str],
    depth: int,
    create_zip: bool
):
    if not json_output:
        console.print(BANNER)

    # --- Load cookies if file provided ---
    cookies: dict = {}
    if cookie_file:
        if not os.path.exists(cookie_file):
            console.print(f"[bold red]Cookies file not found:[/] {cookie_file}")
            sys.exit(1)
        cookies = load_cookies_file(cookie_file)
        if not json_output:
            console.print(f"[dim]🍪 Loaded {len(cookies)} cookies from {cookie_file}[/dim]")

    # --- Load JSON config file if provided ---
    if config_file:
        if not os.path.exists(config_file):
            if json_output:
                print(json.dumps({"status": "error", "message": f"Config file not found: {config_file}"}))
            else:
                console.print(f"[bold red]Config file not found:[/] {config_file}")
            sys.exit(1)
        try:
            with open(config_file, "r", encoding="utf-8") as _cf:
                _cfg = json.load(_cf)
            ext = ext or _cfg.get("ext")
            media_type = media_type or _cfg.get("type")
            min_size = min_size or _cfg.get("min_size")
            output = _cfg.get("output", output)
            concurrency = _cfg.get("concurrency", concurrency)
            retry = _cfg.get("retry", retry)
            if _cfg.get("yes"): yes = True
            if _cfg.get("prefix"): prefix = True
            if _cfg.get("timestamp"): timestamp = True
            if _cfg.get("overwrite"): overwrite = True
        except json.JSONDecodeError as _je:
            if json_output:
                print(json.dumps({"status": "error", "message": f"Invalid JSON config: {_je}"}))
            else:
                console.print(f"[bold red]Invalid JSON config:[/] {_je}")
            sys.exit(1)

    if target_url and target_url.strip().lower() in ['help', 'guide', 'man']:
        print_help_guide()
        sys.exit(0)

    batch_mode = bool(url_file or target_url)
    urls = []
    if url_file:
        if not os.path.exists(url_file):
            console.print(f"[bold red]File not found:[/] {url_file}")
            sys.exit(1)
        with open(url_file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    elif target_url:
        urls = [target_url.strip()]

    while True:
        if not batch_mode:
            console.print("[dim]💡 วาง [bold cyan]URL[/bold cyan] ของเว็บที่ต้องการดูด (หรือพิมพ์ [bold cyan]help[/bold cyan] / [bold red]q[/bold red] เพื่อออก)[/dim]")
            entered_url = Prompt.ask("[bold cyan]Enter Webpage URL to Scrape[/bold cyan]")
            entered_clean = entered_url.strip()
            
            if not entered_clean:
                console.print("[red]No URL provided. Exiting.[/red]")
                sys.exit(0)
                
            if entered_clean.lower() in ['exit', 'q', 'quit']:
                console.print("[yellow]Bye! 👋[/yellow]")
                sys.exit(0)
                
            if entered_clean.lower() in ['help', '?', '-h', '--help', 'guide']:
                print_help_guide()
                continue
                
            parsed_url, p_ext, p_type, p_size, p_yes = parse_pasted_command(entered_clean)
            if p_ext and not ext:
                ext = p_ext
            if p_type and not media_type:
                media_type = p_type
            if p_size and not min_size:
                min_size = p_size
            if p_yes:
                yes = True
                
            urls = [parsed_url]

        min_size_bytes = parse_size_str(min_size) if min_size else 0

        for u in urls:
            if not u.startswith(("http://", "https://")):
                u = "https://" + u
            process_single_url(
                url=u,
                output_dir=output,
                extensions=ext,
                media_type_filter=media_type,
                min_size_bytes=min_size_bytes,
                concurrency=concurrency,
                auto_confirm=yes,
                dry_run=dry_run,
                prefix_index=prefix,
                use_timestamp=timestamp,
                overwrite=overwrite,
                show_stats=stats,
                max_retries=retry,
                json_mode=json_output,
                min_width=min_width,
                min_height=min_height,
                cookies=cookies,
                depth=depth,
                create_zip=create_zip
            )

        if batch_mode:
            break

if __name__ == "__main__":
    main()

