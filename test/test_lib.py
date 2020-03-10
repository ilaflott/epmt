#!/usr/bin/env python

# the import below is crucial to get a sane test environment
# from . import *
import unittest


# The class below tests library functions
class EPMTLib(unittest.TestCase):
    def test_sqlite_json_support(self):
        import sqlite3
        self.assertTrue(sqlite3.sqlite_version_info > (3,9), 'SQLite version {0} is too old and does not have JSON1 extensions. You need version 3.9 or later (with JSON1 extensions enabled)'.format(sqlite3.sqlite_version))

    def test_dict_filter(self):
        from epmtlib import dict_filter
        d = { 'abc': 10, 'def': 20, '_ghi': 30, 'LS_COLORS': 'xyz'}
        cloned_d = d.copy()
        pruned_d = dict_filter(d, ['LS_COLORS'])
        self.assertEqual(d, cloned_d) 
        self.assertEqual(pruned_d, { 'abc': 10, 'def': 20 })
        pruned_d2 = dict_filter(d, ['LS_COLORS'], remove_underscores = False)
        self.assertEqual(pruned_d2, { 'abc': 10, 'def': 20, '_ghi': 30 })

    def test_url_to_db_params(self):
        from orm.pony.general import _url2params
        url = 'postgresql://postgres:example@localhost:5432/EPMT'
        db_params = _url2params(url)
        self.assertEqual(db_params, {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'localhost', 'port': 5432, 'dbname': 'EPMT'})
        url = 'sqlite:///:memory:'
        db_params = _url2params(url)
        self.assertEqual(db_params, { 'provider': 'sqlite', 'filename': ':memory:', 'create_db': True })

    def test_merge_intervals(self):
        from epmtlib import merge_intervals
        merged = merge_intervals([[-25, -14], [-21, -16], [-20, -15], [-10, -7], [-8, -5], [-6, -3], [2, 4], [2, 3], [3, 6], [12, 15], [13, 18], [14, 17], [22, 27], [25, 30], [26, 29]])
        self.assertEqual(merged, [[-25, -14], [-10, -3], [2, 6], [12, 18], [22, 30]])

    def test_encode_strings(self):
        v = ['ABC', 'ABC', 'DEF', '', 'abcd']
        from epmtlib import encode2ints, decode2strings
        x = encode2ints(v)
        self.assertEqual(x, [4407873, 4407873, 4605252, 0, 1684234849])
        self.assertEqual(decode2strings(x), v)


if __name__ == '__main__':
    unittest.main()
