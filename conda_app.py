import os
from pathlib import Path
import json
import argparse

from conda.cli.python_api import run_command

commands_app = {"mercurial": ["hg"], "tortoisehg": ["hg", "thg"]}


def modif_config_file(path_config, line_config):
    path_config = Path(path_config)
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
        if os.name == "nt":
            # quickfix: I wasn't able to permanently set the PATH on Windows
            path_bin = Path(path_root) / "condabin"
        else:
            path_bin = Path(path_root) / "condabin/app"
    else:
        if not os.name == "nt":
            path_bin = Path.home() / ".local/bin/conda-app"
        else:
            raise NotImplementedError
    path_bin.mkdir(exist_ok=True, parents=True)

    export_path_posix = f"export PATH={path_bin}:$PATH\n"
    # bash
    modif_config_file(Path.home() / ".bashrc", export_path_posix)

    # zsh
    modif_config_file(Path.home() / ".zshrc", export_path_posix)

    # fish
    modif_config_file(
        Path.home() / ".config/fish/config.fish",
        f"set -gx PATH {path_bin} $PATH\n",
    )

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
            print("Install hg-git with pip... ", end="")
            run_command(
                "run",
                "-n",
                env_name,
                "pip",
                "install",
                "hg+https://bitbucket.org/durin42/hg-git",
            )
            print("done")

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

    if args.command != "install":
        print(args, args.command)
        raise NotImplementedError
    else:
        install_app(args.package_spec)


if __name__ == "__main__":
    main()
