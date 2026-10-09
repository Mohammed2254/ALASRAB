"""
صفُّ حدثٍ من الدفتر — **شكلٌ واحدٌ يراه الطالب والمشرف**.

كان مكرَّرًا حرفيًّا: `me.EventSchema` (سجلُّ الطالب · FR-012) و
`quran.QuranEventRowSchema` (اختيارُ المشرف حدثًا ليُصحّحه · FR-035). ونفسُ
الصفّ في الحالتين — صفٌّ من `point_events` — فاختلافُ من ينظر إليه لا يُغيّر
شكلَه.

وأثرُ افتراقهما لو وقع: حقلٌ يُضاف لأحدهما فيرى المشرفُ ما لا يراه الطالب من
**نفس الحدث** — فيبلّغ عن عطلٍ ليس عطلًا.

**وما لم يُدمَج وإن تشابه** (قرارُ و-٢٢):

· `fuel.CriterionOutSchema` و`fuel.CreatedActivitySchema` — يبدوان متطابقَين
  (`id` وحده) و**ليسا كذلك**: الأوّل يرث `CriterionRowSchema` فيحمل المفتاحَ
  والاسمَ والوزن. تشابهٌ في جسم الصنف لا في حقوله.
· `quran.ReverseEventSchema` و`reading.RejectSchema` — نفسُ التحقّق
  (`reason` إلزاميّ ١..٥٠٠) و**قيدان مختلفان في القاعدة**: ث-٧ الموسَّعة
  مقابل ث-٦. ودمجُهما يُخفي أيُّ ثابتٍ يحرس أيَّ مسار، وتعليقُ كلٍّ منهما
  يُحيل إلى الآخر عن قصد.
"""

from marshmallow import Schema, fields


class EventRowSchema(Schema):
    id = fields.Int()
    occurred_on = fields.Date()
    delta = fields.Decimal(as_string=True)
    kind = fields.Str()
    reason = fields.Str(allow_none=True)


class EventRefSchema(Schema):
    """
    الحدثُ الناتج عن كتابةٍ في الدفتر — عكسٌ أو إضافة.

    كان `quran.ReversedEventSchema` و`quran.AddedQuranEntrySchema` في الملفّ
    نفسه بنفس الحقول الثلاثة. والمعنى واحد: «هذا ما كُتب».
    """

    id = fields.Int()
    delta = fields.Decimal(as_string=True)
    kind = fields.Str()
