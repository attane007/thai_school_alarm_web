#!/bin/bash
# WiFi Manager Setup Script
# ติดตั้งและตั้งค่าเครื่องมือที่จำเป็นสำหรับ WiFi Management และ Access Point Mode

set -e  # Exit on error

echo "=================================="
echo "WiFi Manager Setup Script"
echo "=================================="
echo ""

# ตรวจสอบว่ารันด้วย sudo หรือไม่
if [ "$EUID" -ne 0 ]; then 
    echo "กรุณารันสคริปต์นี้ด้วย sudo"
    echo "ใช้คำสั่ง: sudo bash $0"
    exit 1
fi

# Detect Linux distribution
echo "กำลังตรวจสอบระบบปฏิบัติการ..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
    OS_NAME=$NAME
else
    echo "ไม่สามารถตรวจสอบระบบปฏิบัติการได้"
    exit 1
fi

echo "ตรวจพบ: $OS_NAME ($OS $VER)"

# ตรวจสอบว่ารองรับหรือไม่
if [[ "$OS" != "ubuntu" && "$OS" != "debian" && "$OS" != "raspbian" ]]; then
    echo "คำเตือน: ระบบนี้อาจไม่รองรับ (รองรับเฉพาะ Ubuntu, Debian, Raspberry Pi OS)"
    read -p "ต้องการดำเนินการต่อหรือไม่? (y/n): " continue
    if [ "$continue" != "y" ]; then
        exit 0
    fi
fi

# Update package list
echo ""
echo "กำลังอัปเดตรายการ package..."
apt-get update -qq

# Install required packages
echo ""
echo "กำลังติดตั้งเครื่องมือที่จำเป็น..."
PACKAGES="network-manager hostapd dnsmasq iw wireless-tools"

for pkg in $PACKAGES; do
    if dpkg -l | grep -q "^ii  $pkg "; then
        echo "✓ $pkg ติดตั้งแล้ว"
    else
        echo "- กำลังติดตั้ง $pkg..."
        apt-get install -y $pkg
    fi
done

echo ""
echo "✓ ติดตั้งเครื่องมือเสร็จสมบูรณ์"

# Handle conflicting services
echo ""
echo "กำลังจัดการ network services..."

# Raspberry Pi OS specific
if [[ "$OS" == "raspbian" ]]; then
    echo "- ตรวจพบ Raspberry Pi OS"
    
    # Disable dhcpcd if exists
    if systemctl list-unit-files | grep -q dhcpcd; then
        echo "- ปิดการใช้งาน dhcpcd (ขัดแย้งกับ NetworkManager)"
        systemctl stop dhcpcd 2>/dev/null || true
        systemctl disable dhcpcd 2>/dev/null || true
    fi
fi

# Ubuntu Server specific
if [[ "$OS" == "ubuntu" && -d /etc/netplan ]]; then
    echo "- ตรวจพบ Ubuntu Server กับ netplan"
    echo "- คำเตือน: อาจต้องแก้ไข netplan config ด้วยตนเอง"
    echo "  เพิ่ม 'renderer: NetworkManager' ใน /etc/netplan/*.yaml"
fi

# Debian specific
if [[ "$OS" == "debian" && -f /etc/network/interfaces ]]; then
    echo "- ตรวจพบ Debian กับ /etc/network/interfaces"
    
    # Backup interfaces file
    if [ ! -f /etc/network/interfaces.backup ]; then
        cp /etc/network/interfaces /etc/network/interfaces.backup
        echo "- สำรองไฟล์ /etc/network/interfaces แล้ว"
    fi
    
    echo "- คำเตือน: อาจต้องคอมเมนต์ wireless interface ใน /etc/network/interfaces"
fi

# Enable and start NetworkManager
echo ""
echo "กำลังเปิดใช้งาน NetworkManager..."
systemctl enable NetworkManager
systemctl start NetworkManager
sleep 2

# Check NetworkManager status
if systemctl is-active --quiet NetworkManager; then
    echo "✓ NetworkManager ทำงานปกติ"
else
    echo "⚠ NetworkManager ไม่ทำงาน กรุณาตรวจสอบ"
fi

