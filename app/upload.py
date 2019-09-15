from PIL import Image

import os

from flask import g, flash
from .models import User, Event, Group


def _store_favicon(file, folder, version, filename_prefix):
    image = Image.open(file.stream)
    os.makedirs(folder, exist_ok=True)
    for (w, h) in [(32, 32), (48, 48), (64, 64), (96, 96), (128, 128)]:
        # try:
        #     os.remove(os.path.join(folder, f'{filename_prefix}_{w}x{h}_v{version - 1}.png'))
        # except FileNotFoundError:
        #     pass

        image.resize((w, h), resample=Image.LANCZOS).save(
            os.path.join(folder, f'{filename_prefix}_{w}x{h}_v{version}.png'))


def store_user_avatar(file, user: User):
    folder = os.path.join('app', 'static', 'upload', 'user', str(user.id))
    user.avatar_version += 1
    _store_favicon(file, folder, user.avatar_version, filename_prefix='avatar',)


def store_event_thumbnail(file, event: Event):
    folder = os.path.join('app', 'static', 'upload', 'event', str(event.id))
    event.thumbnail_version += 1
    _store_favicon(file, folder, event.thumbnail_version, filename_prefix='thumbnail')


def store_group_logo(file, group: Group):
    folder = os.path.join('app', 'static', 'upload', 'group', str(group.id))
    group.logo_version += 1
    _store_favicon(file, folder, group.logo_version, filename_prefix='logo')
