"""
HTML parsing library based on the `WHATWG HTML specification
<https://whatwg.org/html>`_. The parser is designed to be compatible with
existing HTML found in the wild and implements well-defined error recovery that
is largely compatible with modern desktop web browsers.

Example usage::

    import html5lib
    with open("my_document.html", "rb") as f:
        tree = html5lib.parse(f)

For convenience, this module re-exports the following names:

* :func:`~.html5parser.parse`
* :func:`~.html5parser.parseFragment`
* :class:`~.html5parser.HTMLParser`
* :func:`~.treebuilder.getTreeBuilder`
* :func:`~.treewalkers.getTreeWalker`
* :func:`~.serializer.serialize`
"""

from .html5parser import parse

__all__ = ["parse"]

# this has to be at the top level, see how setup.py parses this
#: Distribution version number.
__version__ = "1.2-dev"
