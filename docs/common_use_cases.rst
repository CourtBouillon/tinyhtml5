Common Use Cases
================


Parse HTML document from string
-------------------------------

.. code-block:: python

   from tinyhtml5 import parse
   document = parse('<html><body><p>This is a doc</p></body></html>')


Parse HTML document from file
-----------------------------

To open a file, it is possible to provide a path:

.. code-block:: python

   from pathlib import Path
   from tinyhtml5 import parse
   document = parse("/path/to/file.html")

It is possible to use a :class:`pathlib.Path`:

.. code-block:: python

   from pathlib import Path
   from tinyhtml5 import parse
   document = parse(Path("/path/to/file.html"))

Providing a file descriptor with open is also allowed:

.. code-block:: python

   from tinyhtml5 import parse
   with open("/path/to/file.html", "rb") as fd:
       document = parse(fd)
