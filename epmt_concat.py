#!/usr/bin/env python

# Data Flow:
# Always Check for and Store comments
# Store masterHeader, calculate number of fields
# Verify csv data following header against number of fields
# compare following files header against masterHeader

# Callstack
# csvjoiner > Loop over files(parsefile > parseline) >
#   writeOut > verifyOut[file_len()]

# Jobid is based on parent directory of csv files
# Hostname is determined from csv file name
#   Example:
#   test/data/collate/goodSample_123/asus-papiex-549-0.csv
#   Hostname: `asus`
#   Jobid: `goodSample_123`


from __future__ import print_function
from __future__ import unicode_literals
from sys import argv, version_info
from re import compile
from os import getcwd, path
from glob import glob
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger(__name__)  # you can use other name
from epmtlib import set_logging


# file - Single CSV File to parse for comment,header and data
# masterHeader - Current MasterHeader for comparison against file
# headerFound - State, used to keep track of when header is found for data appending
# headerDelimCount - State, Regex count of header columns
# delim - Delimiter specified from csvjoiner used in parseline
# commentDelim - Delimiter specified from csvjoiner used in parseline
# Returns: tuple(comments list, masterHeader string, datas list)
def parseFile(file, masterHeader, headerFound, headerDelimCount, delim, commentDelim):
    """ Take file and paramaters for parsing return tuple of csv data
    to be passed to writeOut then verifyOut"""
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
        raise SystemError
    for line in fileLines:
        line = line.rstrip('\r\n')
        try:
            comment, header, data, headerDelimCount, headerFound, masterHeader, hostFlag = parseLine(file, line, masterHeader, headerDelimCount, headerFound, delim, commentDelim, hostFlag)
        except SystemError:
            raise SystemError
        if(comment is not None):
            logger.debug("Found Comment \n{}".format(comment))
            comments.append(comment)
        if(data is not None):
            logger.debug("Found Data \n{}".format(data))
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
            logger.debug("Master Header set:\n{}".format(masterHeader))
            return (None, header, None, headerDelimCount, headerFound,
                    masterHeader, hostFlag)
        else:
            if header != masterHeader:
                logger.warning("File {} Header Does Not Match Master".format(infile))
                logger.warning("Bad Job possible, stopping")
                raise SystemError
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
                logger.warning("{} Filename missing host before -papiex".format(str(fn[0])))
                helpDoc()
                raise SystemError
        lineDelimCount = len(regexDelim.findall(line))
        if (lineDelimCount == headerDelimCount):
            return (None, None, line, headerDelimCount, headerFound, masterHeader, hostFlag)
        else:
            logger.warning("File {} Data does not match header".format(infile))
            logger.warning("Header: {} delimiters, row has {} delimiters".format(str(headerDelimCount), str(lineDelimCount)))
            logger.warning("Bad Job possible")
            raise SystemError


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
def writeOut(outfile, comments, masterHeader, dataList):
    """ Write our output file"""
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
        logger.error("Bad output file {}".format(outfile))
        raise SystemError


# Count lines in input directory compare result with length of output file lines
def verifyOut(indir, outfile):
    """ VerifyOut will take a input directory, count the csv files and compare
        the length against the outfile.

        Return: True if line count matches
        """
    # Directory Given
    if(type(indir) == str):
        fileList = glob(indir + "*.csv")
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
        logger.warning("Output File smaller than planned, off by {}".format((result - outputLines)))
        logger.warning("Lines in files {}".format(str(lines)))
        logger.warning("Files(headers removed - 1) {}".format(str(headers2Remove)))
        logger.warning("Output Lines: {}".format(str(outputLines)))
        return False
    elif(result < outputLines):
        logger.warning("Output File larger than planned, off by {}".format((outputLines - result)))
        logger.warning("Lines in files {}".format(str(lines)))
        logger.warning("Files(headers removed - 1) {}".format(str(headers2Remove)))
        logger.warning("Output Lines: {}".format(str(outputLines)))
        return False
    elif(result == outputLines):
        logger.debug("Input: {} Lines {} Files".format(outputLines, len(fileList),))
        logger.debug("Output: {} Lines File: {}".format(result, outfile))
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
              delim=',', comment='#', debug=""):
    """ CSVJoiner will collate the csv files within the indir
        The resulting collated file can be designated with outfile paramater. """
    logger = getLogger(__name__)
    #set_logging(intlvl=2, check=True)
    if (debug.lower() == "true"):
        set_logging(intlvl=2, check=False)  # Since debug paramater is specified check false
    elif (debug.lower() == "false"):
        set_logging(intlvl=0, check=False)  # Since debug paramater is specified check false
    elif (debug != "false"):
        print("""\nUnknown debug option.
        Please use:\ndebug=True full debug details\n
        debug=header\ndebug=data\ndebug=comment\n\n""")
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
        logger.info("Collate in Directory {}".format(indir))
        fileList = glob(indir + "/*.csv")
        # logger.debug("Filelist:{}".format(fileList))
        if(len(fileList) == 0):
            logger.info("{} has no CSV Files".format(indir))
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
            logger.info("Output File set as {}".format(str(outfile)))
    # Now that outfile is known check for it

