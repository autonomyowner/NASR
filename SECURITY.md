# The HIVE Translation System - Security Documentation

## 🔐 Security Overview

The HIVE Translation System implements comprehensive security measures to protect real-time voice translation communications, user data, and system infrastructure. This document outlines security procedures, certificate management, and compliance requirements for production deployment.

## 🛡️ Security Architecture

### Security Layers

```
Security Architecture Stack
┌─────────────────────────────────────────────────────────────────┐
│ Layer 7: Application Security                                   │
│ • JWT Authentication • API Rate Limiting • Input Validation    │
│ • Session Management • RBAC Authorization                      │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Layer 6: WebRTC Security                                        │
│ • DTLS Encryption • SRTP Media Security • ICE Authentication   │
│ • TURN Server Security • Media Path Encryption                 │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Layer 5: Transport Security                                     │
│ • TLS 1.3 Encryption • Certificate Pinning • HSTS Headers     │
│ • Perfect Forward Secrecy • SNI Support                       │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: Network Security                                       │
│ • Firewall Rules • Port Restrictions • DDoS Protection       │
│ • Network Segmentation • VPN Access                           │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: Infrastructure Security                               │
│ • Container Security • Secrets Management • Resource Isolation │
│ • Security Monitoring • Intrusion Detection                   │
└─────────────────────────────────────────────────────────────────┘
```

### Security Principles

1. **Defense in Depth**: Multiple security layers with no single point of failure
2. **Zero Trust Architecture**: Verify every request, encrypt every communication
3. **Principle of Least Privilege**: Minimal access permissions for all components
4. **Security by Design**: Security built into architecture from the ground up
5. **Continuous Monitoring**: Real-time security event detection and response

## 🔑 Authentication & Authorization

### JWT Token Management

#### Token Generation and Validation

```python
# Auth Service JWT Configuration
JWT_CONFIG = {
    'algorithm': 'RS256',           # Asymmetric encryption for security
    'key_rotation_hours': 24,       # Rotate keys every 24 hours
    'token_ttl_hours': 2,          # Short-lived tokens
    'refresh_ttl_hours': 168,      # Refresh tokens valid for 1 week
    'issuer': 'thehive-auth',      # Token issuer identification
    'audience': 'thehive-system'   # Intended audience
}
```

#### Token Scopes and Permissions

```json
{
  "room_access": {
    "permissions": ["can_join", "can_listen"],
    "scope": "participant"
  },
  "speaker_access": {
    "permissions": ["can_join", "can_listen", "can_speak", "can_translate"],
    "scope": "speaker"
  },
  "moderator_access": {
    "permissions": ["can_join", "can_listen", "can_speak", "can_translate", "can_moderate"],
    "scope": "moderator"
  },
  "translator_worker": {
    "permissions": ["can_join", "can_process_audio", "can_publish_translation"],
    "scope": "system"
  }
}
```

#### Token Rotation and Revocation

```bash
# Automated token rotation (cron job)
#!/bin/bash
# rotate-jwt-keys.sh (runs every 12 hours)

# Generate new keypair
openssl genrsa -out /etc/ssl/thehive/jwt_private_new.key 4096
openssl rsa -in /etc/ssl/thehive/jwt_private_new.key -pubout -out /etc/ssl/thehive/jwt_public_new.key

# Update auth service configuration
curl -X POST http://localhost:8004/admin/rotate-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "private_key_path": "/etc/ssl/thehive/jwt_private_new.key",
    "public_key_path": "/etc/ssl/thehive/jwt_public_new.key",
    "transition_period_minutes": 30
  }'

# Clean up old keys after transition
sleep 1800  # 30 minutes
rm /etc/ssl/thehive/jwt_private_old.key /etc/ssl/thehive/jwt_public_old.key
```

### TURN Server Security

#### Credential Management

```bash
# CoTURN secure configuration (/etc/turnserver.conf)
listening-port=3478
tls-listening-port=5349
min-port=50000
max-port=50199

# Security settings
fingerprint
lt-cred-mech
use-auth-secret
static-auth-secret=${TURN_SECRET_KEY}
realm=turn.yourdomain.com
server-name=turn.yourdomain.com

# Certificate configuration
cert=/etc/ssl/thehive/turn_cert.pem
pkey=/etc/ssl/thehive/turn_key.pem

# Security hardening
no-multicast-peers
denied-peer-ip=0.0.0.0-0.255.255.255
denied-peer-ip=127.0.0.0-127.255.255.255
denied-peer-ip=169.254.0.0-169.254.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.0.0.0-192.0.0.255
denied-peer-ip=192.168.0.0-192.168.255.255
denied-peer-ip=224.0.0.0-255.255.255.255

# Rate limiting
max-bps=1000000  # 1 Mbps per allocation
bps-capacity=5000000  # 5 Mbps total capacity

# Logging and monitoring
log-file=/var/log/turnserver.log
verbose
```

