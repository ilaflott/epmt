# settings.py
#db_params = {'provider': 'sqlite', 'filename': ':memory:'}
db_params = {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'db', 'dbname': 'EPMT'}
#db.bind(provider='postgres', user='postgres', password='example', host='0.0.0.0', dbname='EPMT')
# number of columns until caliper
metrics_offset = 12
debug = False
input_pattern = "papiex-[0-9]*-[0-9]*.csv"

