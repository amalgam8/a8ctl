## Amalgam8 CLI Redesign

### New CLI Commands

#### rule-create

```
a8ctl rule-create [ -f rules.yaml|rules.json ]
```
Create one or more routing or action rules described 
by the [Rules DSL](https://www.amalgam8.io/docs/control-plane/controller/rules-dsl/)
in the specified JSON or YAML file. If the value of the -f argument is a single dash
character (`-f -`) or no -f argument is specified, the Rules DSL is read from stdin.

#### rule-delete

```
a8ctl rule-delete [-i id]* [-t tag]* [-d destination]*
```
Delete one or more rules with the specified rule ids, tags, or destinations.

#### rule-get

```
a8ctl rule-get [-o json|yaml] [-i id]* [-t tag]* [-d destination]*
```
Output the [Rules DSL](https://www.amalgam8.io/docs/control-plane/controller/rules-dsl/)
of one or more rules with the specified rule ids, tags, or destinations.
Rule DSL is output in YAML by default but can be changed using the -o option.

#### route-list

```
a8ctl route-list
```
Output a table listing all of the currently defined routing-type rules.

#### action-list

```
a8ctl action-list
```
Output a table listing all of the currently defined action-type rules.

#### service-list

```
a8ctl service-list
```
Output a table listing all of the currently defined services along with any active instances of them.

#### traffic-*

```
a8ctl traffic-start service-name tags [--amount percent]
a8ctl traffic-step service-name [--amount percent]
a8ctl traffic-abort service-name
```
Start/stop/abort traffic to a new version of a service. Unchanged from OLD CLI.

#### recipe-run

a8ctl recipe-run --topology topology.json --scenarios scenarios.json --checks checks.json --header Cookie --pattern='user=jason'

### Examples

#### rule-create

OLD CLI:
```
$ a8ctl route-set reviews --default v1
```
NEW CLI:
```
$ cat <<EOF | a8ctl rule-create -f -
- destination: reviews
  priority: 1
  route:
    backends:
    - tags:
      - v1
EOF
```

OLD CLI:
```
$ a8ctl route-set reviews --default v1 --selector 'v2(weight=0.25)'
```
NEW CLI:
```
$ cat <<EOF | a8ctl rule-create -f -
- destination: reviews
  priority: 1
  route:
    backends:
    - tags:
      - v2
      weight: 0.25
    - tags:
      - v1
EOF
```

OLD CLI:
```
$ a8ctl route-set reviews --default v1 --selector 'v2(user="frankb")' --selector 'v3(user="shriram")'
```
NEW CLI:
```
$ cat <<EOF | a8ctl rule-create -f -
- destination: reviews
  priority: 3
  match:
    headers:
      Cookie: ".*?user=frankb"
  route:
    backends:
    - tags:
      - v2
- destination: reviews
  priority: 2
  match:
    headers:
      Cookie: ".*?user=shriram"
  route:
    backends:
    - tags:
      - v3
- destination: reviews
  priority: 1
  route:
    backends:
    - tags:
      - v1
EOF
```

OLD CLI:
```
$ a8ctl route-set reviews --default v1 --selector 'v2(header="Foo:bar")' --selector 'v3(weight=0.5)'
```
NEW CLI:
```
$ cat <<EOF | a8ctl rule-create -f -
- destination: reviews
  priority: 2
  match:
    headers:
      Foo: bar
  route:
    backends:
    - tags:
      - v2
- destination: reviews
  priority: 1
  route:
    backends:
    - tags:
      - v3
      weight: 0.5
    - tags:
      - v1
EOF
```

OLD CLI:
```
$ a8ctl rule-set --source reviews:v2 --destination ratings:v1 --header Cookie --pattern 'user=jason' --delay-probability 1.0 --delay 7
```
NEW CLI:
```
$ cat <<EOF | a8ctl rule-create -f -
- destination: ratings
  priority: 10
  match:
    source:
      name: reviews
      tags:
      - v2
    headers:
      Cookie: ".*?user=jason"
  actions:
  - action: delay
    probability: 1
    tags:
    - v1
    duration: 7
EOF
```

#### action-list

OLD CLI:
```
$ a8ctl action-list
+-------------+----------------+-------------------------------+----------+----------------------------------------+------------+
| Destination | Source         | Headers                       | Priority | Actions                                | Rule Id    |
+-------------+----------------+-------------------------------+----------+----------------------------------------+------------+
| reviews     | productpage:v1 | Foo:bar, Cookie:.*?user=jason | 15       | v2(0.5->delay=5.0), v2(1.0->abort=400) | my-action1 |
| ratings     | reviews:v2     | Cookie:.*?user=jason          | 10       | v1(1.0->delay=7.0)                     | my-action2 |
+-------------+----------------+-------------------------------+----------+----------------------------------------+------------+    
```
NEW CLI ?????
```
+-------------+------------+----------+----------------------------------------------------------------+---------------------------------------------------------+
| Destination | Rule Id    | Priority | Match                                                          | Actions                                                 |
+-------------+------------+----------+----------------------------------------------------------------+---------------------------------------------------------+
| reviews     | my-action1 | 15       | (source=productpage:v1, headers=Foo:bar, Cookie:.*?user=jason) | (action=delay, tags=v2, probability=0.5, duration=5),   |
|             |            |          |                                                                | (action=abort, tags=v2, probability=1, return_code=400) |
| ratings     | my-action2 | 10       | (source=reviews:v2, headers=Cookie:.*?user=jason)              | (action=delay, tags=v2, probability=1, duration=7)      |
+-------------+------------+----------+----------------------------------------------------------------+---------------------------------------------------------+
```