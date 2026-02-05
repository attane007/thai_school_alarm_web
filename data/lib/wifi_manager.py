"""
WiFi Management Utility
จัดการการเชื่อมต่อ WiFi ผ่าน NetworkManager (nmcli)
"""

import subprocess
import re
import logging
import socket
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)


def is_network_manager_available() -> bool:
    """
    ตรวจสอบว่า NetworkManager พร้อมใช้งานหรือไม่
    Returns:
        bool: True ถ้าพร้อมใช้งาน
    """
    try:
        result = subprocess.run(
            ['nmcli', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def get_wifi_interface() -> Optional[str]:
    """
    ค้นหา WiFi interface ที่ใช้งานได้
    Returns:
        str: ชื่อ interface (e.g., 'wlan0') หรือ None
    """
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'DEVICE,TYPE', 'device'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    device, dev_type = line.split(':', 1)
                    if dev_type == 'wifi':
                        return device
        
        # Fallback: try common names
        for iface in ['wlan0', 'wlp2s0', 'wlp3s0', 'wlo1']:
            check = subprocess.run(
                ['ip', 'link', 'show', iface],
                capture_output=True,
                timeout=3
            )
            if check.returncode == 0:
                return iface
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting WiFi interface: {e}")
        return None


def validate_ssid(ssid: str) -> bool:
    """
    ตรวจสอบความถูกต้องของ SSID
    Args:
        ssid: ชื่อ SSID
    Returns:
        bool: True ถ้าถูกต้อง
    """
    if not ssid or len(ssid) > 32 or len(ssid) < 1:
        return False
    # Allow alphanumeric, spaces, hyphens, underscores
    return bool(re.match(r'^[\w\s\-\.]+$', ssid))


def validate_password(password: str) -> bool:
    """
    ตรวจสอบความถูกต้องของ WiFi password
    Args:
        password: รหัสผ่าน
    Returns:
        bool: True ถ้าถูกต้อง (8-63 characters สำหรับ WPA/WPA2)
    """
    if not password:
        return True  # Open network
    return 8 <= len(password) <= 63


def get_current_wifi() -> Optional[Dict]:
    """
    ดึงข้อมูล WiFi ที่เชื่อมต่ออยู่ปัจจุบัน
    Returns:
        dict: {'ssid', 'signal', 'ip', 'device', 'connected'} หรือ None
    """
    if not is_network_manager_available():
        return None
    
    try:
        # Get active WiFi connection
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device', 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return None
        
        wifi_info = None
        for line in result.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) == 4:
                device, dev_type, state, connection = parts
                if dev_type == 'wifi' and state == 'connected':
                    wifi_info = {
                        'device': device,
                        'ssid': connection,
                        'connected': True
                    }
                    break
        
        if not wifi_info:
            return None
        
        # Get signal strength
        signal_result = subprocess.run(
            ['nmcli', '-t', '-f', 'IN-USE,SIGNAL,SSID', 'device', 'wifi', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if signal_result.returncode == 0:
            for line in signal_result.stdout.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 3 and parts[0] == '*':
                    wifi_info['signal'] = int(parts[1]) if parts[1].isdigit() else 0
                    break
        
        # Get IP address
        ip_result = subprocess.run(
            ['nmcli', '-t', '-f', 'IP4.ADDRESS', 'connection', 'show', wifi_info['ssid']],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if ip_result.returncode == 0 and ip_result.stdout.strip():
            ip_line = ip_result.stdout.strip().split('\n')[0]
            wifi_info['ip'] = ip_line.split(':')[1].split('/')[0] if ':' in ip_line else ip_line.split('/')[0]
        else:
            wifi_info['ip'] = None
        
        return wifi_info
    
    except Exception as e:
        logger.error(f"Error getting current WiFi: {e}")
        return None


def scan_wifi_networks() -> List[Dict]:
    """
    สแกนหา WiFi networks ที่มีอยู่
    Returns:
        list: รายการ dict {'ssid', 'signal', 'security', 'connected'}
    """
    if not is_network_manager_available():
        return []
    
    try:
        # Trigger rescan
        subprocess.run(
            ['sudo', 'nmcli', 'device', 'wifi', 'rescan'],
            capture_output=True,
            timeout=15
        )
        
        # Get list
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'IN-USE,SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return []
        
        networks = []
        seen_ssids = set()
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split(':')
            if len(parts) >= 4:
                in_use = parts[0]
                ssid = parts[1]
                signal = parts[2]
                security = parts[3]
                
                # Skip hidden networks and duplicates
                if not ssid or ssid in seen_ssids:
                    continue
                
                seen_ssids.add(ssid)
                
                networks.append({
                    'ssid': ssid,
                    'signal': int(signal) if signal.isdigit() else 0,
                    'security': security if security else 'Open',
                    'connected': in_use == '*'
                })
        
        # Sort by signal strength
        networks.sort(key=lambda x: x['signal'], reverse=True)
        
        return networks
    
    except Exception as e:
        logger.error(f"Error scanning WiFi: {e}")
        return []


def connect_to_wifi(ssid: str, password: str = '') -> Tuple[bool, str]:
    """
    เชื่อมต่อกับ WiFi network
    Args:
        ssid: ชื่อ SSID
        password: รหัสผ่าน (ถ้ามี)
    Returns:
        tuple: (success: bool, message: str)
    """
    if not is_network_manager_available():
        return False, "NetworkManager ไม่พร้อมใช้งาน"
    
    # Validate inputs
    if not validate_ssid(ssid):
        return False, "SSID ไม่ถูกต้อง (1-32 ตัวอักษร)"
    
    if password and not validate_password(password):
        return False, "รหัสผ่านไม่ถูกต้อง (8-63 ตัวอักษร)"
    
    try:
        logger.info(f"Attempting to connect to WiFi: {ssid}")
        
        # Build command
        cmd = ['sudo', 'nmcli', 'device', 'wifi', 'connect', ssid]
        
        if password:
            cmd.extend(['password', password])
        
        # Connect
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully connected to {ssid}")
            return True, f"เชื่อมต่อ {ssid} สำเร็จ"
        else:
            error_msg = result.stderr.strip() if result.stderr else "ไม่สามารถเชื่อมต่อได้"
            logger.error(f"Failed to connect to {ssid}: {error_msg}")
            
            # Parse common errors
            if 'Secrets were required' in error_msg:
                return False, "รหัสผ่านไม่ถูกต้อง"
            elif 'No network with SSID' in error_msg:
                return False, "ไม่พบเครือข่าย WiFi นี้"
            elif 'Timeout' in error_msg:
                return False, "หมดเวลาการเชื่อมต่อ"
            else:
                return False, f"เชื่อมต่อล้มเหลว: {error_msg}"
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout connecting to {ssid}")
        return False, "หมดเวลาการเชื่อมต่อ (30 วินาที)"
    except Exception as e:
        logger.error(f"Error connecting to WiFi: {e}")
        return False, f"เกิดข้อผิดพลาด: {str(e)}"


def disconnect_wifi() -> Tuple[bool, str]:
    """
    ตัดการเชื่อมต่อ WiFi ปัจจุบัน
    Returns:
        tuple: (success: bool, message: str)
    """
    if not is_network_manager_available():
        return False, "NetworkManager ไม่พร้อมใช้งาน"
    
    try:
        current = get_current_wifi()
        if not current:
            return True, "ไม่ได้เชื่อมต่อ WiFi อยู่"
        
        device = current['device']
        
        result = subprocess.run(
            ['sudo', 'nmcli', 'device', 'disconnect', device],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"Disconnected WiFi on {device}")
            return True, "ตัดการเชื่อมต่อสำเร็จ"
        else:
            return False, "ไม่สามารถตัดการเชื่อมต่อได้"
    
    except Exception as e:
        logger.error(f"Error disconnecting WiFi: {e}")
        return False, f"เกิดข้อผิดพลาด: {str(e)}"


def check_internet_connectivity() -> bool:
    """
    ตรวจสอบว่ามีการเชื่อมต่ออินเทอร์เน็ตหรือไม่
    Returns:
        bool: True ถ้ามีอินเทอร์เน็ต
    """
    # Try pinging multiple DNS servers
    dns_servers = ['8.8.8.8', '1.1.1.1', '208.67.222.222']
    
    for dns in dns_servers:
        try:
            # Use socket to check connectivity (faster than ping)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((dns, 53))
            sock.close()
            
            if result == 0:
                return True
        except Exception:
            continue
    
    return False


def check_wifi_connection() -> bool:
    """
    ตรวจสอบว่ายังเชื่อมต่อ WiFi อยู่หรือไม่
    Returns:
        bool: True ถ้ายังเชื่อมต่ออยู่
    """
    current = get_current_wifi()
    return current is not None and current.get('connected', False)


def is_ap_mode_active() -> bool:
    """
    ตรวจสอบว่าอยู่ใน Access Point mode หรือไม่
    Returns:
        bool: True ถ้าอยู่ใน AP mode
    """
    try:
        # Check if hostapd is running
        result = subprocess.run(
            ['systemctl', 'is-active', 'hostapd'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and result.stdout.strip() == 'active'
    except Exception:
        return False


def forget_network(ssid: str) -> Tuple[bool, str]:
    """
    ลบ/ลืม WiFi network ที่เคยบันทึกไว้
    Args:
        ssid: ชื่อ SSID
    Returns:
        tuple: (success: bool, message: str)
    """
    if not is_network_manager_available():
        return False, "NetworkManager ไม่พร้อมใช้งาน"
    
    try:
        result = subprocess.run(
            ['sudo', 'nmcli', 'connection', 'delete', ssid],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"Forgot network: {ssid}")
            return True, f"ลบเครือข่าย {ssid} สำเร็จ"
        else:
            return False, "ไม่พบเครือข่ายที่ต้องการลบ"
    
    except Exception as e:
        logger.error(f"Error forgetting network: {e}")
        return False, f"เกิดข้อผิดพลาด: {str(e)}"
