#!/usr/bin/python
"""everlink.py

Mark S. Bentley (mark@lunartech.org), 2020

A utility to query the Evernote API and return a list of notes in a give notebook. The list
includes the name, GUID (unique identifier) and creation date of each note.

The joplin API is then queried (an instance of Joplin must be running with the web-clipper
enabled) to search for notes containing inter-note links in imported Evernote notes.

The inter-note link includes the GUID and this is used to locate the GUID and creation date of the
note, which in turn is used to find the filename of the corresponding imported Joplin note.

The API is then used to re-write part of the note, substituting the evernote:// link into a
Jopline link.

"""

import math
import csv
import sys
import json
import configparser
from math import ceil
from lxml import html

# Requires the (experimental!) python3 evernote SDK:
# https://github.com/evernote/evernote-sdk-python3
# TODO: evaluate whether to replace this with simple REST calls
from evernote.api.client import EvernoteClient
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.type.ttypes import NoteSortOrder

import requests

import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                    level=logging.INFO, stream=sys.stdout, datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)


class Evernote():

    def __init__(self, notebook=None, config_file='everlink.ini'):

        self.notebook = None

        try:
            self.config = load_config(config_file)['evernote']
        except KeyError as e:
            log.error('cannot find [Evernote] section in the configuration dictionary')
            return
        self.user_login()
        self.get_user()
        self.set_notebook(notebook)

    def user_login(self):

        # create a client pointing to the operational EN system
        self.client = EvernoteClient(token=self.config['token'], sandbox=False)

        # get the userStore and log the username
        self.userStore = self.client.get_user_store()

        # get the noteStore
        self.noteStore = self.client.get_note_store()
        

    def get_user(self):
        
        user = self.userStore.getUser()
        log.info('user {:s} logged in'.format(user.username))
        
        return self.userStore.getUser()


    def get_notebooks(self):
        return self.noteStore.listNotebooks()


    def get_shared_notebooks(self):
        return self.noteStore.listLinkedNotebooks()


    def list_notebooks(self):
        notebooks = self.get_notebooks()
        for notebook in notebooks:
            print(notebook.name)


    def set_notebook(self, notebook_name):
        """Checks for a notebook with notebook_name and sets it
        as the default for future operations"""

        if notebook_name is not None:

            for notebook in self.get_notebooks():
                if notebook.name == notebook_name:
                    self.notebook = notebook

            if self.notebook is None:
                log.warning('Evernote notebook {:s} not found'.format(notebook_name))


    def get_notes(self, shared=True):

        if self.notebook is None:
            log.debug('no notebook set - using ALL notebooks')
            notebooks = self.get_notebooks()
        else:
            notebooks = [self.notebook]

        spec = NotesMetadataResultSpec(includeTitle=True, includeCreated=True)

        notes = []

        if shared:

            from evernote.api.client import Store

            shared = self.get_shared_notebooks()
            for nb in shared:

                shareKey = nb.shareKey
                note_store_uri = nb.noteStoreUrl
                store = Store(self.client.token, self.noteStore.Client, note_store_uri)
                auth_result = store.authenticateToSharedNotebook(shareKey,self.client.token)
                share_token = auth_result.authenticationToken
                filter = NoteFilter(order=NoteSortOrder.CREATED, notebookGuid=nb.guid)
                notelist = store.findNotesMetadata(filter, 0, 0, spec)
                sdsdf
                # result_list = shared_note_store.findNotesMetadata(share_token, updated_filter, offset, max_notes, result_spec)






                # store = self.client.get_shared_note_store(nb)


                filter = NoteFilter(order=NoteSortOrder.CREATED, notebookGuid=nb.guid)
                notelist = store.findNotesMetadata(filter, 0, 0, spec)
                totalnotes = notelist.totalNotes
                num_queries = math.ceil(totalnotes / maxnotes)

                for query in range(num_queries):
                    note_batch = store.findNotesMetadata(filter, query*maxnotes, maxnotes, spec)
                    for item in note_batch.notes:
                        notes.append(item)

                log.info('retrieved {:d} notes from shared notebook {:s}'.format(totalnotes, nb.name))

        for nb in notebooks:

            filter = NoteFilter(order=NoteSortOrder.CREATED, notebookGuid=nb.guid)
            # find out how many notes are in this notebook
            notelist = self.noteStore.findNotesMetadata(filter, 0, 0, spec)
            totalnotes = notelist.totalNotes

            # max 250 notes can be retrieved in a batch
            maxnotes = 250
            
            # retrieve notes in batches
            num_queries = math.ceil(totalnotes / maxnotes)
            
            for query in range(num_queries):
                note_batch = self.noteStore.findNotesMetadata(filter, query*maxnotes, maxnotes, spec)
                for item in note_batch.notes:
                    notes.append(item)

            # # check we have retrieved everything
            # if len(notes) != totalnotes:
            #     log.warning('could not retrieve all notes ({:d}/{:d}'.format(len(notes), totalnotes))
            log.info('retrieved {:d} notes from notebook {:s}'.format(totalnotes, nb.name))

        return notes


    def getAllSharedNotes(self):
        """Returns a list of all notes shared BY the current user"""

        from evernote.edam.notestore import NoteStore
        from evernote.edam.error.ttypes import EDAMNotFoundException, EDAMSystemException, EDAMUserException
        maxCount = 500
        noteFilter = NoteStore.NoteFilter()
        noteFilter.words = "sharedate:*"
        sharedNotes = []
        offset = 0
        while len(sharedNotes) < maxCount:
            try:
                noteList = self.noteStore.findNotes(self.client.token, noteFilter, offset, 50)
                sharedNotes += noteList.notes
            except (EDAMNotFoundException, EDAMSystemException, EDAMUserException) as e:
                print("Error getting shared notes:")
                print(type(e), e)
                return None

            if len(sharedNotes) % 50 != 0:
                ## We've retrieved all of the notes 
                break
            else:
                offset += 50
        return sharedNotes[:maxCount]



    def write_notes(self, filename):
        """Writes the basic note meta-data to a CSV file"""

        with open(filename, 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            for note in self.notes:
                writer.writerow([note.title, note.guid, note.created])

            


class Joplin:

    default_url = 'http://localhost:41184/'

    def __init__(self, url=default_url, config_file='everlink.ini'):


        try:
            self.config = load_config(config_file)['joplin']
        except KeyError as e:
            log.error('cannot find [Joplin] section in the configuration dictionary')
            return

        self.token = self.config['token']
        if self.config['url'] and self.config['port']:
            self.url = self.config['url'].strip('/') + ':{:s}'.format (self.config['port'])
        else:
            self.url = default_url

    def ping(self):
        
        try:
            r = requests.get(self._url('/ping'), params={'token': self.token})        
            r.raise_for_status()
        except requests.exceptions.RequestException as e: 
            log.error(e)
            return False
            #raise SystemExit(e)

        response =  r.content
        if response != b'JoplinClipperServer':
            log.error('invalid response from server ping - is Joplin running?')
            return False
        else:
            return True       


    def _url(self, path):
        """Helper function to append the path to the base URL"""
        return self.url + path

        
    def get_notes(self, fields=None):

        params = {'token':self.token}
        if fields is not None:
            params.update({'fields': fields})

        try:
            r = requests.get(self._url('/notes'), params=params)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error(e)
            return False
        except requests.exceptions.RequestException as e: 
            log.error(e)
            return False
        notes = r.json()
        return notes


    def get_note(self, note_id, fields=None):

        params = {'token':self.token}
        if fields is not None:
            params.update({'fields': fields})

        try:
            r = requests.get(self._url('/notes/{:s}'.format(note_id)), params=params)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error(e)
            return False
        except requests.exceptions.RequestException as e: 
            log.error(e)
            return False
        
        note = r.json()
        return note

    def update_note(self, note_id, field, data):

        params = {'token':self.token}

        try:
            r = requests.put(self._url('/notes/{:s}'.format(note_id)), data=json.dumps({field: data}), params=params)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error(e)
            return False
        except requests.exceptions.RequestException as e: 
            log.error(e)
            return False
        
        note = r.json()
        return note


    def search_notes(self, query, fields=None):

        params = {'query':query, 'token':self.token}
        if fields is not None:
            params.update({'fields':fields})

        try:
            r = requests.get(self._url('/search'), params=params)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error(e)
            return False
        except requests.exceptions.RequestException as e: 
            log.error(e)
            return False
        
        results = r.json()

        return results


def load_config(config_file):
    """Load the configuration file containing, at minimum,
    the username and password for BOA authentication"""


    config = configparser.ConfigParser()

    try:
        config.read(config_file)
    except configparser.Error as e:
        log.error(e)
        return None

    return config



def main():
    
    import argparse
    import re

    parser = argparse.ArgumentParser()
    parser.add_argument('--notebook', type=str, help='name of the Evernote notebook to query. If none is given, all notebooks are used')
    parser.add_argument('--config', type=str, help='path to the config file')
    parser.add_argument('--debug', type=str, help='boolean flag to enable or disable debug logging')
    args = parser.parse_args()

    # use the Evernote API to get the notes from the notebook
    if args.config:
        if args.notebook:
            nb = Evernote(notebook=args.notebook, config_file=args.config)
        else:
            nb = Evernote(notebook=None, config_file=args.config)
    else:
        if args.notebook:
            nb = Evernote(notebook=args.notebook)
        else:
            nb = Evernote(notebook=None)
    if bool(args.debug)==True:
        log.setLevel(logging.DEBUG)

    en_notes = nb.get_notes(shared=False)
    
    if en_notes is None:
        log.error('no notes returned')
        sys.exit()

    # search for notes in Joplin which contain evernote:// links
    if args.config:
        j = Joplin(config_file=args.config)
    else:
        j = Joplin()
    
    if not j.ping():
        log.error('cannot connect to Joplin, exiting')
        sys.exit()

    # find a list of notes whose body contains evernote:// links
    enex_notes = j.search_notes('body:evernote://', fields='id,title,created_time,markup_language')
    if not enex_notes:
        log.error('could not retrieve list of ENEX notes - aborting')
        sys.exit()

    log.info('Joplin has {:d} notes with Evernote internal links'.format(len(enex_notes)))

    # get a list of ALL notes
    jop_notes = j.get_notes(fields='id,title,created_time,markup_language')

    # this is the meat of the work - loop through each note, extract the link details
    # (which could be in html or markdown), and then:
    #
    # 1. see if we have a note in the en_notes list with matching guid
    # 2. if yes, check if we have a note in enex_notes with the same title + creation date
    # 3. if yes, re-write the html/md and make a PUT request to update the note body in Joplin
    num_links = 0
    num_bad_links = 0
    num_updated = 0

    for note in enex_notes:
        # get note body
        body = j.get_note(note['id'], fields='body')['body']
        # sometimes the search returns hints which are not exact matches
        #if body.find("'evernote://'") == -1:
        #    print('note skipped since evernote:// not found in body')
        #    ssdfsdf
        #    continue
        # check if the links are converted md or plain html
        if note['markup_language'] == 1: # markdown
            # regular expression to match Markdown links with Evernote prefixes
            # [link name](http://www.example.com)
            # \[ = literal open bracket for link name
            # ( = start of group for link name
            # [^\]]+ one or more characters, excluding closing square bracket
            # ) = end of group
            # \] = literal close square bracket
            #
            # \( = literal open bracket for link URL
            # ( = start of group for link URL
            # ( start of group for link URL
            # evernote:\/\/[^)]+ = one or more characters, excluding closing round bracket
            # ) = end of group
            # \) = literal close round bracket

            link_regex = re.compile(r'\[([^\]]+)\]\((evernote:\/\/[^)]+)\)')
            links = list(link_regex.findall(body))
            for link in links:
                guid = link[1].split('/')[6]
                log.debug('Joplin note {:s} has link with GUID {:s}'.format(note['title'], guid))

                # now look for this guid in the set of evernote notes
                match = [note for note in en_notes if note.guid==guid]
                if len(match) == 0:
                    log.warning('could not find note with GUID: {:s}'.format(guid))
                    continue
                elif len(match) > 1:
                    log.warning('found more than one note with GUID: {:s}'.format(guid))
                else:
                    match = match[0]
                    log.debug('GUID {:s} corresponds to Evernote note {:s}'.format(guid, match.title))
                
                # check for a Joplin note with match.title and match.created
                note_id = None
                for n in jop_notes:
                    if (n['title']==match.title) and (n['created_time']==match.created):
                        log.debug('Evernote note with title {:s} and creation date {:d} found in Joplin with ID {:s}'.format(
                            match.title, match.created, n['id']))
                        note_id = n['id']
                        num_links += 1
                        break
                if note_id is None:
                    log.warning('no match could for note with title {:s} and creation time {:d}'.format(match.title, match.created))
                    num_bad_links += 1
                    continue
                # now re-write the link
                # re-write body with regex
                body = link_regex.sub('[\\1](:\/{:s})'.format(n['id']), body)

                # write this back to Joplin
                j.update_note(note['id'], field='body', data=body)
                num_updated += 1



        elif note['markup_language'] == 2:

            if not body.startswith('<en-note'):
                log.warning('HTML note does not start with <en-note>, processing anyway')
            
            body_html = html.fromstring(body)

            # find all links (<a>)
            links = body_html.xpath('//a')
            log.debug('note {:s} has {:d} links'.format(note['title'], len(links)))

            # loop through all links in the note body
            for link in links:
                # check if the href points to an evernote:// link
                href = link.get('href')
                if href is None:
                    continue
                if href.startswith('evernote://'):
                    # extract the GUID
                    guid = href.split('/')[6]
                    log.debug('Joplin note {:s} has link with GUID {:s}'.format(note['title'], guid))
                    
                    # now look for this guid in the set of evernote notes
                    match = [note for note in en_notes if note.guid==guid]
                    if len(match) == 0:
                        log.warning('could not find note with GUID: {:s}'.format(guid))
                        continue
                    elif len(match) > 1:
                        log.warning('found more than one note with GUID: {:s}'.format(guid))
                    else:
                        match = match[0]
                        log.debug('GUID {:s} corresponds to Evernote note {:s}'.format(guid, match.title))
                    
                    # check for a Joplin note with match.title and match.created
                    note_id = None
                    for n in jop_notes:
                        if (n['title']==match.title) and (n['created_time']==match.created):
                            log.debug('Evernote note with title {:s} and creation date {:d} found in Joplin with ID {:s}'.format(
                                match.title, match.created, n['id']))
                            note_id = n['id']
                            num_links += 1
                            break
                    if note_id is None:
                        log.warning('no match could for note with title {:s} and creation time {:d}'.format(match.title, match.created))
                        num_bad_links += 1
                        continue
                    # now re-write the link
                    link.set('href', 'joplin://{:s}'.format(note_id))
                    link.set('title', n['title'])
                    # write this back to Joplin
                    j.update_note(note['id'], field='body', data=html.tostring(body_html).decode())
                    num_updated += 1
                else:
                    log.debug('link is NOT an evernote link ({:s})'.format(href))
        else:
            log.error('unknown note format')
            sys.exit()
            

    log.info('{:d} Joplin notes updated with {:d} links successfully updated, and {:d} failed'.format(num_updated, num_links, num_bad_links))

if __name__ == "__main__":
    main()