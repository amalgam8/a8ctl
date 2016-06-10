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
import yaml
import os
import urllib
import datetime, time
import pprint
from parse import compile
from pygremlin import ApplicationGraph, A8FailureGenerator, A8AssertionChecker


def passOrfail(result):
    if result:
        return "PASS"
    else:
        return "FAIL"

def a8_get(url, token, headers={'Accept': 'application/json'}, showcurl=False, extra_headers={}):
    headers['Authorization'] = token
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
    headers['Authorization'] = token
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

    headers['Authorization'] = token
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
    headers['Authorization'] = token

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

def get_registry_credentials(tenant_info):
    registry = tenant_info["credentials"]["registry"]
    return registry["url"], "Bearer " + registry["token"]
    
NO_VERSION = "UNVERSIONED"
SELECTOR_PARSER = compile("{version}=#{rule}#") # TODO: tolerate white-space in format

############################################
# CLI Commands
############################################

def service_list(args):
    r = a8_get('{0}/v1/tenants/{1}'.format(args.a8_url, args.a8_tenant_id), args.a8_token, showcurl=args.debug)
    fail_unless(r, 200)
    tenant_info = r.json()
    registry_url, registry_token = get_registry_credentials(tenant_info)
    r = a8_get('{0}/api/v1/services'.format(registry_url), registry_token, showcurl=args.debug)
    fail_unless(r, 200)
    service_list = r.json()["services"]
    x = PrettyTable(["Service", "Instances"])
    x.align = "l"
    for service in service_list:
        r = a8_get('{0}/api/v1/services/{1}'.format(registry_url, service), registry_token, showcurl=args.debug)
        fail_unless(r, 200)
        instance_list = r.json()["instances"]
        version_counts = {}
        for instance in instance_list:
            version = instance["metadata"]["version"] if "metadata" in instance and "version" in instance["metadata"] else NO_VERSION
            version_counts[version] = version_counts.get(version, 0) + 1
        formatted_versions = ""
        for version, count in version_counts.iteritems():
            formatted_versions += ", %s(%s)" % (version, count)
        x.add_row([service, formatted_versions[2:]])
    print x

