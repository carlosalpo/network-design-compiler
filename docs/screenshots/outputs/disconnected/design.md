# Two\-site routed network reference

Design `two-site-reference` · Compiler `0.1.0`

Result: **VALID MODEL**

Scope: offline design consistency. No device discovery, configuration generation, routing simulation, deployment or reachability test.

## Validation

- **WARNING DISCONNECTED_TOPOLOGY** · `devices`: Declared graph has 2 components\.

## Inventory

2 sites · 1 VRFs · 4 devices · 8 interfaces · 2 physical links

| Device | Label | Site | Role | Interfaces |
| --- | --- | --- | --- | ---: |
| branch\-core | Branch Core | branch | router | 2 |
| branch\-edge | Branch Edge | branch | router | 2 |
| hq\-core | Hq Core | hq | router | 2 |
| hq\-edge | Hq Edge | hq | router | 2 |

## Address plan

| Device | Interface | VRF | Segment | CIDR | Address | Kind |
| --- | --- | --- | --- | --- | --- | --- |
| branch\-core | Ethernet1 | production | branch\-transit | 192\.0\.2\.8/30 | 192\.0\.2\.10 | p2p |
| branch\-core | Loopback0 | production | branch\-core\-lo | 198\.51\.100\.4/32 | 198\.51\.100\.4 | loopback |
| branch\-edge | Ethernet2 | production | branch\-transit | 192\.0\.2\.8/30 | 192\.0\.2\.9 | p2p |
| branch\-edge | Loopback0 | production | branch\-edge\-lo | 198\.51\.100\.3/32 | 198\.51\.100\.3 | loopback |
| hq\-core | Ethernet1 | production | hq\-transit | 192\.0\.2\.0/30 | 192\.0\.2\.1 | p2p |
| hq\-core | Loopback0 | production | hq\-core\-lo | 198\.51\.100\.1/32 | 198\.51\.100\.1 | loopback |
| hq\-edge | Ethernet1 | production | hq\-transit | 192\.0\.2\.0/30 | 192\.0\.2\.2 | p2p |
| hq\-edge | Loopback0 | production | hq\-edge\-lo | 198\.51\.100\.2/32 | 198\.51\.100\.2 | loopback |

## Link schedule

| Link | Endpoint A | Endpoint B | Segment | Declared Mbps |
| --- | --- | --- | --- | ---: |
| branch\-transit | branch\-core / Ethernet1 | branch\-edge / Ethernet2 | branch\-transit | 1000 |
| hq\-transit | hq\-core / Ethernet1 | hq\-edge / Ethernet1 | hq\-transit | 1000 |

## Diagram and source of truth

Open [topology.drawio](topology.drawio) in draw.io. Sites are containers; colored cards identify device roles. Edges are undirected physical declarations labeled with link IDs. Use links.csv for endpoints and speeds, and addresses.csv for VRFs.

The canonical model.json drives all artifacts. Edit the input and rebuild into a new directory to change the design. Manual draw.io edits are not imported back into the model and will not survive regeneration. Dense layouts may need manual visual adjustment in a separate copy.

## Engineering review before use

Confirm device interface naming/capabilities and declared link speeds. Validate /31 support on both endpoints. Review VRF membership, routing protocols, policy, MTU, redundancy, optics/cabling and operational reachability separately. None of these operational behaviors is certified by a valid model.

Point-to-point segments require exactly two assigned interfaces and one link; loopbacks require one assignment and no link. Overlapping prefixes are rejected within a VRF, including across sites. Reuse in different VRFs is allowed. A graph component warning describes declared links, not live connectivity.
