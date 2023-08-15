#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ ]

test_requirements = ['pytest>=3', ]

setup(
    author="VTDA Research Group",
    author_email='ashleyvillar@cfa.harvard.edu',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Allow secondary processing of alerts from existing brokers or directly from streams",
    entry_points={
        'console_scripts': []
    },
    install_requires=requirements,
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='vtda-alert-pipeline',
    name='vtda-alert-pipeline',
    packages=find_packages(include=['vtda-alert-pipeline', 'vtda-alert-pipeline.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/villrv/vtda-alert-pipeline',
    version='0.1.0',
    zip_safe=False,
)
