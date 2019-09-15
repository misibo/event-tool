from PIL import Image

import os

from flask import g, flash


def store_user_favicon(file, user):
    # filename = secure_filename(file.filename)

    image = Image.open(file.stream)

    folder = os.path.join('app', 'static', 'upload', 'user', str(user.id))

    os.makedirs(folder, exist_ok=True)
    for (w, h) in [(32, 32), (48, 48), (64, 64), (96, 96), (128, 128)]:
        image.resize((w, h), resample=Image.LANCZOS).save(
            os.path.join(folder, f'favicon_{w}x{h}.png'))
    
    flash('Bild wurde erfolgreich hochgeladen', 'info')
