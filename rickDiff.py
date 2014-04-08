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

PROGRAM_NAME = "RickDiff"
VERSION = "0.1"
COPYRIGHT_MESSAGE = "copyright (c) 2012, iDirect"

#//**********************************************************************
#//
#//  main
#//
#//**********************************************************************

def main( ):
    parser = argparse.ArgumentParser( prog=PROGRAM_NAME, description=PROGRAM_NAME + ' - ' + VERSION + ' - ' + COPYRIGHT_MESSAGE )

    parser.add_argument( 'inputFile', help='' )
    parser.add_argument( 'firstVersion', help='' )
    parser.add_argument( 'secondVersion', nargs='?', default='', help='' )

    args = parser.parse_args( )

    try:
        linuxPath = os.path.relpath( args.inputFile, 'd:\\dev\\' )
    except:
        linuxPath = args.inputFile.replace( '\\', '/' )

    fileName = os.path.split( linuxPath )[ 1 ]
    linuxPath = linuxPath[ linuxPath.find( '\\' ) + 1 : ].replace( '\\', '/' )

    firstVersion = args.firstVersion
    secondVersion = args.secondVersion

    #print( linuxPath )            
    #print( fileName )            

    base, ext = os.path.splitext( fileName )

    #print( base )
    #print( ext )

    #print( firstVersion )
    #print( secondVersion )

    tempDir = os.environ[ 'TEMP' ]

    firstFileName = os.path.join( tempDir, base + '.' + firstVersion + ext )
    command = 'cvs co -p -r ' + firstVersion + ' ' + linuxPath + ' > ' + firstFileName

    os.system( command )

    if secondVersion == '':
        secondFileName = os.path.join( tempDir, fileName )
        command = 'cvs co -p ' + linuxPath + ' > ' + secondFileName
    else:                    
        secondFileName = os.path.join( tempDir, base + '.' + secondVersion + ext )
        command = 'cvs co -p -r ' + secondVersion + ' ' + linuxPath + ' > ' + secondFileName

    os.system( command )

    command = 'meld ' + firstFileName + ' ' + secondFileName

    os.system( command )


#//**********************************************************************
#//
#//  __main__
#//
#//**********************************************************************

if __name__ == '__main__':
    main( )





#setlocal
#
#iff "%1" == "" .or. "%2" == "" then
#    echo usage: cvsdiff file version1 [version2]
#else
#   set MODULE=%@replace[\,/,%1]
#
#   set TEMP_FILE_1=%TEMP_DIR%\%@NAME[%1].%2.%@EXT[%1]
#   cvs co -p -r %2 %MODULE > %TEMP_FILE_1%
#
#   iff "%3" == "" then
#       set TEMP_FILE_2=%TEMP_DIR%\%@FILENAME[%1]
#       cvs co -p %MODULE > %TEMP_FILE_2
#   else
#       set TEMP_FILE_2=%TEMP_DIR%\%@NAME[%1].%3.%@EXT[%1]
#       cvs co -p -r %3 %MODULE > %TEMP_FILE_2
#   endiff
#
#   %BAT_DIR%\meld %TEMP_FILE_1 %TEMP_FILE_2
#endiff
#
#endlocal 
#
