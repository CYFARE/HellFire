#!/usr/bin/env python3

import os
import sys
import subprocess
import threading
import gi
import shutil
import re
import requests
import json
import glob
import io

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Adw, Gdk, GdkPixbuf

class CodeProApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.window = None
        self.spinner = None
        self.status_label = None
        self.action_button = None
        self.progress_bar = None
        self.file_to_extract = None

        # --- Key variables ---
        self.keyword = "hellfire"
        self.hellfire_dir = os.path.expanduser("~/HellFire")
        self.firefox_bin = os.path.join(self.hellfire_dir, "firefox", "firefox")
        self.symlink_target = "/usr/bin/hellfire"
        self.desktop_file_path = os.path.expanduser("~/.local/share/applications/hellfire.desktop")

        self.hero_image_url = "https://avatars.githubusercontent.com/u/150654459"
        self.social_icons = {
            "github": {
                "url": "https://github.com/CYFARE/HellFire",
                "icon_url": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/github.svg",
                "tooltip": "GitHub Repository"
            },
            "x": {
                "url": "https://x.com/cyfarelabs",
                "icon_url": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/x.svg",
                "tooltip": "X/Twitter Profile"
            },
            "site": {
                "url": "https://cyfare.net/",
                "icon_url": "https://raw.githubusercontent.com/feathericons/feather/master/icons/link.svg",
                "tooltip": "Releases Page"
            }
        }

    def on_social_button_clicked(self, widget, url):
        """Opens the given URL in the default browser."""
        try:
            Gtk.show_uri(self.window, url, Gdk.CURRENT_TIME)
        except GLib.Error as e:
            self.update_status(f"Error opening link: {e.message}")

    def load_image_in_thread(self, widget, url, is_svg=False):
        """Generic image loader running in a background thread."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            image_data = response.content

            # Use GdkPixbufLoader for robust loading
            loader = GdkPixbuf.PixbufLoader()
            if is_svg:
                loader.set_size(48, 48) # Set a default size for SVGs

            loader.write(image_data)
            loader.close()
            pixbuf = loader.get_pixbuf()

            # Update UI on the main thread
            GLib.idle_add(widget.set_from_pixbuf, pixbuf)

        except Exception as e:
            print(f"Failed to load image from {url}: {e}")

    def load_avatar_in_thread(self, avatar_widget, spinner_widget, url):
        """Loads the main hero avatar in a background thread."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            image_data = response.content

            # Create pixbuf from downloaded data
            input_stream = io.BytesIO(image_data)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream(input_stream)

            def update_ui():
                avatar_widget.set_custom_image(pixbuf)
                spinner_widget.set_spinning(False)
                spinner_widget.set_visible(False)
                avatar_widget.set_visible(True)

            GLib.idle_add(update_ui)

        except Exception as e:
            print(f"Failed to load avatar: {e}")
            GLib.idle_add(spinner_widget.set_spinning, False)


    def do_activate(self):
        if not self.window:
            self.window = Gtk.ApplicationWindow(application=self)
            self.window.set_default_size(550, 550)
            self.window.set_resizable(False)

            header = Adw.HeaderBar()
            self.window.set_titlebar(header)

            # --- Main Overlay Layout ---
            overlay = Gtk.Overlay()
            self.window.set_child(overlay)

            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
            main_box.set_size_request(450, -1)
            overlay.set_child(main_box)

            # --- Hero Image (Avatar) ---
            avatar_spinner = Gtk.Spinner(spinning=True, halign=Gtk.Align.CENTER)
            main_box.append(avatar_spinner)

            hero_avatar = Adw.Avatar(size=128, visible=False, halign=Gtk.Align.CENTER)
            hero_avatar.add_css_class("hero-avatar")
            main_box.append(hero_avatar)

            # Load avatar in background
            threading.Thread(target=self.load_avatar_in_thread, args=(hero_avatar, avatar_spinner, self.hero_image_url), daemon=True).start()

            self.status_label = Gtk.Label(label="Welcome to the HellFire Browser Installer", wrap=True, justify=Gtk.Justification.CENTER)
            self.status_label.add_css_class("status-label")
            main_box.append(self.status_label)

            self.progress_bar = Gtk.ProgressBar(show_text=True, text="Waiting...")
            self.progress_bar.set_visible(False)
            main_box.append(self.progress_bar)

            self.action_button = Gtk.Button(label="Begin Installation", halign=Gtk.Align.CENTER)
            self.action_button.add_css_class("action-button")
            self.action_button.connect("clicked", self.on_action_button_clicked)
            main_box.append(self.action_button)

            # --- Social Icons Box (in Overlay) ---
            social_box = Gtk.Box(spacing=10)
            social_box.set_halign(Gtk.Align.END)
            social_box.set_valign(Gtk.Align.END)
            social_box.set_margin_end(15)
            social_box.set_margin_bottom(15)
            overlay.add_overlay(social_box)

            for key, data in self.social_icons.items():
                icon_image = Gtk.Image()
                icon_image.add_css_class("social-icon")

                button = Gtk.Button()
                button.set_child(icon_image)
                button.set_tooltip_text(data["tooltip"])
                button.add_css_class("social-button")
                button.connect("clicked", self.on_social_button_clicked, data["url"])

                social_box.append(button)

                # Load icon in background
                threading.Thread(target=self.load_image_in_thread, args=(icon_image, data["icon_url"], True), daemon=True).start()

            header.set_title_widget(Adw.WindowTitle.new("HellFire Browser", ""))
            self.load_css()

        self.window.present()

    def load_css(self):
        """Loads the beautiful CSS for custom styling."""
        css_provider = Gtk.CssProvider()
        css = """
        window {
            background: linear-gradient(135deg, #23272A, #2C2F33);
        }
        headerbar { background-color: transparent; }

        .hero-avatar {
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .status-label {
            font-size: 14px;
            font-weight: bold;
            color: #99AAB5;
        }
        progressbar { min-height: 25px; }
        progressbar progress {
            background: linear-gradient(to right, #E67E22, #D35400);
            border-radius: 12px;
        }
        progressbar trough {
            background-color: #40444B;
            border-radius: 12px;
        }
        progressbar text {
            color: white;
            font-weight: bold;
            text-shadow: 1px 1px 2px black;
        }
        .action-button {
            font-size: 16px;
            font-weight: bold;
            padding: 12px 28px;
            margin-top: 10px;
            border-radius: 8px;
            color: white;
            background: linear-gradient(to right, #e06c75, #be5046);
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: all 0.2s ease-in-out;
        }
        .action-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 10px rgba(0,0,0,0.3);
        }
        .social-button {
            background-color: rgba(64, 68, 75, 0.5);
            border-radius: 9999px;
            padding: 0;
            border: none;
            min-height: 40px;
            min-width: 40px;
        }
        .social-button:hover {
            background-color: rgba(88, 93, 102, 0.7);
        }
        .social-icon {
            -gtk-icon-size: 20px;
            filter: invert(0.8); /* Makes dark icons light */
        }
        .social-button:hover .social-icon {
            filter: invert(1);
        }
        """
        css_provider.load_from_data(css.encode('UTF-8'))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # --- All backend methods (on_action_button_clicked, run_installation_flow, etc.) remain unchanged ---

    def on_action_button_clicked(self, widget):
        self.action_button.set_sensitive(False)
        self.action_button.set_label("Working...")
        threading.Thread(target=self.run_installation_flow, daemon=True).start()

    def update_status(self, message):
        GLib.idle_add(self.status_label.set_text, message)

    def update_progress(self, fraction, text):
        GLib.idle_add(self.progress_bar.set_fraction, fraction)
        GLib.idle_add(self.progress_bar.set_text, text)

    def run_command(self, command, use_sudo=False):
        if use_sudo:
            command = ["pkexec"] + command
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return True, result.stdout.strip()
        except FileNotFoundError:
            return False, f"Command not found: {command[0]}"
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()

    def run_installation_flow(self):
        self.update_status(f"Searching for local '{self.keyword}*.7z' file...")
        local_archives = glob.glob(f"./{self.keyword}*.7z") + glob.glob(os.path.expanduser(f"~/Downloads/{self.keyword}*.7z"))

        if local_archives:
            self.file_to_extract = local_archives[0]
            self.update_status(f"Found local archive: {os.path.basename(self.file_to_extract)}")
        else:
            self.update_status("No local archive found. Checking online...")
            download_url, filename = self.get_latest_release_info()
            if not download_url:
                GLib.idle_add(self.reset_ui, "Retry", True); return

            downloaded_file = self.download_file_with_progress(download_url, filename)
            if not downloaded_file:
                GLib.idle_add(self.reset_ui, "Retry", True); return
            self.file_to_extract = downloaded_file

        if not self.file_to_extract:
            self.update_status("Could not find or download the HellFire archive.")
            GLib.idle_add(self.reset_ui, "Error", False); return

        self.update_status("Checking if 7z is installed...")
        if not shutil.which("7z"):
            self.update_status("7z not found. Installing p7zip-full...")
            GLib.idle_add(self.progress_bar.set_visible, True)
            GLib.idle_add(self.progress_bar.set_text, "Installing p7zip...")
            GLib.idle_add(self.progress_bar.pulse)

            success, msg = self.run_command(["apt-get", "update", "-y"], use_sudo=True)
            if not success:
                self.update_status(f"Failed to update package lists. Error: {msg}")
                GLib.idle_add(self.reset_ui, "Retry", True); return

            success, msg = self.run_command(["apt-get", "install", "-y", "p7zip-full"], use_sudo=True)
            if not success:
                self.update_status(f"Failed to install p7zip-full. Error: {msg}")
                GLib.idle_add(self.reset_ui, "Retry", True); return
            self.update_status("p7zip-full installed successfully.")
        else:
            self.update_status("7z is already installed.")

        self.update_status("Preparing HellFire directory...")
        if os.path.exists(self.hellfire_dir): shutil.rmtree(self.hellfire_dir)
        os.makedirs(self.hellfire_dir)

        self.update_status(f"Extracting archive...")
        GLib.idle_add(self.progress_bar.set_visible, True)
        self.update_progress(0, "Starting Extraction...")

        def progress_parser(line):
            match = re.search(r'^\s*(\d+)', line)
            if match:
                percentage = int(match.group(1))
                self.update_progress(percentage / 100.0, f"{percentage}% Extracted")

        extract_cmd = ["7z", "x", f"-o{self.hellfire_dir}", self.file_to_extract, "-bsp1", "-y"]
        success, msg = self.run_command_with_progress(extract_cmd, progress_parser)

        if not success:
            self.update_status(f"Extraction failed. Error: {msg}")
            GLib.idle_add(self.reset_ui, "Retry", True); return
        self.update_progress(1.0, "Extraction Complete")

        self.update_status("Creating system symlink...")
        success, msg = self.run_command(["ln", "-sf", self.firefox_bin, self.symlink_target], use_sudo=True)
        if not success:
            self.update_status(f"Failed to create symlink. Error: {msg}")
            GLib.idle_add(self.reset_ui, "Retry", True); return

        self.update_status("Creating desktop shortcut...")
        desktop_entry_content = f"""
[Desktop Entry]
Name=HellFire Browser
Exec={self.symlink_target}
Comment=The HellFire custom browser
Type=Application
Icon={os.path.join(self.hellfire_dir, 'firefox', 'browser', 'chrome', 'icons', 'default', 'default128.png')}
Terminal=false
Categories=Network;WebBrowser;
"""
        try:
            os.makedirs(os.path.dirname(self.desktop_file_path), exist_ok=True)
            with open(self.desktop_file_path, "w") as f: f.write(desktop_entry_content.strip())
            self.run_command(["update-desktop-database", os.path.dirname(self.desktop_file_path)])
        except Exception as e:
            self.update_status(f"Failed to create desktop file. Error: {e}")
            GLib.idle_add(self.reset_ui, "Retry", True); return

        self.update_status("Installation complete! Enjoy HellFire Browser.")
        GLib.idle_add(self.reset_ui, "Done!", False)

    def get_latest_release_info(self):
        self.update_status("Fetching latest release from GitHub...")
        api_url = "https://api.github.com/repos/CYFARE/HellFire/releases/latest"
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            release_data = response.json()
            for asset in release_data.get("assets", []):
                if asset.get("name", "").endswith(".7z"):
                    self.update_status(f"Found latest release: {asset['name']}")
                    return asset.get("browser_download_url"), asset.get("name")
            self.update_status("No .7z file found in the latest release.")
            return None, None
        except requests.exceptions.RequestException as e:
            self.update_status(f"Error fetching release info: {e}")
            return None, None

    def download_file_with_progress(self, url, filename):
        self.update_status(f"Downloading {filename}...")
        GLib.idle_add(self.progress_bar.set_visible, True)
        try:
            with requests.get(url, stream=True, timeout=15) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                fraction = downloaded_size / total_size
                                self.update_progress(fraction, f"Downloading... {int(fraction * 100)}%")
            self.update_progress(1.0, "Download Complete")
            return filename
        except requests.exceptions.RequestException as e:
            self.update_status(f"Download failed: {e}")
            if os.path.exists(filename): os.remove(filename)
            return None

    def run_command_with_progress(self, command, progress_callback, use_sudo=False):
        if use_sudo: command = ["pkexec"] + command
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
        for line in process.stdout: progress_callback(line)
        process.wait()
        if process.returncode != 0:
            return False, process.stderr.read().strip()
        return True, ""

    def reset_ui(self, button_text, is_enabled):
        self.action_button.set_label(button_text)
        self.action_button.set_sensitive(is_enabled)
        if not is_enabled and button_text == "Done!":
            self.action_button.set_label("Installation Complete")
            self.progress_bar.set_visible(True)
        elif is_enabled:
             self.progress_bar.set_visible(False)
             self.action_button.set_label("Retry Installation")

if __name__ == "__main__":
    app = CodeProApp(application_id="com.codepro.hellfireinstaller")
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