## 📜 Certificate Management

### SSL/TLS Certificate Lifecycle

#### Automated Certificate Management

```bash
#!/bin/bash
# certificate-manager.sh - Comprehensive certificate lifecycle management

set -euo pipefail

DOMAINS=(
    "sfu.yourdomain.com"
    "turn.yourdomain.com" 
    "api.yourdomain.com"
    "monitoring.yourdomain.com"
)

CERT_DIR="/etc/ssl/thehive"
BACKUP_DIR="/backup/certificates"
LOG_FILE="/var/log/cert-manager.log"

# Function to backup existing certificates
backup_certificates() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="${BACKUP_DIR}/${timestamp}"
    
    echo "$(date): Backing up certificates to ${backup_path}" >> $LOG_FILE
    mkdir -p "$backup_path"
    
    if [ -d "$CERT_DIR" ]; then
        cp -r "$CERT_DIR"/* "$backup_path/"
        echo "$(date): Backup completed successfully" >> $LOG_FILE
    fi
}

# Function to obtain/renew certificates
obtain_certificates() {
    for domain in "${DOMAINS[@]}"; do
        echo "$(date): Processing certificate for $domain" >> $LOG_FILE
        
        # Use Certbot for Let's Encrypt
        certbot certonly \
            --standalone \
            --non-interactive \
            --agree-tos \
            --email admin@yourdomain.com \
            --domains "$domain" \
            --cert-name "$domain" \
            --key-type rsa \
            --rsa-key-size 4096
        
        if [ $? -eq 0 ]; then
            echo "$(date): Certificate obtained successfully for $domain" >> $LOG_FILE
        else
            echo "$(date): ERROR: Certificate generation failed for $domain" >> $LOG_FILE
            exit 1
        fi
    done
}

# Function to deploy certificates to services
deploy_certificates() {
    echo "$(date): Deploying certificates to services" >> $LOG_FILE
    
    # Create service-specific certificate directories
    mkdir -p "$CERT_DIR"/{nginx,livekit,coturn,grafana}
    
    # Deploy to each service
    for domain in "${DOMAINS[@]}"; do
        local cert_path="/etc/letsencrypt/live/$domain"
        
        case $domain in
            "sfu.yourdomain.com")
                cp "$cert_path/fullchain.pem" "$CERT_DIR/livekit/cert.pem"
                cp "$cert_path/privkey.pem" "$CERT_DIR/livekit/key.pem"
                ;;
            "turn.yourdomain.com")
                cp "$cert_path/fullchain.pem" "$CERT_DIR/coturn/cert.pem"
                cp "$cert_path/privkey.pem" "$CERT_DIR/coturn/key.pem"
                ;;
            "api.yourdomain.com")
                cp "$cert_path/fullchain.pem" "$CERT_DIR/nginx/cert.pem"
                cp "$cert_path/privkey.pem" "$CERT_DIR/nginx/key.pem"
                ;;
            "monitoring.yourdomain.com")
                cp "$cert_path/fullchain.pem" "$CERT_DIR/grafana/cert.pem"
                cp "$cert_path/privkey.pem" "$CERT_DIR/grafana/key.pem"
                ;;
        esac
    done
    
    # Set appropriate permissions
    chmod 644 "$CERT_DIR"/*/*.pem
    chmod 600 "$CERT_DIR"/*/key.pem
    
    echo "$(date): Certificates deployed successfully" >> $LOG_FILE
}

# Function to restart services
restart_services() {
    echo "$(date): Restarting services with new certificates" >> $LOG_FILE
    
    # Restart Docker services
    cd /opt/thehive/backend/infra
    docker-compose restart nginx livekit coturn grafana
    
    # Restart system services if applicable
    if systemctl is-active --quiet coturn; then
        systemctl restart coturn
    fi
    
    echo "$(date): Services restarted successfully" >> $LOG_FILE
}

# Function to verify certificate validity
verify_certificates() {
    echo "$(date): Verifying certificate installation" >> $LOG_FILE
    
    for domain in "${DOMAINS[@]}"; do
        local port
        case $domain in
            "sfu.yourdomain.com") port=7881 ;;
            "turn.yourdomain.com") port=5349 ;;
            "api.yourdomain.com") port=443 ;;
            "monitoring.yourdomain.com") port=443 ;;
        esac
        
        # Test certificate validity
        if echo | openssl s_client -connect "$domain:$port" -servername "$domain" 2>/dev/null | openssl x509 -noout -checkend 86400; then
            echo "$(date): Certificate valid for $domain" >> $LOG_FILE
        else
            echo "$(date): WARNING: Certificate issues detected for $domain" >> $LOG_FILE
        fi
    done
}

# Main execution
main() {
    echo "$(date): Starting certificate management process" >> $LOG_FILE
    
    backup_certificates
    obtain_certificates
    deploy_certificates
    restart_services
    verify_certificates
    
    echo "$(date): Certificate management completed successfully" >> $LOG_FILE
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

#### Certificate Monitoring

```bash
#!/bin/bash
# certificate-monitor.sh - Monitor certificate expiration

