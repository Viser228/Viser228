#!/usr/bin/env python3
"""Package manually tested only MT7601U candidate if Wi-Fi CRC checks pass.

WARNING: CRC checks are necessary but not sufficient for runtime CFI safety.
No boot scripts/auto-loading are included.
"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,hashlib,sys

src=Path(sys.argv[1]);out=Path(sys.argv[2])
out.mkdir(parents=True,exist_ok=True)
report_file=src/'results/ABI_CHECK.json'
driver=src/'results/mt7601u.ko'
status=out/'PACKAGING_REPORT.txt'

def fail(message):
    status.write_text('BLOCKED: '+message+'\nNo KernelSU package produced.\n')
    print(status.read_text())
    return 2

if not report_file.exists() or not driver.exists():
    sys.exit(fail('compiled MT7601U driver or ABI report missing.'))
report=json.loads(report_file.read_text())
a=report.get('vendor_wifi_exports',{})
b=report.get('vendor_kernel_import_proxy',{})
if a.get('mismatched') or b.get('mismatched'):
    sys.exit(fail('imported symbol CRC disagreement with stock-equivalent POCO Wi-Fi stack.'))
if a.get('checked',0)<18 or a.get('matched',0)!=a.get('checked'):
    sys.exit(fail('fewer than 18 verified Wi-Fi symbol CRC matches.'))
if b.get('checked',0)<50 or b.get('matched',0)!=b.get('checked'):
    sys.exit(fail('fewer than 50 known kernel symbol CRC matches.'))
fw=Path('firmware/mt7601u.bin').read_bytes()
license_text=Path('firmware/LICENCE.ralink_a_mediatek_company_firmware').read_bytes()
if len(fw)!=45412 or hashlib.sha256(fw).hexdigest()!='4511b1d840e22aea2bf5fdca419c91c0d94cbfb291b9ac4f8be6d9100d1a7046':
    sys.exit(fail('firmware length or SHA256 mismatch.'))
blob=driver.read_bytes()
sha=hashlib.sha256(blob).hexdigest()
# NO service.sh, NO post-fs-data.sh. Never automatically insert kernel driver.
# Explicit consent required for manual_test.sh, and it checks actual device modules.
shell='''#!/system/bin/sh
set -u
MOD=/data/adb/modules/mt7601u_duchamp_test
[ "${1:-}" = "--i-accept-test-risk" ] || { echo "Manual test only. Read README.txt first."; exit 2; }
[ "$(uname -r)" = "6.1.177-GKID-r652-8aaf08bba" ] || { echo "STOP: unexpected running kernel"; exit 3; }
verify() { [ "$(sha256sum "$1" | cut -d" " -f1)" = "$2" ]; }
verify /vendor_dlkm/lib/modules/mac80211.ko 7159f34b0aefbf1c6a47823c5b730ca585818bdaf675ab72f7ac82a9f7f9fde7 || { echo "STOP: mac80211 differs"; exit 4; }
verify /vendor_dlkm/lib/modules/cfg80211.ko 2a37a43e27ab665b191da50a5a69ee4e0257bdf9cad644c79f44760bea10e5c2 || { echo "STOP: cfg80211 differs"; exit 4; }
verify "$MOD/mt7601u.ko" DRIVER_SHA || { echo "STOP: driver file changed"; exit 4; }
verify "$MOD/firmware/mt7601u.bin" 4511b1d840e22aea2bf5fdca419c91c0d94cbfb291b9ac4f8be6d9100d1a7046 || { echo "STOP: firmware changed"; exit 4; }
[ ! -d /sys/module/mt7601u ] || { echo "Already loaded"; exit 0; }
# The next operation touches the firmware_class global search path for this session.
F=/sys/module/firmware_class/parameters/path
if [ -w "$F" ]; then echo "$MOD/firmware" > "$F" || exit 5; fi
echo "Inserting test driver now; kernel instability or reboot is possible."
insmod "$MOD/mt7601u.ko" || { echo "insmod failed. Never try insmod -f."; exit 6; }
echo "Inserted. Plug in USB 148f:7601 and inspect dmesg / ip link."
'''.replace('DRIVER_SHA',sha)
readme=f'''MT7601U kernel-module RESEARCH candidate for POCO X6 Pro (duchamp).

Target running kernel: 6.1.177-GKID-r652-8aaf08bba (KernelSU).
USB device: 148f:7601, MT7601U.
Compiled from: mt6897-devs/android_kernel_6.1 lineage-23.2.
vermagic in built module: {report.get('target_vermagic','unknown')}
Offline Wi-Fi CRC matches: {a['checked']}/{a['checked']}. Kernel symbols covered by stock Wi-Fi imports: {b['checked']}.
Unverified imported symbols: {len(report.get('unverifiable_imports',[]))}.
NO runtime CFI validation, NO actual USB test has been performed.

There is NO automatic kernel-module load in this ZIP.
Installation alone is not a functional Wi-Fi driver test.
Only if you understand the risk, in Android root shell:
  su -c 'sh /data/adb/modules/mt7601u_duchamp_test/manual_test.sh --i-accept-test-risk'
If this kernel module crashes the phone, a reboot will not automatically load it again.
DO NOT load with --force, insmod -f, CRC patching, or replace stock Wi-Fi .ko modules.
Firmware file mt7601u.bin: redistribution license included.
'''
zipfile=out/'MT7601U_duchamp_KernelSU_MANUAL_TEST_ONLY.zip'
with ZipFile(zipfile,'w',ZIP_DEFLATED,compresslevel=9) as z:
    for name,content in {
        'module.prop':'id=mt7601u_duchamp_test\nname=MT7601U duchamp (manual test ONLY; no autoload)\nversion=0.1\nversionCode=1\nauthor=community research\ndescription=USB 148f:7601 manual-only driver. No service script or autoload.\n',
        'mt7601u.ko':blob,
        'system/vendor/firmware/mt7601u.bin':fw,
        'firmware/mt7601u.bin':fw,
        'LICENCE.ralink_a_mediatek_company_firmware':license_text,
        'README.txt':readme,
        'manual_test.sh':shell,
        'ABI_CHECK.json':json.dumps(report,indent=2)
    }.items():
        z.writestr(name,content)
status.write_text('CREATED MANUAL-ONLY PACKAGE. NOT VERIFIED ON REAL DEVICE.\nDriver SHA256: '+sha+'\n'+readme)
print(status.read_text())
