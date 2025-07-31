#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest
import sqlite3
import pandas as pd
import numpy as np
import logging
from io import StringIO
from epmt.epmtlib import epmt_logging_init, get_install_root

# import sqlite3
# import pandas as pd
# import numpy as np
# import logging

from epmt.epmtlib import dict_filter
from epmt.epmtlib import merge_intervals
from epmt.epmtlib import encode2ints, decode2strings
from epmt.epmtlib import dframe_encode_features, dframe_decode_features
from epmt.epmtlib import hash_strings
from epmt.epmtlib import get_install_root


# The class below tests library functions
class EPMTLib(unittest.TestCase):
    def test_sqlite_json_support(self):
        self.assertTrue(
            sqlite3.sqlite_version_info > (
                3,
                9),
            'SQLite version {0} is too old and does not have JSON1 extensions. You need version 3.9 or later (with JSON1 extensions enabled)'.format(
                sqlite3.sqlite_version))

    def test_dict_filter(self):
        d = {'abc': 10, 'def': 20, '_ghi': 30, 'LS_COLORS': 'xyz'}
        cloned_d = d.copy()
        pruned_d = dict_filter(d, ['LS_COLORS'])
        self.assertEqual(d, cloned_d)
        self.assertEqual(pruned_d, {'abc': 10, 'def': 20})
        pruned_d2 = dict_filter(d, ['LS_COLORS'], remove_underscores=False)
        self.assertEqual(pruned_d2, {'abc': 10, 'def': 20, '_ghi': 30})

    def test_merge_intervals(self):
        merged = merge_intervals(
            [[-25, -14], [-21, -16], [-20, -15], [-10, -7], [-8, -5], [-6, -3], [2, 4],
             [2, 3], [3, 6], [12, 15], [13, 18], [14, 17], [22, 27], [25, 30], [26, 29]])
        self.assertEqual(merged, [[-25, -14], [-10, -3], [2, 6], [12, 18], [22, 30]])

    def test_encode_decode(self):
        v = ['ABC', 'ABC', 'DEF', '', 'abcd']
        x = encode2ints(v)
        self.assertEqual(x, [4407873, 4407873, 4605252, 0, 1684234849])
        self.assertEqual(decode2strings(x), v)

    def test_encode_decode_dframe(self):
        df = pd.DataFrame([['hello', 1, 2, 'My Name'],
                           ['def', 2, 100, "Your Name"],
                           ['', 0, 45, "No name"]],
                          columns=['A', 'B', 'C', 'D'])
        (encdf, encf) = dframe_encode_features(df, reversible=True)
        self.assertEqual(set(encf), {'D', 'A'})
        self.assertFalse(encdf.equals(df))
        (decdf, decf) = dframe_decode_features(encdf, encf)
        self.assertEqual(set(decf), {'D', 'A'})
        self.assertTrue(decdf.equals(df))

    def test_hash_strings(self):
        int_vec = hash_strings(['ABC', 'ABC', "ABC", 'DEF'])
        self.assertTrue(int_vec[0] == int_vec[1] == int_vec[2])
        self.assertEqual(np.array(int_vec).dtype, np.dtype('int64'))

    def test_hash_strings_encode_dframe(self):
        _s = 'hello'
        df = pd.DataFrame([[_s, 1, 2, 'My Name'],
                           [_s, 2, 100, "Your Name"],
                           ['', 0, 45, "No name"]],
                          columns=['A', 'B', 'C', 'D'])
        (encdf, encf) = dframe_encode_features(df)
        self.assertEqual(set(encf), {'D', 'A'})
        self.assertFalse(encdf.equals(df))
        self.assertEqual(encdf['A'].dtype, np.dtype('int64'))
        self.assertEqual(encdf['D'].dtype, np.dtype('int64'))
        self.assertTrue(encdf['A'][0] == encdf['A'][1])

    def test_install_root(self):
        install_root = get_install_root()
        self.assertTrue(install_root)
        self.assertEqual(install_root + '/test', __file__.rsplit('/', 1)[0])

    # BROKEN FIX TODO
    def test_logfn(self):
        from epmt.epmtlib import logfn, epmt_logging_init, capture

        # enable debug logging and,
        # remove all handlers and add our StringIO handler
        epmt_logging_init(2)
        logger = logging.getLogger()

        @logfn
        def double(x):
            return x * 2

        # this removes the existing handlers
        for handler in logger.handlers:
            logger.removeHandler(handler)
        logger.handlers = []

        log_stream = StringIO()
        # print(log_stream)
        stream_handler = logging.StreamHandler(log_stream)
        # print(stream_handler)
        streamFormatter = logging.Formatter("%(levelname)7.7s: %(name)s: %(message)s")
        # print(streamFormatter)
        stream_handler.setFormatter(streamFormatter)
        logger.addHandler(stream_handler)

        # call our function
        y = double(25)

        # remove the StringIO handler
        logger.removeHandler(stream_handler)

        # restore logging to sanity
        epmt_logging_init(0)

        # grab the logging output and parse it for what we exepct
        s = log_stream.getvalue()
        self.assertEqual(y, 50)
        self.assertIn('DEBUG: epmt.test.test_lib: double(25)', s)
        # print(s)
        # print(s)
        # print(s)
        # print(s)


if __name__ == '__main__':
    unittest.main()