# Disable hostapd and dnsmasq auto-start (will be controlled by Django app)
echo ""
echo "กำลังตั้งค่า hostapd และ dnsmasq..."
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
systemctl disable hostapd 2>/dev/null || true
systemctl disable dnsmasq 2>/dev/null || true
echo "✓ hostapd และ dnsmasq จะถูกควบคุมโดยแอปพลิเคชัน"

# Determine web server user
echo ""
echo "กำลังระบุผู้ใช้ web server..."
WEB_USER=""

if id "www-data" &>/dev/null; then
    WEB_USER="www-data"
elif id "pi" &>/dev/null; then
    WEB_USER="pi"
else
    WEB_USER=$(logname 2>/dev/null || echo $SUDO_USER)
fi

if [ -z "$WEB_USER" ]; then
    read -p "กรุณาระบุชื่อผู้ใช้ที่รัน Django (default: www-data): " WEB_USER
    WEB_USER=${WEB_USER:-www-data}
fi

echo "- ใช้ผู้ใช้: $WEB_USER"

# Create sudoers file
SUDOERS_FILE="/etc/sudoers.d/django-wifi"

echo ""
echo "กำลังสร้างไฟล์ sudo permissions..."

cat > $SUDOERS_FILE << EOF
# Django WiFi Management Permissions
# Created by setup_wifi_manager.sh

# NetworkManager commands
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/nmcli
$WEB_USER ALL=(ALL) NOPASSWD: /usr/sbin/nmcli

# hostapd commands
$WEB_USER ALL=(ALL) NOPASSWD: /usr/sbin/hostapd
$WEB_USER ALL=(ALL) NOPASSWD: /bin/systemctl start hostapd
$WEB_USER ALL=(ALL) NOPASSWD: /bin/systemctl stop hostapd
$WEB_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart hostapd
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start hostapd
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop hostapd
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart hostapd

# dnsmasq commands
$WEB_USER ALL=(ALL) NOPASSWD: /usr/sbin/dnsmasq
$WEB_USER ALL=(ALL) NOPASSWD: /bin/systemctl start dnsmasq
$WEB_USER ALL=(ALL) NOPASSWD: /bin/systemctl stop dnsmasq
$WEB_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart dnsmasq
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start dnsmasq
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop dnsmasq
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dnsmasq

# IP/network commands
$WEB_USER ALL=(ALL) NOPASSWD: /sbin/ip
$WEB_USER ALL=(ALL) NOPASSWD: /usr/sbin/ip

# Package installation (for auto-install feature)
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/apt-get update
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/apt-get install *

# File write commands (for config files)
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/tee /etc/hostapd/*
$WEB_USER ALL=(ALL) NOPASSWD: /usr/bin/tee /etc/dnsmasq.d/*

# Permissions
$WEB_USER ALL=(ALL) NOPASSWD: /bin/chmod * /etc/hostapd/*
EOF

# Set correct permissions
chmod 440 $SUDOERS_FILE

# Validate sudoers syntax
if visudo -c -f $SUDOERS_FILE; then
    echo "✓ สร้างไฟล์ $SUDOERS_FILE สำเร็จ"
else
    echo "⚠ ไฟล์ sudoers มีข้อผิดพลาด กรุณาตรวจสอบ"
    rm -f $SUDOERS_FILE
    exit 1
fi

# Create config directories
echo ""
echo "กำลังสร้างโฟลเดอร์ config..."
mkdir -p /etc/hostapd
mkdir -p /etc/dnsmasq.d
echo "✓ สร้างโฟลเดอร์เสร็จสิ้น"

# Done
echo ""
echo "=================================="
echo "✓ ติดตั้งเสร็จสมบูรณ์!"
echo "=================================="
echo ""
echo "สรุป:"
echo "- ติดตั้งเครื่องมือ: NetworkManager, hostapd, dnsmasq, iw"
echo "- ตั้งค่า sudo permissions สำหรับผู้ใช้: $WEB_USER"
echo "- NetworkManager พร้อมใช้งาน"
echo ""
echo "หมายเหตุ:"
echo "1. คุณสามารถใช้งาน WiFi Management ผ่าน web interface ได้แล้ว"
echo "2. ถ้ามีปัญหา กรุณาตรวจสอบ:"
echo "   - systemctl status NetworkManager"
echo "   - journalctl -u NetworkManager -f"
echo ""
echo "ขอบคุณที่ใช้งาน Thai School Alarm System!"
