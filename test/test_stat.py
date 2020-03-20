#!/usr/bin/env python3

# the import below is crucial to get a sane test environment
# from . import *
import unittest
import numpy as np
from epmt_stat import check_dist

class EPMTStat(unittest.TestCase):

    def test_outliers_iqr(self):
        from epmt_stat import outliers_iqr
        vec = [100, 100, 100, 45, 100]
        r = outliers_iqr(vec)[0]
        self.assertEqual(list(r), [0, 0, 0, 1, 0])
        # now let's do a more involved test
        vec = [1,2,3,4,3,2,1,10]
        (outliers, discard, q1, q3) = outliers_iqr(vec)
        self.assertEqual(list(outliers), [0, 0, 0, 0, 0, 0, 0, 1])
        self.assertEqual((discard, q1, q3), (0, 4.375, 6.625))
        # q1 and q3 are such that if provided as arguments
        # to another call of outliers_iqr with the same input
        # will *just* fit the vector and find no outliers
        (outliers_r, _, q1_r, q3_r) = outliers_iqr(vec, (discard, q1, q3))
        self.assertEqual(list(outliers_r), [0]*8)
        self.assertEqual((q1_r, q3_r), (q1, q3))

    def test_outliers_iqr_strings(self):
        import epmtlib as el
        from epmt_stat import outliers_iqr
        int_vec = el.hash_strings(['ABC', 'ABC', "ABC", 'DEF'])
        r = outliers_iqr(int_vec)[0]
        self.assertEqual(list(r), [0, 0, 0, 1])

    def test_z_score(self):
        import epmt_stat as es
        (scores, max_score, mean_y, stdev_y) = es.z_score([1,2,3,4,5,6,7,8,9,10, 1000])
        self.assertEqual(list(scores),[0.332 , 0.3285, 0.325 , 0.3215, 0.318 , 0.3145, 0.311 , 0.3075, 0.304 , 0.3005, 3.1621])
        self.assertEqual((max_score, mean_y, stdev_y), (3.1621, 95.9091, 285.9118))

    def test_check_dist(self):
        np.random.seed(1)
        (passed, failed) = check_dist(range(100), 'norm')
        self.assertTrue(failed > passed)
        (passed, failed) = check_dist(range(100), 'uniform')
        self.assertTrue(passed > failed)
        (passed, failed) = check_dist(np.linspace(-15,15,100), 'norm')
        self.assertTrue(failed > passed)
        (passed, failed) = check_dist(np.linspace(-15,15,100), 'uniform')
        self.assertTrue(passed > failed)
        (passed, failed) = check_dist(np.random.randn(100), 'norm')
        self.assertTrue(passed > failed)
        (passed, failed) = check_dist(np.random.randn(100), 'uniform')
        self.assertTrue(failed > passed)

    def test_normalize(self):
        from epmt_stat import normalize
        x = np.array([[0.0, 10.0], [0.13216, 12.11837], [0.25379, 42.05027], [0.30874, 13.11784]])
        norm_x = normalize(x)
        self.assertIsNone(np.testing.assert_almost_equal(norm_x, np.array([[0., 0.], [0.42806245, 0.06609523], [0.82201853, 1.], [1., 0.09727968]])))

    def test_dframe_append_weighted_row(self):
        import pandas as pd
        from epmt_stat import dframe_append_weighted_row
        df = pd.DataFrame([[1,2,2],[2,3,4]], columns = ['A', 'B', 'C'])
        x1 = dframe_append_weighted_row(df, [1.5,0.1])
        self.assertEquals(x1.shape, (3,3))
        self.assertTrue(x1.iloc[0].astype('int64').equals(df.iloc[0]))
        self.assertTrue(x1.iloc[1].astype('int64').equals(df.iloc[1]))
        self.assertEqual(list(x1.iloc[-1].values), [1.7, 3.3, 3.4])
        x2 = dframe_append_weighted_row(df, [1,0])
        self.assertTrue(x2.iloc[0].equals(df.iloc[0]))
        self.assertTrue(x2.iloc[1].equals(df.iloc[1]))
        self.assertTrue(x2.iloc[-1].equals(df.iloc[0]))

if __name__ == '__main__':
    unittest.main()
