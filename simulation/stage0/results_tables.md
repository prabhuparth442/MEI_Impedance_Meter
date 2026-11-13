
### S1: budget parts (1% R, 5% C), no calibration

| Bridge | Case | \|Z\| err std % | \|Z\| err p95 % | phase err std deg | phase err p95 deg | extra metric (p95) | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|---|
| Wheatstone | R 100ohm (R3=100) | 1.031 | 2.074 | 0.034 | 0.084 |  | FAIL |
| Wheatstone | R 220ohm (R3=100) | 1.111 | 2.155 | 0.051 | 0.111 |  | FAIL |
| Wheatstone | R 1kohm (R3=1k) | 1.036 | 1.985 | 0.036 | 0.088 |  | FAIL |
| Wheatstone | R 2.2kohm (R3=1k) | 1.140 | 2.273 | 0.047 | 0.101 |  | FAIL |
| Wheatstone | R 4.7kohm (R3=10k) | 1.089 | 2.067 | 0.037 | 0.086 |  | FAIL |
| Wheatstone | R 10kohm (R3=10k) | 1.045 | 2.021 | 0.036 | 0.072 |  | FAIL |
| Wheatstone | R 47kohm (R3=100k) | 1.055 | 1.944 | 0.056 | 0.196 |  | FAIL |
| Wheatstone | R 100kohm (R3=100k) | 1.001 | 1.926 | 0.092 | 0.390 |  | FAIL |
| Kelvin | R 1ohm (Rs=1) | 3.517 | 6.519 | 0.912 | 1.763 |  | FAIL |
| Kelvin | R 2.2ohm (Rs=1) | 1.729 | 3.232 | 0.407 | 0.773 |  | FAIL |
| Kelvin | R 4.7ohm (Rs=10) | 5.702 | 9.776 | 0.210 | 0.401 |  | FAIL |
| Kelvin | R 10ohm (Rs=10) | 3.073 | 5.135 | 0.099 | 0.188 |  | FAIL |
| Kelvin | R 22ohm (Rs=10) | 1.681 | 2.922 | 0.069 | 0.133 |  | FAIL |
| Maxwell-Wien | L 10mH, DCR 8ohm (R3=100, R4=10k) | 2.877 | 5.072 | 0.418 | 0.749 | L 5.31 %, dR 0.24 ohm | FAIL |
| Maxwell-Wien | L 22mH, DCR 18ohm (R3=100, R4=10k) | 1.352 | 2.459 | 0.248 | 0.444 | L 2.60 %, dR 0.32 ohm | FAIL |
| Maxwell-Wien | L 47mH, DCR 35ohm (R3=1k, R4=33k) | 5.894 | 9.952 | 0.290 | 0.636 | L 9.84 %, dR 4.77 ohm | FAIL |
| Maxwell-Wien | L 100mH, DCR 60ohm (R3=1k, R4=10k) | 2.722 | 4.840 | 0.310 | 0.566 | L 5.01 %, dR 1.52 ohm | FAIL |
| Schering | C 1e-08F, ESR 15.9ohm (R4=100) | 3.100 | 5.382 | 1.309 | 2.547 | C 5.34 %, d tan 0.0445 | FAIL |
| Schering | C 4.7e-08F, ESR 3.39ohm (R4=330) | 2.187 | 3.911 | 0.297 | 0.557 | C 3.91 %, d tan 0.0097 | FAIL |
| Schering | C 1e-07F, ESR 63.7ohm (R4=1k) | 3.016 | 5.240 | 0.149 | 0.299 | C 5.19 %, d tan 0.0052 | FAIL |
| Schering | C 2.2e-07F, ESR 0.723ohm (R4=3.3k) | 2.812 | 4.733 | 0.691 | 1.197 | C 4.76 %, d tan 0.0209 | FAIL |
| Schering | C 1e-06F, ESR 0.318ohm (R4=10k) | 2.574 | 4.519 | 0.573 | 1.071 | C 4.46 %, d tan 0.0187 | FAIL |
| Schering | C 1e-05F, ESR 2ohm (R4=100k) | 3.158 | 5.884 | 6.304 | 11.730 | C 4.59 %, d tan 0.2068 | FAIL |

