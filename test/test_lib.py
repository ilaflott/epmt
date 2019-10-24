#!/usr/bin/env python

# the import below is crucial to get a sane test environment
# from . import *
import unittest

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


if __name__ == '__main__':
    unittest.main()
