# -*- coding: utf-8 -*-

"""
tarbell.admin
~~~~~~~~~

This module provides admin utilities for Tarbell cli and gui.
"""
import getpass
import glob
import httplib2
import imp
from multiprocessing import Process, Queue
import os
import sh
import shutil
import subprocess
import sys
import yaml

from datetime import datetime

from apiclient.http import MediaFileUpload as _MediaFileUpload
from apiclient import errors

from oauth2client import client
from oauth2client import keyring_storage

from .oauth import get_drive_api
from .utils import make_dir, delete_dir, backup

from tarbell import __VERSION__ as VERSION

# This directory
TARBELL_PATH = os.path.dirname(os.path.abspath(__file__))

DEFAULT_BLUEPRINTS = [
    {
        "name": "Basic Bootstrap 3 template",
        "url": "https://github.com/newsapps/tarbell-template",
    }, 
    {
        "name": "Searchable map template",
        "url": "https://github.com/eads/tarbell-map-template",
    },
    {
        "name": "Tarbell template walkthrough",
        "url": "https://github.com/hbillings/tarbell-tutorial-template",
    },
    {
        "name": "Empty project (no blueprint)"
    }
]  

DEFAULT_CONFIG = {
    'EXCLUDES': ["*.md", "requirements.txt"],
    'DEFAULT_CONTEXT': {
        'name': '',
        'title': ''
    }
}
        

def _load_module_data(q, module_path, module_name):    
    """Load module and push dict of values into queue"""
    try:
        filename, pathname, description = imp.find_module(module_name, [module_path])
        m = imp.load_module(os.path.dirname(module_path), filename, pathname, description)
        
        d = dict()
        for varname in dir(m):
            if not varname.startswith("_"):
                varval = getattr(m, varname)            
                if isinstance(varval, (bool, int, float, str, unicode, tuple, list, dict)):
                    d[varname] = varval
                            
        q.put(d)                
    except ImportError, e:
        q.put(Exception('Error importing module: %s' % str(e)))
    except Exception, e:
        q.put(e)


def load_module_data(module_path, module_name):
    """Load module in subprocess and return dict of values"""
    q = Queue()
    
    p = Process(target=_load_module_data, args=(q, module_path, module_name))        
    p.start()
    p.join()
    
    while not q.empty():
        r = q.get()
        if isinstance(r, Exception):
            raise r
        return r


def make_project_config(global_config, name, title):
    """Compose project config"""
    project_config = DEFAULT_CONFIG.copy()
    
    project_config['DEFAULT_CONTEXT']['name'] = name
    project_config['DEFAULT_CONTEXT']['title'] = title
        
    if 'default_s3_buckets' in global_config \
    and global_config['default_s3_buckets'].keys():
        project_config['S3_BUCKETS'] = {}
        for k, v in global_config['default_s3_buckets'].iteritems():
            project_config['S3_BUCKETS'][k] = "%s/%s" % (v, name)
    
    return project_config


def write_project_config(project_path, project_config):
    """Write project config yaml"""
    yaml_path = os.path.join(project_path, 'tarbell_config.yaml')
    with open(yaml_path, 'w') as f:
        yaml.dump(project_config, f, default_flow_style=False)


def read_project_config(project_path):
    """
    Read project config.  First, try to load yaml.  Next, try to load
    config module in subprocess (to prevent conflicts) and write new
    yaml file with config information.  Else, return None.
    """
    yaml_path = os.path.join(project_path, 'tarbell_config.yaml')
    if os.path.exists(yaml_path):
        print '\tLoading yaml: %s' % yaml_path
        try:
            with open(yaml_path) as f:
                r = yaml.load(f)
                return r
        except Exception, e:
            raise Exception(
                'Error reading project config file "%s", %s' \
                % (yaml_path, str(e))) 

    module_path = os.path.join(project_path, 'tarbell_config.py')
    if os.path.exists(module_path):
        print '\tLoading module: %s' % module_path
        try:  
            r = load_module_data(project_path, 'tarbell_config')     
            write_project_config(project_path, r)
            return r
        except Exception, e:
            raise Exception(
                'Error loading project config module "%s", %s' \
                % (module_path, str(e)))
    
    return None

         
def list_projects(projects_dir):
    """Get a list of projects in directory."""
    path_prefix = os.path.expanduser(projects_dir)
    if not os.path.exists(path_prefix):
        raise Exception('Project directory does not exist: %s' % projects_dir)

    projects_list = []

    for directory in os.listdir(path_prefix):
        project_path = os.path.join(path_prefix, directory)
        print 'Examining %s' % project_path
        
        r = read_project_config(project_path)
        if r:
            projects_list.append(r)
               
    return projects_list


        
def _ve_subprocess(env_path, *argv):
    """
    Run command in virtual env using subprocess.Popen
    
    To wait for termination:
    
        proc = _ve_subprocess(...)
        (stdout_data, stderr_data) = proc.communicate()  
        if proc.returncode:
            # non-zero return code signifies error
            
    Else, call proc.poll() and check the return value.
    
        None    process is still running
        0       exited without error
        other   exited with error 
        
    For a non-zero return value, call proc.communicate as above and
    check stderr_data for any error output.
    """
    bin_path = os.path.join(env_path, 'bin')
    python_path = os.path.join(bin_path, 'python')
    script_path = os.path.join(TARBELL_PATH, 'cmd.py')
        
    # Make copy of current environment with PATH update
    env = os.environ.copy()
    env['PATH'] = '%s:%s' % (bin_path, os.environ["PATH"])

    args = [python_path, script_path]
    args.extend(argv)
    
    return subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env)   
  
