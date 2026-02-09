# forms.py
from django import forms
from .models import Profile
from skills.models import ProfileSkill, Skill



class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_pic', 'location']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'maxlength': '100', 'placeholder': 'Brief bio (max 100 chars)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Mumbai, India'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_profile_pic(self):
        image = self.cleaned_data.get('profile_pic')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file too large ( > 5MB )")
            # Optional: check format if needed, but user said any format.
        return image

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
             'personal_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': '500', 'placeholder': 'Describe your skill expertise (max 500 chars)'}),
             'token_cost': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '1000'}),
             'skill_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python'}),
        }

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['skill_name'].initial = self.instance.skill.name
        
        # Determine max tokens for the widget
        if self.profile:
            max_tokens = self.profile.get_max_token_cost
        elif self.instance and self.instance.profile:
            max_tokens = self.instance.profile.get_max_token_cost
        else:
            max_tokens = 100 # Default fallback
            
        self.fields['token_cost'].widget.attrs['max'] = max_tokens
        self.fields['token_cost'].help_text = f"Max {max_tokens} tokens based on your level."

    def clean_token_cost(self):
        token_cost = self.cleaned_data.get('token_cost')
        profile = self.profile or (self.instance.profile if self.instance else None)
        
        if profile:
            max_allowed = profile.get_max_token_cost
            if token_cost > max_allowed:
                raise forms.ValidationError(f"Your current level allows a maximum of {max_allowed} tokens.")
        return token_cost

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
