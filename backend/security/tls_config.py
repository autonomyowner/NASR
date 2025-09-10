"""
TLS/mTLS Configuration for The HIVE Services

Service-specific TLS configuration with automatic certificate loading
and secure communication setup for all inter-service communication.
"""

import os
import ssl
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from pathlib import Path
import aiohttp
import httpx
from fastapi import HTTPException
import uvicorn

logger = logging.getLogger(__name__)

@dataclass
class TLSServiceConfig:
    """TLS configuration for a specific service"""
    service_name: str
    cert_file: str
    key_file: str
    ca_file: str
    verify_client: bool = True
    verify_server: bool = True
    min_tls_version: str = "TLSv1.2"
    ciphers: Optional[str] = None
    
    def __post_init__(self):
        """Validate file paths"""
        for file_path in [self.cert_file, self.key_file, self.ca_file]:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"TLS file not found: {file_path}")

class TLSConfigManager:
    """Enhanced central TLS configuration management with comprehensive mTLS support"""
    
    # Enhanced cipher suite (secure configuration with forward secrecy)
    DEFAULT_CIPHERS = (
        "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:"
        "ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA256:"
        "ECDHE-RSA-AES256-SHA:ECDHE-RSA-AES128-SHA:"
        "DHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:"
        "DHE-RSA-AES256-SHA256:DHE-RSA-AES128-SHA256:"
        "!aNULL:!eNULL:!EXPORT:!DES:!RC4:!3DES:!MD5:!PSK:!SRP:!CAMELLIA"
    )
    
    # TLS security profiles
    SECURITY_PROFILES = {
        "maximum": {
            "min_tls_version": "TLSv1.3",
            "ciphers": "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256",
            "verify_client": True,
            "verify_server": True,
            "check_hostname": True
        },
        "high": {
            "min_tls_version": "TLSv1.2",
            "ciphers": DEFAULT_CIPHERS,
            "verify_client": True,
            "verify_server": True,
            "check_hostname": False  # Internal services use IPs
        },
        "standard": {
            "min_tls_version": "TLSv1.2",
            "ciphers": DEFAULT_CIPHERS,
            "verify_client": False,
            "verify_server": True,
            "check_hostname": False
        }
    }
    
    # Service TLS configurations
    SERVICE_CONFIGS = {
        "livekit": {
            "port": 7880,
            "verify_client": True,
            "protocols": ["http", "websocket"]
        },
        "stt-service": {
            "port": 8001,
            "verify_client": True,
            "protocols": ["websocket"]
        },
        "mt-service": {
            "port": 8002,
            "verify_client": True,
            "protocols": ["websocket"]
        },
        "tts-service": {
            "port": 8003,
            "verify_client": True,
            "protocols": ["websocket"]
        },
        "auth-service": {
            "port": 8004,
            "verify_client": True,
            "protocols": ["http"]
        },
        "nginx": {
            "port": 443,
            "verify_client": False,
            "protocols": ["http"]
        }
    }
    
    def __init__(self, cert_base_dir: str = "/etc/ssl/hive"):
        self.cert_base_dir = Path(cert_base_dir)
        self.private_dir = Path("/etc/ssl/private/hive")
        self.service_configs: Dict[str, TLSServiceConfig] = {}
        
        # Load all service configurations
        self._load_service_configs()
    
    def _load_service_configs(self):
        """Load TLS configurations for all services"""
        ca_file = self.cert_base_dir / "ca.pem"
        
        if not ca_file.exists():
            logger.warning(f"CA certificate not found: {ca_file}")
            return
        
        for service_name, config in self.SERVICE_CONFIGS.items():
            cert_file = self.cert_base_dir / f"{service_name}.pem"
            key_file = self.private_dir / f"{service_name}-key.pem"
            
            if cert_file.exists() and key_file.exists():
                try:
                    tls_config = TLSServiceConfig(
                        service_name=service_name,
                        cert_file=str(cert_file),
                        key_file=str(key_file),
                        ca_file=str(ca_file),
                        verify_client=config["verify_client"],
                        ciphers=self.DEFAULT_CIPHERS
                    )
                    self.service_configs[service_name] = tls_config
                    logger.info(f"Loaded TLS config for {service_name}")
                    
                except FileNotFoundError as e:
                    logger.error(f"Failed to load TLS config for {service_name}: {e}")
            else:
                logger.warning(f"Certificate files missing for {service_name}")
    
    def get_service_config(self, service_name: str) -> Optional[TLSServiceConfig]:
        """Get TLS configuration for a service"""
        return self.service_configs.get(service_name)
    
    def create_ssl_context(
        self,
        service_name: str,
        server_side: bool = True
    ) -> Optional[ssl.SSLContext]:
        """
        Create SSL context for a service
        
        Args:
            service_name: Name of the service
            server_side: True for server context, False for client context
            
        Returns:
            Configured SSL context or None if service not configured
        """
        config = self.get_service_config(service_name)
        if not config:
            logger.error(f"No TLS configuration found for {service_name}")
            return None
        
        try:
            # Create SSL context
            if server_side:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(config.cert_file, config.key_file)
                
                # Require client certificates for mTLS
                if config.verify_client:
                    context.verify_mode = ssl.CERT_REQUIRED
                    context.load_verify_locations(config.ca_file)
            else:
                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                context.load_cert_chain(config.cert_file, config.key_file)
                
                # Verify server certificates
                if config.verify_server:
                    context.check_hostname = False  # Using IP addresses
                    context.verify_mode = ssl.CERT_REQUIRED
                    context.load_verify_locations(config.ca_file)
            
            # Set minimum TLS version
            if config.min_tls_version == "TLSv1.3":
                context.minimum_version = ssl.TLSVersion.TLSv1_3
            else:
                context.minimum_version = ssl.TLSVersion.TLSv1_2
            
            # Set cipher suites
            if config.ciphers:
                context.set_ciphers(config.ciphers)
            
            logger.info(f"Created SSL context for {service_name} (server_side={server_side})")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context for {service_name}: {e}")
            return None
    
    def get_uvicorn_ssl_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get SSL configuration for Uvicorn server"""
        config = self.get_service_config(service_name)
        if not config:
            return None
        
        ssl_config = {
            "ssl_keyfile": config.key_file,
            "ssl_certfile": config.cert_file,
            "ssl_ca_certs": config.ca_file,
            "ssl_cert_reqs": ssl.CERT_REQUIRED if config.verify_client else ssl.CERT_NONE,
            "ssl_ciphers": config.ciphers or self.DEFAULT_CIPHERS
        }
        
        return ssl_config
    
    def get_client_ssl_context(self, service_name: str) -> Optional[ssl.SSLContext]:
        """Get SSL context for client connections"""
        return self.create_ssl_context(service_name, server_side=False)
    
    def get_aiohttp_connector(self, service_name: str) -> Optional[aiohttp.TCPConnector]:
        """Get aiohttp connector with TLS configuration"""
        ssl_context = self.get_client_ssl_context(service_name)
        if not ssl_context:
            return None
        
        return aiohttp.TCPConnector(
            ssl=ssl_context,
            limit=100,  # Connection pool limit
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
    
    def get_httpx_client_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get HTTPX client configuration with TLS"""
        ssl_context = self.get_client_ssl_context(service_name)
        if not ssl_context:
            return None
        
        return {
            "verify": ssl_context,
            "cert": None,  # Certificate is loaded in context
            "timeout": httpx.Timeout(10.0, connect=5.0),
            "limits": httpx.Limits(max_keepalive_connections=20, max_connections=100)
        }

