#!/usr/bin/env python3

# the import below is crucial to get a sane test environment
# from . import *
import unittest
import numpy as np
from epmt_stat import check_dist

class EPMTStat(unittest.TestCase):
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

if __name__ == '__main__':
    unittest.main()
