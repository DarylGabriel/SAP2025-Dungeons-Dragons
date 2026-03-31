#importing libraries
import os
import csv
import random
import pygame as py
from pygame import Rect

#Declare Constants
width, height = 900, 600
fps = 60
grid_size = 5
tile = 72
board_ori = 270, 130

#Photo Files
assets_file     = os.path.join(os.path.dirname(__file__), "assets")
font_path       = os.path.join(assets_file, "game_font.ttf")
logo_path       = os.path.join(assets_file, "logo.png")
zombie_path     = os.path.join(assets_file, "zombie.png")
setting_path   = os.path.join(assets_file, "settings.png")
tile_path   = os.path.join(assets_file, "tile.png")
tile2_path = os.path.join(assets_file, "tile_start.png")
player_path     = os.path.join(assets_file, "knight.png")
menu_path = os.path.join(assets_file, "backround.png")

#Audio Files (music)
audio_file = {
    "intro": os.path.join(assets_file, "intro.mp3"),
    "menu":  os.path.join(assets_file, "menu.mp3"),
    "game":  os.path.join(assets_file, "game.mp3"),
    "win":   os.path.join(assets_file, "win.mp3"),
    "lose":  os.path.join(assets_file, "lose.mp3"),
}

#Audio Files (sound effects)
sfx_file = {
    "zombie": os.path.join(assets_file, "zombie.mp3"),
    "move":   os.path.join(assets_file, "move.mp3"),
}

#Colors
white=(255,255,255)
black=(0,0,0)
gray=(40,40,40)
light_gray=(90,90,90)
brown=(82,49,9)
dark_brown=(54,33,10)
red=(230,60,60)
yellow=(230,200,50)

#Health Bar position and colour in the game
HPx, HPy = 40, 70
HP_width, HP_height = 360, 40
HP_background = (120, 0, 0)
HP_fill = (200, 0, 0)

#Intro timing
total_intro_time = 3000
fade_intro_time  = 1000

#gives all of the game screens a string value(oso for debugging later)
intro = "intro"
menu = "menu"
settings = "settings"
game = "game"
quiz = "quiz"
end = "end"
score = "score"

#Making helper functions
def draw_text(surface, msg, x, y, size=28, color=white, center=True, bold=False, left_align=False):
    font = py.font.Font(font_path, size)
    font.set_bold(bold)
    surf = font.render(msg, True, color)
    rect = surf.get_rect()

    #Aligns texts
    if left_align: 
        rect.midleft = (x, y)
    else: 
        rect.center = (x, y)
    surface.blit(surf, rect)

#Creating Buttons
class Button:
    #Setting up button position, text, action, and appearance
    def __init__(self, rect, label, on_click, font_size=28):
        self.rect = Rect(rect)
        self.label = label 
        self.on_click = on_click
        self.hover = False 
        self.font_size = font_size

    #Drawing/designing button and making it light up when button is over it
    def draw(self, surf):
        py.draw.rect(surf, light_gray if self.hover else gray, self.rect, border_radius=10)
        py.draw.rect(surf, white, self.rect, 2, border_radius=10)
        draw_text(surf, self.label, self.rect.centerx, self.rect.centery, size=self.font_size)

    #Checks if button is over it and if the button is clicked
    def handle(self, event):
        if event.type == py.MOUSEMOTION: 
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == py.MOUSEBUTTONDOWN and event.button == 1 and self.hover: 
            self.on_click()

#Quiz Manager to load questions from CSV file and provide random questions
class QuizManager:
    def __init__(self, csv_path="questions.csv"):
        self.questions=[]
        self.load_csv(csv_path)

    #Reads CSV file for questions
    def load_csv(self, path):
        with open(path, newline='', encoding="utf-8") as f:
            for row in csv.reader(f):
                if not row or len(row) < 6:
                    continue
                q,a,b,c,d,correct = row[:6]
                self.questions.append((q,a,b,c,d,correct.strip().upper()[:1]))

    #Getting random questions
    def get_random(self): 
        return random.choice(self.questions)

