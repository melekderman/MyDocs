# Reproducibility Notes

These notes document the Python virtual environment used for the current
electron-transport work in this repository.

Verified on: `2026-04-05 22:12:51 PDT`

## Host system

- OS: `macOS 26.3.1 (build 25D771280a)`
- Kernel: `Darwin 25.3.0`
- Architecture: `arm64` (Apple Silicon)
- Repository path:
  `/Users/melekderman/github/Summer25/3_MCDC-Electron/Apr5_ElectronTransport/MCDC`
- Base git commit at the time these notes were written:
  `85ff0eabf58ec7caf2a9d90b243c74330dad6416`

Note: the local worktree was not clean when these notes were recorded, so the
effective runtime state may differ from the base commit above due to local
uncommitted changes.

## Python used to create the venv

- Python source: Homebrew `python@3.13`
- Python version: `3.13.5`
- Executable used:
  `/opt/homebrew/opt/python@3.13/bin/python3.13`

Venv metadata from `.venv/pyvenv.cfg`:

```txt
home = /opt/homebrew/opt/python@3.13/bin
include-system-site-packages = false
version = 3.13.5
executable = /opt/homebrew/Cellar/python@3.13/3.13.5/Frameworks/Python.framework/Versions/3.13/bin/python3.13
command = /opt/homebrew/opt/python@3.13/bin/python3.13 -m venv /Users/melekderman/github/Summer25/3_MCDC-Electron/Apr5_ElectronTransport/MCDC/.venv
```

## Environment creation

From the repository root:

```bash
cd /Users/melekderman/github/Summer25/3_MCDC-Electron/Apr5_ElectronTransport/MCDC
/opt/homebrew/opt/python@3.13/bin/python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

The dependencies come from `pyproject.toml`, including:

- `numba>=0.60.0`
- `numpy>=2.0.0`
- `scipy`
- `matplotlib`
- `mpi4py>=3.1.4`
- `h5py`
- `colorama`
- `sympy`
- dev extras: `black`, `pre-commit`, `pytest`

## Installed package versions

The key package versions in this venv were:

```txt
Python 3.13.5
h5py==3.16.0
matplotlib==3.10.8
mpi4py==4.1.1
numba==0.65.0
numpy==2.4.4
pytest==9.0.2
scipy==1.17.1
sympy==1.14.0
```

The editable install currently reports:

```txt
-e git+https://github.com/melekderman/MCDC.git@85ff0eabf58ec7caf2a9d90b243c74330dad6416#egg=mcdc
```

## Activation and runtime environment

To activate the environment:

```bash
cd /Users/melekderman/github/Summer25/3_MCDC-Electron/Apr5_ElectronTransport/MCDC
source .venv/bin/activate
```

For this machine, the following runtime environment variables were useful:

```bash
export OMPI_MCA_btl=self
export MCDC_LIB=/Users/melekderman/github/Summer25/3_MCDC-Electron/Apr5_ElectronTransport/MCDC/test/regression/mcdc-regression_test_data
```

`OMPI_MCA_btl=self` was used to avoid OpenMPI transport warnings during import
and execution on this macOS setup.

## Quick verification

Basic import verification used during setup:

```bash
OMPI_MCA_btl=self .venv/bin/python -c "import mcdc, numba, h5py, mpi4py; print('ok')"
```

Example electron-data loader verification:

```bash
MCDC_LIB=/Users/melekderman/github/Summer25/3_MCDC-Electron/Apr5_ElectronTransport/MCDC/test/regression/mcdc-regression_test_data \
OMPI_MCA_btl=self \
.venv/bin/python -c "import mcdc; from mcdc.object_.element import Element; e = Element('Al'); e.set_electron_data(); print(e.atomic_number)"
```

