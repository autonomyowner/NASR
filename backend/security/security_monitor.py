"""
Security Monitoring and Audit System for The HIVE Translation Services

Real-time security monitoring, threat detection, and comprehensive audit logging
with integration to Prometheus metrics and alerting systems.
"""

import os
import json
import time
import logging
import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import ipaddress
import redis
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import aiofiles
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EventType(Enum):
    """Security event types"""
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHENTICATION_SUCCESS = "auth_success"
    AUTHORIZATION_DENIED = "authz_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MALICIOUS_INPUT = "malicious_input"
    SERVICE_ERROR = "service_error"
    CERTIFICATE_EXPIRY = "cert_expiry"
    SECRET_ACCESS = "secret_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_id: str
    event_type: EventType
    severity: AlertSeverity
    timestamp: datetime
    source_ip: str
    user_agent: str
    service: str
    endpoint: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = hashlib.sha256(
                f"{self.timestamp.isoformat()}{self.source_ip}{self.service}{self.event_type.value}".encode()
            ).hexdigest()[:16]

@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    event_types: List[EventType]
    severity_threshold: AlertSeverity
    conditions: Dict[str, Any]  # Custom conditions
    time_window_minutes: int = 5
    threshold_count: int = 5
    enabled: bool = True
    
class SecurityMetrics:
    """Prometheus metrics for security monitoring"""
    
    def __init__(self):
        # Event counters
        self.security_events_total = Counter(
            'security_events_total',
            'Total number of security events',
            ['event_type', 'severity', 'service']
        )
        
        # Authentication metrics
        self.auth_attempts_total = Counter(
            'auth_attempts_total',
            'Total authentication attempts',
            ['service', 'result']
        )
        
        self.auth_failures_by_ip = Counter(
            'auth_failures_by_ip',
            'Authentication failures by IP',
            ['source_ip', 'service']
        )
        
        # Rate limiting metrics
        self.rate_limit_violations = Counter(
            'rate_limit_violations_total',
            'Rate limit violations',
            ['source_ip', 'service', 'endpoint']
        )
        
        # Threat detection metrics
        self.threats_detected_total = Counter(
            'threats_detected_total',
            'Threats detected',
            ['threat_type', 'severity']
        )
        
        # Response time metrics
        self.security_check_duration = Histogram(
            'security_check_duration_seconds',
            'Time spent on security checks',
            ['service', 'check_type']
        )
        
        # Current state gauges
        self.active_sessions = Gauge(
            'active_sessions',
            'Number of active user sessions',
            ['service']
        )
        
        self.blocked_ips_count = Gauge(
            'blocked_ips_count',
            'Number of currently blocked IPs'
        )

