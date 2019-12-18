This Dash interface currently works with EPMT using Pony and sqlite.  

The sqlite file is in this Dash Directory and symbolicly linked inside

the epmt directory.

For example if you use EPMT_DB_PONY.sqlite in the EPMT directory.

epmt$ mv EPMT_DB_PONY.sqlite dash/

epmt$ ln -s dash/EPMT_DB_PONY.sqlite EPMT_DB_PONY.sqlite


├── EPMT

│   ├── Dash

│   │   ├── EPMT_DB_PONY.sqlite

│   │   ├── app.py

│   │   ├── index.py

│   │   ├── layout.py

│   │   ├── callbacks.py

│   │   └── ...

│   ├── EPMT_DB_PONY.sqlite (Symlink to dash/EPMT_DB_PONY.sqlite)

│   ├── epmt

│   └── ...

Make and run the dash interface.

make build && make run

Visit:
    http://localhost:8050

Make build uses the Dockerfiles/Dockerfile.epmt-interface to build the container

The container is tagged with epmt-interface:latest

Make Run mounts container port 8050 to local 8050

Mounts volume parent directory (EPMT) to container /home

Mounds volume current directory (Dash) to container /home/dash