# Check certificate expiration (run daily via cron)
check_certificate_expiration() {
    local domain=$1
    local port=$2
    local warning_days=30
    
    local expiry_date=$(echo | openssl s_client -connect "$domain:$port" -servername "$domain" 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
    local expiry_epoch=$(date -d "$expiry_date" +%s)
    local current_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
    
    if [ $days_until_expiry -le $warning_days ]; then
        echo "WARNING: Certificate for $domain expires in $days_until_expiry days"
        
        # Send alert (customize notification method)
        curl -X POST https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK \
          -H 'Content-type: application/json' \
          --data "{\"text\":\"Certificate for $domain expires in $days_until_expiry days!\"}"
        
        # If less than 7 days, attempt renewal
        if [ $days_until_expiry -le 7 ]; then
            echo "AUTO-RENEWING: Certificate expires in $days_until_expiry days"
            /opt/thehive/scripts/certificate-manager.sh
        fi
    fi
}

# Check all domains
check_certificate_expiration "sfu.yourdomain.com" 7881
check_certificate_expiration "turn.yourdomain.com" 5349
check_certificate_expiration "api.yourdomain.com" 443
check_certificate_expiration "monitoring.yourdomain.com" 3001
```

### Certificate Security Best Practices

1. **Key Length**: Minimum 2048-bit RSA (recommended: 4096-bit)
2. **Algorithms**: RSA-SHA256 or ECDSA P-256
3. **Validity Period**: Maximum 90 days (Let's Encrypt standard)
4. **Key Storage**: Secure file permissions (600 for private keys)
5. **Rotation**: Automated renewal 30 days before expiration
6. **Backup**: Encrypted backups of all certificate material

## 🔒 WebRTC Security

### DTLS and SRTP Configuration

```javascript
// Secure WebRTC configuration
const rtcConfiguration = {
  iceServers: [
    {
      urls: 'stun:turn.yourdomain.com:3478'
    },
    {
      urls: [
        'turn:turn.yourdomain.com:3478?transport=udp',
        'turns:turn.yourdomain.com:5349?transport=tcp'
      ],
      username: temporaryUsername,  // Time-based username
      credential: hmacCredential    // HMAC-based credential
    }
  ],
  iceCandidatePoolSize: 10,
  bundlePolicy: 'max-bundle',        // Minimize ICE candidates
  rtcpMuxPolicy: 'require',          // Multiplex RTP and RTCP
  iceTransportPolicy: 'all'          // Use both STUN and TURN
};

// Security constraints
const mediaConstraints = {
  audio: {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    sampleRate: 16000,
    channelCount: 1,
    // Disable potentially insecure features
    googEchoCancellation: false,
    googAutoGainControl: false,
    googNoiseSuppression: false,
    googHighpassFilter: false,
    googTypingNoiseDetection: false
  }
};
```

### Media Encryption Validation

```javascript
// Verify encryption status
async function verifyEncryption(peerConnection) {
  const stats = await peerConnection.getStats();
  
  for (const [id, stat] of stats) {
    if (stat.type === 'transport') {
      // Verify DTLS encryption
      if (stat.dtlsState !== 'connected') {
        throw new Error('DTLS encryption not established');
      }
      
      // Verify SRTP encryption
      if (!stat.srtpCipher || !stat.srtpCipher.includes('AES')) {
        throw new Error('SRTP encryption not using AES');
      }
      
      console.log('Encryption Status:', {
        dtlsState: stat.dtlsState,
        dtlsCipher: stat.dtlsCipher,
        srtpCipher: stat.srtpCipher
      });
    }
  }
}
```

## 🚨 Security Monitoring

### Security Event Detection

```python
# Security monitoring service
import logging
import re
from typing import Dict, List
from datetime import datetime, timedelta
import asyncio

class SecurityMonitor:
    def __init__(self):
        self.failed_login_threshold = 5
        self.failed_login_window = timedelta(minutes=15)
        self.suspicious_patterns = [
            r'(?i)(union|select|drop|insert|delete|update|exec)',  # SQL injection
            r'<script[^>]*>.*?</script>',                          # XSS
            r'\.\./',                                              # Path traversal
            r'(?i)(eval|exec|system|shell_exec)',                 # Code injection
        ]
        
    async def monitor_authentication_events(self, log_entry: Dict):
        """Monitor authentication failures and potential attacks"""
        if log_entry.get('event') == 'authentication_failed':
            ip_address = log_entry.get('ip_address')
            timestamp = datetime.fromisoformat(log_entry.get('timestamp'))
            
            # Track failed attempts per IP
            recent_failures = await self.get_recent_failures(ip_address, timestamp)
            
            if len(recent_failures) >= self.failed_login_threshold:
                await self.handle_potential_brute_force(ip_address, recent_failures)
                
    async def monitor_input_validation(self, request_data: Dict):
        """Detect potential injection attacks"""
        for field, value in request_data.items():
            if isinstance(value, str):
                for pattern in self.suspicious_patterns:
                    if re.search(pattern, value):
                        await self.handle_suspicious_input(field, value, pattern)
                        
    async def monitor_resource_access(self, resource_request: Dict):
        """Monitor for unauthorized resource access attempts"""
        user_permissions = resource_request.get('user_permissions', [])
        requested_resource = resource_request.get('resource')
        required_permission = resource_request.get('required_permission')
        
        if required_permission not in user_permissions:
            await self.handle_unauthorized_access(resource_request)
            
    async def handle_potential_brute_force(self, ip_address: str, failures: List):
        """Respond to brute force attempts"""
        logging.warning(f"Potential brute force attack from {ip_address}")
        
        # Implement IP blocking
        await self.block_ip_address(ip_address, duration_minutes=60)
        
        # Send security alert
        await self.send_security_alert({
            'type': 'brute_force_attempt',
            'ip_address': ip_address,
            'failure_count': len(failures),
            'time_window': self.failed_login_window,
            'action_taken': 'ip_blocked'
        })
        
    async def handle_suspicious_input(self, field: str, value: str, pattern: str):
        """Handle potentially malicious input"""
        logging.warning(f"Suspicious input detected in field '{field}': {pattern}")
        
        await self.send_security_alert({
            'type': 'suspicious_input',
            'field': field,
            'pattern_matched': pattern,
            'value_preview': value[:50] + '...' if len(value) > 50 else value,
            'timestamp': datetime.utcnow().isoformat()
        })
```

### Automated Security Scanning

```bash
#!/bin/bash
# security-scan.sh - Comprehensive security scanning

# Container security scanning
scan_containers() {
    echo "Running container security scan..."
    
    # Scan all running containers
    for container in $(docker ps --format "{{.Names}}"); do
        echo "Scanning container: $container"
        
        # Use Trivy for vulnerability scanning
        trivy image $(docker inspect --format='{{.Config.Image}}' $container) \
            --exit-code 1 \
            --severity HIGH,CRITICAL \
            --format json > "/tmp/scan-$container.json"
        
        # Check for high/critical vulnerabilities
        critical_count=$(jq '.Results[].Vulnerabilities[] | select(.Severity=="CRITICAL") | .VulnerabilityID' "/tmp/scan-$container.json" | wc -l)
        
        if [ $critical_count -gt 0 ]; then
            echo "ALERT: $critical_count critical vulnerabilities found in $container"
        fi
    done
}

# Network security scan
scan_network() {
    echo "Running network security scan..."
    
    # Port scan
    nmap -sS -O localhost -p 1-65535 > /tmp/port-scan.txt
    
    # Check for unexpected open ports
    expected_ports=(22 80 443 3001 3478 5349 6379 7880 8001 8002 8003 8004 9090 16686)
    open_ports=$(nmap -sS localhost -p 1-65535 | grep "^[0-9]" | grep "open" | cut -d'/' -f1)
    
    for port in $open_ports; do
        if [[ ! " ${expected_ports[@]} " =~ " $port " ]]; then
            echo "WARNING: Unexpected open port $port"
        fi
    done
}

# SSL/TLS security scan
scan_ssl() {
    echo "Running SSL/TLS security scan..."
    
    domains=("sfu.yourdomain.com:7881" "turn.yourdomain.com:5349" "api.yourdomain.com:443")
    
    for domain_port in "${domains[@]}"; do
        echo "Scanning SSL configuration for $domain_port"
        
        # Use testssl.sh for comprehensive SSL testing
        ./testssl.sh --quiet --color 0 "$domain_port" > "/tmp/ssl-scan-${domain_port//:/-}.txt"
        
        # Check for critical SSL issues
        if grep -q "CRITICAL" "/tmp/ssl-scan-${domain_port//:/-}.txt"; then
            echo "CRITICAL SSL issues found for $domain_port"
        fi
    done
}

# Application security scan
scan_application() {
    echo "Running application security scan..."
    
    # OWASP ZAP baseline scan
    docker run -t owasp/zap2docker-stable zap-baseline.py \
        -t http://localhost:5173 \
        -J zap-report.json \
        -r zap-report.html
        
    # Check for high-risk findings
    high_risk_count=$(jq '.site[].alerts[] | select(.riskdesc | startswith("High")) | .name' zap-report.json | wc -l)
    
    if [ $high_risk_count -gt 0 ]; then
        echo "ALERT: $high_risk_count high-risk security issues found"
    fi
}

# Main security scan execution
main() {
    echo "Starting comprehensive security scan at $(date)"
    
    scan_containers
    scan_network  
    scan_ssl
    scan_application
    
    echo "Security scan completed at $(date)"
    
    # Generate summary report
    {
        echo "Security Scan Summary - $(date)"
        echo "=================================="
        echo
        echo "Container Vulnerabilities:"
        find /tmp -name "scan-*.json" -exec jq -r '.Results[].Vulnerabilities[] | select(.Severity=="CRITICAL") | "CRITICAL: \(.VulnerabilityID) - \(.Title)"' {} \;
        echo
        echo "Network Security:"
        echo "Open ports: $(nmap -sS localhost -p 1-65535 | grep 'open' | wc -l)"
        echo
        echo "SSL Security:"
        grep -h "CRITICAL\|HIGH" /tmp/ssl-scan-*.txt || echo "No critical SSL issues found"
        echo
        echo "Application Security:"
        if [ -f zap-report.json ]; then
            echo "High-risk findings: $(jq '[.site[].alerts[] | select(.riskdesc | startswith("High"))] | length' zap-report.json)"
        fi
    } > /tmp/security-summary.txt
    
    # Send report to security team
    mail -s "Security Scan Report - $(date)" security@yourdomain.com < /tmp/security-summary.txt
}

# Execute security scan
main "$@"
```

## 🔐 Secrets Management

### Environment Variable Security

```bash
#!/bin/bash
# secrets-manager.sh - Secure secrets management

SECRETS_DIR="/opt/thehive/secrets"
ENCRYPTED_SECRETS="$SECRETS_DIR/secrets.gpg"
ENV_FILE="/opt/thehive/backend/infra/.env"

# Encrypt secrets file
encrypt_secrets() {
    local secrets_file=$1
    
    # Generate random encryption key if not exists
    if [ ! -f "$SECRETS_DIR/encryption.key" ]; then
        openssl rand -base64 32 > "$SECRETS_DIR/encryption.key"
        chmod 600 "$SECRETS_DIR/encryption.key"
    fi
    
    # Encrypt secrets file
    gpg --batch --yes --cipher-algo AES256 --compress-algo 2 --symmetric \
        --passphrase-file "$SECRETS_DIR/encryption.key" \
        --output "$ENCRYPTED_SECRETS" "$secrets_file"
    
    # Remove plaintext file
    shred -u "$secrets_file"
    
    echo "Secrets encrypted successfully"
}

# Decrypt and load secrets
load_secrets() {
    if [ ! -f "$ENCRYPTED_SECRETS" ]; then
        echo "Encrypted secrets file not found"
        exit 1
    fi
    
    # Decrypt secrets
    gpg --batch --yes --quiet --decrypt \
        --passphrase-file "$SECRETS_DIR/encryption.key" \
        "$ENCRYPTED_SECRETS" > "$ENV_FILE.tmp"
    
    # Set restrictive permissions
    chmod 600 "$ENV_FILE.tmp"
    
    # Atomic move to final location
    mv "$ENV_FILE.tmp" "$ENV_FILE"
    
    echo "Secrets loaded successfully"
}

# Generate secure random secrets
generate_secrets() {
    cat > "$SECRETS_DIR/secrets.txt" << EOF
# Generated secrets - $(date)
LIVEKIT_SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 64)
TURN_SECRET_KEY=$(openssl rand -hex 32)
AUTH_SERVICE_API_KEY=$(openssl rand -hex 32)
DATABASE_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)

