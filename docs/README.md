# الوثائق

| الملفّ | ماذا فيه | المرحلة |
|---|---|:--:|
| [product/SCOPE.md](product/SCOPE.md) | **المصدر الأول للحقيقة** — ما نبنيه ولماذا · ٤١ متطلَّبًا · الافتراضات · المخاطر | ٢ |
| [design/ARCHITECTURE.md](design/ARCHITECTURE.md) | الوحدات · **مصفوفة الملكية** · الاعتماديات · الأمان · **بوابات Stage 4** | ٣ |
| [design/DATABASE.md](design/DATABASE.md) | ٢٤ جدولًا بغرض مكتوب · ERD · ٨ فهارس · ١٥ ثابتًا | ٣ |
| [design/RULES.md](design/RULES.md) | المحرّك · المعايرة · حدّ الاستيعاب · قاعدة «أرضي» | ٣ |
| [design/API.md](design/API.md) | ٣٥ endpoint + مسارات بنيوية | ٣ |
| [design/TRACEABILITY.md](design/TRACEABILITY.md) | **٤١ متطلَّبًا ← وحدة ← جدول ← ثابت ← اختبار** | ٣ |
| [plans/SLICE-01.md](plans/SLICE-01.md) | **و-١ الشريحة الرأسية** — مغلقة · ١٦/١٦ | ٤ |
| [slices/و-٤.md](slices/و-٤.md) | **و-٤ القراءة** — خطّة معتمدة · ق-١٧..٢٦ | ٤ |
| [design/VISUAL.md](design/VISUAL.md) | «المدرّج والشارة» · الألوان · الخطوط · الناقص | ٣ |
| [decisions/](decisions/) | خمسة ADRs | — |

## القرارات

| ADR | العنوان | لماذا يهمّ |
|---|---|---|
| [٠٠١](decisions/ADR-001-event-log.md) | سجلّ أحداث لا أعمدة أرصدة | يجعل التدقيق والتصحيح وإعادة الحساب مجّانية |
| [٠٠٢](decisions/ADR-002-db-constraint.md) | القيد المركزي في القاعدة لا في الكود | يجعل خلط العملتين **مستحيلًا** لا ممنوعًا |
| [٠٠٣](decisions/ADR-003-db-sessions.md) | جلسات في القاعدة لا JWT | طالب ضاع جواله يُخرَج **الآن** |
| [٠٠٤](decisions/ADR-004-rasd-source-manual-exception.md) | **راصد قاعدة · اليدوي استثناء** | ⭐ يحسم ما أوقف البناء الأول |
| [٠٠٥](decisions/ADR-005-defer-measurement-unit.md) | تأجيل وحدة القياس | يمضي البناء بلا انتظار عيّنة راصد |
| [٠٠٦](decisions/ADR-006-cookie-auth-csrf.md) | **CSRF — ما ترتّب على الكوكي** | فجوة في ADR-003 كشفتها البوابات |

## ترتيب القراءة
لفهم المنتج: `SCOPE.md` → `ADR-004`.
للبناء: `TRACEABILITY.md` → `ARCHITECTURE.md` → `DATABASE.md` → `RULES.md` → `API.md` → `SLICE-01.md`.
