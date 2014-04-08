#!/usr/bin/env python

import argparse
import datetime
import fnmatch
import locale
import os
import posixpath
import sys
import time


#//**********************************************************************
#//
#//  globals/constants
#//
#//**********************************************************************

PROGRAM_NAME = 'RickDiff'
VERSION = '0.3'
DESCRIPTION = 'compares CVS versions using meld'

TO_DEV_NULL = ' 2> NUL'


#//**********************************************************************
#//
#//  main
#//
#//**********************************************************************

def main( ):
    parser = argparse.ArgumentParser( prog=PROGRAM_NAME, description=PROGRAM_NAME + ' - ' + VERSION + ' - ' + DESCRIPTION,
                                      epilog=
'''
RickDiff relies on the existence of the file 'CVS/Repository' to figure out 
where 'fileName' is, uses the environment variable 'TEMP', and expects 'cvs' 
and 'meld' to launch those respective programs from the command line.
''' )

    parser.add_argument( 'fileName', nargs='?', default='', help='the file to compare' )
    parser.add_argument( 'firstVersion', nargs='?', default='', help='first version to compare (optional: blank means compare existing file against trunk)' )
    parser.add_argument( 'secondVersion', nargs='?', default='', help='second version to compare (optional: blank means compare firstVersion against trunk)' )
    parser.add_argument( '-d', '--skip_dos2unix', action='store_true', help='skips dos2unix-unix2dos step, which is intended to fix line endings' )
    parser.add_argument( '-t', '--test', action='store_true', help='print commands, don\'t execute them' )

    args = parser.parse_args( )

    if args.fileName == '':
        parser.print_help( )
        return

    try:
        with open( 'CVS/Repository' ) as inputFile:
            linuxPath = inputFile.read( )[ : -1 ]
    except:
        print( PROGRAM_NAME + ':  cannot find CVS/Repository' )
        return

    linuxPath += '/' + args.fileName
        
    firstVersion = args.firstVersion
    secondVersion = args.secondVersion

    base, ext = os.path.splitext( args.fileName )

    tempDir = os.environ[ 'TEMP' ]

    if firstVersion == '':
        firstFileName = os.path.join( tempDir, args.fileName )
        command = 'copy ' + args.fileName + ' ' + tempDir + TO_DEV_NULL
    else:
        firstFileName = os.path.join( tempDir, base + '.' + firstVersion + ext )
        command = 'cvs co -p -r ' + firstVersion + ' ' + linuxPath + ' > ' + firstFileName + TO_DEV_NULL

    if args.test:
        print( command )
    else:
        os.system( command )

    if not args.skip_dos2unix and not args.test:
        os.system( 'dos2unix ' + firstFileName + TO_DEV_NULL )
        os.system( 'unix2dos ' + firstFileName + TO_DEV_NULL )

    if secondVersion == '':
        secondFileName = os.path.join( tempDir, base + '.trunk' + ext )
        command = 'cvs co -p ' + linuxPath + ' > ' + secondFileName + TO_DEV_NULL
    else:                    
        secondFileName = os.path.join( tempDir, base + '.' + secondVersion + ext )
        command = 'cvs co -p -r ' + secondVersion + ' ' + linuxPath + ' > ' + secondFileName + TO_DEV_NULL

    if not args.cmd:
        command += ' >& NUL'

    if args.test:
        print( command )
    else:
        os.system( command )

    if not args.skip_dos2unix and not args.test:
        os.system( 'dos2unix ' + secondFileName + TO_DEV_NULL )
        os.system( 'unix2dos ' + secondFileName + TO_DEV_NULL )

    if firstVersion == '':
        command = 'meld ' + secondFileName + ' ' + firstFileName + TO_DEV_NULL
    else:        
        command = 'meld ' + firstFileName + ' ' + secondFileName + TO_DEV_NULL

    if args.test:
        print( command )
    else:
        os.system( command )


#//**********************************************************************
#//
#//  __main__
#//
#//**********************************************************************

if __name__ == '__main__':
    main( )

