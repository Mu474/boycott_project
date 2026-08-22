import json
from pathlib import Path

from django.core.management.base import BaseCommand
from categories.models import Category
from entities.models import BusinessEntity

DATA_DIR = Path(__file__).resolve().parent / "data"
PARENT_MAP_FILE = DATA_DIR / "manual_parent_overrides.json"
PARENT_DATA_FILE = DATA_DIR / "parent_company_data.json"
CATEGORY_MAP_FILE = DATA_DIR / "manual_category_overrides.json"

# الشركات الخمس غير المدرجة إطلاقًا بمصدر بيانات TFP (لا كشركة ولا
# كبراند) رغم إنها مالكة فعليًا لعدة براندات عندنا — بيانات حقيقية
# بمعرفتي المباشرة، مو من TFP.
NEW_COMPANIES_INFO = {
    "Booking Holdings": {"category": "travel", "status": "boycott",
                          "reason": "الشركة الأم لعدة منصات حجز سفر، من ضمنها Booking.com وKayak وAgoda"},
    "JAB Holding Company": {"category": "coffee", "status": "boycott",
                             "reason": "مجموعة استثمارية أوروبية تملك عدة علامات قهوة ومخبوزات عالمية"},
    "Tata Motors": {"category": "car", "status": "boycott",
                     "reason": "الشركة الأم لـ Jaguar وLand Rover"},
    "Rakuten": {"category": "technology", "status": "boycott",
                "reason": "شركة تقنية يابانية، الشركة الأم لتطبيق Viber"},
    "Phoenix Group": {"category": "insurance", "status": "boycott",
                       "reason": "الشركة الأم الفعلية لعلامة Standard Life بالمملكة المتحدة"},
}

CATEGORY_AR = {
    "books": "كتب", "car": "سيارات", "charity": "خيرية", "clothing": "ملابس", "cloud": "حوسبة سحابية",
    "coffee": "قهوة", "commerce": "تجارة إلكترونية", "contractor": "مقاولات", "cosmetics": "مستحضرات تجميل",
    "dates": "تمور", "development": "تطوير برمجيات", "drinks": "مشروبات", "energy": "طاقة",
    "entertainment": "ترفيه", "fashion": "أزياء", "finance": "مالية", "fintech": "تقنية مالية", "food": "طعام",
    "hardware": "أجهزة", "healthcare": "رعاية صحية", "household": "منزلية", "hr": "موارد بشرية",
    "insurance": "تأمين", "luxury": "فاخرة", "manufacturer": "تصنيع", "marketing": "تسويق", "media": "إعلام",
    "petcare": "عناية بالحيوانات", "pharmaceuticals": "أدوية", "politics": "سياسة", "productivity": "إنتاجية",
    "sales": "مبيعات", "security": "أمن", "semiconductors": "أشباه موصلات", "supermarket": "سوبر ماركت",
    "technology": "تقنية", "travel": "سفر", "weapons": "أسلحة",
}


