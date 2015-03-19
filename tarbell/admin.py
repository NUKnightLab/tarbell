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

from flask import Flask, request, render_template, jsonify
from .oauth import get_drive_api
from .contextmanagers import ensure_project

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
        self.app.add_url_rule('/project/run/', view_func=self.run_server)
        self.app.add_url_rule('/project/stop/', view_func=self.stop_server)
        

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
    # Run project
    #
    
    def _run_server(self, project_path, ip, port):
        print 'DEBUG', '_run_server', ip, port
        with ensure_project('serve', [], path=project_path) as site:
            site.app.run(ip, port=port, use_reloader=False)
 
    def _stop_server(self):
        print 'DEBUG', '_stop_server'
        if self.p:
            self.p.terminate()
            self.p = None
 
           
    def run_server(self):
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
                       
            self.p = multiprocessing.Process(target=self._run_server, 
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
            
    def stop_server(self):
        print 'DEBUG', 'stop_server'
        try:
            self._stop_server()
            return jsonify({})
        except Exception, e:
            traceback.print_exc()
            return jsonify({'error': str(e)})
        

