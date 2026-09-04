"""System metric collection built on psutil."""

import os
import platform
import socket
import subprocess
import time
from typing import Dict, List

import psutil


def bytes_to_human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def uptime() -> Dict:
    boot = psutil.boot_time()
    seconds = time.time() - boot
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return {
        "string": " ".join(parts),
        "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot)),
        "seconds": int(seconds),
    }


def overview() -> Dict:
    cpu = psutil.cpu_percent(interval=0.1)
    freq = psutil.cpu_freq()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()
    return {
        "cpu": {
            "percent": cpu,
            "cores": psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True),
            "threads": psutil.cpu_count(logical=True),
            "freq_mhz": round(freq.current, 1) if freq else 0,
        },
        "memory": {
            "percent": mem.percent,
            "used": mem.used,
            "total": mem.total,
            "used_str": bytes_to_human(mem.used),
            "total_str": bytes_to_human(mem.total),
        },
        "disk": {
            "percent": disk.percent,
            "used": disk.used,
            "total": disk.total,
            "used_str": bytes_to_human(disk.used),
            "total_str": bytes_to_human(disk.total),
            "read_bytes": disk_io.read_bytes if disk_io else 0,
            "write_bytes": disk_io.write_bytes if disk_io else 0,
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
        },
        "uptime": uptime(),
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
    }


def cpu_detail() -> Dict:
    per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    freq = psutil.cpu_freq(percpu=False)
    try:
        load = list(os.getloadavg())
    except (OSError, AttributeError):
        load = [0.0, 0.0, 0.0]
    return {
        "overall": psutil.cpu_percent(interval=0.1),
        "per_core": per_core,
        "cores": psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True),
        "threads": psutil.cpu_count(logical=True),
        "freq_current": round(freq.current, 1) if freq else 0,
        "freq_max": round(freq.max, 1) if freq else 0,
        "load_avg": load,
    }


def memory_detail() -> Dict:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "ram": {
            "total": mem.total,
            "used": mem.used,
            "free": mem.available,
            "percent": mem.percent,
            "total_str": bytes_to_human(mem.total),
            "used_str": bytes_to_human(mem.used),
            "free_str": bytes_to_human(mem.available),
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "percent": swap.percent,
            "total_str": bytes_to_human(swap.total),
            "used_str": bytes_to_human(swap.used),
        },
    }


def disk_detail() -> Dict:
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        partitions.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "total_str": bytes_to_human(usage.total),
            "used_str": bytes_to_human(usage.used),
            "free_str": bytes_to_human(usage.free),
            "percent": usage.percent,
        })
    io = psutil.disk_io_counters()
    return {
        "partitions": partitions,
        "io": {
            "read_bytes": io.read_bytes if io else 0,
            "write_bytes": io.write_bytes if io else 0,
            "read_count": io.read_count if io else 0,
            "write_count": io.write_count if io else 0,
        },
    }


def network_detail() -> Dict:
    io = psutil.net_io_counters()
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    interfaces = []
    for name, addr_list in addrs.items():
        ipv4 = next((a.address for a in addr_list if a.family == socket.AF_INET), None)
        interfaces.append({
            "name": name,
            "ipv4": ipv4,
            "is_up": stats[name].isup if name in stats else False,
        })
    return {
        "bytes_sent": io.bytes_sent,
        "bytes_recv": io.bytes_recv,
        "packets_sent": io.packets_sent,
        "packets_recv": io.packets_recv,
        "interfaces": interfaces,
    }


def services(watched: List[str]) -> Dict:
    result = []
    for name in watched:
        try:
            proc = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True, text=True, timeout=2,
            )
            status = proc.stdout.strip() or "unknown"
        except (FileNotFoundError, subprocess.SubprocessError):
            status = "unknown"
        result.append({"name": name, "active": status == "active", "status": status})
    return {"services": result}


def processes(limit: int, hidden: bool) -> Dict:
    if hidden:
        return {"processes": [], "hidden": True}
    procs: List[Dict] = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "username"]):
        try:
            procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda p: p.get("cpu_percent") or 0, reverse=True)
    return {"processes": procs[:limit], "hidden": False}


def tick() -> Dict:
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    net = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()
    return {
        "ts": int(time.time() * 1000),
        "cpu": cpu,
        "mem": mem.percent,
        "net_sent": net.bytes_sent,
        "net_recv": net.bytes_recv,
        "disk_read": disk_io.read_bytes if disk_io else 0,
        "disk_write": disk_io.write_bytes if disk_io else 0,
    }
