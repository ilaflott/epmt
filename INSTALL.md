# EPMT Installation Guide

The software contained in this repository was written by Philip Mucci of Minimal Metrics LLC.

## Let's go!

Before you start:

```
$ mkdir build
$ cd build/
$ git clone https://<user>@bitbucket.org/minimalmetrics/epmt.git
```

## Requirements

A basic Linux (or container image) with:

* 	python (2.6 or higher)
*  pip (python-pip)
* 	gcc
* git 

For a stock Ubuntu 16.04 box:

```
$ apt-get update
$ apt-get install -y python python-pip git gcc 

```

### System settings

For detailed hardware and software performance metrics to collected by non-privileged users, the following setting must be verified/modified:

```
 # A value of 3 means the system is totally disabled
 $ cat /proc/sys/kernel/perf_event_paranoid
 3 
 $ # Allow root and non-root users to use the perf subsystem
 $ echo 1 > /proc/sys/kernel/perf_event_paranoid 
 1
```

This isn't necessary unless one would like to collect metrics exposed by [PAPI](http://icl.utk.edu/papi/), [libpfm](http://perfmon2.sourceforge.net/) and the [perfevent](http://web.eece.maine.edu/~vweaver/projects/perf_events/) subsystems. But collecting this data is, after all, the entire point of this tool. See [Stack Overflow](https://stackoverflow.com/questions/51911368/what-restriction-is-perf-event-paranoid-1-actually-putting-on-x86-perf) for a discussion of the setting. A setting of 1 is perfectly safe for production systems.

### Data Collection Libraries (aka papiex)

```
$ git clone https://bitbucket.org/minimalmetrics/papiex-oss.git -b papiex-epmt
Cloning into 'papiex-oss'...
remote: Counting objects: 5274, done.
remote: Compressing objects: 100% (3273/3273), done.
remote: Total 5274 (delta 2964), reused 3986 (delta 1909)
Receiving objects: 100% (5274/5274), 8.54 MiB | 1.70 MiB/s, done.
Resolving deltas: 100% (2964/2964), done.
Checking connectivity... done.
$ cd papiex-oss/
$ make
```

Run the tests and examine any failures. *Some may be SKIPPED if the target binary cannot be found*.

```
$ make check
cd papiex; make PREFIX=/build/papiex-oss/papiex-oss-install LIBPAPIEX=/build/papiex-oss/papiex-oss-install/lib/libpapiex.so check
make[1]: Entering directory '/build/papiex-oss/papiex'
make -C /build/papiex-oss/papiex/x86_64-Linux -f /build/papiex-oss/papiex/src/Makefile check
make[2]: Entering directory '/build/papiex-oss/papiex/x86_64-Linux'
cp -Rp /build/papiex-oss/papiex/src/tests/* /build/papiex-oss/papiex/x86_64-Linux/tests
cd tests; ./test.sh
/build/papiex-oss/papiex-oss-install/bin/monitor-run -i /build/papiex-oss/papiex-oss-install/lib/libpapiex.so
Testing papi with PERF_COUNT_SW_CPU_CLOCK...
/build/papiex-oss/papiex-oss-install/bin/papi_command_line PERF_COUNT_SW_CPU_CLOCK: PASS(0)
0 errors.

Testing tagged runs...
sleep 1: PASS
ps -fade: PASS
host google.com: PASS
echo : | tr ':' '\n': PASS
sed -e s/,//g < /dev/null: PASS
tcsh -f module-test.csh: PASS
bash --noprofile -c 'sleep 1': PASS
tcsh -f -c 'sleep 1': PASS
csh -f -c 'sleep 1': PASS
tcsh -f evilcsh.csh: PASS
csh -f evilcsh.csh: PASS
bash --noprofile sieve.sh 100: PASS
tcsh -f sieve.csh 100: PASS
csh -f sieve.csh 100: PASS
python sieve.py: PASS
perl sieve.pl: PASS
gcc -Wall unit1.c -o unit1a: PASS
gcc -pthread dotprod_mutex.c -o dotprod_mutex: PASS
g++ -fopenmp md_openmp.cpp -o md_openmp: PASS
gfortran -fopenmp fft_openmp.f90 -o fft_openmp: PASS
./unit1a: PASS
./dotprod_mutex: PASS
./md_openmp: PASS
./fft_openmp: PASS
0 errors.
```

The collection agent is now installed in the **papiex-oss-install** directory.

```
$ ls papiex-oss-install/
bin  include  lib  share  tmp
```

### EPMT installation

As there is no virtual environment at the moment, the source tree should be copied to the default machines. Here we use ```build/epmt``` as our source dir.

There are three modes to **EPMT** usage, collection, submission and analysis:

