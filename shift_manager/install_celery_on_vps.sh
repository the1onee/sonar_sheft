#!/bin/bash

echo "=========================================="
echo "تثبيت Celery على VPS"
echo "=========================================="
echo ""

# ألوان للطباعة
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# المسارات (عدّل هذه حسب خادمك)
PROJECT_DIR="/var/www/shift_manager"
VENV_DIR="$PROJECT_DIR/venv"
USER="www-data"
GROUP="www-data"

echo -e "${YELLOW}[1/7] إنشاء مجلدات السجلات...${NC}"
sudo mkdir -p /var/log/celery
sudo mkdir -p /var/run/celery
sudo chown $USER:$GROUP /var/log/celery
sudo chown $USER:$GROUP /var/run/celery
echo -e "${GREEN}✓ تم${NC}"
echo ""

echo -e "${YELLOW}[2/7] نسخ ملفات systemd...${NC}"
sudo cp $PROJECT_DIR/celery_worker.service /etc/systemd/system/
sudo cp $PROJECT_DIR/celery_beat.service /etc/systemd/system/
echo -e "${GREEN}✓ تم${NC}"
echo ""

echo -e "${YELLOW}[3/7] إعادة تحميل systemd...${NC}"
sudo systemctl daemon-reload
echo -e "${GREEN}✓ تم${NC}"
echo ""

echo -e "${YELLOW}[4/7] تفعيل خدمات Celery للتشغيل التلقائي...${NC}"
sudo systemctl enable celery_worker
sudo systemctl enable celery_beat
echo -e "${GREEN}✓ تم${NC}"
echo ""

echo -e "${YELLOW}[5/7] بدء خدمة Celery Worker...${NC}"
sudo systemctl start celery_worker
sleep 2
sudo systemctl status celery_worker --no-pager
echo -e "${GREEN}✓ تم${NC}"
echo ""

echo -e "${YELLOW}[6/7] بدء خدمة Celery Beat...${NC}"
sudo systemctl start celery_beat
sleep 2
sudo systemctl status celery_beat --no-pager
echo -e "${GREEN}✓ تم${NC}"
echo ""

echo -e "${YELLOW}[7/7] فحص حالة الخدمات...${NC}"
if sudo systemctl is-active --quiet celery_worker && sudo systemctl is-active --quiet celery_beat; then
    echo -e "${GREEN}✓ جميع الخدمات تعمل بنجاح!${NC}"
else
    echo -e "${RED}⚠ هناك مشكلة في إحدى الخدمات${NC}"
fi
echo ""

echo "=========================================="
echo "الأوامر المتاحة:"
echo "=========================================="
echo "• فحص حالة Worker:   sudo systemctl status celery_worker"
echo "• فحص حالة Beat:      sudo systemctl status celery_beat"
echo "• إعادة تشغيل Worker: sudo systemctl restart celery_worker"
echo "• إعادة تشغيل Beat:   sudo systemctl restart celery_beat"
echo "• إيقاف Worker:       sudo systemctl stop celery_worker"
echo "• إيقاف Beat:         sudo systemctl stop celery_beat"
echo "• عرض السجلات:        sudo journalctl -u celery_worker -f"
echo "=========================================="

