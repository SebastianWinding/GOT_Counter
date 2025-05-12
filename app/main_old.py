import asyncio
import threading
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import re
import json
import os
import sqlite3
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.chat import Chat, EventData, ChatMessage
from twitchAPI.type import AuthScope, ChatEvent

# === CONFIG ===
TARGET_CHANNEL = 'gotgames_tb'
USER_SCOPE = (
    AuthScope.CHAT_READ,
    AuthScope.CHAT_EDIT,
    AuthScope.CHANNEL_MANAGE_BROADCAST,
)

Suggestion_list = []
Counts_list = []
user_votes = {}  # Used in vote mode
stop_updates = False
listening = False
TOP_N = 10
timer_interval = 1
mode = "normal"  # Modes: normal, series
vote_mode_enabled = False

# === Load Show Titles from DB ===
def load_show_titles():
    db_path = os.path.join(os.path.dirname(__file__), "shows.db")
    if not os.path.isfile(db_path):
        print("❌ Could not find shows.db!")
        return set()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT title_romaji, title_english, synonyms FROM anime")
    shows = set()
    for row in cursor.fetchall():
        shows.update(s.lower() for s in row[0:2] if s)
        if row[2]:
            shows.update(map(str.lower, map(str.strip, row[2].split(','))))
    conn.close()
    return shows

SHOW_TITLES = load_show_titles()

# === Credential Loader ===
def load_or_prompt_credentials():
    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            return config.get('client_id'), config.get('client_secret')
    root = tk.Tk()
    root.withdraw()
    client_id = simpledialog.askstring("Twitch Credentials", "Enter your Twitch Client ID:")
    client_secret = simpledialog.askstring("Twitch Credentials", "Enter your Twitch Client Secret:")
    if not client_id or not client_secret:
        messagebox.showerror("Error", "Client ID and Secret are required. Exiting.")
        root.destroy()
        exit()
    with open(config_file, 'w') as f:
        json.dump({'client_id': client_id, 'client_secret': client_secret}, f)
    root.destroy()
    return client_id, client_secret

CLIENT_ID, CLIENT_SECRET = load_or_prompt_credentials()

# === Chat Handling ===
async def on_ready(ready_event: EventData):
    await ready_event.chat.join_room(TARGET_CHANNEL)
    print('✅ Bot has joined the channel!')

async def list_message(msg: ChatMessage):
    global Suggestion_list, Counts_list, user_votes, listening, mode, vote_mode_enabled
    if not listening:
        return

    username = msg.user.name
    text = re.sub(r'[^a-z0-9\s]', '', msg.text.lower())
    text = re.sub(r'\s+', ' ', text).strip()

    if vote_mode_enabled:
        if username not in user_votes:
            user_votes[username] = set()
        if text in user_votes[username]:
            return
        user_votes[username].add(text)

    if mode == "series":
        if text not in SHOW_TITLES:
            return

    if text not in Suggestion_list:
        Suggestion_list.append(text)
        Counts_list.append(1)
    else:
        idx = Suggestion_list.index(text)
        Counts_list[idx] += 1

def sort_suggestions():
    global Suggestion_list, Counts_list
    sorted_pairs = sorted(zip(Counts_list, Suggestion_list), reverse=True)
    if sorted_pairs:
        Counts_list[:], Suggestion_list[:] = zip(*sorted_pairs)
        Counts_list[:] = list(Counts_list)
        Suggestion_list[:] = list(Suggestion_list)

