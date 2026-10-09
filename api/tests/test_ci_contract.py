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

@covers ق-٢٨٥, ق-٢٨٩, ق-٢٩٠
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
