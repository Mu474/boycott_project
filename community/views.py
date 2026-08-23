from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from users.models import User
from .models import Group, GroupMembership
from .serializers import GroupDetailSerializer
from .points import annotate_points


class LeaderboardView(APIView):
    """أفضل 50 فرد — يظهر فيها بس من حدد username (خصوصية، راجع نموذج User)."""
    permission_classes = [AllowAny]

    def get(self, request):
        users = annotate_points(
            User.objects.filter(username__isnull=False).exclude(username='')
        ).order_by('-points')[:50]
        data = [
            {'rank': i + 1, 'id': u.id, 'username': u.username, 'points': u.points}
            for i, u in enumerate(users)
        ]
        return Response(data)


class GroupLeaderboardView(APIView):
    """
    ترتيب المجموعات حسب مجموع نقاط أعضائها. حلقة Python على كل
    المجموعات (N+1) بدل استعلام SQL واحد مجمّع على مستويين — قرار
    مقصود لتبسيط الكود بهذي المرحلة بما إن عدد المجموعات المتوقع صغير؛
    لو صار عدد المجموعات كبير جدًا مستقبلًا، هذا أول مكان يحتاج تحسين
    (aggregate واحد بدل حلقة).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        results = []
        for group in Group.objects.all():
            members = annotate_points(User.objects.filter(group_memberships__group=group))
            member_points = [
                m.points for m in members if m.username
            ]
            results.append({
                'id': group.id,
                'name': group.name,
                'member_count': group.memberships.count(),
                'total_points': sum(member_points),
            })
        results.sort(key=lambda r: r['total_points'], reverse=True)
        for i, r in enumerate(results[:50]):
            r['rank'] = i + 1
        return Response(results[:50])


class GroupCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        if not name:
            return Response({'error': 'اسم المجموعة مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        group = Group.objects.create(name=name, creator=request.user)
        GroupMembership.objects.create(group=group, user=request.user)

        serializer = GroupDetailSerializer(group, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyGroupsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = Group.objects.filter(memberships__user=request.user).order_by('-created_at')
        serializer = GroupDetailSerializer(groups, many=True, context={'request': request})
        return Response(serializer.data)


class GroupDetailView(APIView):
    """
    AllowAny عمدًا — رابط دعوة قابل للمشاركة يفترض إن أي حد يفتحه يقدر
    يشوف اسم المجموعة ونقاطها كمعاينة قبل الانضمام (زي أي رابط دعوة
    عادي). invite_code نفسه محمي داخل السيريلايزر (يظهر للأعضاء بس).
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            group = Group.objects.get(pk=pk)
        except Group.DoesNotExist:
            return Response({'error': 'المجموعة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        serializer = GroupDetailSerializer(group, context={'request': request})
        return Response(serializer.data)


class GroupJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = (request.data.get('invite_code') or '').strip().upper()
        if not code:
            return Response({'error': 'كود الدعوة مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(invite_code=code)
        except Group.DoesNotExist:
            return Response({'error': 'كود الدعوة غير صحيح'}, status=status.HTTP_404_NOT_FOUND)

        # get_or_create بدل create مباشرة: لو المستخدم أصلًا عضو (ضغط
        # نفس رابط الدعوة مرتين مثلًا)، نرجّعه بنجاح بدل خطأ IntegrityError
        _membership, created = GroupMembership.objects.get_or_create(group=group, user=request.user)

        serializer = GroupDetailSerializer(group, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class GroupLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        deleted_count, _ = GroupMembership.objects.filter(group_id=pk, user=request.user).delete()
        if not deleted_count:
            return Response({'error': 'أنت لست عضوًا بهذه المجموعة'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True})
