import io
import os
import re

from setuptools import find_packages
from setuptools import setup


def read(filename):
    filename = os.path.join(os.path.dirname(__file__), filename)
    text_type = type(u"")
    with io.open(filename, mode="r", encoding='utf-8') as fd:
        return re.sub(text_type(r':[a-z]+:`~?(.*?)`'), text_type(r'``\1``'), fd.read())


setup(
    name="{{ cookiecutter.pkg_slug }}",
    version='0.0.1',
    url="{{ cookiecutter.package_url }}",
    license='MIT',

    author="{{ cookiecutter.author_name }}",
    author_email="{{ cookiecutter.author_email }}",

    description="{{ cookiecutter.package_description }}",
    long_description=read("README.md"),

    packages=find_packages(exclude=('tests',)),

    # When you install this package, this console_scripts option ensures that another executable python script named
    # `{{ cookiecutter.docker_entrypoint_script_name }}` is added to your path which will call the function called
    # `{{ cookiecutter.main_func_name }}` in the file imported in
    # `{{ cookiecutter.pkg_slug }}.{{ cookiecutter.docker_entrypoint_script_name }}`
    entry_points={
        'console_scripts': [
            '{{ cookiecutter.docker_entrypoint_script_name }}={{ cookiecutter.pkg_slug }}.{{ cookiecutter.docker_entrypoint_script_name }}:{{ cookiecutter.main_func_name }}'
        ],
    },

    install_requires=[
        'numpy',
        'scipy',
        'pandas',
        'keras',
        'google-cloud-storage',
    ],

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
