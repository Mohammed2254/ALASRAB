# النشر — دليل عمليّ

> يفترض هذا الدليل أنك اتّبعته بنفسك على خادمك — لا أحد يملك بيانات اعتمادك
> السحابية هنا. كل أمر أدناه اختُبر شكله محليًّا (`docker-compose.yml`،
> `docs/slices/و-١٩.md` نقطة تفتيش ٢)، لكن التشغيل الفعليّ على خادم حقيقيّ
> لم يحدث بعد — **جرّبه على نطاق ضيّق (طالبَين-ثلاثة) قبل الإعلان للجميع**.

## ١. اختر المنصّة

| | التكلفة | السهولة | الملاحظة |
|---|---|---|---|
| **Oracle Cloud Always Free** (موصى به أوّلًا) | **مجانًا للأبد** | متوسطة — تسجيل الحصول على خادم ARM قد يحتاج إعادة محاولة (خطأ "out of host capacity" شائع، يزول بالمحاولة على فترات) | ٢ OCPU / ١٢GB RAM كافية جدًّا لـ٢٠٠ مستخدم |
| **Hetzner Cloud** (بديل فوريّ) | **~€٥/شهر** | فورية، بلا تعقيد | CX23 (2vCPU/4GB) كافٍ بفائض |

كلاهما يُدار بنفس الطريقة أدناه بالضبط — لا فرق في الخطوات بعد الحصول على
الخادم.

## ٢. جهّز الخادم (مرّة واحدة)

على خادم Ubuntu جديد (أيّ توزيعة حديثة تصلح):

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # ثمّ أعد تسجيل الدخول للجلسة
```

## ٣. انقل الكود إلى الخادم

**لا `git clone` بعد** — لا remote للمستودع حتى اليوم. مؤقّتًا:

```bash
# من جهازك، لا من الخادم:
rsync -avz --exclude node_modules --exclude .venv --exclude .git \
  /home/mohammed/projects/asrab-v2/ user@YOUR_SERVER_IP:~/asrab-v2/
```

حين يُربَط المستودع بمنصّة استضافة كود لاحقًا، `git clone`/`git pull`
يستبدل هذا فورًا بلا تغيير في أيّ شيء آخر.

## ٤. اضبط أسرار الإنتاج

على الخادم، داخل `~/asrab-v2/`:

```bash
cat > .env.prod << 'EOF'
DB_PASSWORD=CHANGE_ME_TO_SOMETHING_LONG_AND_RANDOM
SECRET_KEY=CHANGE_ME_TOO
DOMAIN=your-domain.example.com
EOF
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # للصق في SECRET_KEY
```

**لا يُلمَس `docker-compose.prod.yml` نفسه أبدًا لوضع سرّ فيه** — كل قيمة
من `.env.prod` وحده (`NFR-09`)، وهو مُستبعَد من Git تلقائيًّا (`.gitignore`).

## ٥. اختر طبقة HTTPS

تسجيل الدخول يستعمل كوكي `Secure` — لا يعمل بلا HTTPS حقيقيّ. خياران في
`docker-compose.prod.yml`، **فعِّل واحدًا فقط**:

### أ. عندك نطاق (يشير سجلّ A فيه لعنوان الخادم)
`caddy` مفعَّلة افتراضيًّا في الملفّ — لا شيء آخر مطلوب، تصدر الشهادة
تلقائيًّا عند أوّل تشغيل.

### ب. بلا نطاق بعد — رابط فوريّ من Cloudflare
عطِّل خدمة `caddy` (بتعليقها) وفعِّل `cloudflared` بدلها في
`docker-compose.prod.yml`، ثمّ:

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs cloudflared | grep trycloudflare
```

يعطيك رابطًا مثل `https://random-words.trycloudflare.com` — HTTPS حقيقيّ،
بلا نطاق وبلا منفذ داخليّ مفتوح على الخادم إطلاقًا (اتصالٌ صادرٌ فقط).
**الرابط يتغيّر كل إعادة تشغيل** — مناسبٌ لتجربة أوّلية لا للإعلان الدائم.

## ٦. شغّل كل شيء

```bash
cd ~/asrab-v2
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm app flask db upgrade
```

الهجرة **يدويّة دائمًا** — لا تُشغَّل تلقائيًّا عند إعادة تشغيل الحاوية
(`ARCHITECTURE.md` §٨). بعدها افتح الرابط، وسجّل دخولًا أوّل مرّة عبر شاشة
المشرف — **لا بذرة تجريبية هنا** (`seed.py` بيانات وهمية للتطوير وحده)؛
إنشاء المنظمة والطلاب الحقيقيين يقع عبر شاشات المشرف نفسها بعد أوّل نشر.

## ٧. التحديث لاحقًا

```bash
# من جهازك:
rsync -avz --exclude node_modules --exclude .venv --exclude .git \
  /home/mohammed/projects/asrab-v2/ user@YOUR_SERVER_IP:~/asrab-v2/
# على الخادم:
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
# فقط إن أضافت الدفعة هجرة جديدة:
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm app flask db upgrade
```

## ٨. النسخ الاحتياطي

`ARCHITECTURE.md` §٨: "نسخة القاعدة من المنصّة المستضيفة" — لا آلية نسخ
احتياطي مبنيّة هنا. أدنى حدّ معقول يدويًّا إلى حين قرار أفضل:

```bash
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U asrab asrab_v2 | gzip > backup-$(date +%F).sql.gz
```
