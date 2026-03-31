# dungeons_and_quizzes.py
# Dungeons & Quizzes — AUDIO BUILD + Settings Toggles
# - Music: Intro, Menu (loop), Game (loop), Win, Lose
# - SFX: Zombie (when quiz opens), Move (when stepping to a tile)
# - Settings "Back" returns to previous screen (Game/Menu)
# - Settings now has: Toggle Music (on/off), Toggle SFX (on/off)
# - Click-only quiz; zombie shown on the left during quiz
# - End/Score screens; Intro auto-fades

import os, csv, random
import pygame as py
from pygame import Rect

# ----------------------------
# Config
# ----------------------------
WIDTH, HEIGHT = 900, 600
FPS = 60
GRID_SIZE = 5
TILE = 72
BOARD_PIX = GRID_SIZE * TILE
BOARD_ORIGIN = ((WIDTH - BOARD_PIX)//2, (HEIGHT - BOARD_PIX)//2 + 10)

ASSETS_DIR      = os.path.join(os.path.dirname(__file__), "assets")
FONT_PATH       = os.path.join(ASSETS_DIR, "game_font.ttf")
LOGO_PATH       = os.path.join(ASSETS_DIR, "logo.png")
ZOMBIE_PATH     = os.path.join(ASSETS_DIR, "zombie.png")
SETTINGS_PATH   = os.path.join(ASSETS_DIR, "settings.png")
TILE_IMG_PATH   = os.path.join(ASSETS_DIR, "tile.png")
TILE_START_PATH = os.path.join(ASSETS_DIR, "tile_start.png")
KNIGHT_PATH     = os.path.join(ASSETS_DIR, "knight.png")

# --- Audio filenames (place these in ./assets) ---
AUDIO = {
    "intro": os.path.join(ASSETS_DIR, "intro.mp3"),
    "menu":  os.path.join(ASSETS_DIR, "menu.mp3"),
    "game":  os.path.join(ASSETS_DIR, "game.mp3"),
    "win":   os.path.join(ASSETS_DIR, "win.mp3"),
    "lose":  os.path.join(ASSETS_DIR, "lose.mp3"),
}
SFX_FILES = {
    "zombie": os.path.join(ASSETS_DIR, "zombie.mp3"),
    "move":   os.path.join(ASSETS_DIR, "move.wav"),
}

MENU_BG_BASENAME = "backround"
MENU_BG_CANDIDATES = [f"{MENU_BG_BASENAME}.png", f"{MENU_BG_BASENAME}.jpg", f"{MENU_BG_BASENAME}.jpeg"]

WHITE=(255,255,255); BLACK=(0,0,0); GRAY=(40,40,40); LIGHT_GRAY=(90,90,90)
BROWN=(92,60,32); BROWN_DARK=(60,40,22); BROWN_LIGHT=(128,86,48)
RED=(230,60,60); YELLOW=(230,200,50)

SAFE_TEXT_POS = (120, HEIGHT//2 - 60)

HP_X, HP_Y = 40, 70
HP_W, HP_H = 360, 40
HP_BG = (120, 0, 0)
HP_FILL = (200, 0, 0)

INTRO_TOTAL = 3000  # ms
INTRO_FADE  = 1000  # ms

STATE_INTRO, STATE_MENU, STATE_SETTINGS, STATE_GAME, STATE_QUIZ, STATE_END, STATE_SCORE = \
    "intro","menu","settings","game","quiz","end","score"

# ----------------------------
# Utils
# ----------------------------
def draw_text(surface, msg, x, y, size=28, color=WHITE, center=True, bold=False, left_align=False):
    font = py.font.Font(FONT_PATH, size)
    if bold: font.set_bold(True)
    surf = font.render(msg, True, color)
    rect = surf.get_rect()
    if left_align: rect.midleft = (x, y)
    else: rect.center = (x, y)
    surface.blit(surf, rect)

class Button:
    def __init__(self, rect, label, on_click, font_size=28):
        self.rect = Rect(rect); self.label = label; self.on_click = on_click
        self.hover = False; self.font_size = font_size
    def draw(self, surf):
        py.draw.rect(surf, LIGHT_GRAY if self.hover else GRAY, self.rect, border_radius=10)
        py.draw.rect(surf, WHITE, self.rect, 2, border_radius=10)
        draw_text(surf, self.label, self.rect.centerx, self.rect.centery, size=self.font_size)
    def handle(self, event):
        if event.type == py.MOUSEMOTION: self.hover = self.rect.collidepoint(event.pos)
        elif event.type == py.MOUSEBUTTONDOWN and event.button == 1 and self.hover: self.on_click()

class QuizManager:
    def __init__(self, csv_path="questions.csv"):
        self.questions=[]; self.load_csv(csv_path)
    def load_csv(self, path):
        with open(path, newline='', encoding="utf-8") as f:
            for row in csv.reader(f):
                if not row or len(row) < 6: continue
                q,a,b,c,d,correct=row[:6]
                self.questions.append((q,a,b,c,d,correct.strip().upper()[:1]))
    def get_random(self): return random.choice(self.questions) if self.questions else ("No questions","A","B","C","D","A")

# ----------------------------
# Game
# ----------------------------
class Game:
    def __init__(self):
        py.init()
        # Mixer init (graceful fallback if audio device unavailable)
        try:
            py.mixer.init()
        except Exception:
            pass

        py.display.set_caption("Dungeons & Quizzes")
        self.screen = py.display.set_mode((WIDTH, HEIGHT))
        self.clock = py.time.Clock()
        self.state = STATE_INTRO; self.running = True
        self.prev_state = None

        # Audio toggles (NEW)
        self.music_enabled = True
        self.sfx_enabled = True

        # UI sets
        self.menu_buttons=[]; self.settings_buttons=[]; self.end_buttons=[]; self.score_buttons=[]
        self.quiz = QuizManager()
        self.reset_run()

        # Build UI
        self.build_menu(); self.build_settings(); self.build_end(); self.build_score()

        # Assets
        self.logo = py.image.load(LOGO_PATH).convert_alpha()
        self.zombie = py.image.load(ZOMBIE_PATH).convert_alpha()
        self.settings_icon = py.image.load(SETTINGS_PATH).convert_alpha()
        self.tile_img_raw = py.image.load(TILE_IMG_PATH).convert_alpha()
        self.tile_start_raw = py.image.load(TILE_START_PATH).convert_alpha()
        self.knight_raw = py.image.load(KNIGHT_PATH).convert_alpha()

        # Menu background (optional)
        self.menu_bg=None
        for name in MENU_BG_CANDIDATES:
            p=os.path.join(ASSETS_DIR,name)
            if os.path.exists(p):
                self.menu_bg=py.image.load(p).convert(); break
        self.menu_bg_scaled=None

        # Scales
        self.tile_img   = py.transform.smoothscale(self.tile_img_raw, (TILE, TILE))
        self.tile_start = py.transform.smoothscale(self.tile_start_raw, (TILE, TILE))
        self.knight     = py.transform.smoothscale(self.knight_raw, (int(TILE*0.9), int(TILE*0.9)))
        self.zombie_side= py.transform.smoothscale(self.zombie, (120, 120))

        # Gear (top-right)
        self.settings_icon = py.transform.smoothscale(self.settings_icon, (64,64))
        self.settings_rect = self.settings_icon.get_rect(); self.settings_rect.topright=(WIDTH-18,18)

        # Intro
        self.intro_elapsed_ms=0

        # Quiz UI selection
        self.quiz_selection=None
        self.quiz_ui={}

        # --- Audio management ---
        self.current_music = None
        self.sfx = {}
        self._load_audio()
        self._play_music("intro")

    # ----- Audio helpers -----
    def _load_audio(self):
        # load sfx
        for key, path in SFX_FILES.items():
            try:
                if os.path.exists(path):
                    self.sfx[key] = py.mixer.Sound(path)
                    self.sfx[key].set_volume(0.7 if key=="zombie" else 0.6)
            except Exception:
                self.sfx[key] = None

    def _play_music(self, track_key, loop=True):
        if not self.music_enabled:
            return
        try:
            path = AUDIO.get(track_key)
            if not path or not os.path.exists(path): return
            if self.current_music == track_key: return
            py.mixer.music.fadeout(300)
            py.mixer.music.load(path)
            py.mixer.music.set_volume(0.5 if track_key in ("menu","game") else 0.6)
            py.mixer.music.play(-1 if loop else 0)
            self.current_music = track_key
        except Exception:
            pass

    def _stop_music(self):
        try:
            py.mixer.music.stop()
            self.current_music = None
        except Exception:
            pass

    def _play_sfx(self, key):
        if not self.sfx_enabled:
            return
        snd = self.sfx.get(key)
        if snd:
            try: snd.play()
            except Exception: pass

    # ----- Run Reset -----
    def reset_run(self):
        self.grid=[[{"visited":False,"enemy":False,"cleared":False,"armed":True} for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        mid=GRID_SIZE//2
        options=[(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if not (r==mid and c==mid)]
        self.escape=random.choice(options)
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if (r,c)==(mid,mid) or (r,c)==self.escape: continue
                self.grid[r][c]["enemy"] = (random.random()<0.35)
                self.grid[r][c]["armed"]=True
        self.player_r=mid; self.player_c=mid
        self.grid[self.player_r][self.player_c]["visited"]=True
        self.grid[self.player_r][self.player_c]["cleared"]=True

        self.health=100; self.correct_count=0; self.wrong_count=0; self.answered_count=0
        self.pending_quiz=None; self.quiz_selection=None; self.quiz_ui={}
        self.escaped=False; self.game_over_reason=""

    # ----- Settings helpers -----
    def open_settings(self):
        self.prev_state = self.state
        self.state = STATE_SETTINGS
        self._refresh_settings_labels()

    def back_from_settings(self):
        if self.prev_state == STATE_GAME:
            self.state = STATE_GAME
            self._play_music("game")
        else:
            self.state = STATE_MENU
            self._play_music("menu")

    def _refresh_settings_labels(self):
        # Update button text to reflect current toggles
        for b in self.settings_buttons:
            if getattr(b, "key", None) == "music":
                b.label = f"Music: {'ON' if self.music_enabled else 'OFF'}"
            if getattr(b, "key", None) == "sfx":
                b.label = f"SFX: {'ON' if self.sfx_enabled else 'OFF'}"

    # ----- UI Builders -----
    def build_menu(self):
        def start_game():
            self.reset_run()
            self.state=STATE_GAME
            self._play_music("game")
        def goto_settings():
            self.prev_state=self.state
            self.state=STATE_SETTINGS
            self._refresh_settings_labels()
        def quit_game(): self.running=False
        w,h=260,60; cx=WIDTH//2; top=260; gap=80
        self.menu_buttons=[
            Button((cx-w//2,top+0*gap,w,h),"Start",start_game),
            Button((cx-w//2,top+1*gap,w,h),"Settings",goto_settings),
            Button((cx-w//2,top+2*gap,w,h),"Quit",quit_game),
        ]

    def build_settings(self):
        def toggle_music():
            self.music_enabled = not self.music_enabled
            # If music was turned off, stop current track; if turned on, resume appropriate
            if not self.music_enabled:
                self._stop_music()
            else:
                # resume according to current state
                if self.state == STATE_SETTINGS and self.prev_state == STATE_GAME:
                    self._play_music("game")
                elif self.state == STATE_SETTINGS and self.prev_state == STATE_MENU:
                    self._play_music("menu")
                elif self.state == STATE_SETTINGS and self.prev_state == STATE_INTRO:
                    self._play_music("intro")
            self._refresh_settings_labels()

        def toggle_sfx():
            self.sfx_enabled = not self.sfx_enabled
            self._refresh_settings_labels()

        def back(): self.back_from_settings()

        # Buttons placed near top-right (under the title)
        self.settings_buttons=[
            Button((WIDTH//2-180, HEIGHT//2-20, 360,60),"Music: ON", toggle_music),
            Button((WIDTH//2-180, HEIGHT//2+30, 360,60),"SFX: ON", toggle_sfx),
            Button((WIDTH//2-180, HEIGHT//2+120, 360,60),"Back", back),
        ]
        # Annotate keys so labels can be updated
        self.settings_buttons[0].key = "music"
        self.settings_buttons[1].key = "sfx"

    def build_end(self):
        def play_again():
            self.reset_run()
            self.state=STATE_GAME
            self._play_music("game")
        def to_score(): self.state=STATE_SCORE
        def back_menu():
            self.state=STATE_MENU
            self._play_music("menu")
        self.end_buttons=[
            Button((WIDTH//2-180, HEIGHT//2+40, 360,60),"Play Again", play_again),
            Button((WIDTH//2-180, HEIGHT//2+110, 360,60),"See Score", to_score),
            Button((WIDTH//2-180, HEIGHT//2+180, 360,60),"Main Menu", back_menu),
        ]

    def build_score(self):
        def back_menu():
            self.state=STATE_MENU
            self._play_music("menu")
        self.score_buttons=[Button((WIDTH//2-180, HEIGHT//2+130, 360,60),"Return to Main Menu", back_menu)]

    # ----------------------------
    # Main loop
    # ----------------------------
    def run(self):
        while self.running:
            dt=self.clock.tick(FPS)
            for e in py.event.get():
                if e.type==py.QUIT: self.running=False

                if self.state==STATE_INTRO:
                    pass

                elif self.state==STATE_MENU:
                    for b in self.menu_buttons: b.handle(e)

                elif self.state==STATE_SETTINGS:
                    if e.type == py.KEYDOWN and e.key == py.K_ESCAPE:
                        self.back_from_settings()
                    for b in self.settings_buttons: b.handle(e)

                elif self.state==STATE_GAME:
                    if e.type==py.MOUSEBUTTONDOWN and e.button==1 and self.settings_rect.collidepoint(e.pos):
                        self.open_settings()
                    self.handle_game_events(e)

                elif self.state==STATE_QUIZ:
                    self.handle_quiz_events(e)

                elif self.state==STATE_END:
                    for b in self.end_buttons: b.handle(e)

                elif self.state==STATE_SCORE:
                    for b in self.score_buttons: b.handle(e)

            if self.state==STATE_INTRO:
                self.intro_elapsed_ms+=dt
                # switch to menu after intro; start menu music
                if self.intro_elapsed_ms>=INTRO_TOTAL:
                    self.state=STATE_MENU
                    self._play_music("menu")

            self.menu_bg_scaled=None
            self.draw()

        py.quit()

    # ----------------------------
    # Draw
    # ----------------------------
    def draw(self):
        if self.state==STATE_INTRO: self.draw_intro()
        elif self.state==STATE_MENU: self.draw_menu()
        elif self.state==STATE_SETTINGS:
            self.screen.fill(BLACK); self.draw_settings()
        elif self.state==STATE_GAME:
            self.screen.fill(BLACK); self.draw_hud(); self.draw_board()
        elif self.state==STATE_QUIZ:
            self.screen.fill(BLACK); self.draw_hud(); self.draw_board(dim=True); self.draw_quiz_panel()
        elif self.state==STATE_END:
            self.screen.fill(BLACK); self.draw_end()
        elif self.state==STATE_SCORE:
            self.screen.fill(BLACK); self.draw_score()
        py.display.flip()

    def draw_intro(self):
        self.screen.fill(BLACK)
        # ensure intro music is playing (respect toggle)
        self._play_music("intro")
        logo_target_w=360; scale=logo_target_w/self.logo.get_width()
        surf=py.transform.smoothscale(self.logo,(int(self.logo.get_width()*scale), int(self.logo.get_height()*scale)))
        rect=surf.get_rect(center=(WIDTH//2,240)); self.screen.blit(surf,rect)
        draw_text(self.screen,"Dungeons and Quizzes", WIDTH//2, 360, size=42, bold=True)
        t=self.intro_elapsed_ms
        alpha=0
        if t<INTRO_FADE: alpha=int(255*(1-t/INTRO_FADE))
        elif t>INTRO_TOTAL-INTRO_FADE: alpha=int(255*((t-(INTRO_TOTAL-INTRO_FADE))/INTRO_FADE))
        if alpha>0:
            overlay=py.Surface((WIDTH,HEIGHT)); overlay.set_alpha(alpha); overlay.fill((0,0,0)); self.screen.blit(overlay,(0,0))

    def get_menu_bg_scaled(self):
        if self.menu_bg_scaled: return self.menu_bg_scaled
        if not self.menu_bg: return None
        bg_w, bg_h=self.menu_bg.get_width(), self.menu_bg.get_height()
        scale = max(WIDTH/bg_w, HEIGHT/bg_h)
        new_w,new_h=int(bg_w*scale), int(bg_h*scale)
        self.menu_bg_scaled=py.transform.smoothscale(self.menu_bg,(new_w,new_h))
        return self.menu_bg_scaled

    def draw_menu(self):
        bg=self.get_menu_bg_scaled()
        if bg:
            x=(WIDTH-bg.get_width())//2; y=(HEIGHT-bg.get_height())//2
            self.screen.blit(bg,(x,y))
            overlay=py.Surface((WIDTH,HEIGHT),py.SRCALPHA); overlay.fill((0,0,0,90)); self.screen.blit(overlay,(0,0))
        else:
            self.screen.fill(BLACK)
        draw_text(self.screen,"Dungeons and Quizzes", WIDTH//2, 120, size=48, bold=True)
        for b in self.menu_buttons: b.draw(self.screen)

    def draw_settings(self):
        draw_text(self.screen,"Settings", WIDTH//2, 110, size=44, bold=True)
        # Show current states under the title
        draw_text(self.screen, f"Music: {'ON' if self.music_enabled else 'OFF'}", WIDTH//2, 160, size=24)
        draw_text(self.screen, f"SFX: {'ON' if self.sfx_enabled else 'OFF'}", WIDTH//2, 190, size=24)
        for b in self.settings_buttons: b.draw(self.screen)

    def draw_hud(self):
        py.draw.rect(self.screen, HP_BG, (HP_X, HP_Y, HP_W, HP_H), border_radius=6)
        fill_w=int((self.health/100)*HP_W)
        py.draw.rect(self.screen, HP_FILL, (HP_X, HP_Y, fill_w, HP_H), border_radius=6)
        draw_text(self.screen, f"{self.health}  /  100", HP_X+HP_W//2, HP_Y+HP_H//2, size=28, center=True, bold=True)
        self.screen.blit(self.settings_icon, self.settings_rect)

    def draw_board(self, dim=False):
        ox, oy = BOARD_ORIGIN
        mid_r=GRID_SIZE//2; mid_c=GRID_SIZE//2
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x=ox+c*TILE; y=oy+r*TILE
                rect=Rect(x,y,TILE,TILE)
                cell=self.grid[r][c]
                if r==mid_r and c==mid_c: self.screen.blit(self.tile_start, rect)
                else: self.screen.blit(self.tile_img, rect)
                if cell.get("cleared"):
                    overlay=py.Surface((TILE,TILE),py.SRCALPHA); overlay.fill((200,0,0,120)); self.screen.blit(overlay, rect)
                py.draw.rect(self.screen,(40,40,40),rect,1)
        px=ox+self.player_c*TILE+TILE//2; pyc=oy+self.player_r*TILE+TILE//2
        krect=self.knight.get_rect(center=(px,pyc)); self.screen.blit(self.knight, krect)
        if not self.grid[self.player_r][self.player_c].get("enemy") and not dim:
            draw_text(self.screen,"SAFE", SAFE_TEXT_POS[0], SAFE_TEXT_POS[1], size=48, left_align=True, bold=True)
        if dim:
            dark=py.Surface((WIDTH,HEIGHT),py.SRCALPHA); dark.fill((0,0,0,160)); self.screen.blit(dark,(0,0))

    # ----------------------------
    # Quiz
    # ----------------------------
    def layout_quiz(self):
        panel = Rect(WIDTH//2-260, HEIGHT//2+30, 520, 200)
        pad=20
        col_left_x  = panel.left + pad + 10
        col_right_x = panel.centerx + 10
        row1_y = panel.top + 70
        row2_y = row1_y + 48
        box_size=18; gap_text=28
        opts=[]
        letters=["A","B","C","D"]
        positions=[(col_left_x,row1_y),(col_left_x,row2_y),(col_right_x,row1_y),(col_right_x,row2_y)]
        for (letter,(x,y)) in zip(letters,positions):
            text_rect=Rect(x, y-14, 220, 28)
            box_rect=Rect(x+gap_text, y-10, box_size, box_size)
            opts.append((letter, text_rect, box_rect))
        return panel, opts

    def draw_quiz_panel(self):
        q,a,b,c,d,correct=self.pending_quiz
        draw_text(self.screen,"ENEMY", 120, 150, size=36, bold=True, left_align=True)
        self.screen.blit(self.zombie_side, self.zombie_side.get_rect(topleft=(40,180)))
        panel, opts = self.layout_quiz()
        py.draw.rect(self.screen, BROWN_DARK, panel.inflate(20,20), border_radius=12)
        py.draw.rect(self.screen, BROWN, panel, border_radius=12)
        inner=panel.inflate(-16,-16)
        py.draw.rect(self.screen, BROWN_LIGHT, inner, border_radius=10)
        draw_text(self.screen, q, panel.centerx, panel.top+36, size=28, center=True, bold=True)
        labels={"A":a,"B":b,"C":c,"D":d}
        for letter, text_rect, box_rect in opts:
            draw_text(self.screen, f"{letter}. {labels[letter]}", text_rect.left, text_rect.centery, size=24, left_align=True)
            py.draw.rect(self.screen, WHITE, box_rect, 2, border_radius=4)
            if self.quiz_selection==letter:
                inner=box_rect.inflate(-6,-6)
                py.draw.rect(self.screen, WHITE, inner, border_radius=3)
        self.quiz_ui={"opts":opts}
        draw_text(self.screen, "Click a box to answer", panel.centerx, panel.bottom-16, size=18)

    # ----------------------------
    # Event handling
    # ----------------------------
    def handle_game_events(self, e):
        if e.type==py.KEYDOWN:
            dr,dc=0,0
            if e.key in (py.K_w,py.K_UP): dr=-1
            elif e.key in (py.K_s,py.K_DOWN): dr=+1
            elif e.key in (py.K_a,py.K_LEFT): dc=-1
            elif e.key in (py.K_d,py.K_RIGHT): dc=+1
            old_r,old_c=self.player_r,self.player_c
            nr=max(0,min(GRID_SIZE-1,self.player_r+dr))
            nc=max(0,min(GRID_SIZE-1,self.player_c+dc))
            if (nr,nc)!=(self.player_r,self.player_c):
                old_cell=self.grid[old_r][old_c]
                if old_cell.get("enemy") and not old_cell.get("cleared"): old_cell["armed"]=True
                self.player_r,self.player_c=nr,nc
                cell=self.grid[nr][nc]; cell["visited"]=True
                # Move SFX
                self._play_sfx("move")
                if (nr,nc)==self.escape:
                    self.escaped=True; self.game_over_reason="ESCAPED"; self.state=STATE_END
                    self._play_music("win", loop=False)
                    return
                if not cell.get("enemy"):
                    cell["cleared"]=True
                else:
                    if cell.get("armed",True):
                        self.begin_quiz(); cell["armed"]=False

    def begin_quiz(self):
        q,a,b,c,d,correct=self.quiz.get_random()
        self.pending_quiz=(q,a,b,c,d,correct)
        self.quiz_selection=None; self.quiz_ui={}
        self.state=STATE_QUIZ
        # Zombie SFX on quiz open
        self._play_sfx("zombie")

    def handle_quiz_events(self, e):
        if e.type==py.MOUSEBUTTONDOWN and e.button==1:
            if self.quiz_ui.get("opts"):
                mx,my=e.pos
                for letter, text_rect, box_rect in self.quiz_ui["opts"]:
                    if text_rect.collidepoint(mx,my) or box_rect.collidepoint(mx,my):
                        self.quiz_selection=letter; self.resolve_quiz(); break

    def resolve_quiz(self):
        q,a,b,c,d,correct=self.pending_quiz
        chosen=self.quiz_selection; self.answered_count+=1
        cell=self.grid[self.player_r][self.player_c]
        if chosen==correct:
            self.correct_count+=1; cell["enemy"]=False; cell["cleared"]=True
        else:
            self.wrong_count+=1; self.health=max(0,self.health-35)
            if self.health<=0:
                self.game_over_reason="DEFEATED"; self.state=STATE_END
                self._play_music("lose", loop=False)
                return
        self.pending_quiz=None; self.state=STATE_GAME

    # ----------------------------
    # End & Score screens
    # ----------------------------
    def draw_end(self):
        title = "GOOD GAME" if self.escaped else "GAME OVER"
        draw_text(self.screen, title, WIDTH//2, 160, size=56, bold=True)
        reason = self.game_over_reason or ("ESCAPED" if self.escaped else "DEFEATED")
        draw_text(self.screen, reason, WIDTH//2, 210, size=28, color=YELLOW)
        draw_text(self.screen, f"HP: {self.health} / 100", WIDTH//2, 250, size=24)
        for b in self.end_buttons: b.draw(self.screen)

    def draw_score(self):
        draw_text(self.screen, "SCORE", WIDTH//2, 140, size=48, bold=True)
        draw_text(self.screen, f"CORRECT ANSWERS : {self.correct_count}", WIDTH//2, 220, size=28)
        draw_text(self.screen, f"WRONG ANSWERS   : {self.wrong_count}",  WIDTH//2, 260, size=28)
        draw_text(self.screen, f"QUIZZES ANSWERED: {self.answered_count}", WIDTH//2, 300, size=28)
        for b in self.score_buttons: b.draw(self.screen)


if __name__=="__main__":
    Game().run()
