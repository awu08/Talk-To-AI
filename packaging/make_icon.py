"""Draw the Talk-To-AI app icon and write a macOS .iconset folder.

Usage:
    python packaging/make_icon.py build/icon

Creates build/icon/Talk-To-AI.iconset/ (all the sizes macOS wants) and
build/icon/Talk-To-AI.png (1024 px). build_app.sh then turns the iconset
into Talk-To-AI.icns with Apple's `iconutil`.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # no window needed

from PyQt6.QtCore import QByteArray, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtSvg import QSvgRenderer

BLUE_TOP = "#4a8ef8"
BLUE_BOTTOM = "#1f5fd6"

# Same microphone as the in-app icons, drawn bolder for a large icon
MIC_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="#ffffff" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="8.6" y="2.6" width="6.8" height="11.6" rx="3.4" fill="#ffffff"/>'
    '<path d="M5 11a7 7 0 0 0 14 0M12 18v3.2M8.8 21.2h6.4"/></svg>'
)


def draw_icon(size: int = 1024) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # macOS icon grid: the shape fills ~80% of the canvas, corners ~22.5% radius
    inset = size * 0.1
    body = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)
    radius = body.width() * 0.225
    path = QPainterPath()
    path.addRoundedRect(body, radius, radius)

    # soft drop shadow
    for i, alpha in enumerate((28, 18, 10)):
        shadow = QPainterPath()
        offset = size * (0.008 + 0.006 * i)
        shadow.addRoundedRect(body.translated(0, offset).adjusted(-offset / 2, 0, offset / 2, 0),
                              radius, radius)
        p.fillPath(shadow, QColor(0, 0, 0, alpha))

    gradient = QLinearGradient(QPointF(0, body.top()), QPointF(0, body.bottom()))
    gradient.setColorAt(0, QColor(BLUE_TOP))
    gradient.setColorAt(1, QColor(BLUE_BOTTOM))
    p.fillPath(path, gradient)

    # subtle top highlight
    highlight = QLinearGradient(QPointF(0, body.top()), QPointF(0, body.center().y()))
    highlight.setColorAt(0, QColor(255, 255, 255, 46))
    highlight.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillPath(path, highlight)

    mic_size = body.width() * 0.56
    mic_rect = QRectF(body.center().x() - mic_size / 2, body.center().y() - mic_size / 2,
                      mic_size, mic_size)
    QSvgRenderer(QByteArray(MIC_SVG.encode())).render(p, mic_rect)
    p.end()
    return image


def main(out_dir: str) -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841
    iconset = os.path.join(out_dir, "Talk-To-AI.iconset")
    os.makedirs(iconset, exist_ok=True)
    master = draw_icon(1024)
    master.save(os.path.join(out_dir, "Talk-To-AI.png"))
    for points in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            pixels = points * scale
            name = f"icon_{points}x{points}{'@2x' if scale == 2 else ''}.png"
            scaled = master.scaled(pixels, pixels, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            scaled.save(os.path.join(iconset, name))
    print(f"Icon written to {iconset}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build/icon")
