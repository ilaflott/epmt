
Version 4.5.2
=============

  Release date: 06/19/2020

  The list includes features and fixes since version 3.7.22.

  - Significant speed up in job submission rates for SQLAlchemy
    under PostgreSQL (20x and higher depending on hw/sw)
    - Direct-copy ingestion of CSV using PostgreSQL COPY
    - Staging of process data into a separate table for faster ingestion
    - Seamless post-processing of staged data on first-use
    - Speed-up in job collation by using `O_APPEND` in papiex
  - EPMT supports unit and integration tests from the CLI
  - EPMT CLI supports conversion of old CSV to faster TSV format
  - Multi-method scoring for outlier detection is now the default
  - Fixes and enhancements to the Query, Outlier detection and Statistics API
  - Outlier detection for processes and threads


Version 3.7.22
==============

  Release date: 04/22/2020

  The list includes features added since version 3.3.20.

  - Support for automatic database migration under SQLAlchemy added
  - `epmt help api` and `epmt help api <function>` provide
    concise list of API index and function docstrings
  - Improved API docstrings
  - API support to find jobs based on experiment name, components,
    times and exit status
  - API support to find missing time-segments in an experiment
  - Revamp of the outliers notebook with the latest data
  - Daemon mode now supports ingestion and retire functions
  - `epmt submit` now supports `--remove` to delete on successful submits
  - bug fixes
    - papiex memory/cache consistency issues resolved
    - fixes to support for `PAPIEX_TAGS`
    - resolved race in submit which could cause jobs to remain unprocessed
  - epmt annotate supports special handling for `EPMT_JOB_TAGS`
  - Additional univariate classifiers added
  - API improvements for PCA-based feature ranking
  - Improved handling of staging and concatenation errors
  - Improvements to the GUI

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
