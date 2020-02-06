from __future__ import print_function

def epmt_show_job(jobid):
    from orm import Job, orm_to_dict
    import epmt_query # to set up db and init stuff
    if type(jobid) == list:
        jobid = jobid[0]
    j = Job[jobid]
    # EXCLUDE_ATTR = { 'processes', 'metadata' }
    j_dict = orm_to_dict(j)
    for key in sorted(j_dict.keys()):
        # if attr.startswith('_'): continue
        # if attr in EXCLUDE_ATTR: continue
        # print("%-20s\t%-20s" % ( attr, getattr(j, attr)))
        print("%-20s      %-20s" % (key, j_dict[key]))
    return True
