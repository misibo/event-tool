from PIL import Image

import os

from flask import g, flash
from .models import User, Event, Group


def _store_favicon(file, folder, filename_prefix):
    image = Image.open(file.stream)
    os.makedirs(folder, exist_ok=True)
    for (w, h) in [(32, 32), (48, 48), (64, 64), (96, 96), (128, 128)]:
        image.resize((w, h), resample=Image.LANCZOS).save(
            os.path.join(folder, f'{filename_prefix}_{w}x{h}.png'))


def store_user_avatar(file, user: User):
    folder = os.path.join('app', 'static', 'upload', 'user', str(user.id))
    _store_favicon(file, folder, filename_prefix='avatar')


def store_event_thumbnail(file, event: Event):
    folder = os.path.join('app', 'static', 'upload', 'event', str(event.id))
    _store_favicon(file, folder, filename_prefix='thumbnail')


def store_group_logo(file, group: Group):
    folder = os.path.join('app', 'static', 'upload', 'group', str(group.id))
    _store_favicon(file, folder, filename_prefix='logo')
