#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HellFire GUI Installer — cross‑distro, single‑prompt sudo, fixed avatar (GdkPaintable), prettier GTK4/Adwaita UI

Key fixes:
- Adwaita titlebar crash: use Adw.ToolbarView (no gtk_window_set_titlebar).
- Avatar TypeError: Adw.Avatar.set_custom_image now receives a Gdk.Paintable via Gdk.Texture.new_for_pixbuf.
- One credentials prompt: package install batched to a single privileged call; rest installs under ~/.local so no sudo.
- Archive discovery: searches ./, ~/, ~/Downloads/ for hellfire*.7z. Falls back to latest GitHub Release asset.
- 7z handling: auto‑detects 7z/7za/7zr; installs p7zip on major distros.
- Progress & UX: clearer progress, resilient subprocess, nicer visuals.

Requires: GTK 4 + libadwaita 1, Python gi, requests, p7zip at runtime for extraction.
"""

import os
import sys
import glob
import re
import shutil
import threading
import subprocess
from pathlib import Path

import requests

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf


class HellFireInstaller(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.codepro.hellfireinstaller")
        self.window = None
        self.status_label = None
        self.progress_bar = None
        self.action_button = None
        self.file_to_extract = None

        # Core paths/flags
        self.keyword = "hellfire"
        self.base_dir = Path.home() / "HellFire"
        self.firefox_bin = self.base_dir / "firefox" / "firefox"
        # user‑level shim in ~/.local/bin (no sudo)
        self.user_bin = Path.home() / ".local" / "bin"
        self.user_bin_symlink = self.user_bin / "hellfire"
        self.desktop_file_path = Path.home() / ".local/share/applications/hellfire.desktop"

        # Branding / links
        # PNG endpoint; requests follows redirects. If it fails, avatar is simply hidden.
        self.hero_image_url = "https://github.com/CYFARE.png?size=256"
        self.social_links = {
            "GitHub": "https://github.com/CYFARE/HellFire",
            "X/Twitter": "https://x.com/cyfarelabs",
            "Site": "https://cyfare.net/",
        }

    # ===== UI =====
    def do_activate(self):
        if not self.window:
            self.window = Adw.ApplicationWindow(application=self)
            self.window.set_title("HellFire Installer")
            self.window.set_default_size(640, 560)

            # Global CSS
            css = Gtk.CssProvider()
            css.load_from_data(
                b"""
                window#root { background: linear-gradient(135deg, rgba(18,18,22,.96), rgba(18,18,22,.92)),
                                           radial-gradient(1200px 500px at 100% 0%, rgba(255,96,64,.08), transparent),
                                           radial-gradient(1000px 500px at 0% 100%, rgba(255,160,64,.06), transparent); }
                .hero-avatar { border-radius: 16px; box-shadow: 0 12px 48px rgba(0,0,0,.45); }
                .status-card { padding: 20px; border-radius: 18px; background: rgba(255,255,255,.05); }
                .status-label { font-size: 1.02rem; }
                .action-button { padding: 12px 20px; border-radius: 14px; font-weight: 600; }
                .mono { font-family: monospace; opacity: .9; }
                """
            )
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER
            )

            # Header inside ToolbarView
            header = Adw.HeaderBar()
            header.set_title_widget(Gtk.Label(label="HellFire Installer"))

            # Main overlay
            overlay = Gtk.Overlay()
            overlay.set_hexpand(True)
            overlay.set_vexpand(True)

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            root.set_margin_top(18)
            root.set_margin_bottom(18)
            root.set_margin_start(18)
            root.set_margin_end(18)
            root.set_hexpand(True)
            root.set_vexpand(True)
            root.set_name("root")

            # Hero avatar
            hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, halign=Gtk.Align.CENTER)
            self.avatar_spinner = Gtk.Spinner(spinning=True)
            hero_box.append(self.avatar_spinner)
            self.hero_avatar = Adw.Avatar(size=128)
            self.hero_avatar.add_css_class("hero-avatar")
            self.hero_avatar.set_visible(False)
            hero_box.append(self.hero_avatar)
            threading.Thread(target=self._load_avatar_thread, daemon=True).start()

            # Status card
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            card.add_css_class("status-card")
            self.status_label = Gtk.Label(label="Welcome to the HellFire Browser Installer", wrap=True, justify=Gtk.Justification.CENTER)
            self.status_label.add_css_class("status-label")

            self.progress_bar = Gtk.ProgressBar(show_text=True)
            self.progress_bar.set_visible(False)
            self.progress_bar.set_text("Waiting…")

            self.action_button = Gtk.Button(label="Begin Installation")
            self.action_button.add_css_class("action-button")
            self.action_button.connect("clicked", self.on_action_button_clicked)

            card.append(self.status_label)
            card.append(self.progress_bar)
            card.append(self.action_button)

            # Helpful links
            links_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, halign=Gtk.Align.CENTER)
            for name, url in self.social_links.items():
                btn = Gtk.Button(label=name)
                btn.connect("clicked", self._open_url, url)
                links_row.append(btn)

            root.append(hero_box)
            root.append(card)
            root.append(links_row)

            overlay.set_child(root)

            tv = Adw.ToolbarView()
            tv.add_top_bar(header)
            tv.set_content(overlay)
            self.window.set_content(tv)
        self.window.present()

    # ===== Avatar loader (produce Gdk.Paintable) =====
    def _load_avatar_thread(self):
        try:
            r = requests.get(self.hero_image_url, timeout=10)
            r.raise_for_status()
            loader = GdkPixbuf.PixbufLoader()
            loader.write(r.content)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf is not None:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                GLib.idle_add(self.hero_avatar.set_custom_image, texture)
                GLib.idle_add(self.hero_avatar.set_visible, True)
        except Exception as e:
            print(f"[avatar] load failed: {e}")
        finally:
            GLib.idle_add(self.avatar_spinner.set_visible, False)

    # ===== UI helpers =====
    def update_status(self, message: str):
        GLib.idle_add(self.status_label.set_text, message)

    def update_progress(self, fraction: float, text: str):
        GLib.idle_add(self.progress_bar.set_fraction, max(0.0, min(1.0, fraction)))
        GLib.idle_add(self.progress_bar.set_text, text)

    def set_progress_visible(self, on: bool):
        GLib.idle_add(self.progress_bar.set_visible, on)

    # ===== Shell helpers =====
    def _run(self, cmd, use_sudo=False):
        full = list(cmd)
        if use_sudo:
            if shutil.which("pkexec"):
                full = ["pkexec"] + full
            elif shutil.which("sudo"):
                full = ["sudo"] + full
        try:
            res = subprocess.run(full, capture_output=True, text=True, check=True)
            return True, res.stdout.strip()
        except FileNotFoundError:
            return False, f"Command not found: {full[0]}"
        except subprocess.CalledProcessError as e:
            return False, (e.stderr or e.stdout or "").strip()

    def _run_progress(self, cmd):
        # Merge stderr into stdout: some 7z builds print progress on stderr
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            if proc.stdout is not None:
                for line in proc.stdout:
                    self._parse_7z_progress(line)
            proc.wait()
            if proc.returncode != 0:
                return False, "extraction command failed"
            return True, ""
        except FileNotFoundError:
            return False, f"Command not found: {cmd[0]}"

    # ===== 7z handling =====
    def _find_7z(self):
        for name in ("7z", "7za", "7zr"):
            if shutil.which(name):
                return name
        return None

    def _ensure_p7zip(self) -> bool:
        if self._find_7z():
            return True
        self.update_status("Installing p7zip… (may prompt once)")
        self.set_progress_visible(True)

        # Batch into ONE privileged call per distro
        if shutil.which("apt-get"):
            cmd = ["sh", "-c", "apt-get update -y && apt-get install -y p7zip-full"]
        elif shutil.which("pacman"):
            cmd = ["pacman", "-Sy", "--noconfirm", "p7zip"]
        elif shutil.which("dnf"):
            cmd = ["dnf", "install", "-y", "p7zip", "p7zip-plugins"]
        elif shutil.which("zypper"):
            cmd = ["zypper", "--non-interactive", "install", "p7zip", "p7zip-full"]
        elif shutil.which("apk"):
            cmd = ["apk", "add", "p7zip"]
        elif shutil.which("emerge"):
            cmd = ["emerge", "--ask=n", "app-arch/p7zip"]
        else:
            self.update_status("No supported package manager detected. Please install p7zip manually.")
            return False

        ok, out = self._run(cmd, use_sudo=True)
        if not ok:
            self.update_status(f"p7zip install failed: {out}")
            return False
        return self._find_7z() is not None

    # ===== Download helpers =====
    def _latest_release_asset(self):
        api = "https://api.github.com/repos/CYFARE/HellFire/releases/latest"
        try:
            r = requests.get(api, timeout=12)
            r.raise_for_status()
            data = r.json()
            assets = data.get("assets", [])
            for a in assets:
                name = a.get("name", "")
                url = a.get("browser_download_url")
                if name.endswith(".7z") and url:
                    return url, name
        except Exception as e:
            self.update_status(f"GitHub release lookup failed: {e}")
        return None, None

    def _download(self, url: str, filename: str):
        try:
            dest_dir = Path.home() / "Downloads"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / filename

            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                self.set_progress_visible(True)
                self.update_progress(0.0, "Starting download…")
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            if total > 0:
                                frac = done / total
                                self.update_progress(frac, f"Downloading… {int(frac*100)}%")
            return True, str(dest)
        except Exception as e:
            return False, str(e)

    # ===== Flow =====
    def on_action_button_clicked(self, _):
        self.action_button.set_sensitive(False)
        self.action_button.set_label("Working…")
        threading.Thread(target=self._install_flow, daemon=True).start()

    def _install_flow(self):
        # 1) locate local archive
        self.update_status(f"Searching for local '{self.keyword}*.7z'…")
        candidates = []
        candidates += glob.glob(f"./{self.keyword}*.7z")
        candidates += glob.glob(str(Path.home() / f"{self.keyword}*.7z"))
        candidates += glob.glob(str(Path.home() / "Downloads" / f"{self.keyword}*.7z"))
        if candidates:
            self.file_to_extract = max(candidates, key=os.path.getmtime)
            self.update_status(f"Using local archive: {os.path.basename(self.file_to_extract)}")
        else:
            # 2) fetch latest release asset
            url, name = self._latest_release_asset()
            if not url:
                self.update_status("No .7z asset found in the latest release.")
                self._done_retry()
                return
            self.update_status(f"Downloading {name}…")
            ok, path_or_err = self._download(url, name)
            if not ok:
                self.update_status(f"Download failed: {path_or_err}")
                self._done_retry()
                return
            self.file_to_extract = path_or_err

        # 3) ensure 7z exists (single sudo prompt if needed)
        self.update_status("Checking for a 7z extractor…")
        seven = self._find_7z()
        if not seven:
            if not self._ensure_p7zip():
                self._done_retry()
                return
            seven = self._find_7z()
        self.update_status(f"Using extractor: {seven}")

        # 4) prepare target dir
        self.update_status("Preparing target directory…")
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.update_status(f"Failed to prepare directory: {e}")
            self._done_retry()
            return

        # 5) extract
        self.update_status("Extracting archive…")
        self.set_progress_visible(True)
        self.update_progress(0.0, "0% Extracted")

        ok, err = self._extract_archive(seven, self.file_to_extract, self.base_dir)
        if not ok:
            self.update_status(f"Extraction failed: {err}")
            self._done_retry()
            return

        # 6) create user‑level symlink (no sudo)
        self.update_status("Creating launcher symlink…")
        if not self.firefox_bin.exists():
            self.update_status("Firefox binary not found in extracted folder.")
            self._done_retry()
            return
        try:
            self.user_bin.mkdir(parents=True, exist_ok=True)
            if self.user_bin_symlink.is_symlink() or self.user_bin_symlink.exists():
                self.user_bin_symlink.unlink()
            self.user_bin_symlink.symlink_to(self.firefox_bin)
        except Exception as e:
            self.update_status(f"Symlink failed: {e}")
            self._done_retry()
            return

        # 7) desktop entry (user scope)
        self.update_status("Registering desktop entry…")
        icon_guess = self.base_dir / 'firefox' / 'browser' / 'chrome' / 'icons' / 'default' / 'default128.png'
        desktop_entry = f"""
