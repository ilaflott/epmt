#!/usr/bin/env python

# Data Flow:
# Always Check for and Store comments
# Store masterHeader, calculate number of fields
# Verify csv data following header against number of fields
# compare following files header against masterHeader

from __future__ import print_function
from __future__ import unicode_literals
from sys import argv, version_info
from re import compile
from os import chdir, getcwd, path
from glob import glob
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger(__name__)  # you can use other name

# The below should just use a verbosity level 
CommentDebug = getLogger(__name__).getEffectiveLevel() > 10
HeaderDebug = getLogger(__name__).getEffectiveLevel() > 10
DataDebug = getLogger(__name__).getEffectiveLevel() > 10

def parseFile(file, masterHeader, headerFound, headerDelimCount, delim, commentDelim):
    """ Take file and paramaters for parsing return tuple of csv data"""
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
    except Exception as E:
        logger.error("No such file ".format(file))
        raise SystemError
    for line in fileLines:
        line = line.rstrip('\r\n')
        comment, header, data, headerDelimCount, headerFound, masterHeader, hostFlag = parseLine(file, line, masterHeader, headerDelimCount, headerFound, delim, commentDelim, hostFlag)
        if(comment is not None):
            comments.append(comment)
        if(data is not None):
            datas.append(data)
    return (comments, masterHeader, datas)


