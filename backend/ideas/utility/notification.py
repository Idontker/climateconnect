from ideas.utility.email import send_idea_join_email
from ideas.models.support import IdeaSupporter
from django.db.models.query_utils import Q
from ideas.models.comment import IdeaComment
from django.contrib.auth.models import User
from climateconnect_api.models.notification import Notification, EmailNotification
from climateconnect_api.utility.notification import create_user_notification, send_comment_notification, send_comment_email_notification, send_out_live_notification

def create_idea_comment_reply_notification(idea, comment, sender):
    notification = send_comment_notification(
        is_reply=True, 
        notification_type=Notification.REPLY_TO_IDEA_COMMENT,        
        comment=comment, 
        sender=sender, 
        comment_model=IdeaComment,
        comment_object_name="idea_comment",
        object_commented_on=idea
    )
    return notification

def create_idea_comment_notification(idea, comment, sender):
    notification = send_comment_notification(
        is_reply=False, 
        notification_type=Notification.IDEA_COMMENT,        
        comment=comment, 
        sender=sender, 
        comment_model=IdeaComment,
        comment_object_name="idea_comment",
        object_commented_on=idea
    )
    return notification

def create_idea_join_notification(idea, idea_supporter, chat_uuid):
    notification = Notification.objects.create(
        notification_type = Notification.PERSON_JOINED_IDEA,
        idea_supporter = idea_supporter
    )
    try:
        all_supporters = IdeaSupporter.objects.filter(idea=idea_supporter.idea).exclude(user=idea.user)
        # send notification to the idea's creator as well        
        users_to_be_notified = [idea.user]
        for supporter in all_supporters:
            if not supporter.user.id == idea.user.id and not supporter.user.id == idea_supporter.user.id:
                users_to_be_notified.append(supporter.user)
        for user in users_to_be_notified:
            create_user_notification(user, notification)
            send_out_live_notification(user.id)
            send_idea_join_email(
                user=user, 
                joining_user=idea_supporter.user, 
                idea=idea, 
                chat_uuid=chat_uuid,
                notification=notification
            )
    except IdeaSupporter.DoesNotExist:
        print("This is the only supporter!")