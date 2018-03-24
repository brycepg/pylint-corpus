import os
import glob

import pylint
import pylint.lint

import pytest


# Ordered by SLOC
def test_pyfunctional(benchmark):
    # SLOC: 2501
    _benchmark_autocomplete(benchmark, "PyFunctional", module_name="functional")

def test_requests(benchmark):
    # SLOC: 2530
    _benchmark_autocomplete(benchmark, "requests")

def test_pgcli(benchmark):
    # SLOC: 3131
    _benchmark_autocomplete(benchmark, "pgcli")

def test_utilisnips(benchmark):
    # SLOC: 3330
    _benchmark_autocomplete(benchmark, "ultisnips",
                            module_name=os.path.join("pythonx", "UltiSnips"))

def test_pycodestyle(benchmark):
    # SLOC: 3466
    _benchmark_autocomplete(benchmark, "pycodestyle", module_name="pycodestyle.py")

def test_yapf(benchmark):
    # SLOC: 3815
    _benchmark_autocomplete(benchmark, "yapf")

def test_lektor(benchmark):
    # SLOC: 8794
    _benchmark_autocomplete(benchmark, "lektor")


@pytest.mark.skip('takes 10 minutes per round')
def test_home_assistant(benchmark):
    # SLOC: 202274
    directory = 'home-assistant-0.65.6'
    benchmark(run_catch_exit, ['-rn', '-sn', f'{directory}/homeassistant', '--rcfile', _rcfile_location(directory)])


@pytest.mark.skip("never completes")
def test_pandas(benchmark):
    # SLOC: 232565
    _benchmark_autocomplete(benchmark, "pandas")


def _rcfile_location(directory):
    return os.path.join(directory, 'pylintrc')


def _benchmark_autocomplete(benchmark, base, module_name=None):
    directory_glob = glob.glob(f"{base}*")
    assert len(directory_glob) == 1
    [directory] = directory_glob
    if not module_name:
        module = os.path.join(directory, base)
    else:
        module = os.path.join(directory, module_name)
    if not os.path.exists(module):
        raise Exception(f"{module} does not exist")
    pylint_args = ['-rn', '-sn', module]

    rcfile_path = _rcfile_location(directory)
    if os.path.exists(rcfile_path):
        pylint_args.extend(['--rcfile', rcfile_path])

    benchmark.pedantic(_run_catch_exit,
                       args=(pylint_args,),
                       rounds=3)

def _run_catch_exit(args):
    try:
        pylint.lint.Run(args)
    except SystemExit as exc:
        if exc.code == 1:
            raise
        # Pylint returns nonzero if there are any messages -- can't have that
        pass

