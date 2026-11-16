#!/usr/bin/env python3
"""Run MTK wireless framework regressions with native ucode, UCI and filesystem I/O.

Hardware capabilities and daemon replies are fixtures. No radio command is executed.
Usage: test-mtwifi-ucode.py --prefix /path/to/native/ucode/install --output results.json
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / 'package/mtk/applications/mtwifi-scripts'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--output', type=Path)
a = p.parse_args()
a.prefix = a.prefix.resolve()
env = os.environ.copy()
env['LD_LIBRARY_PATH'] = str(a.prefix / 'lib') + ':' + env.get('LD_LIBRARY_PATH', '')
results = []

def record(name, ok, detail=''):
    results.append(dict(name=name, passed=bool(ok), detail=detail))
    if not ok:
        raise AssertionError(f'{name}: {detail}')

with tempfile.TemporaryDirectory(prefix='mtwifi-ucode-') as tmp:
    root = Path(tmp)
    for layer in ('files', 'files-ucode'):
        shutil.copytree(PKG / layer, root, dirs_exist_ok=True)
    for name in ('etc/config', 'var/run', 'sys/class/ieee80211', 'sys/class/net', 'usr/sbin'):
        (root / name).mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / 'package/network/config/netifd/files/lib/netifd/utils.uc', root / 'lib/netifd/utils.uc')
    originals = {}
    for file in root.rglob('*'):
        if not file.is_file() or file.suffix not in ('.uc', '.sh'):
            continue
        text = file.read_text()
        originals[str(file.relative_to(root))] = hashlib.sha256(file.read_bytes()).hexdigest()
        # Redirect only filesystem locations and the UCI cursor's configuration directory.
        text = re.sub(r"(['\"`])(/usr/share/|/usr/sbin/|/etc/|/var/run/|/sys/|/tmp/)",
                      lambda m: m[1] + str(root) + m[2], text)
        text = text.replace('uci.cursor()', f'uci.cursor({json.dumps(str(root / "etc/config"))})')
        file.write_text(text)
    cmd = [str(a.prefix / 'bin/ucode'), '-L', str(a.prefix / 'lib/ucode/*.so'), '-L', str(root / 'usr/share/ucode/*.uc')]
    for rel in originals:
        file = root / rel
        text = file.read_text()
        if file.suffix != '.uc' and not text.startswith('#!/usr/bin/ucode'):
            continue
        proc = subprocess.run([*cmd, '-c,module' if re.search(r'^export\b', text, re.M) else '-c', '-o', str(root / 'syntax.ucb'), str(file)], env=env, text=True, capture_output=True)
        record('syntax:' + rel, proc.returncode == 0, proc.stderr[:2000])
    # All configuration files are real fixtures, including the production L1 alias layout.
    datdir = root / 'etc/wireless/mediatek'
    shutil.copytree(REPO / 'package/mtk/drivers/wifi-profile/files/mt7990', datdir)
    for file in datdir.glob('*.dat'):
        file.write_text(file.read_text().replace('/etc/', str(root) + '/etc/'))
    shutil.copy2(datdir / 'l1profile.dat', root / 'etc/wireless/l1profile.dat')
    (root / 'etc/board.json').write_text('{}')
    (root / 'etc/config/network').write_text("config device\n option name 'br-lan'\n option igmp_snooping '1'\n")
    (root / 'etc/config/wireless').write_text('')
    for idx, name in enumerate(('ra0', 'rai0', 'rax0')):
        d = root / f'sys/class/net/{name}/phy80211'
        d.mkdir(parents=True)
        (d / 'name').write_text(f'phy{idx}')
        d = root / f'sys/class/ieee80211/phy{idx}'
        d.mkdir()
        (d / 'index').write_text(str(idx))
    (root / 'usr/sbin/hostapd').touch()

    def run(code, data=None, args=()):
        f = root / 'case.uc'
        f.write_text(code)
        call = [*cmd]
        if data is not None:
            call += ['-D', 'fixture=' + json.dumps(data)]
        proc = subprocess.run([*call, str(f), *args], env=env, text=True, capture_output=True, timeout=25)
        if proc.returncode:
            raise AssertionError(proc.stderr[:5000])
        return proc.stdout

    preamble = """