# Session encryption
SESSION_SECRET=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)

# API keys (replace with actual values)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
EMAIL_API_KEY=your_email_api_key_here
MONITORING_API_KEY=your_monitoring_api_key_here
EOF
    
    encrypt_secrets "$SECRETS_DIR/secrets.txt"
    echo "New secrets generated and encrypted"
}

# Rotate secrets
rotate_secrets() {
    local service=$1
    
    case $service in
        "jwt")
            new_secret=$(openssl rand -hex 64)
            update_secret "JWT_SECRET_KEY" "$new_secret"
            restart_service "auth-service"
            ;;
        "turn")
            new_secret=$(openssl rand -hex 32)
            update_secret "TURN_SECRET_KEY" "$new_secret"
            restart_service "coturn"
            ;;
        "all")
            generate_secrets
            restart_all_services
            ;;
        *)
            echo "Usage: rotate_secrets {jwt|turn|all}"
            exit 1
            ;;
    esac
}

# Update specific secret
update_secret() {
    local key=$1
    local value=$2
    
    # Load current secrets
    load_secrets
    
    # Update the specific key
    sed -i "s/^$key=.*/$key=$value/" "$ENV_FILE"
    
    # Re-encrypt
    encrypt_secrets "$ENV_FILE"
    
    echo "Secret $key updated successfully"
}

