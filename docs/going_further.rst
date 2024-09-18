Going Further
=============


Why tinyhtml5?
--------------

tinyhtml5 is a friendly fork of the unmaintained html5lib_ library, that’s been
adapted to fulfill WeasyPrint_’s needs.

.. _html5lib: https://github.com/html5lib/html5lib-python
.. _WeasyPrint: https://weasyprint.org/


What are the differences with html5lib?
---------------------------------------

tinyhtml5 is a simplified and modernized version of html5lib_, with the given
main differences:

- It is only a HTML parser, providing tree corresponding to a given HTML string
  or file.
- The public API is only the :func:`tinyhtml5.parse()` function, allowing
  filename string and :class:`pathlib.Path` as input in addition to HTML string and
  file descriptor.
- The only output format supported is ElementTree_.
- Tree walkers, adapters and filters are not supported.
- Tests are included.
- Code internals are cleaned, simplified and modernized.

.. _ElementTree: https://docs.python.org/3/library/xml.etree.elementtree.html


Why not maintaining html5lib?
-----------------------------

html5lib is a wonderful piece of software, used by many Python projects, and
we’re really grateful for the work done by its previous authors and
maintainers.

But unfortunately, html5lib is unmaintained. Maintaining it would have been
much more complex for us than creating tinyhtml5, for many different reasons.

First of all, there are many features of html5lib we don’t use. Maintaining
code we don’t use doesn’t look like a good idea for us, because it’s hard to
build a clean API when we don’t know the real needs. html5lib is a whole HTML
manipulation library, with a lot of different use cases, that requires a lot of
internal abstractions to provide its powerful features. tinyhtml5 is much less
powerful, and much simpler too.

The goal was also to clean the code. The syntax and the architecture had to be
modernized, because a lot of things have changed during the last years of the
Python ecosystem. html5lib was supporting Python 2 and included a lot of
details that are useless for recent versions of Python. Cleaning the whole code
was complex in html5lib’s modules we knew, it would have been much harder in
modules we didn’t know.

Maintaining html5lib requires a lot of work, that’s why it’s been unmaintained.
Honestly, there’s no reason why we could do better than the previous
maintainers, we didn’t want to give false hopes to its users. Maintaining and
extending all these features, with a very large community with a lot of
different needs, is a work we can’t do seriously with the limited resources we
have.
