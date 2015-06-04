# -*- coding: utf-8 -*-
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import getpass
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import keyring_storage
from oauth2client import tools

from .settings import Settings

OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

# Force the noauth_local_webserver flag to cover remote operation (e.g.
# using these commands on a server or in a virtual machine.)
parser = ArgumentParser(description=__doc__,
                        formatter_class=RawDescriptionHelpFormatter,
                        parents=[tools.argparser])
flags = parser.parse_args(['--noauth_local_webserver'])


def get_drive_api():
    """Get drive API client based on settings"""
    settings = Settings()

    if settings.credentials:
        return get_drive_api_from_file(settings.credentials_path)

    if settings.client_secrets:
        return get_drive_api_from_client_secrets(settings.client_secrets_path)


def get_drive_api_from_client_secrets(path, reset_creds=False):
    """
    Reads the local client secrets file if available (otherwise, opens a
    browser tab to walk through the OAuth 2.0 process, and stores the client
    secrets for future use) and then authorizes those credentials. Returns a
    Google Drive API service object.
    """
    storage = keyring_storage.Storage('tarbell', getpass.getuser())
    credentials = None
    if not reset_creds:
        credentials = storage.get()
    if path and not credentials:
        flow = client.flow_from_clientsecrets(path, scope=OAUTH_SCOPE)
        credentials = tools.run_flow(flow, storage, flags)
        storage.put(credentials)

    return _get_drive_api(credentials)


def get_client_secrets_authorize_url(client_secrets_path):  
    """Return the client_secrets authorization url (for admin GUI)"""
    flow = client.flow_from_clientsecrets(client_secrets_path, \
        scope=OAUTH_SCOPE, redirect_uri=client.OOB_CALLBACK_URN)
    return flow.step1_get_authorize_url()


def authorize_client_secrets(client_secrets_path, code):
    """Authorize client_secrets using code (for admin GUI)"""
    flow = client.flow_from_clientsecrets(client_secrets_path, \
        scope=OAUTH_SCOPE, redirect_uri=client.OOB_CALLBACK_URN)

    try:
        storage = keyring_storage.Storage('tarbell', getpass.getuser())
        credentials = flow.step2_exchange(code, http=httplib2.Http())
        storage.put(credentials)        
    except client.FlowExchangeError, e:
        raise Exception('Authentication failed: %s' % e)    


def get_drive_api_from_file(path):
    f = open(path)
    credentials = client.OAuth2Credentials.from_json(f.read())
    return _get_drive_api(credentials)


def _get_drive_api(credentials):
    """For a given set of credentials, return a drive API object"""
    http = httplib2.Http()
    http = credentials.authorize(http)
    service = discovery.build('drive', 'v2', http=http)
    service.credentials = credentials  # duck punch service obj. with credentials
    return service
