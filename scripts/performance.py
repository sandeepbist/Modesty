#!/usr/bin/env python3
"""Read Linux counters while the performance panel is open. No external tools."""
import json
import os
import signal
from pathlib import Path
import sys
import time


PROTECTED = {"hyprland", "quickshell", "systemd", "dbus-daemon", "dbus-broker", "dbus-broker-lau", "polkitd"}


def stoppable(pid, name, owner):
    return pid > 1 and pid not in {os.getpid(), os.getppid()} and owner == os.geteuid() and name.casefold() not in PROTECTED


def terminate(pid, started):
    """Pin the original process before checking its birth stamp and requesting SIGTERM."""
    if pid <= 1 or not str(started).isdigit():
        raise ValueError("Process is unavailable.")
    descriptor = os.pidfd_open(pid)
    try:
        folder = Path('/proc')/str(pid)
        raw = (folder/'stat').read_text()
        end = raw.rfind(')')
        born = raw[end+2:].split()[19]
        name = raw[raw.find('(')+1:end]
        if born != str(started):
            raise ValueError("Process changed. Refresh and try again.")
        if not stoppable(pid, name, folder.stat().st_uid):
            raise ValueError("This session process cannot be stopped here.")
        signal.pidfd_send_signal(descriptor, signal.SIGTERM)
        return {"ok":True, "name":name[:80]}
    finally:
        os.close(descriptor)


def counters():
    cpu = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()}
    network = {}
    for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
        interface, values = line.split(':', 1)
        interface = interface.strip()
        # Count physical interfaces only, avoiding VPN/bridge double counting.
        if not (Path('/sys/class/net') / interface / 'device').exists():
            continue
        fields = values.split()
        network[interface] = (int(fields[0]), int(fields[8]))
    devices = {}
    for line in Path('/proc/diskstats').read_text().splitlines():
        fields = line.split()
        name = fields[2]
        # Whole physical devices only: no partition, loop or dm double counting.
        block = Path('/sys/block') / name
        if not (block / 'device').exists() or len(fields) < 14:
            continue
        values = list(map(int, fields[3:]))
        devices[name] = (values[2] * 512, values[6] * 512, values[9])
    return cpu, memory, network, devices


def disk(path):
    stat = os.statvfs(path)
    total = stat.f_blocks * stat.f_frsize
    used = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
    return {'path': path, 'total': total, 'used': used}


def processes():
    result = {}
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():
            continue
        try:
            raw = (folder/'stat').read_text()
            end = raw.rfind(')')
            fields = raw[end+2:].split()
            ticks, born, rss = int(fields[11])+int(fields[12]), int(fields[19]), max(0,int(fields[21]))*os.sysconf('SC_PAGE_SIZE')
            io = None
            try:
                values = dict(line.split(':',1) for line in (folder/'io').read_text().splitlines())
                io = int(values['read_bytes'])+int(values['write_bytes'])
            except (OSError, ValueError, KeyError):
                pass
            name = raw[raw.find('(')+1:end][:80]
            result[int(folder.name)] = (born, ticks, rss, name, io, stoppable(int(folder.name),name,folder.stat().st_uid))
        except (OSError, ValueError, IndexError):
            continue
    return result


def process_rates(current, previous, elapsed):
    rows = []
    clock = os.sysconf('SC_CLK_TCK')
    for pid, (born, ticks, rss, name, io, can_stop) in current.items():
        old = previous.get(pid)
        same = old and old[0] == born
        cpu = max(0, ticks-old[1])/clock/elapsed if same else 0
        rate = max(0,io-old[4])/elapsed if same and io is not None and old[4] is not None else None
        rows.append(dict(pid=pid, started=str(born), canStop=can_stop, name=name, cpu=cpu, memory=rss, io=rate))
    selected = {}
    for key in ('cpu','memory','io'):
        for row in sorted(rows,key=lambda r:r[key] or 0,reverse=True)[:4]:
            selected[row['pid']] = row
    return list(selected.values())


def pressure():
    result = {}
    for name in ('cpu','memory','io'):
        try:
            line = next(line for line in (Path('/proc/pressure')/name).read_text().splitlines() if line.startswith('some '))
            result[name] = float(dict(field.split('=') for field in line.split()[1:])['avg10'])/100
        except (OSError, ValueError, StopIteration):
            result[name] = None
    return result


def run():
    previous, old_processes = None, {}
    while True:
        now = time.monotonic()
        cpu, memory, network, devices = counters()
        usage = None
        down = up = 0
        if previous:
            before, old_cpu, old_network, old_devices = previous
            elapsed = now - before
            total = sum(cpu) - sum(old_cpu)
            idle = cpu[3] + cpu[4] - old_cpu[3] - old_cpu[4]
            usage = max(0, min(1, (total - idle) / total)) if total > 0 else 0
            for name, values in network.items():
                if name in old_network:
                    down += max(0, values[0] - old_network[name][0]) / elapsed
                    up += max(0, values[1] - old_network[name][1]) / elapsed
        current_processes = processes() if "--processes" in sys.argv else {}
        top = process_rates(current_processes, old_processes, elapsed) if previous and current_processes else []
        io = []
        for name, values in devices.items():
            read = write = busy = None
            if previous and name in old_devices:
                old = old_devices[name]
                # Counter reset/hotplug must not produce negative rates.
                read = max(0, values[0] - old[0]) / elapsed
                write = max(0, values[1] - old[1]) / elapsed
                busy = min(1, max(0, values[2] - old[2]) / (elapsed * 1000))
            io.append({'name': name, 'read': read, 'write': write, 'busy': busy})
        total_memory = memory['MemTotal']
        disks = [disk('/')]
        home = os.path.expanduser('~')
        if os.stat(home).st_dev != os.stat('/').st_dev:
            disks.append(disk(home))
        print(json.dumps({'cpu': usage, 'memoryTotal': total_memory,
              'memoryUsed': total_memory - memory.get('MemAvailable', memory['MemFree']),
              'disks': disks, 'diskIo': io, 'download': down, 'upload': up,
              'interfaces': list(network), 'processes': top, 'pressure': pressure(), 'swapUsed': memory.get('SwapTotal',0)-memory.get('SwapFree',0), 'observedAt': time.time()}), flush=True)
        if "--sample" in sys.argv and previous is not None:
            break
        previous = now, cpu, network, devices
        old_processes = current_processes
        time.sleep(1)


if __name__ == '__main__':
    try:
        if len(sys.argv)==4 and sys.argv[1]=='--terminate':
            print(json.dumps(terminate(int(sys.argv[2]),sys.argv[3])),flush=True)
        else:
            run()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    except (OSError, ValueError) as exc:
        message = str(exc) if isinstance(exc,ValueError) else "Process already exited." if isinstance(exc,ProcessLookupError) else "Could not access this process." if '--terminate' in sys.argv else "Could not read system activity."
        print(json.dumps({'ok':False,'error':message}), flush=True)
        sys.exit(1)
