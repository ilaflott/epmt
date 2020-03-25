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
    time_seg_dict = {}
    for j in exp_jobs:
        m = getattr(j, metric)
        exp_time = j.tags.get('exp_time', '')
        if not exp_time: continue
        m_total = time_seg_dict.get(exp_time, 0)
        m_total += m
        time_seg_dict[exp_time] = m_total
    inp_vec = []
    for t in sorted(list(time_seg_dict.keys())):
        inp_vec.append(time_seg_dict[t])
    if inp_vec:
        out_vec = np.abs(es.modified_z_score(inp_vec)[0]) > settings.outlier_thresholds['modified_z_score']
        print('{} by time segment:'.format(metric))
        idx = 0
        for t in sorted(list(time_seg_dict.keys())):
            print("%12s %16d %4s" % (t, time_seg_dict[t], "****" if out_vec[idx] else ""))
            idx += 1
    return True

