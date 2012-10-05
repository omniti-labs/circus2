"""Various helper functions to make using the API a little easier

Many functions come in a regular and 'pretty' version. The pretty version is
designed to be used in an interactive setting, handling errors, printing
messages and asking for input from the command line. The regular version
doesn't deal with errors, and avoids printing messages where possible.
"""
import log
import sys
import re
from circonusapi import config

def confirm(text="OK to continue?"):
    response = None
    while response not in ['Y', 'y', 'N', 'n']:
        response = raw_input("%s (y/n) " % text)
    if response in ['Y', 'y']:
        return True
    return False

def get_broker(api, broker_name):
    """Find a broker endpoint given its name"""
    rv = api.list_broker()
    brokers = dict([(i['name'], i['_cid']) for i in rv])
    return brokers[broker_name]

def get_broker_pretty(api, broker_name):
    """Find a broker endpoint given its name and exit with an error if it's
    not found.
    """
    try:
        return get_broker(api, broker_name)
    except KeyError:
        log.error("Invalid/Unknown Broker: %s" % broker_name)
        sys.exit(1)

def find_check_bundle(api, pattern):
    """Searches for check_bundles via regular expression on the check name

    Returns a list of checks, and also the values of any matching groups
    specified in the regex.
    """
    all_bundles = api.list_check_bundle()
    filtered_bundles = []
    groups = {}
    for b in sorted(all_bundles):
        m = re.search(pattern, b['display_name'])
        if m:
            filtered_bundles.append(b)
            # Store numbered groups
            matchgroups = m.groups()
            groups[b['_cid']] = {}
            for i in range(0, len(matchgroups)):
                groups[b['_cid']]["group%s" % (i + 1)] = matchgroups[i]
            # Store named groups - (?P<name>...)
            groups[b['_cid']].update(m.groupdict())
    return {
        'bundles': filtered_bundles,
        'groups': groups
    }

def find_check_bundle_pretty(api, pattern):
    log.msg("Retrieving matching checks")
    return find_check_bundle(api, pattern)

def find_metrics(check_bundle, pattern):
    """Retreives metrics for a check bundle by regex

    Also returns a list of metrics that didn't match. Useful when disabling
    metrics - where you need to include all metrics except those that matched.

    Parameters:

        check_bundle - a check bundle returned from the API
        pattern - the regex to match metrics on
    """
    all_metrics = check_bundle['metrics']
    matching_metrics = []
    non_matching_metrics = []
    for i in sorted(all_metrics):
        m = re.search(pattern, i['name'])
        if m:
            matching_metrics.append(i)
        else:
            non_matching_metrics.append(i)
    return {
        'matching': matching_metrics,
        'non_matching': non_matching_metrics
    }

def verify_metrics_pretty(template, check_bundles):
    log.msg("Verifying that bundles have the correct metrics")
    template_metrics = template.get_metrics()
    bundles_with_correct_metrics = []
    bundles_with_wrong_metrics = []
    count = 0
    for b in check_bundles:
        count += 1
        print "\r%s/%s" % (count, len(check_bundles)),
        sys.stdout.flush()
        metrics = b['metrics']
        metric_names = [m['name'] for m in metrics]
        for m in template_metrics:
            if m not in metric_names:
                bundles_with_wrong_metrics.append({
                    'name': b['display_name'],
                    'metric': m})
            else:
                bundles_with_correct_metrics.append(b)
    if bundles_with_wrong_metrics:
        log.msg("The following check bundles do not have metrics specified in"
                " the template:")
        for c in bundles_with_wrong_metrics:
            log.msg("%(name)s - %(metric)s" % c)
        if confirm("Do you want to continue with just the check bundles that"
                " match the template?"):
            log.msg("Continuing with only matching check bundles")
        else:
            log.error("Not continuing. The template does not match the"
                    " bundles")
            sys.exit(1)
        return bundles_with_correct_metrics

