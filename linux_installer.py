#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HellFire GUI Installer
"""

import glob
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import gi
import requests

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk


class HellFireInstaller(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.codepro.hellfireinstaller",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.window = None
        self.status_page = None
        self.progress_bar = None
        self.action_button = None
        self.file_to_extract = None

        # Core paths/flags
        self.keyword = "hellfire"
        self.base_dir = Path.home() / "HellFire"
        self.firefox_bin = self.base_dir / "firefox" / "firefox"
        self.user_bin = Path.home() / ".local" / "bin"
        self.user_bin_symlink = self.user_bin / "hellfire"
        self.desktop_file_path = (
            Path.home() / ".local/share/applications/hellfire.desktop"
        )

        # Branding
        self.hero_image_url = "https://github.com/CYFARE.png?size=256"
        self.social_links = {
            "GitHub": "https://github.com/CYFARE/HellFire",
            "X / Twitter": "https://x.com/cyfarelabs",
            "Website": "https://cyfare.net/",
        }

    def do_activate(self):
        if not self.window:
            # 1. Apply Dark Theme
            style_manager = Adw.StyleManager.get_default()
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

            # 2. Configure Main Window
            self.window = Adw.ApplicationWindow(application=self)
            self.window.set_title("HellFire Installer")
            self.window.set_default_size(700, 600)

            # 3. Load Custom CSS
            display = Gdk.Display.get_default()
            if display:
                css = Gtk.CssProvider()
                css.load_from_data(b"""
                    .hellfire-bg {
                        background: linear-gradient(
                            160deg,
                            #1a1a1a 0%,
                            #2d1b1b 60%,
                            #4a2020 100%
                        );
                    }
                    .translucent-card {
                        background-color: rgba(255, 255, 255, 0.06);
                        border-radius: 12px;
                        padding: 24px;
                        margin-top: 20px;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                    }
                    progressbar > trough > progress {
                        background-image: none;
                        background-color: #ff6040;
                    }
                """)
                Gtk.StyleContext.add_provider_for_display(
                    display, css, Gtk.STYLE_PROVIDER_PRIORITY_USER
                )

            # 4. Build UI Structure
            self.status_page = Adw.StatusPage()
            self.status_page.set_title("HellFire Browser")
            self.status_page.set_description(
                "Ready to install the custom compiled browser."
            )
            self.status_page.set_icon_name("web-browser-symbolic")
            self.status_page.add_css_class("hellfire-bg")

            # Center content with Clamp
            clamp = Adw.Clamp(maximum_size=450)

            controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            controls_box.add_css_class("translucent-card")

            # Progress Bar
            self.progress_bar = Gtk.ProgressBar()
            self.progress_bar.set_text("Waiting to start...")
            self.progress_bar.set_show_text(True)
            self.progress_bar.set_visible(False)

            # Main Action Button
            self.action_button = Gtk.Button(label="Install HellFire")
            self.action_button.add_css_class("suggested-action")
            self.action_button.add_css_class("pill")

            # FIX: Use set_size_request(-1, 50) instead of set_height_request
            self.action_button.set_size_request(-1, 50)

            self.action_button.connect("clicked", self.on_action_button_clicked)

            # Social Links
            links_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            links_box.set_halign(Gtk.Align.CENTER)

            for name, url in self.social_links.items():
                btn = Gtk.Button(label=name)
                btn.add_css_class("flat")
                btn.connect("clicked", self._open_url, url)
                links_box.append(btn)

            controls_box.append(self.progress_bar)
            controls_box.append(self.action_button)
            controls_box.append(links_box)

            clamp.set_child(controls_box)
            self.status_page.set_child(clamp)

            # Toolbar View
            header = Adw.HeaderBar()
            header.add_css_class("flat")

            toolbar_view = Adw.ToolbarView()
            toolbar_view.add_top_bar(header)
            toolbar_view.set_content(self.status_page)

            self.window.set_content(toolbar_view)
            self.window.present()

            # Start avatar loader
            threading.Thread(target=self._load_avatar_thread, daemon=True).start()

    # ===== Avatar Logic =====
    def _load_avatar_thread(self):
        try:
            r = requests.get(self.hero_image_url, timeout=10)
            r.raise_for_status()
            loader = GdkPixbuf.PixbufLoader()
            loader.write(r.content)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                GLib.idle_add(self._update_avatar_ui, texture)
        except Exception as e:
            print(f"Avatar load warning: {e}")

    def _update_avatar_ui(self, texture):
        self.status_page.set_paintable(texture)

    # ===== UI Updates =====
    def update_status(self, message: str):
        GLib.idle_add(self.status_page.set_description, message)

    def update_progress(self, fraction: float, text: str):
        GLib.idle_add(self.progress_bar.set_fraction, max(0.0, min(1.0, fraction)))
        GLib.idle_add(self.progress_bar.set_text, text)

    def set_progress_visible(self, on: bool):
        GLib.idle_add(self.progress_bar.set_visible, on)

    # ===== Shell & 7z Logic =====
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
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            err = getattr(e, "stderr", str(e)) or str(e)
            return False, err.strip()

    def _run_progress(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            if proc.stdout:
                for line in proc.stdout:
                    self._parse_7z_progress(line)
            proc.wait()
            return (proc.returncode == 0), "Extraction failed"
        except Exception as e:
            return False, str(e)

    def _find_7z(self):
        for name in ("7z", "7za", "7zr"):
            if shutil.which(name):
                return name
        return None

    def _ensure_p7zip(self) -> bool:
        if self._find_7z():
            return True
        self.update_status("Installing p7zip (password may be required)...")
        self.set_progress_visible(True)

        managers = [
            ("apt-get", "apt-get update -y && apt-get install -y p7zip-full"),
            ("pacman", "pacman -Sy --noconfirm p7zip"),
            ("dnf", "dnf install -y p7zip p7zip-plugins"),
            ("zypper", "zypper --non-interactive install p7zip p7zip-full"),
            ("apk", "apk add p7zip"),
            ("emerge", "emerge --ask=n app-arch/p7zip"),
        ]

        cmd = None
        for mgr, c in managers:
            if shutil.which(mgr):
                cmd = ["sh", "-c", c] if "&&" in c else c.split()
                break

        if not cmd:
            self.update_status(
                "No supported package manager found. Install p7zip manually."
            )
            return False

        ok, out = self._run(cmd, use_sudo=True)
        if not ok:
            self.update_status(f"Installation failed: {out}")
            return False
        return True

    # ===== Download Logic =====
    def _latest_release_asset(self):
        api = "https://api.github.com/repos/CYFARE/HellFire/releases/latest"
        try:
            r = requests.get(api, timeout=12)
            r.raise_for_status()
            for a in r.json().get("assets", []):
                if a.get("name", "").endswith(".7z"):
                    return a.get("browser_download_url"), a.get("name")
        except Exception as e:
            self.update_status(f"GitHub API Error: {e}")
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

                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            if total > 0:
                                self.update_progress(
                                    done / total,
                                    f"Downloading... {int(done / total * 100)}%",
                                )
            return True, str(dest)
        except Exception as e:
            return False, str(e)

    # ===== Installation Flow =====
    def on_action_button_clicked(self, _):
        self.action_button.set_sensitive(False)
        self.action_button.set_label("Working...")
        threading.Thread(target=self._install_flow, daemon=True).start()

    def _install_flow(self):
        self.update_status(f"Searching for '{self.keyword}*.7z'...")
        candidates = []
        for loc in [".", str(Path.home()), str(Path.home() / "Downloads")]:
            candidates += glob.glob(os.path.join(loc, f"{self.keyword}*.7z"))

        if candidates:
            self.file_to_extract = max(candidates, key=os.path.getmtime)
            self.update_status(f"Found local: {os.path.basename(self.file_to_extract)}")
        else:
            self.update_status("Fetching latest release info...")
            url, name = self._latest_release_asset()
            if not url:
                self.update_status("No release found on GitHub.")
                self._reset_ui()
                return

            self.update_status(f"Downloading {name}...")
            ok, path = self._download(url, name)
            if not ok:
                self.update_status(f"Download failed: {path}")
                self._reset_ui()
                return
            self.file_to_extract = path

        if not self._ensure_p7zip():
            self._reset_ui()
            return
        seven = self._find_7z()

        self.update_status("Extracting archive...")
        self.set_progress_visible(True)
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.update_status(f"Dir Error: {e}")
            self._reset_ui()
            return

        ok, err = self._extract_archive(seven, self.file_to_extract, self.base_dir)
        if not ok:
            self.update_status(f"Extraction failed: {err}")
            self._reset_ui()
            return

        self.update_status("Finalizing setup...")
        if not self.firefox_bin.exists():
            self.update_status("Error: 'firefox' binary missing in archive.")
            self._reset_ui()
            return

        try:
            self.user_bin.mkdir(parents=True, exist_ok=True)
            if self.user_bin_symlink.exists() or self.user_bin_symlink.is_symlink():
                self.user_bin_symlink.unlink()
            self.user_bin_symlink.symlink_to(self.firefox_bin)

            icon_path = (
                self.base_dir / "firefox/browser/chrome/icons/default/default128.png"
            )
            desktop_entry = f"""[Desktop Entry]
