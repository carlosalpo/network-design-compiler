# Two\-site routed network reference

Design `two-site-reference` · Compiler `0.1.0`

Result: **INVALID MODEL**

Scope: offline design consistency. No device discovery, configuration generation, routing simulation, deployment or reachability test.

## Validation

- **ERROR ADDRESS_OUTSIDE_SUBNET** · `interfaces/branch-core/Ethernet1`: Address is outside its declared segment\.
- **ERROR ADDRESS_OUTSIDE_SUBNET** · `interfaces/branch-edge/Ethernet2`: Address is outside its declared segment\.
- **ERROR SUBNET_OVERLAP** · `segments/hq-transit`: Overlaps segment branch\-transit in the same VRF\.

No topology, inventory or address/link tables were generated.
