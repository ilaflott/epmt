#!/usr/bin/env python3

# the import below is crucial to get a sane test environment
# from . import *
import unittest
import numpy as np
import pandas as pd


class EPMTStat(unittest.TestCase):

    def test_outliers_iqr(self):
        from epmt.epmt_stat import outliers_iqr, iqr
        vec = [100, 100, 100, 45, 100]
        r = outliers_iqr(vec)
        self.assertEqual(list(r), [0, 0, 0, 1, 0])
        # now let's do a more involved test
        vec = [1, 2, 3, 4, 3, 2, 1, 10]
        (outliers, discard, q1, q3) = iqr(vec)
        self.assertEqual(list(outliers), [0, 0, 0, 0, 0, 0, 0, 1])
        self.assertEqual((discard, q1, q3), (0, 4.375, 6.625))
        # q1 and q3 are such that if provided as arguments
        # to another call of iqr with the same input
        # will *just* fit the vector and find no outliers
        (outliers_r, _, q1_r, q3_r) = iqr(vec, (discard, q1, q3))
        self.assertEqual(list(outliers_r), [0] * 8)
        self.assertEqual((q1_r, q3_r), (q1, q3))

    def test_outliers_iqr_strings(self):
        import epmt.epmtlib as el
        from epmt.epmt_stat import outliers_iqr
        int_vec = el.hash_strings(['ABC', 'ABC', "ABC", 'DEF'])
        r = outliers_iqr(int_vec)
        self.assertEqual(list(r), [0, 0, 0, 1])

    def test_outliers_uv(self):
        from epmt.epmt_stat import outliers_uv
        r = outliers_uv([1, 2, 1, 1, 1, 1, 2, 1, 0, 2, 100, 100])
        self.assertEqual(list(r), [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2])
        r = outliers_uv([1, 2, 1, 1, 1, 1, 2, 1, 0, 2, 100])
        self.assertEqual(list(r), [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3])

    def test_z_score(self):
        import epmt.epmt_stat as es
        (scores, max_score, mean_y, stdev_y) = es.z_score([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1000])
        self.assertEqual(list(scores), [0.332, 0.3285, 0.325, 0.3215, 0.318,
                         0.3145, 0.311, 0.3075, 0.304, 0.3005, 3.1621])
        self.assertEqual((max_score, mean_y, stdev_y), (3.1621, 95.9091, 285.9118))

    def test_check_dist(self):
        from epmt.epmt_stat import check_dist
        np.random.seed(1)
        (passed, failed) = check_dist(range(100), 'norm')
        self.assertTrue(failed > passed)
        (passed, failed) = check_dist(range(100), 'uniform')
        self.assertTrue(passed > failed)
        (passed, failed) = check_dist(np.linspace(-15, 15, 100), 'norm')
        self.assertTrue(failed > passed)
        (passed, failed) = check_dist(np.linspace(-15, 15, 100), 'uniform')
        self.assertTrue(passed > failed)
        (passed, failed) = check_dist(np.random.randn(100), 'norm')
        self.assertTrue(passed > failed)
        (passed, failed) = check_dist(np.random.randn(100), 'uniform')
        self.assertTrue(failed > passed)

    def test_normalize(self):
        from epmt.epmt_stat import normalize
        x = np.array([[0.0, 10.0], [0.13216, 12.11837], [0.25379, 42.05027], [0.30874, 13.11784]])
        norm_x = normalize(x)
        self.assertIsNone(np.testing.assert_almost_equal(norm_x, np.array(
            [[0., 0.], [0.42806245, 0.06609523], [0.82201853, 1.], [1., 0.09727968]])))

    def test_dframe_append_weighted_row(self):
        from epmt.epmt_stat import dframe_append_weighted_row
        df = pd.DataFrame([[1, 2, 2], [2, 3, 4]], columns=['A', 'B', 'C'])
        x1 = dframe_append_weighted_row(df, [1.5, 0.1])
        self.assertEquals(x1.shape, (3, 3))
        self.assertTrue(x1.iloc[0].astype('int64').equals(df.iloc[0]))
        self.assertTrue(x1.iloc[1].astype('int64').equals(df.iloc[1]))
        self.assertEqual(list(x1.iloc[-1].values), [1.7, 3.3, 3.4])
        x2 = dframe_append_weighted_row(df, [1, 0])
        self.assertTrue(x2.iloc[0].equals(df.iloc[0]))
        self.assertTrue(x2.iloc[1].equals(df.iloc[1]))
        self.assertTrue(x2.iloc[-1].equals(df.iloc[0]))

    def test_modes(self):
        from epmt.epmt_stat import get_modes
        N = 100
        np.random.seed(1)
        # unimodal (normal)
        X = np.random.normal(0, 1, N)
        modes = get_modes(X)
        self.assertEqual(len(modes), 1)
        self.assertEqual(sorted(list(modes.round(0))), [0])
        # bimodal
        X = np.concatenate((np.random.normal(0, 1, int(0.3 * N)), np.random.normal(5, 1, int(0.7 * N))))
        modes = get_modes(X)
        self.assertEqual(len(modes), 2)
        self.assertEqual(sorted(list(modes.round(0))), [0, 5])
        # trimodal
        X = np.concatenate((np.random.normal(0, 1, int(0.3 * N)), np.random.normal(5,
                           1, int(0.3 * N)), np.random.normal(10, 1, int(0.4 * N))))
        modes = get_modes(X)
        self.assertEqual(len(modes), 3)
        self.assertEqual(sorted(list(modes.round(0))), [0, 5, 10])

    def test_dict_outliers(self):
        from epmt.epmt_stat import dict_outliers
        dlist = [{'a': 100, 'b': 200}, {'a': 101, 'b': 201}, {'a': 100, 'b': 200}, {'a': 200, 'b': 300}]
        outl, outl_by_key = dict_outliers(dlist, threshold=1.0)
        self.assertEqual(outl, {3})
        self.assertEqual(outl_by_key, {'a': [3], 'b': [3]})


if __name__ == '__main__':
    unittest.main()
