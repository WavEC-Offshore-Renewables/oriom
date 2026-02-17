# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# -- Project information -----------------------------------------------------

project = 'ORIOM'
copyright = '2022, WavEC - Offshore Renewables'
author = 'Riccardo Meda, Luís Amaral, Francisco Correia da Fonseca, Miguel de Matos e Sá, and Alessandra Imperadore'

# The full version, including alpha/beta/rc tags
release = '0.1.0'


# -- General configuration ---------------------------------------------------
import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    "sphinx.ext.viewcode"
    # 'sphinx.ext.intersphinx',
    # 'sphinx.ext.doctest'
]

add_module_names = False                 # Show short names without module prefixes
modindex_common_prefix = ["oriom."]  # Trim common module prefix in modindex
autosummary_generate = True              # Auto-generate summary stub pages
autosummary_generate_overwrite = True         # Overwrite old stubs with new template

autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'inherited-members': True,
    'show-inheritance': True,
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# Always include class __init__ method.
def skip(app, what, name, obj, would_skip, options):
    if name == '__init__':
        return False
    elif '_' in name and '__' not in name:
        # Ignore special functions ("__")
        # but not internal use functions ("_")
        return False
    return would_skip

def setup(app):
    app.connect("autodoc-skip-member", skip)

    # Directory CSS custom
    css_path = os.path.join(os.path.dirname(__file__), "_static", "custom.css")
    os.makedirs(os.path.dirname(css_path), exist_ok=True)

    # Write CSS if not present
    if not os.path.exists(css_path):
        with open(css_path, "w", encoding="utf-8") as f:
            f.write("""
            /* Wrap long names in docs */
            .rst-content code, .rst-content tt, .docutils.literal {
                white-space: pre-wrap !important;
                word-break: break-word !important;
            }
            .wy-nav-side .wy-menu-vertical li a {
                white-space: normal !important;
            }
            """)

    # Add CSS to build
    app.add_css_file("custom.css")


def modify_name_rst():
    for dirpath, dirnames, filenames in os.walk("_api/"):
        for filename in filenames:
            if filename.endswith(".rst"):
                filepath = os.path.join(dirpath, filename)

                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                if lines:
                    lines[0] = lines[0].split('.')[-1]
                else:
                    continue

                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
# html_theme = 'classic'

html_logo = "_static/ORIOM_logo.png"    # Header logo for the docs
html_favicon = "_static/ORIOM_logo.png" # Optional: reuse as favicon

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_logo = "_static/ORIOM_logo.png"

modify_name_rst()