class ThreatDetector:
    """Advanced threat detection engine"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.behavioral_patterns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.ip_reputation: Dict[str, float] = {}  # IP reputation scores
        self.known_bad_ips: Set[str] = set()
        
    async def analyze_event(self, event: SecurityEvent) -> List[str]:
        """
        Analyze security event for threats
        
        Returns:
            List of detected threat types
        """
        threats = []
        
        # Check for brute force attacks
        if await self._detect_brute_force(event):
            threats.append("brute_force_attack")
        
        # Check for suspicious IP behavior
        if await self._detect_suspicious_ip_behavior(event):
            threats.append("suspicious_ip_behavior")
        
        # Check for anomalous request patterns
        if await self._detect_anomalous_patterns(event):
            threats.append("anomalous_request_pattern")
        
        # Check for privilege escalation attempts
        if await self._detect_privilege_escalation(event):
            threats.append("privilege_escalation_attempt")
        
        # Check for data exfiltration patterns
        if await self._detect_data_exfiltration(event):
            threats.append("data_exfiltration_attempt")
        
        return threats
    
    async def _detect_brute_force(self, event: SecurityEvent) -> bool:
        """Detect brute force authentication attacks"""
        if event.event_type != EventType.AUTHENTICATION_FAILURE:
            return False
        
        # Track failed attempts per IP
        key = f"auth_failures:{event.source_ip}"
        window = 300  # 5 minutes
        threshold = 10
        
        if self.redis_client:
            try:
                # Add current attempt
                await self.redis_client.zadd(key, {str(time.time()): time.time()})
                
                # Remove old attempts
                cutoff = time.time() - window
                await self.redis_client.zremrangebyscore(key, 0, cutoff)
                
                # Count recent attempts
                count = await self.redis_client.zcard(key)
                
                # Set expiration
                await self.redis_client.expire(key, window)
                
                return count >= threshold
                
            except Exception as e:
                logger.error(f"Redis error in brute force detection: {e}")
        
        # Fallback to local tracking
        pattern_key = f"auth_fail:{event.source_ip}"
        now = time.time()
        
        # Clean old entries
        self.behavioral_patterns[pattern_key] = deque(
            [t for t in self.behavioral_patterns[pattern_key] if now - t < window],
            maxlen=100
        )
        
        # Add current attempt
        self.behavioral_patterns[pattern_key].append(now)
        
        return len(self.behavioral_patterns[pattern_key]) >= threshold
    
    async def _detect_suspicious_ip_behavior(self, event: SecurityEvent) -> bool:
        """Detect suspicious IP behavior patterns"""
        # Check if IP is in known bad list
        if event.source_ip in self.known_bad_ips:
            return True
        
        # Check IP reputation score
        reputation = self.ip_reputation.get(event.source_ip, 0.0)
        if reputation < -0.7:  # High suspicion threshold
            return True
        
        # Check for rapid endpoint scanning
        key = f"endpoints:{event.source_ip}"
        window = 60  # 1 minute
        threshold = 20  # 20 different endpoints
        
        if self.redis_client:
            try:
                # Track accessed endpoints
                await self.redis_client.sadd(key, event.endpoint)
                await self.redis_client.expire(key, window)
                
                # Count unique endpoints
                endpoint_count = await self.redis_client.scard(key)
                
                return endpoint_count >= threshold
                
            except Exception as e:
                logger.error(f"Redis error in suspicious IP detection: {e}")
        
        return False
    
    async def _detect_anomalous_patterns(self, event: SecurityEvent) -> bool:
        """Detect anomalous request patterns"""
        # Check for unusual request frequencies
        pattern_key = f"requests:{event.source_ip}:{event.service}"
        now = time.time()
        window = 60  # 1 minute
        
        # Normal request rate is service-dependent
        normal_rates = {
            "auth-service": 10,
            "stt-service": 100,
            "mt-service": 200,
            "tts-service": 50,
        }
        
        threshold = normal_rates.get(event.service, 50) * 3  # 3x normal rate
        
        # Track request times
        self.behavioral_patterns[pattern_key] = deque(
            [t for t in self.behavioral_patterns[pattern_key] if now - t < window],
            maxlen=1000
        )
        
        self.behavioral_patterns[pattern_key].append(now)
        
        return len(self.behavioral_patterns[pattern_key]) >= threshold
    
    async def _detect_privilege_escalation(self, event: SecurityEvent) -> bool:
        """Detect privilege escalation attempts"""
        if event.event_type != EventType.AUTHORIZATION_DENIED:
            return False
        
        # Track authorization failures per user
        if not event.user_id:
            return False
        
        key = f"authz_failures:{event.user_id}"
        window = 300  # 5 minutes
        threshold = 5
        
        pattern_key = f"authz_fail:{event.user_id}"
        now = time.time()
        
        # Clean old entries
        self.behavioral_patterns[pattern_key] = deque(
            [t for t in self.behavioral_patterns[pattern_key] if now - t < window],
            maxlen=100
        )
        
        # Add current attempt
        self.behavioral_patterns[pattern_key].append(now)
        
        return len(self.behavioral_patterns[pattern_key]) >= threshold
    
    async def _detect_data_exfiltration(self, event: SecurityEvent) -> bool:
        """Detect potential data exfiltration attempts"""
        # Check for unusual data access patterns
        if not event.details:
            return False
        
        # Look for large response sizes or bulk data access
        response_size = event.details.get("response_size", 0)
        if response_size > 10 * 1024 * 1024:  # 10MB threshold
            return True
        
        # Check for rapid consecutive data requests
        if event.details.get("request_type") == "data_access":
            key = f"data_access:{event.user_id or event.source_ip}"
            window = 60  # 1 minute
            threshold = 50  # requests
            
            pattern_key = f"data_req:{event.user_id or event.source_ip}"
            now = time.time()
            
            self.behavioral_patterns[pattern_key] = deque(
                [t for t in self.behavioral_patterns[pattern_key] if now - t < window],
                maxlen=200
            )
            
            self.behavioral_patterns[pattern_key].append(now)
            
            return len(self.behavioral_patterns[pattern_key]) >= threshold
        
        return False
    
    def update_ip_reputation(self, ip: str, score_delta: float):
        """Update IP reputation score"""
        current_score = self.ip_reputation.get(ip, 0.0)
        new_score = max(-1.0, min(1.0, current_score + score_delta))
        self.ip_reputation[ip] = new_score
        
        # Add to known bad IPs if score is very low
        if new_score < -0.9:
            self.known_bad_ips.add(ip)

class AlertManager:
    """Manages security alerts and notifications"""
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        smtp_config: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None
    ):
        self.redis_client = redis_client
        self.smtp_config = smtp_config
        self.webhook_url = webhook_url
        self.active_alerts: Dict[str, datetime] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_handlers: List[Callable] = []
        
        # Load default alert rules
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default security alert rules"""
        rules = [
            AlertRule(
                rule_id="auth_failures",
                name="Multiple Authentication Failures",
                description="Multiple failed authentication attempts from same IP",
                event_types=[EventType.AUTHENTICATION_FAILURE],
                severity_threshold=AlertSeverity.HIGH,
                conditions={"count": 10, "time_window": 5},
                time_window_minutes=5,
                threshold_count=10
            ),
            
            AlertRule(
                rule_id="rate_limit_violations",
                name="Rate Limit Violations",
                description="Repeated rate limit violations",
                event_types=[EventType.RATE_LIMIT_EXCEEDED],
                severity_threshold=AlertSeverity.MEDIUM,
                conditions={"count": 5, "time_window": 5},
                time_window_minutes=5,
                threshold_count=5
            ),
            
            AlertRule(
                rule_id="malicious_input",
                name="Malicious Input Detected",
                description="Malicious input patterns detected",
                event_types=[EventType.MALICIOUS_INPUT],
                severity_threshold=AlertSeverity.HIGH,
                conditions={"count": 1},
                time_window_minutes=1,
                threshold_count=1
            ),
            
            AlertRule(
                rule_id="privilege_escalation",
                name="Privilege Escalation Attempt",
                description="Multiple authorization denials indicating privilege escalation",
                event_types=[EventType.PRIVILEGE_ESCALATION],
                severity_threshold=AlertSeverity.CRITICAL,
                conditions={"count": 3, "time_window": 5},
                time_window_minutes=5,
                threshold_count=3
            ),
        ]
        
        for rule in rules:
            self.alert_rules[rule.rule_id] = rule
    
    async def process_event(self, event: SecurityEvent):
        """Process security event against alert rules"""
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue
            
            if event.event_type in rule.event_types:
                if await self._check_rule_conditions(rule, event):
                    await self._trigger_alert(rule, event)
    
    async def _check_rule_conditions(self, rule: AlertRule, event: SecurityEvent) -> bool:
        """Check if alert rule conditions are met"""
        # For now, implement simple count-based rules
        # In production, this would be more sophisticated
        
        key = f"rule_events:{rule.rule_id}:{event.source_ip}"
        window = rule.time_window_minutes * 60
        
        if self.redis_client:
            try:
                # Add current event
                await self.redis_client.zadd(key, {str(time.time()): time.time()})
                
                # Remove old events
                cutoff = time.time() - window
                await self.redis_client.zremrangebyscore(key, 0, cutoff)
                
                # Count recent events
                count = await self.redis_client.zcard(key)
                
                # Set expiration
                await self.redis_client.expire(key, window)
                
                return count >= rule.threshold_count
                
            except Exception as e:
                logger.error(f"Redis error checking rule conditions: {e}")
        
        return False
    
    async def _trigger_alert(self, rule: AlertRule, event: SecurityEvent):
        """Trigger security alert"""
        alert_id = f"{rule.rule_id}:{event.source_ip}:{int(time.time() // 300)}"  # 5-minute buckets
        
        # Avoid duplicate alerts
        if alert_id in self.active_alerts:
            return
        
        self.active_alerts[alert_id] = datetime.utcnow()
        
        alert_data = {
            "alert_id": alert_id,
            "rule_name": rule.name,
            "description": rule.description,
            "severity": rule.severity_threshold.value,
            "event": asdict(event),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log alert
        logger.warning(f"SECURITY ALERT: {rule.name} - {event.source_ip}")
        
        # Send notifications
        await self._send_notifications(alert_data)
        
        # Store alert for analysis
        if self.redis_client:
            try:
                await self.redis_client.lpush(
                    "security_alerts",
                    json.dumps(alert_data)
                )
                await self.redis_client.expire("security_alerts", 86400 * 7)  # 7 days
            except Exception as e:
                logger.error(f"Failed to store alert: {e}")
    
    async def _send_notifications(self, alert_data: Dict[str, Any]):
        """Send alert notifications"""
        # Email notification
        if self.smtp_config:
            await self._send_email_alert(alert_data)
        
        # Webhook notification
        if self.webhook_url:
            await self._send_webhook_alert(alert_data)
        
        # Custom handlers
        for handler in self.notification_handlers:
            try:
                await handler(alert_data)
            except Exception as e:
                logger.error(f"Error in custom alert handler: {e}")
    
    async def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Send email alert notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = self.smtp_config['to_email']
            msg['Subject'] = f"HIVE Security Alert: {alert_data['rule_name']}"
            
            body = f"""
Security Alert: {alert_data['rule_name']}

Description: {alert_data['description']}
Severity: {alert_data['severity']}
Time: {alert_data['timestamp']}

Event Details:
- Source IP: {alert_data['event']['source_ip']}
- Service: {alert_data['event']['service']}
- Endpoint: {alert_data['event']['endpoint']}
- Event Type: {alert_data['event']['event_type']}

Please investigate immediately.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email in thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_smtp_email, msg
            )
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_smtp_email(self, msg):
        """Send SMTP email (synchronous)"""
        with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
            if self.smtp_config.get('tls'):
                server.starttls()
            if self.smtp_config.get('username'):
                server.login(self.smtp_config['username'], self.smtp_config['password'])
            server.send_message(msg)
    
    async def _send_webhook_alert(self, alert_data: Dict[str, Any]):
        """Send webhook alert notification"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=alert_data,
                    timeout=10
                )
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")

