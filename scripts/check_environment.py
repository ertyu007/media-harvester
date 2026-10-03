#!/usr/bin/env python3
"""
Environment Diagnostic Tool for Media Harvester
Checks Python version, required packages, network access, and write permissions.
"""

import sys
import os
import shutil
import platform
import importlib

REQUIRED_PYTHON = (3, 10)
REQUIRED_MODULES = {
    "rich": "rich>=13.7.0",
    "httpx": "httpx>=0.27.0",
    "bs4": "beautifulsoup4>=4.12.3",
    "click": "click>=8.1.7",
    "PIL": "Pillow>=10.2.0",
    "lxml": "lxml>=5.1.0"
}

def print_status(component: str, status: str, message: str = ""):
    colors = {
        "OK": "\033[92m[OK]\033[0m",
        "WARN": "\033[93m[WARN]\033[0m",
        "FAIL": "\033[91m[FAIL]\033[0m"
    }
    badge = colors.get(status, f"[{status}]")
    if message:
        print(f" {badge:16} {component:<25} - {message}")
    else:
        print(f" {badge:16} {component}")

def check_python_version() -> bool:
    current = sys.version_info[:2]
    ver_str = f"{current[0]}.{current[1]}.{sys.version_info.micro}"
    if current >= REQUIRED_PYTHON:
        print_status(f"Python {ver_str}", "OK", f"Meets requirement (>={REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]})")
        return True
    else:
        print_status(f"Python {ver_str}", "FAIL", f"Requires Python >={REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}")
        return False

def check_dependencies() -> bool:
    all_ok = True
    import importlib.metadata
    for mod_name, req in REQUIRED_MODULES.items():
        try:
            mod = importlib.import_module(mod_name)
            pkg_name = {"bs4": "beautifulsoup4", "PIL": "Pillow"}.get(mod_name, mod_name)
            try:
                ver = importlib.metadata.version(pkg_name)
            except Exception:
                ver = getattr(mod, "__version__", "installed")
            print_status(f"{mod_name} ({ver})", "OK", req)
        except ImportError:
            print_status(mod_name, "FAIL", f"Missing dependency ({req}). Run: pip install -r requirements.txt")
            all_ok = False
    return all_ok

def check_disk_space(target_dir: str = ".") -> bool:
    try:
        total, used, free = shutil.disk_usage(target_dir)
        free_gb = free / (1024 ** 3)
        if free_gb > 1.0:
            print_status("Disk Space", "OK", f"{free_gb:.2f} GB free")
            return True
        elif free_gb > 0.2:
            print_status("Disk Space", "WARN", f"Low space: {free_gb:.2f} GB free")
            return True
        else:
            print_status("Disk Space", "FAIL", f"Critically low space: {free_gb:.2f} GB free")
            return False
    except Exception as e:
        print_status("Disk Space", "WARN", f"Unable to check ({e})")
        return True

def check_write_permissions(target_dir: str = "downloads") -> bool:
    test_dir = target_dir
    os.makedirs(test_dir, exist_ok=True)
    test_file = os.path.join(test_dir, ".perm_test.tmp")
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test")
        os.remove(test_file)
        print_status(f"Write Permission ({target_dir})", "OK", "Directory is writable")
        return True
    except Exception as e:
        print_status(f"Write Permission ({target_dir})", "FAIL", f"Permission error: {e}")
        return False

def check_network() -> bool:
    try:
        import httpx
        with httpx.Client(timeout=5.0, follow_redirects=True) as client:
            resp = client.head("https://www.google.com")
            if resp.status_code < 400:
                print_status("Internet Access", "OK", "Connected to internet")
                return True
            else:
                print_status("Internet Access", "WARN", f"HTTP status: {resp.status_code}")
                return True
    except Exception as e:
        print_status("Internet Access", "WARN", f"Network check failed or offline: {e}")
        return True

def main():
    print("=" * 65)
    print("   Media Harvester - Environment & Dependency Check")
    print(f"   OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print("=" * 65)

    py_ok = check_python_version()
    dep_ok = check_dependencies()
    disk_ok = check_disk_space()
    write_ok = check_write_permissions()
    net_ok = check_network()

    print("=" * 65)
    if py_ok and dep_ok and disk_ok and write_ok:
        print(" \033[92m[SUCCESS] Environment is fully ready for Media Harvester!\033[0m")
        sys.exit(0)
    else:
        print(" \033[91m[ERROR] Please resolve the issues above before running Media Harvester.\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
