"""
EPMT settings module - user configuration settings.
"""
def test_settings_import():
    pass

# Configure for integration tests with persistent SQLite database in /tmp
import tempfile
import os

# Create a unique temporary database file for this test session
temp_dir = tempfile.gettempdir()
db_path = os.path.join(temp_dir, f"epmt_test_{os.getpid()}.db")

orm = 'sqlalchemy'
db_params = {'url': f'sqlite:///{db_path}', 'echo': False}
bulk_insert = True

epmt_settings_kind = 'integration_test'
