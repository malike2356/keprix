"""SSRF denylist for unmatched outbound proxy traffic."""

from __future__ import annotations

import ipaddress
import socket
from typing import Iterable


_PRIVATE_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def resolve_host_ips(host: str) -> list[str]:
    host = host.split(":")[0].strip("[]")
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve host {host!r}: {exc}") from exc
    ips: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)
    return ips


def is_private_or_loopback_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    for network in _PRIVATE_NETWORKS:
        if ip in network:
            return True
    return ip.is_loopback or ip.is_private or ip.is_link_local


def assert_host_allowed(host: str) -> None:
    for ip in resolve_host_ips(host):
        if is_private_or_loopback_ip(ip):
            raise PermissionError(
                f"Blocked outbound proxy to private or loopback address {host} ({ip})"
            )


def filter_allowed_ips(ips: Iterable[str]) -> list[str]:
    blocked = [ip for ip in ips if is_private_or_loopback_ip(ip)]
    if blocked:
        raise PermissionError(f"Blocked private or loopback IPs: {', '.join(blocked)}")
    return list(ips)
