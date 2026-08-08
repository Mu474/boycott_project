from django.test import TestCase
from rest_framework.test import APIClient
from .models import Report
from users.models import User


class ReportModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@test.com", name="مستخدم", password="123456")

    def test_create_report_default_status_pending(self):
        r = Report.objects.create(
            target_type='product', target_id=1, reason='بيانات خاطئة', user=self.user
        )
        self.assertEqual(r.status, 'pending')


class ReportWhiteBoxTest(TestCase):
    """تغطية: POST يتطلب تسجيل دخول / GET+PATCH يتطلب صلاحية مشرف"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="u2@test.com", name="مستخدم", password="123456")
        self.admin = User.objects.create_superuser(
            email="admin_rep@test.com", name="مشرف", password="123456"
        )

    def test_create_report_requires_login(self):
        response = self.client.post('/api/reports/', {
            'target_type': 'product', 'target_id': 1, 'reason': 'خطأ في البيانات'
        })
        self.assertEqual(response.status_code, 401)

    def test_create_report_authenticated_user_succeeds(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/reports/', {
            'target_type': 'product', 'target_id': 1, 'reason': 'خطأ في البيانات'
        })
        self.assertEqual(response.status_code, 201)

    def test_list_reports_requires_admin(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/reports/')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_resolve_report(self):
        report = Report.objects.create(
            target_type='product', target_id=1, reason='خطأ', user=self.user
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f'/api/reports/{report.id}/', {'status': 'resolved'})
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.status, 'resolved')

    def test_report_not_found_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/reports/9999/')
        self.assertEqual(response.status_code, 404)