import * as fs from 'fs';
import * as dat from 'mtwifi.dat';
import * as cfg from 'mtwifi.cfg';
import * as names from 'mtwifi.ifname';
import * as l1 from 'mtwifi.l1dat';
import { atomic_write, shell_quote } from 'mtwifi.common';
import { validate_profile } from 'mtwifi.validate';
import { validate } from 'wifi.validate';
function check(ok, message) { if (!ok) die(message); };
global.system = () => die('unexpected hardware command');
global.ubus = { call: () => ({ pid: 1234 }) };
"""
    aliases = json.loads(run(preamble + 'printf("%J", l1.list(l1.load_cached()));'))
    record('L1:deduplicate-three-band-alias', aliases == ['MT7990_1_1', 'MT7990_1_2', 'MT7990_2'], str(aliases))
    record('DAT:missing-profile', run(preamble + 'printf("%J", dat.load_profile(ARGV[0]));', args=(str(root / 'missing.dat'),)) == 'null')
    code = preamble + '''
check(atomic_write(ARGV[0], 'Default\nSSID1=  spaced SSID  \nWHNAT=0\nWHNAT=1\n'), 'create');
check(dat.save_profile({ WHNAT: '0', SSID1: '  spaced SSID  ' }, ARGV[0]), 'save');
let text = fs.readfile(ARGV[0]);
check(!match(text, /WHNAT=1/), 'duplicate stale value');
check(dat.load_profile(ARGV[0]).SSID1 == '  spaced SSID  ', 'SSID whitespace');
check((fs.stat(ARGV[0]).mode & 0777) == 0600, 'credential permissions');
check(dat.token_set(';second', 1, 'first') == 'first;second', 'token slots');
check(dat.token_set('', 2, 'second') == ';second', 'token gap');
print('ok');
'''
    record('DAT:atomic-permissions-duplicates-token-slots', run(code, args=(str(root / 'test.dat'),)) == 'ok')
    mapping = root / 'var/run/wps-map'
    mapping.write_text('ra0 a\nrai0 b\nrax0 c\napcli0 d\napclii0 e\n')
    code = preamble + '''
let dev = l1.load_cached()[l1.DEV_RINDEX].MT7990_1_1;
check(names.remove_wps_map(dev, ARGV[0]), 'save map');
let m = names.read_wps_map(ARGV[0]);
check(!m.ra0 && !m.apcli0 && m.rai0 == 'b' && m.rax0 == 'c' && m.apclii0 == 'e', 'sibling map');
print('ok');
'''
    record('WPS:radio-prefix-isolation', run(code, args=(str(mapping),)) == 'ok')

    def payload(band='5g', mode='EHT80', enc='sae'):
        idx = {'2g': 0, '5g': 1, '6g': 2}[band]
        return dict(phy=f'phy{idx}', phy_suffix='', vif_phy_suffix='', ifname_prefix=f'phy{idx}-', config=dict(band=band, htmode=mode, channel={'2g': 6, '5g': 36, '6g': 37}[band], country='CN', phy=f'phy{idx}', dbdc_main=False, whnat=True), interfaces={'00': dict(name='fixture_ap', config=dict(mode='ap', ssid='Cloud validation', encryption=enc, key='validation-only-123', ifname=('ra0', 'rai0', 'rax0')[idx]))})

    normalize = '''
let d = fixture;
let vendor = { dbdc_main: d.config.dbdc_main, whnat: d.config.whnat };
delete d.config.dbdc_main; delete d.config.whnat;
validate('device', d.config);
d.config = { ...d.config, ...vendor };
validate_profile(d);
for (let _, i in d.interfaces) validate('iface', i.config);
'''
    valid = [('2g', m) for m in ('HT20', 'HT40', 'HE20', 'HE40', 'EHT20', 'EHT40')] + [('5g', m) for m in ('VHT20', 'VHT40', 'VHT80', 'VHT160', 'HE20', 'HE40', 'HE80', 'HE160', 'EHT20', 'EHT40', 'EHT80', 'EHT160')] + [('6g', m) for m in ('HE20', 'HE40', 'HE80', 'HE160', 'EHT20', 'EHT40', 'EHT80', 'EHT160', 'EHT320', 'EHT320-1', 'EHT320-2')]
    for band, width in valid:
        data = payload(band, width)
        dev = {'2g': 'MT7990_1_1', '5g': 'MT7990_1_2', '6g': 'MT7990_2'}[band]
        code = preamble + normalize + f'''
let plan = cfg.prepare_dat('{dev}', d);
check(plan.ok, 'profile generation');
check(plan.dats.SSID1 == d.interfaces['00'].config.ssid, 'SSID');
check(plan.dats.WPAPSK1 == d.interfaces['00'].config.key, 'key');
print('ok');
'''
        before = {f: f.read_bytes() for f in datdir.glob('*.dat')}
        response = run(code, data)
        changed = [f.name for f, b in before.items() if f.read_bytes() != b]
        record(f'profile:{band}:{width}', response == 'ok' and not changed, f'output={response!r}, changed={changed}')
    # Only the hardware capability query is replaced; execute the actual AP generator.
    (root / 'usr/share/ucode/mtwifi/caps.uc').write_text("""
