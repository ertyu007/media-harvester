---
name: media-harvester
description: Universal web media scraper and batch downloader. Use this skill whenever you need to discover, extract, download, and organize media assets (images, high-resolution graphics, videos, audio clips, and documents) from single webpages or batches of URLs.
---

# Media Harvester Skill

`media-harvester` is a local-first, async media extraction and download engine. It extracts media from `<img>`, `<picture>`, `srcset`, `<video>`, `<audio>`, CSS `background-image`, and media links, with built-in deduplication (SHA-256 content hashing), MIME-type verification, filename collision resolution, and JSON metadata generation.

---

## Quick Reference / CLI Execution

Run the CLI directly using Python inside the project directory:

```bash
# Direct download with auto-confirm and machine-readable JSON output
python harvester.py <TARGET_URL> -y --json

# Dry-run scan (inspect available media without downloading)
python harvester.py <TARGET_URL> --dry-run --json

# Filter by extension (e.g. webp, jpg, png)
python harvester.py <TARGET_URL> -e webp,jpg,png -y

# Filter by media type (images, videos, audio, documents)
python harvester.py <TARGET_URL> -t images -s 50kb -y

# Batch download from a list file
python harvester.py -f urls.txt -y --stats
```

---

## Common CLI Flags

| Flag | Description | Example |
|---|---|---|
| `-e, --ext TEXT` | Filter specific extensions (comma-separated) | `-e jpg,webp,mp4` |
| `-t, --type TEXT` | Filter media category: `images`, `videos`, `audio`, `documents` | `-t images` |
| `-s, --min-size TEXT` | Filter out tiny icons/placeholders | `-s 50kb` or `-s 1mb` |
| `-o, --output TEXT` | Custom output directory (default: `./downloads`) | `-o ./downloads/project_assets` |
| `-c, --concurrency N` | Concurrent async download workers (default: `6`) | `-c 10` |
| `-f, --file FILE` | Text file with one URL per line for batch scraping | `-f list.txt` |
| `-y, --yes` | Non-interactive mode (auto-confirm) | `-y` |
| `--prefix` | Zero-padded index prefix (`001_image.jpg`) | `--prefix` |
| `--timestamp` | Unique timestamped folder per run | `--timestamp` |
| `--overwrite` | Overwrite existing files on disk | `--overwrite` |
| `--dry-run` | Scan and list assets without saving files | `--dry-run` |
| `--stats` | Print breakdown table of discovered media | `--stats` |
| `--retry N` | Max exponential backoff retry attempts per file (default: 3) | `--retry 4` |
| `--json` | Output machine-readable JSON for automated workflows | `--json` |

---

## Workflow for AI Agents

### 1. Inspect / Scan Mode (Dry-Run)
When you need to discover what assets a page holds before committing to a download:
```bash
python harvester.py https://example.com --dry-run --json
```
**JSON Response:**
```json
{
  "status": "dry_run",
  "source_url": "https://example.com",
  "title": "Example Domain",
  "stats": { "images": 12, "videos": 1 },
  "total_items": 13,
  "items": [
    {
      "url": "https://example.com/hero.jpg",
      "type": "images",
      "extension": ".jpg",
      "filename": "hero.jpg"
    }
  ]
}
```

### 2. Download and Capture Metadata
When you need to download assets for local processing:
```bash
python harvester.py https://example.com -t images -s 50kb -y --json
```
**JSON Response:**
```json
{
  "status": "completed",
  "source_url": "https://example.com",
  "target_folder": "D:\\Dev\\media-harvester\\downloads\\example.com",
  "manifest_file": "D:\\Dev\\media-harvester\\downloads\\example.com\\manifest.json",
  "summary_file": "D:\\Dev\\media-harvester\\downloads\\example.com\\summary.md",
  "total_items": 12,
  "success": 12,
  "skipped": 0,
  "failed": 0,
  "total_mb": 4.52
}
```

### 3. Read Manifest and Summary
After download completion, check:
- `manifest.json`: Contains full item-by-item URLs, saved paths, file sizes, and download statuses.
- `summary.md`: Human-readable summary table of all saved assets.

---

## Diagnostic & Test Commands

To verify environment health or run regression tests:
```bash
# Check Python version, dependencies, network, and disk permissions
python scripts/check_environment.py

# Run unit tests
python scripts/run_tests.py
```
