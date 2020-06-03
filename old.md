## EPMT under Docker 

Using the epmt-command docker image, we run **epmt** on a local directory to submit and set the submission DB host environment variable:

```
$ docker run --network=host -ti --rm -v `pwd`:/app -w /app -e EPMT_DB_HOST=<hostname> epmt-command:latest -v submit <localdir/>
```

This could be easily aliased for convenience.

## Analysis of EPMT Data 

Current analytics are performed in an iPython notebook, specifically the SciPy-Notebook as described on [their homepage](https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html).  

If you have Jupyter installed locally **and** you have installed the prerequisite Python modules (see **INSTALL.md**), there is no need to use the Docker image. You can simply load the **EPMT.ipynb** from the source directory in your environment and begin.

However, for those without an environment, using Docker (and assuming you build the images as described in **INSTALL.md**):

```
$ docker-compose up notebook
```

Follow the instructions printed to the screen to navigate to **EPMT.ipynb** or try this link [http://localhost:8888/notebooks/EPMT.ipynb]() and enter the encryption key. You must be in the directory where EPMT.ipynb exists when you start the notebook service. Further documentation exists in that file.