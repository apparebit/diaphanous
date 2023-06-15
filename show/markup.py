from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import auto, Enum, Flag
from html.parser import HTMLParser
from typing import (
    Callable,
    cast,
    ClassVar,
    Generic,
    Literal,
    overload,
    Self,
    TypeGuard,
    TypeVar,
)

from .texting import Reflow, is_spacing_only


# ======================================================================================
# Parsing Markup

class Traits(Flag):
    """The traits of markup elements."""
    HAS_INLINE = auto()
    HAS_LIST_ITEM = auto()
    HAS_TEXT = auto()
    IS_BLOCK = auto()
    IS_INLINE = auto()
    IS_VOID = auto()


@dataclass(frozen=True)
class TagImpl:
    """The constructor function and traits for implementing a tag."""
    fn: 'Callable[..., Markup]'
    traits: Traits


class Tag(Enum):
    """The enumeration over supported tags."""
    em = TagImpl(lambda t = '': Emphasis(t), Traits.HAS_TEXT | Traits.IS_INLINE)
    h1 = TagImpl(lambda t = '': Heading(1, t), Traits.HAS_TEXT | Traits.IS_BLOCK)
    h2 = TagImpl(lambda t = '': Heading(2, t), Traits.HAS_TEXT | Traits.IS_BLOCK)
    hr = TagImpl(lambda: Rule(), Traits.IS_BLOCK | Traits.IS_VOID)
    li = TagImpl(lambda *fs: ListItem(fs), Traits.HAS_INLINE | Traits.HAS_TEXT)
    ol = TagImpl(lambda *its: List(True, its), Traits.HAS_LIST_ITEM | Traits.IS_BLOCK)
    p = TagImpl(lambda *fs: Paragraph(fs),
        Traits.HAS_INLINE | Traits.HAS_TEXT | Traits.IS_BLOCK)
    strong = TagImpl(lambda t = '': Strong(t), Traits.HAS_TEXT | Traits.IS_INLINE)
    ul = TagImpl(lambda *its: List(False, its), Traits.HAS_LIST_ITEM | Traits.IS_BLOCK)

    def __str__(self) -> str:
        """Get the name of the tag."""
        return self.name

    def __call__(self, *args: 'str | Markup') -> 'Markup':
        """Create a new instance of that element."""
        return self.value.fn(*args)

    def has_inline(self) -> bool:
        """Determine whether elements with this tag contain inline elements."""
        return bool(self.value.traits & Traits.HAS_INLINE)

    def has_list_item(self) -> bool:
        """Determine whether elements with this tag contain list items."""
        return bool(self.value.traits & Traits.HAS_LIST_ITEM)

    def has_text(self) -> bool:
        """Determine whether elements with this tag contain text."""
        return bool(self.value.traits & Traits.HAS_TEXT)

    def is_block(self) -> bool:
        """Determine whether elements with this tag are blocks."""
        return bool(self.value.traits & Traits.IS_BLOCK)

    def is_inline(self) -> bool:
        """Determine whether elements with this tag are inline elements."""
        return bool(self.value.traits & Traits.IS_INLINE)

    def is_void(self) -> bool:
        """Determine whether elements with this tag are void."""
        return bool(self.value.traits & Traits.IS_VOID)


@dataclass
class _PendingElement:
    """An element currently being parsed."""

    tag: None | Tag
    children: 'list[str | Markup]' = field(default_factory=list)

    def add_text(self, child: str) -> Self:
        last_child = None if len(self.children) == 0 else self.children[-1]
        if isinstance(last_child, str):
            self.children[-1] = last_child + child
        else:
            self.children.append(child)
        return self

    def add_element(self, child: 'Markup') -> Self:
        self.children.append(child)
        return self

    def instantiate(self) -> 'Markup':
        assert self.tag is not None
        return self.tag(*self.children)


