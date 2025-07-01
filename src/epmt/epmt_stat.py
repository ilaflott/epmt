# -*- coding: utf-8 -*-
"""
EPMT Statistics Module
======================

This module provides low-level statistical and numerical methods.

Most methods use numpy ndarrays (as opposed to pandas dataframes).
We deliberately do not include an EPMT-specific semantic knowledge
in the functions of this module. The idea is to use them as pure
stateless mathematical functions. No database connectivity is assumed
for the functions in this module.
"""
# from __future__ import print_function
import epmt.epmt_settings as settings
import pandas as pd
import numpy as np
import operator
from logging import getLogger
from numbers import Number
from epmt.epmtlib import logfn

logger = getLogger(__name__)  # you can use other name

# this sets the defaults to be used when a trained model is not provided
thresholds = settings.outlier_thresholds


def get_classifier_name(c):
    """
    Returns the classifier name as a string::Statistics
    """
    if hasattr(c, '__name__'):
        return c.__name__
    if hasattr(c, '__module__'):
        return c.__module__
    raise 'Could not determine classifier name for {}'.format(c)


def is_classifier_mv(c):
    """
    Determines if a classifier is a multivariate classifier or not::Statistics

    Returns True if classifier is a multivariate classifier
    and False in all other cases. At present, we can only handle
    classifiers in this module and pyod
    """
    n = get_classifier_name(c)
    if n.startswith('pyod'):
        return True
    return False


def partition_classifiers_uv_mv(classifiers):
    """
    Partition classifiers into two disjoint sets of univariate and multivariate::Statistics

    """
    mv_set = set([c for c in classifiers if is_classifier_mv(c)])
    uv_set = set(classifiers) - mv_set
    return (uv_set, mv_set)


@logfn
def z_score(ys, params=()):
    '''
    Computes the *absolute* z-scores for an input vector::Statistics

    Parameters
    ----------

        ys : list or numpy 1-d array
             Input vector
    params : tuple of 3 floats
             Usually not provided. It's only of significance when
             computing z-scores against a trained model. In which
             case, it is of the form:
               (z_max, mean_y, stdev_y)
             where z_max: is the max absolute z-score in the model
                  mean_y: is the mean of the trained model input
                 stdev_y: is the std. deviation of the trained model input

    RETURNS
    -------
    abs_z_scores : list of floats
                   Absolute z-scores (same shape as ys)
     z_score_max : float
                   Max. absolute z-score
         mean_ys : float
                   Mean of the input vector
        stdev_ys : Standard deviation of input vector


    NOTES
    -----
    Unless you care about trained models you should ignore
    all return values except the first, and 'params' argument.

    EXAMPLES
    --------

    >>> z_score([1,2,3,4,5,6,7,8,9,10, 1000])
    (array([0.332 , 0.3285, 0.325 , 0.3215, 0.318 , 0.3145, 0.311 , 0.3075,
            0.304 , 0.3005, 3.1621]), 3.1621, 95.9091, 285.9118)
    '''
    # suppress divide by 0 warnings. We handle the actual division
    # issue by using np.nan_to_num
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    logger = getLogger(__name__)  # you can use other name
    logger.debug('scoring using {}'.format('z_score'))
    ys = np.array(ys)
    if params:
        # if params is set, we use it to get the mean and stdev
        _, mean_y, stdev_y = params
    else:
        mean_y = np.mean(ys).round(4)
        stdev_y = np.std(ys).round(4)
    abs_z_scores = np.nan_to_num(np.abs((ys - mean_y) / stdev_y).round(4))
    return (abs_z_scores, abs_z_scores.max(), mean_y, stdev_y)


