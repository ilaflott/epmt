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


from __future__ import print_function
from __future__ import unicode_literals
from sys import argv, version_info, exit
from re import compile
from os import getcwd, path
from glob import glob
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger('epmt_concat')  # you can use other name
from epmtlib import set_logging

class InvalidFileFormat(RuntimeError):
    pass


# file - Single CSV File to parse for comment,header and data
# masterHeader - Current MasterHeader for comparison against file
# headerFound - State, used to keep track of when header is found for data appending
# headerDelimCount - State, Regex count of header columns
# delim - Delimiter specified from csvjoiner used in parseline
# commentDelim - Delimiter specified from csvjoiner used in parseline
# Returns: tuple(comments list, masterHeader string, datas list)
def parseFile(file, masterHeader, headerFound, headerDelimCount, delim, commentDelim):
    """ Take file and paramaters for parsing return tuple of csv data
    to be passed to writeCSV then verifyOut"""
    fileLines = []
    comment = ""
    comments = []
    header = ""
    datas = []
    line = ""
    data = ""
    hostFlag = False
    try:
        with open(file) as fp:
            fileLines += fp.read().splitlines()
    except EnvironmentError:
        logger.error("No such file {}".format(file))
        raise
    for line in fileLines:
        line = line.rstrip('\r\n')
        comment, header, data, headerDelimCount, headerFound, masterHeader, hostFlag = parseLine(file, line, masterHeader, headerDelimCount, headerFound, delim, commentDelim, hostFlag)
        if(comment is not None):
            logger.debug("Found comment \n{}".format(comment))
            comments.append(comment)
        if(data is not None):
            logger.debug("Found data \n{}".format(data))
            datas.append(data)
    return (comments, masterHeader, datas)


# Check for 3 possible conditions:
#    - line is comment
#    - we have no header: set it
#    - header is known: line is data
def parseLine(infile, line, masterHeader, headerDelimCount,
              headerFound, delim, commentDelim, hostFlag):
    """ Parse single line of file with paramaters of current status, returning post status and line info"""
    comment = ""
    regexDelim = compile(r"(?<!\\)" + delim)
    line = line.strip()
    # line is comment
    if line.startswith(commentDelim):
        # Append comment to comment list
        # comments.append(line)
        comment = line
        return (comment, None, None, headerDelimCount, headerFound,
                masterHeader, hostFlag)

    # we have no header: set it
    # Set Header, compare against Master
    elif headerFound is False:
        header = line
        # logger.debug("Found Header: {}".format(header))
        headerFound = True
        if "hostname" not in header:
            # Adding host to header
            logger.info("Header missing \"hostname\"")
            header += ",hostname"
            hostFlag = True
        headerDelimCount = len(regexDelim.findall(header))
        if not masterHeader:
            masterHeader = header
            logger.debug("Master header set:\n{}".format(masterHeader))
            return (None, header, None, headerDelimCount, headerFound,
                    masterHeader, hostFlag)
        else:
            if header != masterHeader:
                msg = "File {} header does not match master".format(infile)
                logger.error(msg)
                logger.error("Likely a corrupted job.. stopping")
                raise InvalidFileFormat(msg)
            elif header == masterHeader:
                return (None, header, None, headerDelimCount, headerFound,
                        masterHeader, hostFlag)
    # header is known: line is data
    # match data against header
    elif headerFound is True and line is not "":
        if(hostFlag):
            fn = path.basename(infile).split("-papiex")
            if(len(fn) > 1):
                host = fn[0]
                line = line + ',' + host
            else:
                logger.warning("{} filename missing host before -papiex".format(str(fn[0])))
                raise ValueError("Invalid filename -- missing host")
        lineDelimCount = len(regexDelim.findall(line))
        if (lineDelimCount == headerDelimCount):
            return (None, None, line, headerDelimCount, headerFound, masterHeader, hostFlag)
        else:
            msg = "Different number of elements in header and data in {0}".format(infile)
            logger.error(msg)
            logger.error("Header: {} delimiters, row has {} delimiters".format(str(headerDelimCount), str(lineDelimCount)))
            raise InvalidFileFormat(msg)


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
    except EnvironmentError:  # parent of IOError, OSError
        logger.error("Error writing output file {}".format(outfile))
        raise


# Count lines in input directory compare result with length of output file lines
def verifyOut(indir, outfile):
    """ VerifyOut will take a input directory, count the csv files and compare
        the length against the outfile.

        Return: True if line count matches
        """
    # Directory Given
    if(type(indir) == str):
        fileList = sorted(glob(indir + "*.csv"))
        # Check for output in list of files
        if indir + outfile in fileList:
            fileList.remove(indir + outfile)
        # If outfile is just a base filename
        if(path.basename(outfile) is outfile):
            outputLines = file_len(outfile)
        # Else outfile includes full directory
        else:
            outputLines = file_len(outfile)
    # List Given
    if(type(indir) == list):
        fileList = indir
        outputLines = file_len(outfile)
    lines = 0
    for file in fileList:
        lines += file_len(file)
    headers2Remove = len(fileList)
    result = lines - (headers2Remove - 1)
    if(result > outputLines):
        logger.warning("Output file smaller than expected, off by {}".format((result - outputLines)))
        logger.warning("Lines in files {}".format(str(lines)))
        logger.warning("Files(headers removed - 1) {}".format(str(headers2Remove)))
        logger.warning("Output Lines: {}".format(str(outputLines)))
        return False
    elif(result < outputLines):
        logger.warning("Output file larger than expected, off by {}".format((outputLines - result)))
        logger.warning("Lines in files {}".format(str(lines)))
        logger.warning("Files(headers removed - 1) {}".format(str(headers2Remove)))
        logger.warning("Output lines: {}".format(str(outputLines)))
        return False
    elif(result == outputLines):
        logger.debug("Input: {} lines {} files".format(outputLines, len(fileList),))
        logger.debug("Output: {} lines file: {}".format(result, outfile))
        return True


