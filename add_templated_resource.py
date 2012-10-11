#!/usr/bin/env python
"""Adds a resource (e.g. graph) in bulk based on a template

The command also makes an api query and uses values from the (filtered)
results of that query to fill in values in the template. Values can also be
specified on the command line to provide information (such as human readable
titles) that isn't available by querying existing resources.

 * Templates are json objects containing the data to add.
 * They may contain variables of the form "{variable_name}", which will be
   substituted with values from the api query results, or from the command
   line.
 * The _cid value in the template specifies the endpoint that the template is
   for. The _cid value shouldn't have a resource ID at the end, so be sure to
   strip it if you are using output from the api to make a template.

TODO (docs)

    * Variable filters {foo:filtername}
    * matching groups from the query filter (e.g. extracting information from
        the check name to put in the graph title)
    * How to make a template:
        * Grab json for an existing resource (e.g. using circonusvi)
        * Add/edit a '_cid' entry with the endpoint.
        * Add a '__comment' entry with information on the template
            * Show an example of what to include based on switch.json
        * Edit out information you want to be different for each entry
            * check_id is a good one (set to "{_cid}")
            * use matching groups if you need to extract part of a result
              (such as a check's display name) and put it in the template.
              See the switch graph for an example.

Example - adding graphs for all checks on switch-foo:

    ./add_template_resource.py \
            -f 'display_name=(switch-foo) port (.*)' \
            switch_graph.json
"""

import getopt
import re
import sys

from circonusapi import circonusapi
from circonusapi import config
from circuslib import log, util, template

def usage(params):
    print "Usage: %s [opts] TEMPLATE_FILE [VAR=VALUE ...]" % sys.argv[0]
    print """
This command queries the switch using snmpwalk to discover what ports
to add checks for. This requires that the snmpwalk command be
available and that the switch be accessible over snmp from the machine
that this command is run from.

Arguments:
    TEMPLATE_FILE   -- A json template
    VAR=VALUE       -- One or more values to substitute in the template
"""
    print "Options:"
    print "  -a -- account"
    print "  -d -- debug (default: %s)" % (params['debug'])
    print "  -e -- endpoint to query for template values (default: %s)" % (
            params['endpoint'])
    print "  -f -- filter on the query (default: %s)" % (params['filter'])

def run_query(params, api):
    log.debug("Querying endpoint: %s" % params['endpoint'])
    results = api.api_call("GET", params['endpoint'])
    filtered_results = []
    k, v = params['filter'].split('=', 1)
    log.debug("Filter is checking that %s matches %s" % (k,v))
    for r in results:
        match = re.search(v, r[k])
        if match:
            for i, j in enumerate(match.groups()):
                # Adds group1, group2 etc. variables
                r['group%s' % (i+1)] = j
            filtered_results.append(r)

    return filtered_results

def flatten_dict(d):
    """Flattens a dictionary/list combo into a 1-level dict.
    Keys are compressed (e.g. {"a": {"b": 0}} becomes: {"a_b": 0}), and lists
    are treated as dicts with numerical keys"""
    scalars = ((k, v) for k, v in d.items() if type(v) not in [dict, list])
    lists = ((k, v) for k, v in d.items() if type(v) == list)
    dicts = [(k, v) for k, v in d.items() if type(v) == dict]
    for l in lists:
        dicts.append((l[0], dict(((k, v) for k, v in enumerate(l[1])))))
    flattened = {}
    flattened.update(scalars)
    for key, d in dicts:
        flattened_d = flatten_dict(d)
        flattened.update(dict(("%s_%s" % (key, k), v) for k, v in
            flattened_d.items()))
    return flattened

def merge_params(static_vars, resource):
    merged_params = {}
    merged_params.update(static_vars)
    merged_params.update(flatten_dict(resource))
    return merged_params

if __name__ == '__main__':
    # Get the api token from the rc file
    c = config.load_config()
    account = c.get('general', 'default_account')

    params = {
        'endpoint': 'check_bundle',
        'filter': ".*",
        'debug': False
    }

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "a:de:f:")
    except getopt.GetoptError, err:
        print str(err)
        usage(params)
        sys.exit(2)

    for o,a in opts:
        if o == '-a':
            account = a
        if o == '-d':
            params['debug'] = not params['debug']
        if o == '-e':
            params['endpoint'] = a
        if o == '-f':
            params['filter'] = a

    # Rest of the command line args
    try:
        params['template'] = args[0]
    except IndexError:
        usage(params)
        sys.exit(1)
    params['vars'] = args[1:]

    # Now initialize the API
    api_token = c.get('tokens', account)
    api = circonusapi.CirconusAPI(api_token)

    if params['debug']:
        api.debug = True
        log.debug_enabled = True

    t = template.Template(params['template'])
    params['vars'] = t.parse_nv_params(params['vars'])
    results = run_query(params, api)
    to_add = []
    for r in results:
        merged_params = merge_params(params['vars'], r)
        processed = t.sub(merged_params)
        to_add.append(processed)
    if util.confirm("%s additions to be made. Continue?" % len(to_add)):
        for i in range(0, len(to_add)):
            log.msgnb("Adding entry %s..." % i)
            api.api_call("POST", to_add[i]['_cid'], to_add[i])