# Restart services after secret rotation
restart_service() {
    local service=$1
    echo "Restarting $service..."
    
    cd /opt/thehive/backend/infra
    docker-compose restart "$service"
    
    # Wait for service to be healthy
    timeout 60 bash -c "until curl -f http://localhost:$(get_service_port $service)/health; do sleep 2; done"
    
    echo "$service restarted successfully"
}

# Main execution
case "${1:-}" in
    "generate") generate_secrets ;;
    "load") load_secrets ;;
    "rotate") rotate_secrets "${2:-}" ;;
    "encrypt") encrypt_secrets "$2" ;;
    *) 
        echo "Usage: $0 {generate|load|rotate|encrypt}"
        echo "  generate - Generate new random secrets"
        echo "  load     - Decrypt and load secrets to environment"
        echo "  rotate   - Rotate specific or all secrets"
        echo "  encrypt  - Encrypt a secrets file"
        exit 1
        ;;
esac
```

## 📊 Compliance and Auditing

### Security Audit Logging

```python
# Security audit logging
import json
import logging
from datetime import datetime
from typing import Dict, Any
from enum import Enum

class SecurityEventType(Enum):
    AUTHENTICATION_SUCCESS = "auth_success"
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_FAILURE = "authz_failure"
    RESOURCE_ACCESS = "resource_access"
    CONFIGURATION_CHANGE = "config_change"
    SECURITY_VIOLATION = "security_violation"
    CERTIFICATE_ROTATION = "cert_rotation"
    SECRET_ROTATION = "secret_rotation"

