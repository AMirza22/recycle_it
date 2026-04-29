from django import forms
import re
from django.contrib.auth.forms import AuthenticationForm
from .services.route_service import RouteService

# ── Login Form ────────────────────────────────────────────────────────────────

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'placeholder': 'staff@recycle-it.org.uk',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••••••',
        })
    )

    error_messages = {
        'invalid_login': 'Invalid email or password. Please try again.',
        'inactive': 'This account is inactive.',
    }


# ── Donor Submission Form ─────────────────────────────────────────────────────

class DonorSubmissionForm(forms.Form):

    # Donor details
    company_name = forms.CharField(
        max_length=255,
        label='Company Name',
        widget=forms.TextInput(attrs={'placeholder': 'Enter company or organisation name'})
    )
    contact_person = forms.CharField(
        max_length=255,
        label='Contact Person',
        widget=forms.TextInput(attrs={'placeholder': 'Full name'})
    )
    contact_email = forms.EmailField(
        label='Contact Email',
        widget=forms.EmailInput(attrs={'placeholder': 'email@example.com'})
    )
    contact_phone = forms.CharField(
        max_length=20,
        label='Contact Phone',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '01234 567890'})
    )
    street_address = forms.CharField(
        max_length=255,
        label='Street Address',
        widget=forms.TextInput(attrs={'placeholder': '10 Market Street'})
    )
    city = forms.CharField(
        max_length=100,
        label='City / Town',
        widget=forms.TextInput(attrs={'placeholder': 'Bolton'})
    )
    postcode = forms.CharField(
        max_length=10,
        label='Postcode',
        widget=forms.TextInput(attrs={'placeholder': 'BL1 1AA'})
    )
    preferred_collection_datetime = forms.DateTimeField(
        label='Preferred Collection Date / Time',
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
    )

    # Item quantities
    qty_processor = forms.IntegerField(
        min_value=0, initial=0, required=False,
        label='Processors (CPU, Tower, Desktop, Tablet, Laptop)',
        widget=forms.NumberInput(attrs={'min': 0})
    )
    qty_monitor = forms.IntegerField(
        min_value=0, initial=0, required=False,
        label='TFT/LCD Flat Screen Monitors',
        widget=forms.NumberInput(attrs={'min': 0})
    )
    qty_printer = forms.IntegerField(
        min_value=0, initial=0, required=False,
        label='Printers (desktop inkjet / office laser, fax)',
        widget=forms.NumberInput(attrs={'min': 0})
    )
    qty_accessories = forms.IntegerField(
        min_value=0, initial=0, required=False,
        label='Accessories (mice, cables, keyboards)',
        widget=forms.NumberInput(attrs={'min': 0})
    )
    qty_networking = forms.IntegerField(
        min_value=0, initial=0, required=False,
        label='Networking Equipment (routers, switches, hubs)',
        widget=forms.NumberInput(attrs={'min': 0})
    )
    qty_mobile = forms.IntegerField(
        min_value=0, initial=0, required=False,
        label='Mobile Phones',
        widget=forms.NumberInput(attrs={'min': 0})
    )
    qty_other = forms.IntegerField(
        min_value=0, initial=0, required=False,
        label='Other items',
        widget=forms.NumberInput(attrs={'min': 0})
    )
    other_description = forms.CharField(
        max_length=255,
        required=False,
        label='Description of other items',
        widget=forms.TextInput(attrs={'placeholder': 'Describe other items if applicable'})
    )

    data_destruction_required = forms.ChoiceField(
        choices=[('no', 'No'), ('yes', 'Yes')],
        initial='no',
        label='Data Destruction Certificate Required? (may take 2–4 weeks)',
        widget=forms.RadioSelect,
    )
    notes = forms.CharField(
        required=False,
        label='Additional Notes / Special Instructions',
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Any additional information for the collection team...'
        })
    )

    def clean(self):
        cleaned_data = super().clean()

        # Validate at least one item quantity
        qty_fields = [
            'qty_processor', 'qty_monitor', 'qty_printer',
            'qty_accessories', 'qty_networking', 'qty_mobile', 'qty_other',
        ]
        total = sum(cleaned_data.get(f) or 0 for f in qty_fields)
        if total == 0:
            raise forms.ValidationError(
                'Please enter at least one item for collection.'
            )

        # Geocode the composed address — only if postcode passed validation
        street = cleaned_data.get('street_address', '')
        city = cleaned_data.get('city', '')
        postcode = cleaned_data.get('postcode', '')

        if street and city and postcode:
            composed = f"{street}, {city}, {postcode}"
            coords = RouteService.geocode_address(composed)
            if coords is None:
                raise forms.ValidationError(
                    'We could not locate this address. Please check all fields '
                    'are correct and the postcode is valid.'
                )
            self._geocoded_lon = coords[0]
            self._geocoded_lat = coords[1]

        return cleaned_data
    
    def clean_postcode(self):
        postcode = self.cleaned_data.get('postcode', '').strip().upper()
        pattern = r'^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}$'
        if not re.match(pattern, postcode, re.IGNORECASE):
            raise forms.ValidationError(
                'Enter a valid UK postcode (e.g. BL1 1AA).'
            )
        return postcode

    def get_donor_data(self):
        return {
            'company_name': self.cleaned_data['company_name'],
            'contact_person': self.cleaned_data['contact_person'],
            'contact_email': self.cleaned_data['contact_email'],
            'contact_phone': self.cleaned_data.get('contact_phone', ''),
        }

    def get_donation_data(self):
        return {
            'street_address': self.cleaned_data['street_address'],
            'city': self.cleaned_data['city'],
            'postcode': self.cleaned_data['postcode'],
            'latitude': getattr(self, '_geocoded_lat', None),
            'longitude': getattr(self, '_geocoded_lon', None),
            'preferred_collection_datetime': self.cleaned_data.get('preferred_collection_datetime'),
            'data_destruction_required': self.cleaned_data['data_destruction_required'] == 'yes',
            'notes': self.cleaned_data.get('notes', ''),
        }

    def get_items_data(self):
        mapping = [
            ('qty_processor', 'PROCESSOR'),
            ('qty_monitor', 'MONITOR'),
            ('qty_printer', 'PRINTER'),
            ('qty_accessories', 'ACCESSORIES'),
            ('qty_networking', 'NETWORKING'),
            ('qty_mobile', 'MOBILE'),
            ('qty_other', 'OTHER'),
        ]
        items = []
        for field_name, category in mapping:
            qty = self.cleaned_data.get(field_name) or 0
            if qty > 0:
                items.append({
                    'category': category,
                    'quantity': qty,
                    'weight': None,
                    'other_description': self.cleaned_data.get('other_description', '')
                    if category == 'OTHER' else '',
                })
        return items