class _MarkupParser(HTMLParser):

    def __init__(self) -> None:
        self._pending: list[_PendingElement] = []
        super().__init__(convert_charrefs=True)

    def reset(self) -> None:
        super().reset()
        self._pending.clear()

    def parse(self, text: str) -> 'list[BlockContent]':
        self.reset()
        self.feed(text.strip())

        still_open = len(self._pending)
        if still_open != 1:
            raise ValueError(f'markup missing {still_open - 1} closing '
                f'tag{"" if still_open == 2 else "s"}')

        pending = self._pending[0]
        if pending.tag is None:
            return cast(list[BlockContent], pending.children)
        else:
            return [cast(BlockContent, pending.instantiate())]

    def has_pending(self, minimum: int = 1) -> bool:
        return len(self._pending) >= minimum

    def most_recent_pending(self) -> _PendingElement:
        return self._pending[-1]

    def start_pending(self, tag: None | Tag) -> None:
        if tag is None and len(self._pending) > 0:
            raise ValueError('null tag is only allowed for top-level pending element')
        self._pending.append(_PendingElement(tag))

    def stop_pending(self) -> None:
        markup = self._pending.pop().instantiate()
        self.most_recent_pending().add_element(markup)

    def handle_starttag(self, name: str, attrs: list[tuple[str, str | None]]) -> None:
        # Reject start tag with attributes
        if len(attrs) > 0:
            raise ValueError('Markup does not support attributes such as those in '
                f'“{self.get_starttag_text()}”')

        # Validate tag
        try:
            tag = Tag[name]
        except KeyError:
            raise ValueError(f'<{name}> is not a valid tag')

        # Initialize outermost pending element if necessary
        if not self.has_pending():
            if tag.is_inline():
                self.start_pending(Tag.p)
            elif tag.is_block():
                self.start_pending(None)
            else:
                raise TypeError(f'<{tag}> must not be the outermost element')

        # Handle implicitly closed <p> and <li>
        most_recent = self.most_recent_pending().tag
        if most_recent is Tag.p and tag.is_block():
            self.stop_pending()
        elif most_recent is Tag.li and tag is Tag.li:
            self.stop_pending()

        # If the currently pending element allows this tag, start pending the tag.
        most_recent = self.most_recent_pending().tag
        if (
            (most_recent is None and tag.is_block())
            or (most_recent and most_recent.has_inline() and tag.is_inline())
            or (most_recent and most_recent.has_list_item() and tag is Tag.li)
        ):
            self.start_pending(tag)
            if tag.is_void():
                self.stop_pending()
            return

        if most_recent is None:
            raise ValueError(f'<{tag}> cannot be outermost element')
        else:
            raise ValueError(f'<{tag}> may not appear inside <{most_recent}>')

    def handle_endtag(self, name: str) -> None:
        # Validate the tag
        try:
            tag = Tag[name]
        except KeyError:
            raise ValueError(f'</{name}> is not a valid tag name')

        # Check that there are pending elements
        if not self.has_pending(2):
            raise ValueError(f'got </{tag}> when no tag has been opened')

        # Handle implicitly closed <li>
        most_recent = self.most_recent_pending().tag
        if most_recent is Tag.li and tag.has_list_item():
            self.stop_pending()

            if not self.has_pending(2):
                raise ValueError(f'got </{tag}> when no tag has been opened')

        # If the end tag matches the most recently opened tag, close that tag.
        most_recent = self.most_recent_pending().tag
        if most_recent is tag:
            self.stop_pending()
        else:
            raise ValueError(f'got </{tag}> where </{most_recent}> expected')

    def handle_data(self, data: str) -> None:
        # Initialize outermost pending element if necessary
        if not self.has_pending():
            self.start_pending(Tag.p)

        # If current tag has textual content, add the text.
        most_recent = self.most_recent_pending().tag
        if most_recent is not None and most_recent.has_text():
            self.most_recent_pending().add_text(data)
            return

        # Otherwise, tolerate spacing.
        if not is_spacing_only(data):
            raise ValueError(
                f'text other than spacing "{data.strip()}" outside <li> or <p>')

    def handle_comment(self, data: str) -> None:
        raise ValueError(
            f'Markup does not support HTML comments such as “<!--{data}-->”')

    def handle_decl(self, decl: str) -> None:
        raise ValueError(
            f'Markup does not support HTML doctypes such as “<!{decl}>”')

    def handle_pi(self, data: str) -> None:
        raise ValueError(
            f'Markup does not support processing instructions such as “<?{data}>”')

    def unknown_decl(self, data: str) -> None:
        raise ValueError(
            f'Markip does not support declarations such as “<![{data}]>”')


# ======================================================================================
# Representing Markup

R = TypeVar('R', str, Iterator[str])

