# ⚡ Media Harvester CLI

**Media Harvester** คือเครื่องมือ Command Line Interface (CLI) อัตโนมัติสำหรับดึงและดาวน์โหลดไฟล์รูปภาพ วิดีโอ เสียง และเอกสารจากหน้าเว็บไซต์ต่าง ๆ แบบ Batch ด้วยความเร็วสูง (High-Speed Async Parallel Downloader) พร้อมระบบคัดกรอง ป้องกันไฟล์ซ้ำ และจัดระเบียบโฟลเดอร์ให้อัตโนมัติ

---

## ✨ คุณสมบัติเด่น (Features)

- 🌐 **Universal Media Extraction**:
  - ดึงรูปภาพทุกรูปแบบ: `<img>`, `srcset` (เลือกภาพความละเอียดสูงสุด), `data-src` (Lazy-load), CSS `background-image`, แท็ก `<a>` ที่ลิงก์ไปยังไฟล์มีเดีย
  - ดึงวิดีโอและเสียง: `<video>`, `<source>`, `<audio>`
- ⚡ **High-Speed Parallel Downloader**:
  - ดาวน์โหลดหลายไฟล์พร้อมกันแบบ Asynchronous ปรับจำนวน Worker ขนานได้
  - แสดง Progress Bar แบบสดผ่าน Rich Terminal (บอกความเร็ว Speed, ข้อมูลที่โหลดแล้ว, เวลาที่เหลือ ETA)
- 🛡️ **Zero-Duplicate System (ระบบป้องกันไฟล์ซ้ำ)**:
  - ตรวจสอบไฟล์ที่มีอยู่แล้วในเครื่องก่อนดาวน์โหลด ช่วยประหยัดแบนด์วิดท์
  - ตรวจจับเนื้อหาไฟล์ซ้ำด้วย SHA-256 Hash
- 🎯 **Advanced Filters (ตัวกรองขั้นสูง)**:
  - กรองตามสกุลไฟล์ (`-e, --ext` เช่น `jpg,webp,png,mp4`)
  - กรองตามประเภทมีเดีย (`-t, --type` เช่น `images,videos,audio,documents`)
  - กรองขนาดไฟล์ขั้นต่ำ (`-s, --min-size` เช่น `50kb`, `1mb` ตัดไอคอนจิ๋วทิ้ง)
- 📂 **Smart Auto-Organizer**:
  - บันทึกลงโฟลเดอร์แยกตามโดเมนอัตโนมัติ เช่น `downloads/thairath.co.th/images/`
  - สร้างไฟล์รายงานสรุปผล **`manifest.json`** และ **`summary.md`** ให้ตรวจสอบย้อนหลังได้
- 🎨 **Rich Interactive UI**:
  - โหมดถาม-ตอบแบบ Interactive มีตารางพรีวิวและเมนูเลือกไฟล์
  - ระบบ Smart Auto-Parser รองรับการวางคำสั่งพร้อม Flag ได้โดยไม่ Error

---

## 📦 การติดตั้ง (Installation)

### 1. โคลนหรือเข้าโฟลเดอร์โปรเจกต์
```powershell
cd D:\Dev\media-harvester
```

### 2. สร้าง Virtual Environment และเปิดใช้งาน
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. ติดตั้ง Dependencies
```powershell
pip install -r requirements.txt
```

---

## 🚀 วิธีการใช้งาน (Usage)

### 1. โหมดถาม-ตอบ (Interactive Mode)
รันคำสั่งเพื่อเปิดโปรแกรม:
```powershell
python harvester.py
```
- โปรแกรมจะให้วาง URL ของเว็บที่ต้องการ
- แสดงตารางรายการไฟล์มีเดียทั้งหมดที่ตรวจพบ
- สามารถเลือกดาวน์โหลดเฉพาะบางไฟล์ได้ (เช่น พิมพ์ `1,3,5-10`, `webp`, หรือกด Enter เพื่อโหลด `all`)

---

### 2. โหมดคำสั่งด่วน (Direct CLI Mode)
สามารถระบุ URL และ Option ต่าง ๆ ในคำสั่งเดียวได้ทันที:

