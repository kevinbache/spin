import shutil
import time
from pathlib import Path

import click
from cookiecutter.main import cookiecutter

from spin import settings, spin_settings, utils


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
# INIT
############################################
@root.command()
@click.pass_context
@click.option('--name', help="Your full name", prompt="Your full name (spaces fine, no quotes needed)")
@click.option('--email', help="Your email", prompt="Your email")
@click.option('--github-username', help="Your Github Username", prompt="Your Github Username")
def init(ctx, name, email, github_username):
    """Create .spinrc in your home directory."""
    spin_tempname = '.spintmp'
    extra_context = {
        'name': name,
        'email': email,
        'github_username': github_username,
        'spin_tempname': spin_tempname,
    }

    _ = cookiecutter(
        str(settings.TEMPLATES_PATH / 'spin_config'),
        extra_context=extra_context,
        no_input=True,
        output_dir=Path.home()
    )

    tmpdir = Path.home() / spin_tempname
    shutil.copy2(str(tmpdir / settings.SPIN_RC_FILENAME), str(Path.home()))
    shutil.rmtree(tmpdir)


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

    extra_context.update(spin_settings.load_spinrc()['project'])

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

