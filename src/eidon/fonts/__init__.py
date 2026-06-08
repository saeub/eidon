from pathlib import Path

_fonts_path = Path(__file__).parent

FONTS = {
    "default": _fonts_path / "NotoSans-Regular.ttf",
    "monospace": _fonts_path / "NotoSansMono-Regular.ttf",
}
