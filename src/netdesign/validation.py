"""Model consistency checks; these do not predict forwarding or availability."""

from collections import defaultdict
from ipaddress import IPv4Address, IPv4Network

from .model import canonical, check_shape


def usable(address):
    return not (
        address.is_multicast
        or address.is_unspecified
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or int(address) < 2**24
    )


def validate(data):
    check_shape(data)
    data = canonical(data)
    findings = []

    def add(code, location, message, severity="error"):
        findings.append(dict(code=code, location=location, message=message, severity=severity))

    def index(values, location):
        result = {}
        for value in values:
            if value["id"] in result:
                add("DUPLICATE_ID", location, "IDs must be unique within this collection.")
            result[value["id"]] = value
        return result

    sites = index(data["sites"], "sites")
    vrfs = index(data["vrfs"], "vrfs")
    segments = index(data["segments"], "segments")
    devices = index(data["devices"], "devices")
    index(data["links"], "links")
    networks = {}
    for segment in segments.values():
        location = "segments/" + segment["id"]
        if segment["vrf"] not in vrfs:
            add("UNKNOWN_VRF", location, "Referenced VRF does not exist.")
        try:
            network = IPv4Network(segment["cidr"], strict=True)
            if str(network) != segment["cidr"] or not usable(network.network_address):
                raise ValueError
            if network.prefixlen not in ((30, 31) if segment["kind"] == "p2p" else (32,)):
                raise ValueError
        except ValueError:
            add(
                "INVALID_CIDR", location, "Use a canonical unicast /30 or /31 p2p, or /32 loopback."
            )
            continue
        for other, other_net in networks.items():
            if segments[other]["vrf"] == segment["vrf"] and network.overlaps(other_net):
                add("SUBNET_OVERLAP", location, f"Overlaps segment {other} in the same VRF.")
        networks[segment["id"]] = network

    interfaces, allocations = {}, defaultdict(list)
    used_addresses = set()
    for device in devices.values():
        if device["site"] not in sites:
            add("UNKNOWN_SITE", "devices/" + device["id"], "Referenced site does not exist.")
        for interface in device["interfaces"]:
            key = (device["id"], interface["name"])
            location = f"interfaces/{key[0]}/{key[1]}"
            if key in interfaces:
                add("DUPLICATE_INTERFACE", location, "Interface names must be unique per device.")
            interfaces[key] = interface
            sid = interface["segment"]
            if sid not in segments:
                add("UNKNOWN_SEGMENT", location, "Referenced segment does not exist.")
                continue
            allocations[sid].append(key)
            try:
                ip = IPv4Address(interface["address"])
                if str(ip) != interface["address"] or not usable(ip):
                    raise ValueError
            except ValueError:
                add("INVALID_ADDRESS", location, "Use a canonical unicast IPv4 address.")
                continue
            address_key = (segments[sid]["vrf"], str(ip))
            if address_key in used_addresses:
                add("DUPLICATE_ADDRESS", location, "IPv4 address is already allocated in this VRF.")
            used_addresses.add(address_key)
            if sid not in networks:
                continue
            network = networks[sid]
            if ip not in network:
                add("ADDRESS_OUTSIDE_SUBNET", location, "Address is outside its declared segment.")
            elif network.prefixlen < 31 and ip in (
                network.network_address,
                network.broadcast_address,
            ):
                add(
                    "NETWORK_OR_BROADCAST",
                    location,
                    "Network/broadcast addresses are not host assignments.",
                )

    used_ports, segment_links = set(), defaultdict(list)
    graph = {key: set() for key in devices}
    for link in data["links"]:
        location = "links/" + link["id"]
        a, b = [(link[key]["device"], link[key]["interface"]) for key in ("a", "b")]
        if a[0] == b[0]:
            add("SELF_LINK", location, "A link must connect two different devices.")
        for key in (a, b):
            if key in used_ports:
                add("PORT_REUSE", location, "An interface is used by more than one link endpoint.")
            used_ports.add(key)
        if a not in interfaces or b not in interfaces:
            add("UNKNOWN_ENDPOINT", location, "A referenced device/interface does not exist.")
            continue
        sid = interfaces[a]["segment"]
        if sid != interfaces[b]["segment"]:
            add(
                "LINK_SEGMENT_MISMATCH",
                location,
                "Link endpoints must use the same segment and VRF.",
            )
            continue
        if sid not in segments:
            continue
        if segments[sid]["kind"] != "p2p":
            add("LOOPBACK_LINK", location, "A loopback cannot be a physical link endpoint.")
            continue
        segment_links[sid].append({a, b})
        graph[a[0]].add(b[0])
        graph[b[0]].add(a[0])
    for sid, segment in segments.items():
        expected = 2 if segment["kind"] == "p2p" else 1
        if len(allocations[sid]) != expected:
            add(
                "SEGMENT_CARDINALITY",
                "segments/" + sid,
                f"This segment requires exactly {expected} interface assignment(s).",
            )
        if segment["kind"] == "p2p" and (
            len(segment_links[sid]) != 1 or segment_links[sid][0] != set(allocations[sid])
        ):
            add(
                "P2P_LINK_REQUIRED",
                "segments/" + sid,
                "Exactly one link must join the two assigned interfaces.",
            )
    valid = not any(f["severity"] == "error" for f in findings)
    if valid:
        unseen, components = set(graph), 0
        while unseen:
            pending = [min(unseen)]
            components += 1
            while pending:
                node = pending.pop()
                if node in unseen:
                    unseen.remove(node)
                    pending.extend(graph[node])
        if components > 1:
            add(
                "DISCONNECTED_TOPOLOGY",
                "devices",
                f"Declared graph has {components} components.",
                "warning",
            )
        for node in sorted(graph):
            if not graph[node]:
                add(
                    "ISOLATED_DEVICE",
                    "devices/" + node,
                    "No physical link is declared for this device.",
                    "warning",
                )
    findings.sort(key=lambda f: (f["severity"], f["location"], f["code"]))
    return {
        "schema_version": 1,
        "valid": valid,
        "scope": "offline-design-consistency",
        "findings": findings,
    }
