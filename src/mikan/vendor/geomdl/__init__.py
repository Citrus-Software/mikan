"""Object-oriented B-Spline and NURBS evaluation library in pure Python

.. moduleauthor:: Onur R. Bingol <contact@onurbingol.net>

"""

import os


def geomdl_version():
    version_file = os.path.join(os.path.dirname(__file__), "VERSION.txt")
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return f.read()
    return "0.0.0-dev"


# Library version
__version__ = geomdl_version()

# Support for "from geomdl import *"
# @see: https://stackoverflow.com/a/41895257
# @see: https://stackoverflow.com/a/35710527
__all__ = [
    "BSpline",
    "compatibility",
    "construct",
    "convert",
    "CPGen",
    "elements",
    "evaluators",
    "exchange",
    "exchange_vtk",
    "fitting",
    "helpers",
    "linalg",
    "multi",
    "NURBS",
    "operations",
    "ray",
    "tessellate",
    "utilities",
    "voxelize",
]
