#!/usr/bin/env python3
"""Fetch timecoded lyrics for the current song, with a bounded disk cache."""
import hashlib,json,os,re,sys,time,urllib.parse,urllib.request
from pathlib import Path

def fetch(track):
    key=hashlib.sha256(json.dumps(track,sort_keys=True).encode()).hexdigest()
    cache=Path(os.environ.get('XDG_CACHE_HOME',Path.home()/'.cache'))/'modesty'/'lyrics';cache.mkdir(parents=True,exist_ok=True)
    path=cache/(key+'.json')
    if path.exists() and time.time()-path.stat().st_mtime<7*86400:return json.loads(path.read_text())
    query=urllib.parse.urlencode({'track_name':track['title'],'artist_name':track['artist'],'duration':round(track.get('duration',0))})
    request=urllib.request.Request('https://lrclib.net/api/get?'+query,headers={'User-Agent':'Modesty/1.0 (Quickshell desktop lyrics)'})
    try:
        with urllib.request.urlopen(request,timeout=6) as response:data=json.loads(response.read(2_000_000))
        lines=[]
        for line in (data.get('syncedLyrics') or '').splitlines():
            match=re.match(r'\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)',line)
            if match:lines.append({'time':int(match[1])*60+float(match[2]),'text':match[3]})
        result={'lines':lines,'instrumental':bool(data.get('instrumental'))}
    except Exception:result={'lines':[]}
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result));temp.replace(path)
    for old in sorted(cache.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[100:]:old.unlink(missing_ok=True)
    return result
if __name__=='__main__':
    track=json.loads(sys.argv[1]);print(json.dumps(dict(fetch(track),key=sys.argv[2])),flush=True)