# List Mode #########################################
    if(type(indir) == list):
        logger.info("Collater in List mode(List arguments Detected)")
        fileList = indir
        for test in fileList:
            if(path.isfile(test) is False):
                logger.error(test + " is not a csv file")
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
            helpDoc()
            return False, None
        logger.info("Output File:{}".format(str(outfile)))
    if (path.isfile(outfile)):
        logger.error("Output {} already exists".format(outfile))
        return False, None
    if any(("collated" in FL for FL in fileList)):
        logger.error("Collated file in filelist")
        return False, None
    # iterate each file building result
    for file in fileList:
        logger.debug("Collating File:{}".format(file))
        try:
            comments, masterHeader, data = parseFile(file, masterHeader,
                                                     headerFound,
                                                     numFields, delim, commentDelim)
        except SystemError:
            raise SystemError
        # Reset for next file
        headerFound = False
        numFields = 0
        # Append lists
        commentsList += comments
        dataList += data
    writeOut(outfile, commentsList, masterHeader, dataList)
    if verifyOut(indir, outfile):
        return True, outfile
    else:
        return False, None


if __name__ == '__main__':
    debug = "False"
    outfile = ""

    def helpDoc():
        """Print Help Information"""
        print("""Usage:\tDirectory\n\tconcat input dir/ [outFile=resulting_Csv.csv] [debug=True]\n\tOR List
\tconcat inputfile.csv inputfile2.csv [inputfile3.csv inputfileN.csv] [outFile=resulting_Csv.csv] [debug=True]
\nIf Specifying csv list parent directory of csv must have underscore followed by jobid in directory name

epmt_concat.py [outfile=results.csv] inputdirectory/ [debug=True] 
epmt_concat.py [outfile=results.csv] csvfile.csv csvfile2.csv [debug=True] 
epmt_concat.py [outfile=results.csv] dir/dir/csvfile.csv dir/csvfile2.csv [debug=True] 
epmt_concat.py [outfile=results.csv] dir/*.csv [debug=True] 
epmt_concat.py -h OR --help

inputdirectory - This directory contains job csv files and has job id after a underscore ex CM4_piControl_C_atmos_00050101
\tex: atmos_00050101
inputfile.csv - this file should have a name preceded by host then hyphen host-details.csv
\tex: pp201-papiex-300-0.csv\n
<debug>=Debug header, data and comments
----------------------------------------
debug=header will display header parsing related debug information
debug=data will display csv data related debug information
debug=comment will display comment related debug information
\n<outfile>=resulting collated file
""")
    # Find debug arg and set debug variable+
    for arg in argv:
        if arg.find("-h") != -1 or arg.find("--help") != -1:
            helpDoc()
            quit(0)
        if arg.find("debug") != -1:
            # Unicode to str for py2
            debug = str(argv[argv.index(arg)].split("=")[1])
            del argv[argv.index(arg)]
        if arg.find("outfile") != -1:
            # Unicode to str for py2
            outfile = str(argv[argv.index(arg)].split("=")[1])
            del argv[argv.index(arg)]
    # Single directory
    if(len(argv) == 2):
        try:
            csvjoiner(debug=debug, indir=str(argv[1]), outfile=outfile)
        except SystemError as E:
            quit(1)
    # List of files : list mode
    if(len(argv) > 2):
        csvjoiner(debug=debug, indir=argv[1:], outfile=outfile)
    if(len(argv) == 1):
        helpDoc()
        quit(0)
