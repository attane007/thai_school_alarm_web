#!/bin/bash

STATUS_FILE="process_status.log"
RELOAD_SCRIPT="scripts/reload_django.sh"

# ฟังก์ชันช่วยในการเขียน log
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$STATUS_FILE"
}

# ล้าง log เก่า และเริ่มต้น process ใหม่
echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- Update Process Started ---" > "$STATUS_FILE"

log_message "⏳ Starting update process..."
log_message "⚡ Resetting local changes..."
git reset --hard origin/prod &>> "$STATUS_FILE"

log_message "🧹 Cleaning untracked files..."
git clean -fd &>> "$STATUS_FILE"

log_message "⬇️ Pulling latest code from branch 'prod'..."
GIT_OUTPUT=$(git pull origin prod --force 2>&1 | tee -a "$STATUS_FILE")
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_message "✅ Git pull completed successfully."

    # ✅ รัน reload script หลังจากอัปเดตสำเร็จ
    if [ -f "$RELOAD_SCRIPT" ]; then
        log_message "🔄 Running reload script: $RELOAD_SCRIPT"
        chmod +x "$RELOAD_SCRIPT"
        "$RELOAD_SCRIPT" 2>&1 | tee -a "$STATUS_FILE"  # ✅ Append output จาก reload script
    else
        log_message "⚠️ Reload script not found!"
    fi
else
    log_message "❌ Git pull failed!"
fi

log_message "✅ Update process finished."
