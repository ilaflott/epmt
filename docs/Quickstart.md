You should have been provided links to two `.tgz` files:

 - epmt-x.y.z.tgz       # main tar containing EPMT release
 - test-epmt-x.y.z.tgz  # only needed for testing

Put these both in a folder and follow the commands below.

```
$ tar xvf epmt-x.y.z.tgz
$ cd epmt-install/epmt
$ cp ../preset_settings/settings_sqlite_inmem_sqlalchemy.py settings.py
$ ./epmt -V
2.1.0


# optional testing
$ cd epmt-install/epmt
$ tar --strip-components=1 -xzvf ../../test-epmt-2.1.0.tgz 
$ ./epmt unittest
```
