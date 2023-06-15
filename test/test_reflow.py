import show.texting as texting

def test_fit() -> None:
    wrapper = texting.Reflow(5)

    # Short and really long words:
    assert wrapper.fill('abc') == 'abc\n'
    assert wrapper.fill('abcd') == 'abcd\n'
    assert wrapper.fill('abcde') == 'abcde\n'
    assert wrapper.fill('abcdef') == 'abcdef\n'

    # Spaces v newlines:
    assert wrapper.fill('ab ab ab') == 'ab ab\nab\n'
    assert wrapper.fill('ab abc ab') == 'ab\nabc\nab\n'

    # Trailing space:
    assert wrapper.fill('a ab zz') == 'a ab\nzz\n'

    # Hyphens including trailing soft hyphens:
    assert wrapper.fill('abcd-efg') == 'abcd-\nefg\n'
    assert wrapper.fill('abcd\xadefg') == 'abcd-\nefg\n'
    assert wrapper.fill('ab\xadcd') == 'abcd\n'

    # En/em dashes:
    assert wrapper.fill('ab--cd') == 'ab--\ncd\n'
    assert wrapper.fill('ab -- cd') == 'ab --\ncd\n'
