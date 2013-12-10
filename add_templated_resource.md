# add_templated_resource.py - Add a resource in bulk based on a json template

This script provides a way to add graphs, checks, and other circonus resources
in bulk using a json template.

## Usage

    ./add_templated_resource.py \
        -f 'display_name=(some_expression)' \
        template_name.json

When you run the script, at a minimum you need to provide the filename for the
json template to use. You will probably also want to provide a filter (the -f
option), and possibly an endpoint (-e).

The first thing the script does is query the API to get a list of items to add
the template based on. For example, if you're making a graph in bulk of all
website page load times, you'll probably want to add one graph for every check
that contain 'load times' in the check description.

To do this, the script will grab all checks, and filter them by what you
provide. In the above example, you would do something like the following:

    ./add_templated_resource.py \
        -f 'display_name=load times' \
        template_name.json

If the resource you're adding in bulk is not based on a check, then you can
specify another endpoint to query by using the -e option. If it's not
provided, checks will be searched.

Once the script has retrieved a list of checks (or other resource), it will
add a new resource (e.g. graph) based on your template for each check it
found. The values of the check found will be made available to your template,
so you can (for example), use the check id in the graph template.

### Filter argument

The filter argument (-f) consists of a key/value pair separated by an equals
sign.

The key part specified which parameter you want to filter on for the
checks (or other resource) you query. In the case of checks, you will probably
want to filter on 'display_name', which is the check's title. You can pick any
paramater that the API gives back.

The value part of the filter argument is a regular expression to match on. It
isn't anchored at the beginning/end, so if you want to do that, you will need
to add '^' and '$' as appropriate to the regular expression.

If you use matching groups (wrapping part of the regular expression in
parentheses), then they will be provided to the template as `{group1}` to
`{groupN}` variables. You will probably want to do this, as it allows you to
(for example) include part of the check name in the title of the graph you
add.

## Template creation

Templates are simply json files, and for the most part will look like the raw
json output from the circonus API with some values replaced with placeholders.
In addition, they need to have a `_cid` attribute that specifies which
endpoint they are for, such as "/graph" or "/rule".

### Placeholders

Placeholders are of the form `{variablename}`, and will be substituted with
the value of the variable or expression provided within. These variables will
come from the API query results (e.g. the checks), or from matching groups
provided on the command line.

### Matching groups

Variables of the form `{group1}` and `{group2}` are 'matching groups'. When a
filter is specified on the command line, any groups specified in the regular
expression will have their values provided to the template using the group
variables.

For example:

    ./add_templated_resource.py -f 'display_name=(www.*) http'

The `www.*` inside parentheses is a matching group, and all returned checks
will have the relevant part of the display name provided to the template. This
is especially useful for providing titles in templates.

#### Nested values

If you wish to get a nested value inside an array or json object, you can
separate the keys by an underscore. For example, if the json returned from the
circonus API for a check looked like:

    {
        "brokers": [
            "/broker/1",
            "/broker/2"
        ],
        "config": {
            "code": "200",
            ...
        }
        "display_name": "My first check"
    }

then you could use the following variables:

    {display_name} == My first check
    {brokers_0}    == /broker/1
    {brokers_1}    == /broker/2
    {config_code}  == 200


#### Filters

Sometimes the value you need for a template isn't available as is, and an
existing value needs modifying slightly to get what's needed. This is where
filters come in.

Filters are separated from variable names by a colon (:), such as
`{filtername:foo}`.

The currently existing filters are:

 * ascii_to_octet: converts ascii text into dot separated octets. Used to
   generate SNMP OIDs that are based on text.
 * len: returns the length of the string
 * strip_endpoint: Converts /endpoint/123 into just 123. Useful if you need
   the ID of a resource but only the full endpoint is shown.

#### Examples

    {group1}        - the first matching group on the command line
    {display_name}  - the check's display name
    {target}        - the target of the check
    {_checks_0}     - the first value of the _checks array. In other words,
                      the check id of the first check in the check bundle.
    {metrics_0_name} - The name of the first metric in the check
    {len:display_name} - The length of the display name

### Comments

The circonus API will ignore any keys that begin with an underscore when they
are submitted to the API, and by convention, documentation for a template is
kept in a `__comment` field. This should be be a json object, and the keys
within should contain metadata/documentation on using the template. Some
recommendations for keys to include in a comment:

 * summary - a quick overview of what the template does
 * example - an example add_templated_resource.py invocation showing how you
   would use the template. This is especially helpful if you use matching
   groups in the filter and/or a different endpoint than /checks.
 * notes - any other notes on template usage. Here you can explain what
   matching groups should be used for (e.g. first matching group should be the
   server name, the second matching group should match the port)

### Templates with multiple resources

