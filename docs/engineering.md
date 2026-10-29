# Engineering behavior

## Validation contract

`ndc validate --input model.json` writes JSON to standard output. `ndc build` compiles reports into a new directory. Exit statuses are **0** for valid models (including warnings), **1** for semantic validation errors, and **2** for unsupported/malformed input, filesystem failures or command usage errors. Human-readable input/file errors go to standard error. Schema errors stop before semantic validation.

| Finding | Meaning |
| --- | --- |
| `DUPLICATE_ID`, `DUPLICATE_INTERFACE` | Ambiguous object/port identity |
| `UNKNOWN_SITE`, `UNKNOWN_VRF`, `UNKNOWN_SEGMENT`, `UNKNOWN_ENDPOINT` | Broken reference |
| `INVALID_CIDR`, `INVALID_ADDRESS` | Unsupported or noncanonical addressing |
| `SUBNET_OVERLAP`, `DUPLICATE_ADDRESS` | Conflicting allocation inside a VRF |
| `ADDRESS_OUTSIDE_SUBNET`, `NETWORK_OR_BROADCAST` | Invalid host assignment |
| `SELF_LINK`, `PORT_REUSE` | Invalid device/port pairing |
| `LINK_SEGMENT_MISMATCH`, `LOOPBACK_LINK` | Incoherent endpoint segments |
| `SEGMENT_CARDINALITY`, `P2P_LINK_REQUIRED` | Missing or excessive assignments/links |
| `DISCONNECTED_TOPOLOGY`, `ISOLATED_DEVICE` | Warnings about the declared physical graph |

Graph warnings are calculated only when there are no errors. They are neither a reachability test nor a statement about routing adjacency: a connected graph can still contain multiple isolated routing domains. Unused site/VRF declarations are permitted. One defect may trigger several related findings; findings are diagnostics, not a root-cause ranking.

## Canonicalization and consistency

Collections are sorted by ID and interfaces by name. Each undirected link's endpoints are ordered by device/interface. Equivalent collection ordering and swapped endpoint order generate byte-identical projections. No timestamps, absolute input paths or environment details are inserted into the compiled artifacts.

The manifest separately records the exact input-byte hash and canonical model hash. Reformatting or reordering input changes the former, but not the canonical model hash or generated tables/diagram. The manifest does not hash itself, and a hash proves content equality only when compared against a trusted value; it is not a signature.

Every table and diagram is projected from the validated model. `addresses.csv` has one row per interface, including unconnected loopbacks; `links.csv` has one row per link with both endpoints. A rejected semantic model emits only `validation.json`, `design.md` and `manifest.json` and has an empty counts object.

## Draw.io rendering

`topology.drawio` is native, uncompressed mxGraph XML. Sites are actual swimlane containers and devices are their child cells. Link edges use the common site as parent for same-site links and the default layer for cross-site links. Labels use HTML escaping followed by XML serialization; there are no imported stencils, scripts or remote image dependencies. The [draw.io XML reference](https://github.com/jgraph/drawio-mcp/blob/main/shared/xml-essentials.md) describes the cell and geometry conventions.

The layout is a deterministic grid, optimized for small designs. Dense, multi-site or highly connected graphs may have overlapping routes or labels and need visual review. Link IDs map to the complete endpoint schedule in `links.csv`; the diagram deliberately does not repeat every address on its canvas. Role colors are display metadata.

The JSON model is the source of truth. Edits made in draw.io are not imported back and disappear on regeneration. For presentation-only adjustments, retain a separate copy and identify it as manually adjusted.

## File lifecycle and failure handling

The output parent must already exist. The requested output directory must not exist; directory creation and exclusive file creation prevent routine overwrites. On POSIX, the directory is created with mode 0700 and files with 0600 (subject to a stricter umask). Permissions are not a substitute for host security and may differ on other platforms.

Artifacts are written sequentially and `manifest.json` is written last. A disk or permission error can leave a partial directory; the process returns 2. This is not an atomic transaction. Before consuming a package, require a parseable manifest, its complete expected file list and matching byte lengths and SHA-256 hashes. A truncated manifest is not a success marker. Build again into a fresh directory after correcting the failure.

## Verification boundaries

The test suite exercises the model, projections, escaping and filesystem behavior. The example runner invokes the installed `ndc` command on seven synthetic models and checks every file hash. CI repeats this on Python 3.11, 3.12 and 3.13. Browser captures document real executions and the native diagram rendering; they do not establish connectivity or platform compatibility. No hardware or EVE-NG deployment is needed to verify this offline compiler.
