import os
from pathlib import Path
import json
import argparse

from conda.cli.python_api import run_command

# Windows support taken from https://stackoverflow.com/a/1146404
try:
    from winreg import (
        CloseKey,
        OpenKey,
        QueryValueEx,
        SetValueEx,
        HKEY_CURRENT_USER,
        HKEY_LOCAL_MACHINE,
        KEY_ALL_ACCESS,
        KEY_READ,
        REG_EXPAND_SZ,
    )
except ImportError:
    pass

commands_app = {"mercurial": ["hg"], "tortoisehg": ["hg", "thg"]}


def env_keys(user=True):
    if user:
        root = HKEY_CURRENT_USER
        subkey = "Environment"
    else:
        root = HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    return root, subkey


def get_env(name, user=True):
    root, subkey = env_keys(user)
    key = OpenKey(root, subkey, 0, KEY_READ)
    try:
        value, _ = QueryValueEx(key, name)
    except WindowsError:
        return ""
    return value


def set_env(name, value):
    key = OpenKey(HKEY_CURRENT_USER, "Environment", 0, KEY_ALL_ACCESS)
    SetValueEx(key, name, 0, REG_EXPAND_SZ, value)
    CloseKey(key)


def modif_config_file(path_config, line_config):
    if path_config.exists():
        with open(path_config) as file:
            lines = file.readlines()
        if line_config not in lines:
            print(f"Add line {line_config} at the end of file {path_config}")
            with open(path_config, "a") as file:
                file.write("\n" + line_config + "\n")


def install_app(app_name):

    package_name = app_name + "-app"

    try:
        result = run_command("search", package_name, "--json")
    except Exception:
        package_name = app_name
        result = run_command("search", package_name, "--json")
    # else:
    #     data = json.loads(result[0])
    #     print(data[package_name][-1])

    result = run_command("info", "--json")
    data_conda = json.loads(result[0])
    # print(data_conda)
    path_root = data_conda["root_prefix"]

    if data_conda["root_writable"]:
        path_bin = Path(path_root) / "condabin/app"
    else:
        if not os.name == "nt":
            path_bin = Path.home() / ".local/bin/conda-app"
        else:
            # TODO: a better PATH for Windows?
            path_bin = Path.home() / "bin/conda-app"
    path_bin.mkdir(exist_ok=True, parents=True)

    # Bash
    modif_config_file(Path.home() / ".bashrc", f"export PATH={path_bin}:$PATH\n")

    # Fish
    modif_config_file(
        Path.home() / ".config/fish/config.fish",
        f"set -gx PATH {path_bin} $PATH\n",
    )

    # Windows
    if os.name == "nt":
        PATH = get_env("PATH")
        path_bin = str(path_bin)
        if path_bin not in PATH:
            PATH = path_bin + ";" + PATH
            set_env("PATH", PATH)

    env_name = "_env_" + app_name
    envs = data_conda["envs"]
    env_names = []
    for path_env in envs:
        if path_env.startswith(path_root):
            path_env = path_env[len(path_root) + 1 :]
        if path_env.startswith("envs" + os.path.sep):
            path_env = path_env[5:]

        env_names.append(path_env)

    env_path = Path(path_root) / "envs" / env_name

    if env_name not in env_names:
        print(
            f"create conda environment {env_name} with package {package_name}... ",
            end="",
        )

        result = run_command("create", "-n", env_name, package_name, "--json")
        try:
            data_create = json.loads(result[0])
        except json.decoder.JSONDecodeError:
            print("json.decoder.JSONDecodeError")
            print(result[0])
        else:
            env_path = Path(data_create["prefix"])

        print("done")

        if app_name == "mercurial":
            print("Install hg-git with pip")
            run_command(
                "run",
                "-n",
                env_name,
                "pip",
                "install",
                "hg+https://bitbucket.org/durin42/hg-git",
            )

        try:
            commands = commands_app[app_name]
        except KeyError:
            commands = [app_name]

        for command in commands:
            path_command = env_path / "bin" / command
            path_symlink = path_bin / command
            if path_symlink.exists():
                path_symlink.unlink()
            path_symlink.symlink_to(path_command)

        print(
            f"{app_name} should now be installed in\n{env_path}\n"
            f"Open a new terminal and the command(s) {commands} "
            "should be available"
        )
    else:
        print(
            f"environment {env_name} already exists in \n{env_path}\n"
            f"Delete it to reinstall {app_name}"
        )


def main():

    parser = argparse.ArgumentParser(
        prog="conda-app", description="Install applications using conda."
    )
    parser.add_argument(
        "command", type=str, help="    install: install an application"
    )

    parser.add_argument("package_spec", type=str, help="Package to install.")

    args = parser.parse_args()

    if args.command != "install" or args.package_spec != "mercurial":
        print(args, args.command, args.package_spec != "mercurial")
        raise NotImplementedError
    else:
        install_app(args.package_spec)


if __name__ == "__main__":
    main()
