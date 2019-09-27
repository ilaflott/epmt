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

    def __init__(self, jobs, tag):
        from epmt_query import get_procs
        from orm import orm_is_query
        if (orm_is_query(jobs) and jobs.count() == 0) or (len(jobs) == 0):
            raise ValueError("jobs count should be greater than zero")
        self.jobs = jobs
        self.tag = tag
        self.processes = get_procs(jobs = jobs, tags = tag, fmt='orm')
        if self.processes.count() == 0:
            logger.warning("operation contains no processes!")
            (self.first_run_start, self.last_run_end) = (None, None)
        else:
            self.first_run_start = min(p.start for p in self.processes)
            self.last_run_end = max(p.end for p in self.processes)
        # this will be initialized on first reference
        self._proc_sums = None
        self._intervals = None
        self._duration = None


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
        from epmt_query import get_op_metrics
        if self._proc_sums is None: 
            op_metrics = get_op_metrics(jobs = self.jobs, tags = self.tag, exact_tags_only = False, group_by_tag=True, fmt='dict')
            assert(len(op_metrics) == 1)
            self._proc_sums = op_metrics[0]
        return self._proc_sums
