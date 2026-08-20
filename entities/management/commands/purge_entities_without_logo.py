from django.core.management.base import BaseCommand
from django.db.models import ProtectedError
from entities.models import BusinessEntity


class Command(BaseCommand):
    help = "يحذف كل الجهات اللي ما عندها شعار (logo فاضي). آمن افتراضيًا: يعرض بس عدد وأسماء اللي بينحذفوا بدون تنفيذ فعلي، إلا لو مرّرت --yes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="تنفيذ الحذف فعليًا. بدونها، الأمر يعرض بس معاينة (dry-run) بدون أي حذف حقيقي.",
        )

    def handle(self, *args, **opts):
        confirm = opts["yes"]

        # نلقط الحالتين الممكنتين لـ "بدون شعار": فاضي بسلسلة نص أو NULL
        no_logo = [e for e in BusinessEntity.objects.all() if not e.logo]

        if not no_logo:
            self.stdout.write(self.style.SUCCESS("لا توجد أي جهة بدون شعار — ما فيه شي يُحذف."))
            return

        self.stdout.write(f"لقيت {len(no_logo)} جهة بدون شعار.")

        if not confirm:
            self.stdout.write(self.style.WARNING("هذا وضع معاينة فقط (dry-run) — ما انحذف أي شيء فعليًا."))
            self.stdout.write("عيّنة من أول 15 اسم:")
            for e in no_logo[:15]:
                self.stdout.write(f"  - {e.name}")
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("لتنفيذ الحذف فعليًا، أعد تشغيل الأمر مع --yes"))
            return

        deleted_count = 0
        skipped_protected = []

        for entity in no_logo:
            try:
                name = entity.name
                entity.delete()
                deleted_count += 1
            except ProtectedError:
                # عندها منتجات مرتبطة — الحذف يكسر سلامة البيانات، نتخطاها
                skipped_protected.append(name)

        self.stdout.write(self.style.SUCCESS(f"تم حذف {deleted_count} جهة بنجاح."))

        if skipped_protected:
            self.stdout.write(
                self.style.WARNING(
                    f"تخطّينا {len(skipped_protected)} جهة لأنها مربوطة بمنتجات فعلية "
                    "(الحذف كان بيمسح المنتجات كمان، فتوقفنا حماية للبيانات):"
                )
            )
            for name in skipped_protected[:15]:
                self.stdout.write(f"  - {name}")
            if len(skipped_protected) > 15:
                self.stdout.write(f"  ... و{len(skipped_protected) - 15} جهة إضافية")
