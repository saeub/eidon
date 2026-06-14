from __future__ import annotations

import csv
import re
import warnings
from pathlib import Path
from typing import Any, Generator, Literal
from collections import defaultdict
from pprint import pprint

from PIL import Image, ImageDraw, ImageFont


def wrap_text(
    text: str, font: ImageFont.FreeTypeFont, max_width: float
) -> Generator[str, None, None]:
    words = re.findall(r"([\S\u00a0]+)([^\S\u00a0]*)", text)
    line = ""

    # TODO: Remove first line if it is empty
    for word, whitespace in words:
        # Add new word, wrap line if it's too long
        if font.getlength(line + word) > max_width:
            yield line.rstrip()
            line = word
        else:
            line += word
        # Add whitespace, create new line if it's a newline
        for ws in whitespace:
            if ws == "\n":  # TODO: Handle CR/CRLF
                yield line.rstrip()
                line = ""
            else:
                line += ws
    # Last line
    if line:
        yield line.rstrip()


class Area:
    def __init__(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        *,
        section: str | None = None,
        line: int | None = None,
        content: str | None = None,
    ):
        assert right >= left, "`right` must be greater than or equal to `left`"
        assert bottom >= top, "`bottom` must be greater than or equal to `top`"
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.section = section
        self.line = line
        self.content = content

    def __repr__(self) -> str:
        args = self.asdict()
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        return f"{self.__class__.__name__}({args_str})"

    def asdict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "section": self.section,
            "line": self.line,
            "content": self.content,
        }

    @property
    def width(self) -> float:
        return self.right - self.left

    @width.setter
    def width(self, value: float):
        self.right = self.left + value

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @height.setter
    def height(self, value: float):
        self.bottom = self.top + value

    @property
    def coords(self) -> tuple[float, float, float, float]:
        return self.left, self.top, self.right, self.bottom

    @property
    def xywh(self) -> tuple[float, float, float, float]:
        return self.left, self.top, self.width, self.height

    @classmethod
    def merge(
        cls,
        boxes: list[tuple[float, float, float, float]],
        *,
        left: float | None = None,
        top: float | None = None,
        right: float | None = None,
        bottom: float | None = None,
    ) -> Area:
        if left is None:
            left = min(box.left for box in boxes)
        if top is None:
            top = min(box.top for box in boxes)
        if right is None:
            right = max(box.right for box in boxes)
        if bottom is None:
            bottom = max(box.bottom for box in boxes)
        return cls(
            left,
            top,
            right,
            bottom,
            line=boxes[0].line,
            content="".join(box.content for box in boxes if box.content),
        )


class TextImage:
    """A stimulus image with areas of interest."""

    generate_area_images = False

    def __init__(
        self,
        image: Image.Image,
        areas: dict[str, list[Area]],
        areas_start_index: dict[str, int] | None = None,
    ):
        self.image = image
        self.areas = areas

        if areas_start_index is None:
            areas_start_index = {}
        assert set(areas_start_index.keys()).issubset(
            set(areas.keys())
        ), "areas_start_index keys must be a subset of areas keys"
        self.areas_start_index = areas_start_index
        for area_type in self.areas:
            if area_type not in self.areas_start_index:
                # Start area indices at 0 by default
                self.areas_start_index[area_type] = 0

        self._imgpath = None

    @property
    def imgpath(self) -> str:
        if self._imgpath is None:
            raise ValueError("TextImage has not been saved yet.")
        return self._imgpath

    def save(
        self,
        experiment_path: Path | str,
        stem: str,
        area_images: bool | None = None,
    ):
        """Save the image (as PNG), areas (as CSV), and (optionally) images with
        outlined areas (as PNG) in the specified directory."""
        if area_images is None:
            area_images = self.generate_area_images

        experiment_path = Path(experiment_path)

        # Image
        image_path = experiment_path / "stimuli" / f"{stem}.png"
        self._imgpath = str(image_path.relative_to(experiment_path))
        self.image.save(image_path)

        # Areas
        fieldnames = [
            "index",
            "left",
            "top",
            "right",
            "bottom",
            "section",
            "line",
            "content",
        ]
        for area_type in self.areas:
            with open(
                experiment_path / "stimuli" / f"{stem}.{area_type}.csv", "w"
            ) as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                area_index = self.areas_start_index[area_type]
                for area in self.areas[area_type]:
                    writer.writerow({"index": area_index} | area.asdict())
                    area_index += 1

        # Image with outlined areas
        if area_images:
            for area_type in self.areas:
                image = self.image.copy()
                draw = ImageDraw.Draw(image)
                for area in self.areas[area_type]:
                    draw.rectangle(area.coords, outline="red", width=1)
                image.save(experiment_path / "stimuli" / f"{stem}.{area_type}.png")


