import time
from datetime import datetime
from typing import List
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
import yagmail
import os
from utils import load_yaml_config
from config.config_path_variables import CONFIG

class ReportGenerator:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.stats = {
            'suppliers_processed': set(),
            'platforms_processed': set(),
            'files_successful': [],
            'files_failed': [],
            'products_updated': 0,
            'errors': [],
            'warnings': []
        }
        self.html_report = None
        self.logger = logging.getLogger("ReportGenerator")

    def start_operation(self):
        self.start_time = time.time()
        self.end_time = None
        self.stats = {
            'suppliers_processed': set(),
            'platforms_processed': set(),
            'files_successful': [],
            'files_failed': [],
            'products_updated': 0,
            'errors': [],
            'warnings': []
        }
        self.html_report = None
        self.logger.info("Début de l'opération de mise à jour.")

    def end_operation(self):
        self.end_time = time.time()
        self.logger.info("Fin de l'opération de mise à jour.")

    def add_supplier_processed(self, supplier_name):
        self.stats['suppliers_processed'].add(supplier_name)

    def add_platform_processed(self, platform_name):
        self.stats['platforms_processed'].add(platform_name)

    def add_file_result(self, file_path, success, error_msg=None):
        if success:
            self.stats['files_successful'].append(file_path)
        else:
            self.stats['files_failed'].append({'file': file_path, 'error': error_msg})
            if error_msg:
                self.stats['errors'].append(error_msg)

    def add_products_count(self, count):
        self.stats['products_updated'] += count

    def add_error(self, error_msg):
        self.stats['errors'].append(error_msg)

    def add_warning(self, warning_msg):
        self.stats['warnings'].append(warning_msg)

    def generate_html_report(self):
        try:
            report_settings = load_yaml_config(CONFIG / "report_settings.yaml")
            env = Environment(
                loader=FileSystemLoader(searchpath=os.path.join(os.path.dirname(__file__), '../templates')),
                autoescape=select_autoescape(['html', 'xml'])
            )
            template = env.get_template('email_report_template.html')
            duration = self._get_duration()
            status = 'success' if not self.stats['errors'] and not self.stats['files_failed'] else 'failure'
            
            context = {
                'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'status': status,
                'duration': duration,
                'sections': report_settings.get('sections', {})
            }

            if context['sections'].get('suppliers_processed', True):
                context['suppliers_processed'] = len(self.stats['suppliers_processed'])
            if context['sections'].get('platforms_processed', True):
                context['platforms_processed'] = len(self.stats['platforms_processed'])
            if context['sections'].get('files_successful', True):
                context['files_successful'] = len(self.stats['files_successful'])
                context['files_successful_list'] = self.stats['files_successful']
            if context['sections'].get('files_failed', True):
                context['files_failed'] = len(self.stats['files_failed'])
                context['files_failed_list'] = self.stats['files_failed']
            if context['sections'].get('products_updated', True):
                context['products_updated'] = self.stats['products_updated']
            if context['sections'].get('errors', True):
                context['errors'] = self.stats['errors']
            if context['sections'].get('warnings', True):
                context['warnings'] = self.stats['warnings']

            html = template.render(**context)
            self.html_report = html
            self.logger.info("Rapport HTML généré avec succès.")
            return html
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du rapport HTML : {e}")
            self.html_report = None
            return None

    def generate_pdf_report(self):
        # Optionnel : à implémenter avec reportlab
        self.logger.info("Génération du rapport PDF non implémentée.")
        return None

    def send_email_report(self):
        notification_settings = load_yaml_config(CONFIG / "notification_settings.yaml")
        if not notification_settings.get('enabled'):
            self.logger.info("L'envoi d'emails est désactivé dans la configuration.")
            return False
            
        try:
            if not self.html_report:
                self.generate_html_report()
            if not self.html_report:
                self.logger.error("Impossible d'envoyer le rapport : rapport HTML non généré.")
                return False
            
            smtp_email = notification_settings.get('smtp_user')
            smtp_password = notification_settings.get('smtp_password')
            recipients = notification_settings.get('recipients')

            if not smtp_email or not smtp_password or not recipients:
                self.logger.error("Identifiants SMTP ou destinataires manquants dans la configuration.")
                return False
            
            yag = yagmail.SMTP(user=smtp_email, password=smtp_password)
            subject = f"Rapport Mise à Jour Automatique – {datetime.now().strftime('%d/%m/%Y')}"
            yag.send(
                to=recipients,
                subject=subject,
                contents=self.html_report
            )
            self.logger.info(f"Rapport envoyé par email à : {', '.join(recipients)}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi du rapport par email : {e}")
            return False

    def _get_duration(self):
        if self.start_time and self.end_time:
            total_seconds = int(self.end_time - self.start_time)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02}:{minutes:02}:{seconds:02}" 