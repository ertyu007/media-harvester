#!/usr/bin/env python3
"""Media Harvester GUI — หน้าต่างคลิกๆ ไม่ต้องพิมพ์คำสั่ง."""

import os
import re
import sys
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from harvester import process_single_url, parse_size_str

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


class QueueWriter:
    """sys.stdout target: ส่ง log ข้าม thread ผ่าน queue (ตัด ANSI ทิ้ง)."""

    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, s: str):
        if s.strip():
            self.q.put(ANSI_RE.sub("", s))

    def flush(self):
        pass


class HarvesterGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Media Harvester")
        root.geometry("760x600")
        self.log_q: queue.Queue = queue.Queue()
        self.last_folder: str = ""
        self._build()
        self._poll_log()

    def _build(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="URL เว็บที่ต้องการดูด:").pack(anchor=tk.W)
        self.url = ttk.Entry(frm, width=90)
        self.url.pack(fill=tk.X, pady=(0, 8))

        opts = ttk.Frame(frm)
        opts.pack(fill=tk.X)
        self.ext = self._field(opts, "สกุลไฟล์ (เช่น webp,jpg):", 0)
        self.mtype = self._field(opts, "ประเภท (images,videos):", 1)
        self.msize = self._field(opts, "ขนาดขั้นต่ำ (เช่น 50kb):", 2)

        out = ttk.Frame(frm)
        out.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(out, text="โฟลเดอร์ปลายทาง:").pack(side=tk.LEFT)
        self.output = ttk.Entry(out, width=60)
        self.output.insert(0, "downloads")
        self.output.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(out, text="Browse…", command=self._browse).pack(side=tk.LEFT)

        flags = ttk.Frame(frm)
        flags.pack(fill=tk.X, pady=8)
        self.v_dry = tk.BooleanVar()
        self.v_prefix = tk.BooleanVar()
        self.v_ts = tk.BooleanVar()
        self.v_over = tk.BooleanVar()
        self.v_zip = tk.BooleanVar()
        for txt, var in [("Dry-run (สแกนอย่างเดียว)", self.v_dry),
                         ("Prefix 001_", self.v_prefix),
                         ("โฟลเดอร์ timestamp", self.v_ts),
                         ("Overwrite", self.v_over),
                         ("บีบเป็น .zip", self.v_zip)]:
            ttk.Checkbutton(flags, text=txt, variable=var).pack(side=tk.LEFT, padx=4)

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(0, 8))
        self.run_btn = ttk.Button(btns, text="เริ่มดูด", command=self._start)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btns, text="เปิดโฟลเดอร์", command=self._open_folder).pack(side=tk.LEFT)
        ttk.Button(btns, text="ล้าง log", command=lambda: self.log.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=5)

        self.log = tk.Text(frm, height=20, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(self.log, command=self.log.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log["yscrollcommand"] = sb.set

    def _field(self, parent, label, col):
        f = ttk.Frame(parent)
        f.grid(row=0, column=col, padx=5, sticky=tk.W)
        ttk.Label(f, text=label).pack(anchor=tk.W)
        e = ttk.Entry(f, width=28)
        e.pack()
        return e

    def _browse(self):
        d = filedialog.askdirectory()
        if d:
            self.output.delete(0, tk.END)
            self.output.insert(0, d)

    def _open_folder(self):
        if self.last_folder and os.path.isdir(self.last_folder):
            os.startfile(self.last_folder)
        else:
            messagebox.showinfo("Media Harvester", "ยังไม่มีโฟลเดอร์ที่โหลดเสร็จ")

    def _poll_log(self):
        try:
            while True:
                line = self.log_q.get_nowait()
                self.log.config(state=tk.NORMAL)
                self.log.insert(tk.END, line + "\n")
                self.log.see(tk.END)
                self.log.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)

    def _start(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning("Media Harvester", "ใส่ URL ก่อน")
            return
        self.run_btn.config(state=tk.DISABLED)
        args = dict(
            url=url if url.startswith(("http://", "https://")) else "https://" + url,
            output_dir=self.output.get().strip() or "downloads",
            extensions=self.ext.get().strip() or None,
            media_type_filter=self.mtype.get().strip() or None,
            min_size_bytes=parse_size_str(self.msize.get().strip()),
            concurrency=6,
            auto_confirm=True,  # GUI ไม่มี prompt ถามซ้ำ
            dry_run=self.v_dry.get(),
            prefix_index=self.v_prefix.get(),
            use_timestamp=self.v_ts.get(),
            overwrite=self.v_over.get(),
            create_zip=self.v_zip.get(),
        )
        threading.Thread(target=self._run, kwargs=args, daemon=True).start()

    def _run(self, **args):
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.log_q)
        try:
            import glob
            before = set(glob.glob(os.path.join(args["output_dir"], "*")))
            process_single_url(**args)
            after = set(glob.glob(os.path.join(args["output_dir"], "*")))
            new = sorted(after - before)
            self.last_folder = new[0] if new else args["output_dir"]
        except Exception as e:  # ponytail: กัน thread ตายเงียบ โชว์ error ใน log
            self.log_q.put(f"ERROR: {e}")
        finally:
            sys.stdout = old_stdout
            self.root.after(0, lambda: self.run_btn.config(state=tk.NORMAL))


def main():
    root = tk.Tk()
    HarvesterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
