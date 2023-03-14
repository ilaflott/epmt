# -*- coding: utf-8 -*-
"""
EPMT Experiment Explore API
===========================

The EPMT Experiment Explore API provides a domain-specific
API where certain primitives such as experiment name,
component are taken for granted.

It's a higher-level API than EPMT Query and EPMT Outliers
API, which it uses underneath.
"""

from orm import db_session
import epmt.epmt_query as eq
import numpy as np
import epmt.epmt_stat as es
import epmt.epmt_settings as settings

from logging import getLogger

logger = getLogger(__name__)

@db_session
def exp_component_outliers(exp_name, metric = 'duration', op = np.sum, limit = 10):
    '''
    Orders components in an experiment by aggregate metric value::Experiments

    Computes an ordered list of components by aggregate metric value
    across jobs of that component. This function can be used to determine
    which jobs/time-segments of a particular component are outliers.
    By segregating jobs by component we are likely looking at comparable
    jobs. So if some job for a particular component takes longer than the
    other jobs within the same component, it might bear investigation.

    exp_name: Experiment name
      metric: A metric from the job model (duration, cpu_time, etc) or
             from its proc_sums field (such as num_threads)
          op: A callable that performs a reduction on a numpy vector or list
              For e.g., np.sum, or np.mean, etc
       limit: Restrict the output to the top N components

     RETURNS:
        Returns a list of components reverse sorted in the decreasing
        order of op(metric), where op is generally np.sum and metric
        is something like "duration". The returned list is of the form:

        [
          { 
            "exp_component" : <component-name>, 
            "jobids": [ list of jobids for component ],
            "metrics" : [ list of metric values corresponding to the jobids (same order) ],
            "exp_times" : [ list of exp_time values corresponding to the jobids (same order) ],
            "outlier_scores" : [ list of outlier scores corresponding to the jobids (same order)]
          },
          ...
        ]

        The ordering of the list is in decreasing order op(metric). For the defaults,
        this translates to decreasing order of cumulative sums of duration across all
        jobs of a component.

       NOTES: Outlier scores represent the number of methods that indicated that
              an element is an outlier. The higher the number, the greater the likelihood
              of the element being an outlier. A score of zero for an element means
              the corresponding jobid was not an outlier. We do multimode outlier
              detection using all available univariate classifiers.

    EXAMPLES:
    # In the example below you can see that for component ocean_annual_z_1x1deg
    # jobs 625151 (time-segment 18540101) and 691209 (time-segment 18890101)
    # are likely outliers; one on the higher side, and one on the lower.
    >>> exp_component_outliers('ESM4_historical_D151', 'duration')
    INFO: epmt_query: Experiment ESM4_historical_D151 contains 13 jobs: 625151,627907,629322,633114,675992, 680163,685000..685001,685003,685016,691209,692500,693129
    [{
         'exp_component': 'ocean_annual_z_1x1deg', 
          'exp_times': ['18540101','18590101','18640101','18690101','18740101','18790101','18840101','18890101','18940101'], 
          'jobids': ['625151','627907','629322','633114','675992','680163','685001','691209','693129'], 
          'metrics': array([1.04256232e+10, 6.58917488e+09, 7.28633175e+09, 6.03672005e+09, 9.11415052e+09, 6.15619201e+09, 6.81571048e+09, 8.60163243e+08, 3.61932477e+09]), 
          'outlier_scores': array([2., 0., 0., 0., 0., 0., 0., 2., 1.])
     }, 
     {
          'exp_component': 'ocean_month_rho2_1x1deg', 
          'exp_times': ['18840101'], 
          'jobids': ['685016'], 
          'metrics': array([7.00561851e+09]), 
          'outlier_scores': array([0.])
     }, 
     ...
    ]
    '''
    from epmt.epmtlib import ranges, natural_keys
    exp_jobs = eq.get_jobs(tags = { 'exp_name': exp_name }, fmt = 'orm' )
    # sorted jobids
    exp_jobids = sorted([j.jobid for j in exp_jobs], key=natural_keys)
    if not exp_jobids:
        logger.warning('Could not find any jobs with an "exp_name" tag matching {}'.format(exp_name))
        return False

    # get a compact string of jobids if possible for logs
    try:
        job_ranges_str = ",".join(["{}..{}".format(a, b) if (a != b) else "{}".format(a) for (a,b) in ranges([int(x) for x in exp_jobids])])
        logger.info('Experiment {} contains {} jobs: {}'.format(exp_name, exp_jobs.count(), job_ranges_str))
    except:
        # the ranges function can fail for non-integer jobids, so here
        # we simply print the job count, and not actually list the jobids
        logger.info('Experiment {} contains {} jobs'.format(exp_name, exp_jobs.count()))

    # we create a dict of dicts. The top-level dict is indexed by component name
    # Effectively we get to know for each component, the jobs and the time-segment
    # for the job, as well as the metric value for the job
    # {
    #      'ocean_annual_z_1x1deg': {'data': [('18540101', '625151', 10425623185.0), 
    #                                         ('18590101', '627907', 6589174875.0), 
    #                                         ('18640101', '629322', 7286331754.0), 
    #                                         ('18690101', '633114', 6036720046.0), 
    #                                         ('18740101', '675992', 9114150525.0), 
    #                                         ('18790101', '680163', 6156192011.0), 
    #                                         ('18840101', '685001', 6815710476.0), 
    #                                         ('18890101', '691209', 860163243.0), 
    #                                         ('18940101', '693129', 3619324767.0)]}, 
    #   'ocean_annual_rho2_1x1deg': {'data': [('18840101', '685000', 6460243317.0)]}, 
    #      'ocean_cobalt_fdet_100': {'data': [('18840101', '685003', 6615525773.0)]}, 
    #    'ocean_month_rho2_1x1deg': {'data': [('18840101', '685016', 7005618511.0)]}, 
    #     'ocean_monthly_z_1x1deg': {'data': [('18890101', '692500', 1663860093.0)]}
    # }
    # More keys (other than data will be added later)
    comp_dict = {}
    for j in exp_jobs:
        c = j.tags['exp_component']
        c_entry = comp_dict.get(c, {'data': []})
        # the metric value is either in the job model or in the proc_sums field
        m = getattr(j, metric) if hasattr(j, metric) else j.proc_sums[metric]
        c_entry['data'].append((j.tags.get('exp_time', ''), j.jobid, m))
        comp_dict[c] = c_entry

    # Now add some more fields to comp_dict entries, and also prepare a list
    # of tuples consisting of component name and some component data.
    # We will sort the component list (comp_list) later.
    comp_list = []
    for c, v in comp_dict.items():
        v['exp_component'] = c
        # d[0] is the time-segment -- extract it from the data field
        # and prepare a list of time-segments
        v['exp_times'] = [ d[0] for d in v['data']]
        # d[1] is the jobid -- extract it from the data field and prepare
        # a list of jobids for the component
        jobids = [d[1] for d in v['data']]
        v['jobids'] = jobids
        # d[2] is the metric -- extract it from the data field and prepare
        # a metrics vector for the component
        v['metrics'] = np.array([d[2] for d in v['data']])
        # compute outlier scores using multimode univariate outlier detection
        v['outlier_scores'] = es.outliers_uv(v['metrics'])
        # we can remove v['data'] once we have created the above fields
        del v['data']
        comp_list.append(v)
   
    # We generally care about components that have higher duration (metric) summed across
    # all the jobs of the component. However, we retain flexibility by ordering by
    # something like min/max/stddev instead by changing op.

    # order the components list by desc. metric sum (op is sum generally, but could be min/max/stddev)
    ordered_comp_list = sorted(comp_list, key = lambda v: op(v['metrics']), reverse=True)[:limit]
    return ordered_comp_list