### S2: 0.1% R / 1% C standards, no calibration

| Bridge | Case | \|Z\| err std % | \|Z\| err p95 % | phase err std deg | phase err p95 deg | extra metric (p95) | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|---|
| Wheatstone | R 100ohm (R3=100) | 0.173 | 0.333 | 0.037 | 0.088 |  | PASS |
| Wheatstone | R 220ohm (R3=100) | 0.208 | 0.419 | 0.046 | 0.101 |  | PASS |
| Wheatstone | R 1kohm (R3=1k) | 0.163 | 0.312 | 0.036 | 0.088 |  | PASS |
| Wheatstone | R 2.2kohm (R3=1k) | 0.240 | 0.454 | 0.046 | 0.092 |  | PASS |
| Wheatstone | R 4.7kohm (R3=10k) | 0.186 | 0.383 | 0.037 | 0.081 |  | PASS |
| Wheatstone | R 10kohm (R3=10k) | 0.166 | 0.308 | 0.035 | 0.068 |  | PASS |
| Wheatstone | R 47kohm (R3=100k) | 0.177 | 0.340 | 0.058 | 0.191 |  | PASS |
| Wheatstone | R 100kohm (R3=100k) | 0.168 | 0.318 | 0.094 | 0.407 |  | PASS |
| Kelvin | R 1ohm (Rs=1) | 1.580 | 3.218 | 0.899 | 1.694 |  | FAIL |
| Kelvin | R 2.2ohm (Rs=1) | 0.867 | 1.705 | 0.385 | 0.797 |  | FAIL |
| Kelvin | R 4.7ohm (Rs=10) | 1.397 | 2.555 | 0.203 | 0.381 |  | FAIL |
| Kelvin | R 10ohm (Rs=10) | 0.611 | 1.079 | 0.110 | 0.212 |  | FAIL |
| Kelvin | R 22ohm (Rs=10) | 0.434 | 0.838 | 0.065 | 0.121 |  | FAIL |
| Maxwell-Wien | L 10mH, DCR 8ohm (R3=100, R4=10k) | 0.581 | 1.032 | 0.157 | 0.294 | L 1.09 %, dR 0.15 ohm | FAIL |
| Maxwell-Wien | L 22mH, DCR 18ohm (R3=100, R4=10k) | 0.288 | 0.539 | 0.083 | 0.152 | L 0.57 %, dR 0.17 ohm | FAIL |
| Maxwell-Wien | L 47mH, DCR 35ohm (R3=1k, R4=33k) | 1.114 | 1.929 | 0.068 | 0.152 | L 1.90 %, dR 0.95 ohm | FAIL |
| Maxwell-Wien | L 100mH, DCR 60ohm (R3=1k, R4=10k) | 0.537 | 0.906 | 0.069 | 0.131 | L 0.94 %, dR 0.37 ohm | FAIL |
| Schering | C 1e-08F, ESR 15.9ohm (R4=100) | 0.986 | 1.894 | 1.295 | 2.580 | C 1.91 %, d tan 0.0451 | FAIL |
| Schering | C 4.7e-08F, ESR 3.39ohm (R4=330) | 0.457 | 0.796 | 0.266 | 0.529 | C 0.80 %, d tan 0.0092 | FAIL |
| Schering | C 1e-07F, ESR 63.7ohm (R4=1k) | 0.620 | 1.022 | 0.134 | 0.262 | C 1.03 %, d tan 0.0046 | FAIL |
| Schering | C 2.2e-07F, ESR 0.723ohm (R4=3.3k) | 0.522 | 0.904 | 0.136 | 0.256 | C 0.91 %, d tan 0.0045 | FAIL |
| Schering | C 1e-06F, ESR 0.318ohm (R4=10k) | 0.518 | 0.843 | 0.113 | 0.215 | C 0.84 %, d tan 0.0038 | FAIL |
| Schering | C 1e-05F, ESR 2ohm (R4=100k) | 0.649 | 1.160 | 1.190 | 2.294 | C 1.03 %, d tan 0.0401 | FAIL |

