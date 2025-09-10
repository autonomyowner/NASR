"""
TLS/mTLS Certificate Management for The HIVE Translation Services

Automated certificate authority management and service certificate generation
for secure inter-service communication with automatic rotation and monitoring.
"""

import os
import time
import json
import hashlib
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import logging
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import ipaddress

logger = logging.getLogger(__name__)

@dataclass
class CertificateConfig:
    """Certificate configuration"""
    # Certificate Authority settings
    ca_key_size: int = 4096
    ca_validity_days: int = 3650  # 10 years
    ca_country: str = "US"
    ca_organization: str = "The HIVE"
    ca_common_name: str = "The HIVE Root CA"
    
    # Service certificate settings
    service_key_size: int = 2048
    service_validity_days: int = 365  # 1 year
    
    # Renewal settings
    renewal_days_before_expiry: int = 30
    auto_renewal_enabled: bool = True
    
    # Certificate storage
    cert_dir: str = "/etc/ssl/hive"
    private_dir: str = "/etc/ssl/private/hive"
    
    # Subject settings
    country: str = "US"
    state: str = "CA"
    locality: str = "San Francisco"
    organization: str = "The HIVE Translation Services"

class ServiceCertificate:
    """Service certificate with metadata"""
    
    def __init__(
        self,
        service_name: str,
        cert_path: str,
        key_path: str,
        ca_path: str,
        expires_at: datetime,
        domains: List[str],
        ips: List[str]
    ):
        self.service_name = service_name
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.expires_at = expires_at
        self.domains = domains
        self.ips = ips
        self.created_at = datetime.utcnow()
    
    def days_until_expiry(self) -> int:
        """Get days until certificate expires"""
        delta = self.expires_at - datetime.utcnow()
        return delta.days
    
    def needs_renewal(self, renewal_threshold: int = 30) -> bool:
        """Check if certificate needs renewal"""
        return self.days_until_expiry() <= renewal_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "service_name": self.service_name,
            "cert_path": self.cert_path,
            "key_path": self.key_path,
            "ca_path": self.ca_path,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "domains": self.domains,
            "ips": self.ips,
            "days_until_expiry": self.days_until_expiry()
        }

