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

def partition_classifiers_uv_mv(classifiers):
    """
    Partition given list of classifiers into two disjoint sets,
    one containing multivariate classifiers and the other
    univariate classifiers
    """
    mv_set = set([ c for c in classifiers if is_classifier_mv(c) ])
    uv_set = set(classifiers) - mv_set
    return (uv_set, mv_set)

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
    logger.debug('original vector: {}'.format(list(ys)))
    if params:
        logger.debug('model params: {}'.format(params))
    logger.debug('madz scores: {}'.format(madz))
    return (madz, round(max(madz), 4), round(median_y, 4), round(median_absolute_deviation_y, 4))


def outliers_modified_z_score(ys,threshold=thresholds['modified_z_score']):
    scores = modified_z_score(ys)[0]
    return np.where(np.abs(scores) > threshold)[0]

def get_outlier_1d(df,column,func=outliers_iqr):
    if column not in df:
        return None
    return(func(df[column]))


def mvod_classifiers(contamination = 0.1, warnopts='ignore'):
    '''
    Returns a list of multivariate classifiers
    '''
    if warnopts:
        from warnings import simplefilter
        simplefilter(warnopts)
    logger = getLogger(__name__)  # you can use other name

    from pyod.models.abod import ABOD
    from pyod.models.knn import KNN
    #from pyod.models.feature_bagging import FeatureBagging # not stable, wrong results
    from pyod.models.mcd import MCD
    from pyod.models.cof import COF
    from pyod.models.hbos import HBOS
    from pyod.models.pca import PCA
    # from pyod.models.sos import SOS  # wrong result
    #from pyod.models.lmdd import LMDD # not stable
    #from pyod.models.cblof import CBLOF
    #from pyod.models.loci import LOCI # wrong result
    from pyod.models.ocsvm import OCSVM
    from pyod.models.iforest import IForest

    classifiers = [
                      ABOD(contamination=contamination), 
                      KNN(contamination=contamination), # requires too many data points
                      MCD(contamination=contamination), 
                      COF(contamination=contamination), 
                      HBOS(contamination=contamination), 
                      PCA(contamination=contamination), 
                      OCSVM(contamination=contamination), 
                      IForest(contamination=contamination),
                  ]
    return classifiers


# use like:
# x = mvod_scores(...)
# to get outliers for a particular threshold:
# (x['K Nearest Neighbors (KNN)'] > 0.5104869395352308) * 1
def mvod_scores(X = None, classifiers = [], warnopts = 'ignore'):
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
            _clf_scores = clf.decision_function(X)
        except Exception as e:
            logger.warning('Could not score using classifier {}'.format(clf_name))
            logger.warning('Exception follows below: ')
            logger.warning(e, exc_info=True)
            continue
        if not check_finite(_clf_scores):
            logger.warning('Could not score using classifier {} -- got NaNs or Inf'.format(clf_name))
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
            threshold = stats.scoreatpercentile(scores[clf_name],100 * (1 - contamination))
            logger.debug('{0} threshold: {1}'.format(clf_name, threshold))
    #print(scores)
    if not scores: 
        # some error occured and we didn't generate scores at all
        return False
    logger.debug('mvod: scores')
    logger.debug(scores)
    return (scores, max_score_for_cf)


