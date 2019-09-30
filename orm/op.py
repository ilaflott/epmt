class Operation(dict):
    '''
    Defines an abstract model for an operation. This will
    NOT be persisted in the database.

    An operation is defined as a collection of processes
    spanning one or more jobs where each processes' tag is
    a superset of the operation tag.
    '''


    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, jobs, tag, exact_tag_only = False):
        from epmt_query import get_procs
        from orm import orm_is_query
        from epmtlib import tag_from_string, tags_list
        if (orm_is_query(jobs) and jobs.count() == 0) or (len(jobs) == 0):
            raise ValueError("jobs count should be greater than zero")
        self.jobs = jobs
        self.tag = tags_list(tag) if (type(tag) == list) else tag_from_string(tag)
        self.processes = get_procs(jobs = jobs, tags = tag, exact_tag_only = exact_tag_only, fmt='orm')
        if len(self.processes[:]) == 0:
            from logging import getLogger
            logger = getLogger(__name__)
            logger.warning("No processes found for operation -- {0}".format(tag))
            return None
        else:
            self.start = min(p.start for p in self.processes)
            self.end = max(p.end for p in self.processes)

        # this will be initialized on first reference
        self._proc_sums = None
        self._intervals = None
        self._duration = None

    def contiguous(self):
        return (len(self.intervals) == 1)

    def num_runs(self):
        return len(self.intervals)

    @property
    def intervals(self):
        '''
        Returns a list of non-overlapping intervals for an operation
        '''
        from epmtlib import merge_intervals
        if self._intervals is None: 
            _intervals = [[p.start, p.end] for p in self.processes]
            _mi = merge_intervals(_intervals)
            self._intervals = tuple([tuple(i) for i in _mi])
        return self._intervals

    @property
    def duration(self):
        if self._duration is None:
            self._duration = sum([(interval[-1] - interval[0]).total_seconds() for interval in self.intervals]) * 1e6
        return self._duration
            

    @property
    def proc_sums(self):
        if self._proc_sums is None: 
            from epmt_query import get_op_metrics
            from epmtlib import sum_dicts_list
            op_metrics = get_op_metrics(jobs = self.jobs, tags = self.tag, exact_tags_only = False, group_by_tag=True, fmt='dict')
            if type(self.tag) == list:
                assert(len(op_metrics) == len(self.tag))
            else:
                assert(len(op_metrics) == 1)
            self._proc_sums = sum_dicts_list(op_metrics, exclude = ['tags'])
        return self._proc_sums

    def to_dict(self):
        (duration, intervals, proc_sums) = (self.duration, self.intervals, self.proc_sums)
        d = dict(self)
        d['duration'] = duration
        d['intervals'] = intervals
        d['proc_sums'] = proc_sums
        d['processes'] = self.processes[:]
        d['contiguous'] = (len(intervals) == 1)
        d['num_runs'] = len(intervals) 
        for attr in ('_duration', '_intervals', '_proc_sums'): del d[attr]
        return d
