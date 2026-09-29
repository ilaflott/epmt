#!/usr/bin/env python3
'''
CLI entry-point for the epmt package.

This module provides the ``main()`` function used by the
``[project.scripts]`` console-script entry point declared in
``pyproject.toml``.  The legacy ``scripts/epmt`` wrapper delegates
here as well, so both invocation paths share the same code.
'''

import argparse
from io import StringIO
from sys import exit as sysexit
from sys import stderr, argv

import epmt.epmt_settings as settings

from epmt.epmt_cmds import epmt_entrypoint, dump_config
from epmt.epmt_cmd_help import epmt_help_api
from epmt.epmtlib import version_str, suggested_cpu_count_for_submit


class DefaultHelpParser(argparse.ArgumentParser):
    '''
    Class for displaying help when errors occur without dump_config
    '''
    def error(self, message):
        stderr.write(f'error: {message}\n')
        self.epilog = ''
        self.print_help()
        sysexit(2)


def main():
    '''
    primary functional bottleneck for all CLI commands, leading to epmt_cmds.epmt_entrypoint
    '''
    # Generate config variable for epilog on long help
    config_string_file = StringIO()
    dump_config(config_string_file)

    # PARSER base is a default help parser
    parser = DefaultHelpParser(
        prog='epmt',
        add_help=True, epilog=config_string_file.getvalue(),
        description="This is a tool to collect metadata and performance data about an entire job- "
        "down to the individual threads in individual processes. "
        "This tool, EPMT, uses papiex to perform the process monitoring. "
        "It is targeted at batch or ephemeral jobs, not daemon processes.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '-V', '--version',
        action='version', version=version_str(),
        help="Display EPMT Version")
    parser.add_argument(
        '-v', '--verbose',
        action='count', default=0,
        help="Increase level of verbosity/debug")

    # SUBPARSER is generic for command parsers below
    subparser = parser.add_subparsers(
        title="EPMT Commands",
        dest="command")

    # Source PARSER
    source_parser = subparser.add_parser(
        'source',
        help="Enable instrumentation of subsequent shell commands",
        formatter_class=argparse.RawTextHelpFormatter,
        description="Source provides commands to begin automatic performance instrumentation of all\n"
        "subsequent shell commands. Standard use of this is via the shell's eval method\n"
        "inside job scripts or batch system wrappers. For example:\n\n"
        "\teval `epmt source` in Bash or Csh\n"
        "\teval `epmt source --slurm` for a SLURM prolog.\n\n"
        "Two shell functions/aliases are created to pause/restart instrumentation:\n\n"
        "\tepmt_uninstrument - to pause automatic instrumentation\n"
        "\tepmt_instrument - to re-enable automatic instruction.\n\n\n"
        "**SLURM USERS NOTE** Use in SLURM's prolog, requires a special syntax\n"
        "enabled here with the -s or --slurm option. For more info, see:\n"
        "https://slurm.schedmd.com/prolog_epilog.html")
    source_parser.add_argument(
        '-s', '--slurm',
        action='store_true',
        help="Generate shell code for a SLURM prolog, https://slurm.schedmd.com/prolog_epilog.html")

    # Start PARSER
    start_parser = subparser.add_parser(
        'start',
        help="Begin EPMT job data collection",
        description="Start creates directory and metadata file for data collection of a job.")
    start_parser.add_argument(
        '-e', '--error',
        action='store_true',
        help="Exit at the first sign of trouble")
    start_parser.set_defaults(epmt_cmd_args=None)

    # Stage PARSER
    stage_parser = subparser.add_parser(
        'stage',
        help="Generate job archive",
        description="Stage will compress job or job directories into tgz files for midterm storage then remove "
        "original job files and job directory.")
    stage_parser.add_argument(
        'epmt_cmd_args',
        nargs='*',
        help="List of directories", metavar="job_dirs")
    stage_parser.add_argument(
        '-e', '--error',
        action='store_true',
        help="Exit at the first sign of trouble")
    stage_parser.add_argument(
        '--no-collate',
        action='store_true',
        help="Don't collate the files")
    stage_parser.add_argument(
        '--no-compress-and-tar',
        action='store_true',
        help="Don't compress and tar the output")

    # Annotate PARSER
    annotate_parser = subparser.add_parser(
        'annotate',
        help="Annotate a job",
        formatter_class=argparse.RawTextHelpFormatter,
        description="Annotates a job with key/value pairs. This call takes three forms:\n\n"
        "To annotate a stopped job within the batch environment: \n"
        "\tepmt annotate x=100 y=200\n\n"
        "To annotate a stage .tgz file:\n"
        "\tepmt annotate 111.tgz x=100 y=200\n\n"
        "To annotate an existing job in the database:\n"
        "\tepmt annotate 685000 x=100 y=200\n\n"
        "In all the above cases the annotations are *merged* on to the existing annotations, unless "
        "--replace is set (in which case existing annotations are removed first)")
    annotate_parser.add_argument(
        'epmt_cmd_args',
        nargs='+',
        help="key/value pairs in the form key1=value1 key2=value2..",
        metavar="kv_pair")
    annotate_parser.add_argument(
        '--replace',
        action='store_true', default=False,
        help="Replace existing annotations instead of merging onto them")

    # Dump PARSER
    dump_parser = subparser.add_parser(
        'dump',
        help="Print job metadata from archive or database",
        description="Dump will print to console the metadata of a job directory, job archive or a job in the database")
    dump_parser.add_argument(
        'epmt_cmd_args',
        default=[], nargs='*',
        help="Archive or list of archives to dump from file-system, or a list of jobids from database",
        metavar="job_dir_file_or_id")
    dump_parser.add_argument(
        '-k', '--key',
        help="Only dump the value for the specified key")

    # Schema PARSER
    subparser.add_parser(
        'schema',
        help="Dump the database schema",
        description="schema will dump the database schema")

    # Migrate PARSER
    subparser.add_parser(
        'migrate',
        help="Migrate the database schema",
        description="Migrate the database schema (if needed). Safe to use this option on an already migrated database")

    # Convert PARSER
    csv_convert_parser = subparser.add_parser(
        'convert',
        help="Convert csv from v1 to v2 format",
        description="Convert will convert the CSV files inside a .tgz staged file from v1 to v2 format")
    csv_convert_parser.add_argument(
        'src_tgz',
        action="store",
        help="Source tgz file. Specify dest_tgz to avoid overwriting src_tgz")
    csv_convert_parser.add_argument(
        'dest_tgz',
        action="store", nargs='?',
        help="Optional output tgz file to create. If unspecified, src_tgz is overwritten")

    # Run PARSER
    run_parser = subparser.add_parser(
        'run',
        help="Execute a process",
        description="Run will execute a command in the shell, typically used with the auto -a flag to perform metadata "
        "collection before and after instrumentation.")
    run_parser.add_argument(
        '-a', '--auto',
        action='store_true',
        help="Perform epmt start/epmt stop before/after running")
    run_parser.add_argument(
        '-n', '--dry-run', action='store_true',
        help="Don't execute anything, just show the commands")
    run_parser.add_argument(
        'epmt_cmd_args',
        default=[], nargs='+',
        help="Command to run, **must** be preceded with double dash followed by a space if options are used, "
        "i.e. epmt run -- ls -C ",
        metavar="cmd_line")
    run_parser.set_defaults(dry_run=False, wrapit=False)

    # Stop PARSER
    stop_parser = subparser.add_parser(
        'stop',
        help="Stop EPMT job data collection",
        description="Stop appends additional metadata created during start at job finish time.")
    stop_parser.add_argument(
        '-e', '--error',
        action='store_true',
        help="Exit at the first sign of trouble")
    stop_parser.set_defaults(epmt_cmd_args=None)

    # Daemon PARSER
    daemon_parser = subparser.add_parser(
        'daemon',
        help="Run the EPMT daemon",
        description="daemon runs an EPMT daemon that will periodically perform certain actions")
    daemon_parser.add_argument(
        '-i', '--ingest',
        nargs='?', default=False, const=settings.stage_command_dest,
        metavar='path',
        help="path to monitor for incoming data. If no path specified, the staging destination directory "
        f"({settings.stage_command_dest}) from settings is used")
    daemon_parser.add_argument(
        '-s', '--start',
        action='store_true',
        help="Start the EPMT daemon")
    daemon_parser.add_argument(
        '-S', '--stop',
        action='store_true',
        help="Stop the EPMT daemon")
    daemon_parser.add_argument(
        '-D', '--foreground',
        action='store_true',
        help="Start the daemon in foreground")
    daemon_parser.add_argument(
        '--post-process',
        action='store_true',
        help="Perform post-processing and analysis on unprocessed jobs")
    daemon_parser.add_argument(
        '--no-analyze',
        action='store_true',
        help="Do not perform analyses on unprocessed jobs, requires --post-process")
    daemon_parser.add_argument(
        '--retire',
        action='store_true',
        help="Perform data retirement based on the retention policy in settings")
    daemon_parser.add_argument(
        '-k', '--keep',
        default=False, action='store_true',
        help='Keep files after successful ingest. Only meaningful with --ingest')
    daemon_parser.add_argument(
        '-m', '--move-away',
        default=True, action='store_true',
        help='Move away files on failed ingest. Only meaningful with --ingest')
    daemon_parser.add_argument(
        '-r', '--recursive',
        default=False, action='store_true',
        help='Recurse into sub-directories to find staged files. Only meaningful with --ingest')
    daemon_parser.set_defaults(
        start_daemon=False, stop_daemon=False,
        foreground=False, post_process=False,
        no_analyze=False, retire=False)

    # Gui PARSER
    subparser.add_parser(
        'gui',
        help="Run the EPMT dashboard GUI",
        description="gui a web-based dashboard accessible at: http://localhost:8050")

    # Drop PARSER
    drop_parser = subparser.add_parser(
        'drop',
        help="Drop the entire database, Caution!! Irreversible!")
    drop_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help="Do not prompt to confirm")

    # DBcare PARSER
    dbcare_parser = subparser.add_parser(
        'dbcare',
        help="retire proc'd jobs, then vacuum db tables, then postproc unproc'd jobs",
        description="it will not retire unprocessed jobs. it vacuums processes and jobs and processes_staging tables")
    dbcare_parser.add_argument(
        '-r', '--retire-jobs',
        default = False, action = 'store_true',
        help='retire jobs.' )
    dbcare_parser.add_argument(
        '--vacuum-tables',
        default = False, action = 'store_true',
        help = 'vacuum db tables for dead rows, leaving them (and assigned ids) re-allocatable')
    dbcare_parser.add_argument(
        '-p', '--post-process',
        default = False, action = 'store_true',
        help = 'postprocess jobs in the DB that are unprocessed (i.e. not associated with entries in processes table)')
    dbcare_parser.add_argument(
        '--time-limit',
        type = float, default = None, metavar = 'MINUTES',
        help = 'time limit in minutes; the command will stop cleanly after this duration')

    # Concat PARSER
    concat_parser = subparser.add_parser(
        'concat',
        help='concatenate CSV files',
        description="Concatenate CSV files. It returns 0 on success and < 0 on error")
    concat_parser.add_argument(
        'files', nargs='+', metavar='FILE',
        help='Two or more CSV files to concatenate OR a directory containing CSV files')
    concat_parser.add_argument(
        '-v', '--verbose',
        action="count",
        default=0,
        help="increase verbosity")
    concat_parser.add_argument(
        '-o', '--output-file',
        help="Name of the output file, determined from input if not specified",
        default='')
    concat_parser.add_argument(
        '-e', '--error',
        action='store_true',
        help="Exit at the first sign of trouble",
        default=False)
    concat_parser.add_argument(
        '-E', '--error-dir',
        help="Name of the directory to save files with errors, disabled if not specified",
        default='')

    # Retire PARSER
    retire_parser = subparser.add_parser(
        'retire', help="Delete jobs/models, retention policy in settings.py")
    retire_parser.add_argument(
        '-n', '--dry-run',
        default=False,
        action='store_true',
        help="Don't touch the database, just report the number of jobs and models that will be retired")
    retire_parser.add_argument(
        '-u', '--skip-unproc',
        default=False,
        action='store_true',
        help="If retire targets a job that hasn't been processed yet, leave that job alone and skip.")
    retire_parser.add_argument(
        '--time-limit',
        type=float, default=None, metavar='MINUTES',
        help='time limit in minutes; the command will stop cleanly after this duration')

    # Submit PARSER
    submit_parser = subparser.add_parser(
        'submit',
        help="Submit/ingest job into database",
        description="Submit accepts job directories and updates the database configured with "
        "directories given.  When run with -n submit will not touch the database and displays the commands leading "
        "up to submission.")
    submit_parser.add_argument(
        'epmt_cmd_args',
        nargs='*',
        help="List of job .tgz files or directories",
        metavar="job_or_dir")
    submit_parser.add_argument(
        '-e', '--error',
        action='store_true',
        help="Exit at the first sign of trouble")
    submit_parser.add_argument(
        '-r', '--remove',
        action='store_true',
        help="Remove the job .tgz on successful ingestion")
    submit_parser.add_argument(
        '-m', '--move-away',
        default=False, action='store_true',
        help='Move away files upon failed ingestion to settings.ingest_failed_dir')
    submit_parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        help="Don't touch the database, but files will still be manipulated")
    submit_parser.add_argument(
        '--drop',
        action='store_true',
        help="Drop all tables/data and recreate before submission")
    OPTIMAL_CPUS = suggested_cpu_count_for_submit()
    submit_parser.add_argument(
        '-p', '--num-cpus',
        type=int, nargs='?', default=1, const=OPTIMAL_CPUS,
        help='Number of parallel processes to use for submission. If specified with no value, then the '
        f'discovered value ({OPTIMAL_CPUS}) will be used.')

    # DBSize PARSER
    dbsize_parser = subparser.add_parser(
        'dbsize',
        help="Find detailed size of database",
        description="Prints the on-disk size of different constructs in the database. Not supported for all databases.")
    dbsize_parser.add_argument(
        'epmt_cmd_args',
        default='all', const='all', nargs='?',
        choices=["all", "database", "table", "index", "tablespace"],
        metavar="dbitem",
        help='%(choices)s')

    # Check PARSER
    subparser.add_parser(
        'check',
        help='Verify EPMT Installation',
        description="Check will verify basic epmt configuration and functionality.")

    # Delete PARSER
    delete_parser = subparser.add_parser(
        'delete',
        help='Delete jobs from the database',
        description="Deletes jobs from the database.")
    delete_parser.add_argument(
        'epmt_cmd_args',
        nargs='+',
        help="job IDs to delete",
        metavar="jobids")

    # List PARSER
    list_parser = subparser.add_parser(
        'list',
        help='Display all jobs in the database',
        description="Display all jobs in the database")
    list_parser.add_argument(
        'epmt_cmd_args',
        nargs='*', metavar="jobids",
        help="Either keyword: jobs, unprocessed_jobs, unanalyzed_jobs, refmodels, procs/processes, "
        "thread_metrics, op_metrics, job_proc_tags or list job IDs to search for")

    # Notebook PARSER
    notebook_parser = subparser.add_parser(
        'notebook',
        help="Start iPython Notebook environment",
        description="Perform programmatic, interactive analyses of EPMT data in iPython")
    notebook_parser.add_argument(
        'epmt_cmd_args',
        default=[], nargs='*', metavar="notebook_args",
        help="Arguments to ipython notebook, **must** be preceded with double dash followed by a space, "
        "i.e. epmt notebook -- --ip 0.0.0.0 --allow-root, see epmt notebook -- --help for more info")

    # Explore PARSER (mostly GFDL-specific)
    exp_explore_parser = subparser.add_parser(
        'explore',
        help="Explore a particular experiment, looking for outliers",
        description="Simple drilldown workflow into an experiment")
    exp_explore_parser.add_argument(
        'epmt_cmd_args',
        help="Experiment name, matched against the 'exp_name' in job tags",
        metavar="exp_name")
    exp_explore_parser.add_argument(
        '--metric',
        help="metric to measure (default: duration)")
    exp_explore_parser.add_argument(
        '--limit',
        type=int,
        help="number of components to show (default: 10)")

    # Help PARSER
    help_parser = subparser.add_parser(
        'help',
        help="Display help with extended configuration information")
    help_parser.add_argument(
        'api',
        nargs='*',
        help="Display help on API functions. If none given then an index of available API functions will be printed")

    # Print help without dump config
    if len(argv) == 1:
        parser.epilog = ''
        parser.print_help()
        sysexit(1)

    args = parser.parse_args()

    # Print help if epmt help is called
    if args.command == 'help':
        if not args.api:
            parser.print_help()
        else:
            # skip the first api string in list and pass the rest (function names) to the function
            epmt_help_api(args.api[1:])
        sysexit(0)

    # Print help if no command is provided
    if args.command is None:
        parser.print_help()
        sysexit(0)

    # in the entry point, settings, logging, etc all gets setup there.
    retval = epmt_entrypoint(args)

    sysexit(retval)


if __name__ == "__main__":
    main()
