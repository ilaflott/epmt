from setuptools import setup

setup(name="epmt",
      version="4.11.0",
      url="https://some.where",
      author_email="some@where.com",
      packages=['epmt', 'epmt.orm', 'epmt.orm.sqlalchemy', 'epmt.test'],
      package_data={'epmt':
                    ['alembic.ini',
                     'preset_settings/*.py',

                     'epmt_migrations/README',
                     'epmt_migrations/env.py',
                     'epmt_migrations/script.py.mako',
                     'epmt_migrations/docker-entrypoint-initdb.d/init-user-db.sh',
                     'epmt_migrations/versions/*',

                             'test/run',
                             'test/test_run.sh',
                             'test/test_source.csh',

                             'test/data/corrupted_csv/*',
                             'test/data/csv/*',
                             'test/data/daemon/627919.tgz',
                             'test/data/daemon/ingest/*',
                             'test/data/misc/*',
                             'test/data/outliers/*',
                             'test/data/outliers_nb/*',
                             'test/data/query/*',
                             'test/data/query_notebook/*',
                             'test/data/submit/692500.tgz',
                             'test/data/submit/804268.tgz',
                             'test/data/submit/804280.tgz',
                             'test/data/submit/3455/*',
                             'test/data/tsv/collated-tsv-2220.tgz',
                             'test/data/tsv/12340/*',

                             'test/integration/*.bats',
                             'test/integration/epmt-annotate.sh',
                     
                             'test/integration/libs/bats/CONDUCT.md',
                             'test/integration/libs/bats/LICENSE',
                             'test/integration/libs/bats/README.md',
                             'test/integration/libs/bats/install.sh',
                             'test/integration/libs/bats/package.json',
                     
                             'test/integration/libs/bats/bin/bats',
                             'test/integration/libs/bats/libexec/bats',
                             'test/integration/libs/bats/libexec/bats-exec-suite',
                             'test/integration/libs/bats/libexec/bats-exec-test',
                             'test/integration/libs/bats/libexec/bats-format-tap-stream',
                             'test/integration/libs/bats/libexec/bats-preprocess',

                             'test/integration/libs/bats/man/*',
                             'test/integration/libs/bats/test/bats.bats',
                             'test/integration/libs/bats/test/suite.bats',
                             'test/integration/libs/bats/test/test_helper.bash',

                             'test/integration/libs/bats/test/fixtures/bats/*',
                             'test/integration/libs/bats/test/fixtures/suite/empty/*',
                             'test/integration/libs/bats/test/fixtures/suite/multiple/*',
                             'test/integration/libs/bats/test/fixtures/suite/single/*',

                             'test/integration/libs/bats-assert/CHANGELOG.md',
                             'test/integration/libs/bats-assert/LICENSE',
                             'test/integration/libs/bats-assert/README.md',
                             'test/integration/libs/bats-assert/load.bash',
                             'test/integration/libs/bats-assert/package.json',

                             'test/integration/libs/bats-assert/script/*',
                             'test/integration/libs/bats-assert/src/*',
                             'test/integration/libs/bats-assert/test/*',

                             'test/integration/libs/bats-support/CHANGELOG.md',
                             'test/integration/libs/bats-support/LICENSE',
                             'test/integration/libs/bats-support/README.md',
                             'test/integration/libs/bats-support/load.bash',
                             'test/integration/libs/bats-support/package.json',

                             'test/integration/libs/bats-support/script/*',
                             'test/integration/libs/bats-support/src/*',
                             'test/integration/libs/bats-support/test/*',

                             'test/shell/*',
                      ]
                    },

##copying papiex-epmt-install/lib/libmonitor.so -> epmt-4.11.0/papiex-epmt-install/lib
##copying papiex-epmt-install/lib/libmonitor.so.0 -> epmt-4.11.0/papiex-epmt-install/lib
##copying papiex-epmt-install/lib/libmonitor.so.0.0.0 -> epmt-4.11.0/papiex-epmt-install/lib
##copying papiex-epmt-install/lib/libpapiex.so -> epmt-4.11.0/papiex-epmt-install/lib
##copying papiex-epmt-install/lib/libpapiex.so.2 -> epmt-4.11.0/papiex-epmt-install/lib
      
      data_files=[('lib/python3.9/site-packages/epmt/lib',
                   [
#                    'papiex-epmt-install/lib/libmonitor_wrap.a',
                    'papiex-epmt-install/lib/libmonitor.so',
                    'papiex-epmt-install/lib/libmonitor.so.0',                         
                    'papiex-epmt-install/lib/libmonitor.so.0.0.0',
#                    'papiex-epmt-install/lib/libpapi.a',
#                    'papiex-epmt-install/lib/libpapi.so',
#                    'papiex-epmt-install/lib/libpapi.so.5',                    
#                    'papiex-epmt-install/lib/libpapi.so.5.7.0',
#                    'papiex-epmt-install/lib/libpapi.so.5.7.0.0',                    
#                    'papiex-epmt-install/lib/libpfm.a',
#                    'papiex-epmt-install/lib/libpfm.so',
#                    'papiex-epmt-install/lib/libpfm.so.4',
#                    'papiex-epmt-install/lib/libpfm.so.4.10.1',
                    'papiex-epmt-install/lib/libpapiex.so',
                    'papiex-epmt-install/lib/libpapiex.so.2',                    
#                    'papiex-epmt-install/lib/libpapiex.so.2.3.14',


                     ] ),
                  ('lib/python3.9/site-packages/epmt/bin',
                    ['papiex-epmt-install/bin/check_events',
                     'papiex-epmt-install/bin/monitor-link',
                     'papiex-epmt-install/bin/monitor-run',
                     'papiex-epmt-install/bin/papi_avail',
                     'papiex-epmt-install/bin/papi_command_line',
                     'papiex-epmt-install/bin/papi_component_avail',
                     'papiex-epmt-install/bin/papi_native_avail',
                     'papiex-epmt-install/bin/showevtinfo',
                             ]) ],
      scripts=['scripts/epmt'],
      )