class Command(BaseCommand):
    help = (
        "يربط الجهات (البراندات) بالشركة الأم المالكة لها، وينشئ أي "
        "شركة أم ناقصة من قاعدة البيانات ببياناتها الحقيقية (الحالة "
        "والسبب) من مصدر TFP نفسه، أو بمعرفة يدوية للشركات غير المدرجة "
        "بمصدر TFP إطلاقًا."
    )

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true",
                             help="تنفيذ الربط فعليًا. بدونها، الأمر يعرض بس معاينة (dry-run).")

    def handle(self, *args, **opts):
        confirm = opts["yes"]

        for f in (PARENT_MAP_FILE, PARENT_DATA_FILE):
            if not f.exists():
                self.stdout.write(self.style.ERROR(f"ملف غير موجود: {f}"))
                return

        brand_to_parent = json.loads(PARENT_MAP_FILE.read_text(encoding="utf-8"))
        parent_company_data = json.loads(PARENT_DATA_FILE.read_text(encoding="utf-8"))
        category_overrides = (
            json.loads(CATEGORY_MAP_FILE.read_text(encoding="utf-8")) if CATEGORY_MAP_FILE.exists() else {}
        )

        self.stdout.write(f"حمّلت خريطة ربط لـ {len(brand_to_parent)} علامة تجارية.")

        existing_names = {e.name.lower(): e for e in BusinessEntity.objects.all()}

        will_link = []
        brand_not_found = []
        parents_to_create = {}  # اسم -> معلومات الإنشاء

        for brand_name, parent_name in brand_to_parent.items():
            brand = existing_names.get(brand_name.lower())
            if not brand:
                brand_not_found.append(brand_name)
                continue

            parent = existing_names.get(parent_name.lower())
            if not parent and parent_name not in parents_to_create:
                if parent_name in NEW_COMPANIES_INFO:
                    info = NEW_COMPANIES_INFO[parent_name]
                elif parent_name in parent_company_data:
                    d = parent_company_data[parent_name]
                    cat_key = category_overrides.get(parent_name, "manufacturer")
                    info = {"category": cat_key, "status": d["status"], "reason": d["reason"]}
                else:
                    # احتياطي نادر: اسم شركة أم مالكة موجود بخريطة الربط
                    # لكن ما لقينا له بيانات حقيقية بأي مصدر — ننشئها
                    # بحد أدنى من المعلومات بدل ما نتجاهلها بصمت
                    info = {"category": "manufacturer", "status": "boycott",
                             "reason": "شركة أم مالكة لعدة علامات تجارية مقاطعة"}
                parents_to_create[parent_name] = info

            will_link.append((brand, parent_name))

        self.stdout.write(f"هينربط فعليًا: {len(will_link)} علامة تجارية")
        self.stdout.write(f"شركات أم هتُنشأ من الصفر: {len(parents_to_create)}")
        for name in list(parents_to_create)[:20]:
            self.stdout.write(f"  - {name}")
        if len(parents_to_create) > 20:
            self.stdout.write(f"  ... و{len(parents_to_create) - 20} إضافية")

        if brand_not_found:
            self.stdout.write(
                self.style.WARNING(f"براندات بالخريطة ما لقيناها بقاعدة البيانات ({len(brand_not_found)}):")
            )
            for n in brand_not_found[:10]:
                self.stdout.write(f"  - {n}")
            if len(brand_not_found) > 10:
                self.stdout.write(f"  ... و{len(brand_not_found) - 10} إضافية (على الأغلب انحذفوا بأمر purge السابق)")

        if not confirm:
            self.stdout.write(self.style.WARNING("هذا وضع معاينة فقط (dry-run) — ما اترابط أي شيء فعليًا."))
            self.stdout.write(self.style.WARNING("لتنفيذ الربط فعليًا، أعد تشغيل الأمر مع --yes"))
            return

        # ── التنفيذ الفعلي ──────────────────────────────────────
        cat_cache: dict = {}
        created_entities = {}

        for name, info in parents_to_create.items():
            name_ar = CATEGORY_AR.get(info["category"], info["category"])
            if name_ar not in cat_cache:
                cat_cache[name_ar], _ = Category.objects.get_or_create(name=name_ar)
            new_entity = BusinessEntity.objects.create(
                name=name,
                status=info["status"],
                reason=info["reason"],
                category=cat_cache[name_ar],
                countries="global",
            )
            created_entities[name] = new_entity
            self.stdout.write(self.style.SUCCESS(f"أنشأت شركة: {name}"))

        linked_count = 0
        for brand, parent_name in will_link:
            parent_entity = created_entities.get(parent_name) or existing_names.get(parent_name.lower())
            if not parent_entity or brand.pk == parent_entity.pk:
                continue
            brand.parent_entity = parent_entity
            brand.save(update_fields=["parent_entity"])
            linked_count += 1

        self.stdout.write(self.style.SUCCESS(f"تم ربط {linked_count} علامة تجارية بشركتها الأم بنجاح."))
        self.stdout.write(self.style.SUCCESS(f"تم إنشاء {len(created_entities)} شركة أم جديدة."))