[Desktop Entry]
Name=HellFire Browser
Exec={self.user_bin_symlink} %u
Comment=The HellFire custom browser
Type=Application
Icon={icon_guess}
Terminal=false
Categories=Network;WebBrowser;
""".strip()
        try:
            self.desktop_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.desktop_file_path.write_text(desktop_entry, encoding="utf-8")
        except Exception as e:
            self.update_status(f"Failed to write desktop file: {e}")
            self._done_retry()
            return

        self.update_status("Installation complete! If '~/.local/bin' isn't on your PATH, add it so 'hellfire' works in the terminal.")
        GLib.idle_add(self.action_button.set_label, "Done!")

    def _done_retry(self):
        GLib.idle_add(self.action_button.set_label, "Retry")
        GLib.idle_add(self.action_button.set_sensitive, True)
        self.set_progress_visible(False)

    # ===== Extraction helpers =====
    def _parse_7z_progress(self, line: str):
        m = re.search(r"(\d+)%", line)
        if m:
            pct = int(m.group(1))
            self.update_progress(pct / 100.0, f"{pct}% Extracted")

    def _extract_archive(self, seven: str, archive_path: str, out_dir: Path):
        cmd = [seven, "x", f"-o{str(out_dir)}", archive_path, "-bsp1", "-y"]
        return self._run_progress(cmd)

    # ===== Helpers =====
    def _open_url(self, _btn, url: str):
        try:
            Gtk.show_uri(self.window, url, Gdk.CURRENT_TIME)
        except GLib.Error as e:
            self.update_status(f"Error opening link: {e.message}")


if __name__ == "__main__":
    app = HellFireInstaller()
    sys.exit(app.run(sys.argv))
