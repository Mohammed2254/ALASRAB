# صورة واحدة — NFR-09. مرحلتان لا حاويتان: `node` يبني `ui/` الساكنة،
# و`python` يشغّل `api/` عبر gunicorn ويخدم الناتج من الأصل نفسه
# (`ui/vite.config.ts` علّق على هذا صراحةً منذ و-١٣ — أصلٌ واحد في الإنتاج،
# فلا CORS ولا حاوية Nginx ثانية تخدم الساكن وحده).

FROM node:22-slim AS ui-build
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

# `psycopg[binary]` يحتاج مكتبات pq وقت التشغيل لا وقت البناء فقط على بعض
# الصور المصغَّرة — تثبيتها هنا صراحةً بدل الاعتماد على العجلة المضمَّنة.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# **الإنتاج وحده** — `requirements-dev.txt` لا يُنسَخ ولا يُثبَّت. وكان
# `pytest` و`ruff` في هذا الملفّ حتى و-٢٢، أي يُشحنان إلى الصورة: أدواتُ
# تطويرٍ على خادمٍ حيّ سطحُ هجومٍ بلا مقابل.
# و`constraints.txt` معه: بلاه يُثبّت المنقولُ أحدثَ ما يجده **وقت البناء**،
# فصورتان من نفس الدفعة تحملان شجرتين مختلفتين. وأظهرُ ما يمسّ: `alembic`
# يُشغّل الهجرات.
COPY api/requirements.txt api/constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY api/ ./
# الساكن يُنسَخ إلى مكان `static_folder` الافتراضيّ لفلاسك — بلا تجاوز
# المسار في الكود (`app/__init__.py` يضبط `static_url_path=""` فقط).
COPY --from=ui-build /ui/dist/ ./app/static/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# **مستخدمٌ غير جذر** (و-٢١): ثغرةُ تنفيذٍ في التطبيق تصير جذرًا داخل
# الحاوية افتراضًا، ومنها الهروب أقرب. والملفّات تبقى للجذر ملكًا —
# التطبيق يقرؤها ولا يحتاج كتابتها، وهذا مقصود.
RUN useradd --system --no-create-home --uid 10001 asrab
USER asrab

EXPOSE 8000

# **فحصُ صحّةٍ في الصورة نفسها** لا في `compose` وحده: منصّةٌ تشغّل الصورة
# بلا `compose` (Render · Cloud Run) تحتاجه معها. ويلمس القاعدة فعلًا، فخادمٌ
# يردّ ٢٠٠ وقاعدته ساقطة لا يُعَدّ سليمًا.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+__import__('os').environ.get('PORT','8000')+'/health',timeout=4).status==200 else 1)"

# `$PORT` لا ٥٠٥٥ مثبَّتة — أغلب منصّات الاستضافة تُملي المنفذ.
#
# وكل معامل أدناه يمنع عطلًا بعينه، لا تزيينًا:
#
# · `--timeout 60` — عاملٌ معلَّق على استعلامٍ لا ينتهي يُقتَل ويُستبدَل.
#   بلا هذا يبتلع العاملان الطلباتَ ويصمت الخادم بلا أن يسقط.
# · `--graceful-timeout 30` — يُنهي الطلب الجاري قبل القتل عند إعادة النشر،
#   فلا تُقطَع كتابةٌ في منتصفها.
# · `--max-requests 1000` + `jitter` — إعادةُ تدوير العامل تمنع تسرّبًا
#   بطيئًا للذاكرة من التراكم أسابيع. والـ`jitter` يمنع تدوير العاملين معًا.
# · `--worker-tmp-dir /dev/shm` — دليل gunicorn المؤقّت يُكتَب في كل نبضة
#   عامل؛ على قرصٍ شبكيّ يُنتج مهلاتٍ كاذبة. والذاكرة هي مكانه الصحيح.
# · `--forwarded-allow-ips` — خلف Caddy وحده، فيُصدَّق `X-Forwarded-*`.
# · السجلّات إلى `stdout` — تلتقطها المنصّة (ARCHITECTURE §٨)، وتدويرُها في
#   `docker-compose.prod.yml`.
# · `WEB_CONCURRENCY` من البيئة بافتراض ٢: كافٍ لمئتَي مستخدم، ويُرفَع بلا بناء.
CMD ["sh", "-c", "exec gunicorn 'app:create_app()' \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout 60 \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --worker-tmp-dir /dev/shm \
    --forwarded-allow-ips '*' \
    --access-logfile - \
    --error-logfile - \
    --capture-output"]