# fname: file name to count lines of
# Returns number of lines
def file_len(fname):
    """Helper function for counting file lines"""
    with open(fname) as f:
        for i, ln in enumerate(f):
            ln = ln
            pass
    return i + 1


# indir - String location of CSV Files to collate
# outfile - string file name for output
# delim - CSV Delimiter character defaults to comma
# comment - CSV Comment character defaults to hashtag
# debug - Defaults to intlvl=2, set "false" to disable debug
def csvjoiner(indir,
              outfile="",
              delim=',', comment='#', debug=0):
    """ CSVJoiner will collate the csv files within the indir
        The resulting collated file can be designated with outfile paramater. """
    logger = getLogger("csvjoiner")
    set_logging(intlvl=debug, check=True)
    #set_logging(intlvl=2, check=True)
    # if (debug.lower() == "true"):
    #     set_logging(intlvl=2, check=False)  # Since debug paramater is specified check false
    # elif (debug.lower() == "false"):
    #     set_logging(intlvl=0, check=False)  # Since debug paramater is specified check false
    # elif (debug != "false"):
    #     print("""\nUnknown debug option.
    #     Please use:\ndebug=True full debug details\n
    #     debug=header\ndebug=data\ndebug=comment\n\n""")
    # Comments Outer
    commentsList = []
    # Header
    masterHeader = ""
    headerFound = False
    # Data
    dataList = []
    numFields = 0
    commentDelim = comment
    if(version_info < (3, 0)):
        if(isinstance(indir, basestring)):
            indir = str(indir.encode('ascii'))
# String (Directory) Mode ##################################
    if(type(indir) == str):
        logger.info("Collate in directory {}".format(indir))
        if not path.isdir(indir):
            msg = "{} does not exist or is not a directory".format(indir)
            logger.error(msg)
            return False, None
        fileList = sorted(glob(indir + "/*.csv"))
        logger.debug("Filelist:{}".format(fileList))
        if(len(fileList) == 0):
            msg = "{} has no CSV files to concatenate".format(indir)
            logger.warning(msg)
            return True, ""
        elif(len(fileList) < 2):
            logger.info("{} has only {} files".format(indir, len(fileList)))
        jobid = path.basename(path.normpath(indir))
        h = path.basename(fileList[0]).split("-")
        if(len(h) > 1):
            host = h[0]
        else:
            logger.error('Hostname missing from header and file does not have hyphen ')
            return False, None
        if outfile is "":
            logger.debug("indir: {} host: {} jobid: {}".format(indir, host, jobid))
            outfile = host + "-collated" + "-papiex-" + jobid + "-0.csv"
            logger.info("Output file set as {}".format(str(outfile)))
    # Now that outfile is known check for it

# List Mode #########################################
    if(type(indir) == list):
        logger.info("Collater in list mode(list arguments detected)")
        fileList = indir
        for test in fileList:
            if(not path.isfile(test)):
                logger.error(test + " does not exist or is not a file")
                return False, None
        if(len(fileList) != len(set(fileList))):
            logger.error("List has duplicates")
            return False, None
        try:
            # Assumption: use first directory as jobid
            # Use normpath to remove the last slash on the directory
            # Use basename to take the upper directory name that is the jobid
            jobid = path.basename(path.dirname(path.abspath(indir[0])))
            # Basename takes the current file name and pull the host before hyphen
            host = path.basename(fileList[0]).split("-")[0]
            if len(host) < 1:
                host = "unknown"
            # Generate outfile name
            logger.debug("indir:{} host:{} jobid:{}".format(indir, host, jobid))
            if(outfile is ""):
                outfile = host + "-collated" + "-papiex-" + jobid + "-0.csv"
            else:
                # Outfile is custom check if it exists
                if any(outfile in FL.lower() for FL in fileList):
                    logger.error(outfile + " is in output file list")
                    return False, None
        except IndexError:
            logger.error("CSV name not formatted properly(jobid or host?)")
            return False, None
        logger.info("Output file:{}".format(str(outfile)))
    if (path.isfile(outfile)):
        logger.error("Output {} already exists".format(outfile))
        return False, None
    if any(("collated" in FL for FL in fileList)):
        logger.error("Collated file in filelist")
        return False, None
    # iterate each file building result
    for file in fileList:
        logger.debug("Collating file:{}".format(file))
        comments, masterHeader, data = parseFile(file, masterHeader,
                                                     headerFound,
                                                     numFields, delim, commentDelim)
        # Reset for next file
        headerFound = False
        numFields = 0
        # Append lists
        commentsList += comments
        dataList += data
    writeCSV(outfile, commentsList, masterHeader, dataList)
    if verifyOut(indir, outfile):
        return True, outfile
    else:
        return False, None


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Concatenate CSV files. It returns 0 on success and < 0 on error")
    parser.add_argument('files', nargs='+', metavar='FILE',
                    help='Two or more CSV files to concatenate OR a directory containing CSV files')
    parser.add_argument('-v', '--verbose', action="count", default=0, help="increase verbosity")
    parser.add_argument('-o', '--output-file', help="output file name. Without this option the file will be automatically named based on the input file names", default='')
    args = parser.parse_args()
    try:
        retval = csvjoiner(debug=args.verbose, indir=(args.files[0] if (len(args.files) == 1) else args.files), outfile=args.output_file)
    except Exception as e:
        # an exception occured 
        retval = (False, str(e))
        logger.error("Error concatenating files: {0}".format(str(e)))
    exit(0 if retval[0] else -1)
