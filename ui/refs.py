import pandas as pd
import numpy as np
import datetime

from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger(__name__)  # you can use other name


def make_refs(name='', jobs=None, tags={}):
    from os import environ
    if environ.get("MOCK_EPMT"):
        import ui.epmt_mock as eq
    else:
        import epmt_query as eq
    # eq.create_refmodel(jobs=['625133','693118','696085'], name='Sample', tag={'exp_name':'ESM4_historical_D151','exp_component': 'atmos_cmip'})
    try:
        nm = eq.create_refmodel(jobs=jobs, name=name, tag=tags)
        return [[nm['id'], nm['name'], nm['created_at'], nm['tags'], nm['jobs'], ['duration', 'cpu_time', 'num_procs'], nm['enabled']]]
    except Exception as e:
        logger.error("Create model failed {}".format(e))
        return None


def get_refs():
    from os import environ
    if environ.get("MOCK_EPMT"):
        import ui.epmt_mock as eq
    else:
        import epmt_query as eq
    m = eq.get_refmodels()
    return [[nm['id'], nm['name'], nm['created_at'], nm['tags'], nm['jobs'], ['duration', 'cpu_time', 'num_procs'], nm['enabled']] for nm in m]


# Generate a list of sample references
# ref_gen does data cleanup and conversions for displaying reference models
class ref_gen:
    def __init__(self):
        from os import environ
        if environ.get("MOCK_EPMT"):
            logger.info("Using Mock data")
            model_data = []
            for n in range(3):
                model_data.append(make_refs(n)[0])
        else:
            import epmt_query as eq
            import epmt_outliers as eod
            model_data = get_refs()
        self.df = pd.DataFrame(model_data, columns=['id',
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
