from django.urls import path
from .views import (
    LeaderboardView, GroupLeaderboardView, GroupCreateView,
    MyGroupsView, GroupJoinView, GroupDetailView, GroupLeaveView,
)

urlpatterns = [
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('groups/', GroupCreateView.as_view(), name='group-create'),
    path('groups/mine/', MyGroupsView.as_view(), name='group-mine'),
    path('groups/join/', GroupJoinView.as_view(), name='group-join'),
    path('groups/leaderboard/', GroupLeaderboardView.as_view(), name='group-leaderboard'),
    path('groups/<int:pk>/', GroupDetailView.as_view(), name='group-detail'),
    path('groups/<int:pk>/leave/', GroupLeaveView.as_view(), name='group-leave'),
]
