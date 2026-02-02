# forms.py
from django import forms
from .models import Profile
from skills.models import ProfileSkill, Skill



class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_pic', 'location']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ProfileSkillForm(forms.ModelForm):
    skill_name = forms.CharField(max_length=100, required=True, label="Skill Name")

    class Meta:
        model = ProfileSkill
        fields = [
            'experience_level',
            'learning_status',
            'personal_description',
            'available_for_teaching',
            'token_cost',
            'desired_exchange_skills',
        ]
        widgets = {
             'desired_exchange_skills': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['skill_name'].initial = self.instance.skill.name

    def save(self, commit=True):
        skill_name = self.cleaned_data.get('skill_name')

        if skill_name:
            # Get or create the Skill object
            skill_instance, created = Skill.objects.get_or_create(name__iexact=skill_name.strip(), defaults={'name': skill_name.strip()})
        else:
            # Fallback (shouldn't happen due to required=True)
            skill_instance = self.instance.skill

        self.instance.skill = skill_instance
        return super().save(commit=commit)
