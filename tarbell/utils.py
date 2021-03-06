# -*- coding: utf-8 -*-

"""
tarbell.utils
~~~~~~~~~

This module provides utilities for Tarbell.
"""

from __future__ import print_function
import os
import sys
from clint.textui import colored, puts as _puts


def is_werkzeug_process():
    """Is the current process the werkzeug reloader thread? Return True if so."""
    return os.environ.get('WERKZEUG_RUN_MAIN') == 'true'


def puts(*args, **kwargs):
    """Wrap puts to avoid getting called twice by Werkzeug reloader"""
    if is_werkzeug_process():
        return print(*args, **kwargs)
    else:
        return _puts(*args, **kwargs)


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