def test_ve_subprocess():
    env_path = '/Users/jenny/.tarbell/env/sdakldjlj'
    print 'TESTING'
    print env_path
    
    proc = _ve_subprocess(env_path, 'test')
    (stdout_data, stderr_data) = proc.communicate()   
     
    if proc.returncode:
        raise Exception(
            'Error running ve test %s, %s [%d]' \
            % (env_path, stderr_data, proc.returncode))

 
def _install_requirements(env_path, file_path):
    """Install requirements in virtual env from file"""
    proc = _ve_subprocess(env_path, 'pip_install', file_path)
    (stdout_data, stderr_data) = proc.communicate()   
     
    if proc.returncode:
        raise Exception(
            'Error installing requirements from %s, %s [%d]' \
            % (file_path, stderr_data, proc.returncode))

    
def create_project_virtualenv(env_path):
    """Create virtual environment and install common requirements"""
    try:
        sh.virtualenv('--clear', env_path)
    except sh.ErrorReturnCode, e:
        raise Exception('Error creating virtual environment, %s' \
            % e.stderr.strip().split('\n')[-1])
               
    file_path = os.path.join(
        TARBELL_PATH, 'files', 'project_requirements.txt')
    _install_requirements(env_path, file_path)


def install_project_requirements(env_path, project_path):
    """Install project requirements in virtual environment"""   
    dir_list = [
        os.path.join(project_path, '_blueprint'),
        os.path.join(project_path, '_base'),
        project_path
    ]
    
    for dir in dir_list:
        file_path = os.path.join(dir, 'requirements.txt')      
        if os.path.exists(file_path):        
            _install_requirements(env_path, file_path)
            

def _add_user_to_file(file_id, service, user_email,
                      perm_type='user', role='writer'):
    """
    Grants the given set of permissions for a given file_id. service
    is an already-credentialed Google Drive service instance.
    """
    new_permission = {
        'value': user_email,
        'type': perm_type,
        'role': role
    }
    try:
        service.permissions()\
            .insert(fileId=file_id, body=new_permission)\
            .execute()
    except errors.HttpError, e :
        raise Exception(
            'Error adding users "%s" to spreadsheet, %s' \
            % (user_email, str(e)))
  

def create_project(env_path, project_path, blueprint, project_config):
    """Create a new project"""
    make_dir(project_path)

    try:        
        # Init repo
        git = sh.git.bake(_cwd=project_path)
        git.init()
        
        if blueprint.get('url'):
            # Create submodule
            git.submodule.add(blueprint['url'], '_blueprint')
            git.submodule.update(*['--init'])
            
            # Get submodule branches, switch to current version
            submodule = sh.git.bake(_cwd=os.path.join(project_path, '_blueprint'))
            submodule.fetch()
            submodule.checkout(VERSION)
                       
            # (handle spreadsheet stuff after)
            
            # Copy html files
            files = glob.iglob(os.path.join(project_path, "_blueprint", "*.html"))
            for file in files:
                if os.path.isfile(file):
                    dir, filename = os.path.split(file)
                    if not filename.startswith("_") and not filename.startswith("."):
                        shutil.copy2(file, project_path)
            ignore = os.path.join(project_path, "_blueprint", ".gitignore")
            if os.path.isfile(ignore):
                shutil.copy2(ignore, project_path)
        else:
            empty_index_path = os.path.join(project_path, "index.html")
            open(empty_index_path, "w")
        
        # Write config file(s)
        write_project_config(project_path, project_config)
        
        # Copy old-style tarbell_config for compatability with yaml
        file_path = os.path.join(TARBELL_PATH, 'files', 'tarbell_config.py')
        shutil.copy2(file_path, project_path)
                
        # Commmit
        git.add('.')
        git.commit(m='Created from {0}'.format(blueprint['name']))
        
        # Make virtual environment
        create_project_virtualenv(env_path)
        
        # Install requirements
        install_project_requirements(env_path, project_path)
       
        # TODO: Run newproject hook                        
    except Exception, e:
        delete_dir(project_path)
        raise e 
    

def delete_project(env_path, project_path):
    """Delete a project and its virtual environment"""
    try:
        delete_dir(project_path)
    except Exception ,e:
        raise Exception('Error deleting project directory, %s' \
            % str(e))
    
    if os.path.exists(env_path):
        try:
            delete_dir(env_path)
        except Exception ,e:
            raise Exception('Error deleting virtual environment, %s' \
                % str(e))
    
            
def run_project(env_path, project_path, ip, port):
    """Start preview server for a project"""
    return _ve_subprocess(env_path, 
        'run_project', project_path, ip, port)
    
    
def create_spreadsheet(spreadsheet_path, name, title, emails):
    """
    Create a new project spreadsheet
    spreadsheet_path = os.path.join(project_path, '_blueprint', '_spreadsheet.xlsx')
    https://docs.google.com/spreadsheet/ccc?key={0}
    """
    if not os.path.exists(spreadsheet_path):
        raise Exception('%s does not exist' % spreadsheet_path)
    
    media_body = _MediaFileUpload(
        spreadsheet_path, mimetype='application/vnd.ms-excel')
    
    body = {
        'title': '{0} (Tarbell)'.format(title),
        'description': '{0} ({1})'.format(title, name),
        'mimeType': 'application/vnd.ms-excel',
    }  
      
    service = get_drive_api()
    try:
        newfile = service.files()\
            .insert(body=body, media_body=media_body, convert=True)\
            .execute()
        if emails:
            for email in emails.split(","):
                _add_user_to_file(newfile['id'], service, user_email=email.strip())
            
        return newfile['id']
    except errors.HttpError, error:
        raise Exception('Error creating spreadsheet, %s' % str(error))



