"""
Module with functionality useful for TEXT processING that gracefully handles
ANSI escape codes and Unicode codepoints.
"""

from collections.abc import Iterator
import re


class CharClass:
    """Helpful character classes, defined inside a class-as-namespace."""
    Letter = r'[^\d\W]'
    SoftHyphen = '\xad'
    BreakingSpace = (
        r'[\x09-\x0d \x85\u2000-\u2006\u2008-\u200a\u2028\u2029\u205f\u3000]'
    )
    NonbreakingSpace = r'[\xa0\u2007\u202f]'
    AllButBreakingSpace: str
    WhiteSpace = r'\s'
    WordOrPunctuation = r'[\w!"\'&.,?“”‘’]'

CharClass.AllButBreakingSpace = fr'[^{CharClass.BreakingSpace[1:]}'


class Syntax:
    """Helpful regular expressions, defined inside a class-as-namespace."""
    CSI = re.compile(r'(?:\x9b|\x1b\[)[0-?]*[@-~]')

    # We need two look behind clauses because they have different widths:
    Pct = re.compile(r'(?:(?<=\A)|(?<=\W))Pct(?=\W|\Z)', re.I)

    BreakingSpaces = re.compile(fr'^{CharClass.BreakingSpace}+$')

    UnderscoresOrSpaces = re.compile(fr'_+|{CharClass.BreakingSpace}+')

    SpacingOnly = re.compile(r'^\s*$')

    # Based on https://github.com/python/cpython/blob/3.11/Lib/textwrap.py
    Separator = re.compile(
        fr'''
            ( # Split (and, thanks to capturing group, also keep) on spacing,
            {CharClass.BreakingSpace}+
            # on em dash after word,
            | (?<= {CharClass.WordOrPunctuation}) -{{2,}}
            # on word-like text
            | {CharClass.AllButBreakingSpace}+?
                (?:
                    # up to and including the hyphen in a hyphenated word,
                    - (?:
                        (?<= {CharClass.Letter}{{2}} - )
                        (?= {CharClass.Letter}{{2}} ) )
                    # up to and including the soft hyphen no matter where,
                    | {CharClass.SoftHyphen}
                    # until the end of a word followed by an em dash
                    | (?<= {CharClass.WordOrPunctuation}) (?= -{{2,}} )
                    # until the end of a word followed by a space or end-of-string.
                    | (?= {CharClass.BreakingSpace} | \Z)
                )
            )
        ''',
        re.X,
    )


def is_spacing_only(text: str) -> bool:
    return bool(Syntax.SpacingOnly.match(text))


def visible_length(text: str) -> int:
    """
    Compute the visible length of the given text on the terminal. This function
    correctly accounts for ANSI escape codes and word joiners. But it doesn't
    yet handle double-wide characters such as emoji and CJK.
    """
    text = Syntax.CSI.sub('', text).replace('\u2060', '')
    return len(text)


def format_label(label: object) -> None | str:
    """
    Format the label for a vertical for humane presentation. This function replaces
    underscores with spaces and turns `pct` (case-insensitive) into `%`.
    """
    if label is None:
        return None

    text = str(label)
    text = Syntax.UnderscoresOrSpaces.sub(' ', text)
    text = Syntax.Pct.sub('%', text)
    return text


