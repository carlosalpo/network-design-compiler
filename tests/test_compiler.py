import copy
import csv
import io
import json
import os
import socket
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from netdesign.cli import main
from netdesign.model import MAX_BYTES, InputError, canonical, check_shape, digest, json_bytes, load
from netdesign.render import compile_design
from netdesign.validation import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def model():
    return json.loads((ROOT / "examples/two-site.json").read_text())


def codes(data):
    return {f["code"] for f in validate(data)["findings"]}


def device(data, identifier="hq-edge"):
    return next(d for d in data["devices"] if d["id"] == identifier)


def interface(data, name="Ethernet1", identifier="hq-edge"):
    return next(p for p in device(data, identifier)["interfaces"] if p["name"] == name)


def segment(data, identifier="wan"):
    return next(s for s in data["segments"] if s["id"] == identifier)


@pytest.mark.parametrize(
    "example,expected",
    [
        ("two-site", set()),
        ("p2p-31", set()),
        ("invalid-duplicate-ip", {"DUPLICATE_ADDRESS"}),
        ("invalid-overlap", {"SUBNET_OVERLAP"}),
        ("invalid-endpoint", {"UNKNOWN_ENDPOINT"}),
        ("invalid-port-reuse", {"PORT_REUSE"}),
        ("disconnected", {"DISCONNECTED_TOPOLOGY"}),
    ],
)
def test_examples(example, expected):
    data, _ = load(ROOT / f"examples/{example}.json")
    assert expected <= codes(data)
    assert validate(data)["valid"] == (not example.startswith("invalid-"))


@pytest.mark.parametrize("collection", ["sites", "vrfs", "segments", "devices", "links"])
def test_duplicate_ids(model, collection):
    model[collection].append(copy.deepcopy(model[collection][0]))
    assert "DUPLICATE_ID" in codes(model)


@pytest.mark.parametrize("value", [True, False, 1.0, "1", 2, None])
def test_schema_version_strict(model, value):
    model["schema_version"] = value
    with pytest.raises(InputError):
        check_shape(model)


@pytest.mark.parametrize("value", [True, 0, -1, 800001, 1.5, "1000", None])
def test_speed_bounds(model, value):
    model["links"][0]["speed_mbps"] = value
    with pytest.raises(InputError):
        check_shape(model)


@pytest.mark.parametrize("value", ["", "a\nb", "\x1b[31m", "x" * 161, None, 42])
def test_title_bounds(model, value):
    model["title"] = value
    with pytest.raises(InputError):
        check_shape(model)


@pytest.mark.parametrize("value", ["", "Eth 1", "Eth`", "Eth\n", "a" * 49, "=formula", 1])
def test_port_names(model, value):
    interface(model)["name"] = value
    with pytest.raises(InputError):
        check_shape(model)


@pytest.mark.parametrize(
    "collection,maximum",
    [("sites", 8), ("vrfs", 32), ("segments", 256), ("devices", 64), ("links", 128)],
)
def test_collection_limits(model, collection, maximum):
    model[collection] = [model[collection][0]] * (maximum + 1)
    with pytest.raises(InputError):
        check_shape(model)


@pytest.mark.parametrize("collection", ["sites", "vrfs", "segments", "devices"])
def test_required_nonempty(model, collection):
    model[collection] = []
    with pytest.raises(InputError):
        check_shape(model)


def test_interface_limits(model):
    device(model)["interfaces"] *= 11
    with pytest.raises(InputError):
        check_shape(model)
    model["devices"] = [device(model)] * 64
    device(model)["interfaces"] = device(model)["interfaces"][:5]
    with pytest.raises(InputError):
        check_shape(model)


@pytest.mark.parametrize("location", ["top", "site", "device", "interface", "link", "endpoint"])
def test_unknown_fields(model, location):
    target = {
        "top": model,
        "site": model["sites"][0],
        "device": device(model),
        "interface": interface(model),
        "link": model["links"][0],
        "endpoint": model["links"][0]["a"],
    }[location]
    target["unexpected"] = "no"
    with pytest.raises(InputError):
        check_shape(model)


@pytest.mark.parametrize(
    "address,code",
    [
        ("192.0.2.0", "NETWORK_OR_BROADCAST"),
        ("192.0.2.3", "NETWORK_OR_BROADCAST"),
        ("192.0.2.5", "ADDRESS_OUTSIDE_SUBNET"),
        ("224.0.0.1", "INVALID_ADDRESS"),
        ("0.1.2.3", "INVALID_ADDRESS"),
        ("127.0.0.1", "INVALID_ADDRESS"),
        ("169.254.1.1", "INVALID_ADDRESS"),
        ("240.0.0.1", "INVALID_ADDRESS"),
        ("192.000.2.1", "INVALID_ADDRESS"),
        ("::1", "INVALID_ADDRESS"),
    ],
)
def test_addresses(model, address, code):
    interface(model)["address"] = address
    assert code in codes(model)


