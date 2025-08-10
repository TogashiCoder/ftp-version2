import sys
import argparse
import shutil
from pathlib import Path

from config.config_path_variables import *  # ensures paths and .env are loaded

from functions.functions_report import ReportGenerator
from functions.functions_FTP import (
    load_fournisseurs_ftp,
    load_platforms_ftp,
    upload_updated_files_to_marketplace,
)
from functions.functions_check_ready_files import check_ready_files
from functions.functions_update import mettre_a_jour_Stock
from utils import load_fournisseurs_config, load_plateformes_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Headless daily runner for FTP inventory pipeline"
    )
    parser.add_argument(
        "--suppliers",
        type=str,
        default="",
        help="Comma-separated list of suppliers to process (default: all in YAML)",
    )
    parser.add_argument(
        "--platforms",
        type=str,
        default="",
        help="Comma-separated list of platforms to process (default: all in YAML)",
    )
    parser.add_argument(
        "--dry-run-upload",
        action="store_true",
        help="Do not actually upload updated files to platform FTP (log only)",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Skip sending the HTML report email",
    )
    return parser.parse_args()


def _clean_directory_contents(dir_path: Path) -> None:
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        for item in dir_path.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    try:
                        item.unlink(missing_ok=True)
                    except TypeError:
                        # Python <3.8 compatibility
                        if item.exists():
                            item.unlink()
            except Exception:
                pass
    except Exception:
        pass


def main() -> int:
    args = parse_args()

    # Fresh start: clean local inputs/outputs before any logging starts
    _clean_directory_contents(DOSSIER_FOURNISSEURS)
    _clean_directory_contents(DOSSIER_PLATFORMS)
    _clean_directory_contents(LOG_FOLDER)
    _clean_directory_contents(UPDATED_FILES_PATH_RACINE)

    # Import logger after cleaning logs to avoid deleting an open file handler
    from config.logging_config import logger

    # Determine scope from YAML unless explicitly provided
    fournisseurs_config = load_fournisseurs_config() or {}
    plateformes_config = load_plateformes_config() or {}

    if args.suppliers.strip():
        list_fournisseurs = [s.strip() for s in args.suppliers.split(",") if s.strip()]
    else:
        list_fournisseurs = list(fournisseurs_config.keys())

    if args.platforms.strip():
        list_platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    else:
        list_platforms = list(plateformes_config.keys())

    report_gen = ReportGenerator()
    report_gen.start_operation()

    try:
        logger.info("==== Start headless update run ====")
        # 1) Download latest inputs via FTP
        fichiers_fournisseurs = load_fournisseurs_ftp(list_fournisseurs, report_gen=report_gen)
        fichiers_platforms = load_platforms_ftp(list_platforms, report_gen=report_gen)

        # 2) Validate readiness
        fournisseurs_files_valides = check_ready_files(
            title_files="Fournisseurs", downloaded_files=fichiers_fournisseurs, report_gen=report_gen
        )
        platforms_files_valides = check_ready_files(
            title_files="Plateformes", downloaded_files=fichiers_platforms, report_gen=report_gen
        )

        # 3) Update stock and write outputs
        is_store_updated = mettre_a_jour_Stock(
            platforms_files_valides, fournisseurs_files_valides, report_gen=report_gen
        )

        # 4) Upload updated files to platform FTP (unless dry run)
        if is_store_updated:
            upload_updated_files_to_marketplace(dry_run=args.dry_run_upload)
        else:
            logger.error("[ERROR]: Store update failed. Skipping upload.")

        return_code = 0 if is_store_updated else 1
        return return_code
    except Exception as e:
        logger.error(f"[FATAL]: Unhandled error in headless run: {e}")
        report_gen.add_error(str(e))
        return 1
    finally:
        report_gen.end_operation()
        # Always try to build the HTML report; optionally send email
        try:
            report_gen.generate_html_report()
            if not args.no_email:
                report_gen.send_email_report()
        except Exception as report_err:
            logger.error(f"[ERROR]: Failed to finalize report: {report_err}")


if __name__ == "__main__":
    sys.exit(main())


