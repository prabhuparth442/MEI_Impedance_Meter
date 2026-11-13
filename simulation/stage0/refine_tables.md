
### Maxwell-Wien, improved arm choice, S2: 0.1% R / 1% C standards, no calibration

| Case | |Z| std % | |Z| p95 % | phase std deg | phase p95 deg | extra | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|
| L 10mH (R3=100, R4=12000) | 0.605 | 1.054 | 0.154 | 0.301 | L p95 1.11 % | FAIL |
| L 22mH (R3=470, R4=27000) | 1.191 | 1.986 | 0.091 | 0.200 | L p95 2.04 % | FAIL |
| L 47mH (R3=470, R4=15000) | 0.582 | 0.955 | 0.082 | 0.145 | L p95 1.00 % | FAIL |
| L 100mH (R3=1000, R4=18000) | 0.598 | 1.008 | 0.070 | 0.137 | L p95 1.05 % | FAIL |

### Schering, improved arm choice, S2: 0.1% R / 1% C standards, no calibration

| Case | |Z| std % | |Z| p95 % | phase std deg | phase p95 deg | extra | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|
| C 10nF (R3=10000, R4=1000, C4=1nF) | 0.557 | 1.024 | 0.126 | 0.231 | C p95 1.04 %, d tan p95 0.0040 | FAIL |
| C 47nF (R3=10000, R4=4700, C4=1nF) | 0.571 | 0.929 | 0.033 | 0.071 | C p95 0.94 %, d tan p95 0.0012 | FAIL |
| C 100nF (R3=10000, R4=10000, C4=1nF) | 0.593 | 0.980 | 0.028 | 0.067 | C p95 0.98 %, d tan p95 0.0012 | FAIL |
| C 220nF (R3=1000, R4=2200, C4=1nF) | 0.584 | 1.012 | 0.063 | 0.129 | C p95 1.01 %, d tan p95 0.0022 | FAIL |
| C 1000nF (R3=1000, R4=10000, C4=1nF) | 0.606 | 0.996 | 0.027 | 0.064 | C p95 1.00 %, d tan p95 0.0011 | FAIL |
| C 10000nF (R3=100, R4=10000, C4=1nF) | 0.584 | 0.981 | 0.028 | 0.064 | C p95 0.97 %, d tan p95 0.0011 | FAIL |

### Maxwell-Wien, improved arm choice, S3: standards calibrated vs reference + ADC loopback-calibrated

| Case | |Z| std % | |Z| p95 % | phase std deg | phase p95 deg | extra | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|
| L 10mH (R3=100, R4=12000) | 0.287 | 0.558 | 0.131 | 0.260 | L p95 0.58 % | FAIL |
| L 22mH (R3=470, R4=27000) | 0.443 | 0.842 | 0.068 | 0.146 | L p95 0.86 % | FAIL |
| L 47mH (R3=470, R4=15000) | 0.220 | 0.429 | 0.040 | 0.087 | L p95 0.44 % | PASS |
| L 100mH (R3=1000, R4=18000) | 0.214 | 0.418 | 0.028 | 0.065 | L p95 0.43 % | PASS |

### Schering, improved arm choice, S3: standards calibrated vs reference + ADC loopback-calibrated

| Case | |Z| std % | |Z| p95 % | phase std deg | phase p95 deg | extra | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|
| C 10nF (R3=10000, R4=1000, C4=1nF) | 0.210 | 0.502 | 0.030 | 0.069 | C p95 0.50 %, d tan p95 0.0012 | FAIL |
| C 47nF (R3=10000, R4=4700, C4=1nF) | 0.222 | 0.426 | 0.014 | 0.039 | C p95 0.42 %, d tan p95 0.0007 | PASS |
| C 100nF (R3=10000, R4=10000, C4=1nF) | 0.209 | 0.389 | 0.017 | 0.044 | C p95 0.39 %, d tan p95 0.0008 | PASS |
| C 220nF (R3=1000, R4=2200, C4=1nF) | 0.218 | 0.427 | 0.017 | 0.045 | C p95 0.43 %, d tan p95 0.0008 | PASS |
| C 1000nF (R3=1000, R4=10000, C4=1nF) | 0.211 | 0.441 | 0.018 | 0.049 | C p95 0.44 %, d tan p95 0.0009 | PASS |
| C 10000nF (R3=100, R4=10000, C4=1nF) | 0.214 | 0.407 | 0.018 | 0.049 | C p95 0.41 %, d tan p95 0.0009 | PASS |

### Kelvin with ideal x10 gain on detector nodes (noise / 10), S2: 0.1% R / 1% C standards, no calibration

| Case | |Z| std % | |Z| p95 % | phase std deg | phase p95 deg | extra | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|
| R 1ohm (Rs=1) | 0.687 | 1.292 | 0.140 | 0.265 |  | FAIL |
| R 2.2ohm (Rs=1) | 0.436 | 0.807 | 0.064 | 0.126 |  | FAIL |
| R 4.7ohm (Rs=10) | 1.287 | 2.361 | 0.051 | 0.103 |  | FAIL |
| R 10ohm (Rs=10) | 0.601 | 1.031 | 0.033 | 0.066 |  | FAIL |
| R 22ohm (Rs=10) | 0.437 | 0.846 | 0.031 | 0.058 |  | FAIL |

### Kelvin with ideal x10 gain on detector nodes (noise / 10), S3: standards calibrated vs reference + ADC loopback-calibrated

| Case | |Z| std % | |Z| p95 % | phase std deg | phase p95 deg | extra | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|
| R 1ohm (Rs=1) | 0.429 | 0.820 | 0.137 | 0.273 |  | FAIL |
| R 2.2ohm (Rs=1) | 0.237 | 0.503 | 0.063 | 0.122 |  | FAIL |
| R 4.7ohm (Rs=10) | 0.504 | 0.987 | 0.037 | 0.073 |  | FAIL |
| R 10ohm (Rs=10) | 0.224 | 0.435 | 0.020 | 0.039 |  | PASS |
| R 22ohm (Rs=10) | 0.187 | 0.411 | 0.013 | 0.026 |  | PASS |
