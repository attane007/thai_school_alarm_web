#!/bin/bash

STATUS_FILE="process_status.json"
RELOAD_SCRIPT="scripts/reload_django.sh"

# ตั้งค่าเริ่มต้นเป็น running
echo '{
    "status": "running",
    "output": "",
    "error": ""
}' > $STATUS_FILE

# รีเซ็ตการเปลี่ยนแปลงใน local
git reset --hard origin/prod

# ล้างไฟล์ที่ไม่ได้อยู่ในการควบคุมของ Git (Optional: ถ้ามีไฟล์ใหม่ที่ไม่ได้ commit)
git clean -fd

# ดึงโค้ดล่าสุดจาก branch prod
GIT_OUTPUT=$(git pull origin prod --force 2>&1)
EXIT_CODE=$?

# ตรวจสอบว่า git pull สำเร็จหรือไม่
if [ $EXIT_CODE -eq 0 ]; then
    STATUS="success"
    ERROR_MSG=""
    
    # ✅ รัน reload.sh หลังจากอัปเดตสำเร็จ
    if [ -f "$RELOAD_SCRIPT" ]; then
        chmod +x "$RELOAD_SCRIPT"
        RELOAD_OUTPUT=$("$RELOAD_SCRIPT" 2>&1)
    else
        RELOAD_OUTPUT="Reload script not found"
    fi
else
    STATUS="failed"
    ERROR_MSG="$GIT_OUTPUT"
    RELOAD_OUTPUT=""
fi

# อัปเดตสถานะในไฟล์ JSON
echo '{
    "status": "'"$STATUS"'",
    "output": "'"$GIT_OUTPUT"'",
    "error": "'"$ERROR_MSG"'",
    "reload_output": "'"$RELOAD_OUTPUT"'"
}' > $STATUS_FILE
