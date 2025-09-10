"""
Comprehensive Security Monitoring System for The HIVE Translation Services

Real-time security monitoring, threat detection, and audit logging for all
security-related events across the translation infrastructure.
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import redis
from pathlib import Path
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Security alert levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class SecurityAlert:
    """Security alert data structure"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    source_service: str
    affected_resources: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

class SecurityMetrics:
    """Security metrics collector and analyzer"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    def record_event(self, event_type: str, service_name: str, metadata: Dict[str, Any] = None):
        """Record a security event"""
        timestamp = time.time()
        event_key = f"security_events:{event_type}:{service_name}"
        
        # Store event with timestamp
        event_data = {
            "timestamp": timestamp,
            "service": service_name,
            "metadata": json.dumps(metadata or {})
        }
        
        # Add to sorted set for time-based queries
        self.redis.zadd(event_key, {json.dumps(event_data): timestamp})
        
        # Set expiration for automatic cleanup (30 days)
        self.redis.expire(event_key, 30 * 24 * 3600)
        
        # Update counters
        self._update_counters(event_type, service_name, timestamp)
    
    def _update_counters(self, event_type: str, service_name: str, timestamp: float):
        """Update various counters for metrics"""
        now = datetime.fromtimestamp(timestamp)
        
        # Hourly counters
        hour_key = f"security_metrics:hourly:{event_type}:{now.strftime('%Y%m%d%H')}"
        self.redis.incr(hour_key)
        self.redis.expire(hour_key, 7 * 24 * 3600)  # Keep for 7 days
        
        # Daily counters
        day_key = f"security_metrics:daily:{event_type}:{now.strftime('%Y%m%d')}"
        self.redis.incr(day_key)
        self.redis.expire(day_key, 30 * 24 * 3600)  # Keep for 30 days
        
        # Service-specific counters
        service_key = f"security_metrics:service:{service_name}:{event_type}"
        self.redis.incr(service_key)
        self.redis.expire(service_key, 30 * 24 * 3600)
    
    def get_metrics(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get security metrics for specified time range"""
        if time_range == "1h":
            return self._get_hourly_metrics(1)
        elif time_range == "24h":
            return self._get_hourly_metrics(24)
        elif time_range == "7d":
            return self._get_daily_metrics(7)
        elif time_range == "30d":
            return self._get_daily_metrics(30)
        else:
            raise ValueError(f"Unsupported time range: {time_range}")
    
    def _get_hourly_metrics(self, hours: int) -> Dict[str, Any]:
        """Get hourly metrics"""
        now = datetime.utcnow()
        metrics = {"timeframe": f"{hours}h", "data": {}}
        
        for hour_offset in range(hours):
            hour = now - timedelta(hours=hour_offset)
            hour_str = hour.strftime('%Y%m%d%H')
            
            # Get all event types for this hour
            pattern = f"security_metrics:hourly:*:{hour_str}"
            keys = self.redis.keys(pattern)
            
            hour_data = {}
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                event_type = key_str.split(':')[2]  # Extract event type
                count = self.redis.get(key)
                hour_data[event_type] = int(count) if count else 0
            
            metrics["data"][hour.strftime('%Y-%m-%d %H:00')] = hour_data
        
        return metrics
    
    def _get_daily_metrics(self, days: int) -> Dict[str, Any]:
        """Get daily metrics"""
        now = datetime.utcnow()
        metrics = {"timeframe": f"{days}d", "data": {}}
        
        for day_offset in range(days):
            day = now - timedelta(days=day_offset)
            day_str = day.strftime('%Y%m%d')
            
            # Get all event types for this day
            pattern = f"security_metrics:daily:*:{day_str}"
            keys = self.redis.keys(pattern)
            
            day_data = {}
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                event_type = key_str.split(':')[2]  # Extract event type
                count = self.redis.get(key)
                day_data[event_type] = int(count) if count else 0
            
            metrics["data"][day.strftime('%Y-%m-%d')] = day_data
        
        return metrics

