from rest_framework.throttling import UserRateThrottle


class CommunityPostRateThrottle(UserRateThrottle):
    """
    حد نشر يومي ثابت لكل المستخدمين بهذي المرحلة (راجع DEFAULT_THROTTLE_RATES
    بـ settings.py — 'community_post': '3/day').

    قرار مقصود: التصميم الأصلي اقترح حدًا متغيّرًا حسب فئة الثقة
    (مستخدم موثوق ينشر أكثر). لم أنفّذه الآن لسبب حقيقي مو تجنّبًا
    للتعقيد: reputation.contributor_reputation() ترجّع None لأي
    مستخدم عنده أقل من 5 اقتراحات مراجَعة — يعني بالأسبوع الأول لهذي
    الميزة، كل المستخدمين بلا استثناء بفئة "عادي" فعليًا (ما فيه بيانات
    كافية للتمييز أصلًا). حد متغيّر بلا بيانات حقيقية يميّز عليها كود
    ميت. لما يتراكم نشاط حقيقي، رفع هذا لحد متغيّر حسب
    trust_tier مباشرة عبر override لـ allow_request() بدل get_rate()
    (DRF يستدعي get_rate() وقت __init__ قبل ما self.request يتوفر).
    """
    scope = 'community_post'
