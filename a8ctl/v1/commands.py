# Copyright 2016 IBM Corporation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# Implementation of Amalgam8 CLI functions

import sys
import requests
import json
import sets
from urlparse import urlparse
from prettytable import PrettyTable
import os
import urllib
import datetime, time
import pprint
from parse import compile
from gremlin import ApplicationGraph, A8FailureGenerator, A8AssertionChecker

def passOrfail(result):
    if result:
        return "PASS"
    else:
        return "FAIL"

def a8_get(url, token, headers={'Accept': 'application/json'}, showcurl=False, extra_headers={}):
    if token != "" :
        headers['Authorization'] = "Bearer " + token
    if extra_headers:
        headers=dict(headers.items() + extra_headers.items())

    if showcurl:
        curl_headers = ' '.join(["-H '{0}: {1}'".format(key, value) for key, value in headers.iteritems()])
        print "curl", curl_headers, url

    try:
        r = requests.get(url, headers=headers)
    except Exception, e:
        sys.stderr.write("Could not contact {0}".format(url))
        sys.stderr.write("\n")
        sys.stderr.write(str(e))
        sys.stderr.write("\n")
        sys.exit(2)

    if showcurl:
        print r.text

    return r

def a8_post(url, token, body, headers={'Accept': 'application/json', 'Content-type': 'application/json'}, showcurl=False, extra_headers={}):
    """
    @type body: str
    """
    if token != "" :
        headers['Authorization'] = "Bearer " + token
    if extra_headers:
        headers=dict(headers.items() + extra_headers.items())

    if showcurl:
        curl_headers = ' '.join(["-H '{0}: {1}'".format(key, value) for key, value in headers.iteritems()])
        print "REQ:", "curl -i -X POST", url, curl_headers, "--data", '\'{0}\''.format(body.replace('\'', '\\\''))

    try:
        r = requests.post(url, headers=headers, data=body)
    except Exception, e:
        sys.stderr.write("Could not POST to {0}".format(url))
        sys.stderr.write("\n")
        sys.stderr.write(str(e))
        sys.stderr.write("\n")
        sys.exit(2)

    if showcurl:
        print "RESP: [{0}]".format(r.status_code), r.headers
        print "RESP BODY:", r.text

    return r

def a8_put(url, token, body, headers={'Accept': 'application/json', 'Content-type': 'application/json'}, showcurl=False, extra_headers={}):
    """
    @type body: str
    """

    if token != "" :
        headers['Authorization'] = "Bearer " + token
    if extra_headers:
        headers=dict(headers.items() + extra_headers.items())

    if showcurl:
        curl_headers = ' '.join(["-H '{0}: {1}'".format(key, value) for key, value in headers.iteritems()])
        print "REQ:", "curl -i -X PUT", url, curl_headers, "--data", '\'{0}\''.format(body.replace('\'', '\\\''))

    try:
        r = requests.put(url, headers=headers, data=body)
    except Exception, e:
        sys.stderr.write("Could not PUT to {0}".format(url))
        sys.stderr.write("\n")
        sys.stderr.write(str(e))
        sys.stderr.write("\n")
        sys.exit(2)

    if showcurl:
        print "RESP: [{0}]".format(r.status_code), r.headers
        print "RESP BODY:", r.text

    return r


def a8_delete(url, token, headers={'Accept': 'application/json'}, showcurl=False, extra_headers={}):
    if token != "" :
        headers['Authorization'] = "Bearer " + token
    if extra_headers:
        headers=dict(headers.items() + extra_headers.items())

    if showcurl:
        curl_headers = ' '.join(["-H '{0}: {1}'".format(key, value) for key, value in headers.iteritems()])
        print "curl -X DELETE", curl_headers, url

    try:
        r = requests.delete(url, headers=headers)
    except Exception, e:
        sys.stderr.write("Could not DELETE {0}".format(url))
        sys.stderr.write("\n")
        sys.stderr.write(str(e))
        sys.stderr.write("\n")
        sys.exit(2)

    return r

def get_field(d, key):
    if key not in d:
        return '***MISSING***'
    return d[key]

