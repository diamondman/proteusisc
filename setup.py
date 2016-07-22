#-*- coding: utf-8 -*-

"""
    ProteusISC
    ~~~~~

    Setup
    `````

    $ pip install . # or python setup.py install
"""

import sys
import os
from distutils.core import setup

setup(
    name='proteusisc',
    version='0.0.12',
    url='https://github.com/diamondman/proteusisc',
    author='Jessy Diamond Exum',
    author_email='jessy.diamondman@gmail.com',
    packages=[
        'proteusisc',
        'proteusisc/drivers',
        'proteusisc/test',
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
