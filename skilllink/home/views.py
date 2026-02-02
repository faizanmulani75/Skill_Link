from django.shortcuts import render
from skills.models import Skill, ProfileSkill

def index(request):

    # Trending skills (Most taught & highest rated)
    trending_profile_skills = ProfileSkill.objects.order_by('-times_taught', '-average_rating')[:6]
    
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
            "role": "Project Manager",
            "image": "https://wallpapers-clan.com/wp-content/uploads/2023/06/cool-pfp-02.jpg",
            "social": {
                "instagram": "https://instagram.com/faizan.m_75",
            }
        },
        {
            "name": "Yash Madane",
            "role": "Backend Developer",
            "image": "https://wallpapers-clan.com/wp-content/uploads/2023/06/cool-pfp-02.jpg",
            "social": {
                "instagram": "https://instagram.com/yash20_06",
                "linkedin": "https://linkedin.com/in/yash-madane",
                "github": "https://github.com/yashmadane06"
            }
        },
        {
            "name": "Mustkim Maniyar",
            "role": "Frontend Developer",
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
