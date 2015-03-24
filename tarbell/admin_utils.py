# -*- coding: utf-8 -*-

"""
tarbell.admin_utils
~~~~~~~~~

This module provides utilities for Tarbell cli and admin.
"""

import codecs
import glob
import imp
import jinja2
import os
import pkg_resources
import sh
import shutil
import sys
import tempfile

from apiclient.http import MediaFileUpload as _MediaFileUpload
from clint.textui import colored

from tarbell import __VERSION__ as VERSION

from .app import pprint_lines, process_xlsx, copy_global_values
from .oauth import get_drive_api
from .contextmanagers import ensure_settings, ensure_project
from .utils import clean_suffix, puts, is_werkzeug_process


def _DeviceNotConfigured():
    raise Exception('' \
        'Git tried to prompt for a username or password.\n\n' \
        'Tarbell doesn\'t support interactive sessions.  ' \
        'Please configure ssh key access to your Git repository.  ' \
        '(See https://help.github.com/articles/generating-ssh-keys/)')


def make_dir(path):
    """Make a directory or raise Exception"""
    try:
        os.mkdir(path)
    except OSError, e:
        if e.errno == 17:
            raise Exception("Directory {0} already exists.".format(path))
        else:
            raise Exception("OSError {0}.".format(e))
         
def delete_dir(path):
    """Delete directory"""
    try:
        shutil.rmtree(path)
    except OSError as exc:
        if exc.errno != 2:  # code 2 - no such file or directory
            raise  # re-raise exception
    except UnboundLocalError:
        pass


def install_requirements(path):
    """Install requirements.txt"""
    locations = [os.path.join(path, "_blueprint"), os.path.join(path, "_base"), path] 
    success = True
    force = is_werkzeug_process() # no interactivity if running admin GUI
    
    for location in locations:
        try:
            with open(os.path.join(location, "requirements.txt")):
                if not force:
                    puts("\nRequirements file found at {0}".format(os.path.join(location, "requirements.txt")))
                    install_reqs = raw_input("Install requirements now with pip install -r requirements.txt? [Y/n] ")
                   
                if force or not install_reqs or install_reqs.lower() == 'y':
                    pip = sh.pip.bake(_cwd=location)                    
                    puts("\nInstalling requirements...")
                    puts(pip("install", "-r", "requirements.txt"))
                else:
                    success = False
                    puts("Not installing requirements. This may break everything! Vaya con dios.")                                             
        except IOError:
            pass
            
    return success
    

def copy_config_template(name, title, template, path, key, settings):
    """Get and render tarbell_config.py.template from blueprint"""       
    puts("\nCopying configuration file")
    context = settings.config
    context.update({
        "default_context": {
            "name": name,
            "title": title,
        },
        "name": name,
        "title": title,
        "template_repo_url": template.get('url'),
        "key": key,
    })

    if not key:
        spreadsheet_path = os.path.join(path, '_blueprint/', '_spreadsheet.xlsx')
        try:
            with open(spreadsheet_path, "rb") as f:
                puts("Copying _blueprint/_spreadsheet.xlsx to tarbell_config.py's DEFAULT_CONTEXT") 
                data = process_xlsx(f.read())
                if 'values' in data:
                    data = copy_global_values(data)
                context["default_context"].update(data)
        except IOError:
            pass

    s3_buckets = settings.config.get("s3_buckets")
    if s3_buckets:
        puts("")
        for bucket, bucket_conf in s3_buckets.items():
            puts("Configuring {0} bucket at {1}\n".format(
                colored.green(bucket),
                colored.yellow("{0}/{1}".format(bucket_conf['uri'], name))
            ))

    puts("\n- Creating {0} project configuration file".format(
        colored.cyan("tarbell_config.py")
    ))
    template_dir = os.path.dirname(pkg_resources.resource_filename(
        "tarbell", "templates/tarbell_config.py.template"))
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader)
    env.filters["pprint_lines"] = pprint_lines  # For dumping context
    content = env.get_template('tarbell_config.py.template').render(context)
    codecs.open(os.path.join(path, "tarbell_config.py"), "w", encoding="utf-8").write(content)
    puts("\n- Done copying configuration file")
 
 
def load_project_config(project_path):
    """Load project tarbell config"""
    filename, pathname, description = imp.find_module('tarbell_config', [project_path])
    return imp.load_module(os.path.dirname(project_path), filename, pathname, description)
        
        
def list_projects(projects_dir):
    """List projects"""
    projects_list = []

    for directory in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, directory)
        try:
            config = load_project_config(project_path)
            title = config.DEFAULT_CONTEXT.get("title", directory)
            projects_list.append({'directory': directory, 'title': title})
        except ImportError:
            pass
    
    return projects_list
    
    
