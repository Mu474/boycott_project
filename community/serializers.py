from rest_framework import serializers
from .models import Group


class GroupDetailSerializer(serializers.ModelSerializer):
    """
    ملاحظة أمنية مهمة: invite_code لا يظهر إلا للأعضاء الحاليين
    (SerializerMethodField يتحقق من العضوية عبر request.context) — لو
    ظهر لأي زائر بمجرد معرفة رقم المجموعة، صار أي حد يقدر ينضم بدون
    دعوة فعلية، وهذا يلغي الغرض الكامل من نظام الكود.

    الأعضاء يظهرون بـ username فقط (لو حدده المستخدم) — لا بريد
    إلكتروني ولا اسم حقيقي بأي واجهة عامة.
    """
    invite_code = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'invite_code', 'created_at', 'member_count', 'total_points', 'members']

    def _is_member(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.memberships.filter(user=request.user).exists()

    def get_invite_code(self, obj):
        return obj.invite_code if self._is_member(obj) else None

    def _members_with_points(self, obj):
        # نستخدم annotate_points هنا (مستورد داخل الدالة تفاديًا لاستيراد
        # دائري بين community.serializers و community.points عند استيراد
        # الموديلات من ملفات ثانية بنفس الحزمة)
        from .points import annotate_points
        from users.models import User

        # كاش بسيط على مستوى الـ serializer نفسه — get_members()
        # و get_total_points() يحتاجان نفس البيانات، وبدون هذا الكاش
        # كل مجموعة تُستعلَم مرتين (خصوصًا مزعج بـ many=True لقائمة
        # مجموعات كاملة بالترتيب)
        cache = getattr(self, '_members_cache', None)
        if cache is None:
            cache = self._members_cache = {}
        if obj.pk in cache:
            return cache[obj.pk]

        users = annotate_points(User.objects.filter(group_memberships__group=obj)).order_by('-points')
        result = [
            {'id': u.id, 'username': u.username, 'points': u.points}
            for u in users
            if u.username  # مستخدم بدون username ما يظهر بأي عرض عام
        ]
        cache[obj.pk] = result
        return result

    def get_members(self, obj):
        return self._members_with_points(obj)

    def get_member_count(self, obj):
        return obj.memberships.count()

    def get_total_points(self, obj):
        return sum(m['points'] for m in self._members_with_points(obj))
