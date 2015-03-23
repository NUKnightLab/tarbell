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
 
    for location in locations:
        try:
            with open(os.path.join(location, "requirements.txt")):
                if not force:
                    puts("\nRequirements file found at {0}".format(os.path.join(location, "requirements.txt")))
                    install_reqs = raw_input("Install requirements now with pip install -r requirements.txt? [Y/n] ")
                    
                    if install_reqs and install_reqs.lower() != 'y':
                        puts("Not installing requirements. This may break everything! Vaya con dios.")
                        return False
                      
                    pip = sh.pip.bake(_cwd=location)                    
                    puts("\nInstalling requirements...")
                    puts(pip("install", "-r", "requirements.txt"))
        except IOError:
            pass

    return True
 
 
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
