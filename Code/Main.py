import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class MainWindow(tk.Tk):

    def __init__(self):
        super().__init__()

        # =========================
        # Cấu hình cửa sổ
        # =========================
        self.title("TCP Client")
        self.geometry("800x600")
        self.resizable(False, False)

        self.connected = False

        self.create_menu()
        self.create_main_window()

        self.add_log("[INFO] Application started")


    # =========================
    # MENU
    # =========================

    def create_menu(self):

        menubar = tk.Menu(self)

        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Home",
            command=self.show_home
        )
        file_menu.add_command(
            label="TCP Configuration",
            command=self.show_tcp
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Exit",
            command=self.destroy
        )

        menubar.add_cascade(
            label="File",
            menu=file_menu
        )

        # Menu Help
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="About",
            command=self.show_about
        )

        menubar.add_cascade(
            label="Help",
            menu=help_menu
        )

        self.config(menu=menubar)


    # =========================
    # MAIN WINDOW
    # =========================

    def create_main_window(self):

        # Tiêu đề
        title = tk.Label(
            self,
            text="TCP CLIENT",
            font=("Arial", 24, "bold")
        )

        title.pack(pady=20)

        # Navigation
        navigation = tk.Frame(self)
        navigation.pack(pady=10)

        tk.Button(
            navigation,
            text="HOME",
            width=15,
            command=self.show_home
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            navigation,
            text="TCP CONFIGURATION",
            width=20,
            command=self.show_tcp
        ).grid(row=0, column=1, padx=5)

        # Frame chứa các màn hình
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.show_home()


    # =========================
    # HOME
    # =========================

    def show_home(self):

        self.clear_content()

        title = tk.Label(
            self.content_frame,
            text="MAIN WINDOW",
            font=("Arial", 20, "bold")
        )

        title.pack(pady=30)

        description = tk.Label(
            self.content_frame,
            text="TCP Client Management System",
            font=("Arial", 14)
        )

        description.pack(pady=10)

        status = tk.Label(
            self.content_frame,
            text="Status: " +
                 ("Connected" if self.connected else "Disconnected"),
            font=("Arial", 12)
        )

        status.pack(pady=20)


    # =========================
    # TCP CONFIGURATION
    # =========================

    def show_tcp(self):

        self.clear_content()

        title = tk.Label(
            self.content_frame,
            text="TCP CONFIGURATION",
            font=("Arial", 20, "bold")
        )

        title.pack(pady=15)

        # =====================
        # Configuration Frame
        # =====================

        config_frame = tk.LabelFrame(
            self.content_frame,
            text="Connection Settings",
            padx=20,
            pady=20
        )

        config_frame.pack(
            fill="x",
            padx=30
        )

        # IP
        tk.Label(
            config_frame,
            text="IP Address:"
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        self.ip_entry = tk.Entry(
            config_frame,
            width=35
        )

        self.ip_entry.insert(
            0,
            "127.0.0.1"
        )

        self.ip_entry.grid(
            row=0,
            column=1,
            padx=10,
            pady=10
        )

        # Port
        tk.Label(
            config_frame,
            text="Port:"
        ).grid(
            row=1,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        self.port_entry = tk.Entry(
            config_frame,
            width=35
        )

        self.port_entry.insert(
            0,
            "8080"
        )

        self.port_entry.grid(
            row=1,
            column=1,
            padx=10,
            pady=10
        )

        # Log Level
        tk.Label(
            config_frame,
            text="Log Level:"
        ).grid(
            row=2,
            column=0,
            padx=10,
            pady=10,
            sticky="w"
        )

        self.log_level = ttk.Combobox(
            config_frame,
            values=[
                "DEBUG",
                "INFO",
                "WARNING",
                "ERROR"
            ],
            state="readonly",
            width=32
        )

        self.log_level.set("INFO")

        self.log_level.grid(
            row=2,
            column=1,
            padx=10,
            pady=10
        )

        # =====================
        # Buttons
        # =====================

        button_frame = tk.Frame(
            self.content_frame
        )

        button_frame.pack(pady=15)

        tk.Button(
            button_frame,
            text="CONNECT",
            width=15,
            command=self.connect
        ).grid(
            row=0,
            column=0,
            padx=5
        )

        tk.Button(
            button_frame,
            text="DISCONNECT",
            width=15,
            command=self.disconnect
        ).grid(
            row=0,
            column=1,
            padx=5
        )

        tk.Button(
            button_frame,
            text="TEST CONNECTION",
            width=20,
            command=self.test_connection
        ).grid(
            row=0,
            column=2,
            padx=5
        )

        # =====================
        # Status
        # =====================

        self.status_label = tk.Label(
            self.content_frame,
            text="Status: Disconnected",
            font=("Arial", 12, "bold")
        )

        self.status_label.pack(
            pady=5
        )

        # =====================
        # LOG
        # =====================

        log_frame = tk.LabelFrame(
            self.content_frame,
            text="System Log"
        )

        log_frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10
        )

        self.log_text = tk.Text(
            log_frame,
            height=8,
            width=75,
            state="disabled"
        )

        self.log_text.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        scrollbar = tk.Scrollbar(
            log_frame,
            command=self.log_text.yview
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.log_text.config(
            yscrollcommand=scrollbar.set
        )


    # =========================
    # CONNECT
    # =========================

    def connect(self):

        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()

        # Kiểm tra IP
        if ip == "":
            messagebox.showwarning(
                "Warning",
                "Please enter IP Address!"
            )
            return

        # Kiểm tra Port
        if not port.isdigit():

            messagebox.showwarning(
                "Warning",
                "Port must be a number!"
            )

            return

        port = int(port)

        if port < 1 or port > 65535:

            messagebox.showwarning(
                "Warning",
                "Port must be between 1 and 65535!"
            )

            return

        # =====================
        # GUI DEMO
        # =====================

        self.connected = True

        self.status_label.config(
            text=f"Status: Connected to {ip}:{port}"
        )

        self.add_log(
            f"[INFO] Connecting to {ip}:{port}"
        )

        self.add_log(
            "[SUCCESS] Connection established"
        )


    # =========================
    # DISCONNECT
    # =========================

    def disconnect(self):

        self.connected = False

        self.status_label.config(
            text="Status: Disconnected"
        )

        self.add_log(
            "[INFO] TCP connection closed"
        )


    # =========================
    # TEST CONNECTION
    # =========================

    def test_connection(self):

        ip = self.ip_entry.get().strip()
        port = self.port_entry.get().strip()

        if ip == "":
            messagebox.showwarning(
                "Warning",
                "Please enter IP Address!"
            )
            return

        if not port.isdigit():
            messagebox.showwarning(
                "Warning",
                "Port must be a number!"
            )
            return

        port = int(port)

        if port < 1 or port > 65535:
            messagebox.showwarning(
                "Warning",
                "Port must be between 1 and 65535!"
            )
            return

        self.add_log(
            f"[TEST] Testing {ip}:{port}"
        )

        self.add_log(
            "[TEST] GUI test completed successfully"
        )

        messagebox.showinfo(
            "Test Connection",
            f"Test GUI connection:\n\n"
            f"IP: {ip}\n"
            f"Port: {port}\n\n"
            f"Ready for TCP Socket module."
        )


    # =========================
    # LOG
    # =========================

    def add_log(self, message):

        current_time = datetime.now().strftime(
            "%H:%M:%S"
        )

        if hasattr(self, "log_text"):

            self.log_text.config(
                state="normal"
            )

            self.log_text.insert(
                tk.END,
                f"[{current_time}] {message}\n"
            )

            self.log_text.see(
                tk.END
            )

            self.log_text.config(
                state="disabled"
            )


    # =========================
    # CLEAR CONTENT
    # =========================

    def clear_content(self):

        for widget in self.content_frame.winfo_children():
            widget.destroy()


    # =========================
    # ABOUT
    # =========================

    def show_about(self):

        messagebox.showinfo(
            "About",
            "TCP Client\n\n"
            "GUI Developer: Trần Ngô Duy Khang\n"
            "Module: Main Window & Navigation\n"
            "Language: Python"
        )


if __name__ == "__main__":

    app = MainWindow()

    app.mainloop()