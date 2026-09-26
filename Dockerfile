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

COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./
# الساكن يُنسَخ إلى مكان `static_folder` الافتراضيّ لفلاسك — بلا تجاوز
# المسار في الكود (`app/__init__.py` يضبط `static_url_path=""` فقط).
COPY --from=ui-build /ui/dist/ ./app/static/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
# `$PORT` لا ٥٠٥٥ مثبَّتة — أغلب منصّات الاستضافة تُملي المنفذ (المرحلة ب).
# محليًّا (`docker-compose.yml`) تُضبَط PORT=8000 صراحةً.
CMD ["sh", "-c", "gunicorn 'app:create_app()' --bind 0.0.0.0:${PORT:-8000} --workers 2"]
