import json
from pathlib import Path

from django.core.management.base import BaseCommand
from categories.models import Category
from entities.models import BusinessEntity
from entities.management.commands.import_tfp_dataset import CATEGORY_AR

DATA_FILE = Path(__file__).resolve().parent / "data" / "manual_category_overrides.json"


class Command(BaseCommand):
    help = (
        "يطبّق تصنيف يدوي (بمعرفة حقيقية لكل جهة، مو تخمين آلي) على "
        "الجهات المصنّفة حاليًا تحت 'أخرى' — عشان نلغي هذا التصنيف "
        "العام نهائيًا ونحل مشكلة اقتراح البدائل غير المنطقية."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="تنفيذ التحديث فعليًا. بدونها، الأمر يعرض بس معاينة (dry-run).",
        )

    def handle(self, *args, **opts):
        confirm = opts["yes"]

        if not DATA_FILE.exists():
            self.stdout.write(self.style.ERROR(f"ملف الخريطة غير موجود: {DATA_FILE}"))
            return

        overrides = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        self.stdout.write(f"حمّلت خريطة تصنيف لـ {len(overrides)} اسم.")

        try:
            other_cat = Category.objects.get(name="أخرى")
        except Category.DoesNotExist:
            self.stdout.write(self.style.SUCCESS("لا يوجد تصنيف 'أخرى' أصلاً بقاعدة البيانات — ما فيه شي نسويه."))
            return

        entities_under_other = list(BusinessEntity.objects.filter(category=other_cat))
        self.stdout.write(f"عدد الجهات الحالية تحت 'أخرى': {len(entities_under_other)}")

        matched = []
        unmatched = []
        for e in entities_under_other:
            key = overrides.get(e.name)
            if key:
                matched.append((e, key))
            else:
                unmatched.append(e.name)

        self.stdout.write(f"هينتصنّف: {len(matched)} جهة")
        if unmatched:
            self.stdout.write(self.style.WARNING(f"ما لقينا لهم تصنيف بالخريطة (تبقى 'أخرى'): {len(unmatched)}"))
            for n in unmatched[:15]:
                self.stdout.write(f"  - {n}")
            if len(unmatched) > 15:
                self.stdout.write(f"  ... و{len(unmatched) - 15} إضافية")

        if not confirm:
            self.stdout.write(self.style.WARNING("هذا وضع معاينة فقط (dry-run) — ما انحدّث أي شيء فعليًا."))
            self.stdout.write(self.style.WARNING("لتنفيذ التحديث فعليًا، أعد تشغيل الأمر مع --yes"))
            return

        cat_cache: dict = {}
        updated = 0
        for entity, key in matched:
            name_ar = CATEGORY_AR.get(key, key)
            if name_ar not in cat_cache:
                cat_cache[name_ar], _ = Category.objects.get_or_create(name=name_ar)
            entity.category = cat_cache[name_ar]
            entity.save(update_fields=["category"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"تم تحديث {updated} جهة بنجاح."))

        remaining = BusinessEntity.objects.filter(category=other_cat).count()
        if remaining == 0:
            other_cat.delete()
            self.stdout.write(self.style.SUCCESS("لم يبقَ أي جهة تحت 'أخرى' — حذفت التصنيف نفسه من قاعدة البيانات."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"لسا باقي {remaining} جهة تحت 'أخرى' (ما لقينا لها تصنيف يدوي بالخريطة) — "
                    "التصنيف نفسه ما انحذف."
                )
            )
