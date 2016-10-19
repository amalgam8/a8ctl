# coding=utf-8

import requests
import json
from collections import defaultdict
import uuid
import logging
import httplib
import re
import datetime, time
logging.basicConfig()
requests_log = logging.getLogger("requests.packages.urllib3")

def split_service(input):
    colon = input.rfind(':')
    if colon != -1:
        service = input[:colon]
        version = input[colon+1:]
    else:
        service = input
        version = None
    return service, version

def _duration_to_floatsec(s):
    r = re.compile(r"(([0-9]*(\.[0-9]*)?)(\D+))", re.UNICODE)
    start=0
    m = r.search(s, start)
    vals = defaultdict(lambda: 0)
    while m is not None:
        unit = m.group(4)
        try:
            value = float(m.group(2))
        except ValueError:
            print(s, unit, m.group(2))
            return datetime.timedelta()
        if unit == "h":
            vals["hours"] = value
        elif unit == 'm':
            vals["minutes"] = value
        elif unit == 's':
            vals["seconds"] = value
        elif unit == "ms":
            vals["milliseconds"] = value
        elif unit == "us":
            vals["microseconds"] = value
        else:
            raise("Unknown time unit")
        start = m.end(1)
        m = r.search(s, start)
    td = datetime.timedelta(**vals)
    duration_us = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6)
    return duration_us/(1.0 * 10**6)

