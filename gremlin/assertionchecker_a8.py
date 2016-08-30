#!/usr/bin/python

import json

from elasticsearch import Elasticsearch
import datetime
import pprint
import warnings
import isodate
import sys

import re
from collections import defaultdict, namedtuple
import datetime
import time
import copy
from __builtin__ import dict
import logging
import logging.handlers

#es_logger = logging.getLogger('elasticsearch')
#es_logger.setLevel(logging.DEBUG)
#es_logger.addHandler(logging.StreamHandler())

# es_tracer = logging.getLogger('elasticsearch.trace')
# es_tracer.setLevel(logging.DEBUG)
# es_tracer.addHandler(logging.StreamHandler())

GremlinTestResult = namedtuple('GremlinTestResult', ['success','errormsg'])
AssertionResult = namedtuple('AssertionResult', ['name','info','success','errormsg'])

max_query_results = 500

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

# def _since(timestamp):
#     return time.time()-timestamp

def _check_value_recursively(key, val, haystack):
    """
    Check **resursively** if there is a given key with a given value in the
    given dictionary.

    ..warning:
        This is geared at JSON dictionaries, so some corner cases are ignored,
        we assume all iterables are either arrays or dicts

    :param key: the key to look for
    :param val: value to look for
    :param haystack: the dictionary

    """
    if isinstance(haystack, list):
        return any([_check_value_recursively(key, val, l) for l in haystack])
    elif isinstance(haystack, dict):
        if not key in haystack:
            return any([_check_value_recursively(key, val, d) for k, d in haystack.items()
                        if isinstance(d, list) or isinstance(d, dict)])
        else:
            return haystack[key] == val
    else:
        return False


def _get_by(key, val, l):
    """
    Out of list *l* return all elements that have *key=val*
    This comes in handy when you are working with aggregated/bucketed queries
    """
    return [x for x in l if _check_value_recursively(key, val, x)]


