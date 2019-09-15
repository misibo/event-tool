import hashlib
import os
from datetime import datetime

import pytz
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.types import TypeDecorator

db = SQLAlchemy()


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
    def get_choices(self):
        return {}

    @classmethod
    def get_select_choices(self):
        return [(value, label) for value, label in self.get_choices().items()]


class GroupMember(db.Model):

    class Role(Choices):

        SPECTATOR = 1
        MEMBER = 2
        LEADER = 3

        @classmethod
        def get_choices(self):
            return {
                self.SPECTATOR: 'Zuschauer',
                self.MEMBER: 'Teilnehmer',
                self.LEADER: 'Leiter'
            }

    __tablename__ = 'GroupMember'
    user_id = db.Column(db.ForeignKey('User.id'), primary_key=True)
    group_id = db.Column(db.ForeignKey('Group.id'), primary_key=True)

    role = db.Column(db.SmallInteger, default=Role.SPECTATOR, nullable=False)
    user = db.relationship('User', back_populates='members')
    group = db.relationship('Group', back_populates='members')

    def get_role_label(self):
        self.Role.get_choices()[self.role]


class GroupEventRelations(db.Model):
    __tablename__ = 'GroupEventRelations'
    group_id = db.Column(db.ForeignKey('Group.id'), primary_key=True)
    event_id = db.Column(db.ForeignKey('Event.id'), primary_key=True)


class Invitation(db.Model):

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
    # None => NAN, false => rejected, true => accepted
    accepted = db.Column(db.Boolean)
    num_friends = db.Column(db.Integer, default=0)
    num_car_seats = db.Column(db.Integer, default=0)

    event: "Event" = db.relationship('Event', back_populates='invitations')
    user: "User" = db.relationship('User', back_populates='invitations')

    def __repr__(self):
        return auto_repr(self, ['id', 'event', 'user', 'accepted', 'num_friends', 'num_car_seats'])

    def __str__(self):
        return repr(self)


class User(db.Model):

    class Role(Choices):

        USER = 1
        ADMIN = 2
        SUPERADMIN = 3

        @classmethod
        def get_choices(self):
            return {
                self.USER: 'Benutzer',
                self.ADMIN: 'Admin',
                self.SUPERADMIN: 'Super Admin'
            }

    __tablename__ = 'User'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)

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
    members = db.relationship('GroupMember', back_populates='user', cascade="all, delete-orphan")
    invitations = db.relationship('Invitation', back_populates='user', cascade="all, delete-orphan")

    def get_role_label(self):
        return self.Role.get_choices()[self.role]

    def hash_password(self, password):
        if not self.password_salt:
            self.password_salt = os.urandom(8).hex()
        hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('UTF-8'),
            self.password_salt.encode('UTF-8'),
            1000
        )
        return hash

    def set_password(self, password):
        self.password_hash = self.hash_password(password)

    def validate_password(self, password):
        return self.hash_password(password) == self.password_hash

    def __repr__(self):
        return auto_repr(self, ['id', 'username', 'email', 'first_name', 'family_name'])

    def __str__(self):
        return repr(self)


class Event(db.Model):
    __tablename__ = 'Event'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    location = db.Column(db.String)
    start = db.Column(UtcDateTime)
    end = db.Column(UtcDateTime)
    equipment = db.Column(db.String)
    cost = db.Column(db.Integer)
    modified = db.Column(UtcDateTime)
    send_invitations = db.Column(db.Boolean)
    deadline = db.Column(UtcDateTime)
    created_at = db.Column(UtcDateTime)
    thumbnail_version = db.Column(db.Integer, default=0, nullable=False)

    groups = db.relationship(
        'Group', secondary=GroupEventRelations.__table__, back_populates='events')
    invitations = db.relationship('Invitation', back_populates='event')

    def __repr__(self):
        return auto_repr(self, ['id', 'name', 'location', 'start'])

    def __str__(self):
        return repr(self)


class Group(db.Model):
    __tablename__ = 'Group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    age = db.Column(db.String)
    logo_version = db.Column(db.Integer, default=0, nullable=False)
    flyer = db.Column(db.String)
    modified = db.Column(UtcDateTime)

    members = db.relationship('GroupMember', back_populates='group')
    events = db.relationship(
        'Event', secondary=GroupEventRelations.__table__, back_populates='groups')


@event.listens_for(Event, 'before_insert')
@event.listens_for(Event, 'before_update')
@event.listens_for(Group, 'before_insert')
@event.listens_for(Group, 'before_update')
def receive_before_modified(mapper, connection, target):
    target.modified = pytz.utc.localize(datetime.utcnow())
