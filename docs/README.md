# Documentation

This directory holds the source files required to build the AIY Python reference with Sphinx.

You can see the generated files at [aiyprojects.readthedocs.io](https://aiyprojects.readthedocs.io/).

If you've downloaded the [aiyprojects-raspbian](https://github.com/google/aiyprojects-raspbian)
repository, you can build these docs locally with the `make docs` command. Of course, this requires
that you install Sphinx and other Python dependencies:

    # We require Python3, so if that's not your default, first start a virtual environment:
    python3 -m venv ~/.aiy_venv
    source ~/.aiy_venv/bin/activate

    # Move to the aiyprojects-raspbian repo root...

    # Install the dependencies:
    python3 -m pip install -r docs/requirements.txt

    # Build the docs:
    make docs

The results are output in `docs/_build/html/`.

**Note:** These output files should not be committed to this repository. We use readthedocs.org
to generate the HTML documentation directly from GitHub—this repo holds the *source files
only*, not the built files.

For more information about the syntax in these RST files, see the [reStructuredText documentation](
http://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html).