### S3: standards calibrated vs reference + ADC loopback-calibrated

| Bridge | Case | \|Z\| err std % | \|Z\| err p95 % | phase err std deg | phase err p95 deg | extra metric (p95) | 0.5 % / 0.5 deg |
|---|---|---|---|---|---|---|---|
| Wheatstone | R 100ohm (R3=100) | 0.094 | 0.189 | 0.023 | 0.064 |  | PASS |
| Wheatstone | R 220ohm (R3=100) | 0.103 | 0.209 | 0.025 | 0.069 |  | PASS |
| Wheatstone | R 1kohm (R3=1k) | 0.094 | 0.188 | 0.020 | 0.060 |  | PASS |
| Wheatstone | R 2.2kohm (R3=1k) | 0.110 | 0.217 | 0.026 | 0.067 |  | PASS |
| Wheatstone | R 4.7kohm (R3=10k) | 0.102 | 0.190 | 0.025 | 0.058 |  | PASS |
| Wheatstone | R 10kohm (R3=10k) | 0.099 | 0.191 | 0.023 | 0.044 |  | PASS |
| Wheatstone | R 47kohm (R3=100k) | 0.107 | 0.203 | 0.050 | 0.174 |  | PASS |
| Wheatstone | R 100kohm (R3=100k) | 0.097 | 0.189 | 0.091 | 0.391 |  | PASS |
| Kelvin | R 1ohm (Rs=1) | 1.547 | 2.977 | 0.863 | 1.771 |  | FAIL |
| Kelvin | R 2.2ohm (Rs=1) | 0.737 | 1.402 | 0.401 | 0.750 |  | FAIL |
| Kelvin | R 4.7ohm (Rs=10) | 0.583 | 1.139 | 0.203 | 0.401 |  | FAIL |
| Kelvin | R 10ohm (Rs=10) | 0.272 | 0.555 | 0.107 | 0.215 |  | FAIL |
| Kelvin | R 22ohm (Rs=10) | 0.221 | 0.435 | 0.061 | 0.125 |  | PASS |
| Maxwell-Wien | L 10mH, DCR 8ohm (R3=100, R4=10k) | 0.307 | 0.591 | 0.133 | 0.253 | L 0.60 %, dR 0.14 ohm | FAIL |
| Maxwell-Wien | L 22mH, DCR 18ohm (R3=100, R4=10k) | 0.149 | 0.305 | 0.066 | 0.125 | L 0.33 %, dR 0.15 ohm | PASS |
| Maxwell-Wien | L 47mH, DCR 35ohm (R3=1k, R4=33k) | 0.431 | 0.834 | 0.042 | 0.113 | L 0.82 %, dR 0.47 ohm | FAIL |
| Maxwell-Wien | L 100mH, DCR 60ohm (R3=1k, R4=10k) | 0.189 | 0.381 | 0.028 | 0.061 | L 0.40 %, dR 0.28 ohm | PASS |
| Schering | C 1e-08F, ESR 15.9ohm (R4=100) | 0.399 | 0.817 | 0.280 | 0.552 | C 0.81 %, d tan 0.0096 | FAIL |
| Schering | C 4.7e-08F, ESR 3.39ohm (R4=330) | 0.175 | 0.352 | 0.063 | 0.119 | C 0.35 %, d tan 0.0021 | PASS |
| Schering | C 1e-07F, ESR 63.7ohm (R4=1k) | 0.232 | 0.455 | 0.030 | 0.064 | C 0.45 %, d tan 0.0011 | PASS |
| Schering | C 2.2e-07F, ESR 0.723ohm (R4=3.3k) | 0.194 | 0.372 | 0.050 | 0.108 | C 0.37 %, d tan 0.0019 | PASS |
| Schering | C 1e-06F, ESR 0.318ohm (R4=10k) | 0.186 | 0.370 | 0.042 | 0.087 | C 0.37 %, d tan 0.0015 | PASS |
| Schering | C 1e-05F, ESR 2ohm (R4=100k) | 0.321 | 0.620 | 0.399 | 0.787 | C 0.57 %, d tan 0.0138 | FAIL |

