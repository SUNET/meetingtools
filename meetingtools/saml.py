from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import SiteProfileNotAvailable, User
from django.core.exceptions import ObjectDoesNotExist
import logging
from saml2.saml import name_id_type__from_string
from assurance.models import IdentityProvider

logger = logging.getLogger('djangosaml2')

__author__ = 'leifj'

class Saml2Backend(ModelBackend):

    """This backend is added automatically by the assertion_consumer_service
    view.

    Don't add it to settings.AUTHENTICATION_BACKENDS.
    """

    def _set(self,o,django_attr,saml_attrs,attributes):
        for saml_attr in saml_attrs:
            if attributes.has_key(saml_attr):
                setattr(o, django_attr, attributes[saml_attr][0])
                return True
        return False

    def get_saml_user(self,session_info,attribute_mapping):
        attributes = session_info['ava']
        if not attributes:
            logger.error('The attributes dictionary is empty')

        for saml_attr, django_fields in attribute_mapping.items():
            if 'username' in django_fields and saml_attr in attributes:
                return attributes[saml_attr][0]
        return None

    def authenticate(self, session_info=None, attribute_mapping=None, create_unknown_user=True):
        if session_info is None or attribute_mapping is None:
            logger.error('Session info or attribute mapping are None')
            return None

        if not 'ava' in session_info:
            logger.error('"ava" key not found in session_info')
            return None

        print session_info

        saml_user = self.get_saml_user(session_info,attribute_mapping)

        if saml_user is None:
            logger.error('Could not find saml_user value')
            return None

        user = None
        username = self.clean_username(saml_user)

        # Note that this could be accomplished in one try-except clause, but
        # instead we use get_or_create when creating unknown users since it has
        # built-in safeguards for multiple threads.
        if create_unknown_user:
            logger.debug('Check if the user "%s" exists or create otherwise' % username)
            user, created = User.objects.get_or_create(username=username)
            if created:
                logger.debug('New user created')
                user = self.configure_user(user, session_info, attribute_mapping)
            else:
                logger.debug('User updated')
                user = self.update_user(user, session_info, attribute_mapping)
        else:
            logger.debug('Retrieving existing user "%s"' % username)
            try:
                user = User.objects.get(username=username)
                user = self.update_user(user, session_info, attribute_mapping)
            except User.DoesNotExist:
                logger.error('The user "%s" does not exist' % username)
                pass

        return user

    def clean_username(self, username):
        """Performs any cleaning on the "username" prior to using it to get or
        create the user object.  Returns the cleaned username.

        By default, returns the username unchanged.
        """
        return username

    def configure_user(self, user, session_info, attribute_mapping):
        """Configures a user after creation and returns the updated user.

        By default, returns the user with his attributes updated.
        """
        user.set_unusable_password()
        user = self.update_user(user, session_info, attribute_mapping, force_save=True)
        try:
            profile = user.get_profile()
            if profile is not None and hasattr(profile,'idp'):
                profile.idp = session_info['issuer']
                profile.save()
                #auto-populate idp table
                idp_object,created = IdentityProvider.objects.get_or_create(uri=profile.idp)
        except Exception:
            pass

        return user

    def update_user(self, user, session_info, attribute_mapping, force_save=False):
        """Update a user with a set of attributes and returns the updated user.

        By default it uses a mapping defined in the settings constant
        SAML_ATTRIBUTE_MAPPING. For each attribute, if the user object has
        that field defined it will be set, otherwise it will try to set
        it in the profile object.
        """
        if not attribute_mapping:
            return user

        attributes = session_info['ava']
        if not attributes:
            logger.error('The attributes dictionary is empty')

        try:
            profile = user.get_profile()
        except ObjectDoesNotExist:
            profile = None
        except SiteProfileNotAvailable:
            profile = None

        user_modified = False
        profile_modified = False
        for django_attr,saml_attrs in attribute_mapping.items():
            try:
                if hasattr(user, django_attr):
                    user_modified = self._set(user,django_attr,saml_attrs,attributes)

                elif profile is not None and hasattr(profile, django_attr):
                    profile_modified = self._set(profile,django_attr,saml_attrs,attributes)

            except KeyError:
                # the saml attribute is missing
                pass

        if user_modified or force_save:
            user.save()

        if profile_modified or force_save:
            profile.save()

        return user

class TargetedUsernameSamlBackend(Saml2Backend):
    def get_saml_user(self,session_info,attributes,attribute_mapping):

        eptid = attributes.get('eduPersonTargetedID',None)
        if eptid is not None:
            try:
                name_id_o = name_id_type__from_string(eptid)
                return "%s!%s!%s" % (name_id_o.name_qualifier,name_id_o.sp_name_qualifier,name_id_o.text)
            except Exception,ex:
                logger.error(ex)
                pass

        username = None
        print attribute_mapping
        if attribute_mapping.has_key('username'):
            for saml_attr in attribute_mapping['username']:
                if attributes.has_key(saml_attr):
                    username = attributes[saml_attr][0]

        if username is None:
            return None

        return username
        #return "%s!%s!%s" % (session_info['issuer'],session_info.get('entity_id',""),username)