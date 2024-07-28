First Steps
===========


Installation
------------

The easiest way to use tinyhtml5 is to install it in a Python `virtual
environment`_. When your virtual environment is activated, you can then install
tinyhtml5 with pip_::

    pip install tinyhtml5

.. _virtual environment: https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/
.. _pip: https://pip.pypa.io/


Parse HTML Document
-------------------

.. code-block:: python

   >>> from tinyhtml5 import parse
   >>> parse('<html><body><p>This is a doc</p></body></html>')
   <Element u'{http://www.w3.org/1999/xhtml}html' at 0x7feac4909db0>