export function device_capabilities(config) {
 return { ht_capa: 65535, vht_capa: 4294967295,
 he_phy_cap: [255,255,255,255,255,255,255,255], he_mac_cap: [255,255],
 eht_phy_cap: [255,255,255,255,255,255,255,255],
 features: { ftm_responder: true, radar_background: false, cipher_gcmp256: true } };
};
""")
    for band, width in valid:
        code = preamble + "import * as ap from 'mtwifi.hostapd';\n" + normalize + """
let plan = ap.prepare(d);
check(plan.ok, 'AP plan');
check(index(plan.text, 'driver=nl80211\\n') >= 0, 'driver');
check(index(plan.text, 'interface=' + d.interfaces['00'].config.ifname) >= 0, 'AP interface');
check(index(plan.text, 'use_driver_iface_addr=1') >= 0, 'driver BSSID');
check(!fs.stat(plan.file), 'prepare wrote live config');
if (d.config.band == '6g') check(index(plan.text, 'ieee80211w=2') >= 0, '6GHz PMF');
print('ok');
"""
        record(f'hostapd:{band}:{width}', run(code, payload(band, width)).endswith('ok'))
    code = preamble + "import * as ap from 'mtwifi.hostapd';\n" + normalize + """
let plan = ap.prepare(d);
let old = 'interface=rai0\\nssid=old\\n';
atomic_write(plan.file, old);
plan.previous = old;
global.ubus.call = (object, method, data) => method == 'config_add' ? null : {};
check(!ap.activate(plan), 'rejected AP must fail');
check(fs.readfile(plan.file) == old, 'restore last AP config');
fs.unlink(plan.file);
print('ok');
"""
    record('hostapd:failed-attach-restores-config', run(code, payload()).endswith('ok'))
    bad = []
    for band, width, enc in [('2g', 'EHT80', 'sae'), ('5g', 'EHT320', 'sae'), ('6g', 'VHT80', 'sae'), ('6g', 'EHT80', 'none'), ('6g', 'EHT80', 'psk2')]:
        bad.append(payload(band, width, enc))
    for key, val in [('ssid', 'injected\nAuthMode=OPEN'), ('key', 'short'), ('ifname', '../../bad')]:
        data = payload(enc='psk2');data['interfaces']['00']['config'][key] = val;bad.append(data)
    for idx, data in enumerate(bad):
        code = preamble + '''let rejected = false; try { ''' + normalize + ''' } catch(e) { rejected = true; };check(rejected, 'must reject invalid config');print('ok');'''
        record(f'validation:reject:{idx}', run(code, data) == 'ok')
    code = preamble + normalize + '''
let plan = cfg.prepare_dat('MT7990_1_2', d);
check(plan.ok && length(plan.files), 'transaction plan');
let originals = map(plan.files, f => fs.readfile(f.path));
check(cfg.commit_dat(plan), 'commit');
check(cfg.rollback_dat(plan), 'rollback');
for (let i, f in plan.files) check(fs.readfile(f.path) == originals[i], 'rollback contents');
push(plan.files, { path: ARGV[0] + '/missing-parent/data', previous: 'old', text: 'new' });
check(!cfg.commit_dat(plan), 'partial failure');
for (let i, f in plan.files) if (i < length(originals)) check(fs.readfile(f.path) == originals[i], 'partial rollback contents');
print('ok');
'''
    record('transaction:commit-rollback-partial-write-failure', run(code, payload(), (str(root),)) == 'ok')
    # Exercise real POSIX locking and automatic release when a process exits.
    code = preamble + "let f = fs.open(ARGV[0], 'ae', 0600);check(f.lock('xn'), 'lock released');print('ok');"
    lock = str(root / 'var/run/test.lock')
    record('transaction:process-exit-releases-lock', run(code, args=(lock,)) == 'ok' and run(code, args=(lock,)) == 'ok')

    # Exercise the real netifd handler with recorded ubus replies and no hardware commands.
    handler = root / 'lib/netifd/wireless/mtwifi.sh'
    text = handler.read_text()
    hook = f"""
