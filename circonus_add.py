#!/usr/bin/env python
import getopt
import json
import re
import sys

from circonusapi import circonusapi
from circonusapi import config
from circuslib import util

conf = config.load_config()

options = {
    'account': conf.get('general', 'default_account'),
    'debug': False
}

def usage():
    print "Usage:"
    print sys.argv[0], "[options] [FILENAME]"
    print
    print "Reads in a json file with a list of resources to add"
    print
    print "  -a -- Specify which account to use"
    print "  -d -- Enable debug mode"

def parse_options():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "a:d?")
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for o,a in opts:
        if o == '-a':
            options['account'] = a
        if o == '-d':
            options['debug'] = not options['debug']
        if o == '-?':
            usage()
            sys.exit(0)
    return args

def get_api():
    token = conf.get('tokens', options['account'], None)
    api = circonusapi.CirconusAPI(token)
    if options['debug']:
        api.debug = True
    return api

def make_changes(changes):
    for c in changes:
        print "Making API Call: %s %s ..." % (c['action'], c['endpoint']),
        if c['action'] == 'DELETE':
            # We don't send any data along for deletions
            c['data'] = None
        try:
            api.api_call(c['action'], c['endpoint'], c['data'])
        except circonusapi.CirconusAPIError, e:
            print "Error"
            print "    %s" % e
            continue
        print "Success"

def json_pairs_hook_dedup_keys(data):
    # json decoder object_pairs_hook that allows duplicate keys, and makes
    # any duplicate keys unique by appending /x1, /x1 and so on to the end.
    # This is used when adding new items via the circonus api, you can just
    # specify /check_bundle multiple times as the endpoint and won't get an
    # error about duplicate keys when decoding the json. Separate code
    # elsewhere automatically strips off the /x1 when selecting the endpoint
    # to use for adding entries.
    d = {}
    ctr = 0
    for k,v in data:
        oldk = k
        while k in d:
            ctr += 1
            k = "%s/x%s" % (oldk, ctr)
        d[k] = v
    return d

def load_json_file(filename):
    with open(filename) as fh:
        return json.load(fh, object_pairs_hook=json_pairs_hook_dedup_keys)

def fix_data_format(data):
    """We accept two formats for adding data:

    A json list, where the '_cid' field is the endpoint to add. We strip off
    any resource ID from the end.

    A json object (python dict), where the keys are the endpoints to add.
    Again we strip off any resource ID. The json parser also will accept
    duplicate keys and dedup them upon loading.

    This function converts the object/dict format into the list format, if
    needed.
    """
    if type(data) == dict:
        new_data = []
        for k, v in data.items():
            v['_cid'] = k
            new_data.append(v)
        return new_data
    return data

def make_additions(api, data):
    for i in data:
        endpoint = re.sub("(?!^)/.*", "", i['_cid'])
        print "Making API Call: POST %s ..." % (endpoint),
        try:
            api.api_call("POST", endpoint, i)
        except circonusapi.CirconusAPIError, e:
            print "Error"
            print "    %s" % e
            continue
        print "Success"

if __name__ == '__main__':
    args = parse_options()
    if len(args) != 1:
        usage()
        sys.exit(2)
    api = get_api()
    data = load_json_file(args[0])
    data = fix_data_format(data)
    if util.confirm("%s additions, OK to continue?" % len(data)):
        make_additions(api, data)