def fail_unless(response, code_or_codes):
    if not isinstance(code_or_codes, list):
        code_or_codes = [code_or_codes]
    if response.status_code not in code_or_codes:
        print response
        print response.text
        sys.exit(3)

# def get_registry_credentials(tenant_info, args):
#     registry = tenant_info["credentials"]["registry"]
#     registry_url = registry["url"] if args.a8_registry_url is None else args.a8_registry_url
#     registry_token = registry["token"] if args.a8_registry_token is None else args.a8_registry_token
#     return registry_url, "Bearer " + registry_token

def is_active(service, default_version, registry_url, registry_token, debug=False):
    r = a8_get('{0}/api/v1/services/{1}'.format(registry_url, service), registry_token, showcurl=debug)
    if r.status_code == 200:
        instance_list = r.json()["instances"]
        for instance in instance_list:
            version = instance["metadata"]["version"] if "metadata" in instance and "version" in instance["metadata"] else NO_VERSION
            if version == default_version:
                return True
    return False

NO_VERSION = "UNVERSIONED"
SELECTOR_PARSER = compile("{version}=#{rule}#") # TODO: tolerate white-space in format

############################################
# CLI Commands
############################################

def service_list(args):
    # r = a8_get('{0}/v1/tenants'.format(args.a8_controller_url),
    #            args.a8_controller_token,
    #            showcurl=args.debug)
    # fail_unless(r, 200)
    # tenant_info = r.json()
    # registry_url, registry_token = get_registry_credentials(tenant_info, args)
    registry_url, registry_token = args.a8_registry_url, args.a8_registry_token
    r = a8_get('{0}/api/v1/services'.format(registry_url), registry_token, showcurl=args.debug)
    fail_unless(r, 200)
    service_list = r.json()["services"]
    result_list = []
    for service in service_list:
        r = a8_get('{0}/api/v1/services/{1}'.format(registry_url, service), registry_token, showcurl=args.debug)
        fail_unless(r, 200)
        instance_list = r.json()["instances"]
        version_counts = {}
        for instance in instance_list:
            version = instance["metadata"]["version"] if "metadata" in instance and "version" in instance["metadata"] else NO_VERSION
            version_counts[version] = version_counts.get(version, 0) + 1
        result_instances = []
        for version, count in version_counts.iteritems():
            result_instances.append("%s(%s)" % (version, count))
        result_list.append({"service": service, "instances": result_instances})
    if args.json:
        print json.dumps(result_list, indent=2)
    else:
        x = PrettyTable(["Service", "Instances"])
        x.align = "l"
        for entry in result_list:
            service = entry["service"]
            versions = ", ".join(entry["instances"])
            x.add_row([service, versions])
        print x

def service_routing(args):
    # r = a8_get('{0}/v1/tenants'.format(args.a8_controller_url),
    #            args.a8_controller_token,
    #            showcurl=args.debug)
    # fail_unless(r, 200)
    # tenant_info = r.json()
    # registry_url, registry_token = get_registry_credentials(tenant_info, args)
    registry_url, registry_token = args.a8_registry_url, args.a8_registry_token
    r = a8_get('{0}/api/v1/services'.format(registry_url), registry_token, showcurl=args.debug)
    fail_unless(r, 200)
    service_list = r.json()["services"]
    result_list = []
    for value in tenant_info['filters']['versions']:
        service = get_field(value, 'service')
        if service in service_list:
            service_list.remove(service)
        default = value.get('default')
        if not default:
            default = NO_VERSION
        selectors = value.get('selectors')
        versions = []
        if selectors:
            selectors = selectors[selectors.find("{")+1:][:selectors.rfind("}")-1]
            selector_list = selectors.split(",")
            for selector in selector_list:
                r = SELECTOR_PARSER.parse(selector.replace("{","#").replace("}","#"))
                versions.append("%s(%s)" % (r['version'], r['rule']))
            result_list.append({"service": service, "default": default, "selectors": versions})
        else:
            result_list.append({"service": service, "default": default})
    for service in service_list:
        result_list.append({"service": service, "default": NO_VERSION})
    if args.json:
        print json.dumps(result_list, indent=2)
    else:
        x = PrettyTable(["Service", "Default Version", "Version Selectors"])
        x.align = "l"
        for entry in result_list:
            x.add_row([entry["service"],
                       entry["default"],
                       ", ".join(entry["selectors"]) if "selectors" in entry else ""
                       ])
        print x

