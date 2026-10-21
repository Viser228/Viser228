#!/usr/bin/env python3
"""Compare published POCO X6 Pro (duchamp) Wi-Fi module exports with stock CRCs.
Uses only the public CRCs from the previously shared vendor-module report.
Never attempts to load or modify kernel modules.
"""
import pathlib, struct, subprocess, json
EXPECTED = {
 "mac80211": {
  "ieee80211_alloc_hw_nm":0xc1e8db04,"ieee80211_free_hw":0x866b3f4b,
  "ieee80211_free_txskb":0xfac65454,"ieee80211_get_tx_rates":0x91ba47db,
  "ieee80211_queue_delayed_work":0x93338062,
  "ieee80211_register_hw":0x4617ea14,
  "ieee80211_rx_list":0xc041edfb,"ieee80211_send_bar":0x6cfb93ca,
  "ieee80211_stop_queue":0x120ec953,"ieee80211_stop_queues":0x56ad81b4,
  "ieee80211_stop_tx_ba_cb_irqsafe":0x907cb2ac,
  "ieee80211_tx_status":0xf4ebb9b5,
  "ieee80211_tx_status_ext":0x41f867dc,
  "ieee80211_unregister_hw":0x1f1cbd9d,
  "ieee80211_wake_queue":0xdb92a2ea,
  "ieee80211_wake_queues":0x208178b6},
 "cfg80211":{
  "ieee80211_get_hdrlen_from_skb":0x3b274a43,
  "ieee80211_hdrlen":0x7ef39823}
}
def exports(path):
 d=pathlib.Path(path).read_bytes()
 if d[:4]!=b'\x7fELF' or d[4:6]!=b'\x02\x01': raise ValueError('not ELF64 little-endian')
 shoff=struct.unpack_from('<Q',d,40)[0]
 entsize,num,shstrid=struct.unpack_from('<HHH',d,58)
 sh=[struct.unpack_from('<IIQQQQIIQQ',d,shoff+i*entsize) for i in range(num)]
 shstr=d[sh[shstrid][4]:sh[shstrid][4]+sh[shstrid][5]]
 def name(b,off):return b[off:b.find(b'\0',off)].decode(errors='replace')
 byindex={}
 byname={}
 for i,h in enumerate(sh):
  k=name(shstr,h[0]); byindex[i]=d[h[4]:h[4]+h[5]];byname[k]=(i,h)
 si,h=byname['.symtab'];syms=byindex[si];strs=byindex[h[6]]
 out={}
 for off in range(0,len(syms),24):
  if off+24>len(syms):break
  sn,info,other,section,value,size=struct.unpack_from('<IBBHQQ',syms,off)
  if sn>=len(strs):continue
  nm=name(strs,sn)
  if not nm.startswith('__crc_'):continue
  sec=byindex.get(section)
  if sec is not None and value+4<=len(sec):out[nm[6:]]=struct.unpack_from('<I',sec,value)[0]
 return out
def main():
 report={}
 for group, ref in EXPECTED.items():
  p=pathlib.Path('prebuilt')/(group+'.ko')
  found=exports(p)
  matches={k:hex(found[k]) for k,v in ref.items() if found.get(k)==v}
  mismatches={k:{'stock':hex(v),'prebuilt':hex(found[k])} for k,v in ref.items() if k in found and found[k]!=v}
  absent=[k for k in ref if k not in found]
  vm=subprocess.run(['modinfo','-F','vermagic',str(p)],capture_output=True,text=True).stdout.strip()
  report[group]={'file_bytes':p.stat().st_size,'vermagic':vm,'matched':matches,'mismatched':mismatches,'missing':absent}
  print(group, 'file_bytes',p.stat().st_size,'vermagic',vm,'MATCH',len(matches),'MISMATCH',len(mismatches),'MISSING',len(absent),flush=True)
  for k,v in mismatches.items():print('  DIFFERENCE',k,v,flush=True)
  for k in absent:print('  MISSING',k,flush=True)
 pathlib.Path('results').mkdir(exist_ok=True)
 pathlib.Path('results/vendor_prebuilt_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('NOTE: CRC matching in two Wi-Fi modules does not prove full kernel/CFI binary compatibility.')
if __name__=='__main__': main()
