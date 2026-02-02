from django.db import models
from accounts.models import Profile
from cloudinary.models import CloudinaryField

# --- Skill Master Table ---
class Skill(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True, null=True)
    skill_icon =CloudinaryField(
    'image',
    folder='skills',
    blank=True,
    null=True,
    default="https://res.cloudinary.com/dctwxqpeo/image/upload/v1762118822/Skills-To-Learn_v7lkgs.png"
)

    def __str__(self):
        return self.name


# --- Profile-Specific Skill Info ---
class ProfileSkill(models.Model):
    # --- Relations ---
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    # --- Experience & Proficiency ---
    EXPERIENCE_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
        ("expert", "Expert"),
    ]
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default="beginner")
    LEARNING_STATUS_CHOICES = [
        ("learning", "Learning"),
        ("practicing", "Practicing"),
        ("mastered", "Mastered"),
        ("teaching", "Teaching"),
    ]
    learning_status = models.CharField(max_length=20, choices=LEARNING_STATUS_CHOICES, default="learning")
    years_of_experience = models.PositiveIntegerField(default=0)
    personal_description = models.TextField(blank=True, null=True)

    # --- Availability / Exchange ---
    available_for_teaching = models.BooleanField(default=False)
    token_cost = models.PositiveIntegerField(default=0)

    # --- Interaction / Social ---
    times_taught = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    verified = models.BooleanField(default=False)
    
    # --- Exchange Preferences ---
    desired_exchange_skills = models.ManyToManyField(
        'Skill', 
        related_name="wanted_in_exchange_for",
        blank=True,
        help_text="Skills the user specifically wants in exchange for teaching this skill."
    )

    # --- Optional Notes ---
    notes = models.TextField(blank=True, null=True)
    certificate_url = models.URLField(blank=True, null=True)

    # --- Timestamp ---
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.user.username} - {self.skill.name}"
