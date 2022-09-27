import os
import sys
from pathlib import Path
import json
import argparse
import platform

import subprocess


def check_command(conda_command):

    try:
        completed_process = subprocess.run(
            [conda_command, "install", "-h"], capture_output=True
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
        cmd, capture_output=capture_output, text=True
    )
    completed_process.check_returncode()
    return completed_process.stdout


commands_app = {"mercurial": ["hg"], "tortoisehg": ["hg", "thg"]}
known_apps_with_app_package = ["mercurial"]
known_apps_without_app_package = ["spyder"]

special_hgrc_windows = ""
if os.name == "nt":
    special_hgrc_windows = "# avoid a bug on Windows if no pager is avail\npaginate = never\n"

default_hgrc = f"""
# File created by conda-app when installing Mercurial
# - change your username and email address
# - delete the character # to activate some lines
#   (in particular the lines starting by username and editor)
[ui]
#username=myusername <email@adress.org>
#editor=nano
tweakdefaults = True
{special_hgrc_windows}
[extensions]
#hgext.extdiff =
# only to use Mercurial with GitHub and Gitlab
hggit =
# more advanced extensions
churn =
shelve =
rebase =
absorb =
evolve =
topic =

#[extdiff]
#cmd.meld =
"""

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
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        print(question + prompt, flush=True, end="")
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]

        elif choice in valid:
            return valid[choice]

        else:
            print(
                "Please respond with 'yes' or 'no' " "(or 'y' or 'n').",
                flush=True,
            )


def modif_config_file(path_config, line_config, force=False):
    path_config = Path(path_config)
    if force and not path_config.exists():
        path_config.touch()
    if not line_config.endswith("\n"):
        line_config = line_config + "\n"
    if path_config.exists():
        with open(path_config) as file:
            lines = file.readlines()
        if lines and lines[-1] and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        if line_config not in lines:
            print(
                f"Add line \n{line_config.strip()}\n"
                f"at the end of file {path_config}"
            )

            with open(
                path_config.with_name(path_config.name + ".orig"), "w"
            ) as file:
                file.write("".join(lines))

            with open(path_config, "a") as file:
                file.write("\n# line added by conda-app\n" + line_config)


def get_conda_data():
    result = run_conda("info", "--json")
    return json.loads(result)


def get_env_names(conda_data):
    envs = conda_data["envs"]
    path_root = conda_data["root_prefix"]
    env_names = []
    for path_env in envs:
        if path_env.startswith(path_root):
            path_env = path_env[len(path_root) + 1 :]
        if path_env.startswith("envs" + os.path.sep):
            path_env = path_env[5:]

        env_names.append(path_env)
    return env_names