let calls = [];
let scenario = json(fs.readfile('{root}/scenario.json'));
global.ubus = {{ call: (object, method, data) => {{
 push(calls, {{object, method, data}});
 fs.writefile('{root}/trace.json', sprintf('%J', calls));
 if (method == 'config_add') return scenario.reject_ap ? null : {{ pid: 1234 }};
 return {{}};
}} }};
global.system = (cmd) => die('unexpected hardware command');
"""
    handler.write_text(text.replace('global.radio = ARGV[2];', hook + '\nglobal.radio = ARGV[2];'))

    def handle(data, reject=False):
        (root / 'scenario.json').write_text(json.dumps(dict(reject_ap=reject)))
        (root / 'trace.json').write_text('[]')
        proc = subprocess.run([*cmd, str(handler), 'mtwifi', 'setup', 'MT7990_1_2', json.dumps(data)], env=env, capture_output=True, text=True, timeout=25)
        calls = json.loads((root / 'trace.json').read_text())
        ups = [c for c in calls if c['object'] == 'network.wireless' and c['data'].get('command') == 0]
        return proc, calls, ups

    before = {f: f.read_bytes() for f in datdir.glob('*.dat')}
    proc, calls, ups = handle(payload(), reject=True)
    record('handler:failed-attach-no-up-and-restored-profiles', proc.returncode != 0 and not ups and any(c['method'] == 'config_add' for c in calls) and all(f.read_bytes() == b for f, b in before.items()), proc.stderr[:1500])
    proc, calls, ups = handle(payload())
    record('handler:one-up-after-successful-attach', proc.returncode == 0 and len(ups) == 1, proc.stderr[:1500])
    proc, calls, ups = handle(payload())
    record('handler:identical-reload', proc.returncode == 0 and len(ups) == 1, proc.stderr[:1500])
    data = payload();data['interfaces']['01'] = dict(name='second_ap', config=dict(mode='ap', ssid='Second AP', encryption='sae', key='validation-only-123', ifname='rai1'))
    before = {f: f.read_bytes() for f in datdir.glob('*.dat')}
    proc, calls, ups = handle(data)
    record('handler:structural-change-keeps-profiles-and-driver', proc.returncode != 0 and not ups and all(f.read_bytes() == b for f, b in before.items()), proc.stderr[:1500])

    # Metadata migration must leave all existing wireless settings intact and be idempotent.
    config = root / 'etc/config/wireless'
    config.write_text("""config wifi-device 'MT7990_1_1'
 option type 'mtwifi'
 option band '2g'
 option htmode 'EHT40'
 option channel '9'
 option country 'CN'
 option whnat '0'
config wifi-iface 'default_MT7990_1_1'
 option device 'MT7990_1_1'
 option mode 'ap'
 option ssid 'Existing SSID'
 option encryption 'sae'
 option key 'existing-validation-only'
""")
    detect = root / 'lib/wifi/mtwifi.uc'
    proc = subprocess.run([*cmd, str(detect)], env=env, text=True, capture_output=True, check=True)
    subprocess.run([str(a.prefix / 'bin/uci'), '-c', str(root / 'etc/config'), 'batch'], input=proc.stdout, env=env, text=True, capture_output=True, check=True)
    migrated = config.read_text()
    record('detect:preserve-wireless-settings', all(v in migrated for v in ["'Existing SSID'", "'existing-validation-only'", "'9'", "'sae'", "'EHT40'"]) and 'default_MT7990_1_1' in migrated)
    again = subprocess.run([*cmd, str(detect)], env=env, text=True, capture_output=True, check=True)
    record('detect:idempotent', not again.stdout.strip(), again.stdout[:500])
    record('detect:no-duplicate-6GHz-alias', 'MT7990_1_3' not in migrated)

report = dict(passed=sum(t['passed'] for t in results), total=len(results), tests=results,
              scope='Native ucode/UCI/filesystem; radio capabilities and daemon replies require hardware integration tests.')
if a.output:
    a.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print(f"PASS {report['passed']}/{report['total']} MTK wireless framework checks")
