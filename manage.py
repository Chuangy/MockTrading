#!/usr/bin/env python3.8

import asyncio
import getopt
import sys

import backend.server as server

def main(argv):
    help_string = '''manage.py 
        -p [--port] <port (8888)> 
        -d [--debug]'''
    try:
        opts, _ = getopt.getopt(
            argv, 'p:d', ['port=', 'debug'])
    except getopt.GetoptError:
        print(help_string)
        return 1

    # Default values
    port = 8887  # Port to run server on
    debug = False

    for opt, arg in opts:
        if opt == '-h':
            print(help_string)
            return 0
        elif opt in ('-p', '--port'):
            port = str(arg)
        elif opt in ('-d', '--debug'):
            debug = True

    print('-' * 60)
    print(f'Running on port {port}')
    print(f'Debug mode is {debug}')
    print('-' * 60)

    asyncio.run(server.main(port=port))

    return 0

if __name__ == '__main__':
    main(sys.argv[1:])
