#!/bin/bash

STATUS_FILE="process_status.json"
RELOAD_SCRIPT="scripts/reload_django.sh"

# ฟังก์ชันช่วยในการเขียน log และอัปเดต JSON
log_and_update() {
    echo "$1" | tee -a "$STATUS_FILE"
}

# ตั้งค่าเริ่มต้นเป็น running และเคลียร์ output เก่า
echo '{
    "status": "running",
    "output": "",
    "error": ""
}' > $STATUS_FILE

log_and_update "⏳ Starting update process..."
log_and_update "⚡ Resetting local changes..."
git reset --hard origin/prod &>> "$STATUS_FILE"

log_and_update "🧹 Cleaning untracked files..."
git clean -fd &>> "$STATUS_FILE"

log_and_update "⬇️ Pulling latest code from branch 'prod'..."
GIT_OUTPUT=$(git pull origin prod --force 2>&1)
EXIT_CODE=$?

echo "$GIT_OUTPUT" >> "$STATUS_FILE"

if [ $EXIT_CODE -eq 0 ]; then
    STATUS="success"
    ERROR_MSG=""
    log_and_update "✅ Git pull completed successfully."

    # ✅ รัน reload script หลังจากอัปเดตสำเร็จ
    if [ -f "$RELOAD_SCRIPT" ]; then
        log_and_update "🔄 Running reload script: $RELOAD_SCRIPT"
        chmod +x "$RELOAD_SCRIPT"
        RELOAD_OUTPUT=$("$RELOAD_SCRIPT" 2>&1)
        log_and_update "$RELOAD_OUTPUT"
    else
        RELOAD_OUTPUT="Reload script not found"
        log_and_update "⚠️ Reload script not found!"
    fi
else
    STATUS="failed"
    ERROR_MSG="$GIT_OUTPUT"
    RELOAD_OUTPUT=""
    log_and_update "❌ Git pull failed!"
fi

# อัปเดตสถานะในไฟล์ JSON (ยังคงเก็บ output เก่าทั้งหมด)
echo '{
    "status": "'"$STATUS"'",
    "output": "'"$(cat $STATUS_FILE)"'",
    "error": "'"$ERROR_MSG"'",
    "reload_output": "'"$RELOAD_OUTPUT"'"
}' > "$STATUS_FILE"

log_and_update "✅ Update process finished."
