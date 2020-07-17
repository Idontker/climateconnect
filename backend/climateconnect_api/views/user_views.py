from django.contrib.auth import (authenticate, login)
import datetime
from django.utils import timezone

# Rest imports
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter

from rest_framework.exceptions import ValidationError
from knox.views import LoginView as KnowLoginView
from climateconnect_api.pagination import MembersPagination

# Database imports
from django.contrib.auth.models import User
from organization.models.members import (ProjectMember, OrganizationMember)
from climateconnect_api.models import UserProfile, Availability, Skill

# Serializer imports
from climateconnect_api.serializers.user import (
    UserProfileSerializer, PersonalProfileSerializer, UserProfileStubSerializer
)
from organization.serializers.project import ProjectFromProjectMemberSerializer
from organization.serializers.organization import OrganizationsFromProjectMember

from climateconnect_main.utility.general import get_image_from_data_url
from climateconnect_api.permissions import UserPermission
from climateconnect_api.utility.email_setup import send_user_verification_email
import logging
logger = logging.getLogger(__name__)


class LoginView(KnowLoginView):
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        if 'username' and 'password' not in request.data:
            message = "Must include 'username' and 'password'"
            return Response({'message': message}, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=request.data['username'], password=request.data['password'])
        if user:
            login(request, user)
            user_profile = UserProfile.objects.filter(user = user)[0]
            if user_profile.has_logged_in<2:
                user_profile.has_logged_in = user_profile.has_logged_in +1 
                user_profile.save()
            return super(LoginView, self).post(request, format=None)
        else:
            if not User.objects.filter(username=request.data['username']).exists():
                return Response({
                    'message': 'Username does not exist. Have you signed up yet?'
                }, status=status.HTTP_401_UNAUTHORIZED)
            return Response({
                'message': 'Invalid password.'
            }, status=status.HTTP_401_UNAUTHORIZED)


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        required_params = [
            'email', 'password', 'first_name', 'last_name',
            'country', 'city'
        ]
        for param in required_params:
            if param not in request.data:
                raise ValidationError('Required parameter is missing')

        if User.objects.filter(username=request.data['email']).exists():
            raise ValidationError("Email already in use.")

        user = User.objects.create(
            username=request.data['email'],
            email=request.data['email'], first_name=request.data['first_name'],
            last_name=request.data['last_name'], is_active=True
        )

        user.set_password(request.data['password'])
        user.save()

        url_slug = (user.first_name + user.last_name).lower() + str(user.id)

        UserProfile.objects.create(
            user=user, country=request.data['country'],
            city=request.data['city'],
            url_slug=url_slug, name=request.data['first_name']+" "+request.data['last_name'],
        )

        send_user_verification_email(user)

        message = "You're almost done! We have sent an email with a confirmation link to {}. Finish creating your account by clicking the link.".format(user.email)  # NOQA

        return Response({'success': message}, status=status.HTTP_201_CREATED)


class PersonalProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # TODO: Add filters
        user = request.user
        if not UserProfile.objects.filter(user=user).exists():
            raise NotFound(detail="Profile not found.", code=status.HTTP_404_NOT_FOUND)

        user_profile = UserProfile.objects.get(user=self.request.user)
        serializer = PersonalProfileSerializer(user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ListMemberProfilesView(ListAPIView):
    permission_classes = [AllowAny]
    pagination_class = MembersPagination
    filter_backends = [SearchFilter]
    search_fields = ['name']

    def get_serializer_class(self):
        return UserProfileStubSerializer

    def get_queryset(self):
        return UserProfile.objects.filter(is_profile_verified=True)


class MemberProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, url_slug, format=None):
        try:
            profile = UserProfile.objects.get(url_slug=str(url_slug))
        except UserProfile.DoesNotExist:
            return Response({'message': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        if self.request.user.is_authenticated:
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            serializer = UserProfileStubSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)


class ListMemberProjectsView(ListAPIView):
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter]
    search_fields = ['parent_organization__url_slug']
    pagination_class = MembersPagination
    serializer_class = ProjectFromProjectMemberSerializer

    def get_queryset(self):
        return ProjectMember.objects.filter(
            user=UserProfile.objects.get(url_slug=self.kwargs['url_slug']).user,
        ).order_by('id')


class ListMemberOrganizationsView(ListAPIView):
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter]
    search_fields = ['parent_organization__url_slug']
    pagination_class = MembersPagination
    serializer_class = OrganizationsFromProjectMember

    def get_queryset(self):
        return OrganizationMember.objects.filter(
            user=UserProfile.objects.get(url_slug=self.kwargs['url_slug']).user,
        ).order_by('id')


class EditUserProfile(APIView):
    permission_classes = [UserPermission]

    def get(self, request):
        try:
            user_profile = UserProfile.objects.get(user=self.request.user)
        except UserProfile.DoesNotExist:
            raise NotFound('User not found.')

        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            user_profile = UserProfile.objects.get(user=self.request.user)
        except UserProfile.DoesNotExist:
            raise NotFound('User not found.')

        user = user_profile.user
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']

        if 'last_name' in request.data:
            user.last_name = request.data['last_name']

        user_profile.name = user.first_name + ' ' + user.last_name
        user_profile.url_slug = (user.first_name + user.last_name).lower() + str(user.id)
        user.save()

        if 'image' in request.data:
            user_profile.image = get_image_from_data_url(request.data['image'])[0]
        if 'background_image' in request.data:
            user_profile.background_image = get_image_from_data_url(request.data['background_image'])[0]

        if 'country' in request.data:
            user_profile.country = request.data['country']

        if 'state' in request.data:
            user_profile.state = request.data['state']
        if 'city' in request.data:
            user_profile.city = request.data['city']
        if 'biography' in request.data:
            user_profile.biography = request.data['biography']

        if 'availability' in request.data:
            try:
                availability = Availability.objects.get(id=int(request.data['availability']))
            except Availability.DoesNotExist:
                raise NotFound('Availability not found.')

            user_profile.availability = availability

        if 'skills' in request.data:
            for skill_id in request.data['skills']:
                skill = Skill.objects.get(id=int(skill_id))
                user_profile.skills.add(skill)

        user_profile.save()
        serializer = UserProfileSerializer(user_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserEmailVerificationLinkView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        print(request.data)
        if 'id' not in request.data or 'expires' not in request.data:
            return Response({'message': 'Required parameters are missing.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=int(request.data['id']))
        except User.DoesNotExist:
            return Response({'message': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)

        if user and UserProfile.objects.filter(user=user).exists():
            # convert timestamp
            expire_time_string = request.data['expires'].replace("%2B", "+").replace("%2D", "-")
            expire_time = datetime.datetime.fromisoformat(expire_time_string)
            if expire_time <= timezone.now():
                return Response({'message': 'Verification link expired.'}, status=status.HTTP_403_FORBIDDEN)
            else:
                if user.user_profile.is_profile_verified:
                    return Response({
                        'message': 'Account already verified. Please contact us if you are having trouble signing in.'
                    }, status=status.HTTP_204_NO_CONTENT)
                else:
                    user.user_profile.is_profile_verified = True
                    user.user_profile.save()
                    return Response({"message": "Your profile is successfully verified"}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Permission Denied'}, status=status.HTTP_403_FORBIDDEN)
