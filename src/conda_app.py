import os
import json
import platform
import subprocess

from pathlib import Path
from functools import partial
from shutil import which

import click
import userpath

_open = partial(open, encoding="utf-8")

SHELLS = ["bash", "fish", "sh", "xonsh", "zsh"]


def check_command(conda_command):
    try:
        completed_process = subprocess.run(
            [conda_command, "install", "-h"],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    else:
        if completed_process.returncode == 0:
            return True


is_conda_avail = check_command("conda")
is_mamba_avail = check_command("mamba")


if not is_conda_avail and not is_mamba_avail:
    raise RuntimeError("No conda or mamba executable available")


def run_conda(*args, conda_command="conda", capture_output=True):
    cmd = [conda_command]
    cmd.extend(args)
    completed_process = subprocess.run(
        cmd, capture_output=capture_output, text=True, check=True
    )
    return completed_process.stdout


commands_app = {"mercurial": ["hg", "hg-setup"], "tortoisehg": ["hg", "thg"]}
known_apps_with_app_package = ["mercurial"]

if os.name == "nt":
    data_dir = "AppData"
else:
    data_dir = ".local/share"

if platform.system() == "Darwin":
    bash_config = Path.home() / ".bash_profile"
else:
    bash_config = Path.home() / ".bashrc"
if not bash_config.exists():
    bash_config.touch()

data_dir = Path.home() / data_dir
data_dir.mkdir(exist_ok=True, parents=True)
path_data = data_dir / "conda-app.json"


def query_yes_no(question, default="yes"):
    """Ask a yes/no question and return the answer.

    Parameters
    ----------

    question : string
       String that is presented to the user.

    default : bool
       The default answer if the user just hits <Enter>.
       It must be "yes" (the default), "no" or None (meaning
       an answer is required of the user).

    Returns
    -------

    answer : bool
       The returned answer.
    """
    valid = {"yes": True, "y": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError(f"invalid default answer: '{default}'")

    while True:
        print(question + prompt, flush=True, end="")
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]

        elif choice in valid:
            return valid[choice]

        else:
            print(
                "Please respond with 'yes' or 'no' (or 'y' or 'n').",
                flush=True,
            )


def get_conda_data():
    result = run_conda("info", "--json")
    return json.loads(result)


def get_env_names(conda_data):
    envs = conda_data["envs"]
    env_names = []
    for path_envs_dir in conda_data["envs_dirs"]:
        for path_env in envs:
            if path_env.startswith(path_envs_dir):
                env_names.append(path_env[len(path_envs_dir) + 1 :])
    return env_names


def load_data():
    if path_data.exists():
        with _open(path_data) as file:
            data = json.load(file)
    else:
        data = {"installed_apps": []}

    return data


def _write_data(data):
    with _open(path_data, "w") as file:
        json.dump(data, file)


def add_to_app_list(app_name):
    data = load_data()
    if app_name not in data["installed_apps"]:
        data["installed_apps"].append(app_name)
    _write_data(data)


def remove_from_app_list(app_name):
    data = load_data()
    data["installed_apps"].remove(app_name)
    _write_data(data)


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def main():
    pass


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument("app_name")
@click.argument("other_packages", nargs=-1, required=False)
def install(app_name, other_packages=None):
    """Install an application."""

    if app_name in known_apps_with_app_package:
        package_name = app_name + "-app"
    else:
        package_name = app_name

    channels = run_conda("config", "--show", "channels", "--json")
    if "conda-forge" not in channels:
        run_conda("config", "--add", "channels", "conda-forge")
        print("Warning: conda-forge channel added!")

    conda_data = get_conda_data()
    path_root = conda_data["root_prefix"]

    path_bin = _get_path_bin(conda_data)
    path_bin.mkdir(exist_ok=True, parents=True)

    _ensurepath(path_bin)

    env_names = get_env_names(conda_data)
    env_name = "_env_" + app_name
    env_path = Path(path_root) / "envs" / env_name

    if env_name not in env_names:
        print(
            f"Creating conda environment {env_name} " f"with package {package_name}...",
            flush=True,
        )

        if is_mamba_avail:
            conda_command = "mamba"
        else:
            conda_command = "conda"

        command = ["create", "-n", env_name, package_name]
        if other_packages:
            command.extend(other_packages)

        command.append("-y")

        run_conda(*command, conda_command=conda_command, capture_output=False)

        result = run_conda("env", "list")
        for line in result.split("\n"):
            if env_name in line:
                try:
                    prefix = line.split()[1]
                except IndexError:
                    pass
                else:
                    break

        env_path = Path(prefix)

        try:
            commands = commands_app[app_name]
        except KeyError:
            commands = [app_name]

        for command in commands:
            if os.name == "nt":
                with _open(path_bin / (command + ".bat"), "w") as file:
                    file.write(
                        "@echo off\n"
                        f"call conda activate {env_name}\n"
                        f"{command} %*\n"
                        "call conda deactivate\n"
                    )
            else:
                path_command = env_path / "bin" / command
                path_symlink = path_bin / command
                if path_symlink.exists():
                    path_symlink.unlink()
                path_symlink.symlink_to(path_command)

        if userpath.need_shell_restart(str(path_bin)):
            txt = "T"
        else:
            txt = "Open a new terminal and t"

        if len(commands) > 1:
            plural = "s"
        else:
            plural = ""

        print(
            f"{app_name} is now installed in\n{env_path}\n"
            + txt
            + f"he command{plural} {commands} should be available."
        )

        add_to_app_list(app_name)
    else:
        print(
            f"environment {env_name} already exists in \n{env_path}\n"
            f"To reinstall or update {app_name}, first uninstall it with:\n"
            f"conda-app uninstall {app_name}"
        )


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument("app_name")
@click.option("-y", "--yes", is_flag=True)
def uninstall(app_name, yes):
    """Uninstall an application."""
    conda_data = get_conda_data()
    env_names = get_env_names(conda_data)

    env_name = "_env_" + app_name

    if env_name not in env_names:
        print(f"{app_name} not installed with conda-app: nothing to do")
        return

    if not yes:
        yes = query_yes_no(f"The application {app_name} will be uninstalled.\nProceed")

    if yes:
        import shutil

        for env_path in conda_data["envs"]:
            if env_path.endswith(os.path.sep + env_name):
                shutil.rmtree(env_path, ignore_errors=True)
                print(f"Directory {env_path} removed")
                remove_from_app_list(app_name)
                break
        else:
            assert False, "Environment not found."


@main.command(name="list", context_settings=CONTEXT_SETTINGS)
def list_apps():
    """List the applications installed by conda-app."""
    data = load_data()
    print("Installed applications:\n", data["installed_apps"])


@main.command(name="ensurepath", context_settings=CONTEXT_SETTINGS)
def ensurepath():
    """Add conda-app path to PATH."""
    conda_data = get_conda_data()
    path_bin = str(_get_path_bin(conda_data))
    _ensurepath(path_bin, verbose=True)

    if userpath.need_shell_restart(path_bin):
        click.echo(
            f"{path_bin} has been been added to PATH, but you need to "
            "open a new terminal or re-login for this PATH change to take "
            "effect. Alternatively, you can source your shell's config file "
            "with e.g. 'source ~/.bashrc'."
        )


def _ensurepath(path_bin, verbose=False):
    path_bin = str(path_bin)
    in_current_path = userpath.in_current_path(path_bin)
    if in_current_path:
        if verbose:
            click.echo(f"{path_bin} is already in PATH.")
        return

    if os.name == "nt":
        shells = None
    else:
        shells = [shell for shell in SHELLS if which(shell) is not None]

    path_added = userpath.prepend(path_bin, "conda-app", shells=shells)

    if not path_added:
        click.secho(
            f"{path_bin} is not added to the PATH environment variable "
            "successfully. You may need to add it to PATH manually.",
            fg="red",
        )
    else:
        click.echo(f"Added {path_bin} to the PATH environment variable.")


def _get_path_bin(conda_data):
    if conda_data["root_writable"]:
        return Path(conda_data["root_prefix"]) / "condabin/app"
    else:
        return Path.home() / ".local/bin/conda-app-bin"
