from PIL import Image
from flask import flash

import os


def crop_center(image, new_width, new_height):
    width, height = image.size   # Get dimensions

    left = (width - new_width)/2
    top = (height - new_height)/2
    right = (width + new_width)/2
    bottom = (height + new_height)/2

    # Crop the center of the image
    return image.crop((left, top, right, bottom))


def crop_to_ratio(image, ratio):
    w, h = image.size

    # aspect ration
    r = w/h

    # image needs cutting left and right -> height fixed
    if r < ratio:
        return crop_center(image, int(r*h), h)

    # image needs cutting top and bottom -> width fixed
    else:
        return crop_center(image, w, int(w/r))


def store_favicon(file, folder, filename):
    image = Image.open(file.stream)
    image = crop_to_ratio(image, 1)
    for (s) in [32, 48, 64, 128, 256]:
        image.resize((s,s), resample=Image.LANCZOS).\
            save(os.path.join(folder, f'{filename}_{s}.png'))


def store_background(file, folder, filename):
    image = Image.open(file.stream)
    # image = crop_to_ratio(file, 16/9)
    w,h = image.size
    ratio = w/h
    for (w) in [1366, 1920, 2560]:
        image.resize((w, int(w/ratio)), resample=Image.LANCZOS).\
            save(os.path.join(folder, f'{filename}_{w}.jpg'))
