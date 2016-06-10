#!/usr/bin/python
#
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



# Amalgam8 CLI parser
import argparse
import os
import sys

import commands # implementation of cli commands

def main():
    parser = argparse.ArgumentParser('a8ctl', description="""
    Query and manipulate the Amalgam8 Microservice Fabric Controller to manage microservice routing rules or inject failures and delays.
    """,
    # a 'usage' here suppresses generated usage and subparser names
    # usage='usage'
    # an 'epilog' here appears after the optional arguments when using --help
#    epilog="epilog"
    # add_help=False suppresses the --help / -h option, but does not affect the list of subcommands
#    add_help=False
    )

    parser.add_argument('--debug',
                        help='show REST communication with Amalgam8 Controller as it is performed',
                        action='store_true',
                        default=os.getenv('A8_DEBUG')=='1'
                        )
    parser.add_argument('--a8-url',
                        help='override $A8_CONTROLLER_URL with url of Amalgam8 Controller',
                        default=os.getenv('A8_CONTROLLER_URL', 'http://192.168.33.33:31200'))
    parser.add_argument('--a8-token',
                        help='override $A8_CONTROLLER_TOKEN with token for Amalgam8 Controller',
                        default=os.getenv('A8_CONTROLLER_TOKEN', '12345'))
    parser.add_argument('--a8-tenant-id',
                        help='override $A8_CONTROLLER_TENANT_ID with tenant-id for Amalgam8 Controller',
                        default=os.getenv('A8_CONTROLLER_TENANT_ID', 'local'))
    
    subparsers = parser.add_subparsers(help='', # 2nd column heading over subcommand name
                                       dest='subparser_name',
                                       # Adding 'description' seems to create a subcommands: section that includes that text
                                       # description="",
                                       # Adding title seems to replace the string 'subcommands:' with the title, if there is subcommand text
                                       title="Commands",
                                       metavar='subcommand' # 1st column heading over subcommand name, and appears in short usage msg
                                       )

    # a8ctl service-list
    parser_service_list = \
        subparsers.add_parser('service-list',
                              description="List managed microservices.",
                              help="List managed microservices."
                              )
    parser_service_list.set_defaults(func=commands.service_list)

    # a8ctl route-list
    parser_service_routing = \
        subparsers.add_parser('route-list',
                              description="List microservices version routing rules.",
                              help="List microservices version routing rules."
                              )
    parser_service_routing.set_defaults(func=commands.service_routing)

    # a8ctl route-set <service> [--default version] [--selector version(condition)]*
    parser_set_routing = \
        subparsers.add_parser('route-set',
                              description='Set version routing rules for a microservice.',
                              help='Set version routing rules for a microservice.'
                              )
    parser_set_routing.set_defaults(func=commands.set_routing)
    parser_set_routing.add_argument("service",
                                     help='The microservice name')
    parser_set_routing.add_argument("--default",
                                    help='The service version to use when no selectors apply (unversioned instances by default)')
    parser_set_routing.add_argument("--selector", action='append',
                                    help='A version(condition) selecting a service version to use when the condition applies')

    # a8ctl route-delete <service>
    parser_delete_routing = \
        subparsers.add_parser('route-delete',
                              description='Delete version routing rules for a microservice.',
                              help='Delete version routing rules for a microservice.'
                              )
    parser_delete_routing.set_defaults(func=commands.delete_routing)
    parser_delete_routing.add_argument("service",
                                       help='The microservice name')

    # a8ctl rule-list
    parser_rules_list = \
        subparsers.add_parser('rule-list',
                              description="List resiliency tesing rules.",
                              help="List resiliency tesing rules."
                              )
    parser_rules_list.set_defaults(func=commands.rules_list)

    # a8ctl gremlin rule-set ...
    parser_set_rules = \
        subparsers.add_parser('rule-set',
                              description='Set a resiliency testing rule.',
                              help='Set a resiliency testing rule.'
                              )
    parser_set_rules.set_defaults(func=commands.set_rule)
    parser_set_rules.add_argument("--source",
                                  help='The source microservice name')
    parser_set_rules.add_argument("--destination",
                                  help='The source microservice name')
    parser_set_rules.add_argument("--header",
                                  help='Filter requests containing a specific header')
    parser_set_rules.add_argument("--pattern",
                                  help='Select only requests whose header matches the pattern')
    parser_set_rules.add_argument("--delay-probability",
                                  help='Percentage of requests to delay',
                                  type=float)
    parser_set_rules.add_argument("--delay",
                                  help='Period of delay to inject in seconds',
                                  type=float)
    parser_set_rules.add_argument("--abort-probability",
                                  help='Percentage of requests to abort',
                                  type=float)
    parser_set_rules.add_argument("--abort-code",
                                  help='HTTP error code to return to caller. Specify 0 to close TCP connection',
                                  type=int)

    # a8ctl gremlin recipe-run ...
    parser_clear_rules = \
                        subparsers.add_parser('rule-clear',
                                              description='Clear all fault injection rules from the application.',
                                              help='Clear all fault injection rules from the application.'
                        )
    parser_clear_rules.set_defaults(func=commands.clear_rules)

    # a8ctl gremlin recipe-run ...
    parser_run_recipe = \
                        subparsers.add_parser('recipe-run',
                                              description='Setup a failure scenario and assertion to test against the application.',
                                              help='Setup a failure scenario and assertion to test against the application.'
                        )
    parser_run_recipe.set_defaults(func=commands.run_recipe)
    parser_run_recipe.add_argument("--topology",
                                   help='The application\'s logical topology')
    parser_run_recipe.add_argument("--scenarios",
                                   help='The failure scenarios')
    parser_run_recipe.add_argument("--checks",
                                   help='Validations on the behavior of the microservices during the failure')
    parser_run_recipe.add_argument("--header",
                                   help='Specify the request tracking header used by the application',
                                   default='X-Request-ID')
    parser_run_recipe.add_argument("--pattern",
                                   help='Select only requests whose request tracking header matches the pattern',
                                   default='*')

    # a8ctl rollout-start <service> <version> [--amount <percent>]
    parser_rollout_start = \
        subparsers.add_parser('rollout-start',
                              description='Start rolling traffic to a new version of a microservice.',
                              help='Start rolling traffic to a new version of a microservice.'
                              )
    parser_rollout_start.set_defaults(func=commands.rollout_start)
    parser_rollout_start.add_argument("service",
                                      help='The microservice name')
    parser_rollout_start.add_argument("version",
                                      help='The new version to rollout')
    parser_rollout_start.add_argument("--amount",
                                      help='A percentage of traffic 0-100 to step',
                                      type=int,
                                      default=10)

    # a8ctl rollout-step <service> [--amount <percent>]
    parser_rollout_step = \
        subparsers.add_parser('rollout-step',
                              description='Step up the amount of traffic to a new version of a microservice.',
                              help='Step up the amount of traffic to a new version of a microservice.'
                              )
    parser_rollout_step.set_defaults(func=commands.rollout_step)
    parser_rollout_step.add_argument("service",
                                     help='The microservice name')
    parser_rollout_step.add_argument("--amount",
                                     help='A percentage of traffic 0-100 to step',
                                     type=int,
                                     default=10)


    # a8ctl rollout-abort <service>
    parser_rollout_abort = \
        subparsers.add_parser('rollout-abort',
                              description='Abort rollout of new version of a microservice.',
                              help='Abort rollout of new version of a microservice.'
                              )
    parser_rollout_abort.set_defaults(func=commands.rollout_abort)
    parser_rollout_abort.add_argument("service",
                                      help='The microservice name')

    args = parser.parse_args()
    args.func(args)
    

if __name__ == '__main__':
    main()
