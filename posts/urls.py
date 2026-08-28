from django.urls import path
from .views import (
    CommunityFeedView, CommunityPostCreateView, MyPostsView, ProductPostsView,
    PostReactionView, CommunityPostAdminListView, CommunityPostReviewView,
    AlternativeSuggestionCreateView, AlternativeSuggestionListView, AlternativeSuggestionReviewView,
)

urlpatterns = [
    path('feed/', CommunityFeedView.as_view(), name='post-feed'),
    path('mine/', MyPostsView.as_view(), name='post-mine'),
    path('product/<int:product_id>/', ProductPostsView.as_view(), name='post-by-product'),
    path('admin/all/', CommunityPostAdminListView.as_view(), name='post-admin-list'),
    path('alternatives/', AlternativeSuggestionCreateView.as_view(), name='alt-suggest-create'),
    path('alternatives/admin/', AlternativeSuggestionListView.as_view(), name='alt-suggest-list'),
    path('alternatives/<int:pk>/review/', AlternativeSuggestionReviewView.as_view(), name='alt-suggest-review'),
    path('<int:pk>/react/', PostReactionView.as_view(), name='post-react'),
    path('<int:pk>/review/', CommunityPostReviewView.as_view(), name='post-review'),
    path('', CommunityPostCreateView.as_view(), name='post-create'),
]
