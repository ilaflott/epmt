from __future__ import print_function
import pandas as pd
import numpy as np

# Return a <boolean, df> tuple that consists of error/no-error and columns where the input data is out of tolerance,
# Rows are currently defined but should be configurable.

def rootcause_zscore(ref, input, features):
# describe() computes the following, as an example
#count  100.000000  100.000000  100.000000
#mean    73.540000   73.570000   73.620000
#std     14.887742   14.430786   13.690504
#min     50.000000   50.000000   50.000000
#25%     58.750000   61.750000   63.500000
#50%     73.000000   73.500000   74.000000
#75%     86.000000   85.000000   84.250000
#max     99.000000   99.000000   98.000000
#value   27.000000   29.000000  121.000000
    ref_computed = ref.describe()
# Now add the actual input vector to the describe output as a row for later reference, probably not needed
# and not really in the right place
    ref_computed.loc['value'] = input.iloc[0]
# I could not figure out how to do this arraywise so we do it per feature...
    for f in features:
        mean = ref_computed[f]['mean']
        sd = ref_computed[f]['std']
        val2compare = input[f][0]
# Instead of binary testing here, I should be returning the score per metric and not dropping columns
        tester = ((val2compare > (mean + 3*sd)) or (val2compare < (mean - 3*sd)))
# Delete all features (columns) that are not out of tolerance
        if tester == False:
            ref_computed.drop(f, axis=1, inplace=True)
#        else:
#            print(f,mean,sd,val2compare,tester)
    return ref_computed

#
# Observe that this function looks very much like the outlier detection functions. Can we integrate?
#

def rootcause(ref, input, features, methods = [rootcause_zscore]):
# API input checking
    if ref.empty or input.empty: 
        return False
    if not features:
        features = input.columns.all()
    if ref.columns.all() != input.columns.all():
        return False
# We don't really know what to do with multiple methods here yet, so just use the first
    for m in methods:
        df = m(ref,input,features)
# Here we should never be returning an empty set, just sets of scores for interpretation
        if df.empty:
            return False, None
        return True, df
# If methods list was empty...
    return False, None

if (__name__ == "__main__"):
# Synthesize 10 feature names
    n_features = 10
    features = [ '%c' % x for x in range(97, 97+n_features) ] 
    print("Features:\n",features)
#
# Check with multiple outliers
#
# Narrow range of reference values
    np.random.seed(104)
    random_reference_df = pd.DataFrame(np.random.randint(50,100,size=(100,n_features)), columns=features)
    print("Reference:\n",random_reference_df.head())
# Wider range input values for test set
    random_input_df = pd.DataFrame(np.random.randint(25,125,size=(1,n_features)), columns=features)
    print("Input:\n",random_input_df.head())
    retval, df = rootcause(random_reference_df,random_input_df,features)
    print("Retval:\n",retval)
    print("Result:\n",df)
#
# Check with one outlier
#
# Narrow range of reference values
    np.random.seed(102)
    random_reference_df = pd.DataFrame(np.random.randint(50,100,size=(100,n_features)), columns=features)
    print("Reference:\n",random_reference_df.head())
# Wider range input values for test set
    random_input_df = pd.DataFrame(np.random.randint(25,125,size=(1,n_features)), columns=features)
    print("Input:\n",random_input_df.head())
    retval, df = rootcause(random_reference_df,random_input_df,features)
    print("Retval:\n",retval)
    print("Result:\n",df)
#
# Check with no outliers
#
# Narrow range of reference values
    np.random.seed(103)
    random_reference_df = pd.DataFrame(np.random.randint(50,100,size=(100,n_features)), columns=features)
    print("Reference:\n",random_reference_df.head())
# Wider range input values for test set
    random_input_df = pd.DataFrame(np.random.randint(25,125,size=(1,n_features)), columns=features)
    print("Input:\n",random_input_df.head())
    retval, df = rootcause(random_reference_df,random_input_df,features)
    print("Retval:\n",retval)
    print("Result:\n",df)
