"""Запись GIF с экрана игры (для README)."""

import pygame


class Recorder:
    def __init__(self, path, every=3, scale=1, skip=0, limit=900):
        self.path, self.every, self.scale, self.skip, self.limit = path, every, scale, skip, limit
        self.frames = []

    def capture(self, surface, frame):
        if frame < self.skip or frame % self.every or len(self.frames) >= self.limit:
            return
        image = pygame.transform.scale_by(surface, self.scale)
        self.frames.append(pygame.image.tobytes(image, "RGB"))
        self.size = image.get_size()

    def save(self):
        from PIL import Image

        images = [Image.frombytes("RGB", self.size, raw).quantize(colors=128, method=Image.Quantize.MEDIANCUT)
                  for raw in self.frames]
        images[0].save(self.path, save_all=True, append_images=images[1:], duration=1000 * self.every // 60,
                       loop=0, optimize=True)