@pytest.mark.parametrize(
    "cidr",
    [
        "192.0.2.5/30",
        "192.0.2.0/24",
        "192.0.2.4/32",
        "224.0.0.0/30",
        "0.0.0.0/30",
        "::/31",
        "broken",
    ],
)
def test_invalid_p2p_networks(model, cidr):
    segment(model)["cidr"] = cidr
    assert "INVALID_CIDR" in codes(model)


def test_loopback_prefix(model):
    next(s for s in model["segments"] if s["kind"] == "loopback")["cidr"] = "198.51.100.0/30"
    assert "INVALID_CIDR" in codes(model)


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda m: segment(m).update(vrf="missing"), "UNKNOWN_VRF"),
        (lambda m: device(m).update(site="missing"), "UNKNOWN_SITE"),
        (lambda m: interface(m).update(segment="missing"), "UNKNOWN_SEGMENT"),
        (
            lambda m: device(m)["interfaces"].append(copy.deepcopy(interface(m))),
            "DUPLICATE_INTERFACE",
        ),
        (lambda m: m["links"][0]["a"].update(device="missing"), "UNKNOWN_ENDPOINT"),
        (lambda m: m["links"][0].update(b=copy.deepcopy(m["links"][0]["a"])), "SELF_LINK"),
        (lambda m: m["links"].pop(), "P2P_LINK_REQUIRED"),
        (lambda m: interface(m).update(segment="wan"), "LINK_SEGMENT_MISMATCH"),
        (lambda m: device(m)["interfaces"].remove(interface(m)), "SEGMENT_CARDINALITY"),
    ],
)
def test_semantics(model, mutation, code):
    mutation(model)
    assert code in codes(model)


def test_loopback_link_rejected(model):
    model["links"][0]["a"] = {"device": "hq-core", "interface": "Loopback0"}
    model["links"][0]["b"] = {"device": "hq-core", "interface": "Loopback0"}
    assert "LOOPBACK_LINK" in codes(model)


def test_repeated_prefix_and_ip_allowed_across_vrfs(model):
    model["vrfs"].append({"id": "tenant-b", "label": "Tenant B"})
    target = segment(model, "branch-transit")
    target.update(vrf="tenant-b", cidr="192.0.2.0/30")
    interface(model, "Ethernet2", "branch-edge")["address"] = "192.0.2.1"
    interface(model, "Ethernet1", "branch-core")["address"] = "192.0.2.2"
    assert validate(model)["valid"]
    target["vrf"] = "production"
    assert {"SUBNET_OVERLAP", "DUPLICATE_ADDRESS"} <= codes(model)


def test_isolated_loopback_only_node(model):
    node = device(model, "hq-core")
    model["devices"] = [node]
    node["interfaces"] = [p for p in node["interfaces"] if p["name"] == "Loopback0"]
    model["segments"] = [
        s for s in model["segments"] if s["id"] == node["interfaces"][0]["segment"]
    ]
    model["links"] = []
    result = validate(model)
    assert result["valid"] and codes(model) == {"ISOLATED_DEVICE"}


@pytest.mark.parametrize(
    "raw",
    [
        b'{"id":1,"id":2}',
        b"NaN",
        b"{",
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"[" * 2000 + b"]" * 2000,
        b" " * (MAX_BYTES + 1),
    ],
)
def test_loader_rejects_bad_bytes(tmp_path, raw):
    path = tmp_path / "input.json"
    path.write_bytes(raw)
    with pytest.raises(InputError):
        load(path)


def test_load_preserves_exact_source_hash(tmp_path, model):
    raw = json.dumps(model).encode()
    path = tmp_path / "input.json"
    path.write_bytes(raw)
    loaded, source_hash = load(path)
    assert loaded == canonical(model)
    assert source_hash == digest(raw)


def test_deterministic_reordered_model(model):
    changed = copy.deepcopy(model)
    for key in ("sites", "vrfs", "segments", "devices", "links"):
        changed[key].reverse()
    for d in changed["devices"]:
        d["interfaces"].reverse()
    for link in changed["links"]:
        link["a"], link["b"] = link["b"], link["a"]
    first, _ = compile_design(model, "same-source")
    second, _ = compile_design(changed, "same-source")
    assert first == second
    third, _ = compile_design(changed, "different-source")
    assert {k: v for k, v in first.items() if k != "manifest.json"} == {
        k: v for k, v in third.items() if k != "manifest.json"
    }


