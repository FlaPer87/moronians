from __future__ import absolute_import

import os

import pygame

from .events import EVENT_STOP_GAME, EVENT_STORY_SCRIPT_DELAY_FOR_LAUGH
from .literals import (COLOR_ALMOST_BLACK, COLOR_BLACK, COLOR_WHITE,
    HEALTH_BAR_TEXT, SCORE_TEXT, SEX_MALE)
from .utils import outlined_text
from .vec2d import vec2d


class PlayerSprite(pygame.sprite.Sprite):
    def __init__(self, game, sex=SEX_MALE):
        pygame.sprite.Sprite.__init__(self)
        self.game = game
        self.result_font = pygame.font.Font('assets/fonts/PressStart2P-Regular.ttf', 12)
        self.thought_image = pygame.image.load('assets/players/thought.png').convert_alpha()
        self.scroll = pygame.image.load('assets/players/I_Scroll02.png').convert_alpha()
        self.win_sound = pygame.mixer.Sound('assets/players/141695__copyc4t__levelup.wav')
        self.scroll_speed = 0.008
        self.total_health = 100
        self.health_bar_image = pygame.image.load('assets/players/healthBar_100x12px_3Colors.png').convert_alpha()
        self.score = 0
        self.die_sound = pygame.mixer.Sound('assets/players/falldown.wav')
        self.sex = sex

        self.reset()

        self.rect = self.image.get_rect()
        self.size = self.image.get_size()
        self.pos = (
            self.game.screen.get_size()[0] / 2 - self.size[0] / 2,
            self.game.screen.get_size()[1] / 2 - self.size[1] / 2
        )
        self.rect.topleft = [self.pos[0], self.pos[1]]

    def set_image(self):
        if self.sex == SEX_MALE:
            self.image = pygame.image.load('assets/players/boy.png').convert_alpha()
        else:
            self.image = pygame.image.load('assets/players/girl.png').convert_alpha()

    def reset(self):
        self.death = False
        self.alive = True
        self.death_roll = False
        self.health = self.total_health
        self.has_scroll = False
        self.set_image()

    def update(self, time_passed):
        if self.has_scroll:
            if not self.scroll_position[1] < self.scroll_original_position[1] - 40:
                displacement = vec2d(
                    self.scroll_direction.x * self.scroll_speed * time_passed,
                    self.scroll_direction.y * self.scroll_speed * time_passed
                )
                self.scroll_position += displacement
            else:
                if self.win_time + 8000 < pygame.time.get_ticks():
                    self.game.can_be_paused = True
                    self.has_scroll = False
                    raise LevelComplete

        if self.death and self.death_time + 1000 < pygame.time.get_ticks():
            self.die_sound.play()
            self.death_roll = True
            self.death = False

    def blit(self):
        if self.death_roll:
            if self.sex == SEX_MALE:
                self.image = pygame.image.load('assets/players/boy_left_view_2.png').convert_alpha()
            else:
                self.image = pygame.image.load('assets/players/girl_left_view_2.png').convert_alpha()
            self.game.screen.blit(pygame.transform.rotozoom(self.image, 90, 1), self.pos)
        else:
            self.game.screen.blit(self.image, self.pos)

        # Blit health bar
        text_size = self.result_font.size(HEALTH_BAR_TEXT)
        label = outlined_text(self.result_font, HEALTH_BAR_TEXT, COLOR_WHITE, COLOR_ALMOST_BLACK)
        self.game.screen.blit(label, (1, 1))
        self.game.screen.blit(self.health_bar_image, (text_size[0] + 10, 1), area=pygame.Rect(0, 0, self.health_bar_image.get_size()[0] * self.health / float(self.total_health), self.health_bar_image.get_size()[1]))

        # Blit score
        score_text = '%s %d' % (SCORE_TEXT, self.score)
        text_size = self.result_font.size(score_text)
        label = outlined_text(self.result_font, score_text, COLOR_WHITE, COLOR_ALMOST_BLACK)
        self.game.screen.blit(label, (self.game.screen.get_size()[0] - text_size[0] - 10, 1))

        if self.has_scroll:
            self.game.screen.blit(self.scroll, self.scroll_position)

    def result(self, result):
        if len(result) != 0:
            thought_size = self.thought_image.get_size()
            self.game.screen.blit(self.thought_image, (self.pos[0] + thought_size[1] / 2, self.pos[1] - 20))

            text_size = self.result_font.size(result)
            label = outlined_text(self.result_font, result, COLOR_WHITE, COLOR_ALMOST_BLACK)
            self.game.screen.blit(label, (self.pos[0] + self.size[0] / 2 - text_size[0] / 2, self.pos[1] - 30))

    def win_scroll(self):
        if not self.has_scroll and self.alive:
            pygame.mixer.music.stop()
            self.has_scroll = True
            self.win_sound.play()
            self.scroll_direction = (vec2d(self.pos[0], 0) - vec2d(self.pos)).normalized()
            self.scroll_position = ((self.pos[0] + self.size[0] / 2) - self.scroll.get_size()[0] / 2, self.pos[1] - 80)
            self.scroll_original_position = self.scroll_position
            self.win_time = pygame.time.get_ticks()
            self.game.can_be_paused = False

    def take_damage(self, enemy):
        self.health -= enemy.attack_points
        if self.health <= 0:
            self.health = 0
            self.player_dies()

    def player_dies(self):
        self.game.can_be_paused = False
        self.alive = False
        self.death = True
        self.death_time = pygame.time.get_ticks()
        pygame.event.post(pygame.event.Event(EVENT_STOP_GAME))


