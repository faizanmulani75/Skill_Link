from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST

# ---------------- APP MODELS & FORMS ----------------
from .models import Profile, Transaction
from .forms import ProfileForm, ProfileSkillForm
from skills.models import Skill, ProfileSkill
from mettings.models import Booking, SwapRequest

# ---------------- EXTERNAL LIBS ----------------
import random
import razorpay

from django.core.mail import send_mail
from django.contrib import messages
from Base.EmailOTP import send_otp



from django.template.loader import render_to_string
from django.conf import settings

# def send_otp_email(email, otp, username):
#     send_mail(
#         subject="Your SkillLink OTP",
#         message=f"Your OTP is {otp}",  # plain text fallback
#         from_email=settings.EMAIL_HOST_USER,
#         recipient_list=[email],
#         fail_silently=False
#     )

# ---------------- LOGIN ----------------

@csrf_protect
def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # defensive: ensure profile exists immediately (avoids template errors)
            from .models import Profile
            Profile.objects.get_or_create(user=user)
            return redirect("dashboard")
        messages.error(request, "Invalid credentials")
    return render(request, "login.html")


# ---------------- REGISTER USER ----------------
def register_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # ✅ Validate passwords
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        # ✅ Check existing username & email
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        # ✅ Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        # ✅ Profile auto-created by signal
        messages.success(request, "Registration successful! Please login.")
        return redirect("login")

    return render(request, "register.html")


# def register_page(request):
#     if request.method == "POST":
#         username = request.POST.get("username")
#         email = request.POST.get("email")
#         password1 = request.POST.get("password1")
#         password2 = request.POST.get("password2")

#         # validations
#         if password1 != password2:
#             messages.error(request, "Passwords do not match")
#             return redirect("register")

#         if User.objects.filter(username=username).exists():
#             messages.error(request, "Username already exists")
#             return redirect("register")

#         if User.objects.filter(email=email).exists():
#             messages.error(request, "Email already registered")
#             return redirect("register")

#         # ✅ Generate OTP
#         otp = send_otp(email)

#         # ✅ Store in session
#         request.session["reg_username"] = username
#         request.session["reg_email"] = email
#         request.session["reg_password"] = password1
#         request.session["reg_otp"] = otp

#         return redirect("verify_otp")

#     return render(request, "register.html")

# ---------------- VERIFY OTP ----------------
# def verify_otp(request):
#     if request.method == "POST":
#         entered_otp = request.POST.get("otp")
#         session_otp = request.session.get("reg_otp")

#         if entered_otp == session_otp:
#             # ✅ create user
#             username = request.session["reg_username"]
#             email = request.session["reg_email"]
#             password = request.session["reg_password"]

#             user = User.objects.create_user(username=username, email=email, password=password)
#             login(request, user)

#             # ✅ clear session data
#             for key in ["reg_username", "reg_email", "reg_password", "reg_otp"]:
#                 request.session.pop(key, None)

#             messages.success(request, "Registration complete!")
#             return redirect("home")

#         else:
#             messages.error(request, "Incorrect OTP")
#             return redirect("verify_otp")

#     return render(request, "verify_otp.html")


# ---------------- RESEND OTP ----------------
# @require_POST
# def resend_otp(request):
#     temp_user = request.session.get("temp_user")
#     if not temp_user:
#         messages.error(request, "Session expired. Please register again.")
#         return redirect("register")

#     # Generate new OTP
#     otp = str(random.randint(100000, 999999))
#     temp_user["otp"] = otp
#     request.session["temp_user"] = temp_user  # update session

#     try:
#         send_otp_email(temp_user["email"], otp, temp_user["username"])
#         messages.success(request, "OTP resent successfully. Please check your email.")
#         return redirect("verify_otp")
#     except Exception as e:
#         print("Resend OTP failed:", e)
#         messages.error(request, "Failed to resend OTP. Try again.")
#         return redirect("verify_otp")



# ---------------- LOGOUT ----------------
@csrf_exempt
def logout_view(request):
    logout(request)
    return redirect("dashboard")


# ---------------- PROFILE ----------------
@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    user_skills = ProfileSkill.objects.filter(profile=profile)
    return render(request, "profile.html", {"profile": profile, "user_skills": user_skills})


@login_required
def profile_edit(request):
    profile = request.user.profile
    if request.method == "POST":
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile_edit")
    else:
        profile_form = ProfileForm(instance=profile)

    skills = profile.skills.all()
    return render(request, "profile_edit.html", {"profile_form": profile_form, "skills": skills})