### Error budget, one source at a time, S2: 0.1% R / 1% C standards, no calibration (std of |Z| error % / phase error deg)

| Bridge | Case | component tolerance | stray capacitance (detector nodes) | ADC noise + quantisation | ADC channel gain mismatch | ADC INL (cubic) | channel timing / phase mismatch | return-buffer (A2) output impedance | loss of C standards | Kelvin link resistance r | all together |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Wheatstone | R 1kohm (R3=1k) | 0.103 / 0.000 | 0.000 / 0.009 | 0.028 / 0.017 | 0.152 / 0.000 | 0.000 / 0.000 | 0.000 / 0.031 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.163 / 0.036 |
| Wheatstone | R 100kohm (R3=100k) | 0.096 / 0.000 | 0.001 / 0.092 | 0.029 / 0.019 | 0.133 / 0.000 | 0.000 / 0.000 | 0.000 / 0.027 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.168 / 0.094 |
| Kelvin | R 1ohm (Rs=1) | 0.601 / 0.000 | 0.000 / 0.001 | 1.658 / 0.878 | 0.153 / 0.000 | 0.000 / 0.000 | 0.000 / 0.029 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 1.580 / 0.899 |
| Kelvin | R 10ohm (Rs=10) | 0.588 / 0.000 | 0.000 / 0.001 | 0.177 / 0.106 | 0.144 / 0.000 | 0.000 / 0.000 | 0.000 / 0.028 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.611 / 0.110 |
| Maxwell-Wien | L 10mH, DCR 8ohm (R3=100, R4=10k) | 0.557 / 0.082 | 0.000 / 0.000 | 0.238 / 0.133 | 0.078 / 0.002 | 0.000 / 0.001 | 0.001 / 0.014 | 0.000 / 0.000 | 0.003 / 0.006 | 0.000 / 0.000 | 0.581 / 0.157 |
| Maxwell-Wien | L 100mH, DCR 60ohm (R3=1k, R4=10k) | 0.542 / 0.065 | 0.000 / 0.001 | 0.029 / 0.017 | 0.078 / 0.011 | 0.000 / 0.001 | 0.007 / 0.016 | 0.000 / 0.000 | 0.002 / 0.006 | 0.000 / 0.000 | 0.537 / 0.069 |
| Schering | C 4.7e-08F, ESR 3.39ohm (R4=330) | 0.407 / 0.018 | 0.012 / 0.000 | 0.052 / 0.027 | 0.084 / 0.275 | 0.000 / 0.001 | 0.160 / 0.016 | 0.000 / 0.000 | 0.001 / 0.004 | 0.000 / 0.000 | 0.457 / 0.266 |
| Schering | C 1e-06F, ESR 0.318ohm (R4=10k) | 0.506 / 0.118 | 0.004 / 0.001 | 0.028 / 0.015 | 0.073 / 0.013 | 0.000 / 0.003 | 0.007 / 0.014 | 0.000 / 0.001 | 0.004 / 0.006 | 0.000 / 0.000 | 0.518 / 0.113 |

### Error budget, one source at a time, S3: standards calibrated vs reference + ADC loopback-calibrated (std of |Z| error % / phase error deg)

