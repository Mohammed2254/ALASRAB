"""
عقدُ بوّابة CI — **إعدادٌ يُفحَص لا يُؤتمَن عليه**.

وُجد هذا الملفّ لأن أوّل تشغيلٍ حقيقيّ للبوّابة الخلفية سقط بـ**exit 4**:
الأمر `pytest` (السكربت) لا يضيف المجلّد الحاليّ إلى `sys.path`، فسقط تحميل
`conftest.py`. و`docs/HANDOFF.md` كان يوثّق `python -m pytest` و
`.github/workflows/ci.yml` يكتب `pytest` — **وثيقتان افترقتا، ولم يُشغَّل
اختبارٌ خلفيٌّ واحد في CI قطّ.** و«٤٨٨ نجحت» كانت محليّةً وحدها.

**ولا يكفي أن نُصلح الإعداد:** إعدادٌ صحيحٌ اليوم بلا فحصٍ يحرسه ينكسر غدًا
بسطرٍ يُحذف سهوًا، ويعود العمى. فهذه الفحوص تحرس **شكل البوّابة نفسها** —
وهي الطبقة التي لم يكن أحدٌ يحرسها.

@covers ق-٢٨٥, ق-٢٨٩, ق-٢٩٠, ق-٢٩٣, ق-٢٩٥, ق-٢٩٦
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
CI = REPO / ".github" / "workflows" / "ci.yml"


def _pytest_config() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["tool"]["pytest"]["ini_options"]


def test_pytest_adds_the_project_root_to_the_import_path():
    """
    **بدون هذا يفشل CI ولا ينجح.** `pytest` السكربت لا يضيف المجلّد الحاليّ
    إلى `sys.path` بخلاف `python -m pytest`، فـ`conftest.py` لا يجد `app`.
    و٤ **خطأُ استعمال** لا فشلُ اختبار — فلا يُقرَأ في التقرير كفشلٍ ولا
    يسمّي سببه، وهو ما جعل التشخيص يستغرق ثلاث محاولاتِ إعادةِ إنتاج.

    @covers ق-٢٨٥
    """
    assert "." in _pytest_config().get(
        "pythonpath", []
    ), "pythonpath مفقود — سيعمل `python -m pytest` محليًّا ويفشل `pytest` في CI"


def test_ci_runs_the_backend_suite_and_lints_it():
    """
    ثلاثُ خطواتٍ لا واحدة: اللنت والتهيئة والاختبارات. و`ruff` كان في
    `requirements.txt` منذ و-١ **ولا يُشغَّل في CI إطلاقًا** — فعاش خطأُ
    ترتيبِ استيرادٍ و١٥ ملفًّا غير مُهيَّأة بلا أن يُنبّه شيء.

    @covers ق-٢٨٩
    """
    ci = CI.read_text(encoding="utf-8")
    for step in ("ruff check", "ruff format --check", "pytest -q"):
        assert step in ci, f"خطوةُ «{step}» غائبةٌ عن CI"


def test_ci_runs_both_traceability_gates():
    """
    `ق` تقيس «هل اختبرتُ ما قلتُ إنّي سأختبره»، و`FR` تقيس «هل المنتج
    مكتمل». والأولى وحدها كانت تعمل، فـ«٢٧٥/٢٧٥ أخضر» قُرئ اكتمالًا.

    @covers ق-٢٨٩
    """
    ci = CI.read_text(encoding="utf-8")
    assert "check-slice-gate.sh" in ci
    assert "check-fr-gate.sh" in ci


def test_every_gate_script_is_wired_into_ci():
    """
    **بوّابةٌ مكتوبةٌ لا تُشغَّل ليست بوّابة** — درسٌ دُفع ثمنُه أربع مرّات في
    هذا المشروع. فأيُّ `check-*` يُضاف ولا يُوصَل بـCI يُسقط هذا الفحص.

    @covers ق-٢٨٩
    """
    ci = CI.read_text(encoding="utf-8")
    scripts = sorted(
        p.name
        for p in list((REPO / "scripts").glob("check-*.sh"))
        + list((REPO / "ui" / "scripts").glob("check-*.mjs"))
    )
    assert scripts, "لم يُعثر على بوّابةٍ واحدة — فحصٌ معطوبٌ لا نجاحٌ له"
    missing = [s for s in scripts if s not in ci]
    assert not missing, f"بوّابات غير موصولة بـCI: {missing}"


def test_deploy_skips_cleanly_without_a_configured_host():
    """
    إجراءُ نشرٍ يحمرّ في كل دفعة لأن هدفه غير موجود **يُعلّم القارئَ تجاهلَ
    الأحمر** — فلا تنفع بوّابةٌ حين تحمرّ لسببٍ حقيقيّ. وقد وقع فورًا: أوّل
    دفعةٍ بعد ربط GitHub أخضرّ فيها CI وحمرّ Deploy بلا سبب يملكه أحد.

    @covers ق-٢٩٠
    """
    deploy = (REPO / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "DEPLOY_HOST" in deploy
    # حرسٌ يُخرج `ready` ويشترطه كلُّ ما بعده — لا `exit 1` عند الغياب.
    assert "ready=false" in deploy
    assert deploy.count("steps.gate.outputs.ready == 'true'") >= 3


# ═══ و-٢٢ — مراجعُ الوثائق تُحرَس آليًّا (ق-٢٩٤) ═══


def _doc_sections(md: Path) -> set[str]:
    """أرقامُ الأقسام المعلَنة في وثيقةٍ — `## ٣. اسم` ⇒ `٣`."""
    import re

    return set(re.findall(r"^## ([٠-٩]+)\. ", md.read_text(encoding="utf-8"), re.M))


def test_no_document_cites_a_section_that_does_not_exist():
    """
    **المشكلةُ ليست المرجعَ الكاذب بل غيابُ من يحرسه.**

    `TRACEABILITY.md` تعفّنت شهرًا وهي تقول إن مسار `FR-004` هو
    `PATCH /admin/teams`. ثمّ وقعتُ في النظير بنفسي: نقلتُ `§٧` و`§٨` من
    `ARCHITECTURE.md` إلى `SECURITY.md` و`OPERATIONS.md`، **فصار أربعةَ عشرَ
    مرجعًا في الكود والوثائق يشير إلى أقسامٍ لم تبقَ**.

    فهذا الفحص يمشي على كل استشهادٍ بـ`§N` في وثيقةٍ من وثائق التصميم،
    ويؤكّد أن القسم موجودٌ فيها فعلًا. وإعادةُ ترقيمٍ أو نقلُ قسمٍ تُسقطه.

    @covers ق-٢٩٤
    """
    import re

    design = REPO / "docs" / "design"
    known = {p.name: _doc_sections(p) for p in design.glob("*.md")}
    assert known, "لم يُعثر على وثيقةِ تصميمٍ واحدة — فحصٌ معطوبٌ لا نجاحٌ له"

    cite = re.compile(r"`?(?P<doc>[A-Z]+)(?:\.md)?`?\s*§(?P<sec>[٠-٩]+)")
    broken = []
    for p in REPO.rglob("*"):
        if p.suffix not in {".md", ".py", ".ts", ".tsx", ".mjs", ".sh", ".yml"}:
            continue
        if any(x in p.parts for x in ("node_modules", ".venv", ".git", "dist", "archive")):
            continue
        for m in cite.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            name = f"{m.group('doc')}.md"
            if name not in known:
                continue
            # وثيقةٌ تستشهد بنفسها: الترقيمُ الداخليّ محفوظٌ عن قصد في
            # `SECURITY.md`، فلا تُحسَب إشاراتُها إلى `٧.x` خارجَ أقسامها.
            if p.name == name:
                continue
            if m.group("sec") not in known[name]:
                broken.append(f"{p.relative_to(REPO)} → {name} §{m.group('sec')}")

    assert not broken, "مراجعُ أقسامٍ لا وجود لها:\n  " + "\n  ".join(sorted(set(broken)))


def test_ci_scans_dependencies_and_secrets():
    """
    كان صفرًا حتى و-٢٢. وأوّلُ تشغيلٍ كشف **خمس ثغرات** في المثبَّت — منها
    ترويسةُ `Vary: Cookie` الساقطة في Flask ٣.١.٠، ونحن نعتمد كوكي الجلسة.

    و**التشديدُ على الإنتاج وحده** (`requirements.txt`) مقصود: ثغرةٌ في
    `pytest` لا تصل مستخدمًا، وإفشالُ البناء عليها يُدرَّب على تجاهله فتضيع
    قيمةُ الفحص. ولذلك فُصل `requirements-dev.txt` — وكان `pytest` و`ruff`
    في ملفّ الإنتاج أي **يُشحنان إلى الصورة**.

    @covers ق-٢٩٣
    """
    ci = CI.read_text(encoding="utf-8")
    assert "pip-audit" in ci
    assert "npm audit" in ci
    assert "gitleaks" in ci
    assert "requirements.txt" in ci

    # **الاعتمادياتُ لا التعاليق.** أوّلُ صياغةٍ لهذا الفحص قرأت الملفّ
    # كاملًا فأمسكت تعليقي الذي *يشرح* نقلَ `pytest` و`ruff` — فحصٌ يفشل
    # على توثيق إصلاحه.
    def _names(f: str) -> set[str]:
        out = set()
        for line in (ROOT / f).read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line and not line.startswith("-r"):
                out.add(line.split("==")[0].split("[")[0].strip().lower())
        return out

    prod = _names("requirements.txt")
    for tool in ("pytest", "ruff", "pip-audit"):
        assert tool not in prod, f"{tool} في اعتماديات الإنتاج — يُشحن إلى الصورة"
    assert {"pytest", "ruff"} <= _names("requirements-dev.txt")


def test_every_archived_document_carries_the_history_header():
    """
    **الأرشيفُ تاريخٌ، والقارئُ يجب أن يعرف ذلك من أوّل سطر.**

    ٦٢٣٦ سطرًا من وثائق شرائحَ مغلقة نُقلت إلى `docs/archive/slices/` في
    و-٢٢، لأن بقاءها في مسار القراءة يجعلها تُقرَأ كأنها حاضر — ووقع بي ذلك
    في و-٢١: قرأتُ «لا مسار إنشاء إداريّ للسؤال» في `و-٩` فحسبتُها حاضرة،
    وكانت صحيحةً حين كُتبت.

    **وأوّلُ صياغةٍ لهذا الفحص كانت خاطئة:** منعتُ وثائقَ الحاضر من
    الاستشهاد بالأرشيف، فأسقطت ثلاثةَ عشرَ استشهادًا **مشروعًا كلَّها** —
    وثيقةُ تصميمٍ تنصّ قاعدةً وتُحيل إلى مسوّغها التاريخيّ تفعل ما تفعله
    ADRs بالضبط. وبوّابةٌ تمنع ممارسةً صحيحة يُحتال عليها (درسُ `3.0` في
    بوّابة AST).

    فالحرسُ الصحيح على **العلاج** لا على الاستشهاد: كلُّ ملفٍّ في الأرشيف
    يحمل ترويسةً تقول إنه تاريخ. وملفٌّ يُضاف بلا ترويسة يُسقط هذا الفحص.

    @covers ق-٢٩٥
    """
    archive = REPO / "docs" / "archive" / "slices"
    docs = sorted(archive.glob("*.md"))
    assert len(docs) >= 20, f"استُخرج {len(docs)} وثيقةً — فحصٌ معطوبٌ لا نجاحٌ له"

    bare = [
        p.name for p in docs if "لا يُستشهد به كحاضر" not in p.read_text(encoding="utf-8")[:1200]
    ]
    assert not bare, "وثائقُ أرشيفٍ بلا ترويسة التاريخ:\n  " + "\n  ".join(bare)


def test_schemas_package_has_no_re_export_barrel():
    """
    **وُجد هذا الفحص لأن الـbarrel عاد مرّةً سيعود مرّاتٍ.**

    كان `app/schemas/__init__.py` ١٩٨ سطرًا يُعيد تصدير ٨٨ اسمًا لثلاثة
    ملفّاتٍ فقط، و**أكثرَ ملفٍّ تغيُّرًا في المستودع: ١٧ دفعةً من ١١٢** —
    لأن كلَّ ميزةٍ تلمسه مرّتين (استيرادًا و`__all__`). وفيه عطلٌ كامن:
    `"StationTaskSchema"` في `__all__` بلا استيرادٍ يقابله، فأيُّ `import *`
    ينكسر.

    وإضافةُ استيرادٍ واحدٍ «للتسهيل» هي بداية عودته — فالحرسُ على البنية لا
    على النيّة: الحزمةُ تبقى بلا تصديرٍ مُسطَّح، والاستيرادُ من الوحدة
    (`from ..schemas.roster import …`).

    @covers ق-٢٩٦
    """
    import app.schemas as pkg

    assert not hasattr(pkg, "__all__"), "عاد `__all__` إلى حزمة المخططات"
    leaked = [n for n in dir(pkg) if n.endswith("Schema") and not n.startswith("_")]
    assert not leaked, "أسماءٌ مُسطَّحة في `app.schemas` — الـbarrel يعود:\n  " + "\n  ".join(leaked)