def set_routing(args):
    if not args.default and not args.selector:
         print "You must specify --default or at least one --selector argument"
         sys.exit(4)

    routing_request = {}

    if args.default:
        routing_request['default'] = args.default

    if args.selector:
        selector_list = []
        for selector in args.selector:
            selector_list.append(selector.replace("(","={").replace(")","}"))
        routing_request['selectors'] = "{" + ",".join(selector_list) + "}"

    r = a8_put('{0}/v1/versions/{1}'.format(args.a8_controller_url, args.service),
               args.a8_controller_token,
               json.dumps(routing_request),
               showcurl=args.debug)
    fail_unless(r, 200)
    print 'Set routing rules for microservice', args.service

def delete_routing(args):
    r = a8_delete('{0}/v1/versions/{1}'.format(args.a8_controller_url, args.service),
               args.a8_controller_token,
               showcurl=args.debug)
    fail_unless(r, 200)
    print 'Deleted routing rules for microservice', args.service

def rules_list(args):
    r = a8_get('{0}/v1/rules'.format(args.a8_controller_url),
               args.a8_controller_token,
               showcurl=args.debug)
    fail_unless(r, 200)
    response = r.json()
    result_list = []
    for value in response['rules']:
        result_list.append({"id": value["id"],
                            "source": value["source"],
                            "destination": value["destination"],
                            "header": value["header"],
                            "header_pattern": value["pattern"],
                            "delay_probability": value["delay_probability"],
                            "delay": value["delay"],
                            "abort_probability": value["abort_probability"],
                            "abort_code": value["return_code"]})
    if args.json:
        print json.dumps(result_list, indent=2)
    else:
        x = PrettyTable(["Source", "Destination", "Header", "Header Pattern", "Delay Probability", "Delay", "Abort Probability", "Abort Code", "Rule Id"])
        x.align = "l"
        for entry in result_list:
            x.add_row([entry["source"],
                       entry["destination"],
                       entry["header"],
                       entry["header_pattern"],
                       entry["delay_probability"],
                       entry["delay"],
                       entry["abort_probability"],
                       entry["abort_code"],
                       entry["id"]
            ])
        print x

def set_rule(args):
    if not args.source or not args.destination or not args.header:
         print "You must specify --source, --destination, and --header"
         sys.exit(4)

    rule_request = {
        "source": args.source,
        "destination": args.destination,
        "header" : args.header
    }

    if args.pattern:
        rule_request['pattern'] = '.*?'+args.pattern
    else:
        rule_request['pattern'] = '.*'

    if args.delay:
        rule_request['delay'] = args.delay
    if args.delay_probability:
        rule_request['delay_probability'] = args.delay_probability
    if args.abort_probability:
        rule_request['abort_probability'] = args.abort_probability
    if args.abort_code:
        rule_request['return_code'] = args.abort_code

    if not (args.delay > 0 and args.delay_probability > 0.0) and not (args.abort_code and args.abort_probability > 0.0):
        print "You must specify either a valid delay with non-zero delay_probability or a valid abort-code with non-zero abort-probability"
        sys.exit(4)

    payload = {"rules": [rule_request]}

    r = a8_post('{}/v1/rules'.format(args.a8_controller_url),
                args.a8_controller_token,
                json.dumps(payload),
                showcurl=args.debug)
    fail_unless(r, 201)
    print 'Set fault injection rule between %s and %s' % (args.source, args.destination)

def clear_rules(args):

    r = a8_delete('{0}/v1/rules'.format(args.a8_controller_url),
                  args.a8_controller_token,
                  showcurl=args.debug)
    fail_unless(r, 200)
    print 'Cleared fault injection rules from all microservices'