# Check for 3 possible conditions:
#    - line is comment
#    - we have no header: set it
#    - header is known: line is data
def parseLine(file, line, masterHeader, headerDelimCount,
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
        headerFound = True
        if "hostname" not in header:
            # Adding host to header
            header += ",hostname"
            hostFlag = True
        headerDelimCount = len(regexDelim.findall(header))
        if not masterHeader:
            masterHeader = header
            return (None, header, None, headerDelimCount, headerFound,
                    masterHeader, hostFlag)
        else:
            if header != masterHeader:
                logger.warning("File {} Header Does Not Match Master".format(file))
                logger.warning("Bad Job possible")
                raise SystemError
            elif header == masterHeader:
                return (None, header, None, headerDelimCount, headerFound,
                        masterHeader, hostFlag)
    # header is known: line is data
    # match data against header
    elif headerFound is True and line is not "":
        if(hostFlag):
            fn = file.split("/")[-1].split("-papiex")
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
            logger.warning("{} problem, Header: {} delimiters, row has {} delimiters".format(file, str(headerDelimCount), str(lineDelimCount)))
            logger.warning("Bad Job possible")
            raise SystemError


def writeOut(outfile, comments, masterHeader, dataList):
    """ Write our output file"""
    try:
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
    except FileNotFoundError as E:
        logger.warning("Bad output file")
        raise SystemError


def verifyOut(indir, outfile):
    """ Check line count """
    outdir = getcwd()
    if(type(indir) == str):
        chdir(indir)
        fileList = glob("*.csv")
        # Remove output file from list of csv's
        if(len(outfile.rsplit("/", 1)) > 1):
            fileList.remove(outfile.rsplit("/", 1)[1])
        else:
            if(path.isfile(outfile)):
                fileList.remove(outfile)
        if(len(outfile.rsplit("/", 1)) > 1):
            outputLines = file_len(outfile.rsplit("/", 1)[1])
        else:
            chdir(outdir)
            outputLines = file_len(outfile)
            chdir(indir)
    if(type(indir) == list):
        fileList = indir
        outputLines = file_len(outfile)
    lines = 0
    for file in fileList:
        lines += file_len(file)
    headers2Remove = len(fileList)
    # Total lines - headers except 1
    result = lines - (headers2Remove - 1)
    if(result > outputLines):
        logger.warning("Output File smaller than planned, off by {}".format((result - outputLines)))
        logger.warning("Lines in files {}".format(str(lines)))
        logger.warning("Files(headers removed - 1) {}".format(str(headers2Remove)))
        logger.warning("Output Lines: {}".format(str(outputLines)))
    elif(result < outputLines):
        logger.warning("Output File larger than planned, off by {}".format((outputLines - result)))
        logger.warning("Lines in files {}".format(str(lines)))
        logger.warning("Files(headers removed - 1) {}".format(str(headers2Remove)))
        logger.warning("Output Lines: {}".format(str(outputLines)))
    elif(result == outputLines):
        return True


def file_len(fname):
    """Helper function for counting file lines"""
    with open(fname) as f:
        for i, ln in enumerate(f):
            ln = ln
            pass
    return i + 1


def csvjoiner(indir,
              outfile="",
              delim=',', comment='#', debug="", escaped=['\n', '\a', '\b']):
    """ main function for orchestrating """
    global DataDebug
    global HeaderDebug
    global CommentDebug
    if (debug.lower() == "true"):
        DataDebug = True
        HeaderDebug = True
        CommentDebug = True
    elif (debug.lower() == "header"):
        HeaderDebug = True
    elif (debug.lower() == "data"):
        DataDebug = True
    elif (debug.lower() == "comment"):
        CommentDebug = True
    elif (debug.lower() == "false"):
        pass
    elif (debug != "false"):
        print("""\nUnknown debug option.  
        Please use:\ndebug=True full debug details\n
        debug=header\ndebug=data\ndebug=comment\n\n""")
    cwd = getcwd()
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
        try:
            if (path.isfile(outfile)):
                logger.error(outfile + " already exists")
                return False, None
            chdir(indir)
        except Exception as e:
            logger.error(str(e))
            return False, None
        fileList = glob("*.csv")
        if(len(fileList) < 2):
            logger.info("%d files, less than 2 csv files",len(fileList))
            return True,""
        try:
            jobid = indir.split("/")[-2].split("_")[-1].split("/")[0]
            host = fileList[0].split("-")[0]
        except Exception as e:
            logger.error(str(e))
            return False, None
        if(outfile is ""):
            outfile = indir + host + "-collated" + "-papiex-" + jobid + "-0.csv"
            # Verify concat does not exist, break if does
            if any(outfile.rsplit("/", 1)[1] in FL.lower() for FL in fileList):
                logger.error( outfile + " already exists remove to collate again")
                return False, None
        else:
            # still verify concat hasn't already been done
            tempoutfile = indir + host + "-collated" + "-papiex-" + jobid + "-0.csv"
            # Verify concat does not exist, break if does
            if any(tempoutfile.rsplit("/", 1)[1] in FL.lower() for FL in fileList):
                logger.error(tempoutfile + " already exists remove to collate again")
                return False, None

            if any(outfile in FL.lower() for FL in fileList):
                logger.error(outfile + " already already exists remove to collate again")
                return False, None
            logger.info("Output File:{}".format(str(outfile)))
# List Mode #########################################
    if(type(indir) == list):
        fileList = indir
        for test in fileList:
            if(path.isfile(test) is False):
                logger.error(test + " does not exist, please provide csv file list OR directory containing csv files")
                return False, None
        if(len(fileList) != len(set(fileList))):
            logger.error("List has duplicates")
            return False, None
        try:
            # Assumption: use first directory as jobid
            jobid = indir[0].split("/")[-2].split("_")[-1].split("/")[0]
            host = fileList[0].rsplit("/")[-1].split("-")[0]
            if(outfile is ""):
                outfile = indir[0].rsplit("/", 1)[0] + "/" + host + "-collated" + "-papiex-" + jobid + "-0.csv"
            tempoutfile = indir[0].rsplit("/", 1)[0] + "/" + host + "-collated" + "-papiex-" + jobid + "-0.csv"

        except IndexError:
            logger.error("CSV name not formatted properly(jobid or host?)")
            helpDoc()
            return False, None

        if(path.isfile(outfile)):
            logger.error("File {} already exists".format(outfile))
            return False, None
        if(path.isfile(tempoutfile)):
            logger.error("File {} already exists".format(tempoutfile))
            return False, None

        # Verify concat does not exist, break if does
        if any("concat" in FL.lower() for FL in fileList):
            logger.error(outfile + " already exists")
            return False, None
        else:
            logger.info("Output File:{}".format(str(outfile)))

    # iterate each file
    for file in fileList:
        comments, masterHeader, data = parseFile(file, masterHeader,
                                                 headerFound,
                                                 numFields, delim, commentDelim)
        # Reset for next file
        headerFound = False
        numFields = 0
        # Append lists
        commentsList += comments
        dataList += data

    chdir(cwd)
    writeOut(outfile, commentsList, masterHeader, dataList)
    verifyOut(indir, outfile)
    return True, outfile


if __name__ == '__main__':
    debug = "False"
    outfile = ""
    def helpDoc():
        """Print Help Information"""
        print("""Usage:\tDirectory\n\tconcat input dir/ [outFile=resulting_Csv.csv] [debug=True]\n\tOR List
\tconcat inputfile.csv inputfile2.csv [inputfile3.csv inputfileN.csv] [outFile=resulting_Csv.csv] [debug=True]
\nIf Specifying csv list parent directory of csv must have "_####" where # is job id

concat inputdirectory/ [debug=True] [outfile=results.csv]
concat csvfile.csv csvfile2.csv [debug=True] [outfile=results.csv]
concat dir/dir/csvfile.csv dir/csvfile2.csv [debug=True] [outfile=results.csv]
concat dir/*.csv [debug=True] [outfile=results.csv]
concat -h OR --help

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
        elif arg.find("outfile") != -1:
            # Unicode to str for py2
            outfile = str(argv[argv.index(arg)].split("=")[1])
            del argv[argv.index(arg)]
    # Single directory 
    if(len(argv) == 2):
        csvjoiner(debug=debug, indir=str(argv[1]), outfile=outfile)
    # List of files : list mode
    if(len(argv) > 2):
        csvjoiner(debug=debug, indir=argv[1:], outfile=outfile)
    if(len(argv) == 1):
        helpDoc()
        quit(0)
