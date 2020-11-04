from micropython import const

from trezor import ui

if False:
    from typing import List, Union, Optional, Sequence

TEXT_HEADER_HEIGHT = const(48)
TEXT_LINE_HEIGHT = const(26)
TEXT_LINE_HEIGHT_HALF = const(13)
TEXT_MARGIN_LEFT = const(14)
TEXT_MAX_LINES = const(5)

# needs to be different from all colors and font ids
BR = const(-256)
BR_HALF = const(-257)

_FONTS = (ui.NORMAL, ui.BOLD, ui.MONO)

if False:
    TextContent = Union[str, int]


def render_text(
    words: Sequence[TextContent],
    new_lines: bool,
    max_lines: int,
    font: int = ui.NORMAL,
    fg: int = ui.FG,
    bg: int = ui.BG,
    offset_x: int = TEXT_MARGIN_LEFT,
    offset_y: int = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT,
    offset_x_max: int = ui.WIDTH,
    pre_linebreaked: bool = False,
) -> None:
    if not pre_linebreaked:
        lines = break_lines(
            words, new_lines, max_lines, font, fg, offset_x, offset_y, offset_x_max
        )
        words = [word for line in lines for word in line]

    # initial rendering state
    INITIAL_OFFSET_X = offset_x
    offset_y_max = TEXT_HEADER_HEIGHT + (TEXT_LINE_HEIGHT * max_lines)

    for word in words:
        if isinstance(word, int):
            if word is BR or word is BR_HALF:
                # line break or half-line break
                if offset_y > offset_y_max:
                    return
                offset_x = INITIAL_OFFSET_X
                offset_y += TEXT_LINE_HEIGHT if word is BR else TEXT_LINE_HEIGHT_HALF
            elif word in _FONTS:
                # change of font style
                font = word
            else:
                # change of foreground color
                fg = word
            continue

        ui.display.text(offset_x, offset_y, word, font, fg, bg)
        offset_x += ui.display.text_width(word, font)


def break_lines(
    words: Sequence[TextContent],
    new_lines: bool,
    max_lines: Optional[int],
    font: int = ui.NORMAL,
    fg: int = ui.FG,
    offset_x: int = TEXT_MARGIN_LEFT,
    offset_y: int = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT,
    offset_x_max: int = ui.WIDTH,
) -> List[List[TextContent]]:
    if max_lines is None:
        max_lines = 65536
    INITIAL_OFFSET_X = offset_x
    offset_y_max = TEXT_HEADER_HEIGHT + (TEXT_LINE_HEIGHT * max_lines)

    # sizes of common glyphs
    DASH = ui.display.text_width("-", ui.BOLD)
    ELLIPSIS = ui.display.text_width("...", ui.BOLD)

    result = []  # type: List[List[TextContent]]
    current_line = [fg, font]  # type: List[TextContent]

    def next_line(br: int = BR) -> None:
        nonlocal current_line, result, offset_x, offset_y
        current_line.append(br)
        result.append(current_line)
        current_line = [fg, font]
        offset_x = INITIAL_OFFSET_X
        offset_y += TEXT_LINE_HEIGHT if br is BR else TEXT_LINE_HEIGHT_HALF

    for word_index, word in enumerate(words):
        has_next_word = word_index < len(words) - 1

        if isinstance(word, int):
            if word is BR or word is BR_HALF:
                # line break or half-line break
                if offset_y > offset_y_max:
                    current_line.extend([ui.BOLD, ui.GREY, "..."])
                    result.append(current_line)
                    return result

                next_line(word)
            elif word in _FONTS:
                # change of font style
                font = word
                current_line.append(font)
            else:
                # change of foreground color
                fg = word
                current_line.append(fg)
            continue

        width = ui.display.text_width(word, font)

        while offset_x + width > offset_x_max or (
            has_next_word and offset_y >= offset_y_max
        ):
            beginning_of_line = offset_x == INITIAL_OFFSET_X
            word_fits_in_one_line = width < (offset_x_max - INITIAL_OFFSET_X)
            if (
                offset_y < offset_y_max
                and word_fits_in_one_line
                and not beginning_of_line
            ):
                # line break
                next_line()
                break
            # word split
            if offset_y < offset_y_max:
                split = "-"
                splitw = DASH
            else:
                split = "..."
                splitw = ELLIPSIS
            # find span that fits
            for index in range(len(word) - 1, 0, -1):
                letter = word[index]
                width -= ui.display.text_width(letter, font)
                if offset_x + width + splitw < offset_x_max:
                    break
            else:
                width = 0
                index = 0

            # avoid rendering "-" with empty span
            if index == 0 and offset_y < offset_y_max and not beginning_of_line:
                next_line()
                width = ui.display.text_width(word, font)
                continue

            span = word[:index]
            # render word span
            current_line.extend([span, ui.BOLD, ui.GREY, split])

            # line break
            if offset_y >= offset_y_max:
                result.append(current_line)
                return result
            next_line()

            # continue with the rest
            word = word[index:]
            width = ui.display.text_width(word, font)

        # render word
        current_line.append(word)

        if new_lines and has_next_word:
            # line break
            if offset_y >= offset_y_max:
                result.append(current_line + [ui.BOLD, ui.GREY, "..."])
                return result

            next_line()
        else:
            # shift cursor
            current_line.append(" ")
            offset_x += width + ui.display.text_width(" ", font)

    result.append(current_line)
    return result


