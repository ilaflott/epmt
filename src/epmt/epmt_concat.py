#!/usr/bin/env python3

# Data Flow:
# Always Check for and Store comments
# Store masterHeader, calculate number of fields
# Verify csv data following header against number of fields
# compare following files header against masterHeader

# Callstack
# csvjoiner > Loop over files(parsefile > parseline) >
#   writeCSV > verifyOut[file_len()]

# Jobid is based on parent directory of csv files
# Hostname is determined from csv file name
#   Example:
#   test/data/collate/goodSample_123/asus-papiex-549-0.csv
#   Hostname: `asus`
#   Jobid: `goodSample_123`


# from __future__ import print_function
from __future__ import unicode_literals
from epmt.epmtlib import epmt_logging_init, logfn
from sys import exit
from re import findall, search
from os import path, remove, makedirs
from shutil import copyfile
from glob import glob
from logging import getLogger
logger = getLogger('epmt_concat')  # you can use other name


class InvalidFileFormat(RuntimeError):
    pass

# outfile is argument to csv joiner
# errdir is place for output
# badfiles is possibly empty list of files that errored in parsing


def rename_bad_files(outfile, errdir, badfiles):
    logger = getLogger('rename_bad_files')
    logger.debug("%s,%s,%s", outfile, errdir, str(badfiles))
    if not errdir:
        logger.warning("No error dir specified, skipping renaming of bad CSV files!")
        return badfiles
    ed = path.normpath(errdir)
    if not path.exists(ed):
        try:
            makedirs(ed)
        except OSError as e:
            logger.error("makedirs(%s): %s, skipping renamng of bad CSV files!", ed, str(e))
            return badfiles
    renamed_badfiles = []
    for f in badfiles:
        p = path.basename(path.normpath(f))
        fn = ed + "/" + p + ".error"
        logger.debug("copyfile(%s,%s)", f, fn)
        try:
            copyfile(f, fn)
            remove(f)
            renamed_badfiles.append(fn)
        except Exception as e:
            logger.error("copyfile(%s,%s) or remove(%s) failed: %s", f, fn, f, str(e))
            renamed_badfiles.append(f)
    return renamed_badfiles

# file - Single CSV File to parse for comment,header and data
# masterHeader - Current MasterHeader for comparison against file
# headerFound - State, used to keep track of when header is found for data appending
# headerDelimCount - State, Regex count of header columns
# delim - Delimiter specified from csvjoiner used in parseline
# commentDelim - Delimiter specified from csvjoiner used in parseline
# Returns: tuple(comments list, masterHeader string, datas list)


def parseFile(inputfile, masterHeader, masterHeaderFile, delim, commentDelim):
    """ Take file and paramaters for parsing return tuple of csv data
    to be passed to writeCSV then verifyOut"""
    logger = getLogger('parseFile')
    fileLines = []
    comments = []
    header = ""
    datas = []
    line = ""
    data = ""
    headerFound = False
    headerDelimCount = 0

    try:
        with open(inputfile) as fp:
            fileLines += fp.read().splitlines()
    except Exception as e:
        logger.error("Failed to read file %s: %s", inputfile, str(e))
        return (comments, masterHeader, masterHeaderFile, None)

    for line in fileLines:
        line = line.strip('\r\n')
        # line is blank
        if not line:
            continue
        # line is comment
        if line.startswith(commentDelim):
            logger.debug("File %s: comment %s", inputfile, line)
            comments.append(line)
            continue
        try:
            header, data, headerDelimCount, headerFound, masterHeader, masterHeaderFile = parseLine(
                inputfile, line, masterHeader, masterHeaderFile, headerDelimCount, headerFound, delim)
            if data:
                datas.append(data)
            logger.debug("File %s: data %s", inputfile, str(data))
        except BaseException:
            return ([], masterHeader, masterHeaderFile, [])
    return (comments, masterHeader, masterHeaderFile, datas)


