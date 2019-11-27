#!/usr/bin/env python

# the import below is crucial to get a sane test environment
# from . import *
import unittest

# def setUpModule():
#     print('\n' + str(settings.db_params))
#     setup_db(settings)

from os import path    

class EPMTSettings(unittest.TestCase):

    def test_default_settings(self):
        default_settings_file = 'epmt_default_settings.py'
        # the test below will fail when we use pyinstaller so let's skip it
        # it's anyhow covered in the tests below
        # self.assertTrue(path.exists(default_settings_file) and (path.getsize(default_settings_file) > 0))
        try:
            import epmt_default_settings as defaults
        except:
            self.assertTrue(False, "default settings import failed")
        self.assertEqual(defaults.orm, 'sqlalchemy')
        # default settings shouldn't have db_params set. 
        with self.assertRaises(AttributeError):
            defaults.db_params

    def test_epmt_settings(self):
        self.assertTrue(path.exists('settings.py') and (path.getsize('settings.py') > 0))
        try:
            import epmt_settings as settings
        except:
            self.assertTrue(False, "could not load epmt_settings as settings")


    def test_settings_overrides_defaults(self):
        import epmt_default_settings as defaults # referred to as default settings below
        import settings as later_settings # referred to as 'later' settings below
        import epmt_settings as settings # referred to as settings module below
        default_vars = vars(defaults)
        later_vars = vars(later_settings)
        settings_vars = vars(settings)
        # Hack for the extra functions in the module. I'm confused yet I wrote this. -Pjm
        for n in ['basicConfig','getLogger','exit','ERROR']:
            del settings_vars[n]
        
        # the settings module keys are a union of the defaults and the later settings
        self.assertEqual(set(default_vars) | set(later_vars), set(settings_vars))
        # the values of the later settings take precedence over defaults
        for k in later_vars.keys():
            if k.startswith('_'): continue  # skip keys like __name__, __loader__
            self.assertEqual(settings_vars[k], later_vars[k], k)
        # for the keys in defaults but not in 'later', the settings will use the defaults
        for k in default_vars.keys():
            if k not in later_vars:
                self.assertEqual(settings_vars[k], default_vars[k], k)


if __name__ == '__main__':
    unittest.main()
