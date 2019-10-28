#!/usr/bin/env python

# the import below is crucial to get a sane test environment
# from . import *
import unittest


# The class below tests library functions
class EPMTLib(unittest.TestCase):

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


if __name__ == '__main__':
    unittest.main()
