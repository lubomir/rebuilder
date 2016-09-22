#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

long_description = ''

requires = [
]


setup(
    name='rebuilder',
    version='0.1.0',
    description='Rebuild many packages',
    long_description=long_description,
    author='Lubomír Sedlář',
    author_email='lsedlar@redhat.com',
    url='https://github.com/lubomir/rebuilder',
    license='GPLv3+',
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3 :: Only",
    ],
    install_requires=requires,
    test_suite='nose.collector',
    packages=find_packages(),
    include_package_data=True,
    entry_points="""
    [console_scripts]
    rebuilder = rebuilder:main
    """
)
