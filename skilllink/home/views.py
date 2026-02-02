from django.shortcuts import render
from skills.models import Skill, ProfileSkill
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import PlatformReview # Import the new model

def index(request):

    # Trending skills (Most taught & highest rated)
    trending_profile_skills = ProfileSkill.objects.order_by('-times_taught', '-average_rating')
    if request.user.is_authenticated:
        trending_profile_skills = trending_profile_skills.exclude(profile__user=request.user)
    trending_profile_skills = trending_profile_skills[:6]
    
    trending_cards = []
    for ps in trending_profile_skills:
        trending_cards.append({
            'skill': ps.skill,
            'provider': ps,
            'profile_skill': ps,
        })

    # Top tutors
    from accounts.models import Profile
    top_tutors = Profile.objects.filter(rating__gt=0).order_by('-rating')[:4]

    # Reviews from Database
    from mettings.models import Review
    latest_reviews = Review.objects.select_related('booking__requester__user').order_by('-created_at')[:6]
    reviews = []
    for r in latest_reviews:
        reviews.append({
            "name": r.booking.requester.user.get_full_name() or r.booking.requester.user.username,
            "text": r.comment,
            "profile_pic": r.booking.requester.profile_pic.url if r.booking.requester.profile_pic else "https://res.cloudinary.com/dctwxqpeo/image/upload/v1757868228/default_ehmhxs.png",
            "role": f"Learned {r.booking.skill.name}"
        })

    # Fallback to static if no reviews yet
    # if not reviews:
    #     reviews = [
    #         {"name": "yash", "text": "SkillLink helped me learn Python fast!",
    #          "profile_pic": "https://res.cloudinary.com/dctwxqpeo/image/upload/v1757868228/default_ehmhxs.png", "role": "SkillLink User"},
    #         {"name": "Faizan", "text": "Amazing platform for peer-to-peer skill sharing.",
    #          "profile_pic": "https://res.cloudinary.com/dctwxqpeo/image/upload/v1757868228/default_ehmhxs.png", "role": "SkillLink User"},
    #     ]

    # Team Section
    team = [
        {
            "name": "Faizan Mulani",
            "role": "Founder",
            "image": "https://wallpapers-clan.com/wp-content/uploads/2023/06/cool-pfp-02.jpg",
            "social": {
                "instagram": "https://instagram.com/faizan.m_75",
            }
        },
        {
            "name": "Yash Madane",
            "role": "Co-Founder",
            "image": "https://wallpapers-clan.com/wp-content/uploads/2023/06/cool-pfp-02.jpg",
            "social": {
                "instagram": "https://instagram.com/yash20_06",
                "linkedin": "https://linkedin.com/in/yash-madane",
                "github": "https://github.com/yashmadane06"
            }
        },
        {
            "name": "Mustkim Maniyar",
            "role": "Co-Founder",
            "image": "https://wallpapers-clan.com/wp-content/uploads/2023/06/cool-pfp-02.jpg",
            "social": {
                "instagram": "https://instagram.com/_mustkim_maniyar_585",
            }
        },
        # {
        #     "name": "Rushabh Patekar",
        #     "role": "UI/UX Designer",
        #     "image": "https://wallpapers-clan.com/wp-content/uploads/2023/06/cool-pfp-02.jpg",
        #     "social": {
        #         "instagram": "https://instagram.com/rushabh_patekar_",
        #     }
        # },
        # {
        #     "name": "Dipak Supekar",
        #     "role": "QA & Testing",
        #     "image": "https://wallpapers-clan.com/wp-content/uploads/2023/06/cool-pfp-02.jpg",
        #     "social": {
        #         "instagram": "https://instagram.com/dipaksupekar_09",
        #     }
        # },
    ]

    context = {
        'trending_cards': trending_cards,  
        'top_tutors': top_tutors,
        'reviews': reviews,
        'team': team,
    }

    return render(request, 'index.html', context)


@login_required
@require_POST
def submit_platform_review(request):
    import json
    try:
        data = json.loads(request.body)
        content = data.get('content')
        rating = int(data.get('rating', 5))

        if not content:
            return JsonResponse({'success': False, 'message': 'Review content is required.'})

        PlatformReview.objects.create(
            user=request.user,
            content=content,
            rating=rating
        )

        # Update profile
        profile = request.user.profile
        profile.has_reviewed_platform = True
        profile.save()

        return JsonResponse({'success': True, 'message': 'Review submitted successfully!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
