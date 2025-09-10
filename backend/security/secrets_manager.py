"""
Secrets Management System for The HIVE Translation Services

Secure storage, rotation, and access control for sensitive configuration
including API keys, JWT secrets, database credentials, and certificates.
"""

import os
import json
import time
import hashlib
import secrets
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import redis
from enum import Enum

logger = logging.getLogger(__name__)

class SecretType(Enum):
    """Types of secrets managed by the system"""
    API_KEY = "api_key"
    JWT_SECRET = "jwt_secret"
    DATABASE_PASSWORD = "database_password"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    ENCRYPTION_KEY = "encryption_key"
    OAUTH_TOKEN = "oauth_token"
    WEBHOOK_SECRET = "webhook_secret"

@dataclass
class SecretMetadata:
    """Metadata for a stored secret"""
    secret_id: str
    secret_type: SecretType
    service_name: str
    description: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    rotation_interval_days: Optional[int] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    
    def needs_rotation(self) -> bool:
        """Check if secret needs rotation"""
        if not self.rotation_interval_days:
            return False
        
        rotation_due = self.updated_at + timedelta(days=self.rotation_interval_days)
        return datetime.utcnow() >= rotation_due
    
    def is_expired(self) -> bool:
        """Check if secret is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

@dataclass
class SecretVersion:
    """Versioned secret storage"""
    version: int
    encrypted_value: bytes
    created_at: datetime
    is_active: bool = True

class SecretEncryption:
    """Handles encryption and decryption of secrets"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or self._get_master_key()
        self.cipher = self._create_cipher()
    
    def _get_master_key(self) -> str:
        """Get or generate master encryption key"""
        key_file = Path("/etc/ssl/hive/master.key")
        
        if key_file.exists():
            return key_file.read_text().strip()
        else:
            # Generate new master key
            master_key = Fernet.generate_key().decode()
            
            # Ensure directory exists
            key_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write key with secure permissions
            key_file.write_text(master_key)
            key_file.chmod(0o600)
            
            logger.info(f"Generated new master encryption key: {key_file}")
            return master_key
    
    def _create_cipher(self) -> Fernet:
        """Create Fernet cipher from master key"""
        try:
            # If master key is already a valid Fernet key
            return Fernet(self.master_key.encode())
        except:
            # Derive key from password using PBKDF2
            salt = b"the_hive_salt_2024"  # Fixed salt for consistency
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
            return Fernet(key)
    
    def encrypt(self, value: str) -> bytes:
        """Encrypt a secret value"""
        return self.cipher.encrypt(value.encode())
    
    def decrypt(self, encrypted_value: bytes) -> str:
        """Decrypt a secret value"""
        return self.cipher.decrypt(encrypted_value).decode()

