# -*- coding: utf-8 -*-
"""
Tarbell project configuration
"""
import os

# Load basic config from yaml
yaml_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'tarbell_config.yaml')

with open(yaml_path) as f:
    d = yaml.load(f)
locals().update(d)
    