#Main game
class Game:
    #Starting the game and music/sound effects
    def __init__(self):
        py.init()
        py.mixer.init()

        #Window setup
        py.display.set_caption("Dungeons & Quizzes")
        self.screen = py.display.set_mode((width, height))
        self.clock = py.time.Clock()
        self.state = intro; self.running = True
        self.prev_state = None

        #Audio toggles
        self.music_enabled = True
        self.sfx_enabled = True

        #UI buttons
        self.menu_buttons=[] 
        self.settings_buttons=[]
        self.end_buttons=[]
        self.score_buttons=[]
        self.quiz = QuizManager()
        self.reset_run()

        # Build UI
        self.build_menu()
        self.build_settings()
        self.build_end()
        self.build_score()

        # Assets
        self.logo = py.image.load(logo_path).convert_alpha()
        self.zombie = py.image.load(zombie_path).convert_alpha()
        self.settings_icon = py.image.load(setting_path).convert_alpha()
        self.tile_img_raw = py.image.load(tile_path).convert_alpha()
        self.tile_start_raw = py.image.load(tile2_path).convert_alpha()
        self.knight_raw = py.image.load(player_path).convert_alpha()
        self.menu_bg = py.image.load(menu_path).convert_alpha()

        #Photo scales
        self.tile_img = py.transform.smoothscale(self.tile_img_raw, (tile, tile))
        self.tile_start = py.transform.smoothscale(self.tile_start_raw, (tile, tile))
        self.knight = py.transform.smoothscale(self.knight_raw, (130, 100,))
        self.zombie_side = py.transform.smoothscale(self.zombie, (120, 120))
        self.settings_icon = py.transform.smoothscale(self.settings_icon, (160, 160))
        self.settings_rect = self.settings_icon.get_rect(); self.settings_rect.topright=(width-18,18)
        

        #Intro
        self.intro_elapsed_ms=0

        #Audio management
        self.current_music = None
        self.sfx = {}
        self.load_audio()
        self.play_music("intro")

    #Audio helpers
    def load_audio(self):
        #Load sfx
        for key, path in sfx_file.items():
            self.sfx[key] = py.mixer.Sound(path)
            self.sfx[key].set_volume(0.7 if key=="zombie" else 0.6) #make volume lower for move sfx

    #Play background music
    def play_music(self, track_key, loop=True):
        
        #Check if music is enabled
        if not self.music_enabled:
            return
        path = audio_file.get(track_key)

        #if same track is already playing then return
        if self.current_music == track_key: 
            return
        
        #Play new track
        py.mixer.music.fadeout(300)
        py.mixer.music.load(path)
        py.mixer.music.set_volume(0.5 if track_key in ("menu","game") else 0.6)
        py.mixer.music.play(-1 if loop else 0)
        self.current_music = track_key

    #Stop music playback
    def stop_music(self):
        py.mixer.music.stop()
        self.current_music = None

    #Play sound effects
    def play_sfx(self, key):
        if not self.sfx_enabled:
            return
        soundplay = self.sfx.get(key)
        if soundplay:
            soundplay.play()

    #Reset game if player wants to restart
    def reset_run(self):
        self.grid=[[{"visited":False,"enemy":False,"cleared":False,"armed":True} for i in range(grid_size)] for i in range(grid_size)]
        mid = grid_size//2
        options=[(r,c) for r in range(grid_size) for c in range(grid_size) if not (r==mid and c==mid)]
        self.escape=random.choice(options)

        #Placing enemies randomly on the grid
        for r in range(grid_size):
            for c in range(grid_size):
                if (r,c)==(mid,mid) or (r,c)==self.escape:
                    continue
                self.grid[r][c]["enemy"] = (random.random()<0.35)
                self.grid[r][c]["armed"] = True

        #Player starting position
        self.player_r=mid
        self.player_c=mid
        self.grid[self.player_r][self.player_c]["visited"] = True
        self.grid[self.player_r][self.player_c]["cleared"] = True

        #Game stats
        self.health=100
        self.correct_count=0
        self.wrong_count=0
        self.answered_count=0
        self.pending_quiz=None
        self.quiz_selection=None
        self.quiz_ui={}
        self.escaped=False
        self.game_over_reason=""

    #Settings management
    def open_settings(self):
        self.prev_state = self.state
        self.state = settings
        self._refresh_settings_labels()

    #Going back from settings to previous screen
    def back_from_settings(self):
        if self.prev_state == game:
            self.state = game
            self.play_music("game")
        else:
            self.state = menu
            self.play_music("menu")

    #Update settings button labels
    def _refresh_settings_labels(self):
        for b in self.settings_buttons:

            #Update music and sfx labels
            if getattr(b, "key", None) == "music":
                b.label = f"Music: {'ON' if self.music_enabled else 'OFF'}"
            if getattr(b, "key", None) == "sfx":
                b.label = f"SFX: {'ON' if self.sfx_enabled else 'OFF'}"

    #muenu screen
    def build_menu(self):
        def start_game():
            self.reset_run()
            self.state=game
            self.play_music("game")

        #Go to settings screen
        def goto_settings():
            self.prev_state=self.state
            self.state=settings
            self._refresh_settings_labels()

        #Quit game
        def quit_game(): 
            self.running=False
        w,h=260,60
        cx=width//2
        top=260
        gap=80
        self.menu_buttons=[
            Button((cx-w//2,top+0*gap,w,h),"Start",start_game),
            Button((cx-w//2,top+1*gap,w,h),"Settings",goto_settings),
            Button((cx-w//2,top+2*gap,w,h),"Quit",quit_game),
        ]

    #Settings screen
    def build_settings(self):
        def toggle_music():
            self.music_enabled = not self.music_enabled
            #stop or start again track
            if not self.music_enabled:
                self.stop_music()
            else:
                if self.state == settings and self.prev_state == game:
                    self.play_music("game")
                elif self.state == settings and self.prev_state == menu:
                    self.play_music("menu")
                elif self.state == settings and self.prev_state == intro:
                    self.play_music("intro")
            self._refresh_settings_labels()

        #Toggles sound effects
        def toggle_sfx():
            self.sfx_enabled = not self.sfx_enabled
            self._refresh_settings_labels()

        #Back button
        def back(): 
            self.back_from_settings()

        #Buttons position
        self.settings_buttons=[
            Button((width//2-180, height//2-30, 360,60),"Music: ON", toggle_music),
            Button((width//2-180, height//2+50, 360,60),"SFX: ON", toggle_sfx),
            Button((width//2-180, height//2+160, 360,60),"Back", back),
        ]
        #Lableling
        self.settings_buttons[0].key = "music"
        self.settings_buttons[1].key = "sfx"

    #End screen
    def build_end(self):

        #Play again button
        def play_again():
            self.reset_run()
            self.state = game
            self.play_music("game")

        #Button to switch from end screen to score screen
        def to_score():
            self.state=score

        #Back to main menu button
        def back_menu():
            self.state=menu
            self.play_music("menu")

        #End screen buttons and position
        self.end_buttons=[
            Button((width//2-180, height//2+40, 360,60),"Play Again", play_again),
            Button((width//2-180, height//2+110, 360,60),"See Score", to_score),
            Button((width//2-180, height//2+180, 360,60),"Main Menu", back_menu),
        ]

    #Score screen
    def build_score(self):
        #Back to main menu button
        def back_menu():
            self.state = menu
            self.play_music("menu")
        self.score_buttons=[Button((width//2-180, height//2+130, 360,60),"Return to Main Menu", back_menu)]

    #Main game loop
    def run(self):
        while self.running:
            dt = self.clock.tick(fps)

            #Ensure event can be handled to prevent crashes
            for e in py.event.get():
                if e.type==py.QUIT:
                    self.running=False

                #Decides what game logic to run depending on what is the current game state
                if self.state == intro:
                    pass
                elif self.state == menu:
                    for b in self.menu_buttons: b.handle(e)
                elif self.state == settings:
                    if e.type == py.KEYDOWN and e.key == py.K_ESCAPE:
                        self.back_from_settings()
                    for b in self.settings_buttons: b.handle(e)
                elif self.state == game:
                    if e.type == py.MOUSEBUTTONDOWN and e.button==1 and self.settings_rect.collidepoint(e.pos):
                        self.open_settings()
                    self.handle_game_events(e)
                elif self.state == quiz:
                    self.handle_quiz_events(e)
                elif self.state == end:
                    for b in self.end_buttons: 
                        b.handle(e)
                elif self.state == score:
                    for b in self.score_buttons: 
                        b.handle(e)

            #Updates intro timer
            if self.state == intro:
                self.intro_elapsed_ms += dt

                #switches to menu after intro and start menu music
                if self.intro_elapsed_ms >= total_intro_time:
                    self.state=menu
                    self.play_music("menu")

            self.menu_bg_scaled = None
            self.draw()
        py.quit()

    #Draw functions for different game states
    def draw(self):
        if self.state==intro:
            self.draw_intro()
        elif self.state==menu:
            self.draw_menu()
        elif self.state==settings:
            self.screen.fill(black)
            self.draw_settings()
        elif self.state==game:
            self.screen.fill(black)
            self.draw_hud()
            self.draw_board()
        elif self.state==quiz:
            self.screen.fill(black)
            self.draw_hud()
            self.draw_board(dim=True)
            self.draw_quiz_panel()
        elif self.state==end:
            self.screen.fill(black)
            self.draw_end()
        elif self.state==score:
            self.screen.fill(black)
            self.draw_score()
        py.display.flip()

    #Intro screen design and layout
    def draw_intro(self):

        #Makes background black
        self.screen.fill(black)

        #Plays intro music
        self.play_music("intro")

        #Displays logo and title
        logo_target_w=360; scale=logo_target_w/self.logo.get_width()
        surf = py.transform.smoothscale(self.logo,(int(self.logo.get_width()*scale), int(self.logo.get_height()*scale)))
        rect = surf.get_rect(center=(width//2,240))
        self.screen.blit(surf,rect)
        draw_text(self.screen,"Dungeons and Quizzes", width//2, 400, size=42, bold=True)

        #Fade in/out effect during intro screen time
        t = self.intro_elapsed_ms
        alpha = 0

        #Fade calculations
        if t<fade_intro_time:
            alpha=int(255*(1-t/fade_intro_time))
        elif t>total_intro_time-fade_intro_time:
            alpha=int(255*((t-(total_intro_time-fade_intro_time))/fade_intro_time))
        if alpha>0:
            overlay=py.Surface((width,height))
            overlay.set_alpha(alpha)
            overlay.fill((0,0,0))
            self.screen.blit(overlay,(0,0))

    #Menu background scale
    def get_menu_bg_scaled(self):
        self.menu_bg_scaled = py.transform.smoothscale(self.menu_bg,(700,700))
        return self.menu_bg_scaled

    #Menu design and layout
    def draw_menu(self):
        bg=self.get_menu_bg_scaled()

        #Center background
        if bg:
            x=(width-bg.get_width())//2
            y=(height-bg.get_height())//2
            self.screen.blit(bg,(x,y))

        #Title and buttons
        draw_text(self.screen,"Dungeons and Quizzes", width//2, 120, size=48, bold=True)
        for b in self.menu_buttons: b.draw(self.screen)

    #Settings screen design and layout
    def draw_settings(self):
        draw_text(self.screen,"Settings", width//2, 110, size=44, bold=True)

        #Music and SFX toggles
        draw_text(self.screen, f"Music: {'ON' if self.music_enabled else 'OFF'}", width//2, 160, size=24)
        draw_text(self.screen, f"SFX: {'ON' if self.sfx_enabled else 'OFF'}", width//2, 190, size=24)
        #Buttons
        for b in self.settings_buttons: b.draw(self.screen)

    #health bar size witdh height, and settings icon
    def draw_hud(self):
        py.draw.rect(self.screen, HP_background, (HPx, HPy, HP_width, HP_height), border_radius=6)
        fill_w=int((self.health/100)*HP_width)
        py.draw.rect(self.screen, HP_fill, (HPx, HPy, fill_w, HP_height), border_radius=6)
        draw_text(self.screen, f"{self.health}  /  100", HPx+HP_width//2, HPy+HP_height//2, size=28, center=True, bold=True)
        self.screen.blit(self.settings_icon, self.settings_rect)

    #Game board layout
    def draw_board(self, dim=False):
        ox, oy = board_ori
        mid_r=grid_size//2
        mid_c=grid_size//2

        #grid design and layout 
        for r in range(grid_size):
            for c in range(grid_size):
                x=ox+c*tile
                y=oy+r*tile
                rect=Rect(x,y,tile,tile)
                cell=self.grid[r][c]

                #Starting tile
                if r==mid_r and c==mid_c:
                    self.screen.blit(self.tile_start, rect)
                else:
                    self.screen.blit(self.tile_img, rect)
                if cell.get("cleared"):
                    overlay=py.Surface((tile,tile),py.SRCALPHA)
                    overlay.fill((200,0,0,120))
                    self.screen.blit(overlay, rect)

                py.draw.rect(self.screen, (40,40,40), rect, 1)

        #Drawing player knight, position
        px = ox + self.player_c * tile + tile // 2
        pyc = oy + self.player_r * tile + tile // 2
        krect=self.knight.get_rect(center=(px,pyc-20)); self.screen.blit(self.knight, krect)

        #Safe text display
        if not self.grid[self.player_r][self.player_c].get("enemy") and not dim:
            draw_text(self.screen,"SAFE", (120, height//2 - 60)[0], (120, height//2 - 60)[1], size=48, left_align=True, bold=True)
        if dim:
            dark=py.Surface((width,height),py.SRCALPHA)
            dark.fill((0,0,0,160))
            self.screen.blit(dark,(0,0))


    #Quiz UI layout
    def layout_quiz(self):
        #Answer panel layout
        panel = Rect(width//2-260, height//2+30, 520, 200)
        pad=20
        col_left_x  = panel.left + pad + 10
        col_right_x = panel.centerx + 10
        row1_y = panel.top + 70
        row2_y = row1_y + 48
        box_size=18
        gap_text=-20
        opts=[]

        #Answer options layout
        letters=["A","B","C","D"]
        positions=[(col_left_x,row1_y),(col_left_x,row2_y),(col_right_x,row1_y),(col_right_x,row2_y)]

        #Creating rectangles for text and boxes
        for (letter,(x,y)) in zip(letters,positions):
            text_rect=Rect(x, y-14, 220, 28)
            box_rect=Rect(x+gap_text, y-10, box_size, box_size)
            opts.append((letter, text_rect, box_rect))
        return panel, opts

    #Quiz panel design, layout and text
    def draw_quiz_panel(self):
        q,a,b,c,d,correct=self.pending_quiz
        draw_text(self.screen,"ENEMY", 120, 150, size=36, bold=True, left_align=True)
        self.screen.blit(self.zombie_side, self.zombie_side.get_rect(topleft=(40,180)))
        panel, opts = self.layout_quiz()
        py.draw.rect(self.screen, dark_brown, panel.inflate(20,20), border_radius=12)
        inner=panel.inflate(-16,-16)
        py.draw.rect(self.screen, brown, inner, border_radius=10)
        draw_text(self.screen, q, panel.centerx, panel.top+36, size=28, center=True, bold=True)
        labels={"A":a,"B":b,"C":c,"D":d}

        #Drawing answer options
        for letter, text_rect, box_rect in opts:
            draw_text(self.screen, f"{letter}. {labels[letter]}", text_rect.left, text_rect.centery, size=24, left_align=True)
            py.draw.rect(self.screen, white, box_rect, 2, border_radius=4)
            if self.quiz_selection== letter:
                inner=box_rect.inflate(-6,-6)
                py.draw.rect(self.screen, white, inner, border_radius=3)

        #Storing quiz uis
        self.quiz_ui={"opts":opts}
        draw_text(self.screen, "Click a box to answer", panel.centerx, panel.bottom-16, size=18)

    #movement and quiz handling
    def handle_game_events(self, e):
        if e.type==py.KEYDOWN:
            dr,dc=0,0
            if e.key in (py.K_w,py.K_UP):
                dr=-1
            elif e.key in (py.K_s,py.K_DOWN):
                dr=+1
            elif e.key in (py.K_a,py.K_LEFT):
                dc=-1
            elif e.key in (py.K_d,py.K_RIGHT):
                dc=+1
            old_r,old_c=self.player_r,self.player_c
            nr=max(0,min(grid_size-1,self.player_r+dr))
            nc=max(0,min(grid_size-1,self.player_c+dc))

            #if player leaves without getting correcvt answer, previous tile will still contatin enemy
            if (nr,nc)!=(self.player_r,self.player_c):
                old_cell=self.grid[old_r][old_c]

                #Checks if enemy is present in old cell and not cleared
                if old_cell.get("enemy") and not old_cell.get("cleared"): 
                    old_cell["armed"] = True
                self.player_r,self.player_c = nr,nc
                cell=self.grid[nr][nc]
                cell["visited"] = True

                #Sound effect
                self.play_sfx("move")

                #Check if the player escapes
                if (nr,nc)==self.escape:
                    self.escaped=True
                    self.game_over_reason="ESCAPED"
                    self.state=end
                    self.play_music("win", loop=False)
                    return
                
                #If the cell is not cleared and has an enemy then start quiz
                if not cell.get("enemy"):
                    cell["cleared"]=True

                #If enemy is present then start quiz
                else:
                    if cell.get("armed",True):
                        self.begin_quiz()
                        cell["armed"]=False

    def begin_quiz(self):
        #Getting random quiz question tores it in memory.
        #also clears old quiz data and selections
        q,a,b,c,d,correct=self.quiz.get_random()
        self.pending_quiz=(q,a,b,c,d,correct)

        #Changes game state to quiz
        self.quiz_selection=None
        self.quiz_ui={}
        self.state=quiz

        # Zombie SFX on quiz open
        self.play_sfx("zombie")

    #Handling quiz answer selection
    def handle_quiz_events(self, e):
        #Detects mose clicks during the quiz
        if e.type==py.MOUSEBUTTONDOWN and e.button==1:
            if self.quiz_ui.get("opts"):
                mx,my=e.pos

                #Checking if any answer box or text is clicked
                for letter, text_rect, box_rect in self.quiz_ui["opts"]:
                    if text_rect.collidepoint(mx,my) or box_rect.collidepoint(mx,my):
                        self.quiz_selection=letter
                        self.resolve_quiz()
                        break

    #Resolving quiz answers if was wrong or correct
    def resolve_quiz(self):
        q,a,b,c,d,correct = self.pending_quiz
        chosen=self.quiz_selection
        self.answered_count+=1
        cell=self.grid[self.player_r][self.player_c]

        #If correct answer is chosen then clear enemy
        if chosen == correct:
            self.correct_count += 1
            cell["enemy"]=False
            cell["cleared"]=True

        #If wrong answer then health is minused by 35
        else:
            self.wrong_count += 1
            self.health = max(0,self.health-35)

            #Player dies if health is = or less than 0
            if self.health <=0:
                self.game_over_reason="DEFEATED"
                self.state=end
                self.play_music("lose", loop=False)
                return
        self.pending_quiz=None
        self.state=game

    #End screen
    def draw_end(self):
        #Title based on win or lose
        if self.escaped:
            title = "GOOD GAME"
        else:
            title = "GAME OVER"

        #Displays the End screen layout and text
        draw_text(self.screen, title, width//2, 160, size=56, bold=True)
        reason = self.game_over_reason or ("ESCAPED" if self.escaped else "DEFEATED")
        draw_text(self.screen, reason, width//2, 210, size=28, color=yellow)
        draw_text(self.screen, f"HP: {self.health} / 100", width//2, 250, size=24)
        for b in self.end_buttons: 
            b.draw(self.screen)

    #Display Score screen
    def draw_score(self):
        draw_text(self.screen, "SCORE", width//2, 140, size=48, bold=True)
        draw_text(self.screen, f"CORRECT ANSWERS : {self.correct_count}", width//2, 220, size=28)
        draw_text(self.screen, f"WRONG ANSWERS   : {self.wrong_count}",  width//2, 260, size=28)
        draw_text(self.screen, f"QUIZZES ANSWERED: {self.answered_count}", width//2, 300, size=28)
        for b in self.score_buttons: 
            b.draw(self.screen)

#Starting the game
if __name__ == "__main__":
    Game().run()