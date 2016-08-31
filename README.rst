Amalgam8 Command Line Interface (CLI)
=====================================

Command-line tool for Amalgam8 (http://www.amalgam8.io/).

Installation
------------

To install the Amalgam8 CLI:

.. code:: bash

    sudo pip install git+https://github.com/amalgam8/a8ctl #install from github repo. Preferred.

or

.. code:: bash

    sudo pip install a8ctl # from pypi
    sudo pip install a8ctl==<version> # for specific version, e.g., pip install a8ctl==0.1.8

For usage information, run the following command:

.. code:: bash

    a8ctl -h

Commands
--------

.. code:: bash

    a8ctl service-list

    a8ctl route-list
    a8ctl route-set <service> [--default <tags>] [--selector <tags> "(" (weight "=" <weight> | user "=" <name> | header "=" <name> ":" <pattern>) ")"]*
    a8ctl route-delete <service>

    a8ctl action-list
    a8ctl action-add [--source <service>[":" <tags>]] [--destination <service>] [--header <name> ":" <pattern>]* [--cookie <key> "=" <value>]* [--action <tags> "(" <probability> "->" (delay "=" <seconds> | abort "=" <return_code>) ")"]* [--priority <number>]
    a8ctl rule-delete <rule-id>

    a8ctl traffic-start <service> <tags> [--amount <percent>]
    a8ctl traffic-step <service> [--amount <percent>]
    a8ctl traffic-abort <service>

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
    +-------------+---------------------+

    $ a8ctl route-set productpage --default v1
    Set routing rules for productpage productpage

    $ a8ctl route-set helloworld --default v1 --selector 'v2(weight=0.25)'
    Set routing rules for microservice helloworld
    
    $ a8ctl route-set reviews --default v1 --selector 'v2(user="frankb")' --selector 'v3(user="shriram")'
    Set routing rules for microservice reviews
    
    $ a8ctl route-list
    +-------------+-----------------+---------------------------------------+
    | Service     | Default Version | Version Selectors                     |
    +-------------+-----------------+---------------------------------------+
    | productpage | v1              |                                       |
    | reviews     | v1              | v2(user="frankb"), v3(user="shriram") |
    | ratings     |                 |                                       |
    | details     |                 |                                       |
    | helloworld  | v1              | v2(weight=0.25)                       |
    +-------------+-----------------+---------------------------------------+
    
    $ a8ctl action-add --source reviews:v2 --destination ratings --cookie user=jason --action 'v1(1->delay=7)'
    Set action rule for destination ratings
    
    $ a8ctl action-add --source productpage:v1 --destination reviews --cookie user=jason --header Foo:bar --action 'v2(0.5->delay=5)' --action 'v2(1->abort=400)' --priority 15
    Set action rule for destination reviews

    $ a8ctl action-list
    +-------------+----------------+-------------------------------+----------+----------------------------------------+--------------------------------------+
    | Destination | Source         | Headers                       | Priority | Actions                                | Rule Id                              |
    +-------------+----------------+-------------------------------+----------+----------------------------------------+--------------------------------------+
    | reviews     | productpage:v1 | Foo:bar, Cookie:.*?user=jason | 15       | v2(0.5->delay=5.0), v2(1.0->abort=400) | 4ccad0c9-277f-49ae-89be-d900cf66a24d |
    | ratings     | reviews:v2     | Cookie:.*?user=jason          | 10       | v1(1.0->delay=7.0)                     | e76d79e6-8b3e-45a7-87e7-674480a92d7c |
    +-------------+----------------+-------------------------------+----------+----------------------------------------+--------------------------------------+    

    $ a8ctl rule-delete e76d79e6-8b3e-45a7-87e7-674480a92d7c
    Deleted rule with id: e76d79e6-8b3e-45a7-87e7-674480a92d7c
       
    $ a8ctl traffic-start reviews v2
    Transfer starting for reviews: diverting 10% of traffic from v1 to v2 
    $ a8ctl traffic-step reviews
    Transfer step for reviews: diverting 20% of traffic from v1 to v2 
    $ a8ctl traffic-step reviews --amount 40
    Transfer step for reviews: diverting 40% of traffic from v1 to v2 
    ...
    $ a8ctl traffic-step reviews
    Transfer step for reviews: diverting 90% of traffic from v1 to v2 
    $ a8ctl traffic-step reviews
    Transfer complete for reviews: sending 100% of traffic to v2
    
    $ a8ctl traffic-start reviews v2
    Transfer starting for reviews: diverting 10% of traffic from v1 to v2 
    $ a8ctl traffic-abort reviews
    Transfer aborted for reviews: all traffic reverted to v1

Contributing
------------
Proposals and pull requests will be considered.
Please see the https://github.com/amalgam8/amalgam8.github.io/blob/master/CONTRIBUTING.md file for more information.