def service_routing(args):
    r = a8_get('{0}/v1/tenants/{1}'.format(args.a8_url, args.a8_tenant_id), args.a8_token, showcurl=args.debug)
    fail_unless(r, 200)
    tenant_info = r.json()
    registry_url, registry_token = get_registry_credentials(tenant_info)
    r = a8_get('{0}/api/v1/services'.format(registry_url), registry_token, showcurl=args.debug)
    fail_unless(r, 200)
    service_list = r.json()["services"]
    x = PrettyTable(["Service", "Default Version", "Version Selectors"])
    x.align = "l"
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
        x.add_row([service,
                   default,
                   ", ".join(versions)
                   ])
    for service in service_list:
        x.add_row([service,
                   NO_VERSION,
                   ""
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

    r = a8_put('{0}/v1/tenants/{1}/versions/{2}'.format(args.a8_url, args.a8_tenant_id, args.service),
               args.a8_token, 
               json.dumps(routing_request),
               showcurl=args.debug)
    fail_unless(r, 200)
    print 'Set routing rules for microservice', args.service

def delete_routing(args):
    r = a8_delete('{0}/v1/tenants/{1}/versions/{2}'.format(args.a8_url, args.a8_tenant_id, args.service),
               args.a8_token, 
               showcurl=args.debug)
    fail_unless(r, 200)
    print 'Deleted routing rules for microservice', args.service

def rules_list(args):
    r = a8_get('{0}/v1/tenants/{1}'.format(args.a8_url, args.a8_tenant_id), args.a8_token, showcurl=args.debug)
    fail_unless(r, 200)
    tenant_info = r.json()
    x = PrettyTable(["Source", "Destination", "Header", "Header Pattern", "Delay Probability", "Delay", "Abort Probability", "Abort Code"])
    x.align = "l"
    for value in tenant_info['filters']['rules']:
        x.add_row([get_field(value, 'source'),
                   get_field(value, 'destination'),
                   get_field(tenant_info, 'req_tracking_header'),
                   get_field(value, 'pattern'),
                   get_field(value, 'delay_probability'),
                   get_field(value, 'delay'),
                   get_field(value, 'abort_probability'),
                   get_field(value, 'return_code')
                   ])
    print x

def set_rule(args):
    if not args.source and not args.destination:
         print "You must specify --source and --destination"
         sys.exit(4)

    rule_request = {
        "source": args.source,
        "destination": args.destination
    }

    if args.pattern:
        rule_request['pattern'] = '.*?'+args.pattern
    if args.delay:
        rule_request['delay'] = args.delay
    if args.delay_probability:
        rule_request['delay_probability'] = args.delay_probability
    if args.abort_probability:
        rule_request['abort_probability'] = args.abort_probability
    if args.abort_code:
        rule_request['return_code'] = args.abort_code

    payload = {"filters":{"rules":[rule_request]}}
    if args.header:
        payload['req_tracking_header'] = args.header

    r = a8_put('{0}/v1/tenants/{1}'.format(args.a8_url, args.a8_tenant_id), # TODO: use an API that won't wipe out other rules
               args.a8_token, 
               json.dumps(payload),
               showcurl=args.debug)
    fail_unless(r, 200)
    print 'Set resiliency test rule between %s and %s' % (args.source, args.destination)

def clear_rules(args):

    r = a8_put('{0}/v1/tenants/{1}'.format(args.a8_url, args.a8_tenant_id), # TODO: use an API that won't wipe out other rules
               args.a8_token, 
               json.dumps({"filters":{"rules":[]}}),
               showcurl=args.debug)
    fail_unless(r, 200)
    print 'Cleared fault injection rules from all microservices'

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

    fg = A8FailureGenerator(topology, a8_url=args.a8_url, a8_token=args.a8_token, a8_tenant_id=args.a8_tenant_id,
                            header=header, pattern='.*?'+pattern, debug=args.debug)
    fg.setup_failures(scenarios)
    start_time = datetime.datetime.utcnow().isoformat()
    print start_time
    print 'Inject test requests with HTTP header %s matching the pattern %s' % (header, pattern)
    if args.checks:
        print ('When done, press Enter key to continue to validation phase')
        a = sys.stdin.read(1)
        #sleep for 3sec to make sure all logs reach elasticsearch
        time.sleep(3)
        end_time=datetime.datetime.utcnow().isoformat()
        print end_time
        #sleep for some more time to make sure all logs have been flushed
        time.sleep(5)
        ac = A8AssertionChecker(checklist['log_server'], None, header=header, pattern=pattern, start_time=start_time, end_time=end_time, debug=args.debug)
        results = ac.check_assertions(checklist, continue_on_error=True)
        _print_assertion_results(results)
        clear_rules(args)
        # for check in results:
        #     print 'Check %s %s %s' % (check.name, check.info, passOrfail(check.success))
        # if not check.success:
        #     exit_status = 1
        # sys.exit(exit_status)

def rollout_start(args):
    if args.amount < 0 or args.amount > 100:
         print "--amount must be between 0 and 100"
         sys.exit(4)
    r = a8_get('{0}/v1/tenants/{1}/versions/{2}'.format(args.a8_url, args.a8_tenant_id, args.service), args.a8_token, showcurl=args.debug)
    fail_unless(r, [200, 404])
    if r.status_code == 200:
        service_info = r.json()
        if service_info['selectors']:
            print "Invalid state for start operation"
            sys.exit(5)
    else:
        service_info = {}
    default_version = service_info.get('default')
    if not default_version:
        default_version = NO_VERSION
    if args.amount == 100:
        service_info['default'] = args.version
    else:
        service_info['selectors'] = "{%s={weight=%s}}" % (args.version, float(args.amount)/100)
    r = a8_put('{0}/v1/tenants/{1}/versions/{2}'.format(args.a8_url, args.a8_tenant_id, args.service),
               args.a8_token, 
               json.dumps(service_info),
               showcurl=args.debug)
    fail_unless(r, 200)
    if args.amount == 100:
        print 'Rollout complete for {}: sending {}% of traffic to {}'.format(args.service, args.amount, args.version)
    else:
        print 'Rollout starting for {}: diverting {}% of traffic from {} to {}'.format(args.service, args.amount, default_version, args.version)

def rollout_step(args):
    if args.amount < 0 or args.amount > 100:
         print "--amount must be between 0 and 100"
         sys.exit(4)
    r = a8_get('{0}/v1/tenants/{1}/versions/{2}'.format(args.a8_url, args.a8_tenant_id, args.service), args.a8_token, showcurl=args.debug)
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
    rollout_version = r['version']
    rule = r['rule'].split("=")
    if rule[0].strip() != "weight":
         print "Invalid state for step operation"
         sys.exit(6)       
    current_weight = rule[1]
    new_amount = float(current_weight) * 100 + args.amount
    if new_amount < 100:
        service_info['selectors'] = "{%s={weight=%s}}" % (rollout_version, new_amount/100)
    else:
        new_amount = 100
        service_info['default'] = rollout_version
        service_info['selectors'] = None
    r = a8_put('{0}/v1/tenants/{1}/versions/{2}'.format(args.a8_url, args.a8_tenant_id, args.service),
               args.a8_token, 
               json.dumps(service_info),
               showcurl=args.debug)
    fail_unless(r, 200)
    if new_amount == 100:
        print 'Rollout complete for {}: sending {}% of traffic to {}'.format(args.service, new_amount, rollout_version)
    else:
        print 'Rollout step for {}: diverting {}% of traffic from {} to {}'.format(args.service, new_amount, default_version, rollout_version)

def rollout_abort(args):
    r = a8_get('{0}/v1/tenants/{1}/versions/{2}'.format(args.a8_url, args.a8_tenant_id, args.service), args.a8_token, showcurl=args.debug)
    fail_unless(r, 200)
    service_info = r.json()
    if not service_info['selectors']:
        print "Invalid state for abort operation"
        sys.exit(5)
    default_version = service_info.get('default')
    if not default_version:
        default_version = NO_VERSION
    service_info['selectors'] = None
    r = a8_put('{0}/v1/tenants/{1}/versions/{2}'.format(args.a8_url, args.a8_tenant_id, args.service),
               args.a8_token, 
               json.dumps(service_info),
               showcurl=args.debug)
    fail_unless(r, 200)
    print 'Rollout aborted for {}: all traffic reverted to {}'.format(args.service, default_version)
