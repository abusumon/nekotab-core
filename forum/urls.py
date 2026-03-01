from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    # ── Page views ──
    path('', views.ForumHomeView.as_view(), name='forum-home'),
    path('new/', views.ForumCreateView.as_view(), name='forum-create'),
    path('thread/<slug:slug>/', views.ForumThreadView.as_view(), name='forum-thread'),

    # ── API: Tags ──
    path('api/tags/', views.ForumTagListAPI.as_view(), name='api-forum-tags'),

    # ── API: Threads ──
    path('api/threads/', views.ForumThreadListAPI.as_view(), name='api-forum-threads'),
    path('api/threads/<slug:slug>/', views.ForumThreadDetailAPI.as_view(), name='api-forum-thread-detail'),
    path('api/threads/<slug:slug>/delete/', views.ForumThreadDeleteAPI.as_view(), name='api-forum-thread-delete'),
    path('api/threads/<slug:slug>/lock/', views.ForumThreadLockAPI.as_view(), name='api-forum-thread-lock'),
    path('api/threads/<slug:slug>/unlock/', views.ForumThreadUnlockAPI.as_view(), name='api-forum-thread-unlock'),

    # ── API: Posts (comments / replies) ──
    path('api/posts/', views.ForumPostCreateAPI.as_view(), name='api-forum-post-create'),
    path('api/posts/<int:pk>/', views.ForumPostUpdateAPI.as_view(), name='api-forum-post-update'),
    path('api/posts/<int:pk>/delete/', views.ForumPostDeleteAPI.as_view(), name='api-forum-post-delete'),

    # ── API: Votes ──
    path('api/votes/', views.ForumVoteAPI.as_view(), name='api-forum-vote'),
    path('api/votes/<int:post_id>/', views.ForumVoteDeleteAPI.as_view(), name='api-forum-vote-delete'),

    # ── API: Bookmarks ──
    path('api/bookmarks/', views.ForumBookmarkListAPI.as_view(), name='api-forum-bookmarks'),
    path('api/bookmarks/<int:thread_id>/', views.ForumBookmarkDeleteAPI.as_view(), name='api-forum-bookmark-delete'),

    # ── API: Reports (mod) ──
    path('api/reports/', views.ForumReportCreateAPI.as_view(), name='api-forum-report'),
    path('api/reports/list/', views.ForumReportListAPI.as_view(), name='api-forum-report-list'),
    path('api/reports/<int:pk>/resolve/', views.ForumReportResolveAPI.as_view(), name='api-forum-report-resolve'),

    # ── API: Badges ──
    path('api/badges/<int:user_id>/', views.UserBadgeListAPI.as_view(), name='api-forum-badges'),
]
