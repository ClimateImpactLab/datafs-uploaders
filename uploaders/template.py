
'''
Template uploader script for Climate Impact Lab projects
========================================================

Instructions
------------

1.  Fill out user-defined parameters

2.  Modify user-defined functions to ensure that the archive names, tags,
    metadata, and dependencies will be correct

    - Check out the library functions to pull metadata automatically from 
      netCDF, metaCSV, and fgh files

3.  Do a "dry run" by running `python my_script_name.py -d`

4.  Do a live run by running `nice nohup python my_script_name.py &`

5.  Look for the output logs in nohup.out

'''

import glob
import logging
import re
import os
import math

import datafs # pip install datafs
import click  # pip install click

import xarray as xr  # conda install xarray netCDF4
import metacsv       # conda install metacsv


'''
User-defined parameters
-----------------------

Set these parameters to define the behavior of the upload script

'''

PATTERN = '/mnt/norgay_gcp/climate/HDDCDD/smme/*/*/*/*/*.nc'
'''
The unix-style path pattern that will be used to find files to upload

Any files matching this pattern will be uploaded to DataFS
'''

CACHE = False
'''
Flag indicating whether the files should be cached locally as they are uploaded

Set to True if the file will be used frequently, especially for large files
that we don't want to transfer frequently. Caching can always be turned on 
later.

If you are unsure about whether to cache an archive, ask Justin.
'''

RAISE_ON_RECREATE = True
'''
Set to False if you are running this script a second time with updated data or
metadata. The script will update the 
'''

ADDITIONAL_METADATA = {
    'project': 'ACP',
    'team': 'climate',
    'probability_method': 'smme'}
'''
Supply additional metadata to include with the archive. This will override any
metadata retrieved by `get_metadata`.
'''


'''
Additional user config data
----------------------

You probably don't have to worry about this stuff

'''

BUMPVERSION = 'major'
'''
Define how the version number changes. Your options are 'major', 'minor', and
'patch', for the three segments of the version number (e.g. 1.0.0), 
respectively. If you're not sure, major is fine.
'''



'''
User-defined functions
----------------------

Modify these functions to define how the script should handle each file

This is important - the script won't work unless you make sure these are right.

:py:func:`get_metadata` accepts path to the upload file as its only argument
and generates metadata from that file path and the file contents. The metadata
dictionary returned by this function are then made available to all of the
other user-defined functions.

:py:func:`namer` defines the name that will be used for your archive

:py:func:`tagger` defines the tags that can be used when searching for this
archive

:py:func:`get_dependencies` defines the dependencies for this archive, if any

'''


def get_metadata(fp):
    '''
    Return a dictionary of metadata from a filepath

    This metadata will be provided to other functions, such as :py:func:`namer`
    and :py:func:`tagger`, and will also be uploaded as archive metadata.

    Parameters
    ----------

    fp : str

        The local path to the file being uploaded

    Returns
    -------

    metadata : dict

        Dictionary of metadata used in the rest of this script and also 
        uploaded to DataFS as archive metadata

    '''

    # Use a library function to get metadata from the file or header
    metadata = get_netcdf_metadata(fp)

    # Modify the metadata here
    
    # metadata['description'] = 'My description of this data'

    # You can also get metadata from filename components

    fname_metadata = {}

    # If you uncomment the following, you could use the list elements to 
    # name the metadata extracted from the file name:

    # fname_components = [
    #     'geography',
    #     'ncdc',
    #     'frequency',
    #     'weather',
    #     'variable',
    #     'model',
    #     'scenario',
    #     'time_horizon']
    #
    # parsed_fname = os.path.splitext(os.path.basename(fp))[0].split('_')
    #
    # fname_metadata = dict(zip(fname_components, parsed_fname))

    # add metadata from filename to metadata dict
    metadata.update(fname_metadata)

    return metadata


def namer(fp, metadata):
    '''
    Construct an archive name from the filepath and metadata
    '''

    # build an archive name from the metadata and filepath
    return (
        '{project}/' +
        '{team}/' +
        '{probability_method}/' +
        '{variable}/' +
        '{geography}/' +
        '{weather}/' +
        '{frequency}/' +
        '{scenario}/' +
        '{model}/' +
        '{time_horizon}.nc'
        ).format(**metadata)


def tagger(fp, metadata):
    '''
    Create a list of tags for the archive

    These tags should represent atomic concepts that one might search for. For
    example, the project, team, task, scenario, creator, method, and other
    attributes are all valid tags.

    Parameters
    ----------

    fp : str

        The local path to the file being uploaded

    metadata : dict

        Dictionary of metadata attributes from :py:func:`get_metadata`


    Returns
    -------

    tags : list

        Descriptive tags that can be used to find this archive

    '''

    # For example, build tags using the relative path segments
    relpath = os.path.relpath(fp, start='/mnt/norgagy_gcp')

    # remove file extension
    relpath = os.path.splitext(relpath)[0]

    # split on slashes
    path_segments = relpath.replace('\\', '/').split('/')

    tags = path_segments

    
    # add your own tags
    my_extra_tags = []
    tags.extend(my_extra_tags)

    return tags


