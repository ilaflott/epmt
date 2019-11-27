You should have been provided links to two `.tgz` files:

 - epmt-x.y.z.tgz       # main tar containing EPMT release
 - test-epmt-x.y.z.tgz  # only needed for testing

Put these both in a folder and follow the commands below.

```
$ tar xvf epmt-x.y.z.tgz
$ cd epmt-install/epmt
$ cp ../preset_settings/settings_sqlite_inmem_sqlalchemy.py settings.py
$ ./epmt -V
EPMT 2.1.0


# unit testing (optional)
$ cd epmt-install/epmt
$ tar --strip-components=1 -xzvf ../../test-epmt-2.1.0.tgz 
$ ./epmt unittest
...

# run integration tests (optional)
# make sure you have untarred the test-epmt as shown above
$ test/integration/run_integration 
 ✓ epmt version
 ✓ epmt submit
 - epmt_concat -h (skipped)
 - epmt_concat with valid input dir (skipped)
 - epmt_concat with valid input files (skipped)
 - epmt_concat with non-existent directory (skipped)
 - epmt_concat with non-existent files (skipped)
 - epmt_concat with corrupted csv (skipped)
 ✓ no daemon running
 ✓ start epmt daemon
 ✓ stop epmt daemon

11 tests, 0 failures, 6 skipped

```
