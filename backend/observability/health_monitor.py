"""
Comprehensive Health Monitoring System for The HIVE Translation Services
Provides health check endpoints, dependency monitoring, and service status tracking
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
import psutil
import redis
import socket
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .metrics import TranslationMetrics, get_metrics

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceHealth:
    """Health information for a service"""
    service_name: str
    status: HealthStatus
    response_time_ms: float
    last_check: datetime
    details: Dict[str, Any]
    dependencies: List[str]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'status': self.status.value,
            'last_check': self.last_check.isoformat()
        }

class HealthChecker:
    """Performs health checks for individual services"""
    
    def __init__(self, service_configs: Dict[str, Dict[str, Any]]):
        self.service_configs = service_configs
        self.metrics = get_metrics("health-monitor")
        
    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """Check health of a specific service"""
        config = self.service_configs.get(service_name)
        if not config:
            return ServiceHealth(
                service_name=service_name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                last_check=datetime.utcnow(),
                details={},
                dependencies=[],
                error_message=f"Service {service_name} not configured"
            )
        
        start_time = time.time()
        
        try:
            # Perform HTTP health check
            health_data = await self._http_health_check(
                config['url'],
                config.get('health_endpoint', '/health'),
                config.get('timeout', 5)
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Determine status based on response
            status = self._determine_health_status(health_data, response_time_ms, config)
            
            # Record metrics
            self.metrics.update_service_health(status == HealthStatus.HEALTHY)
            self.metrics.record_http_request(
                method="GET",
                endpoint=config.get('health_endpoint', '/health'),
                status_code=200,
                duration_seconds=response_time_ms / 1000
            )
            
            return ServiceHealth(
                service_name=service_name,
                status=status,
                response_time_ms=response_time_ms,
                last_check=datetime.utcnow(),
                details=health_data,
                dependencies=config.get('dependencies', [])
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            # Record failure metrics
            self.metrics.update_service_health(False)
            self.metrics.record_http_request(
                method="GET", 
                endpoint=config.get('health_endpoint', '/health'),
                status_code=500,
                duration_seconds=response_time_ms / 1000
            )
            
            return ServiceHealth(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                last_check=datetime.utcnow(),
                details={},
                dependencies=config.get('dependencies', []),
                error_message=str(e)
            )
    
    async def _http_health_check(self, base_url: str, endpoint: str, timeout: int) -> Dict[str, Any]:
        """Perform HTTP health check"""
        url = f"{base_url.rstrip('/')}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
    
    def _determine_health_status(self, health_data: Dict[str, Any], response_time_ms: float, config: Dict[str, Any]) -> HealthStatus:
        """Determine health status based on response data and thresholds"""
        
        # Check response time threshold
        max_response_time = config.get('max_response_time_ms', 1000)
        if response_time_ms > max_response_time:
            return HealthStatus.DEGRADED
        
        # Check specific health indicators from response
        if 'status' in health_data:
            status_value = health_data['status'].lower()
            if status_value in ['healthy', 'ok', 'up']:
                return HealthStatus.HEALTHY
            elif status_value in ['degraded', 'warning']:
                return HealthStatus.DEGRADED
            elif status_value in ['unhealthy', 'down', 'error']:
                return HealthStatus.UNHEALTHY
        
        # Check resource utilization if available
        if 'resources' in health_data:
            resources = health_data['resources']
            
            cpu_usage = resources.get('cpu_percent', 0)
            memory_usage = resources.get('memory_percent', 0)
            
            if cpu_usage > 90 or memory_usage > 95:
                return HealthStatus.DEGRADED
        
        # Default to healthy if no issues found
        return HealthStatus.HEALTHY

class SystemHealthMonitor:
    """Monitors overall system health and dependencies"""
    
    def __init__(self):
        self.service_configs = {
            'stt-service': {
                'url': 'http://localhost:8001',
                'health_endpoint': '/health',
                'timeout': 5,
                'max_response_time_ms': 500,
                'dependencies': ['redis', 'gpu']
            },
            'mt-service': {
                'url': 'http://localhost:8002', 
                'health_endpoint': '/health',
                'timeout': 5,
                'max_response_time_ms': 300,
                'dependencies': ['redis']
            },
            'tts-service': {
                'url': 'http://localhost:8003',
                'health_endpoint': '/health', 
                'timeout': 10,
                'max_response_time_ms': 1000,
                'dependencies': ['redis', 'gpu']
            },
            'livekit': {
                'url': 'http://localhost:7880',
                'health_endpoint': '/health',
                'timeout': 3,
                'max_response_time_ms': 200,
                'dependencies': ['redis']
            }
        }
        
        self.health_checker = HealthChecker(self.service_configs)
        self.metrics = get_metrics("system-health-monitor")
        self.health_history: Dict[str, List[ServiceHealth]] = {}
        
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        
        # Check all services concurrently
        service_checks = [
            self.health_checker.check_service_health(service_name)
            for service_name in self.service_configs.keys()
        ]
        
        service_health_results = await asyncio.gather(*service_checks, return_exceptions=True)
        
        # Process results
        service_health = {}
        overall_status = HealthStatus.HEALTHY
        
        for i, result in enumerate(service_health_results):
            service_name = list(self.service_configs.keys())[i]
            
            if isinstance(result, Exception):
                health = ServiceHealth(
                    service_name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    last_check=datetime.utcnow(),
                    details={},
                    dependencies=[],
                    error_message=str(result)
                )
            else:
                health = result
            
            service_health[service_name] = health
            
            # Store in history
            if service_name not in self.health_history:
                self.health_history[service_name] = []
            self.health_history[service_name].append(health)
            
            # Keep only recent history
            if len(self.health_history[service_name]) > 100:
                self.health_history[service_name] = self.health_history[service_name][-50:]
            
            # Update overall status
            if health.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        # Check infrastructure dependencies
        infrastructure_health = await self._check_infrastructure_health()
        
        # Calculate system metrics
        system_metrics = await self._get_system_metrics()
        
        # Determine final system health
        if infrastructure_health['redis']['status'] != HealthStatus.HEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'services': {name: health.to_dict() for name, health in service_health.items()},
            'infrastructure': infrastructure_health,
            'system_metrics': system_metrics,
            'slo_status': await self._get_slo_status()
        }
    
    async def _check_infrastructure_health(self) -> Dict[str, Any]:
        """Check infrastructure component health"""
        
        # Check Redis
        redis_health = await self._check_redis_health()
        
        # Check GPU availability (if configured)
        gpu_health = self._check_gpu_health()
        
        # Check disk space
        disk_health = self._check_disk_health()
        
        # Check network connectivity
        network_health = await self._check_network_health()
        
        return {
            'redis': redis_health,
            'gpu': gpu_health,
            'disk': disk_health,
            'network': network_health
        }
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            
            start_time = time.time()
            ping_result = r.ping()
            response_time = (time.time() - start_time) * 1000
            
            if ping_result:
                info = r.info()
                
                return {
                    'status': HealthStatus.HEALTHY.value,
                    'response_time_ms': response_time,
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory_human', 'unknown'),
                    'uptime_seconds': info.get('uptime_in_seconds', 0)
                }
            else:
                return {
                    'status': HealthStatus.UNHEALTHY.value,
                    'error': 'Ping failed'
                }
                
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY.value,
                'error': str(e)
            }
    
    def _check_gpu_health(self) -> Dict[str, Any]:
        """Check GPU availability and utilization"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            if not gpus:
                return {
                    'status': HealthStatus.UNKNOWN.value,
                    'message': 'No GPUs detected'
                }
            
            gpu_info = []
            overall_healthy = True
            
            for gpu in gpus:
                gpu_healthy = gpu.load < 0.95 and gpu.memoryUtil < 0.9
                if not gpu_healthy:
                    overall_healthy = False
                
                gpu_info.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'load': gpu.load,
                    'memory_util': gpu.memoryUtil,
                    'temperature': gpu.temperature,
                    'healthy': gpu_healthy
                })
            
            return {
                'status': HealthStatus.HEALTHY.value if overall_healthy else HealthStatus.DEGRADED.value,
                'gpus': gpu_info
            }
            
        except ImportError:
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': 'GPUtil not available'
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY.value,
                'error': str(e)
            }
    
    def _check_disk_health(self) -> Dict[str, Any]:
        """Check disk space availability"""
        try:
            disk_usage = psutil.disk_usage('/')
            available_percent = (disk_usage.free / disk_usage.total) * 100
            
            if available_percent < 10:
                status = HealthStatus.UNHEALTHY
            elif available_percent < 20:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return {
                'status': status.value,
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'available_percent': round(available_percent, 1)
            }
            
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY.value,
                'error': str(e)
            }
    
    async def _check_network_health(self) -> Dict[str, Any]:
        """Check network connectivity to key endpoints"""
        endpoints_to_check = [
            ('localhost', 6379, 'redis'),
            ('localhost', 7880, 'livekit'),
            ('localhost', 9090, 'prometheus')
        ]
        
        connectivity_results = []
        overall_healthy = True
        
        for host, port, service in endpoints_to_check:
            try:
                start_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                
                response_time = (time.time() - start_time) * 1000
                is_reachable = result == 0
                
                if not is_reachable:
                    overall_healthy = False
                
                connectivity_results.append({
                    'service': service,
                    'host': host,
                    'port': port,
                    'reachable': is_reachable,
                    'response_time_ms': response_time if is_reachable else None
                })
                
            except Exception as e:
                overall_healthy = False
                connectivity_results.append({
                    'service': service,
                    'host': host,
                    'port': port,
                    'reachable': False,
                    'error': str(e)
                })
        
        return {
            'status': HealthStatus.HEALTHY.value if overall_healthy else HealthStatus.DEGRADED.value,
            'connectivity': connectivity_results
        }
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'boot_time': psutil.boot_time(),
                'process_count': len(psutil.pids())
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
    
    async def _get_slo_status(self) -> Dict[str, Any]:
        """Get current SLO compliance status"""
        # This would typically query Prometheus for current SLO metrics
        # For now, we'll return a placeholder structure
        
        return {
            'ttft_slo_compliance': True,  # p95 TTFT ≤ 450ms
            'caption_latency_slo_compliance': True,  # p95 ≤ 250ms
            'retraction_rate_slo_compliance': True,  # < 5%
            'last_slo_breach': None,
            'slo_breach_count_24h': 0
        }

