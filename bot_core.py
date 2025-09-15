# bot_core.py
import time
import threading
from pynput import keyboard
from collections import deque
from datetime import datetime

# ---- TECLADO: pydirectinput (melhor p/ jogos); fallback p/ pyautogui ----
try:
    import pydirectinput as kb
    USING_PDI = True
except ImportError:
    import pyautogui as kb
    USING_PDI = False
    kb.FAILSAFE = True
kb.PAUSE = 0.05

# ---- CAPTURA DE TELA p/ detectar loading preto ----
import numpy as np
import cv2
import mss

# ========== PARÂMETROS AJUSTÁVEIS ==========
DARK_THRESHOLD     = 3
DARK_RATIO_LOAD    = 0.95
SAMPLE_SIZE        = 300
MIN_BLACK_DURATION = 0.05
MIN_CLEAR_DURATION = 0.10
SCAN_INTERVAL_MS   = 10

LOAD_TARGET1 = 1
LOAD_TARGET2 = 2
LOAD_TARGET3 = 3
LOAD_TARGET4 = 4

# ========== ESTADO GLOBAL ==========
running = False
paused = False

cycle = 1
_cycle_lock = threading.Lock()

# Configuração do monitor/recorte
_sct = mss.mss()
mon_info = _sct.monitors[1]  # 1 = principal
screen_w = mon_info["width"]
screen_h = mon_info["height"]
left = int(screen_w/2 - SAMPLE_SIZE/2)
top  = int(screen_h/2 - SAMPLE_SIZE/2)
REGION = {"left": left, "top": top, "width": SAMPLE_SIZE, "height": SAMPLE_SIZE}

# ========== CONTROLE DE AÇÃO ==========
class ActionController:
    def __init__(self):
        self.should_interrupt = False
        self.current_action = None
        self.lock = threading.Lock()
    
    def set_interrupt(self, action_name):
        with self.lock:
            self.should_interrupt = True
            self.current_action = action_name
    
    def clear_interrupt(self):
        with self.lock:
            self.should_interrupt = False
    
    def check_interrupt(self):
        with self.lock:
            return self.should_interrupt
    
    def get_current_action(self):
        with self.lock:
            return self.current_action

action_controller = ActionController()

# ========== DETECTOR ==========
class BlackScreenDetector:
    def __init__(self, action_controller):
        self.load_count = 0
        self.is_black = False
        self.last_transition = None
        self.running = True
        self.lock = threading.Lock()
        self.history = deque(maxlen=100)
        self.thread = None
        self.action_controller = action_controller
        
    def _is_screen_black(self, sct):
        try:
            img = np.array(sct.grab(REGION))[:, :, :3]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            dark_ratio = (gray <= DARK_THRESHOLD).sum() / gray.size
            return dark_ratio >= DARK_RATIO_LOAD
        except Exception:
            return False
    
    def _detector_loop(self):
        with mss.mss() as sct:
            last_state = None
            black_start = None
            clear_start = None
            
            while self.running:
                current_black = self._is_screen_black(sct)
                current_time = time.time()
                
                self.history.append((current_time, current_black))
                with self.lock:
                    self.is_black = current_black
                
                if last_state is None:
                    last_state = current_black
                    if current_black:
                        black_start = current_time
                    else:
                        clear_start = current_time
                
                elif last_state != current_black:
                    # clara -> preta
                    if current_black and not last_state:
                        if clear_start and (current_time - clear_start) >= MIN_CLEAR_DURATION:
                            black_start = current_time
                            last_state = True
                    
                    # preta -> clara
                    elif not current_black and last_state:
                        if black_start and (current_time - black_start) >= MIN_BLACK_DURATION:
                            with self.lock:
                                self.load_count += 1
                                self.last_transition = current_time
                            
                            action_name = self._get_action_for_count(self.load_count)
                            if action_name:
                                self.action_controller.set_interrupt(action_name)
                            
                            print(f"[LOADING #{self.load_count}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} -> {action_name}")
                            
                        clear_start = current_time
                        last_state = False
                
                time.sleep(SCAN_INTERVAL_MS / 1000)
    
    def _get_action_for_count(self, count):
        if count == LOAD_TARGET1:
            return "ACTION_1"
        elif count == LOAD_TARGET2:
            return "ACTION_2"
        elif count == LOAD_TARGET3:
            return "ACTION_3"
        elif count >= LOAD_TARGET4:
            return "ACTION_4_RESET"
        else:
            return "ACTION_0"
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._detector_loop, daemon=True)
        self.thread.start()
        print(f"[DETECTOR] Iniciado - Varredura a cada {SCAN_INTERVAL_MS}ms")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def get_load_count(self):
        with self.lock:
            return self.load_count
    
    def reset_count(self):
        with self.lock:
            self.load_count = 0
    
    def wait_if_loading(self, timeout=5):
        start = time.time()
        while self.is_black and (time.time() - start) < timeout:
            time.sleep(0.01)

