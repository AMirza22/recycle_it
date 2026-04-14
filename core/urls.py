from django.urls import path
from . import views

urlpatterns = [

    # ── Auth ──────────────────────────────────────────────────────────────────
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # ── Donor Facing (public) ─────────────────────────────────────────────────
    path('donate/', views.donate_view, name='donate'),
    path('donate/success/', views.donate_success_view, name='donate_success'),

    # ── Donations (staff) ─────────────────────────────────────────────────────
    path('donations/', views.donations_list_view, name='donations_list'),
    path('donations/<int:donation_id>/', views.donation_review_view, name='donation_review'),
    path('donations/<int:donation_id>/approve/', views.donation_approve_view, name='donation_approve'),
    path('donations/<int:donation_id>/reject/', views.donation_reject_view, name='donation_reject'),
    path('donations/<int:donation_id>/assign/', views.donation_assign_view, name='donation_assign'),
    path('donations/<int:donation_id>/unassign/', views.donation_unassign_view, name='donation_unassign'),

    # ── Collections (staff) ───────────────────────────────────────────────────
    path('collections/', views.collections_list_view, name='collections_list'),
    path('collections/new/', views.collection_create_view, name='collection_create'),
    path('collections/<int:collection_id>/', views.collection_detail_view, name='collection_detail'),
    path('collections/<int:collection_id>/add-donation/', views.collection_add_donation_view, name='collection_add_donation'),
    path('collections/<int:collection_id>/update-status/', views.collection_update_status_view, name='collection_update_status'),
    path('donations/<int:donation_id>/remove-from-collection/', views.collection_remove_donation_view, name='collection_remove_donation'),

    # ── Route Planner (staff) ─────────────────────────────────────────────────
    path('route-planner/', views.route_planner_index_view, name='route_planner_index'),
    path('route-planner/<int:collection_id>/', views.route_planner_view, name='route_planner'),

    # ── KPI Dashboard (staff) ─────────────────────────────────────────────────
    path('kpi/', views.kpi_dashboard_view, name='kpi_dashboard'),

    # ── User Management (admin only) ──────────────────────────────────────────
    path('users/', views.users_list_view, name='users_list'),
    path('users/new/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
]