def draw_text(
    draw: ImageDraw.ImageDraw,
    text: str | list[str],
    x: float,
    y: float,
    max_width: float,
    font: ImageFont.FreeTypeFont,
    align: Literal["left", "center", "right"] = "left",
    line_spacing: float = 1.0,
    extend_word_areas: bool = True,
    extend_char_areas: bool = True,
    max_height: float = float("inf"),
    vertical_align: Literal["top", "center", "bottom"] = "top",
    color: tuple[int, int, int] = (0, 0, 0),
    raise_on_overflow: bool = False,
) -> tuple[list[Area], list[Area], Area]:
    """Draw text on an image and return character, word, and text areas.

    Args:
        image: Image to draw on.
        text: Text to draw (single string or list of one string per line).
        x: X coordinate of the top-left corner of the text.
        y: Y coordinate of the top-left corner of the text.
        max_width: Maximum width of the text.
        font: Font to use for rendering.
        align: Text alignment ('left', 'center', 'right').
        line_spacing: Line spacing as a factor of line height.
        extend_word_areas: Extend word areas to cover whitespace around words.
        extend_char_areas: Extend character areas to cover whitespace around characters.
        max_height: Maximum height of the text (warning if exceeded).
        vertical_align: Vertical alignment within max_height ('top', 'center', 'bottom').
        color: Text color as an RGB tuple.
        raise_on_overflow: Whether to raise an error if text exceeds max_height.

    Returns:
        A tuple containing a list of character areas, a list of word areas, and a text area.
    """
    if isinstance(text, str):
        lines = list(wrap_text(text, font, max_width))
    else:
        lines = text

    line_left = x
    line_top = y
    font_ascent, font_descent = font.getmetrics()
    line_height = (font_ascent + font_descent) * line_spacing
    line_offset = (line_height - font_ascent - font_descent) / 2

    total_height = line_height * len(lines)
    if total_height > max_height:
        message = f"Text height {total_height} exceeds max_height {max_height}."
        if raise_on_overflow:
            raise ValueError(message)
        warnings.warn(message)

    if vertical_align != "top":
        assert max_height < float(
            "inf"
        ), f"max_height must be specified when vertical_align is {vertical_align:r}"
    if vertical_align == "center":
        line_top += (max_height - total_height) / 2
    elif vertical_align == "bottom":
        line_top += max_height - total_height

    char_areas = []
    word_areas = []
    text_area = Area(
        line_left,
        line_top,
        line_left + max_width,
        line_top + total_height,
    )

    for line_num, line in enumerate(lines):
        line_width = font.getlength(line)
        if align == "left":
            line_indent = 0
        elif align == "center":
            line_indent = (max_width - line_width) / 2
        elif align == "right":
            line_indent = max_width - line_width
        else:
            raise NotImplementedError(f"Alignment {align!r} not supported")

        draw.text(
            (line_left + line_indent, line_top + line_offset),
            line,
            font=font,
            fill=tuple(color),
        )

        line_char_areas = []
        word_start_index = 0
        for i, char in enumerate(line):
            _, char_top, char_width, char_bottom = font.getbbox(char)
            char_left = font.getlength(line[: i + 1]) - char_width
            char_area = Area(
                line_left + line_indent + char_left,
                line_top + char_top + line_offset,
                line_left + line_indent + char_left + char_width,
                line_top + char_bottom + line_offset,
                line=line_num,
                content=char,
            )
            char_left += char_width
            line_char_areas.append(char_area)

            if char.isspace():  # End of word
                if word_start_index < i:
                    word_area = Area.merge(
                        line_char_areas[word_start_index:i],
                        top=line_top if extend_word_areas else None,
                        bottom=line_top + line_height if extend_word_areas else None,
                    )
                    word_areas.append(word_area)
                word_start_index = i + 1
        if word_start_index < len(line):  # Last word
            word_area = Area.merge(
                line_char_areas[word_start_index:],
                top=line_top if extend_word_areas else None,
                bottom=line_top + line_height if extend_word_areas else None,
            )
            word_areas.append(word_area)
            word_start_index = i + 1

        if extend_char_areas:
            for char_area in line_char_areas:
                char_area.top = line_top
                char_area.bottom = line_top + line_height

        char_areas.extend(line_char_areas)
        line_top += line_height

    if extend_word_areas:
        whitespace_length = font.getlength(" ")
        dummy = Area(0, 0, 0, 0, line=None)
        for word1, word2 in zip([dummy] + word_areas, word_areas + [dummy]):
            # Extend adjacent words to meet in the middle of the whitespace
            if word1.line == word2.line:
                word1.right = word2.left = (word1.right + word2.left) / 2

            # Extend first and last words towards the edges of the image
            else:
                word1.right += whitespace_length
                word2.left -= whitespace_length

    return char_areas, word_areas, text_area


