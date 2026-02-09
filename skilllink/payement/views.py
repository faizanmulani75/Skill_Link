from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
import razorpay
from django.contrib import messages
from .models import Profile

@login_required
def initiate_payment(request):
    if request.method == "POST":
        tokens = request.POST.get("tokens")
        if not tokens:
            messages.error(request, "Please enter a valid number of tokens.")
            return redirect('token_balance')

        try:
            tokens = int(tokens)
            if tokens <= 0:
                messages.error(request, "Token amount must be greater than zero.")
                return redirect('token_balance')
            if tokens > 1000:
                messages.error(request, "Maximum 1000 tokens can be purchased at once.")
                return redirect('token_balance')
        except (TypeError, ValueError):
            messages.error(request, "Please enter a valid integer for tokens.")
            return redirect('token_balance')

        amount_in_paise = tokens * 100

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": 1,
        })

        request.session['token_amount'] = tokens
        request.session['payment_order_id'] = order['id']

        return render(
            request,
            "checkout.html",
            {
                "order": order,
                "amount": tokens,
                "key_id": settings.RAZORPAY_KEY_ID,
            },
        )

    # If method is GET or anything else, redirect to token balance
    return redirect('token_balance')
