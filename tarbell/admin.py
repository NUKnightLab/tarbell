# -*- coding: utf-8 -*-
import traceback
import os
import json
import multiprocessing
import imp

from flask import Flask, render_template, jsonify
from .oauth import get_drive_api
from .contextmanagers import ensure_project

class TarbellAdminSite:
    def __init__(self, settings,  quiet=False):
        self.settings = settings
        
        self.p = None   
        
        self.app = Flask(__name__)
        self.app.debug = True  # Always debug
        
        self.app.add_url_rule('/', view_func=self.main)
        
        self.app.add_url_rule('/project/run/<project>/', view_func=self.run_server)
        self.app.add_url_rule('/project/stop/', view_func=self.stop_server)
        
        api = get_drive_api()
        print api.credentials
        print api.credentials.to_json()
       
        self.credentials = json.loads(api.credentials.to_json())
        print type(self.credentials)

    def main(self):
    
        project_list = [{'name': 'ethelpayne', 'title': 'Ethel Payne: A life in jounalism'}]
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
    # Run project
    #
    
    def _run_server(self, project_path):
        with ensure_project('serve', [], path=project_path) as site:
            site.app.run('0.0.0.0', port=5000, use_reloader=False)
 
    def run_server(self, project):
        print 'run_server'
        try:
            project_path = os.path.join(
                self.settings.config.get('projects_path'), project)
            print project_path
            self.p = multiprocessing.Process(
                target=self._run_server, args=(project_path,))
            self.p.start()
            return jsonify({})
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
            
    def stop_server(self):
        print 'stop_server'
        try:
            if self.p:
                self.p.terminate()
            return jsonify({})
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
        

