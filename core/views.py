from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.mail import send_mail
from functools import wraps

from .forms import (
    EmailAuthenticationForm,
    DonorSubmissionForm,
    UserForm,
    SystemSettingsForm,
    CollectionForm,
)
from .models import (
    Donation, Collection, EmissionRecord, SystemSettings, Item
)
from .services.auth_service import AuthService
from .services.donation_service import DonationService
from .services.collection_service import CollectionService
from .services.emissions_service import EmissionsService
from .services.route_service import RouteService


# ══════════════════════════════════════════════════════════════════════════════
#  DECORATORS
# ══════════════════════════════════════════════════════════════════════════════

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin:
            return HttpResponseForbidden('You do not have permission to access this page.')
        return view_func(request, *args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH VIEWS
# ══════════════════════════════════════════════════════════════════════════════

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            remember_me = request.POST.get('remember_me')
            if not remember_me:
                request.session.set_expiry(0)
            login(request, user)
            return redirect('dashboard')
    else:
        form = EmailAuthenticationForm(request)

    return render(request, 'core/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def dashboard_view(request):
    pending_donations = Donation.objects.filter(
        approval_status='awaiting_review'
    ).count()

    scheduled_collections = Collection.objects.filter(
        status='scheduled'
    ).count()

    emission_records = EmissionRecord.objects.all()
    total_co2_saved = sum(r.co2_kg for r in emission_records)

    total_devices_diverted = Item.objects.filter(
        donation__collection__status='completed'
    ).values_list('quantity', flat=True)
    devices_diverted = sum(total_devices_diverted)

    recent_donations = DonationService.get_donations()[:5]

    upcoming_collections = Collection.objects.filter(
        status__in=['draft', 'scheduled', 'in_progress']
    ).order_by('scheduled_datetime')[:3]

    context = {
        'pending_donations': pending_donations,
        'scheduled_collections': scheduled_collections,
        'total_co2_saved': round(total_co2_saved, 2),
        'devices_diverted': devices_diverted,
        'recent_donations': recent_donations,
        'upcoming_collections': upcoming_collections,
    }
    return render(request, 'core/dashboard.html', context)


# ══════════════════════════════════════════════════════════════════════════════
#  DONOR FACING VIEWS (public — no login required)
# ══════════════════════════════════════════════════════════════════════════════

def donate_view(request):
    if request.method == 'POST':
        form = DonorSubmissionForm(request.POST)
        if form.is_valid():
            donation, reference_id = DonationService.create_donation(
                form.get_donor_data(),
                form.get_donation_data(),
                form.get_items_data(),
            )
            DonationService.send_confirmation_email(donation, reference_id)
            request.session['reference_id'] = reference_id
            return redirect('donate_success')
            
    else:
        form = DonorSubmissionForm()
        

    return render(request, 'core/donate.html', {'form': form})


def donate_success_view(request):
    reference_id = request.session.pop('reference_id', None)
    if not reference_id:
        return redirect('donate')
    return render(request, 'core/donate_success.html', {'reference_id': reference_id})


# ══════════════════════════════════════════════════════════════════════════════
#  DONATION MANAGEMENT VIEWS (staff)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def donations_list_view(request):
    filters = {
        'approval_status': request.GET.get('approval_status', ''),
        'status': request.GET.get('status', ''),
    }
    filters = {k: v for k, v in filters.items() if v}
    donations = DonationService.get_donations(filters=filters)
    return render(request, 'core/donations_list.html', {
        'donations': donations,
        'filters': filters,
    })


@login_required
def donation_review_view(request, donation_id):
    try:
        donation = DonationService.get_donation_by_id(donation_id)
    except Donation.DoesNotExist:
        messages.error(request, 'Donation not found.')
        return redirect('donations_list')

    unassigned_collections = Collection.objects.filter(
        status__in=['draft', 'scheduled']
    ).order_by('-created_at')

    return render(request, 'core/donation_review.html', {
        'donation': donation,
        'unassigned_collections': unassigned_collections,
    })


@login_required
def donation_approve_view(request, donation_id):
    if request.method == 'POST':
        try:
            donation = DonationService.toggle_approval_status(donation_id, 'approved')
            DonationService.send_approval_email(donation)
            messages.success(request, f'Donation {donation.reference_id} approved.')
        except Donation.DoesNotExist:
            messages.error(request, 'Donation not found.')
    return redirect('donation_review', donation_id=donation_id)


@login_required
def donation_reject_view(request, donation_id):
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        if not rejection_reason:
            messages.error(request, 'A rejection reason is required.')
            return redirect('donation_review', donation_id=donation_id)
        try:
            donation = DonationService.toggle_approval_status(
                donation_id, 'rejected', rejection_reason=rejection_reason
            )
            DonationService.send_rejection_email(donation, rejection_reason)
            messages.success(request, f'Donation {donation.reference_id} rejected.')
        except Donation.DoesNotExist:
            messages.error(request, 'Donation not found.')
    return redirect('donation_review', donation_id=donation_id)


@login_required
def donation_assign_view(request, donation_id):
    if request.method == 'POST':
        collection_id = request.POST.get('collection_id')
        if collection_id:
            success, msg = CollectionService.add_donation(collection_id, donation_id)
            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
        else:
            messages.error(request, 'No collection selected.')
    return redirect('donation_review', donation_id=donation_id)


@login_required
def donation_unassign_view(request, donation_id):
    if request.method == 'POST':
        success, msg = CollectionService.remove_donation(donation_id)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect('donation_review', donation_id=donation_id)


# ══════════════════════════════════════════════════════════════════════════════
#  COLLECTION MANAGEMENT VIEWS (staff)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def collections_list_view(request):
    filters = {'status': request.GET.get('status', '')}
    filters = {k: v for k, v in filters.items() if v}
    collections = CollectionService.get_collections(filters=filters)
    return render(request, 'core/collections_list.html', {
        'collections': collections,
        'filters': filters,
        'status_choices': Collection.STATUS_CHOICES,
    })


@login_required
def collection_create_view(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = CollectionService.create_collection(
                user=request.user,
                scheduled_datetime=form.cleaned_data.get('scheduled_datetime'),
                driver_name=form.cleaned_data.get('driver_name', ''),
                vehicle_id=form.cleaned_data.get('vehicle_id', ''),
                status=form.cleaned_data.get('status', 'draft'),
            )
            messages.success(request, f'Collection #{collection.pk} created.')
            return redirect('collection_detail', collection_id=collection.pk)
    else:
        form = CollectionForm(initial={'status': 'draft'})

    return render(request, 'core/collection_create.html', {'form': form})


@login_required
def collection_detail_view(request, collection_id):
    try:
        collection = CollectionService.get_collection_by_id(collection_id)
    except Collection.DoesNotExist:
        messages.error(request, 'Collection not found.')
        return redirect('collections_list')

    stats = CollectionService.get_collection_stats(collection)
    emission_record = EmissionsService.get_emission_record(collection_id)
    unassigned_donations = CollectionService.get_unassigned_donations()

    return render(request, 'core/collection_detail.html', {
        'collection': collection,
        'stats': stats,
        'emission_record': emission_record,
        'unassigned_donations': unassigned_donations,
    })


@login_required
def collection_add_donation_view(request, collection_id):
    if request.method == 'POST':
        donation_id = request.POST.get('donation_id')
        if donation_id:
            success, msg = CollectionService.add_donation(collection_id, donation_id)
            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
        else:
            messages.error(request, 'No donation selected.')
    return redirect('collection_detail', collection_id=collection_id)


@login_required
def collection_remove_donation_view(request, donation_id):
    if request.method == 'POST':
        donation = Donation.objects.get(pk=donation_id)
        collection_id = donation.collection_id
        success, msg = CollectionService.remove_donation(donation_id)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect('collection_detail', collection_id=collection_id)
    return redirect('collections_list')


@login_required
def collection_update_status_view(request, collection_id):
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            collection = CollectionService.update_status(collection_id, new_status)
            if new_status == 'completed':
                collection.donations.all().update(status='collected')
                EmissionsService.calculate_emissions(collection_id)
                messages.success(request, 'Collection marked as complete. Emissions calculated.')
            else:
                messages.success(request, f'Status updated to {new_status}.')
    return redirect('collection_detail', collection_id=collection_id)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTE PLANNER VIEWS (staff)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def route_planner_index_view(request):
    collections = Collection.objects.filter(
        status__in=['draft', 'scheduled']
    ).prefetch_related('donations').order_by('-created_at')
    return render(request, 'core/route_planner_index.html', {
        'collections': collections,
    })


@login_required
def route_planner_view(request, collection_id):
    try:
        collection = CollectionService.get_collection_by_id(collection_id)
    except Collection.DoesNotExist:
        messages.error(request, 'Collection not found.')
        return redirect('route_planner_index')

    route_result = None
    estimated_emissions = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'optimise':
            route_result = RouteService.optimise_route(collection_id)
            if route_result['optimised']:
                messages.success(request, 'Route optimised successfully via OpenRouteService.')
            else:
                messages.warning(request, 'Route optimisation unavailable — showing original order.')

        elif action == 'save_distance':
            distance = request.POST.get('total_distance_km')
            if distance:
                collection.total_distance_km = float(distance)
                collection.save()
                messages.success(request, f'Distance saved: {distance} km')

        elif action == 'confirm_schedule':
            CollectionService.update_status(collection_id, 'scheduled')
            EmissionsService.calculate_emissions(collection_id)
            messages.success(request, 'Collection scheduled and emissions estimated.')
            return redirect('collection_detail', collection_id=collection_id)

    else:
        route_result = RouteService.get_route(collection_id)

    if collection.total_distance_km:
        emission_record = EmissionsService.get_emission_record(collection_id)
        if not emission_record:
            from .models import SystemSettings
            try:
                settings_obj = SystemSettings.objects.get(pk=1)
                fuel_eff = settings_obj.fuel_efficiency_km_per_litre
                co2_rate = settings_obj.co2_per_litre_kg
            except SystemSettings.DoesNotExist:
                fuel_eff, co2_rate = 8.8, 2.31
            fuel = collection.total_distance_km / fuel_eff
            estimated_emissions = round(fuel * co2_rate, 2)
        else:
            estimated_emissions = emission_record.co2_kg

    unassigned_donations = CollectionService.get_unassigned_donations()

    return render(request, 'core/route_planner.html', {
        'collection': collection,
        'route_result': route_result,
        'estimated_emissions': estimated_emissions,
        'unassigned_donations': unassigned_donations,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  KPI DASHBOARD VIEW (staff)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def kpi_dashboard_view(request):
    emission_records = EmissionRecord.objects.select_related('collection').all()

    total_co2 = round(sum(r.co2_kg for r in emission_records), 2)
    total_distance = round(sum(r.distance_km for r in emission_records), 2)
    total_fuel = round(sum(r.fuel_litres_used for r in emission_records), 2)
    completed_collections = Collection.objects.filter(status='completed').count()
    devices_diverted = sum(
        Item.objects.filter(
            donation__collection__status='completed'
        ).values_list('quantity', flat=True)
    )

    monthly_data = {}
    for record in emission_records:
        month = record.calculated_at.strftime('%b %Y')
        monthly_data[month] = monthly_data.get(month, 0) + record.co2_kg

    category_totals = {}
    completed_items = Item.objects.filter(
        donation__collection__status='completed'
    )
    for item in completed_items:
        category_totals[item.category] = category_totals.get(item.category, 0) + item.quantity

    fuel_table = emission_records.order_by('-collection__scheduled_datetime')[:10]

    try:
        system_settings = SystemSettings.objects.get(pk=1)
    except SystemSettings.DoesNotExist:
        system_settings = None

    if request.method == 'POST' and request.user.is_admin:
        settings_form = SystemSettingsForm(request.POST)
        if settings_form.is_valid():
            obj, created = SystemSettings.objects.get_or_create(pk=1)
            obj.co2_per_litre_kg = settings_form.cleaned_data['co2_per_litre_kg']
            obj.fuel_efficiency_km_per_litre = settings_form.cleaned_data['fuel_efficiency_km_per_litre']
            obj.save()
            messages.success(request, 'Emissions formula settings updated.')
            return redirect('kpi_dashboard')
    else:
        initial = {}
        if system_settings:
            initial = {
                'co2_per_litre_kg': system_settings.co2_per_litre_kg,
                'fuel_efficiency_km_per_litre': system_settings.fuel_efficiency_km_per_litre,
            }
        settings_form = SystemSettingsForm(initial=initial)

    return render(request, 'core/kpi_dashboard.html', {
        'total_co2': total_co2,
        'total_distance': total_distance,
        'total_fuel': total_fuel,
        'completed_collections': completed_collections,
        'devices_diverted': devices_diverted,
        'monthly_data': monthly_data,
        'category_totals': category_totals,
        'fuel_table': fuel_table,
        'settings_form': settings_form,
        'system_settings': system_settings,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT VIEWS (admin only)
# ══════════════════════════════════════════════════════════════════════════════

@admin_required
def users_list_view(request):
    from .models import User
    users = User.objects.all().order_by('email')
    return render(request, 'core/users_list.html', {'users': users})


@admin_required
def user_create_view(request):
    if request.method == 'POST':
        form = UserForm(request.POST, editing=False)
        if form.is_valid():
            try:
                AuthService.create_user(
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    is_admin=form.cleaned_data.get('is_admin', False),
                )
                messages.success(request, 'User created successfully.')
                return redirect('users_list')
            except ValueError as e:
                form.add_error('email', str(e))
    else:
        form = UserForm(editing=False)

    return render(request, 'core/user_form.html', {'form': form, 'editing': False})


@admin_required
def user_edit_view(request, user_id):
    from .models import User
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('users_list')

    if request.method == 'POST':
        form = UserForm(request.POST, editing=True)
        if form.is_valid():
            try:
                AuthService.edit_user(
                    user_id=user_id,
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    is_admin=form.cleaned_data.get('is_admin', False),
                    password=form.cleaned_data.get('password') or None,
                )
                messages.success(request, 'User updated successfully.')
                return redirect('users_list')
            except ValueError as e:
                form.add_error('email', str(e))
    else:
        form = UserForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'is_admin': user.is_admin,
        }, editing=True)

    return render(request, 'core/user_form.html', {
        'form': form,
        'editing': True,
        'edit_user': user,
    })


@admin_required
def user_delete_view(request, user_id):
    if request.method == 'POST':
        if user_id == request.user.pk:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('users_list')
        success = AuthService.delete_user(user_id)
        if success:
            messages.success(request, 'User deleted.')
        else:
            messages.error(request, 'User not found.')
    return redirect('users_list')