@db_session
def exp_time_segment_stats(exp_name, metric = 'duration'):
    '''
    Computes statistics by time-segment for an experiment::Experiments

    This function can help you determine if one time-segment is taking
    significantly longer than another time-segment.

    exp_name: Experiment name
      metric: A field of the job model such as duration or cpu_time

     RETURNS: A an OrderedDict of the form:
              {
                '18540101': { 
                               'jobids': [list of jobids],
                              'metrics': [vector of metric values corresponding to the jobids]
                            }
                '18590101': {
                               ...
                            }
              }

   EXAMPLES:
   # The example is not ideal since different time segments have differing
   # number of jobs. If the number of jobs had been same (something we expect
   # normally, then by aggregating the metrics vector, one can easily
   # determine if one time-segment is an outlier.
   >>> exp_time_segment_stats('ESM4_historical_D151')                                                 
OrderedDict([('18540101', {'jobids': ['625151'], 'metrics': [10425623185.0]}),
             ('18590101', {'jobids': ['627907'], 'metrics': [6589174875.0]}),
             ('18640101', {'jobids': ['629322'], 'metrics': [7286331754.0]}),
             ('18690101', {'jobids': ['633114'], 'metrics': [6036720046.0]}),
             ('18740101', {'jobids': ['675992'], 'metrics': [9114150525.0]}),
             ('18790101', {'jobids': ['680163'], 'metrics': [6156192011.0]}),
             ('18840101', {'jobids': ['685000', '685001', '685003', '685016'],
                           'metrics': [6460243317.0, 6815710476.0, 6615525773.0, 7005618511.0]}), 
             ('18890101', {'jobids': ['691209', '692500'], 'metrics': [860163243.0, 1663860093.0]}),
             ('18940101', {'jobids': ['693129'], 'metrics': [3619324767.0]})])
    '''
    # We use an ordered dictionary as we want to return
    # a dictionary with time-segments in increasing order.
    from collections import OrderedDict
    od = OrderedDict()
    exp_jobs = eq.get_jobs(tags = { 'exp_name': exp_name }, fmt = 'orm' )
    # because jobs are ordered in increasing start time, we we will
    # end up creating a dictionary with time-segments in increasing order
    for j in exp_jobs:
        exp_time = j.tags.get('exp_time', '')
        if exp_time:
            if not exp_time in od:
                # initialize the dict
                od[exp_time] = { 'jobids': [], 'metrics': [] }
            # append the jobid and it's metric to the list of jobids 
            # for the corresponding time-segment
            od[exp_time]['jobids'].append(j.jobid)
            # the metric value is either in the job model or in the proc_sums field
            m = getattr(j, metric) if hasattr(j, metric) else j.proc_sums[metric]
            od[exp_time]['metrics'].append(m)
    return od



