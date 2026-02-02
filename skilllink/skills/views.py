from django.shortcuts import render, get_object_or_404
from .models import Skill, ProfileSkill
from accounts.models import Profile

from django.shortcuts import render

from django.db.models import Prefetch



def skill_list(request):
    # Prefetch ProfileSkill objects for each skill with related profile and user
    if request.user.is_authenticated:
        qs = ProfileSkill.objects.select_related('profile', 'profile__user').exclude(profile__user=request.user)
    else:
        qs = ProfileSkill.objects.select_related('profile', 'profile__user')

    skills = Skill.objects.prefetch_related(
        Prefetch(
            'profileskill_set',  # reverse relation from Skill to ProfileSkill
            queryset=qs
        )
    ).all()
    
    context = {
        'skills': skills
    }
    
    return render(request, "skills_available.html", context)



def skill_detail(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)
    providers_list = []
    for profile in skill.profiles_offered.all():
        try:
            profile_skill = ProfileSkill.objects.get(profile=profile, skill=skill)
        except ProfileSkill.DoesNotExist:
            profile_skill = None
        providers_list.append({
            "profile": profile,
            "profile_skill": profile_skill
        })

    return render(request, "skills/skill_detail.html", {"skill": skill, "providers": providers_list})



def skills_available(request):
    # Example: show all skills
    skills = ProfileSkill.objects.filter(available_for_teaching=True)
    return render(request, 'skills_available.html', {'skills': skills})

def share_skill(request):
    # Example: show top tutors or skill sharers
    top_tutors = ProfileSkill.objects.filter(available_for_teaching=True)[:10]
    return render(request, 'share_skill.html', {'top_tutors': top_tutors})

