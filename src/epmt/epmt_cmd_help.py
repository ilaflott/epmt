"""
EPMT help command module - provides help functionality.
"""
# from __future__ import print_function
from inspect import signature
from sys import stderr

# ian - what is this???


def epmt_help_api(funcs=[]):
    import epmt.epmt_settings as settings
    import epmt.epmt_query as eq
    import epmt.epmt_outliers as eod
    import epmt.epmtlib as el
    import epmt.epmt_stat as es
    import epmt.epmt_exp_explore as exp
    from epmt.epmtlib import docs_module_index

    if funcs:
        for fname in funcs:
            func = None
            for m in (eq, eod, es, el, exp):
                if hasattr(m, fname):
                    func = getattr(m, fname)
                    break
            if func:
                print("from {} import {}\n".format(m.__name__, fname))
                section = el.docs_func_section(func)
                print("{}{}".format(func.__name__, signature(func)))
                doc = func.__doc__
                if section:
                   # add the section name with suitable indent
                    print('\n    Section::{}'.format(section))
                    # remove the ugly section suffix from the summary string
                    doc = doc.replace('::{}'.format(section), '')
                print(doc, '\n\n')
            else:
                print('Could not find function {} in any module'.format(fname), file=stderr)
    else:
        for m in (eq, eod, exp, es):
            print(m.__doc__)
            print(docs_module_index(m, fmt='string'), '\n')
