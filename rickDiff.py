#!/usr/bin/env python

import argparse
from argparse import RawTextHelpFormatter
import codecs
import fnmatch
import os
import subprocess
import sys
import tempfile


#//************************************************************************************************
#//
#//  globals/constants
#//
#//************************************************************************************************

PROGRAM_NAME = 'rickDiff'
VERSION = '0.7.1'
DESCRIPTION = 'compares CVS versions using meld'

STD_DEV_NULL = ' > NUL'
ERR_DEV_NULL = ' 2> NUL'

TO_DEV_NULL = STD_DEV_NULL + ERR_DEV_NULL


#//******************************************************************************
#//
#//  parseIncrement
#//
#//  parses '+n' and '-n' to return an integer value, and 0 if anything else
#//
#//******************************************************************************

def parseIncrement( increment ):
    if len( increment ) < 2:
        return 0;

    if increment[ 0 ] == '+':
        return int( increment[ 1: ] )
    elif increment[ 0 ] == '-':
        return -int( increment[ 1: ] )
    else:
        return 0


#//******************************************************************************
#//
#//  incrementVersionSimple
#//
#//  version - version string
#//  increment - integer value of how much to increment the last token in the
#//              version string (and it can be negative, but the resulting
#//              version number will be invalid if the last token ends up less
#//              than 1
#//******************************************************************************

def incrementVersionSimple( version, increment ):
    if increment == 0:
        return version
    else:
        tokens = version.split( '.' )
        tokens[ -1 ] = str( int( tokens[ -1 ] ) + increment )

        return '.'.join( tokens )


#//******************************************************************************
#//
#//  incrementVersion
#//
#//  increment the version number forwards or backwards based on cvs log
#//
#//  version - version string
#//  increment - integer value of how much to increment the version
#//              (positive or negative)
#//
#//  If the increment goes higher then the current version, then it will call
#//  incrementVersionSimple.  This may or may be a valid version number.
#//
#//  If the increment goes lower than 1.1, then it will return '1.1'
#//
#//******************************************************************************

def incrementVersion( targetFile, version, increment ):
    print( '\rParsing CVS log...\r', end='' )
    process = subprocess.Popen( [ 'cvs', 'log', '-Nb', targetFile ], stdout=subprocess.PIPE, shell=True,
                                universal_newlines=True )

    versions = [ ]

    index = -1

    for line in process.stdout:
        if str( line ).startswith( 'revision ' ):
            newVersion = line[ 9 : -1 ]

            versions.append( newVersion )

            if ( index == -1 ) and ( newVersion == version ):
                index = len( versions ) - 1

    # remember versions in order from newest to oldest
    newIndex = index - increment

    print( '\r                  \r', end='' )

    if newIndex > len( versions ):
        return '1.1'
    elif newIndex < 0:
        return incrementVersionSimple( version, increment )
    else:
        return versions[ newIndex ]


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

        if len( fields ) < 3:
            break

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
'CVS/Entries'.  'CURRENT' can be followed by '-n' where n is a number, and
rickDiff will retrieve n versions back, according to 'cvs log -b'.

In addition, a version name after the first of the form '+n' will be translated
into the previously specified version incremented by n versions.\n

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
    if firstVersion.startswith( 'CURRENT' ):
        increment = parseIncrement( firstVersion[ 7: ] )

        try:
            firstVersion = parseVersionFromEntries( sourceFileName )
        except Exception as error:
            print( PROGRAM_NAME + ": {0}".format( error ) )
            return

        if increment != 0:
            firstVersion = incrementVersion( sourceFileName, firstVersion, increment )

        firstFileName = os.path.join( tempDir, base + '.' + firstVersion + ext )

        command = 'cvs co -p -r ' + firstVersion + ' ' + linuxPath + ' > ' + firstFileName + ERR_DEV_NULL
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
            print( '\rRetrieving first file...\r', end='' )

            os.system( command )

            if os.stat( firstFileName ).st_size == 0:
                print( "Version '" + firstVersion + "' not found for file '" + base + ext + "'" )
                return

            print( '\rFormatting first file...\r', end='' )

            if args.astyle:
                os.system( 'astyle ' + firstFileName + TO_DEV_NULL )
            elif not args.skip_dos2unix:
                os.system( 'dos2unix ' + firstFileName + TO_DEV_NULL )
                os.system( 'unix2dos ' + firstFileName + TO_DEV_NULL )

            print( '\r                        \r', end='' )

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
    elif secondVersion.startswith( 'CURRENT' ):
        increment = parseIncrement( secondVersion[ 7: ] )

        try:
            secondVersion = parseVersionFromEntries( sourceFileName )
        except Exception as error:
            print( PROGRAM_NAME + ": {0}".format( error ) )
            return

        if increment != 0:
            secondVersion = incrementVersion( secondVersion, increment )

        secondFileName = os.path.join( tempDir, base + '.' + secondVersion + ext )

        command = 'cvs co -p -r ' + secondVersion + ' ' + linuxPath + ' > ' + secondFileName + ERR_DEV_NULL
    elif secondVersion[ 0 ] == '+':
        secondVersion = incrementVersion( sourceFileName, firstVersion, int( secondVersion[ 1: ] ) )
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
            print( '\rRetrieving second file...\r', end='' )

            os.system( command )

            if os.stat( secondFileName ).st_size == 0:
                print( "Version '" + secondVersion + "' not found for file '" + base + ext + "'" )
                return

            print( '\rFormatting second file...\r', end='' )

            if args.astyle:
                os.system( 'astyle ' + secondFileName + TO_DEV_NULL )
            elif not args.skip_dos2unix:
                os.system( 'dos2unix ' + secondFileName + TO_DEV_NULL )
                os.system( 'unix2dos ' + secondFileName + TO_DEV_NULL )

            print( '\r                         \r', end='' )

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
    elif thirdVersion.startswith( 'CURRENT' ):
        increment = parseIncrement( thirdVersion[ 7: ] )

        try:
            thirdVersion = parseVersionFromEntries( sourceFileName )
        except Exception as error:
            print( PROGRAM_NAME + ": {0}".format( error ) )
            return

        if increment != 0:
            thirdVersion = incrementVersion( sourceFileName, thirdVersion, increment )

        thirdFileName = os.path.join( tempDir, base + '.' + thirdVersion + ext )

        command = 'cvs co -p -r ' + thirdVersion + ' ' + linuxPath + ' > ' + thirdFileName + ERR_DEV_NULL
    elif thirdVersion[ 0 ] == '+':
        thirdVersion = incrementVersion( sourceFileName, secondVersion, int( thirdVersion[ 1: ] ) )
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
            print( '\rRetrieving third file...\r', end='' )

            os.system( command )

            if os.stat( thirdFileName ).st_size == 0:
                print( "Version '" + thirdVersion + "' not found for file '" + base + ext + "'" )
                return

            print( '\rFormatting third file...\r', end='' )

            if args.astyle:
                os.system( 'astyle ' + thirdFileName + TO_DEV_NULL )
            elif not args.skip_dos2unix:
                os.system( 'dos2unix ' + thirdFileName + TO_DEV_NULL )
                os.system( 'unix2dos ' + thirdFileName + TO_DEV_NULL )

            print( '\r                        \r', end='' )

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
        print( '\rLaunching Meld...\r', end='' )
        os.system( command )
        print( '\r                 \r', end='' )


#//**********************************************************************
#//
#//  __main__
#//
#//**********************************************************************

if __name__ == '__main__':
    main( )

