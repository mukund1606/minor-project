from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites
import asyncio
from random import randint, choice
import pygame


class Game:
    def __init__(self):
        # setup
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Survivor")
        self.clock = pygame.time.Clock()
        self.speed = pyodide.globals.get("speed")
        self.running = True

        # groups
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()

        # gun timer
        self.can_shoot = True
        self.shoot_time = 0
        self.gun_cooldown = 100

        # enemy timer
        self.enemy_event = pygame.event.custom_type()
        # pygame.time.set_timer(self.enemy_event, 300)
        self.spawn_positions = []

        # audio
        self.shoot_sound = pygame.mixer.Sound("audio/shoot.wav")
        self.shoot_sound.set_volume(0.2)
        self.impact_sound = pygame.mixer.Sound("audio/impact.wav")
        self.music = pygame.mixer.Sound("audio/music.wav")
        self.music.set_volume(0.5)
        # Uncomment this to play music in the background
        # self.music.play(loops=-1)

        # setup
        self.load_images()
        self.setup()

    def load_images(self):
        self.bullet_surf = pygame.image.load("images/gun/bullet.png").convert_alpha()

        folders = list(walk("images/enemies"))[0][1]
        self.enemy_frames = {}
        for folder in folders:
            for folder_path, _, file_names in walk(f"images/enemies/{folder}"):
                self.enemy_frames[folder] = []
                for file_name in sorted(
                    file_names, key=lambda name: int(name.split(".")[0])
                ):
                    full_path = f"{folder_path}/{file_name}"
                    surf = pygame.image.load(full_path).convert_alpha()
                    self.enemy_frames[folder].append(surf)

    def input(self):
        if pygame.mouse.get_pressed()[0] and self.can_shoot:
            self.shoot_sound.play()
            pos = self.gun.rect.center + self.gun.player_direction * 50
            Bullet(
                self.bullet_surf,
                pos,
                self.gun.player_direction,
                (self.all_sprites, self.bullet_sprites),
            )
            self.can_shoot = False
            self.shoot_time = pygame.time.get_ticks()

    def gun_timer(self):
        if not self.can_shoot:
            current_time = pygame.time.get_ticks()
            if current_time - self.shoot_time >= self.gun_cooldown:
                self.can_shoot = True

    def setup(self):
        print("Loading map...")
        map = load_pygame("data/maps/world.tmx")
        print("Done loading map")
        for x, y, image in map.get_layer_by_name("Ground").tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)

        for obj in map.get_layer_by_name("Objects"):
            CollisionSprite(
                (obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites)
            )

        for obj in map.get_layer_by_name("Collisions"):
            CollisionSprite(
                (obj.x, obj.y),
                pygame.Surface((obj.width, obj.height)),
                self.collision_sprites,
            )

        for obj in map.get_layer_by_name("Entities"):
            if obj.name == "Player":
                self.player = Player(
                    (obj.x, obj.y), self.all_sprites, self.collision_sprites
                )
                self.gun = Gun(self.player, self.all_sprites)
            else:
                self.spawn_positions.append((obj.x, obj.y))

    def bullet_collision(self):
        if self.bullet_sprites:
            for bullet in self.bullet_sprites:
                collision_sprites = pygame.sprite.spritecollide(
                    bullet, self.enemy_sprites, False, pygame.sprite.collide_mask
                )
                if collision_sprites:
                    self.impact_sound.play()
                    for sprite in collision_sprites:
                        sprite.destroy()
                    bullet.kill()

    def player_collision(self):
        if pygame.sprite.spritecollide(
            self.player, self.enemy_sprites, False, pygame.sprite.collide_mask
        ):
            self.running = False

    async def spawn_enemy_event(self):
        while self.running:
            # Sleep for 300 ms (same as pygame.time.set_timer(..., 300))
            await asyncio.sleep(0.3)
            pygame.event.post(pygame.event.Event(self.enemy_event))
        print("Spawn enemy event cancelled")

    async def run(self):
        asyncio.create_task(self.spawn_enemy_event())
        while self.running:
            dt = (self.clock.tick() / 1000) * (self.speed / 60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    game_over_text = "Game Over"
                    font = pygame.font.SysFont("Arial", 32)
                    text = font.render(game_over_text, True, (255, 255, 255))
                    self.display_surface.blit(
                        text,
                        (
                            WINDOW_WIDTH // 2 - text.get_width() // 2,
                            WINDOW_HEIGHT // 2 - text.get_height() // 2,
                        ),
                    )
                    pygame.display.update()
                    await asyncio.sleep(0.2)
                    pyodide.globals.get("setGameStatus")("STOPPED")
                    self.running = False
                    return

                if event.type == self.enemy_event:
                    Enemy(
                        choice(self.spawn_positions),
                        choice(list(self.enemy_frames.values())),
                        (self.all_sprites, self.enemy_sprites),
                        self.player,
                        self.collision_sprites,
                    )

            self.gun_timer()
            self.input()
            self.all_sprites.update(dt)
            self.bullet_collision()

            self.display_surface.fill("black")
            self.all_sprites.draw(self.player.rect.center)
            pygame.display.update()
            await asyncio.sleep(0)


async def exit_game():
    pygame.quit()


game = Game()
game.run()
