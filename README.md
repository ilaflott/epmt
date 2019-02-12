# EPMT

## How to Run

```docker-compose up adminer db```

## Before importing data, create the EPMT database. 

From the Adminer Console:

http://localhost:8080/?pgsql=db&username=postgres&database=

Or using the command line:

```sudo su - postgres``` to become postgres

```psql -c "create database EPMT"```

## How to Shutdown

```docker-compose down adminer db```

## Usage

* Browse to 5000 for App interface
* Browse to 8080 for DB admin interface
* Browse to 3000 for Grafana interface
* Connect to 5432 for PostGresQL

## Persistant Storage

Persistent data and config present in the ./data. 