class SecurityAuditor:
    def __init__(self, log_file_path: str = "/var/log/thehive/security-audit.log"):
        self.logger = logging.getLogger("security_audit")
        handler = logging.FileHandler(log_file_path)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_security_event(
        self,
        event_type: SecurityEventType,
        user_id: str = None,
        ip_address: str = None,
        resource: str = None,
        details: Dict[str, Any] = None
    ):
        """Log security-related events for audit purposes"""
        
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "resource": resource,
            "details": details or {},
            "session_id": self._get_session_id(),
            "user_agent": self._get_user_agent()
        }
        
        # Log as structured JSON for easy parsing
        self.logger.info(json.dumps(audit_entry))
        
        # Send to SIEM if configured
        self._send_to_siem(audit_entry)
    
    def log_authentication_attempt(
        self,
        user_id: str,
        ip_address: str,
        success: bool,
        failure_reason: str = None
    ):
        """Log authentication attempts"""
        event_type = SecurityEventType.AUTHENTICATION_SUCCESS if success else SecurityEventType.AUTHENTICATION_FAILURE
        
        details = {
            "success": success,
            "method": "jwt",
            "failure_reason": failure_reason
        }
        
        self.log_security_event(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details
        )
    
    def log_configuration_change(
        self,
        admin_user: str,
        component: str,
        changes: Dict[str, Any]
    ):
        """Log security-relevant configuration changes"""
        self.log_security_event(
            event_type=SecurityEventType.CONFIGURATION_CHANGE,
            user_id=admin_user,
            resource=component,
            details={
                "changes": changes,
                "component": component
            }
        )
```

### Compliance Checklist

```bash
#!/bin/bash
# compliance-checker.sh - Security compliance validation

