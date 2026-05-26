#!/usr/bin/env python3
"""
Banking Client GUI – Tkinter
Supports Sign Up (new) and Login (existing) with 3-factor auth
"""

import json
import socket
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk
import serial
import serial.tools.list_ports

class BankingClient:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 12345
        self.sock = None
        self.connected = False

        self.user = None
        self.account = None
        self.puf_value = None
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

        self.signup_btn = tk.Button(self.ops_frame, text="Sign Up", command=self.register_dialog,
                                    bg="#3498db", fg="white", width=20, height=2, state="disabled")
        self.signup_btn.grid(row=0, column=0, padx=10, pady=10)

        self.login_btn = tk.Button(self.ops_frame, text="Login", command=self.login_dialog,
                                   bg="#9b59b6", fg="white", width=20, height=2, state="disabled")
        self.login_btn.grid(row=0, column=1, padx=10, pady=10)

        self.pass_btn = tk.Button(self.ops_frame, text="Passbook", command=self.open_passbook,
                                  bg="#27ae60", fg="white", width=20, height=2, state="disabled")
        self.pass_btn.grid(row=0, column=2, padx=10, pady=10)

        # Progress
        prog = tk.LabelFrame(main, text="Progress", font=("Arial", 12, "bold"))
        prog.pack(fill="x", pady=(0, 20))
        pf = tk.Frame(prog, bg="#ecf0f1")
        pf.grid(row=0, column=0, pady=10)
        self.steps = {
            "register_account": ("1. Register Account", tk.Label(pf, text="Pending")),
            "enable_netbanking": ("2. Enable NetBanking", tk.Label(pf, text="Pending")),
            "access_passbook": ("3. Access Passbook", tk.Label(pf, text="Pending"))
        }
        for i, (sid, (txt, lbl)) in enumerate(self.steps.items()):
            lbl.config(font=("Arial", 12), fg="#f39c12", bg="#ecf0f1")
            tk.Label(pf, text=txt, font=("Arial", 10), fg="#7f8c8d", bg="#ecf0f1").grid(row=0, column=i*2, padx=5, pady=2, sticky="e")
            lbl.grid(row=0, column=i*2+1, padx=2, pady=2, sticky="w")

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
        self.user = None
        self.account = None
        self.user_lbl.config(text="No user logged in", fg="#7f8c8d")
        self.update_step("register_account", False)
        self.update_step("enable_netbanking", False)
        self.update_step("access_passbook", False)
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

    # === SIGN UP (REGISTER) DIALOG ===
    def register_dialog(self):
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
            if idx == 2:
                e.insert(0, "1000")
            elif idx == 3:
                e.insert(0, "1234567890")
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
                       command=lambda: self.toggle_puf_in_dialog(parent), font=("Arial", 10), bg="#ecf0f1")\
            .pack(pady=5)
        self.puf_subframe = tk.Frame(parent, bg="#ecf0f1")

        row = tk.Frame(self.puf_subframe, bg="#ecf0f1")
        row.pack(fill="x", pady=5)
        tk.Label(row, text="COM Port:", bg="#ecf0f1").pack(side="left", padx=5)
        self.port_cb = ttk.Combobox(row, state="readonly", width=15)
        self.port_cb.pack(side="left", padx=5)
        tk.Button(row, text="Refresh", command=self.refresh_ports,
                  bg="#3498db", fg="white", font=("Arial", 8), width=2)\
            .pack(side="left", padx=5)
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
            self.refresh_ports()
        else:
            self.puf_subframe.pack_forget()

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if ports:
            self.port_cb.current(0)

    def connect_puf(self):
        port = self.port_cb.get()
        if not port:
            messagebox.showerror("Error", "Select COM port")
            return
        try:
            if hasattr(self, "ser") and self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = serial.Serial(port, 115200, timeout=1)
            self.puf_stat.config(text=f"Connected {port}", fg="#27ae60")
            self.read_puf_btn.config(state="normal")
            self.disc_puf_btn.config(state="normal")
            self.log("PUF device connected")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.puf_stat.config(text="Connection failed", fg="#e74c3c")

    def disconnect_puf(self):
        if hasattr(self, "ser") and self.ser and self.ser.is_open:
            self.ser.close()
            self.puf_stat.config(text="Disconnected", fg="#e74c3c")
            self.read_puf_btn.config(state="disabled")
            self.disc_puf_btn.config(state="disabled")
            self.puf_data_lbl.config(text="PUF Data: Not read")
            self.log("PUF device disconnected")

    def read_puf(self):
        if not (hasattr(self, "ser") and self.ser and self.ser.is_open):
            messagebox.showerror("Error", "No COM connection")
            return
        try:
            challenge = bytes.fromhex("ffc3330ff0aacc30ff0aacc01ffc3301")
            self.ser.write(challenge)
            time.sleep(1)
            if self.ser.in_waiting >= 16:
                resp = self.ser.read(16).hex()
                self.puf_value = resp
                self.puf_data_lbl.config(text=f"PUF: {resp[:16]}...")
                self.log(f"PUF read: {resp}")
                if self.reg_mode and self.puf_value:
                    self.store_puf_on_server()
            else:
                messagebox.showerror("Error", "No PUF response")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def store_puf_on_server(self):
        if not (self.account and self.puf_value):
            return
        res = self.send("store_puf", {"account_no": self.account, "puf_data": self.puf_value})
        if res and res["status"] == "success":
            self.log("PUF stored on server")
        else:
            msg = res["message"] if res else "Unknown"
            messagebox.showerror("Error", "Store PUF failed: " + msg)

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
            self.user = name
            self.account = res["account_no"]
            self.user_lbl.config(text=f"Name: {name} | Account: {self.account}", fg="#27ae60")
            self.update_step("register_account", True)
            if self.netbanking_enabled:
                self.update_step("enable_netbanking", True)
                if self.puf_value:
                    self.store_puf_on_server()
            messagebox.showinfo("Success", f"Account registered: {self.account}")
            self.hide_auth_buttons()
            self.pass_btn.config(state="normal")
            win.destroy()
        elif res and res.get("account_exists"):
            self.prompt_account_number(win, res.get("existing_account_no"), mobile)
        else:
            error_msg = res["message"] if res else "Unknown error"
            messagebox.showerror("Error", error_msg)

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

    # === LOGIN DIALOG ===
    def login_dialog(self):
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
        win.geometry("400x300")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="PUF Required", font=("Arial", 14, "bold"), bg="#ecf0f1").pack(pady=20)

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

        def connect():
            try:
                if hasattr(self, "tmp_ser") and self.tmp_ser.is_open:
                    self.tmp_ser.close()
                self.tmp_ser = serial.Serial(cb.get(), 115200, timeout=1)
                stat.config(text="Connected", fg="#27ae60")
                btn.config(state="normal")
            except Exception as e:
                stat.config(text=str(e), fg="#e74c3c")

        def verify():
            try:
                self.tmp_ser.write(bytes.fromhex("ffc3330ff0aacc30ff0aacc01ffc3301"))
                time.sleep(1)
                resp = self.tmp_ser.read(16).hex()
                res = self.send("verify_puf", {"account_no": self.account, "puf_data": resp})
                if res and res["status"] == "success":
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
        self.update_step("access_passbook", True)
        self.hide_auth_buttons()
        self.pass_btn.config(state="normal")
        self.log(f"Logged in: {self.user} ({self.account})")

    def hide_auth_buttons(self):
        self.signup_btn.grid_remove()
        self.login_btn.grid_remove()
        self.pass_btn.grid(row=0, column=0, padx=10, pady=10)

    # === PASSBOOK ACCESS ===
    def open_passbook(self):
        if not self.account:
            messagebox.showerror("Error", "No account logged in")
            return
        res = self.send("verify_password", {"account_no": self.account, "password": simpledialog.askstring("Password", "Re-enter password:", show="*", parent=self.root)})
        if not (res and res["status"] == "success"):
            messagebox.showerror("Error", "Password required")
            return
        self.perform_login(None, self.account, None)  # Skip password prompt

    def show_passbook_win(self, data):
        win = tk.Toplevel(self.root)
        win.title("Bank Passbook")
        win.geometry("600x500")
        win.transient(self.root)
        win.configure(bg="#ecf0f1")

        tk.Label(win, text="Bank Passbook", font=("Arial", 18, "bold"), bg="#3498db", fg="white", height=3)\
            .pack(fill="x")
        info = tk.Frame(win, bg="#ecf0f1")
        info.pack(pady=10, padx=20, fill="x")
        tk.Label(info, text=f"Holder: {data['name']}", font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(info, text=f"Account: {data['account_no']}").pack(anchor="w")
        tk.Label(info, text=f"Balance: ₹{data['balance']:.2f}", font=("Arial", 14, "bold"), fg="#27ae60")\
            .pack(anchor="w", pady=5)
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
        _, lbl = self.steps[step]
        lbl.config(text="Complete" if done else "Pending", fg="#27ae60" if done else "#f39c12")

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_txt.insert("end", f"[{ts}] {msg}\n")
        self.log_txt.see("end")

    def on_close(self):
        if self.connected:
            self.disconnect()
        if hasattr(self, "ser") and self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()

    def run(self):
        self.log("Client started")
        self.root.mainloop()

if __name__ == "__main__":
    BankingClient().run()