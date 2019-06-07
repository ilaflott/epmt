#!/usr/bin/env python

# Linter PEP8
# Python 3.6.5 or 2.7
# Chris Ault
#
# Data Flow:
# Always Check for and Store comments
# Store masterHeader, calculate number of fields
# Verify csv data following header against number of fields
# compare following files header against masterHeader


# Py3 to Py2 compat futures must be first
from __future__ import print_function
from __future__ import unicode_literals
from sys import argv, version_info
from re import compile
from os import chdir, getcwd, path
from glob import glob

CommentDebug = False
HeaderDebug = False
DataDebug = False


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
    if(CommentDebug or HeaderDebug or DataDebug):
        print("File:" + file)
    try:
        with open(file) as fp:
            fileLines += fp.read().splitlines()
    except Exception as E:
        print("No such file ", file, " exiting\n", E)
        raise SystemError
    for line in fileLines:
        line = line.rstrip('\r\n')
        if(CommentDebug or HeaderDebug or DataDebug):
            print("Line:", line)

        comment, header, data, headerDelimCount, headerFound, masterHeader, hostFlag = parseLine(file, line, masterHeader, headerDelimCount, headerFound, delim, commentDelim, hostFlag)

        if(CommentDebug):
            print("Parse Line Returns Comment: " + str(comment) + " " + str(type(comment)))
        if(comment is not None):
            comments.append(comment)

        if(HeaderDebug):
            print("Parse Line Returns Header:\n" + str(header))

        if(DataDebug):
            print("Parse Line Returns Data: " + str(data) + " " + str(type(data)))
        if(data is not None):
            datas.append(data)
        if(CommentDebug or HeaderDebug or DataDebug):
            print("\n")
    return (comments, masterHeader, datas)


# Check for 3 possible conditions:
# line is comment
# we have no header: set it
# header is known: line is data
def parseLine(file, line, masterHeader, headerDelimCount,
              headerFound, delim, commentDelim, hostFlag):
    """ Parse single line of file with paramaters of current status, returning post status and line info"""
    comment = ""
    regexDelim = compile(r"(?<!\\)" + delim)
    line = line.strip()
    if(HeaderDebug):
        print("Header is set:\n" + str(headerFound))
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
        if(HeaderDebug):
            print("setting header")
        header = line
        headerFound = True
        if "hostname" not in header:
            # Adding host to header
            header += ",hostname"
            hostFlag = True
        headerDelimCount = len(regexDelim.findall(header))
        if(HeaderDebug):
            print("Header:\n" + header + " Has " + str(headerDelimCount) + " delimiters")
            print("Commas on header:", header.count(","))
        if not masterHeader:
            masterHeader = header
            if(HeaderDebug):
                print("Master Header set by ", file, "as:\n" + masterHeader)
            return (None, header, None, headerDelimCount, headerFound,
                    masterHeader, hostFlag)
        else:
            if header != masterHeader:
                print("File: " + file + " Header Does Not Match Master")
                print("Bad Job possible")
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
                print(str(fn[0]), " Filename missing host before -papiex")
                helpDoc()
                raise SystemError
        lineDelimCount = len(regexDelim.findall(line))
        if (lineDelimCount == headerDelimCount):
            return (None, None, line, headerDelimCount, headerFound, masterHeader, hostFlag)
        else:
            print(file + " problem, Header: " + str(headerDelimCount) +
                  " delimiters, row has " + str(lineDelimCount) + " delimiters")
            print("Commas on line:", line.count(","))
            print("Commas on master:", masterHeader.count(","), "line appears as:")
            print(line)
            print("Bad Job possible, quitting")
            raise SystemError
    else:
        print("unreachable, quitting")
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
        print("Bad output file (create the dir maybe?), quitting\n", E)
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
    try:
        for file in fileList:
            lines += file_len(file)
    except Exception as E:
        print("File in list provided not found, quitting", E)
        raise SystemError
    headers2Remove = len(fileList)
    # Total lines - headers except 1
    result = lines - (headers2Remove - 1)
    if(result > outputLines):
        print("Output File smaller than planned, off by ", (result - outputLines))
        print("Lines in files" + str(lines))
        print("Files(headers removed - 1)" + str(headers2Remove))
        print("Output Lines: " + str(outputLines))
    elif(result < outputLines):
        print("Output File larger than planned, off by ", (outputLines - result))
        print("Lines in files" + str(lines))
        print("Files(headers removed - 1)" + str(headers2Remove))
        print("Output Lines: " + str(outputLines))
    elif(result == outputLines):
        print(result, " Lines Wrote and verified to ", outfile)
        return


