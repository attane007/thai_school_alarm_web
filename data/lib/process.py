"""
Cross-platform process management utilities.
Supports both Windows and Linux process checking.
"""

from .platform_helpers import check_process_exists


def is_process_running(process_id):
    """
    ตรวจสอบว่า process_id กำลังทำงานอยู่หรือไม่
    Cross-platform implementation supporting Windows and Linux.
    
    Args:
        process_id: Process ID to check
        
    Returns:
        True if process is running, False otherwise
    """
    try:
        process_id = int(process_id)  # แปลงเป็น int เพื่อตรวจสอบ
        return check_process_exists(process_id)
    except (ValueError, TypeError):
        return False  # process_id ไม่ใช่ตัวเลขที่ถูกต้อง
    except Exception:
        return False  # กรณีอื่น ๆ