class SecretStorage:
    """Storage backend for secrets (supports file and Redis)"""
    
    def __init__(
        self,
        storage_type: str = "file",
        storage_path: str = "/etc/ssl/hive/secrets",
        redis_url: Optional[str] = None
    ):
        self.storage_type = storage_type
        self.storage_path = Path(storage_path)
        self.redis_client = None
        
        if storage_type == "redis" and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.redis_client.ping()
                logger.info("Connected to Redis for secret storage")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        elif storage_type == "file":
            self.storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
    
    def store_secret(
        self,
        secret_id: str,
        encrypted_value: bytes,
        metadata: SecretMetadata
    ) -> bool:
        """Store encrypted secret with metadata"""
        try:
            if self.storage_type == "redis":
                return self._store_redis(secret_id, encrypted_value, metadata)
            else:
                return self._store_file(secret_id, encrypted_value, metadata)
        except Exception as e:
            logger.error(f"Failed to store secret {secret_id}: {e}")
            return False
    
    def retrieve_secret(self, secret_id: str) -> Optional[Tuple[bytes, SecretMetadata]]:
        """Retrieve encrypted secret and metadata"""
        try:
            if self.storage_type == "redis":
                return self._retrieve_redis(secret_id)
            else:
                return self._retrieve_file(secret_id)
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_id}: {e}")
            return None
    
    def delete_secret(self, secret_id: str) -> bool:
        """Delete secret from storage"""
        try:
            if self.storage_type == "redis":
                return self._delete_redis(secret_id)
            else:
                return self._delete_file(secret_id)
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_id}: {e}")
            return False
    
    def list_secrets(self) -> List[SecretMetadata]:
        """List all secrets metadata"""
        try:
            if self.storage_type == "redis":
                return self._list_redis()
            else:
                return self._list_file()
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
    
    def _store_file(self, secret_id: str, encrypted_value: bytes, metadata: SecretMetadata) -> bool:
        """Store secret in file system"""
        secret_dir = self.storage_path / secret_id
        secret_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Store encrypted value
        value_file = secret_dir / "value"
        value_file.write_bytes(encrypted_value)
        value_file.chmod(0o600)
        
        # Store metadata
        metadata_file = secret_dir / "metadata.json"
        metadata_dict = asdict(metadata)
        # Convert datetime objects to strings
        for key, value in metadata_dict.items():
            if isinstance(value, datetime):
                metadata_dict[key] = value.isoformat() if value else None
            elif isinstance(value, SecretType):
                metadata_dict[key] = value.value
        
        metadata_file.write_text(json.dumps(metadata_dict, indent=2))
        metadata_file.chmod(0o600)
        
        return True
    
    def _retrieve_file(self, secret_id: str) -> Optional[Tuple[bytes, SecretMetadata]]:
        """Retrieve secret from file system"""
        secret_dir = self.storage_path / secret_id
        
        if not secret_dir.exists():
            return None
        
        value_file = secret_dir / "value"
        metadata_file = secret_dir / "metadata.json"
        
        if not value_file.exists() or not metadata_file.exists():
            return None
        
        # Read encrypted value
        encrypted_value = value_file.read_bytes()
        
        # Read metadata
        metadata_dict = json.loads(metadata_file.read_text())
        
        # Convert strings back to datetime objects
        for key in ["created_at", "updated_at", "expires_at", "last_accessed"]:
            if metadata_dict.get(key):
                metadata_dict[key] = datetime.fromisoformat(metadata_dict[key])
        
        # Convert secret type
        metadata_dict["secret_type"] = SecretType(metadata_dict["secret_type"])
        
        metadata = SecretMetadata(**metadata_dict)
        
        return encrypted_value, metadata
    
    def _delete_file(self, secret_id: str) -> bool:
        """Delete secret from file system"""
        import shutil
        secret_dir = self.storage_path / secret_id
        
        if secret_dir.exists():
            shutil.rmtree(secret_dir)
        
        return True
    
    def _list_file(self) -> List[SecretMetadata]:
        """List secrets from file system"""
        secrets = []
        
        for secret_dir in self.storage_path.iterdir():
            if secret_dir.is_dir():
                metadata_file = secret_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        metadata_dict = json.loads(metadata_file.read_text())
                        
                        # Convert strings back to datetime objects
                        for key in ["created_at", "updated_at", "expires_at", "last_accessed"]:
                            if metadata_dict.get(key):
                                metadata_dict[key] = datetime.fromisoformat(metadata_dict[key])
                        
                        # Convert secret type
                        metadata_dict["secret_type"] = SecretType(metadata_dict["secret_type"])
                        
                        secrets.append(SecretMetadata(**metadata_dict))
                    except Exception as e:
                        logger.error(f"Failed to load metadata for {secret_dir.name}: {e}")
        
        return secrets
    
    def _store_redis(self, secret_id: str, encrypted_value: bytes, metadata: SecretMetadata) -> bool:
        """Store secret in Redis"""
        pipe = self.redis_client.pipeline()
        
        # Store encrypted value
        pipe.set(f"secret:value:{secret_id}", encrypted_value)
        
        # Store metadata
        metadata_dict = asdict(metadata)
        for key, value in metadata_dict.items():
            if isinstance(value, datetime):
                metadata_dict[key] = value.isoformat() if value else None
            elif isinstance(value, SecretType):
                metadata_dict[key] = value.value
        
        pipe.hset(f"secret:metadata:{secret_id}", mapping=metadata_dict)
        
        # Add to secrets index
        pipe.sadd("secrets:index", secret_id)
        
        results = pipe.execute()
        return all(results)
    
    def _retrieve_redis(self, secret_id: str) -> Optional[Tuple[bytes, SecretMetadata]]:
        """Retrieve secret from Redis"""
        pipe = self.redis_client.pipeline()
        pipe.get(f"secret:value:{secret_id}")
        pipe.hgetall(f"secret:metadata:{secret_id}")
        
        results = pipe.execute()
        encrypted_value, metadata_dict = results
        
        if not encrypted_value or not metadata_dict:
            return None
        
        # Convert metadata
        for key in ["created_at", "updated_at", "expires_at", "last_accessed"]:
            if metadata_dict.get(key):
                metadata_dict[key] = datetime.fromisoformat(metadata_dict[key].decode())
        
        metadata_dict["secret_type"] = SecretType(metadata_dict["secret_type"].decode())
        metadata_dict["access_count"] = int(metadata_dict["access_count"])
        
        # Convert other bytes to strings
        for key, value in metadata_dict.items():
            if isinstance(value, bytes):
                metadata_dict[key] = value.decode()
        
        metadata = SecretMetadata(**metadata_dict)
        
        return encrypted_value, metadata
    
    def _delete_redis(self, secret_id: str) -> bool:
        """Delete secret from Redis"""
        pipe = self.redis_client.pipeline()
        pipe.delete(f"secret:value:{secret_id}")
        pipe.delete(f"secret:metadata:{secret_id}")
        pipe.srem("secrets:index", secret_id)
        
        results = pipe.execute()
        return any(results)
    
    def _list_redis(self) -> List[SecretMetadata]:
        """List secrets from Redis"""
        secret_ids = self.redis_client.smembers("secrets:index")
        secrets = []
        
        for secret_id in secret_ids:
            secret_id = secret_id.decode()
            result = self._retrieve_redis(secret_id)
            if result:
                _, metadata = result
                secrets.append(metadata)
        
        return secrets

