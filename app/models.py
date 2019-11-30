import hashlib
import os
from datetime import datetime

import pytz
from flask import current_app, g, request, url_for
from flask_sqlalchemy import BaseQuery, SQLAlchemy
from sqlalchemy import or_
from sqlalchemy.types import TypeDecorator

from .image import store_background, store_favicon

tz = pytz.timezone('Europe/Zurich')

class ExtendedQuery(BaseQuery):

    def order_by_request(self, attr, arg, default='', join=None):
        value = request.args.get(arg, default)
        query = self

        if join:
            query = self.join(join)

        if value == 'asc':
            query = self.order_by(attr.asc())
        elif value == 'asc':
            query = self.order_by(attr.desc())

        return query

    def filter_by_request(self, attr, arg, choices, t=int, join=None):
        value = request.args.get(arg, type=t)
        query = self

        if join:
            query = query.join(join)
        if value and value in choices:
            query = query.filter(attr == value)

        return query

    def search_by_request(self, attrs, arg):
        value = request.args.get(arg)
        if value:
            searches = []
            for attr in attrs:
                searches.append(attr.contains(value))
            return self.filter(or_(*searches))
        else:
            return self


db = SQLAlchemy(query_class=ExtendedQuery)


class UtcDateTime(TypeDecorator):
    """Convert local time to UTC, before storing value to database.
    """

    impl = db.DateTime(timezone=False)

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not isinstance(value, datetime):
                raise TypeError(
                    'expected datetime.datetime, not ' + repr(value))
            elif value.tzinfo is None:
                raise ValueError('naive datetime is disallowed')
            return value.astimezone(pytz.utc)

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = pytz.utc.localize(value)
        return value


def auto_repr(obj, attrs):
    arglist = ', '.join(f'{k}={getattr(obj, k)}' for k in attrs)
    return f'{type(obj).__name__}({arglist})'


class Choices:

    @classmethod
    def cast_value(self, value):
        if isinstance(value, int):
            return value
        else:
            return int(value) if value else None

    @classmethod
    def get_items(self):
        return self.get_choices().items()

    @classmethod
    def get_labels(self):
        return self.get_choices().values()

    @classmethod
    def has_value(self, value):
        return self.cast_value(value) in self.get_values()

    @classmethod
    def get_values(self):
        return self.get_choices().keys()

    @classmethod
    def get_choice_label(self, value):
        return self.get_choices().get(self.cast_value(value))

    def get_choices(self):
        return {}

    @classmethod
    def get_select_choices(self):
        return [(value, label) for value, label in self.get_items()]


class GroupMember(db.Model):

    class Role(Choices):

        SPECTATOR = 10
        MEMBER = 20
        LEADER = 30

        @classmethod
        def get_choices(self):
            return {
                self.SPECTATOR: 'Zuschauer',
                self.MEMBER: 'Teilnehmer',
                self.LEADER: 'Leiter',
            }

    __tablename__ = 'GroupMember'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'group_id'),
    )

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('Group.id'))
    joined = db.Column(UtcDateTime)
    role = db.Column(db.SmallInteger, default=Role.SPECTATOR, nullable=False)
    user = db.relationship('User', back_populates='memberships')
    group = db.relationship('Group', back_populates='members')

    def get_role_label(self):
        return self.Role.get_choice_label(self.role)


class GroupEventRelation(db.Model):
    __tablename__ = 'GroupEventRelation'
    group_id = db.Column(db.ForeignKey('Group.id'), primary_key=True)
    event_id = db.Column(db.ForeignKey('Event.id'), primary_key=True)


