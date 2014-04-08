#!/usr/bin/env python

import argparse
from argparse import RawTextHelpFormatter
import codecs
import fnmatch
import os
import sys


#//************************************************************************************************
#//
#//  globals/constants
#//
#//************************************************************************************************

PROGRAM_NAME = 'rickDiff'
VERSION = '0.6.0'
DESCRIPTION = 'compares CVS versions using meld'

STD_DEV_NULL = ' > NUL'
ERR_DEV_NULL = ' 2> NUL'

TO_DEV_NULL = STD_DEV_NULL + ERR_DEV_NULL


#//******************************************************************************
#//
#//  incrementVersion
#//
#//  version - version string
#//  increment - integer value of how much to increment the last token in the
#//              version string (and it can be negative if you really want)
#//
#//******************************************************************************

def incrementVersion( version, increment ):
    if increment == 0:
        return version
    else:
        tokens = version.split( '.' )
        tokens[ -1 ] = str( int( tokens[ -1 ] ) + increment )

        return '.'.join( tokens )


#//******************************************************************************
#//
#//  parseVersionFromEntries
#//
#//  parses the current version of the file from the CVS/Entries file
#//
#//******************************************************************************

def parseVersionFromEntries( targetFile ):
    pathList = targetFile.split( os.sep )

    fileName = pathList.pop( )

    pathList.append( 'CVS' )
    pathList.append( 'Entries' )

    entriesFileName = os.sep.join( pathList )

    for line in codecs.open( entriesFileName, 'rU', 'ascii', 'replace' ):
        fields = line[ : -1 ].split( '/' )

        if ( fields[ 1 ] == fileName ):
            return fields[ 2 ]

    raise Exception( "'" + targetFile + "' not found in CVS/Entries, not under version control?" )



#//******************************************************************************
#//
#//  buildDevFileName
#//
#//******************************************************************************

def buildDevFileName( devRoot, sourceFileName, dirName ):
    source = os.path.abspath( sourceFileName )

    sourceList = os.path.relpath( source, devRoot ).split( os.sep )
    sourceList.pop( 0 )

    sourceList.insert( 0, dirName )

    devRootList = devRoot.split( os.sep )
    devRootList.reverse( )

    for i in devRootList:
        sourceList.insert( 0, i )

    return os.sep.join( sourceList )


#//************************************************************************************************
#//
#//  main
#//
#//************************************************************************************************