def generate_text_pages(
    text: str,
    width: int,
    height: int,
    margin: float,
    font_path: str,
    font_size: float,
    align: Literal["left", "center", "right"] = "left",
    vertical_align: Literal["top", "center", "bottom"] = "top",
    line_spacing: float = 1.0,
    background_color: tuple[int, int, int] = (255, 255, 255),
    text_color: tuple[int, int, int] = (0, 0, 0),
    extend_word_areas: bool = True,
) -> list[TextImage]:
    """Generate text stimulus images with character- and word-level areas of interest.

    Args:
        text: Text to render.
        width: Image width in pixels.
        height: Image height in pixels.
        margin: Margin around text in pixels.
        font_path: Font name or path to TrueType/OpenType font file.
        font_size: Font size in pixels.
        align: Text alignment ('left', 'center', 'right').
        vertical_align: Vertical alignment of the content within the image ('top', 'center', 'bottom').
        line_spacing: Line spacing as a factor of line height.
        background_color: Background color as an RGB tuple.
        text_color: Text color as an RGB tuple.
        extend_word_areas: Extend word areas to cover whitespace between words.

    Returns:
        The generated TextImages.
    """
    text_width = width - 2 * margin
    text_height = height - 2 * margin

    font = ImageFont.truetype(font_path, font_size)

    font_ascent, font_descent = font.getmetrics()
    line_height = (font_ascent + font_descent) * line_spacing
    num_lines_per_page = int(text_height / line_height)
    lines = list(wrap_text(text, font, text_width))
    pages = [[]]
    for line in lines:
        if len(pages[-1]) >= num_lines_per_page:
            # Add new page
            pages.append([])
            # Add line to new page if it's not empty
            if line.strip():
                pages[-1].append(line)
        else:
            # Add line to current page
            pages[-1].append(line)

    images = []
    char_index_start = 0
    word_index_start = 0
    for page_index, page_lines in enumerate(pages):
        image = Image.new("RGB", (width, height), tuple(background_color))
        draw = ImageDraw.Draw(image)
        char_areas, word_areas, text_area = draw_text(
            draw,
            page_lines,
            margin,
            margin,
            text_width,
            font,
            align=align,
            line_spacing=line_spacing,
            extend_word_areas=extend_word_areas,
            max_height=text_height,
            vertical_align=vertical_align,
            color=text_color,
        )
        images.append(
            TextImage(
                image,
                areas={"char": char_areas, "word": word_areas, "page": [text_area]},
                areas_start_index={
                    "char": char_index_start,
                    "word": word_index_start,
                    "page": page_index,
                },
            )
        )
        char_index_start += len(char_areas)
        word_index_start += len(word_areas)

    return images