def file_len(fname):
    """Helper function for counting file lines"""
    with open(fname) as f:
        for i, l in enumerate(f):
            l = l
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
        print("input type:", type(indir))
    elif (debug.lower() == "header"):
        HeaderDebug = True
    elif (debug.lower() == "data"):
        DataDebug = True
    elif (debug.lower() == "comment"):
        CommentDebug = True
    elif (debug.lower() == "false"):
        pass
    elif (debug != "false"):
        print("\nUnknown debug option.  Please use:\ndebug=True full debug details\ndebug=header\ndebug=data\ndebug=comment\n\n")
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
            if(path.isfile(outfile)):
                        print("File ", outfile, " already there, exiting")
                        raise SystemError
        except:
            raise SystemError
        try:
            chdir(indir)
        except IOError:
            print("Bad input dir\nPlease provide directory to collate containing csv files")
            raise SystemError
        fileList = glob("*.csv")
        if(len(fileList) < 2):
            print("Found less than 2 csv files, exiting\nPlease provide directory to collate containing csv files")
            raise SystemError
        try:
            jobid = indir.split("/")[-2].split("_")[-1].split("/")[0]
            host = fileList[0].split("-")[0]
        except IndexError as E:
            print("CSV files in directory have malformed name (jobid or host?)\nPlease provide directory to collate containing csv files\n")
            helpDoc()
            raise SystemError
        if(outfile is ""):
            outfile = indir + host + "-papiex-" + jobid + ".csv"
            # Verify concat does not exist, break if does
            if any(outfile.rsplit("/", 1)[1] in FL.lower() for FL in fileList):
                print("File: ", outfile, " already exists remove to collate again")
                raise SystemError
        else:
            # still verify concat hasn't already been done
            tempoutfile = indir + host + "-papiex-" + jobid + ".csv"
            # Verify concat does not exist, break if does
            if any(tempoutfile.rsplit("/", 1)[1] in FL.lower() for FL in fileList):
                print("File: ", tempoutfile, " already exists remove to collate again")
                raise SystemError

            if any(outfile in FL.lower() for FL in fileList):
                print("File: ", outfile, " already already exists remove to collate again")
                raise SystemError
            print("Output File:", str(outfile))
# List Mode #########################################
    if(type(indir) == list):
            fileList = indir
            for test in fileList:
                if(path.isfile(test) is False):
                    print(test, " file does not exist, please provide csv file list OR directory containing csv files")
                    raise SystemError
            if(len(fileList) != len(set(fileList))):
                print("List has duplicates")
                raise SystemError
            try:
                # Assumption: use first directory as jobid
                jobid = indir[0].split("/")[-2].split("_")[-1].split("/")[0]
                host = fileList[0].rsplit("/")[-1].split("-")[0]
                if(outfile is ""):
                    outfile = indir[0].rsplit("/", 1)[0] + "/" + host + "-papiex-" + jobid + ".csv"
                tempoutfile = indir[0].rsplit("/", 1)[0] + "/" + host + "-papiex-" + jobid + ".csv"

            except IndexError as E:
                print("CSV name not formatted properly(jobid or host?)\n")
                helpDoc()
                raise SystemError

            if(path.isfile(outfile)):
                print("File ", outfile, " already exists")
                raise SystemError
            if(path.isfile(tempoutfile)):
                print("File ", tempoutfile, " already exists")
                raise SystemError

            # Verify concat does not exist, break if does
            if any("concat" in FL.lower() for FL in fileList):
                print("File ", outfile, " already exists")
                raise SystemError
            else:
                print("Output File:", str(outfile))

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
    return outfile

# Wish I knew about this earlier 
# https://docs.python.org/3.6/library/argparse.html#module-argparse
# Link string to directory parsing and List to individual parsing
if __name__ == '__main__':
    debug = "False"
    outfile = ""
    # print(argv)

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
            # print("removing argument", argv[argv.index(arg)])
            del argv[argv.index(arg)]
        elif arg.find("outfile") != -1:
            # Unicode to str for py2
            outfile = str(argv[argv.index(arg)].split("=")[1])
            # print("removing argument", argv[argv.index(arg)])
            del argv[argv.index(arg)]
    try:
        if(len(argv) == 2):
            print("Operating in directory mode\nDirectory:", argv[1], " given")
            csvjoiner(debug=debug, indir=str(argv[1]), outfile=outfile)
        if(len(argv) > 2):
            print("Operating in list mode\nArgument, ", argv[1:], " given")
            csvjoiner(debug=debug, indir=argv[1:], outfile=outfile)
    except Exception as E:
        print(E)
        raise SystemExit
    if(len(argv) == 1):
        helpDoc()
        quit(0)