detector = BlackScreenDetector(action_controller)

# ========== HOTKEYS ==========
def on_press(key):
    global running, paused
    if key == keyboard.Key.esc:
        print("[ESC] Encerrando...")
        running = False
        return False
    elif key == keyboard.Key.f8:
        paused = not paused
        print(f"[{'PAUSADO' if paused else 'RODANDO'}]")
    elif key == keyboard.Key.f9:
        count = detector.get_load_count()
        current_action = action_controller.get_current_action()
        with _cycle_lock:
            c = cycle
        print(f"[STATUS] Loadings: {count} | Ciclo: {c} | Ação atual: {current_action}")

# ========== PRIMITIVAS DE TECLA ==========
def press(key, duration=0.1, check_interrupt=True):
    if check_interrupt and action_controller.check_interrupt():
        return False
    detector.wait_if_loading()
    kb.keyDown(key)
    intervals = max(1, int(duration / 0.05))
    sleep_time = duration / intervals
    for _ in range(intervals):
        if check_interrupt and action_controller.check_interrupt():
            kb.keyUp(key); return False
        time.sleep(sleep_time)
    kb.keyUp(key)
    return True

def press_combo(keys, duration=0.2, check_interrupt=True):
    if check_interrupt and action_controller.check_interrupt():
        return False
    detector.wait_if_loading()
    for k in keys: kb.keyDown(k)
    intervals = max(1, int(duration / 0.05))
    sleep_time = duration / intervals
    for _ in range(intervals):
        if check_interrupt and action_controller.check_interrupt():
            for k in keys: kb.keyUp(k)
            return False
        time.sleep(sleep_time)
    for k in keys: kb.keyUp(k)
    return True

def sleep_interruptible(seconds, check_interrupt=True):
    if not check_interrupt:
        time.sleep(seconds); return True
    intervals = max(1, int(seconds / 0.05))
    sleep_time = seconds / intervals
    for _ in range(intervals):
        if action_controller.check_interrupt():
            return False
        time.sleep(sleep_time)
    return True

# ========== AÇÕES ==========
def executar_ACTION_0():
    print("\n[EXECUTANDO] Ação 0")
    press('up', 0.1)
    time.sleep(0.2)
    press_combo(['left', 'c'], 0.3)
    press_combo(['right', 'c'], 8.0)

def executar_ACTION_1():
    print("\n[EXECUTANDO] Ação 1 - Primeira interação")
    if not press_combo(['right', 'c'], 2.5):
        print("[INTERROMPIDO] Ação 1")

def executar_ACTION_2():
    print("\n[EXECUTANDO] Ação 2 - Entrar e bater")
    if not press_combo(['right', 'c'], 1.0): return
    for _ in range(6):
        if not press_combo(['up', 'f'], 0.1): return
    for _ in range(3):
        if not press('x', 0.1): return
    if not press_combo(['x', 'right'], 0.1): return
    if not press_combo(['right', 'c'], 0.7): return
    if not press_combo(['left', 'c'], 10.0): return

