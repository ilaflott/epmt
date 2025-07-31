#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest
from glob import glob
from epmt.epmtlib import capture, timing, get_install_root
import epmt.epmt_query as eq
import epmt.epmt_settings as settings
import epmt.epmt_exp_explore as exp


def do_cleanup():
    eq.delete_jobs(['685000', '685003'], force=True, remove_models=True)


@timing
def setUpModule():
    print('\n' + str(settings.db_params))
    setup_db(settings)
    do_cleanup()
    datafiles = '{}/test/data/query/68500[03].tgz'.format(install_root)
    print('setUpModdule: importing {0}'.format(datafiles))
    epmt_submit(sorted(glob(datafiles)), dry_run=False)


def tearDownModule():
    do_cleanup()


class ExploreAPI(unittest.TestCase):
    #     # called ONCE before before first test in this class starts
    #     @classmethod
    #     def setUpClass(cls):
    #         pass
    #
    #     # called ONCE after last tests in this class is finished
    #     @classmethod
    #     def tearDownClass(cls):
    #         pass
    #
    #     # called before every test
    #     def setUp(self):
    #         pass
    #
    #     # called after every test
    #     def tearDown(self):
    #         pass

    def test_exp_find_jobs(self):
        jobs = exp.exp_find_jobs(
            'ESM4_historical_D151', components=[
                'ocean_annual_rho2_1x1deg', 'ocean_cobalt_fdet_100'], exp_times=[
                '18540101', '18840101'], jobs=[
                '685000', '685003'], failed=False)
        self.assertEqual(set(jobs), {'685000', '685003'})
        jobs = exp.exp_find_jobs(
            'ESM4_historical_D151',
            components=[
                'ocean_annual_rho2_1x1deg',
                'ocean_cobalt_fdet_100'],
            exp_times=['18840101'],
            failed=True)
        self.assertFalse(jobs)
        jobs = exp.exp_find_jobs(
            'ESM4_historical_D151',
            components=['ocean_annual_rho2_1x1deg'],
            exp_times=['18840101'])
        self.assertEqual(jobs, ['685000'])

    def test_missing_segments(self):
        with capture() as (out, err):
            d = exp.find_missing_time_segments(
                'ESM4_historical_D151', jobs=[
                    '685000', '685003'], time_segments=range(
                    18540101, 20140101, 50000))
        self.assertEqual(d,
                         {'ocean_annual_rho2_1x1deg': [18540101,
                                                       18590101,
                                                       18640101,
                                                       18690101,
                                                       18740101,
                                                       18790101,
                                                       18890101,
                                                       18940101,
                                                       18990101,
                                                       19040101,
                                                       19090101,
                                                       19140101,
                                                       19190101,
                                                       19240101,
                                                       19290101,
                                                       19340101,
                                                       19390101,
                                                       19440101,
                                                       19490101,
                                                       19540101,
                                                       19590101,
                                                       19640101,
                                                       19690101,
                                                       19740101,
                                                       19790101,
                                                       19840101,
                                                       19890101,
                                                       19940101,
                                                       19990101,
                                                       20040101,
                                                       20090101],
                          'ocean_cobalt_fdet_100': [18540101,
                                                    18590101,
                                                    18640101,
                                                    18690101,
                                                    18740101,
                                                    18790101,
                                                    18890101,
                                                    18940101,
                                                    18990101,
                                                    19040101,
                                                    19090101,
                                                    19140101,
                                                    19190101,
                                                    19240101,
                                                    19290101,
                                                    19340101,
                                                    19390101,
                                                    19440101,
                                                    19490101,
                                                    19540101,
                                                    19590101,
                                                    19640101,
                                                    19690101,
                                                    19740101,
                                                    19790101,
                                                    19840101,
                                                    19890101,
                                                    19940101,
                                                    19990101,
                                                    20040101,
                                                    20090101]})


if __name__ == '__main__':
    unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(ExploreAPI)
    unittest.TextTestRunner(verbosity=2).run(suite)
