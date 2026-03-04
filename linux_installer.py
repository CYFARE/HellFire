#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HellFire GUI Installer
"""

import glob
import io
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import webbrowser
from pathlib import Path

import requests

try:
    from PIL import Image, ImageDraw, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import tkinter as tk
from tkinter import ttk


class HellFireInstallerTk:
    def __init__(self, root):
        self.root = root
        self.root.title("HellFire Installer")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)
        self.root.configure(bg="#1a1a1a")

        self.center_window()

        self.keyword = "hellfire"
        self.base_dir = Path.home() / "HellFire"
        self.firefox_bin = self.base_dir / "firefox" / "firefox"
        self.user_bin = Path.home() / ".local" / "bin"
        self.user_bin_symlink = self.user_bin / "hellfire"
        self.desktop_file_path = Path.home() / ".local/share/applications/hellfire.desktop"
        self.file_to_extract = None
        self.avatar_image = None

        self.hero_image_url = "https://github.com/CYFARE.png?size=256"
        self.social_links = {
            "GitHub": "https://github.com/CYFARE/HellFire",
            "X / Twitter": "https://x.com/cyfarelabs",
            "Website": "https://cyfare.net/",
        }

        self.colors = {
            'bg_dark': '#1a1a1a',
            'bg_mid': '#2d1b1b',
            'bg_light': '#4a2020',
            'accent': '#ff6040',
            'accent_hover': '#ff7559',
            'text': '#ffffff',
            'text_secondary': '#cccccc',
            'card_bg': '#2a2a2a',
            'card_border': '#555555'
        }

        self.setup_styles()
        self.create_widgets()
        self.load_avatar()

    def center_window(self):
        self.root.update_idletasks()
        width = 700
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.style.configure('Horizontal.TProgressbar',
                           background=self.colors['accent'],
                           troughcolor='#333333',
                           thickness=6,
                           borderwidth=0)

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def interpolate_color(self, color1, color2, factor):
        r1, g1, b1 = self.hex_to_rgb(color1)
        r2, g2, b2 = self.hex_to_rgb(color2)
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        return f'#{r:02x}{g:02x}{b:02x}'

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg=self.colors['bg_dark'])
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.draw_gradient()

        self.container = tk.Frame(self.canvas, bg=self.colors['bg_dark'])
        self.canvas_window = self.canvas.create_window(
            (350, 300), window=self.container, anchor='center', width=500
        )

        self.avatar_frame = tk.Frame(self.container, bg=self.colors['bg_dark'], width=128, height=128)
        self.avatar_frame.pack(pady=(0, 16))
        self.avatar_frame.pack_propagate(False)

        self.avatar_label = tk.Label(
            self.avatar_frame,
            bg=self.colors['bg_dark'],
            text="🌐",
            font=('Segoe UI', 48),
            fg=self.colors['accent']
        )
        self.avatar_label.place(relx=0.5, rely=0.5, anchor='center')

        self.title_label = tk.Label(
            self.container,
            text="HellFire Browser",
            font=('Segoe UI', 24, 'bold'),
            bg=self.colors['bg_dark'],
            fg=self.colors['text']
        )
        self.title_label.pack(pady=(16, 8))

        self.desc_label = tk.Label(
            self.container,
            text="Ready to install the custom compiled browser.",
            font=('Segoe UI', 12),
            bg=self.colors['bg_dark'],
            fg=self.colors['text_secondary'],
            wraplength=450,
            justify='center'
        )
        self.desc_label.pack(pady=(0, 24))

        self.card_outer = tk.Frame(self.container, bg=self.colors['bg_dark'])
        self.card_outer.pack(pady=(20, 0), fill=tk.X)

        self.card_frame = tk.Frame(
            self.card_outer,
            bg='#252525',
            highlightbackground=self.colors['card_border'],
            highlightthickness=1,
            padx=24,
            pady=24
        )
        self.card_frame.pack(fill=tk.X)

        self.progress_frame = tk.Frame(self.card_frame, bg='#252525')

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=1,
            mode='determinate',
            length=400,
            style='Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        self.progress_text = tk.Label(
            self.progress_frame,
            text="Waiting to start...",
            font=('Segoe UI', 10),
            bg='#252525',
            fg=self.colors['text_secondary']
        )
        self.progress_text.pack()

        self.action_button = tk.Button(
            self.card_frame,
            text="Install HellFire",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['accent'],
            fg='white',
            activebackground=self.colors['accent_hover'],
            activeforeground='white',
            cursor='hand2',
            relief=tk.FLAT,
            height=2,
            width=20,
            command=self.on_action_button_clicked
        )
        self.action_button.pack(pady=(10, 0))

        self.action_button.bind('<Enter>', lambda e: self.action_button.configure(bg=self.colors['accent_hover']))
        self.action_button.bind('<Leave>', lambda e: self.action_button.configure(bg=self.colors['accent']))

        self.links_frame = tk.Frame(self.card_frame, bg='#252525')
        self.links_frame.pack(pady=(20, 0))

        for name, url in self.social_links.items():
            link_btn = tk.Label(
                self.links_frame,
                text=name,
                font=('Segoe UI', 10, 'underline'),
                bg='#252525',
                fg=self.colors['accent'],
                cursor='hand2',
                padx=6
            )
            link_btn.pack(side=tk.LEFT, padx=6)
            link_btn.bind('<Button-1>', lambda e, u=url: webbrowser.open(u))
            link_btn.bind('<Enter>', lambda e, lbl=link_btn: lbl.configure(fg=self.colors['accent_hover']))
            link_btn.bind('<Leave>', lambda e, lbl=link_btn: lbl.configure(fg=self.colors['accent']))

        self.root.bind('<Configure>', self.on_resize)

    def draw_gradient(self):
        width = self.root.winfo_width()
        height = self.root.winfo_height()

        self.canvas.delete('gradient')

        for i in range(height):
            ratio = i / height if height > 0 else 0

            if ratio < 0.6:
                color = self.interpolate_color('#1a1a1a', '#2d1b1b', ratio / 0.6)
            else:
                color = self.interpolate_color('#2d1b1b', '#4a2020', (ratio - 0.6) / 0.4)

            self.canvas.create_line(0, i, width, i, fill=color, tags='gradient')

        self.canvas.tag_lower('gradient')

    def on_resize(self, event):
        if event.widget == self.root:
            self.draw_gradient()
            width = event.width
            height = event.height
            self.canvas.coords(self.canvas_window, width//2, height//2)

    def create_circular_image(self, image_path_or_url):
        if not PIL_AVAILABLE:
            return None

        try:
            if isinstance(image_path_or_url, str) and image_path_or_url.startswith('http'):
                response = requests.get(image_path_or_url, timeout=10)
                image = Image.open(io.BytesIO(response.content))
            else:
                image = Image.open(image_path_or_url)

            image = image.convert('RGBA')
            image = image.resize((128, 128), Image.Resampling.LANCZOS)

            mask = Image.new('L', (128, 128), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 128, 128), fill=255)

            output = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
            output.paste(image, (0, 0))
            output.putalpha(mask)

            return ImageTk.PhotoImage(output)
        except Exception as e:
            print(f"Avatar error: {e}")
            return None

    def load_avatar(self):
        def fetch():
            img = self.create_circular_image(self.hero_image_url)
            if img:
                self.avatar_image = img
                self.root.after(0, lambda: self.avatar_label.configure(image=img, text=""))
        threading.Thread(target=fetch, daemon=True).start()

    def update_status(self, message: str):
        self.root.after(0, lambda: self.desc_label.configure(text=message))

    def update_progress(self, fraction: float, text: str):
        self.root.after(0, lambda: self._do_update_progress(fraction, text))

    def _do_update_progress(self, fraction: float, text: str):
        self.progress_var.set(max(0.0, min(1.0, fraction)))
        self.progress_text.configure(text=text)

    def set_progress_visible(self, visible: bool):
        def toggle():
            if visible:
                self.progress_frame.pack(fill=tk.X, pady=(0, 16), before=self.action_button)
            else:
                self.progress_frame.pack_forget()
        self.root.after(0, toggle)

    def on_action_button_clicked(self):
        self.action_button.configure(state='disabled', text="Working...")
        threading.Thread(target=self._install_flow, daemon=True).start()

    def _install_flow(self):
        self.update_status(f"Searching for '{self.keyword}*.tar.xz'...")
        candidates = []
        for loc in [".", str(Path.home()), str(Path.home() / "Downloads")]:
            candidates += glob.glob(os.path.join(loc, f"{self.keyword}*.tar.xz"))

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
                self.update_status("Download failed.")
                self._reset_ui()
                return
            self.file_to_extract = path

        self.update_status("Extracting archive...")
        self.set_progress_visible(True)

        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.update_status(f"Directory Error: {e}")
            self._reset_ui()
            return

        ok, err_msg = self._extract_archive(self.file_to_extract, self.base_dir)
        if not ok:
            self.update_status(f"Extraction failed: {err_msg}")
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

            icon_path = self.base_dir / "firefox/browser/chrome/icons/default/default128.png"
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
        self.root.after(0, lambda: self.action_button.configure(text="Done"))

    def _reset_ui(self):
        self.root.after(0, lambda: self.action_button.configure(text="Retry", state='normal'))
        self.set_progress_visible(False)

    def _latest_release_asset(self):
        api = "https://api.github.com/repos/CYFARE/HellFire/releases/latest"
        try:
            r = requests.get(api, timeout=12)
            r.raise_for_status()
            for a in r.json().get("assets", []):
                if a.get("name", "").endswith(".tar.xz"):
                    return a.get("browser_download_url"), a.get("name")
        except Exception:
            self.update_status("GitHub API Error")
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
                                self.update_progress(done / total, f"Downloading... {int(done / total * 100)}%")
            return True, str(dest)
        except Exception as e:
            return False, str(e)

    def _extract_archive(self, archive, out):
        try:
            with tarfile.open(archive, "r:xz") as tar:
                members = tar.getmembers()
                total = max(1, len(members))
                
                extract_kwargs = {}
                if hasattr(tarfile, 'data_filter'):
                    extract_kwargs['filter'] = 'data'
                
                for i, member in enumerate(members):
                    tar.extract(member, path=out, **extract_kwargs)
                    
                    if i % max(1, (total // 100)) == 0 or i == total - 1:
                        self.update_progress((i + 1) / total, f"Extracting... {int((i + 1) / total * 100)}%")
                        
            return True, ""
        except Exception as e:
            return False, str(e)


def main():
    root = tk.Tk()
    app = HellFireInstallerTk(root)
    root.mainloop()


if __name__ == "__main__":
    main()