def test_projections_and_manifest(model):
    files, result = compile_design(model, digest(json_bytes(model)))
    assert result["valid"] and len(files) == 8
    manifest = json.loads(files["manifest.json"])
    assert manifest["counts"] == dict(
        sites=2, vrfs=1, devices=4, interfaces=10, segments=7, links=3
    )
    assert set(manifest["files"]) == set(files) - {"manifest.json"}
    for name, item in manifest["files"].items():
        assert item == {"bytes": len(files[name]), "sha256": digest(files[name])}
    rows = list(csv.DictReader(io.StringIO(files["addresses.csv"].decode())))
    assert len(rows) == 10
    by_port = {(r["device"], r["interface"]): r for r in rows}
    for row in rows:
        if row["kind"] == "loopback":
            assert not row["link"] and not row["peer_device"]
        else:
            peer = by_port[(row["peer_device"], row["peer_interface"])]
            assert peer["peer_device"] == row["device"]
            assert peer["peer_interface"] == row["interface"]
            assert peer["segment"] == row["segment"] and peer["link"] == row["link"]
    assert len(list(csv.DictReader(io.StringIO(files["links.csv"].decode())))) == 3


def test_native_drawio_structure(model):
    files, _ = compile_design(model, "source")
    root = ET.fromstring(files["topology.drawio"])
    cells = root.findall(".//mxCell")
    by_id = {c.get("id"): c for c in cells}
    assert len(cells) == len(by_id)
    assert by_id["1"].get("parent") == "0"
    assert sum(c.get("edge") == "1" for c in cells) == 3
    for cell in cells:
        if cell.get("id") not in ("0", "1"):
            assert cell.get("parent") in by_id
            assert cell.find("mxGeometry") is not None
        if cell.get("edge"):
            assert cell.get("source") in by_id and cell.get("target") in by_id
            assert cell.find("mxGeometry").get("relative") == "1"
    assert by_id["link-wan"].get("parent") == "1"
    assert by_id["link-hq-transit"].get("parent") == "site-hq"
    assert by_id["device-hq-edge"].get("parent") == "site-hq"
    assert b"<!--" not in files["topology.drawio"]


def test_untrusted_labels_are_escaped(model):
    model["title"] = "<img src=x onerror=alert(1)> & stuff"
    model["sites"][0]["label"] = "<script>alert(1)</script>"
    device(model)["label"] = '=HYPERLINK("https://example.com")'
    files, _ = compile_design(model, "source")
    assert b"<img" not in files["design.md"]
    root = ET.fromstring(files["topology.drawio"])
    heading = root.find('.//mxCell[@id="heading"]').get("value")
    assert "<img" not in heading and "&lt;img" in heading
    devices = list(csv.DictReader(io.StringIO(files["devices.csv"].decode())))
    assert next(d for d in devices if d["id"] == "hq-edge")["label"].startswith("'=")


def test_invalid_output_contains_only_reports(model):
    interface(model)["address"] = "192.0.2.1"
    files, result = compile_design(model, "source")
    assert not result["valid"]
    assert set(files) == {"validation.json", "design.md", "manifest.json"}
    assert json.loads(files["manifest.json"])["counts"] == {}


def test_no_network_required(model, monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("Compilation attempted network access")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    assert compile_design(model, "source")[1]["valid"]


@pytest.mark.parametrize(
    "example,expected", [("two-site", 0), ("disconnected", 0), ("invalid-duplicate-ip", 1)]
)
def test_cli_build_and_validate(tmp_path, capsys, example, expected):
    source = str(ROOT / f"examples/{example}.json")
    assert main(["validate", "--input", source]) == expected
    validation = json.loads(capsys.readouterr().out)
    assert validation["valid"] == (expected == 0)
    output = tmp_path / "output"
    assert main(["build", "--input", source, "--output", str(output)]) == expected
    assert json.loads((output / "manifest.json").read_text())["result"] == (
        "valid-model" if expected == 0 else "invalid-model"
    )
    if os.name == "posix":
        assert output.stat().st_mode & 0o077 == 0
        assert all(p.stat().st_mode & 0o077 == 0 for p in output.iterdir())


def test_existing_output_untouched(tmp_path):
    marker = tmp_path / "keep.txt"
    marker.write_text("keep")
    assert (
        main(["build", "--input", str(ROOT / "examples/two-site.json"), "--output", str(tmp_path)])
        == 2
    )
    assert list(tmp_path.iterdir()) == [marker] and marker.read_text() == "keep"


@pytest.mark.parametrize("raw", ["{}", "{", '{"schema_version":true}'])
def test_bad_input_does_not_create_output(tmp_path, raw):
    source = tmp_path / "input.json"
    source.write_text(raw)
    output = tmp_path / "new"
    assert main(["build", "--input", str(source), "--output", str(output)]) == 2
    assert not output.exists()


def test_missing_input(tmp_path):
    assert main(["validate", "--input", str(tmp_path / "absent")]) == 2


def test_write_failure_has_no_complete_manifest(tmp_path, monkeypatch):
    real_open = os.open

    def interrupted(path, *args, **kwargs):
        if Path(path).name == "topology.drawio":
            raise OSError("simulated disk failure")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", interrupted)
    output = tmp_path / "new"
    assert (
        main(["build", "--input", str(ROOT / "examples/two-site.json"), "--output", str(output)])
        == 2
    )
    assert output.exists() and not (output / "manifest.json").exists()
