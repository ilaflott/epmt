# EPMT Installation Guide

## Requirements

First download the most recent source tree.

```
$ git clone https://<user>@bitbucket.org/minimalmetrics/epmt.git
$ cd epmt
```

The following python packages are needed to run **EPMT**. It is recommended that one use the Docker image which contains all the dependencies and **requires no user setup**.

However, one may install these in a Python virtual environment, as part of the system Python or one's own local Python repository, using **pip install**. 

- pandas
- pony
- psycopg2-binary

```
$ pip install --user -r requirements.txt
```

## Building the Docker Images

This guide assumes one is using Docker and Docker Composer for deployment. 

First we build the various **EPMT** images:

```
$ make
.
.
$ docker images
REPOSITORY               TAG                 IMAGE ID            CREATED              SIZE
epmt-notebook            latest              045023fc0ccc        About a minute ago   4.3GB
epmt-command             latest              530fe3198a1d        About a minute ago   1.1GB
python-epmt              latest              5b99ede4828d        About a minute ago   1.1GB
```

## Start the Database

If you do not have a postgres database daemon installed and running, it's easiest to use the provided dockerized services. 

Using the command line, we start both the database and the administrative interface:

```
$ docker-compose up adminer db
```

## Create the Database

If you are not using the sqlite database for testing, you need to create the **EPMT** database before proceeding.

Use the **Adminer** console:

```
$ firefox http://localhost:8080/?pgsql=db&username=postgres&database=
```

Or using the command line:

```
$ sudo su - postgres
$ psql -c "create database EPMT"
```

## Safe Shutdown Of Daemons

To shut down everything:
```
$ docker-compose down 
```

To only shut down a service, like the database:
```
$ docker-compose stop db
```

## Testing Python Versions under Docker

One can test **EPMT** on various versions of python with the following make commands. Each will test against a minimal install of Python, without installing any dependencies. This should work for **start, stop, dump, help and submit, the latter with -n or --dry-run**. 

```
make check-python-native
make check-python-2.6
make check-python-2.7
make check-python-3
```

## Port Usage

* 8888 for Jupyter/iPython Notebook
* 8080 for DB admin interface
* 5432 for PostGresQL

## Persistant Storage

Persistent data and config present in the **./data** directory where the containers are started.