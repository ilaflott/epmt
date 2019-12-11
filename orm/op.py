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

    # op_duration_method is one of "sum", "sum-minus-overlap", "finish-minus-start"
    def __init__(self, jobs, tags, exact_tag_only = False, op_duration_method = "sum"):
        from orm import orm_is_query, orm_jobs_col
        from epmtlib import tag_from_string, tags_list
        from logging import getLogger
        logger = getLogger(__name__)
        if op_duration_method not in ("sum", "sum-minus-overlap", "finish-minus-start"):
            raise ValueError('op_duration_method must be one of ("sum", "sum-minus-overlap", "finish-minus-start")')
        jobs = orm_jobs_col(jobs)
        if (jobs.count() == 0):
            raise ValueError("jobs count should be greater than zero")
        self.jobs = jobs
        self.tags = tags_list(tags) if (type(tags) == list) else tag_from_string(tags)
        self.exact_tag_only = exact_tag_only
        self.op_duration_method = op_duration_method
        # this will be initialized on first reference
        self._processes = None
        self._proc_sums = None
        self._intervals = None
        self._duration = None
        self._start = None
        self._finish = None

    def contiguous(self):
        return (len(self.intervals) == 1)

    def num_runs(self):
        return len(self.intervals)

    @property
    def start(self):
        if self._start is None:
            self._start = min([p.start for p in self.processes])
        return self._start


    @property
    def finish(self):
        if self._finish is None:
            self._finish = max([p.end for p in self.processes])
        return self._finish


    @property
    def processes(self):
        if self._processes is None:
            from logging import getLogger
            from epmt_query import get_procs
            logger = getLogger(__name__)
            logger.debug('computing op processes..')
            self._processes = get_procs(jobs = self.jobs, tags = self.tags, exact_tag_only = self.exact_tag_only, fmt='orm')
            if len(self._processes[:]) == 0:
                logger.warning("No processes found for operation -- {0}".format(self.tags))
            # else:
            #     logger.debug('computing op start/end times..')
            #     self.start = min(p.start for p in self.processes)
            #     self.end = max(p.end for p in self.processes)
        return self._processes


    @property
    def intervals(self):
        '''
        Returns a list of non-overlapping intervals for an operation
        '''
        from epmtlib import merge_intervals
        if self._intervals is None:
            from logging import getLogger
            logger = getLogger(__name__)
            logger.debug('computing operation intervals..') 
            _intervals = [[p.start, p.end] for p in self.processes]
            logger.debug('merging operation intervals..') 
            _mi = merge_intervals(_intervals)
            self._intervals = tuple([tuple(i) for i in _mi])
        return self._intervals

    @property
    def duration(self):
        if self._duration is None:
            if self.op_duration_method == "sum":
                from datetime import timedelta
                self._duration = timedelta(0)
                for p in self.processes:
                    self._duration += (p.end - p.start)
                self._duration = round(self._duration.total_seconds() * 1e6, 1)
            elif self.op_duration_method == "sum-minus-overlap":
                # self.intervals is a sorted list of tuples
                self._duration = round(sum([(interval[-1] - interval[0]).total_seconds() for interval in self.intervals]) * 1e6, 1)
            elif self.op_duration_method == "finish-minus-start":
                self._duration = round((self.finish - self.start).total_seconds() * 1e6, 1)
            else:
                raise ValueError("Do not know how to handle op_duration_method: {}".format(self.op_duration_method))
        return self._duration
            

    @property
    def proc_sums(self):
        if self._proc_sums is None: 
            from epmt_query import get_op_metrics
            from epmtlib import sum_dicts_list
            from logging import getLogger
            logger = getLogger(__name__)
            logger.debug('getting op_metrics for jobs={0}, tags={1}'.format(self.jobs, self.tags))
            op_metrics = get_op_metrics(jobs = self.jobs, tags = self.tags, exact_tags_only = False, group_by_tag=True, fmt='dict')
            if type(self.tags) == list:
                assert(len(op_metrics) == len(self.tags))
            else:
                assert(len(op_metrics) == 1)
            self._proc_sums = sum_dicts_list(op_metrics, exclude = ['tags'])
            # use duration as calculated by us
            self._proc_sums['duration'] = self.duration
        return self._proc_sums

    def to_dict(self, full = False):
        d = dict(self)
        d['jobs'] = self.jobs[:]
        d['duration'] = self.duration
        d['proc_sums'] = self.proc_sums
        d['processes'] = self.processes[:]
        d['start'] = self.start
        d['finish'] = self.finish
        if full:
            d['intervals'] = self.intervals
            d['contiguous'] = (len(self.intervals) == 1)
            d['num_runs'] = len(self.intervals) 
        for attr in ('_duration', '_start', '_finish', '_intervals', '_proc_sums', '_processes'): del d[attr]
        return d