class A8AssertionChecker(object):

    """
    The asssertion checker
    """

    def __init__(self, es_host=None, header=None, pattern=None, test_id=None,
                 start_time=None, end_time=None,
                 header_field_name='gremlin_header_name',
                 pattern_field_name='gremlin_header_val', index="", debug=False):
        """
        param host: the elasticsearch host
        header: the gremlin header used while injecting faults
        pattern: the regex pattern that was used to pick requests
        """
        assert es_host is not None and header is not None and pattern is not None
        self._es = Elasticsearch(hosts=[es_host])
        self.debug=debug
        self.header = header
        self.pattern = pattern
        self.test_id = test_id
        self.start_time=start_time
        self.end_time=end_time
        self.header_field_name = header_field_name
        self.pattern_field_name = pattern_field_name
        if self.start_time or self.end_time:
            self.time_range={"@timestamp":{}}
            if self.start_time:
                self.time_range["@timestamp"]["gte"]=self.start_time
            if self.end_time:
                self.time_range["@timestamp"]["lte"]=self.end_time
        else:
            self.time_range = None

        if index is None or index == "":
            self.index = [ "_all" ]
        elif type(index) == str:
            self.index = [ index ]
        else:
            self.index = index
        assert(type(self.index) == list)

        self.functiondict = {
            'bounded_response_time' : self.check_bounded_response_time,
            'http_success_status' : self.check_http_success_status,
            'http_status' : self.check_http_status,
            'bounded_retries' : self.check_bounded_retries,
            'at_most_requests': self.check_at_most_requests
        }

    def _check_non_zero_results(self, data):
        """
        Checks wheter the output we got from elasticsearch is empty or not
        """
        return data["hits"]["total"] != 0 and len(data["hits"]["hits"]) != 0

    def _get_query_object(self, src=None, dst=None):
        body={
            "size": max_query_results,
            "query": {
                "bool": {
                    "must": [
                        {"match": {self.header_field_name: self.header}},
                        {"match": {self.pattern_field_name: self.pattern}}
                    ]
                }
            }
        }
        if self.time_range:
            body["filter"] = {"range" : self.time_range}
        if src:
            body["query"]["bool"]["must"].append({"prefix": {"src": src}})
        if dst:
            body["query"]["bool"]["must"].append({"prefix": {"dst": dst}})
        return body

    def check_bounded_response_time(self, **kwargs):
        assert 'source' in kwargs and 'dest' in kwargs and 'max_latency' in kwargs
        dest = kwargs['dest']
        source = kwargs['source']
        max_latency = _duration_to_floatsec(kwargs['max_latency'])
        query_body = self._get_query_object(source, dest)
        data = self._es.search(index=self.index, body=query_body)
        if self.debug:
            pprint.pprint(data)

        result = True
        errormsg = ""
        if not self._check_non_zero_results(data):
            result = False
            errormsg = "No log entries found"
            return GremlinTestResult(result, errormsg)

        for message in data["hits"]["hits"]:
            if float(message['_source']["upstream_response_time"]) > max_latency:
                result = False
                errormsg = "{} did not reply in time for request from {}: found one instance where resp time was {}s - max {}s".format(
                    dest, source, message['_source']["upstream_response_time"], max_latency)
                if self.debug:
                    print errormsg
        return GremlinTestResult(result, errormsg)

    #This isn't working with elasticsearch 2.0+. Neither does regexp
    def check_http_success_status(self, **kwargs):
        data = self._es.search(index=self.index, body={
            "size": max_query_results,
            "query": {
                "filtered": {
                    "query": {
                        "match_all": {}
                    },
                    "filter": {
                        "and" : [
                            {"exists": {"field": "status"}},
                            { "prefix": {self.header_field_name: self.header}},
                            { "prefix": {self.pattern_field_name: self.pattern}}
                        ]
                    }
                }
            }})
        result = True
        errormsg = ""
        if not self._check_non_zero_results(data):
            result = False
            errormsg = "No log entries found"
            return GremlinTestResult(result, errormsg)

        for message in data["hits"]["hits"]:
            if int(message['_source']["status"]) != 200:
                errormsg = "{} -> {} - expected HTTP 200 but found found HTTP {}".format(
                    message["_source"]["src"], message["_source"]["dst"], message["_source"]["status"])
                result = False
        return GremlinTestResult(result, errormsg)

    ##check if the interaction between a given pair of services resulted in the required response status
    def check_http_status(self, **kwargs):
        assert 'source' in kwargs and 'dest' in kwargs and 'status' in kwargs
        source = kwargs['source']
        dest = kwargs['dest']
        status = kwargs['status']
        if isinstance(status, int):
            status = [status]
        query_body = self._get_query_object(source, dest)
        data = self._es.search(index=self.index, body=query_body)
        result = True
        errormsg = ""
        if not self._check_non_zero_results(data):
            result = False
            errormsg = "No log entries found"
            return GremlinTestResult(result, errormsg)

        for message in data["hits"]["hits"]:
            hstatus = int(message['_source']['status'])
            if hstatus not in status:
                if hstatus == 499: #nginx 499 indicates unexpected timeout
                    errormsg = "unexpected connection termination"
                else:
                    errormsg = "unexpected status {}".format(message["_source"]["status"])
                if self.debug:
                    print(errormsg)
                result = False
        return GremlinTestResult(result, errormsg)

    def check_at_most_requests(self, source, dest, num_requests, **kwargs):
        """
        Check that source service sent at most num_request to the dest service
        :param source the source service name
        :param dest the destination service name
        :param num_requests the maximum number of requests that we expect
        :return:
        """
        # TODO: Does the proxy support logging of instances so that grouping by instance is possible?

        # Fetch requests for src->dst
        data = self._es.search(index=self.index, body={
            "size": max_query_results,
            "query": {
                "filtered": {
                    "query": {
                        "match_all": {}
                    },
                    "filter": {
                        "bool": {
                            "must": [
                                {"term": {"src": source}},
                                {"prefix": {"dst": dest}},
                                { "prefix": {self.header_field_name: self.header}},
                                { "prefix": {self.pattern_field_name: self.pattern}}
                            ]
                        }
                    }
                }
            },
            "aggs": {
                # Need size, otherwise only top buckets are returned
                "size": max_query_results,
                "byid": {
                    "terms": {
                        "field": self.header_field_name,
                    }
                }
            }
        })

        if self.debug:
            pprint.pprint(data)

        result = True
        errormsg = ""
        if not self._check_non_zero_results(data):
            result = False
            errormsg = "No log entries found"
            return GremlinTestResult(result, errormsg)

        # Check number of requests in each bucket
        for bucket in data["aggregations"]["byid"]["buckets"]:
            if bucket["doc_count"] > (num_requests + 1):
                errormsg = "{} -> {} - expected {} requests, but found {} "\
                         "requests for id {}".format(
                            source, dest, num_requests, bucket['doc_count'] - 1,
                            bucket['key'])
                result = False
                if self.debug:
                    print errormsg
                return GremlinTestResult(result, errormsg)
        return GremlinTestResult(result, errormsg)

    def check_bounded_retries(self, **kwargs):
        assert 'source' in kwargs and 'dest' in kwargs and 'retries' in kwargs
        source = kwargs['source']
        dest = kwargs['dest']
        retries = kwargs['retries']
        wait_time = kwargs.pop('wait_time', None)
        errdelta = kwargs.pop('errdelta', 0.0) #datetime.timedelta(milliseconds=10))
        by_uri = kwargs.pop('by_uri', False)

        if self.debug:
            print 'in bounded retries (%s, %s, %s)' % (source, dest, retries)

        data = self._es.search(index=self.index, body={
            "size": max_query_results,
            "query": {
                "filtered": {
                    "query": {
                        "match_all": {}
                    },
                    "filter": {
                        "bool": {
                            "must": [
                                {"term": {"src": source}},
                                {"prefix": {"dst": dest}},
                                {"prefix": {self.header_field_name: self.header}},
                                {"prefix": {self.pattern_field_name: self.pattern}}
                            ]
                        }
                    }
                }
            },
            "aggs": {
                "byid": {
                    "terms": {
                        "field": self.header_field_name if not by_uri else "uri",
                    }
                }
            }
        })

        if self.debug:
            pprint.pprint(data)

        result = True
        errormsg = ""
        if not self._check_non_zero_results(data):
            result = False
            errormsg = "No log entries found"
            return GremlinTestResult(result, errormsg)

        # Check number of req first
        for bucket in data["aggregations"]["byid"]["buckets"]:
            if bucket["doc_count"] > (num + 1):
                errormsg = "{} -> {} - expected {} retries, but found {} retries for request {}".format(
                    source, dest, retries, bucket['doc_count']-1, bucket['key'])
                result = False
                if self.debug:
                    print errormsg
                return GremlinTestResult(result, errormsg)
        if wait_time is None:
            return GremlinTestResult(result, errormsg)

        wait_time = _duration_to_floatsec(wait_time)
        # Now we have to check the timestamps
        for bucket in data["aggregations"]["byid"]["buckets"]:
            req_id = bucket["key"]
            req_seq = _get_by(self.header_field_name, req_id, data["hits"]["hits"])
            req_seq.sort(key=lambda x: int(x['_source']["timestamp_in_ms"]))
            for i in range(len(req_seq) - 1):
                observed = (req_seq[i + 1]['_source']["timestamp_in_ms"] - req_seq[i]['_source']["timestamp_in_ms"])/1000.0
                if not (((wait_time - errdelta) <= observed) or (observed <= (wait_time + errdelta))):
                    errormsg = "{} -> {} - expected {}+/-{}s spacing for retry attempt {}, but request {} had a spacing of {}s".format(
                        source, dest, wait_time, errdelta, i+1, req_id, observed)
                    result = False
                    if self.debug:
                        print errormsg
                    break
        return GremlinTestResult(result, errormsg)

    def check_assertion(self, name=None, **kwargs):
        # assertion is something like {"name": "bounded_response_time",
        #                              "service": "productpage",
        #                              "max_latency": "100ms"}

        assert name is not None and name in self.functiondict
        gremlin_test_result = self.functiondict[name](**kwargs)
        if self.debug and not gremlin_test_result.success:
            print gremlin_test_result.errormsg

        return AssertionResult(name, str(kwargs), gremlin_test_result.success, gremlin_test_result.errormsg)

    def check_assertions(self, checklist, continue_on_error=False):
        """Check a set of assertions
        @param all boolean if False, stop at first failure
        @return: False if any assertion fails.
        """

        assert isinstance(checklist, dict) and 'checks' in checklist

        retval = None
        retlist = []
        for assertion in checklist['checks']:
            retval = self.check_assertion(**assertion)
            check = copy.deepcopy(assertion)
            check['result']=retval.success
            check['errormsg']=retval.errormsg
            retlist.append(check)
            if not retval.success and not continue_on_error:
                return retlist

        return retlist
