from django.conf import settings
from django.contrib.auth import login, authenticate
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View
from .models import Item, OrderItem, Order, BillingAddress, Payment, Coupon
from .forms import CheckoutForm

import stripe
stripe.api_key = settings.STRIPE_SECRET_KEYS

# Create your views here.
def signup(request):
    if request.method   == 'POST':
        form        = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username        = form.cleaned_data.get('username')
            raw_password    = form.cleaned_data.get('password1')
            user            = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('core:item-list')
    else:
        form        = UserCreationForm()
    context     = {
        'form':form
    }
    return render(request, 'signup.html', context)

def item_list(request):
    context         = {
        'items':Item.objects.all()
    }
    return render(request, 'home-page.html', context)

@login_required
def add_to_cart(request, slug):
    item                    = get_object_or_404(Item, slug=slug)
    order_item, created     = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs        = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order       = order_qs[0]
        # cek jika item yang dipesan itu sudah masuk
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Barang ini telah di update jumlah pesanan anda.")
        else:
            order.items.add(order_item)
            messages.info(request, "Barang ini telah ditambahkan ke keranjang anda.")
            return redirect("core:order-summary")
    else:
        ordered_date    = timezone.now()
        order           = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "Barang ini telah ditambahkan ke keranjang anda.")
    return redirect('core:order-summary')

@login_required
def remove_from_cart(request, slug):
    item            = get_object_or_404(Item, slug=slug)
    order_qs        = Order.objects.filter(
        user=request.user,
        ordered=False,
    )
    if order_qs.exists():
        order       = order_qs[0]
        # cek jika item yang dipesan itu sudah masuk
        if order.items.filter(item__slug=item.slug).exists():
            order_item      = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "Barang ini telah dihapus dari keranjang anda.")
        else:
            messages.info(request, "Barang ini tidak ada di keranjang anda.")
            return redirect('core:order-summary')
    else:
        messages.info(request, "Kamu belum mempunyai pesanannya")
    return redirect('core:order-summary')

@login_required
def remove_single_item_from_cart(request, slug):
    item            = get_object_or_404(Item, slug=slug)
    order_qs        = Order.objects.filter(
        user=request.user,
        ordered=False,
    )
    if order_qs.exists():
        order       = order_qs[0]
        # cek jika item yang dipesan itu sudah masuk
        if order.items.filter(item__slug=item.slug).exists():
            order_item      = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "Jumlah barang ini telah diupdate dari keranjang anda.")
        else:
            messages.info(request, "Barang ini tidak ada di keranjang anda.")
            return redirect('core:order-summary')
    else:
        messages.info(request, "Kamu belum mempunyai pesanannya")
    return redirect('core:order-summary')

# class based view

class HomeView(ListView):
    model           = Item
    paginate_by     = 10
    template_name   = 'home-page.html'

class PaymentView(View):
    def get(self, *args, **kwargs):
        order   = Order.objects.get(user=self.request.user, ordered=False)
        context     = {
            'order':order,
        }
        return render(self.request, "payment.html", context)

    def post(self, *args, **kwargs):
        order   = Order.objects.get(user=self.request.user, ordered=False)
        # order   = get_object_or_404(Order, user=self.request.user, ordered=False)
        token   = self.request.POST.get('stripeToken')
        amount  = int(order.get_total() * 100)

        try:
            # Use Stripe's library to make requests...
            charge  = stripe.Charge.create(
                amount=amount, # sen
                currency="usd",
                source=token
            )

            # buat pembayaran
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # memasukan pembayaran ke pemesanan
            order_items     = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            order.ordered   = True
            order.payment   = payment
            order.save()

            messages.success(self.request, "Pemesananmu telah berhasil")
            return redirect("/")

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body    = json_body
            err     = body.get('error', {})
            messages.error(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request, "Rate limit error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request, "Invalid parameter")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request, "Not authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request, "Network error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(self.request, "Something wrong, please try again")
            return redirect("/")

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            raise e
            messages.error(self.request, "a serious error, we have been notified")
            return redirect("/")


class OrderSummaryView(View):
    def get(self, *args, **kwargs):
        try:
            order       = Order.objects.get(user=self.request.user, ordered=False)
            context     = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.error(self.request, "Kamu belum punya pesanan")
            return redirect('/')

class CheckoutView(View):
    def get(self, *args, **kwargs):
        form        = CheckoutForm
        context     = {
            'form': form
        }
        return render(self.request, 'checkout-page.html', context)
    
    def post(self, *args, **kwargs):
        form        = CheckoutForm(self.request.POST or None)
        try:
            order       = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address          = form.cleaned_data.get('street_address')
                appartement_address     = form.cleaned_data.get('appartement_address')
                country                 = form.cleaned_data.get('country')
                zip                     = form.cleaned_data.get('zip')
                # TODO: tambahkan beberapa function untuk fields
                # same_shipping_address = form.cleaned_data.get('same_shipping_address')
                # save_info             = form.cleaned_data.get('save_info')
                payment_option          = form.cleaned_data.get('payment_option')

                billing_address             = BillingAddress(
                    user                = self.request.user,
                    street_address      = street_address,
                    appartement_address = appartement_address,
                    country             = country,
                    zip                 = zip    
                )
                billing_address.save()
                order.billing_address   = billing_address
                order.save()

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(self.request, "Pemilihan metode pembayaran tidak valid")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.error(self.request, "Kamu belum punya pesanan")
            return redirect('/')

class ItemDetailView(DetailView):
    model           = Item
    template_name   = 'product-page.html'

def get_coupon(request, code):
    try:
        coupon          = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "Kupon tidak tersedia")
        return redirect("core:checkout")

def add_coupon(request, code):
    try:
        order           = Order.objects.get(user=request.user, ordered=False)
        order.coupon    = get_coupon(request, code)
        order.save()
        messages.success(request, "Berhasil menambahkan kupon")
        return redirect("core:checkout")
    except ObjectDoesNotExist:
        messages.info(request, "Kamu belum mempunyai pesanan")
        return redirect("core:checkout")
