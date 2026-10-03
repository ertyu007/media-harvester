# Media Harvester

![Media Harvester](assets/header.svg)

> **Universal Media Scraper & Batch Downloader** — CLI tool ดูดรูป วิดีโอ เสียง เอกสาร จากเว็บใดก็ได้

[![Version](https://img.shields.io/badge/version-v1.2.0-brightgreen?style=flat-square)](https://github.com/ertyu007/media-harvester)
[![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)](LICENSE)

---

## Features

| Feature | Details |
|---------|---------|
| **Universal Extraction** | `<img>`, `srcset`, `<picture>`, `<video>`, `<audio>`, `<a href>`, CSS `background-image` |
| **Smart Dedup** | ตรวจ content hash (SHA-256) ทั้ง in-session และ on-disk |
| **Filename Collision Fix** | `image.jpg` → `image_2.jpg` → `image_3.jpg` อัตโนมัติ |
| **Content-Type Validation** | เช็ก MIME type ก่อนเซฟ — ป้องกันดาวน์โหลด HTML/JSON ผิด |
| **Exponential Backoff Retry** | retry 403/429 พร้อม delay ทวีคูณ (configurable) |
| **Async Downloads** | Concurrent downloads ด้วย `httpx` + `asyncio` |
| **Agent Skill & JSON Mode** | `--json` output + `SKILL.md` พร้อมให้ AI Agent เรียกใช้ |
| **Environment Diagnostics** | `python scripts/check_environment.py` ตรวจความพร้อมของระบบ |
| **Automated Test Suite** | `python scripts/run_tests.py` รวม 14 unit tests ครอบคลุม core engine |
| **Statistics Table** | `--stats` แสดงจำนวนสื่อแยกประเภท |
| **Manifest & Summary** | `manifest.json` + `summary.md` อัตโนมัติหลังดาวน์โหลด |
| **JSON Config File** | `--config config.json` โหลด default settings จากไฟล์ |
| **Smart Filtering** | กรองด้วย extension, media type, ขนาดไฟล์ขั้นต่ำ |
| **High-Res Detection** | ลบ WordPress `-300x200` suffix อัตโนมัติ |
| **Batch URL Support** | ป้อน URLs เป็น list file ด้วย `-f urls.txt` |

---

## Installation & Setup

```bash
git clone https://github.com/ertyu007/media-harvester.git
cd media-harvester
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt

# ตรวจสอบความพร้อมของระบบ (Environment Check)
python scripts/check_environment.py
```

---

## Testing & Quality

รันชุด Automated Unit Tests ทั้งหมด:

```bash
python scripts/run_tests.py
# หรือ
python -m unittest discover -s tests -v
```

---

## Usage

### Basic

```bash
# Interactive mode
python harvester.py

# Scrape a URL directly
python harvester.py https://example.com

# Dry-run (scan only, no download)
python harvester.py https://example.com --dry-run --stats

# JSON output mode (สำหรับ AI Agent / Script automation)
python harvester.py https://example.com --dry-run --json
```

### Filter & Control

```bash
# Download only images (jpg + png)
python harvester.py https://example.com -t images -e jpg,png

# Minimum file size 100KB, auto-confirm
python harvester.py https://example.com -s 100kb -y

# Custom output folder, 10 concurrent downloads
python harvester.py https://example.com -o ~/Pictures/harvest -c 10

# Prefix filenames with index numbers
python harvester.py https://example.com --prefix

# Timestamped subfolder per session
python harvester.py https://example.com --timestamp
```

### Batch & Config

```bash
# Batch from URL file
python harvester.py -f urls.txt -y --stats

# Load defaults from JSON config
python harvester.py --config my_config.json https://example.com

# Override retry count
python harvester.py https://example.com --retry 5
```

### Example `config.json`

```json
{
  "output": "downloads/art",
  "ext": "jpg,png,webp",
  "type": "images",
  "min_size": "50kb",
  "concurrency": 8,
  "retry": 4,
  "yes": true,
  "prefix": false,
  "timestamp": true
}
```

---

## All Options

```
Usage: harvester.py [OPTIONS] [TARGET_URL]

Options:
  -e, --ext TEXT        Filter extensions (e.g. webp,jpg,mp4)
  -t, --type TEXT       Filter type: images, videos, audio, documents
  -s, --min-size TEXT   Min file size (e.g. 50kb, 1mb)
  -o, --output TEXT     Output directory (default: ./downloads)
  -c, --concurrency N   Concurrent downloads (default: 6)
  -f, --file TEXT       Text file with one URL per line
  -y, --yes             Auto-confirm without prompts
  --prefix              Prefix filenames: 001_image.jpg
  --timestamp           New timestamped folder per session
  --overwrite           Re-download existing files
  --dry-run             Scan only, no download
  --stats               Show per-type statistics table
  --retry N             Retry attempts per file (default: 3)
  --config FILE         Load defaults from JSON config file
  --json                Output machine-readable JSON for AI agents and scripts
  -h, --help            Show help message
```

---

## AI Agent Skill Integration

Media Harvester รองรับการทำงานร่วมกับ AI Coding Agents (เช่น Antigravity, Copilot, Claude Code) ผ่าน [skills/media-harvester/SKILL.md](skills/media-harvester/SKILL.md):
- สแกนและพรีวิวไฟล์แบบไม่ดาวน์โหลดด้วย `--dry-run --json`
- ดาวน์โหลดอัตโนมัติพร้อมบันทึก `manifest.json` และ `summary.md`
- นำผลลัพธ์ JSON ไปประมวลผลต่อเนื่องใน Data Pipeline ได้ทันที

---

## Output Structure

```
downloads/
└── example.com/
    ├── images/
    │   ├── hero-photo.jpg
    │   ├── logo.png
    │   └── banner_2.png       <- auto-renamed on collision
    ├── videos/
    ├── audio/
    ├── documents/
    ├── manifest.json          <- full download metadata
    └── summary.md             <- human-readable report
```

---

## Changelog

### v1.2.0 — Toolkit Standards & AI Agent Skill
- Environment Diagnostics — เพิ่ม `scripts/check_environment.py` ตรวจ Python, dependencies, disk space และ network
- Automated Test Suite — เพิ่ม `tests/` และ `scripts/run_tests.py` ครอบคลุม 14 unit tests
- AI Agent Skill Package — เพิ่ม `skills/media-harvester/SKILL.md` และ `.agents/skills/media-harvester/SKILL.md`
- JSON Automation Mode — เพิ่ม `--json` flag ให้ CLI คืนค่าผลลัพธ์เป็น JSON สำหรับ Script และ Agent
- Offline HTML Extraction API — เพิ่ม `extract_from_html()` ใน `MediaExtractor`

### v1.1.0 — Reliability & Quality
- Filename collision fix — `image.jpg` -> `image_2.jpg` (in-memory + on-disk)
- Content-Type validation — reject HTML/JSON, auto-fix extension mismatch
- Exponential backoff retry — configurable `--retry N`
- `--stats` flag — per-type statistics table
- `--config FILE` — load settings from JSON config file
- Improved progress bar with `N/M` file counter

### v1.0.0 — Initial Release
- Universal media extraction from any webpage
- Async parallel downloads with progress bar
- Content-hash deduplication
- Interactive CLI with Prompt selection
- Manifest + summary report generation

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

```bash
git checkout -b feat/your-feature
git commit -m "feat: describe your change"
git push origin feat/your-feature
```

---

## License

MIT © [ertyu007](https://github.com/ertyu007)


