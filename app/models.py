from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from datetime import datetime

db = SQLAlchemy()

GroupMembers = db.Table(
    'GroupMembers',
    db.Column('user_id', db.ForeignKey('User.id'), primary_key=True),
    db.Column('group_id', db.ForeignKey('Group.id'), primary_key=True),
)


GroupEventRelations = db.Table(
    'GroupEventRelations',
    db.Column('group_id', db.ForeignKey('Group.id'), primary_key=True),
    db.Column('event_id', db.ForeignKey('Event.id'), primary_key=True),
)


class Invitation(db.Model):
    __tablename__ = 'Invitation'
    event_id = db.Column(db.Integer, db.ForeignKey('Event.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'), primary_key=True)
    token = db.Column(db.String)
    accepted = db.Column(db.Boolean)

    event = db.relationship('Event', back_populates='invitations')
    user = db.relationship('User', back_populates='invitations')


class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)

    email = db.Column(db.String, nullable=False)

    first_name = db.Column(db.String, nullable=False)
    family_name = db.Column(db.String, nullable=False)

    password_salt = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    password_reset_token = db.Column(db.String)
    password_reset_insertion_time_utc = db.Column(db.DateTime)

    email_change_request = db.Column(db.String)
    email_change_token = db.Column(db.String)
    email_change_insertion_time_utc = db.Column(db.DateTime)

    # can create events and assign an admin
    create_events_permissions = db.Column(db.Boolean)

    # can create groups and assign an admin
    create_groups_permissions = db.Column(db.Boolean)

    groups = db.relationship('Group', secondary=GroupMembers, back_populates='users')
    invitations = db.relationship('Invitation', back_populates='user')
    administrated_events = db.relationship('Event', back_populates='admin')
    administrated_groups = db.relationship('Group', back_populates='admin')

    def __repr__(self):
        return f'User(first_name={self.first_name}, family_name={self.family_name})'


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

    insertion_time_utc = db.Column(db.DateTime, nullable=False)


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
    send_invitations = db.Column(db.Boolean)
    deadline = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    admin_id = db.Column(db.Integer, db.ForeignKey(User.id))
    admin = db.relationship(User, back_populates='administrated_events')
    groups = db.relationship('Group', secondary=GroupEventRelations, back_populates='events')
    invitations = db.relationship('Invitation', back_populates='event')
    # updates = db.relationship(
    #     'EventUpdate', order_by='EventUpdate.created_at', back_populates='event')


class Group(db.Model):
    __tablename__ = 'Group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    logo = db.Column(db.String)
    description = db.Column(db.String)
    modified = db.Column(db.DateTime)
    admin_id = db.Column(db.Integer, db.ForeignKey(User.id))

    # a group admin can add and remove users from a group
    admin = db.relationship('User', back_populates='administrated_groups')
    users = db.relationship('User', secondary=GroupMembers, back_populates='groups')
    events = db.relationship('Event', secondary=GroupEventRelations, back_populates='groups')


@event.listens_for(Event, 'before_insert')
@event.listens_for(Event, 'before_update')
@event.listens_for(Group, 'before_insert')
@event.listens_for(Group, 'before_update')
def receive_before_modified(mapper, connection, target):
    target.modified = datetime.now()
