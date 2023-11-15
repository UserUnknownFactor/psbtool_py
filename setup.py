"""
PSB Tool
-----------
Tool for translating KiriKiri Z (E-Mote) .psb files

Link
`````
 `github <https://github.com/UserUnknownFactor/psbtool_py>`_

"""
from setuptools import setup, find_packages
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md')) as f: long_description = f.read()
#with open(path.join(this_directory, 'requirements.txt')) as f: requirements = f.read().splitlines()

setup(
    name='psbtool_py',
    version='0.1.1',
    url='https://github.com/UserUnknownFactor/psbtool_py',
    license='MIT',
    author='UserUnknownFactor',
    author_email='noreply@example.com',
    description='Tool for translating KiriKiri Z .psb files',
    long_description=long_description,
    #install_requires=requirements,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Games/Entertainment',
    ],
    packages = find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'psb_tool=psbtool_py.psb_tool:main', 
            'tjs_tool=psbtool_py.tjs_tool:main'
        ]
    }
)
