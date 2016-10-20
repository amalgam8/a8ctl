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

from flask import Flask, json, jsonify, make_response, request, url_for, abort
from applicationgraph import ApplicationGraph
from failuregenerator_a8 import A8FailureGenerator
from assertionchecker_a8 import A8AssertionChecker
import os, sys, requests

debug = os.getenv('A8_DEBUG')=='1'
a8_controller_url = os.getenv('A8_CONTROLLER_URL', 'http://localhost:31200')
a8_controller_token = os.getenv('A8_CONTROLLER_TOKEN', '')
a8_log_server = os.getenv('A8_LOG_SERVER', 'localhost:30200')

app = Flask(__name__, static_url_path='')
app.debug = True

@app.route('/api/v1/recipes', methods=["POST"])
def post_recipe():
    payload = request.get_json()

    topology = payload.get("topology")
    scenarios = payload.get("scenarios")
    header = payload.get("header")
    pattern = payload.get("header_pattern")
    
    if not topology:
        abort(400, "Topology required")

    if not scenarios:
        abort(400, "Failure scenarios required")

    if not header:
        abort(400, "Header required")

    if not pattern:
        abort(400, "Header_pattern required")

    appgraph = ApplicationGraph(topology)
    fg = A8FailureGenerator(appgraph, a8_controller_url='{0}/v1/rules'.format(a8_controller_url), a8_controller_token=a8_controller_token,
                            header=header, pattern=pattern, debug=debug)
    fg.setup_failures(scenarios)
    return make_response(jsonify(recipe_id=fg.get_id()), 201, {'location': url_for('get_recipe_results', recipe_id=fg.get_id())})

@app.route('/api/v1/recipes/<recipe_id>', methods=["POST"])
def get_recipe_results(recipe_id):
    payload = request.get_json()
    #print json.dumps(payload, indent=2)

    checklist = payload.get("checklist")

    if not checklist:
        abort(400, "Checklist required")
    
    log_server = checklist.get('log_server', a8_log_server)
    
    ac = A8AssertionChecker(es_host=log_server, trace_log_value=recipe_id, index=["_all"])      
    results = ac.check_assertions(checklist, continue_on_error=True)

    #print json.dumps(results, indent=2)
    return make_response(jsonify(results=results), 200)

@app.route('/api/v1/recipes/<recipe_id>', methods=["DELETE"])
def delete_recipe(recipe_id):
    # clear fault injection rules
    url = '{0}/v1/rules?tag={1}'.format(a8_controller_url, recipe_id)
    headers = {}
    if a8_controller_token != "" :
        headers['Authorization'] = "Bearer " + token

    try:
        r = requests.delete(url, headers=headers)
    except Exception, e:
        sys.stderr.write("Could not DELETE {0}".format(url))
        sys.stderr.write("\n")
        sys.stderr.write(str(e))
        sys.stderr.write("\n")
        abort(500, "Could not DELETE {0}".format(url))
        
    if r.status_code != 200 and r.status_code != 204:
        abort(r.status_code)

    return ""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