# ── User Management Form ──────────────────────────────────────────────────────

class UserForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        label='First Name',
        widget=forms.TextInput(attrs={'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        label='Last Name',
        widget=forms.TextInput(attrs={'placeholder': 'Last name'})
    )
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'placeholder': 'staff@recycle-it.org.uk'})
    )
    is_admin = forms.BooleanField(
        required=False,
        label='Administrator access',
    )
    password = forms.CharField(
        required=False,
        label='Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Leave blank to keep existing'})
    )
    password_confirm = forms.CharField(
        required=False,
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat password'})
    )

    def __init__(self, *args, editing=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.editing = editing
        if not editing:
            self.fields['password'].required = True
            self.fields['password_confirm'].required = True
            self.fields['password'].widget.attrs['placeholder'] = 'Choose a password'
            self.fields['password_confirm'].widget.attrs['placeholder'] = 'Repeat password'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('password_confirm')

        if password or not self.editing:
            if password != confirm:
                raise forms.ValidationError('Passwords do not match.')
            if password and len(password) < 8:
                raise forms.ValidationError('Password must be at least 8 characters.')

        return cleaned_data


# ── System Settings Form ──────────────────────────────────────────────────────

class SystemSettingsForm(forms.Form):
    co2_per_litre_kg = forms.FloatField(
        label='CO₂ per litre of fuel (kg/L)',
        min_value=0.1,
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    fuel_efficiency_km_per_litre = forms.FloatField(
        label='Fuel efficiency (km/L)',
        min_value=0.1,
        widget=forms.NumberInput(attrs={'step': '0.1'})
    )


# ── Collection Form ───────────────────────────────────────────────────────────

class CollectionForm(forms.Form):
    scheduled_datetime = forms.DateTimeField(
        label='Scheduled Date / Time',
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
    )
    driver_name = forms.CharField(
        max_length=255,
        required=False,
        label='Driver Name',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. John Smith'})
    )
    vehicle_id = forms.CharField(
        max_length=50,
        required=False,
        label='Vehicle ID',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. VAN-01'})
    )
    status = forms.ChoiceField(
        choices=[
            ('draft', 'Draft'),
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        label='Status',
    )