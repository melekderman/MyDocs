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

## Download eprdata
```bash
wget https://nucleardata.lanl.gov/lib/eprdata14.tgz
tar -xzf eprdata14.tgz
```