def install_blueprint(blueprint_url, settings):
    """
    Install blueprint
    """
    matches = [b for b in settings.config["project_templates"] if b.get("url") == blueprint_url]
    if matches:
        raise Exception('Blueprint already exists.  Nothing to do.')
    
    tempdir = tempfile.mkdtemp()
    try:
        puts("\nInstalling {0}".format(colored.cyan(blueprint_url)))
        puts("\n- Cloning repo")
        git = sh.git.bake(_cwd=tempdir, _tty_in=True, _tty_out=False, _err_to_out=True)
        puts(git.clone(blueprint_url, '.'))
        puts(git.fetch())
        puts(git.checkout(VERSION))

        install_requirements(tempdir)

        filename, pathname, description = imp.find_module('blueprint', [tempdir])
        blueprint = imp.load_module('blueprint', filename, pathname, description)
        puts("\n- Found _blueprint/blueprint.py")
        
        try:
            name = blueprint.NAME
            puts("\n- Name specified in blueprint.py: {0}".format(colored.yellow(name)))
        except AttributeError:
            name = blueprint_url.split("/")[-1]
            puts("\n- No name specified in blueprint.py, using '{0}'".format(colored.yellow(name)))
            
        data = {"name": name, "url": blueprint_url}
        settings.config["project_templates"].append(data)
        settings.save()

        return data
    except ImportError:
        raise Exception('No blueprint.py found')
    except sh.ErrorReturnCode_128, e:
        if e.stdout.strip('\n').endswith('Device not configured'):
            _DeviceNotConfigured()
        else:
            raise Exception('Not a valid repository or Tarbell project')
    finally:
        delete_dir(tempdir)
 
     
def install_project(project_url, project_path):
    """
    Install project at project_url to project_path
    """
    error = None
    
    tempdir = tempfile.mkdtemp()
    
    try:
        testgit = sh.git.bake(_cwd=tempdir, _tty_in=True, _tty_out=False) # _err_to_out=True)
        puts(testgit.clone(project_url, '.', '--depth=1', '--bare'))
        testgit.show("HEAD:tarbell_config.py")
        puts("\n- Found tarbell_config.py")
 
        make_dir(project_path)
        git = sh.git.bake(_cwd=project_path)
        puts(git.clone(project_url, '.', _tty_in=True, _tty_out=False, _err_to_out=True))
        puts(git.submodule.update('--init', '--recursive', _tty_in=True, _tty_out=False, _err_to_out=True))
        
        install_requirements(project_path)

        return git # for hooks
    except sh.ErrorReturnCode_128, e:
        if e.message.endswith('Device not configured\n'):
            _DeviceNotConfigured()
        else:
            error = 'Not a valid repository or Tarbell project'
        raise Exception(error)
    except Exception, e:
        raise e
    finally:
        delete_dir(tempdir)
        
                   
def _add_user_to_file(file_id, service, user_email, perm_type='user', role='writer'):
    """
    Grants the given set of permissions for a given file_id. service is an
    already-credentialed Google Drive service instance.
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
    except errors.HttpError, e:
        raise Exception('Error adding users to spreadsheet: {0}'.format(e))

  
def _create_spreadsheet(path, name, title, emails, settings):
    """Create Google spreadsheet"""    
    try:
        media_body = _MediaFileUpload(
            os.path.join(path, '_blueprint/_spreadsheet.xlsx'),
            mimetype='application/vnd.ms-excel')
    except IOError:
        show_error("_blueprint/_spreadsheet.xlsx doesn't exist!")
        return None
    
    service = get_drive_api()
    body = {
        'title': '{0} (Tarbell)'.format(title),
        'description': '{0} ({1})'.format(title, name),
        'mimeType': 'application/vnd.ms-excel',
    }
    try:
        newfile = service.files()\
            .insert(body=body, media_body=media_body, convert=True).execute()
        for email in emails.split(","):
            _add_user_to_file(newfile['id'], service, user_email=email.strip())

        puts("\n{0}! View the spreadsheet at {1}".format(
            colored.green("Success"),
            colored.yellow("https://docs.google.com/spreadsheet/ccc?key={0}".format(newfile['id']))
        ))        
        return newfile['id']
    except errors.HttpError, e:
        raise Exception('An error occurred creating spreadsheet: {0}'.format(str(e)))


def _copy_blueprint_files(project_path):
    """Copy blueprint html files"""
    puts(colored.green("\nCopying html files..."))
    files = glob.iglob(os.path.join(project_path, "_blueprint", "*.html"))
    for file in files:
        if os.path.isfile(file):
            dir, filename = os.path.split(file)
            if not filename.startswith("_") and not filename.startswith("."):
                puts("Copying {0} to {1}".format(filename, project_path))
                shutil.copy2(file, project_path)
    ignore = os.path.join(project_path, "_blueprint", ".gitignore")
    if os.path.isfile(ignore):
        shutil.copy2(ignore, project_path)
    

def create_project(path, name, title, template, emails, settings):
    """Create a project"""
    key = None
    
    # Init repo
    git = sh.git.bake(_cwd=path)
    puts(git.init())

    if template.get("url"):       
        # Create blueprint submodule
        puts(git.submodule.add(template['url'], '_blueprint'))
        puts(git.submodule.update(*['--init']))

        # Get submodule branches, switch to current version
        submodule = sh.git.bake(_cwd=os.path.join(path, '_blueprint'))
        puts(submodule.fetch())
        puts(submodule.checkout(VERSION))
        
        # Create spreadsheet?
        if emails:
            key = _create_spreadsheet(path, name, title, emails, settings)

        # Copy blueprint html files
        _copy_blueprint_files(path)
    else:
        # Create empty index.html
        empty_index_path = os.path.join(path, "index.html")
        open(empty_index_path, "w")

    # Create config file
    copy_config_template(name, title, template, path, key, settings)

    # Commit
    puts(colored.green("\nInitial commit"))
    puts(git.add('.'))
    puts(git.commit(m='Created {0} from {1}'.format(name, template['name'])))

    # Install requirements
    install_requirements(path)
    
    return git  # for hooks
    