# Check for 3 possible conditions:
#    - line is comment
#    - we have no header: set it
#    - header is known: line is data
def parseLine(infile, line, masterHeader, masterHeaderFile, headerDelimCount, headerFound, delim):
    """ Parse single line of file with paramaters of current status, returning post status and line info"""
    logger = getLogger('parseLine')
    Delim = r"(?<!\\)" + delim
    lineDelimCount = len(findall(Delim, line))
    # we have no header: set it
    # Set Header, compare against Master
    if headerFound is False:
        # logger.debug("Found Header: {}".format(header))
        # if "hostname" not in header:
        #     # Adding host to header
        #     logger.info("Header missing \"hostname\"")
        #     header += ",hostname"
        #     hostFlag = True
        headerFound = True
        headerDelimCount = lineDelimCount
        if not masterHeader:
            masterHeader = line
            masterHeaderFile = infile
            logger.info("Master header file: %s", masterHeaderFile)
            logger.info("Master header count: %d", headerDelimCount)
            logger.info("Master header set: %s", masterHeader)
            return (line, None, headerDelimCount, headerFound, masterHeader, masterHeaderFile)
        elif line != masterHeader:
            msg = "Header mismatch: File {} does not match master file {}".format(infile, masterHeaderFile)
            logger.error(msg)
            msg = "Header: {}".format(line)
            logger.error(msg)
            msg = "Master: {}".format(masterHeader)
            logger.error(msg)
            raise InvalidFileFormat()
        else:
            return (None, None, headerDelimCount, headerFound, masterHeader, masterHeaderFile)
    # header is known: line is data
    # match data against header
    elif headerFound is True and line != "":
        # if(hostFlag):
        #     fn = path.basename(infile).split("-papiex")
        #     if(len(fn) > 1):
        #         host = fn[0]
        #         line = line + ',' + host
        #     else:
        #         logger.warning("{} filename missing host before -papiex".format(str(fn[0])))
        #         raise ValueError("Invalid filename -- missing host")
        if (lineDelimCount == headerDelimCount):
            return (None, line, headerDelimCount, headerFound, masterHeader, masterHeaderFile)
        else:
            logger.error(
                "File: {}, Header: {} delimiters, but this row has {} delimiters".format(
                    infile, str(headerDelimCount), str(lineDelimCount)))
            logger.error("Row: {}".format(line))
            logger.error("Master File: {}".format(masterHeaderFile))
            logger.error("Master header: {}".format(masterHeader))
            raise InvalidFileFormat()


#
# Here All Aggrigated data is written to an output file in the pwd
#
# outfile - csv name to write to pwd
#   ex: asus-collated-papiex-2-0.csv

# comments - Aggrigated list of comments
#   ex: ['comment1','comment2','...']

# masterHeader - String holding header to be written
#   ex:"tags,hostname,exename,path,args,exitcode,pid,..."

# dataList - Aggrigated list of csv data
#   ex:[",asus,sleep,/bin/sleep,1,0,26577,0,26576,26497"]
def writeCSV(outfile, comments, masterHeader, dataList):
    """ Write our output file"""
    logger = getLogger('writeCSV')
    try:
        logger.info("Writing file({})".format(outfile))
        # write comments
        with open(outfile, 'w') as f:
            for item in comments:
                f.write("%s\n" % item)
        # write header
            f.write("%s" % masterHeader)
            f.write("\n")
        # write data
            for item in dataList:
                f.write("%s\n" % item)
    except Exception as e:  # parent of IOError, OSError
        logger.error("Error writing output file %s, removing...: %s", outfile, str(e))
        remove(outfile)
        return False
    return True

# Count lines in input directory compare result with length of output file lines


def verifyOut(fileList, outfile):
    """ VerifyOut will take a list of files, count the csv files and compare
        the length against the outfile.

        Return: True if line count matches
        """
    logger = getLogger('verifyOut')
    outputLines = file_len(outfile)
    lines = 0
    for file in fileList:
        lines += file_len(file)
    headers2Remove = len(fileList)
    result = lines - (headers2Remove - 1)
    logger.debug("{} input files have {} lines".format(len(fileList), lines))
    logger.debug("{} output file has {} lines".format(outfile, outputLines))
    logger.debug("{} output file expected {} lines".format(outfile, result))
    if (result != outputLines):
        logger.error(
            "Output file {} smaller than expected, off by {} lines, expected {}".format(
                outfile, result - outputLines, result))
        logger.error("Input files {} have {} lines".format(str(fileList), str(lines)))
        logger.error("Total header lines removed - 1 {}".format(str(headers2Remove)))
        return False
    else:
        return True

# fname: file name to count lines of
# Returns number of lines


def file_len(fname):
    """Helper function for counting file lines"""
    ind = None
    with open(fname) as f:
        for i, ln in enumerate(f):
            ind = i
    return ind + 1


def determine_output_filename(instr):
    try:
        jobid = path.basename(path.dirname(path.abspath(instr)))
        logger.debug("jobid %s", jobid)
        m = search('(.+)-papiex-.+\\.csv', path.basename(instr))
        logger.debug("host %s", m.group(1))
        outfile = m.group(1) + "-collated" + "-papiex-" + jobid + "-0.csv"
    except Exception as e:
        logger.error("Could not determine output file name from %s: %s", instr, str(e))
        return ""
    logger.info("Output file set as {}".format(outfile))
    return outfile

# indir - String location of CSV Files to collate
# outfile - string file name for output
# delim - CSV Delimiter character defaults to comma
# comment - CSV Comment character defaults to hashtag
# debug - Defaults to intlvl=2, set "false" to disable debug


