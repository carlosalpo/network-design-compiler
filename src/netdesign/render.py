"""All projections derive from one validated canonical model."""

import csv
import html
import io
import re
from xml.etree import ElementTree as ET

from . import __version__
from .model import canonical, digest, json_bytes
from .validation import validate


def md(value):
    return re.sub(r"([\\`*{}\[\]()#+.!_|-])", r"\\\1", html.escape(str(value), quote=False))


def csv_bytes(rows, headers):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        values = {}
        for key in headers:
            value = str(row[key])
            values[key] = "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
        writer.writerow(values)
    return output.getvalue().encode()


def projections(data):
    segments = {s["id"]: s for s in data["segments"]}
    interfaces = {(d["id"], p["name"]): p for d in data["devices"] for p in d["interfaces"]}
    peers = {}
    links = []
    for link in data["links"]:
        a, b = [(link[k]["device"], link[k]["interface"]) for k in ("a", "b")]
        peers[a], peers[b] = (link["id"], *b), (link["id"], *a)
        segment = segments[interfaces[a]["segment"]]
        links.append(
            dict(
                id=link["id"],
                a_device=a[0],
                a_interface=a[1],
                a_address=interfaces[a]["address"],
                b_device=b[0],
                b_interface=b[1],
                b_address=interfaces[b]["address"],
                segment=segment["id"],
                vrf=segment["vrf"],
                cidr=segment["cidr"],
                speed_mbps=link["speed_mbps"],
            )
        )
    devices, addresses = [], []
    for device in data["devices"]:
        devices.append(
            {k: device[k] for k in ("id", "label", "site", "role")}
            | {"interfaces": len(device["interfaces"])}
        )
        for interface in device["interfaces"]:
            segment = segments[interface["segment"]]
            peer = peers.get((device["id"], interface["name"]), ("", "", ""))
            addresses.append(
                dict(
                    device=device["id"],
                    interface=interface["name"],
                    site=device["site"],
                    role=device["role"],
                    segment=segment["id"],
                    kind=segment["kind"],
                    vrf=segment["vrf"],
                    cidr=segment["cidr"],
                    address=interface["address"],
                    link=peer[0],
                    peer_device=peer[1],
                    peer_interface=peer[2],
                )
            )
    return devices, addresses, links


def topology(data):
    """Native uncompressed draw.io XML. Built-in shapes only; no remote resources."""
    devices_by_id = {device["id"]: device for device in data["devices"]}
    external = set()
    for link in data["links"]:
        a, b = link["a"]["device"], link["b"]["device"]
        if devices_by_id[a]["site"] != devices_by_id[b]["site"]:
            external.update((a, b))
    by_site = {
        site["id"]: [d for d in data["devices"] if d["site"] == site["id"]]
        for site in data["sites"]
    }
    max_rows = max((len(values) + 1) // 2 for values in by_site.values())
    site_height = max(180, max_rows * 120 + 70)
    page_width = 1040
    page_height = 140 + ((len(by_site) + 1) // 2) * (site_height + 100)
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "type": "device"})
    diagram = ET.SubElement(mxfile, "diagram", {"id": "network-design", "name": "Routed topology"})
    graph = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "adaptiveColors": "auto",
            "grid": "1",
            "gridSize": "10",
            "page": "1",
            "pageScale": "1",
            "pageWidth": str(page_width),
            "pageHeight": str(page_height),
        },
    )
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    def vertex(identifier, value, parent, style, x, y, width, height):
        cell = ET.SubElement(
            root,
            "mxCell",
            {"id": identifier, "value": value, "parent": parent, "vertex": "1", "style": style},
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
                "as": "geometry",
            },
        )

    vertex(
        "heading",
        "<b>" + html.escape(data["title"]) + "</b><br>"
        "Declarative topology — not discovery or verified connectivity. "
        "Link IDs refer to links.csv; interfaces and VRFs are in addresses.csv.",
        "1",
        "text;html=1;whiteSpace=wrap;align=left;verticalAlign=middle;fontSize=14;",
        40,
        20,
        960,
        60,
    )
    roles = {"router": "#dae8fc", "switch": "#d5e8d4", "firewall": "#ffe6cc", "server": "#e1d5e7"}
    for i, site in enumerate(data["sites"]):
        by_site[site["id"]].sort(
            key=lambda device: (
                device["id"] in external if i % 2 == 0 else device["id"] not in external,
                device["id"],
            )
        )
        sid = "site-" + site["id"]
        vertex(
            sid,
            html.escape(site["label"]),
            "1",
            "swimlane;html=1;whiteSpace=wrap;startSize=36;rounded=1;"
            "fillColor=#f5f5f5;strokeColor=#b8c5cc;fontStyle=1;",
            40 + (i % 2) * 500,
            120 + (i // 2) * (site_height + 100),
            440,
            site_height,
        )
        for j, device in enumerate(by_site[site["id"]]):
            vertex(
                "device-" + device["id"],
                f"<b>{html.escape(device['id'])}</b><br>"
                f"{device['role']}<br>{len(device['interfaces'])} interfaces",
                sid,
                "rounded=1;whiteSpace=wrap;html=1;fontSize=12;strokeColor=#506575;"
                f"fillColor={roles[device['role']]};",
                40 + (j % 2) * 180,
                60 + (j // 2) * 120,
                140,
                80,
            )
    devices = {d["id"]: d for d in data["devices"]}
    for link in data["links"]:
        a, b = link["a"]["device"], link["b"]["device"]
        common = devices[a]["site"] == devices[b]["site"]
        edge = ET.SubElement(
            root,
            "mxCell",
            {
                "id": "link-" + link["id"],
                "value": html.escape(link["id"]),
                "edge": "1",
                "source": "device-" + a,
                "target": "device-" + b,
                "parent": "site-" + devices[a]["site"] if common else "1",
                "style": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=none;"
                "defaultLabelBackgroundColor=page;strokeColor=#3d6474;fontSize=11;",
            },
        )
        ET.SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})
    return ET.tostring(mxfile, encoding="utf-8") + b"\n"


