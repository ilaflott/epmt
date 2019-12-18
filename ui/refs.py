import pandas as pd
import numpy as np
import datetime

from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger(__name__)  # you can use other name


def get_refs():
    import epmt_query as eq
    m = eq.get_refmodels()
    return [[nm['id'], nm['name'], nm['created_at'], nm['tags'], nm['jobs'], ['duration', 'cpu_time', 'num_procs'], nm['enabled']] for nm in m]



def make_refs(name='', jobs=None, tags={}):
    import epmt_query as eq
    # eq.create_refmodel(jobs=['625133','693118','696085'], name='Sample', tag={'exp_name':'ESM4_historical_D151','exp_component': 'atmos_cmip'})
    try:
        nm = eq.create_refmodel(jobs=jobs, name=name, tag=tags)
        return [[nm['id'], nm['name'], nm['created_at'], nm['tags'], nm['jobs'], ['duration', 'cpu_time', 'num_procs'], nm['enabled']]]
    except Exception as e:
        logger.error("Create model failed {}".format(e))
        return None

# Returns a list of model data to be converted into a dataframe
def _old_make_refs(x, name='', jobs=None, tags={}):
    from random import randint, getrandbits
    from .jobs import job_gen
    # Our generated references need to pull jobids and tags from jobs
    job_df = job_gen().df
    refs = []
    joblist = job_df['job id'].tolist()
    featureli = ['duration', 'cpu_time', 'num_procs']
    datefmt = "%Y-%m-%d"
    from copy import deepcopy
    for n in range(x):
        # If jobs were not passed randomly create some 500 days ago
        # subsequent jobs will be incrementally sooner
        from datetime import date, timedelta
        ref_date = (date.today() - timedelta(days=500) +
                    timedelta(days=n)).strftime(datefmt)
        if not jobs:
            ref_jobs = [joblist[i]
                        for i in range(randint(1, 1))]  # setup 5-8 jobs per ref
            # 95% Chance of being active
            ref_active = False
            features = [featureli[i]
                        for i in range(randint(1, 3))]  # Setup random features
            jname = 'Sample_Model_' + str(n) + name
            tags = {"exp_name": "ESM0_historical", "exp_component": "ocean_annual_rho2_1x1deg"}
        else:
            # User is building a reference with jobs selected today
            jname = name
            ref_jobs = jobs
            today = date.today()
            # Ref model is being generated now
            ref_date = today.strftime(datefmt)
            ref_active = True   # Set active User Friendly
            features = featureli  # Full Features
        refs.append(deepcopy([jname, ref_date, tags, ref_jobs,
                     features, ref_active]))                       # Append each ref to refs list
    return refs

# Generate a list of sample references
# ref_gen does data cleanup and conversions for displaying reference models
class ref_gen:
    def __init__(self):
        #references = make_refs(2)
        self.df = pd.DataFrame(get_refs(), columns=['id',
                               'name', 'date created', 'tags', 'jobs', 'features', 'active'])
        # self.df['active'] = np.where(self.df['active'], 'Yes', 'No')
        # Reorder
        self.df = self.df[['id', 'name', 'active',
                           'date created', 'tags', 'jobs', 'features']]


# Grabs sample reference models
# formats them
# returns dataframe
def get_references():
    ref_df = ref_gen().df
    logger.debug("Refs({}):\n{}".format(id(ref_df), ref_df))
    # Ref model initialization data
    from json import dumps
    ref_df['tags'] = ref_df['tags'].apply(dumps)  # Dumps stringify's dictionaries
    ref_df['jobs'] = ref_df['jobs'].apply(dumps)  # Dumps stringify's lists
    ref_df['features'] = ref_df['features'].apply(
        dumps)  # Dumps stringify's lists
    return ref_df


ref_df = get_references()