class CertificateAuthority:
    """Certificate Authority management"""
    
    def __init__(self, config: CertificateConfig):
        self.config = config
        self.ca_cert_path = os.path.join(config.cert_dir, "ca.pem")
        self.ca_key_path = os.path.join(config.private_dir, "ca-key.pem")
        
        # Ensure directories exist
        os.makedirs(config.cert_dir, mode=0o755, exist_ok=True)
        os.makedirs(config.private_dir, mode=0o700, exist_ok=True)
    
    def create_ca(self, force: bool = False) -> Tuple[str, str]:
        """
        Create Certificate Authority certificate and key
        
        Args:
            force: Force recreation even if CA exists
            
        Returns:
            Tuple of (cert_path, key_path)
        """
        if not force and os.path.exists(self.ca_cert_path) and os.path.exists(self.ca_key_path):
            logger.info("CA certificate already exists")
            return self.ca_cert_path, self.ca_key_path
        
        logger.info("Creating Certificate Authority...")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.config.ca_key_size,
            backend=default_backend()
        )
        
        # Create subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, self.config.ca_country),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.config.ca_organization),
            x509.NameAttribute(NameOID.COMMON_NAME, self.config.ca_common_name)
        ])
        
        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            subject  # Self-signed
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=self.config.ca_validity_days)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Write certificate
        with open(self.ca_cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write private key
        with open(self.ca_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Set secure permissions
        os.chmod(self.ca_key_path, 0o600)
        os.chmod(self.ca_cert_path, 0o644)
        
        logger.info(f"CA certificate created: {self.ca_cert_path}")
        logger.info(f"CA private key created: {self.ca_key_path}")
        
        return self.ca_cert_path, self.ca_key_path
    
    def load_ca(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Load CA certificate and private key"""
        if not os.path.exists(self.ca_cert_path) or not os.path.exists(self.ca_key_path):
            raise FileNotFoundError("CA certificate or key not found. Create CA first.")
        
        # Load certificate
        with open(self.ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        
        # Load private key
        with open(self.ca_key_path, "rb") as f:
            ca_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        return ca_cert, ca_key

class CertificateManager:
    """Main certificate management system"""
    
    # Service definitions with networking requirements
    SERVICES = {
        "livekit": {
            "domains": ["livekit", "livekit-server"],
            "ips": ["172.20.0.10"],
            "client_cert": True
        },
        "stt-service": {
            "domains": ["stt-service", "hive-stt"],
            "ips": ["172.20.0.11"],
            "client_cert": True
        },
        "mt-service": {
            "domains": ["mt-service", "hive-mt"],
            "ips": ["172.20.0.12"],
            "client_cert": True
        },
        "tts-service": {
            "domains": ["tts-service", "hive-tts"],
            "ips": ["172.20.0.13"],
            "client_cert": True
        },
        "auth-service": {
            "domains": ["auth-service", "hive-auth"],
            "ips": ["172.20.0.14"],
            "client_cert": True
        },
        "redis": {
            "domains": ["redis", "hive-redis"],
            "ips": ["172.20.0.20"],
            "client_cert": False
        },
        "nginx": {
            "domains": ["nginx", "hive-nginx", "localhost"],
            "ips": ["127.0.0.1"],
            "client_cert": False
        }
    }
    
    def __init__(self, config: CertificateConfig):
        self.config = config
        self.ca = CertificateAuthority(config)
        self.certificates: Dict[str, ServiceCertificate] = {}
        self.cert_metadata_file = os.path.join(config.cert_dir, "certificates.json")
        
        # Load existing certificate metadata
        self._load_certificate_metadata()
    
    def initialize_ca(self, force: bool = False) -> bool:
        """Initialize Certificate Authority"""
        try:
            self.ca.create_ca(force=force)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize CA: {e}")
            return False
    
    def generate_service_certificate(
        self,
        service_name: str,
        domains: Optional[List[str]] = None,
        ips: Optional[List[str]] = None,
        force: bool = False
    ) -> Optional[ServiceCertificate]:
        """
        Generate certificate for a service
        
        Args:
            service_name: Name of the service
            domains: List of domain names
            ips: List of IP addresses
            force: Force regeneration even if certificate exists
            
        Returns:
            ServiceCertificate object or None if failed
        """
        # Use predefined service configuration if available
        if service_name in self.SERVICES:
            service_config = self.SERVICES[service_name]
            domains = domains or service_config["domains"]
            ips = ips or service_config["ips"]
        
        domains = domains or [service_name]
        ips = ips or []
        
        cert_path = os.path.join(self.config.cert_dir, f"{service_name}.pem")
        key_path = os.path.join(self.config.private_dir, f"{service_name}-key.pem")
        
        # Check if certificate exists and is valid
        if not force and service_name in self.certificates:
            cert = self.certificates[service_name]
            if not cert.needs_renewal(self.config.renewal_days_before_expiry):
                logger.info(f"Certificate for {service_name} is still valid")
                return cert
        
        try:
            logger.info(f"Generating certificate for service: {service_name}")
            
            # Load CA
            ca_cert, ca_key = self.ca.load_ca()
            
            # Generate private key for service
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=self.config.service_key_size,
                backend=default_backend()
            )
            
            # Create subject
            subject = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, self.config.country),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, self.config.state),
                x509.NameAttribute(NameOID.LOCALITY_NAME, self.config.locality),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.config.organization),
                x509.NameAttribute(NameOID.COMMON_NAME, domains[0])
            ])
            
            # Create Subject Alternative Name extension
            san_names = []
            
            # Add DNS names
            for domain in domains:
                san_names.append(x509.DNSName(domain))
            
            # Add IP addresses
            for ip in ips:
                try:
                    san_names.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
                except ValueError:
                    logger.warning(f"Invalid IP address: {ip}")
            
            # Build certificate
            cert_builder = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                ca_cert.subject
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=self.config.service_validity_days)
            )
            
            # Add extensions
            cert_builder = cert_builder.add_extension(
                x509.SubjectAlternativeName(san_names),
                critical=False
            ).add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True
            ).add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH
                ]),
                critical=True
            ).add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False
            ).add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                critical=False
            )
            
            # Sign certificate
            cert = cert_builder.sign(ca_key, hashes.SHA256(), default_backend())
            
            # Write certificate
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Set secure permissions
            os.chmod(key_path, 0o600)
            os.chmod(cert_path, 0o644)
            
            # Create ServiceCertificate object
            service_cert = ServiceCertificate(
                service_name=service_name,
                cert_path=cert_path,
                key_path=key_path,
                ca_path=self.ca.ca_cert_path,
                expires_at=cert.not_valid_after,
                domains=domains,
                ips=ips
            )
            
            # Store in memory and persist metadata
            self.certificates[service_name] = service_cert
            self._save_certificate_metadata()
            
            logger.info(f"Certificate generated for {service_name}: {cert_path}")
            
            return service_cert
            
        except Exception as e:
            logger.error(f"Failed to generate certificate for {service_name}: {e}")
            return None
    
    def generate_all_service_certificates(self, force: bool = False) -> Dict[str, bool]:
        """Generate certificates for all predefined services"""
        results = {}
        
        for service_name in self.SERVICES.keys():
            logger.info(f"Generating certificate for {service_name}...")
            cert = self.generate_service_certificate(service_name, force=force)
            results[service_name] = cert is not None
        
        return results
    
    def check_certificate_expiry(self) -> Dict[str, Dict[str, Any]]:
        """Check expiry status of all certificates"""
        status = {}
        
        for service_name, cert in self.certificates.items():
            days_left = cert.days_until_expiry()
            needs_renewal = cert.needs_renewal(self.config.renewal_days_before_expiry)
            
            status[service_name] = {
                "days_until_expiry": days_left,
                "expires_at": cert.expires_at.isoformat(),
                "needs_renewal": needs_renewal,
                "status": "expired" if days_left < 0 else ("expires_soon" if needs_renewal else "valid")
            }
        
        return status
    
    def renew_expiring_certificates(self) -> Dict[str, bool]:
        """Automatically renew certificates that are expiring soon"""
        if not self.config.auto_renewal_enabled:
            logger.info("Auto-renewal is disabled")
            return {}
        
        results = {}
        expiry_status = self.check_certificate_expiry()
        
        for service_name, status in expiry_status.items():
            if status["needs_renewal"]:
                logger.info(f"Renewing certificate for {service_name} (expires in {status['days_until_expiry']} days)")
                cert = self.generate_service_certificate(service_name, force=True)
                results[service_name] = cert is not None
        
        return results
    
    def get_certificate_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get certificate information for a service"""
        if service_name not in self.certificates:
            return None
        
        return self.certificates[service_name].to_dict()
    
    def list_certificates(self) -> Dict[str, Dict[str, Any]]:
        """List all certificates and their status"""
        result = {}
        expiry_status = self.check_certificate_expiry()
        
        for service_name, cert in self.certificates.items():
            cert_info = cert.to_dict()
            cert_info.update(expiry_status.get(service_name, {}))
            result[service_name] = cert_info
        
        return result
    
    def _load_certificate_metadata(self):
        """Load certificate metadata from file"""
        if not os.path.exists(self.cert_metadata_file):
            return
        
        try:
            with open(self.cert_metadata_file, 'r') as f:
                data = json.load(f)
            
            for service_name, cert_data in data.items():
                cert = ServiceCertificate(
                    service_name=cert_data["service_name"],
                    cert_path=cert_data["cert_path"],
                    key_path=cert_data["key_path"],
                    ca_path=cert_data["ca_path"],
                    expires_at=datetime.fromisoformat(cert_data["expires_at"]),
                    domains=cert_data["domains"],
                    ips=cert_data["ips"]
                )
                self.certificates[service_name] = cert
                
        except Exception as e:
            logger.error(f"Failed to load certificate metadata: {e}")
    
    def _save_certificate_metadata(self):
        """Save certificate metadata to file"""
        try:
            data = {}
            for service_name, cert in self.certificates.items():
                data[service_name] = cert.to_dict()
            
            with open(self.cert_metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save certificate metadata: {e}")

def create_docker_tls_config(cert_manager: CertificateManager, output_dir: str = "/tmp/docker-certs"):
    """
    Create Docker TLS configuration files for services
    
    Args:
        cert_manager: CertificateManager instance
        output_dir: Output directory for Docker certificate volume
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Copy CA certificate
    ca_dest = os.path.join(output_dir, "ca.pem")
    if os.path.exists(cert_manager.ca.ca_cert_path):
        subprocess.run(["cp", cert_manager.ca.ca_cert_path, ca_dest], check=True)
    
    # Create service certificate directories and copy files
    for service_name, cert in cert_manager.certificates.items():
        service_dir = os.path.join(output_dir, service_name)
        os.makedirs(service_dir, exist_ok=True)
        
        # Copy certificate and key
        cert_dest = os.path.join(service_dir, "cert.pem")
        key_dest = os.path.join(service_dir, "key.pem")
        ca_dest = os.path.join(service_dir, "ca.pem")
        
        subprocess.run(["cp", cert.cert_path, cert_dest], check=True)
        subprocess.run(["cp", cert.key_path, key_dest], check=True)
        subprocess.run(["cp", cert.ca_path, ca_dest], check=True)
        
        # Set appropriate permissions
        os.chmod(key_dest, 0o600)
        os.chmod(cert_dest, 0o644)
        os.chmod(ca_dest, 0o644)
    
    logger.info(f"Docker TLS configuration created in: {output_dir}")

# CLI interface for certificate management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Certificate Management for The HIVE")
    parser.add_argument("--init-ca", action="store_true", help="Initialize Certificate Authority")
    parser.add_argument("--force", action="store_true", help="Force recreation of existing certificates")
    parser.add_argument("--generate-all", action="store_true", help="Generate all service certificates")
    parser.add_argument("--service", help="Generate certificate for specific service")
    parser.add_argument("--check-expiry", action="store_true", help="Check certificate expiry status")
    parser.add_argument("--renew", action="store_true", help="Renew expiring certificates")
    parser.add_argument("--list", action="store_true", help="List all certificates")
    parser.add_argument("--cert-dir", default="/etc/ssl/hive", help="Certificate directory")
    parser.add_argument("--private-dir", default="/etc/ssl/private/hive", help="Private key directory")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    # Create configuration
    config = CertificateConfig(
        cert_dir=args.cert_dir,
        private_dir=args.private_dir
    )
    
    # Create certificate manager
    manager = CertificateManager(config)
    
    try:
        if args.init_ca:
            if manager.initialize_ca(force=args.force):
                print("Certificate Authority initialized successfully")
            else:
                print("Failed to initialize Certificate Authority")
                exit(1)
        
        if args.generate_all:
            results = manager.generate_all_service_certificates(force=args.force)
            for service, success in results.items():
                print(f"{service}: {'✓' if success else '✗'}")
        
        if args.service:
            cert = manager.generate_service_certificate(args.service, force=args.force)
            if cert:
                print(f"Certificate generated for {args.service}")
                print(f"  Certificate: {cert.cert_path}")
                print(f"  Private key: {cert.key_path}")
                print(f"  Expires: {cert.expires_at}")
            else:
                print(f"Failed to generate certificate for {args.service}")
        
        if args.check_expiry:
            status = manager.check_certificate_expiry()
            print("\nCertificate Expiry Status:")
            for service, info in status.items():
                print(f"  {service}: {info['status']} (expires in {info['days_until_expiry']} days)")
        
        if args.renew:
            results = manager.renew_expiring_certificates()
            if results:
                print("Renewed certificates:")
                for service, success in results.items():
                    print(f"  {service}: {'✓' if success else '✗'}")
            else:
                print("No certificates needed renewal")
        
        if args.list:
            certs = manager.list_certificates()
            print("\nAll Certificates:")
            for service, info in certs.items():
                print(f"  {service}:")
                print(f"    Status: {info.get('status', 'unknown')}")
                print(f"    Expires: {info['expires_at']}")
                print(f"    Days left: {info['days_until_expiry']}")
                print(f"    Domains: {', '.join(info['domains'])}")
                print(f"    IPs: {', '.join(info['ips'])}")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)