def install_app(app_name):

    package_name = app_name + "-app"

    channels = run_conda("config", "--show", "channels", "--json")
    if "conda-forge" not in channels:
        run_conda("config", "--add", "channels", "conda-forge")
        print("Warning: conda-forge channel added!")

    if app_name in known_apps_without_app_package:
        package_name = app_name
    elif app_name not in known_apps_with_app_package:
        print(f"Checking if package {package_name} exists...")
        try:
            result = run_conda("search", package_name, "--json")
        except Exception:
            package_name = app_name
            try:
                result = run_conda("search", package_name, "--json")
            except Exception:
                print(
                    "An exception occurred during the conda search. "
                    "It maybe that the package does not exist"
                )
                sys.exit(1)

        print(f"Package {package_name} found!")

    print("Running conda info... ", end="", flush=True)
    conda_data = get_conda_data()
    print("done")
    path_root = conda_data["root_prefix"]

    if conda_data["root_writable"]:
        if os.name == "nt":
            # quickfix: I wasn't able to permanently set the PATH on Windows
            path_bin = Path(path_root) / "condabin"
        else:
            path_bin = Path(path_root) / "condabin/app"
    else:
        if not os.name == "nt":
            path_bin = Path.home() / ".local/bin/conda-app"
        else:
            print(
                "\nError: conda-app cannot be used on Windows when "
                "conda root is not writable. "
                "You can retry with miniconda installed "
                "only for you (not globally)."
            )
            sys.exit(1)

    path_bin.mkdir(exist_ok=True, parents=True)

    export_path_posix = f"export PATH={path_bin}:$PATH\n"
    # bash
    modif_config_file(bash_config, export_path_posix)

    # zsh
    force_zshrc = platform.system() == "Darwin"
    modif_config_file(
        Path.home() / ".zshrc", export_path_posix, force=force_zshrc
    )

    # fish
    modif_config_file(
        Path.home() / ".config/fish/config.fish",
        f"set -gx PATH {path_bin} $PATH\n",
    )

    env_names = get_env_names(conda_data)
    env_name = "_env_" + app_name
    env_path = Path(path_root) / "envs" / env_name

    if env_name not in env_names:
        print(
            f"Creating conda environment {env_name} "
            f"with package {package_name}... (it can be long...)",
            flush=True,
        )

        if is_mamba_avail:
            conda_command = "mamba"
        else:
            conda_command = "conda"

        run_conda(
            "create",
            "-n",
            env_name,
            package_name,
            "-y",
            conda_command=conda_command,
            capture_output=False,
        )

        result = run_conda("env", "list")
        for line in result.split("\n"):
            if env_name in line:
                prefix = line.split()[1]
                break

        env_path = Path(prefix)

        if app_name == "mercurial":
            path_home_hgrc = Path.home() / ".hgrc"
            if not path_home_hgrc.exists():
                print(
                    "Filling ~/.hgrc with reasonable default "
                    "(edit to fill correct username and email address!)"
                )
                with open(path_home_hgrc, "w") as file:
                    file.write(default_hgrc)

        try:
            commands = commands_app[app_name]
        except KeyError:
            commands = [app_name]

        for command in commands:
            if os.name == "nt":
                with open(path_bin / (command + ".bat"), "w") as file:
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

        if os.name == "nt":
            txt = "T"
        else:
            txt = "Open a new terminal and t"

        print(
            f"{app_name} should now be installed in\n{env_path}\n"
            + txt
            + f"he command(s) {commands} should be available."
        )

        add_to_app_list(app_name)
    else:
        print(
            f"environment {env_name} already exists in \n{env_path}\n"
            f"To reinstall or update {app_name}, first uninstall it with:\n"
            f"conda-app uninstall {app_name}"
        )


def load_data():
    if path_data.exists():
        with open(path_data) as file:
            data = json.load(file)
    else:
        data = {"installed_apps": []}

    return data


def add_to_app_list(app_name):
    data = load_data()
    if app_name not in data["installed_apps"]:
        data["installed_apps"].append(app_name)
    with open(path_data, "w") as file:
        json.dump(data, file)


def list_apps():
    data = load_data()
    print("Installed applications:\n", data["installed_apps"])


def uninstall_app(app_name):
    conda_data = get_conda_data()
    env_names = get_env_names(conda_data)

    env_name = "_env_" + app_name

    if env_name not in env_names:
        print("Nothing to do")
        return

    if query_yes_no(f"The application {app_name} will be uninstalled.\nProceed"):
        import shutil

        path_root = conda_data["root_prefix"]
        env_path = Path(path_root) / "envs" / env_name
        shutil.rmtree(env_path, ignore_errors=True)
        print(f"Directory {env_path} removed")


commands = ["install", "list", "uninstall"]


class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def main():

    parser = argparse.ArgumentParser(
        prog="conda-app",
        description="Install applications using conda.",
        formatter_class=SmartFormatter,
    )
    parser.add_argument(
        "command",
        type=str,
        help=(
            "R|Can be in:\n- install: install an application\n"
            "- uninstall: uninstall an application\n"
            "- list: list applications installed with conda-app\n"
        ),
    )

    parser.add_argument(
        "package_spec",
        type=str,
        nargs="?",
        default=None,
        help="Package to install.",
    )

    args = parser.parse_args()

    if args.command not in commands:
        print(f"command {args.command} unknown")
        sys.exit(1)
    elif args.command == "install":
        install_app(args.package_spec)
    elif args.command == "list":
        list_apps()
    elif args.command == "uninstall":
        uninstall_app(args.package_spec)
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
