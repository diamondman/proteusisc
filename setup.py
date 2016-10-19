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
from setuptools import setup, Extension

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
        'proteusisc/drivers',
        'proteusisc/drivers/xilinxPC1driver',
        'proteusisc/test_utils'
        ],
    platforms='any',
    license='LGPL 2.1',
    install_requires=[
        'libusb1 >= 1.5.3',
        'bitarray >= 0.8.1',
        'bs4 >= 0.0.1',
        'requests >= 2.11.1',
    ],
    ext_modules = [
        Extension(
            'proteusisc.drivers.xilinxPC1driver._xpcu1utils',
            sources = ['proteusisc/drivers/xilinxPC1driver/_xpcu1utils.c'],
            extra_compile_args = ["-std=c99"],
        )
    ],
    description="Driver framework for In System Configureation (ISC) Controllers (for example, JTAG)",
    long_description=open(os.path.join(os.path.dirname(__file__),
                                       'README.md')).read(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Topic :: Software Development :: Embedded Systems",
        "Topic :: System :: Hardware",
    ],
)
