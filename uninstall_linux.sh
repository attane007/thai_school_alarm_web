#!/bin/bash

# Thai School Alarm Web - Linux/Raspberry Pi Uninstall Script
# Requires: Linux/Raspberry Pi OS, sudo access

set -e

INSTALL_PATH="${1:-.}"
APP_NAME="thai_school_alarm_web"
SERVICE_NAME="thai-school-alarm"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

write_status() {
    local message="$1"
    local status="${2:Info}"
    
    case $status in
        "Success")
            echo -e "${GREEN}[✓]${NC} $message"
            ;;
        "Error")
            echo -e "${RED}[✗]${NC} $message"
            ;;
        "Warning")
            echo -e "${YELLOW}[!]${NC} $message"
            ;;
        *)
            echo -e "${CYAN}[*]${NC} $message"
            ;;
    esac
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        write_status "This script requires root (sudo) privileges!" "Error"
        exit 1
    fi
}

stop_services() {
    write_status "Checking for systemd services..." "Info"
    
    local services=(
        "${SERVICE_NAME}-scheduler.service"
        "${SERVICE_NAME}.service"
        "thai-school-alarm-scheduler"
    )
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            write_status "Stopping $service..." "Info"
            systemctl stop "$service" || true
            systemctl disable "$service" || true
            write_status "Service stopped and disabled" "Success"
        fi
    done
}

remove_service_files() {
    write_status "Removing systemd service files..." "Info"
    
    local service_files=(
        "/etc/systemd/system/${SERVICE_NAME}-scheduler.service"
        "/etc/systemd/system/${SERVICE_NAME}-scheduler.service.bak"
        "/etc/systemd/system/${SERVICE_NAME}.service"
        "/etc/systemd/system/${SERVICE_NAME}.service.bak"
    )
    
    for file in "${service_files[@]}"; do
        if [ -f "$file" ]; then
            rm -f "$file"
            write_status "Removed $file" "Success"
        fi
    done
    
    systemctl daemon-reload || true
}

remove_app_directory() {
    if [ ! -d "$INSTALL_PATH" ]; then
        write_status "Installation directory not found: $INSTALL_PATH" "Info"
        return 0
    fi
    
    write_status "Removing installation directory..." "Info"
    
    if rm -rf "$INSTALL_PATH" 2>/dev/null; then
        write_status "Installation directory removed successfully" "Success"
        return 0
    else
        write_status "Failed to remove directory (permission issue?): $INSTALL_PATH" "Error"
        return 1
    fi
}

remove_logs_directory() {
    write_status "Checking for application logs directory..." "Info"
    
    local logs_path="/var/log/$APP_NAME"
    
    if [ -d "$logs_path" ]; then
        write_status "Found logs directory: $logs_path" "Info"
        
        read -p "$(echo -e ${YELLOW}Remove application logs? (y/n)${NC} )" -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if rm -rf "$logs_path" 2>/dev/null; then
                write_status "Logs directory removed successfully" "Success"
            else
                write_status "Could not remove logs directory: $logs_path" "Warning"
            fi
        else
            write_status "Skipping logs directory" "Warning"
        fi
    else
        write_status "Logs directory not found" "Info"
    fi
}

remove_backups() {
    write_status "Checking for database backups..." "Info"
    
    local backup_path="/var/backups/$APP_NAME"
    
    if [ -d "$backup_path" ]; then
        write_status "Found backup directory: $backup_path" "Info"
        
        read -p "$(echo -e ${YELLOW}Remove database backups? (y/n)${NC} )" -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if rm -rf "$backup_path" 2>/dev/null; then
                write_status "Backup directory removed successfully" "Success"
            else
                write_status "Could not remove backup directory: $backup_path" "Warning"
            fi
        else
            write_status "Skipping backup directory" "Warning"
        fi
    else
        write_status "Backup directory not found" "Info"
    fi
}

remove_cron_jobs() {
    write_status "Checking for cron jobs..." "Info"
    
    if crontab -l 2>/dev/null | grep -q "$APP_NAME"; then
        write_status "Found $APP_NAME cron jobs" "Info"
        (crontab -l 2>/dev/null | grep -v "$APP_NAME"; echo "") | crontab - 2>/dev/null || true
        write_status "Cron jobs removed" "Success"
    else
        write_status "No cron jobs found" "Info"
    fi
}

remove_udev_rules() {
    write_status "Checking for udev rules..." "Info"
    
    if [ -f "/etc/udev/rules.d/99-$APP_NAME.rules" ]; then
        rm -f "/etc/udev/rules.d/99-$APP_NAME.rules"
        write_status "Udev rules removed" "Success"
        udevadm control --reload-rules || true
        udevadm trigger || true
    else
        write_status "No udev rules found" "Info"
    fi
}

main() {
    echo ""
    echo -e "${CYAN}=== Thai School Alarm Web - Linux Uninstall ===${NC}"
    echo -e "${CYAN}Install Path: $INSTALL_PATH${NC}"
    echo ""
    
    echo -e "${YELLOW}This will remove Thai School Alarm Web from:${NC}"
    echo "  - Installation: $INSTALL_PATH"
    echo "  - Systemd Services"
    echo "  - Logs: /var/log/$APP_NAME (optional)"
    echo "  - Backups: /var/backups/$APP_NAME (optional)"
    echo ""
    
    read -p "$(echo -e ${YELLOW}Continue with uninstall? (y/n)${NC} )" -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        write_status "Uninstall cancelled" "Warning"
        exit 0
    fi
    
    echo ""
    check_root
    stop_services
    remove_service_files
    remove_app_directory || true
    remove_logs_directory
    remove_backups
    remove_cron_jobs
    remove_udev_rules
    
    echo ""
    write_status "Uninstall completed successfully!" "Success"
    echo ""
    echo -e "${CYAN}=== Summary ===${NC}"
    echo "✓ Systemd services removed"
    echo "✓ Application directory removed"
    echo "✓ Logs and backups removed (if selected)"
    echo "✓ Cron jobs removed"
    echo "✓ Udev rules removed"
    echo ""
    echo -e "${GREEN}Thai School Alarm Web has been completely uninstalled from your system.${NC}"
    echo ""
}

main
