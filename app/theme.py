"""Theme: Shared visual style for every Talk-To-AI window.

A dark, macOS-native look inspired by modern menu bar utilities: near-black
surfaces, softly rounded cards, quiet uppercase section labels, and a single
blue accent. Every window imports its colors, fonts, icons and stylesheet from
here so the app looks like one product.

Author: Allen Wu
Version: 1.1.0
"""

import os
import sys
import tempfile
from typing import Dict

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
COLORS: Dict[str, str] = {
    "window": "#1c1c1e",        # window and popover background
    "sidebar": "#202022",       # settings sidebar
    "card": "#28282b",          # grouped content
    "card_hover": "#303034",
    "field": "#353539",         # inputs, combos, secondary buttons
    "field_hover": "#3d3d42",
    "border": "#38383c",        # hairlines around cards
    "divider": "#323236",       # lines between rows inside a card
    "text": "#f2f2f4",
    "text_secondary": "#a1a1a8",
    "text_tertiary": "#6e6e75",
    "accent": "#2f7cf6",
    "accent_hover": "#4a8ef8",
    "accent_soft": "#1e3354",   # selected tab / subtle accent fill
    "green": "#30d158",
    "orange": "#ff9f0a",
    "red": "#ff453a",
    "red_soft": "#3a2324",
}

RADIUS_WINDOW: int = 16
RADIUS_CARD: int = 12
RADIUS_CONTROL: int = 8

# Platform font stacks: SF on macOS, Segoe on Windows, Inter elsewhere.
if sys.platform == "darwin":
    FONT_FAMILIES = [".AppleSystemUIFont", "SF Pro Text", "Helvetica Neue"]
    MONO_FAMILIES = ["Menlo", "Monaco"]
elif sys.platform.startswith("win"):
    FONT_FAMILIES = ["Segoe UI Variable Text", "Segoe UI"]
    MONO_FAMILIES = ["Cascadia Mono", "Consolas"]
else:
    FONT_FAMILIES = ["Inter", "Cantarell", "DejaVu Sans"]
    MONO_FAMILIES = ["DejaVu Sans Mono", "Liberation Mono"]


# ---------------------------------------------------------------------------
# Icons (simple 24x24 line icons, drawn for this app)
# ---------------------------------------------------------------------------
_ICON_PATHS: Dict[str, str] = {
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/>'
           '<path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    "keyboard": '<rect x="2.5" y="6" width="19" height="12" rx="2.5"/>'
                '<path d="M6.5 10h.01M10 10h.01M14 10h.01M17.5 10h.01M8 14h8"/>',
    "sparkles": '<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/>'
                '<path d="M18.5 15.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>',
    "wave": '<path d="M3 12h1.5M7 8v8M11 5v14M15 9v6M19 7v10M21.5 12H21"/>',
    "bubble": '<path d="M20 15a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/>',
    "gear": '<circle cx="12" cy="12" r="3"/>'
            '<path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 '
            '1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1'
            'a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1'
            'a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 '
            '1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3'
            'l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 '
            '0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    "power": '<path d="M12 3v8M6.3 7.3a8 8 0 1 0 11.4 0"/>',
    "trash": '<path d="M4 7h16M9 7V4.5h6V7M6.5 7l1 13h9l1-13M10 11v5M14 11v5"/>',
    "copy": '<rect x="8.5" y="8.5" width="12" height="12" rx="2.5"/>'
            '<path d="M15.5 8.5V6a2.5 2.5 0 0 0-2.5-2.5H6A2.5 2.5 0 0 0 3.5 6v7A2.5 2.5 0 0 0 6 15.5h2.5"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>'
           '<circle cx="12" cy="12" r="3"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor"/>',
    "chevrons": '<path d="M8 9.5l4-4 4 4M8 14.5l4 4 4-4"/>',
    "reset": '<path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4.5h4.5"/>',
}