@db_session
def exp_explore(exp_name, metric = 'duration', op = np.sum, limit=10):
    '''
    Prints a drilldown for an experiment by components and time-segments::Experiments
    '''
    from scipy.stats import variation

    metric = metric or 'duration' # defaults when using with command-line
    limit = limit or 10 # defaults when using with command-line
    
    exp_jobs = eq.get_jobs(tags = { 'exp_name': exp_name }, fmt = 'orm' )
    ordered_comp_list = exp_component_outliers(exp_name, metric, op, limit)

    agg_metric = np.sum([ np.array(d['metrics']).sum() for d in ordered_comp_list ])

    print('\ntop {} components by {}({}):'.format(limit, op.__name__, metric))
    print("%16s  %12s         %12s %12s %4s" % ("component", "sum", "min", "max", "cv"))
    for v in ordered_comp_list:
        print("%16.16s: %12d [%4.1f%%] %12d %12d %4.1f" % (v['exp_component'], op(v['metrics']), 100*np.sum(v['metrics'])/agg_metric, np.min(v['metrics']),  np.max(v['metrics']), variation(v['metrics'])))

    # now let's the variations within a component across different time segments
    print('\nvariations across time segments (by component):')
    print("%16s %12s %12s %16s" % ("component", "exp_time", "jobid", metric))

    for v in ordered_comp_list:
        outliers = v['outlier_scores']
        for idx in range(len(v['metrics'])):
            print("%16.16s %12s %12s %16d %6s" % (v['exp_component'], v['exp_times'][idx], v['jobids'][idx], v['metrics'][idx], "**" * int(outliers[idx])))
        print()

    # finally let's see if by summing the metric across all the jobs in a 
    # time segment we can spot something interesting
    od = exp_time_segment_stats(exp_name, metric)
    time_segments = list(od.keys())
    metric_sums = [np.sum(od[t]['metrics']) for t in time_segments]
    outlier_scores = es.outliers_uv(metric_sums)
    print('{} by time segment:'.format(metric))
    for idx in range(len(time_segments)):
        print("%12s %16d %6s" % (time_segments[idx], metric_sums[idx], "**" * int(outlier_scores[idx])))
    return True

