import subprocess

def is_process_running(process_id):
    """ ตรวจสอบว่า process_id กำลังทำงานอยู่หรือไม่โดยใช้คำสั่งระบบ """
    try:
        process_id = int(process_id)  # แปลงเป็น int เพื่อตรวจสอบ
        result = subprocess.run(["ps", "-p", str(process_id)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0  # ถ้า returncode = 0 แสดงว่า process กำลังทำงาน
    except ValueError:
        return False  # process_id ไม่ใช่ตัวเลขที่ถูกต้อง
    except Exception:
        return False  # กรณีอื่น ๆ เช่นคำสั่งล้มเหลว