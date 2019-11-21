from logging import getLogger
logger = getLogger(__name__)  # you can use other name

# Takes string
# Returns list of successfully deleted jobid's as strings

def epmt_notebook(arglist):
    logger.info("epmt_notebook: %s",str(arglist))

    mode = None
    cmd_args = []
    all_args = arglist
    for index, arg in enumerate(all_args):
        if arg == "kernel":
            mode = "kernel"
            pass
        else:
            cmd_args.append(arg)

    if mode == "kernel":  # run iPython kernel with passed ops
        args = ["kernel"]
        args.extend(cmd_args)
        # This does not want argv[0]
        logger.info("ipython kernel argv: %s",str(args))
        from IPython import start_ipython, start_kernel
        rv = start_ipython(argv=args)
    else:                 # Run IPython Notebook with passed ops
        import sys
        from os.path import realpath
        from os import getcwd
        me = realpath(sys.argv[0])
        logger.debug("Using %s as binary" ,me)
        args = []
        args.extend(["--notebook-dir="+getcwd(),
                     "--KernelManager.kernel_cmd=['"+me+"', 'notebook', 'kernel', '--', '-f', '{connection_file}']"])
        args.extend(all_args)
        logger.info("notebook argv: %s",str(args))
        from notebook import notebookapp
        rv = notebookapp.launch_new_instance(argv=args)
    return True

# Parse command line to check for kernel mode and clean up extraneous commands
