import re
import ast
import platform
from setuptools import setup, find_packages

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('pgcli/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

description = 'CLI for Postgres Database. With auto-completion and syntax highlighting.'

install_requirements = [
    'pgspecial>=1.10.0',
    'click >= 4.1',
    'Pygments >= 2.0',  # Pygments has to be Capitalcased. WTF?
    'prompt_toolkit>=1.0.10,<1.1.0',
    'psycopg2-binary >= 2.7.4',
    'sqlparse >=0.2.2,<0.3.0',
    'configobj >= 5.0.6',
    'humanize >= 0.5.1',
    'cli_helpers[styles] >= 1.0.1',
]


# setproctitle is used to mask the password when running `ps` in command line.
# But this is not necessary in Windows since the password is never shown in the
# task manager. Also setproctitle is a hard dependency to install in Windows,
# so we'll only install it if we're not in Windows.
if platform.system() != 'Windows' and not platform.system().startswith("CYGWIN"):
    install_requirements.append('setproctitle >= 1.1.9')

setup(
    name='pgcli',
    author='Pgcli Core Team',
    author_email='pgcli-dev@googlegroups.com',
    version=version,
    license='BSD',
    url='http://pgcli.com',
    packages=find_packages(),
    package_data={'pgcli': ['pgclirc',
                            'packages/pgliterals/pgliterals.json']},
    description=description,
    long_description=open('README.rst').read(),
    install_requires=install_requirements,
    entry_points='''
        [console_scripts]
        pgcli=pgcli.main:cli
    ''',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: SQL',
        'Topic :: Database',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