def delete_rule(args):
    r = a8_delete('{}/v1/rules?id={}'.format(args.a8_controller_url, args.id),
                  args.a8_controller_token,
                  showcurl=args.debug)
    fail_unless(r, 200)
    print 'Deleted fault injection rule with id: %s' % args.id

def _print_assertion_results(results):
    x = PrettyTable(["AssertionName", "Source", "Destination", "Result", "ErrorMsg"])
    x.align = "l"
    newlist={}
    for res in results:
        res['result']=passOrfail(res['result'])
    #pprint.pprint(results)
    for check in results:
        x.add_row([get_field(check, 'name'),
                   get_field(check, 'source'),
                   get_field(check, 'dest'),
                   get_field(check, 'result'),
                   get_field(check, 'errormsg')
        ])
    print x

def run_recipe(args):
    if not args.topology or not args.scenarios:
        print "You must specify --topology and --scenarios"
        sys.exit(4)

    if args.header:
        header = args.header
    else:
        header = "X-Request-ID"

    if args.pattern:
        pattern = args.pattern
    else:
        pattern = '*'

    if not os.path.isfile(args.topology):
        print u"Topology file {} not found".format(args.topology)
        sys.exit(4)

    if not os.path.isfile(args.scenarios):
        print u"Failure scenarios file {} not found".format(args.scenarios)
        sys.exit(4)

    if args.checks and not os.path.isfile(args.checks):
        print u"Checklist file {} not found".format(args.checks)
        sys.exit(4)

    with open(args.topology) as fp:
        app = json.load(fp)
    topology = ApplicationGraph(app)
    if args.debug:
        print "Using topology:\n", topology

    with open(args.scenarios) as fp:
        scenarios = json.load(fp)

    if args.checks:
        with open(args.checks) as fp:
            checklist = json.load(fp)

    fg = A8FailureGenerator(topology, a8_controller_url='{0}/v1/rules'.format(args.a8_controller_url), a8_controller_token=args.a8_controller_token, 
                            header=header, pattern='.*?'+pattern, debug=args.debug)
    fg.setup_failures(scenarios)

    start_time = datetime.datetime.utcnow().isoformat()
    #print start_time

    if args.checks:
        if args.run_load_script:
            import subprocess
            #print ">>>", args.run_load_script
            retcode = subprocess.call([args.run_load_script])
            if retcode: #load injection failed. Do not run assertions
                sys.exit(retcode)
        else:
            print 'Inject test requests with HTTP header %s matching the pattern %s' % (header, pattern)
            print ('When done, press Enter key to continue to validation phase')
            a = sys.stdin.read(1)

        #sleep for 3sec to make sure all logs reach elasticsearch
        time.sleep(3)

        end_time=datetime.datetime.utcnow().isoformat()
        #print end_time

        #sleep for some more time to make sure all logs have been flushed
        time.sleep(5)

        log_server = checklist.get('log_server', args.a8_log_server)

        # TODO: Obtain the logstash index as user input or use logstash-YYYY.MM.DD with current date and time.
        ac = A8AssertionChecker(es_host=log_server, header=header, pattern=pattern,
                                start_time=start_time, end_time=end_time, index=["_all"], debug=args.debug)
        results = ac.check_assertions(checklist, continue_on_error=True)
        if args.json:
            print json.dumps(results, indent=2)
        else:
            _print_assertion_results(results)
        clear_rules(args)

