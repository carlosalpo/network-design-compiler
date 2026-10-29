"""Exercise the installed CLI and verify actual artifact hashes and structure."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

CASES = {
    "two-site": (0, None),
    "p2p-31": (0, None),
    "disconnected": (0, "DISCONNECTED_TOPOLOGY"),
    "invalid-duplicate-ip": (1, "DUPLICATE_ADDRESS"),
    "invalid-overlap": (1, "SUBNET_OVERLAP"),
    "invalid-endpoint": (1, "UNKNOWN_ENDPOINT"),
    "invalid-port-reuse": (1, "PORT_REUSE"),
}


def run(output):
    cli = shutil.which("ndc")
    if not cli:
        raise SystemExit("Install the package and activate its environment first.")
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    summary = []
    for name, (expected, code) in CASES.items():
        destination = output / name
        completed = subprocess.run(
            [
                cli,
                "build",
                "--input",
                str(root / f"examples/{name}.json"),
                "--output",
                str(destination),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        (output / f"{name}.log").write_text(
            f"case={name}\nexit={completed.returncode}\n{completed.stdout}{completed.stderr}",
            encoding="utf-8",
        )
        assert completed.returncode == expected, name
        validation = json.loads((destination / "validation.json").read_text())
        assert validation["valid"] == (expected == 0), name
        if code:
            assert code in {f["code"] for f in validation["findings"]}, name
        manifest = json.loads((destination / "manifest.json").read_text())
        assert set(manifest["files"]) == {p.name for p in destination.iterdir()} - {"manifest.json"}
        for filename, metadata in manifest["files"].items():
            raw = (destination / filename).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == metadata["sha256"], (name, filename)
            assert len(raw) == metadata["bytes"], (name, filename)
        if expected == 0:
            diagram = ET.parse(destination / "topology.drawio")
            assert len(diagram.findall('.//mxCell[@edge="1"]')) == manifest["counts"]["links"]
        else:
            assert set(manifest["files"]) == {"validation.json", "design.md"}
        summary.append(
            {
                "case": name,
                "exit_code": completed.returncode,
                "valid": validation["valid"],
                "expected_code": code,
                "artifacts": len(manifest["files"]) + 1,
                "hashes_verified": True,
            }
        )
        print(f"PASS {name}: exit={completed.returncode}, artifacts={len(manifest['files']) + 1}")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{len(summary)} CLI scenarios passed; all artifact hashes verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