def get_dependencies(fp, metadata):
    '''
    Return the dependencies for the archive from the filepath and metadata

    These dependencies should be valid archive names (e.g. not the abstract 
    "variable" it depends on). Dependencies are specified using dictionaries,
    where the key is the archive name and the value is the version number.

    .. code-block:: python

        {'dependency1': None, 'dependency2': '1.5.12'}

    The version number may be set to ``None`` if the dependency is not pinned
    to a specific version.

    For more information see `the datafs docs 
    <https://datafs.readthedocs.io/en/latest/pythonapi.dependencies.html>`_

    Parameters
    ----------

    fp : str

        The local path to the file being uploaded

    metadata : dict

        Dictionary of metadata attributes from :py:func:`get_metadata`


    Returns
    -------

    dependencies : dict

        Dependencies for this archive, expressed as a dictionary of archive
        names and version numbers.

    '''
    # Use the filename or metadata to construct the dependencies
    dependencies = {}

    return dependencies


'''
Library functions
-----------------

Call these functions in the user-defined functions for out-of-the-box 
functionality such as automatically parsing the headers of NetCDF or .fgh files
'''

def get_netcdf_metadata(fp):
    '''
    Pull metadata from a NetCDF header
    '''

    with xr.open_dataset(fp) as ds:
        return dict(ds.attrs)


def get_fgh_metadata(fp):
    '''
    Pull metadata from an fgh header
    '''

    pass


def get_metacsv_metadata(fp):
    '''
    Pull metadata from a MetaCSV header
    '''

    pass


'''
Utility functions
-----------------

This is the core of the upload script. Don't modify these functions unless you
know what you're doing

'''

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('uploader')
logger.setLevel('INFO')


def upload_file(api, fp, extra_metadata, dry_run=False):
    '''
    Controls the behavior of the uploader for each file

    Parameters
    ----------

    api : object

        :py:class:`DataFS.DataAPI` object with which the archive will be 
        created and updated

    fp : str

        path to the file to upload

    extra_metadata : dict

        additional metadata that will override values obtained by 
        :py:func:`get_metadata`

    dry_run : bool



    '''

    metadata = get_metadata(fp)
    metadata.update(extra_metadata)

    name = namer(fp, metadata)
    tags = tagger(fp, metadata)
    
    dependencies = get_dependencies(fp, metadata)

    if dry_run:
        return name

    try:
        archive = api.create(
            archive_name = name,
            metadata = metadata,
            tags = tags,
            authority_name = 'osdc')

    except KeyError as e:
        if RAISE_ON_RECREATE:
            raise e

        archive = api.get_archive(
            archive_name = name)

        archive.add_tags(*tuple(tags))

    archive.update(
        fp,
        metadata=metadata,
        dependencies=dependencies,
        bumpversion=BUMPVERSION)

    return name


def upload_files(api, pattern, extra_metadata, dry_run=False):
    '''
    Loops through all files matching ``pattern`` and uploads them to the api

    Parameters
    ----------

    api : object

        :py:class:`DataFS.DataAPI` object with which the archive will be 
        created and updated

    pattern : str

        unix-style path pattern used to find files to upload. Use the wildcard
        characters * (unlimited characters) and ? (single character) and the 
        option syntax [abcd] to specify paths. Pattern matching and file 
        discovery is done with the :py:func:`~glob.glob` utility.

    extra_metadata : dict

        additional metadata that will override values obtained by 
        :py:func:`get_metadata`

    '''

    all_files = glob.glob(pattern)

    template = '{{}} {{:{}}}/{{}}: {{}}'.format(
        int(math.log(len(all_files), 10)//1+1))

    for i, fp in enumerate(all_files):

        try:
            archive_name = upload_file(
                api,
                fp,
                extra_metadata,
                dry_run=dry_run)

            if dry_run:
                message_header = 'Parsed'

            else:
                message_header = 'Uploaded'

            logger.info(template.format(
                message_header,
                i+1,
                len(all_files),
                archive_name))
        
        except Exception as e:
            logger.error(
                'Errors encountered parsing file {}:'.format(fp),
                exc_info=e)


@click.command(name='upload')
@click.option('-d', '--dry-run', is_flag=True, default=False)
def main(dry_run=False):

    api = datafs.get_api()

    upload_files(api, PATTERN, ADDITIONAL_METADATA, dry_run=dry_run)


if __name__ == '__main__':
    main()
