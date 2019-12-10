# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from glob import glob
import os.path
from PyInstaller.utils.hooks import collect_submodules
from IPython import extensions as IPython_extensions

hidden = collect_submodules('notebook',filter=lambda name: name.endswith('handlers') and ".tests." not in name)
uniq = set(hidden)
hidden = list(uniq)
# Without this, we get no tree view
hidden.append('notebook.tree')
# Whats a notebook without pandas
hidden.append('pandas')
# Add default plotting engine
hidden.append('matplotlib')
# Required for IPython kernel
hidden.append('ipykernel.datapub')
# Required for EPMT
hidden.append('sqlalchemy.ext.baked')
print("Hidden modules: ",hidden)

exclude = ['settings']
print("Excluded modules: ",exclude)

ipe_extra_datas = []
IPython_extensions_path = os.path.split(IPython_extensions.__file__)[0]
files = glob(os.path.join(IPython_extensions_path,"*.py"))
for f in files:
    fn = "IPython/extensions/" + os.path.basename(f)
    ipe_extra_datas.append((f, '.'))
print("Extra data: ",ipe_extra_datas)


a = Analysis(['epmt'],
             pathex=['/Users/philipmucci/Work/epmt.git'],
             binaries=[],
             datas=ipe_extra_datas,
             hiddenimports=hidden,
             hookspath=[],
             runtime_hooks=[],
             excludes=exclude,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='epmt',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='epmt')
