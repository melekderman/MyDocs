# load_env.sh — Load ACEtk environment
# Usage: source load_env.sh  (DO NOT execute)

module load python/3.11.5
module load cmake/3.29.2

WORKDIR="/usr/workspace/derman1/ACEtk-tuo/2"

source "$WORKDIR/.venv-ace/bin/activate"

export PYTHONPATH="$WORKDIR/ACEtk/build/python:$PYTHONPATH"
export MCDC_LIB="$WORKDIR/mcdc_lib"
export MCDC_ACELIB="$WORKDIR/Lib81/Lib81/"

echo "ACEtk environment loaded (venv: $VIRTUAL_ENV)"
