import re
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, UserSerializer, MeSerializer
from .models import User

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,30}$')


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, username=email, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response(
            {'error': 'البريد الإلكتروني أو كلمة المرور غير صحيحة'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class UserMeView(APIView):
    """
    الملف الشخصي للمستخدم الحالي (GET) وتحديث اسم المستخدم العام (PATCH).
    اسم المستخدم شرط أساسي للظهور بأي ترتيب عام (راجع نموذج User) —
    هذا الـ endpoint هو المكان الوحيد اللي يقدر المستخدم يحدده منه.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        username = (request.data.get('username') or '').strip()
        if not username:
            return Response({'error': 'اسم المستخدم مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        if not USERNAME_RE.match(username):
            return Response(
                {'error': 'اسم المستخدم يجب أن يكون بين 3-30 حرفًا، ويحتوي فقط على حروف إنجليزية وأرقام و_ (بدون مسافات أو رموز)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username__iexact=username).exclude(pk=request.user.pk).exists():
            return Response({'error': 'اسم المستخدم هذا مُستخدم مسبقًا'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.username = username
        request.user.save(update_fields=['username'])
        return Response(MeSerializer(request.user).data)


class UserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all().order_by('-created_at')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class UserDeleteView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
