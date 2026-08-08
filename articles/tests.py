from django.test import TestCase
from rest_framework.test import APIClient
from .models import Article
from users.models import User


class ArticleModelTest(TestCase):
    def test_create_article(self):
        a = Article.objects.create(title="مقال تجريبي", content="محتوى المقال")
        self.assertEqual(str(a), "مقال تجريبي")
        self.assertIsNotNone(a.published_at)


class ArticleWhiteBoxTest(TestCase):
    """تغطية صلاحيات GET (عام) مقابل POST/PUT/DELETE (مشرف فقط)"""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin_article@test.com", name="مشرف", password="123456"
        )
        self.article = Article.objects.create(title="مقال 1", content="نص")

    def test_get_articles_allowed_without_auth(self):
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, 200)

    def test_create_article_without_auth_returns_401(self):
        response = self.client.post('/api/articles/', {'title': 'جديد', 'content': 'نص'})
        self.assertEqual(response.status_code, 401)

    def test_create_article_with_auth_succeeds(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/articles/', {'title': 'جديد', 'content': 'نص'})
        self.assertEqual(response.status_code, 201)

    def test_update_article_missing_required_field(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.put(f'/api/articles/{self.article.id}/', {'title': ''})
        self.assertEqual(response.status_code, 400)

    def test_article_not_found_returns_404(self):
        response = self.client.get('/api/articles/9999/')
        self.assertEqual(response.status_code, 404)

    def test_delete_article_success(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/articles/{self.article.id}/')
        self.assertEqual(response.status_code, 204)