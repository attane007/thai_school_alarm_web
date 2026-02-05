"""
Access Point (AP) Manager Utility
จัดการโหมด Access Point สำหรับ fallback เมื่อ WiFi หลุด
"""

import subprocess
import os
import logging
import secrets
import string
from typing import Optional, Dict, Tuple, List
from jinja2 import Template

logger = logging.getLogger(__name__)

# Default configurations
DEFAULT_AP_SSID = "SchoolAlarm-Setup"
DEFAULT_AP_CHANNEL = 6
DEFAULT_AP_IP = "192.168.50.1"
DEFAULT_AP_NETMASK = "255.255.255.0"
DEFAULT_DHCP_RANGE_START = "192.168.50.10"
DEFAULT_DHCP_RANGE_END = "192.168.50.50"

# Config file paths
HOSTAPD_CONF = "/etc/hostapd/hostapd-school-alarm.conf"
DNSMASQ_CONF = "/etc/dnsmasq.d/school-alarm-ap.conf"


def generate_random_password(length=10):
    """สร้างรหัสผ่านแบบสุ่ม"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_wifi_interface():
    """ดึงชื่อ WiFi interface"""
    from .wifi_manager import get_wifi_interface as get_iface
    return get_iface() or 'wlan0'


def create_hostapd_config(ssid, password, channel=DEFAULT_AP_CHANNEL, interface=None):
    """
    สร้างไฟล์ config ของ hostapd
    Args:
        ssid: ชื่อ AP
        password: รหัสผ่าน AP
        channel: WiFi channel
        interface: WiFi interface (auto-detect ถ้าไม่ระบุ)
    Returns:
        tuple: (success: bool, message: str)
    """
    if interface is None:
        interface = get_wifi_interface()
    
    template = """interface={{interface}}