def design_report(data, validation, tables=None):
    lines = [
        f"# {md(data['title'])}",
        "",
        f"Design `{data['id']}` · Compiler `{__version__}`",
        "",
        f"Result: **{'VALID MODEL' if validation['valid'] else 'INVALID MODEL'}**",
        "",
        "Scope: offline design consistency. No device discovery, configuration generation, "
        "routing simulation, deployment or reachability test.",
        "",
        "## Validation",
        "",
    ]
    if not validation["findings"]:
        lines.append("No modeled errors or warnings.")
    for finding in validation["findings"]:
        lines.append(
            f"- **{finding['severity'].upper()} {finding['code']}** · "
            f"`{finding['location']}`: {md(finding['message'])}"
        )
    if not validation["valid"]:
        lines += ["", "No topology, inventory or address/link tables were generated.", ""]
        return "\n".join(lines).encode()
    devices, addresses, links = tables
    lines += [
        "",
        "## Inventory",
        "",
        f"{len(data['sites'])} sites · {len(data['vrfs'])} VRFs · "
        f"{len(devices)} devices · {len(addresses)} interfaces · {len(links)} physical links",
        "",
        "| Device | Label | Site | Role | Interfaces |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for row in devices:
        lines.append(
            "| "
            + " | ".join(md(row[k]) for k in ("id", "label", "site", "role", "interfaces"))
            + " |"
        )
    lines += [
        "",
        "## Address plan",
        "",
        "| Device | Interface | VRF | Segment | CIDR | Address | Kind |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in addresses:
        lines.append(
            "| "
            + " | ".join(
                md(row[k])
                for k in ("device", "interface", "vrf", "segment", "cidr", "address", "kind")
            )
            + " |"
        )
    lines += [
        "",
        "## Link schedule",
        "",
        "| Link | Endpoint A | Endpoint B | Segment | Declared Mbps |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for row in links:
        lines.append(
            f"| {md(row['id'])} | {md(row['a_device'])} / {md(row['a_interface'])} | "
            f"{md(row['b_device'])} / {md(row['b_interface'])} | {md(row['segment'])} | "
            f"{row['speed_mbps']} |"
        )
    lines += [
        "",
        "## Diagram and source of truth",
        "",
        "Open [topology.drawio](topology.drawio) in draw.io. Sites are containers; colored "
        "cards identify device roles. Edges are undirected physical declarations labeled "
        "with link IDs. Use links.csv for endpoints and speeds, and addresses.csv for VRFs.",
        "",
        "The canonical model.json drives all artifacts. Edit the input and rebuild into a "
        "new directory to change the design. Manual draw.io edits are not imported back "
        "into the model and will not survive regeneration. Dense layouts may need manual "
        "visual adjustment in a separate copy.",
        "",
        "## Engineering review before use",
        "",
        "Confirm device interface naming/capabilities and declared link speeds. Validate "
        "/31 support on both endpoints. Review VRF membership, routing protocols, policy, "
        "MTU, redundancy, optics/cabling and operational reachability separately. "
        "None of these operational behaviors is certified by a valid model.",
        "",
        "Point-to-point segments require exactly two assigned interfaces and one link; "
        "loopbacks require one assignment and no link. Overlapping prefixes are rejected "
        "within a VRF, including across sites. Reuse in different VRFs is allowed. "
        "A graph component warning describes declared links, not live connectivity.",
        "",
    ]
    return "\n".join(lines).encode()


def compile_design(data, input_hash):
    validation = validate(data)
    data = canonical(data)
    files = {"validation.json": json_bytes(validation)}
    counts = {}
    tables = None
    if validation["valid"]:
        tables = projections(data)
        devices, addresses, links = tables
        counts = {
            "sites": len(data["sites"]),
            "vrfs": len(data["vrfs"]),
            "devices": len(devices),
            "segments": len(data["segments"]),
            "interfaces": len(addresses),
            "links": len(links),
        }
        files.update(
            {
                "model.json": json_bytes(data),
                "topology.drawio": topology(data),
                "devices.csv": csv_bytes(devices, ["id", "label", "site", "role", "interfaces"]),
                "addresses.csv": csv_bytes(
                    addresses,
                    [
                        "device",
                        "interface",
                        "site",
                        "role",
                        "segment",
                        "kind",
                        "vrf",
                        "cidr",
                        "address",
                        "link",
                        "peer_device",
                        "peer_interface",
                    ],
                ),
                "links.csv": csv_bytes(
                    links,
                    [
                        "id",
                        "a_device",
                        "a_interface",
                        "a_address",
                        "b_device",
                        "b_interface",
                        "b_address",
                        "segment",
                        "vrf",
                        "cidr",
                        "speed_mbps",
                    ],
                ),
            }
        )
    files["design.md"] = design_report(data, validation, tables)
    files["manifest.json"] = json_bytes(
        {
            "schema_version": 1,
            "tool": "network-design-compiler",
            "version": __version__,
            "result": "valid-model" if validation["valid"] else "invalid-model",
            "scope": "offline-design-consistency",
            "counts": counts,
            "input_sha256": input_hash,
            "canonical_model_sha256": digest(json_bytes(data)),
            "files": {
                name: {"sha256": digest(raw), "bytes": len(raw)}
                for name, raw in sorted(files.items())
            },
        }
    )
    return files, validation
