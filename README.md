scorer-to-usebio
================

Converts from the NZ Bridge Scorer XML results format to USEBIO 1.2.

Installation
------------

    > pip install scorer_to_usebio

Usage
-----
 * Run the GUI (note that you will need PyQt5 installed!):

        > ScorerConverter

 * Convert a file on the command-line:

        > scorer_to_usebio -p examples/pairs.xml

 * Or on the command-line via the python interpreter:

        > python3 -m scorer_to_usebio -p examples/pairs.xml

 * Or using the repl:

        >>> import scorer_to_usebio
        >>> scorer_to_usebio.convert('examples/pairs.xml')

 * Run unit tests:

        > nosetests

 * Check unit test code coverage:

        > nosetests --with-coverage --cover-erase --cover-package=scorer_to_usebio

Dependencies for Python 3
-------------------------
 * Python 3.5 (will probably work with earlier 3.x versions, but untested)
 * PyQt5 (optional, required for the GUI)
 * lxml (optional, required for DTD & pretty-printing support)
 * nose (optional for running tests)
 * coverage (optional for checking test code coverage)

Python 2.7 support
------------------

The conversion code supports running with Python 2.7 as well as Python 3. The
GUI has not been tested and may or may not work correctly.

When running with Python 2.7 the following additional dependencies are required
to run the unit tests:
 * mock
 * pathlib2

License
-------

GNU Affero General Public License (AGPLv3) or any later version.

See also
--------
 * The [USEBIO](http://www.usebio.org/) page has information, history, and a full specification.
 * [Bridge NZ](http://bridgenz.co.nz/) provide the Scorer software this converts from.
 * [Pianola](http://www.pianola.net/) is probably why you are looking at this in the first place.