class SecureHTTPClient:
    """Secure HTTP client with automatic mTLS configuration"""
    
    def __init__(self, service_name: str, tls_manager: TLSConfigManager):
        self.service_name = service_name
        self.tls_manager = tls_manager
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        client_config = self.tls_manager.get_httpx_client_config(self.service_name)
        if client_config:
            self.client = httpx.AsyncClient(**client_config)
        else:
            logger.warning(f"No TLS config for {self.service_name}, using insecure client")
            self.client = httpx.AsyncClient()
        
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()

class SecureWebSocketClient:
    """Secure WebSocket client with mTLS support"""
    
    def __init__(self, service_name: str, tls_manager: TLSConfigManager):
        self.service_name = service_name
        self.tls_manager = tls_manager
    
    def get_connection_kwargs(self) -> Dict[str, Any]:
        """Get WebSocket connection arguments with TLS"""
        ssl_context = self.tls_manager.get_client_ssl_context(self.service_name)
        
        if ssl_context:
            return {
                "ssl": ssl_context,
                "server_hostname": None,  # Using IP addresses
            }
        else:
            logger.warning(f"No TLS config for {self.service_name}, using insecure connection")
            return {}

class TLSMiddleware:
    """Middleware to enforce TLS requirements"""
    
    def __init__(self, tls_manager: TLSConfigManager):
        self.tls_manager = tls_manager
    
    def verify_client_certificate(self, request) -> Dict[str, Any]:
        """Verify client certificate from request"""
        # Extract certificate information from request
        # This would be populated by the web server (nginx/uvicorn)
        cert_info = {}
        
        # Check for X-SSL-Client-* headers (set by nginx)
        headers = request.headers
        
        if "X-SSL-Client-Verify" in headers:
            cert_info["verified"] = headers["X-SSL-Client-Verify"] == "SUCCESS"
        
        if "X-SSL-Client-S-DN" in headers:
            cert_info["subject"] = headers["X-SSL-Client-S-DN"]
        
        if "X-SSL-Client-I-DN" in headers:
            cert_info["issuer"] = headers["X-SSL-Client-I-DN"]
        
        if "X-SSL-Client-Serial" in headers:
            cert_info["serial"] = headers["X-SSL-Client-Serial"]
        
        return cert_info

