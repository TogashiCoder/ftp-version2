import time
from datetime import datetime
from typing import List
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
import yagmail
import os
import csv
import pandas as pd
from pathlib import Path
from utils import load_yaml_config
from config.config_path_variables import CONFIG, LOG_FOLDER

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
            'stock_changes': [],  # New field to track actual changes
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
            'stock_changes': [],  # Reset stock changes
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
    
    def add_stock_changes(self, changes):
        """Add stock changes to the report"""
        self.stats['stock_changes'].extend(changes)
        # Update the count of products actually updated
        self.stats['products_updated'] = len(self.stats['stock_changes'])

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
                # Add stock changes details
                context['stock_changes'] = self.stats['stock_changes']
                context['has_stock_changes'] = len(self.stats['stock_changes']) > 0

                # Build per-platform summary: changed_count and supplier contribution percentages using real supplier names
                per_platform = {}
                for change in self.stats['stock_changes']:
                    platform = change.get('platform')
                    if not platform:
                        continue
                    entry = per_platform.setdefault(platform, {
                        'changed_count': 0,
                        'total_new_quantity': 0,
                        'supplier_totals': {},
                        'supplier_article_counts': {}
                    })
                    entry['changed_count'] += 1
                    new_q = change.get('new_quantity', 0) or 0
                    entry['total_new_quantity'] += int(new_q)
                    supplier_details = change.get('supplier_details', {}) or {}
                    for supplier, qty in supplier_details.items():
                        entry['supplier_totals'][supplier] = entry['supplier_totals'].get(supplier, 0) + (qty or 0)
                        # Count articles per supplier (only count if supplier contributes > 0)
                        try:
                            qty_val = int(qty)
                        except Exception:
                            qty_val = 0
                        if qty_val > 0:
                            entry['supplier_article_counts'][supplier] = entry['supplier_article_counts'].get(supplier, 0) + 1

                # Compute percentages per supplier
                platform_change_summary = []
                for platform, data in per_platform.items():
                    total_new = data['total_new_quantity'] if data['total_new_quantity'] else 0
                    supplier_percentages = {}
                    # Include suppliers with 0 contribution if configured
                    include_zero = report_settings.get('include_zero_contributions', True)
                    # Determine full supplier set from entire run (stable across multiple updates)
                    all_suppliers = set()
                    try:
                        all_suppliers = set(self.stats.get('all_suppliers', set()))
                    except Exception:
                        pass
                    # Fallback to per-platform scan if global set is empty
                    if not all_suppliers:
                        for ch in self.stats['stock_changes']:
                            if ch.get('platform') == platform and isinstance(ch.get('supplier_details'), dict):
                                all_suppliers.update(ch['supplier_details'].keys())
                    # Build percentages
                    candidate_suppliers = sorted(all_suppliers) if include_zero else sorted(data['supplier_totals'].keys())
                    for supplier in candidate_suppliers:
                        total_qty = data['supplier_totals'].get(supplier, 0)
                        percent = (total_qty / total_new) * 100 if total_new else 0
                        supplier_percentages[supplier] = round(percent, 1)
                    # Build article counts aligned to suppliers
                    supplier_article_counts = {}
                    for supplier in candidate_suppliers:
                        supplier_article_counts[supplier] = int(data['supplier_article_counts'].get(supplier, 0))
                    platform_change_summary.append({
                        'platform': platform,
                        'changed_count': data['changed_count'],
                        'supplier_percentages': supplier_percentages,
                        'supplier_article_counts': supplier_article_counts
                    })
                # Sort by platform name for stable display
                platform_change_summary.sort(key=lambda x: x['platform'])
                context['platform_change_summary'] = platform_change_summary
                context['has_platform_change_summary'] = len(platform_change_summary) > 0
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
    
    def generate_csv_report(self):
        """Generate CSV files with stock changes - one per platform"""
        try:
            if not self.stats['stock_changes']:
                self.logger.info("Aucun changement de stock à exporter en CSV.")
                return []
            
            # Create timestamp for consistent naming
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create DataFrame from stock changes
            df_all = pd.DataFrame(self.stats['stock_changes'])
            
            # Get all unique supplier names
            all_suppliers = set()
            for change in self.stats['stock_changes']:
                if 'supplier_details' in change and isinstance(change['supplier_details'], dict):
                    all_suppliers.update(change['supplier_details'].keys())
            
            sorted_suppliers = sorted(list(all_suppliers))
            
            # Prepare data for DataFrame
            records = []
            for change in self.stats['stock_changes']:
                record = {
                    'platform': change['platform'],
                    'product_id': change['product_id'],
                    'old_quantity': change['old_quantity'],
                    'new_quantity': change['new_quantity'],
                    'difference': change['new_quantity'] - change['old_quantity'],
                    'run_timestamp': timestamp
                }
                
                # Add individual supplier quantities
                if 'supplier_details' in change and isinstance(change['supplier_details'], dict):
                    for supplier in sorted_suppliers:
                        record[f'stock_{supplier}'] = change['supplier_details'].get(supplier, 0)
                
                records.append(record)
            
            df_all = pd.DataFrame(records)
            # Enforce column order: core columns first, then supplier columns (sorted)
            core_cols = ['platform', 'product_id', 'old_quantity', 'new_quantity', 'difference', 'run_timestamp']
            supplier_cols = [f'stock_{s}' for s in sorted_suppliers]
            for col in core_cols:
                if col not in df_all.columns:
                    df_all[col] = None
            for col in supplier_cols:
                if col not in df_all.columns:
                    df_all[col] = None
            df_all = df_all[core_cols + supplier_cols]
            platforms = df_all['platform'].unique()
            csv_files = []
            
            for platform in platforms:
                # Filter data for this platform
                df_platform = df_all[df_all['platform'] == platform].copy()
                
                # Create filename for this platform
                csv_filename = f"stock_changes_{platform}_{timestamp}.csv"
                csv_path = LOG_FOLDER / csv_filename
                
                # Save to CSV (sorted by product_id for easier review)
                try:
                    df_platform_sorted = df_platform.sort_values(by=['product_id'])
                except Exception:
                    df_platform_sorted = df_platform
                df_platform_sorted.to_csv(csv_path, index=False, encoding='utf-8-sig')
                
                csv_files.append(csv_path)
                self.logger.info(f"Rapport CSV généré pour {platform} : {csv_path}")
            
            return csv_files
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération des rapports CSV : {e}")
            return []

    def send_email_report(self):
        notification_settings = load_yaml_config(CONFIG / "notification_settings.yaml")
        report_settings = load_yaml_config(CONFIG / "report_settings.yaml")
        
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
            
            # Prepare email contents
            contents = [self.html_report]
            
            # Generate and attach CSV files if enabled and there are stock changes
            if report_settings.get('attach_csv', True) and self.stats['stock_changes']:
                csv_paths = self.generate_csv_report()
                if csv_paths:
                    # Enforce total size cap for attachments
                    max_mb = report_settings.get('max_attachment_mb', 10)
                    try:
                        max_bytes = int(max_mb) * 1024 * 1024
                    except Exception:
                        max_bytes = 10 * 1024 * 1024
                    total_bytes = 0
                    for csv_path in csv_paths:
                        if csv_path.exists():
                            try:
                                size = csv_path.stat().st_size
                            except Exception:
                                size = 0
                            if total_bytes + size <= max_bytes:
                                contents.append(str(csv_path))
                                total_bytes += size
                                self.logger.info(f"Fichier CSV ajouté en pièce jointe : {csv_path.name}")
                            else:
                                self.logger.warning(f"Pièce jointe ignorée (taille max atteinte) : {csv_path.name}")
            
            yag = yagmail.SMTP(user=smtp_email, password=smtp_password)
            subject = f"Rapport Mise à Jour Automatique – {datetime.now().strftime('%d/%m/%Y')}"
            
            # Send email with or without attachment
            yag.send(
                to=recipients,
                subject=subject,
                contents=contents
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