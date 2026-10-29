# Captions and alt text

## 01 — Native topology (portfolio selection 1)

**EN:** Native editable topology generated from one declared network model and rendered in draw.io: two sites, four devices and three declared links. This represents design intent, not verified connectivity.

**ES:** Topología editable generada desde un único modelo declarado y renderizada en draw.io: dos sitios, cuatro equipos y tres enlaces declarados. Representa intención de diseño, no conectividad comprobada.

**Alt:** draw.io editor showing Branch and Headquarters, with branch-core, branch-edge, hq-edge and hq-core connected by branch-transit, wan and hq-transit.

## 02 — IP plan and port schedule

**EN:** Ten interface assignments and three port-to-port links derived from the same validated model. All six link endpoints were checked against the address table. Static evidence viewer, not product UI.

**ES:** Diez asignaciones de interfaz y tres enlaces entre puertos derivados del mismo modelo validado. Los seis extremos coinciden con la tabla IP. Visor estático de evidencia, no interfaz del producto.

**Alt:** Tables listing all ten interface addresses and all three links for the two-site reference model, with selected CSV columns.

## 03 — Duplicate rejection (portfolio selection 2)

**EN:** A duplicate IPv4 address is rejected with `DUPLICATE_ADDRESS` and exit code 1. Only validation, failure report and manifest are emitted; no topology or addressing tables are generated. Static evidence viewer, not product UI.

**ES:** Una IPv4 duplicada se rechaza con `DUPLICATE_ADDRESS` y código de salida 1. Solo se emiten validación, informe de fallo y manifiesto; no se genera topología ni tablas de direccionamiento. Visor estático de evidencia, no interfaz del producto.

**Alt:** Actual rejected-build output, duplicate-address validation JSON and the three observed report filenames.

## 04 — Valid /31

**EN:** The synthetic WAN `/31` accepts both endpoint addresses, `192.0.2.4` and `192.0.2.5`, with no findings. This validates the declared model, not hardware support or forwarding. Static evidence viewer, not product UI.

**ES:** El enlace WAN sintético `/31` acepta ambas direcciones, `192.0.2.4` y `192.0.2.5`, sin hallazgos. Valida el modelo declarado, no compatibilidad de equipos ni reenvío real. Visor estático de evidencia, no interfaz del producto.

**Alt:** Two WAN interface rows in the 192.0.2.4/31 subnet and a validation report with valid true.

## 05 — Verification

**EN:** Fresh local execution: 107 tests passed and seven CLI scenarios passed, with every generated artifact hash verified. Additional checks confirm counts, endpoint consistency and report-only rejection. Static evidence viewer, not product UI.

**ES:** Ejecución local nueva: 107 tests y siete escenarios CLI aprobados, con verificación de cada hash generado. Comprobaciones adicionales confirman conteos, coherencia de extremos y rechazo que emite solo informes. Visor estático de evidencia, no interfaz del producto.

**Alt:** Real pytest and seven-case CLI logs, plus three successful evidence checks.