class Reflow:
    """
    Class to reflow text that may contain embedded ANSI escape sequences to a
    given width. While the regular expression used for splitting the text into
    tokens is directly based on the one used by Python's `textwrap` module, the
    rest of the code is an independent implementation. Supporting the same
    features as the standard library is an explicit nongoal.
    """
    def __init__(self, max_width: int) -> None:
        self.max_width = max_width

    @staticmethod
    def tokenize(text: str) -> Iterator[str]:
        """Tokenize the given text, yielding tokens."""
        for token in Syntax.Separator.split(text):
            if len(token) == 0:
                continue
            if Syntax.BreakingSpaces.match(token):
                yield ' '
                continue
            yield token

    @staticmethod
    def has_trailing_space(line: list[str]) -> bool:
        """Check whether the last token is a space."""
        return bool(line) and line[-1] == ' '

    @staticmethod
    def has_trailing_soft_hyphen(line: list[str]) -> bool:
        """Check whether the last token ends in a soft hyphen."""
        return bool(line) and line[-1][-1] == CharClass.SoftHyphen

    @staticmethod
    def handle_space_token(line: list[str], width: int) -> int:
        """
        Process a space as the next token. This method returns the updated width.
        """
        if len(line) == 0:
            return width

        line.append(' ')
        return width + 1

    @staticmethod
    def width(token: str) -> int:
        """
        Determine the token's width. This method accounts for ANSI escape
        sequences but not yet for double-wide emoji or CJK glyphs.
        """
        return visible_length(token)

    def handle_token_width(
        self, line: list[str], width: int, token: str
    ) -> tuple[int, bool, bool]:
        """Determine the token's width and whether it fits onto the current line."""
        token_width = Reflow.width(token)
        has_width = width + token_width <= self.max_width
        return token_width, has_width

    @staticmethod
    def handle_trailing_space(line: list[str], width: int, fits: bool) -> int:
        """If the line cannot accommodate the next token, remove any trailing space."""
        if fits or len(line) == 0 or line[-1] != ' ':
            return width

        line.pop()
        return width - 1

    @staticmethod
    def handle_trailing_hyphen(line: list[str], width: int, fits: bool) -> int:
        """
        Remove the soft hyphen from the last token. If the line does not have
        width, replace with hard hyphen. This method returns the updated width.
        """
        if len(line) == 0 or line[-1][-1] != CharClass.SoftHyphen:
            return width
        if fits:
            line[-1] = line[-1][:-1]
            return width - 1

        line[-1] = line[-1][:-1] + '-'
        return width

    @staticmethod
    def should_yield(line: list[str], has_width: bool) -> bool:
        """Determine whether to yield the current line."""
        return not has_width and len(line) > 0

    @staticmethod
    def handle_nonspace_token(
        line: list[str], width: int, token: str, token_width: int, fits: bool
    ) -> int:
        """
        Add the token to the line, making it the last one. This method modifies
        the line in place and returns the updated width.
        """
        if fits:
            line.append(token)
            return width + token_width

        line[:] = [token]
        return token_width

    def wrap_paragraph(
        self, text: str, *, max_width: None | int = None
    ) -> Iterator[str]:
        """
        Wrap the paragraph's text according to the provided maximum value or, if
        that is missing, the configured maximum width. This method yields the
        result line by line. It also normalizes sequences of intra-paragraph
        whitespace to a single regular space. Yielded lines are *not* terminated
        by a newline.
        """
        if max_width is None:
            max_width = self.max_width
        saved_max_width = self.max_width
        try:
            self.max_width = max_width
            yield from self._do_wrap_paragraph(text)
        finally:
            self.max_width = saved_max_width

    def _do_wrap_paragraph(self, text: str) -> Iterator[str]:
        line: list[str] = []
        width = 0

        for token in Reflow.tokenize(text):
            # Handle space token, appending it to current line.
            if token == ' ':
                width = Reflow.handle_space_token(line, width)
                continue

            # Determine whether token fits on current line.
            token_width, fits = self.handle_token_width(line, width, token)

            # Handle trailing space and (soft) hyphen before possibly yielding.
            width = Reflow.handle_trailing_space(line, width, fits)
            width = Reflow.handle_trailing_hyphen(line, width, fits)
            if Reflow.should_yield(line, fits):
                yield ''.join(line)

            # Handle regular, non-space token, making it the last token on the line.
            width = self.handle_nonspace_token(
                line, width, token, token_width, fits
            )

        # Once more with feeling: Handle trailing space & hyphen before yielding.
        width = Reflow.handle_trailing_space(line, width, False)
        width = Reflow.handle_trailing_hyphen(line, width, False)
        if Reflow.should_yield(line, False):
            yield ''.join(line)

    def wrap(self, text: str, *, max_width: None | int = None) -> Iterator[str]:
        """
        Wrap the given text according to this wrapper's maximum width and yield
        the result line by line. This method preserves paragraphs ending with
        two consecutive newline characters. Yielded lines are not terminated by
        a newline.
        """
        for index, paragraph in enumerate(text.split('\n\n')):
            if index > 0:
                yield ''
            yield from self.wrap_paragraph(paragraph, max_width=max_width)

    def fill(self, text: str, *, max_width: None | int = None) -> str:
        """Fill the given text to this wrapper's maximum width."""
        return '\n'.join(self.wrap(text, max_width=max_width)) + '\n'
