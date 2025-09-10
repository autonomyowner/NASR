"""
Service Account Management System for The HIVE Translation Services

Least-privilege service account management with role-based access control,
credential rotation, and comprehensive access tracking for all services.
"""

import os
import json
import time
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import redis
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)

class ServiceRole(Enum):
    """Service roles with specific permission sets"""
    # Core translation services
    STT_SERVICE = "stt_service"
    MT_SERVICE = "mt_service" 
    TTS_SERVICE = "tts_service"
    
    # Infrastructure services
    AUTH_SERVICE = "auth_service"
    TRANSLATOR_WORKER = "translator_worker"
    HEALTH_MONITOR = "health_monitor"
    
    # External integrations
    LIVEKIT_SFU = "livekit_sfu"
    REDIS_CLIENT = "redis_client"
    
    # Administrative
    SYSTEM_ADMIN = "system_admin"
    SECURITY_MONITOR = "security_monitor"

class Permission(Enum):
    """Granular permissions for service operations"""
    # Authentication & Authorization
    AUTH_GENERATE_TOKEN = "auth:generate_token"
    AUTH_VALIDATE_TOKEN = "auth:validate_token"
    AUTH_REVOKE_TOKEN = "auth:revoke_token"
    
    # Room Management
    ROOM_CREATE = "room:create"
    ROOM_JOIN = "room:join"
    ROOM_LEAVE = "room:leave"
    ROOM_LIST = "room:list"
    ROOM_DELETE = "room:delete"
    
    # Audio Processing
    AUDIO_SUBSCRIBE = "audio:subscribe"
    AUDIO_PUBLISH = "audio:publish"
    AUDIO_PROCESS = "audio:process"
    
    # Translation Pipeline
    STT_PROCESS = "stt:process"
    MT_TRANSLATE = "mt:translate"
    TTS_SYNTHESIZE = "tts:synthesize"
    
    # Data Access
    DATA_SEND = "data:send"
    DATA_RECEIVE = "data:receive"
    DATA_STORE = "data:store"
    
    # Service Management
    SERVICE_START = "service:start"
    SERVICE_STOP = "service:stop"
    SERVICE_RESTART = "service:restart"
    SERVICE_STATUS = "service:status"
    
    # Monitoring & Metrics
    METRICS_READ = "metrics:read"
    METRICS_WRITE = "metrics:write"
    LOGS_READ = "logs:read"
    
    # Security Operations
    SECURITY_AUDIT = "security:audit"
    SECURITY_ALERT = "security:alert"
    SECRET_READ = "secret:read"
    SECRET_WRITE = "secret:write"

