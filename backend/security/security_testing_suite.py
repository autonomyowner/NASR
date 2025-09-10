"""
Security Testing and Validation Suite for The HIVE Translation Services

Comprehensive security testing tools including penetration testing,
vulnerability scanning, configuration validation, and compliance checking.
"""

import asyncio
import json
import time
import ssl
import socket
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import requests
import aiohttp
import paramiko
from urllib.parse import urlparse
import nmap
import re
import hashlib

logger = logging.getLogger(__name__)

class TestSeverity(Enum):
    """Security test result severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityTestResult:
    """Security test result structure"""
    test_name: str
    test_category: str
    severity: TestSeverity
    passed: bool
    description: str
    details: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime
    execution_time: float

class TLSSecurityTester:
    """TLS/SSL security testing"""
    
    def __init__(self):
        self.results = []
    
    async def test_tls_configuration(self, host: str, port: int) -> List[SecurityTestResult]:
        """Test TLS configuration for a service"""
        tests = []
        
        # Test TLS version support
        tests.append(await self._test_tls_versions(host, port))
        
        # Test cipher suites
        tests.append(await self._test_cipher_suites(host, port))
        
        # Test certificate validation
        tests.append(await self._test_certificate_validation(host, port))
        
        # Test certificate chain
        tests.append(await self._test_certificate_chain(host, port))
        
        # Test HSTS headers
        tests.append(await self._test_hsts_headers(host, port))
        
        return [test for test in tests if test is not None]
    
    async def _test_tls_versions(self, host: str, port: int) -> SecurityTestResult:
        """Test supported TLS versions"""
        start_time = time.time()
        supported_versions = []
        insecure_versions = []
        
        # Test various TLS versions
        tls_versions = {
            "SSLv2": ssl.PROTOCOL_SSLv23,  # Will fail on modern systems
            "SSLv3": ssl.PROTOCOL_SSLv23,
            "TLSv1.0": ssl.PROTOCOL_TLSv1,
            "TLSv1.1": ssl.PROTOCOL_TLSv1_1,
            "TLSv1.2": ssl.PROTOCOL_TLSv1_2,
        }
        
        # Add TLSv1.3 if available
        if hasattr(ssl, 'PROTOCOL_TLSv1_3'):
            tls_versions["TLSv1.3"] = ssl.PROTOCOL_TLSv1_3
        
        for version_name, protocol in tls_versions.items():
            try:
                context = ssl.SSLContext(protocol)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                with socket.create_connection((host, port), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=host) as ssock:
                        supported_versions.append({
                            "version": version_name,
                            "protocol": ssock.version()
                        })
                        
                        if version_name in ["SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1"]:
                            insecure_versions.append(version_name)
            except Exception:
                # Version not supported (which is good for insecure versions)
                pass
        
        execution_time = time.time() - start_time
        
        # Determine result
        if insecure_versions:
            severity = TestSeverity.HIGH
            passed = False
            description = f"Insecure TLS versions supported: {', '.join(insecure_versions)}"
            recommendations = [
                "Disable SSLv2, SSLv3, TLSv1.0, and TLSv1.1",
                "Use only TLSv1.2 and TLSv1.3",
                "Update TLS configuration to enforce minimum version"
            ]
        elif not any("TLSv1.2" in v["version"] or "TLSv1.3" in v["version"] for v in supported_versions):
            severity = TestSeverity.MEDIUM
            passed = False
            description = "No modern TLS versions (1.2+) supported"
            recommendations = ["Enable TLSv1.2 and TLSv1.3 support"]
        else:
            severity = TestSeverity.INFO
            passed = True
            description = "Only secure TLS versions supported"
            recommendations = []
        
        return SecurityTestResult(
            test_name="TLS Version Support",
            test_category="TLS/SSL",
            severity=severity,
            passed=passed,
            description=description,
            details={
                "supported_versions": supported_versions,
                "insecure_versions": insecure_versions
            },
            recommendations=recommendations,
            timestamp=datetime.utcnow(),
            execution_time=execution_time
        )
    
    async def _test_cipher_suites(self, host: str, port: int) -> SecurityTestResult:
        """Test cipher suite configuration"""
        start_time = time.time()
        
        try:
            # Use nmap to scan cipher suites
            nm = nmap.PortScanner()
            scan_result = nm.scan(host, str(port), arguments=f'--script ssl-enum-ciphers -p {port}')
            
            execution_time = time.time() - start_time
            
            # Parse cipher suite results
            weak_ciphers = []
            strong_ciphers = []
            
            if host in scan_result['scan']:
                host_data = scan_result['scan'][host]
                if 'tcp' in host_data and port in host_data['tcp']:
                    port_data = host_data['tcp'][port]
                    if 'script' in port_data:
                        ssl_script = port_data['script'].get('ssl-enum-ciphers', '')
                        
                        # Look for weak cipher indicators
                        weak_indicators = ['RC4', 'MD5', 'SHA1', 'DES', '3DES', 'NULL', 'EXPORT']
                        for indicator in weak_indicators:
                            if indicator.lower() in ssl_script.lower():
                                weak_ciphers.append(indicator)
            
            # Determine result
            if weak_ciphers:
                severity = TestSeverity.HIGH
                passed = False
                description = f"Weak cipher suites detected: {', '.join(weak_ciphers)}"
                recommendations = [
                    "Remove weak cipher suites from configuration",
                    "Use only AEAD cipher suites (AES-GCM, ChaCha20-Poly1305)",
                    "Prioritize perfect forward secrecy (ECDHE, DHE)"
                ]
            else:
                severity = TestSeverity.INFO
                passed = True
                description = "No obviously weak cipher suites detected"
                recommendations = []
            
            return SecurityTestResult(
                test_name="Cipher Suite Security",
                test_category="TLS/SSL",
                severity=severity,
                passed=passed,
                description=description,
                details={
                    "weak_ciphers": weak_ciphers,
                    "scan_output": ssl_script if 'ssl_script' in locals() else ""
                },
                recommendations=recommendations,
                timestamp=datetime.utcnow(),
                execution_time=execution_time
            )
            
        except Exception as e:
            return SecurityTestResult(
                test_name="Cipher Suite Security",
                test_category="TLS/SSL",
                severity=TestSeverity.MEDIUM,
                passed=False,
                description=f"Failed to test cipher suites: {str(e)}",
                details={"error": str(e)},
                recommendations=["Manually verify cipher suite configuration"],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )
    
    async def _test_certificate_validation(self, host: str, port: int) -> SecurityTestResult:
        """Test certificate validation"""
        start_time = time.time()
        
        try:
            # Get certificate information
            cert_info = ssl.get_server_certificate((host, port))
            cert = ssl.PEM_cert_to_DER_cert(cert_info)
            
            # Parse certificate
            import cryptography.x509
            parsed_cert = cryptography.x509.load_der_x509_certificate(cert)
            
            execution_time = time.time() - start_time
            
            # Check certificate validity
            now = datetime.utcnow()
            not_before = parsed_cert.not_valid_before.replace(tzinfo=None)
            not_after = parsed_cert.not_valid_after.replace(tzinfo=None)
            
            issues = []
            severity = TestSeverity.INFO
            
            # Check expiration
            days_until_expiry = (not_after - now).days
            if days_until_expiry < 0:
                issues.append("Certificate has expired")
                severity = TestSeverity.CRITICAL
            elif days_until_expiry < 30:
                issues.append(f"Certificate expires in {days_until_expiry} days")
                severity = TestSeverity.HIGH
            elif days_until_expiry < 90:
                issues.append(f"Certificate expires in {days_until_expiry} days")
                severity = TestSeverity.MEDIUM
            
            # Check if certificate is valid now
            if now < not_before:
                issues.append("Certificate is not yet valid")
                severity = TestSeverity.HIGH
            
            # Check key size
            public_key = parsed_cert.public_key()
            if hasattr(public_key, 'key_size'):
                key_size = public_key.key_size
                if key_size < 2048:
                    issues.append(f"Weak key size: {key_size} bits")
                    severity = TestSeverity.HIGH
            
            # Check signature algorithm
            sig_alg = parsed_cert.signature_algorithm_oid._name
            if 'md5' in sig_alg.lower() or 'sha1' in sig_alg.lower():
                issues.append(f"Weak signature algorithm: {sig_alg}")
                severity = TestSeverity.HIGH
            
            passed = len(issues) == 0
            description = "Certificate validation passed" if passed else f"Certificate issues: {'; '.join(issues)}"
            
            recommendations = []
            if issues:
                recommendations = [
                    "Renew certificate before expiration",
                    "Use at least 2048-bit RSA or 256-bit ECC keys",
                    "Use SHA-256 or stronger signature algorithms"
                ]
            
            return SecurityTestResult(
                test_name="Certificate Validation",
                test_category="TLS/SSL",
                severity=severity,
                passed=passed,
                description=description,
                details={
                    "subject": str(parsed_cert.subject),
                    "issuer": str(parsed_cert.issuer),
                    "not_before": not_before.isoformat(),
                    "not_after": not_after.isoformat(),
                    "days_until_expiry": days_until_expiry,
                    "signature_algorithm": sig_alg,
                    "key_size": getattr(public_key, 'key_size', 'unknown'),
                    "issues": issues
                },
                recommendations=recommendations,
                timestamp=datetime.utcnow(),
                execution_time=execution_time
            )
            
        except Exception as e:
            return SecurityTestResult(
                test_name="Certificate Validation",
                test_category="TLS/SSL",
                severity=TestSeverity.MEDIUM,
                passed=False,
                description=f"Failed to validate certificate: {str(e)}",
                details={"error": str(e)},
                recommendations=["Manually verify certificate configuration"],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )
    
    async def _test_certificate_chain(self, host: str, port: int) -> SecurityTestResult:
        """Test certificate chain validation"""
        start_time = time.time()
        
        try:
            # Test certificate chain validation
            context = ssl.create_default_context()
            
            with socket.create_connection((host, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    # If we get here, chain validation passed
                    cert_chain = ssock.getpeercert_chain()
                    
            execution_time = time.time() - start_time
            
            return SecurityTestResult(
                test_name="Certificate Chain",
                test_category="TLS/SSL",
                severity=TestSeverity.INFO,
                passed=True,
                description="Certificate chain validation passed",
                details={"chain_length": len(cert_chain) if cert_chain else 0},
                recommendations=[],
                timestamp=datetime.utcnow(),
                execution_time=execution_time
            )
            
        except ssl.SSLError as e:
            return SecurityTestResult(
                test_name="Certificate Chain",
                test_category="TLS/SSL",
                severity=TestSeverity.HIGH,
                passed=False,
                description=f"Certificate chain validation failed: {str(e)}",
                details={"ssl_error": str(e)},
                recommendations=[
                    "Verify certificate chain is complete",
                    "Ensure intermediate certificates are included",
                    "Check root CA is trusted"
                ],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return SecurityTestResult(
                test_name="Certificate Chain",
                test_category="TLS/SSL",
                severity=TestSeverity.MEDIUM,
                passed=False,
                description=f"Failed to test certificate chain: {str(e)}",
                details={"error": str(e)},
                recommendations=["Manually verify certificate chain"],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )
    
    async def _test_hsts_headers(self, host: str, port: int) -> SecurityTestResult:
        """Test HTTP Strict Transport Security headers"""
        start_time = time.time()
        
        try:
            url = f"https://{host}:{port}/health"
            response = requests.get(url, timeout=10, verify=False)
            
            execution_time = time.time() - start_time
            
            hsts_header = response.headers.get('Strict-Transport-Security')
            
            if hsts_header:
                # Parse HSTS header
                max_age = None
                include_subdomains = False
                preload = False
                
                parts = hsts_header.split(';')
                for part in parts:
                    part = part.strip()
                    if part.startswith('max-age='):
                        max_age = int(part.split('=')[1])
                    elif part == 'includeSubDomains':
                        include_subdomains = True
                    elif part == 'preload':
                        preload = True
                
                issues = []
                severity = TestSeverity.INFO
                
                if max_age is None:
                    issues.append("No max-age directive")
                    severity = TestSeverity.MEDIUM
                elif max_age < 31536000:  # 1 year
                    issues.append(f"HSTS max-age too short: {max_age} seconds")
                    severity = TestSeverity.LOW
                
                passed = len(issues) == 0
                description = "HSTS properly configured" if passed else f"HSTS issues: {'; '.join(issues)}"
                
                return SecurityTestResult(
                    test_name="HSTS Headers",
                    test_category="HTTP Security",
                    severity=severity,
                    passed=passed,
                    description=description,
                    details={
                        "hsts_header": hsts_header,
                        "max_age": max_age,
                        "include_subdomains": include_subdomains,
                        "preload": preload
                    },
                    recommendations=["Set HSTS max-age to at least 1 year", "Consider includeSubDomains directive"] if issues else [],
                    timestamp=datetime.utcnow(),
                    execution_time=execution_time
                )
            else:
                return SecurityTestResult(
                    test_name="HSTS Headers",
                    test_category="HTTP Security",
                    severity=TestSeverity.MEDIUM,
                    passed=False,
                    description="HSTS header not present",
                    details={"response_headers": dict(response.headers)},
                    recommendations=[
                        "Add Strict-Transport-Security header",
                        "Set appropriate max-age value",
                        "Consider includeSubDomains directive"
                    ],
                    timestamp=datetime.utcnow(),
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name="HSTS Headers",
                test_category="HTTP Security",
                severity=TestSeverity.LOW,
                passed=False,
                description=f"Failed to test HSTS headers: {str(e)}",
                details={"error": str(e)},
                recommendations=["Manually verify HSTS configuration"],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )

class AuthenticationSecurityTester:
    """Authentication and authorization testing"""
    
    async def test_jwt_security(self, auth_endpoint: str, api_key: str) -> List[SecurityTestResult]:
        """Test JWT token security"""
        tests = []
        
        # Test token generation
        tests.append(await self._test_token_generation(auth_endpoint, api_key))
        
        # Test token validation
        tests.append(await self._test_token_validation(auth_endpoint, api_key))
        
        # Test token expiration
        tests.append(await self._test_token_expiration(auth_endpoint, api_key))
        
        # Test invalid tokens
        tests.append(await self._test_invalid_tokens(auth_endpoint))
        
        return [test for test in tests if test is not None]
    
    async def _test_token_generation(self, endpoint: str, api_key: str) -> SecurityTestResult:
        """Test JWT token generation security"""
        start_time = time.time()
        
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "room_name": "test-room",
                "participant_name": "test-participant",
                "role": "listener"
            }
            
            response = requests.post(f"{endpoint}/token/room", json=payload, headers=headers, timeout=10)
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                token_data = response.json()
                token = token_data.get('token')
                
                # Basic JWT structure validation
                if token and token.count('.') == 2:
                    # Decode JWT header to check algorithm
                    import base64
                    header_b64 = token.split('.')[0]
                    # Add padding if needed
                    header_b64 += '=' * (4 - len(header_b64) % 4)
                    header = json.loads(base64.urlsafe_b64decode(header_b64))
                    
                    algorithm = header.get('alg')
                    
                    issues = []
                    severity = TestSeverity.INFO
                    
                    if algorithm == 'none':
                        issues.append("JWT uses 'none' algorithm - no signature")
                        severity = TestSeverity.CRITICAL
                    elif algorithm in ['HS256', 'HS384', 'HS512']:
                        # HMAC algorithms are OK but check for weak secrets
                        pass
                    elif algorithm in ['RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512']:
                        # Asymmetric algorithms are preferred
                        pass
                    else:
                        issues.append(f"Unknown or weak JWT algorithm: {algorithm}")
                        severity = TestSeverity.MEDIUM
                    
                    passed = len(issues) == 0
                    description = "JWT token generation secure" if passed else f"JWT issues: {'; '.join(issues)}"
                    
                    return SecurityTestResult(
                        test_name="JWT Token Generation",
                        test_category="Authentication",
                        severity=severity,
                        passed=passed,
                        description=description,
                        details={
                            "algorithm": algorithm,
                            "header": header,
                            "token_structure_valid": True
                        },
                        recommendations=["Use RS256 or ES256 algorithms", "Avoid 'none' algorithm"] if issues else [],
                        timestamp=datetime.utcnow(),
                        execution_time=execution_time
                    )
                else:
                    return SecurityTestResult(
                        test_name="JWT Token Generation",
                        test_category="Authentication",
                        severity=TestSeverity.HIGH,
                        passed=False,
                        description="Invalid JWT token structure",
                        details={"token": token, "response": token_data},
                        recommendations=["Verify JWT token generation implementation"],
                        timestamp=datetime.utcnow(),
                        execution_time=execution_time
                    )
            else:
                return SecurityTestResult(
                    test_name="JWT Token Generation",
                    test_category="Authentication",
                    severity=TestSeverity.MEDIUM,
                    passed=False,
                    description=f"Token generation failed: HTTP {response.status_code}",
                    details={"status_code": response.status_code, "response": response.text},
                    recommendations=["Check authentication endpoint configuration"],
                    timestamp=datetime.utcnow(),
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name="JWT Token Generation",
                test_category="Authentication",
                severity=TestSeverity.MEDIUM,
                passed=False,
                description=f"Failed to test token generation: {str(e)}",
                details={"error": str(e)},
                recommendations=["Verify authentication service is accessible"],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )
    
    async def _test_token_validation(self, endpoint: str, api_key: str) -> SecurityTestResult:
        """Test JWT token validation security"""
        start_time = time.time()
        
        try:
            # Generate a valid token first
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "room_name": "test-room",
                "participant_name": "test-participant",  
                "role": "listener"
            }
            
            response = requests.post(f"{endpoint}/token/room", json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                token = response.json().get('token')
                
                # Test token validation
                validation_response = requests.post(
                    f"{endpoint}/token/validate",
                    json={"token": token},
                    headers=headers,
                    timeout=10
                )
                
                execution_time = time.time() - start_time
                
                if validation_response.status_code == 200:
                    validation_data = validation_response.json()
                    
                    if validation_data.get('valid'):
                        return SecurityTestResult(
                            test_name="JWT Token Validation",
                            test_category="Authentication",
                            severity=TestSeverity.INFO,
                            passed=True,
                            description="JWT token validation working correctly",
                            details=validation_data,
                            recommendations=[],
                            timestamp=datetime.utcnow(),
                            execution_time=execution_time
                        )
                    else:
                        return SecurityTestResult(
                            test_name="JWT Token Validation",
                            test_category="Authentication",
                            severity=TestSeverity.HIGH,
                            passed=False,
                            description="Valid token rejected by validation",
                            details=validation_data,
                            recommendations=["Check token validation implementation"],
                            timestamp=datetime.utcnow(),
                            execution_time=execution_time
                        )
                else:
                    return SecurityTestResult(
                        test_name="JWT Token Validation",
                        test_category="Authentication",
                        severity=TestSeverity.MEDIUM,
                        passed=False,
                        description=f"Token validation endpoint error: HTTP {validation_response.status_code}",
                        details={"status_code": validation_response.status_code, "response": validation_response.text},
                        recommendations=["Check token validation endpoint"],
                        timestamp=datetime.utcnow(),
                        execution_time=execution_time
                    )
            else:
                return SecurityTestResult(
                    test_name="JWT Token Validation",
                    test_category="Authentication",
                    severity=TestSeverity.MEDIUM,
                    passed=False,
                    description="Could not generate token for validation test",
                    details={"token_generation_error": response.status_code},
                    recommendations=["Fix token generation before testing validation"],
                    timestamp=datetime.utcnow(),
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name="JWT Token Validation",
                test_category="Authentication",
                severity=TestSeverity.MEDIUM,
                passed=False,
                description=f"Failed to test token validation: {str(e)}",
                details={"error": str(e)},
                recommendations=["Verify authentication service configuration"],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )
    
    async def _test_token_expiration(self, endpoint: str, api_key: str) -> SecurityTestResult:
        """Test JWT token expiration handling"""
        start_time = time.time()
        
        try:
            # Generate a token with short expiration
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "room_name": "test-room",
                "participant_name": "test-participant",
                "role": "listener",
                "ttl_hours": 1  # Very short for testing
            }
            
            response = requests.post(f"{endpoint}/token/room", json=payload, headers=headers, timeout=10)
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                token_data = response.json()
                expires_at = token_data.get('expires_at')
                
                if expires_at:
                    # Parse expiration time
                    from dateutil import parser
                    exp_time = parser.parse(expires_at)
                    now = datetime.utcnow().replace(tzinfo=exp_time.tzinfo)
                    
                    time_until_expiry = (exp_time - now).total_seconds()
                    
                    if time_until_expiry > 0 and time_until_expiry <= 3600:  # 1 hour
                        return SecurityTestResult(
                            test_name="JWT Token Expiration",
                            test_category="Authentication",
                            severity=TestSeverity.INFO,
                            passed=True,
                            description="JWT token expiration properly configured",
                            details={
                                "expires_at": expires_at,
                                "seconds_until_expiry": time_until_expiry
                            },
                            recommendations=[],
                            timestamp=datetime.utcnow(),
                            execution_time=execution_time
                        )
                    else:
                        return SecurityTestResult(
                            test_name="JWT Token Expiration",
                            test_category="Authentication",
                            severity=TestSeverity.MEDIUM,
                            passed=False,
                            description=f"JWT token expiration issue: {time_until_expiry} seconds",
                            details={
                                "expires_at": expires_at,
                                "seconds_until_expiry": time_until_expiry
                            },
                            recommendations=["Verify token TTL configuration"],
                            timestamp=datetime.utcnow(),
                            execution_time=execution_time
                        )
                else:
                    return SecurityTestResult(
                        test_name="JWT Token Expiration",
                        test_category="Authentication",
                        severity=TestSeverity.MEDIUM,
                        passed=False,
                        description="JWT token missing expiration information",
                        details=token_data,
                        recommendations=["Ensure JWT tokens include expiration claims"],
                        timestamp=datetime.utcnow(),
                        execution_time=execution_time
                    )
            else:
                return SecurityTestResult(
                    test_name="JWT Token Expiration",
                    test_category="Authentication",
                    severity=TestSeverity.MEDIUM,
                    passed=False,
                    description="Could not generate token for expiration test",
                    details={"error": response.status_code},
                    recommendations=["Fix token generation endpoint"],
                    timestamp=datetime.utcnow(),
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name="JWT Token Expiration",
                test_category="Authentication",
                severity=TestSeverity.MEDIUM,
                passed=False,
                description=f"Failed to test token expiration: {str(e)}",
                details={"error": str(e)},
                recommendations=["Verify authentication service configuration"],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )
    
    async def _test_invalid_tokens(self, endpoint: str) -> SecurityTestResult:
        """Test handling of invalid tokens"""
        start_time = time.time()
        
        try:
            # Test various invalid tokens
            invalid_tokens = [
                "invalid.token.here",
                "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0In0.",  # No signature
                "",  # Empty token
                "not-a-jwt-at-all",
                "a.b"  # Wrong structure
            ]
            
            validation_results = []
            
            for token in invalid_tokens:
                try:
                    response = requests.post(
                        f"{endpoint}/token/validate",
                        json={"token": token},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('valid', False):
                            validation_results.append(f"Invalid token accepted: {token[:20]}...")
                    
                except Exception:
                    # Expected - invalid tokens should cause errors
                    pass
            
            execution_time = time.time() - start_time
            
            if validation_results:
                return SecurityTestResult(
                    test_name="Invalid Token Handling",
                    test_category="Authentication", 
                    severity=TestSeverity.CRITICAL,
                    passed=False,
                    description=f"Invalid tokens accepted: {len(validation_results)} cases",
                    details={"accepted_invalid_tokens": validation_results},
                    recommendations=[
                        "Fix token validation to reject invalid tokens",
                        "Implement proper JWT signature verification",
                        "Validate token structure and claims"
                    ],
                    timestamp=datetime.utcnow(),
                    execution_time=execution_time
                )
            else:
                return SecurityTestResult(
                    test_name="Invalid Token Handling",
                    test_category="Authentication",
                    severity=TestSeverity.INFO,
                    passed=True,
                    description="Invalid tokens properly rejected",
                    details={"tested_invalid_tokens": len(invalid_tokens)},
                    recommendations=[],
                    timestamp=datetime.utcnow(),
                    execution_time=execution_time
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name="Invalid Token Handling",
                test_category="Authentication",
                severity=TestSeverity.MEDIUM,
                passed=False,
                description=f"Failed to test invalid token handling: {str(e)}",
                details={"error": str(e)},
                recommendations=["Manually test token validation with invalid inputs"],
                timestamp=datetime.utcnow(),
                execution_time=time.time() - start_time
            )

class SecurityTestSuite:
    """Main security testing suite orchestrator"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tls_tester = TLSSecurityTester()
        self.auth_tester = AuthenticationSecurityTester()
        self.results = []
    
    async def run_comprehensive_tests(self, services: List[Dict[str, Any]]) -> List[SecurityTestResult]:
        """Run comprehensive security tests on all services"""
        all_results = []
        
        for service in services:
            service_name = service.get('name')
            host = service.get('host')
            port = service.get('port')
            service_type = service.get('type')
            
            logger.info(f"Testing security for {service_name} ({host}:{port})")
            
            try:
                # TLS/SSL tests for all HTTPS services
                if service.get('tls_enabled', True):
                    tls_results = await self.tls_tester.test_tls_configuration(host, port)
                    all_results.extend(tls_results)
                
                # Authentication tests for auth service
                if service_type == 'auth' and service.get('api_key'):
                    auth_endpoint = f"https://{host}:{port}"
                    auth_results = await self.auth_tester.test_jwt_security(auth_endpoint, service['api_key'])
                    all_results.extend(auth_results)
                
                # Service-specific tests
                service_results = await self._test_service_specific(service)
                all_results.extend(service_results)
                
            except Exception as e:
                logger.error(f"Failed to test {service_name}: {e}")
                # Add error result
                all_results.append(SecurityTestResult(
                    test_name=f"Service Test - {service_name}",
                    test_category="General",
                    severity=TestSeverity.MEDIUM,
                    passed=False,
                    description=f"Failed to test service: {str(e)}",
                    details={"error": str(e), "service": service},
                    recommendations=["Verify service is running and accessible"],
                    timestamp=datetime.utcnow(),
                    execution_time=0.0
                ))
        
        self.results.extend(all_results)
        return all_results
    
    async def _test_service_specific(self, service: Dict[str, Any]) -> List[SecurityTestResult]:
        """Run service-specific security tests"""
        results = []
        service_type = service.get('type')
        
        if service_type == 'livekit':
            results.extend(await self._test_livekit_security(service))
        elif service_type == 'redis':
            results.extend(await self._test_redis_security(service))
        elif service_type in ['stt', 'mt', 'tts']:
            results.extend(await self._test_translation_service_security(service))
        
        return results
    
    async def _test_livekit_security(self, service: Dict[str, Any]) -> List[SecurityTestResult]:
        """Test LiveKit-specific security"""
        # Placeholder for LiveKit-specific tests
        return []
    
    async def _test_redis_security(self, service: Dict[str, Any]) -> List[SecurityTestResult]:
        """Test Redis security configuration"""
        # Placeholder for Redis-specific tests
        return []
    
    async def _test_translation_service_security(self, service: Dict[str, Any]) -> List[SecurityTestResult]:
        """Test translation service security"""
        # Placeholder for translation service tests
        return []
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security test report"""
        if not self.results:
            return {"error": "No test results available"}
        
        # Group results by category and severity
        categories = {}
        severity_counts = {s.value: 0 for s in TestSeverity}
        
        for result in self.results:
            category = result.test_category
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
            severity_counts[result.severity.value] += 1
        
        # Calculate overall security score
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        critical_failures = severity_counts['critical']
        high_failures = severity_counts['high']
        
        # Security score calculation (0-100)
        base_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        penalty = (critical_failures * 20) + (high_failures * 10)
        security_score = max(0, base_score - penalty)
        
        # Determine overall status
        if security_score >= 90 and critical_failures == 0:
            overall_status = "SECURE"
        elif security_score >= 70 and critical_failures == 0:
            overall_status = "MODERATE"
        elif critical_failures > 0:
            overall_status = "CRITICAL"
        else:
            overall_status = "NEEDS_ATTENTION"
        
        return {
            "report_generated": datetime.utcnow().isoformat(),
            "overall_status": overall_status,
            "security_score": round(security_score, 2),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "severity_breakdown": severity_counts
            },
            "categories": {
                category: {
                    "total": len(results),
                    "passed": sum(1 for r in results if r.passed),
                    "failed": sum(1 for r in results if not r.passed)
                }
                for category, results in categories.items()
            },
            "detailed_results": [asdict(result) for result in self.results],
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate prioritized security recommendations"""
        recommendations = []
        
        # Collect all recommendations from failed tests
        failed_results = [r for r in self.results if not r.passed]
        
        # Group by severity
        critical_recs = []
        high_recs = []
        medium_recs = []
        
        for result in failed_results:
            for rec in result.recommendations:
                if result.severity == TestSeverity.CRITICAL and rec not in critical_recs:
                    critical_recs.append(rec)
                elif result.severity == TestSeverity.HIGH and rec not in high_recs:
                    high_recs.append(rec)
                elif result.severity == TestSeverity.MEDIUM and rec not in medium_recs:
                    medium_recs.append(rec)
        
        # Prioritize recommendations
        if critical_recs:
            recommendations.extend([f"CRITICAL: {rec}" for rec in critical_recs])
        if high_recs:
            recommendations.extend([f"HIGH: {rec}" for rec in high_recs])
        if medium_recs:
            recommendations.extend([f"MEDIUM: {rec}" for rec in medium_recs])
        
        return recommendations[:20]  # Limit to top 20 recommendations

