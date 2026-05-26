#!/usr/bin/env python3
"""
Banking Client GUI – Tkinter
Fixed: Passbook & Logout only visible after login
"""

import json
import socket
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk
import serial
import serial.tools.list_ports

from virtual_puf import DEFAULT_CHALLENGE, VirtualPUFClient

class BankingClient:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 12345
        self.sock = None
        self.connected = False

        self.user = None
        self.account = None
        self.puf_value = None
        self.virtual_puf = None
        self.use_virtual_puf = False
        self.reg_mode = False
        self.netbanking_enabled = False

        self.root = tk.Tk()
        self.root.title("Banking Client")
        self.root.geometry("1000x900")
        self.root.configure(bg="#ecf0f1")
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_gui(self):
        # Title
        title = tk.Frame(self.root, bg="#3498db", height=70)
        title.pack(fill="x", pady=(0, 20))
        title.pack_propagate(False)
        tk.Label(title, text="Banking Client", font=("Arial", 18, "bold"),
                 fg="white", bg="#3498db").pack(pady=20)

        main = tk.Frame(self.root, bg="#ecf0f1")
        main.pack(fill="both", expand=True, padx=30, pady=10)

        # Server Connection
        conn = tk.LabelFrame(main, text="Server Connection", font=("Arial", 12, "bold"))
        conn.pack(fill="x", pady=(0, 20))
        f = tk.Frame(conn, bg="#ecf0f1")
        f.pack(pady=15)
        tk.Label(f, text="Server IP:", bg="#ecf0f1").pack(side="left", padx=5)
        self.ip_entry = tk.Entry(f, font=("Arial", 12), width=15)
        self.ip_entry.insert(0, self.host)
        self.ip_entry.pack(side="left", padx=5)
        self.conn_btn = tk.Button(f, text="Connect", command=self.connect,
                                  bg="#27ae60", fg="white", width=15)
        self.conn_btn.pack(side="left", padx=5)
        self.disc_btn = tk.Button(f, text="Disconnect", command=self.disconnect,
                                  bg="#e74c3c", fg="white", width=15, state="disabled")
        self.disc_btn.pack(side="left", padx=5)
        self.stat_lbl = tk.Label(conn, text="Status: Disconnected", fg="#e74c3c")
        self.stat_lbl.pack()

        # User Info
        info = tk.LabelFrame(main, text="User Information", font=("Arial", 12, "bold"))
        info.pack(fill="x", pady=(0, 20))
        self.user_lbl = tk.Label(info, text="No user logged in", fg="#7f8c8d")
        self.user_lbl.pack(pady=15)

        # Operations
        ops = tk.LabelFrame(main, text="Banking Operations", font=("Arial", 12, "bold"))
        ops.pack(fill="x", pady=(0, 20))
        self.ops_frame = tk.Frame(ops, bg="#ecf0f1")
        self.ops_frame.pack(pady=20)

        # Only Sign Up & Login visible initially
        self.signup_btn = tk.Button(self.ops_frame, text="Sign Up", command=self.register_dialog,
                                    bg="#3498db", fg="white", width=20, height=2, state="disabled")
        self.signup_btn.grid(row=0, column=0, padx=10, pady=10)

        self.login_btn = tk.Button(self.ops_frame, text="Login", command=self.login_dialog,
                                   bg="#9b59b6", fg="white", width=20, height=2, state="disabled")
        self.login_btn.grid(row=0, column=1, padx=10, pady=10)

        # Passbook & Logout hidden initially
        self.pass_btn = tk.Button(self.ops_frame, text="Passbook", command=self.open_passbook,
                                  bg="#27ae60", fg="white", width=20, height=2, state="disabled")
        # Do NOT grid yet

        self.logout_btn = tk.Button(self.ops_frame, text="Logout", command=self.logout,
                                    bg="#e74c3c", fg="white", width=20, height=2, state="disabled")
        # Do NOT grid yet

        # Progress
        prog = tk.LabelFrame(main, text="Progress", font=("Arial", 12, "bold"))
        prog.pack(fill="x", pady=(0, 20))
        self.prog_pf = tk.Frame(prog, bg="#ecf0f1")
        self.prog_pf.grid(row=0, column=0, pady=10)
        self.steps = {}

        # Log
        log = tk.LabelFrame(main, text="Activity Log", font=("Arial", 12, "bold"))
        log.pack(fill="both", expand=True)
        c = tk.Frame(log, bg="#ecf0f1")
        c.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_txt = tk.Text(c, height=8, font=("Consolas", 9), bg="#34495e", fg="#ecf0f1", wrap="word")
        sb = ttk.Scrollbar(c, orient="vertical", command=self.log_txt.yview)
        self.log_txt.configure(yscrollcommand=sb.set)
        self.log_txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def configure_progress(self, mode):
        self.clear_frame(self.prog_pf)
        self.steps = {}
        if mode == 'signup':
            steps_list = [
                ("1. Register Account", "register_account"),
                ("2. Enable NetBanking", "enable_netbanking")
            ]
        elif mode == 'login':
            steps_list = [("Login", "login")]
        else:
            return

        for i, (txt, sid) in enumerate(steps_list):
            lbl = tk.Label(self.prog_pf, text="Pending", font=("Arial", 12), fg="#f39c12", bg="#ecf0f1")
            tk.Label(self.prog_pf, text=txt, font=("Arial", 10), fg="#7f8c8d", bg="#ecf0f1").grid(row=0, column=i*2, padx=5, pady=2, sticky="e")
            lbl.grid(row=0, column=i*2+1, padx=2, pady=2, sticky="w")
            self.steps[sid] = (txt, lbl)

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def connect(self):
        self.host = self.ip_entry.get().strip()
        if not self.host:
            messagebox.showerror("Error", "Enter server IP")
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host, self.port))
            self.connected = True
            self.conn_btn.config(state="disabled")
            self.disc_btn.config(state="normal")
            self.stat_lbl.config(text=f"Connected to {self.host}:{self.port}", fg="#27ae60")
            self.signup_btn.config(state="normal")
            self.login_btn.config(state="normal")
            self.log("Connected to server")
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.connected = False

    def disconnect(self):
        if self.sock:
            self.sock.close()
        self.connected = False
        self.conn_btn.config(state="normal")
        self.disc_btn.config(state="disabled")
        self.stat_lbl.config(text="Status: Disconnected", fg="#e74c3c")
        self.signup_btn.config(state="disabled")
        self.login_btn.config(state="disabled")
        self.pass_btn.config(state="disabled")
        self.logout_btn.config(state="disabled")
        self.user = None
        self.account = None
        self.user_lbl.config(text="No user logged in", fg="#7f8c8d")
        self.clear_frame(self.prog_pf)
        self.steps = {}
        self.hide_session_buttons()
        self.show_auth_buttons()
        self.log("Disconnected")

    def send(self, action, data):
        if not self.connected:
            return None
        try:
            self.sock.send(json.dumps({"action": action, "data": data}).encode())
            resp = self.sock.recv(4096).decode()
            return json.loads(resp)
        except Exception as e:
            messagebox.showerror("Communication Error", str(e))
            self.disconnect()
            return None

    # === SIGN UP ===
    def register_dialog(self):
        self.configure_progress('signup')
        win = tk.Toplevel(self.root)
        win.title("Sign Up - New Account")
        win.geometry("600x800")
        win.transient(self.root)
        win.grab_set()
        win.configure(bg="#ecf0f1")
        tk.Label(win, text="Create New Account", font=("Arial", 16, "bold"), bg="#ecf0f1").pack(pady=20)

        f = tk.Frame(win, bg="#ecf0f1")
        f.pack(pady=10)
        labels = ["Customer Name:", "Password:", "Initial Deposit (₹):", "Mobile Number:"]
        self.reg_entries = []
        for idx, txt in enumerate(labels):
            tk.Label(f, text=txt, font=("Arial", 12), bg="#ecf0f1").grid(row=idx, column=0, sticky="e", padx=10, pady=8)
            e = tk.Entry(f, font=("Arial", 12))
            e.grid(row=idx, column=1, padx=10, pady=8)
            if idx == 2: e.insert(0, "1000")
            elif idx == 3: e.insert(0, "1234567890")
            self.reg_entries.append(e)
        self.reg_entries[0].focus()

        nb_var = tk.BooleanVar()
        nb_check = tk.Checkbutton(f, text="Enable NetBanking", variable=nb_var,
                                 command=lambda: self.toggle_netbanking(win, nb_var), font=("Arial", 11), bg="#ecf0f1")
        nb_check.grid(row=4, column=0, columnspan=2, pady=10)

        self.puf_frame = tk.Frame(win, bg="#ecf0f1")
        self.build_puf_frame_in_dialog(self.puf_frame)
        self.puf_frame.pack_forget()

        bf = tk.Frame(win, bg="#ecf0f1")
        bf.pack(pady=20, side="bottom")
        tk.Button(bf, text="Sign Up", command=lambda: self.submit_registration(win, self.reg_entries, nb_var),
                  bg="#3498db", fg="white", font=("Arial", 12, "bold"), width=12).pack(side="left", padx=10)
        tk.Button(bf, text="Cancel", command=win.destroy, bg="#95a5a6", fg="white",
                  font=("Arial", 12, "bold"), width=12).pack(side="left")

    def toggle_netbanking(self, win, nb_var):
        if nb_var.get():
            self.puf_frame.pack(fill="x", pady=10)
            self.refresh_ports()
        else:
            self.puf_frame.pack_forget()

    def build_puf_frame_in_dialog(self, parent):
        self.puf_var = tk.BooleanVar()
        tk.Checkbutton(parent, text="Enable PUF Authentication", variable=self.puf_var,
                       command=lambda: self.toggle_puf_in_dialog(parent), font=("Arial", 10), bg="#ecf0f1").pack(pady=5)
        self.puf_subframe = tk.Frame(parent, bg="#ecf0f1")

        self.virtual_puf_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            self.puf_subframe,
            text="Use Virtual PUF (Python simulator, no Arduino)",
            variable=self.virtual_puf_var,
            command=self.toggle_virtual_puf_ui,
            font=("Arial", 10),
            bg="#ecf0f1",
        ).pack(pady=5)

        row = tk.Frame(self.puf_subframe, bg="#ecf0f1")
        row.pack(fill="x", pady=5)
        tk.Label(row, text="COM Port:", bg="#ecf0f1").pack(side="left", padx=5)
        self.port_cb = ttk.Combobox(row, state="readonly", width=15)
        self.port_cb.pack(side="left", padx=5)
        tk.Button(row, text="Refresh", command=self.refresh_ports,
                  bg="#3498db", fg="white", font=("Arial", 8), width=2).pack(side="left", padx=5)
        self.con_puf_btn = tk.Button(row, text="Connect", command=self.connect_puf,
                                     bg="#27ae60", fg="white", font=("Arial", 10))
        self.con_puf_btn.pack(side="left", padx=5)

        self.puf_stat = tk.Label(self.puf_subframe, text="Disconnected", fg="#e74c3c", bg="#ecf0f1")
        self.puf_stat.pack(pady=5)
        self.read_puf_btn = tk.Button(self.puf_subframe, text="Read PUF", command=self.read_puf,
                                      bg="#9b59b6", fg="white", state="disabled")
        self.read_puf_btn.pack(pady=5)
        self.disc_puf_btn = tk.Button(self.puf_subframe, text="Disconnect", command=self.disconnect_puf,
                                      bg="#e74c3c", fg="white", state="disabled")
        self.disc_puf_btn.pack(pady=5)
        self.puf_data_lbl = tk.Label(self.puf_subframe, text="PUF Data: Not read", bg="#ecf0f1")
        self.puf_data_lbl.pack(pady=5)

    def toggle_puf_in_dialog(self, parent):
        if self.puf_var.get():
            self.puf_subframe.pack(fill="x", pady=5)
            self.toggle_virtual_puf_ui()
        else:
            self.puf_subframe.pack_forget()

    def toggle_virtual_puf_ui(self):
        use_virtual = self.virtual_puf_var.get()
        state = "disabled" if use_virtual else "readonly"
        self.port_cb.config(state=state)

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if ports:
            self.port_cb.current(0)

    def connect_puf(self):
        self.use_virtual_puf = self.virtual_puf_var.get()
        try:
            self.disconnect_puf()
            if self.use_virtual_puf:
                self.virtual_puf = VirtualPUFClient()
                self.virtual_puf.connect()
                self.puf_stat.config(text="Connected Virtual PUF (127.0.0.1:8765)", fg="#27ae60")
                self.log("Virtual PUF connected")
            else:
                port = self.port_cb.get()
                if not port:
                    messagebox.showerror("Error", "Select COM port")
                    return
                self.ser = serial.Serial(port, 115200, timeout=1)
                self.puf_stat.config(text=f"Connected {port}", fg="#27ae60")
                self.log("PUF device connected")
            self.read_puf_btn.config(state="normal")
            self.disc_puf_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.puf_stat.config(text="Connection failed", fg="#e74c3c")

    def disconnect_puf(self):
        if self.virtual_puf:
            self.virtual_puf.close()
            self.virtual_puf = None
        if hasattr(self, "ser") and self.ser and self.ser.is_open:
            self.ser.close()
        self.puf_stat.config(text="Disconnected", fg="#e74c3c")
        self.read_puf_btn.config(state="disabled")
        self.disc_puf_btn.config(state="disabled")
        self.puf_data_lbl.config(text="PUF Data: Not read")
        self.log("PUF disconnected")

    def exchange_puf_challenge(self, ser=None, virtual_client=None):
        if virtual_client and virtual_client.connected:
            return virtual_client.read_puf(DEFAULT_CHALLENGE)
        if ser and ser.is_open:
            ser.write(DEFAULT_CHALLENGE)
            time.sleep(1)
            if ser.in_waiting >= 16:
                return ser.read(16).hex()
        return None

    def read_puf(self):
        connected = (
            self.use_virtual_puf and self.virtual_puf and self.virtual_puf.connected
        ) or (hasattr(self, "ser") and self.ser and self.ser.is_open)
        if not connected:
            messagebox.showerror("Error", "No PUF connection")
            return
        try:
            resp = self.exchange_puf_challenge(
                ser=getattr(self, "ser", None),
                virtual_client=self.virtual_puf if self.use_virtual_puf else None,
            )
            if resp:
                self.puf_value = resp
                self.puf_data_lbl.config(text=f"PUF: {resp[:16]}...")
                self.log(f"PUF read (128-bit): {resp}")
            else:
                messagebox.showerror("Error", "No PUF response")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def submit_registration(self, win, ents, nb_var):
        name, pw, dep, mobile = [e.get().strip() for e in ents]
        if not all([name, pw, dep, mobile]):
            messagebox.showerror("Error", "Fill all fields")
            return
        try:
            dep = float(dep)
            if dep < 500:
                raise ValueError
            if not (len(mobile) == 10 and mobile.isdigit()):
                raise ValueError("Invalid mobile number")
        except ValueError as ve:
            messagebox.showerror("Error", f"Minimum deposit ₹500 or {str(ve)}")
            return
        if len(pw) < 4:
            messagebox.showerror("Error", "Password min 4 chars")
            return

        self.reg_mode = True
        self.netbanking_enabled = nb_var.get()
        self.log(f"Registering: {name}, mobile: {mobile}, netbanking: {self.netbanking_enabled}")
        res = self.send("register_account", {
            "name": name, "password": pw, "deposit": dep,
            "enable_netbanking": self.netbanking_enabled, "mobile_number": mobile
        })

        if res and res.get("status") == "success":
            account_no = res["account_no"]
            self.update_step("register_account", True)
            if self.netbanking_enabled:
                self.update_step("enable_netbanking", True)
                if self.puf_value:
                    # Temporarily set account to store PUF
                    temp_account = account_no
                    self.account = temp_account
                    self.store_puf(self.puf_value)
                    self.account = None  # Reset

            messagebox.showinfo(
                "Registration Successful",
                f"Account Created!\n\n"
                f"Account Number: {account_no}\n"
                f"Mobile: {mobile}\n\n"
                f"Please use these to Login."
            )
            self.log(f"Registered account {account_no}. Login required.")
            win.destroy()
        elif res and res.get("account_exists"):
            self.prompt_account_number(win, res.get("existing_account_no"), mobile)
        else:
            error_msg = res["message"] if res else "Unknown error"
            messagebox.showerror("Error", error_msg)

    def store_puf(self, puf_data):
        if not self.account:
            return
        res = self.send("store_puf", {"account_no": self.account, "puf_data": puf_data})
        if res and res["status"] == "success":
            self.log("PUF stored on server")
        else:
            messagebox.showerror("Error", "Failed to store PUF")

    def prompt_account_number(self, parent_win, existing_account_no, mobile):
        win = tk.Toplevel(self.root)
        win.title("Account Exists")
        win.geometry("400x200")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text=f"Mobile {mobile} already registered.\nEnter account number:", bg="#ecf0f1").pack(pady=20)
        e = tk.Entry(win, font=("Arial", 12))
        e.insert(0, existing_account_no or "")
        e.pack(pady=10)
        tk.Button(win, text="Verify", command=lambda: self.verify_existing_account(win, e.get(), parent_win),
                  bg="#27ae60", fg="white").pack(pady=5)
        tk.Button(win, text="Cancel", command=win.destroy, bg="#95a5a6", fg="white").pack(pady=5)

    def verify_existing_account(self, win, account_no, parent_win):
        if not account_no:
            messagebox.showerror("Error", "Enter account number")
            return
        pw = simpledialog.askstring("Password", "Enter password:", show="*", parent=win)
        res = self.send("verify_password", {"account_no": account_no, "password": pw})
        if res and res["status"] == "success":
            win.destroy()
            parent_win.destroy()
            self.account = account_no
            self.open_passbook()
        else:
            messagebox.showerror("Error", "Invalid credentials")

    # === LOGIN ===
    def login_dialog(self):
        self.configure_progress('login')
        win = tk.Toplevel(self.root)
        win.title("Login - Existing Customer")
        win.geometry("400x250")
        win.transient(self.root)
        win.grab_set()
        win.configure(bg="#ecf0f1")

        tk.Label(win, text="Login to Your Account", font=("Arial", 14, "bold"), bg="#ecf0f1").pack(pady=20)

        f = tk.Frame(win, bg="#ecf0f1")
        f.pack(pady=10)
        tk.Label(f, text="Account Number:", bg="#ecf0f1").grid(row=0, column=0, sticky="e", padx=10)
        acc_entry = tk.Entry(f, font=("Arial", 12), width=20)
        acc_entry.grid(row=0, column=1, padx=10)
        acc_entry.focus()

        def start_login():
            account_no = acc_entry.get().strip()
            if not account_no:
                messagebox.showerror("Error", "Enter account number")
                return
            pw = simpledialog.askstring("Password", "Enter password:", show="*", parent=win)
            if not pw:
                return
            self.perform_login(win, account_no, pw)

        tk.Button(win, text="Login", command=start_login, bg="#9b59b6", fg="white", width=15).pack(pady=15)
        tk.Button(win, text="Cancel", command=win.destroy, bg="#95a5a6", fg="white", width=15).pack(pady=5)

    def perform_login(self, win, account_no, password):
        res = self.send("verify_password", {"account_no": account_no, "password": password})
        if not (res and res["status"] == "success"):
            messagebox.showerror("Error", res["message"] if res else "Invalid credentials")
            return

        res = self.send("send_otp", {"account_no": account_no})
        if not (res and res["status"] == "success"):
            messagebox.showerror("Error", res["message"] if res else "OTP failed")
            return

        messagebox.showinfo("OTP Sent", "An OTP has been sent to your registered mobile number.")
        otp = simpledialog.askstring("OTP", "Enter OTP:", parent=win)
        if not otp:
            return

        res = self.send("verify_otp", {"account_no": account_no, "otp": otp})
        if not (res and res["status"] == "success"):
            messagebox.showerror("Error", res["message"] if res else "Invalid OTP")
            return

        data = res["data"]
        self.account = account_no
        self.user = data["name"]
        self.user_lbl.config(text=f"Name: {self.user} | Account: {self.account}", fg="#27ae60")

        if data.get("puf_data"):
            self.request_puf_verification(data, win)
        else:
            self.finalize_login(data, win)

    def request_puf_verification(self, data, parent_win):
        win = tk.Toplevel(self.root)
        win.title("PUF Verification")
        win.geometry("450x320")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="PUF Required", font=("Arial", 14, "bold"), bg="#ecf0f1").pack(pady=20)

        use_virtual_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            win,
            text="Use Virtual PUF (Python simulator)",
            variable=use_virtual_var,
            font=("Arial", 10),
            bg="#ecf0f1",
        ).pack(pady=5)

        row = tk.Frame(win, bg="#ecf0f1")
        row.pack(pady=10)
        tk.Label(row, text="COM:", bg="#ecf0f1").pack(side="left")
        cb = ttk.Combobox(row, values=[p.device for p in serial.tools.list_ports.comports()], width=15)
        if cb["values"]:
            cb.current(0)
        cb.pack(side="left", padx=5)
        tk.Button(row, text="Refresh", command=lambda: cb.config(values=[p.device for p in serial.tools.list_ports.comports()]))\
            .pack(side="left")

        stat = tk.Label(win, text="Disconnected", fg="#e74c3c", bg="#ecf0f1")
        stat.pack(pady=5)
        btn = tk.Button(win, text="Verify PUF", state="disabled", bg="#9b59b6", fg="white")
        btn.pack(pady=10)

        tmp_ser = {"conn": None}
        tmp_virtual = {"conn": None}

        def connect():
            try:
                if tmp_ser["conn"] and tmp_ser["conn"].is_open:
                    tmp_ser["conn"].close()
                if tmp_virtual["conn"]:
                    tmp_virtual["conn"].close()
                    tmp_virtual["conn"] = None
                if use_virtual_var.get():
                    tmp_virtual["conn"] = VirtualPUFClient()
                    tmp_virtual["conn"].connect()
                    stat.config(text="Connected Virtual PUF", fg="#27ae60")
                else:
                    tmp_ser["conn"] = serial.Serial(cb.get(), 115200, timeout=1)
                    stat.config(text="Connected", fg="#27ae60")
                btn.config(state="normal")
            except Exception as e:
                stat.config(text=str(e), fg="#e74c3c")

        def verify():
            try:
                resp = self.exchange_puf_challenge(
                    ser=tmp_ser["conn"],
                    virtual_client=tmp_virtual["conn"],
                )
                if not resp:
                    messagebox.showerror("Error", "No PUF response")
                    return
                res = self.send("verify_puf", {"account_no": self.account, "puf_data": resp})
                if res and res["status"] == "success":
                    if tmp_ser["conn"] and tmp_ser["conn"].is_open:
                        tmp_ser["conn"].close()
                    if tmp_virtual["conn"]:
                        tmp_virtual["conn"].close()
                    win.destroy()
                    self.finalize_login(data, parent_win)
                else:
                    messagebox.showerror("Error", "PUF verification failed")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(row, text="Connect", command=connect, bg="#27ae60", fg="white").pack(side="left", padx=5)
        btn.config(command=verify)

    def finalize_login(self, data, login_win):
        login_win.destroy()
        self.show_passbook_win(data)
        self.update_step("login", True)
        self.hide_auth_buttons()
        self.show_session_buttons()
        self.pass_btn.config(state="normal")
        self.logout_btn.config(state="normal")
        self.log(f"Logged in: {self.user} ({self.account})")

    def show_auth_buttons(self):
        self.signup_btn.grid(row=0, column=0, padx=10, pady=10)
        self.login_btn.grid(row=0, column=1, padx=10, pady=10)

    def hide_auth_buttons(self):
        self.signup_btn.grid_remove()
        self.login_btn.grid_remove()

    def show_session_buttons(self):
        self.pass_btn.grid(row=0, column=0, padx=10, pady=10)
        self.logout_btn.grid(row=0, column=1, padx=10, pady=10)

    def hide_session_buttons(self):
        self.pass_btn.grid_remove()
        self.logout_btn.grid_remove()

    def logout(self):
        self.user = None
        self.account = None
        self.user_lbl.config(text="No user logged in", fg="#7f8c8d")
        self.hide_session_buttons()
        self.show_auth_buttons()
        self.pass_btn.config(state="disabled")
        self.logout_btn.config(state="disabled")
        self.clear_frame(self.prog_pf)
        self.steps = {}
        self.log("Logged out")

    def open_passbook(self):
        if not self.account:
            messagebox.showerror("Error", "No account logged in")
            return
        res = self.send("verify_password", {"account_no": self.account, "password": simpledialog.askstring("Password", "Re-enter password:", show="*", parent=self.root)})
        if not (res and res["status"] == "success"):
            messagebox.showerror("Error", "Password required")
            return
        self.perform_login(None, self.account, None)

    def show_passbook_win(self, data):
        win = tk.Toplevel(self.root)
        win.title("Bank Passbook")
        win.geometry("600x500")
        win.transient(self.root)
        win.configure(bg="#ecf0f1")

        tk.Label(win, text="Bank Passbook", font=("Arial", 18, "bold"), bg="#3498db", fg="white", height=3).pack(fill="x")
        info = tk.Frame(win, bg="#ecf0f1")
        info.pack(pady=10, padx=20, fill="x")
        tk.Label(info, text=f"Holder: {data['name']}", font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(info, text=f"Account: {data['account_no']}").pack(anchor="w")
        tk.Label(info, text=f"Balance: ₹{data['balance']:.2f}", font=("Arial", 14, "bold"), fg="#27ae60").pack(anchor="w", pady=5)
        tk.Label(info, text=f"Mobile: {data.get('mobile_number', 'N/A')}").pack(anchor="w")

        trans = tk.LabelFrame(win, text="Transactions")
        trans.pack(fill="both", expand=True, padx=20, pady=10)
        tree = ttk.Treeview(trans, columns=("Date", "Desc", "Amt", "Bal"), show="headings")
        for c in tree["columns"]:
            tree.heading(c, text=c)
            tree.column(c, width=120)
        for t in data["transactions"]:
            tree.insert("", "end", values=(t["date"], t["description"],
                                           f"₹{t['amount']:.2f}", f"₹{t['balance']:.2f}"))
        tree.pack(fill="both", expand=True)

        tk.Button(win, text="Close", command=win.destroy, bg="#95a5a6", fg="white", width=15).pack(pady=10)

    def update_step(self, step, done=True):
        if step not in self.steps:
            return
        _, lbl = self.steps[step]
        lbl.config(text="Complete" if done else "Pending", fg="#27ae60" if done else "#f39c12")

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_txt.insert("end", f"[{ts}] {msg}\n")
        self.log_txt.see("end")

    def on_close(self):
        if self.connected:
            self.disconnect()
        if self.virtual_puf:
            self.virtual_puf.close()
        if hasattr(self, "ser") and self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()

    def run(self):
        self.log("Client started")
        self.hide_session_buttons()  # Ensure hidden at start
        self.root.mainloop()

if __name__ == "__main__":
    BankingClient().run()