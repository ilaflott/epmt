from epmt_query import get_jobs
from logging import getLogger
#import pandas
logger = getLogger(__name__)  # you can use other name


def check_int(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()
def check_boolean(s):
    if s.upper() in ('TRUE', 'FALSE'):
        return True
    return False
def check_none(s):
    if s.upper() in ('NONE'):
        return True
    return False

# Checks on a few types
def kwargify(list_of_str):
    myDict = {}
    jobs = []
    for s in list_of_str:
        if not "=" in s:
            jobs.append(s)
        else:
            a, b = s.split('=')
            if check_int(b):
                myDict[a] = int(b)
            elif check_boolean(b):
                myDict[a] = bool(b)
            elif check_none(b):
                myDict[a] = None
            else: #string
                myDict[a] = b
    if myDict.get('jobs') == None and jobs:
        myDict['jobs'] = jobs
    if myDict.get('fmt') == None:
        myDict['fmt'] = 'terse'
    return myDict

def epmt_list_jobs(arglist):
    logger.info("epmt_list_jobs: %s",str(arglist))
    kwargs = kwargify(arglist)
    jobs = get_jobs(**kwargs)
#    if type(jobs) == pandas.core.frame.DataFrame:
    if len(jobs) == 0:
        logger.error("get_jobs %s failed\n",str(kwargs))
        return False
    print(jobs)
    return True

