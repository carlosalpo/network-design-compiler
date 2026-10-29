# Two\-site routed network reference

Design `two-site-reference` · Compiler `0.1.0`

Result: **INVALID MODEL**

Scope: offline design consistency. No device discovery, configuration generation, routing simulation, deployment or reachability test.

## Validation

- **ERROR UNKNOWN_ENDPOINT** · `links/wan`: A referenced device/interface does not exist\.
- **ERROR P2P_LINK_REQUIRED** · `segments/wan`: Exactly one link must join the two assigned interfaces\.

No topology, inventory or address/link tables were generated.