class SecurityMonitor:
    """Main security monitoring system"""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        smtp_config: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
        metrics_port: int = 9100
    ):
        # Redis connection
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
        
        # Components
        self.metrics = SecurityMetrics()
        self.threat_detector = ThreatDetector(self.redis_client)
        self.alert_manager = AlertManager(self.redis_client, smtp_config, webhook_url)
        
        # Event storage
        self.event_log_file = "/var/log/hive/security.log"
        os.makedirs(os.path.dirname(self.event_log_file), exist_ok=True)
        
        # Start metrics server
        try:
            start_http_server(metrics_port)
            logger.info(f"Security metrics server started on port {metrics_port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    async def process_event(self, event: SecurityEvent):
        """Process a security event"""
        # Update metrics
        self.metrics.security_events_total.labels(
            event_type=event.event_type.value,
            severity=event.severity.value,
            service=event.service
        ).inc()
        
        # Specific metrics
        if event.event_type in [EventType.AUTHENTICATION_FAILURE, EventType.AUTHENTICATION_SUCCESS]:
            result = "success" if event.event_type == EventType.AUTHENTICATION_SUCCESS else "failure"
            self.metrics.auth_attempts_total.labels(service=event.service, result=result).inc()
            
            if result == "failure":
                self.metrics.auth_failures_by_ip.labels(
                    source_ip=event.source_ip,
                    service=event.service
                ).inc()
        
        if event.event_type == EventType.RATE_LIMIT_EXCEEDED:
            self.metrics.rate_limit_violations.labels(
                source_ip=event.source_ip,
                service=event.service,
                endpoint=event.endpoint
            ).inc()
        
        # Threat detection
        threats = await self.threat_detector.analyze_event(event)
        
        for threat in threats:
            self.metrics.threats_detected_total.labels(
                threat_type=threat,
                severity=event.severity.value
            ).inc()
            
            # Update IP reputation
            self.threat_detector.update_ip_reputation(event.source_ip, -0.1)
        
        # Alert processing
        await self.alert_manager.process_event(event)
        
        # Log event
        await self._log_event(event)
    
    async def _log_event(self, event: SecurityEvent):
        """Log security event to file"""
        try:
            event_data = asdict(event)
            # Convert datetime and enum objects
            event_data['timestamp'] = event.timestamp.isoformat()
            event_data['event_type'] = event.event_type.value
            event_data['severity'] = event.severity.value
            
            log_entry = json.dumps(event_data) + "\n"
            
            async with aiofiles.open(self.event_log_file, 'a') as f:
                await f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def get_security_dashboard_data(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        # This would typically query stored metrics and events
        # For now, return current state
        return {
            "active_threats": len(self.threat_detector.known_bad_ips),
            "blocked_ips": list(self.threat_detector.known_bad_ips),
            "ip_reputation_scores": dict(list(self.threat_detector.ip_reputation.items())[:10]),
            "alert_rules": len(self.alert_manager.alert_rules),
            "active_alerts": len(self.alert_manager.active_alerts),
            "timestamp": datetime.utcnow().isoformat()
        }

# Factory function for easy integration
def create_security_monitor(
    redis_url: Optional[str] = None,
    smtp_config: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None
) -> SecurityMonitor:
    """Create security monitor with configuration"""
    return SecurityMonitor(
        redis_url=redis_url or os.getenv("REDIS_URL"),
        smtp_config=smtp_config,
        webhook_url=webhook_url or os.getenv("SECURITY_WEBHOOK_URL")
    )

# Integration helper for FastAPI services
def create_security_event(
    event_type: EventType,
    severity: AlertSeverity,
    request,
    service: str,
    details: Optional[Dict[str, Any]] = None
) -> SecurityEvent:
    """Create security event from FastAPI request"""
    return SecurityEvent(
        event_id="",  # Will be generated
        event_type=event_type,
        severity=severity,
        timestamp=datetime.utcnow(),
        source_ip=request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or 
                 request.headers.get('X-Real-IP', '') or 
                 str(request.client.host),
        user_agent=request.headers.get('User-Agent', 'Unknown'),
        service=service,
        endpoint=request.url.path,
        user_id=getattr(request.state, 'user_id', None),
        session_id=getattr(request.state, 'session_id', None),
        details=details
    )

if __name__ == "__main__":
    # CLI for testing security monitoring
    import argparse
    
    async def test_monitoring():
        monitor = create_security_monitor()
        
        # Create test events
        test_events = [
            SecurityEvent(
                event_id="",
                event_type=EventType.AUTHENTICATION_FAILURE,
                severity=AlertSeverity.MEDIUM,
                timestamp=datetime.utcnow(),
                source_ip="192.168.1.100",
                user_agent="Test-Agent",
                service="auth-service",
                endpoint="/token",
                details={"reason": "invalid_credentials"}
            ),
            SecurityEvent(
                event_id="",
                event_type=EventType.RATE_LIMIT_EXCEEDED,
                severity=AlertSeverity.HIGH,
                timestamp=datetime.utcnow(),
                source_ip="192.168.1.100",
                user_agent="Test-Agent",
                service="stt-service",
                endpoint="/transcribe",
                details={"requests_per_minute": 150}
            )
        ]
        
        # Process events
        for event in test_events:
            await monitor.process_event(event)
            print(f"Processed event: {event.event_type.value}")
        
        # Display dashboard data
        dashboard = monitor.get_security_dashboard_data()
        print("\nSecurity Dashboard:")
        for key, value in dashboard.items():
            print(f"  {key}: {value}")
    
    parser = argparse.ArgumentParser(description="Security Monitor Test")
    parser.add_argument("--test", action="store_true", help="Run test monitoring")
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_monitoring())
    else:
        print("Use --test to run test monitoring")