## Service-mesh Routing Rules DSL Examples

### Example 1

**Informal Grammar:**
```
from *:env=staging,region=us-east
  routeTo *:env=staging
```

**Rule DSL:**
```
match:
  source:
    labels:
      - env=staging
      - region=us-east
route:
  - labels:
    - env=staging
```

### Example 2

**Informal Grammar:**
```
from serviceA:env=staging,experimental=true with url:/serviceB/api/v1
  routeTo serviceB:env=prod
```

**Rule DSL:**
```
match:
  destination:
    urlPath: /serviceB/api/v1
  source:
    name: serviceA
    labels:
      - env=staging
      - experimental=true
route:
  - name: serviceB
    labels:
    - env=prod
```

### Example 3

**Informal Grammar:**
```
from serviceA:env=prod with url:/serviceB/api/v1 
  routeTo serviceB:env=prod,v1.1 weight 1
  routeTo serviceB:env=prod,v1 weight 99
```

**Rule DSL:**
```
match:
  destination:
    urlPath: /serviceB/api/v1
  source:
    name: serviceA
    labels:
      - env=prod
route:
  - name: serviceB
    labels:
    - env=prod
    - v1.1
    weight: 1
  - name: serviceB
    labels:
    - env=prod
    - v1
    weight: 99
```

### Example 4

**Informal Grammar:**
```
from * with header:Cookie=".*?user=tester1" 
  routeTo serviceB:v1.1
```

**Rule DSL:**
```
match:
  destination:
    urlPath: /serviceB/api/v1
  headers:
    - name: Cookie
      value: .*?user=tester1
route:
  - name: serviceB
    labels:
    - v1.1
```

### Example 5

**Informal Grammar:**
```
from * with localhost:3306 
  routeTo mysql-slave-5.6 weight 99
  routeTo mysql-slave-5.7-test weight 1
```

**Rule DSL:**
```
match:
  destination:
    ipPort: localhost:3306
route:
  - name: mysql-slave-5.7-test
    weight: 1
  - name: mysql-slave-5.6
    weight: 99
```

### More Examples

#### Send all traffic to v1 of serviceA

```
match:
  destination:
    urlPrefix: serviceA
route:
  - name: serviceA
    labels:
    - v1
```

#### Send 25% of serviceA traffic to v2, the rest to v1

```
match:
  destination:
    urlPrefix: serviceA
route:
  - name: serviceA
    labels:
    - v2
    weight: 25
  - name: serviceA
    labels:
    - v1
```
