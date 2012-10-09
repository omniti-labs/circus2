#!/usr/bin/env python
"""Adds snmp checks for a switch """

import getopt
import re
import subprocess
import sys

from circonusapi import circonusapi
from circonusapi import config
from circuslib import log, util


# OID prefixes
prefix_1 = ".1.3.6.1.2.1.2.2.1"
prefix_2 = ".1.3.6.1.2.1.31.1.1.1"

oids = {
    'status':       "%s.8" % prefix_1,
    'name':         "%s.18" % prefix_2,
    'speed':        "%s.5" % prefix_1,
    'in_octets':    "%s.6" % prefix_2,  # 64-bit version
    'out_octets':   "%s.10" % prefix_2,  # 64-bit counter
    'in_errors':    "%s.14" % prefix_1,
    'out_errors':   "%s.20" % prefix_1}
metrics = [
    { "name": "in_errors", "type": "numeric" },
    { "name": "in_octets", "type": "numeric" },
    { "name": "name", "type": "text" },
    { "name": "out_errors", "type": "numeric" },
    { "name": "out_octets", "type": "numeric" },
    { "name": "speed", "type": "numeric" },
    { "name": "status", "type": "numeric" }
]
port_name_prefix = "%s.1" % prefix_2

def get_ports(params):
    """Looks up what ports are on the switch via snmpwalk"""
    output = subprocess.Popen(("/usr/bin/snmpwalk", "-On", "-v2c", "-c",
        params['community'], params['target'], port_name_prefix),
        stdout=subprocess.PIPE).communicate()[0]
    ports = {}
    for line in output.split("\n"):
        m = re.match(
            r'[.0-9]+\.(\d+) = STRING: "?(?:ethernet)?([0-9/]+)"?', line)
        if m:
            if not params['pattern'] or re.match(params['pattern'], m.group(2)):
                ports[m.group(2)] = m.group(1)
    return ports

def add_checks(params):
    for name, idx in sorted(params['ports'].items()):
        log.msgnb("Adding port %s..." % name)
        check_bundle = {
            "brokers": [ "/broker/%s" % params['broker'] ],
            "config": {
                "community": params['community'],
                "port": params['snmp_port']
            },
            "display_name" : "%s port %s interface stats" % (
                        params['friendly_name'], name),
            "metrics": [],
            "period": 60,
            "status": "active",
            "target": params['target'],
            "timeout": 10,
            "type": "snmp"
        }

        for m in metrics:
            check_bundle["metrics"].append(m)
            check_bundle['config']["oid_%s" % m['name']] = "%s.%s" % (
                    oids[m['name']], idx)

        try:
            api.add_check_bundle(check_bundle)
            log.msgnf("Success")
        except circonusapi.CirconusAPIError, e:
            log.msgnf("Failed")
            log.error(e)

def usage(params):
    print "Usage: %s [opts] TARGET FRIENDLY_NAME PATTERN" % sys.argv[0]
    print """
This command queries the switch using snmpwalk to discover what ports
to add checks for. This requires that the snmpwalk command be
available and that the switch be accessible over snmp from the machine
that this command is run from.

Arguments:
    target          -- The address of the switch
    friendly_name   -- what to call the switch in the check name. This
                       is usually the (short) hostname of the switch.
    pattern         -- An optional regex to limit which ports to add.

"""
    print "Options:"
    print "  -a -- account"
    print "  -c -- SNMP community (default: %s)" % (params['community'],)
    print "  -p -- SNMP port (default: %s)" % (params['snmp_port'],)
    print "  -b -- ID of the broker to use: (default: %s)" % (
            params['broker'],)

if __name__ == '__main__':
    # Get the api token from the rc file
    c = config.load_config()
    account = c.get('general', 'default_account')

    params = {
        'community': 'public',
        'snmp_port': 161,
        'broker': 1,
        'debug': False
    }

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "a:b:c:dp:")
    except getopt.GetoptError, err:
        print str(err)
        usage(params)
        sys.exit(2)

    for o,a in opts:
        if o == '-a':
            account = a
        if o == '-b':
            params['broker'] = a
        if o == '-c':
            params['community'] = a
        if o == '-d':
            params['debug'] = not params['debug']
        if o == '-p':
            params['snmp_port'] = a

    # Rest of the command line args
    try:
        params['target'] = args[0]
        params['friendly_name'] = args[1]
    except IndexError:
        usage(params)
        sys.exit(1)
    try:
        params['pattern'] = args[2]
    except IndexError:
        params['pattern'] = None

    # Now initialize the API
    api_token = c.get('tokens', account)
    api = circonusapi.CirconusAPI(api_token)

    if params['debug']:
        api.debug = True
        log.debug_enabled = True

    ports = get_ports(params)
    log.msg("About to add checks for the following ports:")
    for port in sorted(ports):
        log.msg(port)
    params['ports'] = ports
    if util.confirm():
        add_checks(params)