@dataclass
class ServiceAccount:
    """Service account with credentials and permissions"""
    account_id: str
    service_name: str
    role: ServiceRole
    permissions: Set[Permission]
    api_key: str
    secret_key: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "account_id": self.account_id,
            "service_name": self.service_name,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions],
            "api_key": self.api_key,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "usage_count": self.usage_count
        }
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if account has specific permission"""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if account has any of the specified permissions"""
        return any(p in self.permissions for p in permissions)
    
    def is_expired(self) -> bool:
        """Check if account is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

class ServiceAccountManager:
    """Service account management with role-based access control"""
    
    # Role-based permission mappings
    ROLE_PERMISSIONS = {
        ServiceRole.STT_SERVICE: {
            Permission.AUDIO_SUBSCRIBE,
            Permission.AUDIO_PROCESS,
            Permission.STT_PROCESS,
            Permission.DATA_SEND,
            Permission.METRICS_WRITE,
            Permission.AUTH_VALIDATE_TOKEN,
        },
        
        ServiceRole.MT_SERVICE: {
            Permission.MT_TRANSLATE,
            Permission.DATA_RECEIVE,
            Permission.DATA_SEND,
            Permission.METRICS_WRITE,
            Permission.AUTH_VALIDATE_TOKEN,
        },
        
        ServiceRole.TTS_SERVICE: {
            Permission.TTS_SYNTHESIZE,
            Permission.AUDIO_PUBLISH,
            Permission.DATA_RECEIVE,
            Permission.METRICS_WRITE,
            Permission.AUTH_VALIDATE_TOKEN,
        },
        
        ServiceRole.TRANSLATOR_WORKER: {
            Permission.ROOM_JOIN,
            Permission.AUDIO_SUBSCRIBE,
            Permission.AUDIO_PUBLISH,
            Permission.STT_PROCESS,
            Permission.MT_TRANSLATE,
            Permission.TTS_SYNTHESIZE,
            Permission.DATA_SEND,
            Permission.DATA_RECEIVE,
            Permission.AUTH_VALIDATE_TOKEN,
        },
        
        ServiceRole.AUTH_SERVICE: {
            Permission.AUTH_GENERATE_TOKEN,
            Permission.AUTH_VALIDATE_TOKEN,
            Permission.AUTH_REVOKE_TOKEN,
            Permission.SECRET_READ,
            Permission.METRICS_WRITE,
        },
        
        ServiceRole.HEALTH_MONITOR: {
            Permission.SERVICE_STATUS,
            Permission.METRICS_READ,
            Permission.LOGS_READ,
            Permission.SECURITY_ALERT,
        },
        
        ServiceRole.LIVEKIT_SFU: {
            Permission.ROOM_CREATE,
            Permission.ROOM_JOIN,
            Permission.ROOM_DELETE,
            Permission.AUDIO_SUBSCRIBE,
            Permission.AUDIO_PUBLISH,
            Permission.AUTH_VALIDATE_TOKEN,
        },
        
        ServiceRole.REDIS_CLIENT: {
            Permission.DATA_STORE,
            Permission.METRICS_WRITE,
            Permission.METRICS_READ,
        },
        
        ServiceRole.SECURITY_MONITOR: {
            Permission.SECURITY_AUDIT,
            Permission.SECURITY_ALERT,
            Permission.LOGS_READ,
            Permission.METRICS_READ,
            Permission.SECRET_READ,
        },
        
        ServiceRole.SYSTEM_ADMIN: set(Permission),  # All permissions
    }
    
    def __init__(
        self,
        storage_path: str = "/etc/ssl/hive/service_accounts",
        redis_url: Optional[str] = None,
        encryption_key: Optional[str] = None
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Initialize encryption
        self.encryption_key = encryption_key or self._get_encryption_key()
        self.cipher = self._create_cipher()
        
        # Initialize Redis connection if provided
        self.redis = None
        if redis_url:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
                logger.info("Connected to Redis for service account caching")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
        
        # Account storage
        self.accounts: Dict[str, ServiceAccount] = {}
        self.accounts_file = self.storage_path / "accounts.json"
        
        # Load existing accounts
        self._load_accounts()
    
    def _get_encryption_key(self) -> str:
        """Get or generate encryption key for credentials"""
        key_file = self.storage_path / "encryption.key"
        
        if key_file.exists():
            return key_file.read_text().strip()
        else:
            # Generate new encryption key
            key = Fernet.generate_key().decode()
            key_file.write_text(key)
            key_file.chmod(0o600)
            logger.info(f"Generated new encryption key: {key_file}")
            return key
    
    def _create_cipher(self) -> Fernet:
        """Create Fernet cipher from encryption key"""
        try:
            # If key is already a valid Fernet key
            return Fernet(self.encryption_key.encode())
        except:
            # Derive key from password using PBKDF2
            salt = b"hive_service_accounts_2024"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            return Fernet(key)
    
    def create_service_account(
        self,
        service_name: str,
        role: ServiceRole,
        expires_hours: Optional[int] = None,
        custom_permissions: Optional[Set[Permission]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceAccount:
        """
        Create a new service account with specified role and permissions
        
        Args:
            service_name: Name of the service
            role: Service role (defines default permissions)
            expires_hours: Account expiration in hours (None = no expiration)
            custom_permissions: Override default role permissions
            metadata: Additional metadata
            
        Returns:
            Created ServiceAccount
        """
        # Generate account ID and credentials
        account_id = f"{service_name}_{int(time.time())}_{secrets.token_hex(4)}"
        api_key = f"hive_{secrets.token_urlsafe(32)}"
        secret_key = secrets.token_urlsafe(64)
        
        # Determine permissions
        permissions = custom_permissions or self.ROLE_PERMISSIONS.get(role, set())
        
        # Calculate expiration
        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        # Create service account
        account = ServiceAccount(
            account_id=account_id,
            service_name=service_name,
            role=role,
            permissions=permissions,
            api_key=api_key,
            secret_key=secret_key,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # Store account
        self.accounts[account_id] = account
        self._save_accounts()
        
        # Cache in Redis if available
        if self.redis:
            self._cache_account(account)
        
        logger.info(f"Created service account: {account_id} for {service_name} ({role.value})")
        
        return account
    
    def get_account(self, account_id: str) -> Optional[ServiceAccount]:
        """Get service account by ID"""
        # Try Redis cache first
        if self.redis:
            account_data = self.redis.get(f"service_account:{account_id}")
            if account_data:
                try:
                    data = json.loads(account_data)
                    return self._account_from_dict(data)
                except (json.JSONDecodeError, KeyError):
                    pass
        
        # Fall back to local storage
        return self.accounts.get(account_id)
    
    def get_account_by_api_key(self, api_key: str) -> Optional[ServiceAccount]:
        """Get service account by API key"""
        # Try Redis cache first
        if self.redis:
            account_id = self.redis.get(f"api_key_lookup:{api_key}")
            if account_id:
                return self.get_account(account_id)
        
        # Search local accounts
        for account in self.accounts.values():
            if account.api_key == api_key and account.is_active and not account.is_expired():
                return account
        
        return None
    
    def authenticate_account(self, api_key: str, secret_key: str) -> Optional[ServiceAccount]:
        """Authenticate service account with API key and secret"""
        account = self.get_account_by_api_key(api_key)
        
        if not account:
            logger.warning(f"Authentication failed: Account not found for API key")
            return None
        
        if not account.is_active:
            logger.warning(f"Authentication failed: Account {account.account_id} is inactive")
            return None
        
        if account.is_expired():
            logger.warning(f"Authentication failed: Account {account.account_id} is expired")
            return None
        
        # Verify secret key (encrypted comparison)
        try:
            encrypted_secret = self.cipher.encrypt(secret_key.encode())
            stored_secret = self.cipher.encrypt(account.secret_key.encode())
            
            if encrypted_secret == stored_secret:
                # Update last used timestamp
                account.last_used = datetime.utcnow()
                account.usage_count += 1
                self._save_accounts()
                
                if self.redis:
                    self._cache_account(account)
                
                logger.info(f"Successful authentication for account {account.account_id}")
                return account
            else:
                logger.warning(f"Authentication failed: Invalid secret key for {account.account_id}")
                return None
                
        except Exception as e:
            logger.error(f"Authentication error for {account.account_id}: {e}")
            return None
    
    def check_permission(self, account_id: str, permission: Permission) -> bool:
        """Check if service account has specific permission"""
        account = self.get_account(account_id)
        if not account:
            return False
        
        return account.has_permission(permission)
    
    def rotate_credentials(self, account_id: str) -> Optional[ServiceAccount]:
        """Rotate API key and secret for service account"""
        account = self.get_account(account_id)
        if not account:
            logger.error(f"Cannot rotate credentials: Account {account_id} not found")
            return None
        
        # Generate new credentials
        old_api_key = account.api_key
        account.api_key = f"hive_{secrets.token_urlsafe(32)}"
        account.secret_key = secrets.token_urlsafe(64)
        account.updated_at = datetime.utcnow()
        
        # Update storage
        self.accounts[account_id] = account
        self._save_accounts()
        
        # Update Redis cache
        if self.redis:
            # Remove old API key lookup
            self.redis.delete(f"api_key_lookup:{old_api_key}")
            # Cache updated account
            self._cache_account(account)
        
        logger.info(f"Rotated credentials for account {account_id}")
        
        return account
    
    def deactivate_account(self, account_id: str) -> bool:
        """Deactivate service account"""
        account = self.get_account(account_id)
        if not account:
            return False
        
        account.is_active = False
        account.updated_at = datetime.utcnow()
        
        self.accounts[account_id] = account
        self._save_accounts()
        
        # Remove from Redis cache
        if self.redis:
            self.redis.delete(f"service_account:{account_id}")
            self.redis.delete(f"api_key_lookup:{account.api_key}")
        
        logger.info(f"Deactivated account {account_id}")
        
        return True
    
    def list_accounts(self, service_name: Optional[str] = None, role: Optional[ServiceRole] = None) -> List[ServiceAccount]:
        """List service accounts with optional filtering"""
        accounts = list(self.accounts.values())
        
        if service_name:
            accounts = [a for a in accounts if a.service_name == service_name]
        
        if role:
            accounts = [a for a in accounts if a.role == role]
        
        return sorted(accounts, key=lambda a: a.created_at)
    
    def cleanup_expired_accounts(self) -> List[str]:
        """Remove expired service accounts"""
        expired_accounts = []
        
        for account_id, account in list(self.accounts.items()):
            if account.is_expired():
                expired_accounts.append(account_id)
                del self.accounts[account_id]
                
                # Remove from Redis cache
                if self.redis:
                    self.redis.delete(f"service_account:{account_id}")
                    self.redis.delete(f"api_key_lookup:{account.api_key}")
        
        if expired_accounts:
            self._save_accounts()
            logger.info(f"Cleaned up {len(expired_accounts)} expired accounts")
        
        return expired_accounts
    
    def get_account_stats(self) -> Dict[str, Any]:
        """Get service account statistics"""
        total_accounts = len(self.accounts)
        active_accounts = sum(1 for a in self.accounts.values() if a.is_active)
        expired_accounts = sum(1 for a in self.accounts.values() if a.is_expired())
        
        role_distribution = {}
        for account in self.accounts.values():
            role = account.role.value
            role_distribution[role] = role_distribution.get(role, 0) + 1
        
        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "inactive_accounts": total_accounts - active_accounts,
            "expired_accounts": expired_accounts,
            "role_distribution": role_distribution,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _load_accounts(self):
        """Load service accounts from storage"""
        if not self.accounts_file.exists():
            return
        
        try:
            with open(self.accounts_file, 'r') as f:
                data = json.load(f)
            
            for account_id, account_data in data.items():
                try:
                    account = self._account_from_dict(account_data)
                    self.accounts[account_id] = account
                except Exception as e:
                    logger.error(f"Failed to load account {account_id}: {e}")
            
            logger.info(f"Loaded {len(self.accounts)} service accounts")
            
        except Exception as e:
            logger.error(f"Failed to load service accounts: {e}")
    
    def _save_accounts(self):
        """Save service accounts to storage"""
        try:
            data = {}
            for account_id, account in self.accounts.items():
                # Encrypt sensitive data before saving
                account_data = account.to_dict()
                account_data["secret_key"] = self.cipher.encrypt(account.secret_key.encode()).decode()
                data[account_id] = account_data
            
            with open(self.accounts_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Secure file permissions
            self.accounts_file.chmod(0o600)
            
        except Exception as e:
            logger.error(f"Failed to save service accounts: {e}")
    
    def _account_from_dict(self, data: Dict[str, Any]) -> ServiceAccount:
        """Create ServiceAccount from dictionary"""
        # Decrypt secret key
        secret_key = data["secret_key"]
        if isinstance(secret_key, str) and secret_key.startswith("gAAAAAA"):
            # Encrypted secret key
            secret_key = self.cipher.decrypt(secret_key.encode()).decode()
        
        return ServiceAccount(
            account_id=data["account_id"],
            service_name=data["service_name"],
            role=ServiceRole(data["role"]),
            permissions={Permission(p) for p in data["permissions"]},
            api_key=data["api_key"],
            secret_key=secret_key,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            is_active=data.get("is_active", True),
            metadata=data.get("metadata", {}),
            usage_count=data.get("usage_count", 0)
        )
    
    def _cache_account(self, account: ServiceAccount):
        """Cache service account in Redis"""
        if not self.redis:
            return
        
        try:
            # Cache account data
            account_data = account.to_dict()
            self.redis.setex(
                f"service_account:{account.account_id}",
                3600,  # 1 hour TTL
                json.dumps(account_data)
            )
            
            # Cache API key lookup
            self.redis.setex(
                f"api_key_lookup:{account.api_key}",
                3600,  # 1 hour TTL
                account.account_id
            )
            
        except Exception as e:
            logger.error(f"Failed to cache account {account.account_id}: {e}")

# Factory functions and utilities
def create_service_account_manager(
    storage_path: str = "/etc/ssl/hive/service_accounts",
    redis_url: Optional[str] = None
) -> ServiceAccountManager:
    """Create service account manager with default configuration"""
    return ServiceAccountManager(storage_path, redis_url)

def setup_default_service_accounts(manager: ServiceAccountManager) -> Dict[str, ServiceAccount]:
    """Setup default service accounts for The HIVE services"""
    accounts = {}
    
    # Core translation services
    services = [
        ("stt-service", ServiceRole.STT_SERVICE),
        ("mt-service", ServiceRole.MT_SERVICE),
        ("tts-service", ServiceRole.TTS_SERVICE),
        ("auth-service", ServiceRole.AUTH_SERVICE),
        ("translator-worker", ServiceRole.TRANSLATOR_WORKER),
        ("health-monitor", ServiceRole.HEALTH_MONITOR),
        ("security-monitor", ServiceRole.SECURITY_MONITOR),
    ]
    
    for service_name, role in services:
        # Check if account already exists
        existing = [a for a in manager.list_accounts(service_name=service_name) if a.is_active]
        if not existing:
            account = manager.create_service_account(
                service_name=service_name,
                role=role,
                metadata={
                    "auto_created": True,
                    "environment": "production"
                }
            )
            accounts[service_name] = account
            logger.info(f"Created default account for {service_name}")
        else:
            accounts[service_name] = existing[0]
    
    return accounts

# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Service Account Management for The HIVE")
    parser.add_argument("--create", nargs=2, metavar=("SERVICE", "ROLE"), 
                       help="Create service account (service_name role)")
    parser.add_argument("--list", action="store_true", help="List all service accounts")
    parser.add_argument("--stats", action="store_true", help="Show account statistics")
    parser.add_argument("--authenticate", nargs=2, metavar=("API_KEY", "SECRET_KEY"),
                       help="Test account authentication")
    parser.add_argument("--rotate", help="Rotate credentials for account ID")
    parser.add_argument("--deactivate", help="Deactivate account by ID")
    parser.add_argument("--cleanup", action="store_true", help="Remove expired accounts")
    parser.add_argument("--setup-defaults", action="store_true", help="Setup default service accounts")
    parser.add_argument("--storage-path", default="/etc/ssl/hive/service_accounts", 
                       help="Service accounts storage path")
    parser.add_argument("--redis-url", help="Redis connection URL")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    try:
        manager = create_service_account_manager(args.storage_path, args.redis_url)
        
        if args.create:
            service_name, role_str = args.create
            try:
                role = ServiceRole(role_str)
                account = manager.create_service_account(service_name, role)
                print(f"Created account: {account.account_id}")
                print(f"API Key: {account.api_key}")
                print(f"Secret Key: {account.secret_key}")
            except ValueError:
                print(f"Invalid role: {role_str}")
                print(f"Valid roles: {[r.value for r in ServiceRole]}")
        
        elif args.list:
            accounts = manager.list_accounts()
            print(f"\n{'ID':<30} {'Service':<20} {'Role':<20} {'Active':<10} {'Expires'}")
            print("-" * 90)
            for account in accounts:
                expires = account.expires_at.strftime('%Y-%m-%d') if account.expires_at else "Never"
                active = "Yes" if account.is_active and not account.is_expired() else "No"
                print(f"{account.account_id:<30} {account.service_name:<20} {account.role.value:<20} {active:<10} {expires}")
        
        elif args.stats:
            stats = manager.get_account_stats()
            print(json.dumps(stats, indent=2))
        
        elif args.authenticate:
            api_key, secret_key = args.authenticate
            account = manager.authenticate_account(api_key, secret_key)
            if account:
                print(f"Authentication successful for {account.service_name}")
                print(f"Permissions: {[p.value for p in account.permissions]}")
            else:
                print("Authentication failed")
        
        elif args.rotate:
            account = manager.rotate_credentials(args.rotate)
            if account:
                print(f"Credentials rotated for {args.rotate}")
                print(f"New API Key: {account.api_key}")
                print(f"New Secret Key: {account.secret_key}")
            else:
                print(f"Account {args.rotate} not found")
        
        elif args.deactivate:
            success = manager.deactivate_account(args.deactivate)
            print(f"Account {args.deactivate}: {'deactivated' if success else 'not found'}")
        
        elif args.cleanup:
            expired = manager.cleanup_expired_accounts()
            print(f"Cleaned up {len(expired)} expired accounts")
            if expired:
                print("Expired accounts:", expired)
        
        elif args.setup_defaults:
            accounts = setup_default_service_accounts(manager)
            print(f"Setup {len(accounts)} default service accounts")
            for service, account in accounts.items():
                print(f"  {service}: {account.account_id}")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)