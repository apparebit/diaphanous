from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
import textwrap
from typing import ClassVar, Literal


# --------------------------------------------------------------------------------------


class Markup(ABC):
    """The base class for markup."""
    RENDER_WITH: ClassVar[str]

    @staticmethod
    def em(text: str) -> 'Emphasis':
        return Emphasis(text)

    @staticmethod
    def strong(text: str) -> 'Strong':
        return Strong(text)

    @staticmethod
    def p(*fragments: 'str | InlineContent') -> 'Paragraph':
        return Paragraph(tuple(fragments))

    @staticmethod
    def li(*fragments: 'str | InlineContent') -> 'ListItem':
        return ListItem(tuple(fragments))

    @staticmethod
    def ul(*items: 'ListItem') -> 'UnorderedList':
        return UnorderedList(tuple(items))

    @staticmethod
    def h1(text: str) -> 'Heading':
        return Heading(1, text)

    @staticmethod
    def h2(text: str) -> 'Heading':
        return Heading(2, text)

    def render_with(self, renderer: 'MarkupRenderer') -> str:
        # Renderer and render_with() do implement the visitor pattern's double
        # dispatch. Thanks to introspection and dynamic typing, a single
        # render_with() suffices.
        return getattr(renderer, self.RENDER_WITH)(self)


class InlineContent(Markup):
    """Inline content modifies spans of text within a paragraph or similar block."""


@dataclass(frozen=True, slots=True)
class Emphasis(InlineContent):
    RENDER_WITH = 'render_emphasis'

    text: str


@dataclass(frozen=True, slots=True)
class Strong(InlineContent):
    RENDER_WITH = 'render_strong'

    text: str


class BlockContent(Markup):
    """Block content comprises one or more lines of text of its own."""


@dataclass(frozen=True, slots=True)
class Paragraph(BlockContent):
    RENDER_WITH = 'render_paragraph'

    fragments: Sequence[str | InlineContent]


@dataclass(frozen=True, slots=True)
class ListItem(Markup):
    RENDER_WITH = 'render_list_item'

    fragments: Sequence[str | InlineContent]


@dataclass(frozen=True, slots=True)
class UnorderedList(BlockContent):
    RENDER_WITH = 'render_unordered_list'

    list_items: Sequence[ListItem]


@dataclass(frozen=True, slots=True)
class Heading(BlockContent):
    RENDER_WITH = 'render_heading'

    level: Literal[1, 2]
    text: str


# ======================================================================================


class MarkupRenderer(ABC):
    """The base class of markup renderers."""

    @abstractmethod
    def render_heading(self, heading: Heading) -> str:
        ...

    @abstractmethod
    def render_unordered_list(self, unordered_list: UnorderedList) -> str:
        ...

    @abstractmethod
    def render_list_item(self, list_item: ListItem) -> str:
        ...

    @abstractmethod
    def render_paragraph(self, paragraph: Paragraph) -> str:
        ...

    @abstractmethod
    def render_strong(self, strong: Strong) -> str:
        ...

    @abstractmethod
    def render_emphasis(self, emphasis: Emphasis) -> str:
        ...

    def reduce(self, fragments: Sequence[str | Markup]) -> str:
        return ''.join(
            f if isinstance(f, str) else f.render_with(self) for f in fragments
        )


# --------------------------------------------------------------------------------------


class HtmlRenderer(MarkupRenderer):
    def render_heading(self, heading: Heading) -> str:
        return f'<h{heading.level}>{heading.text}</h{heading.level}>'

    def render_unordered_list(self, unordered_list: UnorderedList) -> str:
        return f'<ul>{self.reduce(unordered_list.list_items)}</ul>'

    def render_list_item(self, list_item: ListItem) -> str:
        return f'<li>{self.reduce(list_item.fragments)}</li>'

    def render_paragraph(self, paragraph: Paragraph) -> str:
        return f'<p>{self.reduce(paragraph.fragments)}</p>'

    def render_strong(self, strong: Strong) -> str:
        return f'<strong>{strong.text}</strong>'

    def render_emphasis(self, emphasis: Emphasis) -> str:
        return f'<em>{emphasis.text}</em>'


# --------------------------------------------------------------------------------------


class TerminalRenderer(MarkupRenderer):
    # TODO: Take ANSI escapes & wide glyphs (https://github.com/jquast/wcwidth)
    # into account when wrapping text.
    MAX_LINE_WIDTH = 70

    def __init__(self, terminal_line_width: int, use_sgr: bool) -> None:
        self._terminal_line_width = terminal_line_width
        self._use_sgr = use_sgr

    @property
    def terminal_line_width(self) -> int:
        return self._terminal_line_width

    def _sgr(self, code: str) -> str:
        return f'\x1b[{code}m' if self._use_sgr else ''

    def render_heading(self, heading: Heading) -> str:
        return ''.join([
            ('━' if heading.level == 1 else '─') * self.terminal_line_width,
            '\n',
            self._sgr('1') + heading.text + self._sgr('0'),
            '\n\n'
        ])

    def render_unordered_list(self, unordered_list: UnorderedList) -> str:
        return self.reduce(unordered_list.list_items) + '\n'

    def render_list_item(self, list_item: ListItem) -> str:
        lines = textwrap.wrap(
            self.reduce(list_item.fragments),
            width=min(self.terminal_line_width - 4, self.MAX_LINE_WIDTH - 4))
        return '  • ' + '\n    '.join(lines) + '\n'

    def render_paragraph(self, paragraph: Paragraph) -> str:
        lines = textwrap.wrap(
            self.reduce(paragraph.fragments),
            width=min(self.terminal_line_width, self.MAX_LINE_WIDTH))
        return '\n'.join(lines) + '\n\n'

    def render_strong(self, strong: Strong) -> str:
        return self._sgr('1') + strong.text + self._sgr('0')

    def render_emphasis(self, emphasis: Emphasis) -> str:
        return f'*{emphasis.text}*'
