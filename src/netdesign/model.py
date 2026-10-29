"""Strict, bounded design input; no vendor configuration parsing."""

import hashlib
import json
import re
from pathlib import Path

MAX_BYTES = 1_000_000
ID = re.compile(r"[a-z][a-z0-9-]{0,31}\Z")
PORT = re.compile(r"[A-Za-z][A-Za-z0-9./_-]{0,47}\Z")


class InputError(ValueError):
    """Invalid input; messages do not include unvalidated values."""


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("Duplicate JSON keys are not accepted.")
        result[key] = value
    return result


def _constant(value):
    raise InputError("Non-finite JSON numbers are not accepted.")


def load(path: Path):
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError("Input exceeds 1,000,000 bytes.")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InputError("Expected UTF-8 JSON with unique keys and finite numbers.") from exc
    check_shape(data)
    return canonical(data), digest(raw)


def fields(value, expected, location):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise InputError(f"{location}: fields must match the input specification exactly.")


def name(value, location):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise InputError(
            f"{location}: use a lowercase letter and up to 31 letters, digits or hyphens."
        )


def label(value, location, maximum=64):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or not value.isprintable():
        raise InputError(f"{location}: expected 1..{maximum} printable characters on one line.")


def port(value):
    if not isinstance(value, str) or not PORT.fullmatch(value):
        raise InputError("Interface name must be an ASCII letter followed by letters/digits ./_-. ")


def items(value, location, minimum=0, maximum=64):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise InputError(f"{location}: expected a list of {minimum}..{maximum} items.")
    return value


def check_shape(data):
    fields(data, "schema_version id title sites vrfs segments devices links", "design")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise InputError("schema_version must be integer 1.")
    name(data["id"], "design.id")
    label(data["title"], "design.title", 160)
    for collection in ("sites", "vrfs"):
        for value in items(data[collection], collection, 1, 8 if collection == "sites" else 32):
            fields(value, "id label", collection)
            name(value["id"], collection + ".id")
            label(value["label"], collection + ".label")
    for segment in items(data["segments"], "segments", 1, 256):
        fields(segment, "id vrf kind cidr", "segment")
        name(segment["id"], "segment.id")
        name(segment["vrf"], "segment.vrf")
        if segment["kind"] not in ("p2p", "loopback"):
            raise InputError("segment.kind must be p2p or loopback.")
        label(segment["cidr"], "segment.cidr", 18)
    total = 0
    for device in items(data["devices"], "devices", 1):
        fields(device, "id label site role interfaces", "device")
        name(device["id"], "device.id")
        name(device["site"], "device.site")
        label(device["label"], "device.label")
        if device["role"] not in ("router", "switch", "firewall", "server"):
            raise InputError("device.role must be router, switch, firewall or server.")
        for interface in items(device["interfaces"], "device.interfaces", 1, 32):
            fields(interface, "name segment address", "interface")
            port(interface["name"])
            name(interface["segment"], "interface.segment")
            label(interface["address"], "interface.address", 15)
            total += 1
    if total > 256:
        raise InputError("At most 256 interfaces are supported.")
    for link in items(data["links"], "links", maximum=128):
        fields(link, "id a b speed_mbps", "link")
        name(link["id"], "link.id")
        if type(link["speed_mbps"]) is not int or not 1 <= link["speed_mbps"] <= 800000:
            raise InputError("link.speed_mbps must be integer 1..800000.")
        for key in ("a", "b"):
            fields(link[key], "device interface", "link endpoint")
            name(link[key]["device"], "link endpoint.device")
            port(link[key]["interface"])


def canonical(data):
    result = json.loads(json_bytes(data))
    for key in ("sites", "vrfs", "segments", "devices", "links"):
        result[key].sort(key=lambda obj: obj["id"])
    for device in result["devices"]:
        device["interfaces"].sort(key=lambda obj: obj["name"])
    for link in result["links"]:
        link["a"], link["b"] = sorted(
            (link["a"], link["b"]), key=lambda ep: (ep["device"], ep["interface"])
        )
    return result
