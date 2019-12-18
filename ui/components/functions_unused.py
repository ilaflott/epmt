def str_time_prop(start, end, format):
    """Get a time at a proportion of a range of two formatted times.

    start and end should be strings specifying times formated in the
    given format (strftime-style), giving an interval [start, end].
    prop specifies how a proportion of the interval to be taken after
    start.  The returned time will be in the specified format.
    """

    stime = time.mktime(time.strptime(start, format))
    etime = time.mktime(time.strptime(end, format))

    ptime = stime + random.random() * (etime - stime)

    return time.strftime(format, time.localtime(ptime))


def random_date(start, end, dfmt):
    return str_time_prop(start, end, dfmt)
# Generate Random time,zone
# random_date("1:30 PM UTC", "4:50 PM UTC", "%I:%M %p %Z", random.random())
# Generate Random Date,time,zone
# random_date("1/1/1990 1:30 PM UTC", "1/2/1990 4:50 PM UTC", "%m/%d/%Y %I:%M %p %Z", random.random())


def _unused_random_job_generator(x):
    # Old tags
    tags = {'atm_res': 'c96l49',
            'ocn_res': '0.5l75',
            'exp_name': 'ESM4_historical_D151',
            'exp_time': '18640101',
            'script_name': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18640101',
            'exp_component': 'ocean_annual_rho2_1x1deg'}
    result = []
    for n in range(x):
        jobid = "job-" + str(n)
        import names
        job_name = names.name_gen().name
        Processed = bool(random.getrandbits(1))
        tag = dict(tags) if bool(random.getrandbits(1)) else {'Tags': 'None'}
        timeformat = "%m/%d/%Y %I:%M %p %Z"
        start_datetime = random_date(
            "11/1/2019 1:30 PM UTC", "11/5/2019 4:50 PM UTC", timeformat)  # + timedelta(days=n)
        from datetime import datetime
        start_time = datetime.strptime(start_datetime, timeformat).time()
        start_day = datetime.strptime(start_datetime, timeformat).date()
        usert = random.randrange(0, 8640000 * 0.5)
        systemt = random.randrange(0, 8640000 * 0.5)
        cput = usert + systemt
        # 8640000 jiffies in 24 hours
        duration = random.uniform(cput, cput * 1.3)
        exit_code = int(1) if bool(random.random() < 0.3) else int(0)
        result.append([jobid, job_name, Processed, tag, start_day, start_time,
                       # Exit code, duration, user, system
                       exit_code, duration, usert, systemt, cput,
                       # Bytes in, Bytes out
                       random.randrange(0, 1024**4), random.randrange(0, 1024**4)])
    return result

    def reset(self):
        self.__init__()