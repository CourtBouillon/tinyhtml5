"""HTML parsing library based on the WHATWG HTML specification.

The parser is designed to be compatible with existing HTML found in the wild
and implements well-defined error recovery that is largely compatible with
modern desktop web browsers.

Example usage::

    import html5lib
    with open("my_document.html", "rb") as f:
        tree = html5lib.parse(f)

"""

from .parser import HTMLParser, parse

__all__ = ["HTMLParser", "parse"]

VERSION = __version__ = "1.2-dev"