def iqr(ys, params=()):
    '''
    Detects outliers using the 1.5 IQR rule::Statistics

        ys: Input vector
    params: If params is provided it should be of the form
            (0, lower_bound, upper_bound). In which case, we use
            the bounds provided for outlier detection, rather
            than computing the quartiles on the input vector.
            If not provided (default), the 25% and 75% quartiles
            are computed on the input vector. You should only
            be prividing params when using this method against
            a trained model.

   RETURNS: A tuple (outliers, 0, Q1, Q3), where:
            outliers is a mask with the same length as the input,
                and contains 0 if the element is an inlier and 1
                if the element is an outlier
            Q1: A theoretical value of Q1 is computed so that
                the input vector just fits on the lower side
            Q3: A theoretical value of Q3 is computed so that
                the input vector just fits on the upper side.

            0, which is the second element of the tuple is for
            compatibility with other outlier detection routines.
            Unless you care about training a model, you should
            ignore all return values except the first.

     NOTES: The motivation to return a theoretical value of Q1
            and Q3 stems from being able to use a trained model. We want
            to return some measure from the model run that can
            then be used later. The Q1 and Q3 are derived by solving
            a simutaneous equations such that the min of the input
            vector fits in the lower bound and the max in the upper
            bound. IOW:
            Ymin = Q1 - 1.5 * (Q3 - Q1)
            Ymax = Q3 + 1.5 * (Q3 - Q1)

            Solving the equations yeilds:
            Q1 = 3*Ymax/8 + 5*Ymin/8
            Q3 = 5*Ymax/8 + 3*Ymin/8


  EXAMPLES:

    # in the simplest case we only care about the outliers vector
    # not the other two return values (those are used for trained models)
    >>> (outliers, _, _, _) = es.iqr([1,1,2,3,4,1,100])
    >>> outliers
        array([0, 0, 0, 0, 0, 0, 1])
    '''
    logger = getLogger(__name__)  # you can use other name
    logger.debug('scoring using {}'.format('iqr'))
    ys = np.array(ys)
    span = [25, 75]
    if not params:
        # usual case: no model params
        quartile_1, quartile_3 = np.percentile(ys, span)
    else:
        # we have the lower and upper quartiles from a model
        _, quartile_1, quartile_3 = params
    iqr = quartile_3 - quartile_1
    logger.debug('Q1, Q3, IQR: {}, {}, {}'.format(quartile_1, quartile_3, iqr))
    lower_bound = quartile_1 - (iqr * 1.5)
    upper_bound = quartile_3 + (iqr * 1.5)
    logger.debug('lower_bound, upper_bound: {}, {}'.format(lower_bound, upper_bound))
    # the + 0 below makes boolean array a numeric array of 0s and 1s
    outliers = ((ys > upper_bound) | (ys < lower_bound)) + 0
    logger.debug('outliers vec: {}'.format(outliers))

    # If this vector were to be fitted, we can compute artifical
    # values of Q1 and Q3 based on the equation (see NOTES in the
    # documentation)
    fitted_Q1 = 3 * ys.max() / 8 + 5 * ys.min() / 8
    fitted_Q3 = 5 * ys.max() / 8 + 3 * ys.min() / 8
    return (outliers, 0, round(fitted_Q1, 4), round(fitted_Q3, 4))

# this function returns a tuple consisting of:
#  (scores, worst_score, median, median_absolute_deviation)
#
# All values after the first two are relevant only to this method
# and will only be used to compare an input against a reference run
# params if passed in, is of the form (max, median, median_abs_dev)
# We will ignore params(0) as that's the max z_score in the ref_model


def modified_z_score(ys, params=()):
    '''
    Returns the modified-adjusted Z-score (MADZ) for an input vector::Statistics
    '''
    logger = getLogger(__name__)  # you can use other name
    logger.debug('scoring using {}'.format('modified_z_score'))
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
    logger.debug('original vector: {}'.format(list(ys)))
    if params:
        logger.debug('model params: {}'.format(params))
    logger.debug('madz scores: {}'.format(madz))
    return (madz, round(max(madz), 4), round(median_y, 4), round(median_absolute_deviation_y, 4))

# All outliers_* methods return a vector mask that indicates
# whether an element is an outlier or not. They are wrappers
# around scoring methods -- z_score, modified_z_score, iqr


def outliers_iqr(ys):
    '''
    Returns a vector mask that identifies outliers using IQR::Statistics
    '''
    return iqr(ys)[0]


def outliers_modified_z_score(ys, threshold=thresholds['modified_z_score']):
    '''
    Returns a vector mask that identifies outliers using MADZ::Statistics
    '''
    scores = modified_z_score(ys)[0]
    # return np.where(np.abs(scores) > threshold)[0]
    # the + 0 will make it a numeric bitmask
    return (np.abs(scores) > threshold) + 0


def outliers_z_score(ys, threshold=thresholds['z_score']):
    '''
    Returns a vector mask that identifies outliers using z-score::Statistics
    '''
    scores = z_score(ys)[0]
    # return np.where(np.abs(scores) > threshold)[0]
    # the + 0 will make it a numeric bitmask
    return (np.abs(scores) > threshold) + 0


def outliers_uv(ys, methods=[outliers_iqr, outliers_z_score, outliers_modified_z_score]):
    '''
    Detects outliers in a vector using one or more univariate classifiers::Statistics

    Returns a vector that identifies outliers using the argument
    methods. For each element the returned vector indicates the
    number of outlier methods that considered that element to be
    an outlier.

         ys: Input vector (numpy 1-d array)
    methods: List of univariate classifiers to use. If unset all
             supported UV classifiers will be used. The classifiers
             must all return the outliers bitmask as their sole return
             value. So, use the outliers_* wrappers instead of methods
             such as iqr, z_score, modified_z_score
    '''
    logger = getLogger(__name__)  # you can use other name
    ys = np.array(ys)
    logger.debug('input vector: {}'.format(ys))
    out_vec = np.zeros_like(ys)
    if not methods:
        raise ValueError("'methods' needs to contain one or more univariate classifiers")
    logger.debug('outlier detection using {} methods'.format(len(methods)))
    for m in methods:
        outliers = m(ys)
        logger.debug('outliers using {}: {}'.format(m.__name__, outliers))
        out_vec += outliers
    logger.info('outliers using {} classifiers: {}'.format(len(methods), out_vec))
    return out_vec