@logfn
def csvjoiner(indir,
              outfile="",
              outpath="",
              delim=',', comment='#', debug=0, keep_going=True, errdir="/tmp/"):
    """ CSVJoiner will collate the csv files within the indir
        The resulting collated file can be designated with outfile paramater. """

    logger = getLogger("csvjoiner")
    epmt_logging_init(intlvl=debug, check=True)
    logger.debug("indir=%s,outfile=%s,delim=%s,comment=%s,keep_going=%s,errdir=%s",
                 str(indir), outfile, delim, comment, keep_going, errdir)
    # epmt_logging_init(intlvl=2, check=True)
    # if (debug.lower() == "true"):
    #     epmt_logging_init(intlvl=2, check=False)  # Since debug paramater is specified check false
    # elif (debug.lower() == "false"):
    #     epmt_logging_init(intlvl=0, check=False)  # Since debug paramater is specified check false
    # elif (debug != "false"):
    #     print("""\nUnknown debug option.
    #     Please use:\ndebug=True full debug details\n
    #     debug=header\ndebug=data\ndebug=comment\n\n""")
    # Comments Outer
    commentsList = []
    # List of corrupted CSV files not joined
    badfiles = []
    # Header
    masterHeader = ""
    masterHeaderFile = ""
    # Data
    dataList = []
    commentDelim = comment
    # if(version_info < (3, 0)):
    #     if(isinstance(indir, basestring)):
    #         indir = str(indir.encode('ascii'))
# String (Directory) Mode ##################################
    if (isinstance(indir, str)):
        if not path.isdir(indir):
            msg = "{} does not exist or is not a directory".format(indir)
            logger.error(msg)
            return False, None, badfiles
        logger.info("Collate in directory {}".format(indir))
        fileList = sorted(glob(indir + "/*.csv"))
        logger.debug("Filelist:{}".format(fileList))
# List Mode #########################################
    if (isinstance(indir, list)):
        logger.info("Collate list")
        fileList = indir
        if (len(fileList) != len(set(fileList))):
            logger.warning("Input has duplicates")
            if not keep_going:
                return False, None, badfiles
        fileList = sorted(list(set(fileList)))
        for test in fileList:
            if (not path.isfile(test)):
                logger.error(test + " does not exist or is not a file")
                return False, None, badfiles
    if (len(fileList) == 0):
        msg = "{} has no CSV files to concatenate".format(indir)
        logger.warning(msg)
        return True, None, badfiles
    if any(("collated" in FL for FL in fileList)):
        logger.error("Collated output file in input")
        return False, None, badfiles
    if outfile == "":
        outfile = determine_output_filename(fileList[0])
        if outfile == "":
            return False, None, badfiles
    outfile = outpath + outfile
    if (path.exists(outfile)):
        logger.error("Output {} already exists".format(outfile))
        return False, None, badfiles

    # iterate each file building result
    badfiles = []
    badfiles_renamed = []
    for f in fileList:
        logger.info("Collating file:{}".format(f))
        comments, masterHeader, masterHeaderFile, data = parseFile(
            f, masterHeader, masterHeaderFile, delim, commentDelim)
        if not data:
            badfiles.append(f)
        else:
            commentsList += comments
            dataList += data

    if badfiles:
        logger.debug("parseFile returned some bad files: %s", str(badfiles))
        if not keep_going:
            return False, None, badfiles
        badfiles_renamed = rename_bad_files(outfile, errdir, badfiles)

    if masterHeader and masterHeaderFile and dataList:
        rv = writeCSV(outfile, commentsList, masterHeader, dataList)
        if (rv is True) and verifyOut(list(set(fileList) - set(badfiles)), outfile):
            return True, outfile, badfiles_renamed
        else:
            return False, None, badfiles_renamed

    logger.error("Missing dataList, masterHeader or masterHeaderFile: %s", str(fileList))
    return False, None, badfiles_renamed


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Concatenate CSV files. It returns 0 on success and < 0 on error")
    parser.add_argument('files', nargs='+', metavar='FILE',
                        help='Two or more CSV files to concatenate OR a directory containing CSV files')
    parser.add_argument('-v', '--verbose', action="count", default=0, help="increase verbosity")
    parser.add_argument(
        '-o',
        '--output-file',
        help="Name of the output file, determined from input if not specified",
        default='')
    parser.add_argument('-e', '--error', action='store_true', help="Exit at the first sign of trouble", default=False)
    parser.add_argument(
        '-E',
        '--error-dir',
        help="Name of the directory to save files with errors, disabled if not specified",
        default='')
    args = parser.parse_args()
    retval, of, bf = csvjoiner(debug=args.verbose,
                               indir=(args.files[0] if (len(args.files) == 1) else args.files),
                               outfile=args.output_file,
                               keep_going=not args.error,
                               errdir=args.error_dir)
    exit(0 if retval else -1)
