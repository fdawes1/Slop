import threading
from typing import Callable

from scapy.all import ARP, ICMP, IP, TCP, Dot11, Dot11Deauth, sniff


class PacketMonitor:
    def __init__(self, callback: Callable[[str, str], None]) -> None:
        self._callback = callback
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self, iface: str) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(iface,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self, iface: str) -> None:
        sniff(
            iface=iface,
            prn=self._handle,
            store=False,
            stop_filter=lambda _: not self._running,
        )

    def _handle(self, pkt) -> None:
        if pkt.haslayer(Dot11Deauth):
            d = pkt[Dot11]
            reason = pkt[Dot11Deauth].reason
            self._callback("attack", f"DEAUTH  {d.addr2} → {d.addr1}  reason={reason}")

        elif pkt.haslayer(ARP):
            arp = pkt[ARP]
            if arp.op == 1:
                self._callback("info", f"ARP who-has {arp.pdst}  tell {arp.psrc}")
            elif arp.op == 2:
                self._callback("event", f"ARP reply  {arp.psrc} is-at {arp.hwsrc}")

        elif pkt.haslayer(ICMP) and pkt.haslayer(IP):
            ip = pkt[IP]
            icmp_type = pkt[ICMP].type
            label = {0: "echo-reply", 8: "echo-req"}.get(icmp_type, f"type={icmp_type}")
            self._callback("info", f"ICMP {label}  {ip.src} → {ip.dst}")

        elif pkt.haslayer(TCP) and pkt.haslayer(IP):
            tcp = pkt[TCP]
            ip = pkt[IP]
            flags = tcp.sprintf("%flags%")
            if "S" in flags and "A" not in flags:
                self._callback("info", f"TCP SYN  {ip.src}:{tcp.sport} → {ip.dst}:{tcp.dport}")
            elif "R" in flags:
                self._callback("warning", f"TCP RST  {ip.src}:{tcp.sport} → {ip.dst}:{tcp.dport}")
