# -*- coding: utf-8 -*-

"""
tarbell.admin_utils
~~~~~~~~~

This module provides utilities for Tarbell cli and admin.
"""

import os
import sys
import imp
import shutil
import sh
import pkg_resources
import tempfile

from apiclient.http import MediaFileUpload as _MediaFileUpload
from clint.textui import colored

from tarbell import __VERSION__ as VERSION

from .app import process_xlsx, copy_global_values
from .contextmanagers import ensure_settings, ensure_project
from .oauth import get_drive_api
from .utils import puts

def clean_suffix(string, suffix):
    """If string endswith the suffix, remove it. Else leave it alone"""
    suffix_len = len(suffix)

    if len(string) < suffix_len:
        # the string param was shorter than the suffix
        raise ValueError("A suffix can not be bigger than string argument.")
    if string.endswith(suffix):
        # return from the beginning up to
        # but not including the first letter
        # in the suffix
        return string[0:-suffix_len]   
    else:
        # leave unharmed
        return string

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


def install_requirements(path, force=False):
    """Install requirements.txt"""
    locations = [os.path.join(path, "_blueprint"), os.path.join(path, "_base"), path] 
    success = True
    
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
    template_dir = os.path.dirname(pkg_resources.resource_filename("tarbell", "templates/tarbell_config.py.template"))
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
    

def _add_user_to_file(file_id, service, user_email, 
    perm_type='user', role='writer'):
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
    except errors.HttpError, error:
        raise Exception('Error adding users to spreadsheet: {0}'.format(error))

    
def create_spreadsheet(name, title, path, settings, emails):
    """Create Google spreadsheet"""
    if not emails:
        emails = settings.config.get('google_account')
    
    try:
        media_body = _MediaFileUpload(
            os.path.join(path, '_blueprint/_spreadsheet.xlsx'),
            mimetype='application/vnd.ms-excel')
    except IOError:
        print "_blueprint/_spreadsheet.xlsx doesn't exist!"
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
        
        print "https://docs.google.com/spreadsheet/ccc?key={0}".format(newfile['id'])
        return newfile['id']
    except errors.HttpError, error:
        raise Exception('Error occurred creating spreadsheet: {0}'.format(error))
    

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
            raise Exception('Git tried to prompt for a username or password.' \
                + '  Tarbell doesn\'t support interactive sessions.' \
                + '  Please configure ssh key access to your Git repository.' \
                + '  (See https://help.github.com/articles/generating-ssh-keys/)')
        else:
            raise Exception('Not a valid repository or Tarbell project')
    finally:
        delete_dir(tempdir)
 
     
def install_project(project_url, project_path, command=None, args=None):
    """
    Install project at project_url to project_path
    """
    error = None
    
    # Create a tempdir and clone
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

        if command:
            with ensure_project(command, args, project_path) as site:
                site.call_hook("install", site, git)

    except sh.ErrorReturnCode_128, e:
        if e.message.endswith('Device not configured\n'):
            error = 'Git tried to prompt for a username or password.\n\n' \
                'Tarbell doesn\'t support interactive sessions.  ' \
                'Please configure ssh key access to your Git repository.  ' \
                '(See https://help.github.com/articles/generating-ssh-keys/)'
        else:
            error = 'Not a valid repository or Tarbell project'
        raise Exception(error)
    except Exception, e:
        raise e
    finally:
        delete_dir(tempdir)

