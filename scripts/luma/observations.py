"""Read measured desktop resources, sensors and timezone-aware clock values."""
from datetime import datetime
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

def metrics():
    # Reuse the panel sampler; --sample exits after one real rate measurement.
    sample = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "performance.py"), "--sample", "--processes"],
                            capture_output=True, text=True, timeout=4, check=True)
    data=json.loads(sample.stdout.splitlines()[-1])
    data["observedAt"]=datetime.now().astimezone().isoformat()
    data["units"]={"cpu":"fraction 0..1","memory":"bytes","diskIo":"bytes/second","network":"bytes/second","processCpu":"fraction of one core, may exceed 1","processMemory":"RSS bytes, shared pages can be counted in multiple processes","pressure":"fraction of stalled time averaged over ten seconds"}
    data["displayValues"]={"memoryUsedGiB":round(data["memoryUsed"]/1024**3,2),"memoryTotalGiB":round(data["memoryTotal"]/1024**3,2),
        "memoryUsedGB":round(data["memoryUsed"]/10**9,2),"memoryTotalGB":round(data["memoryTotal"]/10**9,2),"cpuPercent":round((data.get("cpu") or 0)*100,2),
        "processes":[dict(pid=p["pid"],name=p["name"],memoryMiB=round(p["memory"]/1024**2,2),memoryGiB=round(p["memory"]/1024**3,2),cpuPercent=round(p["cpu"]*100,2)) for p in data.get("processes",[])]}
    data["diagnosticLimits"]=[
        "This is one short snapshot, not a history of the user's lag. A cause must not be asserted without evidence linking it to the lag.",
        "swapUsed measures pages stored in swap, not current paging activity. Nonzero swap does not prove current RAM exhaustion or swap-induced lag. No paging-in/out rates are measured here.",
        "memoryUsed uses MemAvailable, not simply allocated or cached RAM. Compare it with memoryTotal before describing RAM pressure.",
        "Disk capacity, I/O throughput and I/O pressure are different observations. A nearly full filesystem alone does not establish the cause of general slowness.",
        "Name actual CPU load, available memory and pressure when assessing bottlenecks. If these show no clear current contention, explain that this snapshot cannot determine the earlier slowdown; do not invent one."
    ]
    return data



def hardware():
    """Read labeled sensors through libsensors; no probing or fan/thermal writes."""
    sample = subprocess.run(["sensors", "-j"], capture_output=True, text=True, timeout=3)
    if len(sample.stdout)>131072:
        raise ValueError("Hardware sensor response is too large")
    data=json.loads(sample.stdout)
    if not isinstance(data,dict):
        raise ValueError("Invalid hardware sensor response")
    readings=[]
    for chip,channels in data.items():
        if not isinstance(channels,dict):
            continue
        for label,values in channels.items():
            if not isinstance(values,dict):
                continue
            for field,value in values.items():
                match=re.fullmatch(r"(temp|fan)(\d+)_input",field)
                if not match or type(value) not in (int,float) or not math.isfinite(value):
                    continue
                kind,number=match.groups()
                if (kind=="temp" and not -273.15<=value<=1000) or (kind=="fan" and value<0) or values.get(kind+number+"_fault")==1:
                    continue
                reading={"chip":chip,"label":label,"channel":field,"kind":"temperature" if kind=="temp" else "fan","value":value,"unit":"°C" if kind=="temp" else "RPM"}
                for suffix in ("min","max","crit","lcrit","alarm","fault"):
                    limit=values.get(kind+number+"_"+suffix)
                    if type(limit) in (int,float) and math.isfinite(limit) and (suffix in {"alarm","fault"} or kind!="temp" or -273.15<=limit<=1000):
                        reading[suffix]=limit
                readings.append(reading)
    if not readings:
        raise ValueError("No readable temperature or fan sensors reported")
    return {"observedAt":datetime.now().astimezone().isoformat(),"source":"lm-sensors","readings":readings[:64],
            "warnings":sample.stderr.strip()[:1000],
            "scope":"Only listed chip/channel readings were measured. Unlisted hardware is unavailable. Labels distinguish CPU, GPU and storage; never use the hottest sensor as CPU. A control reading such as Tctl is not a separate measured CPU core. Limits are reported sensor values, not universal safety guarantees."}



def clock(zones):
    """Convert one real timestamp with installed timezone rules; no city table."""
    if not isinstance(zones, list) or len(zones)>2 or any(not isinstance(z,str) or len(z)>100 for z in zones):
        raise ValueError("Invalid clock timezones")
    now=datetime.now().astimezone()
    readings=[]
    for zone in dict.fromkeys(zones):
        try:
            value=now.astimezone(ZoneInfo(zone))
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("Requested timezone is unavailable") from None
        readings.append({"zone":zone,"datetime":value.isoformat(),"abbreviation":value.tzname()})
    return {"source":"System clock and installed IANA timezone rules","observedAt":now.isoformat(),"readings":readings}
