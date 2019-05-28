# without extracting the .tgz
Did 2000 of 46237...22.32/sec  (without any optimization)
Did 2000 of 46237...24.95/sec  (metrics json in thread object)


# after extracting tgz
Did 1000 of 46237...92.88/sec (without any optimization)
Did 1000 of 46237...113.94/sec (metrics json in thread object)


It's clear that .tgz extraction is critial for performance. So we will
only deal with that case below.

load_process_from_pandas takes 61% less time by folding metrics
into Thread object. The optimized case has a breakup of time as:
72% -> read_csv
23% -> load_process_from_pandas

So any further optimization with the object model will have
limited (under 20%) gains performance-wise.

After putting threads dataframe into the process
and skipping creating Thread objects, we get:
INFO:epmt_job:Did 1000 of 46237...121.73/sec 

