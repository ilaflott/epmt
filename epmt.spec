# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from glob import glob
import os.path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
from IPython import extensions as IPython_extensions

hidden = collect_submodules('notebook',filter=lambda name: name.endswith('handlers') and ".tests." not in name)
uniq = set(hidden)
hidden = list(uniq)
# Without this, we get no tree view
hidden.append('notebook.tree')
# Whats a notebook without pandas
hidden.append('pandas')
# Required for IPython kernel
hidden.append('ipykernel.datapub')
# Required for migration migrations/versions/e703296695bf_create_processes_staging_table.py
hidden.append('orm.sqlalchemy.custom_types')
# Required for EPMT
hidden.append('sqlalchemy.ext.baked')
# pyod, pca
hidden.extend(['sklearn.neighbors._typedefs','sklearn.neighbors._quad_tree','sklearn.tree._utils','sklearn.utils', 'sklearn.utils._cython_blas', 'sklearn.utils.arrayfuncs', 'sklearn.utils.arrayfuncs.array'])

hidden.append('ui.components')
hidden.append('ui')

print("Hidden modules: ",hidden)

exclude = ['settings','matplotlib']
print("Excluded modules: ",exclude)

ipe_extra_datas = []
IPython_extensions_path = os.path.split(IPython_extensions.__file__)[0]
files = glob(os.path.join(IPython_extensions_path,"*.py"))
for f in files:
    fn = "IPython/extensions/" + os.path.basename(f)
    ipe_extra_datas.append((f, '.'))

alembic_extras = []
alembic_migration_files = glob(os.path.join('migrations/versions', "*.py")) + glob(os.path.join('migrations', "*.py")) 
for f in alembic_migration_files:
    alembic_extras.append((f, '.'))

# Move web components into root
dash_resources = []
files = glob('ui/components/*.py')
for f in files:
    dash_resources.append((f, '.'))

# Move Web assets into subdirectory
files = glob('ui/assets/*')
for f in files:
    dash_resources.append((f, './assets/'))

dash_extra_datas = collect_data_files('dash_html_components') + collect_data_files('dash_core_components') + collect_data_files('dash_daq') + collect_data_files('dash_table') + collect_data_files('dash_renderer') + collect_data_files('dash_bootstrap_components')
plotly_extra_datas = collect_data_files('plotly.graph_objects') + collect_data_files('plotly.express') + collect_data_files('plotly.figure_factory')

extra_datas = ipe_extra_datas + dash_extra_datas + alembic_extras + dash_resources + plotly_extra_datas

print("Extra data: ",extra_datas)

# see we add the ui directory to 
a = Analysis(['epmt','ui/index.py'],
             pathex=['./ui'],
             binaries=[],
             datas=extra_datas,
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
