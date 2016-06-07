Amalgam8 Command Line Interface (CLI)
=====================================

Command-line tool for Amalgam8 Microservices Fabric (http://www.amalgam8.io/).

Installation
------------

To install the Amalgam8 CLI:

.. code:: bash

    pip install a8ctl

For usage information, execute the following command:

.. code:: bash

    a8ctl -h

Commands
--------

.. code:: bash

    a8ctl service-list

    a8ctl route-list
    a8ctl route-set <service> [--default <version>] [--selector <version> "(" <condition> ")"]*
    a8ctl route-delete <service>

    a8ctl rule-list
    a8ctl rule-set --source <service> --destination <service> [--header <string>] [--patern <regexp>] [--delay-percent <float>] [--delay <float>] [--abort-percent <float>] [--abort-code <code>]

    a8ctl rollout-start <service> <version> [--amount <percent>]
    a8ctl rollout-step <service> [--amount <percent>]
    a8ctl rollout-abort <service>

Examples
--------

.. code::

    $ a8ctl service-list
    +-------------+---------------------+
    | Service     | Instances           |
    +-------------+---------------------+
    | reviews     | v1(1), v2(1), v3(1) |
    | productpage | v1(1)               |
    | ratings     | v1(1)               |
    | helloworld  | v1(2), v2(2)        |
    | details     | v1(1)               |
    | serviceA    | UNVERSIONED(1)      |
    +-------------+---------------------+
    
    $ a8ctl route-list
    +-------------+-----------------+---------------------------------------+
    | Service     | Default Version | Version Selectors                     |
    +-------------+-----------------+---------------------------------------+
    | productpage | v1              |                                       |
    | reviews     | v1              | v2(user="frankb"), v3(user="shriram") |
    | ratings     | v1              |                                       |
    | details     | v1              |                                       |
    | helloworld  | v1              | v2(weight=0.25)                       |
    | serviceA    | UNVERSIONED     |                                       |
    +-------------+-----------------+---------------------------------------+
    
    $ a8ctl route-set reviews --default v1 --selector 'v2(user="frankb")' --selector 'v3(user="shriram")'
    Set routing rules for microservice reviews
    
    $ a8ctl rule-list
    +---------+-------------+----------------+---------+---------------+-------+---------------+------------+
    | Source  | Destination | Header         | Pattern | Delay Percent | Delay | Abort Percent | Abort Code |
    +---------+-------------+----------------+---------+---------------+-------+---------------+------------+
    | reviews | ratings     | X-Gremlin-Test | *       | 0.5           | 7     | 0             | 0          |
    +---------+-------------+----------------+---------+---------------+-------+---------------+------------+
    
    $ a8ctl rule-set --source reviews --destination ratings --header X-Gremlin-Test --pattern=\* --delay-percent 0.5 --delay 7
    Set resiliency test rule between reviews and ratings
    
    $ a8ctl rollout-start reviews v2
    Rollout starting for reviews: diverting 10% of traffic from v1 to v2 
    $ a8ctl rollout-step reviews
    Rollout step for reviews: diverting 20% of traffic from v1 to v2 
    $ a8ctl rollout-step reviews --amount 20
    Rollout step for reviews: diverting 40% of traffic from v1 to v2 
    ...
    $ a8ctl rollout-step reviews
    Rollout step for reviews: diverting 90% of traffic from v1 to v2 
    $ a8ctl rollout-step reviews
    Rollout complete for reviews: sending 100% of traffic to v2
    
    $ a8ctl rollout-start reviews v2
    Rollout starting for reviews: diverting 10% of traffic from v1 to v2 
    $ a8ctl rollout-abort reviews
    Rollout aborted for reviews: all traffic reverted to v1

Documentation
-------------

Documentation is available at http://amalgam8.io/.
