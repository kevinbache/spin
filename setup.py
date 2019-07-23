from setuptools import setup, find_packages

setup(
    name='spin',
    version='0.0.1',
    description='spin',
    author='"Kevin Bache" <kevin.bache@gmail.com>',
    install_requires=[
        'Click',
        'cookiecutter',
        'sshconf',
    ],
    packages=find_packages(),
    classifiers=[],
    python_requires='>=3.5.3',
    include_package_data=True,
    entry_points='''
        [console_scripts]
        spin=spin.cli:root
    ''',
)
