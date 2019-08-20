from sqlalchemy import create_engine, event, UniqueConstraint
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from flask import current_app
from datetime import datetime
import pytz


class UtcDateTime(TypeDecorator):
    """Convert local time to UTC, before storing value to database.
    """

    impl = DateTime(timezone=False)

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not isinstance(value, datetime):
                raise TypeError('expected datetime.datetime, not ' + repr(value))
            elif value.tzinfo is None:
                raise ValueError('naive datetime is disallowed')
            return value.astimezone(pytz.utc)

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = pytz.utc.localize(value)
        return value


engine = create_engine('sqlite:///db.sqlite3', echo=True)
Base = declarative_base()


def auto_repr(obj, attrs):
    arglist = ', '.join(f'{k}={getattr(obj, k)}' for k in attrs)
    return f'{type(obj).__name__}({arglist})'


class GroupMembers(Base):
    __tablename__ = 'GroupMembers'
    user_id = Column(ForeignKey('User.id'), primary_key=True)
    group_id = Column(ForeignKey('Group.id'), primary_key=True)


class GroupEventRelations(Base):
    __tablename__ = 'GroupEventRelations'
    group_id = Column(ForeignKey('Group.id'), primary_key=True)
    event_id = Column(ForeignKey('Event.id'), primary_key=True)


class Invitation(Base):
    __tablename__ = 'Invitation'
    __table_args__ = (
        UniqueConstraint('event_id', 'user_id'),  # avoid sending multiple invitations to same user
    )

    id = Column(Integer, primary_key=True, nullable=False)
    event_id = Column(Integer, ForeignKey('Event.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('User.id'), nullable=False)
    token = Column(String, nullable=False)
    send_email_attempt_utc = Column(UtcDateTime)
    send_email_success_utc = Column(UtcDateTime)
    accepted = Column(Boolean)  # None => NAN, false => rejected, true => accepted
    num_friends = Column(Integer, default=0)
    num_car_seats = Column(Integer, default=0)

    event: "Event" = relationship('Event', back_populates='invitations')
    user: "User" = relationship('User', back_populates='invitations')

    def __repr__(self):
        return auto_repr(self, ['id', 'event', 'user', 'accepted', 'num_friends', 'num_car_seats'])

    def __str__(self):
        return repr(self)


class User(Base):
    __tablename__ = 'User'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)

    email = Column(String, nullable=False)

    first_name = Column(String, nullable=False)
    family_name = Column(String, nullable=False)

    password_salt = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    password_reset_token = Column(String)
    password_reset_insertion_time_utc = Column(UtcDateTime)

    email_change_request = Column(String)
    email_change_token = Column(String)
    email_change_insertion_time_utc = Column(UtcDateTime)

    # can create events and assign an admin
    create_events_permissions = Column(Boolean)

    # can create groups and assign an admin
    create_groups_permissions = Column(Boolean)

    groups = relationship('Group', secondary=GroupMembers.__table__,
                          back_populates='users')
    invitations = relationship('Invitation', back_populates='user')
    administrated_events = relationship('Event', back_populates='admin')
    administrated_groups = relationship('Group', back_populates='admin')

    def __repr__(self):
        return auto_repr(self, ['id', 'username', 'email', 'first_name', 'family_name'])

    def __str__(self):
        return repr(self)


class PendingUser(Base):
    __tablename__ = 'PendingUser'
    id = Column(Integer, primary_key=True)
    confirm_token = Column(String, nullable=False)
    username = Column(String, nullable=False)

    email = Column(String, nullable=False)

    first_name = Column(String, nullable=False)
    family_name = Column(String, nullable=False)

    password_salt = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)

    insertion_time_utc = Column(UtcDateTime, nullable=False)

    def __repr__(self):
        return auto_repr(self, ['id', 'username', 'email'])

    def __str__(self):
        return repr(self)


class Event(Base):
    __tablename__ = 'Event'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    location = Column(String)
    start = Column(UtcDateTime)
    end = Column(UtcDateTime)
    equipment = Column(String)
    cost = Column(Integer)
    modified = Column(UtcDateTime)
    send_invitations = Column(Boolean)
    deadline = Column(UtcDateTime)
    created_at = Column(UtcDateTime)
    admin_id = Column(Integer, ForeignKey(User.id))

    admin = relationship(User, back_populates='administrated_events')
    groups = relationship(
        'Group', secondary=GroupEventRelations.__table__, back_populates='events')
    invitations = relationship('Invitation', back_populates='event')
    # updates = relationship(
    #     'EventUpdate', order_by='EventUpdate.created_at', back_populates='event')

    def __repr__(self):
        return auto_repr(self, ['id', 'name', 'location', 'start'])

    def __str__(self):
        return repr(self)


class Group(Base):
    __tablename__ = 'Group'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    modified = Column(UtcDateTime)
    admin_id = Column(Integer, ForeignKey(User.id))

    # a group admin can add and remove users from a group
    admin = relationship(User, back_populates='administrated_groups')

    users = relationship('User', secondary=GroupMembers.__table__,
                         back_populates='groups')
    events = relationship(
        'Event', secondary=GroupEventRelations.__table__, back_populates='groups')

    def __repr__(self):
        return auto_repr(self, ['id', 'name'])

    def __str__(self):
        return repr(self)


@event.listens_for(Event, 'before_insert')
@event.listens_for(Event, 'before_update')
@event.listens_for(Group, 'before_insert')
@event.listens_for(Group, 'before_update')
def receive_before_modified(mapper, connection, target):
    target.modified = pytz.utc.localize(datetime.utcnow())


# class EventUpdate(Base):
#     __tablename__ = 'EventUpdate'
#     id = Column(Integer, primary_key=True)
#     message = Column(String)
#     event_id = Column(Integer, ForeignKey(Event.id))
#     created_at = Column(UtcDateTime)

#     event = relationship(Event, back_populates='updates')


Base.metadata.create_all(engine)
db_session = scoped_session(sessionmaker(bind=engine))