class A8FailureGenerator(object):

    def __init__(self, app, header=None, pattern=None, a8_controller_url = None, a8_controller_token=None, debug=False):
        """
        Create a new failure generator
        @param app ApplicationGraph: instance of ApplicationGraph object
        """
        self.app = app
        self.debug = debug
        self._id = str(uuid.uuid1())
        self._queue = []
        self._rule_ids = []
        self.header = header
        self.pattern = pattern
        self.a8_controller_url = a8_controller_url
        self.a8_controller_token = a8_controller_token
        assert a8_controller_url is not None and a8_controller_token is not None
        # The failure generator SDK supports only one failure recipe at a given time. A recipe can consist of multiple tests.
        # The trackingheader and pattern fields in the recipes will be ignored. But multiple failure generators
        # can be run from different processes. So, the user has to supply the header name and pattern being used.
        assert pattern is not None and header is not None
        assert app is not None

        #some common scenarios
        self.functiondict = {
            'delay_requests' : self.delay_requests,
            'delay_responses' : self.delay_responses,
            'abort_requests' : self.abort_requests,
            'abort_responses' : self.abort_responses,
            'partition_services' : self.partition_services,
            'crash_service' : self.crash_service,
            'overload_service' : self.overload_service
        }
        if debug:
            httplib.HTTPConnection.debuglevel = 1
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
            
    def get_id(self):
        return self._id

    def add_rule(self, **args):
        """
        @param args keyword argument list, consisting of:

        source: <source service name>,
        dest: <destination service name>,
        messagetype: <request|response|publish|subscribe|stream>

        trackingheader: <inject faults only on requests that carry this header>
        headerpattern: <For requests carrying the specific header above, match the regex against the header's value>

        delayprobability: <float, 0.0 to 1.0>
        delaytime: <string> latency to inject into requests <string, e.g., "10ms", "1s", "5m", "3h", "1s500ms">
        
        abortprobability: <float, 0.0 to 1.0>
        errorcode: <Number> HTTP error code or -1 to reset TCP connection

        bodypattern: <regex to match against HTTP message body> -- unused
        delaydistribution: <uniform|exponential|normal> probability distribution function -- unused
        mangleprobability: <float, 0.0 to 1.0> -- unused
        mangledistribution: <uniform|exponential|normal> probability distribution function -- unused
        abortdistribution: <uniform|exponential|normal> probability distribution function -- unused
        searchstring: <string> string to replace when Mangle is enabled -- unused
        replacestring: <string> string to replace with for Mangle fault -- unused
        """
        rule = args.copy()
        services = self.app.get_services()

        #check defaults
        assert self.header != "" and self.pattern != ""
        assert rule["source"] != "" and rule["dest"] != ""
        assert rule["source"] in services and rule["dest"] in services
        assert "delayprobability" in rule or "abortprobability" in rule
        if "delayprobability" in rule:
            assert rule['delayprobability'] > 0.0
            assert rule.get("delaytime", "") != ""
        if "abortprobability" in rule:
            assert rule['abortprobability'] > 0.0
            assert rule.get("errorcode", 0) != 0

        graph = self.app._get_networkX()
        ##For graph edges covered by rules, color them red
        graph[rule['source']][rule['dest']]['color']='red'

        source_name, source_version = split_service(rule["source"])
        destination_name, destination_version = split_service(rule["dest"])

        a8rule = {
            "destination": destination_name,
            "tags": [ self._id ],
            "priority": 10,
            "match": {
                "source": {
                   "name": source_name
                },
                "headers": {
                    self.header: self.pattern
                }
            },
            "actions": [
                {
                    "action": "trace",
                    "log_key": "gremlin_recipe_id",
                    "log_value": self._id
                }
            ]
        }

        if source_version:
            a8rule["match"]["source"]["tags"] = source_version.split(",")
        if destination_version:
            a8rule["actions"][0]["tags"] = destination_version.split(",")

        if "delayprobability" in rule:
            action = {
                "action": "delay",
                "probability": rule["delayprobability"],
                "duration": _duration_to_floatsec(rule["delaytime"])
            }
            if destination_version:
                action["tags"] = destination_version.split(",")
            a8rule["actions"].append(action)

        if "abortprobability" in rule:
            action = {
                "action": "abort",
                "probability": rule["abortprobability"],
                "return_code": rule["errorcode"]
            }
            if destination_version:
                action["tags"] = destination_version.split(",")
            a8rule["actions"].append(action)
                   
        self._queue.append(a8rule)

    def clear_rules_from_all_proxies(self):
        """
            Clear fault injection rules from all known service proxies.
        """
        if self.debug:
            print 'Clearing rules'
        try:
            headers = {"Content-Type" : "application/json"}
            if self.a8_controller_token != "" :
                headers['Authorization'] = "Bearer " + self.a8_controller_token
            for rule_id in self._rule_ids:
                resp = requests.delete(self.a8_controller_url + "?id=" + rule_id,
                                       headers = headers)
                resp.raise_for_status()
        except requests.exceptions.ConnectionError, e:
            print "FAILURE: Could not communicate with control plane %s" % self.a8_controller_url
            print e
            sys.exit(3)

    #TODO: Create a plugin model here, to support gremlinproxy and nginx
    def push_rules(self):
        try:
            headers = {"Content-Type" : "application/json"}
            if self.a8_controller_token != "" :
                headers['Authorization'] = "Bearer " + self.a8_controller_token
            payload = {"rules": self._queue}
            #print json.dumps(payload, indent=2)
            resp = requests.post(self.a8_controller_url,
                                 headers = headers,
                                 data=json.dumps(payload))
            resp.raise_for_status()
            self._rule_ids = resp.json()["ids"]
        except requests.exceptions.ConnectionError, e:
            print "FAILURE: Could not communicate with control plane %s" % self.a8_controller_url
            print e
            sys.exit(3)

    # Generate empty rules to just log requests with Gremlin header
    def _generate_log_rules(self):
        graph = self.app._get_networkX()
        for e in graph.edges(data='color'):
            if e[2] == 'black': #uncovered edge
                source_name, source_version = split_service(e[0])
                destination_name, destination_version = split_service(e[1])
                log_rule = {
                    "destination": destination_name,
                    "tags": [ self._id ],
                    "priority": 10,
                    "match": {
                        "source": {
                            "name": source_name
                        },
                        "headers": {
                            self.header: self.pattern
                        }
                    },
                    "actions": [
                        {
                            "action": "trace",
                            "log_key": "gremlin_recipe_id",
                            "log_value": self._id
                        }
                    ]
                }
                if source_version:
                    log_rule["match"]["source"]["tags"] = source_version.split(",")
                if destination_version:
                    log_rule["actions"][0]["tags"] = destination_version.split(",")
                self._queue.append(log_rule)                
                if self.debug:
                    print '%s - %s' % ('log_rule', str(log_rule))


    def _generate_rules(self, rtype, **args):
        rule = args.copy()
        assert rtype is not None and rtype != "" and (rtype is "delay" or rtype is "abort")

        if rtype is "abort":
            rule['abortprobability']=rule.pop('abortprobability',1) or 1
            rule['errorcode']=rule.pop('errorcode',-1) or -1
        else:
            rule['delayprobability']=rule.pop('delayprobability',1) or 1
            rule['delaytime']=rule.pop('delaytime',"1s") or "1s"
            
        assert 'source' in rule or 'dest' in rule
        if 'source' in rule:
            assert rule['source'] != ""
        if 'dest' in rule:
            assert rule['dest'] != ""

        #rule['headerpattern'] = rule.pop('headerpattern', '.*') or '.*'
        rule['bodypattern'] = rule.pop('bodypattern', '*') or '*'
        sources = []
        destinations = []
        if 'source' not in rule:
            sources = self.app.get_dependents(rule['dest'])
        else:
            sources.append(rule['source'])

        if 'dest' not in rule:
            destinations = self.app.get_dependencies(rule['source'])
        else:
            destinations.append(rule['dest'])

        for s in sources:
            for d in destinations:
                rule["source"] = s
                rule["dest"] = d
                self.add_rule(**rule)
                if self.debug:
                    print '%s - %s' % (rtype, str(rule))

    def abort_requests(self, **args):
        args['messagetype']='request'
        self._generate_rules('abort', **args)

    def abort_responses(self, **args):
        args['messagetype']='response'
        self._generate_rules('abort', **args)

    def delay_requests(self, **args):
        args['messagetype']='request'
        self._generate_rules('delay', **args)

    def delay_responses(self, **args):
        args['messagetype']='response'
        self._generate_rules('delay', **args)

    """
    Gives the impression of an overloaded service. If no probability is given
    50% of requests will be delayed by 10s (default) and rest 50% will get HTTP 503.
    """
    def overload_service(self, **args):
        rule = args.copy()
        assert 'dest' in rule

        rule['delayprobability'] = rule.pop('delayprobability', 0.5) or 0.5
        rule['abortprobability'] = rule.pop('abortprobability', 0.5) or 0.5
        rule['delaytime'] = rule.pop('delaytime', "10s") or "10s"
        rule['errorcode'] = rule.pop("errorcode", 503) or 503
        rule['messagetype'] = rule.pop('messagetype', 'request') or 'request'
        #rule['headerpattern'] = rule.pop('headerpattern', '*') or '*'
        rule['bodypattern'] = rule.pop('bodypattern','*') or '*'

        sources = []
        if 'source' not in rule or rule['source'] == "":
            sources = self.app.get_dependents(rule['dest'])
        else:
            sources.append(rule['source'])

        for s in sources:
            rule["source"] = s
            self.add_rule(**rule)
            if self.debug:
                print 'Overload %s ' % str(rule)

    def partition_services(self, **args):
        """Partitions two connected services. Not two sets of services (TODO)
        Expects usual arguments and srcprobability and dstprobability, that indicates probability of 
        terminating connections from source to dest and vice versa
        """
        rule = args.copy()
        assert 'source' in rule and 'dest' in rule
        #assert 'srcprobability' in rule and 'dstprobability' in rule
        assert rule['source'] != "" and rule['dest'] != ""
        #check if the two services are connected
        assert rule['dest'] in self.app.get_dependencies(rule['source'])

        rule['errorcode'] = rule.pop('errorcode', 0) or 0
        rule['abortprobability'] = rule.pop('srcprobability', 1) or 1
        self.abort_requests(**rule)

        rule['abortprobability'] = rule.pop('dstprobability', 1) or 1
        temp = rule['source']
        rule['source'] = rule['dest']
        rule['dest'] = temp
        self.abort_requests(**rule)

    """
    Causes the dest service to become unavailable to all callers
    """
    def crash_service(self, **args):
        rule = args.copy()
        rule['source']=''
        rule['errorcode']=rule.pop('errorcode', 0) or 0
        self.abort_requests(**rule)

    def setup_failure(self, scenario=None, **args):
        """Add a given failure scenario
        @param scenario: string 'delayrequests' or 'crash'
        """
        assert scenario is not None and scenario in self.functiondict
        self.functiondict[scenario](**args)

    def setup_failures(self, gremlins):
        """Add gremlins to environment"""

        assert isinstance(gremlins, dict) and 'gremlins' in gremlins
        graph = self.app._get_networkX()
        ##color edges initially
        for e in graph.edges():
            graph[e[0]][e[1]]['color'] = 'black'

        for gremlin in gremlins['gremlins']:
            self.setup_failure(**gremlin)
        self._generate_log_rules()
        self.push_rules()
