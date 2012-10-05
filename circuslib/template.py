"""Template module

Note: The templates in this module are not those inside circonus, but are
simply json files with placeholders for things like check bundle IDs to allow
bulk operations.
"""
import json
import re
import sys

import log

class Template(object):
    """Generic template class for json templates"""
    def __init__(self, filename):
        fh = open(filename)
        self.template = json.load(fh)
        fh.close()
        # Allow a special property __vars in all templates which contain
        # variables specified in the template file itself. This is most useful
        # for when you have repetitive items
        if '__vars' in self.template:
            self.vars = self.template['__vars']
            del self.template['__vars']
        else:
            self.vars = {}
        # Allow '__comment' to be used for file comments
        if '__comment' in self.template:
            del self.template['__comment']

    def sub(self, params):
        """Substitute parameters in the template"""
        return self._process(self.template, params)

    def parse_nv_params(self, params):
        """Parses a list of params in the form name=value into a dict
        suitable for passing to Template.sub"""
        template_params = {}
        for param in params:
            try:
                name, value = param.split('=', 1)
            except ValueError:
                log.error("Invalid parameter: %s" % param)
                log.error("Extra parameters must be specified as name=value")
                sys.exit(1)
            template_params[name] = value
        return template_params

    def _process(self, i, params):
        if type(i) == dict:
            return self._process_dict(i, params)
        if type(i) == list:
            return self._process_list(i, params)
        if type(i) == str or type(i) == unicode:
            return self._process_str(i, params)
        return i

    def _process_dict(self, d, params):
        new_d = {}
        for k, v in d.items():
            new_k = self._process_str(k, params)
            new_d[new_k] = self._process(v, params)
        return new_d

    def _process_list(self, l, params):
        new_l = []
        for i in l:
            new_l.append(self._process(i, params))
        return new_l

    def _apply_filter(self, filter_name, s):
        return getattr(self, "%s_filter" % filter_name, str)(s)

    def _expand_var(self, filter_name, var, params):
        """Recursively expand variables/parameters

        Parameters take precedence over template variables
        """
        expansion = None
        if var in params:
            expansion = params[var]
        elif var in self.vars:
            expansion = self.vars[var]
        if not expansion:
            raise ValueError("Unable to expand variable %s. Perhaps it "
                    "needs to be provided on the command line. " % var)
        # Recursively expand variables
        expansion = self._process_str(expansion, params)
        # Apply any filters
        expansion = self._apply_filter(filter_name, expansion)
        return expansion

    def _process_str(self, s, params):
        return re.sub("{(?:([a-zA-Z_]+):)?([^ }]+)}",
                lambda m: self._expand_var(m.group(1), m.group(2), params), s)

    def ascii_to_octet_filter(self, s):
        return '.'.join(str(ord(i)) for i in s)

    def len_filter(self, s):
        return str(len(s))


class GraphTemplate(Template):
    def __init__(self, name):
        super(GraphTemplate, self).__init__(name, "graph")

    def get_metrics(self):
        """Returns a list of metrics specified in the graph template"""
        return [i['metric_name'] for i in self.template['datapoints']]

    def _process_str(self, s, params):
        # Special case the check_id - make it an integer if it's the only
        # thing present in the string

        if s == "{check_id}":
            return int(params['check_id'])
        return super(GraphTemplate, self)._process_str(s, params)
