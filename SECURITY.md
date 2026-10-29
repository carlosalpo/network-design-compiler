# Security and privacy

This is an offline design compiler. The runtime uses only Python's standard library and does not open network connections, execute shell commands, log in to devices, or read credentials. Package installation and CI may access dependency registries; the example runner executes the installed local CLI.

The JSON input is bounded, strictly shaped and rejects duplicate keys. No Python expressions, templates, YAML constructors or external XML entities are evaluated. Output filenames are fixed. Printable labels are escaped for Markdown and draw.io XML/HTML. CSV cells beginning with a formula marker after leading whitespace receive a leading apostrophe; spreadsheet handling varies, so import them as data. Device IDs and interface names use restricted character sets.

Compilation is **not anonymization**. Generated files retain supplied design names, addresses, device labels, site labels and interface information. Never commit client inventories, private diagrams, credentials or sensitive operational details. The included models use synthetic names and documentation ranges. Use a local diagram editor for private inputs; an online draw.io session is a separate service outside this tool's offline boundary.

Output permissions are restrictive on POSIX, but the tool assumes a trusted local filesystem and parent directory. It is not hardened against another user/process racing to replace its output paths. It is not a sandbox for hostile filesystem trees. Hashes detect differences against a trusted reference; they provide neither authentication nor tamper resistance when an attacker can replace both files and manifest.

Report reproducible issues privately through the maintainer's GitHub profile contact options when available. Do not post secrets or real client data in public issues; use synthetic reproductions.
