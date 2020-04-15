from __future__ import print_function

def epmt_help_api(funcs = []):
    import epmt_settings as settings
    import epmt_query as eq
    import epmt_outliers as eod
    import epmtlib as el
    import epmt_stat as es
    import epmt_exp_explore as exp
    from epmtlib import docs_module_index
    from inspect import signature
    from sys import stderr
    if funcs:
        for fname in funcs:
            func = None
            for m in (eq, eod, es, el, exp):
                if hasattr(m, fname):
                    func = getattr(m, fname)
                    break
            if func:
                print("from {} import {}\n".format(m.__name__, fname))
                print("{}{}".format(func.__name__, signature(func)))
                print(func.__doc__, '\n\n')
            else:
                print('Could not find function {} in any module'.format(fname), file=stderr)
    else:
        for m in (eq, eod, exp):
            print(m.__doc__)
            print(docs_module_index(m, fmt='string'), '\n\n')
