#!/bin/sh

# cached wheels + other elements can screw up the installation process.
# before i do this, i use 'checkmytemps' to look at all cache dirs 
# if there's wheels or other things... even empty dirs, i remove them
module load conda
conda create --clone python-3.9-20220720 --prefix=/nbhome/$USER/ians_epmt
conda activate /nbhome/$USER/ians_epmt

which pip

pip install /nbhome/epmt/epmt-4.10.0.tar.gz

return

### at the end of all of this, got the following complaints.
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
xarray 2023.2.0 requires pandas>=1.4, but you have pandas 1.3.5 which is incompatible.
sphinx 5.0.2 requires importlib-metadata>=4.4; python_version < "3.10", but you have importlib-metadata 0.23 which is incompatible.
nbclient 0.6.6 requires jupyter-client>=6.1.5, but you have jupyter-client 5.3.4 which is incompatible.
nbclient 0.6.6 requires nbformat>=5.0, but you have nbformat 4.4.0 which is incompatible.
nbclient 0.6.6 requires traitlets>=5.2.2, but you have traitlets 4.3.3 which is incompatible.
nbclassic 0.4.3 requires jupyter-client>=6.1.1, but you have jupyter-client 5.3.4 which is incompatible.
nbclassic 0.4.3 requires Send2Trash>=1.8.0, but you have send2trash 1.5.0 which is incompatible.
jupyterlab-server 2.15.0 requires importlib-metadata>=3.6; python_version < "3.10", but you have importlib-metadata 0.23 which is incompatible.
jupyterlab-server 2.15.0 requires jinja2>=3.0.3, but you have jinja2 2.10.3 which is incompatible.
jupyter-server 1.18.1 requires jupyter-client>=6.1.12, but you have jupyter-client 5.3.4 which is incompatible.
jupyter-server 1.18.1 requires jupyter-core>=4.7.0, but you have jupyter-core 4.6.1 which is incompatible.
jupyter-server 1.18.1 requires nbconvert>=6.4.4, but you have nbconvert 5.6.1 which is incompatible.
jupyter-server 1.18.1 requires nbformat>=5.2.0, but you have nbformat 4.4.0 which is incompatible.
jupyter-server 1.18.1 requires traitlets>=5.1, but you have traitlets 4.3.3 which is incompatible.
importlib-resources 5.8.0 requires zipp>=3.1.0; python_version < "3.10", but you have zipp 0.6.0 which is incompatible.
distributed 2022.7.0 requires tornado<6.2,>=6.0.3, but you have tornado 6.2 which is incompatible.
basemap 1.3.4 requires matplotlib<3.6,>=1.5; python_version >= "3.5", but you have matplotlib 3.6.3 which is incompatible.
aiohttp 3.8.1 requires charset-normalizer<3.0,>=2.0, but you have charset-normalizer 3.0.1 which is incompatible.
```
