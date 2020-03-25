from orm import db_session
import epmt_query as eq
import numpy as np
import epmt_settings as settings
import epmt_stat as es

@db_session
def exp_explore(exp_name, metric = 'duration', op = np.sum, limit=10):
    from scipy.stats import variation

    metric = metric or 'duration' # defaults when using with command-line
    limit = limit or 10 # defaults when using with command-line
    
    exp_jobs = eq.get_jobs(tags = { 'exp_name': exp_name }, fmt = 'orm' )
    ordered_comp_list = eq.exp_comp_stats(exp_name, metric, op, limit)

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
    od = eq.exp_time_segment_stats(exp_name, metric)
    time_segments = list(od.keys())
    metric_sums = [np.sum(od[t]['metrics']) for t in time_segments]
    outlier_scores = es.outliers_uv(metric_sums)
    print('{} by time segment:'.format(metric))
    for idx in range(len(time_segments)):
        print("%12s %16d %6s" % (time_segments[idx], metric_sums[idx], "**" * int(outlier_scores[idx])))
    return True