def mvod_scores_using_model(inp, model_inp, classifier, threshold = None):
    """
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
        logger.warning('MVOD {} is not stable. We computed a threshold {}, while the passed threshold from the saved model was {}'.format(c_name, model_score_max, threshold))
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


def check_finite(values):
    from math import isnan, isinf
    n_nans = 0
    n_infs = 0
    for v in values:
        if isnan(v): n_nans += 1
        if isinf(v): n_infs += 1
    if n_nans:
        logger.debug('found {} NaN'.format(n_nans))
    if n_infs:
        logger.debug('found {} Inf'.format(n_infs))
    return ((n_infs == 0) and (n_nans == 0))

def pca_stat(inp_features, desired = 2):
    '''
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
             the list of explained variance ratios. If you sum this
             list of explained variance ratios you arrive at the
             cumumlative variance of the PCA, and is a measure
             of the extent to which the new PCA features capture
             the original features information.
    '''
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA

    logger = getLogger(__name__)  # you can use other name
    logger.debug('input feature array shape: {}'.format(inp_features.shape))

    # the second paramer denotes the number of components usually
    # however if it is less than 1, then it denotes the desired variance.
    # In the latter case the number of components is automatically chosen
    # to achieve the desired variance.
    if desired >= 1:
        logger.debug('desired num. PCA components: {}'.format(desired))
    else:
        logger.debug('desired variance ratio: {}'.format(desired))

    n_samples, n_dim = inp_features.shape
    assert(n_dim > 1)

    x = StandardScaler().fit_transform(inp_features)

    pca = PCA(n_components=desired) if (desired >= 1) else PCA(desired)
    pc_array = pca.fit_transform(x)
    if desired < 1:
        logger.debug('number of PCA components: {}'.format(pc_array.shape[1]))
    logger.debug('PCA array:\n{}'.format(pc_array))
    sum_variance = sum(pca.explained_variance_ratio_)
    logger.debug('PCA explained variance ratio: {}, sum({})'.format(pca.explained_variance_ratio_, sum_variance))
    if sum_variance < 0.80:
        logger.warning('cumulative variance for PCA ({}) < 0.80'.format(sum_variance))
    return (pc_array, pca.explained_variance_ratio_)


def check_distribution(data = [], dist='norm', alpha = 0.05):
    '''

        data: numpy 1-d array or list of numbers. If none is provided then
              one will be generated of the type of distribution to be tested for

        dist: A string representing the distribution from scipy.distributions
              such as 'norm' or 'uniform'. At present only 'norm' and 'uniform'
              are supported.

        alpha: Advanced option that helps set a threshold for null hypothesis

      RETURNS: A tuple, where the first member is the number of tests that PASSED
               and the second is the number of tests that FAILED.

    Reference: https://machinelearningmastery.com/a-gentle-introduction-to-normality-tests-in-python/

    >>> check_distribution(np.linspace(-15, 15, 100), 'uniform')                                              
      DEBUG: epmt_stat: data array shape: (100,)
      DEBUG: epmt_stat: min=-15.000 max=15.000 mean=0.000 std=8.747
      DEBUG: epmt_stat: alpha=0.05
      DEBUG: epmt_stat: Testing for uniform distribution
      DEBUG: epmt_stat: Doing Kolmogorov-Smirnov (uniform) test..
      DEBUG: epmt_stat:   statistics=0.010, p=1.000
      DEBUG: epmt_stat:   Kolmogorov-Smirnov (uniform) test: PASSED
      DEBUG: epmt_stat: check_distribution: 1 tests PASSED, 0 tests FAILED
    (1, 0)
    >>> check_distribution(np.random.randn(100), 'norm')                                                      
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
      DEBUG: epmt_stat: check_distribution: 3 tests PASSED, 0 tests FAILED
    (3, 0)
    >>> check_distribution(np.random.randn(100), 'uniform')                                                   
      DEBUG: epmt_stat: data array shape: (100,)
      DEBUG: epmt_stat: min=-2.207 max=2.165 mean=0.090 std=0.944
      DEBUG: epmt_stat: alpha=0.05
      DEBUG: epmt_stat: Testing for uniform distribution
      DEBUG: epmt_stat: Doing Kolmogorov-Smirnov (uniform) test..
      DEBUG: epmt_stat:   statistics=0.174, p=0.004
      DEBUG: epmt_stat:   Kolmogorov-Smirnov (uniform) test: FAILED
      DEBUG: epmt_stat: check_distribution: 0 tests PASSED, 1 tests FAILED
    (0, 1)
    '''
    # Shapiro-Wilk Test
    from scipy.stats import shapiro
    # D'Agostino
    from scipy.stats import normaltest
    from scipy.stats import kstest

    if (type(data) != np.ndarray) and not data:
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

    kstest_norm = lambda d: kstest(d, 'norm', (_mean, _std))
    kstest_uniform = lambda d: kstest(d, 'uniform', (_min, _max - _min))
    tests = { 'norm': [('Shapiro-Wilk', shapiro), ('Kolmogorov-Smirnov (norm)', kstest_norm)], 'uniform': [('Kolmogorov-Smirnov (uniform)', kstest_uniform)] }
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

    logger.debug('check_distribution: {} tests PASSED, {} tests FAILED'.format(passed, failed))
    return(passed, failed)
