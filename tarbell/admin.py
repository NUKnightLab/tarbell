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

from .admin_utils import delete_dir, install_requirements

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

        self.app.add_url_rule('/blueprint/install/', view_func=self.blueprint_install)
             
        self.app.add_url_rule('/project/install/', view_func=self.project_install)
        self.app.add_url_rule('/project/run/', view_func=self.project_run)
        self.app.add_url_rule('/project/stop/', view_func=self.project_stop)
        self.app.add_url_rule('/project/update/', view_func=self.project_update)
        self.app.add_url_rule('/project/generate/', view_func=self.project_generate)
        self.app.add_url_rule('/project/publish/', view_func=self.project_publish)
        

    #
    # Main view
    # 
     
    def main(self):
        project_list = []
        
        projects_path = self.settings.config.get('projects_path')
        for directory in os.listdir(projects_path):
            project_path = os.path.join(projects_path, directory)
            try:
                filename, pathname, description = imp.find_module('tarbell_config', [project_path])
                config = imp.load_module(directory, filename, pathname, description)
                title = config.DEFAULT_CONTEXT.get("title", directory)
                project_list.append({'directory': directory, 'title': title})
            except ImportError:
                pass
         
        return render_template('admin.html', 
            config=self.settings.config, 
            credentials=self.credentials,
            project_list=project_list)

    #
    # Blueprints
    #
    
    def blueprint_install(self):
        """
        Install blueprint
        test URL: https://github.com/hbillings/tarbell-tutorial-template
        
        """
        try:
            url = request.args.get('url')
            if not url:
                raise Exception('Expected "url" parameter')
            
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
                
                self.settings.config["project_templates"].append(
                    {"name": name, "url": url})
                self.settings.save()

                return jsonify({"name": name, "url": url})

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
        print 'DEBUG', '_project_run', ip, port
        with ensure_project('serve', [], path=project_path) as site:
            site.app.run(ip, port=port, use_reloader=False)
 
    def _project_stop(self):
        print 'DEBUG', '_project_stop'
        if self.p:
            self.p.terminate()
            self.p = None
    
    def project_install(self):
        try:
            raise Exception('Not implemented yet')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
           
    def project_run(self):
        print 'DEBUG', 'run_server'
        try:
            project = request.args.get('project')
            if not project:
                raise Exception('Expected "project" parameter')
              
            address = request.args.get('address')
            if not address:
                raise Exception('Expected "address" parameter')
            m = re.match(r'([\w.]+):(\d+)', address)   
            if not m:
                raise Exception('Invalid "address" parameter')

            project_path = os.path.join(
                self.settings.config.get('projects_path'), project)
            ip = m.group(1)
            port = m.group(2)
                       
            self.p = multiprocessing.Process(target=self._project_run, 
                args=(project_path, ip, port))
            self.p.start()
            
            # Wait for server to come up...            
            for i in [1, 2, 3]:
                time.sleep(2)
                
                try:
                    print 'Waiting for server...'
                    r = requests.get('http://127.0.0.1:5000', timeout=3)
                
                    if r.status_code == requests.codes.ok:
                        return jsonify({})                       
                except requests.exceptions.ConnectionError, e:
                    print 'ERROR', e
                            
            raise Exception('Could not start preview server')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
            
    def project_stop(self):
        print 'DEBUG', 'project_stop'
        try:
            self.project_stop()
            return jsonify({})
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
    
    def project_update(self):
        try:
            raise Exception('Not implemented yet')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
            
    def project_generate(self):
        try:
            raise Exception('Not implemented yet')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})

    def project_publish(self):
        try:
            raise Exception('Not implemented yet')
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
        
