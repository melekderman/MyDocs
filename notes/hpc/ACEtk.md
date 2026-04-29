# ACEtk Installation on Tuo

## Modules

```bash
module load python/3.11.5
module load cmake/3.29.2
```

## Python venv
```bash
python -m venv ~/envs/eprdata_env
source ~/envs/eprdata_env/bin/activate
```

## Clone and build ACEtk
```bash
git clone git@github.com:njoy/ACEtk.git
cd ACEtk
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ../
make -j8
```

## Add python path - temp
```bash
export PYTHONPATH=$PYTHONPATH:~/ACE-work/ACEtk/build/python
```

## Or copy in into venv - permanent
```bash
cp ACEtk/build/python/ACEtk.cpython-311-x86_64-linux-gnu.so \
   ~/envs/eprdata_env/lib/python3.11/site-packages/
python -c "import ACEtk; print('OK')"
```

## Download eprdata
```bash
wget https://nucleardata.lanl.gov/lib/eprdata14.tgz
tar -xzf eprdata14.tgz
```
## Set your paths
```bash
module load python/3.11.5
source ~/envs/eprdata_env/bin/activate

export PYTHONPATH=$HOME/4-ACEtk/ACEtk/build/_deps/tools-build/python:$HOME/4-ACEtk/ACEtk/build/python:$PYTHONPATH
export MCDC_ACELIB=/nfs/stak/users/dermanm/4-ACEtk/epics
export MCDC_LIB=/nfs/stak/users/dermanm/4-ACEtk/mcdc-lib-e
```
