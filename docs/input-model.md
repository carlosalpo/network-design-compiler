# Input model v1

Start with [the complete two-site example](../examples/two-site.json). JSON is the only input format. Every object must have exactly its documented keys; optional/unknown keys, duplicate JSON keys, non-finite values and non-UTF-8 data are rejected. The entire input is limited to 1,000,000 bytes.

| Object | Required fields | Bounds |
| --- | --- | --- |
| Design | `schema_version`, `id`, `title`, `sites`, `vrfs`, `segments`, `devices`, `links` | Version must be integer 1; title 1–160 printable characters |
| Site | `id`, `label` | 1–8 sites; labels 1–64 printable characters |
| VRF | `id`, `label` | 1–32 VRFs; labels 1–64 printable characters |
| Segment | `id`, `vrf`, `kind`, `cidr` | 1–256 segments; kind `p2p` or `loopback` |
| Device | `id`, `label`, `site`, `role`, `interfaces` | 1–64 devices |
| Interface | `name`, `segment`, `address` | 1–32 per device; 256 total |
| Link | `id`, `a`, `b`, `speed_mbps` | 0–128 links; speed integer 1–800000 |
| Endpoint (`a` or `b`) | `device`, `interface` | Existing device ID and exact interface name |

IDs are unique within their collection: a lowercase ASCII letter followed by up to 31 lowercase letters, digits or hyphens. References use those exact IDs. Interface names begin with an ASCII letter and contain at most 48 letters, digits, dots, slashes, underscores or hyphens. Interface names are case-sensitive, unique per device and not normalized for vendor aliases (`Gi0/1` and `GigabitEthernet0/1` are different identifiers).

Labels must be printable, single-line strings. Device roles are `router`, `switch`, `firewall` or `server`; these affect display only. Interface addresses are canonical dotted IPv4 without a prefix; the prefix belongs to the referenced segment. CIDRs must be canonical network addresses with a decimal prefix length. Host bits in a CIDR are errors.

## Routing domains and assignments

A segment belongs to exactly one VRF. An interface inherits its VRF from the segment. Both endpoints of a link must reference the same point-to-point segment. A device may have interfaces in multiple VRFs; no inter-VRF route leaking is implied.

A point-to-point segment has exactly two assigned interfaces on different devices and exactly one link joining them. A `/30` reserves its network and broadcast addresses. Both addresses in a `/31` are usable under the point-to-point convention described in [RFC 3021](https://www.rfc-editor.org/rfc/rfc3021.html). A loopback segment is a `/32` assigned to exactly one interface and cannot participate in a physical link.

Duplicate addresses and overlapping prefixes are rejected within a VRF across the whole model. This deliberately excludes secondary prefixes, shared/anycast addresses, subnet nesting, unnumbered links and multipoint segments. Repeated addresses/prefixes in separate VRFs are supported. A loopback that overlaps a point-to-point range in its VRF is rejected.

The implementation rejects multicast, unspecified, loopback, link-local and reserved IPv4 addresses, plus the entire `0.0.0.0/8` block. Private and documentation ranges are accepted. This is a bounded design rule, not a complete registry-based determination of deployability or globally routable space.

## Minimal connected model

```json
{
  "schema_version": 1,
  "id": "small-link",
  "title": "Two routed devices",
  "sites": [{"id": "lab", "label": "Synthetic lab"}],
  "vrfs": [{"id": "default", "label": "Default"}],
  "segments": [{"id": "transit", "vrf": "default", "kind": "p2p", "cidr": "192.0.2.0/31"}],
  "devices": [
    {"id": "r1", "label": "Router 1", "site": "lab", "role": "router", "interfaces": [
      {"name": "Ethernet1", "segment": "transit", "address": "192.0.2.0"}
    ]},
    {"id": "r2", "label": "Router 2", "site": "lab", "role": "router", "interfaces": [
      {"name": "Ethernet1", "segment": "transit", "address": "192.0.2.1"}
    ]}
  ],
  "links": [{"id": "transit", "a": {"device": "r1", "interface": "Ethernet1"},
    "b": {"device": "r2", "interface": "Ethernet1"}, "speed_mbps": 1000}]
}
```

The compiler intentionally does not infer interfaces, addresses, speeds or missing links. Supply those decisions explicitly and use separate engineering review for platform capabilities, protocol design and operational behavior.
