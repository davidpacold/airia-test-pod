from typing import Dict, Any, List, Optional
import os
import ssl
import socket
import datetime
from urllib.parse import urlparse
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from .base_test import BaseTest, TestResult
from ..models import TestStatus


class SSLTest(BaseTest):
    """Test SSL Certificate validation and chain integrity"""
    
    def __init__(self):
        super().__init__()
        # Get list of URLs to test from environment
        urls_env = os.getenv("SSL_TEST_URLS", "")
        self.test_urls = [url.strip() for url in urls_env.split(",") if url.strip()]
        self.timeout_seconds_connect = int(os.getenv("SSL_CONNECT_TIMEOUT", "10"))
        self.warning_days = int(os.getenv("SSL_WARNING_DAYS", "30"))
        
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
        return ("SSL certificate testing requires URLs to test. "
                "Configure using environment variables: "
                "SSL_TEST_URLS (comma-separated URLs, e.g., 'https://api.example.com,https://app.example.com'), "
                "SSL_CONNECT_TIMEOUT (default: 10), SSL_WARNING_DAYS (default: 30)")
        
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
                    
                    if url_result["success"]:
                        result.add_sub_test(test_name, url_result)
                    else:
                        result.add_sub_test(test_name, url_result)
                        all_passed = False
                        failed_urls.append(url)
                        
                except Exception as e:
                    result.add_sub_test(f"SSL Check: {url}", {
                        "success": False,
                        "message": f"Failed to test URL: {str(e)}",
                        "error": str(e),
                        "remediation": "Check URL format and network connectivity"
                    })
                    all_passed = False
                    failed_urls.append(url)
            
            if all_passed:
                result.complete(
                    True, 
                    f"All {len(self.test_urls)} SSL certificates validated successfully"
                )
            else:
                result.fail(
                    f"SSL validation failed for {len(failed_urls)} out of {len(self.test_urls)} URLs: {', '.join(failed_urls)}",
                    remediation="Check certificate chains, expiration dates, and hostname matching for failed URLs"
                )
                
        except Exception as e:
            result.fail(
                f"SSL test failed: {str(e)}",
                error=e,
                remediation="Check SSL test configuration and network connectivity"
            )
            
        return result
        
    def _test_single_url(self, url: str) -> Dict[str, Any]:
        """Test SSL certificate for a single URL"""
        parsed_url = urlparse(url)
        if not parsed_url.hostname:
            return {
                "success": False,
                "message": "Invalid URL format",
                "remediation": "Ensure URL includes protocol and hostname"
            }
            
        hostname = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
        
        if parsed_url.scheme != "https":
            return {
                "success": False,
                "message": "URL is not HTTPS",
                "remediation": "SSL tests require HTTPS URLs"
            }
        
        try:
            # Get certificate from server
            cert_info = self._get_certificate_info(hostname, port)
            
            # Perform various certificate checks
            checks = {
                "connection": self._check_ssl_connection(hostname, port),
                "certificate_chain": self._check_certificate_chain(cert_info),
                "expiration": self._check_certificate_expiration(cert_info["cert"]),
                "hostname_match": self._check_hostname_match(cert_info["cert"], hostname),
                "signature": self._check_certificate_signature(cert_info["cert"])
            }
            
            all_checks_passed = all(check["success"] for check in checks.values())
            warnings = [check["message"] for check in checks.values() 
                       if not check["success"] and check.get("warning", False)]
            
            return {
                "success": all_checks_passed,
                "message": "SSL certificate validation passed" if all_checks_passed 
                          else f"SSL certificate validation failed",
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
                    "chain_details": cert_info.get("cert_chain", [])
                },
                "checks": checks,
                "warnings": warnings,
                "remediation": self._get_ssl_remediation(checks) if not all_checks_passed else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to validate SSL certificate: {str(e)}",
                "error": str(e),
                "remediation": "Check network connectivity and certificate availability"
            }
    
    def _get_certificate_info(self, hostname: str, port: int) -> Dict[str, Any]:
        """Retrieve certificate information and full chain from server"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((hostname, port), timeout=self.timeout_seconds_connect) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Get the server certificate (leaf certificate)
                cert_pem = ssl.DER_cert_to_PEM_cert(ssock.getpeercert(binary_form=True))
                cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
                
                # Get the full certificate chain
                cert_chain = []
                try:
                    # Try to get all certificates in the chain
                    # Note: getpeercert_chain() is not available in all Python SSL implementations
                    if hasattr(ssock, 'getpeercert_chain'):
                        peer_cert_chain = ssock.getpeercert_chain()
                        if peer_cert_chain:
                            for cert_der in peer_cert_chain:
                                # Convert each certificate from DER to PEM format
                                if hasattr(cert_der, 'to_bytes'):
                                    cert_der_bytes = cert_der.to_bytes()
                                else:
                                    cert_der_bytes = cert_der
                                cert_pem_chain = ssl.DER_cert_to_PEM_cert(cert_der_bytes)
                                cert_obj = x509.load_pem_x509_certificate(cert_pem_chain.encode(), default_backend())
                                cert_chain.append({
                                    "cert": cert_obj,
                                    "pem": cert_pem_chain,
                                    "subject": cert_obj.subject.rfc4514_string(),
                                    "issuer": cert_obj.issuer.rfc4514_string(),
                                    "is_ca": self._is_ca_certificate(cert_obj),
                                    "is_self_signed": cert_obj.issuer == cert_obj.subject
                                })
                        else:
                            # Empty chain, add just the server cert
                            raise AttributeError("No certificates in chain")
                    else:
                        # getpeercert_chain() not available, use alternative approach
                        raise AttributeError("getpeercert_chain not available")
                        
                except (AttributeError, Exception) as e:
                    # Fallback: try to use OpenSSL approach for chain retrieval
                    try:
                        # Alternative approach using a fresh connection with validation enabled
                        chain_context = ssl.create_default_context()
                        with socket.create_connection((hostname, port), timeout=self.timeout_seconds_connect) as chain_sock:
                            with chain_context.wrap_socket(chain_sock, server_hostname=hostname) as chain_ssock:
                                # This will validate and potentially give us more info about the chain
                                server_cert_der = chain_ssock.getpeercert(binary_form=True)
                                server_cert_pem = ssl.DER_cert_to_PEM_cert(server_cert_der)
                                server_cert_obj = x509.load_pem_x509_certificate(server_cert_pem.encode(), default_backend())
                                
                                cert_chain.append({
                                    "cert": server_cert_obj,
                                    "pem": server_cert_pem,
                                    "subject": server_cert_obj.subject.rfc4514_string(),
                                    "issuer": server_cert_obj.issuer.rfc4514_string(),
                                    "is_ca": self._is_ca_certificate(server_cert_obj),
                                    "is_self_signed": server_cert_obj.issuer == server_cert_obj.subject
                                })
                    except Exception:
                        # Final fallback to single certificate from original retrieval
                        cert_chain.append({
                            "cert": cert,
                            "pem": cert_pem,
                            "subject": cert.subject.rfc4514_string(),
                            "issuer": cert.issuer.rfc4514_string(),
                            "is_ca": self._is_ca_certificate(cert),
                            "is_self_signed": cert.issuer == cert.subject
                        })
                
                return {
                    "cert": cert,
                    "cert_pem": cert_pem,
                    "subject": cert.subject.rfc4514_string(),
                    "issuer": cert.issuer.rfc4514_string(),
                    "valid_from": cert.not_valid_before_utc.isoformat(),
                    "valid_until": cert.not_valid_after_utc.isoformat(),
                    "days_until_expiry": (cert.not_valid_after_utc.replace(tzinfo=None) - datetime.datetime.now()).days,
                    "cert_chain": cert_chain,
                    "chain_length": len(cert_chain)
                }
    
    def _check_ssl_connection(self, hostname: str, port: int) -> Dict[str, Any]:
        """Check if SSL connection can be established"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=self.timeout_seconds_connect) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return {
                        "success": True,
                        "message": "SSL connection successful",
                        "cipher": ssock.cipher(),
                        "version": ssock.version()
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"SSL connection failed: {str(e)}",
                "error": str(e)
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
                    "chain_length": 0
                }
            
            # Analyze the certificate chain
            server_cert = cert_chain[0]  # First cert should be the server cert
            ca_certs = cert_chain[1:]    # Remaining certs should be intermediates/root
            
            issues = []
            warnings = []
            chain_details = []
            
            # Check each certificate in the chain
            for i, cert_data in enumerate(cert_chain):
                cert_type = "Server" if i == 0 else "Intermediate" if i < chain_length - 1 else "Root"
                
                chain_details.append({
                    "position": i,
                    "type": cert_type,
                    "subject": cert_data["subject"],
                    "issuer": cert_data["issuer"],
                    "is_ca": cert_data["is_ca"],
                    "is_self_signed": cert_data["is_self_signed"]
                })
                
                # Validate certificate properties
                if i == 0:  # Server certificate
                    if cert_data["is_ca"]:
                        warnings.append("Server certificate has CA flag set")
                    if cert_data["is_self_signed"]:
                        warnings.append("Server certificate is self-signed")
                else:  # Intermediate/Root certificates
                    if not cert_data["is_ca"] and not cert_data["is_self_signed"]:
                        issues.append(f"{cert_type} certificate at position {i} is not a CA certificate")
            
            # Check chain continuity (each cert should be signed by the next one)
            chain_valid = self._validate_chain_continuity(cert_chain)
            if not chain_valid["valid"]:
                issues.extend(chain_valid["issues"])
            
            # Determine if chain appears complete
            has_root_ca = any(cert["is_self_signed"] for cert in cert_chain)
            chain_complete = has_root_ca or chain_length > 1
            
            if chain_length == 1 and not server_cert["is_self_signed"]:
                issues.append("Certificate chain appears incomplete - no intermediate certificates found")
                issues.append("This may cause SSL/TLS validation failures for some clients")
            
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
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Certificate chain validation failed: {str(e)}",
                "error": str(e)
            }
    
    def _check_certificate_expiration(self, cert: x509.Certificate) -> Dict[str, Any]:
        """Check certificate expiration"""
        try:
            now = datetime.datetime.now()
            cert_expiry = cert.not_valid_after_utc.replace(tzinfo=None)
            days_until_expiry = (cert_expiry - now).days
            
            if cert_expiry < now:
                return {
                    "success": False,
                    "message": f"Certificate expired {abs(days_until_expiry)} days ago",
                    "days_until_expiry": days_until_expiry
                }
            elif days_until_expiry < self.warning_days:
                return {
                    "success": True,
                    "message": f"Certificate expires in {days_until_expiry} days (warning threshold: {self.warning_days})",
                    "days_until_expiry": days_until_expiry,
                    "warning": True
                }
            else:
                return {
                    "success": True,
                    "message": f"Certificate expires in {days_until_expiry} days",
                    "days_until_expiry": days_until_expiry
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Certificate expiration check failed: {str(e)}",
                "error": str(e)
            }
    
    def _check_hostname_match(self, cert: x509.Certificate, hostname: str) -> Dict[str, Any]:
        """Check if certificate matches hostname"""
        try:
            # Get Subject Alternative Names
            san_extension = None
            try:
                san_extension = cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            except x509.ExtensionNotFound:
                pass
            
            # Get Common Name from subject
            common_name = None
            for attribute in cert.subject:
                if attribute.oid == x509.NameOID.COMMON_NAME:
                    common_name = attribute.value
                    break
            
            # Check hostname against SAN and CN
            valid_hostnames = []
            if san_extension:
                for san in san_extension.value:
                    if isinstance(san, x509.DNSName):
                        valid_hostnames.append(san.value)
            
            if common_name:
                valid_hostnames.append(common_name)
            
            # Simple hostname matching (not implementing full wildcard matching)
            hostname_matches = any(
                hostname.lower() == valid_hostname.lower() or
                (valid_hostname.startswith('*.') and hostname.lower().endswith(valid_hostname[2:].lower()))
                for valid_hostname in valid_hostnames
            )
            
            return {
                "success": hostname_matches,
                "message": f"Hostname {'matches' if hostname_matches else 'does not match'} certificate",
                "hostname": hostname,
                "valid_hostnames": valid_hostnames,
                "common_name": common_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Hostname verification failed: {str(e)}",
                "error": str(e)
            }
    
    def _check_certificate_signature(self, cert: x509.Certificate) -> Dict[str, Any]:
        """Check certificate signature algorithm"""
        try:
            sig_algorithm = cert.signature_algorithm_oid._name
            
            # Check for weak signature algorithms
            weak_algorithms = ['md5', 'sha1']
            is_weak = any(weak_alg in sig_algorithm.lower() for weak_alg in weak_algorithms)
            
            return {
                "success": not is_weak,
                "message": f"Signature algorithm: {sig_algorithm}" + (" (weak)" if is_weak else ""),
                "algorithm": sig_algorithm,
                "warning": is_weak
            }
            
        except Exception as e:
            return {
                "success": True,  # Don't fail the test for this
                "message": f"Could not determine signature algorithm: {str(e)}",
                "warning": True
            }
    
    def _get_ssl_remediation(self, checks: Dict[str, Dict[str, Any]]) -> str:
        """Generate remediation suggestions based on failed checks"""
        suggestions = []
        
        if not checks.get("connection", {}).get("success"):
            suggestions.append("Check network connectivity and firewall rules")
        
        if not checks.get("certificate_chain", {}).get("success"):
            chain_check = checks.get("certificate_chain", {})
            if "incomplete chain" in chain_check.get("message", "").lower():
                suggestions.append("Install intermediate certificates on the server - clients may not be able to validate the certificate")
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
            suggestions.append("Certificate hostname/SAN does not match the requested hostname")
        
        if checks.get("signature", {}).get("warning"):
            suggestions.append("Consider upgrading to a stronger signature algorithm")
        
        chain_check = checks.get("certificate_chain", {})
        if chain_check.get("warnings"):
            for warning in chain_check.get("warnings", []):
                suggestions.append(f"Chain warning: {warning}")
        
        # Check for specific chain issues
        if any("self-signed" in detail.get("type", "") for detail in chain_check.get("chain_details", [])):
            suggestions.append("Self-signed certificates may not be trusted by clients")
        
        return "; ".join(suggestions) if suggestions else "Check certificate configuration"
    
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
    
    def _validate_chain_continuity(self, cert_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that each certificate in the chain is signed by the next one"""
        issues = []
        
        if len(cert_chain) <= 1:
            return {"valid": True, "issues": []}
        
        try:
            for i in range(len(cert_chain) - 1):
                current_cert = cert_chain[i]["cert"]
                next_cert = cert_chain[i + 1]["cert"]
                
                # Check if current cert's issuer matches next cert's subject
                if current_cert.issuer != next_cert.subject:
                    issues.append(
                        f"Certificate at position {i} issuer does not match "
                        f"certificate at position {i + 1} subject"
                    )
                
                # For the last certificate, check if it's self-signed (root CA)
                if i == len(cert_chain) - 2:  # Last pair
                    if not next_cert.issuer == next_cert.subject:
                        issues.append("Chain does not end with a self-signed root CA certificate")
            
        except Exception as e:
            issues.append(f"Error validating chain continuity: {str(e)}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }