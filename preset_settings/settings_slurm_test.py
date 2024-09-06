def test_settings_import():
    print('settings.py imported!')

orm = 'sqlalchemy'
db_params = { 'url': 'sqlite:///:memory:', 'echo': False }
bulk_insert = True
epmt_output_prefix = "/tmp/epmt/"
install_prefix = "/opt/epmt/papiex-epmt-install/"
