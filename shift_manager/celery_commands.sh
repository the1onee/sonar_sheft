#!/bin/bash

# ملف للأوامر السريعة لإدارة Celery على VPS

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

show_menu() {
    clear
    echo -e "${BLUE}=========================================="
    echo "إدارة Celery - نظام إدارة السونار"
    echo -e "==========================================${NC}"
    echo ""
    echo "1. فحص حالة الخدمات"
    echo "2. إعادة تشغيل Worker"
    echo "3. إعادة تشغيل Beat"
    echo "4. إعادة تشغيل الكل"
    echo "5. إيقاف الخدمات"
    echo "6. بدء الخدمات"
    echo "7. عرض سجلات Worker"
    echo "8. عرض سجلات Beat"
    echo "9. تحديث وإعادة تشغيل"
    echo "0. خروج"
    echo ""
    echo -n "اختر رقم: "
}

check_status() {
    echo -e "${YELLOW}فحص حالة الخدمات...${NC}"
    echo ""
    echo -e "${BLUE}=== Celery Worker ===${NC}"
    sudo systemctl status celery_worker --no-pager | head -n 10
    echo ""
    echo -e "${BLUE}=== Celery Beat ===${NC}"
    sudo systemctl status celery_beat --no-pager | head -n 10
    echo ""
}

restart_worker() {
    echo -e "${YELLOW}إعادة تشغيل Worker...${NC}"
    sudo systemctl restart celery_worker
    sleep 2
    sudo systemctl status celery_worker --no-pager | head -n 5
    echo -e "${GREEN}✓ تم${NC}"
}

restart_beat() {
    echo -e "${YELLOW}إعادة تشغيل Beat...${NC}"
    sudo systemctl restart celery_beat
    sleep 2
    sudo systemctl status celery_beat --no-pager | head -n 5
    echo -e "${GREEN}✓ تم${NC}"
}

restart_all() {
    echo -e "${YELLOW}إعادة تشغيل جميع الخدمات...${NC}"
    sudo systemctl restart celery_worker
    sudo systemctl restart celery_beat
    sleep 2
    check_status
    echo -e "${GREEN}✓ تم إعادة تشغيل جميع الخدمات${NC}"
}

stop_services() {
    echo -e "${YELLOW}إيقاف الخدمات...${NC}"
    sudo systemctl stop celery_worker
    sudo systemctl stop celery_beat
    echo -e "${GREEN}✓ تم إيقاف جميع الخدمات${NC}"
}

start_services() {
    echo -e "${YELLOW}بدء الخدمات...${NC}"
    sudo systemctl start celery_worker
    sudo systemctl start celery_beat
    sleep 2
    check_status
    echo -e "${GREEN}✓ تم بدء جميع الخدمات${NC}"
}

show_worker_logs() {
    echo -e "${YELLOW}عرض سجلات Worker (اضغط Ctrl+C للخروج)...${NC}"
    sleep 1
    sudo journalctl -u celery_worker -f
}

show_beat_logs() {
    echo -e "${YELLOW}عرض سجلات Beat (اضغط Ctrl+C للخروج)...${NC}"
    sleep 1
    sudo journalctl -u celery_beat -f
}

update_and_restart() {
    echo -e "${YELLOW}تحديث وإعادة تشغيل...${NC}"
    cd /var/www/shift_manager
    source venv/bin/activate
    git pull
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py collectstatic --noinput
    sudo systemctl restart celery_worker
    sudo systemctl restart celery_beat
    echo -e "${GREEN}✓ تم التحديث وإعادة التشغيل${NC}"
}

while true; do
    show_menu
    read choice
    
    case $choice in
        1) check_status ;;
        2) restart_worker ;;
        3) restart_beat ;;
        4) restart_all ;;
        5) stop_services ;;
        6) start_services ;;
        7) show_worker_logs ;;
        8) show_beat_logs ;;
        9) update_and_restart ;;
        0) echo "وداعاً!"; exit 0 ;;
        *) echo -e "${RED}خيار غير صحيح!${NC}" ;;
    esac
    
    echo ""
    echo -n "اضغط Enter للمتابعة..."
    read
done

