Contribute
==========

You want to add some code to tinyhtml5, launch its tests or improve its
documentation? Thank you very much! Here are some tips to help you play with
tinyhtml5 in good conditions.

The first step is to clone the repository, create a virtual environment and
install tinyhtml5 dependencies.

.. code-block:: shell

   git clone https://github.com/CourtBouillon/tinyhtml5.git
   cd tinyhtml5
   python -m venv venv
   venv/bin/pip install .[doc,test]

You can then let your terminal in the current directory and launch Python to
test your changes. ``import tinyhtml5`` will then import the working directory
code, so that you can modify it and test your changes.

.. code-block:: shell

   venv/bin/python


Code & Issues
-------------

If you’ve found a bug in tinyhtml5, it’s time to report it, and to fix it if
you can!

You can report bugs and feature requests on GitHub_. If you want to add or
fix some code, please fork the repository and create a pull request, we’ll be
happy to review your work.

.. _GitHub: https://github.com/CourtBouillon/tinyhtml5


Tests
-----

Tests are stored in the ``tests`` folder at the top of the repository. They use
the pytest_ library.

You can launch tests using the following command::

  venv/bin/pytest

tinyhtml5 also uses ruff_ to check the coding style::

  venv/bin/python -m ruff check

.. _pytest: https://docs.pytest.org/
.. _Ghostscript: https://www.ghostscript.com/
.. _ruff: https://docs.astral.sh/ruff/


Documentation
-------------

Documentation is stored in the ``docs`` folder at the top of the repository. It
relies on the Sphinx_ library.

You can build the documentation using the following command::

  venv/bin/sphinx-build docs docs/_build

The documentation home page can now be found in the ``docs/_build/index.html``
file. You can open this file in a browser to see the final rendering.

.. _Sphinx: https://www.sphinx-doc.org/
