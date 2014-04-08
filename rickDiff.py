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
VERSION = '0.8.0'
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

    process = subprocess.Popen( [ 'cvs', 'log', '-Nb', targetFile ], stdout=subprocess.PIPE,
                                  shell=True, universal_newlines=True )

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


#//******************************************************************************
#//
#//  createFileCommand
#//
#//  This function interprets the version argument in one of several ways.
#//
#//  First, if it's 'HEAD', rickDiff will check out the trunk version.
#//
#//  If it's 'CURRENT', rickDiff will check out whatever version is checked out
#//  in the source directory according to CVS/Entries.  'CURRENT' can also have
#//  '+n' or '-n' appended to it and rickDiff will instead get n versions before
#//  or after the version 'CURRENT' refers to, if it exists.
#//
#//  If the argument is of the form '+n' then rickDiff will get n versions newer
#//  than the version of the previous argument.  '-n' is not supported as a
#//  stand-alone argument because argParser tries to interpret it as a
#//  non-existent option, and it's not really useful anyway.
#//
#//  Next, if the argument corresponds to a directory name under devRoot, then
#//  rickDiff will use the corresponding file in that directory tree.
#//
#//  And finally, if nothing else matches, rickDiff passes the argument unchanged
#//  to CVS where it can be interpreted as a version number, branch name or tag
#//  name.
#//
#//  On errors, the fileName returned will be empty.
#//
#//******************************************************************************

def createFileCommand( sourceFileName, versionArg, linuxPath, devDirs, localFlag, oldVersion='' ):
    command = ''
    fileName = ''
    version = ''

    tempDir = os.environ[ 'TEMP' ]

    base, ext = os.path.splitext( os.path.basename( sourceFileName ) )

    if versionArg == '':
        if localFlag:
            fileName = sourceFileName
        else:
            command = 'copy ' + sourceFileName + ' ' + tempDir + TO_DEV_NULL
            fileName = os.path.join( tempDir, base + ext )
    elif versionArg == 'HEAD':
        fileName = os.path.join( tempDir, base + '.' + versionArg + ext )
    elif versionArg.startswith( 'CURRENT' ):
        increment = parseIncrement( versionArg[ 7: ] )

        version = parseVersionFromEntries( sourceFileName )

        if increment != 0:
            version = incrementVersion( sourceFileName, version, increment )

        fileName = os.path.join( tempDir, base + '.' + version + ext )

        command = 'cvs co -p -r ' + version + ' ' + linuxPath + ' > ' + fileName + ERR_DEV_NULL
    elif versionArg[ 0 ] == '+':
        version = incrementVersion( sourceFileName, oldVersion, int( versionArg[ 1: ] ) )

        fileName = os.path.join( tempDir, base + '.' + version + ext )
        command = 'cvs co -p -r ' + version + ' ' + linuxPath + ' > ' + fileName + ERR_DEV_NULL
    elif versionArg in devDirs:
        source = buildDevFileName( devRoot, sourceFileName, versionArg )

        if not os.path.isfile( source ):
            raise Exception( "File '" + source + "' does not appear to exist." )

        version = versionArg

        fileName = os.path.join( tempDir, base + '.' + version + ext )
        command = 'copy ' + source + ' ' + fileName + TO_DEV_NULL

        if localFlag:
            fileName = buildDevFileName( devRoot, sourceFileName, version )
        else:
            fileName = os.path.join( tempDir, base + '.' + version + ext )
            command = 'copy ' + source + ' ' + fileName + TO_DEV_NULL
    else:
        version = versionArg
        fileName = os.path.join( tempDir, base + '.' + version + ext )
        command = 'cvs co -p -r ' + version + ' ' + linuxPath + ' > ' + fileName + ERR_DEV_NULL

    return command, fileName, version



#//******************************************************************************
#//
#//  retrieveFile
#//
#//******************************************************************************

def retrieveFile( command, ordinal, version, fileName, sourceFileName, astyle, skip_dos2unix ):
    print( '\rRetrieving ' + ordinal + ' file...\r', end='' )

    os.system( command )

    if os.stat( fileName ).st_size == 0:
        raise Exception( "Version '" + version + "' not found for file '" + sourceFileName + "'" )

    print( '\rFormatting ' + ordinal + ' file...\r', end='' )

    if astyle:
        os.system( 'astyle ' + fileName + TO_DEV_NULL )
    elif not skip_dos2unix:
        os.system( 'dos2unix ' + fileName + TO_DEV_NULL )
        os.system( 'unix2dos ' + fileName + TO_DEV_NULL )

    print( '\r                             \r', end='' )


#//******************************************************************************
#//
#//  handleArgument
#//
#//******************************************************************************

def handleArgument( ordinal, sourceFileName, linuxPath, devDirs, versionArg, args, oldVersion='' ):
    try:
        command, fileName, version = \
               createFileCommand( sourceFileName, versionArg, linuxPath, devDirs, args.local, oldVersion )
    except Exception as error:
        print( PROGRAM_NAME + ": {0}".format( error ) )
        return ''

    # execute the command for the third file (if we need to)
    if command != '':
        if args.test:
            print( command )
        else:
            try:
                retrieveFile( command, ordinal, version, fileName, sourceFileName,
                              args.astyle, args.skip_dos2unix )
            except Exception as error:
                print( PROGRAM_NAME + ": {0}".format( error ) )
                return ''

    return version, fileName


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

    # parse the first version argument and build the shell command
    if firstVersion == '':
        firstVersion = 'CURRENT'

    firstVersion, firstFileName = handleArgument( 'first', sourceFileName, linuxPath, devDirs, firstVersion, args )

    if firstVersion == '':
        return

    secondVersion, secondFileName = \
            handleArgument( 'second', sourceFileName, linuxPath, devDirs, secondVersion, args, firstVersion )

    if secondVersion == '':
        return

    # parse the third version argument and build the shell command (if we need one)
    if thirdVersion != '' or args.three_way:
        thirdVersion, thirdFileName = \
                handleArgument( 'third', sourceFileName, linuxPath, devDirs, thirdVersion, args, firstVersion )
    else:
        thirdFileName = ''

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

