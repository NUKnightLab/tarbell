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
from clint.textui import colored

from apiclient.http import MediaFileUpload as _MediaFileUpload
from apiclient import errors


from oauth2client import client
from oauth2client import keyring_storage

from .oauth import OAUTH_SCOPE, get_drive_api
from .utils import puts

from tarbell import __VERSION__ as VERSION

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

def _make_dir(path):
    """Create directory"""
    try:
        os.mkdir(path)        
    except OSError, e:
        if e.errno == 16:
            raise Exception('Error creating directory "%s", already exists' % path)
        else:
            raise Exception('Error creating directory "%s", %s' % (path, str(e)))

def _delete_dir(path):
    """Delete directory"""
    try:
        shutil.rmtree(path)
    except OSError, e:
        if e.errno != 2:  # code 2 - no such file or directory
            raise Exception(str(e))
    except UnboundLocalError:
        pass
        

def write_project_config(project_path, project_config):
    """Write project config yaml"""
    yaml_path = os.path.join(project_path, 'tarbell_config.yaml')
    print 'writing project_config', yaml_path
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
    """Run command in virtual env using subprocess.Popen"""
    this_path = os.path.dirname(os.path.abspath(__file__))
        
    bin_path = os.path.join(env_path, 'bin')
    python_path = os.path.join(bin_path, 'python')
    script_path = os.path.join(this_path, 'cmd.py')
    
    # DEBUG
    print 'bin_path', bin_path
    print 'python_path', python_path
    print 'script_path', script_path
    
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
  
    
def create_virtualenv(env_path):
    """Create virtual environment"""
    try:
        sh.virtualenv('--clear', env_path)
    except sh.ErrorReturnCode, e:
        raise Exception('Error creating virtual environment, %s' \
            % e.stderr.strip().split('\n')[-1])


def install_requirements(env_path, project_path):
    """Install project requirements in virtual environment"""   
    dir_list = [
        os.path.join(project_path, '_blueprint'),
        os.path.join(project_path, '_base'),
        project_path
    ]
    
    for dir in dir_list:
        file_path = os.path.join(dir, 'requirements.txt')      
        if os.path.exists(file_path):        
            proc = _ve_subprocess(env_path, 'pip_install', file_path)
            (stdout_data, stderr_data) = proc.communicate()   
             
            if proc.returncode:
                raise Exception(
                    'Error installing requirements from %s, %s [%d]' \
                    % (file_path, stderr_data, proc.returncode))


def make_project_config(global_config, name, title):
    project_config = DEFAULT_CONFIG.copy()
    
    project_config['DEFAULT_CONTEXT']['name'] = name
    project_config['DEFAULT_CONTEXT']['title'] = title
        
    if 'default_s3_buckets' in global_config \
    and global_config['default_s3_buckets'].keys():
        project_config['S3_BUCKETS'] = {}
        for k, v in global_config['default_s3_buckets'].iteritems():
            project_config['S3_BUCKETS'][k] = "%s/%s" % (v, name)
    
    return project_config
            


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
    except errors.HttpError, error:
        show_error('An error adding users to spreadsheet: {0}'.format(error))


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
        for email in emails.split(","):
            _add_user_to_file(newfile['id'], service, user_email=email.strip())
            
        return newfile['id']
    except errors.HttpError, error:
        raise Exception('Error creating spreadsheet, %s' % str(error))
  
        
def create_project(env_path, project_path, blueprint, project_config):
    """Create a new project"""
    _make_dir(project_path)

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
        
        # Create config file(s)
        write_project_config(project_path, project_config)
        
        # Commmit
        git.add('.')
        git.commit(m='Created from {0}'.format(blueprint['name']))
        
        # Make virtual environment
        create_virtualenv(env_path)
        
        # Install requirements
        install_requirements(env_path, project_path)
       
        # TODO: Run newproject hook                        
    except Exception, e:
        _delete_dir(project_path)
        raise e 
    
      
def run_project(env_path, project_path, ip, port):
    """Start preview server for a project"""
    return _ve_subprocess(env_path, 
        'run_project', project_path, ip, port)
    
    

#
# -------------
#

def props(obj):
    """
    Return object as dictionary
    Only gets attributes set on the instance, not on the class!
    """
    return dict((key, value) \
        for key, value in obj.__dict__.iteritems() \
        if not callable(value) and not key.startswith('__'))

def backup(path, filename):
    """Backup a file"""
    target = os.path.join(path, filename)
    if os.path.isfile(target):
        dt = datetime.now()
        new_filename = ".{0}.{1}.{2}".format(
            filename, dt.isoformat(), "backup"
        )
        destination = os.path.join(path, new_filename)
        print("- Backing up {0} to {1}".format(
            colored.cyan(target),
            colored.cyan(destination)
        ))
        shutil.copy(target, destination)

def safe_write(data, path, backup_existing=True):
    """Write data to path.  If path exists, backup first"""
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    
    if backup_existing and os.path.exists(path):
        backup(dirname, filename)
    
    print 'Writing %s' % path
    with open(path, 'w+') as f:
        f.write(data)
         
def get_or_create_config(path):
    """Get or create a tarbell configuration directory"""
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)

    try:
        os.makedirs(dirname)
    except OSError:
        pass

    try:
        with open(path, 'r+') as f:
            if os.path.isfile(path):
                puts("{0} already exists, backing up".format(colored.green(path)))
                backup(dirname, filename)
            return yaml.load(f)
    except IOError:
        return {}
    
def load_module_dict(module_name, module_path):
    """
    Load module as a dictionary
    This works fine as long as the module doesn't import other modules!
    """
    filename, pathname, description = imp.find_module(module_name, [module_path])
    m = imp.load_module(os.path.dirname(module_path), filename, pathname, description)
    
    d = dict([(varname, getattr(m, varname)) \
        for varname in dir(m) if not varname.startswith("_") ]) 

    del sys.modules[m.__name__]
    return d

def client_secrets_authorize_url(client_secrets_path):  
    """Get the client_secrets authorization url"""
    flow = client.flow_from_clientsecrets(client_secrets_path, \
        scope=OAUTH_SCOPE, redirect_uri=client.OOB_CALLBACK_URN)
    return flow.step1_get_authorize_url()

def client_secrets_authorize(client_secrets_path, code):
    """Authorize client_secrets"""
    flow = client.flow_from_clientsecrets(client_secrets_path, \
        scope=OAUTH_SCOPE, redirect_uri=client.OOB_CALLBACK_URN)

    try:
        storage = keyring_storage.Storage('tarbell', getpass.getuser())
        credentials = flow.step2_exchange(code, http=httplib2.Http())
        storage.put(credentials)        
    except client.FlowExchangeError, e:
        raise Exception('Authentication failed: %s' % e)    
