import os
from pathlib import Path
import json
import argparse


from conda.cli.python_api import run_command


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

    # todo: windows + use data_conda
    path_bin = Path.home() / ".local/bin/conda-app"
    path_bin.mkdir(exist_ok=True, parents=True)

    # bash
    modif_config_file(Path.home() / ".bashrc", f"export PATH={path_bin}:$PATH\n")

    # fish
    modif_config_file(
        Path.home() / ".config/fish/config.fish",
        f"set -gx PATH {path_bin} $PATH\n",
    )

    # todo: modify PATH on Windows!

    env_name = "_env_" + app_name

    path_root = data_conda["root_prefix"]

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
        print(f"create conda environment {env_name}")

        result = run_command("create", "-n", env_name, package_name, "--json")
        data_create = json.loads(result[0])
        env_path = Path(data_create["prefix"])

        if app_name == "mercurial":
            run_command(
                "run",
                "-n",
                env_name,
                "pip",
                "install",
                "hg+https://bitbucket.org/durin42/hg-git",
            )

        commands = ["hg"]
        command = commands[0]

        path_command = env_path / "bin" / command
        path_symlink = path_bin / command

        if path_symlink.exists():
            path_symlink.unlink()

        path_symlink.symlink_to(path_command)

        print(
            f"{app_name} should now be installed in\n{env_path}\n"
            f"The command(s) {commands} should be available"
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
