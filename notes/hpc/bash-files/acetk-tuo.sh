#!/bin/bash
# Setup ACEtk and download EPRDATA14

# =============================================================================
# User configuration for Tuolumne
# =============================================================================

PYTHON_BIN="/usr/tce/packages/python/python-3.11.5/bin"
CMAKE_BIN="/usr/tce/packages/cmake/cmake-3.29.2/bin"
VENV_DIR="$(pwd)/venv"
PYTHON_VERSION="3.11"
N_CORES=8
# =============================================================================
 
# Add tools to PATH
export PATH="$CMAKE_BIN:$PYTHON_BIN:$PATH"

# Python venv
python -m venv $VENV_DIR
source $VENV_DIR/bin/activate
 
# Clone and build ACEtk
git clone git@github.com:njoy/ACEtk.git
cd ACEtk
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ../
make -j$N_CORES
cd ../..
 
# Copy .so into venv
SO_FILE="ACEtk/build/python/ACEtk.cpython-$(echo $PYTHON_VERSION | tr -d '.')-x86_64-linux-gnu.so"
cp $SO_FILE $VENV_DIR/lib/python$PYTHON_VERSION/site-packages/
python -c "import ACEtk; print('ACEtk OK')"
 
# Download EPRDATA14
wget https://nucleardata.lanl.gov/lib/eprdata14.tgz
tar -xzf eprdata14.tgz
