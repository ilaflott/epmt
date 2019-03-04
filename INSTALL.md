# EPMT Installation Guide

## Starting the Database Daemons

If you do not have a postgres database daemon installed and running, it's easiest to use the provided dockerized services. 

Using the command line, we start both the database and the administrative interface:

```
$ docker-compose up adminer db
```

## Creating the Database.

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

```
$ docker-compose down adminer db
```

## Port Usage

* 8080 for DB admin interface
* 5432 for PostGresQL

## Persistant Storage

Persistent data and config present in the **./data** directory where the containers are started.