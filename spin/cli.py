import time

import click
from cookiecutter.main import cookiecutter

from spin import spin_settings, settings, utils


############################################
# SPIN
############################################
@click.group()
@click.pass_context
def root(ctx):
    """
    Load project settings
    """
    pass

############################################
# UP
############################################
@root.group(invoke_without_command=True)
@click.pass_context
def up(ctx):
    pass


############################################
# PROJECT
############################################
@up.command()
@click.argument('pkg_slug', default='my_project')
@click.argument('output_dir', default='.')
@click.option('--config/--no-config', is_flag=True, default=False)
@click.option('--install/--no-install', is_flag=True, default=True)
@click.pass_context
def project(ctx, pkg_slug, output_dir, config, install):

    # extra_content is a cookiecutter concept which overwrites cookiecutter.json
    extra_context = {}
    if pkg_slug is not None:
        extra_context['pkg_slug'] = pkg_slug

    project_dir = cookiecutter(
        str(settings.TEMPLATES_PATH / 'project'),
        extra_context=extra_context,
        no_input=not config,
        output_dir=output_dir
    )
    if install:
        time.sleep(1.0)
        exitcode, out, err = utils.get_exitcode_stdout_stderr(f'pip install --editable {project_dir}')
        print(f"New project install finished with exit code: {exitcode}")
        if out:
            print(f'    stdout: {out}')
        if err:
            print(f'    stderr: {err}')

    print(f"Created project at {project_dir}")


# spin_settings = spin_settings.load_project_settings()