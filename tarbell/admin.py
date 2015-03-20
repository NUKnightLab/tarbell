# -*- coding: utf-8 -*-
"""
This module provides a web-based GUI interface to tarbell.
"""
import traceback
import os
import json
import multiprocessing
import imp
import time
import requests
import re
import sh
import tempfile

from flask import Flask, request, render_template, jsonify

from tarbell import __VERSION__ as VERSION
from .oauth import get_drive_api
from .contextmanagers import ensure_project
from .admin_utils import make_dir, delete_dir, install_requirements, \
    load_project_config, list_projects, clean_suffix

class TarbellAdminSite:
    def __init__(self, settings,  quiet=False):
        self.settings = settings
        
        self.p = None

        api = get_drive_api()       
        self.credentials = json.loads(api.credentials.to_json())
        
        self.app = Flask(__name__)
        self.app.debug = True  # Always debug
        
        # Add routes
        self.app.add_url_rule('/', view_func=self.main)   

        self.app.add_url_rule('/exists/', view_func=self.exists)
        
        self.app.add_url_rule('/configuration/save/', view_func=self.configuration_save)   

        self.app.add_url_rule('/blueprint/install/', view_func=self.blueprint_install)
             
        self.app.add_url_rule('/project/install/', view_func=self.project_install)
        self.app.add_url_rule('/project/run/', view_func=self.project_run)
        self.app.add_url_rule('/project/stop/', view_func=self.project_stop)
        self.app.add_url_rule('/project/update/', view_func=self.project_update)
        self.app.add_url_rule('/project/generate/', view_func=self.project_generate)
        self.app.add_url_rule('/project/publish/', view_func=self.project_publish)
        

    def _get_path(self, name):
        return os.path.join(self.settings.config.get('projects_path'), name)
      
    def _request_get(self, *keys):
        """Verify existence of request data and return values"""
        if request.method == 'POST':
            obj = request.form
        else:
            obj = request.args
        values = []
        for k in keys:
            v = obj.get(k)
            if not v:
                raise Exception('Expected "%s" parameter' % k)
            values.append(v)
        if len(values) > 1:
            return values
        return values[0]
          
    #
    # Main view
    # 
     
    def main(self):
        project_list = list_projects(self.settings.config.get('projects_path'))

        return render_template('admin.html', 
            version=VERSION,
            config=self.settings.config, 
            credentials=self.credentials,
            project_list=project_list)

    #
    # Utility
    #
    
    def exists(self):
        """Check if a path exists"""
        try:
            path = self._request_get('path')
            return jsonify({'exists': os.path.exists(path)})            
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})


    #
    # Configuration
    #
    
    def configuration_save(self):
        try:
            raise Exception('Not implemented yet')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
            
    #
    # Blueprints
    #
    
    def blueprint_install(self):
        """
        Install blueprint
        test URL: https://github.com/jywsn/test-blueprint      
        """
        try:
            url = self._request_get('url')
             
            matches = [b for b in self.settings.config["project_templates"] if b.get("url") == url]
            if matches:
                raise Exception('Blueprint already exists.  Nothing to do.')
                
            try:
                print 'Installing %s' % url
                tempdir = tempfile.mkdtemp()

                print 'Cloning repo'
                git = sh.git.bake(_cwd=tempdir, _tty_in=True, _tty_out=False, _err_to_out=True)
                git.clone(url, '.')
                git.fetch()
                git.checkout(VERSION)

                print 'Installing requirements'
                install_requirements(tempdir)

                print 'Loading blueprint module'
                filename, pathname, description = imp.find_module('blueprint', [tempdir])
                blueprint = imp.load_module('blueprint', filename, pathname, description)            
                print 'Found _blueprint/blueprint.py'
                
                try:
                    name = blueprint.NAME
                    print 'Name specified in blueprint.py: %s' % name
                except AttributeError:
                    name = url.split("/")[-1]   
                    print 'No name specified in blueprint.py, using "%s"' % name
               
                data = {"name": name, "url": url} 
                self.settings.config["project_templates"].append(data)
                self.settings.save()

                return jsonify(data)
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

        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
  
    #
    # Projects
    #

    def _project_run(self, project_path, ip, port):
        with ensure_project('serve', [], path=project_path) as site:
            site.app.run(ip, port=port, use_reloader=False)
 
    def _project_stop(self):
        if self.p:
            self.p.terminate()
            self.p = None
    
    def project_install(self):
        """
        Install project
        test URL: https://github.com/jywsn/testproject
        """
        try:
            url = self._request_get('url')
            
            name = url.split("/").pop()
            if not name:
                raise Exception('Could not determine project name from url')
            name = clean_suffix(name, ".git")
                        
            tempdir = tempfile.mkdtemp()
            
            print name, url, tempdir
            
            try:
                testgit = sh.git.bake(_cwd=tempdir, _tty_in=True, _tty_out=False) # _err_to_out=True)
                testclone = testgit.clone(url, '.', '--depth=1', '--bare')
                print testclone
                
                print testgit.show("HEAD:tarbell_config.py")
                                             
                path = self._get_path(name)
                print path
                
                make_dir(path)
                
                git = sh.git.bake(_cwd=path)
                print git.clone(url, '.', _tty_in=True, _tty_out=False, _err_to_out=True)
                print git.submodule.update('--init', '--recursive', _tty_in=True, _tty_out=False, _err_to_out=True)

                install_requirements(path)

                # Get site, run hook
                with ensure_project(None, None, path) as site:
                    site.call_hook("install", site, git)
                  
                # Load new project config
                config = load_project_config(path)
                                 
                return jsonify({
                    'directory': name, 
                    'title': config.DEFAULT_CONTEXT.get("title", name)
                })
            except sh.ErrorReturnCode_128, e:
                if e.message.endswith('Device not configured\n'):
                    raise Exception('Git tried to prompt for a username or password.' \
                        + '  Tarbell doesn\'t support interactive sessions.' \
                        + '  Please configure ssh key access to your Git repository.' \
                        + '  (See https://help.github.com/articles/generating-ssh-keys/)')
                else:
                    raise Exception('Not a valid repository or Tarbell project')
            finally:
                delete_dir(tempdir)
 
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
           
    def project_run(self):
        try:
            project, address = self._request_get('project', 'address')

            m = re.match(r'([\w.]+):(\d+)', address)   
            if not m:
                raise Exception('Invalid "address" parameter')

            project_path = self._get_path(project)
            ip = m.group(1)
            port = m.group(2)
                       
            self.p = multiprocessing.Process(target=self._project_run, 
                args=(project_path, ip, port))
            self.p.start()
            
            # Wait for server to come up...            
            for i in [1, 2, 3]:
                time.sleep(2)
                
                try:
                    print 'Waiting for server...', 'http://'+address
                    r = requests.get('http://'+address, timeout=3)
                
                    if r.status_code == requests.codes.ok:
                        return jsonify({})                       
                except requests.exceptions.ConnectionError, e:
                    print 'ERROR', e
                            
            raise Exception('Could not start preview server')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
            
    def project_stop(self):
        try:
            self._project_stop()
            return jsonify({})
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
    
    def project_update(self):
        try:
            project = self._request_get('project')

            raise Exception('Not implemented yet')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
      
                  
    def project_generate(self):
        """
        Generate static files
        Assumes GUI has already confirmed overwrite (if applicable)
        """
        try:
            project = self._request_get('project')
   
            project_path = self._get_path(project)
                
            output_path = request.args.get('path')

            with ensure_project(None, None, path=project_path) as site:                                
                if not output_path:
                    output_path = tempfile.mkdtemp(prefix="{0}-".format(site.project.__name__))
                
                if os.path.exists(output_path):
                    delete_dir(output_path)
                    
                site.generate_static_site(output_path, None)
                site.call_hook("generate", site, output_path, True)
     
            return jsonify({'path': output_path})           
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})

    def project_publish(self):
        try:
            project, bucket = self._request_get('project', 'bucket')

            raise Exception('Not implemented yet')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
        
