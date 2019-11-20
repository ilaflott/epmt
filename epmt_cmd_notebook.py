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
        from IPython import start_ipython, start_kernel
        # This does not want argv[0]
        logger.info("ipython kernel argv: %s",str(args))
        rv = start_ipython(argv=args)
    else:                 # Run IPython Notebook with passed ops
        import sys
        import os.path
        me = os.path.realpath(sys.argv[0])
        logger.debug("Using %s as binary" ,me)
        args = [me]
        args.extend(all_args)
        args.extend(["--KernelManager.kernel_cmd=['"+me+"', 'notebook', 'kernel', '--', '-f', '{connection_file}']"])
        from notebook import notebookapp
        logger.info("notebook argv: %s",str(args))
        rv = notebookapp.launch_new_instance(argv=args)
    return True

# Parse command line to check for kernel mode and clean up extraneous commands
