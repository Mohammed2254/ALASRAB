"""
أوامر الطرفية — **مدخل التأسيس الوحيد في الإنتاج** (و-٢١).

قبل هذا الملفّ لم يكن في المشروع أمرُ CLI واحد (`grep "cli.command"` ⇒ صفر)،
وكان الكاتب الوحيد لـ`Org` و`User` هو `seed.py` — وهو يرفض الإنتاج صراحةً.
فقاعدةٌ منشورة جديدة كانت **بلا أيّ طريق** إلى جمعية أو مشرف.

**ولماذا أمرُ طرفية لا شاشةُ تسجيل:** مسارٌ عامّ يُنشئ جمعيةً ومشرفًا هو
بابٌ لمن يسبق صاحب الخادم إليه. والطرفية داخل الحاوية صلاحيتُها هي صلاحية
الخادم نفسه — فلا سطح هجوم جديد إطلاقًا.

وهذه الطبقة **HTTP-free ومنطق-free**: تقرأ المدخلات وتطبع الناتج، والعمل
كلّه في `services/provision.py`.
"""

import click
from flask import Flask

from .services import provision


def register_cli(app: Flask) -> None:
    @app.cli.command("bootstrap-org")
    @click.option("--name", prompt="اسم الجمعية", help="اسم الجمعية كما يظهر للمشرف.")
    @click.option("--timezone", default="Asia/Riyadh", show_default=True)
    @click.option("--team-name", prompt="اسم أوّل سرب", default="السرب الأول")
    @click.option("--team-code", prompt="رمز أوّل سرب", default="SQ1")
    @click.option("--admin-name", prompt="اسم المشرف")
    @click.option("--admin-no", prompt="رقم المشرف (به يدخل)")
    @click.option(
        "--admin-pin",
        default=None,
        help="رمزٌ من أربعة أرقام. اتركه فيولّده الخادم — وهو الأفضل.",
    )
    def bootstrap_org(name, timezone, team_name, team_code, admin_name, admin_no, admin_pin):
        """تأسيس جمعية جديدة وأوّل مشرف — على قاعدة فارغة وحدها."""
        try:
            org, team, admin, pin = provision.bootstrap(
                name=name,
                timezone=timezone,
                team_name=team_name,
                team_code=team_code,
                admin_name=admin_name,
                admin_student_no=admin_no,
                admin_pin=admin_pin,
            )
        except provision.ProvisionError as exc:
            # `ClickException` لا `raise`: أثرُ تنفيذٍ بايثونيّ في وجه من ينشر
            # لأوّل مرّة يبدو عطلًا، والرسالة هي كل ما يحتاجه.
            raise click.ClickException(str(exc)) from exc

        click.echo(f"\n✅ الجمعية «{org.name}» (#{org.id}) · السرب «{team.name}» (#{team.id})")
        click.echo(f"   المشرف: {admin.full_name} — رقم الدخول {admin.student_no}")
        click.echo(f"   الرمز:  {pin}")
        click.echo("\n   ⚠️  هذا الرمز **لا يُعرض مرّةً أخرى** — ولا يُخزَّن نصًّا.")
        click.echo("       إن فُقد، أعِد تعيينه من شاشة الطلاب بمشرفٍ آخر.\n")
