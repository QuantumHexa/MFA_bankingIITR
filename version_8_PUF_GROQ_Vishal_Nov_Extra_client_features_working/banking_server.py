#!/usr/bin/env python3
"""
Banking Server GUI – Tkinter
Handles client requests for registration, authentication, and passbook with a graphical interface
Uses SQLite database for persistent storage
Sends OTP via Fast2SMS API
"""

import json
import os
import socket
import sqlite3
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import requests


class BankingServer:
    def __init__(self):
        self.host = "0.0.0.0"
        self.port = 12345
        self.server = None
        self.running = False
        self.admin_password = "admin123"
        self.fast2sms_api_key = "B4waH0tR6oXcMShkx8jbu2YqZi9yr7mV1ICnpsEePGWLfvlQDA8Tjt30M51l2BDUYSQkZ9RzpXe4acKF"

        self.root = tk.Tk()
        self.root.title("Banking Server")
        self.root.geometry("700x600")
        self.root.configure(bg="#ecf0f1")
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_gui(self):
        title = tk.Frame(self.root, bg="#3498db", height=70)
        title.pack(fill="x", pady=(0, 20))
        title.pack_propagate(False)
        tk.Label(
            title,
            text="Banking Server",
            font=("Arial", 18, "bold"),
            fg="white",
            bg="#3498db",
        ).pack(pady=20)

        main = tk.Frame(self.root, bg="#ecf0f1")
        main.pack(fill="both", expand=True, padx=30, pady=10)

        status = tk.LabelFrame(main, text="Server Status", font=("Arial", 12, "bold"))
        status.pack(fill="x", pady=(0, 20))
        f = tk.Frame(status, bg="#ecf0f1")
        f.pack(pady=15)
        self.start_btn = tk.Button(
            f,
            text="Start Server",
            command=self.start_server,
            bg="#27ae60",
            fg="white",
            width=15,
        )
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = tk.Button(
            f,
            text="Stop Server",
            command=self.stop_server,
            bg="#e74c3c",
            fg="white",
            width=15,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=5)
        self.stat_lbl = tk.Label(status, text="Status: Stopped", fg="#e74c3c")
        self.stat_lbl.pack()

        admin = tk.Frame(main, bg="#ecf0f1")
        admin.pack(pady=10)
        self.admin_btn = tk.Button(
            admin,
            text="Admin View",
            command=self.show_admin_login,
            bg="#e67e22",
            fg="white",
            width=15,
            state="disabled",
        )
        self.admin_btn.pack()

        log = tk.LabelFrame(main, text="Activity Log", font=("Arial", 12, "bold"))
        log.pack(fill="both", expand=True)
        c = tk.Frame(log, bg="#ecf0f1")
        c.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_txt = tk.Text(
            c, height=15, font=("Consolas", 9), bg="#34495e", fg="#ecf0f1", wrap="word"
        )
        sb = ttk.Scrollbar(c, orient="vertical", command=self.log_txt.yview)
        self.log_txt.configure(yscrollcommand=sb.set)
        self.log_txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_txt.insert("end", f"[{ts}] {msg}\n")
        self.log_txt.see("end")

    def setup_database(self):
        conn = sqlite3.connect("banking.db")
        cursor = conn.cursor()
        try:
            cursor.execute("""CREATE TABLE IF NOT EXISTS accounts
                             (account_no TEXT PRIMARY KEY, name TEXT, password TEXT, balance REAL,
                              netbanking INTEGER, puf_data TEXT, transactions TEXT, otp TEXT, mobile_number TEXT)""")
            cursor.execute("PRAGMA table_info(accounts)")
            columns = [col[1] for col in cursor.fetchall()]
            if "mobile_number" not in columns:
                cursor.execute("ALTER TABLE accounts ADD COLUMN mobile_number TEXT")
                self.log("Added mobile_number column")
            if "otp" not in columns:
                cursor.execute("ALTER TABLE accounts ADD COLUMN otp TEXT")
                self.log("Added otp column")
            conn.commit()
        except Exception as e:
            self.log(f"Database setup error: {e}")
            conn.rollback()
        finally:
            conn.close()
        self.log("Database initialized")

    def reset_database(self):
        if messagebox.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset the database? This will delete all data!",
        ):
            try:
                if os.path.exists("banking.db"):
                    os.remove("banking.db")
                self.setup_database()
                self.log("Database reset successfully")
            except Exception as e:
                self.log(f"Database reset error: {e}")
                messagebox.showerror("Error", f"Failed to reset database: {e}")

    def get_next_account_no(self, conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT account_no FROM accounts ORDER BY account_no DESC LIMIT 1"
        )
        last_account = cursor.fetchone()
        current_date = datetime.now().strftime("%Y%m%d")
        if last_account:
            last_no = last_account[0]
            date_part = last_no[:8]
            if date_part == current_date:
                num_part = int(last_no[9:]) + 1
            else:
                num_part = 1
        else:
            num_part = 1
        return f"{current_date}_{num_part:03d}"

    def show_admin_login(self):
        if not self.running:
            messagebox.showerror("Error", "Start the server first")
            return
        win = tk.Toplevel(self.root)
        win.title("Admin Login")
        win.geometry("300x150")
        win.configure(bg="#ecf0f1")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="Admin Password", font=("Arial", 12), bg="#ecf0f1").pack(
            pady=20
        )
        pw_entry = tk.Entry(win, show="*", font=("Arial", 12))
        pw_entry.pack(pady=10)
        tk.Button(
            win,
            text="Login",
            command=lambda: self.verify_admin_login(win, pw_entry.get()),
            bg="#27ae60",
            fg="white",
            width=10,
        ).pack(pady=5)
        tk.Button(
            win, text="Cancel", command=win.destroy, bg="#95a5a6", fg="white", width=10
        ).pack(pady=5)

    def verify_admin_login(self, win, password):
        if password == self.admin_password:
            win.destroy()
            self.show_admin_view()
        else:
            messagebox.showerror("Error", "Incorrect admin password")

    def show_admin_view(self):
        win = tk.Toplevel(self.root)
        win.title("Admin View - All Accounts")
        win.geometry("800x600")
        win.configure(bg="#ecf0f1")
        win.transient(self.root)

        frame = tk.Frame(win, bg="#ecf0f1")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("Account No", "Name", "Balance", "Netbanking", "Mobile Number")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        conn = sqlite3.connect("banking.db")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT account_no, name, balance, netbanking, mobile_number FROM accounts"
            )
            for row in cursor.fetchall():
                tree.insert(
                    "",
                    "end",
                    values=(
                        row[0],
                        row[1],
                        f"₹{row[2]:.2f}",
                        "Yes" if row[3] else "No",
                        row[4] or "N/A",
                    ),
                )
        except Exception as e:
            self.log(f"Admin view error: {e}")
        finally:
            conn.close()

        tk.Button(
            win,
            text="Reset Database",
            command=self.reset_database,
            bg="#e74c3c",
            fg="white",
            width=15,
        ).pack(pady=10)
        tk.Button(
            win, text="Close", command=win.destroy, bg="#95a5a6", fg="white", width=15
        ).pack(pady=10)

    def send_sms_via_fast2sms(self, otp, mobile_number):
        message = f"Hi. Your OTP is {otp}. Valid for 5 minutes. - YourBank"
        url = "https://www.fast2sms.com/dev/bulkV2"
        mobile_number = str(mobile_number).strip()
        if not (mobile_number.isdigit() and len(mobile_number) == 10):
            self.log(f"Invalid mobile number: {mobile_number}")
            return False

        headers = {
            "authorization": self.fast2sms_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "route": "q",
            "message": message,
            "flash": 0,
            "numbers": mobile_number,
            "sender_id": "FSTSMS",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()
            self.log(f"SMS API Full Response: {result}")

            if result.get("return") is True:
                self.log(f"OTP sent successfully to {mobile_number}")
                return True
            else:
                error_msg = result.get("message", "Unknown error")
                if isinstance(error_msg, list):
                    error_msg = " | ".join(error_msg)
                self.log(f"SMS failed: {error_msg}")
                return False
        except Exception as e:
            self.log(f"SMS error: {e}")
            return False

    def handle_client(self, client_socket, address):
        self.log(f"New connection from {address}")
        conn = sqlite3.connect("banking.db")
        try:
            while True:
                data = client_socket.recv(4096).decode()
                if not data:
                    break
                request = json.loads(data)
                action = request.get("action")
                data = request.get("data", {})

                response = {"status": "error", "message": "Unknown action"}
                if action == "register_account":
                    name = data.get("name")
                    password = data.get("password")
                    deposit = data.get("deposit")
                    enable_netbanking = data.get("enable_netbanking", False)
                    mobile_number = data.get("mobile_number")
                    self.log(
                        f"Register attempt: name={name}, deposit={deposit}, netbanking={enable_netbanking}, mobile={mobile_number}"
                    )
                    if not all([name, password, deposit, mobile_number]):
                        response = {"status": "error", "message": "Invalid data"}
                    else:
                        try:
                            deposit = float(deposit)
                            if deposit < 500:
                                response = {
                                    "status": "error",
                                    "message": "Minimum deposit ₹500",
                                }
                            else:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT account_no FROM accounts WHERE mobile_number = ?",
                                    (mobile_number,),
                                )
                                existing_account = cursor.fetchone()
                                if existing_account:
                                    response = {
                                        "status": "error",
                                        "message": "Account exists with this mobile number",
                                        "account_exists": True,
                                        "existing_account_no": existing_account[0],
                                    }
                                else:
                                    account_no = self.get_next_account_no(conn)
                                    transactions = json.dumps(
                                        [
                                            {
                                                "date": datetime.now().strftime(
                                                    "%Y-%m-%d %H:%M:%S"
                                                ),
                                                "description": "Initial deposit",
                                                "amount": deposit,
                                                "balance": deposit,
                                            }
                                        ]
                                    )
                                    cursor.execute(
                                        "INSERT INTO accounts (account_no, name, password, balance, netbanking, puf_data, transactions, otp, mobile_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                        (
                                            account_no,
                                            name,
                                            password,
                                            deposit,
                                            int(enable_netbanking),
                                            None,
                                            transactions,
                                            None,
                                            mobile_number,
                                        ),
                                    )
                                    conn.commit()
                                    response = {
                                        "status": "success",
                                        "message": "Account registered",
                                        "account_no": account_no,
                                    }
                                    self.log(
                                        f"Registered account {account_no} for {name}"
                                    )
                        except Exception as e:
                            response = {
                                "status": "error",
                                "message": f"Server error: {str(e)}",
                            }
                            self.log(f"Registration failed: {e}")

                elif action == "verify_password":
                    account_no = data.get("account_no")
                    password = data.get("password")
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT password FROM accounts WHERE account_no = ?",
                        (account_no,),
                    )
                    result = cursor.fetchone()
                    if result and result[0] == password:
                        response = {"status": "success"}
                    else:
                        response = {"status": "error", "message": "Invalid credentials"}

                elif action == "send_otp":
                    account_no = data.get("account_no")
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT mobile_number FROM accounts WHERE account_no = ?",
                        (account_no,),
                    )
                    account_data = cursor.fetchone()
                    if account_data:
                        mobile_number = account_data[0]
                        if (
                            not mobile_number
                            or len(mobile_number) != 10
                            or not mobile_number.isdigit()
                        ):
                            response = {
                                "status": "error",
                                "message": "Invalid mobile number in database",
                            }
                        else:
                            otp = str(
                                abs(
                                    hash(
                                        f"{account_no}{datetime.now().strftime('%Y%m%d%H%M')}"
                                    )
                                )
                                % 1000000
                            ).zfill(6)
                            if self.send_sms_via_fast2sms(otp, mobile_number):
                                cursor.execute(
                                    "UPDATE accounts SET otp = ? WHERE account_no = ?",
                                    (otp, account_no),
                                )
                                conn.commit()
                                response = {
                                    "status": "success",
                                    "message": "OTP sent successfully.",
                                }
                                self.log(f"OTP {otp} sent to {mobile_number}")
                            else:
                                response = {
                                    "status": "error",
                                    "message": "Failed to send OTP. Check server logs.",
                                }
                    else:
                        response = {"status": "error", "message": "Account not found"}

                elif action == "verify_otp":
                    account_no = data.get("account_no")
                    otp = data.get("otp")
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT otp FROM accounts WHERE account_no = ?", (account_no,)
                    )
                    result = cursor.fetchone()
                    if result and result[0] == otp:
                        cursor.execute(
                            "UPDATE accounts SET otp = NULL WHERE account_no = ?",
                            (account_no,),
                        )
                        conn.commit()
                        cursor.execute(
                            "SELECT account_no, name, balance, netbanking, puf_data, transactions, mobile_number FROM accounts WHERE account_no = ?",
                            (account_no,),
                        )
                        result = cursor.fetchone()
                        if result:
                            transactions = json.loads(result[5])
                            response = {
                                "status": "success",
                                "data": {
                                    "account_no": result[0],
                                    "name": result[1],
                                    "balance": result[2],
                                    "netbanking": bool(result[3]),
                                    "puf_data": result[4],
                                    "transactions": transactions,
                                    "mobile_number": result[6],
                                },
                            }
                    else:
                        response = {"status": "error", "message": "Invalid OTP"}

                elif action == "store_puf":
                    account_no = data.get("account_no")
                    puf_data = data.get("puf_data")
                    if account_no and puf_data:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE accounts SET puf_data = ? WHERE account_no = ?",
                            (puf_data, account_no),
                        )
                        conn.commit()
                        response = {"status": "success"}
                        self.log(f"Stored PUF for account {account_no}")
                    else:
                        response = {"status": "error", "message": "Invalid PUF data"}

                elif action == "verify_puf":
                    account_no = data.get("account_no")
                    puf_data = data.get("puf_data")
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT puf_data FROM accounts WHERE account_no = ?",
                        (account_no,),
                    )
                    result = cursor.fetchone()
                    if result and result[0] == puf_data:
                        response = {"status": "success"}
                    else:
                        response = {
                            "status": "error",
                            "message": "PUF verification failed",
                        }

                client_socket.send(json.dumps(response).encode())
        except Exception as e:
            self.log(f"Error handling {address}: {e}")
        finally:
            conn.close()
        client_socket.close()
        self.log(f"Connection closed from {address}")

    def start_server(self):
        if self.running:
            return
        try:
            self.setup_database()
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(5)
            self.running = True
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.stat_lbl.config(
                text=f"Status: Running on {self.host}:{self.port}", fg="#27ae60"
            )
            self.admin_btn.config(state="normal")
            self.log(f"Server started on {self.host}:{self.port}")

            def accept_clients():
                while self.running:
                    try:
                        client_socket, address = self.server.accept()
                        client_thread = threading.Thread(
                            target=self.handle_client, args=(client_socket, address)
                        )
                        client_thread.daemon = True
                        client_thread.start()
                    except Exception as e:
                        if self.running:
                            self.log(f"Accept error: {e}")

            self.accept_thread = threading.Thread(target=accept_clients)
            self.accept_thread.daemon = True
            self.accept_thread.start()
        except Exception as e:
            messagebox.showerror("Server Error", str(e))
            self.running = False

    def stop_server(self):
        if not self.running:
            return
        self.running = False
        if self.server:
            self.server.close()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.stat_lbl.config(text="Status: Stopped", fg="#e74c3c")
        self.admin_btn.config(state="disabled")
        self.log("Server stopped")

    def on_close(self):
        self.stop_server()
        self.root.destroy()

    def run(self):
        self.log("Server GUI started")
        self.root.mainloop()


if __name__ == "__main__":
    BankingServer().run()