# === GUI ===
class SuggestionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 Twitch Chat Tracker")
        self.root.configure(bg="#222")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#333", foreground="white", rowheight=25,
                        fieldbackground="#333", font=("Arial", 10))
        style.map("Treeview", background=[('selected', '#555')])
        style.configure("Treeview.Heading", background="#444", foreground="white", font=("Arial", 10, "bold"))

        self.mode_label = tk.Label(self.root, text="Current Mode: Normal | Vote: Off", bg="#222", fg="#aaa", font=("Arial", 10, "italic"))
        self.mode_label.pack(pady=(5, 0))

        self.table_frame_container = tk.Frame(self.root, bg="#222", height=500, width=600)
        self.table_frame_container.pack(pady=10, fill="x")
        self.table_frame_container.pack_propagate(False)

        self.tree_scroll = tk.Scrollbar(self.table_frame_container)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            self.table_frame_container,
            columns=("Rank", "Suggestion", "Count"),
            show="headings",
            yscrollcommand=self.tree_scroll.set
        )
        self.tree_scroll.config(command=self.tree.yview)

        self.tree.column("Rank", anchor="center", width=60)
        self.tree.column("Suggestion", anchor="w", width=300)
        self.tree.column("Count", anchor="center", width=100)

        self.tree.heading("Rank", text="Rank")
        self.tree.heading("Suggestion", text="Suggestion")
        self.tree.heading("Count", text="Count")
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)

        button_frame = tk.Frame(self.root, bg="#222")
        button_frame.pack(pady=5)

        self.listen_btn = tk.Button(button_frame, text="▶ Start", command=self.toggle_listening, bg="#444", fg="white", width=16)
        self.listen_btn.grid(row=0, column=0, padx=5)

        tk.Button(button_frame, text="🔄 Reset", command=self.reset, bg="#444", fg="white", width=14).grid(row=0, column=1, padx=5)

        self.mode_btn = tk.Button(button_frame, text="Mode: Normal", command=self.toggle_mode, bg="#555", fg="white", width=16)
        self.mode_btn.grid(row=0, column=2, padx=5)

        self.vote_btn = tk.Button(button_frame, text="Vote Mode: Off", command=self.toggle_vote_mode, bg="#555", fg="white", width=16)
        self.vote_btn.grid(row=0, column=3, padx=5)

        tk.Label(button_frame, text="⏱ Timer (mm:ss):", bg="#222", fg="white").grid(row=0, column=4, padx=(10, 2))
        self.timer_entry = tk.Entry(button_frame, width=8, justify="center")
        self.timer_entry.insert(0, "00:30")
        self.timer_entry.grid(row=0, column=5)

        self.timer_btn = tk.Button(button_frame, text="⏱ Start Timer", command=self.start_timer, bg="#444", fg="white", width=14)
        self.timer_btn.grid(row=0, column=6, padx=5)

        config_frame = tk.Frame(self.root, bg="#222")
        config_frame.pack(pady=5)

        tk.Label(config_frame, text="Top N:", bg="#222", fg="white").grid(row=0, column=0, padx=5)
        self.top_n_var = tk.IntVar(value=TOP_N)
        self.top_n_var.trace_add("write", self.update_top_n)
        tk.Spinbox(config_frame, from_=1, to=50, textvariable=self.top_n_var, width=5).grid(row=0, column=1)

        tk.Label(config_frame, text="Update Interval (s):", bg="#222", fg="white").grid(row=0, column=2, padx=5)
        self.interval_var = tk.IntVar(value=timer_interval)
        self.interval_var.trace_add("write", self.update_interval)
        tk.Spinbox(config_frame, from_=1, to=60, textvariable=self.interval_var, width=5).grid(row=0, column=3)

        self.root.after(1000, self.refresh_table)

    def update_top_n(self, *_):
        global TOP_N
        TOP_N = self.top_n_var.get()

    def update_interval(self, *_):
        global timer_interval
        timer_interval = self.interval_var.get()

    def toggle_mode(self):
        global mode
        mode = "series" if mode == "normal" else "normal"
        self.update_mode_label()

    def toggle_vote_mode(self):
        global vote_mode_enabled
        vote_mode_enabled = not vote_mode_enabled
        self.update_mode_label()

    def update_mode_label(self):
        label = f"Current Mode: {'Series' if mode == 'series' else 'Normal'} | Vote: {'On' if vote_mode_enabled else 'Off'}"
        self.mode_label.config(text=label)
        self.mode_btn.config(text=f"Mode: {'Series' if mode == 'series' else 'Normal'}")
        self.vote_btn.config(text=f"Vote Mode: {'On' if vote_mode_enabled else 'Off'}")

    def update_table(self):
        sort_suggestions()
        self.tree.delete(*self.tree.get_children())
        top_suggestions = Suggestion_list[:TOP_N]
        top_counts = Counts_list[:TOP_N]
        for i, (s, c) in enumerate(zip(top_suggestions, top_counts), 1):
            self.tree.insert("", "end", values=(i, s, c))

    def refresh_table(self):
        if not stop_updates:
            self.update_table()
        self.root.after(timer_interval * 1000, self.refresh_table)

    def reset(self):
        Suggestion_list.clear()
        Counts_list.clear()
        user_votes.clear()
        self.update_table()

    def toggle_updates(self):
        global stop_updates
        stop_updates = not stop_updates

    def toggle_listening(self):
        global listening
        listening = not listening
        state = "Stop" if listening else "Start"
        self.listen_btn.config(text=f"{'⏹' if listening else '▶'} {state}")

    def start_timer(self):
        time_str = self.timer_entry.get()
        try:
            minutes, seconds = map(int, time_str.split(":"))
            total_seconds = minutes * 60 + seconds
        except ValueError:
            self.timer_btn.config(text="⚠ Invalid format")
            self.root.after(2000, lambda: self.timer_btn.config(text="⏱ Start Timer"))
            return
        if total_seconds <= 0:
            return
        global listening
        listening = True
        self.listen_btn.config(text="⏹ Stop")
        self.timer_btn.config(state="disabled")

        def countdown(secs_left):
            if secs_left <= 0:
                global listening
                listening = False
                self.listen_btn.config(text="▶ Start")
                self.timer_btn.config(state="normal")
                self.timer_btn.config(text="⏱ Start Timer")
                return
            mins, secs = divmod(secs_left, 60)
            self.timer_btn.config(text=f"⏱ {mins:02}:{secs:02}")
            self.root.after(1000, countdown, secs_left - 1)

        countdown(total_seconds)

# === Run Bot ===
async def run_bot():
    twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)
    auth = UserAuthenticator(twitch, USER_SCOPE)
    token, refresh_token = await auth.authenticate()
    await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)
    chat = await Chat(twitch)
    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.MESSAGE, list_message)

    chat_started = threading.Event()
    def start_chat():
        chat_started.set()
        chat.start()
    chat_thread = threading.Thread(target=start_chat, daemon=True)
    chat_thread.start()

    root = tk.Tk()
    _gui = SuggestionGUI(root)
    try:
        root.mainloop()
    finally:
        if chat_started.is_set():
            chat.stop()
        await twitch.close()

if __name__ == '__main__':
    asyncio.run(run_bot())
