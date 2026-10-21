#!/usr/bin/env python3
"""Read-only Android arm64 module ABI comparison against *public* duchamp Wi-Fi prebuilts.
We have independently checked 18 exported CRCs in these prebuilts against stock POCO X6 Pro.
This does NOT check Kernel CFI nor authorize loading a driver on a phone.
"""
import sys,struct,pathlib,json,subprocess
def parse_elf(p):
 d=pathlib.Path(p).read_bytes()
 if d[:6]!=b'\x7fELF\x02\x01':raise ValueError('Not ELF64 little-endian')
 off=struct.unpack_from('<Q',d,40)[0]
 step,n,strid=struct.unpack_from('<HHH',d,58)
 ss=[struct.unpack_from('<IIQQQQIIQQ',d,off+i*step) for i in range(n)]
 names=d[ss[strid][4]:ss[strid][4]+ss[strid][5]]
 def cstr(b,o):
  e=b.find(b'\0',o);return b[o:e if e!=-1 else None].decode(errors='replace')
 byindex={}
 sections={}
 for i,s in enumerate(ss):
  v=d[s[4]:s[4]+s[5]];byindex[i]=v;sections[cstr(names,s[0])]=(s,v)
 imports={}
 v=sections.get('__versions')
 if v:
  a=v[1]
  for i in range(0,len(a)-63,64):
   name=cstr(a,i+8)
   if name: imports[name]=struct.unpack_from('<I',a,i)[0]
 exports={}
 if '.symtab' in sections:
  s,syms=sections['.symtab']; strs=byindex[s[6]]
  for i in range(0,len(syms)-23,s[9] or 24):
   idx,info,other,sec,value,size=struct.unpack_from('<IBBHQQ',syms,i)
   if idx>=len(strs):continue
   n=cstr(strs,idx)
   if n.startswith('__crc_') and sec in byindex and value+4<=len(byindex[sec]):
    exports[n[6:]]=struct.unpack_from('<I',byindex[sec],value)[0]
 return imports,exports

def main():
 target=pathlib.Path('results/mt7601u.ko')
 actual,_=parse_elf(target)
 stockimports={}
 stockexports={}
 for n in ('cfg80211','mac80211'):
  imp,exp=parse_elf(pathlib.Path('prebuilt')/(n+'.ko'))
  for key,val in imp.items():
   if key in stockimports and stockimports[key]!=val:raise ValueError('Inconsistent stock kernel CRC for '+key)
   stockimports[key]=val
  for key,val in exp.items():
   if key in stockexports and stockexports[key]!=val:raise ValueError('Inconsistent WiFi export CRC for '+key)
   stockexports[key]=val
 report={}
 for label,ref in [('vendor_wifi_exports',stockexports),('vendor_kernel_import_proxy',stockimports)]:
  common=actual.keys() & ref.keys()
  good={k:hex(actual[k]) for k in sorted(common) if actual[k]==ref[k]}
  bad={k:{'built':hex(actual[k]),'prebuilt':hex(ref[k])} for k in sorted(common) if actual[k]!=ref[k]}
  report[label]={'checked':len(common),'matched':len(good),'mismatched':bad}
  print(label,'checked',len(common),'matched',len(good),'mismatches',len(bad))
  for k,v in bad.items():print(' DIFF',k,v)
 missed=actual.keys()-stockimports.keys()-stockexports.keys()
 report['unverifiable_imports']=sorted(missed)
 print('unverifiable imports',len(missed),'(the published vendor WiFi modules do not cover these kernel symbols)')
 report['target_vermagic']=subprocess.run(['modinfo','-F','vermagic',str(target)],capture_output=True,text=True).stdout.strip()
 report['verified_for_installation']=False
 pathlib.Path('results/ABI_CHECK.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Compiled vermagic:',report['target_vermagic'])
 print('NOT VERIFIED FOR DEVICE: mismatches and unverified KCFI/kernel symbols must be resolved before installation.')
if __name__=='__main__':main()