class Markup(ABC):
    """The base class for markup."""

    RENDER_METHOD: ClassVar[str]
    tx: ClassVar[type[Tag]] = Tag

    @staticmethod
    def parse(text: str) -> 'list[BlockContent]':
        return _MarkupParser().parse(text)

    @property
    @abstractmethod
    def tag(self) -> Tag:
        ...

    def render(self, renderer: 'MarkupRenderer[R]') -> str:
        """
        Render this markup to a string. This method treats strings yielded by
        stream renderers as lines and adds line terminators. It simply passes
        through strings returned by string renderers without inspection.
        """
        if is_streaming_renderer(renderer):
            return '\n'.join(getattr(renderer, self.RENDER_METHOD)(self)) + '\n'
        else:
            return getattr(renderer, self.RENDER_METHOD)(self)

    def render_stream(self, renderer: 'MarkupRenderer[R]') -> Iterator[str]:
        """
        Render this markup to a stream of strings. Preferrably, each yielded
        string is a line without line terminator. This method ensures that
        invariant for string renderers but passes through the results of stream
        renderers without inspection.
        """
        if is_streaming_renderer(renderer):
            yield from getattr(renderer, self.RENDER_METHOD)(self)
        else:
            text = getattr(renderer, self.RENDER_METHOD)(self)
            yield from text.split('\n')


class InlineContent(Markup):
    """Inline content modifies spans of text within a paragraph or similar block."""

    def render(self, renderer: 'MarkupRenderer[R]') -> str:
        return getattr(renderer, self.RENDER_METHOD)(self)

    def render_stream(self, renderer: 'MarkupRenderer[R]') -> Iterator[str]:
        yield getattr(renderer, self.RENDER_METHOD)(self)


@dataclass(frozen=True, slots=True)
class Emphasis(InlineContent):
    RENDER_METHOD = 'render_emphasis'

    text: str

    @property
    def tag(self) -> Tag:
        return Tag.em


@dataclass(frozen=True, slots=True)
class Strong(InlineContent):
    RENDER_METHOD = 'render_strong'

    text: str

    @property
    def tag(self) -> Tag:
        return Tag.strong


class BlockContent(Markup):
    """Block content comprises one or more lines of text of its own."""

    @staticmethod
    def cast(markup: Markup) -> 'BlockContent':
        if isinstance(markup, BlockContent):
            return markup
        raise TypeError(f'got <{markup.tag}> where block expected')

    @staticmethod
    def cast_all(markup_list: Sequence[Markup]) -> 'tuple[BlockContent, ...]':
        blocks: list[BlockContent] = []
        for block in markup_list:
            blocks.append(BlockContent.cast(block))
        return tuple(blocks)

@dataclass(frozen=True, slots=True)
class Rule(BlockContent):
    RENDER_METHOD = 'render_rule'

    @property
    def tag(self) -> Tag:
        return Tag.hr


@dataclass(frozen=True, slots=True)
class Paragraph(BlockContent):
    RENDER_METHOD = 'render_paragraph'

    fragments: Sequence[str | InlineContent]

    @property
    def tag(self) -> Tag:
        return Tag.p


@dataclass(frozen=True, slots=True)
class ListItem(Markup):
    RENDER_METHOD = 'render_list_item'

    fragments: Sequence[str | InlineContent]

    @classmethod
    def cast(cls, markup: Markup) -> Self:
        if isinstance(markup, cls):
            return markup
        raise TypeError(f'got <{markup.tag}> where list item expected')

    @property
    def tag(self) -> Tag:
        return Tag.li


@dataclass(frozen=True, slots=True)
class List(BlockContent):
    RENDER_METHOD = 'render_list'

    is_ordered: bool
    items: Sequence[ListItem]

    @property
    def tag(self) -> Tag:
        return Tag.ol if self.is_ordered else Tag.ul


@dataclass(frozen=True, slots=True)
class Heading(BlockContent):
    RENDER_METHOD = 'render_heading'

    level: Literal[1, 2]
    text: str

    @property
    def tag(self) -> Tag:
        return Tag.h1 if self.level == 1 else Tag.h2


# --------------------------------------------------------------------------------------


def only_inline_content(
    sequence: Sequence[object]
) -> TypeGuard[Sequence[str | InlineContent]]:
    """Check whether the sequence contains only text and inline content."""
    return all(isinstance(el, (str, InlineContent)) for el in sequence)


def only_block_content(
    sequence: Sequence[object]
) -> TypeGuard[Sequence[BlockContent]]:
    """Check whether the sequence contains only block content."""
    return all(isinstance(el, BlockContent) for el in sequence)


# ======================================================================================
# Rendering Markup