class EnemySprite(pygame.sprite.Sprite):
    @staticmethod
    def load_sliced_sprites(w, h, filename):
        images = []
        master_image = pygame.image.load(os.path.join('assets', filename)).convert_alpha()

        master_width, master_height = master_image.get_size()
        for i in xrange(int(master_width / w)):
            images.append(master_image.subsurface((i * w, 0, w , h)))
        return images

    @staticmethod
    def is_all_defeated(enemies):
        return enemies == []

    @staticmethod
    def player_shot(player, value, enemies):
        for enemy in enemies:
            if enemy.result == value:
                player.score += enemy.prize_value
                enemy.defeat(enemies)

    def __init__(self, game, font, text, init_position, speed, images, fps, value, attack_points):
        pygame.sprite.Sprite.__init__(self)
        self._images = images
        self.speed = speed
        self._start = pygame.time.get_ticks()
        self._delay = 1000 / fps
        self._last_update = 0
        self._frame = 0
        self.font = font
        self.text = text
        self.result = eval(text)
        self.rect = self._images[0].get_rect()
        self.size = self._images[0].get_size()
        self.game = game
        self.alive = True
        self.loop = True
        self.prize_value = value
        self.attack_points = attack_points

        self.pos = vec2d(init_position)
        self.smoke_images = [
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0001.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0002.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0003.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0004.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0005.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0006.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0007.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0008.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0009.32x32.png'),
            pygame.image.load('assets/explosions/smoke_puff/smoke_puff_0010.32x32.png')
        ]

        self.death_sound = pygame.mixer.Sound('assets/sounds/8bit_bomb_explosion.wav')

        # Calculate direction to the center of the screen
        self.direction = (vec2d(self.game.screen.get_size()[0] / 2,self.game.screen.get_size()[1] / 2) - vec2d(init_position)).normalized()

        # Call update to set our first image.
        self.update(pygame.time.get_ticks(), force=True)

    def update(self, time_passed, force=False):
        if not self.game.paused:
            t = pygame.time.get_ticks()
            if t - self._last_update > self._delay or force:
                self._frame += 1
                if self._frame >= len(self._images):
                    if self.loop:
                        self._frame = 0
                    else:
                        self._frame -= 1
                        self.enemies.remove(self)

                self.image = self._images[self._frame]
                self._last_update = t

            if self.alive:
                displacement = vec2d(
                    self.direction.x * self.speed * time_passed,
                    self.direction.y * self.speed * time_passed
                )

                self.pos += displacement
                self.rect.topleft = [self.pos.x, self.pos.y]

    def blitme(self):
        self.game.screen.blit(self.image, (self.pos.x, self.pos.y))
        if self.alive:
            # If enemy is alive show it's formula
            text_size = self.font.size(self.text)
            label = outlined_text(self.font, self.text, COLOR_WHITE, COLOR_ALMOST_BLACK)

            self.game.screen.blit(label, (self.pos.x + self.size[0] / 2 - text_size[0] / 2, self.pos.y - 11))

    def defeat(self, enemies):
        if self.alive:
            self.alive = False
            self.loop = False
            self.enemies = enemies
            self._images = self.smoke_images
            self.death_sound.play()


class SpaceshipSprite(pygame.sprite.Sprite):
    def __init__(self, game, image, speed):
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.speed = speed
        self.game = game
        self.rect = self.image.get_rect()
        self.size = self.image.get_size()
        self.pos = vec2d(self.game.screen.get_size()[0] / 2 - self.size[0] / 2, 0)
        self._start = pygame.time.get_ticks()
        self._last_update = 0
        self.direction = (vec2d(self.game.screen.get_size()[0] / 2, self.game.screen.get_size()[1] / 2) - vec2d(self.pos)).normalized()

        self.tractor_beam_image = pygame.image.load('assets/enemies/tractor_beam.png').convert()

        self.show_tractor_beam = False
        self.tractor_beam_active = False
        self.active = False

        self.book_active = False
        self.book_image = pygame.image.load('assets/enemies/books.png').convert_alpha()
        self.book_speed = 0.03

    def update(self, time_passed):
        if self.active:
            if self.pos[1] < 40:
                displacement = vec2d(
                    self.direction.x * self.speed * time_passed,
                    self.direction.y * self.speed * time_passed
                )
                self.pos += displacement
            elif self.tractor_beam_active == False:
                self.tractor_beam_active = True
                self.book_active = True
                self.book_position = (self.game.screen.get_size()[0] / 2, self.game.screen.get_size()[1] / 2 - 40)
                self.book_direction = (vec2d(self.pos[0], self.pos[1]) - vec2d(self.book_position)).normalized()
            if self.pos[1] < -69:
                self.active = False
                pygame.time.set_timer(EVENT_STORY_SCRIPT_DELAY_FOR_LAUGH, 1000)

        if self.book_active:
            displacement = vec2d(
                self.book_direction.x * self.book_speed * time_passed,
                self.book_direction.y * self.book_speed * time_passed
            )
            self.book_position += displacement
            if self.book_position[1] < 65:
                self.tractor_beam_active = False
                self.show_tractor_beam = False
                self.book_active = False
                self.direction = (vec2d(self.game.screen.get_size()[0] / 2, 0) - vec2d(self.pos)).normalized()
                self.active = True
                self.pos = (self.pos[0], self.pos[1] -1)

        if self.tractor_beam_active:
            self.show_tractor_beam = not self.show_tractor_beam

        if self.show_tractor_beam:
            self.game.screen.blit(self.tractor_beam_image, (self.pos[0] + 18, self.pos[1] + 25))

    def blit(self):
        if self.book_active:
            self.game.screen.blit(self.book_image, self.book_position)

        if self.active:
            self.game.screen.blit(self.image, self.pos)

    def activate(self):
        self.active = True
        self.original_position = self.pos