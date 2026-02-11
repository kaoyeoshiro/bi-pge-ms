"""Gerenciamento de VPN e túnel SSH para acesso ao Oracle."""

import logging
import socket
import subprocess
import time

from .config import TunnelConfig

logger = logging.getLogger(__name__)

# Timeout para o túnel SSH ficar disponível
TUNNEL_TIMEOUT = 30
TUNNEL_POLL_INTERVAL = 1


def _is_vpn_connected(vpn_name: str) -> bool:
    """Verifica se a VPN está conectada via rasdial."""
    try:
        result = subprocess.run(
            ["rasdial"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return vpn_name in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _connect_vpn(config: TunnelConfig) -> None:
    """Conecta a VPN via rasdial usando credenciais do .env."""
    import os

    vpn_user = os.getenv("VPN_USER", "")
    vpn_password = os.getenv("VPN_PASSWORD", "")

    if not vpn_user or not vpn_password:
        raise RuntimeError(
            "Credenciais VPN não encontradas no .env (VPN_USER, VPN_PASSWORD)"
        )

    logger.info("Conectando VPN '%s'...", config.vpn_name)
    result = subprocess.run(
        ["rasdial", config.vpn_name, vpn_user, vpn_password],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Falha ao conectar VPN: {result.stderr.strip()}")
    logger.info("VPN conectada.")


def _is_port_open(host: str, port: int) -> bool:
    """Verifica se a porta está aceitando conexões."""
    try:
        with socket.create_connection((host, port), timeout=2):
            pass
        return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


class OracleTunnel:
    """Context manager que garante VPN + túnel SSH para o Oracle.

    Uso:
        with OracleTunnel(config) as tunnel:
            # Conectar ao Oracle em localhost:1521
            ...
    """

    def __init__(self, config: TunnelConfig) -> None:
        self._config = config
        self._ssh_process = None
        self._vpn_was_connected = False

    def __enter__(self) -> "OracleTunnel":
        config = self._config

        # Verifica VPN
        self._vpn_was_connected = _is_vpn_connected(config.vpn_name)
        if self._vpn_was_connected:
            logger.info("VPN '%s' já está conectada.", config.vpn_name)
        else:
            _connect_vpn(config)

        # Verifica se a porta já está aberta (túnel existente)
        if _is_port_open("localhost", config.oracle_port):
            logger.info(
                "Porta localhost:%d já aberta (túnel existente?).",
                config.oracle_port,
            )
            return self

        logger.info(
            "Abrindo túnel SSH %s:%d via %s@%s...",
            config.oracle_host,
            config.oracle_port,
            config.ssh_user,
            config.ssh_host,
        )

        # Abre túnel SSH
        ssh_cmd = [
            config.ssh_exe,
            "-L",
            f"{config.oracle_port}:{config.oracle_host}:{config.oracle_port}",
            f"{config.ssh_user}@{config.ssh_host}",
            "-N",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=60",
        ]

        self._ssh_process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        # Aguarda porta ficar disponível
        start = time.monotonic()
        while time.monotonic() - start < TUNNEL_TIMEOUT:
            if _is_port_open("localhost", config.oracle_port):
                logger.info("Túnel SSH ativo em localhost:%d.", config.oracle_port)
                return self
            time.sleep(TUNNEL_POLL_INTERVAL)

        # Timeout — limpa e erro
        self._cleanup_ssh()
        raise RuntimeError(
            f"Túnel SSH não ficou disponível em {TUNNEL_TIMEOUT}s. "
            "Verifique a conexão VPN e a chave SSH."
        )

    def __exit__(self, *args) -> None:
        self._cleanup_ssh()

    def _cleanup_ssh(self) -> None:
        """Encerra o processo SSH se foi criado por nós."""
        if self._ssh_process:
            logger.info("Encerrando túnel SSH (PID %d)...", self._ssh_process.pid)
            self._ssh_process.terminate()
            try:
                self._ssh_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ssh_process.kill()
            self._ssh_process = None