@login_required
def add_skill(request):
    profile = request.user.profile
    if request.method == "POST":
        skill_name = request.POST.get("skill_name", "").strip()
        experience_level = request.POST.get("experience_level")
        learning_status = request.POST.get("learning_status")
        personal_description = request.POST.get("personal_description", "")
        token_cost = request.POST.get("token_cost", 0)
        available_for_teaching = request.POST.get("available_for_teaching") == "on"
        certificate_url = request.POST.get("certificate_url", "")
        skill_icon = request.FILES.get("skill_icon")

        if skill_name:
            skill_obj, _ = Skill.objects.get_or_create(name=skill_name)
            if skill_icon:
                skill_obj.skill_icon = skill_icon
                skill_obj.save()
            ProfileSkill.objects.create(
                profile=profile,
                skill=skill_obj,
                experience_level=experience_level,
                learning_status=learning_status,
                personal_description=personal_description,
                token_cost=token_cost,
                available_for_teaching=available_for_teaching,
                certificate_url=certificate_url,
            )
            messages.success(request, f"Skill '{skill_name}' added successfully.")
            return redirect("profile_edit")
        else:
            messages.error(request, "Please enter a skill name.")
    return render(request, "skill_add.html")


@login_required
def edit_profile(request):
    profile = request.user.profile
    skills = ProfileSkill.objects.filter(profile=profile)
    if request.method == "POST":
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("edit_profile")
    else:
        profile_form = ProfileForm(instance=profile)
    return render(request, "accounts/edit_profile.html", {"profile_form": profile_form, "skills": skills})


@login_required
def edit_skill(request, pk):
    profile = request.user.profile
    skill_instance = get_object_or_404(ProfileSkill, pk=pk, profile=profile)
    if request.method == "POST":
        form = ProfileSkillForm(request.POST, instance=skill_instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"Skill '{skill_instance.skill.name}' updated successfully.")
            return redirect("profile_edit")
    else:
        form = ProfileSkillForm(instance=skill_instance)
    return render(request, "skill_edit.html", {"form": form, "skill_instance": skill_instance})


@login_required
def delete_skill(request, pk):
    skill = get_object_or_404(ProfileSkill, pk=pk, profile=request.user.profile)
    skill_name = skill.skill.name
    skill.delete()
    messages.success(request, f"Skill '{skill_name}' deleted.")
    return redirect("profile_edit")


