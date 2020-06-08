#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
from epmtlib import tag_from_string, logfn, epmt_logging_init, timing
import epmt_settings as settings
from os.path import abspath, isdir, isfile, basename
import os
import shutil
from logging import getLogger
import time
import tempfile
import tarfile
from glob import glob
import atexit

# these fields must be present at a minimum or our sanity
# check will flag an error
INPUT_CSV_FIELDS = {'tags','hostname','exename','path','args','exitcode','pid','generation','ppid','pgid','sid','numtids','tid','start','end'}
# Only the fields present in the list below will be output and the order will match the list order
# Please note, threads_df will be replaced by a string of metric names
OUTPUT_CSV_FIELDS = ['threads_df', 'tags', 'hostname', 'exename', 'path', 'exitcode', 'exitsignal', 'pid', 'generation', 'ppid', 'pgid', 'sid', 'numtids', 'start', 'finish', 'args']
# we need to use a character that doesn't occur in the
# input as the postgres copy_from cannot handle quoted delimiters
OUTPUT_CSV_SEP = '\t'

# Expected input format
# tags,hostname,exename,path,args,exitcode,pid,generation,ppid,pgid,sid,numtids,tid,start,end,usertime,systemtime,rssmax,minflt,majflt,inblock,outblock,vol_ctxsw,invol_ctxsw,num_threads,starttime,processor,delayacct_blkio_time,guest_time,rchar,wchar,syscr,syscw,read_bytes,write_bytes,cancelled_write_bytes,time_oncpu,time_waiting,timeslices,rdtsc_duration,PERF_COUNT_SW_CPU_CLOCK
# ,pp208,tcsh,/bin/tcsh,-f /home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101.tags,0,6099,0,6098,6089,6084,1,6099,1560599524133795,1560599524134048,2999,0,2852,387,0,0,0,0,0,0,1296261120000,0,0,0,17618,0,40,0,0,0,0,3604195,47138,1,846248,246094
def conv_csv_for_dbcopy(infile, outfile = '', jobid = '', input_fields = INPUT_CSV_FIELDS):
    '''
    Convert a CSV into a format suitable for ingestion using PostgreSQL COPY

    This file will convert a CSV from legacy format (with header)
    to a CSV that is suitable for ingestion into PostgreSQL using
    its COPY method. In particular the output will use strings
    or ARRAYs for JSON fields, and will remove extraneous computed fields. 

    Parameters
    ----------
       infile : string or file handle
                Path to input csv or input CSV file handle
      outfile : string, optional
                Path to output CSV. If empty, the output will
                be assumed to have the same name as input and
                will overwrite the input safely.
        jobid : string, optional
                Job ID. If not provided it will be determined from
                `infile`
 input_fields : set, optional
                Expected set of input fields. If provided, the input
                CSV fields must exactly match this


    Returns
    -------
    string representing the header, False otherwise

    Notes
    -----
    If the input and output filenames are the same, then a
    temporary file will be created for the output CSV. Finally
    the input CSV will be replaced with the temporary file.

    '''

    logger = getLogger(__name__)  # you can use other name
    outfile = outfile or infile   # empty outfile => overwrite infile

    if infile == outfile:
        outfd, outfile = tempfile.mkstemp(prefix = 'epmt_conv_outcsv_', suffix = '.csv')
        # logger.debug('in-place CSV conversion, so creating a tempfile {}'.format(outfile))
        in_place = True
    else:
        in_place = False

    if not jobid:
        jobid = extract_jobid_from_collated_csv(infile)
        if not jobid:
            logger.error('Could not determine jobid from input path: ' + infile)
            return False
        logger.debug('determined jobid ' + jobid + ' from input csv')
    _start_time = time.time()

    # if infile is a string, then it's a path
    # else it's a file-handle
    f = open(infile, newline='') if (type(infile) == str) else infile

    reader = csv.DictReader(f, escapechar='\\')
    # open a file for writing if we have a string, otherwise assume
    # its an already open file-handle
    with open(outfile, 'w', newline='') as csvfile:
        row_num = 0 # input row being processed
        outrows = 0 # number of rows output (we combine threads into one row)
        for r in reader:
            row_num += 1
            if row_num == 1:
                if input_fields and not(set(r.keys()) >= input_fields):
                    # sanity check to make sure our input file has the correct format
                    logger.error('Input CSV format is not correct. Likely missing  header row. Is it already in v2 format?')
                    return False
                thr_fields = sorted(set(r.keys()) - set(settings.skip_for_thread_sums) - set(settings.per_process_fields))
                metric_names = ",".join(thr_fields)
                header = OUTPUT_CSV_SEP.join(OUTPUT_CSV_FIELDS).replace('threads_df', '{'+metric_names+'}')
                # initialize the output file
                output_fields = OUTPUT_CSV_FIELDS
                output_fields[output_fields.index('threads_df')] = metric_names
                writer = csv.DictWriter(csvfile, fieldnames=output_fields, delimiter=OUTPUT_CSV_SEP)
                # writer.writeheader()
                
            
            # thread_metric_sums = {k: int(r[k]) for k in thr_fields }
            threads_df = [ int(r[k]) for k in thr_fields ] # array of ints
            numtids = int(r['numtids'])
            # now read in remaining thread rows (if the process is multithreaded)
            # and combine into threads_df/threads_sums 
            for i in range(1, numtids):
                thr = next(reader)
                row_num += 1
                thr_data = []
                for k in thr_fields:
                    # thread_metric_sums[k] += int(thr[k])
                    thr_data.append(int(thr[k]))
                # flatten multiple thread metrics into a 1-d array
                # to speed up ingestion
                threads_df.extend(thr_data)
            # only populate threads_sums for multithreaded processes
            # r['threads_sums'] = [ int(thread_metric_sums[k]) for k in thr_fields ] if numtids > 1 else []
            r[metric_names] = threads_df
            r['jobid'] = jobid
            # r['host_id'] = r['hostname']
            # r['gen'] = r['generation']
            if not 'exitsignal' in r:
                r['exitsignal'] = 0

            # We no longer need to do the hack below, as we now use copy_expert
            # for ingestion. The code below was only needed when using the deprecated
            # copy_from postgres ingestion
            #
            # replace postgres eof marker in the args field
            # https://stackoverflow.com/questions/23790995/postgres-9-3-end-of-copy-marker-corrupt-any-way-to-change-this-setting
            #if '\.' in r['args']:
            #    r['args'] = r['args'].replace('\.', '\\\.')

            for field in ['pid', 'ppid', 'pgid', 'sid', 'generation', 'exitcode', 'exitsignal', 'start', 'end']:
                r[field] = int(r[field])
            r['finish'] = r['end'] # end is reserved word in sql

            outrow = {}
            outrows += 1
            for f in output_fields:
                outrow[f] = r[f]
                # postgrsql requires arrays to use curly braces instead
                # of the square brackets we get with list objects in Python
                if f == metric_names:
                    outrow[f] = json.dumps(r[f]).replace('[', '{').replace(']', '}')
            writer.writerow(outrow)
    _finish_time = time.time()
    logger.info('Wrote {} rows at {:.2f} procs/sec'.format(outrows,(outrows/(_finish_time - _start_time))))
    if in_place:
        logger.debug('overwriting input file {} with {}'.format(infile, outfile))
        shutil.move(outfile, infile)
    return header


