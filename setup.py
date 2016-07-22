#-*- coding: utf-8 -*-

"""
    ProteusISC
    ~~~~~

    Setup
    `````

    $ pip install . # or python setup.py install
"""

import codecs
import os
import re
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

def read(*parts):
    """Taken from pypa pip setup.py:
    intentionally *not* adding an encoding option to open, See:
    https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    """
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

setup(
    name='proteusisc',
    version=find_version("proteusisc", "__init__.py"),
    url='https://github.com/diamondman/proteusisc',
    author='Jessy Diamond Exum',
    author_email='jessy.diamondman@gmail.com',
    packages=[
        'proteusisc',
        'proteusisc/drivers'
        ],
    platforms='any',
    license='MIT',
    install_requires=[
        'libusb1 >= 1.5.0',
        'bitarray >= 0.8.1',
        'bs4 >= 0.0.1',
        'requests >= 2.10.0',
    ],
    description="Driver framework for In System Configureation (ISC) Controllers (for example, JTAG)",
    long_description=open(os.path.join(os.path.dirname(__file__),
                                       'README.md')).read(),
)
