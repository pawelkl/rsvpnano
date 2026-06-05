#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import pathlib

from PIL import Image, ImageDraw, ImageFont

from generate_embedded_serif_font import CUSTOM_GLYPH_CODEPOINTS


DEFAULT_POINT_SIZE = 52
CANVAS_WIDTH = 112
CANVAS_HEIGHT = 128
ORIGIN_X = 10
BASELINE_Y = 76
ALPHA_THRESHOLD = 16
FONT_TOP_PADDING = 4
FONT_BOTTOM_PADDING = 2
DEFAULT_FIRST_CHAR = 1
DEFAULT_LAST_CHAR = 255


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an embedded font header from a TTF file.")
    parser.add_argument("--font-file", type=pathlib.Path, required=True)
    parser.add_argument("--point-size", type=int, default=DEFAULT_POINT_SIZE)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--symbol-prefix", required=True)
    parser.add_argument("--source-name", default="")
    parser.add_argument("--first-char", type=int, default=DEFAULT_FIRST_CHAR)
    parser.add_argument("--last-char", type=int, default=DEFAULT_LAST_CHAR)
    return parser.parse_args()


def display_codepoint_for_slot(slot: int) -> int:
    return CUSTOM_GLYPH_CODEPOINTS.get(slot, slot)


def glyph_comment_for_slot(slot: int) -> str:
    mapped_codepoint = CUSTOM_GLYPH_CODEPOINTS.get(slot)
    if mapped_codepoint is None:
        return ascii(chr(slot))
    return f"slot 0x{slot:02X} -> U+{mapped_codepoint:04X}"


def render_glyph(font: ImageFont.FreeTypeFont, slot: int) -> Image.Image:
    image = Image.new("L", (CANVAS_WIDTH, CANVAS_HEIGHT), 0)
    draw = ImageDraw.Draw(image)
    draw.text((ORIGIN_X, BASELINE_Y), chr(display_codepoint_for_slot(slot)), font=font, fill=255,
              anchor="ls")
    return image


def alpha_at(image: Image.Image, x: int, y: int) -> int:
    return int(image.getpixel((x, y)))


def main() -> None:
    args = parse_args()
    if not (0 <= args.first_char <= args.last_char <= 255):
        raise ValueError("Character range must satisfy 0 <= first-char <= last-char <= 255")

    font = ImageFont.truetype(str(args.font_file), args.point_size)
    glyph_images: dict[int, Image.Image] = {}
    global_top = CANVAS_HEIGHT
    global_bottom = -1

    for code in range(args.first_char, args.last_char + 1):
        image = render_glyph(font, code)
        glyph_images[code] = image
        for y in range(CANVAS_HEIGHT):
            for x in range(CANVAS_WIDTH):
                if alpha_at(image, x, y) > ALPHA_THRESHOLD:
                    global_top = min(global_top, y)
                    global_bottom = max(global_bottom, y)

    if global_bottom < global_top:
        raise RuntimeError("Failed to detect any font pixels")

    crop_top = max(0, global_top - FONT_TOP_PADDING)
    crop_bottom = min(CANVAS_HEIGHT - 1, global_bottom + FONT_BOTTOM_PADDING)
    font_height = crop_bottom - crop_top + 1
    bitmap_bytes: list[int] = []
    glyph_entries: list[str] = []

    for code in range(args.first_char, args.last_char + 1):
        image = glyph_images[code]
        min_x = CANVAS_WIDTH
        max_x = -1
        for y in range(crop_top, crop_bottom + 1):
            for x in range(CANVAS_WIDTH):
                if alpha_at(image, x, y) > ALPHA_THRESHOLD:
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)

        bitmap_offset = len(bitmap_bytes)
        codepoint = display_codepoint_for_slot(code)
        x_advance = max(1, int(math.floor(font.getlength(chr(codepoint)) + 0.5)))

        if max_x >= min_x:
            glyph_width = max_x - min_x + 1
            for y in range(crop_top, crop_bottom + 1):
                for x in range(min_x, max_x + 1):
                    alpha = alpha_at(image, x, y)
                    bitmap_bytes.append(alpha if alpha > ALPHA_THRESHOLD else 0)
            x_offset = min_x - ORIGIN_X
        else:
            glyph_width = 0
            x_offset = 0

        glyph_entries.append(
            "    "
            + "{"
            + f"{bitmap_offset}, {x_offset}, {glyph_width}, {x_advance}"
            + "}, "
            + f"// {glyph_comment_for_slot(code)}"
        )

    source_name = args.source_name or args.font_file.name
    lines: list[str] = [
        "#pragma once",
        "",
        "#include <Arduino.h>",
        "",
        "// Generated from a TrueType font and embedded as glyph data.",
        f"// Source font: {source_name} at {args.point_size} pt",
        "",
        f"struct {args.symbol_prefix}Glyph " + "{",
        "  uint32_t bitmapOffset;",
        "  int8_t xOffset;",
        "  uint8_t width;",
        "  uint8_t xAdvance;",
        "};",
        "",
        f"constexpr uint8_t k{args.symbol_prefix}FirstChar = {args.first_char};",
        f"constexpr uint8_t k{args.symbol_prefix}LastChar = {args.last_char};",
        f"constexpr uint8_t k{args.symbol_prefix}Height = {font_height};",
        "",
        f"static const uint8_t k{args.symbol_prefix}Bitmaps[] PROGMEM = " + "{",
    ]

    for offset in range(0, len(bitmap_bytes), 16):
        chunk = bitmap_bytes[offset:offset + 16]
        lines.append("    " + ", ".join(f"{value:3d}" for value in chunk) + ",")

    lines += [
        "};",
        "",
        f"static const {args.symbol_prefix}Glyph k{args.symbol_prefix}Glyphs[] PROGMEM = " + "{",
        *glyph_entries,
        "};",
        "",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
