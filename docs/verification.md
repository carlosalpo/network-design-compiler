# Verification record — v0.1.0

Tested implementation: [`d2503b5fa350d33782a78a429e551e2ba66612f4`](https://github.com/carlosalpo/network-design-compiler/commit/d2503b5fa350d33782a78a429e551e2ba66612f4).

On 2026-10-29, **107 tests and seven CLI scenarios passed**, with Ruff lint and formatting checks, on local Python 3.12 and on GitHub Actions Python 3.11, 3.12 and 3.13. [CI execution](https://github.com/carlosalpo/network-design-compiler/actions/runs/40953663733).

The valid reference generated eight artifacts for 2 sites, 1 VRF, 4 devices, 7 segments, 10 interfaces and 3 link declarations. The `/31` case accepted both endpoint addresses. The disconnected model remained valid with a graph warning. Duplicate-IP, overlap, missing-endpoint and reused-port examples returned exit 1 and emitted only three reporting artifacts. The scenario runner independently verified every package file's recorded size and SHA-256 hash.

The unit tests also cover address reuse across VRFs, canonical ordering, endpoint-order equivalence, reciprocal peer references, XML parent/edge integrity, untrusted label escaping, restrictive POSIX permissions, existing-output preservation and interrupted writes without a completed manifest. Compilation was exercised with Python socket creation and DNS lookup disabled.

These checks verify offline model consistency and document generation. They do not establish device compatibility, routing convergence, forwarding or reachability. Screenshots document observed output and are supplementary evidence; source, tests and raw outputs remain the reproducible basis.

A generated reference package is included as `network-design-compiler-example-v0.1.0.zip` in the release, with its separate `SHA256SUMS`. Its canonical `model.json` is also a valid input for rebuilding. The per-file manifest covers the remaining seven files; neither the manifest nor the release checksum is a cryptographic signature.
