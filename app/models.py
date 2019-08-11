from sqlalchemy import create_engine
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///db.sqlite3', echo=True)
Base = declarative_base()

GroupMembers = Table(
    'GroupMembers', Base.metadata,
    Column('user_id', ForeignKey('User.id'), primary_key=True),
    Column('group_id', ForeignKey('Group.id'), primary_key=True),
)


GroupEventRelations = Table(
    'GroupEventRelations', Base.metadata,
    Column('group_id', ForeignKey('Group.id'), primary_key=True),
    Column('event_id', ForeignKey('Event.id'), primary_key=True),
)


class Invitation(Base):
    __tablename__ = 'Invitation'
    event_id = Column(Integer, ForeignKey('Event.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('User.id'), primary_key=True)
    token = Column(String)
    accepted = Column(Boolean)

    event = relationship('Event', back_populates='invitations')
    user = relationship('User', back_populates='invitations')


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
    password_reset_insertion_time_utc = Column(DateTime)

    email_change_request = Column(String)
    email_change_token = Column(String)
    email_change_insertion_time_utc = Column(DateTime)

    # can create events and assign an admin
    create_events_permissions = Column(Boolean)

    # can create groups and assign an admin
    create_groups_permissions = Column(Boolean)

    groups = relationship('Group', secondary=GroupMembers,
                          back_populates='users')
    invitations = relationship('Invitation', back_populates='user')
    administrated_events = relationship('Event', back_populates='admin')
    administrated_groups = relationship('Group', back_populates='admin')

    def __repr__(self):
        return f'User(first_name={self.first_name}, family_name={self.family_name})'


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

    insertion_time_utc = Column(DateTime, nullable=False)


class Event(Base):
    __tablename__ = 'Event'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    message = Column(String)
    location = Column(String)
    time = Column(DateTime)
    equipment = Column(String)
    money = Column(Integer)

    send_invitations = Column(Boolean)
    deadline = Column(DateTime)
    created_at = Column(DateTime)
    admin_id = Column(Integer, ForeignKey(User.id))

    admin = relationship(User, back_populates='administrated_events')
    groups = relationship(
        'Group', secondary=GroupEventRelations, back_populates='events')
    invitations = relationship('Invitation', back_populates='event')
    updates = relationship(
        'EventUpdate', order_by='EventUpdate.created_at', back_populates='event')


class Group(Base):
    __tablename__ = 'Group'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    admin_id = Column(Integer, ForeignKey(User.id))

    # a group admin can add and remove users from a group
    admin = relationship(User, back_populates='administrated_groups')

    users = relationship('User', secondary=GroupMembers,
                         back_populates='groups')
    events = relationship(
        'Event', secondary=GroupEventRelations, back_populates='groups')


class EventUpdate(Base):
    __tablename__ = 'EventUpdate'
    id = Column(Integer, primary_key=True)
    message = Column(String)
    event_id = Column(Integer, ForeignKey(Event.id))
    created_at = Column(DateTime)

    event = relationship(Event, back_populates='updates')


Base.metadata.create_all(engine)
db_session = scoped_session(sessionmaker(bind=engine))
