#!/usr/bin/env python

from setuptools import setup

setup(
    name='extractpart',
    version='1.0.0',
    description="Extract individual partitions for MBR or GPT disk images",
    long_description="""CLI utility for extracting an individual partition from MBR or GPT
disk images into a file.  eg. Extracting a partition from a VM disk image in order
to be mounted with a loopback file system (aka. "mount -o loop ...").
""",
    url='https://github.com/mdavidsaver/extractpart',
    author='Michael Davidsaver',
    author_email='mdavidsaver@gmail.com',
    license='GPL-2',
    keywords='vm disk image mbr gpt',
    project_urls = {
        'Source': 'https://github.com/mdavidsaver/extractpart',
        'Tracker': 'https://github.com/mdavidsaver/extractpart/issues',
    },
    python_requires='>=3.4',
    packages=['extractpart'],
    entry_points = {
        'console_scripts':['extractpart=extractpart:main'],
    },
)
