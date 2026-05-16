#!/bin/bash
# setup_acetk.sh — One-time installer for ACEtk + Lib81
# Usage: bash setup_acetk.sh

set -e  # exit on any error

module load python/3.11.5
module load cmake/3.29.2

WORKDIR="/usr/workspace/derman1/ACEtk-tuo/2"
VENV_DIR="$WORKDIR/.venv-ace"
ACETK_DIR="$WORKDIR/ACEtk"
LIB_DIR="$WORKDIR/Lib81"
LIB_URL="https://nucleardata.lanl.gov/lib/Lib81.tgz"

mkdir -p "$WORKDIR"
cd "$WORKDIR"

# ---- Venv ----
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "[1/3] Venv already exists, skipping."
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

# ---- ACEtk ----
if [ ! -d "$ACETK_DIR" ]; then
    echo "[2/3] Cloning ACEtk..."
    cd "$WORKDIR"
    git clone https://github.com/njoy/ACEtk.git
else
    echo "[2/3] ACEtk already cloned, pulling latest..."
    cd "$ACETK_DIR"
    git pull
fi

# Build (only if build/ missing or python binding missing)
if [ ! -f "$ACETK_DIR/build/python/ACEtk.so" ] && \
   [ ! -f "$ACETK_DIR/build/python/ACEtk"*.so ]; then
    echo "       Building ACEtk..."
    mkdir -p "$ACETK_DIR/build"
    cd "$ACETK_DIR/build"
    cmake -DCMAKE_BUILD_TYPE=Release ../
    make -j8
else
    echo "       ACEtk build already exists, skipping. (Delete build/ to rebuild.)"
fi

# ---- Lib81 ----
if [ ! -d "$LIB_DIR" ]; then
    echo "[3/3] Downloading Lib81..."
    cd "$WORKDIR"
    wget "$LIB_URL"
    tar -xzf Lib81.tgz
    rm Lib81.tgz
    echo "       Lib81 extracted."
else
    echo "[3/3] Lib81 already present, skipping."
fi

echo ""
echo "Setup complete. Load the environment with:"
echo "  source $WORKDIR/load_venv-tuo.sh"