def uvod_classifiers():
    '''
    Get a list of available univariate classifiers::Statistics

    Returns a list of available univariate classifiers based on settings.py
    If no univariate classifiers are defined in settings, then sensible defaults
    are returned. The returned list contains one or more callables that support
    the epmt univariate classifier interface.
    '''
    method_names = settings.univariate_classifiers if hasattr(settings, 'univariate_classifiers') else [
        'iqr', 'modified_z_score', 'z_score']
    import sys
    thismodule = sys.modules[__name__]
    funcs = [getattr(thismodule, m) for m in method_names]
    return funcs


def mvod_classifiers(contamination=0.1, warnopts='ignore'):
    '''
    Returns a list of multivariate classifiers::Statistics
    '''
    if warnopts:
        from warnings import simplefilter
        simplefilter(warnopts)
    logger = getLogger(__name__)  # you can use other name

    from pyod.models.abod import ABOD
    from pyod.models.knn import KNN
    # from pyod.models.feature_bagging import FeatureBagging # not stable, wrong results
    from pyod.models.mcd import MCD
    from pyod.models.cof import COF
    from pyod.models.hbos import HBOS
    from pyod.models.pca import PCA
    # from pyod.models.sos import SOS  # wrong result
    # from pyod.models.lmdd import LMDD # not stable
    # from pyod.models.cblof import CBLOF
    # from pyod.models.loci import LOCI # wrong result
    from pyod.models.ocsvm import OCSVM
    # from pyod.models.iforest import IForest # not stable, repeated calls give different scores

    classifiers = [
        ABOD(contamination=contamination),
        KNN(contamination=contamination),  # requires too many data points
        MCD(contamination=contamination),
        COF(contamination=contamination),
        HBOS(contamination=contamination),
        PCA(contamination=contamination),
        OCSVM(contamination=contamination),
        # IForest(contamination=contamination), # unstable, repeated calls give diff scores
    ]
    return classifiers


