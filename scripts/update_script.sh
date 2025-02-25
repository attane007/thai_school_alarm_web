#!/bin/bash

STATUS_FILE="process_status.json"

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
else
    STATUS="failed"
    ERROR_MSG="$GIT_OUTPUT"
fi

# อัปเดตสถานะในไฟล์ JSON
echo '{
    "status": "'"$STATUS"'",
    "output": "'"$GIT_OUTPUT"'",
    "error": "'"$ERROR_MSG"'"
}' > $STATUS_FILE
