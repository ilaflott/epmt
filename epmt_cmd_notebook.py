from logging import getLogger
logger = getLogger(__name__)  # you can use other name

# Takes string
# Returns list of successfully deleted jobid's as strings

def epmt_notebook(arglist):
    logger.info("epmt_notebook: %s",str(arglist))
    import sys
    from os import getcwd, path

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):  # we are running in a pyinstaller bundle
        frozen = 'ever so'
        bundle_dir = getattr(sys, '_MEIPASS', '')
        me = "'"+sys.executable + "'"
    else: # we are running in a normal Python environment
        frozen = 'not'
        bundle_dir = path.dirname(path.abspath(__file__))
        me = "'"+sys.executable + "','" + sys.argv[0]+"'"    
    logger.debug( 'we are %s',frozen+' frozen')
    logger.debug( 'sys.argv[0] is %s', sys.argv[0] )
    logger.debug( 'sys.executable is %s', sys.executable )
    logger.debug( 'os.getcwd is %s', getcwd() )
    logger.debug( 'bundle/module dir is %s', bundle_dir )
    logger.debug( 'epmt is %s',me)

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
        from IPython import start_ipython
        args = ["kernel"]
        args.extend(cmd_args)
        # This does not want argv[0]
        logger.info("mode kernel argv: %s",str(args))
        start_ipython(argv=args)
    else:                 # Run IPython Notebook with passed ops
        from logging import root
        debug=""
        if (root.level < 30):
            debug="-v"
        if (root.level < 20):
            debug+="v"
        if (root.level < 10):
            debug+="v"
        if debug:
            debug = ", '"+debug+"'"
        logger.debug('debug is %s',debug)
        args = []
        args.extend(["--notebook-dir="+getcwd(),
                     "--KernelManager.kernel_cmd=["+me+debug+", 'notebook', 'kernel', '--', '-f', '{connection_file}']"])
        args.extend(all_args)
        logger.info("mode notebook argv: %s",str(args))
        from notebook import notebookapp
        notebookapp.launch_new_instance(argv=args)
    return True

# Parse command line to check for kernel mode and clean up extraneous commands
