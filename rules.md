## Kubernetes Routing Rules

### Example 1

Send all traffic to v1 of the reviews service

```
from * with urlPrefix:reviews
  routeTo reviews:v1
```

```
match:
  destination:
    urlPrefix: /reviews
route:
    - name: reviews
      labels:
      - v1
```

### Example 1

Send 25% of reviews service traffic to v2, the rest to v1

```
from * with urlPrefix:reviews
  routeTo reviews:v2 weight 25
  routeTo reviews:v1
```

```
match:
  destination:
    urlPrefix: /reviews
route:
    - name: reviews
      labels:
      - v1
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