driver=nl80211
ssid={{ssid}}
hw_mode=g
channel={{channel}}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={{password}}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
    
    try:
        config = Template(template).render(
            interface=interface,
            ssid=ssid,
            channel=channel,
            password=password
        )
        
        # Write to file
        result = subprocess.run(
            ['sudo', 'tee', HOSTAPD_CONF],
            input=config,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Set permissions
            subprocess.run(['sudo', 'chmod', '600', HOSTAPD_CONF], timeout=5)
            logger.info(f"Created hostapd config: {HOSTAPD_CONF}")
            return True, "สร้างไฟล์ config สำเร็จ"
        else:
            return False, "ไม่สามารถสร้างไฟล์ config ได้"
    
    except Exception as e:
        logger.error(f"Error creating hostapd config: {e}")
        return False, f"เกิดข้อผิดพลาด: {str(e)}"


def create_dnsmasq_config(
    interface=None,
    gateway_ip=DEFAULT_AP_IP,
    dhcp_start=DEFAULT_DHCP_RANGE_START,
    dhcp_end=DEFAULT_DHCP_RANGE_END
):
    """
    สร้างไฟล์ config ของ dnsmasq สำหรับ DHCP และ DNS
    Args:
        interface: WiFi interface
        gateway_ip: IP ของ AP (gateway)
        dhcp_start: IP เริ่มต้นของ DHCP pool
        dhcp_end: IP สิ้นสุดของ DHCP pool
    Returns:
        tuple: (success: bool, message: str)
    """
    if interface is None:
        interface = get_wifi_interface()
    
    template = """interface={{interface}}
bind-interfaces
server=8.8.8.8
server=1.1.1.1
domain-needed
bogus-priv
dhcp-range={{dhcp_start}},{{dhcp_end}},12h
address=/alarm.local/{{gateway_ip}}
"""
    
    try:
        config = Template(template).render(
            interface=interface,
            gateway_ip=gateway_ip,
            dhcp_start=dhcp_start,
            dhcp_end=dhcp_end
        )
        
        # Write to file
        result = subprocess.run(
            ['sudo', 'tee', DNSMASQ_CONF],
            input=config,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"Created dnsmasq config: {DNSMASQ_CONF}")
            return True, "สร้างไฟล์ config สำเร็จ"
        else:
            return False, "ไม่สามารถสร้างไฟล์ config ได้"
    
    except Exception as e:
        logger.error(f"Error creating dnsmasq config: {e}")
        return False, f"เกิดข้อผิดพลาด: {str(e)}"


def start_ap_mode(ssid=DEFAULT_AP_SSID, password=None, channel=DEFAULT_AP_CHANNEL):
    """
    เปิดโหมด Access Point
    Args:
        ssid: ชื่อ AP
        password: รหัสผ่าน AP (สุ่มถ้าไม่ระบุ)
        channel: WiFi channel
    Returns:
        tuple: (success: bool, message: str, ap_info: dict)
    """
    try:
        logger.info(f"Starting AP mode: {ssid}")
        
        # Generate password if not provided
        if not password:
            password = generate_random_password()
        
        interface = get_wifi_interface()
        if not interface:
            return False, "ไม่พบ WiFi interface", {}
        
        # Step 1: Stop NetworkManager on WiFi interface
        logger.info("Stopping NetworkManager on WiFi interface...")
        subprocess.run(
            ['sudo', 'nmcli', 'device', 'set', interface, 'managed', 'no'],
            capture_output=True,
            timeout=10
        )
        
        # Step 2: Bring interface down
        subprocess.run(
            ['sudo', 'ip', 'link', 'set', interface, 'down'],
            capture_output=True,
            timeout=5
        )
        
        # Step 3: Set static IP
        logger.info(f"Setting static IP {DEFAULT_AP_IP} on {interface}...")
        subprocess.run(
            ['sudo', 'ip', 'addr', 'flush', 'dev', interface],
            capture_output=True,
            timeout=5
        )
        subprocess.run(
            ['sudo', 'ip', 'addr', 'add', f'{DEFAULT_AP_IP}/24', 'dev', interface],
            capture_output=True,
            timeout=5
        )
        
        # Step 4: Bring interface up
        subprocess.run(
            ['sudo', 'ip', 'link', 'set', interface, 'up'],
            capture_output=True,
            timeout=5
        )
        
        # Step 5: Create hostapd config
        success, msg = create_hostapd_config(ssid, password, channel, interface)
        if not success:
            return False, f"ไม่สามารถสร้าง hostapd config: {msg}", {}
        
        # Step 6: Create dnsmasq config
        success, msg = create_dnsmasq_config(interface)
        if not success:
            return False, f"ไม่สามารถสร้าง dnsmasq config: {msg}", {}
        
        # Step 7: Start hostapd
        logger.info("Starting hostapd...")
        result = subprocess.run(
            ['sudo', 'systemctl', 'restart', 'hostapd'],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0:
            error = result.stderr or "Unknown error"
            logger.error(f"Failed to start hostapd: {error}")
            return False, f"ไม่สามารถเริ่ม hostapd: {error}", {}
        
        # Step 8: Start dnsmasq
        logger.info("Starting dnsmasq...")
        result = subprocess.run(
            ['sudo', 'systemctl', 'restart', 'dnsmasq'],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0:
            error = result.stderr or "Unknown error"
            logger.error(f"Failed to start dnsmasq: {error}")
            # Try to stop hostapd
            subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'], timeout=10)
            return False, f"ไม่สามารถเริ่ม dnsmasq: {error}", {}
        
        logger.info(f"AP mode started successfully: {ssid}")
        
        ap_info = {
            'ssid': ssid,
            'password': password,
            'channel': channel,
            'ip': DEFAULT_AP_IP,
            'interface': interface
        }
        
        return True, f"เปิดโหมด AP สำเร็จ: {ssid}", ap_info
    
    except Exception as e:
        logger.error(f"Error starting AP mode: {e}")
        return False, f"เกิดข้อผิดพลาด: {str(e)}", {}


def stop_ap_mode():
    """
    ปิดโหมด Access Point และกลับสู่ client mode
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        logger.info("Stopping AP mode...")
        
        interface = get_wifi_interface()
        
        # Step 1: Stop hostapd
        logger.info("Stopping hostapd...")
        subprocess.run(
            ['sudo', 'systemctl', 'stop', 'hostapd'],
            capture_output=True,
            timeout=10
        )
        
        # Step 2: Stop dnsmasq
        logger.info("Stopping dnsmasq...")
        subprocess.run(
            ['sudo', 'systemctl', 'stop', 'dnsmasq'],
            capture_output=True,
            timeout=10
        )
        
        # Step 3: Flush IP addresses
        if interface:
            subprocess.run(
                ['sudo', 'ip', 'addr', 'flush', 'dev', interface],
                capture_output=True,
                timeout=5
            )
            
            # Step 4: Return interface to NetworkManager
            subprocess.run(
                ['sudo', 'nmcli', 'device', 'set', interface, 'managed', 'yes'],
                capture_output=True,
                timeout=10
            )
        
        logger.info("AP mode stopped successfully")
        return True, "ปิดโหมด AP สำเร็จ"
    
    except Exception as e:
        logger.error(f"Error stopping AP mode: {e}")
        return False, f"เกิดข้อผิดพลาด: {str(e)}"


def get_ap_status() -> Dict:
    """
    ดึงสถานะของ Access Point
    Returns:
        dict: สถานะ AP
    """
    try:
        # Check if hostapd is running
        result = subprocess.run(
            ['systemctl', 'is-active', 'hostapd'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        is_active = result.returncode == 0 and result.stdout.strip() == 'active'
        
        if not is_active:
            return {
                'active': False,
                'ssid': None,
                'clients': 0,
                'ip': None
            }
        
        # Try to read config to get SSID
        ssid = None
        try:
            with open(HOSTAPD_CONF, 'r') as f:
                for line in f:
                    if line.startswith('ssid='):
                        ssid = line.split('=', 1)[1].strip()
                        break
        except Exception:
            pass
        
        # Get connected clients count
        clients_count = 0
        try:
            # Try to read hostapd status
            result = subprocess.run(
                ['sudo', 'hostapd_cli', '-p', '/var/run/hostapd', 'all_sta'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Count MAC addresses
                clients_count = result.stdout.count('\n') // 5  # Rough estimate
        except Exception:
            pass
        
        return {
            'active': True,
            'ssid': ssid or DEFAULT_AP_SSID,
            'clients': clients_count,
            'ip': DEFAULT_AP_IP,
            'interface': get_wifi_interface()
        }
    
    except Exception as e:
        logger.error(f"Error getting AP status: {e}")
        return {
            'active': False,
            'error': str(e)
        }


def get_connected_clients() -> List[Dict]:
    """
    ดึงรายการ clients ที่เชื่อมต่อกับ AP
    Returns:
        list: รายการ dict {'mac', 'ip', 'hostname'}
    """
    clients = []
    
    try:
        # Read dnsmasq leases file
        leases_file = '/var/lib/misc/dnsmasq.leases'
        if os.path.exists(leases_file):
            with open(leases_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        clients.append({
                            'mac': parts[1],
                            'ip': parts[2],
                            'hostname': parts[3] if parts[3] != '*' else 'Unknown'
                        })
    except Exception as e:
        logger.error(f"Error reading dnsmasq leases: {e}")
    
    return clients


def is_ap_mode_active() -> bool:
    """
    ตรวจสอบว่าอยู่ใน AP mode หรือไม่
    Returns:
        bool: True ถ้าอยู่ใน AP mode
    """
    status = get_ap_status()
    return status.get('active', False)