# ---------------- TOKENS ----------------
@login_required
def add_tokens_view(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount", 0))
        profile = request.user.profile
        profile.add_tokens(amount)
        messages.success(request, f"{amount} tokens added successfully!")
        return redirect("dashboard")


@login_required
def token_balance(request):
    profile = request.user.profile
    token_history = Transaction.objects.filter(user=profile).order_by("-timestamp")[:10]
    return render(request, "token_balance.html", {"profile": profile, "token_history": token_history})


@login_required
def spend_tokens(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount"))
        profile = request.user.profile
        if profile.deduct_tokens(amount):
            Transaction.objects.create(
                user=profile, amount=amount, transaction_type="spent", description="Spent tokens"
            )
            messages.success(request, f"{amount} tokens spent successfully!")
        else:
            messages.error(request, "Insufficient tokens.")
        return redirect("token_balance")
    return render(request, "spend_tokens.html")


@login_required
def payment_success(request):
    tokens = request.session.get("token_amount")
    order_id = request.session.get("payment_order_id")
    if not tokens or not order_id:
        messages.error(request, "Payment session expired or invalid.")
        return redirect("token_balance")
    profile = request.user.profile
    profile.add_tokens(tokens, description="Purchased tokens via Razorpay")
    request.session.pop("token_amount", None)
    request.session.pop("payment_order_id", None)
    messages.success(request, f"{tokens} tokens added to your account!")
    return redirect("token_balance")


# ---------------- DASHBOARD ----------------
@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # --- Existing Booking Logic ---
    provider_bookings = Booking.objects.filter(provider=profile).order_by("-requested_at")
    incoming_requests = provider_bookings.filter(status="pending")
    accepted_bookings_provider = provider_bookings.filter(status__in=["accepted", "scheduled"])
    past_bookings_provider = provider_bookings.filter(status__in=["completed", "rejected", "cancelled"])

    requester_bookings = Booking.objects.filter(requester=profile).order_by("-requested_at")
    pending_bookings_requester = requester_bookings.filter(status="pending")
    accepted_bookings_requester = requester_bookings.filter(status__in=["accepted", "scheduled"])
    past_bookings_requester = requester_bookings.filter(status__in=["completed", "rejected", "cancelled"])

    user_skills = ProfileSkill.objects.filter(profile=profile)

    # --- Analytics Logic ---
    from django.db.models.functions import TruncDate
    from django.db.models import Sum
    import json
    from django.core.serializers.json import DjangoJSONEncoder

    # Token Trends (Last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    transactions = Transaction.objects.filter(user=profile, timestamp__gte=thirty_days_ago)
    
    daily_stats = transactions.annotate(date=TruncDate('timestamp')).values('date', 'transaction_type').annotate(total=Sum('amount')).order_by('date')
    
    dates = []
    earned_data = []
    spent_data = []
    
    # Process data for Chart.js
    # (Simplified for Hackathon: just listing transactions might be easier, but let's try aggregation)
    # A dictionary to hold date -> {earned: 0, spent: 0}
    stats_dict = {}
    for stat in daily_stats:
        date_str = stat['date'].strftime("%Y-%m-%d")
        if date_str not in stats_dict:
            stats_dict[date_str] = {'earned': 0, 'spent': 0}
        
        if stat['transaction_type'] == 'earned':
            stats_dict[date_str]['earned'] = stat['total']
        elif stat['transaction_type'] == 'spent':
            stats_dict[date_str]['spent'] = stat['total']

    # Fill lists
    sorted_dates = sorted(stats_dict.keys())
    for d in sorted_dates:
        dates.append(d)
        earned_data.append(stats_dict[d]['earned'])
        spent_data.append(stats_dict[d]['spent'])

    context = {
        "profile": profile,
        "user_skills": user_skills,
        "incoming_requests": incoming_requests,
        "accepted_bookings_provider": accepted_bookings_provider,
        "past_bookings_provider": past_bookings_provider,
        "pending_bookings_requester": pending_bookings_requester,
        "accepted_bookings_requester": accepted_bookings_requester,
        "past_bookings_requester": past_bookings_requester,
        "level_progress": profile.get_level_progress(),
        # Analytics
        "analytics_dates": json.dumps(dates, cls=DjangoJSONEncoder),
        "analytics_earned": json.dumps(earned_data, cls=DjangoJSONEncoder),
        "analytics_spent": json.dumps(spent_data, cls=DjangoJSONEncoder),
        "total_meetings_hosted": provider_bookings.filter(status="completed").count(),
        "total_meetings_attended": requester_bookings.filter(status="completed").count(),
        "swaps_pending": SwapRequest.objects.filter(target=profile, status='pending').count(),
    }
    return render(request, "dashboard.html", context)


def public_profile(request, username):
    target_user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=target_user)
    user_skills = ProfileSkill.objects.filter(profile=profile)
    
    # --- Performance/Analytics Logic (similar to dashboard) ---
    from django.db.models.functions import TruncDate
    from django.db.models import Sum, Avg
    import json
    from django.core.serializers.json import DjangoJSONEncoder
    
    # Token Trends (Expertise Gains - Earned Transactions)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    # For public profile, we only show "earned" tokens to demonstrate activity/expertise
    earned_transactions = Transaction.objects.filter(
        user=profile, 
        transaction_type='earned',
        timestamp__gte=thirty_days_ago
    ).annotate(date=TruncDate('timestamp')).values('date').annotate(total=Sum('amount')).order_by('date')
    
    dates = []
    earned_data = []
    for stat in earned_transactions:
        dates.append(stat['date'].strftime("%Y-%m-%d"))
        earned_data.append(stat['total'])

    # Reviews received as a provider
    # Note: We need to import Review here or at the top
    from mettings.models import Review
    reviews_received = Review.objects.filter(booking__provider=profile).order_by('-created_at')

    # Meeting Stats
    total_meetings_hosted = Booking.objects.filter(provider=profile, status="completed").count()
    total_meetings_attended = Booking.objects.filter(requester=profile, status="completed").count()

    context = {
        "profile": profile,
        "user_skills": user_skills,
        "reviews_received": reviews_received,
        "total_meetings_hosted": total_meetings_hosted,
        "total_meetings_attended": total_meetings_attended,
        "analytics_dates": json.dumps(dates, cls=DjangoJSONEncoder),
        "analytics_earned": json.dumps(earned_data, cls=DjangoJSONEncoder),
    }
    return render(request, "public_profile.html", context)