def create_secure_uvicorn_config(
    service_name: str,
    host: str = "0.0.0.0",
    port: Optional[int] = None,
    tls_manager: Optional[TLSConfigManager] = None
) -> Dict[str, Any]:
    """
    Create Uvicorn configuration with TLS support
    
    Args:
        service_name: Name of the service
        host: Host to bind to
        port: Port to bind to (uses default if None)
        tls_manager: TLS configuration manager
        
    Returns:
        Uvicorn configuration dictionary
    """
    if tls_manager is None:
        tls_manager = TLSConfigManager()
    
    config = {
        "host": host,
        "port": port or TLSConfigManager.SERVICE_CONFIGS.get(service_name, {}).get("port", 8000),
        "log_level": "info",
        "access_log": True,
        "server_header": False,  # Hide server information
        "date_header": False,    # Hide date header
    }
    
    # Add TLS configuration if available
    ssl_config = tls_manager.get_uvicorn_ssl_config(service_name)
    if ssl_config:
        config.update(ssl_config)
        logger.info(f"Enabling TLS for {service_name}")
    else:
        logger.warning(f"No TLS configuration for {service_name}, running in insecure mode")
    
    return config

# Factory functions for easy integration
def create_tls_manager(cert_dir: str = "/etc/ssl/hive") -> TLSConfigManager:
    """Create TLS configuration manager"""
    return TLSConfigManager(cert_dir)

async def create_secure_http_client(service_name: str, tls_manager: Optional[TLSConfigManager] = None) -> httpx.AsyncClient:
    """Create secure HTTP client for service communication"""
    if tls_manager is None:
        tls_manager = TLSConfigManager()
    
    client_config = tls_manager.get_httpx_client_config(service_name)
    if client_config:
        return httpx.AsyncClient(**client_config)
    else:
        logger.warning(f"No TLS config for {service_name}, creating insecure client")
        return httpx.AsyncClient()

# Example usage for service integration
def setup_service_tls(service_name: str, app) -> Dict[str, Any]:
    """
    Setup TLS for a FastAPI service
    
    Args:
        service_name: Name of the service
        app: FastAPI application instance
        
    Returns:
        Uvicorn configuration with TLS
    """
    tls_manager = TLSConfigManager()
    
    # Add TLS middleware if needed
    if service_name in tls_manager.service_configs:
        tls_middleware = TLSMiddleware(tls_manager)
        # Add middleware to app if needed
        # app.add_middleware(...)
    
    # Return Uvicorn configuration
    return create_secure_uvicorn_config(service_name, tls_manager=tls_manager)

if __name__ == "__main__":
    # CLI for testing TLS configuration
    import argparse
    import asyncio
    
    async def test_tls_config(service_name: str):
        """Test TLS configuration for a service"""
        tls_manager = TLSConfigManager()
        
        # Test server context
        server_context = tls_manager.create_ssl_context(service_name, server_side=True)
        print(f"Server SSL context: {'✓' if server_context else '✗'}")
        
        # Test client context
        client_context = tls_manager.create_ssl_context(service_name, server_side=False)
        print(f"Client SSL context: {'✓' if client_context else '✗'}")
        
        # Test HTTP client
        try:
            async with SecureHTTPClient(service_name, tls_manager) as client:
                print(f"HTTP client: ✓")
        except Exception as e:
            print(f"HTTP client: ✗ ({e})")
    
    parser = argparse.ArgumentParser(description="Test TLS configuration")
    parser.add_argument("--service", required=True, help="Service name to test")
    parser.add_argument("--cert-dir", default="/etc/ssl/hive", help="Certificate directory")
    
    args = parser.parse_args()
    
    asyncio.run(test_tls_config(args.service))