def main( ):
    parser = argparse.ArgumentParser( prog=PROGRAM_NAME, description=PROGRAM_NAME + ' - ' + VERSION + ' - ' + DESCRIPTION,
                                      formatter_class=RawTextHelpFormatter, epilog=
'''
rickDiff relies on the existence of the file 'CVS/Repository' to figure out
where 'fileName' is, uses the environment variable 'TEMP', and expects 'cvs'
'meld', and 'astyle' to launch those respective programs from the command line.\n

It also assumes that a version string that is the name of a directory under
devRoot means that it should compare the appropriate file under that directory.\n

rickDiff recognizes some special version names:  'HEAD' for the CVS trunk
version; 'CURRENT' for the currently checked out version (according to
'CVS/Entries'.  In addition, a version name after the first of the form '+n'
will be translated into the previously specified version incremented by n
versions.\n

Any other name is passed on to CVS, so branch names and tag names can be used.\n

rickDiff does leave files in the %TEMP directory when it is done.
''' )

    parser.add_argument( 'fileName', nargs='?', default='', help='the file to compare' )
    parser.add_argument( 'firstVersion', nargs='?', default='',
                         help='first version to compare (optional: otherwise current version)' )
    parser.add_argument( 'secondVersion', nargs='?', default='',
                         help='second version to compare (optional: otherwise local checked out file)' )
    parser.add_argument( 'thirdVersion', nargs='?', default='',
                         help='third version to compare (optional: if --three-way then local checked out file, otherwise two-way comparison)' )
    parser.add_argument( '-3', '--three_way', action='store_true', help='three-way comparison' )
    parser.add_argument( '-a', '--astyle', action='store_true', help='run astyle on non-local files before comparison' )
    parser.add_argument( '-d', '--skip_dos2unix', action='store_true',
                         help='skips dos2unix-unix2dos step, which is intended to fix line endings' )
    parser.add_argument( '-l', '--local', action='store_true', help='use the local file, don\'t check out from the HEAD' )
    parser.add_argument( '-t', '--test', action='store_true', help='print commands, don\'t execute them' )
    parser.add_argument( '-r', '--reverse', action='store_true', help='load the files into Meld in reverse order' )

    args = parser.parse_args( )

    if args.fileName == '':
        parser.print_help( )
        return

    # determine the CVS information
    try:
        with open( 'CVS/Repository' ) as inputFile:
            linuxPath = inputFile.read( )[ : -1 ]
    except:
        print( PROGRAM_NAME + ':  cannot find CVS/Repository (not in the sandbox?)' )
        return

    # parse the arguments
    linuxPath += '/' + args.fileName.replace( '\\', '/' )

    sourceFileName = args.fileName.replace( '/', '\\' )

    firstVersion = args.firstVersion
    secondVersion = args.secondVersion
    thirdVersion = args.thirdVersion

    devRoot = 'd:\\dev'

    devDirs = [ name for name in os.listdir( devRoot ) if os.path.isdir( os.path.join( devRoot, name ) ) ]

    if args.three_way and ( firstVersion == '' or secondVersion == '' ):
        print( PROGRAM_NAME + ":  Please specify at least two CVS versions for three-way comparison." )
        return

    base, ext = os.path.splitext( os.path.basename( sourceFileName ) )

    tempDir = os.environ[ 'TEMP' ]

    # determine what the first file should be
    if firstVersion == '':
        firstVersion = 'CURRENT'

    executeCommand = True

    # parse the first version argument and build the shell command
    if firstVersion == 'HEAD':
        firstFileName = os.path.join( tempDir, base + '.' + firstVersion + ext )
        command = 'cvs co -p ' + linuxPath + ' > ' + firstFileName + ERR_DEV_NULL
    if firstVersion == 'CURRENT':
        try:
            firstVersion = parseVersionFromEntries( sourceFileName )
        except Exception as error:
            print( PROGRAM_NAME + ": {0}".format( error ) )
            return

        firstFileName = os.path.join( tempDir, base + '.' + firstVersion + ext )
        command = 'cvs co -p ' + linuxPath + ' > ' + firstFileName + ERR_DEV_NULL
    elif firstVersion in devDirs:
        source = buildDevFileName( devRoot, sourceFileName, firstVersion )

        if not os.path.isfile( source ):
            print( "File '" + source + "' does not appear to exist." )
            return

        if args.local:
            firstFileName = buildDevFileName( devRoot, sourceFileName, firstVersion )
            executeCommand = False
        else:
            firstFileName = os.path.join( tempDir, base + '.' + firstVersion + ext )
            command = 'copy ' + source + ' ' + firstFileName + TO_DEV_NULL
    else:
        firstFileName = os.path.join( tempDir, base + '.' + firstVersion + ext )
        command = 'cvs co -p -r ' + firstVersion + ' ' + linuxPath + ' > ' + firstFileName + ERR_DEV_NULL

    # execute the command for the first file
    if executeCommand:
        if args.test:
            print( command )
        else:
            os.system( command )

            if os.stat( firstFileName ).st_size == 0:
                print( "Version '" + firstVersion + "' not found for file '" + base + ext + "'" )
                return

            if args.astyle:
                os.system( 'astyle ' + firstFileName + TO_DEV_NULL )
            elif not args.skip_dos2unix:
                os.system( 'dos2unix ' + firstFileName + TO_DEV_NULL )
                os.system( 'unix2dos ' + firstFileName + TO_DEV_NULL )

    executeCommand = True
    checkedOut = True

    # parse the second version argument and build the shell command
    if secondVersion == '':
        if args.local:
            secondFileName = sourceFileName
            executeCommand = False
        else:
            command = 'copy ' + sourceFileName + ' ' + tempDir + TO_DEV_NULL
            checkedOut = False
            secondFileName = os.path.join( tempDir, base + ext )
    elif secondVersion == 'HEAD':
        secondFileName = os.path.join( tempDir, base + '.' + secondVersion + ext )
    elif secondVersion == 'CURRENT':
        secondVersion = parseVersionFromEntries( linuxPath )
        secondFileName = os.path.join( tempDir, base + '.' + secondVersion + ext )
    elif secondVersion[ 0 ] == '+':
        secondVersion = incrementVersion( firstVersion, int( secondVersion[ 1: ] ) )
        secondFileName = os.path.join( tempDir, base + '.' + secondVersion + ext )
        command = 'cvs co -p -r ' + secondVersion + ' ' + linuxPath + ' > ' + secondFileName + ERR_DEV_NULL
    elif secondVersion in devDirs:
        source = buildDevFileName( devRoot, sourceFileName, secondVersion )

        if not os.path.isfile( source ):
            print( "File '" + source + "' does not appear to exist." )
            return

        secondFileName = os.path.join( tempDir, base + '.' + secondVersion + ext )
        command = 'copy ' + source + ' ' + secondFileName + TO_DEV_NULL
    else:
        secondFileName = os.path.join( tempDir, base + '.' + secondVersion + ext )
        command = 'cvs co -p -r ' + secondVersion + ' ' + linuxPath + ' > ' + secondFileName + ERR_DEV_NULL

    # execute the command for the second file (if we need to)
    if executeCommand:
        if args.test:
            print( command )
        else:
            os.system( command )

            if os.stat( secondFileName ).st_size == 0:
                print( "Version '" + secondVersion + "' not found for file '" + base + ext + "'" )
                return

            if args.astyle:
                os.system( 'astyle ' + secondFileName + TO_DEV_NULL )
            elif not args.skip_dos2unix:
                os.system( 'dos2unix ' + secondFileName + TO_DEV_NULL )
                os.system( 'unix2dos ' + secondFileName + TO_DEV_NULL )

    executeCommand = True
    checkedOut = True

    thirdFileName = ''

    # parse the third version argument and build the shell command (if we need one)
    if thirdVersion == '':
        checkedOut = False

        if args.three_way:
            if args.local:
                thirdFileName = sourceFileName
                executeCommand = False
            else:
                thirdFileName = os.path.join( tempDir, base + ext )
                command = 'copy ' + sourceFileName + ' ' + tempDir + TO_DEV_NULL
        else:
            executeCommand = False
    elif thirdVersion == 'HEAD':
        thirdFileName = os.path.join( tempDir, base + '.' + thirdVersion + ext )
        command = 'cvs co -p ' + linuxPath + ' > ' + thirdFileName + ERR_DEV_NULL
    elif thirdVersion[ 0 ] == '+':
        thirdVersion = incrementVersion( secondVersion, int( thirdVersion[ 1: ] ) )
        thirdFileName = os.path.join( tempDir, base + '.' + thirdVersion + ext )
        command = 'cvs co -p -r ' + thirdVersion + ' ' + linuxPath + ' > ' + thirdFileName + ERR_DEV_NULL
    elif thirdVersion in devDirs:
        thirdFileName = os.path.join( tempDir, base + '.' + thirdVersion + ext )

        source = buildDevFileName( devRoot, sourceFileName, thirdVersion )

        if not os.path.isfile( source ):
            print( "File '" + source + "' does not appear to exist." )
            return

        command = 'copy ' + source + ' ' + thirdFileName + TO_DEV_NULL
    else:
        command = 'cvs co -p -r ' + thirdVersion + ' ' + linuxPath + ' > ' + thirdFileName + ERR_DEV_NULL

    # execute the command for the third file (if we need to)
    if executeCommand:
        if args.test:
            print( command )
        else:
            os.system( command )

            if os.stat( thirdFileName ).st_size == 0:
                print( "Version '" + thirdVersion + "' not found for file '" + base + ext + "'" )
                return

            if args.astyle:
                os.system( 'astyle ' + thirdFileName + TO_DEV_NULL )
            elif not args.skip_dos2unix:
                os.system( 'dos2unix ' + thirdFileName + TO_DEV_NULL )
                os.system( 'unix2dos ' + thirdFileName + TO_DEV_NULL )

    # we have everything, so let's launch meld
    if thirdFileName == '':
        if args.reverse:
            command = 'meld ' + secondFileName + ' ' + firstFileName
        else:
            command = 'meld ' + firstFileName + ' ' + secondFileName
    else:
        if args.reverse:
            command = 'meld ' + thirdFileName + ' ' + secondFileName + ' ' + firstFileName
        else:
            command = 'meld ' + firstFileName + ' ' + secondFileName + ' ' + thirdFileName

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

