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
import shutil
import tempfile
import StringIO
from .utils import puts

from flask import Flask, request, render_template, jsonify

from tarbell import __VERSION__ as VERSION
from .oauth import get_drive_api
from .contextmanagers import ensure_project
from .admin_utils import make_dir, delete_dir, install_requirements, \
    install_project, install_blueprint, \
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
        self.app.add_url_rule('/project/create/', view_func=self.project_create)
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
             
            data = install_blueprint(url, self.settings)
            
            return jsonify(data)

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
            
            name = clean_suffix(url.split("/").pop(), ".git")      
            path = self._get_path(name)
            
            install_project(url, path)
                   
            config = load_project_config(path)
                                 
            return jsonify({
                'directory': name, 
                'title': config.DEFAULT_CONTEXT.get("title", name)
            })
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
      
      
    def project_create(self):
        """Create project"""
        try:            
            name, title, blueprint = self._request_get('name', 'title', 'blueprint')
            spreadsheet_emails = request.args.get('spreadsheet_emails')            
            
            key = None
            path = self._get_path(name)   

            print 'name', name
            print 'title', title
            print 'blueprint', blueprint
            print 'google', spreadsheet_emails
            print 'mkdir', path        

            raise Exception('NOT IMPLEMENTED')

            make_dir(path)
            
            try:
                template = settings.config['project_templates'][int(blueprint) - 1]

                # Init repo
                git = sh.git.bake(_cwd=path)
                print(git.init())
            
                if template.get('url'):
                    # Create submodule
                    print(git.submodule.add(template['url'], '_blueprint'))
                    print(git.submodule.update(*['--init']))

                    # Get submodule branches, switch to current version
                    submodule = sh.git.bake(_cwd=os.path.join(path, '_blueprint'))
                    print(submodule.fetch())
                    print(submodule.checkout(VERSION))
 
                    # Create spreadsheet?
                    if spreadsheet_emails:
                        key = _create_spreadsheet(name, title, path, settings)
                   
                    # Copy html files
                    print "Copying html files..."
                    files = glob.iglob(os.path.join(path, "_blueprint", "*.html"))
                    for file in files:
                        if os.path.isfile(file):
                            dir, filename = os.path.split(file)
                            if not filename.startswith("_") and not filename.startswith("."):
                                print("Copying {0} to {1}".format(filename, path))
                                shutil.copy2(file, path)
                    ignore = os.path.join(path, "_blueprint", ".gitignore")
                    if os.path.isfile(ignore):
                        shutil.copy2(ignore, path)
                else:
                    empty_index_path = os.path.join(path, "index.html")
                    open(empty_index_path, "w")
                                         
                # Create config file
                _copy_config_template(name, title, template, path, key, settings)
                
                # Commit
                print(git.add('.'))
                print(git.commit(m='Created {0} from {1}'.format(name, template['name'])))   
                
                # Install requirements
                install_requirements(path, True) 
            except Exception, e:
                delete_dir(path)
                raise e

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
            project_path = self._get_path(project)

            with ensure_project(None, None, path=project_path) as site:                                
                git = sh.git.bake(_cwd=site.base.base_dir)
                git.fetch()
  
                puts(git.checkout(VERSION))
                puts(git.stash())                
                
                output = StringIO.StringIO()
                output.write(git.pull('origin', VERSION))
                resp = output.getvalue()
                output.close()
                
                puts(resp)
                
            return jsonify({'msg': resp})    
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
        
