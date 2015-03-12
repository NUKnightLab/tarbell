# -*- coding: utf-8 -*-
import json
from flask import Flask, render_template
from .oauth import get_drive_api

class TarbellAdminSite:
    def __init__(self, settings,  quiet=False):
        self.settings = settings
        
        self.app = Flask(__name__)
        self.app.debug = True  # Always debug
        self.app.add_url_rule('/', view_func=self.main)
        
        api = get_drive_api()
        print api.credentials
        print api.credentials.to_json()
        self.credentials = json.loads(api.credentials.to_json())
        print type(self.credentials)

    def main(self):
    
        project_list = [{'name': 'ethelpayne', 'title': 'Ethel Payne: A life in jounalism'}]
        
        return render_template('admin.html', 
            config=self.settings.config, 
            credentials=self.credentials,
            project_list=project_list)