Name=HellFire Browser
Exec={self.user_bin_symlink} %u
Comment=Custom Firefox Compile
Type=Application
Icon={icon_path}
Terminal=false
Categories=Network;WebBrowser;
"""
            self.desktop_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.desktop_file_path.write_text(desktop_entry, encoding="utf-8")
        except Exception as e:
            self.update_status(f"Setup failed: {e}")
            self._reset_ui()
            return

        self.update_progress(1.0, "Completed")
        self.update_status("Installation Successful!")
        GLib.idle_add(self.action_button.set_label, "Done")
        GLib.idle_add(self.action_button.add_css_class, "success")

    def _reset_ui(self):
        GLib.idle_add(self.action_button.set_label, "Retry")
        GLib.idle_add(self.action_button.set_sensitive, True)
        GLib.idle_add(self.action_button.remove_css_class, "success")
        self.set_progress_visible(False)

    def _parse_7z_progress(self, line):
        m = re.search(r"(\d+)%", line)
        if m:
            pct = int(m.group(1))
            self.update_progress(pct / 100, f"Extracting... {pct}%")

    def _extract_archive(self, seven, archive, out):
        cmd = [seven, "x", f"-o{str(out)}", archive, "-bsp1", "-y"]
        return self._run_progress(cmd)

    def _open_url(self, _, url):
        Gtk.show_uri(self.window, url, Gdk.CURRENT_TIME)


if __name__ == "__main__":
    app = HellFireInstaller()
    sys.exit(app.run(sys.argv))
