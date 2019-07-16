import shutil
import time
from pathlib import Path

import click
from cookiecutter.main import cookiecutter

from spin import settings, spin_config, utils, ssh


############################################
# spin
############################################
@click.group()
@click.pass_context
def root(ctx):
    """This is the CLI for interacting with Spin."""
    pass


############################################
# init
############################################
@root.command()
@click.pass_context
@click.option('--name', help="Your full name", prompt="Your full name (spaces fine, no quotes needed)")
@click.option('--email', help="Your email", prompt="Your email")
@click.option('--github-username', help="Your Github Username", prompt="Your Github Username")
# @click.option(
#     '--private-key',
#     help="The path to a private ssh key on your local machine",
#     prompt="The path to a private ssh key on your local machine",
#     default='~/.ssh/id_rsa',
# )
# def init(ctx, name, email, github_username, private_key_filename):
def init(ctx, name, email, github_username):
    """Create .spinrc in your home directory + create or claim a private key."""
    # if not utils.file_exists(private_key_filename):
    #     creator = ssh.SshKeyCreator(private_key_filename, comment=email)
    #     creator.create(do_error_if_exists=True, do_add_ssh_config_entry=False)

    rc = spin_config.SpinRc(
        spin_config.SpinRcUser(name, email, github_username),
        projects=[],
    )
    rc.save()

############################################
# up
############################################
@root.group(invoke_without_command=True)
@click.pass_context
def up(ctx):
    """Create things."""
    pass


############################################
# up project
############################################
@up.command()
@click.argument('pkg_slug')
@click.argument('output_dir', default='.')
@click.option('--config/--no-config', is_flag=True, default=False)
@click.option('--install/--no-install', is_flag=True, default=True)
@click.option('--set-current/--no-set-current', is_flag=True, default=True)
@click.pass_context
def project(ctx, pkg_slug, output_dir, config, install, set_current):
    """Create a directory containing spin project files."""
    # extra_content is a cookiecutter concept which overwrites cookiecutter.json
    extra_context = {}
    if pkg_slug is not None:
        extra_context['pkg_slug'] = pkg_slug

    rc = spin_config.SpinRc.load()
    extra_context.update(rc.user.to_dict())

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
    rc_project = spin_config.SpinRcProject(project_dir)
    rc.add_project(rc_project, set_current)
    rc.save()


############################################
# up cluster
############################################
@up.command()
@click.pass_context
def cluster(ctx):
    """Create an empty cluster using the config.py located in your current project."""
    config = spin_config.load_project_config_from_spinrc()
    utils.confirm_prompt(f"You are about to spin up a cluster for the project {config.name}")

    print(f"Creating cluster: {config.cluster.name}...")
    config.cluster.create()
    for name, node_pool in config.cluster.node_pools.items():
        print(f"  creating node pool {name}")
        node_pool.create()

#
# ############################################
# # set
# ############################################
# @root.group(invoke_without_command=True)
# @click.pass_context
# def set(ctx):
#     """Set config values."""
#     pass
#
#
# ############################################
# # set project
# ############################################
# @set.command()
# @click.pass_context
# @click.argument('name')
# def project(ctx, name):
#     """Set the current project. Refer to the project by it's short name, usually just the name of the package."""
#     spin_config.SpinRc.load_and_set_current_project_and_save(name)
#     return
#
#
# ############################################
# # get
# ############################################
# @root.group(invoke_without_command=True)
# @click.pass_context
# def get(ctx):
#     """Get things."""
#     pass
#
#
# ############################################
# # get project
# ############################################
# @get.command()
# @click.pass_context
# def project(ctx):
#     """Get the name of the current project if there is one."""
#     project = spin_config.SpinRc.load_and_get_current_project()
#     if project is not None:
#         print(project.name)
#
# ############################################
# # add
# ############################################
# @root.group(invoke_without_command=True)
# @click.pass_context
# def add(ctx):
#     """Add things to the config."""
#     pass
#
#
# ############################################
# # get project
# ############################################
# @add.command()
# @click.pass_context
# @click.argument(
#     'project_dir',
#     # help='The directory containing an existing spin project.',
#     type=click.Path(exists=True, file_okay=False),
# )
# @click.argument(
#     'config_file_location',
#     # help='The config.py file within the spin project directory.  Defaults to location/config.py',
#     required=False,
#     default=None,
# )
# @click.option(
#     '--set-current',
#     help='Set the added project to be the current default spin project.',
#     is_flag=True,
#     required=False,
#     default=False,
# )
# def project(ctx, project_dir, config_file_location, set_current):
#     """Add a project to the list of projects in your spinrc file."""
#     if config_file_location is None:
#         config_file_location = spin_config.SpinRcProject.get_config_location_from_project_directory(project_dir)
#
#     if not Path(config_file_location).exists():
#         raise IOError(f"No file found at {str(config_file_location)}")
#
#     project = spin_config.SpinRcProject(
#         project_dir,
#         project_config_file=config_file_location,
#     )
#
#     rc = spin_config.SpinRc.load()
#     for p in rc.projects:
#         if project.name == p.name:
#             raise ValueError(f"You already have a project named {project.name} "
#                              f"in your spinrc located at {str(spin_config.SpinRc.DEFAULT_LOCATION_PATH)}")
#
#         if project.project_dir == p.project_dir:
#             raise ValueError(f"You already have a project at the directory {project.project_dir} "
#                              f"in your spinrc located at {str(spin_config.SpinRc.DEFAULT_LOCATION_PATH)}")
#
#         if project.project_config_file == p.project_config_file:
#             raise ValueError(f"You already have a project with the config file {project.project_config_file} "
#                              f"in your spinrc located at {str(spin_config.SpinRc.DEFAULT_LOCATION_PATH)}")
#
#     rc.projects.append(project)
#     if set_current:
#         rc.set_current_project(project.name)
#
#     rc.save()

if __name__ == '__main__':
    pass