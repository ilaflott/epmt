from __future__ import print_function
from os import environ
import pandas as pd
import numpy as np
import operator
from logging import getLogger
from numbers import Number

logger = getLogger(__name__)  # you can use other name
import epmt_settings as settings

# this sets the defaults to be used when a trained model is not provided
thresholds = settings.outlier_thresholds 


def get_classifier_name(c):
    """
    Returns the classifier name as a string
    """
    if hasattr(c, '__name__'): return c.__name__
    if hasattr(c, '__module__'): return c.__module__
    raise 'Could not determine classifier name for {}'.format(c)

def is_classifier_mv(c):
    """
    Returns True if classifier is a multivariate classifier
    and False in all other cases. At present, we can only handle
    classifiers in this module and pyod
    """
    n = get_classifier_name(c)
    if n.startswith('pyod'): return True
    return False


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



# use like:
# x = mvod_scores(...)
# to get outliers for a particular threshold:
# (x['K Nearest Neighbors (KNN)'] > 0.5104869395352308) * 1
def mvod_scores(X = None, classifiers = []):
    '''
    Performs multivariate outlier scoring on a multi-dimensional
    numpy array. Returns a numpy array of scores for each
    classifier (same length as the input) where each score 
    represents to the anomaly score of the corresponding point 
    in the original array using that classifer.
    The more the likelihood of a point being an outlier, the
    higher score it will have.

    At present we support classifiers from PYOD. If none
    are provided in the 'classifiers' argument, then default
    classifiers (ABOD, KNN) will be selected.

    X: Multi-dimensional np array. If not provided a random
       two-dimenstional numpy array is generated
       
    classifiers is a list of classifier functions like so:
             [
                 ABOD(),
                 KNN()
             ]

    Here is a run with random data:

    >>> x = mvod_scores()                                                                                     
    No input data for MVOD. Random data will be used with 16 features
    No of Errors using  Angle-based Outlier Detector (ABOD) :  2
    Angle-based Outlier Detector (ABOD)  threshold:  -0.0883552095486537  (> threshold => outlier)
    No of Errors using  K Nearest Neighbors (KNN) :  0
    K Nearest Neighbors (KNN)  threshold:  0.8296872805514997  (> threshold => outlier)
    >>> x
    {'Angle-based Outlier Detector (ABOD)': array(...),
     'K Nearest Neighbors (KNN)':  array(...) }    
    '''
    logger = getLogger(__name__)  # you can use other name

    # the contamination below, is *ONLY* used in the model
    # for preditiction of outliers and used for random data
    # The API is confusing and it might appear that we are using the
    # parameter for the classifier, in fact, its' only used for
    # prediction of the outlier. The scores are the *same* regardless
    # of the contamination factor
    contamination = 0.1


    if not classifiers:
        from pyod.models.abod import ABOD
        from pyod.models.knn import KNN
        from pyod.models.iforest import IForest
        from pyod.models.mcd import MCD
        classifiers = [
             ABOD(contamination=contamination),
             KNN(contamination=contamination),
             IForest(contamination=contamination),
             MCD(contamination=contamination)
        ]
    logger.debug('using classifiers: {}'.format([get_classifier_name(c) for c in classifiers]))

    Y = None  # Y is only used to test predictor with random data
    if X is None:
        n_pts = 100
        n_features = 16
        logger.warning('No input data for MVOD. Random data will be used with contamination {}'.format(contamination))
        from pyod.utils.data import generate_data, get_outliers_inliers
        from scipy import stats
        #generate random data with two features
        X = None
        # generate_data has a bug in that in some rare cases it produces
        # zeroes for the outliers. This messes model
        # fitting. So we just make sure we generate valid data
        # pylint: disable=unsubscriptable-object
        while (X is None) or (X[-int(n_pts*contamination):-1].sum() == 0.0):
            X, Y = generate_data(n_train=n_pts,train_only=True, n_features=n_features, contamination=contamination)
        # store outliers and inliers in different numpy arrays
        x_outliers, x_inliers = get_outliers_inliers(X,Y)
    
        n_inliers = len(x_inliers)
        n_outliers = len(x_outliers)

    (npts, ndim) = X.shape
    logger.info('mvod: Input data length {0}, dimensions {1}'.format(npts, ndim))
    
    scores = {}
    max_score_for_cf = {}
    for clf in classifiers:
        clf_name = get_classifier_name(clf)
        # fit the dataset to the model
        clf.fit(X)
    
        # predict raw anomaly score
        scores[clf_name] = clf.decision_function(X)
        max_score_for_cf[clf_name] = scores[clf_name].max()
   
        if Y is not None: 
            # prediction of a datapoint category outlier or inlier
            y_pred = clf.predict(X)
            # print(Y)
            # print(y_pred)
    
            # no of errors in prediction
            n_errors = (y_pred != Y).sum()
            print('No of Errors using ', clf_name, ': ', n_errors)
    
    
            # threshold value to consider a datapoint inlier or outlier
            # 0.1 is the default outlier fraction in the generated data
            threshold = stats.scoreatpercentile(scores[clf_name],100 * (1 - contamination))
            print(clf_name, ' threshold: ', threshold, ' (> threshold => outlier)')
    #print(scores)
    return (scores, max_score_for_cf)
    

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
        c_name = get_classifier_name(m)
        ref_computed.loc['ref_max_' + c_name] = 0
        ref_computed.loc[c_name] = 0
        ref_computed.loc[c_name+'_ratio' ] = 0
        for f in features:
            # lets get the params for ref using the scoring method
            # we expect the following tuple:
            # the params following the score are of relevance to the method
            # and we use it to feed back into the method for inp
            # ([scores], max_score, ....)
            ref_params = m(ref[f])
            ref_max_score = ref_params[1]
            ref_computed[f]['ref_max_' + c_name] = ref_max_score
            inp_params = m([inp[f][0]], ref_params[1:])
            inp_score = inp_params[0][0]
            ref_computed[f][c_name] = inp_score
            if ref_max_score != 0:
                ratio = inp_score/ref_max_score
            elif inp_score == 0:
                ratio = inp_score
            else:
                ratio = float('inf')
            ref_computed[f][c_name+'_ratio'] = ratio
            result_dict[f] += ratio

    # sort the result_dict by descending value
    dlst = sorted(result_dict.items(), key=operator.itemgetter(1), reverse=True)

    # Here we should never be returning an empty set, just sets of scores for interpretation
    ranked_features = [x[0] for x in dlst]

    # print("Sorted metrics",ranked_features)
    # Sort order of columns in returned dataframe
    return (True, ref_computed[ranked_features], dlst)

