"""DNS resolution test — resolve configured and ad-hoc hostnames."""

import os
import re
import socket
import time
from typing import Any, Dict, List

from .base_test import BaseTest, TestResult


class DNSTest(BaseTest):
    def __init__(self):
        super().__init__()
        hostnames_str = os.getenv("DNS_TEST_HOSTNAMES", "")
        self.hostnames = [h.strip() for h in hostnames_str.split(",") if h.strip()]
        self.timeout = int(os.getenv("DNS_TEST_TIMEOUT", "10"))

    @property
    def test_name(self) -> str:
        return "DNS Resolution"

    @property
    def test_description(self) -> str:
        return "Tests DNS resolution for configured hostnames"

    @property
    def test_id(self) -> str:
        return "dns"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return max(self.timeout * len(self.hostnames), 30) if self.hostnames else 30

    def is_configured(self) -> bool:
        # DNS is always available; pre-configured hostnames are optional
        return True

    def get_configuration_help(self) -> str:
        return (
            "Configure with DNS_TEST_HOSTNAMES (comma-separated hostnames), "
            "DNS_TEST_TIMEOUT (default: 10). You can also resolve ad-hoc hostnames via the dashboard."
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        if not self.hostnames:
            result.complete(
                True,
                "No hostnames configured. Use the dashboard to test ad-hoc resolution.",
                {"hostnames_tested": 0},
            )
            return result

        passed = 0
        failed = 0

        for hostname in self.hostnames:
            resolution = self.resolve_hostname(hostname)
            result.add_sub_test(hostname, {
                "success": resolution["resolved"],
                "message": resolution["message"],
                **resolution,
            })
            if resolution["resolved"]:
                passed += 1
            else:
                failed += 1

        total = passed + failed
        if failed == 0:
            result.complete(True, f"All {total} hostnames resolved successfully")
        else:
            result.complete(False, f"{passed}/{total} hostnames resolved, {failed} failed")

        return result

    @staticmethod
    def _get_system_resolver() -> str:
        """Detect the system DNS resolver address."""
        try:
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        return line.split()[1]
        except (FileNotFoundError, IndexError):
            pass
        return "system default"

    @staticmethod
    def resolve_hostname(hostname: str) -> Dict[str, Any]:
        """Resolve a single hostname. Used by both run_test and ad-hoc endpoint."""
        resolver = DNSTest._get_system_resolver()
        start = time.time()
        try:
            results = socket.getaddrinfo(hostname, None)
            latency_ms = round((time.time() - start) * 1000, 1)

            # Separate IPv4 and IPv6
            ipv4 = sorted({r[4][0] for r in results if r[0] == socket.AF_INET})
            ipv6 = sorted({r[4][0] for r in results if r[0] == socket.AF_INET6})
            all_ips = ipv4 + ipv6

            # Detect address families present
            families = []
            if ipv4:
                families.append("A")
            if ipv6:
                families.append("AAAA")

            # Try reverse lookup on first IP for CNAME-like info
            canonical = None
            try:
                canonical_info = socket.gethostbyaddr(all_ips[0])
                if canonical_info[0] != hostname:
                    canonical = canonical_info[0]
            except (socket.herror, IndexError):
                pass

            return {
                "resolved": True,
                "hostname": hostname,
                "ip_addresses": all_ips,
                "ipv4_addresses": ipv4,
                "ipv6_addresses": ipv6,
                "record_types": families,
                "canonical_name": canonical,
                "resolver": resolver,
                "latency_ms": latency_ms,
                "message": f"Resolved to {', '.join(all_ips)} ({latency_ms}ms)",
            }
        except socket.gaierror as e:
            latency_ms = round((time.time() - start) * 1000, 1)
            return {
                "resolved": False,
                "hostname": hostname,
                "ip_addresses": [],
                "ipv4_addresses": [],
                "ipv6_addresses": [],
                "record_types": [],
                "canonical_name": None,
                "resolver": resolver,
                "latency_ms": latency_ms,
                "error_code": str(e),
                "message": f"Failed to resolve: {e}",
            }

    @staticmethod
    def validate_hostname(hostname: str) -> bool:
        """Validate hostname format: alphanumeric + dots + hyphens, max 253 chars."""
        if not hostname or len(hostname) > 253:
            return False
        return bool(re.match(r'^[a-zA-Z0-9](?:[a-zA-Z0-9.\-]*[a-zA-Z0-9])?$', hostname))
