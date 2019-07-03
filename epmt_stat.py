from __future__ import print_function
from os import environ
import pandas as pd
import numpy as np
import operator
from logging import getLogger
from numbers import Number

logger = getLogger(__name__)  # you can use other name

if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
    import epmt_default_settings as settings
else:
    import settings


# this sets the defaults to be used when a trained model is not provided
thresholds = settings.outlier_thresholds 

# These all return a tuple containing a list of indicies
# For 1-D this is just a tuple with one element that is a list of rows
def outliers_z_score(ys, threshold=thresholds['z_score']):
    mean_y = np.mean(ys)
    stdev_y = np.std(ys)
    z_scores = [(y - mean_y) / stdev_y for y in ys]
    return np.where(np.abs(z_scores) > threshold)[0]

def outliers_iqr(ys, span=thresholds['iqr']):
    quartile_1, quartile_3 = np.percentile(ys, span)
    iqr = quartile_3 - quartile_1
    lower_bound = quartile_1 - (iqr * 1.5)
    upper_bound = quartile_3 + (iqr * 1.5)
    return np.where((ys > upper_bound) | (ys < lower_bound))[0]

# this function returns a tuple consisting of:
#  (scores, worst_score, median, median_absolute_deviation)
# 
# All values after the first two are relevant only to this method
# and will only be used to compare an input against a reference run
# params if passed in, is of the form (max, median, median_abs_dev)
# We will ignore params(0) as that's the max z_score in the ref_model
def modified_z_score(ys, params=()):
    median_y = params[1] if params else np.median(ys)
    if params:
        median_absolute_deviation_y = params[2]
    else:
        median_absolute_deviation_y = np.median([np.abs(y - median_y) for y in ys])
        if median_absolute_deviation_y == 0:
            # use the mean absolute deviation if the median abs deviation is zero
            median_absolute_deviation_y = np.mean([np.abs(y - median_y) for y in ys])
    # z_score will be zero if std. dev is zero, for all others compute it
    if median_absolute_deviation_y > 0:
        madz = [round(0.6745 * abs(y - median_y) / median_absolute_deviation_y, 4) for y in ys]
    else:
        madz = [float('inf') if abs((y - median_y)) > 0 else 0 for y in ys]
    return (madz, max(madz), median_y, median_absolute_deviation_y)


def outliers_modified_z_score(ys,threshold=thresholds['modified_z_score']):
    scores = modified_z_score(ys)[0]
    return np.where(np.abs(scores) > threshold)[0]

def get_outlier_1d(df,column,func=outliers_iqr):
    if column not in df:
        return None
    return(func(df[column]))


# ref is a dataframe of reference entities, where the columns represent
# the features.
# inp represents a single entity and is either a Series or a DataFrame 
# with a single row. If inp is a series then it's index labels MUST
# match the column labels of the ref dataframe. Similarly if inp is a
# dataframe then it's column labels must match those of ref and in the
# same order.
def rca(ref, inp, features, methods = [modified_z_score]):
    # API input checking
    if ref.empty or inp.empty:
        return (False, None, None)

    if type(inp) == pd.Series:
        inp = pd.DataFrame(inp).transpose()

    if list(ref.columns.values) != list(inp.columns.values):
        logger.error('ref and inp MUST have the same columns and in the same order')
        return (False, None, None)

    if not features:
        # pick all the numeric columns in the dataframe
        features = [f for f in list(inp.columns.values) if isinstance(inp[f][0], Number)]
        logger.debug('using following features for RCA analysis: ' + str(features))

    ref_computed = ref[features].describe()
    ref_computed.loc['input'] = inp.iloc[0]

    result_dict = { f: 0 for f in features }

    for m in methods:
        ref_computed.loc['ref_max_' + m.__name__] = 0
        ref_computed.loc[m.__name__] = 0
        ref_computed.loc[m.__name__+'_ratio' ] = 0
        for f in features:
            # lets get the params for ref using the scoring method
            # we expect the following tuple:
            # the params following the score are of relevance to the method
            # and we use it to feed back into the method for inp
            # ([scores], max_score, ....)
            ref_params = m(ref[f])
            ref_max_score = ref_params[1]
            ref_computed[f]['ref_max_' + m.__name__] = ref_max_score
            inp_params = m([inp[f][0]], ref_params[1:])
            inp_score = inp_params[0][0]
            ref_computed[f][m.__name__] = inp_score
            if ref_max_score != 0:
                ratio = inp_score/ref_max_score
            elif inp_score == 0:
                ratio = inp_score
            else:
                ratio = float('inf')
            ref_computed[f][m.__name__+'_ratio'] = ratio
            result_dict[f] += ratio

    # sort the result_dict by descending value
    dlst = sorted(result_dict.items(), key=operator.itemgetter(1), reverse=True)

    # Here we should never be returning an empty set, just sets of scores for interpretation
    ranked_features = [x[0] for x in dlst]

    # print("Sorted metrics",ranked_features)
    # Sort order of columns in returned dataframe
    return (True, ref_computed[ranked_features], dlst)

