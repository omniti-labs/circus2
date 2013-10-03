#!/usr/bin/env python
"""
tag.py - Add tags to resources in bulk

This command takes a regular expression and one or more tags. Any resources
(checks, graphs, worksheets) that match the regular expression will have the
tags applied. You are given the opportunity to preview what items matched
and confirm that you want the tags to be applied.

For tagging items other than check bundles, specify the appropriate endpoint
with the -e option (e.g. ./tag.py -e graph).
"""
import getopt
import re
import sys

from circonusapi import circonusapi
from circonusapi import config
from circuslib import util
from circuslib import log

conf = config.load_config()

options = {
    'account': conf.get('general', 'default_account'),
    'debug': False,
    'endpoint': 'check_bundle'
}


def usage():
    print "Usage:"
    print sys.argv[0], "[options] PATTERN TAG [TAG...]"
    print
    print "Lets you bulk tag resources based on a regex"
    print
    print "  -a -- Specify which account to use"
    print "  -d -- Enable debug mode"
    print "  -e -- Specify the endpoint (check, rule_set) to search/tag"


def parse_options():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "a:d?e:")
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for o, a in opts:
        if o == '-a':
            options['account'] = a
        if o == '-d':
            options['debug'] = not options['debug']
        if o == '-e':
            options['endpoint'] = a
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


def get_matching_resources(api, search_field, pattern):
    log.msg("Finding matching resources")
    try:
        resources = api.api_call('GET', options['endpoint'])
    except circonusapi.CirconusAPIError, e:
        print "ERROR: %s" % e
        return None
    matching = []
    for r in resources:
        if re.search(pattern, r[search_field], re.I):
            matching.append(r)
    return matching


def tag_resources(api, resources, tags, search_field):
    log.msg("Tagging resources:")
    for r in resources:
        old_tags = set(r['tags'])
        new_tags = old_tags | set(tags)
        data = {'tags': list(new_tags)}
        # Exceptions for differnet endpoint types
        if options['endpoint'] == 'graph':
            # You have to provide title/datapoints with any graph changes
            data['title'] = r['title']
            data['datapoints'] = r['datapoints']
        log.debug("Data for %s: %s" % (r['_cid'], data))
        log.msgnb("%s: %s... " % (r['_cid'], r[search_field]))
        if old_tags == new_tags:
            log.msgnf("No change")
            continue
        try:
            api.api_call("PUT", r['_cid'], data)
            log.msgnf("Done")
        except circonusapi.CirconusAPIError, e:
            log.msgnf("Failed")
            log.error(e)

if __name__ == '__main__':
    args = parse_options()
    if options['debug']:
        log.debug_enabled = True
    if len(args) < 2:
        usage()
        sys.exit(2)
    api = get_api()
    pattern = args[0]
    tags = args[1:]

    for t in tags:
        if ':' not in t:
            log.error("Tag '%s' should be of the form category:tag" % t)
            sys.exit(1)

    # What field to search on for a given resource type
    search_fields = {
        'check_bundle': 'display_name',
        'graph': 'title',
        'worksheet': 'title'
    }
    # Default to 'title' as a guess for unknown resource types
    search_field = search_fields.get(options['endpoint'], 'title')
    resources = get_matching_resources(api, search_field, pattern)
    log.msg("Matching resources:")
    for r in resources:
        print "    %5s: %s" % (r['_cid'], r[search_field])
    if util.confirm("Do you want to tag these resources with: %s?" % (
            ', '.join(tags))):
        tag_resources(api, resources, tags, search_field)
    else:
        log.msg("Not applying tags")
