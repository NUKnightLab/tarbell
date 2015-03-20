# -*- coding: utf-8 -*-

"""
tarbell.admin_utils
~~~~~~~~~

This module provides utilities for Tarbell cli and admin.
"""

import os
import sys
import shutil
import sh

from .utils import puts

def delete_dir(dir):
    """Delete dir"""
    try:
        shutil.rmtree(dir)  # delete directory
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
    
def list_projects():
    """TODO"""
    pass
