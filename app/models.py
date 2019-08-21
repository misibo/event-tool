import pytz
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.types import TypeDecorator
from datetime import datetime

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


class GroupMembers(db.Model):
    __tablename__ = 'GroupMembers'
    user_id = db.Column(db.ForeignKey('User.id'), primary_key=True)
    group_id = db.Column(db.ForeignKey('Group.id'), primary_key=True)


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

    __tablename__ = 'User'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)

    # personal info
    first_name = db.Column(db.String, nullable=False)
    family_name = db.Column(db.String, nullable=False)
    birthday = db.Column(db.Date)

    # contact info
    email = db.Column(db.String, nullable=False)
    mobil_phone = db.Column(db.String)

    # adress
    street = db.Column(db.String)
    postal_code = db.Column(db.String)
    city = db.Column(db.String)

    # password management
    password_salt = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    password_reset_token = db.Column(db.String)
    password_reset_insertion_time_utc = db.Column(db.DateTime)

    # email management
    email_change_request = db.Column(db.String)
    email_change_token = db.Column(db.String)
    email_change_insertion_time_utc = db.Column(db.DateTime)

    # can create events and assign an admin
    create_events_permissions = db.Column(db.Boolean)

    # can create groups and assign an admin
    create_groups_permissions = db.Column(db.Boolean)

    # relations
    groups = db.relationship(
        'Group', secondary=GroupMembers.__table__, back_populates='users')
    invitations = db.relationship('Invitation', back_populates='user')
    administrated_events = db.relationship('Event', back_populates='admin')
    administrated_groups = db.relationship('Group', back_populates='admin')

    def __repr__(self):
        return auto_repr(self, ['id', 'username', 'email', 'first_name', 'family_name'])

    def __str__(self):
        return repr(self)


class PendingUser(db.Model):
    __tablename__ = 'PendingUser'
    id = db.Column(db.Integer, primary_key=True)
    confirm_token = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)

    email = db.Column(db.String, nullable=False)

    first_name = db.Column(db.String, nullable=False)
    family_name = db.Column(db.String, nullable=False)

    password_salt = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)

    insertion_time_utc = db.Column(UtcDateTime, nullable=False)

    def __repr__(self):
        return auto_repr(self, ['id', 'username', 'email'])

    def __str__(self):
        return repr(self)


class Event(db.Model):
    __tablename__ = 'Event'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    location = db.Column(db.String)
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    equipment = db.Column(db.String)
    cost = db.Column(db.Integer)
    modified = db.Column(db.DateTime)
    image = db.Column(db.String)
    send_invitations = db.Column(db.Boolean)
    deadline = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    admin_id = db.Column(db.Integer, db.ForeignKey(User.id))
    admin = db.relationship(User, back_populates='administrated_events')
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
    logo = db.Column(db.String)
    flyer = db.Column(db.String)
    modified = db.Column(db.DateTime)
    admin_id = db.Column(db.Integer, db.ForeignKey(User.id))

    # a group admin can add and remove users from a group
    admin = db.relationship('User', back_populates='administrated_groups')
    users = db.relationship(
        'User', secondary=GroupMembers.__table__, back_populates='groups')
    events = db.relationship(
        'Event', secondary=GroupEventRelations.__table__, back_populates='groups')


@event.listens_for(Event, 'before_insert')
@event.listens_for(Event, 'before_update')
@event.listens_for(Group, 'before_insert')
@event.listens_for(Group, 'before_update')
def receive_before_modified(mapper, connection, target):
    target.modified = pytz.utc.localize(datetime.utcnow())
