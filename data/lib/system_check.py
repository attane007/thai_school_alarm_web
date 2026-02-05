"""
System Check and Auto-installation Utility
ตรวจสอบและติดตั้งเครื่องมือที่จำเป็นสำหรับ WiFi Management
"""

import subprocess
import platform
import logging

logger = logging.getLogger(__name__)


def is_linux():
    """ตรวจสอบว่าเป็น Linux OS หรือไม่"""
    return platform.system() == 'Linux'


def detect_linux_distro():
    """
    ตรวจสอบ Linux distribution
    Returns: dict with 'id', 'version', 'name'
    """
    if not is_linux():
        return None
    
    try:
        # Try reading /etc/os-release (modern way)
        if hasattr(platform, 'freedesktop_os_release'):
            info = platform.freedesktop_os_release()
            return {
                'id': info.get('ID', '').lower(),
                'version': info.get('VERSION_ID', ''),
                'name': info.get('NAME', '')
            }
    except Exception:
        pass
    
    try:
        # Fallback: parse /etc/os-release manually
        with open('/etc/os-release', 'r') as f:
            lines = f.readlines()
            info = {}
            for line in lines:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    info[key] = value.strip('"')
            
            return {
                'id': info.get('ID', '').lower(),
                'version': info.get('VERSION_ID', ''),
                'name': info.get('NAME', '')
            }
    except Exception as e:
        logger.error(f"Cannot detect Linux distro: {e}")
        return None


def check_command_exists(command):
    """
    ตรวจสอบว่า command มีอยู่ในระบบหรือไม่
    Args:
        command: ชื่อ command (e.g., 'nmcli')
    Returns:
        bool: True ถ้ามี, False ถ้าไม่มี
    """
    try:
        result = subprocess.run(
            ['which', command],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def check_service_exists(service_name):
    """
    ตรวจสอบว่า systemd service มีอยู่หรือไม่
    Args:
        service_name: ชื่อ service (e.g., 'NetworkManager')
    Returns:
        bool: True ถ้ามี, False ถ้าไม่มี
    """
    try:
        result = subprocess.run(
            ['systemctl', 'list-unit-files', f'{service_name}.service'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return service_name in result.stdout
    except Exception:
        return False


def check_network_tools():
    """
    ตรวจสอบเครื่องมือที่จำเป็นทั้งหมด
    Returns:
        dict: สถานะของแต่ละ tool
    """
    if not is_linux():
        return {
            'platform_supported': False,
            'message': 'WiFi management รองรับเฉพาะ Linux เท่านั้น'
        }
    
    distro = detect_linux_distro()
    if distro:
        distro_id = distro['id']
        supported = distro_id in ['ubuntu', 'debian', 'raspbian']
    else:
        supported = False
    
    tools = {
        'platform_supported': supported,
        'distro': distro,
        'network_manager': {
            'command': 'nmcli',
            'installed': check_command_exists('nmcli'),
            'service': check_service_exists('NetworkManager'),
            'package': 'network-manager'
        },
        'hostapd': {
            'command': 'hostapd',
            'installed': check_command_exists('hostapd'),
            'service': check_service_exists('hostapd'),
            'package': 'hostapd'
        },
        'dnsmasq': {
            'command': 'dnsmasq',
            'installed': check_command_exists('dnsmasq'),
            'service': check_service_exists('dnsmasq'),
            'package': 'dnsmasq'
        },
        'iw': {
            'command': 'iw',
            'installed': check_command_exists('iw'),
            'package': 'iw'
        }
    }
    
    # สรุปว่าครบหรือไม่
    all_installed = all(
        tool['installed'] for name, tool in tools.items() 
        if isinstance(tool, dict) and 'installed' in tool
    )
    
    tools['all_installed'] = all_installed
    
    return tools


def get_missing_packages():
    """
    ดึงรายการ packages ที่ยังไม่ได้ติดตั้ง
    Returns:
        list: รายการชื่อ packages
    """
    status = check_network_tools()
    
    if not status['platform_supported']:
        return []
    
    missing = []
    for name, tool in status.items():
        if isinstance(tool, dict) and 'installed' in tool:
            if not tool['installed']:
                missing.append(tool['package'])
    
    return missing


def install_package(package_name, progress_callback=None):
    """
    ติดตั้ง package ผ่าน apt
    Args:
        package_name: ชื่อ package
        progress_callback: function สำหรับส่ง progress (optional)
    Returns:
        tuple: (success: bool, message: str)
    """
    if not is_linux():
        return False, "ไม่รองรับระบบปฏิบัติการนี้"
    
    try:
        logger.info(f"Installing {package_name}...")
        
        if progress_callback:
            progress_callback(f"กำลังติดตั้ง {package_name}...")
        
        # Update apt cache first
        update_result = subprocess.run(
            ['sudo', 'apt-get', 'update'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if update_result.returncode != 0:
            logger.warning(f"apt-get update warning: {update_result.stderr}")
        
        # Install package
        install_result = subprocess.run(
            ['sudo', 'apt-get', 'install', '-y', package_name],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if install_result.returncode == 0:
            logger.info(f"Successfully installed {package_name}")
            if progress_callback:
                progress_callback(f"ติดตั้ง {package_name} สำเร็จ")
            return True, f"ติดตั้ง {package_name} สำเร็จ"
        else:
            error_msg = install_result.stderr or "Unknown error"
            logger.error(f"Failed to install {package_name}: {error_msg}")
            if progress_callback:
                progress_callback(f"ติดตั้ง {package_name} ล้มเหลว: {error_msg}")
            return False, f"ติดตั้งล้มเหลว: {error_msg}"
    
    except subprocess.TimeoutExpired:
        msg = f"การติดตั้ง {package_name} ใช้เวลานานเกินไป"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"เกิดข้อผิดพลาด: {str(e)}"
        logger.error(f"Error installing {package_name}: {e}")
        return False, msg


def install_all_missing_tools(progress_callback=None):
    """
    ติดตั้งเครื่องมือที่ขาดหายไปทั้งหมด
    Args:
        progress_callback: function สำหรับส่ง progress
    Returns:
        tuple: (success: bool, results: dict)
    """
    missing_packages = get_missing_packages()
    
    if not missing_packages:
        return True, {"message": "เครื่องมือครบถ้วนแล้ว"}
    
    results = {
        'installed': [],
        'failed': [],
        'total': len(missing_packages)
    }
    
    for package in missing_packages:
        success, message = install_package(package, progress_callback)
        
        if success:
            results['installed'].append(package)
        else:
            results['failed'].append({
                'package': package,
                'error': message
            })
    
    overall_success = len(results['failed']) == 0
    
    return overall_success, results


def get_installation_status():
    """
    ดึงสถานะการติดตั้งแบบละเอียด
    Returns:
        dict: ข้อมูลสถานะทั้งหมด
    """
    tools = check_network_tools()
    missing = get_missing_packages()
    
    return {
        'supported': tools.get('platform_supported', False),
        'distro': tools.get('distro'),
        'tools': tools,
        'missing_packages': missing,
        'ready': tools.get('all_installed', False)
    }