def generate_mcq_page(
    question: str,
    options: list[str],
    width: int,
    height: int,
    margin: float,
    font_path: str,
    font_size: float,
    vertical_align: Literal["top", "center", "bottom"] = "top",
    line_spacing: float = 1.0,
    background_color: tuple[int, int, int] = (255, 255, 255),
    text_color: tuple[int, int, int] = (0, 0, 0),
    extend_word_areas: bool = True,
    option_layout: Literal["horizontal", "vertical", "diamond"] = "horizontal",
) -> tuple[TextImage, list[tuple[float, float, float, float]]]:
    """Generate stimulus image for a MultipleChoiceQuestion stage listing answer options horizontally.

    Args:
        question: Question text to render.
        options: List of answer options.
        width: Image width in pixels.
        height: Image height in pixels.
        margin: Margin around text in pixels.
        font_path: Font name or path to TrueType/OpenType font file.
        font_size: Font size in pixels.
        vertical_align: Vertical alignment of the content within the image ('top', 'center', 'bottom').
        line_spacing: Line spacing as a factor of line height.
        text_color: Text color as an RGB tuple.
        background_color: Background color as an RGB tuple.
        extend_word_areas: Extend word areas to cover whitespace between words.
        option_layout: Layout of answer options ('horizontal', 'diamond').
            'diamond' arranges four options in a diamond shape with the first option at the top,
            the second and third options in the middle row, and the fourth option at the bottom.

    Returns:
        A tuple containing the generated TextImage and the option boxes (x, y, width, height).
    """
    text_width = width - 2 * margin
    text_height = height - 2 * margin

    image = Image.new("RGB", (width, height), tuple(background_color))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)

    num_question_lines = len(list(wrap_text(question, font, text_width)))

    if option_layout == "horizontal":
        option_width = text_width / len(options)
    elif option_layout == "diamond":
        assert len(options) == 4, "Diamond option layout requires exactly 4 options"
        option_width = text_width / 2
    else:
        raise NotImplementedError(f"Option layout {option_layout!r} not supported")
    num_option_lines = [
        len(list(wrap_text(option, font, option_width))) for option in options
    ]

    font_ascent, font_descent = font.getmetrics()
    line_height = (font_ascent + font_descent) * line_spacing
    if option_layout == "horizontal":
        option_height = line_height * max(num_option_lines)
        total_height = num_question_lines * line_height + option_height
    elif option_layout == "diamond":
        option_height = line_height * max(num_option_lines)
        total_height = (num_question_lines + 1) * line_height + 3 * option_height
    question_left = margin
    question_top = margin
    question_bottom = question_top + num_question_lines * line_height
    question_width = text_width
    if vertical_align == "center":
        question_top += (text_height - total_height) / 2
    elif vertical_align == "bottom":
        question_top += text_height - total_height

    char_areas = []
    word_areas = []
    section_areas = []

    # Draw question
    question_char_areas, question_word_areas, question_area = draw_text(
        draw,
        question,
        question_left,
        question_top,
        question_width,
        font,
        line_spacing=line_spacing,
        extend_word_areas=extend_word_areas,
        max_height=text_height,
        color=text_color,
    )
    for char_area in question_char_areas:
        char_area.section = "question"
    for word_area in question_word_areas:
        word_area.section = "question"
    question_area.content = "question"
    char_areas.extend(question_char_areas)
    word_areas.extend(question_word_areas)
    section_areas.append(question_area)

    # Draw answer options
    option_boxes = []
    if option_layout == "horizontal":
        option_left = margin + 2 * font_size
        option_top = question_area.bottom + line_height
        for option_index, option in enumerate(options):
            # Draw option text
            option_char_areas, option_word_areas, option_area = draw_text(
                draw,
                option,
                option_left,
                option_top,
                option_width,
                font,
                align="center",
                line_spacing=line_spacing,
                extend_word_areas=extend_word_areas,
                color=text_color,
            )
            for char_area in option_char_areas:
                char_area.section = f"option:{option_index}"
            for word_area in option_word_areas:
                word_area.section = f"option:{option_index}"
            option_area.content = f"option:{option_index}"
            char_areas.extend(option_char_areas)
            word_areas.extend(option_word_areas)
            section_areas.append(option_area)
            option_boxes.append((option_left, option_top, option_width, option_height))
            option_left += option_width

    elif option_layout == "diamond":
        option_centers = [
            (width / 2, line_height * 2),
            (margin + option_width / 2, line_height * 2 + option_height),
            (width - margin - option_width / 2, line_height * 2 + option_height),
            (width / 2, line_height * 2 + option_height * 2),
        ]
        for option_index, (option, option_center) in enumerate(
            zip(options, option_centers)
        ):
            option_left = option_center[0] - option_width / 2
            option_top = question_bottom + option_center[1] - option_height / 2
            option_char_areas, option_word_areas, option_area = draw_text(
                draw,
                option,
                option_left,
                option_top,
                option_width,
                max_height=option_height,
                font=font,
                align="center",
                vertical_align="center",
                line_spacing=line_spacing,
                extend_word_areas=extend_word_areas,
                color=text_color,
            )
            for char_area in option_char_areas:
                char_area.section = f"option:{option_index}"
            for word_area in option_word_areas:
                word_area.section = f"option:{option_index}"
            option_area.content = f"option:{option_index}"
            char_areas.extend(option_char_areas)
            word_areas.extend(option_word_areas)
            option_boxes.append((option_left, option_top, option_width, option_height))
            section_areas.append(option_area)

    return (
        TextImage(
            image, {"char": char_areas, "word": word_areas, "section": section_areas}
        ),
        option_boxes,
    )


