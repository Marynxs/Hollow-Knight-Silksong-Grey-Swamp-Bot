# ui.py
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import bot_core

REFRESH_MS = 300 

class BotGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HollowBot")
        self.geometry("420x260")
        self.resizable(False, False)

        s = ttk.Style(self)
        try: s.theme_use("clam")
        except: pass

        # Header
        ttk.Label(self, text="Farm Grey Swamp Silksong", font=("Segoe UI", 13, "bold")).pack(pady=(16, 8))

        # Painel de status
        panel = ttk.Frame(self)
        panel.pack(pady=(0, 12), padx=12, fill="x")

        self.lbl_status_val = tk.StringVar(value="stopped")
        self.lbl_cycle_val  = tk.StringVar(value="0")
        self.lbl_loads_val  = tk.StringVar(value="0")
        self.lbl_action_val = tk.StringVar(value="-")

        row1 = ttk.Frame(panel); row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="Status:", width=16).pack(side="left")
        ttk.Label(row1, textvariable=self.lbl_status_val).pack(side="left")

        row2 = ttk.Frame(panel); row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="Cycle:", width=16).pack(side="left")
        ttk.Label(row2, textvariable=self.lbl_cycle_val).pack(side="left")

        row3 = ttk.Frame(panel); row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="Current Action:", width=16).pack(side="left")
        ttk.Label(row3, textvariable=self.lbl_action_val).pack(side="left")

        # Botões
        btns = ttk.Frame(self)
        btns.pack(pady=8)
        self.start_btn = ttk.Button(btns, text="Start Bot", command=self.start_bot)
        self.pause_btn = ttk.Button(btns, text="Pause/Continue (F8)", command=self.pause_bot, state="disabled")
        self.stop_btn  = ttk.Button(btns, text="Stop Bot (Esc)", command=self.stop_bot, state="disabled")
        self.start_btn.grid(row=0, column=0, padx=6)
        self.pause_btn.grid(row=0, column=1, padx=6)
        self.stop_btn.grid(row=0, column=2, padx=6)

        # Atualização periódica
        self.after(REFRESH_MS, self.refresh_panel)

    # --- Ações dos botões ---
    def start_bot(self):
        if bot_core.is_running():
            messagebox.showinfo("Bot", "Bot alreay running")
            return

        def _run():
            try:
                self.update_buttons(True)
                bot_core.run_bot()
            except Exception as e:
                messagebox.showerror("Bot Error", str(e))
            finally:
                self.update_buttons(False)
                self.lbl_status_val.set("Stopped")

        threading.Thread(target=_run, daemon=True).start()
        self.lbl_status_val.set("running")

    def pause_bot(self):
        if not bot_core.is_running():
            return
        bot_core.pause_toggle()
        # O painel se atualiza sozinho no refresh_panel()

    def stop_bot(self):
        if not bot_core.is_running():
            return
        bot_core.stop_bot()

    # --- UI helpers ---
    def update_buttons(self, running: bool):
        if running:
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.stop_btn.config(state="normal")
        else:
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled")
            self.stop_btn.config(state="disabled")

    def refresh_panel(self):
        running = bot_core.is_running()
        paused  = bot_core.is_paused()
        loads   = bot_core.get_load_count()
        cycle   = bot_core.get_cycle()
        action  = bot_core.get_current_action_name()

        self.lbl_status_val.set("running (paused)" if (running and paused) else ("running" if running else "stopped"))
        self.lbl_cycle_val.set(str(cycle))
        self.lbl_loads_val.set(str(loads))
        self.lbl_action_val.set(action if action else "-")

        self.update_buttons(running)
        self.after(REFRESH_MS, self.refresh_panel)

if __name__ == "__main__":
    app = BotGUI()
    app.mainloop()