# CLI interface for security testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Testing Suite for The HIVE")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--services", help="Services configuration file")
    parser.add_argument("--output", help="Output report file path")
    parser.add_argument("--format", choices=["json", "html"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    async def main():
        try:
            # Load configuration
            config = {}
            if args.config and Path(args.config).exists():
                with open(args.config) as f:
                    config = json.load(f)
            
            # Load services configuration
            services = []
            if args.services and Path(args.services).exists():
                with open(args.services) as f:
                    services = json.load(f)
            else:
                # Default services for The HIVE
                services = [
                    {"name": "auth-service", "type": "auth", "host": "localhost", "port": 8004, "tls_enabled": True},
                    {"name": "livekit", "type": "livekit", "host": "localhost", "port": 7880, "tls_enabled": True},
                    {"name": "stt-service", "type": "stt", "host": "localhost", "port": 8001, "tls_enabled": True},
                    {"name": "mt-service", "type": "mt", "host": "localhost", "port": 8002, "tls_enabled": True},
                    {"name": "tts-service", "type": "tts", "host": "localhost", "port": 8003, "tls_enabled": True},
                ]
            
            # Create test suite
            suite = SecurityTestSuite(config)
            
            # Run comprehensive tests
            logger.info("Starting comprehensive security tests...")
            results = await suite.run_comprehensive_tests(services)
            
            # Generate report
            report = suite.generate_security_report()
            
            # Output report
            if args.output:
                if args.format == "json":
                    with open(args.output, 'w') as f:
                        json.dump(report, f, indent=2, default=str)
                else:
                    # Generate HTML report (placeholder)
                    html_content = f"<html><body><h1>Security Report</h1><pre>{json.dumps(report, indent=2, default=str)}</pre></body></html>"
                    with open(args.output, 'w') as f:
                        f.write(html_content)
                
                logger.info(f"Security report saved to: {args.output}")
            else:
                print(json.dumps(report, indent=2, default=str))
            
            # Exit with appropriate code
            if report["overall_status"] in ["CRITICAL", "NEEDS_ATTENTION"]:
                exit(1)
            else:
                exit(0)
                
        except Exception as e:
            logger.error(f"Security testing failed: {e}")
            exit(1)
    
    # Run async main
    asyncio.run(main())