@db_session
def find_missing_time_segments(exp_name, jobs=[], components = [], time_segments = range(18540101, 20190101, 50000)):
    '''
    Finds missing time segments in an experiment::Experiments

    Parameters
    ----------
        exp_name : string
                   Experiment name
            jobs : list of strings or list of Job objects or ORM query, optional
                   Restrict the search to a subset of the experiment's jobs
                   If unspecified or empty all jobs belonging to the experiment
                   will be used.
      components : list, optional
                   Restrict the search to specified components
                   If unspecified or empty all components in the experiment
                   will be used
   time_segments : list of ints, optional
                   List of expected time segments. Defaults to 18540101 - 20090101
                   with a spacing of 50000.
                   You really should be specifying this parameter!

    Returns
    -------
    dict containing components with missing segments, with the
    key being the component name, and the value being the list
    if missing time segments

    Notes
    -----
    The function also prints the missing segment names against the component

    Examples
    --------
    >>> d = exp.find_missing_time_segments('ESM4_historical_D151', time_segments=range(18540101, 20140101, 50000))
    ocean_annual_rho2_1x1deg is missing [18540101, 18590101, 18640101, 18690101, 18740101, 18790101, 18890101, 18940101, 18990101, 19040101, 19090101, 19140101, 19190101, 19240101, 19290101, 19340101, 19390101, 19440101, 19490101, 19540101, 19590101, 19640101, 19690101, 19740101, 19790101, 19840101, 19890101, 19940101, 19990101, 20040101, 20090101]
    ocean_cobalt_fdet_100 is missing [18540101, 18590101, 18640101, 18690101, 18740101, 18790101, 18890101, 18940101, 18990101, 19040101, 19090101, 19140101, 19190101, 19240101, 19290101, 19340101, 19390101, 19440101, 19490101, 19540101, 19590101, 19640101, 19690101, 19740101, 19790101, 19840101, 19890101, 19940101, 19990101, 20040101, 20090101]
    >>> d
    { 'ocean_annual_rho2_1x1deg' : [18540101, 18590101, 18640101, 18690101, 18740101, 18790101, 18890101, 18940101, 18990101, 19040101, 19090101, 19140101, 19190101, 19240101, 19290101, 19340101, 19390101, 19440101, 19490101, 19540101, 19590101, 19640101, 19690101, 19740101, 19790101, 19840101, 19890101, 19940101, 19990101, 20040101, 20090101],
      'ocean_cobalt_fdet_100': [18540101, 18590101, 18640101, 18690101, 18740101, 18790101, 18890101, 18940101, 18990101, 19040101, 19090101, 19140101, 19190101, 19240101, 19290101, 19340101, 19390101, 19440101, 19490101, 19540101, 19590101, 19640101, 19690101, 19740101, 19790101, 19840101, 19890101, 19940101, 19990101, 20040101, 20090101]
    }
    '''
    tag_filter = { 'exp_name': exp_name }
    jobs = eq.get_jobs(jobs, fmt='orm', tags = [ tag_filter ])
    logger.debug('Looking for time segments: {}'.format(sorted(time_segments)))
    logger.debug('{} matching jobs from the experiment'.format(jobs.count()))
    jobs_tags = eq.get_job_tags(jobs, tag_filter = tag_filter, fold=True)
    matched_comp = jobs_tags['exp_component']
    if components:
        matched_comp &= set(components)
    logger.debug('{} components matched'.format(len(matched_comp)))
    ret = {}
    for c in sorted(matched_comp):
        comp_tags = eq.get_job_tags(jobs, tag_filter = 'exp_name:{};exp_component:{}'.format(exp_name, c))
        exp_times = comp_tags['exp_time']
        if type(exp_times) == str:
            exp_times = [exp_times]
        exp_times = set([ int(t) for t in exp_times ])
        missing_times = set(time_segments) - exp_times
        if missing_times:
            print('{} is missing {}'.format(c, sorted(missing_times)))
            ret[c] = sorted(missing_times)
    return ret

@db_session
def exp_find_jobs(exp_name, components = [], exp_times = [], failed = None, **kwargs):
    '''
    Finds jobs within an experiment::Experiments

    The function searches for jobs within an experiment based on
    restrictions on components, times and exit status

    Parameters
    ----------
          exp_name : string
                     Experiment name
        components : list of strings, optional
                     Restrict the search space to a set of components.
                     If unspecified, all jobs within the experiment are
                     candidates
         exp_times : list of ints or list of strings, optional
                     Restrict the search space to a set of time segments.
                     If unspecified, all jobs within the experiment are
                     candidates
            failed : boolean, optional
                     Restrict the search space to failed jobs if True
                     or successful jobs if False. If not set, both
                     failed and successful jobs will be returned

          **kwargs : Any keyword option from `get_jobs`. You may
                     consider `fmt` and other useful options.

    Returns
    -------
    Collection (possibly, empty) of jobs in the selected format

    Notes
    -----
    This function is a wrapper on `get_jobs` so you can use options
    from that function as arguments here. The arguments `exp_name`,
    `components` and `exp_times` are expanded to a set of tags and
    passed to `get_jobs`. That's why you are strongly discouraged from
    passing `tags` as an option to this function.
    You can combine `components` and `exp_times`. This will use a
    cross-product of the two in terms of acceptable tags.

    Examples
    --------
    >>> exp.exp_find_jobs('ESM4_historical_D151', components=['ocean_annual_rho2_1x1deg', 'ocean_cobalt_fdet_100'], exp_times=['18540101', '18840101'], failed = False)
    ['685000', '685003']
    '''
    if 'tags' in kwargs:
        logger.warning('If you use the "tags" option then "exp_name", "components" and "exp_time" options will be ignored')
    else:
        # create tags using exp_name and components
        tags = [ { 'exp_name': exp_name, 'exp_component' : c } for c in components ] if components else [ { 'exp_name': exp_name } ]
        # expand exp_times into the tag dictionaries
        if exp_times:
            _tags = []
            for tag in tags:
                _tags.extend([ dict(tag, exp_time = str(t)) for t in exp_times ])
            tags = _tags
        kwargs['tags'] = tags


    if failed is not None:
        # create a filter with exitcode, but first check the user isn't
        # using the fltr keyword themselves!
        if 'fltr' in kwargs:
            raise ValueError("You cannot use the 'fltr' option in conjunction with 'failed'")
        # pony and sqlalchemy have different syntax for filters
        if settings.orm == 'sqlalchemy':
            from orm import Job
            kwargs['fltr'] = (Job.exitcode != 0) if failed else (Job.exitcode == 0)
        else:
            # pony
            kwargs['fltr'] = (lambda j: j.exitcode != 0) if failed else (lambda j: j.exitcode == 0)


    # if fmt is not set use fmt default as 'terse'
    out_fmt = kwargs.get('fmt', 'terse')
    if 'fmt' in kwargs:
        del kwargs['fmt']
    return eq.get_jobs(**kwargs, fmt=out_fmt)