run_compliance_check() {
    echo "Starting security compliance check..."
    
    # Check 1: Strong authentication
    check_authentication_security() {
        echo "Checking authentication security..."
        
        # Verify JWT key strength
        jwt_key_length=$(openssl rsa -in /etc/ssl/thehive/jwt_private.key -text -noout 2>/dev/null | grep "Private-Key" | grep -o '[0-9]*' | head -1)
        if [ "$jwt_key_length" -lt 2048 ]; then
            echo "❌ FAIL: JWT key length ($jwt_key_length) below minimum (2048)"
        else
            echo "✅ PASS: JWT key length sufficient ($jwt_key_length)"
        fi
        
        # Check token expiration
        if grep -q "token_ttl_hours.*[0-9][0-9]" /opt/thehive/backend/infra/.env; then
            echo "❌ FAIL: Token TTL too long (>9 hours)"
        else
            echo "✅ PASS: Token TTL within acceptable range"
        fi
    }
    
    # Check 2: Encryption in transit
    check_encryption_in_transit() {
        echo "Checking encryption in transit..."
        
        # Test TLS configuration
        domains=("sfu.yourdomain.com" "turn.yourdomain.com" "api.yourdomain.com")
        
        for domain in "${domains[@]}"; do
            tls_version=$(echo | openssl s_client -connect "$domain:443" 2>/dev/null | grep "Protocol" | cut -d: -f2 | tr -d ' ')
            
            if [[ "$tls_version" =~ TLSv1\.[23] ]]; then
                echo "✅ PASS: $domain using secure TLS version ($tls_version)"
            else
                echo "❌ FAIL: $domain using insecure TLS version ($tls_version)"
            fi
        done
    }
    
    # Check 3: Access controls
    check_access_controls() {
        echo "Checking access controls..."
        
        # Check file permissions
        critical_files=(
            "/opt/thehive/backend/infra/.env:600"
            "/etc/ssl/thehive/jwt_private.key:600"
            "/opt/thehive/secrets/encryption.key:600"
        )
        
        for file_perm in "${critical_files[@]}"; do
            file="${file_perm%:*}"
            expected_perm="${file_perm#*:}"
            
            if [ -f "$file" ]; then
                actual_perm=$(stat -c "%a" "$file")
                if [ "$actual_perm" = "$expected_perm" ]; then
                    echo "✅ PASS: $file has correct permissions ($actual_perm)"
                else
                    echo "❌ FAIL: $file has incorrect permissions ($actual_perm, expected: $expected_perm)"
                fi
            else
                echo "⚠️  WARN: $file not found"
            fi
        done
    }
    
    # Check 4: Vulnerability management
    check_vulnerability_management() {
        echo "Checking vulnerability management..."
        
        # Check for critical vulnerabilities
        critical_vulns=$(find /tmp -name "scan-*.json" -exec jq -r '.Results[].Vulnerabilities[] | select(.Severity=="CRITICAL") | .VulnerabilityID' {} \; 2>/dev/null | wc -l)
        
        if [ "$critical_vulns" -eq 0 ]; then
            echo "✅ PASS: No critical vulnerabilities detected"
        else
            echo "❌ FAIL: $critical_vulns critical vulnerabilities found"
        fi
    }
    
    # Check 5: Monitoring and logging
    check_monitoring_logging() {
        echo "Checking monitoring and logging..."
        
        # Check if security audit log exists and is being written to
        if [ -f "/var/log/thehive/security-audit.log" ]; then
            recent_entries=$(find /var/log/thehive/security-audit.log -mtime -1 -exec wc -l {} \; | cut -d' ' -f1)
            if [ "$recent_entries" -gt 0 ]; then
                echo "✅ PASS: Security audit logging is active ($recent_entries recent entries)"
            else
                echo "⚠️  WARN: No recent security audit log entries"
            fi
        else
            echo "❌ FAIL: Security audit log file not found"
        fi
        
        # Check monitoring services
        monitoring_services=("prometheus" "grafana" "jaeger")
        for service in "${monitoring_services[@]}"; do
            if docker-compose -f /opt/thehive/backend/infra/docker-compose.yml ps $service | grep -q "Up"; then
                echo "✅ PASS: $service monitoring service is running"
            else
                echo "❌ FAIL: $service monitoring service not running"
            fi
        done
    }
    
    # Run all checks
    check_authentication_security
    check_encryption_in_transit
    check_access_controls
    check_vulnerability_management
    check_monitoring_logging
    
    echo "Compliance check completed"
}

# Generate compliance report
generate_compliance_report() {
    local report_file="/tmp/compliance-report-$(date +%Y%m%d).txt"
    
    {
        echo "The HIVE Translation System - Security Compliance Report"
        echo "Generated: $(date)"
        echo "========================================================"
        echo
        run_compliance_check
    } | tee "$report_file"
    
    echo "Compliance report saved to: $report_file"
}

# Main execution
case "${1:-check}" in
    "check") run_compliance_check ;;
    "report") generate_compliance_report ;;
    *) 
        echo "Usage: $0 {check|report}"
        exit 1
        ;;
esac
```

## 🚨 Incident Response

### Security Incident Response Plan

```bash
#!/bin/bash
# incident-response.sh - Automated security incident response

INCIDENT_LOG="/var/log/thehive/security-incidents.log"
BACKUP_DIR="/backup/incident-response"

# Incident response levels
declare -A RESPONSE_LEVELS=(
    ["LOW"]="Log and monitor"
    ["MEDIUM"]="Alert security team"
    ["HIGH"]="Block threat and alert"
    ["CRITICAL"]="Isolate system and escalate"
)

respond_to_incident() {
    local incident_type=$1
    local severity=$2
    local details=$3
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Log incident
    echo "[$timestamp] INCIDENT: $incident_type | SEVERITY: $severity | $details" >> "$INCIDENT_LOG"
    
    case $severity in
        "CRITICAL")
            # Immediate containment actions
            isolate_system
            escalate_to_security_team "$incident_type" "$details"
            create_incident_backup
            ;;
        "HIGH")
            # Blocking and alerting actions
            block_threat "$details"
            alert_security_team "$incident_type" "$details"
            ;;
        "MEDIUM")
            # Monitoring and alerting actions
            alert_security_team "$incident_type" "$details"
            increase_monitoring
            ;;
        "LOW")
            # Logging only
            log_incident "$incident_type" "$details"
            ;;
    esac
}

# System isolation for critical incidents
isolate_system() {
    echo "CRITICAL: Isolating system due to security incident"
    
    # Stop external connections
    iptables -P INPUT DROP
    iptables -P FORWARD DROP
    iptables -P OUTPUT DROP
    
    # Allow only essential internal communication
    iptables -A INPUT -i lo -j ACCEPT
    iptables -A OUTPUT -o lo -j ACCEPT
    
    # Create system snapshot
    docker-compose -f /opt/thehive/backend/infra/docker-compose.yml pause
    
    echo "System isolated successfully"
}

