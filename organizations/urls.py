from django.urls import path

from . import views

urlpatterns = [
    path('', views.OrganizationListView.as_view(), name='org-list'),
    path('create/', views.OrganizationCreateView.as_view(), name='org-create'),
    path('api/check-slug/', views.OrgSlugAvailabilityView.as_view(), name='org-check-slug'),
    path('<slug:org_slug>/', views.OrganizationDetailView.as_view(), name='org-detail'),
    path('<slug:org_slug>/edit/', views.OrganizationUpdateView.as_view(), name='org-edit'),
    path('<slug:org_slug>/members/', views.OrganizationMembersView.as_view(), name='org-members'),
    path('<slug:org_slug>/members/add/', views.OrganizationAddMemberView.as_view(), name='org-add-member'),
    path('<slug:org_slug>/members/<int:membership_id>/remove/', views.OrganizationRemoveMemberView.as_view(), name='org-remove-member'),
    path('<slug:org_slug>/members/<int:membership_id>/role/', views.OrganizationChangeMemberRoleView.as_view(), name='org-change-role'),
]
