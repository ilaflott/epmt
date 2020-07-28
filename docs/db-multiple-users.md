EPMT can work with multiple DB accounts with varying privilege levels.

Single-account permissions
--------------------------
 Here a single DB account is used and all operations use the same
singular DB account. In such a case, you can set the `db_params:url` parameter
in `settings.py` to the singular account and password. 

Multiple accounts
-----------------
EPMT supports an environment variable `EPMT_DB_URL`, which can be
set to a valid postgres URI of the form:

`postgresql://postgres:example@localhost:5432/EPMT`

When EPMT finds `EPMT_DB_URL` set in the environment, it will use
that URI to connect to the database, and ignore the `db_params:url`
parameter in `settings.py`.


Please view `migrations/docker-entrypoint-initdb.d/init-user-db.sh`

It is configured with 3 different accounts:

1. postgres database admin account (DB ADMIN): 
This account is of the owner of the EPMT database. This account can do 
all operations including creating and deleting tables. When EPMT is 
first-installed or after a new drop, it is recommended you run the following.

```
$ EPMT_DB_URL=postgresql://<admin-user>:<admin-passwd>@postgres-host:5432/EPMT epmt -v migrate
```

This will create the necessary tables and apply migrations. It is necessary
to apply migrations using the admin account as shown above.

If you inspect `migrations/docker-entrypoint-initdb.d/init-user-db.sh`, you will
spot a commented-out section that sets up an `epmt-admin` role. This is optional
and only needed if you want to not use the main database admin account, and have
a separate admin account for EPMT. If you decide to uncomment the `epmt-admin`
section, then you should use those credentials in the command above.


2. A read-write user account:
This account can do everything the admin account can do, except create/delete
tables. It cannot apply database migrations either. You can use this account
for all other EPMT tasks, such as ingestion, querying and deleting jobs, 
post-processing, etc. This account is named as `epmt-rw` in the 
`migrations/docker-entrypoint-initdb.d/init-user-db.sh` script.

3. A read-only user account:
This account provides read-only access to the EPMT database, and as such 
can be used for querying and outlier detection. It cannot modify the database
in anyway. It cannot perform post-processing either, since that requires
database writes. When performing queries on unprocessed jobs, R/O user accounts
will see certain fields such as `proc_sums` (in the job model) empty as
post-processing is required to populate such fields.

This account is named `epmt-ro` in the 
`migrations/docker-entrypoint-initdb.d/init-user-db.sh` script.

It is recommended that you edit `settings.py` and set `db_params:url` to
the DB URI for the R/O account. All other account credentials for R/W
and admin user can be configured by setting `EPMT_DB_URL` from the environment
when such privilege is needed.

Configuring a docker postgres image with multiple user accounts
===============================================================

1. Edit `migrations/docker-entrypoint-initdb.d/init-user-db.sh` to suit
your needs. You should only need to modify the passwords for `epmt-rw`
and `epmt-ro`. 

2. Now edit `settings.py` and set the `db_params:url` parameter to the
postgres URI for the read-only user. This will ensure the default
permissions give read-only DB access.


3. Now run postgres container. The script `init-user-db.sh` needs to
be bind-mounted under `/docker-entrypoint-initdb.d/init-user-db.sh`. And,
postgres will *only execute the script if the database is empty* and it's
running for the first time. If not, you will need to run the script commands
using a `psql` client.

A sample docker invocation is:

```
$ docker run --rm --name postgres -v $PWD/migrations/docker-entrypoint-initdb.d:/docker-entrypoint-initdb.d -v /path/to/data/dir:/var/lib/postgresql/data -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT -p 5432:5432   postgres:latest
```

Here the admin user is `postgres` and has a password `example`.

To first apply migrations as the admin user, you would do:
```
EPMT_DB_URL=postgresql://postgres:example@localhost:5432/EPMT epmt -v migrate
```

Then you can submit a job using the R/W user as follows:
```
EPMT_DB_URL=postgresql://epmt-rw:<password>@localhost:5432/EPMT epmt -v submit xyz.tgz
```

Finally, an epmt command executed without `EPMT_DB_URL` will use the
credentials in `settings.py` and default to the read-only user.
