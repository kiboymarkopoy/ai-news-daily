"""Tests for kiboy.thumbnail — accent markup, image sniffing, gradient."""

import io

import numpy as np
import pytest
from PIL import Image

from kiboy.thumbnail import (
    tokenize_accents,
    strip_accent_markup,
    wrap_accent_tokens,
    _sniff_image_ext,
    _create_gradient_background,
    auto_wrap_text,
)
from PIL import ImageDraw, ImageFont


class TestTokenizeAccents:
    def test_basic_markup(self):
        out = tokenize_accents("**Anthropic** kuasai **AI DUNIA**")
        assert out == [
            ("Anthropic", True), ("kuasai", False),
            ("AI", True), ("DUNIA", True),
        ]

    def test_no_markup_all_plain(self):
        out = tokenize_accents("berita biasa saja")
        assert all(not accent for _w, accent in out)

    def test_all_accent(self):
        out = tokenize_accents("**semua hijau total**")
        assert all(accent for _w, accent in out)

    def test_empty(self):
        assert tokenize_accents("") == []

    def test_leading_and_trailing_plain(self):
        out = tokenize_accents("awal **tengah** akhir")
        assert out == [("awal", False), ("tengah", True), ("akhir", False)]


class TestStripAccentMarkup:
    def test_removes_markers(self):
        assert strip_accent_markup("**A** b **C**") == "A b C"

    def test_no_markers_unchanged(self):
        assert strip_accent_markup("plain text") == "plain text"


class TestWrapAccentTokens:
    def test_preserves_accent_flag_across_wrap(self):
        font = ImageFont.load_default()
        img = Image.new("RGB", (200, 100))
        draw = ImageDraw.Draw(img)
        tokens = [("aaa", True), ("bbb", False), ("ccc", True)]
        lines = wrap_accent_tokens(tokens, 10_000, font, draw)
        # Wide max_width → single line, flags preserved
        flat = [t for line in lines for t in line]
        assert flat == tokens

    def test_empty(self):
        font = ImageFont.load_default()
        img = Image.new("RGB", (200, 100))
        draw = ImageDraw.Draw(img)
        assert wrap_accent_tokens([], 100, font, draw) == []


class TestSniffImageExt:
    def test_detects_png(self):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="PNG")
        assert _sniff_image_ext(buf.getvalue()) == "png"

    def test_detects_jpeg_normalized(self):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="JPEG")
        assert _sniff_image_ext(buf.getvalue()) == "jpg"

    def test_rejects_svg_xml_bytes(self):
        svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
        assert _sniff_image_ext(svg) is None

    def test_rejects_html(self):
        assert _sniff_image_ext(b"<!DOCTYPE html><html></html>") is None

    def test_rejects_garbage(self):
        assert _sniff_image_ext(b"not an image at all") is None


class TestGradientBackground:
    def test_dimensions(self):
        img = _create_gradient_background(1080, 1350)
        assert img.size == (1080, 1350)
        assert img.mode == "RGB"

    def test_top_brighter_than_bottom(self):
        arr = np.array(_create_gradient_background(100, 200))
        top_mean = arr[:10].mean()
        bottom_mean = arr[-10:].mean()
        assert top_mean > bottom_mean  # dark transition downward


class TestAutoWrapText:
    def test_wraps_long_text(self):
        font = ImageFont.load_default()
        img = Image.new("RGB", (200, 100))
        draw = ImageDraw.Draw(img)
        # Narrow width forces multiple lines.
        lines = auto_wrap_text("word " * 20, 50, font, draw)
        assert len(lines) > 1

    def test_empty_returns_empty(self):
        font = ImageFont.load_default()
        img = Image.new("RGB", (200, 100))
        draw = ImageDraw.Draw(img)
        assert auto_wrap_text("", 100, font, draw) == []
