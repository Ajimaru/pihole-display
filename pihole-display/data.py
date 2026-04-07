"""Fetch and cache Pi-hole, Unbound, and system telemetry for the UI."""

# ============================================================
# data.py — Data retrieval: Pi-hole, Unbound, System
# ============================================================

import subprocess
import time
import logging
import socket
import re
from dataclasses import dataclass
from typing import Optional

import requests
import psutil

import config

log = logging.getLogger(__name__)


# ── Pi-hole ──────────────────────────────────────────────────

@dataclass
class PiholeStats:  # pylint: disable=too-many-instance-attributes
    """Container for Pi-hole state and aggregated statistics."""

    enabled: bool = False
    blocked_today: int = 0
    queries_today: int = 0
    block_percent: float = 0.0
    clients: int = 0
    domains_blocked: int = 0
    pause_remaining: int = 0  # Remaining seconds while paused
    version: int = 5  # API version (5 or 6)
    error: str = ''


class PiholeAPI:
    """Supports Pi-hole v5 and v6."""

    def __init__(self):
        self._session_token = None  # for v6
        self._api_token = None  # for v5
        self._version = None
        self._base_v5 = f'http://{config.PIHOLE_HOST}/admin/api.php'
        self._base_v6 = f'http://{config.PIHOLE_HOST}/api'

    def _detect_version(self) -> int:
        try:
            r = requests.get(f'{self._base_v6}/stats/summary', timeout=3)
            if r.status_code in (200, 401):
                return 6
        except requests.RequestException:
            pass
        return 5

    def _load_v5_token(self) -> Optional[str]:
        try:
            with open(config.PIHOLE_SETUPVARS, encoding='utf-8') as f:
                for line in f:
                    if line.startswith('WEBPASSWORD='):
                        return line.strip().split('=', 1)[1]
        except OSError:
            pass
        return None

    def _ensure_v6_auth(self):
        if self._session_token:
            return True
        if not config.PIHOLE_PASSWORD:
            return False
        try:
            r = requests.post(
                f'{self._base_v6}/auth',
                json={'password': config.PIHOLE_PASSWORD},
                timeout=3
            )
            data = r.json()
            self._session_token = data.get('session', {}).get('sid')
            return bool(self._session_token)
        except (requests.RequestException, ValueError, TypeError) as e:
            log.warning('Pi-hole v6 auth failed: %s', e)
            return False

    def _headers_v6(self) -> dict:
        if self._session_token:
            return {'X-FTL-SID': self._session_token}
        return {}

    def fetch(self) -> PiholeStats:
        """Return current Pi-hole stats using the detected API version."""
        stats = PiholeStats()
        if self._version is None:
            self._version = self._detect_version()
            stats.version = self._version
            log.info('Pi-hole API version: %d', self._version)

        try:
            if self._version == 6:
                return self._fetch_v6(stats)
            return self._fetch_v5(stats)
        except (
            requests.RequestException,
            ValueError,
            TypeError,
            OSError,
        ) as e:
            stats.error = str(e)
            log.error('Pi-hole error: %s', e)
            return stats

    def _fetch_v5(self, stats: PiholeStats) -> PiholeStats:
        if not self._api_token:
            self._api_token = self._load_v5_token()
        r = requests.get(f'{self._base_v5}?summary', timeout=5)
        d = r.json()
        stats.version = 5
        stats.enabled = d.get('status', '') == 'enabled'
        stats.blocked_today = int(d.get('ads_blocked_today', 0))
        stats.queries_today = int(d.get('dns_queries_today', 0))
        stats.block_percent = float(d.get('ads_percentage_today', 0.0))
        stats.clients = int(d.get('unique_clients', 0))
        stats.domains_blocked = int(d.get('domains_being_blocked', 0))
        return stats

    def _fetch_v6(self, stats: PiholeStats) -> PiholeStats:
        self._ensure_v6_auth()
        headers = self._headers_v6()

        r = requests.get(
            f'{self._base_v6}/stats/summary',
            headers=headers,
            timeout=5,
        )
        d = r.json()
        queries = d.get('queries', {})
        stats.version = 6
        stats.blocked_today = queries.get('blocked', 0)
        stats.queries_today = queries.get('total', 0)
        stats.block_percent = queries.get('percent_blocked', 0.0)
        stats.clients = d.get('clients', {}).get('active', 0)
        stats.domains_blocked = d.get('gravity', {}).get(
            'domains_being_blocked',
            0,
        )

        rb = requests.get(
            f'{self._base_v6}/dns/blocking',
            headers=headers,
            timeout=5,
        )
        db = rb.json()
        stats.enabled = db.get('blocking', False)
        stats.pause_remaining = db.get('timer', 0) or 0
        return stats

    def set_blocking(self, enable: bool, seconds: int = 0) -> bool:
        """Enable or disable Pi-hole blocking, optionally with a timer."""
        if self._version is None:
            self._version = self._detect_version()
        try:
            if self._version == 6:
                return self._set_blocking_v6(enable, seconds)
            return self._set_blocking_v5(enable, seconds)
        except (
            requests.RequestException,
            ValueError,
            TypeError,
            OSError,
        ) as e:
            log.error('Failed to set Pi-hole blocking: %s', e)
            return False

    def _set_blocking_v5(self, enable: bool, seconds: int) -> bool:
        if not self._api_token:
            self._api_token = self._load_v5_token()
        if not self._api_token:
            log.warning(
                'No Pi-hole API token - enable/disable not possible',
            )
            return False
        if enable:
            url = f'{self._base_v5}?enable&auth={self._api_token}'
        else:
            url = f'{self._base_v5}?disable={seconds}&auth={self._api_token}'
        r = requests.get(url, timeout=5)
        return r.status_code == 200

    def _set_blocking_v6(self, enable: bool, seconds: int) -> bool:
        self._ensure_v6_auth()
        payload: dict[str, object] = {'blocking': enable}
        if not enable and seconds:
            payload['timer'] = seconds
        r = requests.post(
            f'{self._base_v6}/dns/blocking',
            headers=self._headers_v6(),
            json=payload,
            timeout=5
        )
        return r.status_code == 200

    def flush_cache(self) -> bool:
        """Trigger a Pi-hole DNS reload to flush resolver cache."""
        try:
            result = subprocess.run(
                ['pihole', 'restartdns', 'reload'],
                capture_output=True, timeout=15, check=False
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            log.error('Pi-hole flush failed: %s', e)
            return False

    def update_gravity(self) -> bool:
        """Run a gravity update via the Pi-hole CLI."""
        try:
            result = subprocess.run(
                ['pihole', '-g'],
                capture_output=True, timeout=300, check=False
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            log.error('Gravity update failed: %s', e)
            return False


# ── Unbound ──────────────────────────────────────────────────

@dataclass
class UnboundStats:  # pylint: disable=too-many-instance-attributes
    """Container for Unbound status and cache/query metrics."""

    running: bool = False
    cache_hits: int = 0
    cache_misses: int = 0
    cache_percent: float = 0.0
    queries_total: int = 0
    queries_ps: float = 0.0
    uptime_sec: int = 0
    error: str = ''


class UnboundData:
    """Collect and control Unbound runtime information."""

    def fetch(self) -> UnboundStats:
        """Fetch Unbound stats using `unbound-control stats_noreset`."""
        stats = UnboundStats()
        try:
            result = subprocess.run(
                ['unbound-control', 'stats_noreset'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                stats.error = 'unbound-control error'
                return stats

            d = {}
            for line in result.stdout.splitlines():
                if '=' in line:
                    k, v = line.split('=', 1)
                    d[k.strip()] = v.strip()

            stats.running = True
            stats.cache_hits = int(float(d.get('total.num.cachehits', 0)))
            stats.cache_misses = int(float(d.get('total.num.cachemiss', 0)))
            total_q = stats.cache_hits + stats.cache_misses
            stats.queries_total = total_q
            if total_q > 0:
                stats.cache_percent = round(
                    stats.cache_hits / total_q * 100,
                    1,
                )
            stats.queries_ps = float(
                d.get('total.num.queries_ip_ratelimited', 0),
            )
            uptime = float(d.get('time.elapsed', 0))
            stats.uptime_sec = int(uptime)
            # Queries/s based on uptime and total queries
            if uptime > 0:
                stats.queries_ps = round(total_q / uptime, 1)
        except FileNotFoundError:
            stats.error = 'unbound-control not found'
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            stats.error = str(e)
            log.error('Unbound error: %s', e)
        return stats

    def flush_cache(self) -> bool:
        """Flush the Unbound cache through `unbound-control flush_all`."""
        try:
            result = subprocess.run(
                ['unbound-control', 'flush_all'],
                capture_output=True, timeout=10, check=False
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            log.error('Unbound flush failed: %s', e)
            return False


# ── System ───────────────────────────────────────────────────

@dataclass
class SystemStats:  # pylint: disable=too-many-instance-attributes
    """Container for host, resource, service, and DNS health data."""

    hostname: str = ''
    ip_address: str = ''
    gateway: str = ''
    cpu_percent: float = 0.0
    cpu_temp: float = 0.0
    ram_used_mb: int = 0
    ram_total_mb: int = 0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    uptime_str: str = ''
    pihole_ok: bool = False
    unbound_ok: bool = False
    dns_ok: bool = False


class SystemData:  # pylint: disable=too-few-public-methods
    """Collect system-level telemetry and service health checks."""

    def fetch(self) -> SystemStats:
        """Fetch a full snapshot of host and service status."""
        s = SystemStats()
        s.hostname = socket.gethostname()

        s.ip_address = self._get_ip()
        s.gateway = self._get_gateway()
        s.cpu_percent = psutil.cpu_percent(interval=0.5)
        s.cpu_temp = self._get_cpu_temp()

        mem = psutil.virtual_memory()
        s.ram_used_mb = mem.used // (1024 * 1024)
        s.ram_total_mb = mem.total // (1024 * 1024)

        disk = psutil.disk_usage('/')
        s.disk_used_gb = round(disk.used / (1024**3), 1)
        s.disk_total_gb = round(disk.total / (1024**3), 1)

        uptime_sec = int(time.time() - psutil.boot_time())
        s.uptime_str = self._format_uptime(uptime_sec)

        s.pihole_ok = self._service_running('pihole-FTL')
        s.unbound_ok = self._service_running('unbound')
        s.dns_ok = self._check_dns()
        return s

    def _get_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(('8.8.8.8', 80))
                return sock.getsockname()[0]
        except OSError:
            return '0.0.0.0'

    def _get_gateway(self) -> str:
        try:
            result = subprocess.run(
                ['ip', 'route', 'show', 'default'],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            m = re.search(r'via\s+(\S+)', result.stdout)
            return m.group(1) if m else ''
        except (OSError, subprocess.SubprocessError):
            return ''

    def _get_cpu_temp(self) -> float:
        # BeagleBone Black temperature sensor
        paths = [
            '/sys/class/thermal/thermal_zone0/temp',
            '/sys/devices/virtual/thermal/thermal_zone0/temp',
        ]
        for path in paths:
            try:
                with open(path, encoding='utf-8') as f:
                    return int(f.read().strip()) / 1000.0
            except (OSError, ValueError):
                pass
        try:
            temps = psutil.sensors_temperatures()
            for _, entries in temps.items():
                if entries:
                    return entries[0].current
        except (AttributeError, OSError):
            pass
        return 0.0

    def _format_uptime(self, seconds: int) -> str:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        if days > 0:
            return f'{days}T {hours:02d}:{minutes:02d}'
        return f'{hours:02d}:{minutes:02d}'

    def _service_running(self, name: str) -> bool:
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', name],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            return result.stdout.strip() == 'active'
        except (OSError, subprocess.SubprocessError):
            return False

    def _check_dns(self) -> bool:
        try:
            socket.setdefaulttimeout(2)
            socket.getaddrinfo('pi.hole', None)
            return True
        except (socket.gaierror, OSError):
            try:
                socket.getaddrinfo('google.com', None)
                return True
            except (socket.gaierror, OSError):
                return False


# ── Central cache ────────────────────────────────────────────

class DataCache:
    """Holds all data and refreshes it periodically."""

    def __init__(self):
        self.pihole = PiholeStats()
        self.unbound = UnboundStats()
        self.system = SystemStats()
        self.last_update = 0.0

        self._pihole_api = PiholeAPI()
        self._unbound_api = UnboundData()
        self._system_api = SystemData()

    def refresh(self):
        """Refresh all cached data snapshots from their data sources."""
        self.pihole = self._pihole_api.fetch()
        self.unbound = self._unbound_api.fetch()
        self.system = self._system_api.fetch()
        self.last_update = time.time()
        log.debug('Data refreshed')

    def needs_refresh(self) -> bool:
        """Return whether periodic refresh interval has elapsed."""
        return (time.time() - self.last_update) >= config.REFRESH_INTERVAL

    # Actions
    def pihole_set_blocking(self, enable: bool, seconds: int = 0) -> bool:
        """Apply Pi-hole blocking state and update cached Pi-hole stats."""
        ok = self._pihole_api.set_blocking(enable, seconds)
        if ok:
            time.sleep(0.5)
            self.pihole = self._pihole_api.fetch()
        return ok

    def pihole_flush(self) -> bool:
        """Flush Pi-hole resolver cache."""
        return self._pihole_api.flush_cache()

    def pihole_gravity_update(self) -> bool:
        """Run a gravity update through the Pi-hole API wrapper."""
        return self._pihole_api.update_gravity()

    def unbound_flush(self) -> bool:
        """Flush Unbound resolver cache."""
        return self._unbound_api.flush_cache()
