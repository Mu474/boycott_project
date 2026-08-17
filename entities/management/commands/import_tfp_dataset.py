"""
أمر استيراد قاعدة بيانات TechForPalestine (BDS + Who Profits + AFSC مجمّعة)
مباشرة لجداول الجهات والتصنيفات بمشروع بصيرة.

الاستخدام:
    python manage.py import_tfp_dataset
    python manage.py import_tfp_dataset --fetch-latest   # يجيب أحدث نسخة من GitHub بدل الملف المرفق
    python manage.py import_tfp_dataset --dry-run         # يعرض وش بيسوي بدون حفظ فعلي بالقاعدة
    python manage.py import_tfp_dataset --skip-images      # يتخطى تحميل الشعارات (أسرع بكثير)

المصدر: https://github.com/TechForPalestine/boycott-israeli-consumer-goods-dataset
رخصة البيانات: راجع LICENSE بمستودع المصدر قبل الاستخدام التجاري.
"""
import json
import re
import time
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from categories.models import Category
from entities.models import BusinessEntity

DATASET_JSON_URL = (
    "https://raw.githubusercontent.com/TechForPalestine/"
    "boycott-israeli-consumer-goods-dataset/main/output/json/data.json"
)

# تصنيفات TechForPalestine (إنجليزي) -> اسم عربي يُعرض بالتطبيق.
# أي تصنيف من القائمة الرسمية ما هو موجود هنا يُضاف تلقائيًا باسمه
# الإنجليزي الخام كإجراء احتياطي، حتى ما يوقف الاستيراد.
CATEGORY_AR = {
    "books": "كتب", "car": "سيارات", "charity": "خيرية", "clothing": "ملابس",
    "cloud": "حوسبة سحابية", "coffee": "قهوة", "commerce": "تجارة إلكترونية",
    "contractor": "مقاولات", "cosmetics": "مستحضرات تجميل", "dates": "تمور",
    "development": "تطوير برمجيات", "drinks": "مشروبات", "energy": "طاقة",
    "entertainment": "ترفيه", "fashion": "أزياء", "finance": "مالية",
    "fintech": "تقنية مالية", "food": "أغذية", "hardware": "أجهزة",
    "healthcare": "رعاية صحية", "household": "مستلزمات منزلية", "hr": "موارد بشرية",
    "insurance": "تأمين", "luxury": "سلع فاخرة", "manufacturer": "تصنيع",
    "marketing": "تسويق", "media": "إعلام", "petcare": "مستلزمات حيوانات أليفة",
    "pharmaceuticals": "أدوية", "politics": "سياسة", "productivity": "إنتاجية",
    "sales": "مبيعات", "security": "أمن", "semiconductors": "أشباه موصلات",
    "supermarket": "سوبرماركت", "technology": "تقنية", "travel": "سفر",
    "weapons": "أسلحة",
}
FALLBACK_CATEGORY_AR = "أخرى"

STATUS_MAP = {"avoid": "boycott", "support": "alternative", "neutral": "caution"}

REASON_LABELS_AR = {
    "operations_in_israel": "عمليات داخل إسرائيل",
    "operations_in_settlements": "عمليات بالمستوطنات",
    "executive_supports_israel": "دعم تنفيذي معلن لإسرائيل",
    "hiring_discrimination": "تمييز بالتوظيف",
}

MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^\d+\]:\s*(https?://\S+)", re.MULTILINE)


def clean_description(desc: str) -> str:
    """يشيل تنسيق Markdown (** **) ويحوّل النص لصيغة عادية قابلة للعرض."""
    if not desc:
        return ""
    text = MD_BOLD_RE.sub(r"\1", desc)
    # نحذف سطور تعريف الحواشي [^1]: https://... من النص المعروض
    # (بنستخرج أول رابط منها لحقل evidence_url بدل ما يبقى بالنص)
    text = FOOTNOTE_DEF_RE.sub("", text).strip()
    return text


def extract_evidence_url(desc: str, website: str = "") -> str:
    """يستخرج أول رابط مصدر من حواشي الوصف، أو يرجع رابط الموقع الرسمي كبديل."""
    m = FOOTNOTE_DEF_RE.search(desc or "")
    if m:
        return m.group(1)
    return website or ""


def build_reason(description: str, reasons: list[str]) -> str:
    parts = []
    if reasons:
        labels = [REASON_LABELS_AR.get(r, r) for r in reasons]
        parts.append("السبب: " + "، ".join(labels))
    cleaned = clean_description(description)
    if cleaned:
        parts.append(cleaned)
    return "\n\n".join(parts).strip()


class Command(BaseCommand):
    help = "يستورد بيانات الشركات/العلامات التجارية من قاعدة TechForPalestine مباشرة لجدول الجهات"

    def add_arguments(self, parser):
        parser.add_argument("--fetch-latest", action="store_true",
                             help="يجيب أحدث نسخة من GitHub بدل الملف المحلي المرفق")
        parser.add_argument("--file", type=str, default=None,
                             help="مسار ملف data.json محلي (اختياري)")
        parser.add_argument("--dry-run", action="store_true",
                             help="يعرض إحصائيات بدون أي تعديل فعلي بقاعدة البيانات")
        parser.add_argument("--skip-images", action="store_true",
                             help="يتخطى تحميل الشعارات (أسرع بكثير، تقدر تضيفها لاحقًا يدويًا)")

    # ── تحميل البيانات ────────────────────────────────────────
    def _load_data(self, opts) -> dict:
        if opts["file"]:
            with open(opts["file"], encoding="utf-8") as f:
                return json.load(f)
        if opts["fetch_latest"]:
            self.stdout.write("جاري تحميل أحدث نسخة من GitHub...")
            with urllib.request.urlopen(DATASET_JSON_URL, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        # الملف المرفق افتراضيًا مع هذا الأمر (snapshot محلي، يشتغل بدون إنترنت)
        import os
        bundled = os.path.join(os.path.dirname(__file__), "data", "tfp_dataset.json")
        with open(bundled, encoding="utf-8") as f:
            return json.load(f)

    def _get_category(self, cache: dict, category_keys: list[str], dry_run: bool) -> Category | None:
        key = category_keys[0] if category_keys else None
        name_ar = CATEGORY_AR.get(key, key) if key else FALLBACK_CATEGORY_AR
        if name_ar in cache:
            return cache[name_ar]
        if dry_run:
            cache[name_ar] = None
            return None
        cat, _ = Category.objects.get_or_create(name=name_ar)
        cache[name_ar] = cat
        return cat

    def _download_logo(self, url: str):
        if not url:
            return None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read()
                content_type = r.headers.get("Content-Type", "")
        except Exception:
            return None

        ext = self._safe_image_extension(url, content_type)
        try:
            return ContentFile(data, name=f"import.{ext}")
        except Exception:
            return None

    @staticmethod
    def _safe_image_extension(url: str, content_type: str = "") -> str:
        """يستخرج امتداد صورة نظيف وآمن من رابط أو نوع المحتوى (Content-Type).
        لازم يرجع دائمًا امتداد أبجدي رقمي بحت من قائمة معروفة، وإلا Django
        يرفض اسم الملف كمشكوك فيه (SuspiciousFileOperation) — صار فعليًا
        بسبب روابط فيها / أو رموز غريبة بعد نقطة الامتداد المفترضة.
        """
        valid = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
        # ناخذ آخر جزء بالمسار بس (بعد آخر /)، بعيدًا عن أي query/fragment
        path = url.split("?")[0].split("#")[0]
        last_segment = path.rsplit("/", 1)[-1]
        if "." in last_segment:
            raw = last_segment.rsplit(".", 1)[-1].lower()
            raw = re.sub(r"[^a-z0-9]", "", raw)[:5]
            if raw in valid:
                return raw
        ct_map = {
            "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
            "image/gif": "gif", "image/webp": "webp", "image/bmp": "bmp",
        }
        return ct_map.get(content_type.split(";")[0].strip().lower(), "jpg")

    def handle(self, *args, **opts):
        data = self._load_data(opts)
        companies = data.get("companies", {})
        brands = data.get("brands", {})
        dry_run = opts["dry_run"]
        skip_images = opts["skip_images"]

        cat_cache: dict = {}
        id_to_entity: dict[str, BusinessEntity] = {}
        stats = {"created": 0, "updated": 0, "skipped": 0, "images_ok": 0, "images_failed": 0}

        with transaction.atomic():
            # المرحلة ١: الشركات الأم (companies) — بدون parent_entity
            for cid, c in companies.items():
                status = STATUS_MAP.get(c.get("status"))
                if not status:
                    stats["skipped"] += 1
                    continue
                category = self._get_category(cat_cache, [], dry_run)
                reason = build_reason(c.get("description", ""), [])
                entity, created = self._upsert_entity(
                    name=c["name"], status=status, reason=reason,
                    evidence_url="", category=category, parent_entity=None,
                    dry_run=dry_run,
                )
                id_to_entity[cid] = entity
                stats["created" if created else "updated"] += 1

            # المرحلة ٢: العلامات التجارية (brands) — مع ربط الشركة الأم لو موجودة
            for bid, b in brands.items():
                status = STATUS_MAP.get(b.get("status"))
                if not status:
                    stats["skipped"] += 1
                    continue
                category = self._get_category(cat_cache, b.get("categories") or [], dry_run)
                reason = build_reason(b.get("description", ""), b.get("reasons") or [])
                evidence = extract_evidence_url(b.get("description", ""), b.get("website", ""))

                parent = None
                for sh in (b.get("stakeholders") or []):
                    if sh.get("type") == "owner" and sh.get("id") in id_to_entity:
                        parent = id_to_entity[sh["id"]]
                        break

                entity, created = self._upsert_entity(
                    name=b["name"], status=status, reason=reason,
                    evidence_url=evidence, category=category, parent_entity=parent,
                    dry_run=dry_run,
                )
                id_to_entity[bid] = entity
                stats["created" if created else "updated"] += 1

                if not skip_images and not dry_run and b.get("logo_url") and entity and not entity.logo:
                    img = self._download_logo(b["logo_url"])
                    if img:
                        entity.logo.save(img.name, img, save=True)
                        stats["images_ok"] += 1
                    else:
                        stats["images_failed"] += 1

            if dry_run:
                self.stdout.write(self.style.WARNING("وضع dry-run — بالغاء أي تعديل فعلي (rollback)"))
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"تم! أُنشئ: {stats['created']} | حُدّث: {stats['updated']} | "
            f"تُخُطّي: {stats['skipped']} | شعارات نجحت: {stats['images_ok']} | "
            f"شعارات فشلت: {stats['images_failed']}"
        ))

    def _upsert_entity(self, *, name, status, reason, evidence_url, category, parent_entity, dry_run):
        """يبحث عن جهة بنفس الاسم (غير حساس لحالة الأحرف)؛ يحدّثها لو موجودة، وإلا ينشئها."""
        if dry_run:
            return None, True
        existing = BusinessEntity.objects.filter(name__iexact=name).first()
        if existing:
            existing.status = status
            existing.reason = reason or existing.reason
            existing.evidence_url = evidence_url or existing.evidence_url
            if category:
                existing.category = category
            if parent_entity:
                existing.parent_entity = parent_entity
            existing.save()
            return existing, False
        entity = BusinessEntity.objects.create(
            name=name, status=status, reason=reason,
            evidence_url=evidence_url, category=category, parent_entity=parent_entity,
        )
        return entity, True