def executar_ACTION_3():
    print("\n[EXECUTANDO] Ação 3 - Voltar")
    if not press_combo(['left', 'c'], 2.3):
        print("[INTERROMPIDO] Ação 3")

def executar_ACTION_4_reset():
    print("\n" + "="*50)
    print("[EXECUTANDO] Ação 4 - Sentar no banquinho e RESET")
    print("="*50)
    if not press('left', 0.4): return
    if not press_combo(['z', 'right'], 0.5): return
    if not press('right', 0.7): return
    if not press('up', 0.1): return
    if not sleep_interruptible(2.0): return
    print("[RESET] Contador zerado!")
    detector.reset_count()
    action_controller.set_interrupt("ACTION_0")
    print("[START] Início imediato: ACTION_0 (load_count=0)")

# ========== API p/ UI ==========
def pause_toggle():
    global paused
    paused = not paused
    print(f"[{'PAUSADO' if paused else 'RODANDO'}]")

def stop_bot():
    global running
    global cycle
    running = False
    cycle = 0
    

def is_running():
    return running

def is_paused():
    return paused

def get_load_count():
    try:
        return detector.get_load_count()
    except Exception:
        return 0

def get_cycle():
    with _cycle_lock:
        return cycle

def get_current_action_name():
    return action_controller.get_current_action()

def get_status():
    return f"Loadings: {get_load_count()} | Ciclo: {get_cycle()} | Pausado: {is_paused()}"

# ========== LOOP PRINCIPAL ==========
def run_bot():
    global running, paused, cycle
    if running:
        print("[INFO] Bot já está rodando."); return

    print(f"""
╔═══════════════════════════════════════════════════════╗
║  BOT CONTROLADO POR TELAS PRETAS v3.0                ║
║  Biblioteca: {'pydirectinput' if USING_PDI else 'pyautogui':15}                      ║
║  Scan Rate: {SCAN_INTERVAL_MS}ms | Threshold: {DARK_THRESHOLD} | Ratio: {DARK_RATIO_LOAD}  ║
╠═══════════════════════════════════════════════════════╣
║  Sistema: Cada loading executa ação específica       ║
║  • Loading 1: Ação básica | 2: Entrar e bater        ║
║  • Loading 3: Voltar     | 4: Reset + banquinho      ║
╠═══════════════════════════════════════════════════════╣
║  Teclas: F8 pausa | F9 status | ESC encerra          ║
╚═══════════════════════════════════════════════════════╝

Iniciando em 3 segundos... Foque no jogo!
""")

    running = True
    paused = False

    keyboard.Listener(on_press=on_press).start()
    detector.start()
    time.sleep(3)

    detector.load_count = 0
    action_controller.set_interrupt("ACTION_0")
    print("[START] Início imediato: ACTION_0 (load_count=0)")

    while running:
        if paused:
            time.sleep(0.1); continue

        if action_controller.check_interrupt():
            action_name = action_controller.get_current_action()
            action_controller.clear_interrupt()

            if action_name == "ACTION_0":
                with _cycle_lock:
                    print(f"[Ciclo: {cycle}]")
                    cycle += 1
                executar_ACTION_0()
            elif action_name == "ACTION_1":
                executar_ACTION_1()
            elif action_name == "ACTION_2":
                executar_ACTION_2()
            elif action_name == "ACTION_3":
                executar_ACTION_3()
            elif action_name == "ACTION_4_RESET":
                executar_ACTION_4_reset()

            print(f"[CONCLUÍDO] {action_name}\n")
        
        time.sleep(0.1)

    detector.stop()
    print("\n[FIM] Bot encerrado.")

if __name__ == "__main__":
    run_bot()
