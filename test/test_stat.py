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

if __name__ == '__main__':
    unittest.main()
