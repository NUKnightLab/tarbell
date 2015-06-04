# -*- coding: utf-8 -*-

"""
tarbell.utils
~~~~~~~~~

This module provides utilities for Tarbell.
"""
from datetime import datetime
import os
import sys

from clint.textui import colored, puts as _puts
import shutil


def is_werkzeug_process():
    """Is the current process the werkzeug reloader thread? Return True if so."""
    return os.environ.get('WERKZEUG_RUN_MAIN') == 'true'


def puts(*args, **kwargs):
    """Wrap puts to avoid getting called twice by Werkzeug reloader"""
    if not is_werkzeug_process():
        return _puts(*args, **kwargs)


def props(obj):
    """
    Return object as dictionary
    Only gets attributes set on the instance, not on the class!
    """
    return dict((key, value) \
        for key, value in obj.__dict__.iteritems() \
        if not callable(value) and not key.startswith('__'))


def list_get(l, idx, default=None):
    """Get from a list with an optional default value."""
    try:
        if l[idx]:
            return l[idx]
        else:
            return default
    except IndexError:
        return default


def split_sentences(s, pad=0):
    """Split sentences for formatting."""
    sentences = []
    for index, sentence in enumerate(s.split('. ')):
        padding = ''
        if index > 0:
            padding = ' ' * (pad + 1)
        if sentence.endswith('.'):
            sentence = sentence[:-1]
        sentences.append('%s %s.' % (padding, sentence.strip()))
    return "\n".join(sentences)


def show_error(msg):
    """Displays error message."""
    sys.stdout.flush()
    sys.stderr.write("\n{0}: {1}".format(colored.red("Error"), msg + '\n'))
    
    
def make_dir(path):
    """Create directory"""
    try:
        os.mkdir(path)        
    except OSError, e:
        if is_werkzeug_process():
            if e.errno == 16:
                raise Exception('Error creating directory "%s", already exists' % path)
            else:
                raise Exception('Error creating directory "%s", %s' % (path, str(e)))
        else:
            if e.errno == 17:
                show_error("ABORTING: Directory {0} already exists.".format(path))
            else:
                show_error("ABORTING: OSError {0}".format(e))
            sys.exit()

            
def delete_dir(path):
    """Delete directory"""
    try:
        shutil.rmtree(path)
    except OSError, e:
        if e.errno != 2:  # code 2 - no such file or directory
            raise Exception(str(e))
    except UnboundLocalError:
        pass


def backup(path, filename):
    """Backup a file"""
    target = os.path.join(path, filename)
    if os.path.isfile(target):
        dt = datetime.now()
        new_filename = ".{0}.{1}.{2}".format(
            filename, dt.isoformat(), "backup"
        )
        destination = os.path.join(path, new_filename)
        puts("- Backing up {0} to {1}".format(
            colored.cyan(target),
            colored.cyan(destination)
        ))

        shutil.copy(target, destination)

