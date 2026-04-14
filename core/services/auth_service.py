from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthService:

    @staticmethod
    def create_user(email, password, first_name, last_name, is_admin=False):
        if User.objects.filter(email__iexact=email).exists():
            raise ValueError(f'A user with the email {email} already exists.')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
        )
        return user

    @staticmethod
    def edit_user(user_id, email, first_name, last_name, is_admin, password=None):
        user = User.objects.get(pk=user_id)

        if User.objects.filter(email__iexact=email).exclude(pk=user_id).exists():
            raise ValueError(f'The email {email} is already in use.')

        user.email = email
        user.username = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_admin = is_admin

        if password:
            user.set_password(password)

        user.save()
        return user

    @staticmethod
    def delete_user(user_id):
        try:
            user = User.objects.get(pk=user_id)
            user.delete()
            return True
        except User.DoesNotExist:
            return False

    @staticmethod
    def verify_user(email, password):
        return authenticate(username=email, password=password)