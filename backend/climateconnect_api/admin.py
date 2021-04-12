from django.contrib import admin

from climateconnect_api.models import (UserProfile, Availability, Skill, Role, UserProfileTranslation)
from climateconnect_api.models.common import Feedback
from climateconnect_api.models.faq import (FaqSection, FaqQuestion)
from climateconnect_api.models.notification import (Notification, UserNotification, EmailNotification)
from climateconnect_api.models.donation import Donation, DonationGoal
from climateconnect_api.models.language import Language


pass_through_models = (
    UserProfile, Availability, Role, 
    Feedback, FaqSection, FaqQuestion,
    Notification, UserNotification, EmailNotification,
    Donation, DonationGoal
)

for model in pass_through_models:
    admin.site.register(model, admin.ModelAdmin)


class SkillAdmin(admin.ModelAdmin):
    search_fields = ('name',)


admin.site.register(Skill, SkillAdmin)


class LanguageAdmin(admin.ModelAdmin):
    search_fields = ('name', 'language_code', 'native_name')


admin.site.register(Language, LanguageAdmin)


class UserProfileTranslationAdmin(admin.ModelAdmin):
    search_fields = (
        'user_profile__user__first_name', 'user_profile__user__last_name', 
        'user_profile__name', 'name_translation'
    )


admin.site.register(UserProfileTranslation, UserProfileTranslationAdmin)