def icon_pixmap(name: str, color: str = COLORS["text_secondary"], size: int = 18,
                stroke: float = 1.8) -> QPixmap:
    """Render one of the built-in line icons to a crisp, HiDPI-aware pixmap."""
    body = _ICON_PATHS.get(name, "").replace("currentColor", color)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</svg>'
    )
    app = QApplication.instance()
    ratio = app.devicePixelRatio() if app else 2.0
    ratio = max(ratio, 2.0)
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, pixmap.width(), pixmap.height()))
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def icon(name: str, color: str = COLORS["text_secondary"], size: int = 18) -> QIcon:
    """Return a QIcon for one of the built-in line icons."""
    return QIcon(icon_pixmap(name, color, size))


def tray_icon(recording: bool) -> QIcon:
    """Menu bar icon: a template mic when idle, an orange filled mic when recording.

    The idle icon is a mask ("template") image so macOS tints it to match a
    light or dark menu bar, like built-in status items.
    """
    if recording:
        body = (f'<rect x="8.5" y="2.5" width="7" height="12" rx="3.5" fill="{COLORS["orange"]}"/>'
                f'<path d="M5 11a7 7 0 0 0 14 0M12 18v3.5" stroke="{COLORS["orange"]}"/>')
    else:
        body = ('<rect x="9" y="3" width="6" height="11" rx="3" stroke="#000"/>'
                '<path d="M5 11a7 7 0 0 0 14 0M12 18v3.5" stroke="#000"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
    result = QIcon()
    for size in (16, 22, 32, 44, 64):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, size, size))
        painter.end()
        result.addPixmap(pixmap)
    result.setIsMask(not recording)
    return result


