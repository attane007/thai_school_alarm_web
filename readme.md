# Thai School Alarm Web by KruFame

[![Test Status](https://img.shields.io/badge/tests-passing-brightgreen?style=flat-square&logo=pytest)](https://github.com/attane007/thai_school_alarm_web/actions)

ระบบออดโรงเรียนอัตโนมัติสำหรับโรงเรียนไทย รองรับการตั้งเวลาเสียงออด เสียงประกาศ และเสียงกิจกรรมต่าง ๆ พร้อมระบบอัพโหลดไฟล์เสียงและ AI สังเคราะห์เสียงภาษาไทย

## คุณสมบัติเด่น
- ตั้งเวลาออดและกิจกรรมได้อย่างยืดหยุ่น
- อัพโหลดไฟล์เสียง MP3/WAV และจัดการไฟล์เสียงผ่านหน้าเว็บ
- สังเคราะห์เสียงประกาศด้วย AI (Text-to-Speech)
- รองรับการใช้งานผ่าน Cloudflare Tunnel และ Reverse Proxy
- ระบบความปลอดภัย CSRF Token และรองรับ HTTPS
- รองรับการ deploy อัตโนมัติด้วย Shell Script

## Deployment

Deploy ได้ง่าย ๆ ด้วยคำสั่งเดียว:

```bash
curl -sSL https://raw.githubusercontent.com/attane007/thai_school_alarm_web/prod/deploy_django.sh -o deploy_django.sh
chmod +x deploy_django.sh
./deploy_django.sh
```

## การสนับสนุนและติดต่อ

- อีเมล: poramin@kkumail.com
- Facebook: [KruFame](https://www.facebook.com/kru.fame)
- รายละเอียดและคู่มือเพิ่มเติม: [Wiki](https://github.com/attane007/thai_school_alarm_web/wiki)

---

> โครงการนี้พัฒนาเพื่อสนับสนุนโรงเรียนไทยและการเรียนรู้ด้านเทคโนโลยี