class SecurityAuditor:
    """Security audit log manager"""
    
    def __init__(self, log_directory: str = "/var/log/hive/security"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Setup structured logging for audit events
        self.audit_logger = logging.getLogger("security_audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.audit_logger.handlers:
            # File handler for audit logs
            audit_file = self.log_directory / "security_audit.log"
            file_handler = logging.FileHandler(audit_file)
            file_handler.setLevel(logging.INFO)
            
            # JSON formatter for structured logs
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"message": "%(message)s", "extras": %(extras)s}'
            )
            file_handler.setFormatter(formatter)
            self.audit_logger.addHandler(file_handler)
    
    def log_authentication_event(
        self,
        event_type: str,
        user_id: str,
        client_ip: str,
        user_agent: str,
        success: bool,
        metadata: Dict[str, Any] = None
    ):
        """Log authentication-related events"""
        event_data = {
            "event_category": "authentication",
            "event_type": event_type,
            "user_id": user_id,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "success": success,
            "metadata": metadata or {}
        }
        
        self._log_audit_event(event_data)
    
    def log_authorization_event(
        self,
        event_type: str,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        reason: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log authorization-related events"""
        event_data = {
            "event_category": "authorization",
            "event_type": event_type,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "allowed": allowed,
            "reason": reason,
            "metadata": metadata or {}
        }
        
        self._log_audit_event(event_data)
    
    def log_security_incident(
        self,
        incident_type: str,
        severity: str,
        source_ip: str,
        target_resource: str,
        description: str,
        metadata: Dict[str, Any] = None
    ):
        """Log security incidents"""
        event_data = {
            "event_category": "security_incident",
            "incident_type": incident_type,
            "severity": severity,
            "source_ip": source_ip,
            "target_resource": target_resource,
            "description": description,
            "metadata": metadata or {}
        }
        
        self._log_audit_event(event_data)
    
    def _log_audit_event(self, event_data: Dict[str, Any]):
        """Log structured audit event"""
        # Add common fields
        event_data.update({
            "event_id": hashlib.sha256(f"{time.time()}{json.dumps(event_data, sort_keys=True)}".encode()).hexdigest()[:16],
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        })
        
        # Log the event
        self.audit_logger.info(
            f"Security audit event: {event_data.get('event_type', 'unknown')}",
            extra={"extras": json.dumps(event_data)}
        )

class SecurityAlertManager:
    """Security alert management system"""
    
    def __init__(self, redis_client: redis.Redis, config: Dict[str, Any] = None):
        self.redis = redis_client
        self.config = config or {}
        self.alert_handlers: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.INFO: [],
            AlertLevel.WARNING: [],
            AlertLevel.CRITICAL: [],
            AlertLevel.EMERGENCY: []
        }
        
        # Setup default handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default alert handlers"""
        # Log all alerts
        for level in AlertLevel:
            self.register_handler(level, self._log_alert)
        
        # Email critical and emergency alerts
        if self.config.get("email_enabled"):
            self.register_handler(AlertLevel.CRITICAL, self._email_alert)
            self.register_handler(AlertLevel.EMERGENCY, self._email_alert)
    
    def register_handler(self, level: AlertLevel, handler: Callable):
        """Register an alert handler for a specific level"""
        self.alert_handlers[level].append(handler)
    
    def create_alert(
        self,
        level: AlertLevel,
        title: str,
        description: str,
        source_service: str,
        affected_resources: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> SecurityAlert:
        """Create and process a security alert"""
        alert = SecurityAlert(
            alert_id=hashlib.sha256(f"{time.time()}{title}{source_service}".encode()).hexdigest()[:16],
            level=level,
            title=title,
            description=description,
            source_service=source_service,
            affected_resources=affected_resources or [],
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store alert in Redis
        self._store_alert(alert)
        
        # Process alert through handlers
        self._process_alert(alert)
        
        return alert
    
    def _store_alert(self, alert: SecurityAlert):
        """Store alert in Redis"""
        alert_key = f"security_alerts:{alert.alert_id}"
        alert_data = asdict(alert)
        
        # Convert datetime objects to strings
        alert_data["timestamp"] = alert.timestamp.isoformat()
        if alert.resolved_at:
            alert_data["resolved_at"] = alert.resolved_at.isoformat()
        
        # Convert AlertLevel enum
        alert_data["level"] = alert.level.value
        
        # Store alert data
        self.redis.hset(alert_key, mapping={
            key: json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            for key, value in alert_data.items()
        })
        
        # Add to alerts index sorted by timestamp
        self.redis.zadd("security_alerts_index", {alert.alert_id: alert.timestamp.timestamp()})
        
        # Set expiration (30 days)
        self.redis.expire(alert_key, 30 * 24 * 3600)
    
    def _process_alert(self, alert: SecurityAlert):
        """Process alert through registered handlers"""
        handlers = self.alert_handlers.get(alert.level, [])
        
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
    
    def _log_alert(self, alert: SecurityAlert):
        """Default log handler"""
        logger.error(f"SECURITY ALERT [{alert.level.value.upper()}]: {alert.title}")
        logger.error(f"Description: {alert.description}")
        logger.error(f"Source: {alert.source_service}")
        if alert.affected_resources:
            logger.error(f"Affected resources: {', '.join(alert.affected_resources)}")
    
    def _email_alert(self, alert: SecurityAlert):
        """Email alert handler"""
        email_config = self.config.get("email", {})
        
        if not email_config.get("enabled"):
            return
        
        try:
            # Create email
            msg = MIMEMultipart()
            msg['From'] = email_config.get("from_address")
            msg['To'] = ", ".join(email_config.get("to_addresses", []))
            msg['Subject'] = f"[SECURITY ALERT] {alert.title}"
            
            # Email body
            body = f"""
Security Alert Details:
======================

Level: {alert.level.value.upper()}
Title: {alert.title}
Description: {alert.description}
Source Service: {alert.source_service}
Timestamp: {alert.timestamp}
Alert ID: {alert.alert_id}

Affected Resources:
{chr(10).join(f"- {resource}" for resource in alert.affected_resources)}

Metadata:
{json.dumps(alert.metadata, indent=2)}

This is an automated security alert from The HIVE Translation Services.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(email_config.get("smtp_host"), email_config.get("smtp_port", 587))
            server.starttls()
            server.login(email_config.get("username"), email_config.get("password"))
            
            text = msg.as_string()
            server.sendmail(email_config.get("from_address"), email_config.get("to_addresses"), text)
            server.quit()
            
            logger.info(f"Security alert email sent: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send security alert email: {e}")
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        resolved: Optional[bool] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SecurityAlert]:
        """Get alerts with optional filtering"""
        # Get alert IDs from index
        if since:
            min_score = since.timestamp()
            alert_ids = self.redis.zrangebyscore("security_alerts_index", min_score, "+inf", start=0, num=limit)
        else:
            alert_ids = self.redis.zrevrange("security_alerts_index", 0, limit - 1)
        
        alerts = []
        for alert_id in alert_ids:
            alert_id = alert_id.decode() if isinstance(alert_id, bytes) else alert_id
            alert_data = self.redis.hgetall(f"security_alerts:{alert_id}")
            
            if not alert_data:
                continue
            
            # Decode alert data
            decoded_data = {}
            for key, value in alert_data.items():
                key = key.decode() if isinstance(key, bytes) else key
                value = value.decode() if isinstance(value, bytes) else value
                
                if key in ["metadata", "affected_resources"]:
                    try:
                        decoded_data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        decoded_data[key] = value
                elif key == "resolved":
                    decoded_data[key] = value.lower() == "true"
                elif key == "level":
                    try:
                        decoded_data[key] = AlertLevel(value)
                    except ValueError:
                        decoded_data[key] = AlertLevel.INFO
                elif key in ["timestamp", "resolved_at"]:
                    try:
                        decoded_data[key] = datetime.fromisoformat(value) if value and value != "None" else None
                    except ValueError:
                        decoded_data[key] = None
                else:
                    decoded_data[key] = value
            
            # Create SecurityAlert object
            try:
                alert = SecurityAlert(**decoded_data)
            except TypeError as e:
                logger.error(f"Failed to create SecurityAlert from data: {e}")
                continue
            
            # Apply filters
            if level and alert.level != level:
                continue
            if resolved is not None and alert.resolved != resolved:
                continue
            
            alerts.append(alert)
        
        return alerts

class SecurityMonitor:
    """Main security monitoring orchestrator"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        config: Dict[str, Any] = None
    ):
        self.config = config or {}
        
        # Setup Redis connection
        try:
            self.redis = redis.from_url(redis_url, decode_responses=False)
            self.redis.ping()
            logger.info("Connected to Redis for security monitoring")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        
        # Initialize components
        self.metrics = SecurityMetrics(self.redis)
        self.auditor = SecurityAuditor()
        self.alert_manager = SecurityAlertManager(self.redis, config)
        
        # Monitoring state
        self.running = False
        self.monitoring_tasks = []
    
    async def start_monitoring(self):
        """Start security monitoring tasks"""
        if self.running:
            logger.warning("Security monitoring already running")
            return
        
        self.running = True
        logger.info("Starting security monitoring...")
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._monitor_failed_logins()),
            asyncio.create_task(self._monitor_rate_limit_violations()),
            asyncio.create_task(self._monitor_certificate_expiry()),
            asyncio.create_task(self._cleanup_old_data())
        ]
        
        # Wait for tasks
        try:
            await asyncio.gather(*self.monitoring_tasks)
        except asyncio.CancelledError:
            logger.info("Security monitoring cancelled")
        except Exception as e:
            logger.error(f"Security monitoring error: {e}")
    
    async def stop_monitoring(self):
        """Stop security monitoring tasks"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping security monitoring...")
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.monitoring_tasks = []
    
    async def _monitor_failed_logins(self):
        """Monitor for suspicious login patterns"""
        while self.running:
            try:
                # Check for failed login patterns in the last hour
                now = time.time()
                hour_ago = now - 3600
                
                # Get failed login events
                pattern = "security_events:authentication_failed:*"
                keys = self.redis.keys(pattern)
                
                failed_logins_by_ip = {}
                for key in keys:
                    events = self.redis.zrangebyscore(key, hour_ago, now)
                    for event_data in events:
                        try:
                            event = json.loads(event_data)
                            client_ip = json.loads(event["metadata"]).get("client_ip")
                            if client_ip:
                                failed_logins_by_ip[client_ip] = failed_logins_by_ip.get(client_ip, 0) + 1
                        except (json.JSONDecodeError, KeyError):
                            continue
                
                # Check for brute force attempts
                for ip, count in failed_logins_by_ip.items():
                    if count >= 10:  # 10 failed logins in an hour
                        self.alert_manager.create_alert(
                            level=AlertLevel.WARNING,
                            title="Potential Brute Force Attack",
                            description=f"IP {ip} has {count} failed login attempts in the last hour",
                            source_service="security_monitor",
                            affected_resources=[f"ip:{ip}"],
                            metadata={"ip": ip, "failed_count": count, "time_window": "1h"}
                        )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Failed login monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_rate_limit_violations(self):
        """Monitor for rate limit violations"""
        while self.running:
            try:
                # Check for rate limit violations and create alerts
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Rate limit monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_certificate_expiry(self):
        """Monitor certificate expiry"""
        while self.running:
            try:
                # Check certificate expiry status
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Certificate monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        while self.running:
            try:
                # Cleanup old security events and metrics
                cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days ago
                
                # Clean up old security events
                pattern = "security_events:*"
                keys = self.redis.keys(pattern)
                
                for key in keys:
                    self.redis.zremrangebyscore(key, 0, cutoff_time)
                
                logger.info("Cleaned up old security monitoring data")
                await asyncio.sleep(24 * 3600)  # Run daily
                
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(3600)
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {},
            "alerts": {},
            "system_status": {}
        }
        
        try:
            # Get recent metrics
            dashboard["metrics"]["last_24h"] = self.metrics.get_metrics("24h")
            dashboard["metrics"]["last_7d"] = self.metrics.get_metrics("7d")
            
            # Get recent alerts
            dashboard["alerts"]["unresolved"] = len(self.alert_manager.get_alerts(resolved=False))
            dashboard["alerts"]["critical"] = len(self.alert_manager.get_alerts(level=AlertLevel.CRITICAL, resolved=False))
            dashboard["alerts"]["recent"] = [
                {**asdict(alert), "level": alert.level.value, 
                 "timestamp": alert.timestamp.isoformat(),
                 "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None}
                for alert in self.alert_manager.get_alerts(limit=10)
            ]
            
            # System status
            dashboard["system_status"]["monitoring_active"] = self.running
            dashboard["system_status"]["redis_connected"] = True  # We got this far
            
        except Exception as e:
            logger.error(f"Dashboard generation error: {e}")
            dashboard["error"] = str(e)
        
        return dashboard

# Factory function
def create_security_monitor(redis_url: str = "redis://localhost:6379", config: Dict[str, Any] = None) -> SecurityMonitor:
    """Create security monitor with default configuration"""
    return SecurityMonitor(redis_url, config)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Monitor for The HIVE")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="Redis connection URL")
    parser.add_argument("--config-file", help="Configuration file path")
    parser.add_argument("--dashboard", action="store_true", help="Show security dashboard")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config_file and os.path.exists(args.config_file):
        with open(args.config_file) as f:
            config = json.load(f)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    try:
        monitor = create_security_monitor(args.redis_url, config)
        
        if args.dashboard:
            dashboard = monitor.get_security_dashboard()
            print(json.dumps(dashboard, indent=2, default=str))
        else:
            # Start monitoring
            asyncio.run(monitor.start_monitoring())
    
    except KeyboardInterrupt:
        print("\nSecurity monitoring stopped")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)