| Bridge | Case | component tolerance | stray capacitance (detector nodes) | ADC noise + quantisation | ADC channel gain mismatch | ADC INL (cubic) | channel timing / phase mismatch | return-buffer (A2) output impedance | loss of C standards | Kelvin link resistance r | all together |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Wheatstone | R 1kohm (R3=1k) | 0.086 / 0.000 | 0.000 / 0.010 | 0.030 / 0.017 | 0.025 / 0.000 | 0.000 / 0.000 | 0.000 / 0.008 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.094 / 0.020 |
| Wheatstone | R 100kohm (R3=100k) | 0.094 / 0.000 | 0.001 / 0.090 | 0.031 / 0.017 | 0.028 / 0.000 | 0.000 / 0.000 | 0.000 / 0.009 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.097 / 0.091 |
| Kelvin | R 1ohm (Rs=1) | 0.199 / 0.000 | 0.000 / 0.001 | 1.569 / 0.843 | 0.031 / 0.000 | 0.000 / 0.000 | 0.000 / 0.009 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 1.547 / 0.863 |
| Kelvin | R 10ohm (Rs=10) | 0.222 / 0.000 | 0.000 / 0.001 | 0.172 / 0.104 | 0.028 / 0.000 | 0.000 / 0.000 | 0.000 / 0.008 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.272 / 0.107 |
| Maxwell-Wien | L 10mH, DCR 8ohm (R3=100, R4=10k) | 0.189 / 0.027 | 0.000 / 0.000 | 0.235 / 0.133 | 0.015 / 0.000 | 0.000 / 0.001 | 0.000 / 0.004 | 0.000 / 0.000 | 0.003 / 0.006 | 0.000 / 0.000 | 0.307 / 0.133 |
| Maxwell-Wien | L 100mH, DCR 60ohm (R3=1k, R4=10k) | 0.203 / 0.024 | 0.001 / 0.001 | 0.031 / 0.016 | 0.015 / 0.002 | 0.000 / 0.001 | 0.002 / 0.004 | 0.000 / 0.000 | 0.002 / 0.006 | 0.000 / 0.000 | 0.189 / 0.028 |
| Schering | C 4.7e-08F, ESR 3.39ohm (R4=330) | 0.155 / 0.006 | 0.011 / 0.000 | 0.053 / 0.028 | 0.016 / 0.053 | 0.000 / 0.001 | 0.052 / 0.005 | 0.000 / 0.000 | 0.001 / 0.005 | 0.000 / 0.000 | 0.175 / 0.063 |
| Schering | C 1e-06F, ESR 0.318ohm (R4=10k) | 0.192 / 0.040 | 0.004 / 0.001 | 0.025 / 0.015 | 0.015 / 0.002 | 0.000 / 0.003 | 0.002 / 0.004 | 0.000 / 0.001 | 0.004 / 0.006 | 0.000 / 0.000 | 0.186 / 0.042 |

### ADC channel gain mismatch sweep (S3 otherwise; p95 of |Z| error % / phase error deg)

| Bridge | Case | 0.01 % | 0.05 % | 0.2 % |
|---|---|---|---|---|
| Wheatstone | R 1kohm (R3=1k) | 0.160 / 0.059 | 0.320 / 0.065 | 1.092 / 0.057 |
| Wheatstone | R 100kohm (R3=100k) | 0.184 / 0.406 | 0.335 / 0.391 | 1.323 / 0.400 |
| Kelvin | R 1ohm (Rs=1) | 3.346 / 1.600 | 3.031 / 1.704 | 3.148 / 1.708 |
| Kelvin | R 10ohm (Rs=10) | 0.547 / 0.193 | 0.590 / 0.194 | 1.206 / 0.210 |
| Maxwell-Wien | L 10mH, DCR 8ohm (R3=100, R4=10k) | 0.597 / 0.279 | 0.608 / 0.277 | 0.835 / 0.296 |
| Maxwell-Wien | L 100mH, DCR 60ohm (R3=1k, R4=10k) | 0.398 / 0.065 | 0.414 / 0.069 | 0.741 / 0.115 |
| Schering | C 4.7e-08F, ESR 3.39ohm (R4=330) | 0.350 / 0.123 | 0.384 / 0.547 | 0.754 / 2.244 |
| Schering | C 1e-06F, ESR 0.318ohm (R4=10k) | 0.361 / 0.091 | 0.348 / 0.090 | 0.639 / 0.120 |
