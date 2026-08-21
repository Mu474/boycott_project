import json
from pathlib import Path

from django.core.management.base import BaseCommand
from categories.models import Category
from entities.models import BusinessEntity

DATA_DIR = Path(__file__).resolve().parent / "data"
PARENT_MAP_FILE = DATA_DIR / "manual_parent_overrides.json"

# الشركات الخمس غير المدرجة أصلًا بمصدر البيانات (TFP) رغم إنها مالكة
# فعليًا لعشرات البراندات المسجّلة عندنا — لازم تُنشأ من الصفر بأول
# مرة تشتغل فيها هذا الأمر. الفئة مبنية على النشاط الأساسي المعروف لكل
# شركة (مو تخمين عشوائي).
NEW_PARENT_COMPANIES = {
    "Booking Holdings": "travel",
    "JAB Holding Company": "coffee",
    "Tata Motors": "car",
    "Rakuten": "technology",
    "Phoenix Group": "insurance",
}

CATEGORY_AR = {
    "travel": "سفر", "coffee": "قهوة", "car": "سيارات",
    "technology": "تقنية", "insurance": "تأمين",
}


class Command(BaseCommand):
    help = (
        "يربط الجهات (البراندات) بالشركة الأم المالكة لها. يستخدم بيانات "
        "stakeholders الأصلية لو الشركة موجودة عندنا، وخريطة يدوية "
        "(بمعرفة حقيقية) للشركات الناقصة من مصدر TFP نفسه — وينشئها "
        "تلقائيًا لو ما كانت موجودة أصلًا."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="تنفيذ الربط فعليًا. بدونها، الأمر يعرض بس معاينة (dry-run).",
        )

    def handle(self, *args, **opts):
        confirm = opts["yes"]

        if not PARENT_MAP_FILE.exists():
            self.stdout.write(self.style.ERROR(f"ملف الخريطة غير موجود: {PARENT_MAP_FILE}"))
            return

        brand_to_parent = json.loads(PARENT_MAP_FILE.read_text(encoding="utf-8"))
        self.stdout.write(f"حمّلت خريطة ربط لـ {len(brand_to_parent)} علامة تجارية.")

        # نتحقق مسبقًا (بدون أي تعديل) من كل الحالات، عشان المعاينة تكون دقيقة
        will_link = []
        brand_not_found = []
        parent_not_found_and_not_new = []

        existing_names = {e.name.lower(): e for e in BusinessEntity.objects.all()}

        for brand_name, parent_name in brand_to_parent.items():
            brand = existing_names.get(brand_name.lower())
            if not brand:
                brand_not_found.append(brand_name)
                continue
            parent = existing_names.get(parent_name.lower())
            if not parent and parent_name not in NEW_PARENT_COMPANIES:
                parent_not_found_and_not_new.append((brand_name, parent_name))
                continue
            will_link.append((brand, parent_name))

        self.stdout.write(f"هينربط فعليًا: {len(will_link)} علامة تجارية")
        self.stdout.write(f"شركات جديدة هتُنشأ (لو ما كانت موجودة): {len(NEW_PARENT_COMPANIES)}")
        for name in NEW_PARENT_COMPANIES:
            self.stdout.write(f"  - {name}")

        if brand_not_found:
            self.stdout.write(
                self.style.WARNING(f"براندات بالخريطة ما لقيناها بقاعدة البيانات ({len(brand_not_found)}):")
            )
            for n in brand_not_found[:10]:
                self.stdout.write(f"  - {n}")
            if len(brand_not_found) > 10:
                self.stdout.write(f"  ... و{len(brand_not_found) - 10} إضافية")

        if parent_not_found_and_not_new:
            self.stdout.write(
                self.style.ERROR(
                    f"⚠️ خطأ بالخريطة نفسها — شركة أم متوقّع وجودها لكن غير موجودة "
                    f"وغير مدرجة بقائمة الإنشاء ({len(parent_not_found_and_not_new)}):"
                )
            )
            for b, p in parent_not_found_and_not_new[:10]:
                self.stdout.write(f"  - {b} -> {p}")

        if not confirm:
            self.stdout.write(self.style.WARNING("هذا وضع معاينة فقط (dry-run) — ما اترابط أي شيء فعليًا."))
            self.stdout.write(self.style.WARNING("لتنفيذ الربط فعليًا، أعد تشغيل الأمر مع --yes"))
            return

        # ── التنفيذ الفعلي ──────────────────────────────────────
        cat_cache: dict = {}
        created_companies = {}
        linked_count = 0

        for name, cat_key in NEW_PARENT_COMPANIES.items():
            existing = existing_names.get(name.lower())
            if existing:
                created_companies[name] = existing
                continue
            name_ar = CATEGORY_AR.get(cat_key, cat_key)
            if name_ar not in cat_cache:
                cat_cache[name_ar], _ = Category.objects.get_or_create(name=name_ar)
            new_entity = BusinessEntity.objects.create(
                name=name,
                status="boycott",
                reason="شركة أم مالكة لعدة علامات تجارية مدرجة بقاعدة بياناتنا",
                category=cat_cache[name_ar],
                countries="global",
            )
            created_companies[name] = new_entity
            self.stdout.write(self.style.SUCCESS(f"أنشأت شركة جديدة: {name}"))

        for brand, parent_name in will_link:
            parent_entity = created_companies.get(parent_name) or existing_names.get(parent_name.lower())
            if not parent_entity:
                continue
            if brand.pk == parent_entity.pk:
                continue  # حماية من ربط جهة بنفسها بالغلط
            brand.parent_entity = parent_entity
            brand.save(update_fields=["parent_entity"])
            linked_count += 1

        self.stdout.write(self.style.SUCCESS(f"تم ربط {linked_count} علامة تجارية بشركتها الأم بنجاح."))
