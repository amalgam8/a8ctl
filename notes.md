Amalgam8 CLI Redesign
=====================

OLD CLI:
```
a8ctl route-set reviews --default v1
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
a8ctl route-set reviews --default v1 --selector 'v2(weight=0.25)'
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
a8ctl route-set reviews --default v1 --selector 'v2(user="frankb")' --selector 'v3(user="shriram")'
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
a8ctl route-set reviews --default v1 --selector 'v2(header="Foo:bar")' --selector 'v3(weight=0.5)'
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
a8ctl rule-set --source reviews:v2 --destination ratings:v1 --header Cookie --pattern 'user=jason' --delay-probability 1.0 --delay 7
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
