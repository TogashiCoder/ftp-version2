import customtkinter as ctk
from tkinter import messagebox
from utils import load_yaml_config, save_yaml_config, send_test_email
from config.config_path_variables import CONFIG

class ConfigurationFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.notification_settings_path = CONFIG / "notification_settings.yaml"
        self.report_settings_path = CONFIG / "report_settings.yaml"

        self.notification_config = load_yaml_config(self.notification_settings_path) or {}
        self.report_config = load_yaml_config(self.report_settings_path) or {}
        
        self.build_gui()

    def build_gui(self):
        # --- Main Layout ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scrollable_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        scrollable_frame.grid_columnconfigure(0, weight=1)

        # --- Email Notifications Section ---
        email_frame = ctk.CTkFrame(scrollable_frame)
        email_frame.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        email_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(email_frame, text="Paramètres de Notification par Email", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(5,10))
        
        self.email_enabled = ctk.BooleanVar(value=self.notification_config.get('enabled', False))
        ctk.CTkSwitch(email_frame, text="Activer les notifications par email", variable=self.email_enabled).grid(row=1, column=0, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(email_frame, text="Destinataires (séparés par des virgules) :").grid(row=2, column=0, sticky="w", padx=10, pady=(10, 0))
        self.recipients_entry = ctk.CTkEntry(email_frame)
        self.recipients_entry.insert(0, ", ".join(self.notification_config.get('recipients', [])))
        self.recipients_entry.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(email_frame, text="Utilisateur SMTP :").grid(row=4, column=0, sticky="w", padx=10, pady=(10, 0))
        self.smtp_user_entry = ctk.CTkEntry(email_frame)
        self.smtp_user_entry.insert(0, self.notification_config.get('smtp_user', ''))
        self.smtp_user_entry.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(email_frame, text="Mot de passe SMTP :").grid(row=6, column=0, sticky="w", padx=10, pady=(10, 0))
        self.smtp_password_entry = ctk.CTkEntry(email_frame, show="*")
        self.smtp_password_entry.insert(0, self.notification_config.get('smtp_password', ''))
        self.smtp_password_entry.grid(row=7, column=0, sticky="ew", padx=10, pady=5)
        
        # --- Report Content Section ---
        report_frame = ctk.CTkFrame(scrollable_frame)
        report_frame.grid(row=1, column=0, pady=10, sticky="ew")
        report_frame.grid_columnconfigure(0, weight=1)
        report_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(report_frame, text="Contenu du Rapport", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(5,10))
        
        self.report_vars = {}
        report_sections = self.report_config.get('sections', {})
        if report_sections:
            row, col = 1, 0
            for section, enabled in report_sections.items():
                var = ctk.BooleanVar(value=enabled)
                checkbox = ctk.CTkCheckBox(report_frame, text=section.replace('_', ' ').title(), variable=var)
                checkbox.grid(row=row, column=col, padx=10, pady=2, sticky="w")
                self.report_vars[section] = var
                col += 1
                if col > 1:
                    col = 0
                    row += 1
            
        # --- Action Buttons ---
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, padx=10, pady=(10, 20), sticky="e")
        
        ctk.CTkButton(button_frame, text="Tester l'Email", command=self.test_email).pack(side="left", padx=(0, 10))
        ctk.CTkButton(button_frame, text="Enregistrer", command=self.save_settings).pack(side="left")

    def save_settings(self):
        # Save notification settings
        self.notification_config['enabled'] = self.email_enabled.get()
        self.notification_config['recipients'] = [email.strip() for email in self.recipients_entry.get().split(',') if email.strip()]
        self.notification_config['smtp_user'] = self.smtp_user_entry.get()
        self.notification_config['smtp_password'] = self.smtp_password_entry.get()
        
        if not save_yaml_config(self.notification_config, self.notification_settings_path):
            messagebox.showerror("Erreur", "Échec de la sauvegarde des paramètres de notification.")
            return

        # Save report settings
        report_sections = self.report_config.get('sections', {})
        for section, var in self.report_vars.items():
            if section in report_sections:
                report_sections[section] = var.get()
        
        if not save_yaml_config(self.report_config, self.report_settings_path):
            messagebox.showerror("Erreur", "Échec de la sauvegarde des paramètres du rapport.")
            return

        messagebox.showinfo("Succès", "Les paramètres ont été enregistrés avec succès.")

    def test_email(self):
        smtp_user = self.smtp_user_entry.get()
        smtp_password = self.smtp_password_entry.get()
        recipients = [email.strip() for email in self.recipients_entry.get().split(',') if email.strip()]

        if not all([smtp_user, smtp_password, recipients]):
            messagebox.showwarning("Champs manquants", "Veuillez remplir l'utilisateur SMTP, le mot de passe et au moins un destinataire.")
            return
            
        self.after(10, lambda: self.send_email_in_thread(smtp_user, smtp_password, recipients))

    def send_email_in_thread(self, user, password, recipients):
        # Disable button to prevent multiple clicks
        # This assumes the button is accessible; for simplicity, we are not disabling it here,
        # but in a real-world scenario, you would manage the button state.
        
        import threading
        thread = threading.Thread(target=self.execute_sending, args=(user, password, recipients))
        thread.start()

    def execute_sending(self, user, password, recipients):
        success, message = send_test_email(user, password, recipients)
        
        # Schedule the messagebox to be shown in the main thread
        self.after(0, lambda: self.show_result_message(success, message))

    def show_result_message(self, success, message):
        if success:
            messagebox.showinfo("Succès", message)
        else:
            messagebox.showerror("Échec", message)