A template is normally a single json object (hash, map, dictionary) with a
single resource to add. However, the template can also be a list of objects
containing multiple resources to add (e.g. multiple graphs for the same check)
and all of them will be added.

### Walk through of template creation

The following is a walk through for creating a website latency graph template,
which can then be used to create latency graphs in bulk for all websites
monitored.

The first step is to create (or find) an existing graph in circonus for a
single check that meets your needs. Creating a single graph is best done in
the web interface and you can tweak the layout as desired.

Once you have found or created the graph required, note down the uuid of the
graph, which will look something like `550e8400-e29b-41d4-a716-446655440000`
and will be shown in the URL when you view the graph.

Next, you need to export the graph. This can be done using circonusvi, or via
curl. Here I'm going to use circonusvi:

    ./circonusvi.py -e graph '_cid=550e8400-e29b-41d4-a716-446655440000'

Circonusvi shows results as a json object containing multiple keys for each
graph returned. We only want a single graph and so should edit the file to
just show the values for the graph we want. The results should look something
like this:

    {
        "composites": [],
        "datapoints": [
            {
                "alpha": "0.3",
                "axis": "l",
                "check_id": 1234,
                "color": "#33aa33",
                "data_formula": null,
                "derive": "gauge",
                "hidden": false,
                "legend_formula": null,
                "metric_name": "tt_connect",
                "metric_type": "numeric",
                "name": "www.example.com http time to initial connect (ms)",
                "stack": null
            },
            {
                "alpha": "0.3",
                "axis": "l",
                "check_id": 1234,
                "color": "#4a00dc",
                "data_formula": null,
                "derive": "gauge",
                "hidden": false,
                "legend_formula": null,
                "metric_name": "tt_firstbyte",
                "metric_type": "numeric",
                "name": "www.example.com http time to first byte (ms)",
                "stack": null
            },
            {
                "alpha": "0.3",
                "axis": "l",
                "check_id": 1234,
                "color": "#caac00",
                "data_formula": null,
                "derive": "gauge",
                "hidden": false,
                "legend_formula": null,
                "metric_name": "duration",
                "metric_type": "numeric",
                "name": "www.example.com http time to document complete (ms)",
                "stack": null
            },
            {
                "alpha": "0.3",
                "axis": null,
                "check_id": 1234,
                "color": "#3377cc",
                "data_formula": null,
                "derive": false,
                "hidden": false,
                "legend_formula": null,
                "metric_name": "code",
                "metric_type": "text",
                "name": "www.example.com http response code",
                "stack": null
            }
        ],
        "description": null,
        "guides": [],
        "max_left_y": null,
        "max_right_y": null,
        "min_left_y": null,
        "min_right_y": null,
        "notes": null,
        "style": "area",
        "tags": [],
        "title": "www.example.com http"
    }

Save this to a json file, which will become the template.

Next, we need to make this into a template. This consists of finding the items
that are specific to the one graph, and adding placeholders to substitute
values in as appropriate.

The first specific item is the graph title and metric names, all of which
contain the website address 'www.example.com'. We need to add a placeholder to
this, and it is most likely going to come as part of the check name. If we use
a regular expression matching group, then the user can specify which part of
the check name is the website address when they run the template. The
advantage of this is that we don't need to know the format of the check title
in advance.

To do this, replace all occurrences of 'www.example.com' in the json file with
'{group1}'. The following is an example of the command to use in vi/vim:

    :%s/www.example.com/{group1}/g

This takes care of the title and legend values, but the actual data still
comes from the same check. In this case it's check '1234'.

We need to add a placeholder to extract the check id from the results we get
when searching the API for checks.

The placeholder we want in this case is `{strip_endpoint:_checks_0}`. This
means:

 * Look at the `_checks` attribute returned from the API for each check. This
   contains a read_only list of checks for each check bundle.
 * We can just pick the first of these checks - if you have a single check
   bundle on multiple brokers then there will be more than one value here, but
   in that case you'll probably want a combined graph showing http connect
   times from multiple locations. The `_0` part picks just the first check ID.
 * The check_id field in the template is just a number: `1234`, but the value
   shown in the `_checks` field is a full endpoint: `/checks/1234`. We use the
   `strip_endpoint` filter to extract just the ID.

One thing we haven't specified so far is what this is a template for. This is
done with the `_cid` attribute. Add the following key at the top of the json
object:

    "_cid": "/graph",

The template is now done, just add a comment with some documentation and it's
complete:

    "__comment": {
        "summary": "A http latency graph for HTTP checks",
        "example": "./add_templated_resource.py -f 'display_name=(.*) http' http.json",
        "notes": "The first matching group is used as part of the graph title and should show the hostname of the site being monitored"
    },
