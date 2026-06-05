from __future__ import annotations

from presentation_tool.models.schema import Position

# Widescreen slide dimensions (cm)
SLIDE_W_CM = 33.87
SLIDE_H_CM = 19.05

# Horizontal content margins
_MARGIN_X = 2.0
_CONTENT_W = SLIDE_W_CM - _MARGIN_X * 2  # 29.87

# Vertical zones
_TITLE_Y = 0.5
_TITLE_H = 2.0
_BODY_Y = 3.2
_BODY_H = SLIDE_H_CM - _BODY_Y - 1.5  # ~14.35, leaves room for footer

# Two-column split
_COL_GAP = 1.87
_COL_W = (_CONTENT_W - _COL_GAP) / 2  # ~14.0

# Layout position table: layout_type → role → (x, y, w, h)
_LAYOUT: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "cover": {
        "title":    (_MARGIN_X, 6.5,  _CONTENT_W, 4.0),
        "subtitle": (_MARGIN_X, 11.5, _CONTENT_W, 2.5),
    },
    "title_only": {
        "title": (_MARGIN_X, _TITLE_Y, _CONTENT_W, _TITLE_H),
    },
    "title_content": {
        "title": (_MARGIN_X, _TITLE_Y, _CONTENT_W, _TITLE_H),
        "body":  (_MARGIN_X, _BODY_Y,  _CONTENT_W, _BODY_H),
    },
    "two_column": {
        "title":      (_MARGIN_X,          _TITLE_Y, _CONTENT_W, _TITLE_H),
        "body_left":  (_MARGIN_X,          _BODY_Y,  _COL_W,     _BODY_H),
        "body_right": (_MARGIN_X + _COL_W + _COL_GAP, _BODY_Y, _COL_W, _BODY_H),
    },
    "title_chart": {
        "title": (_MARGIN_X, _TITLE_Y, _CONTENT_W, _TITLE_H),
        "chart": (2.5,       _BODY_Y,  _CONTENT_W - 0.5, _BODY_H),
    },
    "title_table": {
        "title": (_MARGIN_X, _TITLE_Y, _CONTENT_W, _TITLE_H),
        "table": (_MARGIN_X, _BODY_Y,  _CONTENT_W, _BODY_H),
    },
    "title_image": {
        "title": (_MARGIN_X, _TITLE_Y, _CONTENT_W, _TITLE_H),
        "image": (6.0,       _BODY_Y,  _CONTENT_W - 8.0, _BODY_H - 0.35),
    },
    "blank": {},
}

_FALLBACK: tuple[float, float, float, float] = (_MARGIN_X, _BODY_Y, _CONTENT_W, _BODY_H)


def get_position(layout_type: str, role: str) -> Position:
    """Return the canonical Position for a named role in a given layout."""
    coords = _LAYOUT.get(layout_type, {}).get(role, _FALLBACK)
    x, y, w, h = coords
    return Position(x=x, y=y, w=w, h=h)


def get_positions(layout_type: str) -> dict[str, Position]:
    """Return all named positions for the given layout type."""
    slots = _LAYOUT.get(layout_type, {})
    return {role: Position(x=x, y=y, w=w, h=h) for role, (x, y, w, h) in slots.items()}


def layout_types() -> list[str]:
    """Return the list of all supported layout type names."""
    return list(_LAYOUT.keys())
