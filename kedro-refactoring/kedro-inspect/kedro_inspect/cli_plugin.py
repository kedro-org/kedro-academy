import click
from kedro.framework.project import pipelines
from .plugin import _inspect_func

# TODO: Take your code from cli.py and put it here.
#  Instead of using @cli, use the new click group `inspect_cli`.

@click.group(name="kedro-inspect")
def inspect_cli():
    pass