class SecretsManager:
    """Main secrets management interface"""
    
    # Default secret generators
    SECRET_GENERATORS = {
        SecretType.API_KEY: lambda: secrets.token_urlsafe(32),
        SecretType.JWT_SECRET: lambda: secrets.token_urlsafe(64),
        SecretType.DATABASE_PASSWORD: lambda: secrets.token_urlsafe(24),
        SecretType.ENCRYPTION_KEY: lambda: Fernet.generate_key().decode(),
        SecretType.WEBHOOK_SECRET: lambda: secrets.token_hex(32),
        SecretType.OAUTH_TOKEN: lambda: secrets.token_urlsafe(40),
    }
    
    # Default rotation intervals (days)
    ROTATION_INTERVALS = {
        SecretType.API_KEY: 90,
        SecretType.JWT_SECRET: 30,
        SecretType.DATABASE_PASSWORD: 180,
        SecretType.OAUTH_TOKEN: 30,
        SecretType.WEBHOOK_SECRET: 365,
    }
    
    def __init__(
        self,
        storage_type: str = "file",
        storage_path: str = "/etc/ssl/hive/secrets",
        redis_url: Optional[str] = None,
        master_key: Optional[str] = None
    ):
        self.encryption = SecretEncryption(master_key)
        self.storage = SecretStorage(storage_type, storage_path, redis_url)
    
    def store_secret(
        self,
        secret_id: str,
        value: str,
        secret_type: SecretType,
        service_name: str,
        description: str = "",
        expires_at: Optional[datetime] = None,
        rotation_interval_days: Optional[int] = None
    ) -> bool:
        """
        Store a new secret
        
        Args:
            secret_id: Unique identifier for the secret
            value: Secret value to store
            secret_type: Type of secret
            service_name: Service that owns this secret
            description: Human-readable description
            expires_at: Optional expiration date
            rotation_interval_days: Auto-rotation interval
            
        Returns:
            True if stored successfully
        """
        try:
            # Encrypt the secret value
            encrypted_value = self.encryption.encrypt(value)
            
            # Create metadata
            metadata = SecretMetadata(
                secret_id=secret_id,
                secret_type=secret_type,
                service_name=service_name,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                expires_at=expires_at,
                rotation_interval_days=rotation_interval_days or self.ROTATION_INTERVALS.get(secret_type)
            )
            
            # Store in backend
            success = self.storage.store_secret(secret_id, encrypted_value, metadata)
            
            if success:
                logger.info(f"Stored secret: {secret_id} for service: {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to store secret {secret_id}: {e}")
            return False
    
    def get_secret(self, secret_id: str) -> Optional[str]:
        """
        Retrieve and decrypt a secret
        
        Args:
            secret_id: Secret identifier
            
        Returns:
            Decrypted secret value or None if not found
        """
        try:
            result = self.storage.retrieve_secret(secret_id)
            if not result:
                return None
            
            encrypted_value, metadata = result
            
            # Check if secret is expired
            if metadata.is_expired():
                logger.warning(f"Secret {secret_id} is expired")
                return None
            
            # Update access tracking
            metadata.last_accessed = datetime.utcnow()
            metadata.access_count += 1
            
            # Update metadata in storage
            self.storage.store_secret(secret_id, encrypted_value, metadata)
            
            # Decrypt and return
            return self.encryption.decrypt(encrypted_value)
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_id}: {e}")
            return None
    
    def generate_secret(
        self,
        secret_id: str,
        secret_type: SecretType,
        service_name: str,
        description: str = "",
        expires_at: Optional[datetime] = None,
        rotation_interval_days: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate and store a new secret
        
        Args:
            secret_id: Unique identifier
            secret_type: Type of secret to generate
            service_name: Owning service
            description: Description
            expires_at: Expiration date
            rotation_interval_days: Rotation interval
            
        Returns:
            Generated secret value or None if failed
        """
        generator = self.SECRET_GENERATORS.get(secret_type)
        if not generator:
            logger.error(f"No generator available for secret type: {secret_type}")
            return None
        
        # Generate secret value
        value = generator()
        
        # Store the secret
        success = self.store_secret(
            secret_id=secret_id,
            value=value,
            secret_type=secret_type,
            service_name=service_name,
            description=description,
            expires_at=expires_at,
            rotation_interval_days=rotation_interval_days
        )
        
        return value if success else None
    
    def rotate_secret(self, secret_id: str) -> Optional[str]:
        """
        Rotate a secret (generate new value)
        
        Args:
            secret_id: Secret to rotate
            
        Returns:
            New secret value or None if failed
        """
        # Get existing metadata
        result = self.storage.retrieve_secret(secret_id)
        if not result:
            logger.error(f"Secret {secret_id} not found for rotation")
            return None
        
        _, metadata = result
        
        # Generate new value
        generator = self.SECRET_GENERATORS.get(metadata.secret_type)
        if not generator:
            logger.error(f"Cannot rotate secret {secret_id}: no generator for type {metadata.secret_type}")
            return None
        
        new_value = generator()
        
        # Update with new value
        metadata.updated_at = datetime.utcnow()
        encrypted_value = self.encryption.encrypt(new_value)
        
        success = self.storage.store_secret(secret_id, encrypted_value, metadata)
        
        if success:
            logger.info(f"Rotated secret: {secret_id}")
            return new_value
        else:
            logger.error(f"Failed to rotate secret: {secret_id}")
            return None
    
    def delete_secret(self, secret_id: str) -> bool:
        """Delete a secret"""
        success = self.storage.delete_secret(secret_id)
        if success:
            logger.info(f"Deleted secret: {secret_id}")
        return success
    
    def list_secrets(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List secrets with metadata (optionally filtered by service)"""
        secrets = self.storage.list_secrets()
        
        if service_name:
            secrets = [s for s in secrets if s.service_name == service_name]
        
        # Convert to dictionaries for JSON serialization
        result = []
        for secret in secrets:
            secret_dict = asdict(secret)
            # Convert datetime objects and enums
            for key, value in secret_dict.items():
                if isinstance(value, datetime):
                    secret_dict[key] = value.isoformat() if value else None
                elif isinstance(value, SecretType):
                    secret_dict[key] = value.value
            
            # Add status information
            secret_dict["needs_rotation"] = secret.needs_rotation()
            secret_dict["is_expired"] = secret.is_expired()
            
            result.append(secret_dict)
        
        return result
    
    def check_rotations_needed(self) -> List[str]:
        """Check which secrets need rotation"""
        secrets = self.storage.list_secrets()
        return [s.secret_id for s in secrets if s.needs_rotation()]
    
    def auto_rotate_secrets(self) -> Dict[str, bool]:
        """Automatically rotate secrets that need rotation"""
        secrets_to_rotate = self.check_rotations_needed()
        results = {}
        
        for secret_id in secrets_to_rotate:
            new_value = self.rotate_secret(secret_id)
            results[secret_id] = new_value is not None
        
        return results

# Utility functions for common operations
def create_secrets_manager(
    storage_type: str = "file",
    redis_url: Optional[str] = None
) -> SecretsManager:
    """Create secrets manager with default configuration"""
    return SecretsManager(
        storage_type=storage_type,
        redis_url=redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
    )

def setup_service_secrets(
    service_name: str,
    secrets_manager: SecretsManager,
    required_secrets: Dict[str, SecretType]
) -> Dict[str, str]:
    """
    Setup required secrets for a service
    
    Args:
        service_name: Name of the service
        secrets_manager: Secrets manager instance
        required_secrets: Dict of {secret_name: secret_type}
        
    Returns:
        Dict of {secret_name: secret_value}
    """
    secrets = {}
    
    for secret_name, secret_type in required_secrets.items():
        secret_id = f"{service_name}:{secret_name}"
        
        # Try to get existing secret
        value = secrets_manager.get_secret(secret_id)
        
        if not value:
            # Generate new secret
            value = secrets_manager.generate_secret(
                secret_id=secret_id,
                secret_type=secret_type,
                service_name=service_name,
                description=f"{secret_name} for {service_name} service"
            )
        
        if value:
            secrets[secret_name] = value
        else:
            logger.error(f"Failed to setup secret {secret_name} for {service_name}")
    
    return secrets

# CLI interface for secret management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Secrets Management CLI")
    parser.add_argument("--storage", choices=["file", "redis"], default="file", help="Storage backend")
    parser.add_argument("--redis-url", help="Redis URL for storage")
    parser.add_argument("--list", action="store_true", help="List all secrets")
    parser.add_argument("--service", help="Filter secrets by service name")
    parser.add_argument("--generate", help="Generate new secret (format: service:name:type)")
    parser.add_argument("--get", help="Get secret value by ID")
    parser.add_argument("--rotate", help="Rotate secret by ID")
    parser.add_argument("--check-rotations", action="store_true", help="Check which secrets need rotation")
    parser.add_argument("--auto-rotate", action="store_true", help="Automatically rotate expired secrets")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    try:
        # Create secrets manager
        manager = create_secrets_manager(args.storage, args.redis_url)
        
        if args.list:
            secrets = manager.list_secrets(args.service)
            print(f"\n{'ID':<30} {'Service':<20} {'Type':<15} {'Status':<15} {'Expires'}")
            print("-" * 90)
            for secret in secrets:
                status = "expired" if secret["is_expired"] else ("needs_rotation" if secret["needs_rotation"] else "valid")
                expires = secret["expires_at"] or "never"
                print(f"{secret['secret_id']:<30} {secret['service_name']:<20} {secret['secret_type']:<15} {status:<15} {expires}")
        
        elif args.generate:
            parts = args.generate.split(":")
            if len(parts) != 3:
                print("Generate format: service:name:type")
                exit(1)
            
            service, name, type_str = parts
            try:
                secret_type = SecretType(type_str)
            except ValueError:
                print(f"Invalid secret type: {type_str}")
                print(f"Valid types: {[t.value for t in SecretType]}")
                exit(1)
            
            secret_id = f"{service}:{name}"
            value = manager.generate_secret(secret_id, secret_type, service)
            if value:
                print(f"Generated secret {secret_id}: {value}")
            else:
                print(f"Failed to generate secret {secret_id}")
        
        elif args.get:
            value = manager.get_secret(args.get)
            if value:
                print(f"Secret {args.get}: {value}")
            else:
                print(f"Secret {args.get} not found")
        
        elif args.rotate:
            new_value = manager.rotate_secret(args.rotate)
            if new_value:
                print(f"Rotated secret {args.rotate}: {new_value}")
            else:
                print(f"Failed to rotate secret {args.rotate}")
        
        elif args.check_rotations:
            secrets = manager.check_rotations_needed()
            if secrets:
                print("Secrets needing rotation:")
                for secret_id in secrets:
                    print(f"  {secret_id}")
            else:
                print("No secrets need rotation")
        
        elif args.auto_rotate:
            results = manager.auto_rotate_secrets()
            if results:
                print("Auto-rotation results:")
                for secret_id, success in results.items():
                    print(f"  {secret_id}: {'✓' if success else '✗'}")
            else:
                print("No secrets rotated")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)