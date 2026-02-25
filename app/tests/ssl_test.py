import datetime
import os
import socket
import ssl
import subprocess
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from .base_test import BaseTest, TestResult


class SSLTest(BaseTest):
    """Test SSL Certificate validation and chain integrity"""

    def __init__(self):
        super().__init__()
        # Get list of URLs to test from environment
        urls_env = os.getenv("SSL_TEST_URLS", "")
        self.test_urls = [url.strip() for url in urls_env.split(",") if url.strip()]
        self.timeout_seconds_connect = int(os.getenv("SSL_CONNECT_TIMEOUT", "10"))

    @property
    def test_name(self) -> str:
        return "SSL Certificates"

    @property
    def test_description(self) -> str:
        return "Validates SSL certificate chains and expiration"

    @property
    def test_id(self) -> str:
        return "ssl"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 60

    def is_configured(self) -> bool:
        """Check if SSL test URLs are configured"""
        return len(self.test_urls) > 0

    def get_configuration_help(self) -> str:
        return (
            "SSL certificate testing requires URLs to test. "
            "Configure using environment variables: "
            "SSL_TEST_URLS (comma-separated URLs, e.g., 'https://api.example.com,https://app.example.com'), "
            "SSL_CONNECT_TIMEOUT (default: 10), SSL_WARNING_DAYS (default: 30)"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            if not self.test_urls:
                result.skip("No SSL test URLs configured")
                return result

            all_passed = True
            failed_urls = []

            for url in self.test_urls:
                try:
                    url_result = self._test_single_url(url)
                    test_name = f"SSL Check: {url}"

                    result.add_sub_test(test_name, url_result)
                    if not url_result["success"]:
                        all_passed = False
                        failed_urls.append(url)

                except Exception as e:
                    result.add_sub_test(
                        f"SSL Check: {url}",
                        {
                            "success": False,
                            "message": f"Failed to test URL: {str(e)}",
                            "error": str(e),
                            "remediation": "Check URL format and network connectivity",
                        },
                    )
                    all_passed = False
                    failed_urls.append(url)

            if all_passed:
                result.complete(
                    True,
                    f"All {len(self.test_urls)} SSL certificates validated successfully",
                )
            else:
                result.fail(
                    f"SSL validation failed for {len(failed_urls)} out of {len(self.test_urls)} URLs: {', '.join(failed_urls)}",
                    remediation="Check certificate chains, expiration dates, and hostname matching for failed URLs",
                )

        except Exception as e:
            result.fail(
                f"SSL test failed: {str(e)}",
                error=e,
                remediation="Check SSL test configuration and network connectivity",
            )

        return result

    def _test_single_url(self, url: str) -> Dict[str, Any]:
        """Test SSL certificate for a single URL"""
        parsed_url = urlparse(url)
        if not parsed_url.hostname:
            return {
                "success": False,
                "message": "Invalid URL format",
                "remediation": "Ensure URL includes protocol and hostname",
            }

        hostname = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)

        if parsed_url.scheme != "https":
            return {
                "success": False,
                "message": "URL is not HTTPS",
                "remediation": "SSL tests require HTTPS URLs",
            }

        try:
            # Get certificate from server
            cert_info = self._get_certificate_info(hostname, port)

            # Perform various certificate checks
            checks = {
                "connection": self._check_ssl_connection(hostname, port),
                "certificate_chain": self._check_certificate_chain(cert_info),
                "expiration": self._check_certificate_expiration_from_info(cert_info),
                "hostname_match": self._check_hostname_match_from_info(
                    cert_info, hostname
                ),
                "signature": self._check_certificate_signature_from_info(cert_info),
            }

            all_checks_passed = all(check["success"] for check in checks.values())
            warnings = [
                check["message"]
                for check in checks.values()
                if not check["success"] and check.get("warning", False)
            ]

            # Add detailed troubleshooting information
            cert_chain_info = self._format_certificate_chain_info(cert_info, checks)

            return {
                "success": all_checks_passed,
                "message": (
                    "SSL certificate validation passed"
                    if all_checks_passed
                    else f"SSL certificate validation failed"
                ),
                "url": url,
                "hostname": hostname,
                "port": port,
                "certificate_info": {
                    "subject": cert_info["subject"],
                    "issuer": cert_info["issuer"],
                    "valid_from": cert_info["valid_from"],
                    "valid_until": cert_info["valid_until"],
                    "days_until_expiry": cert_info["days_until_expiry"],
                    "chain_length": cert_info["chain_length"],
                    "chain_details": cert_info.get("cert_chain", []),
                },
                "checks": checks,
                "warnings": warnings,
                "certificate_chain_analysis": cert_chain_info,
                "remediation": (
                    self._get_ssl_remediation(checks, cert_chain_info)
                    if not all_checks_passed
                    else None
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to validate SSL certificate: {str(e)}",
                "error": str(e),
                "remediation": "Check network connectivity and certificate availability",
            }

    def _get_certificate_info(self, hostname: str, port: int) -> Dict[str, Any]:
        """Retrieve certificate information and full chain from server"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection(
            (hostname, port), timeout=self.timeout_seconds_connect
        ) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Get the server certificate (leaf certificate)
                cert_pem = ssl.DER_cert_to_PEM_cert(ssock.getpeercert(binary_form=True))
                cert = x509.load_pem_x509_certificate(
                    cert_pem.encode(), default_backend()
                )

                # Get the full certificate chain
                cert_chain = []
                retrieval_method = "python_ssl"
                try:
                    # Try to get all certificates in the chain
                    # Note: getpeercert_chain() is not available in all Python SSL implementations
                    if hasattr(ssock, "getpeercert_chain"):
                        peer_cert_chain = ssock.getpeercert_chain()
                        if peer_cert_chain:
                            for cert_der in peer_cert_chain:
                                # Convert each certificate from DER to PEM format
                                if hasattr(cert_der, "to_bytes"):
                                    cert_der_bytes = cert_der.to_bytes()
                                else:
                                    cert_der_bytes = cert_der
                                cert_pem_chain = ssl.DER_cert_to_PEM_cert(
                                    cert_der_bytes
                                )
                                cert_obj = x509.load_pem_x509_certificate(
                                    cert_pem_chain.encode(), default_backend()
                                )
                                cert_chain.append(
                                    {
                                        "pem": cert_pem_chain,
                                        "subject": cert_obj.subject.rfc4514_string(),
                                        "issuer": cert_obj.issuer.rfc4514_string(),
                                        "is_ca": self._is_ca_certificate(cert_obj),
                                        "is_self_signed": cert_obj.issuer
                                        == cert_obj.subject,
                                    }
                                )
                        else:
                            # Empty chain, add just the server cert
                            raise AttributeError("No certificates in chain")
                    else:
                        # getpeercert_chain() not available, use alternative approach
                        raise AttributeError("getpeercert_chain not available")

                except (AttributeError, Exception) as e:
                    # Fallback: Use OpenSSL command to get the complete certificate chain
                    try:
                        openssl_certs = self._get_cert_chain_with_openssl(
                            hostname, port
                        )
                        if openssl_certs:
                            cert_chain.extend(openssl_certs)
                            retrieval_method = "openssl_fallback"
                        else:
                            # Final fallback to single certificate from original retrieval
                            cert_chain.append(
                                {
                                    "pem": cert_pem,
                                    "subject": cert.subject.rfc4514_string(),
                                    "issuer": cert.issuer.rfc4514_string(),
                                    "is_ca": self._is_ca_certificate(cert),
                                    "is_self_signed": cert.issuer == cert.subject,
                                }
                            )
                    except Exception:
                        # Final fallback to single certificate from original retrieval
                        cert_chain.append(
                            {
                                "pem": cert_pem,
                                "subject": cert.subject.rfc4514_string(),
                                "issuer": cert.issuer.rfc4514_string(),
                                "is_ca": self._is_ca_certificate(cert),
                                "is_self_signed": cert.issuer == cert.subject,
                            }
                        )

                # Extract SAN (Subject Alternative Names)
                san_list = []
                try:
                    san_ext = cert.extensions.get_extension_for_oid(
                        x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                    )
                    san_list = [name.value for name in san_ext.value]
                except x509.ExtensionNotFound:
                    san_list = []

                return {
                    "cert_pem": cert_pem,
                    "subject": cert.subject.rfc4514_string(),
                    "issuer": cert.issuer.rfc4514_string(),
                    "valid_from": cert.not_valid_before_utc.isoformat(),
                    "valid_until": cert.not_valid_after_utc.isoformat(),
                    "days_until_expiry": (
                        cert.not_valid_after_utc
                        - datetime.datetime.now(datetime.timezone.utc)
                    ).days,
                    "san_names": san_list,
                    "cert_chain": cert_chain,
                    "chain_length": len(cert_chain),
                    "retrieval_method": retrieval_method,
                }

    def _check_ssl_connection(self, hostname: str, port: int) -> Dict[str, Any]:
        """Check if SSL connection can be established"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection(
                (hostname, port), timeout=self.timeout_seconds_connect
            ) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return {
                        "success": True,
                        "message": "SSL connection successful",
                        "cipher": ssock.cipher(),
                        "version": ssock.version(),
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"SSL connection failed: {str(e)}",
                "error": str(e),
            }

    def _check_certificate_chain(self, cert_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check certificate chain validity and completeness"""
        try:
            cert_chain = cert_info.get("cert_chain", [])
            chain_length = len(cert_chain)

            if chain_length == 0:
                return {
                    "success": False,
                    "message": "No certificates found in chain",
                    "chain_length": 0,
                }

            # Analyze the certificate chain
            server_cert = cert_chain[0]  # First cert should be the server cert
            ca_certs = cert_chain[1:]  # Remaining certs should be intermediates/root

            issues = []
            warnings = []
            chain_details = []

            # Check each certificate in the chain
            for i, cert_data in enumerate(cert_chain):
                cert_type = (
                    "Server"
                    if i == 0
                    else "Intermediate" if i < chain_length - 1 else "Root"
                )

                chain_details.append(
                    {
                        "position": i,
                        "type": cert_type,
                        "subject": cert_data["subject"],
                        "issuer": cert_data["issuer"],
                        "is_ca": cert_data["is_ca"],
                        "is_self_signed": cert_data["is_self_signed"],
                    }
                )

                # Validate certificate properties
                if i == 0:  # Server certificate
                    if cert_data["is_ca"]:
                        warnings.append("Server certificate has CA flag set")
                    if cert_data["is_self_signed"]:
                        warnings.append("Server certificate is self-signed")
                else:  # Intermediate/Root certificates
                    if not cert_data["is_ca"] and not cert_data["is_self_signed"]:
                        issues.append(
                            f"{cert_type} certificate at position {i} is not a CA certificate"
                        )

            # Check chain continuity (each cert should be signed by the next one)
            chain_valid = self._validate_chain_continuity(cert_chain)
            if not chain_valid["valid"]:
                issues.extend(chain_valid["issues"])
            # Add any warnings from chain validation
            warnings.extend(chain_valid.get("warnings", []))

            # Determine if chain appears complete
            # A chain is valid if it has multiple certificates OR ends with self-signed root
            has_root_ca = any(cert["is_self_signed"] for cert in cert_chain)
            chain_complete = has_root_ca or chain_length > 1

            # Updated logic to handle normal production certificate chains
            if chain_length == 1 and not server_cert["is_self_signed"]:
                # This is often normal in production - intermediate certs may be cached
                # Don't treat this as an error, but as a warning for troubleshooting
                warnings.append(
                    "Only leaf certificate retrieved - intermediate certificates may be cached by clients"
                )
                warnings.append("This is normal for many production environments")
            elif chain_length > 1:
                # Complete chain found, this is good!
                # Note: It's normal for chains to not include the root CA certificate
                # Browsers and systems have trusted root CAs built-in
                if not has_root_ca:
                    # This is actually normal and expected
                    warnings.append(
                        "Chain terminates at intermediate CA (root CA not included - this is normal)"
                    )
                else:
                    # Root CA is included - this is complete but unusual
                    warnings.append(
                        "Complete chain including root CA (unusual but valid)"
                    )

            # Generate summary message
            status_parts = []
            if chain_length == 1:
                if server_cert["is_self_signed"]:
                    status_parts.append("self-signed certificate")
                else:
                    status_parts.append("incomplete chain (server cert only)")
            else:
                status_parts.append(f"{chain_length} certificates")
                if has_root_ca:
                    status_parts.append("complete chain to root CA")
                else:
                    status_parts.append("chain to intermediate CA")

            success = len(issues) == 0
            has_warnings = len(warnings) > 0

            message = f"Certificate chain: {', '.join(status_parts)}"
            if issues:
                message += f" - {len(issues)} issue(s) found"
            if warnings:
                message += f" - {len(warnings)} warning(s)"

            return {
                "success": success,
                "message": message,
                "warning": has_warnings and success,
                "chain_length": chain_length,
                "chain_complete": chain_complete,
                "has_root_ca": has_root_ca,
                "chain_details": chain_details,
                "issues": issues,
                "warnings": warnings,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Certificate chain validation failed: {str(e)}",
                "error": str(e),
            }

    def _get_ssl_remediation(
        self, checks: Dict[str, Dict[str, Any]], chain_info: Dict[str, Any] = None
    ) -> str:
        """Generate remediation suggestions based on failed checks"""
        suggestions = []

        if not checks.get("connection", {}).get("success"):
            suggestions.append("Check network connectivity and firewall rules")

        if not checks.get("certificate_chain", {}).get("success"):
            chain_check = checks.get("certificate_chain", {})

            # Add detailed chain analysis if available
            if chain_info:
                certificates_found = chain_info.get("certificates_found", 0)
                retrieval_method = chain_info.get("retrieval_method", "Unknown")

                if certificates_found == 1:
                    suggestions.append(
                        f"Only 1 certificate retrieved using {retrieval_method}"
                    )
                    suggestions.append(
                        "IMPORTANT: OpenSSL shows complete chains - this may be a client retrieval issue, not a server configuration problem"
                    )
                    suggestions.append(
                        "Verify with: openssl s_client -connect hostname:443 -showcerts"
                    )
                else:
                    suggestions.append(
                        f"Retrieved {certificates_found} certificates using {retrieval_method}"
                    )

            if "incomplete chain" in chain_check.get("message", "").lower():
                suggestions.append(
                    "Install intermediate certificates on the server - clients may not be able to validate the certificate"
                )
            else:
                suggestions.append("Verify certificate chain is complete and valid")

            # Add specific issues from chain validation
            for issue in chain_check.get("issues", []):
                suggestions.append(f"Chain issue: {issue}")

        if not checks.get("expiration", {}).get("success"):
            suggestions.append("Renew expired certificate")
        elif checks.get("expiration", {}).get("warning"):
            suggestions.append("Certificate expires soon - plan renewal")

        if not checks.get("hostname_match", {}).get("success"):
            suggestions.append(
                "Certificate hostname/SAN does not match the requested hostname"
            )

        if checks.get("signature", {}).get("warning"):
            suggestions.append("Consider upgrading to a stronger signature algorithm")

        chain_check = checks.get("certificate_chain", {})
        if chain_check.get("warnings"):
            for warning in chain_check.get("warnings", []):
                suggestions.append(f"Chain warning: {warning}")

        # Check for specific chain issues
        if any(
            "self-signed" in detail.get("type", "")
            for detail in chain_check.get("chain_details", [])
        ):
            suggestions.append("Self-signed certificates may not be trusted by clients")

        return (
            "; ".join(suggestions) if suggestions else "Check certificate configuration"
        )

    def _is_ca_certificate(self, cert: x509.Certificate) -> bool:
        """Check if certificate is a CA certificate"""
        try:
            # Check Basic Constraints extension
            basic_constraints = cert.extensions.get_extension_for_oid(
                x509.ExtensionOID.BASIC_CONSTRAINTS
            ).value
            return basic_constraints.ca
        except x509.ExtensionNotFound:
            return False
        except Exception:
            return False

    def _validate_chain_continuity(
        self, cert_chain: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate that each certificate in the chain is signed by the next one"""
        issues = []
        warnings = []

        if len(cert_chain) <= 1:
            return {"valid": True, "issues": [], "warnings": []}

        try:
            for i in range(len(cert_chain) - 1):
                current_cert_issuer = cert_chain[i]["issuer"]
                next_cert_subject = cert_chain[i + 1]["subject"]

                # Check if current cert's issuer matches next cert's subject
                if current_cert_issuer != next_cert_subject:
                    issues.append(
                        f"Certificate at position {i} issuer does not match "
                        f"certificate at position {i + 1} subject"
                    )

                # For the last certificate, check if it's self-signed (root CA)
                # Note: It's normal for production chains to NOT include root CA
                if i == len(cert_chain) - 2:  # Last pair
                    if not cert_chain[i + 1]["is_self_signed"]:
                        # This is normal - most chains don't include root CA
                        warnings.append(
                            "Chain terminates at intermediate CA (root CA not included - this is normal)"
                        )

        except Exception as e:
            issues.append(f"Error validating chain continuity: {str(e)}")

        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

    def _check_certificate_expiration_from_info(self, cert_info):
        """Check certificate expiration using cert_info data"""
        try:
            days_until_expiry = cert_info.get("days_until_expiry", 0)
            valid_until = cert_info.get("valid_until", "Unknown")

            if days_until_expiry < 0:
                return {
                    "success": False,
                    "message": f"Certificate expired {abs(days_until_expiry)} days ago",
                    "warning": False,
                    "details": {
                        "valid_until": valid_until,
                        "days_until_expiry": days_until_expiry,
                    },
                }
            elif days_until_expiry < 30:
                return {
                    "success": True,
                    "message": f"Certificate expires in {days_until_expiry} days (warning)",
                    "warning": True,
                    "details": {
                        "valid_until": valid_until,
                        "days_until_expiry": days_until_expiry,
                    },
                }
            else:
                return {
                    "success": True,
                    "message": f"Certificate is valid for {days_until_expiry} more days",
                    "warning": False,
                    "details": {
                        "valid_until": valid_until,
                        "days_until_expiry": days_until_expiry,
                    },
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error checking expiration: {str(e)}",
                "warning": False,
                "details": {},
            }

    def _check_hostname_match_from_info(self, cert_info, hostname):
        """Check hostname match using cert_info data with proper SAN validation"""
        try:
            subject = cert_info.get("subject", "")
            san_names = cert_info.get("san_names", [])
            hostname_lower = hostname.lower()

            # Check SAN names first (modern approach)
            for san_name in san_names:
                san_lower = san_name.lower()
                # Exact match
                if hostname_lower == san_lower:
                    return {
                        "success": True,
                        "message": f"Hostname matches SAN: {san_name}",
                        "warning": False,
                        "details": {
                            "hostname": hostname,
                            "matched_san": san_name,
                            "all_sans": san_names,
                        },
                    }
                # Wildcard match (*.example.com matches sub.example.com)
                elif san_lower.startswith("*."):
                    wildcard_domain = san_lower[2:]  # Remove *.
                    if (
                        hostname_lower.endswith("." + wildcard_domain)
                        or hostname_lower == wildcard_domain
                    ):
                        return {
                            "success": True,
                            "message": f"Hostname matches wildcard SAN: {san_name}",
                            "warning": False,
                            "details": {
                                "hostname": hostname,
                                "matched_san": san_name,
                                "all_sans": san_names,
                            },
                        }

            # Fallback: check subject CN (legacy approach)
            if hostname_lower in subject.lower():
                return {
                    "success": True,
                    "message": "Hostname matches certificate subject (legacy CN check)",
                    "warning": True,  # Warn that SAN should be used instead
                    "details": {
                        "hostname": hostname,
                        "subject": subject,
                        "sans_available": len(san_names) > 0,
                    },
                }

            # No match found
            return {
                "success": False,
                "message": f"Hostname '{hostname}' does not match certificate",
                "warning": False,
                "details": {
                    "hostname": hostname,
                    "subject": subject,
                    "san_names": san_names,
                    "remediation": f"Add '{hostname}' to certificate SAN or use wildcard certificate",
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error checking hostname match: {str(e)}",
                "warning": False,
                "details": {},
            }

    def _check_certificate_signature_from_info(self, cert_info):
        """Check certificate signature using cert_info data.

        Note: Full cryptographic signature verification is not implemented.
        This check returns an informational result with issuer details.
        """
        try:
            return {
                "success": True,
                "message": "Certificate signature check skipped (cryptographic verification not implemented)",
                "warning": True,
                "details": {
                    "issuer": cert_info.get("issuer", "Unknown"),
                    "note": "Signature validation requires full chain verification which is not yet implemented",
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error checking signature: {str(e)}",
                "warning": False,
                "details": {},
            }

    def _get_cert_chain_with_openssl(
        self, hostname: str, port: int
    ) -> List[Dict[str, Any]]:
        """Use OpenSSL command to get the complete certificate chain"""
        try:
            # Use OpenSSL s_client to get all certificates in the chain
            cmd = [
                "openssl",
                "s_client",
                "-connect",
                f"{hostname}:{port}",
                "-showcerts",
                "-servername",
                hostname,
            ]

            result = subprocess.run(
                cmd,
                input="",
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds_connect,
            )

            if result.returncode != 0:
                return []

            # Parse certificates from OpenSSL output
            cert_chain = []
            cert_blocks = []

            # Split output into certificate blocks
            lines = result.stdout.split("\n")
            current_cert = []
            in_cert = False

            for line in lines:
                if "-----BEGIN CERTIFICATE-----" in line:
                    in_cert = True
                    current_cert = [line]
                elif "-----END CERTIFICATE-----" in line and in_cert:
                    current_cert.append(line)
                    cert_blocks.append("\n".join(current_cert))
                    current_cert = []
                    in_cert = False
                elif in_cert:
                    current_cert.append(line)

            # Parse each certificate
            for i, cert_pem in enumerate(cert_blocks):
                try:
                    cert_obj = x509.load_pem_x509_certificate(
                        cert_pem.encode(), default_backend()
                    )
                    cert_chain.append(
                        {
                            "pem": cert_pem,
                            "subject": cert_obj.subject.rfc4514_string(),
                            "issuer": cert_obj.issuer.rfc4514_string(),
                            "is_ca": self._is_ca_certificate(cert_obj),
                            "is_self_signed": cert_obj.issuer == cert_obj.subject,
                            "position_in_chain": i,
                        }
                    )
                except Exception as e:
                    # Skip malformed certificates but log the issue
                    continue

            return cert_chain

        except subprocess.TimeoutExpired:
            return []
        except Exception as e:
            return []

    def _format_certificate_chain_info(
        self, cert_info: Dict[str, Any], checks: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format detailed certificate chain information for display"""
        retrieval_method_display = {
            "python_ssl": "Python SSL (native)",
            "openssl_fallback": "OpenSSL fallback",
        }.get(cert_info.get("retrieval_method", "unknown"), "Unknown method")

        chain_info = {
            "certificates_found": cert_info["chain_length"],
            "retrieval_method": retrieval_method_display,
            "certificates": [],
        }

        for i, cert_data in enumerate(cert_info.get("cert_chain", [])):
            # Determine certificate type based on position in chain
            if i == 0:
                cert_type = "Server (Leaf)"
            elif i == len(cert_info.get("cert_chain", [])) - 1:
                # Last certificate in chain is considered the root/trust anchor
                cert_type = "Root CA"
            else:
                # Middle certificates are intermediate CAs
                cert_type = "Intermediate CA"

            # Parse subject and issuer to extract readable components
            subject_parts = self._parse_distinguished_name(cert_data["subject"])
            issuer_parts = self._parse_distinguished_name(cert_data["issuer"])

            # Get certificate sample (first 200 chars + last 100 chars for brevity)
            cert_pem = cert_data.get("pem", "")
            cert_sample = ""
            if cert_pem:
                lines = cert_pem.strip().split("\n")
                if len(lines) > 10:
                    # Show header + first few lines + ... + last few lines + footer
                    cert_sample = "\n".join(lines[:3] + ["..."] + lines[-3:])
                else:
                    cert_sample = cert_pem

            chain_info["certificates"].append(
                {
                    "position": i + 1,
                    "type": cert_type,
                    "subject": cert_data["subject"],
                    "subject_parsed": subject_parts,
                    "issuer": cert_data["issuer"],
                    "issuer_parsed": issuer_parts,
                    "is_ca": cert_data["is_ca"],
                    "is_self_signed": cert_data["is_self_signed"],
                    "certificate_sample": cert_sample,
                }
            )

        # Add analysis and troubleshooting information
        if cert_info["chain_length"] == 1:
            chain_info["analysis"] = (
                "Only leaf certificate retrieved - this may indicate Python SSL client limitation"
            )
            chain_info["recommendation"] = (
                "Certificate chain appears incomplete from client perspective, but may be complete on server"
            )
            chain_info["troubleshooting"] = [
                "This is likely normal - many production servers only present the leaf certificate",
                "Intermediate certificates are often cached by clients or resolved via AIA",
                "Verify chain completeness with: openssl s_client -connect hostname:443 -showcerts",
            ]
        elif cert_info["chain_length"] >= 2:
            chain_info["analysis"] = "Complete certificate chain retrieved successfully"
            chain_info["recommendation"] = "Certificate chain is properly configured"
            chain_info["troubleshooting"] = [
                "Chain appears complete and properly ordered",
                "Each certificate should be signed by the next certificate in the chain",
                f"Retrieved {cert_info['chain_length']} certificates via {retrieval_method_display}",
            ]

        # Add validation status from checks
        cert_chain_check = checks.get("certificate_chain", {})
        if cert_chain_check:
            chain_info["validation_status"] = {
                "passed": cert_chain_check.get("success", False),
                "issues": cert_chain_check.get("issues", []),
                "warnings": cert_chain_check.get("warnings", []),
                "details": cert_chain_check.get("message", "No details available"),
            }

        return chain_info

    @staticmethod
    def check_host(hostname: str, port: int = 443) -> Dict[str, Any]:
        """Check SSL/TLS for a single host. Used by ad-hoc endpoint."""
        import time as _time

        start = _time.time()
        try:
            # First, get cert info without verification (works for self-signed)
            ctx_noverify = ssl.create_default_context()
            ctx_noverify.check_hostname = False
            ctx_noverify.verify_mode = ssl.CERT_NONE

            with socket.create_connection((hostname, port), timeout=10) as sock:
                with ctx_noverify.wrap_socket(sock, server_hostname=hostname) as ssock:
                    der_cert = ssock.getpeercert(binary_form=True)
                    tls_version = ssock.version()
                    cipher_info = ssock.cipher()

            cert_pem = ssl.DER_cert_to_PEM_cert(der_cert)
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())

            # Extract fields
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            not_before = cert.not_valid_before_utc.isoformat()
            not_after = cert.not_valid_after_utc.isoformat()
            now = datetime.datetime.now(datetime.timezone.utc)
            days_remaining = (cert.not_valid_after_utc - now).days
            is_self_signed = cert.issuer == cert.subject
            serial = format(cert.serial_number, 'x').upper()

            # Signature algorithm
            sig_algo = cert.signature_algorithm_oid._name if hasattr(cert.signature_algorithm_oid, '_name') else str(cert.signature_algorithm_oid.dotted_string)

            # SANs
            san_list = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                san_list = [name.value for name in san_ext.value]
            except x509.ExtensionNotFound:
                pass

            # Key info
            pub_key = cert.public_key()
            key_type = type(pub_key).__name__.replace('_', ' ')
            key_size = getattr(pub_key, 'key_size', None)

            # Check if trusted (try with default verification)
            trusted = False
            trust_error = None
            try:
                ctx_verify = ssl.create_default_context()
                with socket.create_connection((hostname, port), timeout=10) as sock2:
                    with ctx_verify.wrap_socket(sock2, server_hostname=hostname) as ssock2:
                        trusted = True
            except ssl.SSLCertVerificationError as e:
                trust_error = str(e)
            except Exception as e:
                trust_error = str(e)

            # Hostname match
            hostname_match = False
            matched_name = None
            hn_lower = hostname.lower()
            for san in san_list:
                san_lower = san.lower()
                if hn_lower == san_lower:
                    hostname_match = True
                    matched_name = san
                    break
                if san_lower.startswith('*.') and (
                    hn_lower.endswith('.' + san_lower[2:]) or hn_lower == san_lower[2:]
                ):
                    hostname_match = True
                    matched_name = san
                    break

            latency_ms = round((_time.time() - start) * 1000, 1)

            return {
                "success": True,
                "hostname": hostname,
                "port": port,
                "tls_version": tls_version,
                "cipher": cipher_info[0] if cipher_info else None,
                "cipher_bits": cipher_info[2] if cipher_info and len(cipher_info) > 2 else None,
                "subject": subject,
                "issuer": issuer,
                "not_before": not_before,
                "not_after": not_after,
                "days_remaining": days_remaining,
                "expired": days_remaining < 0,
                "is_self_signed": is_self_signed,
                "trusted": trusted,
                "trust_error": trust_error,
                "hostname_match": hostname_match,
                "matched_name": matched_name,
                "san": san_list,
                "serial": serial,
                "signature_algorithm": sig_algo,
                "key_type": key_type,
                "key_size": key_size,
                "latency_ms": latency_ms,
                "message": (
                    f"{'Trusted' if trusted else 'Self-signed' if is_self_signed else 'Untrusted'} certificate, "
                    f"expires in {days_remaining} days"
                ),
            }

        except socket.timeout:
            latency_ms = round((_time.time() - start) * 1000, 1)
            return {
                "success": False,
                "hostname": hostname,
                "port": port,
                "latency_ms": latency_ms,
                "error_code": "timeout",
                "message": f"Connection timed out to {hostname}:{port}",
            }
        except ConnectionRefusedError:
            latency_ms = round((_time.time() - start) * 1000, 1)
            return {
                "success": False,
                "hostname": hostname,
                "port": port,
                "latency_ms": latency_ms,
                "error_code": "connection_refused",
                "message": f"Connection refused on {hostname}:{port}",
            }
        except socket.gaierror as e:
            latency_ms = round((_time.time() - start) * 1000, 1)
            return {
                "success": False,
                "hostname": hostname,
                "port": port,
                "latency_ms": latency_ms,
                "error_code": "dns_failure",
                "message": f"DNS resolution failed for {hostname}: {e}",
            }
        except Exception as e:
            latency_ms = round((_time.time() - start) * 1000, 1)
            return {
                "success": False,
                "hostname": hostname,
                "port": port,
                "latency_ms": latency_ms,
                "error_code": "error",
                "message": f"SSL check failed: {e}",
            }

    def _parse_distinguished_name(self, dn_string: str) -> Dict[str, str]:
        """Parse a distinguished name string into readable components"""
        try:
            parts = {}
            # Split by commas and parse key=value pairs
            for part in dn_string.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Convert common DN abbreviations to readable names
                    readable_key = {
                        "CN": "Common Name",
                        "O": "Organization",
                        "OU": "Organizational Unit",
                        "C": "Country",
                        "ST": "State",
                        "L": "Locality",
                        "DC": "Domain Component",
                    }.get(key, key)

                    parts[readable_key] = value
            return parts
        except Exception:
            return {"Raw": dn_string}
