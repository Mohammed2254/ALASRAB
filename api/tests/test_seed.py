"""
بذرة التطوير — و-١٢.

**حدُّ هذا الملفّ معلَنٌ صراحةً:** يفحص ما **تُعلنه** البذرة، لا ما تُنتجه على
قاعدةٍ حيّة. و`seed.run()` يكتب على قاعدة التطوير (`DATABASE_URL`) لا على
قاعدة الاختبار، فاستدعاؤه من pytest يمسح قاعدة المطوّر تحت قدميه — ثمنٌ لا
يبرّره فحصٌ يمكن أداؤه على الإعلان.

وما تُنتجه فعلًا **قِيس حيًّا** بتشغيل البذرة على قاعدة التطوير واستعلامها
(و-١٢، سجلّ التقدّم، نقطة تفتيش ٣): ٨ أوزان · نشاط وقود ببنوده الخمسة وتقييمه
· ٥ درجات بنود · سؤال يوميّ · ملاحظة · طيار أسبوع · تحضيران · ٢٠.٢٦ لترًا
مشتقّة من البنود الموزونة.

**ولماذا الإعلان يكفي حارسًا؟** لأن الفجوة التي أوجدت هذه الوحدة كانت فجوة
إعلان لا فجوة تنفيذ: `WEIGHTS` لم تكن تحوي `tahdir` إطلاقًا، فكان كل اعتماد
تحضير يسقط بـ٤٢٢ على كل قاعدة نظيفة. والسلوك نفسه (اعتمادٌ ينجح بوزنٍ سارٍ)
مملوكٌ سلفًا في `test_tahdir.py`.
"""

from decimal import Decimal
from pathlib import Path

import seed

SEED_SOURCE = Path(seed.__file__).read_text()


def test_seed_declares_the_tahdir_weight():
    """
    @covers ق-٢٠٥

    بدونه: `hours_for()` ترفض بـ«لا وزن سارٍ» فيسقط اعتماد أي تحضير بـ٤٢٢ —
    شاشتا و-١١ مبنيّتان ومعطَّلتان معًا على كل قاعدة تطوير جديدة.
    """
    assert "tahdir" in dict(seed.WEIGHTS)


def test_seed_declares_the_three_rasd_quran_categories():
    """
    @covers ق-٢٠٦

    `ENTRY_DEFAULTS` تُنشئ مفاتيح الفئات الثلاث للترويسة، فاستيراد راصد يقرؤها
    ثم **يتخطّاها بصمت** إن لم يكن لها وزن — مفاتيحٌ بلا أوزان أسوأ من غيابهما
    لأنها تُوهم بالاكتمال.
    """
    declared = dict(seed.WEIGHTS)
    assert {"quran_hifz", "quran_thabat", "quran_muraja3a"} <= set(declared)


def test_every_entry_default_category_has_a_weight():
    """
    @covers ق-٢٠٦

    الضلع الآخر، ومقاوم للتوسيع: أي فئة قرآنية تُضاف إلى `ENTRY_DEFAULTS` غدًا
    بلا وزن يُسقط هذا الاختبار — بدل أن تتخطّاها عملية الاستيراد صامتةً.
    """
    weights = set(dict(seed.WEIGHTS))
    quran_categories = {
        activity
        for activity, _label in seed.ENTRY_DEFAULTS
        if activity.startswith("quran_") and activity.endswith("_achieved")
    }
    missing = {c.removesuffix("_achieved") for c in quran_categories} - weights
    assert not missing, f"فئات راصد بلا وزن: {sorted(missing)}"


def test_seed_fuel_criteria_sum_to_exactly_100():
    """
    @covers ق-٢٠٧

    ث-١٠أ يرفض أي مجموع غير ١٠٠٪ في الخدمة **وفي القاعدة** — فبذرةٌ بأوزان
    خاطئة لا تُنتج نشاطًا معطوبًا بل **تُسقط البذرة كلّها**، وتترك المطوّر بقاعدة
    نصف مبذورة. فحصُها هنا يكشفها قبل التشغيل لا بعده.
    """
    total = sum(c["weight_pct"] for c in seed.FUEL_ACTIVITY["criteria"])
    assert total == Decimal("100")


def test_seed_question_answer_is_among_its_choices():
    """
    @covers ق-٢٠٨

    `correct_id` عمودٌ حرّ لا مفتاح أجنبيّ على الخيارات (الخيارات JSONB بقصد)،
    فسؤالٌ صحيحه ليس من خياراته يُعرَض بلا إجابة صحيحة ممكنة — والقاعدة لا
    تمنعه. وشرحُه إلزاميّ لأن FR-060 يوجب ظهوره في الحالتين.
    """
    assert seed.QUESTION["correct_id"] in {c["id"] for c in seed.QUESTION["choices"]}
    assert seed.QUESTION["note"].strip()


def test_seed_never_writes_a_delta_it_did_not_derive():
    """
    @covers ق-٢٠٩

    الدرس ٧: بذرةٌ تكتب `delta` رقمًا تتجاوز `rules/engine` — أي تتجاوز القاعدة
    التي وُجد المشروع لأجلها، وتترك المحرّك كودًا لا يستدعيه أحد.

    فحصٌ نصّيّ لا AST: المطلوب منع **كتابة رقم** في موضع `delta`، وكل `delta=`
    في البذرة يجب أن تكون قيمتها اسمًا مشتقًّا من المحرّك (`hours`).
    """
    assignments = [
        line.split("delta=", 1)[1].split(",")[0].strip()
        for line in SEED_SOURCE.splitlines()
        if "delta=" in line
    ]
    assert assignments, "لم يُعثر على أي `delta=` — الفحص معطوب لا ناجح (حارس الدرس ٥)."
    assert all(value == "hours" for value in assignments), assignments
