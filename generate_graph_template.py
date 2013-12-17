#!/usr/bin/env python
"""
Creates a graph template suitable for use add_templated_resource from
circonusvi output containing graph data.

Usage:
  - Create your graphs in the circonus web interface
  - Run circonusvi.py -c -e graph [pattern]
    - The pattern should be enough to limit the output to just the graphs you
      want to make the template for.
  - Save the json output to a file
  - Run generate_graph_template.py filename.json > template.json

Assumptions/limitations:
  - Graph titles have a hostname or IP address at the beginning, which will
  be replaced with the hostname/ip address when adding the graphs back in
  using matching groups on the check name. If a hostname/ip address isn't
  present, then the title is left alone.
  - All graphs only contain metrics from a single check. Check IDs are
  blindly replaced with a variable for the check id.
  - The check ID inserted into the template is the first one listed for each
  check bundle. This means that checks on multiple brokers won't work
  correclty.
"""

import json
import re
import sys

with open(sys.argv[1]) as fh:
    data = json.load(fh)

out = []

for k, v in data.items():
    if not k.startswith('/graph/'):
        sys.stderr.write("WARNING: Non-graph resource found: %s, skipping\n"
                         % k)
        continue
    # We don't want access keys in the template
    del v['access_keys']
    # Set the check id to be templated
    for d in v['datapoints']:
        d['check_id'] = '{strip_endpoint:_checks_0}'
    # Set the cid
    v['_cid'] = '/graph'
    # Genericize the title - looks for something hostname/ip-like at the
    # beginning and replaces it if it is there.
    v['title'] = re.sub('^[a-zA-Z0-9]+\.[a-zA-Z0-9.]+', '{group1}',
                        v['title'])
    out.append(v)

print json.dumps(out, indent=4, sort_keys=True)