# Block specific threats
block_threat() {
    local threat_details=$1
    
    # Extract IP address if present
    ip_address=$(echo "$threat_details" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
    
    if [ -n "$ip_address" ]; then
        echo "Blocking IP address: $ip_address"
        iptables -A INPUT -s "$ip_address" -j DROP
        iptables -A OUTPUT -d "$ip_address" -j DROP
        
        # Add to fail2ban if available
        if command -v fail2ban-client &> /dev/null; then
            fail2ban-client set sshd banip "$ip_address"
        fi
    fi
}

# Create incident response backup
create_incident_backup() {
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local incident_backup_dir="$BACKUP_DIR/incident_$backup_timestamp"
    
    mkdir -p "$incident_backup_dir"
    
    # Backup critical system state
    cp -r /var/log/thehive/* "$incident_backup_dir/"
    docker-compose -f /opt/thehive/backend/infra/docker-compose.yml logs > "$incident_backup_dir/container_logs.txt"
    netstat -tuln > "$incident_backup_dir/network_connections.txt"
    ps aux > "$incident_backup_dir/running_processes.txt"
    
    echo "Incident backup created at: $incident_backup_dir"
}

# Security team notification
escalate_to_security_team() {
    local incident_type=$1
    local details=$2
    
    # Send emergency notification
    curl -X POST https://hooks.slack.com/services/YOUR/EMERGENCY/WEBHOOK \
        -H 'Content-type: application/json' \
        --data "{
            \"text\": \"🚨 CRITICAL SECURITY INCIDENT 🚨\",
            \"attachments\": [{
                \"color\": \"danger\",
                \"fields\": [
                    {\"title\": \"Incident Type\", \"value\": \"$incident_type\", \"short\": true},
                    {\"title\": \"Time\", \"value\": \"$(date)\", \"short\": true},
                    {\"title\": \"Details\", \"value\": \"$details\", \"short\": false},
                    {\"title\": \"Actions Taken\", \"value\": \"System isolated, backup created\", \"short\": false}
                ]
            }]
        }"
    
    # Send email notification
    {
        echo "CRITICAL SECURITY INCIDENT - The HIVE Translation System"
        echo "========================================="
        echo "Time: $(date)"
        echo "Incident Type: $incident_type"
        echo "Details: $details"
        echo ""
        echo "Immediate actions taken:"
        echo "- System has been isolated"
        echo "- Incident backup created"
        echo "- Security team notified"
        echo ""
        echo "Please respond immediately to assess and remediate."
    } | mail -s "CRITICAL: Security Incident - The HIVE" security@yourdomain.com
}

# Example usage for common incident types
case "${1:-}" in
    "brute_force")
        respond_to_incident "Brute Force Attack" "HIGH" "Multiple failed login attempts from IP: $2"
        ;;
    "injection")
        respond_to_incident "Code Injection Attempt" "CRITICAL" "Malicious code injection detected: $2"
        ;;
    "unauthorized_access")
        respond_to_incident "Unauthorized Access" "HIGH" "Unauthorized resource access attempt: $2"
        ;;
    "ddos")
        respond_to_incident "DDoS Attack" "CRITICAL" "Distributed denial of service attack detected"
        ;;
    *)
        echo "Usage: $0 {brute_force|injection|unauthorized_access|ddos} [details]"
        echo "Available incident types and default severity levels:"
        echo "  brute_force         - HIGH"
        echo "  injection           - CRITICAL"  
        echo "  unauthorized_access - HIGH"
        echo "  ddos               - CRITICAL"
        exit 1
        ;;
esac
```

## 📋 Security Maintenance Schedule

### Daily Security Tasks
- [x] Review security audit logs
- [x] Check failed authentication attempts
- [x] Monitor certificate expiration warnings
- [x] Verify backup completion
- [x] Review system resource usage

### Weekly Security Tasks
- [x] Run vulnerability scans on all containers
- [x] Review firewall logs and rules
- [x] Update security documentation
- [x] Test incident response procedures
- [x] Rotate non-critical secrets

### Monthly Security Tasks  
- [x] Full security compliance audit
- [x] Penetration testing
- [x] Certificate renewal (if needed)
- [x] Security training updates
- [x] Disaster recovery testing

### Quarterly Security Tasks
- [x] Complete security architecture review
- [x] Update threat model
- [x] Review and update security policies
- [x] Third-party security assessment
- [x] Rotate all critical secrets

---

This security documentation provides comprehensive coverage of The HIVE Translation System's security implementation. Regular review and updates ensure continued protection against evolving threats.

**Document Version**: 1.0  
**Last Updated**: 2024-01-01  
**Next Review**: 2024-04-01  
**Compliance Standards**: SOC 2 Type II, ISO 27001, GDPR