# use like:
# x = mvod_scores(...)
# to get outliers for a particular threshold:
# (x['K Nearest Neighbors (KNN)'] > 0.5104869395352308) * 1
def mvod_scores(X=None, classifiers=[], warnopts='ignore'):
    '''
    Perform outlier scoring using multivariate classifiers::Statistics

    Performs multivariate outlier scoring on a multi-dimensional
    numpy array. Returns a numpy array of scores for each
    classifier (same length as the input) where each score
    represents to the anomaly score of the corresponding point
    in the original array using that classifer.
    The more the likelihood of a point being an outlier, the
    higher score it will have.

    At present we support classifiers from PYOD. If none
    are provided in the 'classifiers' argument, then default
    classifiers will be selected using mvod_classifiers()

    X: Multi-dimensional np array. If not provided a random
       two-dimenstional numpy array is generated

    classifiers is a list of classifier functions like so:
             [
                 ABOD(),
                 KNN()
             ]

    warnopts takes the options from the python warning module:
        "default", "error", "ignore", "always", "module" and "once"

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

    if warnopts:
        from warnings import simplefilter
        # ignore all future warnings
        # simplefilter(action='ignore', category=FutureWarning)
        simplefilter(warnopts)

    logger = getLogger(__name__)  # you can use other name

    # the contamination below, is *ONLY* used in the model
    # for preditiction of outliers and used for random data
    # The API is confusing and it might appear that we are using the
    # parameter for the classifier, in fact, its' only used for
    # prediction of the outlier. The scores are the *same* regardless
    # of the contamination factor
    contamination = 0.1

    if not classifiers:
        classifiers = mvod_classifiers(contamination, warnopts)

    logger.debug('using classifiers: {}'.format([get_classifier_name(c) for c in classifiers]))

    Y = None  # Y is only used to test predictor with random data
    if X is None:
        n_pts = 100
        n_features = 16
        logger.warning('No input data for MVOD. Random data will be used with contamination {}'.format(contamination))
        from pyod.utils.data import generate_data, get_outliers_inliers
        from scipy import stats
        # generate random data with two features
        X = None
        # generate_data has a bug in that in some rare cases it produces
        # zeroes for the outliers. This messes model
        # fitting. So we just make sure we generate valid data
        # pylint: disable=unsubscriptable-object
        while (X is None) or (X[-int(n_pts * contamination):-1].sum() == 0.0):
            X, Y = generate_data(n_train=n_pts, train_only=True, n_features=n_features, contamination=contamination)
        # store outliers and inliers in different numpy arrays
        x_outliers, x_inliers = get_outliers_inliers(X, Y)

        n_inliers = len(x_inliers)
        n_outliers = len(x_outliers)

    (npts, ndim) = X.shape
    logger.debug('mvod: input length {0}, dimensions {1}'.format(npts, ndim))
    logger.debug(X)

    scores = {}
    max_score_for_cf = {}
    for clf in classifiers:
        clf_name = get_classifier_name(clf)

        # classifiers may often fail for a variety of reasons,
        # and do so by throwing exceptions. We trap those
        # exceptions, issue a warning and move on to the
        # next MVOD classifiers
        try:
            # fit the dataset to the model
            clf.fit(X)
            # predict raw anomaly score
            _clf_scores = clf.decision_function(X).round(4)
        except Exception as e:
            logger.warning('Could not score using classifier {}: {}'.format(clf_name, e))
            # logger.warning(e, exc_info=True)
            continue
        if not check_finite(_clf_scores):
            logger.warning('Could not score using classifier {}: got NaN or Inf'.format(clf_name))
            continue
        scores[clf_name] = _clf_scores
        max_score_for_cf[clf_name] = _clf_scores.max()

        if Y is not None:
            # prediction of a datapoint category outlier or inlier
            y_pred = clf.predict(X)
            # print(Y)
            # print(y_pred)

            # no of errors in prediction
            n_errors = (y_pred != Y).sum()
            print('No. of errors using ', clf_name, ': ', n_errors)

            # threshold value to consider a datapoint inlier or outlier
            # 0.1 is the default outlier fraction in the generated data
            threshold = stats.scoreatpercentile(scores[clf_name], 100 * (1 - contamination))
            logger.debug('{0} threshold: {1}'.format(clf_name, threshold))
    # print(scores)
    if not scores:
        # some error occured and we didn't generate scores at all
        return False
    logger.debug('mvod: scores')
    logger.debug(scores)
    return (scores, max_score_for_cf)


def mvod_scores_using_model(inp, model_inp, classifier, threshold=None):
    """
    Performs multivariate scoring against a model::Statistics

    Determines the score for *each row* separately against
    a model for a given classifier. If threshold is set, then
    rather than returning an array of scores, we just return
    an array of 0/1 corresponding to whether the row was an
    outlier or not.

    The important thing to remember in this function is that
    we do NOT run an MV classifier on the whole "inp". Rather
    we iterate over "inp" one row at a time. Join it to
    the model input, and then run on MVOD on the resultant
    matrix. Then we pick score for the inp row and append
    it to the return array of scores. If threshold is set
    then we just return an array of 0/1 values.

    inp: ndarray, columns correspond to features, and rows
         presumably, different jobs.

    model_inp: ndarray of model input

    classifier: a multivariate classifier

    threshold: optional. If provided this represents the
               the model score, and the inp is classified
               against it.

    Returns: If threshold is not set, then:

             numpy array of scores where the score at the
             ith index corresponds to the score of
             the ith row of inp.

             If threshold is set, then a numpy array of
             0 or 1, where the ith index is 1 if the ith
             row score is higher than the given threshold
             and 0 if its lower.
    """
    logger = getLogger(__name__)  # you can use other name
    inp_nrows = inp.shape[0]
    logger.debug('--- input to classify ---')
    logger.debug(inp)
    logger.debug('-------------------------')
    logger.debug('=== model input ===')
    logger.debug(model_inp)
    logger.debug('===================')

    scores = []
    # compute model score for sanity
    logger.debug('recomputing model scores as a sanity check on model stability..')
    c_name = get_classifier_name(classifier)
    retval = mvod_scores(model_inp, [classifier])
    if not retval:
        logger.warning('could not score using {}'.format(c_name))
        return False
    (model_scores, model_score_max) = retval
    model_score_max = model_score_max[c_name]
    logger.debug('MVOD {0} (threshold={1})'.format(c_name, threshold))
    from math import isclose
    if not isclose(model_score_max, threshold, rel_tol=1e-2):
        logger.warning(
            'MVOD {} is not stable. We computed a threshold {}, while the passed threshold from the saved model was {}'.format(
                c_name,
                model_score_max,
                threshold))
    for i in range(inp_nrows):
        # pick the ith row
        row = inp[i]
        # append it to the model input
        X = np.append(model_inp, [row], axis=0)
        # now run the mvod scoring
        retval = mvod_scores(X, [classifier])
        if not retval:
            logger.warning('could not score using {}'.format(c_name))
            return False
        (_scores, _) = retval
        # mvod_scores returns a dict indexed by classifier name
        # it will have exactly 1 key/value
        _scores = list(_scores.values())[0]
        # pick the score of the appended row (last element) and save it
        score = _scores[-1]
        logger.debug('MVOD {0} score for input index #{1}: {2}'.format(c_name, i, score))
        scores.append(_scores[-1])

    # make list into a numpy array
    scores = np.array(scores)

    # return scores if threshold is not set. Else return
    # a 0/1 vector of inlier / outliers
    # multiply by 1 to convert to a 0/1 vector
    logger.debug('*** input scores (model threshold={}) ***'.format(threshold))
    logger.debug(scores)

    return scores if (threshold is None) else (scores > threshold) * 1


# ref is a dataframe of reference entities, where the columns represent
# the features.
# inp represents a single entity and is either a Series or a DataFrame
# with a single row. If inp is a series then it's index labels MUST
# match the column labels of the ref dataframe. Similarly if inp is a
# dataframe then it's column labels must match those of ref and in the
# same order.
def rca(ref, inp, features, methods=[modified_z_score]):
    '''
    Perform low-level RCA::Statistics
    '''
    # API input checking
    if ref.empty or inp.empty:
        return (False, None, None)

    if isinstance(inp, pd.Series):
        inp = pd.DataFrame(inp).transpose()

    # if list(ref.columns.values) != list(inp.columns.values):
    #     logger.error('ref and inp MUST have the same columns and in the same order')
    #     logger.error('ref has columns: {}\ninp has columns: {}'.format(ref.columns.values, inp.columns.values))
    #     return (False, None, None)

    if (not features) or (features == '*'):
        # pick all the common numeric columns in the dataframe
        ref_cols_set = set(ref.columns.values)
        features = [f for f in list(inp.columns.values) if (isinstance(inp[f][0], Number) and (f in ref_cols_set))]
        logger.debug('using following features for RCA analysis: ' + str(features))

    ref_computed = ref[features].describe()
    ref_computed.loc['input'] = inp.iloc[0]

    result_dict = {f: 0 for f in features}

    for m in methods:
        c_name = get_classifier_name(m)
        ref_computed.loc['ref_max_' + c_name] = 0
        ref_computed.loc[c_name] = 0
        ref_computed.loc[c_name + '_ratio'] = 0
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
                ratio = inp_score / ref_max_score
            elif inp_score == 0:
                ratio = inp_score
            else:
                ratio = float('inf')
            ref_computed[f][c_name + '_ratio'] = ratio
            result_dict[f] += ratio

    # sort the result_dict by descending value
    dlst = sorted(result_dict.items(), key=operator.itemgetter(1), reverse=True)

    # Here we should never be returning an empty set, just sets of scores for interpretation
    ranked_features = [x[0] for x in dlst]

    # print("Sorted metrics",ranked_features)
    # Sort order of columns in returned dataframe
    return (True, ref_computed[ranked_features], dlst)


def check_finite(values):
    '''
    Low-level function to check if a vector contains finite values::Statistics
    '''
    from math import isnan, isinf
    n_nans = 0
    n_infs = 0
    for v in values:
        if isnan(v):
            n_nans += 1
        if isinf(v):
            n_infs += 1
    if n_nans:
        logger.debug('found {} NaN'.format(n_nans))
    if n_infs:
        logger.debug('found {} Inf'.format(n_infs))
    return ((n_infs == 0) and (n_nans == 0))


def pca_stat(inp_features, desired=2):
    '''
    Performs PCA on an ndarray::Statistics

    Combines features ndarray into a new PCA feature array with
    a dimensionality equal to n_components. It also returns an
    array containing the explained_variance_ratio.

    The PCA analysis will do scaling as part of this function,
    so the original feature set need not be provided scaled.

    inp_features: numpy multidimensional array of input features

    desired: Usually represents the number of PCA components desired.
             Defaults to 2. If this number is set to a floating point number
             less than 1.0, then it will be interpreted as the desired
             variance ratio. In that case the number of PCA components
             will be determined to be the least number of components that
             yields a variance greater than or equal to the level desired.

    Returns: A tuple, the first element is a numpy array of
             new PCA features. The second element of the tuple is
             the PCA transform.
    '''
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA

    logger = getLogger(__name__)  # you can use other name
    logger.debug('input feature array shape: {}'.format(inp_features.shape))
    if np.isnan(inp_features).any():
        raise ValueError('input contains at-least one non-numeric (nan) element')

    logger.debug('input:\n{}'.format(inp_features))

    # the second paramer denotes the number of components usually
    # however if it is less than 1, then it denotes the desired variance.
    # In the latter case the number of components is automatically chosen
    # to achieve the desired variance.
    if desired >= 1:
        logger.debug('desired num. PCA components: {}'.format(desired))
    else:
        logger.debug('desired variance ratio: {}'.format(desired))

    n_samples, n_dim = inp_features.shape
    assert (n_dim > 1)

    x = StandardScaler().fit_transform(inp_features)
    logger.debug('input after standard scaling:\n{}'.format(x))

    pca = PCA(n_components=desired) if (desired >= 1) else PCA(desired)
    pc_array = pca.fit_transform(x)
    if desired < 1:
        logger.debug('number of PCA components: {}'.format(pc_array.shape[1]))
    logger.debug('PCA array:\n{}'.format(pc_array))
    logger.debug('PCA feature weights:\n{}'.format(abs(pca.components_)))
    sum_variance = sum(pca.explained_variance_ratio_)
    logger.debug('PCA explained variance ratio: {}, sum({})'.format(pca.explained_variance_ratio_, sum_variance))
    if sum_variance < 0.80:
        logger.warning('cumulative variance for PCA ({}) < 0.80'.format(sum_variance))
    return (pc_array, pca)


def check_dist(data=[], dist='norm', alpha=0.05):
    '''
    Determines the distribution of input data::Statistics

        data: numpy 1-d array or list of numbers. If none is provided then
              one will be generated of the type of distribution to be tested for

        dist: A string representing the distribution from scipy.distributions
              such as 'norm' or 'uniform'. At present only 'norm' and 'uniform'
              are supported.

        alpha: Advanced option that helps set a threshold for null hypothesis

      RETURNS: A tuple, where the first member is the number of tests that PASSED
               and the second is the number of tests that FAILED.

    Reference: https://machinelearningmastery.com/a-gentle-introduction-to-normality-tests-in-python/

    >>> check_dist(np.linspace(-15, 15, 100), 'uniform')
      DEBUG: epmt_stat: data array shape: (100,)
      DEBUG: epmt_stat: min=-15.000 max=15.000 mean=0.000 std=8.747
      DEBUG: epmt_stat: alpha=0.05
      DEBUG: epmt_stat: Testing for uniform distribution
      DEBUG: epmt_stat: Doing Kolmogorov-Smirnov (uniform) test..
      DEBUG: epmt_stat:   statistics=0.010, p=1.000
      DEBUG: epmt_stat:   Kolmogorov-Smirnov (uniform) test: PASSED
      DEBUG: epmt_stat: check_dist: 1 tests PASSED, 0 tests FAILED
    (1, 0)
    >>> check_dist(np.random.randn(100), 'norm')
      DEBUG: epmt_stat: data array shape: (100,)
      DEBUG: epmt_stat: min=-2.613 max=2.773 mean=-0.096 std=1.049
      DEBUG: epmt_stat: alpha=0.05
      DEBUG: epmt_stat: Testing for norm distribution
      DEBUG: epmt_stat: Doing Shapiro-Wilk test..
      DEBUG: epmt_stat:   statistics=0.994, p=0.920
      DEBUG: epmt_stat:   Shapiro-Wilk test: PASSED
      DEBUG: epmt_stat: Doing D'Agostino test..
      DEBUG: epmt_stat:   statistics=0.390, p=0.823
      DEBUG: epmt_stat:   D'Agostino test: PASSED
      DEBUG: epmt_stat: Doing Kolmogorov-Smirnov (norm) test..
      DEBUG: epmt_stat:   statistics=0.067, p=0.777
      DEBUG: epmt_stat:   Kolmogorov-Smirnov (norm) test: PASSED
      DEBUG: epmt_stat: check_dist: 3 tests PASSED, 0 tests FAILED
    (3, 0)
    >>> check_dist(np.random.randn(100), 'uniform')
      DEBUG: epmt_stat: data array shape: (100,)
      DEBUG: epmt_stat: min=-2.207 max=2.165 mean=0.090 std=0.944
      DEBUG: epmt_stat: alpha=0.05
      DEBUG: epmt_stat: Testing for uniform distribution
      DEBUG: epmt_stat: Doing Kolmogorov-Smirnov (uniform) test..
      DEBUG: epmt_stat:   statistics=0.174, p=0.004
      DEBUG: epmt_stat:   Kolmogorov-Smirnov (uniform) test: FAILED
      DEBUG: epmt_stat: check_dist: 0 tests PASSED, 1 tests FAILED
    (0, 1)
    '''
    # https://stackoverflow.com/questions/40845304/runtimewarning-numpy-dtype-size-changed-may-indicate-binary-incompatibility
    import warnings
    warnings.filterwarnings("ignore")

    # Shapiro-Wilk Test
    from scipy.stats import shapiro
    # D'Agostino
    from scipy.stats import normaltest
    from scipy.stats import kstest

    if (not isinstance(data, np.ndarray)) and not data:
        from numpy.random import seed
        from numpy.random import randn
        # seed the random number generator
        seed(1)
        # generate univariate observations
        if dist == 'uniform':
            logger.debug('generating random data with uniform distribution')
            data = np.random.uniform(-1, 1, 100)
        else:
            logger.info('generating random data with Gaussian distribution')
            data = 5 * randn(100) + 50
    else:
        data = np.asarray(data)
    logger.debug('data array shape: {}'.format(data.shape))
    (_min, _max, _mean, _std) = np.min(data), np.max(data), np.mean(data), np.std(data)
    logger.debug('min=%.3f max=%.3f mean=%.3f std=%.3f' % (_min, _max, _mean, _std))
    logger.debug('alpha=%.2f' % alpha)
    passed = 0
    failed = 0

    def kstest_norm(d): return kstest(d, 'norm', (_mean, _std))
    def kstest_uniform(d): return kstest(d, 'uniform', (_min, _max - _min))
    tests = {'norm': [('Shapiro-Wilk', shapiro), ('Kolmogorov-Smirnov (norm)', kstest_norm)],
             'uniform': [('Kolmogorov-Smirnov (uniform)', kstest_uniform)]}
    if data.size > 20:
        # The test below requires at least 20 elements
        tests['norm'].append(('D\'Agostino', normaltest))
    if not dist in tests:
        raise ValueError('We only support the following distributions: {}'.format(tests.keys()))
    logger.debug('Testing for {} distribution'.format(dist))

    for (test, f) in tests[dist]:
        # normality test
        logger.debug('Doing {} test..'.format(test))
        stat, p = f(data)
        logger.debug('  statistics=%.3f, p=%.3f' % (stat, p))
        if p > alpha:
            passed += 1
            logger.debug('  {} test: PASSED'.format(test))
        else:
            failed += 1
            logger.debug('  {} test: FAILED'.format(test))

    logger.debug('check_dist: {} tests PASSED, {} tests FAILED'.format(passed, failed))
    return (passed, failed)


def get_modes(X, max_modes=10):
    '''
    Get the modes for a distribution::Statistics

    Parameters
    ----------
                X: 1-d numpy array or list
                   Possibly, multimodal, 1-D vector for which we want to
                   determine the number of modes
        max_modes: int
                   The maximum number of modes to check for (>= 2)

    Returns
    -------
          modes: numpy 1-D array of mode values

    Notes
    -----
    The approach uses KMeans clustering with the Silhouette method to determine
    the optimal number of clusters.

    The Silhouette method only works if number of clusters is >= 2.
    The elbow method (also computed) as km_scores works with number of
    clusters equal to 1.

    The data will be scaled automatically as needed so you don't need to
    pass scaled data.

    See:
    https://github.com/tirthajyoti/Machine-Learning-with-Python/blob/master/Clustering-Dimensionality-Reduction/Clustering_metrics.ipynb
    '''
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import silhouette_score
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X.reshape(-1, 1))
    km_silhouette = []
    km_scores = []
    for i in range(1, max_modes):
        km = KMeans(n_clusters=i, random_state=0).fit(X_scaled)
        preds = km.predict(X_scaled)

        logger.debug("Score for number of cluster(s) {}: {}".format(i, km.score(X_scaled)))
        km_scores.append(-km.score(X_scaled))

        if (i > 1):
            # silhouette method only works for n_clusters >= 2
            silhouette = silhouette_score(X_scaled, preds)
            km_silhouette.append(silhouette)
            logger.debug("Silhouette score for number of cluster(s) {}: {}".format(i, silhouette))

    # find optimal value according to elbow method
    diffs = np.abs(np.diff(km_scores))
    logger.debug('diffs of km_scores: {}'.format(diffs))
    from kneed import KneeLocator
    kneedle = KneeLocator(range(len(km_scores)), km_scores, S=1.0, curve='convex', direction='decreasing')
    modes_by_elbow_method = kneedle.elbow + 1
    logger.debug('optimal clustering according to elbow method: {}'.format(modes_by_elbow_method))
    num_modes = modes_by_elbow_method
    if modes_by_elbow_method != 1:
        # the index of the peak value fo km_silhouette + 2 (since we start
        # from 2 to max_modes represents the number of modes
        modes_by_silhouette_method = (np.argmax(km_silhouette) + 2)
        logger.debug('optimal clustering according to silhouette method: {}'.format(modes_by_silhouette_method))
        if modes_by_elbow_method != modes_by_silhouette_method:
            logger.warning(
                'Elbow and silhouette methods gave different mode counts -- {} and {}. Usually this means you might have a single mode or your data was not drawn from normal distributions'.format(
                    modes_by_elbow_method,
                    modes_by_silhouette_method))
            num_modes = 1

    km = KMeans(n_clusters=num_modes, random_state=0).fit(X_scaled)
    preds = km.predict(X_scaled)
    modes = scaler.inverse_transform(km.cluster_centers_).reshape(num_modes,)
    return modes


def normalize(v, min_=0, max_=1):
    '''
    Performs normalization (min-max scaling) on an input vector::Statistics

    Performs column-wise min-max scaling of a numpy array (of any dimension)
    so that the elements of each column range from min_ to max_.

    Returns a new scaled numpy array of the same shape as the original.
    '''
    from sklearn.preprocessing import minmax_scale
    return minmax_scale(v, feature_range=(min_, max_), axis=0)


def standardize(v):
    '''
    Performs standardization (z-score normalization) on a vector::Statistics

    Performs column-wise standardization (z-score normalization),
    so that each column has a mean 0, and a standard deviation 1.0.

          v: Input ndarray

    RETURNS: A standardized ndarray of the same shape as the input
    '''
    from scipy.stats import zscore
    return zscore(v, axis=0)


def dframe_append_weighted_row(df, weights, ignore_index=True, use_abs=False):
    '''
    Appends row to dataframe that uses a weighted combination of other rows::Statistics

    Returns a dataframe that's a copy of the original dataframe,
    with an additional row computed by multiplying each element
    in the same column with its corresponding weight and then
    summing over the columns.

    df: input dataframe
    weights: list of weights, with same length as number of rows in df
    ignore_index = If True (default), index labels are dropped.
    use_abs: If set, use absolute values of all values when computing
             row to append

    NOTE: The dtype will be upgraded to float64 if weights are floats.
    >>> df
       A  B  C
    0  1  2  2
    1  2  3  4

    # Notice the return dtype is float64 if the weights are floats
    >>> dframe_append_weighted_row(df, [1.5,0.1])
         A    B    C
    0  1.0  2.0  2.0
    1  2.0  3.0  4.0
    2  1.7  3.3  3.4

    >>> dframe_append_weighted_row(df, [0, 1])
       A  B  C
    0  1  2  2
    1  2  3  4
    2  2  3  4
    >>> dframe_append_weighted_row(df, [1, 0])
       A  B  C
    0  1  2  2
    1  2  3  4
    2  1  2  2

    '''
    assert (df.shape[0] == len(weights))
    weights_array = np.asarray(weights)
    new_row = []

    for c in df.columns:
        new_row.append(((abs(df[c].values) if use_abs else df[c].values) * np.asarray(weights_array)).sum())
    return df.append(pd.DataFrame([new_row], columns=df.columns), ignore_index=ignore_index)


def dict_outliers(dlist, labels=[], threshold=2.0):
    '''
    Get outliers from a collection of dictionaries::Statistics

    Parameters
    ----------
        dlist : list of dicts
       labels : list of strings, optional
                List of labels. If provided this must be the same
                length as dlist and each item in the labels must
                be the label for the corresponding dict in dlist.
                If not provided, the index of the dict in dlist will
                be assumed to be its label
    threshold : float, optional
                Number of standard deviations to determine if a value
                is an outlier or not. Defaults to 2.0, which means a
                key/value is an outlier if it the value is out of the
                range (mean - 2 * sigma, mean + 2*sigma)

    Returns
    -------
     (outliers, outl_by_key)

        outliers: set of outlier labels (or indices)
     outl_by_key: dict of outliers
    '''
    data = {}
    for d in dlist:
        for k in d:
            if k in data:
                data[k].append(d[k])
            else:
                data[k] = [d[k]]
    mean = {}
    std = {}
    labels = labels or range(len(dlist))
    outliers = set([])
    outl_by_key = {}
    for k in data:
        mean[k] = np.mean(data[k])
        std[k] = np.std(data[k])
        outl_by_key[k] = []

    i = 0
    for d in dlist:
        label = labels[i]
        for k in d:
            if (d[k] < (mean[k] - threshold * std[k])) or (d[k] > (mean[k] + threshold * std[k])):
                outl_by_key[k].append(label)
                outliers.add(label)
        i += 1

    # get the dict with non-empty keys
    pop_dict = {k: v for k, v in outl_by_key.items() if v}
    return (outliers, pop_dict)

# https://datascience.stackexchange.com/questions/57122/in-elbow-curve-how-to-find-the-point-from-where-the-curve-starts-to-rise
# def __find_elbow(data):
#     theta = np.arctan2(data[:, 1].max() - data[:, 1].min(), data[:, 0].max() - data[:, 0].min())
#
#     # make rotation matrix
#     co = np.cos(theta)
#     si = np.sin(theta)
#     rotation_matrix = np.array(((co, -si), (si, co)))
#
#     # rotate data vector
#     rotated_vector = data.dot(rotation_matrix)
#
#     # return index of elbow
#     return np.where(rotated_vector == rotated_vector.min())[0][0]
