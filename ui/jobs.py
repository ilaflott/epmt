# Generate a random list of jobs
from string import ascii_letters
import random
import datetime
import time
import pandas as pd

# Index.py Configures logger debug level
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger(__name__)  # you can use other name

# Job_gen does data cleanup and conversions for displaying
class job_gen:
    def __init__(self, limit=60, offset=0):
        from os import environ
        if environ.get("MOCK_EPMT"):
            import ui.epmt_mock as eq
        else:
            import epmt_query as eq
        sample = eq.get_jobs(fmt='dict', limit=limit, offset=offset)

        self.df = pd.DataFrame(sample)
        self.df = self.df.sort_values(
                "start",  # Column to sort on
                ascending = False,  # Boolean eval.
                inplace=False
            )
        # Extract the exit code to a column
        exit_codes = [d.get('status')['exit_code'] for d in self.df.info_dict]
        self.df['exit_code'] = exit_codes
        self.df['Processed'] = 0
        # Extract tags out and merge them in as columns
        # tags = pd.DataFrame.from_dict(self.df['tags'].tolist())
        # self.df = pd.merge(self.df,tags, left_index=True, right_index=True)

        # Convert Job date into a start_day datetime date
        self.df['start_day'] = self.df.start.map(lambda x: x.date())
        # datetime.strptime(start, "%Y-%m-%d").date()

        # Select specific tags for displaying
        # logger.info("Tags{}".format(self.df['tags']))

        from .dash_config import columns_to_print
        self.df = self.df[columns_to_print]
        from json import dumps
        #self.df['tags'] = self.df['tags'].apply(dumps)
        # Convert True into 'Yes' for user friendly display
        import numpy as np
        self.df['Processed'] = np.where(self.df['Processed'], 'Yes', 'No')

        # User friendly column names
        self.df.rename(columns={
            'jobid': 'job id',
            'exit_code': 'exit status',
            'Processed': 'processing complete',
            'write_bytes': 'bytes_out',
            'read_bytes': 'bytes_in'
        }, inplace=True)

# ####################### End List of jobs ########################


# API Call
def comparable_job_partitions(jobs, matching_keys = ['exp_name', 'exp_component']):
    # Returns [ (('matchname','matchcomponent'), {set of matchjobids}), ...]

    # Typically jobids are only passed
    # I need to get the jobids name and component
    alt = job_gen().df[job_gen().df['job id'].isin(jobs)].reset_index()
    tags_df = pd.DataFrame.from_dict(alt['tags'].tolist())
    # Only Display Specific tags from dash_config
    tags_df = tags_df[['exp_name','exp_component']]
    # Dataframe of jobs
    #logger.debug(alt)
    # Dataframe of Tags of jobs
    #logger.debug(tags_df)
    alt = pd.merge(alt, tags_df, left_index=True, right_index=True)
    #alt.drop('tags',axis=1)
    # Now Calculate comparable jobs
    recs = alt.to_dict('records')
    cdict = {}
    for rec in recs:
        if (rec['exp_name'],rec['exp_component']) in cdict:
            cdict[(rec['exp_name'],rec['exp_component'])].update({rec['job id']})
        else:    
            cdict[(rec['exp_name'],rec['exp_component'])] = {str(rec['job id'])}
    # Reconfigure output format with out
    out = [ ((exp_name,exp_component),cdict[(exp_name,exp_component)]) for exp_name, exp_component in cdict]
    logger.debug(out)
    return out


# API Call
def detect_outlier_jobs(jobs, trained_model=None, features=['cpu_time', 'duration', 'num_procs'], methods=['modified_z_score'], thresholds='thresholds', sanity_check=True):
    """
    (df, parts) = eod.detect_outlier_jobs(jobs)
    pprint(parts)
    {'cpu_time': ([u'kern-6656-20190614-190245',
                   u'kern-6656-20190614-194024',
                   u'kern-6656-20190614-191138'],
                  [u'kern-6656-20190614-192044-outlier']),
     'duration': ([u'kern-6656-20190614-190245',
                   u'kern-6656-20190614-194024',
                   u'kern-6656-20190614-191138'],
                  [u'kern-6656-20190614-192044-outlier']),
     'num_procs': ([u'kern-6656-20190614-190245',
                    u'kern-6656-20190614-192044-outlier',
                    u'kern-6656-20190614-194024',
                    u'kern-6656-20190614-191138'],
                   [])}
    """
    returns = ('df', {'feature' : (['job','job2'], ['joboutlier'])})
    return "Running outlier analysis on Jobs: " + str(jobs)

df = pd.DataFrame()

def get_version():
    return "EPMT 1.1.1"
