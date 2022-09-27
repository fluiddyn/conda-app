# Conda-app

[![PyPI][pypi-badge]][pypi-link]
[![Github Actions][GH-badge]][GH-link]
[![Appveyor][Appveyor-badge]][Appveyor-link]

## Install isolated applications using conda

`conda-app` is a tiny `conda` extension (actually a commandline tool using
`conda` or `mamba`) to install applications in isolated environments. Like
[pipx](https://github.com/pypa/pipx) but with conda environments.

The main advantages are:

- very simple **cross-platform** installation commands for Windows, macOS and
  Linux (and different shells, as bash, fish and zsh).

- the applications are installed in **isolated** environments.

- commands provided by the applications are **available system-wide**, i.e. even
  when the associated conda environment is not activated.

- Installation from the `conda-forge` channel so there is **no need for
compilation**.

### Installation of conda-app

```bash
pip install conda-app
```

### Example of Mercurial

Mercurial and common extensions (`hg-git` and `hg-evolve`) can be installed with:

```bash
conda-app install mercurial
```

Then, in **a new terminal** (on Windows, the "Conda Prompt"), the Mercurial
command `hg` should be available so one can try `hg version -v`.

This should also work:

```raw
$ conda-app list
Installed applications:
 ['mercurial', 'spyder', 'pandoc']

$ conda-app uninstall pandoc
...
```

[pypi-badge]: https://img.shields.io/pypi/v/conda-app.svg
[pypi-link]: https://pypi.python.org/pypi/conda-app/
[GH-badge]: https://github.com/fluiddyn/conda-app/actions/workflows/ci.yml/badge.svg?branch=branch/default
[GH-link]: https://github.com/fluiddyn/conda-app/actions
[Appveyor-badge]: https://ci.appveyor.com/api/projects/status/github/fluiddyn/conda-app?svg=true
[Appveyor-link]: https://ci.appveyor.com/project/fluiddyn/conda-app
