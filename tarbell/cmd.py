"""
Operations to be run within subprocesses for virtual environments.
It is assumed that the caller has activated the virtual environment 
by running this script with the python executable within the virtual
environment and updating the environment PATH by prepending the
virtual environment bin directory.

Usage:
    <virtualenv_dir>/bin/python <script> <command> [args] [options]

Commands:
    pip_install <requirements_file>
        Will call 'pip install -r [args]'
    
    project_run <address> <port> ??
    
    project_publish ??
    
Options:
    -h, --help
        Print this help information   
"""
import getopt
import os
import sys
import pip
import time



def pip_install(requirements_file):
    """Install requirements from file using pip"""
    if not os.path.exists(requirements_file):
        raise Exception('requirements file "%s" does not exist' \
            % requirements_file)
            
    return pip.main(['install', '-r', requirements_file])


def project_run(address, port):
    """TODO"""
    pass


def project_publish():
    """TODO"""
    pass

    
class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


if __name__ == '__main__': 
    try:
        try:
            opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
        except getopt.error, msg:
             raise Usage(msg)

        # Handle options 
        for option, value in opts:
            if option in ("-h", "--help"):
                print __doc__
                sys.exit(0)
            else:
                raise Usage('unknown option "%s"' % option)

        # Handle args             
        if not args:
            raise Usage('you must specify a command')
                        
        command = args[0]
        args  = args[1:]
        
        if command == 'pip_install':
            if len(args) <> 1:
                raise Exception('pip_install expected requirements file')                               
            pip_install(args[0])
        elif command == 'project_run':
            if len(args) <> 2:
                raise Exception('run_project expected address and port')
            run_project(args[0], args[1], args[2])            
        else:
            raise Exception('unknown command "%s"' % command)
                    
            
    except Usage, err:
        print >>sys.stderr, err.msg
        sys.exit(2)
    except Exception, err:
        print >>sys.stderr, str(err)
        #traceback.print_exc(err)
        sys.exit(1)
    else:
        sys.exit(0)
