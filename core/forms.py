from django import forms
from django_countries.fields import CountryField

PAYMENT_CHOICES     = (
    ('S', 'Stripe'),
    # ('P', 'PayPal'),
)

class CheckoutForm(forms.Form):
    street_address          = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Jl. 123',
    }))
    appartement_address     = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Apartemen atau perumahan',
    }))
    country                 = CountryField(blank_label='(pilih negara)').formfield()
    zip                     = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Kode pos',
    }))
    # same_shipping_address    = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    # save_info               = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    payment_option          = forms.ChoiceField(widget=forms.RadioSelect, choices=PAYMENT_CHOICES)