class Text(ui.Component):
    def __init__(
        self,
        header_text: str,
        header_icon: str = ui.ICON_DEFAULT,
        icon_color: int = ui.ORANGE_ICON,
        max_lines: int = TEXT_MAX_LINES,
        new_lines: bool = True,
        pre_linebreaked: bool = False,
    ):
        self.header_text = header_text
        self.header_icon = header_icon
        self.icon_color = icon_color
        self.max_lines = max_lines
        self.new_lines = new_lines
        self.content = []  # type: List[TextContent]
        self.repaint = True
        self.pre_linebreaked = pre_linebreaked

    def normal(self, *content: TextContent) -> None:
        self.content.append(ui.NORMAL)
        self.content.extend(content)

    def bold(self, *content: TextContent) -> None:
        self.content.append(ui.BOLD)
        self.content.extend(content)

    def mono(self, *content: TextContent) -> None:
        self.content.append(ui.MONO)
        self.content.extend(content)

    def br(self) -> None:
        self.content.append(BR)

    def br_half(self) -> None:
        self.content.append(BR_HALF)

    def on_render(self) -> None:
        if self.repaint:
            ui.header(
                self.header_text,
                self.header_icon,
                ui.TITLE_GREY,
                ui.BG,
                self.icon_color,
            )
            render_text(
                self.content,
                self.new_lines,
                self.max_lines,
                pre_linebreaked=self.pre_linebreaked,
            )
            self.repaint = False

    if __debug__:

        def read_content(self) -> List[str]:
            lines = [w for w in self.content if isinstance(w, str)]
            return [self.header_text] + lines[: self.max_lines]


LABEL_LEFT = const(0)
LABEL_CENTER = const(1)
LABEL_RIGHT = const(2)


class Label(ui.Component):
    def __init__(
        self,
        area: ui.Area,
        content: str,
        align: int = LABEL_LEFT,
        style: int = ui.NORMAL,
    ) -> None:
        self.area = area
        self.content = content
        self.align = align
        self.style = style
        self.repaint = True

    def on_render(self) -> None:
        if self.repaint:
            align = self.align
            ax, ay, aw, ah = self.area
            ui.display.bar(ax, ay, aw, ah, ui.BG)
            tx = ax + aw // 2
            ty = ay + ah // 2 + 8
            if align is LABEL_LEFT:
                ui.display.text(tx, ty, self.content, self.style, ui.FG, ui.BG)
            elif align is LABEL_CENTER:
                ui.display.text_center(tx, ty, self.content, self.style, ui.FG, ui.BG)
            elif align is LABEL_RIGHT:
                ui.display.text_right(tx, ty, self.content, self.style, ui.FG, ui.BG)
            self.repaint = False

    if __debug__:

        def read_content(self) -> List[str]:
            return [self.content]


def text_center_trim_left(
    x: int, y: int, text: str, font: int = ui.NORMAL, width: int = ui.WIDTH - 16
) -> None:
    if ui.display.text_width(text, font) <= width:
        ui.display.text_center(x, y, text, font, ui.FG, ui.BG)
        return

    ELLIPSIS_WIDTH = ui.display.text_width("...", ui.BOLD)
    if width < ELLIPSIS_WIDTH:
        return

    text_length = 0
    for i in range(1, len(text)):
        if ui.display.text_width(text[-i:], font) + ELLIPSIS_WIDTH > width:
            text_length = i - 1
            break

    text_width = ui.display.text_width(text[-text_length:], font)
    x -= (text_width + ELLIPSIS_WIDTH) // 2
    ui.display.text(x, y, "...", ui.BOLD, ui.GREY, ui.BG)
    x += ELLIPSIS_WIDTH
    ui.display.text(x, y, text[-text_length:], font, ui.FG, ui.BG)


def text_center_trim_right(
    x: int, y: int, text: str, font: int = ui.NORMAL, width: int = ui.WIDTH - 16
) -> None:
    if ui.display.text_width(text, font) <= width:
        ui.display.text_center(x, y, text, font, ui.FG, ui.BG)
        return

    ELLIPSIS_WIDTH = ui.display.text_width("...", ui.BOLD)
    if width < ELLIPSIS_WIDTH:
        return

    text_length = 0
    for i in range(1, len(text)):
        if ui.display.text_width(text[:i], font) + ELLIPSIS_WIDTH > width:
            text_length = i - 1
            break

    text_width = ui.display.text_width(text[:text_length], font)
    x -= (text_width + ELLIPSIS_WIDTH) // 2
    ui.display.text(x, y, text[:text_length], font, ui.FG, ui.BG)
    x += text_width
    ui.display.text(x, y, "...", ui.BOLD, ui.GREY, ui.BG)