* **Collection** only requires minimal Python installation of 2.6.x or higher
* **Submission** requires python packages for data and database interaction
* **Analysis** requires [Jupyter](https://jupyter.org), an iPython notebook environment, as well as additional python data analysis libraries.   

First we run the basic **collection** tests:

```
$ cd ../epmt
$ make check
make[1]: Entering directory '/build/epmt'
PAPIEX_OUTPUT=/build/epmt  python -m py_compile *.py models/*.py         # Compile everything
PAPIEX_OUTPUT=/build/epmt  ./epmt -h >/dev/null      # help path 1
PAPIEX_OUTPUT=/build/epmt  ./epmt help >/dev/null    # help path 2
PAPIEX_OUTPUT=/build/epmt  ./epmt start           # Generate prolog
.
.
.
job_pl_start            2019-03-06 15:29:35.706748                              
job_pl_submit           2019-03-06 15:29:35.706804                              
job_pl_username         root                                                    
PAPIEX_OUTPUT=/build/epmt  ./epmt -n submit       # Submit
Python 2.7.12
Tests pass! 
```

All three modes reference the **settings.py** file as well as **environment variables**. The shipped version uses a in-memory, ephemeral database for testing. 

```
$ cat settings.py
db_params = {'provider': 'sqlite', 'filename': ':memory:'}
papiex_options = "PERF_COUNT_SW_CPU_CLOCK"
papiex_output = "/tmp/epmt/"
debug = False
input_pattern = "*-papiex-[0-9]*-[0-9]*.csv"
install_prefix = "../papiex-oss/papiex-oss-install/"
# DO NOT TOUCH THIS
metrics_offset = 12
```

Let's collect some data on an interactive run and treat it as an entire job (using **--a**). 

```
$ ./epmt -a run sleep 10
$ ls /tmp/epmt/1/
job_metadata  linuxkit-025000000001-papiex-14346-0.csv
```

In order to submit data to the database, we need to install the dependencies. It is recommended that one use the Docker image which contains all the dependencies and **requires no user setup**. However, one may install these in a Python virtual environment, to the system Python or the user's local repository, using **pip install** as below:

```
$ cat requirements.txt
pandas==0.17.1
pony==0.7.6
psycopg2-binary==2.7.5
$ pip install --user -r requirements.txt
```

Now we can submit:

```
$ ./epmt -v submit /tmp/epmt/1/
INFO:epmt_cmds:submit_to_db(/tmp/epmt/1/,*-papiex-[0-9]*-[0-9]*.csv,False)
INFO:epmt_cmds:Unpickling from /tmp/epmt/1/job_metadata
INFO:epmt_cmds:1 files to submit
INFO:epmt_cmds:1 hosts found: ['linuxkit-025000000001-']
INFO:epmt_cmds:host linuxkit-025000000001-: 1 files to import
INFO:epmt_job:Binding to DB: {'filename': ':memory:', 'provider': 'sqlite'}
INFO:epmt_job:Generating mapping from schema...
INFO:epmt_job:Processing job id 1
INFO:epmt_job:Creating user root
INFO:epmt_job:Creating job 1
INFO:epmt_job:Creating host linuxkit-025000000001-
INFO:epmt_job:Creating metricname usertime
INFO:epmt_job:Creating metricname systemtime
INFO:epmt_job:Creating metricname rssmax
INFO:epmt_job:Creating metricname minflt
INFO:epmt_job:Creating metricname majflt
INFO:epmt_job:Creating metricname inblock
INFO:epmt_job:Creating metricname outblock
INFO:epmt_job:Creating metricname vol_ctxsw
INFO:epmt_job:Creating metricname invol_ctxsw
INFO:epmt_job:Creating metricname num_threads
INFO:epmt_job:Creating metricname starttime
INFO:epmt_job:Creating metricname processor
INFO:epmt_job:Creating metricname delayacct_blkio_time
INFO:epmt_job:Creating metricname guest_time
INFO:epmt_job:Creating metricname rchar
INFO:epmt_job:Creating metricname wchar
INFO:epmt_job:Creating metricname syscr
INFO:epmt_job:Creating metricname syscw
INFO:epmt_job:Creating metricname read_bytes
INFO:epmt_job:Creating metricname write_bytes
INFO:epmt_job:Creating metricname cancelled_write_bytes
INFO:epmt_job:Creating metricname time_oncpu
INFO:epmt_job:Creating metricname time_waiting
INFO:epmt_job:Creating metricname timeslices
INFO:epmt_job:Creating metricname rdtsc_duration
INFO:epmt_job:Creating metricname PERF_COUNT_SW_CPU_CLOCK
INFO:epmt_job:Adding 1 processes to job
INFO:epmt_job:Earliest process start: 2019-03-06 15:36:56.948350
INFO:epmt_job:Latest process end: 2019-03-06 15:37:06.996065
INFO:epmt_job:Computed duration of job: 10047715.000000 us, 0.17 m
INFO:epmt_job:Staged import of 1 processes, 1 threads
INFO:epmt_job:Staged import took 0:00:00.189151, 5.286781 processes per second
INFO:epmt_cmds:Committed job 1 to database: Job[u'1']
```

If you've made it this far, you are ready to configure a real database.


## Start the Database Services

If you do not have a postgres database daemon installed and running, it's easiest to use the provided Docker Compose recipe for both the database and the administrative interface:

```
$ docker-compose up adminer db
$ docker-compose ps
     Name                   Command               State           Ports         
--------------------------------------------------------------------------------
epmt_adminer_1   entrypoint.sh docker-php-e ...   Up      0.0.0.0:8080->8080/tcp
epmt_db_1        docker-entrypoint.sh postgres    Up      0.0.0.0:5432->5432/tcp
```

These services will export the following ports:

* 8080 for **Adminer**, the DB administration interface
* 5432 for **PostGresQL**

After these are running, one can examine the database using the provided **Adminer** console: [http://localhost:8080/?pgsql=db&username=postgres&db=EPMT&ns=public](). 

### Configuring a Database

There is a prebuilt settings.py file to connect to the localhost.

```
$ rm settings.py settings.pyc
$ ln -s settings/settings_pg_localhost.py settings.py
$ grep db_params settings.py
db_params = {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'localhost', 'dbname': 'EPMT'}

```

The database is ready to go.

### Database Container and Storage onfiguration

Persistent data and config present in **./data/postgres**. See the below **docker-compose.yml** file:

```
db:
    image: postgres
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: example
      POSTGRES_DB: EPMT
    ports:
      - 5432:5432
```

Postgres will self-provision if the above database and user are not found.  One could run it directly from the command line using **docker**.

```
docker run --name postgres -v ./data/postgres:/var/lib/postgresql/data -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=example -e POSTGRES_DB=EPMT -d postgres:latest
```

See [https://hub.docker.com/_/postgres/]() for documentation of the parameters of the image.
 
### Dropping and Recreating Database 

You can do this with the provided **Adminer** console: [http://localhost:8080/?pgsql=db&username=postgres]() or via the command line with **psql**. 

```
$ sudo su - postgres
$ psql -c "create database EPMT"
```

## Analysis and Visualization with Jupyter

For this, we need to build the container images. In the source tree:

```
$ make
.
.
.
$ docker images
REPOSITORY               TAG                 IMAGE ID            CREATED              SIZE
epmt-notebook            latest              045023fc0ccc        About a minute ago   4.3GB
epmt-command             latest              530fe3198a1d        About a minute ago   1.1GB
python-epmt              latest              5b99ede4828d        About a minute ago   1.1GB
```

In the source tree:

```
$ docker-compose up notebook
Creating epmt_notebook_1 ... done
Attaching to epmt_notebook_1
notebook_1  | Executing the command: jupyter notebook
notebook_1  | [I 16:21:22.330 NotebookApp] JupyterLab extension loaded from /opt/conda/lib/python3.6/site-packages/jupyterlab
notebook_1  | [I 16:21:22.330 NotebookApp] JupyterLab application directory is /opt/conda/share/jupyter/lab
notebook_1  | [I 16:21:22.332 NotebookApp] Serving notebooks from local directory: /home/jovyan
notebook_1  | [I 16:21:22.333 NotebookApp] The Jupyter Notebook is running at:
notebook_1  | [I 16:21:22.333 NotebookApp] http://(9a7974f0ffb9 or 127.0.0.1):8888/?token=c9d7cb543a82a7a278197b874c789da99a7ed91cd2f84016
notebook_1  | [I 16:21:22.333 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
notebook_1  | [C 16:21:22.339 NotebookApp] 
notebook_1  |     
notebook_1  |     Copy/paste this URL into your browser when you connect for the first time,
notebook_1  |     to login with a token:
notebook_1  |         http://(9a7974f0ffb9 or 127.0.0.1):8888/?token=c9d7cb543a82a7a278197b874c789da99a7ed91cd2f84016
```

and then load and execute the **EPMT.ipynb** file.

## Docker Images for the EPMT command

The make builds the various **EPMT** images. The image **epmt-command** is the image that contains a working **EPMT** and all it's dependencies. It's mean to be run as a command with arguments via **docker run**.

## Testing EPMT Collection with Various Python Versions under Docker

One can test **EPMT** on various versions of python with the following make commands. Each will test against a minimal install of Python, without installing any dependencies. This should work for **start, stop, dump, help and submit, the latter with -n or --dry-run**. 

```
make check-python-native
make check-python-2.6
make check-python-2.7
make check-python-3
```









