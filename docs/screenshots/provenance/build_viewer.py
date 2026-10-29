from pathlib import Path
import csv,json,html
p=Path(__file__).resolve().parent.parent
metadata=json.loads((p/'manifest.json').read_text())
commit_short=metadata['commit'][:7]
h=html.escape
read=lambda f:(p/f).read_text()
def table(file,cols,filterfn=None):
 rows=list(csv.DictReader((p/file).open()))
 if filterfn: rows=[r for r in rows if filterfn(r)]
 return '<table><thead><tr>'+''.join('<th>'+h(c)+'</th>' for c in cols)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+h(r[c])+'</td>' for c in cols)+'</tr>' for r in rows)+'</tbody></table>'
def pre(file): return '<pre>'+h(read(file))+'</pre>'
def section(title,body):return '<section><h2>'+h(title)+'</h2>'+body+'</section>'
def page(name,kicker,title,body):
 css='''*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:#152a38;font:14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{padding:26px 32px;max-width:1600px;margin:auto}header{border-bottom:2px solid #235c72;padding-bottom:14px;margin-bottom:16px}.kicker{font-size:11px;letter-spacing:1.7px;font-weight:700;color:#376479}h1{font-size:28px;margin:7px 0}header p{margin:0;color:#51616b;font-size:12px}section{background:white;border:1px solid #d7e0e6;margin:12px 0;padding:14px 16px}h2{font-size:14px;margin:0 0 10px;color:#235c72}table{width:100%;border-collapse:collapse;text-align:left;font:12px ui-monospace,SFMono-Regular,Consolas,monospace}th{color:#44606f;font-size:11px;background:#f1f5f7}th,td{padding:7px 6px;border-bottom:1px solid #e6ecef;white-space:nowrap}tr:last-child td{border:0}pre{font:14px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre-wrap;margin:0;color:#172c3a}.grid{display:grid;grid-template-columns:1.25fr 1fr;gap:16px}.grid section{margin-top:0}footer{font-size:11px;color:#556975;line-height:1.6;margin-top:14px}.note{font-size:13px;line-height:1.6}.status{display:inline-block;border:1px solid #9fb9b1;color:#24604f;background:#edf6f1;padding:5px 10px;font-size:12px;margin:4px 0 8px}.reject{color:#9a3434;background:#fff0ee;border-color:#dbb0a8}'''
 text='<!doctype html><html lang="en"><meta charset="utf-8"><title>'+h(title)+' | Evidence viewer</title><style>'+css+'</style><main><header><div class="kicker">NETWORK DESIGN COMPILER / '+h(kicker)+'</div><h1>'+h(title)+'</h1><p>Static evidence viewer · Not product UI · v0.1.0 · commit '+commit_short+' · 2026-10-29</p></header>'+body+'<footer>Scope: offline-design-consistency · Public synthetic examples · No discovery, deployment, routing simulation or verified connectivity.<br>Values and logs reproduced from generated files; source paths are relative to this evidence package.</footer></main></html>'
 (p/'viewer'/name).write_text(text)
a=list(csv.DictReader((p/'outputs/two-site/addresses.csv').open())); links=list(csv.DictReader((p/'outputs/two-site/links.csv').open())); lookup={(r['device'],r['interface']):r for r in a}
for l in links:
 for end,other in [('a','b'),('b','a')]:
  r=lookup[(l[end+'_device'],l[end+'_interface'])]
  assert r['address']==l[end+'_address'] and r['link']==l['id'] and r['cidr']==l['cidr']
  assert r['peer_device']==l[other+'_device'] and r['peer_interface']==l[other+'_interface']
counts=json.loads(read('outputs/two-site/manifest.json'))['counts']
assert counts==dict(devices=4,interfaces=10,links=3,segments=7,sites=2,vrfs=1)
rej=sorted(f.name for f in (p/'outputs/invalid-duplicate-ip').iterdir())
assert rej==['design.md','manifest.json','validation.json']
(p/'logs/cross-artifact-check.log').write_text('PASS counts: 2 sites / 4 devices / 10 interfaces / 3 links\nPASS all 6 link endpoints agree with addresses.csv (address, link, prefix, peer)\nPASS duplicate-address rejection emits exactly 3 report files\n')
(p/'logs/rejected-files.log').write_text('outputs/invalid-duplicate-ip/\n'+''.join('  '+f+'\n' for f in rej)+'\nFile count: '+str(len(rej))+'\nOperational artifact count: 0\n')
page('02-ip-and-ports.html','02 / SHARED MODEL','One model, matching addresses and ports', '<span class="status">2 sites · 4 devices · 10 interfaces · 3 links · 1 VRF · 7 segments</span>'+section('outputs/two-site/addresses.csv · selected columns, all 10 rows',table('outputs/two-site/addresses.csv',['device','interface','site','vrf','cidr','address','link']))+section('outputs/two-site/links.csv · selected columns, all 3 rows',table('outputs/two-site/links.csv',['id','a_device','a_interface','a_address','b_device','b_interface','b_address'])) )
page('03-duplicate-rejected.html','03 / REJECTED DESIGN','Duplicate address: generation stops',section('Actual CLI output · outputs/invalid-duplicate-ip.log',pre('outputs/invalid-duplicate-ip.log'))+'<div class="grid">'+section('outputs/invalid-duplicate-ip/validation.json',pre('outputs/invalid-duplicate-ip/validation.json'))+section('Observed output directory · logs/rejected-files.log',pre('logs/rejected-files.log')+'<p class="note">Only the validation report, failure report and manifest were emitted. No topology, addressing table, link schedule or canonical model was produced.</p>')+'</div>')
page('04-valid-31.html','04 / VALID EDGE CASE','Both /31 endpoint addresses are accepted',section('Actual CLI output · outputs/p2p-31.log',pre('outputs/p2p-31.log'))+section('outputs/p2p-31/addresses.csv · selected columns; segment = wan (2 of 10 rows)',table('outputs/p2p-31/addresses.csv',['device','interface','segment','vrf','cidr','address','peer_device','peer_interface'],lambda r:r['segment']=='wan'))+section('outputs/p2p-31/validation.json',pre('outputs/p2p-31/validation.json'))+'<p class="note">This proves model validation for the synthetic /31 case. Device support and live forwarding require independent review.</p>')
page('05-verification.html','05 / REPRODUCIBLE CHECKS','107 tests. Seven CLI scenarios.',section('logs/pytest.log · .venv/bin/python -m pytest -q -p no:cacheprovider',pre('logs/pytest.log'))+section('logs/scenarios.log · .venv/bin/python scripts/check_examples.py --output <fresh-directory>',pre('logs/scenarios.log'))+section('logs/cross-artifact-check.log · additional evidence checks',pre('logs/cross-artifact-check.log')))
print('Viewer generated; cross-artifact checks passed.')
