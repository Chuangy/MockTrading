'''
util.py

21/01/2020 Colin Huang
'''

import inspect
import hashlib

def print_core(message: str):
    print(f'({inspect.stack()[1][3]})\t{message}')

def hash_string(s):
    return int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16)