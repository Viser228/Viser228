#!/usr/bin/env python3
"""Read-only comparator for Linux arm64 module imports against stock Wi-Fi symbol CRCs."""
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

EXPECTED = {
    "mac80211": {
        "ieee80211_alloc_hw_nm": 0xc1e8db04,
        "ieee80211_free_hw": 0x866b3f4b,
        "ieee80211_free_txskb": 0xfac65454,
        "ieee80211_get_tx_rates": 0x91ba47db,
        "ieee80211_queue_delayed_work": 0x93338062,
        "ieee80211_register_hw": 0x4617ea14,
        "ieee80211_rx_list": 0xc041edfb,
        "ieee80211_send_bar": 0x6cfb93ca,
        "ieee80211_stop_queue": 0x120ec953,
        "ieee80211_stop_queues": 0x56ad81b4,
        "ieee80211_stop_tx_ba_cb_irqsafe": 0x907cb2ac,
        "ieee80211_tx_status": 0xf4ebb9b5,
        "ieee80211_tx_status_ext": 0x41f867dc,
        "ieee80211_unregister_hw": 0x1f1cbd9d,
        "ieee80211_wake_queue": 0xdb92a2ea,
        "ieee80211_wake_queues": 0x208178b6,
    },
    "cfg80211": {
        "ieee80211_get_hdrlen_from_skb": 0x3b274a43,
        "ieee80211_hdrlen": 0x7ef39823,
    },
}

def imports(path):
    s = subprocess.check_output(["readelf", "-SW", str(path)], text=True)
    for line in s.splitlines():
        m = re.match(r"\s*\[\s*\d+\]\s+__versions\s+\S+\s+\S+\s+([a-fA-F0-9]+)\s+([a-fA-F0-9]+)", line)
        if m:
            off, size = (int(v, 16) for v in m.groups())
            break
    else:
        raise ValueError("Module has no __versions section")
    blob = Path(path).read_bytes()[off:off+size]
    result = {}
    for i in range(0,len(blob),64):
        entry = blob[i:i+64]
        if len(entry)<64: continue
        name = entry[8:].split(b"\0",1)[0].decode("utf-8","replace")
        if name: result[name] = struct.unpack_from("<I",entry)[0]
    return result

def main():
    path=Path(sys.argv[1])
    got=imports(path)
    report={"module":str(path),"total_imports":len(got),"dependencies":{}}
    failures=0
    for dep, expected in EXPECTED.items():
        matched=[]; mismatched=[]; missing=[]
        for name,crc in expected.items():
            val=got.get(name)
            if val is None: missing.append(name)
            elif val==crc: matched.append(name)
            else: mismatched.append({"symbol":name,"built":f"0x{val:08x}","stock":f"0x{crc:08x}"})
        failures+=len(mismatched)
        report["dependencies"][dep]={"matched":len(matched),"mismatched":mismatched,"missing":missing}
        print(f"{dep}: {len(matched)} matched; {len(mismatched)} CRC mismatch; {len(missing)} unused",flush=True)
        for x in mismatched: print(" MISMATCH",x["symbol"],x["built"],"!=",x["stock"],flush=True)
    report["all_checked_crc_match"]=failures==0
    print("CRC check:", "PASS (not a full ABI/CFI safety test)" if failures==0 else "FAILED",flush=True)
    if len(sys.argv)>2:
        Path(sys.argv[2]).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    return 0 if failures==0 else 2

if __name__=="__main__":
    sys.exit(main())
