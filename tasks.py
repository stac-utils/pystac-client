from invoke import task


@task(help={'coverage': 'Whether to generate a coverage report. Defaults to True.'})
def unit_tests(c, coverage=True, record_mode='once'):
    """Runs the unit tests and, optionally, generates a coverage report."""
    cmd = f'pytest --record-mode {record_mode} --block-network'
    if coverage:
        cmd += ' --cov=pystac_api --cov-report=term-missing'
    c.run(cmd)


@task
def lint(c):
    """Runs the flake8 linter"""
    c.run('flake8')
    c.run('isort --check-only -q .')
    c.run('vulture')


@task(unit_tests, lint)
def ci(c):
    """Runs unit tests and linter."""


@task
def build_docs(c, output_format='html'):
    """Builds the documentation using sphinx."""
    c.run(f'sphinx-build -M {output_format} docs/source docs/build')