def _cleanup(path):
    if isfile(path):
        try:
            os.remove(path)
        except: pass
    elif isdir(path):
        try:
            shutil.rmtree(path)
        except: pass
    

def convert_csv_in_tar(in_tar, out_tar = ''):
    '''
    Converts a collated CSV in a staged tarfile into a format
    suitable for direct copy into PostgreSQL

    Parameters
    ----------
        in_tar: string
                Path to input tar or compressed tar (.tgz)
       out_tar: string, optional
                Path for output tar or compressed tar (.tgz)
                If left empty, the input tar will be replaced

    Returns
    -------
    True on success, False otherwise

    Notes
    -----
    If input and output paths are identical, the input will be
    overwritten. This action will not cause a warning to be issued,
    since there are legitimate cases where one may want in-place
    format conversion. This method will also add a header file
    in the newly-created tar.
    '''
    logger = getLogger(__name__)  # you can use other name
    if not in_tar.endswith('.tgz') or in_tar.endswith('.tar.gz') or in_tar.endswith('.tar'):
        raise ValueError('input file must have a .tar, .tgz or .tar.gz suffix')

    # if out_tar is empty, the input will be safely overwritten
    out_tar = out_tar or in_tar
    if not out_tar.endswith('.tgz') or out_tar.endswith('.tar.gz') or out_tar.endswith('.tar'):
        raise ValueError('output file must have a .tar, .tgz or .tar.gz suffix')

    if (in_tar == out_tar):
        # in-place editing, so create a temporary output file,
        # and then replace the input file
        in_place = True
        _, out_tar = tempfile.mkstemp(prefix='epmt_conv_outtar_', suffix = '.tgz')
        atexit.register(_cleanup, out_tar)
        logger.info('Doing in-place CSV format conversion in {}'.format(in_tar))
        logger.debug('Will create a temporary output tar ({}) as we are doing in-place conversion'.format(out_tar))
    else:
        in_place = False

    try:
        tar = tarfile.open(in_tar, 'r|*')
    except Exception as e:
        logger.error('error in processing compressed tar: ' + str(e))
        return False

    tempdir = tempfile.mkdtemp(prefix='epmt_conv_csv_')
    atexit.register(_cleanup, tempdir)
    logger.info('Extracting files from archive..')
    try:
        tar.extractall(tempdir)
        tar_contents = tar.getnames()
    except Exception as e:
        logger.error('Error extracting {} to {}: {}'.format(in_tar, tempdir, e))
        return False
    tar.close()
    in_csv_files = glob('{}/*.csv'.format(tempdir))
    if not in_csv_files:
        logger.error('No CSV files found in {}'.format(in_tar))
        return False
    # we should be having exactly 1 CSV file
    assert(len(in_csv_files) == 1)
    hostname = basename(in_csv_files[0]).split('-')[0]
    header_filename = "{}-papiex-header.tsv".format(hostname)
    if "./" + header_filename in tar_contents:
        # a header file presence indicates v2 CSV
        logger.error('{} already contains CSV files in v2 format'.format(in_tar))
        return False
    in_csv = in_csv_files[0]
    out_csv = tempdir + "/" + "{}-papiex.tsv".format(hostname)
    logger.info('Starting CSV conversion..')
    hdr = conv_csv_for_dbcopy(in_csv, out_csv)
    if not hdr:
        logger.error('Error converting {}'.format(in_csv))
        return False

    with open('{}/{}'.format(tempdir, header_filename), 'w') as csv_hdr_flo:
        csv_hdr_flo.write(hdr)
    logger.debug("Created CSV header file: {}".format(header_filename))
    tar_contents.append("./" + header_filename)

    logger.debug('Creating {} and adding contents to it'.format(out_tar))
    try:
        tar = tarfile.open(out_tar, 'w|gz')
    except Exception as e:
        logger.error('error in creating compressed tar {}: {}'.format(out_tar, e))
        return False
    owd = os.getcwd()
    try:
        os.chdir(tempdir)
    except OSError as e:
        logger.error('Error changing directory to {} while creating tarfile: {}'.format(tempdir, e))
        return False
    # copy files other than *.csv
    for f in tar_contents + ["./" + basename(out_csv)]:
        if f.endswith('.csv'): continue
        try:
            if os.path.isfile(f): tar.add(f)
        except Exception as e:
            logger.error('Error adding {}/{} to {}: {}'.format(tempdir, f, out_tar, e))
            return False
    # return to the original working dir
    os.chdir(owd)
    tar.close()
    logger.debug('Finished creating archive: {}'.format(out_tar))
    if in_place:
        logger.debug('Replacing {} with newly-created archive'.format(in_tar))
        shutil.move(out_tar, in_tar)
    logger.info('CSV format conversion successful!')
    shutil.rmtree(tempdir)

    
def extract_jobid_from_collated_csv(collated_csv):
    '''
    Returns a jobid from a collated CSV file
    '''
    return collated_csv.split('papiex')[-1].split('-')[1]


if __name__ == "__main__":
    logger = getLogger("epmt_convert_csv")
    epmt_logging_init(intlvl=2)
    import sys
    # conv_csv_for_dbcopy('pp208-collated-papiex-685000-0.csv', 'out.csv')
    # conv_csv_for_dbcopy('in-collated-papiex-685000-0.csv')
    # conv_csv_for_dbcopy('685000', 'out.csv', 'out2.csv')
    convert_csv_in_tar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '')
