from invoke import task

unit_tests_help = {
    'coverage': 'Whether to generate a coverage report. Defaults to True.',
    'record_mode': 'The record mode value to use for VCRpy.',
    'verbose': 'Whether to use verbose output.'
}


@task(help=unit_tests_help)
def unit_tests(c, coverage=False, record_mode='once', verbose=False):
    """Runs the unit tests and, optionally, generates a coverage report."""
    cmd = f'pytest --record-mode {record_mode} --block-network'
    if coverage:
        cmd += ' --cov=pystac_api --cov-report=term-missing'
    if verbose:
        cmd += ' -rs'
    c.run(cmd)


@task
def lint(c):
    """Runs the flake8 linter"""
    c.run('flake8')
    c.run('isort --check-only -q pystac_api tests')
    c.run('vulture')


@task
def vulture_allowlist(c):
    """Re-creates the vulture allow-list"""
    c.run('vulture --make-whitelist > vulture_allow.py')


@task(unit_tests, lint)
def ci(c):
    """Runs unit tests and linter."""


@task
def build_docs(c, output_format='html'):
    """Builds the documentation using sphinx."""
    c.run(f'sphinx-build -M {output_format} docs/source docs/build')
