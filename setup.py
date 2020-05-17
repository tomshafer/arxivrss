"""Package setup script."""

import os

from setuptools import setup


def get_version():
    """Extract version number from arxivrss.py."""
    with open(os.path.join(os.path.dirname(__file__), "arxivrss.py")) as f:
        for line in map(lambda l: l.strip().split(), f):
            if line and "__version__" in line[0]:
                return line[-1].strip("'\"")


setup(
    name="arxivrss",
    version=get_version(),
    description="Deduplicate and tidy a collection of arXiv.org RSS feeds",
    url="https://github.com/tomshafer/arxivrss",
    author="Tom Shafer",
    author_email="contact@tshafer.com",
    license="MIT",
    py_modules=["arxivrss"],
    install_requires=["defusedxml", "requests"],
)
