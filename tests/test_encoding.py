from pathlib import Path

import pytest

from html5lib._inputstream import HTMLBinaryInputStream
from html5lib.html5parser import HTMLParser

from . import Data


_tests = tuple(
    (f'{path.stem}-{i}', test)
    for path in (Path(__file__).parent / 'encoding').glob('*.dat')
    for i, test in enumerate(Data(path, b'data', encoding=None)))


@pytest.mark.parametrize('id, test', _tests, ids=(id for id, _ in _tests))
def test_parser_encoding(id, test):
    parser = HTMLParser()
    assert parser.documentEncoding is None
    parser.parse(test[b'data'])
    encoding = test[b'encoding'].lower().decode('ascii')
    error_message = (
        f'\nData: {test[b'data']!r}',
        f'\nExpected encoding: {encoding}',
        f'\nParser encoding: {parser.documentEncoding}')
    assert encoding == parser.documentEncoding, error_message


@pytest.mark.parametrize('id, test', _tests, ids=(id for id, _ in _tests))
def test_prescan_encoding(id, test):
    stream = HTMLBinaryInputStream(test[b'data'])

    # Very crude way to ignore irrelevant tests.
    if len(test[b'data']) > stream.numBytesMeta:
        return

    encoding = test[b'encoding'].lower().decode('ascii')
    error_message = (
        f'\nData: {test[b'data']!r}',
        f'\nExpected encoding: {encoding}',
        f'\nParser encoding: {stream.charEncoding[0].name}')
    assert encoding == stream.charEncoding[0].name, error_message