def ui_font(point_size: float = 13, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return the platform UI font at the given size and weight."""
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPointSizeF(point_size)
    font.setWeight(weight)
    return font


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------
c = COLORS
STYLESHEET: str = f"""
QWidget {{
    color: {c['text']};
    font-size: 13px;
    selection-background-color: {c['accent']};
    selection-color: #ffffff;
}}
QMainWindow, QWidget#Root {{ background: {c['window']}; }}
QToolTip {{
    background: {c['field']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 6px; padding: 4px 8px;
}}

/* ---- Text roles ---- */
QLabel {{ background: transparent; }}
QLabel[role="title"] {{ font-size: 20px; font-weight: 600; }}
QLabel[role="subtitle"] {{ color: {c['text_secondary']}; font-size: 12px; }}
QLabel[role="section"] {{
    color: {c['text_tertiary']}; font-size: 11px; font-weight: 600;
    letter-spacing: 1px; padding: 0 2px;
}}
QLabel[role="rowTitle"] {{ font-size: 13px; font-weight: 500; }}
QLabel[role="rowHint"] {{ color: {c['text_secondary']}; font-size: 11.5px; }}
QLabel[role="value"] {{ color: {c['text_secondary']}; font-size: 12px; font-weight: 500; }}
QLabel[role="muted"] {{ color: {c['text_tertiary']}; font-size: 11.5px; }}
QLabel[role="chip"] {{
    color: {c['text_secondary']}; background: {c['field']};
    border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 500;
}}
QLabel[role="error"] {{ color: {c['orange']}; font-size: 11.5px; }}
QLabel[role="success"] {{ color: {c['green']}; font-size: 11.5px; font-weight: 500; }}

/* ---- Cards ---- */
QFrame[role="card"] {{
    background: {c['card']}; border: 1px solid {c['border']};
    border-radius: {RADIUS_CARD}px;
}}
QFrame[role="divider"] {{ background: {c['divider']}; border: none; max-height: 1px; min-height: 1px; }}

/* ---- Inputs ---- */
QLineEdit {{
    background: {c['field']}; border: 1px solid transparent;
    border-radius: {RADIUS_CONTROL}px; padding: 6px 10px; min-height: 18px;
}}
QLineEdit:hover {{ background: {c['field_hover']}; }}
QLineEdit:focus {{ border: 1px solid {c['accent']}; background: {c['field']}; }}
QPushButton[role="keycap"] {{
    font-weight: 600; color: {c['text']}; background: {c['field']};
    border: 1px solid {c['border']}; border-bottom: 2px solid #26262a;
    border-radius: {RADIUS_CONTROL}px; padding: 5px 10px;
}}
QPushButton[role="keycap"]:hover {{ background: {c['field_hover']}; border-color: #4a4a50; }}
QPushButton[role="keycap"][recording="true"] {{
    background: {c['accent_soft']}; color: #ffffff;
    border: 1px solid {c['accent']}; border-bottom: 2px solid {c['accent']};
}}
QLineEdit::placeholder {{ color: {c['text_tertiary']}; }}

QComboBox {{
    background: {c['field']}; border: 1px solid transparent;
    border-radius: {RADIUS_CONTROL}px; padding: 6px 10px; min-height: 18px;
}}
QComboBox:hover {{ background: {c['field_hover']}; }}
QComboBox:focus {{ border: 1px solid {c['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url("__CHEVRON__"); width: 14px; height: 14px; margin-right: 8px; }}
QComboBox QAbstractItemView {{
    background: {c['field']}; border: 1px solid {c['border']}; border-radius: 8px;
    padding: 4px; outline: none;
    selection-background-color: {c['accent']}; selection-color: #ffffff;
}}

/* ---- Slider ---- */
QSlider::groove:horizontal {{ height: 6px; background: {c['field']}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: #e9e9ee; border: 1px solid #b9b9c0;
    width: 18px; height: 18px; margin: -7px 0; border-radius: 9px;
}}
QSlider::handle:horizontal:hover {{ background: #ffffff; }}

/* ---- Buttons ---- */
QPushButton {{
    background: {c['field']}; color: {c['text']};
    border: 1px solid transparent; border-radius: {RADIUS_CONTROL}px;
    padding: 7px 14px; font-weight: 500;
}}
QPushButton:hover {{ background: {c['field_hover']}; }}
QPushButton:pressed {{ background: {c['border']}; }}
QPushButton:focus {{ border: 1px solid {c['accent']}; }}
QPushButton[variant="primary"] {{ background: {c['accent']}; color: #ffffff; }}
QPushButton[variant="primary"]:hover {{ background: {c['accent_hover']}; }}
QPushButton[variant="outline"] {{
    background: transparent; border: 1px solid {c['border']}; padding: 9px 14px;
}}
QPushButton[variant="outline"]:hover {{ background: {c['card_hover']}; }}
QPushButton[variant="danger"] {{ background: {c['red_soft']}; color: {c['red']}; }}
QPushButton[variant="danger"]:hover {{ background: #4a2a2b; }}
QPushButton[variant="ghost"] {{ background: transparent; padding: 4px; border-radius: 6px; }}
QPushButton[variant="ghost"]:hover {{ background: {c['field']}; }}

/* ---- Sidebar ---- */
QListWidget#Sidebar {{
    background: {c['sidebar']}; border: none; outline: none; padding: 6px 10px;
}}
QListWidget#Sidebar::item {{
    padding: 7px 8px; margin: 1px 0; border-radius: 7px; color: {c['text']};
}}
QListWidget#Sidebar::item:hover {{ background: {c['card']}; }}
QListWidget#Sidebar::item:selected {{ background: {c['accent']}; color: #ffffff; }}

/* ---- Scrolling ---- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #4a4a50; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #5a5a62; }}
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; }}

QTextBrowser {{ background: transparent; border: none; }}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the shared font and stylesheet to the whole application."""
    app.setFont(ui_font(13))
    app.setStyle("Fusion")  # consistent rendering of styled widgets on every OS
    # Qt stylesheets load images from files, so write the combo-box chevron
    # to a temporary PNG once and point the stylesheet at it.
    chevron = os.path.join(tempfile.gettempdir(), "talktoai-chevron.png")
    icon_pixmap("chevrons", COLORS["text_secondary"], 14, 2.0).save(chevron)
    app.setStyleSheet(STYLESHEET.replace("__CHEVRON__", chevron.replace("\\", "/")))


def repolish(widget) -> None:
    """Re-apply the stylesheet after changing a dynamic property like `role`."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def with_alpha(hex_color: str, alpha: int) -> QColor:
    """Return a QColor from a hex string with the given 0-255 alpha."""
    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color
