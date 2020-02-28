Version 3.3.20
==============

  Release date: 02/28/2020

  The list below includes features added since version 2.2.7.

  - 7x to 10x speedup in ingestion performance for SQLAlchemy
    (tested against SQLite and PostgreSQL backends)
  - Principal Component Analysis (PCA) support added for outlier detection
  - Multivariate Outlier Detection (MVOD) support added (pyod classifiers
    are supported at present)
  - 100x improvement in delete performance with PostgreSQL
  - `epmt explore` command-line support to enable GFDL-specific
    explorations into experiments
  - `epmt retire` supports period job deletion based on policies
  - `epmt annotate` supports appending metrics to a job archive or in the DB
  - built-ins such as `help` added to `epmt shell`
  - `epmt python` can run arbitrary python scripts
  - `epmt dump` now shows job archives and details of jobs in the database
