import pgzrun
from pygame import Rect
import random


WIDTH, HEIGHT = 800, 480
TITLE = "Forest Adventure"
GROUND_LEVEL = HEIGHT - 60
ENEMY_TYPES = ["type1", "type2"]


MENU, PLAYING, GAME_OVER, PAUSED = range(4)

game_state = MENU
transition_phase = None
transition_alpha = 0


music_enabled = True
volume = 0.7


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


class Button:
    def __init__(self, text, pos, size=(220, 60), base_color=(34, 139, 34), highlight_color=(46, 184, 46)):
        self.text = text
        self.pos = pos
        self.width, self.height = size
        self.base_color = base_color
        self.highlight_color = highlight_color
        self.current_color = base_color
        self.text_color = (255, 255, 210)
        self.rect = Rect(pos[0] - self.width // 2, pos[1] - self.height // 2, self.width, self.height)

    def draw(self):
        screen.draw.filled_rect(Rect(self.rect.x + 3, self.rect.y + 3, self.rect.width, self.rect.height), (0, 0, 0))
        screen.draw.filled_rect(self.rect, self.current_color)
        
        border_rect = Rect(self.rect.x + 2, self.rect.y + 2, self.rect.width - 4, self.rect.height - 4)
        screen.draw.rect(border_rect, (139, 69, 19))
        
        screen.draw.text(self.text, center=self.pos, fontsize=28, color=self.text_color, shadow=(1, 1), scolor=(0, 50, 0))

    def collide(self, pos):
        if self.rect.collidepoint(pos):
            self.current_color = self.highlight_color
            return True
        self.current_color = self.base_color
        return False


class MainMenu:
    def __init__(self):
        spacing = 70
        center_y = HEIGHT // 2 - 40
        dark_green, light_green = (34, 139, 34), (50, 205, 50)

        self.buttons = {
            "start": Button("START ADVENTURE", (WIDTH // 2, center_y), (240, 65), dark_green, light_green),
            "sound_toggle": Button("SOUND ON", (WIDTH // 2, center_y + spacing), (200, 55), (47, 79, 79), (70, 130, 110)),
            "exit": Button("LEAVE FOREST", (WIDTH // 2, center_y + 2 * spacing), (220, 55), (101, 67, 33), (139, 90, 43)),
        }

    def update(self):
        sound_btn = self.buttons["sound_toggle"]
        if music_enabled:
            sound_btn.text = "SOUND ON"
            sound_btn.base_color, sound_btn.highlight_color = (47, 79, 79), (70, 130, 110)
        else:
            sound_btn.text = "SOUND OFF"
            sound_btn.base_color, sound_btn.highlight_color = (139, 0, 0), (205, 50, 50)

    def draw(self):
        screen.blit("background", (0, 0))
        for btn in self.buttons.values():
            btn.draw()
        screen.draw.text(TITLE, center=(WIDTH // 2, 80), fontsize=48, color=(255, 255, 210), shadow=(2, 2), scolor=(101, 67, 33))


menu = MainMenu()
pause_button = Button("CONTINUE", (WIDTH // 2, HEIGHT // 2 + 80), (200, 55), (50, 50, 150), (80, 80, 200))
pause_menu_button = Button("MENU", (WIDTH // 2, HEIGHT // 2 + 150), (200, 55), (139, 69, 19), (160, 82, 45))


def toggle_music():
    global music_enabled
    music_enabled = not music_enabled
    if music_enabled:
        sounds.menu_theme.play(-1)
        sounds.menu_theme.set_volume(volume)
    else:
        sounds.menu_theme.stop()


class Character:
    def __init__(self):
        self.current_images = []
        self.image_index = 0
        self.animation_speed = 0.3
        self.animation_time = 0
        self.facing_right = True
        self.sprite_width = 0
        self.sprite_height = 0
        self.x = self.y = 0

    @staticmethod
    def _image_exists(img_name):
        try:
            Actor(img_name)
            return True
        except Exception:
            return False

    def load_images(self, action, count):
        images = [f"{self.prefix}/{action}_{i}" for i in range(count) if self._image_exists(f"{self.prefix}/{action}_{i}")]
        return images or None

    def get_rect(self):
        return Rect(self.x - self.sprite_width / 2, self.y - self.sprite_height, self.sprite_width, self.sprite_height)

    def collides_with(self, other):
        return self.get_rect().colliderect(other.get_rect())

    def update_animation(self):
        self.animation_time += self.animation_speed
        if self.animation_time >= 1:
            self.animation_time = 0
            last_frame = len(self.current_images) - 1
            if len(self.current_images) > 1 and not (getattr(self, "is_dead", False) and self.image_index >= last_frame):
                self.image_index = (self.image_index + 1) % len(self.current_images)

    def draw(self, flip_x=False):
        try:
            img = self.current_images[min(self.image_index, len(self.current_images) - 1)]
            actor = Actor(img, (self.x, self.y))
        except Exception:
            actor = Actor(f"{self.prefix}/idle_0", (self.x, self.y))
        actor.flip_x = flip_x
        actor.draw()


class Hero(Character):
    def __init__(self):
        super().__init__()
        self.prefix = "hero"

        self.run_images = self.load_images("run", 8) or [f"{self.prefix}/run_0"]
        self.idle_images = self.load_images("idle", 4) or self.run_images
        self.jump_image = (self.load_images("jump", 1) or [f"{self.prefix}/run_0"])[0]
        self.attack_images = self.load_images("attack", 8) or self.run_images
        self.hit_images = self.load_images("hit", 4) or self.run_images
        self.death_images = self.load_images("death", 9) or self.run_images
        self.current_images = self.idle_images

        self.x, self.y = 100, GROUND_LEVEL
        self.speed, self.jump_power = 5, 12
        self.velocity_y = 0
        self.on_ground = True
        self.sprite_width, self.sprite_height = 20, 80

        self.is_jumping = self.is_attacking = self.is_hit = self.is_dead = False
        self.attack_complete = False
        self.facing_right = True
        self.was_moving = False

        self.attack_cooldown = self.hit_cooldown = 0
        self.attack_frame = 4
        self.attack_range = 60
        self.max_health = 15
        self.health = self.max_health

    def update(self):
        if self.is_dead:
            return self.update_animation()
        if self.is_hit:
            return self._handle_hit_state()

        self._handle_attack_state() if self.is_attacking else self._handle_normal_state()

        self.update_animation()
        self._apply_gravity()
        self._check_collisions()
        self._keep_in_bounds()
        self.attack_cooldown = max(0, self.attack_cooldown - 1)

    def draw(self):
        super().draw(flip_x=not self.facing_right)

    def draw_health_bar(self):
        bar_width, bar_height = 200, 20
        fill = (self.health / self.max_health) * bar_width
        screen.draw.filled_rect(Rect((20, 20), (bar_width, bar_height)), (100, 100, 100))
        health_color = (255, 0, 0) if self.health < self.max_health / 4 else (0, 255, 0)
        screen.draw.filled_rect(Rect((20, 20), (fill, bar_height)), health_color)
        screen.draw.text(f"Health: {self.health}/{self.max_health}", topleft=(25, 22), color="white", fontsize=16)

    def _apply_gravity(self):
        if not self.on_ground:
            self.velocity_y += 0.5
            self.y += self.velocity_y

    def _keep_in_bounds(self):
        self.x = clamp(self.x, 0, WIDTH - 50)
        if self.y < 0:
            self.y, self.velocity_y = 0, 0

    def _check_collisions(self):
        self.on_ground = False
        if self.y >= GROUND_LEVEL:
            self.y, self.velocity_y, self.on_ground = GROUND_LEVEL, 0, True
            return

        hero_rect = Rect(self.x - self.sprite_width / 2 + 5, self.y - self.sprite_height + 10, self.sprite_width - 10, self.sprite_height)
        for platform in platforms:
            if hero_rect.colliderect(platform.rect):
                if self.velocity_y > 0 and abs(self.y - platform.rect.top) < 15:
                    self.y, self.velocity_y, self.on_ground = platform.rect.top, 0, True
                elif not self.on_ground:
                    if self.x < platform.rect.left and keyboard.right:
                        self.x = platform.rect.left - self.sprite_width / 2
                    elif self.x > platform.rect.right and keyboard.left:
                        self.x = platform.rect.right + self.sprite_width / 2

    def _handle_normal_state(self):
        self._handle_movement()
        self._handle_jump()
        self._handle_attack_input()

    def _handle_movement(self, allow_movement=False):
        if not allow_movement and self.is_attacking:
            return

        moving = False
        if keyboard.left:
            self.x -= self.speed
            moving = True
            if self.facing_right:
                self.facing_right = False
                self._reset_animation(self.run_images)
        elif keyboard.right:
            self.x += self.speed
            moving = True
            if not self.facing_right:
                self.facing_right = True
                self._reset_animation(self.run_images)

        if moving and not self.was_moving and not self.is_attacking:
            self._reset_animation(self.run_images)
        elif not moving and self.was_moving and not self.is_attacking:
            self._reset_animation(self.idle_images)
        self.was_moving = moving

    def _handle_jump(self):
        if keyboard.space and self.on_ground and not self.is_attacking:
            self.is_jumping, self.on_ground, self.velocity_y = True, False, -self.jump_power
            self._reset_animation([self.jump_image])
            sounds.hero_jump.play()

    def _handle_attack_input(self):
        if keyboard.z and not self.is_attacking and self.attack_cooldown <= 0:
            self.is_attacking, self.attack_complete, self.attack_cooldown = True, False, 30
            self._reset_animation(self.attack_images)
            sounds.hero_attack.play()

    def _handle_attack_state(self):
        if self.image_index == self.attack_frame and not self.attack_complete:
            for enemy in enemies[:]:
                if self.collides_with(enemy):
                    enemy.take_hit()
            self.attack_complete = True

        if self.image_index >= len(self.attack_images) - 1:
            self.attack_complete = True

        if self.attack_complete and not keyboard.z:
            self.is_attacking = False
            self._reset_animation(self.run_images if (keyboard.left or keyboard.right) else self.idle_images)

        self._handle_movement(allow_movement=True)
        self._handle_jump()

    def take_hit(self):
        if not self.is_hit and not self.is_dead:
            self.is_hit, self.health, self.hit_cooldown = True, self.health - 1, 30
            self._reset_animation(self.hit_images)
            if self.health <= 0:
                self._die()

    def _handle_hit_state(self):
        self.hit_cooldown -= 1
        if self.hit_cooldown <= 0:
            self.is_hit = False
            self._reset_animation(self.run_images if (keyboard.left or keyboard.right) else self.idle_images)

    def _die(self):
        if not self.is_dead:
            self.is_dead = True
            self._reset_animation(self.death_images)
            sounds.hero_death.play()
            global game_state
            game_state = GAME_OVER

    def _reset_animation(self, images):
        self.current_images, self.image_index = images, 0


class Enemy(Character):
    def __init__(self, enemy_type, x, y, is_ground_enemy=False):
        super().__init__()
        self.prefix = f"enemy_{enemy_type}"
        self.walk_images = self.load_images("walk", 4) or [f"{self.prefix}/walk_0"]
        self.attack_images = self.load_images("attack", 8) or self.walk_images
        self.death_images = self.load_images("death", 4) or self.walk_images
        self.idle_images = self.load_images("idle", 4) or self.walk_images
        self.current_images = self.idle_images

        self.x, self.y = x, y
        self.speed = random.uniform(0.8, 1.5)
        self.sprite_width, self.sprite_height = 30, 60

        self.direction = random.choice([-1, 1])
        self.is_attacking = self.is_dead = False
        self.attack_cooldown = 2
        self.attack_range, self.detection_range = 35, 100
        self.attack_frame = 4
        self.is_ground_enemy = is_ground_enemy
        self.idle_time = 0
        self.max_idle_time = random.randint(30, 90)
        self.platform_limits = None

        self.health = 3 if enemy_type == "type1" else 5

    def update(self, hero):
        if self.is_dead:
            self.update_animation()
            return

        dx, dy = hero.x - self.x, hero.y - self.y
        distance_to_hero = abs(dx)
        same_height = abs(dy) < 20

        if same_height and distance_to_hero < self.attack_range and not hero.is_dead:
            self.is_attacking, self.current_images, self.direction = True, self.attack_images, -1 if dx < 0 else 1
            if self.image_index == self.attack_frame and self.attack_cooldown <= 0 and self.collides_with(hero):
                hero.take_hit()
                self.attack_cooldown = 60
                sounds.enemy_attack.play()
        else:
            self.is_attacking = False
            if same_height and distance_to_hero < self.detection_range and not hero.is_dead:
                self.current_images = self.walk_images
                self.direction = -1 if dx < 0 else 1
                new_x = self.x + self.speed * 1.5 * self.direction
                if self._can_move_to(new_x):
                    self.x = new_x
            else:
                self._patrol_behavior()

        self.update_animation()
        self.attack_cooldown = max(0, self.attack_cooldown - 1)

    def draw(self):
        super().draw(flip_x=self.direction < 0)

    def _patrol_behavior(self):
        self.current_images = self.walk_images
        if self.platform_limits and (self.x <= self.platform_limits[0] + 10 or self.x >= self.platform_limits[1] - 10):
            self.direction *= -1
            self.idle_time = self.max_idle_time // 2

        new_x = self.x + self.speed * self.direction
        if self._can_move_to(new_x):
            self.x = new_x

        self.idle_time += 1
        if self.idle_time >= self.max_idle_time:
            self.direction = random.choice([-1, 1])
            self.idle_time, self.max_idle_time = 0, random.randint(60, 180)

    def _can_move_to(self, new_x):
        if self.is_ground_enemy:
            return True
        if self.platform_limits:
            return self.platform_limits[0] <= new_x <= self.platform_limits[1]
        return 0 <= new_x <= WIDTH

    def take_hit(self):
        self.health -= 1
        sounds.enemy_hit.play()
        if self.health <= 0:
            self._die()

    def _die(self):
        if not self.is_dead:
            self.is_dead, self.current_images, self.image_index = True, self.death_images, 0
            sounds.enemy_death.play()

    def set_platform_limits(self, left, right):
        self.platform_limits = (left, right)


class Platform:
    def __init__(self, x, y, img_name, repeat_x=3):
        self.img_name = img_name
        self.repeat_x = repeat_x
        self.x, self.y = x, y
        self.img = Actor(img_name)
        self.tile_width, self.tile_height = self.img.width, self.img.height
        self.width = self.tile_width * repeat_x

        padding_x, pad_y_top, pad_y_bot = self.tile_width * 0.1, 8, 4
        self.rect = Rect(self.x + padding_x, self.y + pad_y_top, self.width - 2 * padding_x, self.tile_height - pad_y_top - pad_y_bot)

    def draw(self):
        for i in range(self.repeat_x):
            screen.blit(self.img_name, (self.x + i * self.tile_width, self.y))


hero = Hero()
platforms = [
    Platform(100, 350, "platform_grass", 3),
    Platform(400, 300, "platform_rock", 3),
    Platform(200, 200, "platform_log", 3),
    Platform(600, 250, "platform_rock", 3),
]
enemies = []

background = "background"

def spawn_initial_enemies():
    for platform in platforms:
        e_type = random.choice(ENEMY_TYPES)
        x = random.uniform(platform.rect.left + 30, platform.rect.right - 30)
        enemy = Enemy(e_type, x, platform.rect.top)
        enemy.set_platform_limits(platform.rect.left, platform.rect.right)
        enemies.append(enemy)

    e_type = random.choice(ENEMY_TYPES)
    enemies.append(Enemy(e_type, random.randint(100, WIDTH - 100), GROUND_LEVEL, is_ground_enemy=True))


def start_game():
    global transition_phase, transition_alpha
    transition_phase, transition_alpha = "fade_out", 0


def complete_game_start():
    global hero, enemies
    hero = Hero()
    enemies.clear()
    spawn_initial_enemies()


def return_to_menu():
    global game_state
    game_state = MENU
    if music_enabled:
        sounds.menu_theme.play(-1)


def update():
    if game_state == MENU:
        menu.update()
    elif game_state == PLAYING:
        hero.update()
        for enemy in enemies[:]:
            enemy.update(hero)
            if enemy.is_dead and enemy.image_index >= len(enemy.death_images) - 1:
                enemies.remove(enemy)
            elif game_state == PAUSED:
                pass


def draw():
    if game_state == MENU:
        menu.draw()
    elif game_state in (PLAYING, PAUSED):
        screen.blit(background, (0, 0))
        for platform in platforms:
            platform.draw()
        for enemy in enemies:
            enemy.draw()
        hero.draw()
        hero.draw_health_bar()
        if game_state == PAUSED:
            _draw_pause_overlay()
    elif game_state == GAME_OVER:
        _draw_game_over()
    if transition_phase:
        _draw_transition()

def _draw_pause_overlay():
    overlay = screen.surface.copy()
    overlay.fill((0, 0, 0))
    overlay.set_alpha(150)
    screen.surface.blit(overlay, (0, 0))
    screen.draw.text("PAUSED", center=(WIDTH // 2, HEIGHT // 2 - 40), fontsize=64, color="white")
    screen.draw.text("Press P to continue", center=(WIDTH // 2, HEIGHT // 2), fontsize=28, color="white")
    pause_button.draw()
    pause_menu_button.draw()


def _draw_game_over():
    screen.draw.filled_rect(Rect((0, 0), (WIDTH, HEIGHT)), (0, 0, 0))
    screen.draw.text("GAME OVER", center=(WIDTH // 2, HEIGHT // 2 - 50), fontsize=72, color="red")

    restart_btn = Rect((WIDTH // 2 - 100, HEIGHT // 2 + 20), (200, 50))
    quit_btn = Rect((WIDTH // 2 - 100, HEIGHT // 2 + 90), (200, 50))
    for btn, txt in ((restart_btn, "Restart"), (quit_btn, "Quit")):
        screen.draw.filled_rect(btn, (50, 50, 50))
        screen.draw.text(txt, center=btn.center, fontsize=30, color="white")

def _draw_transition():
    global transition_alpha, transition_phase, game_state

    if transition_phase == "fade_out":
        menu.draw()
    elif transition_phase == "fade_in":
        screen.blit(background, (0, 0))
        for platform in platforms:
            platform.draw()
        for enemy in enemies:
            enemy.draw()
        hero.draw()
        hero.draw_health_bar()

    transition_alpha += 10 if transition_phase == "fade_out" else -10
    transition_alpha = clamp(transition_alpha, 0, 255)

    if music_enabled:
        volume_factor = max(0, volume * (1 - transition_alpha / 255)) if transition_phase == "fade_out" else volume * (1 - transition_alpha / 255)
        theme = sounds.menu_theme if transition_phase == "fade_out" else getattr(sounds, "game_theme", None)
        if theme:
            theme.set_volume(volume_factor)

    if transition_phase == "fade_out" and transition_alpha >= 255:
        transition_phase, game_state = "fade_in", PLAYING
        complete_game_start()
        if music_enabled and hasattr(sounds, "game_theme"):
            sounds.game_theme.play(-1)
            sounds.game_theme.set_volume(0)
    elif transition_phase == "fade_in" and transition_alpha <= 0:
        transition_phase = None

    s = screen.surface.copy()
    s.fill((0, 0, 0))
    s.set_alpha(transition_alpha)
    screen.surface.blit(s, (0, 0))

def on_mouse_down(pos):
    global game_state
    if game_state == MENU:
        for name, btn in menu.buttons.items():
            if btn.collide(pos):
                if name == "start":
                    start_game()
                elif name == "exit":
                    quit()
                elif name == "sound_toggle":
                    toggle_music()
                break
    elif game_state == GAME_OVER:
        restart_btn = Rect((WIDTH // 2 - 100, HEIGHT // 2 + 20), (200, 50))
        quit_btn = Rect((WIDTH // 2 - 100, HEIGHT // 2 + 90), (200, 50))
        if restart_btn.collidepoint(pos):
            start_game()
        elif quit_btn.collidepoint(pos):
            quit()
            
    elif game_state == PAUSED:
        if pause_button.collide(pos):
            game_state = PLAYING
    
        elif pause_menu_button.collide(pos):
            return_to_menu()

def on_mouse_move(pos):
    if game_state == PAUSED:
        pause_button.collide(pos)
        pause_menu_button.collide(pos)

def on_key_down(key):
    global game_state
    if game_state == PLAYING:
        if key == keys.P:
            game_state = PAUSED
    elif game_state == PAUSED:
        if key == keys.P:
            game_state = PLAYING

if music_enabled:
    sounds.menu_theme.play(-1)
    sounds.menu_theme.set_volume(volume)

pgzrun.go()