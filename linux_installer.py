#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HellFire GUI Installer
"""

import glob
import io
import os
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
from tkinter import font as tkfont


# ---------------------------------------------------------------------------
# Font fallback for broad Linux distro coverage
# ---------------------------------------------------------------------------

SANS_PREFERENCES = (
    "Inter", "Inter Variable", "SF Pro Display",
    "Ubuntu", "Cantarell", "Noto Sans", "Roboto",
    "DejaVu Sans", "Liberation Sans", "FreeSans", "Sans",
)

SANS_BOLD_PREFERENCES = (
    "Inter Black", "Inter SemiBold",
    "Ubuntu Bold", "Cantarell Bold", "Noto Sans Bold",
    *SANS_PREFERENCES,
)


def pick_font(preferred, size, weight="normal"):
    try:
        available = {f.lower() for f in tkfont.families()}
    except Exception:
        available = set()
    for name in preferred:
        if name.lower() in available:
            return (name, size, weight)
    return ("TkDefaultFont", size, weight)


# ---------------------------------------------------------------------------
# Custom widgets
# ---------------------------------------------------------------------------

class RoundedFrame(tk.Canvas):
    """Canvas with a rounded-rect background. Use .interior for content."""

    def __init__(self, parent, width, height, parent_bg, card_bg,
                 border_color=None, radius=14):
        super().__init__(
            parent, width=width, height=height,
            highlightthickness=0, bd=0, bg=parent_bg,
        )
        self._cw, self._ch, self._r = width, height, radius
        self._parent_bg = parent_bg
        self._card_bg = card_bg
        self._border_color = border_color
        self._draw()

        self.interior = tk.Frame(self, bg=card_bg)
        self.create_window(
            radius, radius, anchor="nw", window=self.interior,
            width=width - 2 * radius, height=height - 2 * radius,
        )

    def _draw(self):
        self.delete("bg")
        w, h, r = self._cw, self._ch, self._r
        c = self._card_bg
        self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=90,
                        fill=c, outline=c, tags="bg")
        self.create_arc(w - 2 * r, 0, w, 2 * r, start=0, extent=90,
                        fill=c, outline=c, tags="bg")
        self.create_arc(0, h - 2 * r, 2 * r, h, start=180, extent=90,
                        fill=c, outline=c, tags="bg")
        self.create_arc(w - 2 * r, h - 2 * r, w, h, start=270, extent=90,
                        fill=c, outline=c, tags="bg")
        self.create_rectangle(r, 0, w - r, h, fill=c, outline=c, tags="bg")
        self.create_rectangle(0, r, w, h - r, fill=c, outline=c, tags="bg")
        self.tag_lower("bg")

    def update_theme(self, parent_bg, card_bg, border_color=None):
        self._parent_bg = parent_bg
        self._card_bg = card_bg
        self._border_color = border_color
        self.configure(bg=parent_bg)
        self.interior.configure(bg=card_bg)
        self._draw()


class RoundedButton(tk.Canvas):
    """Pill button with hover/press/disabled states."""

    def __init__(self, parent, text="", command=None,
                 width=160, height=42, radius=21,
                 bg="#ff6b3d", hover_bg="#ff8559", active_bg="#e55a2e",
                 disabled_bg="#cccccc", disabled_fg="#777",
                 fg="white", font=None, parent_bg="#ffffff"):
        super().__init__(
            parent, width=width, height=height,
            highlightthickness=0, bd=0, bg=parent_bg,
        )
        self._text = text
        self._command = command
        self._cw, self._ch, self._r = width, height, radius
        self._bg, self._hover, self._active = bg, hover_bg, active_bg
        self._disabled_bg, self._disabled_fg = disabled_bg, disabled_fg
        self._fg = fg
        self._font = font or pick_font(SANS_BOLD_PREFERENCES, 11, "bold")
        self._enabled = True
        self._current_bg = bg
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self):
        self.delete("all")
        w, h, r = self._cw, self._ch, self._r
        bg = self._current_bg if self._enabled else self._disabled_bg
        fg = self._fg if self._enabled else self._disabled_fg
        self.create_arc(0, 0, 2 * r, h, start=90, extent=180,
                        fill=bg, outline=bg)
        self.create_arc(w - 2 * r, 0, w, h, start=270, extent=180,
                        fill=bg, outline=bg)
        self.create_rectangle(r, 0, w - r, h, fill=bg, outline=bg)
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=fg, font=self._font)

    def configure_text(self, text):
        self._text = text
        self._draw()

    def set_enabled(self, enabled):
        self._enabled = enabled
        self._current_bg = self._bg
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def update_colors(self, parent_bg, bg, hover_bg, active_bg,
                      disabled_bg, disabled_fg, fg):
        self._bg, self._hover, self._active = bg, hover_bg, active_bg
        self._disabled_bg, self._disabled_fg = disabled_bg, disabled_fg
        self._fg = fg
        self._current_bg = bg
        self.configure(bg=parent_bg)
        self._draw()

    def _on_enter(self, _):
        if self._enabled:
            self._current_bg = self._hover
            self.configure(cursor="hand2")
            self._draw()

    def _on_leave(self, _):
        if self._enabled:
            self._current_bg = self._bg
            self._draw()

    def _on_press(self, _):
        if self._enabled:
            self._current_bg = self._active
            self._draw()

    def _on_release(self, _):
        if not self._enabled:
            return
        self._current_bg = self._hover
        self._draw()
        if self._command:
            self._command()


class SmoothProgressBar(tk.Canvas):
    """Rounded progress bar with eased animation + indeterminate shimmer."""

    def __init__(self, parent, width=440, height=8,
                 bg_track="#ecebf3", fg="#ff6b3d", parent_bg="#ffffff"):
        super().__init__(
            parent, width=width, height=height,
            highlightthickness=0, bd=0, bg=parent_bg,
        )
        self._cw, self._ch = width, height
        self._track = bg_track
        self._fg = fg
        self._target = 0.0
        self._current = 0.0
        self._animating = False
        self._indeterminate = False
        self._shimmer_x = -0.3
        self._draw()

    def _rounded_rect(self, x1, y1, x2, y2, r, fill):
        if x2 - x1 < 2 * r:
            r = max(0, (x2 - x1) // 2)
        if r <= 0:
            self.create_rectangle(x1, y1, x2, y2, fill=fill, outline=fill)
            return
        self.create_arc(x1, y1, x1 + 2 * r, y2, start=90, extent=180,
                        fill=fill, outline=fill)
        self.create_arc(x2 - 2 * r, y1, x2, y2, start=270, extent=180,
                        fill=fill, outline=fill)
        self.create_rectangle(x1 + r, y1, x2 - r, y2,
                              fill=fill, outline=fill)

    def _draw(self):
        self.delete("all")
        w, h = self._cw, self._ch
        r = h // 2
        self._rounded_rect(0, 0, w, h, r, self._track)
        if self._indeterminate:
            seg = int(w * 0.3)
            x = int(self._shimmer_x * w)
            x1 = max(0, x)
            x2 = min(w, x + seg)
            if x2 > x1:
                self._rounded_rect(x1, 0, x2, h, r, self._fg)
        else:
            fw = int(self._current * w)
            if fw > 0:
                self._rounded_rect(0, 0, fw, h, r, self._fg)

    def set_value(self, value):
        self._indeterminate = False
        self._target = max(0.0, min(1.0, value))
        if not self._animating:
            self._animating = True
            self._tick()

    def _tick(self):
        if self._indeterminate:
            self._shimmer_x += 0.02
            if self._shimmer_x > 1.05:
                self._shimmer_x = -0.3
            self._draw()
            self.after(30, self._tick)
            return
        delta = self._target - self._current
        if abs(delta) < 0.002:
            self._current = self._target
            self._draw()
            self._animating = False
            return
        self._current += delta * 0.25
        self._draw()
        self.after(16, self._tick)

    def start_indeterminate(self):
        self._indeterminate = True
        self._shimmer_x = -0.3
        if not self._animating:
            self._animating = True
            self._tick()

    def stop_indeterminate(self):
        self._indeterminate = False
        self._animating = False
        self._current = 0.0
        self._draw()

    def update_colors(self, parent_bg, track, fg):
        self._track = track
        self._fg = fg
        self.configure(bg=parent_bg)
        self._draw()


class ToggleSwitch(tk.Canvas):
    """iOS-style sliding toggle for theme switching."""

    def __init__(self, parent, parent_bg, track_off, track_on, knob,
                 command=None, on=False):
        super().__init__(
            parent, width=44, height=24,
            highlightthickness=0, bd=0, bg=parent_bg,
        )
        self._on = on
        self._track_off = track_off
        self._track_on = track_on
        self._knob = knob
        self._command = command
        self.configure(cursor="hand2")
        self._draw()
        self.bind("<Button-1>", self._click)

    def _draw(self):
        self.delete("all")
        track = self._track_on if self._on else self._track_off
        self.create_arc(0, 0, 24, 24, start=90, extent=180,
                        fill=track, outline=track)
        self.create_arc(20, 0, 44, 24, start=270, extent=180,
                        fill=track, outline=track)
        self.create_rectangle(12, 0, 32, 24, fill=track, outline=track)
        kx = 22 if self._on else 2
        self.create_oval(kx, 2, kx + 20, 22,
                         fill=self._knob, outline=self._knob)

    def _click(self, _):
        self._on = not self._on
        self._draw()
        if self._command:
            self._command(self._on)

    def update_colors(self, parent_bg, track_off, track_on, knob):
        self._track_off = track_off
        self._track_on = track_on
        self._knob = knob
        self.configure(bg=parent_bg)
        self._draw()


class PillNavItem(tk.Frame):
    """Sidebar nav row with a pill-shaped active/hover background."""

    HEIGHT = 38
    RADIUS = 10
    LEFT_PAD = 16

    def __init__(self, parent, text, font, on_click=None):
        super().__init__(parent, height=self.HEIGHT)
        self.pack_propagate(False)
        self._text = text
        self._font = font
        self._on_click = on_click
        self._active = False
        self._hover = False
        self._colors = None

        self._canvas = tk.Canvas(
            self, height=self.HEIGHT,
            highlightthickness=0, bd=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Configure>", lambda e: self._draw())
        self._canvas.bind("<Button-1>", self._click)
        self._canvas.bind("<Enter>", self._enter)
        self._canvas.bind("<Leave>", self._leave)

    def _draw(self):
        if not self._colors:
            return
        c = self._canvas
        c.delete("all")
        w = c.winfo_width()
        h = self.HEIGHT
        r = self.RADIUS
        if w < 2 * r:
            return

        bg = self._colors["sidebar_bg"]
        if self._active:
            fill = self._colors["accent"]
            text_color = "#ffffff"
        elif self._hover:
            fill = self._colors["nav_hover"]
            text_color = self._colors["text"]
        else:
            fill = bg
            text_color = self._colors["text_muted"]

        c.configure(bg=bg)
        self.configure(bg=bg)

        if fill != bg:
            c.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=90,
                         fill=fill, outline=fill)
            c.create_arc(w - 2 * r, 0, w, 2 * r, start=0, extent=90,
                         fill=fill, outline=fill)
            c.create_arc(0, h - 2 * r, 2 * r, h, start=180, extent=90,
                         fill=fill, outline=fill)
            c.create_arc(w - 2 * r, h - 2 * r, w, h, start=270, extent=90,
                         fill=fill, outline=fill)
            c.create_rectangle(r, 0, w - r, h, fill=fill, outline=fill)
            c.create_rectangle(0, r, w, h - r, fill=fill, outline=fill)

        c.create_text(self.LEFT_PAD, h // 2, text=self._text,
                      fill=text_color, anchor="w", font=self._font)

    def set_active(self, active):
        self._active = active
        self._draw()

    def _enter(self, _):
        self._hover = True
        self._canvas.configure(cursor="hand2")
        self._draw()

    def _leave(self, _):
        self._hover = False
        self._draw()

    def _click(self, _):
        if self._on_click:
            self._on_click()

    def update_colors(self, colors):
        self._colors = colors
        self._draw()


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------

THEMES = {
    "light": {
        "bg":             "#f4f1fb",
        "sidebar_bg":     "#ffffff",
        "card_bg":        "#ffffff",
        "card_alt":       "#faf9ff",
        "border":         "#ecebf3",
        "text":           "#1a1a2e",
        "text_muted":     "#6b6b80",
        "text_dim":       "#a0a0b0",
        "accent":         "#ff6b3d",
        "accent_hover":   "#ff8559",
        "accent_active":  "#e55a2e",
        "accent_soft":    "#fff1eb",
        "secondary":      "#7c6ef0",
        "secondary_soft": "#efedff",
        "track":          "#ecebf3",
        "success":        "#22c55e",
        "error":          "#ef4444",
        "nav_hover":      "#f5f3ff",
        "toggle_off":     "#dcd9e8",
        "toggle_on":      "#ff6b3d",
        "toggle_knob":    "#ffffff",
        "cta_grad_a":     "#7c6ef0",
        "cta_grad_b":     "#a594ff",
    },
    "dark": {
        "bg":             "#0e0c14",
        "sidebar_bg":     "#15131c",
        "card_bg":        "#1a1822",
        "card_alt":       "#211e2c",
        "border":         "#2a2734",
        "text":           "#f4f1ee",
        "text_muted":     "#a39ab0",
        "text_dim":       "#6b6673",
        "accent":         "#ff6b3d",
        "accent_hover":   "#ff8559",
        "accent_active":  "#e55a2e",
        "accent_soft":    "#2a1d18",
        "secondary":      "#9787f5",
        "secondary_soft": "#1f1b2e",
        "track":          "#2a2734",
        "success":        "#4ade80",
        "error":          "#f87171",
        "nav_hover":      "#211e2c",
        "toggle_off":     "#2a2734",
        "toggle_on":      "#ff6b3d",
        "toggle_knob":    "#f4f1ee",
        "cta_grad_a":     "#5b4fc7",
        "cta_grad_b":     "#7c6ef0",
    },
}


# ---------------------------------------------------------------------------
# Main installer
# ---------------------------------------------------------------------------

class HellFireInstallerTk:
    WINDOW_W = 1024
    WINDOW_H = 660
    SIDEBAR_W = 220
    PADDING = 24

    def __init__(self, root):
        self.root = root
        self.root.title("HellFire Installer")
        self.root.geometry(f"{self.WINDOW_W}x{self.WINDOW_H}")
        self.root.resizable(False, False)
        self._center_window()

        self.theme_name = "dark"
        self.colors = THEMES[self.theme_name]
        self._themed_widgets = []
        self._themed_custom = []

        self.root.configure(bg=self.colors["bg"])

        self.keyword = "hellfire"
        self.base_dir = Path.home() / "HellFire"
        self.firefox_bin = self.base_dir / "firefox" / "firefox"
        self.user_bin = Path.home() / ".local" / "bin"
        self.user_bin_symlink = self.user_bin / "hellfire"
        self.desktop_file_path = (
            Path.home() / ".local/share/applications/hellfire.desktop"
        )
        self.file_to_extract = None
        self.avatar_image = None
        self._installed = False

        self.hero_image_url = "https://github.com/CYFARE.png?size=256"
        self.social_links = {
            "GitHub":  "https://github.com/CYFARE/HellFire",
            "Twitter": "https://x.com/cyfarelabs",
            "Website": "https://cyfare.net/",
        }

        self.fonts = {
            "logo":      pick_font(SANS_BOLD_PREFERENCES, 16, "bold"),
            "title":     pick_font(SANS_BOLD_PREFERENCES, 22, "bold"),
            "subtitle":  pick_font(SANS_PREFERENCES, 11, "normal"),
            "body":      pick_font(SANS_PREFERENCES, 10, "normal"),
            "body_bold": pick_font(SANS_BOLD_PREFERENCES, 10, "bold"),
            "small":     pick_font(SANS_PREFERENCES, 9, "normal"),
            "tiny":      pick_font(SANS_PREFERENCES, 8, "normal"),
            "section":   pick_font(SANS_BOLD_PREFERENCES, 8, "bold"),
            "nav":       pick_font(SANS_PREFERENCES, 11, "normal"),
            "stat_num":  pick_font(SANS_BOLD_PREFERENCES, 18, "bold"),
            "card_h":    pick_font(SANS_BOLD_PREFERENCES, 13, "bold"),
            "btn":       pick_font(SANS_BOLD_PREFERENCES, 11, "bold"),
            "cta_h":     pick_font(SANS_BOLD_PREFERENCES, 17, "bold"),
            "cta_b":     pick_font(SANS_PREFERENCES, 11, "normal"),
        }

        self._stats = {
            "source": ("Source", "—", "Awaiting"),
            "size":   ("Size",   "—", "Pending"),
            "files":  ("Files",  "—", "Pending"),
            "status": ("Status", "Ready", "Click install"),
        }
        self._stat_widgets = {}

        self._build_ui()
        self._load_avatar()
        threading.Thread(target=self._refresh_stats, daemon=True).start()

    # ----- window helpers ----------------------------------------------------

    def _center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.WINDOW_W) // 2
        y = (self.root.winfo_screenheight() - self.WINDOW_H) // 2
        self.root.geometry(f"{self.WINDOW_W}x{self.WINDOW_H}+{x}+{y}")

    # ----- theme system ------------------------------------------------------

    def _theme(self, widget, **roles):
        self._themed_widgets.append((widget, roles))
        self._apply_theme_to(widget, roles)

    def _apply_theme_to(self, widget, roles):
        try:
            widget.configure(**{
                opt: self.colors[role] for opt, role in roles.items()
            })
        except tk.TclError:
            pass

    def _theme_custom(self, fn):
        self._themed_custom.append(fn)
        fn(self.colors)

    def _toggle_theme(self, is_dark):
        self.theme_name = "dark" if is_dark else "light"
        self.colors = THEMES[self.theme_name]
        self.root.configure(bg=self.colors["bg"])
        for widget, roles in self._themed_widgets:
            self._apply_theme_to(widget, roles)
        for fn in self._themed_custom:
            fn(self.colors)

    # ----- UI construction ---------------------------------------------------

    def _build_ui(self):
        self.outer = tk.Frame(self.root)
        self._theme(self.outer, bg="bg")
        self.outer.pack(fill=tk.BOTH, expand=True)

        self._build_sidebar(self.outer)

        self.main_area = tk.Frame(self.outer)
        self._theme(self.main_area, bg="bg")
        self.main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_main(self.main_area)

    # ----- sidebar -----------------------------------------------------------

    def _build_sidebar(self, parent):
        self.sidebar = tk.Frame(parent, width=self.SIDEBAR_W)
        self.sidebar.pack_propagate(False)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self._theme(self.sidebar, bg="sidebar_bg")

        logo_frame = tk.Frame(self.sidebar, height=80)
        logo_frame.pack(fill=tk.X, padx=24, pady=(28, 28))
        self._theme(logo_frame, bg="sidebar_bg")

        logo_a = tk.Label(logo_frame, text="HELL", font=self.fonts["logo"])
        logo_a.pack(side=tk.LEFT)
        self._theme(logo_a, bg="sidebar_bg", fg="text")

        logo_b = tk.Label(logo_frame, text="FIRE", font=self.fonts["logo"])
        logo_b.pack(side=tk.LEFT)
        self._theme(logo_b, bg="sidebar_bg", fg="accent")

        # Only Install nav — About and Settings removed (no features behind them)
        nav_data = [("Install", True)]
        self._nav_items = []
        for label, active in nav_data:
            item = PillNavItem(
                self.sidebar, text=label,
                font=self.fonts["nav"],
                on_click=lambda l=label: self._on_nav_click(l),
            )
            item.pack(fill=tk.X, padx=14, pady=2)
            item.set_active(active)
            self._theme_custom(item.update_colors)
            self._nav_items.append((label, item))

        section_lbl = tk.Label(
            self.sidebar, text="OTHER LINKS",
            font=self.fonts["section"], anchor="w",
        )
        section_lbl.pack(fill=tk.X, padx=24, pady=(28, 8))
        self._theme(section_lbl, bg="sidebar_bg", fg="text_dim")

        for name, url in self.social_links.items():
            item = PillNavItem(
                self.sidebar, text=name,
                font=self.fonts["nav"],
                on_click=lambda u=url: webbrowser.open(u),
            )
            item.pack(fill=tk.X, padx=14, pady=2)
            self._theme_custom(item.update_colors)

        spacer = tk.Frame(self.sidebar)
        spacer.pack(fill=tk.BOTH, expand=True)
        self._theme(spacer, bg="sidebar_bg")

        toggle_row = tk.Frame(self.sidebar)
        toggle_row.pack(fill=tk.X, padx=24, pady=(12, 28))
        self._theme(toggle_row, bg="sidebar_bg")

        sun = tk.Label(toggle_row, text="☀", font=self.fonts["body_bold"])
        sun.pack(side=tk.LEFT)
        self._theme(sun, bg="sidebar_bg", fg="text_muted")

        self.theme_toggle = ToggleSwitch(
            toggle_row,
            parent_bg=self.colors["sidebar_bg"],
            track_off=self.colors["toggle_off"],
            track_on=self.colors["toggle_on"],
            knob=self.colors["toggle_knob"],
            on=(self.theme_name == "dark"),
            command=self._toggle_theme,
        )
        self.theme_toggle.pack(side=tk.LEFT, padx=10)

        def _update_toggle(colors):
            self.theme_toggle.update_colors(
                parent_bg=colors["sidebar_bg"],
                track_off=colors["toggle_off"],
                track_on=colors["toggle_on"],
                knob=colors["toggle_knob"],
            )
        self._theme_custom(_update_toggle)

        moon = tk.Label(toggle_row, text="☾", font=self.fonts["body_bold"])
        moon.pack(side=tk.LEFT)
        self._theme(moon, bg="sidebar_bg", fg="text_muted")

    def _on_nav_click(self, label):
        for name, item in self._nav_items:
            item.set_active(name == label)

    # ----- main area --------------------------------------------------------

    def _build_main(self, parent):
        wrap = tk.Frame(parent)
        wrap.pack(fill=tk.BOTH, expand=True, padx=self.PADDING, pady=(16, 20))
        self._theme(wrap, bg="bg")

        self._build_header(wrap)

        spacer1 = tk.Frame(wrap, height=20)
        self._theme(spacer1, bg="bg")
        spacer1.pack(fill=tk.X)
        self._build_stat_cards(wrap)

        spacer2 = tk.Frame(wrap, height=16)
        self._theme(spacer2, bg="bg")
        spacer2.pack(fill=tk.X)
        self._build_middle_row(wrap)

        spacer3 = tk.Frame(wrap, height=16)
        self._theme(spacer3, bg="bg")
        spacer3.pack(fill=tk.X)
        self._build_cta_card(wrap)

    def _build_header(self, parent):
        header = tk.Frame(parent, height=44)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        self._theme(header, bg="bg")

        left = tk.Frame(header)
        left.pack(side=tk.LEFT, fill=tk.Y)
        self._theme(left, bg="bg")

        welcome = tk.Label(left, text="Welcome to ",
                           font=self.fonts["title"])
        welcome.pack(side=tk.LEFT)
        self._theme(welcome, bg="bg", fg="text")

        brand = tk.Label(left, text="HellFire", font=self.fonts["title"])
        brand.pack(side=tk.LEFT)
        self._theme(brand, bg="bg", fg="accent")

        right = tk.Frame(header)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        self._theme(right, bg="bg")

        version_pill = RoundedFrame(
            right, width=130, height=36,
            parent_bg=self.colors["bg"],
            card_bg=self.colors["card_bg"], radius=18,
        )
        version_pill.pack(side=tk.RIGHT, padx=(0, 4))

        # Colored dot + text inside the pill
        pill_inner = tk.Frame(version_pill.interior, bg=self.colors["card_bg"])
        pill_inner.pack(expand=True)

        dot = tk.Canvas(pill_inner, width=8, height=8,
                        highlightthickness=0, bd=0,
                        bg=self.colors["card_bg"])
        dot.pack(side=tk.LEFT, padx=(0, 6))
        dot.create_oval(0, 0, 8, 8, fill=self.colors["accent"], outline="")

        def _upd_dot(colors):
            dot.configure(bg=colors["card_bg"])
            dot.delete("all")
            dot.create_oval(0, 0, 8, 8, fill=colors["accent"], outline="")
        self._theme_custom(_upd_dot)

        ver_label = tk.Label(
            pill_inner, text="Linux build",
            font=self.fonts["small"], anchor="center",
            bg=self.colors["card_bg"], fg=self.colors["text_muted"],
        )
        ver_label.pack(side=tk.LEFT)
        self._theme(ver_label, bg="card_bg", fg="text_muted")

        def _upd_pill(colors):
            version_pill.update_theme(colors["bg"], colors["card_bg"])
            pill_inner.configure(bg=colors["card_bg"])
        self._theme_custom(_upd_pill)

    # ----- stat cards row ---------------------------------------------------

    def _build_stat_cards(self, parent):
        row = tk.Frame(parent, height=98)
        row.pack(fill=tk.X)
        row.pack_propagate(False)
        self._theme(row, bg="bg")

        inner_w = self.WINDOW_W - self.SIDEBAR_W - 2 * self.PADDING
        gap = 12
        card_w = (inner_w - gap * 3) // 4
        card_h = 98

        keys = ["source", "size", "files", "status"]
        accent_colors = ["accent", "secondary", "accent", "secondary"]

        for i, (key, accent) in enumerate(zip(keys, accent_colors)):
            label, value, sub = self._stats[key]

            card = RoundedFrame(
                row, width=card_w, height=card_h,
                parent_bg=self.colors["bg"],
                card_bg=self.colors["card_bg"], radius=14,
            )
            card.pack(side=tk.LEFT, padx=(0 if i == 0 else gap, 0))

            def _upd_card(colors, c=card):
                c.update_theme(colors["bg"], colors["card_bg"])
            self._theme_custom(_upd_card)

            content = tk.Frame(card.interior)
            content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
            self._theme(content, bg="card_bg")

            top = tk.Frame(content)
            top.pack(fill=tk.X)
            self._theme(top, bg="card_bg")

            lbl = tk.Label(top, text=label, font=self.fonts["small"],
                           anchor="w")
            lbl.pack(side=tk.LEFT)
            self._theme(lbl, bg="card_bg", fg="text_muted")

            dot = tk.Label(top, text="●", font=self.fonts["small"])
            dot.pack(side=tk.RIGHT)
            self._theme(dot, bg="card_bg", fg=accent)

            val = tk.Label(content, text=value,
                           font=self.fonts["stat_num"], anchor="w")
            val.pack(fill=tk.X, pady=(6, 0))
            self._theme(val, bg="card_bg", fg="text")

            sub_lbl = tk.Label(content, text=sub,
                               font=self.fonts["tiny"], anchor="w")
            sub_lbl.pack(fill=tk.X)
            self._theme(sub_lbl, bg="card_bg", fg="text_dim")

            self._stat_widgets[key] = (val, sub_lbl)

    def _set_stat(self, key, value=None, sub=None):
        def apply():
            val_w, sub_w = self._stat_widgets[key]
            if value is not None:
                val_w.configure(text=value)
            if sub is not None:
                sub_w.configure(text=sub)
        self.root.after(0, apply)

    # ----- middle row: progress + about -------------------------------------

    def _build_middle_row(self, parent):
        row = tk.Frame(parent, height=236)
        row.pack(fill=tk.X)
        row.pack_propagate(False)
        self._theme(row, bg="bg")

        inner_w = self.WINDOW_W - self.SIDEBAR_W - 2 * self.PADDING
        gap = 12
        progress_w = int(inner_w * 0.66)
        about_w = inner_w - progress_w - gap

        self._build_progress_card(row, progress_w, 236)
        spacer = tk.Frame(row, width=gap)
        spacer.pack(side=tk.LEFT)
        self._theme(spacer, bg="bg")
        self._build_about_card(row, about_w, 236)

    def _build_progress_card(self, parent, w, h):
        card = RoundedFrame(
            parent, width=w, height=h,
            parent_bg=self.colors["bg"],
            card_bg=self.colors["card_bg"], radius=14,
        )
        card.pack(side=tk.LEFT)

        def _upd(colors):
            card.update_theme(colors["bg"], colors["card_bg"])
        self._theme_custom(_upd)

        body = tk.Frame(card.interior)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)
        self._theme(body, bg="card_bg")

        head = tk.Frame(body)
        head.pack(fill=tk.X)
        self._theme(head, bg="card_bg")

        title = tk.Label(head, text="Installation",
                         font=self.fonts["card_h"], anchor="w")
        title.pack(side=tk.LEFT)
        self._theme(title, bg="card_bg", fg="text")

        self.percent_label = tk.Label(head, text="",
                                      font=self.fonts["body_bold"])
        self.percent_label.pack(side=tk.RIGHT)
        self._theme(self.percent_label, bg="card_bg", fg="text_muted")

        sub = tk.Label(
            body,
            text="Custom-compiled Firefox build, installed to your home folder.",
            font=self.fonts["small"], anchor="w", justify="left",
        )
        sub.pack(fill=tk.X, pady=(4, 12))
        self._theme(sub, bg="card_bg", fg="text_muted")

        status_row = tk.Frame(body)
        status_row.pack(fill=tk.X, pady=(0, 6))
        self._theme(status_row, bg="card_bg")

        self.status_dot = tk.Canvas(
            status_row, width=10, height=10,
            highlightthickness=0, bd=0,
        )
        self.status_dot.pack(side=tk.LEFT, padx=(0, 10))
        self._set_status_dot(self.colors["text_dim"])

        def _upd_dot(colors):
            self.status_dot.configure(bg=colors["card_bg"])
        self._theme_custom(_upd_dot)

        self.status_label = tk.Label(
            status_row, text="Ready to install",
            font=self.fonts["body"], anchor="w",
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._theme(self.status_label, bg="card_bg", fg="text")

        bar_w = w - 2 * 14 - 28
        self.progress = SmoothProgressBar(
            body, width=bar_w, height=6,
            bg_track=self.colors["track"],
            fg=self.colors["accent"],
            parent_bg=self.colors["card_bg"],
        )
        self.progress.pack(fill=tk.X, pady=(0, 10))

        def _upd_bar(colors):
            self.progress.update_colors(
                colors["card_bg"], colors["track"], colors["accent"]
            )
        self._theme_custom(_upd_bar)

        path_note = tk.Label(
            body,
            text=f"📁  Installs to  {self._tilde(self.base_dir)}",
            font=self.fonts["small"], anchor="w",
        )
        path_note.pack(fill=tk.X, pady=(0, 10))
        self._theme(path_note, bg="card_bg", fg="text_dim")

        self.action_button = RoundedButton(
            body, text="Install HellFire",
            command=self._on_action_clicked,
            width=170, height=42, radius=21,
            bg=self.colors["accent"],
            hover_bg=self.colors["accent_hover"],
            active_bg=self.colors["accent_active"],
            disabled_bg=self.colors["track"],
            disabled_fg=self.colors["text_dim"],
            fg="white",
            font=self.fonts["btn"],
            parent_bg=self.colors["card_bg"],
        )
        self.action_button.pack(anchor="w")

        def _upd_btn(colors):
            self.action_button.update_colors(
                parent_bg=colors["card_bg"],
                bg=colors["accent"],
                hover_bg=colors["accent_hover"],
                active_bg=colors["accent_active"],
                disabled_bg=colors["track"],
                disabled_fg=colors["text_dim"],
                fg="white",
            )
        self._theme_custom(_upd_btn)

    def _build_about_card(self, parent, w, h):
        card = RoundedFrame(
            parent, width=w, height=h,
            parent_bg=self.colors["bg"],
            card_bg=self.colors["card_bg"], radius=14,
        )
        card.pack(side=tk.LEFT)

        def _upd(colors):
            card.update_theme(colors["bg"], colors["card_bg"])
        self._theme_custom(_upd)

        body = tk.Frame(card.interior)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self._theme(body, bg="card_bg")

        self.avatar_canvas = tk.Canvas(
            body, width=72, height=72,
            highlightthickness=0, bd=0,
        )
        self.avatar_canvas.pack(pady=(8, 8))
        self._draw_avatar_placeholder()

        def _upd_avatar(colors):
            self.avatar_canvas.configure(bg=colors["card_bg"])
            self._draw_avatar_placeholder()
        self._theme_custom(_upd_avatar)

        name = tk.Label(body, text="HellFire Browser",
                        font=self.fonts["card_h"])
        name.pack()
        self._theme(name, bg="card_bg", fg="text")

        handle = tk.Label(body, text="@cyfarelabs",
                          font=self.fonts["small"])
        handle.pack(pady=(2, 8))
        self._theme(handle, bg="card_bg", fg="text_muted")

        divider = tk.Frame(body, height=1)
        divider.pack(fill=tk.X, padx=8, pady=(2, 10))
        self._theme(divider, bg="border")

        stats_row = tk.Frame(body)
        stats_row.pack()
        self._theme(stats_row, bg="card_bg")

        for i, (num, lbl) in enumerate(
            [("Custom", "BUILD"), ("Firefox", "BASE"), ("MPL", "LICENSE")]
        ):
            if i > 0:
                sep = tk.Frame(stats_row, width=1)
                sep.pack(side=tk.LEFT, fill=tk.Y, padx=10)
                self._theme(sep, bg="border")

            col = tk.Frame(stats_row)
            col.pack(side=tk.LEFT)
            self._theme(col, bg="card_bg")

            n = tk.Label(col, text=num, font=self.fonts["body_bold"])
            n.pack()
            self._theme(n, bg="card_bg", fg="text")

            l = tk.Label(col, text=lbl, font=self.fonts["tiny"])
            l.pack()
            self._theme(l, bg="card_bg", fg="text_dim")

    # ----- CTA card ---------------------------------------------------------

    def _build_cta_card(self, parent):
        inner_w = self.WINDOW_W - self.SIDEBAR_W - 2 * self.PADDING
        h = 92

        card = tk.Canvas(
            parent, width=inner_w, height=h,
            highlightthickness=0, bd=0,
        )
        card.pack()
        self._theme(card, bg="bg")

        self._cta_canvas = card
        self._cta_w = inner_w
        self._cta_h = h
        self._draw_cta(self.colors)

        def _upd(colors):
            card.configure(bg=colors["bg"])
            self._draw_cta(colors)
        self._theme_custom(_upd)

        card.bind("<Button-1>", self._on_cta_click)
        card.bind("<Enter>", lambda e: card.configure(cursor="hand2"))
        card.bind("<Leave>", lambda e: card.configure(cursor=""))

    def _draw_cta(self, colors):
        c = self._cta_canvas
        c.delete("all")
        w, h = self._cta_w, self._cta_h
        r = 14

        a = self._hex_to_rgb(colors["cta_grad_a"])
        b = self._hex_to_rgb(colors["cta_grad_b"])

        for y in range(h):
            if y < r:
                dy = r - y
                inner = r * r - dy * dy
                offset = r - (inner ** 0.5) if inner >= 0 else r
            elif y >= h - r:
                dy = y - (h - r - 1)
                inner = r * r - dy * dy
                offset = r - (inner ** 0.5) if inner >= 0 else r
            else:
                offset = 0

            t = y / max(1, h - 1)
            r_c = int(a[0] + (b[0] - a[0]) * t)
            g_c = int(a[1] + (b[1] - a[1]) * t)
            b_c = int(a[2] + (b[2] - a[2]) * t)
            color = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
            c.create_line(int(offset), y, int(w - offset), y, fill=color)

        for x, y, size in [
            (w - 80, 22, 8),
            (w - 50, 56, 5),
            (w - 130, 16, 4),
            (w - 110, 64, 6),
            (w - 170, 40, 5),
        ]:
            self._draw_sparkle(c, x, y, size, "#ffffff")

        c.create_text(
            28, 32, text="Optimized Firefox for GNU/Linux",
            font=self.fonts["cta_h"], fill="#ffffff", anchor="w",
        )
        c.create_text(
            28, 56, text="Custom-compiled Firefox · view source on GitHub →",
            font=self.fonts["cta_b"], fill="#e8e4ff", anchor="w",
        )

    @staticmethod
    def _draw_sparkle(canvas, cx, cy, size, color):
        s = size
        canvas.create_polygon(
            cx, cy - s,
            cx + s * 0.3, cy - s * 0.3,
            cx + s, cy,
            cx + s * 0.3, cy + s * 0.3,
            cx, cy + s,
            cx - s * 0.3, cy + s * 0.3,
            cx - s, cy,
            cx - s * 0.3, cy - s * 0.3,
            fill=color, outline="",
        )

    def _on_cta_click(self, _):
        webbrowser.open(self.social_links["GitHub"])

    # ----- avatar -----------------------------------------------------------

    def _draw_avatar_placeholder(self):
        c = self.avatar_canvas
        c.delete("all")
        c.configure(bg=self.colors["card_bg"])
        c.create_oval(2, 2, 70, 70,
                      outline=self.colors["accent"], width=2)
        c.create_oval(8, 8, 64, 64,
                      fill=self.colors["accent_soft"], outline="")
        c.create_text(36, 38, text="🔥",
                      font=pick_font(SANS_BOLD_PREFERENCES, 24, "bold"),
                      fill=self.colors["accent"])

    def _load_avatar(self):
        if not PIL_AVAILABLE:
            return

        def fetch():
            try:
                resp = requests.get(self.hero_image_url, timeout=10)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                size = 64
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (size, size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
                circle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                circle.paste(img, (0, 0), mask)
                photo = ImageTk.PhotoImage(circle)
                self.avatar_image = photo
                self.root.after(0, self._apply_avatar)
            except Exception as e:
                print(f"Avatar fetch failed: {e}", file=sys.stderr)

        threading.Thread(target=fetch, daemon=True).start()

    def _apply_avatar(self):
        c = self.avatar_canvas
        c.delete("all")
        c.configure(bg=self.colors["card_bg"])
        c.create_oval(1, 1, 71, 71,
                      outline=self.colors["accent"], width=2)
        c.create_image(36, 36, image=self.avatar_image)

    # ----- status helpers ----------------------------------------------------

    def _set_status_dot(self, color):
        self.status_dot.delete("all")
        self.status_dot.configure(bg=self.colors["card_bg"])
        self.status_dot.create_oval(0, 0, 10, 10, fill=color, outline=color)

    def update_status(self, message, *, dot=None):
        def apply():
            self.status_label.configure(text=message)
            if dot is not None:
                self._set_status_dot(dot)
        self.root.after(0, apply)

    def update_progress(self, fraction, text=None):
        def apply():
            self.progress.set_value(fraction)
            if text is not None:
                self.status_label.configure(text=text)
            self.percent_label.configure(text=f"{int(fraction * 100)}%")
        self.root.after(0, apply)

    def show_indeterminate(self, message):
        def apply():
            self.status_label.configure(text=message)
            self.percent_label.configure(text="")
            self.progress.start_indeterminate()
            self._set_status_dot(self.colors["accent"])
        self.root.after(0, apply)

    def stop_indeterminate(self):
        self.root.after(0, self.progress.stop_indeterminate)

    # ----- install flow ------------------------------------------------------

    def _on_action_clicked(self):
        if self._installed:
            return
        self.action_button.set_enabled(False)
        self.action_button.configure_text("Installing…")
        self._set_stat("status", value="Working", sub="In progress")
        threading.Thread(target=self._install_flow, daemon=True).start()

    def _install_flow(self):
        self.show_indeterminate(f"Searching for '{self.keyword}*.tar.xz'…")
        candidates = []
        for loc in [".", str(Path.home()), str(Path.home() / "Downloads")]:
            candidates += glob.glob(os.path.join(loc, f"{self.keyword}*.tar.xz"))

        if candidates:
            self.file_to_extract = max(candidates, key=os.path.getmtime)
            size_mb = os.path.getsize(self.file_to_extract) / (1024 * 1024)
            self.stop_indeterminate()
            self._set_stat("source", value="Local", sub="Cached file")
            self._set_stat("size", value=f"{size_mb:.1f} MB", sub="On disk")
            self.update_status(
                f"Found: {os.path.basename(self.file_to_extract)}",
                dot=self.colors["accent"],
            )
        else:
            self.show_indeterminate("Fetching latest release info…")
            self._set_stat("source", value="GitHub", sub="Fetching")
            url, name = self._latest_release_asset()
            if not url:
                self.stop_indeterminate()
                self._fail("No release found on GitHub.")
                return
            self.stop_indeterminate()
            self.update_status(f"Downloading {name}…",
                               dot=self.colors["accent"])
            ok, path = self._download(url, name)
            if not ok:
                self._fail(f"Download failed: {path}")
                return
            self.file_to_extract = path
            size_mb = os.path.getsize(path) / (1024 * 1024)
            self._set_stat("size", value=f"{size_mb:.1f} MB", sub="Downloaded")

        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._fail(f"Directory error: {e}")
            return

        self.update_status("Extracting archive…", dot=self.colors["accent"])
        ok, err = self._extract_archive(self.file_to_extract, self.base_dir)
        if not ok:
            self._fail(f"Extraction failed: {err}")
            return

        self.show_indeterminate("Finalizing setup…")
        if not self.firefox_bin.exists():
            self.stop_indeterminate()
            self._fail("'firefox' binary missing in archive.")
            return

        try:
            self.user_bin.mkdir(parents=True, exist_ok=True)
            if self.user_bin_symlink.exists() or self.user_bin_symlink.is_symlink():
                self.user_bin_symlink.unlink()
            self.user_bin_symlink.symlink_to(self.firefox_bin)

            icon_path = (
                self.base_dir / "firefox/browser/chrome/icons/default/default128.png"
            )
            desktop_entry = (
                "[Desktop Entry]\n"
                "Name=HellFire Browser\n"
                f"Exec={self.user_bin_symlink} %u\n"
                "Comment=Custom Firefox Compile\n"
                "Type=Application\n"
                f"Icon={icon_path}\n"
                "Terminal=false\n"
                "Categories=Network;WebBrowser;\n"
            )
            self.desktop_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.desktop_file_path.write_text(desktop_entry, encoding="utf-8")
        except Exception as e:
            self.stop_indeterminate()
            self._fail(f"Setup failed: {e}")
            return

        self.stop_indeterminate()
        self.update_progress(1.0, "Installation complete")
        self.update_status("Installation complete — launch from your menu",
                           dot=self.colors["success"])
        self._set_stat("status", value="Done", sub="Successful")
        self._installed = True
        self.root.after(0, self._mark_done)

    def _mark_done(self):
        self.action_button.configure_text("✓ Installed")
        self.action_button.set_enabled(False)

    def _fail(self, message):
        self.update_status(message, dot=self.colors["error"])
        self._set_stat("status", value="Failed", sub="Click retry")
        self.root.after(0, lambda: (
            self.action_button.set_enabled(True),
            self.action_button.configure_text("Retry"),
        ))

    # ----- network -----------------------------------------------------------

    def _latest_release_asset(self):
        api = "https://api.github.com/repos/CYFARE/HellFire/releases/latest"
        try:
            r = requests.get(api, timeout=12)
            r.raise_for_status()
            for a in r.json().get("assets", []):
                if a.get("name", "").endswith(".tar.xz"):
                    return a.get("browser_download_url"), a.get("name")
        except Exception:
            self.update_status("GitHub API error",
                               dot=self.colors["error"])
        return None, None

    def _download(self, url, filename):
        try:
            dest_dir = Path.home() / "Downloads"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / filename

            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        if total > 0:
                            frac = done / total
                            mb_d = done / (1024 * 1024)
                            mb_t = total / (1024 * 1024)
                            self.update_progress(
                                frac,
                                f"Downloading… {mb_d:.1f} / {mb_t:.1f} MB",
                            )
                            self._set_stat("size",
                                           value=f"{mb_t:.1f} MB",
                                           sub=f"{int(frac * 100)}% done")
            return True, str(dest)
        except Exception as e:
            return False, str(e)

    def _extract_archive(self, archive, out):
        try:
            with tarfile.open(archive, "r:xz") as tar:
                members = tar.getmembers()
                total = max(1, len(members))
                kwargs = {}
                if hasattr(tarfile, "data_filter"):
                    kwargs["filter"] = "data"
                step = max(1, total // 100)
                for i, member in enumerate(members):
                    tar.extract(member, path=out, **kwargs)
                    if i % step == 0 or i == total - 1:
                        frac = (i + 1) / total
                        self.update_progress(
                            frac, f"Extracting… {i + 1} / {total} files"
                        )
                        self._set_stat("files",
                                       value=f"{i + 1}",
                                       sub=f"of {total}")
            return True, ""
        except Exception as e:
            return False, str(e)

    # ----- stats refresh -----------------------------------------------------

    def _refresh_stats(self):
        """Pre-fetch release info so top cards show real data on launch."""
        # 1) Check for a local cached file first
        candidates = []
        for loc in [".", str(Path.home()), str(Path.home() / "Downloads")]:
            candidates += glob.glob(os.path.join(loc, f"{self.keyword}*.tar.xz"))

        if candidates:
            cached = max(candidates, key=os.path.getmtime)
            size_mb = os.path.getsize(cached) / (1024 * 1024)
            self._set_stat("source", value="Local", sub="Cached file")
            self._set_stat("size", value=f"{size_mb:.1f} MB", sub=os.path.basename(cached)[:26])
            self._set_stat("files", value="—", sub="Pending")
            self._set_stat("status", value="Ready", sub="Click install")
            return

        # 2) Nothing local — probe GitHub latest release
        self._set_stat("source", value="GitHub", sub="Checking…")
        url, name = self._latest_release_asset()
        if url and name:
            try:
                r = requests.head(url, timeout=10, allow_redirects=True)
                size = int(r.headers.get("content-length", 0))
                if size > 0:
                    size_mb = size / (1024 * 1024)
                    self._set_stat("size", value=f"{size_mb:.1f} MB", sub=name[:26])
                else:
                    self._set_stat("size", value="—", sub=name[:26])
                self._set_stat("source", value="GitHub", sub="Latest release")
            except Exception:
                self._set_stat("source", value="GitHub", sub="Latest release")
                self._set_stat("size", value="—", sub=name[:26])
        else:
            self._set_stat("source", value="GitHub", sub="Unavailable")
            self._set_stat("size", value="—", sub="API error")

        self._set_stat("files", value="—", sub="Pending")
        self._set_stat("status", value="Ready", sub="Click install")

    # ----- utils -------------------------------------------------------------

    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _tilde(path):
        try:
            return "~/" + str(path.relative_to(Path.home()))
        except ValueError:
            return str(path)


def main():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.25)
    except tk.TclError:
        pass
    HellFireInstallerTk(root)
    root.mainloop()


if __name__ == "__main__":
    main()

