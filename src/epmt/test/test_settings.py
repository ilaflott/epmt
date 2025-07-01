#!/usr/bin/env python

# don't do this for this one, i think....
# from . import *

import unittest
from epmt.epmtlib import get_install_root
from os import path


def setUpModule():
    global install_root
    install_root = get_install_root()


class EPMTSettings(unittest.TestCase):

    def test_default_settings(self):
        default_settings_file = 'epmt_default_settings.py'
        # the test below will fail when we use pyinstaller so let's skip it
        # it's anyhow covered in the tests below
        # self.assertTrue(path.exists(default_settings_file)
        # and (path.getsize(default_settings_file) > 0))
        try:
            import epmt.epmt_default_settings as defaults
        except BaseException:
            self.assertTrue(False, "default settings import failed")
        self.assertEqual(defaults.orm, 'sqlalchemy')
        # default settings shouldn't have db_params set.
        # with self.assertRaises(AttributeError):
        #     defaults.db_params # pylint: disable=no-member
        # default settings uses in-memory sqlite
        self.assertEqual(defaults.db_params, {'url': 'sqlite:///:memory:', 'echo': False})

    def test_epmt_settings(self):
        self.assertTrue(path.exists(install_root + '/settings.py') and
                        (path.getsize(install_root + '/settings.py') > 0))
        try:
            import epmt.epmt_settings as settings
        except BaseException:
            self.assertTrue(False, "could not load epmt_settings as settings")

    def test_settings_overrides_defaults(self):

        import epmt.epmt_default_settings as defaults
        default_vars = vars(defaults)

        import epmt.settings as later_settings
        later_vars = vars(later_settings)

        import epmt.epmt_settings as settings
        settings_vars = vars(settings)

        # Hack for the extra functions in the module. I'm confused yet I wrote this. -Pjm
        # for n in ['basicConfig','getLogger','exit','ERROR']:
        # for n in ['basicConfig','getLogger','ERROR', 'epmt', 'logger', 'sys']:
        # for n in ['sys']:
        #    del settings_vars[n]

        # the settings module keys are a union of the defaults and the later settings
        self.assertEqual(set(default_vars) | set(later_vars),
                         set(settings_vars))

        # the values of the later settings take precedence over defaults
        for k in later_vars.keys():
            if k.startswith('_'):
                continue  # skip keys like __name__, __loader__
            if k == 'epmt_settings_kind':
                continue  # empty/null v 'user'
            self.assertEqual(settings_vars[k], later_vars[k], k)

        # for the keys in defaults but not in 'later', the settings will use the defaults
        for k in default_vars.keys():
            if k in later_vars:
                continue  # overwritten, so shouldnt be equal
            if k == 'epmt_settings_kind':
                continue  # empty/null v 'default'
            # print('\n')
            # print(f'k = {k}')
            if k == 'path':
                continue
                # print(settings_vars[k])
                # print(default_vars[k])
            self.assertEqual(settings_vars[k], default_vars[k], k)


if __name__ == '__main__':
    unittest.main()