class Invitation(db.Model):

    class Reply(Choices):

        NONE = 1
        ACCEPTED = 2
        DECLINED = 3

        @classmethod
        def get_choices(self):
            return {
                self.NONE: 'Keine Antwort',
                self.ACCEPTED: 'Angemeldet',
                self.DECLINED: 'Abgemeldet'
            }

    __tablename__ = 'Invitation'
    __table_args__ = (
        # avoid sending multiple invitations to same user
        db.UniqueConstraint('event_id', 'user_id'),
    )

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('Event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
    token = db.Column(db.String, nullable=False)
    send_email_attempt_utc = db.Column(UtcDateTime)
    send_email_success_utc = db.Column(UtcDateTime)
    reply = db.Column(db.Integer, default=1)
    num_friends = db.Column(db.Integer, default=0)
    num_car_seats = db.Column(db.Integer, default=0)

    event = db.relationship('Event', back_populates='invitations')
    user = db.relationship('User', back_populates='invitations')

    def no_reply(self):
        return self.reply == self.Reply.NONE

    def accepted_reply(self):
        return self.reply == self.Reply.ACCEPTED

    def declined_reply(self):
        return self.reply == self.Reply.DECLINED

    def get_reply_label(self):
        return self.Reply.get_choice_label(self.reply)

    def __repr__(self):
        return auto_repr(self, ['id', 'event', 'user', 'accepted', 'num_friends', 'num_car_seats'])

    def __str__(self):
        return repr(self)


class User(db.Model):

    class Role(Choices):

        USER = 10
        MANAGER = 20
        ADMIN = 30

        @classmethod
        def get_choices(self):
            return {
                self.USER: 'Benutzer',
                self.MANAGER: 'Leiter',
                self.ADMIN: 'Administrator',
            }

    __tablename__ = 'User'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)

    registered = db.Column(UtcDateTime)
    last_login = db.Column(UtcDateTime)
    modified = db.Column(UtcDateTime)

    # personal info
    first_name = db.Column(db.String, nullable=False)
    family_name = db.Column(db.String, nullable=False)
    birthday = db.Column(db.Date)

    # contact info
    email = db.Column(db.String, nullable=False)
    mobile_phone = db.Column(db.String)

    # adress
    street = db.Column(db.String)
    postal_code = db.Column(db.String)
    city = db.Column(db.String)

    # password management
    password_salt = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    password_reset_token = db.Column(db.String)
    password_reset_insertion_time_utc = db.Column(UtcDateTime)

    # email management
    email_change_request = db.Column(db.String)
    email_change_token = db.Column(db.String)
    email_change_insertion_time_utc = db.Column(UtcDateTime)

    avatar_version = db.Column(db.Integer, default=0, nullable=False)

    role = db.Column(db.SmallInteger, default=Role.USER, nullable=False)

    # relations
    memberships = db.relationship('GroupMember', back_populates='user', cascade="all, delete-orphan")
    invitations = db.relationship('Invitation', back_populates='user', cascade="all, delete-orphan")

    def query_membership_for_event(self, event):
        return GroupMember.query.\
            join(GroupMember.user).\
            join(GroupMember.group).\
            join(Group.events).\
            filter(User.id == self.id).\
            filter(Event.id == event.id).\
            order_by(GroupMember.role.desc()).\
            first()

    def query_membership(self, group):
        return GroupMember.query.\
            join(GroupMember.user).\
            join(GroupMember.group).\
            filter(User.id == self.id).\
            filter(Group.id == group.id).\
            order_by(GroupMember.role.desc()).\
            first()

    def query_invitation_for_event(self, event):
        return Invitation.query.\
            join(Invitation.user).\
            join(Invitation.event).\
            filter(Event.id == event.id).\
            filter(User.id == self.id).\
            first()

    def get_role_label(self):
        return self.Role.get_choice_label(self.role)

    def hash_password(self, password):
        if not self.password_salt:
            self.password_salt = os.urandom(8).hex()
        hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('UTF-8'),
            self.password_salt.encode('UTF-8'),
            1000
        )
        return hash.hex()

    def can_manage(self):
        return self.role >= self.Role.MANAGER

    def is_admin(self):
        return self.role == self.Role.ADMIN

    def get_fullname(self):
        return f'{self.first_name} {self.family_name}'

    def set_password(self, password):
        self.password_hash = self.hash_password(password)

    def validate_password(self, password):
        return self.hash_password(password) == self.password_hash

    def get_folder(self):
        folder = os.path.join('app', 'static', 'user', str(self.id))
        os.makedirs(folder, exist_ok=True)
        return folder

    def get_url(self, file, version):
        if version:
            return url_for('static', filename=os.path.join('user', str(self.id), file), v=version)
        else:
            return False

    def save_avatar(self, file):
        store_favicon(file, self.get_folder(), 'avatar')
        self.avatar_version += 1

    def get_avatar_url(self, resolution=256):
        return self.get_url(f'avatar_{resolution}.png', self.avatar_version)

    def __repr__(self):
        return auto_repr(self, ['id', 'username', 'email', 'first_name', 'family_name'])

    def __str__(self):
        return repr(self)