def generate_cursor_mcq_page(
    question: str,
    options: list[str],
    width: int,
    height: int,
    margin: float,
    font_path: str,
    font_size: float,
    vertical_align: Literal["top", "center", "bottom"] = "top",
    line_spacing: float = 1.0,
    background_color: tuple[int, int, int] = (255, 255, 255),
    text_color: tuple[int, int, int] = (0, 0, 0),
    extend_word_areas: bool = True,
) -> tuple[TextImage, list[tuple[float, float]]]:
    """Generate stimulus image for a CursorMultipleChoiceQuestion stage with circles indicating cursor locations.

    Args:
        question: Question text to render.
        options: List of answer options.
        width: Image width in pixels.
        height: Image height in pixels.
        margin: Margin around text in pixels.
        font_path: Font name or path to TrueType/OpenType font file.
        font_size: Font size in pixels.
        vertical_align: Vertical alignment of the content within the image ('top', 'center', 'bottom').
        line_spacing: Line spacing as a factor of line height.
        text_color: Text color as an RGB tuple.
        background_color: Background color as an RGB tuple.
        extend_word_areas: Extend word areas to cover whitespace between words.

    Returns:
        A tuple containing the generated TextImage and the cursor locations.
    """
    text_width = width - 2 * margin
    text_height = height - 2 * margin

    image = Image.new("RGB", (width, height), tuple(background_color))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)

    num_question_lines = len(list(wrap_text(question, font, text_width)))

    font_ascent, font_descent = font.getmetrics()
    line_height = (font_ascent + font_descent) * line_spacing
    total_height = line_height * (num_question_lines + 1 + len(options))
    question_left = margin
    question_top = margin
    question_width = text_width
    if vertical_align == "center":
        question_top += (text_height - total_height) / 2
    elif vertical_align == "bottom":
        question_top += text_height - total_height

    char_areas = []
    word_areas = []
    section_areas = []

    question_char_areas, question_word_areas, question_area = draw_text(
        draw,
        question,
        question_left,
        question_top,
        question_width,
        font,
        line_spacing=line_spacing,
        extend_word_areas=extend_word_areas,
        max_height=text_height,
        color=text_color,
    )
    for char_area in question_char_areas:
        char_area.section = "question"
    for word_area in question_word_areas:
        word_area.section = "question"
    question_area.content = "question"
    char_areas.extend(question_char_areas)
    word_areas.extend(question_word_areas)
    section_areas.append(question_area)

    # Draw answer options
    option_left = margin + 2 * font_size
    option_top = question_area.bottom + line_height
    option_width = text_width - 2 * font_size
    cursor_locations = []

    for option_index, option in enumerate(options):
        # Draw option circle
        circle_x = margin + font_size / 2
        circle_y = option_top + line_height / 2
        draw.circle(
            (circle_x, circle_y),
            font_size / 2,
            outline="black",
            width=2,
        )

        # Put cursor in the middle of the circle
        cursor_locations.append((circle_x, circle_y))

        # Draw option text
        option_char_areas, option_word_areas, option_area = draw_text(
            draw,
            option,
            option_left,
            option_top,
            option_width,
            font,
            line_spacing=line_spacing,
            extend_word_areas=extend_word_areas,
            color=text_color,
        )
        for char_area in option_char_areas:
            char_area.section = f"option:{option_index}"
        for word_area in option_word_areas:
            word_area.section = f"option:{option_index}"
        option_area.content = f"option:{option_index}"
        char_areas.extend(option_char_areas)
        word_areas.extend(option_word_areas)
        section_areas.append(option_area)

        # TODO: Support multi-line options
        option_top += line_height

    return (
        TextImage(
            image, {"char": char_areas, "word": word_areas, "section": section_areas}
        ),
        cursor_locations,
    )
