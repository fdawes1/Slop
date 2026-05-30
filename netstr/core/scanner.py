import subprocess
from dataclasses import dataclass
from typing import List

from scapy.all import ARP, Ether, conf, srp


@dataclass
class AP:
    ssid: str
    bssid: str
    channel: int
    signal: float


@dataclass
class Host:
    ip: str
    mac: str


def scan_aps(iface: str) -> List[AP]:
    try:
        result = subprocess.run(
            ["iw", "dev", iface, "scan"],
            capture_output=True, text=True, timeout=15,
        )
        return _parse_iw_scan(result.stdout)
    except Exception:
        return []


def _parse_iw_scan(output: str) -> List[AP]:
    aps, cur = [], {}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("BSS "):
            if cur.get("bssid"):
                aps.append(AP(
                    ssid=cur.get("ssid", "<hidden>"),
                    bssid=cur["bssid"],
                    channel=cur.get("channel", 0),
                    signal=cur.get("signal", 0.0),
                ))
            cur = {"bssid": line.split()[1].split("(")[0].strip()}
        elif line.startswith("SSID:"):
            cur["ssid"] = line.split(":", 1)[1].strip()
        elif "DS Parameter set: channel" in line:
            try:
                cur["channel"] = int(line.split()[-1])
            except ValueError:
                pass
        elif line.startswith("signal:"):
            try:
                cur["signal"] = float(line.split()[1])
            except ValueError:
                pass
    if cur.get("bssid"):
        aps.append(AP(
            ssid=cur.get("ssid", "<hidden>"),
            bssid=cur["bssid"],
            channel=cur.get("channel", 0),
            signal=cur.get("signal", 0.0),
        ))
    return aps


def scan_hosts(network: str, iface: str) -> List[Host]:
    conf.verb = 0
    try:
        ans, _ = srp(
            Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network),
            timeout=3, iface=iface, verbose=False,
        )
        return [Host(ip=r.psrc, mac=r.hwsrc) for _, r in ans]
    except Exception:
        return []
