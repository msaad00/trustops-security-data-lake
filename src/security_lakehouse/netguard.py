"""Shared SSRF / URL-safety guard for outbound and inbound HTTP.

Both the workflow egress path and the inbound connector clients route
credentialed requests at operator-supplied hosts. This module centralizes the
defense so the check is identical on every path: only ``http``/``https`` is
allowed, and the *resolved* address(es) must be public — a public-looking name
that resolves to a private/loopback address (DNS rebinding, split-horizon) is
still blocked.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


def assert_resolved_ip_is_public(host: str, *, label: str = "target") -> list[str]:
    """Resolve ``host`` and reject any address in a non-public range.

    Returns the resolved addresses on success; raises ``ValueError`` otherwise.
    The private/loopback/link-local/reserved/multicast check runs on the
    resolved address(es), not just the hostname string.
    """
    if host.lower() == "localhost":
        raise ValueError(f"{label} 'localhost' is not allowed")
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise ValueError(f"{label} host {host!r} did not resolve: {exc}") from exc
    addresses = [str(info[4][0]) for info in infos]
    if not addresses:
        raise ValueError(f"{label} host {host!r} did not resolve to any address")
    for raw_ip in addresses:
        # Strip any IPv6 scope id (e.g. fe80::1%eth0) before parsing.
        ip = ipaddress.ip_address(raw_ip.split("%", 1)[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(f"{label} resolves to non-public address {raw_ip} (SSRF blocked)")
    return addresses


def assert_url_is_public(url: str, *, label: str = "target") -> str:
    """Validate that ``url`` is http(s) and its host resolves to a public IP.

    Returns the host on success; raises ``ValueError`` otherwise. Use at the
    boundary where an operator-configured base URL first enters a credentialed
    request path.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"{label} URL scheme must be http or https, got {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise ValueError(f"{label} URL has no host: {url!r}")
    assert_resolved_ip_is_public(host, label=label)
    return host
