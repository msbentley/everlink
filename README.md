# everlink

## Introduction
Everlink is a python utility designed to help the transition from Evernote to another service whilst retaining full note-link functionality. To do this is queries the Evernote API and retrieves note meta-data. These meta-data can either be dumped to disk, or used in conjuction with supported note taking packages to fix the broken links. Currently only Joplin is supported.

### Background
The export format provided by Evernote is an XML file (one per notebook) containing all note data, meta-data and attachments. This is rather complete, _but_ it misses one vital piece of information - the unique identifier (GUID) of each note. Unfortunately this is the mechanism used by Evernote to internally link notes together. Without this, notes imported into other software (e.g. Joplin) become useless.

### Approach
This utility uses the Evernote API (via developer token, rather than OAuth - feel free to make a pull request if you want to implement that!) to request key meta-data from each notebook in turn:
- note name
- note GUID
- note creation date

The Joplin API (accessed using the API token provided under the web clipper settings) is then exercised to:
- search for notes including `evernote://`
- for each note found:
  - check if the note is Markdown or HTML (Joplin supports ENEX import with or without conversion to MD)
  - search for each `evernote://` link in the note
  - for each note:
    - extract the GUID from the link URL
    - see if there is a note matching this GUID in the list returned from Evernote
    - compare the title and creation date of this matching note with those in Joplin
    - if there is a match, re-write the link to replace the `evernote://` link with a Joplin one
    - write the note body back to Joplin via the API
    
 ### Caveats
 1. If you have modified the creation date after import, this will not work
 2. It is tested primarily with HTML imported notes, since this is my primary use case
 3. It needs the python3 Evernote SDK (see Installation)
 4. Linked/shared notebooks are currently not supported, until I can figure out the correct API calls!
 
 ## Installation
 
 ### Dependencies
 
 everlink needs the following dependencies:
 - python 3
 - lxml
 - python-oauth2 (this is a dependency of the Evernote SDK, although it is not used here)
 - [evernote-sdk-python3](https://github.com/evernote/evernote-sdk-python3)
 
 The first three can easily be met by installing in a virtualenv, or using conda, e.g. 
 `conda create --file environment.yml`
 The last should be downloaded/checked out and installed in the environment with `python setup.py install`.
 
 ### everjop_relinker
 Clone the Git repository
 
 **TODO: complete this when packaging is done**
 
 ### Configuration
 
 A few critical parameters must be provided, and put in a .ini file, namely:
 - Evernote developer token
   - go here https://dev.evernote.com/doc/articles/dev_tokens.php and click "Get an API key"
 - Joplin access token
   - in the Joplin settings, go to the Web Clipper section
   - if not enabled, start the web clipper (this enables API access)
   - the authorization token can be found in Advanced options
   
 Both of these should be placed in a configuration file using the python .ini format - see the example in the repo and below:
```
[evernote]
token = S=thisisalongtokenstring

[joplin]
token = 03670ethisisanotherlongstring
url = http://localhost
port = 41184
```
Note that the Joplin URL and port can also be given - these typically do not change, and if the configuration options are not given, defaults will be used.

## Usage

everjop_relinker can be executed without any additional parameters:
```bash
$ everlink.py
```
In this case all Evernote notebooks will be used to build the list of note meta-data, and the configuration file will be assumed to be called `everjop_relinker.ini` and in the same directory as the source.
To specify the path to the configuration file, use:
```bash
$ everlink.py --config /path/to/config.ini
```
To specify only a single Evernote notebook to process:
```bash
$ everlink.py --notebook MyPersonalNotes
```


