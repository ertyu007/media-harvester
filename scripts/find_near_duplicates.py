#!/usr/bin/env python3
"""Report near-duplicate images using Pillow thumbnails (no new deps)."""

import argparse
import os
import sys
from collections import defaultdict

from PIL import Image, UnidentifiedImageError

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def thumb(path: str, size: int = 8):
    try:
        with Image.open(path) as im:
            return list(im.convert("RGB").resize((size, size), Image.LANCZOS).getdata())
    except (UnidentifiedImageError, OSError):
        return None


def mae(a, b) -> float:
    diffs = [abs(x - y) for pa, pb in zip(a, b) for x, y in zip(pa, pb)]
    return sum(diffs) / len(diffs)


def main():
    ap = argparse.ArgumentParser(description="Find near-duplicate images")
    ap.add_argument("folder", nargs="?", default="downloads")
    ap.add_argument("--threshold", type=float, default=10.0, help="Max mean absolute pixel diff (0-255, default 10)")
    ap.add_argument("--delete", action="store_true", help="Move later duplicates to <folder>/_duplicates")
    args = ap.parse_args()

    sigs = {}
    groups = defaultdict(list)
    for root, _, files in os.walk(args.folder):
        for f in files:
            if os.path.splitext(f)[1].lower() not in IMG_EXTS:
                continue
            p = os.path.join(root, f)
            sig = thumb(p)
            if sig is None:
                continue
            placed = False
            for rep, rep_sig in list(sigs.items()):
                if mae(sig, rep_sig) <= args.threshold:
                    groups[rep].append(p)
                    placed = True
                    break
            if not placed:
                sigs[p] = sig
                groups[p].append(p)

    dups = {rep: paths for rep, paths in groups.items() if len(paths) > 1}
    if not dups:
        print("No near-duplicates found.")
        return 0

    moved = 0
    for rep, paths in dups.items():
        print(f"{rep}")
        for p in paths[1:]:
            print(f"  near-dup: {p}")
            if args.delete:
                target_dir = os.path.join(args.folder, "_duplicates")
                os.makedirs(target_dir, exist_ok=True)
                base = os.path.basename(p)
                target = os.path.join(target_dir, base)
                stem, ext = os.path.splitext(base)
                i = 2
                while os.path.exists(target):
                    target = os.path.join(target_dir, f"{stem}_{i}{ext}")
                    i += 1
                os.replace(p, target)
                moved += 1
                print(f"    moved -> {target}")
    if args.delete:
        print(f"Moved {moved} duplicates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
