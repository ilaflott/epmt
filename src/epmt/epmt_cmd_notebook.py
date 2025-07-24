"""
EPMT notebook command module - handles IPython notebook functionality.
"""
import sys
import os
from logging import getLogger

logger = getLogger(__name__)  # you can use other name

# Takes string
# Returns list of successfully deleted jobid's as strings


def epmt_notebook(arglist):
    """
    Launch IPython notebook or kernel based on command line arguments.
    
    Args:
        arglist: List of command line arguments
        
    Returns:
        bool: True if successful
    """
    logger.info("epmt_notebook: %s", str(arglist))

    mode = None
    cmd_args = []
    all_args = arglist
    for arg in all_args:
        if arg == "kernel":
            mode = "kernel"
        else:
            cmd_args.append(arg)

    if mode == "kernel":  # run iPython kernel with passed ops
        args = ["kernel"]
        args.extend(cmd_args)
        # This does not want argv[0]
        logger.info("ipython kernel argv: %s", str(args))
        try:
            from IPython import start_ipython
            start_ipython(argv=args)
        except ImportError:
            logger.error("IPython not available")
            return False
    else:                 # Run IPython Notebook with passed ops
        me = os.path.realpath(sys.argv[0])
        logger.debug("Using %s as binary", me)
        args = []
        args.extend([f"--notebook-dir={os.getcwd()}",
                    f"--KernelManager.kernel_cmd=['{me}', 'notebook', 'kernel',"
                    f" '--', '-f', '{{connection_file}}']"])
        args.extend(all_args)
        logger.info("notebook argv: %s", str(args))
        try:
            from notebook import notebookapp
            notebookapp.launch_new_instance(argv=args)
        except ImportError:
            logger.error("notebook not available")
            return False
    return True

# Parse command line to check for kernel mode and clean up extraneous commands