def traffic_start(args):
    if args.amount < 0 or args.amount > 100:
         print "--amount must be between 0 and 100"
         sys.exit(4)
    r = a8_get('{0}/v1/versions/{1}'.format(args.a8_controller_url, args.service),
               args.a8_controller_token,
               showcurl=args.debug)
    fail_unless(r, [200, 404])
    if r.status_code == 200:
        service_info = r.json()
        if service_info['selectors']:
            print "Invalid state for start operation: service \"%s\" traffic is already being split" % args.service
            sys.exit(5)
    else:
        service_info = {}
    default_version = service_info.get('default')
    if not default_version:
        default_version = NO_VERSION
    # r = a8_get('{0}/v1/tenants'.format(args.a8_controller_url),
    #            args.a8_controller_token,
    #            showcurl=args.debug)
    # fail_unless(r, 200)
    # tenant_info = r.json()
    # registry_url, registry_token = get_registry_credentials(tenant_info, args)
    registry_url, registry_token = args.a8_registry_url, args.a8_registry_token
    if not is_active(args.service, default_version, registry_url, registry_token, args.debug):
        print "Invalid state for start operation: service \"%s\" is not currently receiving traffic" % args.service
        sys.exit(6)
    if not is_active(args.service, args.version, registry_url, registry_token, args.debug):
        print "Invalid state for start operation: service \"%s\" does not have active instances of version \"%s\"" % (args.service, args.version)
        sys.exit(7)
    if args.amount == 100:
        service_info['default'] = args.version
    else:
        service_info['selectors'] = "{%s={weight=%s}}" % (args.version, float(args.amount)/100)
    r = a8_put('{0}/v1/versions/{1}'.format(args.a8_controller_url, args.service),
               args.a8_controller_token,
               json.dumps(service_info),
               showcurl=args.debug)
    fail_unless(r, 200)
    if args.amount == 100:
        print 'Transfer complete for {}: sending {}% of traffic to {}'.format(args.service, args.amount, args.version)
    else:
        print 'Transfer starting for {}: diverting {}% of traffic from {} to {}'.format(args.service, args.amount, default_version, args.version)

def traffic_step(args):
    r = a8_get('{0}/v1/versions/{1}'.format(args.a8_controller_url, args.service),
               args.a8_controller_token,
               showcurl=args.debug)
    fail_unless(r, 200)
    service_info = r.json()
    default_version = service_info.get('default')
    if not default_version:
        default_version = NO_VERSION
    selectors = service_info.get('selectors')
    selectors = selectors[selectors.find("{")+1:][:selectors.rfind("}")-1]
    selector_list = selectors.split(",")
    if len(selector_list) != 1 or not selector_list[0]:
         print "Invalid state for step operation"
         sys.exit(5)
    r = SELECTOR_PARSER.parse(selector_list[0].replace("{","#").replace("}","#"))
    traffic_version = r['version']
    rule = r['rule'].split("=")
    if rule[0].strip() != "weight":
         print "Invalid state for step operation"
         sys.exit(6)
    current_weight = rule[1]
    if not args.amount:
        new_amount = int(float(current_weight) * 100) + 10
    else:
        if args.amount < 0 or args.amount > 100:
            print "--amount must be between 0 and 100"
            sys.exit(4)
        new_amount = args.amount
    if new_amount < 100:
        service_info['selectors'] = "{%s={weight=%s}}" % (traffic_version, float(new_amount)/100)
    else:
        new_amount = 100
        service_info['default'] = traffic_version
        service_info['selectors'] = None
    r = a8_put('{0}/v1/versions/{1}'.format(args.a8_controller_url, args.service),
               args.a8_controller_token,
               json.dumps(service_info),
               showcurl=args.debug)
    fail_unless(r, 200)
    if new_amount == 100:
        print 'Transfer complete for {}: sending {}% of traffic to {}'.format(args.service, new_amount, traffic_version)
    else:
        print 'Transfer step for {}: diverting {}% of traffic from {} to {}'.format(args.service, new_amount, default_version, traffic_version)

def traffic_abort(args):
    r = a8_get('{0}/v1/versions/{1}'.format(args.a8_controller_url, args.service),
               args.a8_controller_token,
               showcurl=args.debug)
    fail_unless(r, 200)
    service_info = r.json()
    if not service_info['selectors']:
        print "Invalid state for abort operation"
        sys.exit(5)
    default_version = service_info.get('default')
    if not default_version:
        default_version = NO_VERSION
    service_info['selectors'] = None
    r = a8_put('{0}/v1/versions/{1}'.format(args.a8_controller_url, args.service),
               args.a8_controller_token,
               json.dumps(service_info),
               showcurl=args.debug)
    fail_unless(r, 200)
    print 'Transfer aborted for {}: all traffic reverted to {}'.format(args.service, default_version)
