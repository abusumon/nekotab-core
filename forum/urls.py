from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    # Page views
    path('', views.ForumHomeView.as_view(), name='forum-home'),
    path('new/', views.ForumCreateView.as_view(), name='forum-create'),
    path('thread/<slug:slug>/', views.ForumThreadView.as_view(), name='forum-thread'),

    # API endpoints
    path('api/tags/', views.ForumTagListAPI.as_view(), name='api-forum-tags'),
    path('api/threads/', views.ForumThreadListAPI.as_view(), name='api-forum-threads'),
    path('api/threads/<slug:slug>/', views.ForumThreadDetailAPI.as_view(), name='api-forum-thread-detail'),
    path('api/posts/', views.ForumPostCreateAPI.as_view(), name='api-forum-post-create'),
    path('api/posts/<int:pk>/', views.ForumPostUpdateAPI.as_view(), name='api-forum-post-update'),
    path('api/votes/', views.ForumVoteAPI.as_view(), name='api-forum-vote'),
    path('api/votes/<int:post_id>/', views.ForumVoteDeleteAPI.as_view(), name='api-forum-vote-delete'),
    path('api/bookmarks/', views.ForumBookmarkListAPI.as_view(), name='api-forum-bookmarks'),
    path('api/bookmarks/<int:thread_id>/', views.ForumBookmarkDeleteAPI.as_view(), name='api-forum-bookmark-delete'),
    path('api/reports/', views.ForumReportCreateAPI.as_view(), name='api-forum-report'),
    path('api/badges/<int:user_id>/', views.UserBadgeListAPI.as_view(), name='api-forum-badges'),
]