# FastAPI health endpoints
app = FastAPI(title="The HIVE Health Monitor", version="1.0.0")
health_monitor = SystemHealthMonitor()

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with all services and dependencies"""
    try:
        system_health = await health_monitor.get_system_health()
        
        status_code = 200
        if system_health['overall_status'] == HealthStatus.UNHEALTHY.value:
            status_code = 503
        elif system_health['overall_status'] == HealthStatus.DEGRADED.value:
            status_code = 200  # Return 200 but with degraded status in response
            
        return JSONResponse(content=system_health, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "overall_status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )

@app.get("/health/service/{service_name}")
async def service_health_check(service_name: str):
    """Health check for a specific service"""
    try:
        service_health = await health_monitor.health_checker.check_service_health(service_name)
        
        status_code = 200
        if service_health.status == HealthStatus.UNHEALTHY:
            status_code = 503
            
        return JSONResponse(content=service_health.to_dict(), status_code=status_code)
        
    except Exception as e:
        logger.error(f"Service health check failed for {service_name}: {e}")
        return JSONResponse(
            content={
                "service_name": service_name,
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )

@app.get("/metrics/health")
async def health_metrics():
    """Prometheus-compatible health metrics"""
    metrics = health_monitor.metrics.export_metrics()
    return Response(content=metrics, media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)