class Event(db.Model):
    __tablename__ = 'Event'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    abstract = db.Column(db.String)
    details = db.Column(db.String)
    location = db.Column(db.String)
    start = db.Column(UtcDateTime)
    end = db.Column(UtcDateTime)
    equipment = db.Column(db.String)
    cost = db.Column(db.Integer)
    created = db.Column(UtcDateTime)
    modified = db.Column(UtcDateTime)
    invited = db.Column(db.Boolean)
    deadline = db.Column(UtcDateTime)
    background_version = db.Column(db.Integer, default=0, nullable=False)

    groups = db.relationship(
        'Group', secondary=GroupEventRelation.__table__, back_populates='events')
    invitations = db.relationship('Invitation', back_populates='event')

    def print_start_end(self):
        if (self.start.day == self.end.day):
            return f'{self.start.astimezone(tz).strftime("%d.%m.%y")}, {self.start.astimezone(tz).strftime("%H:%M")} bis {self.end.strftime("%H:%M")}'
        else:
            return f'{self.start.astimezone(tz).strftime("%d.%m.%y %H:%M")} bis {self.end.astimezone(tz).strftime("%d.%m.%y %H:%M")}'

    def get_folder(self):
        folder = os.path.join('app', 'static', 'event', str(self.id))
        os.makedirs(folder, exist_ok=True)
        return folder

    def get_url(self, file, version):
        if version:
            return url_for('static', filename=os.path.join('event', str(self.id), file), v=version)
        else:
            return False

    def save_background(self, file):
        store_background(file, self.get_folder(), 'background')
        self.background_version += 1

    def get_background_url(self, resolution=1920):
        return self.get_url(f'background_{resolution}.jpg', self.background_version)

    def __repr__(self):
        return auto_repr(self, ['id', 'name', 'location', 'start'])

    def __str__(self):
        return repr(self)


class Group(db.Model):
    __tablename__ = 'Group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    slug = db.Column(db.String)
    abstract = db.Column(db.String)
    details = db.Column(db.String)
    logo_version = db.Column(db.Integer, default=0, nullable=False)
    background_version = db.Column(db.Integer, default=0, nullable=False)
    flyer_version = db.Column(db.Integer, default=0, nullable=False)
    created = db.Column(UtcDateTime)
    modified = db.Column(UtcDateTime)

    members = db.relationship('GroupMember', back_populates='group')
    events = db.relationship('Event',
        secondary=GroupEventRelation.__table__,
        back_populates='groups',
        lazy='dynamic')

    def get_folder(self):
        folder = os.path.join('app', 'static', 'group', str(self.id))
        os.makedirs(folder, exist_ok=True)
        return folder

    def get_url(self, file, version):
        if version:
            return url_for('static', filename=os.path.join('group', str(self.id), file), v=version)
        else:
            return False

    def save_logo(self, file):
        store_favicon(file, self.get_folder(), 'logo')
        self.logo_version += 1

    def save_background(self, file):
        store_background(file, self.get_folder(), 'background')
        self.background_version += 1

    def save_flyer(self, pdf):
        pdf.save(os.path.join(self.get_folder(), 'flyer.pdf'))
        self.flyer_version += 1

    def get_logo_url(self, resolution=256):
        return self.get_url(f'logo_{resolution}.png', self.logo_version)

    def get_background_url(self, width=1920):
        return self.get_url(f'background_{width}.jpg', self.background_version)

    def get_flyer_url(self):
        return self.get_url(f'flyer.pdf', self.flyer_version)

    def get_upcoming_events(self):
        return self.events.\
            filter(Event.start >= pytz.utc.localize(datetime.utcnow())).\
            order_by(Event.start.asc()).\
            all()

    def get_membership_of_authenticated_user(self):
        return GroupMember.query.\
                filter(GroupMember.user_id == g.user.id).\
                filter(GroupMember.group_id == self.id).\
                first()

    def get_members_ordered_by_role(self):
        return GroupMember.query.\
            join(User, GroupMember.user).\
            join(Group, GroupMember.group).\
            filter(Group.id == self.id).\
            order_by(GroupMember.role.desc()).\
            all()