```powershell
# ตัวอย่าง: ดาวน์โหลดเฉพาะรูปภาพ .webp และ .jpg ขนาด > 50KB จากเว็บข่าว
python harvester.py https://www.sanook.com/news/politic/ -e webp,jpg -s 50kb -y

# ตัวอย่าง: ดาวน์โหลดเฉพาะวิดีโอจากเว็บเป้าหมาย
python harvester.py https://example.com -t videos -y

# ตัวอย่าง: ดาวน์โหลดแบบ Batch จากไฟล์รายการ URL หลาย ๆ เว็บพร้อมกัน
python harvester.py -f urls.txt -e jpg,png -s 100kb -y

# ตัวอย่าง: สแกนดูรายการไฟล์ก่อน (ยังไม่ดาวน์โหลดจริง)
python harvester.py https://example.com --dry-run
```

---

## ⚙️ สรุปคำสั่งและ Flags ทั้งหมด (Options Reference)

| Flag / Option | คำอธิบาย | ตัวอย่างการใช้งาน |
| :--- | :--- | :--- |
| `-e, --ext` | กรองตามนามสกุลไฟล์ที่ต้องการ | `-e webp,jpg,png` |
| `-t, --type` | กรองประเภทมีเดีย (`images`, `videos`, `audio`, `documents`) | `-t images,videos` |
| `-s, --min-size` | กำหนดขนาดไฟล์ขั้นต่ำ (ข้ามไฟล์เล็กกว่าที่ระบุ) | `-s 50kb` หรือ `-s 1mb` |
| `-o, --output` | กำหนดโฟลเดอร์สำหรับบันทึกไฟล์ (ค่าเริ่มต้น: `./downloads`) | `-o D:\MyDownloads` |
| `-c, --concurrency` | จำนวนดาวน์โหลดขนานพร้อมกัน (ค่าเริ่มต้น: `6`) | `-c 12` |
| `-f, --file` | ระบุไฟล์ `.txt` รวมรายการ URL สำหรับดูดแบบ Batch | `-f urls.txt` |
| `-y, --yes` | ข้ามขั้นตอนถามยืนยัน โหลดทุกรายการทันที | `-y` |
| `--prefix` | ใส่ตัวเลขลำดับ (`001_`, `002_`) นำหน้าชื่อไฟล์ | `--prefix` |
| `--timestamp` | สร้างโฟลเดอร์ใหม่แยกตามวันเวลาทุกครั้ง | `--timestamp` |
| `--overwrite` | บังคับดาวน์โหลดทับไฟล์เดิมที่มีอยู่แล้ว | `--overwrite` |
| `--dry-run` | สแกนและแสดงตารางรายการไฟล์โดยไม่ดาวน์โหลด | `--dry-run` |
| `help / -h / --help` | แสดงคู่มือการใช้งานแบบ Rich Terminal | `python harvester.py help` |

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```
media-harvester/
├── core/
│   ├── __init__.py
│   ├── models.py        # Data models (MediaItem, ScrapeResult)
│   ├── extractor.py     # ระบบ Scraper ดึง Assets พร้อมกรอง Tracking & ขยะ
│   ├── downloader.py    # ระบบ Async Downloader, Live Progress & Deduplication
│   └── organizer.py     # จัดการโฟลเดอร์, ป้องกันชื่อซ้ำ, เขียน manifest.json & summary.md
├── downloads/           # โฟลเดอร์เก็บไฟล์ที่ดาวน์โหลด (แยกตามชื่อโดเมน)
├── harvester.py         # Entry point หลักของโปรแกรม CLI
├── requirements.txt     # ไลบรารีที่จำเป็น (rich, httpx, bs4, click, Pillow, lxml)
└── README.md            # คู่มือการใช้งาน
```

---

## 📝 ตัวอย่างไฟล์ `urls.txt` (สำหรับ Batch Download)

สร้างไฟล์ `urls.txt` แล้วใส่รายการ URL แต่ละบรรทัด:
```text
https://www.sanook.com/news/politic/
https://www.thairath.co.th/news/foreign
https://en.wikipedia.org/wiki/Photography
```
จากนั้นรัน:
```powershell
python harvester.py -f urls.txt -e webp,jpg -s 50kb -y
```

---

## 📜 License
MIT License
