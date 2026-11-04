"""Trava de instância única via porta TCP local.

Sem isso, dar dois cliques no atalho abre dois HUDs (e dois conjuntos de timers).
Funciona igual em Windows, Linux e Mac, e o SO libera a porta se o processo morrer.
"""

import socket


class SingleInstance:
    def __init__(self, port: int):
        self.port = port
        self._sock: socket.socket = None

    def acquire(self) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Sem SO_REUSEADDR: no Windows ele permitiria dois processos na mesma porta.
        try:
            sock.bind(("127.0.0.1", self.port))
            sock.listen(1)
        except OSError:
            sock.close()
            return False
        self._sock = sock
        return True

    def release(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
