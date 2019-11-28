[![release](https://img.shields.io/pypi/v/conda-app.svg)](https://pypi.python.org/pypi/conda-app/)
[![Build Status](https://travis-ci.org/paugier/conda-app.svg?branch=master)](https://travis-ci.org/paugier/conda-app)
[![Build Status](https://ci.appveyor.com/api/projects/status/github/paugier/conda-app?branch=master&svg=true)](https://ci.appveyor.com/project/paugier/conda-app/branch/master)

# Install applications using conda

Tiny conda extension (actually a commandline tool using conda) to install
applications.

The main advantages are:

- very simple **cross-platform** installation commands for Windows, macOS and
  Linux (and different shells, as bash, fish and zsh).

- the applications are installed in isolated conda environments.

- commands provided by the applications are available system-wide, i.e. when
  the associated conda environment is not activated.

## Installation of conda-app

conda-app needs to be installed in the `base` conda environment:

```bash
conda activate base
pip install conda-app
```

-----------
**Warning**

Note that conda-app needs Python >= 3.6, so if your base environment still uses
Python 2.7, you first need to update it with `conda update conda` and `conda
install python=3`.

-----------

## Example

With the conda-forge channel added (`conda config --add channels conda-forge`),
one should be able to install Mercurial (plus few important extensions) with:

```bash
conda-app install mercurial
```

This should also work:

```bash
conda-app list
conda-app uninstall mercurial
```

**Open a new terminal** (on Windows, the "Conda Prompt") and the Mercurial
command `hg` should be available.