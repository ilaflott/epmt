#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE EPMT;
    CREATE USER epmt_rw PASSWORD 'Hb79xbwD';
    CREATE USER epmt_ro PASSWORD 'b33JFn2X';

    -- Do not allow create permissions by default
    REVOKE CREATE ON SCHEMA public FROM public;

    -- We can choose to create a separate EPMT admin account, distinct
    -- from the main database admin by uncommenting the block below:
    /*
    CREATE USER epmt_admin PASSWORD 'MhwTnx39F';
    ALTER DATABASE EPMT OWNER TO epmt_admin;
    GRANT ALL PRIVILEGES ON DATABASE EPMT TO epmt_admin;
    GRANT ALL ON SCHEMA public TO epmt_admin;
    GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO epmt_admin;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO epmt_admin;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES to epmt_admin;
    ALTER DEFAULT PRIVILEGES FOR ROLE epmt_admin GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO epmt_rw;
    ALTER DEFAULT PRIVILEGES FOR ROLE epmt_admin GRANT ALL ON SEQUENCES to epmt_rw;
    ALTER DEFAULT PRIVILEGES FOR ROLE epmt_admin GRANT SELECT ON TABLES TO epmt_ro;
    */

    -- EPMT R/W account. This can do everything except drop/create tables/database.
    -- This account can also do post-processing.
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO epmt_rw;
    GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO epmt_rw;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO epmt_rw;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES to epmt_rw;

    -- EPMT R/O account. Can do read-only querying. Cannot do post-processing
    GRANT CONNECT ON DATABASE EPMT TO epmt_ro;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO epmt_ro;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO epmt_ro;
EOSQL