class MarkupRenderer(ABC, Generic[R]):
    """The base class of markup renderers."""

    IS_STREAMING: ClassVar[bool]

    @abstractmethod
    def render_heading(self, heading: Heading) -> R:
        ...

    @abstractmethod
    def render_list(self, list: List) -> R:
        ...

    @abstractmethod
    def render_list_item(self, list_item: ListItem) -> R:
        ...

    @abstractmethod
    def render_paragraph(self, paragraph: Paragraph) -> R:
        ...

    @abstractmethod
    def render_rule(self, rule: Rule) -> R:
        ...

    @abstractmethod
    def render_strong(self, strong: Strong) -> str:
        ...

    @abstractmethod
    def render_emphasis(self, emphasis: Emphasis) -> str:
        ...

    @overload
    def reduce(self: 'MarkupRenderer[str]', fragments: Iterable[str|Markup]) -> str:
        ...

    @overload
    def reduce(self, fragments: Iterable[str|InlineContent]) -> str:
        ...

    def reduce(self, fragments: Iterable[str|Markup]) -> str:
        return ''.join(
            f if isinstance(f, str) else f.render(self) for f in fragments
        )


def is_string_renderer(
    renderer: MarkupRenderer[R]
) -> TypeGuard[MarkupRenderer[str]]:
    """Determine whether the renderer produces strings."""
    return not renderer.IS_STREAMING


def is_streaming_renderer(
    renderer: MarkupRenderer[R]
) -> TypeGuard[MarkupRenderer[Iterator[str]]]:
    """Determine whether the renderer is a streaming one."""
    return renderer.IS_STREAMING


# --------------------------------------------------------------------------------------


class HtmlRenderer(MarkupRenderer[str]):
    # With HTML the blueprint for Markup classes, rendering is really hard...

    IS_STREAMING = False

    def render_heading(self, heading: Heading) -> str:
        return f'<{heading.tag}>{heading.text}</{heading.tag}>'

    def render_list(self, list: List) -> str:
        return f'<{list.tag}>{self.reduce(list.items)}</{list.tag}>'

    def render_list_item(self, item: ListItem) -> str:
        return f'<li>{self.reduce(item.fragments)}</li>'

    def render_paragraph(self, paragraph: Paragraph) -> str:
        return f'<p style="max-width: 70ch;">{self.reduce(paragraph.fragments)}</p>'

    def render_rule(self, rule: Rule) -> str:
        return '<hr>'

    def render_strong(self, strong: Strong) -> str:
        return f'<strong>{strong.text}</strong>'

    def render_emphasis(self, emphasis: Emphasis) -> str:
        return f'<em>{emphasis.text}</em>'


# --------------------------------------------------------------------------------------


class TerminalRenderer(MarkupRenderer[Iterator[str]]):

    IS_STREAMING = True

    # TODO: Take ANSI escapes & wide glyphs (https://github.com/jquast/wcwidth)
    # into account when wrapping text.
    MAX_LINE_WIDTH = 70

    def __init__(self, *, line_width: int, use_sgr: bool) -> None:
        self._line_width = line_width
        self._use_sgr = use_sgr
        self._reflow_engine = Reflow(max_width=TerminalRenderer.MAX_LINE_WIDTH)

    @property
    def line_width(self) -> int:
        return self._line_width

    @contextmanager
    def new_line_width(self, line_width: int) -> Iterator[Self]:
        saved_line_width = self._line_width
        self._line_width = line_width
        try:
            yield self
        finally:
            self._line_width = saved_line_width

    @property
    def reflow_engine(self) -> Reflow:
        return self._reflow_engine

    def _sgr(self, code: str) -> str:
        return f'\x1b[{code}m' if self._use_sgr else ''

    def render_heading(self, heading: Heading) -> Iterator[str]:
        yield ('━' if heading.level == 1 else '─') * self.line_width
        yield self._sgr('1') + heading.text + self._sgr('0')
        yield ''

    def render_list(self, list: List) -> Iterator[str]:
        for item_index, item in enumerate(list.items):
            for line_index, line in enumerate(item.render_stream(self)):
                if line_index == 0:
                    prefix = f'{item_index + 1: 2d}. ' if list.is_ordered else '  • '
                else:
                    prefix = '    '
                yield prefix + line
        yield ''

    def render_list_item(self, list_item: ListItem) -> Iterator[str]:
        yield from self._reflow_engine.wrap(
            self.reduce(list_item.fragments),
            max_width=min(self.line_width - 4, self.MAX_LINE_WIDTH - 4),
        )

    def render_paragraph(self, paragraph: Paragraph) -> Iterator[str]:
        yield from self._reflow_engine.wrap(
            self.reduce(paragraph.fragments),
            max_width=min(self.line_width, self.MAX_LINE_WIDTH),
        )
        yield ''

    def render_rule(self, rule: Rule) -> Iterator[str]:
        yield '─' * self.line_width

    def render_strong(self, strong: Strong) -> str:
        return self._sgr('1') + strong.text + self._sgr('0')

    def render_emphasis(self, emphasis: Emphasis) -> str:
        return f'*{emphasis.text}*'
