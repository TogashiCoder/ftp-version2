# FTP Inventory Pipeline

## Overview

**FTP Inventory Pipeline** is a robust, extensible system for synchronizing inventory (stock) data between suppliers (fournisseurs) and sales platforms (plateformes). It supports a wide range of file formats, flexible column mapping (by name or index), multi-file aggregation, and both manual and automated (FTP) workflows. The project is designed for businesses that need to keep platform stock levels up-to-date using supplier data, with maximum reliability and transparency.

---

## Features & Techniques (Detailed)

### **File Format Handling**

- Supports CSV, TXT, XLS, XLSX files for both input and output.
- Automatically detects file type by extension.
- Intermediate/verification files are always saved as CSV for speed and reliability; final output matches the original platform file's extension (Excel or CSV).

### **Encoding & Separator Detection**

- Tries multiple encodings and separators (from `config/config_encodings_separateurs.yaml`) to robustly read supplier/platform files.
- Uses `chardet` for fast encoding detection.
- Defaults to comma if separator is missing or invalid.

### **Header vs. No-Header File Support**

- Handles files with or without header rows.
- For no-header files, mapping is done by column index (0-based).
- For header files, mapping is done by column name.
- The `no_header` flag is set per supplier/platform in the mapping YAML and GUI.

### **Flexible Column Mapping**

- Mapping is configured in `config/header_mappings.yaml`.
- Each mapping can specify columns by name or index.
- GUI allows you to set and preview mappings, including for files without headers.
- Mapping structure supports `no_header` and `multi_file` flags for each entity.

### **Multi-File Supplier Support & Aggregation**

- Some suppliers provide multiple files (e.g., for different warehouses).
- The system downloads all relevant files, applies the same mapping, and aggregates stock by product reference (summing quantities).
- Aggregation is done using pandas `concat` and `groupby().sum()`.

### **Data Cleaning & Normalization**

- Stock values are cleaned and normalized using `process_stock_value`:
  - Handles values like `"AVAILABLE"`, `"N/A"`, `">10"`, `"<5"`, negative numbers, and more.
  - Always converts to integer for reliable aggregation and merging.
- Product references are always converted to string before merging to avoid type errors.

### **Robust Error Handling & Logging**

- Extensive logging at every step (INFO, WARNING, ERROR, DEBUG).
- If a file cannot be read, the system tries all encodings/separators and logs all attempts.
- If mapping or merge fails, the error is logged, reported, and the script continues with other files.
- All errors are included in the HTML/email report for transparency.

### **Output File Format Logic**

- Final output for each platform is saved with the same extension as the original platform file (e.g., `.csv`, `.xls`, `.xlsx`, `.txt`).
- Excel output uses the correct engine and only saves as Excel when needed.
- Intermediate/verification files are always saved as CSV, even if the input was Excel.

### **GUI Features & Configuration**

- GUI for managing FTP connections, column mappings, and manual/automated updates.
- Allows setting `no_header` and `multi_file` flags per supplier/platform.
- Preview and validate mappings with sample files.
- Configuration is saved in YAML files for easy editing and backup.

### **Email Notification & Reporting System**

- Sends HTML email reports after each update operation.
- Report includes summary, errors, warnings, and file-level results.
- Email settings and report sections are configurable in the GUI.

### **FTP Download/Upload Logic**

- Connects to supplier and platform FTP servers using credentials from YAML config.
- Downloads all relevant files for each supplier/platform.
- Uploads updated files to platform FTP, matching the required file format.

### **YAML Configuration Structure**

- All connections, mappings, encodings, and settings are stored in YAML files for transparency and version control.
- Example mapping for a no-header file:
  ```yaml
  SKV:
    columns:
      - source: 0
        target: nom_reference
      - source: 2
        target: quantite_stock
    multi_file: false
    no_header: true
  ```

### **Extensibility & Best Practices**

- Modular codebase: core logic in `functions/` and `utils.py`, GUI in `gui_app/`, tests in `test_unitaires/`.
- Easy to add new suppliers/platforms, file types, or processing steps.
- All config files should be kept under version control.
- Always validate mappings with real sample files before running updates.
- Use the preview feature to check mapped data.

---

## Data Processing Flow (Step-by-Step)

1. **File Acquisition**
   - Download from FTP or select locally.
2. **File Reading**
   - Detect encoding, separator, and header (if present).
   - Read as pandas DataFrame.
3. **Column Mapping**
   - Use mapping (by name or index) to identify reference and stock columns.
4. **Data Cleaning**
   - Normalize stock values (e.g., “AVAILABLE” → 3, “N/A” → 0, negatives → 0).
5. **Aggregation**
   - If multiple supplier files, sum stock by product reference.
6. **Platform Update**
   - Update platform file’s stock column using supplier data.
7. **Save/Upload**
   - Save updated files locally and/or upload via FTP, matching the original file extension.
8. **Reporting**
   - Log actions, errors, and optionally send email notifications.

---

## Example Workflow

1. **Download supplier and platform files from FTP.**
2. **Read each file, auto-detecting encoding and separator.**
3. **Apply column mapping (by name or index) as configured.**
4. **Clean and normalize stock values.**
5. **Aggregate stock for multi-file suppliers.**
6. **Update each platform file, matching the original file extension.**
7. **Upload updated files to platform FTP.**
8. **Send HTML/email report with summary, errors, and file-level results.**

---

## Error Handling & Troubleshooting

- All errors are logged (see the `logs/` directory).
- If a file cannot be read, the system tries multiple encodings and separators.
- If mapping fails (column not found), you’ll see a clear error in the GUI and report.
- If a merge fails due to type mismatch, the error is logged and the platform is skipped.
- If you don’t see expected changes, ensure you are running the latest code and restart the app after changes.
- For files without headers, always use index mapping and check your sample file in the mapping modal.

---

## Tips & Best Practices

- Use CSV for all intermediate/verification saves; only use Excel for final output if required.
- Always convert product reference columns to string before merging.
- Validate your mapping with a real sample file before running updates.
- Use the preview feature to check the first 10 rows of mapped data.
- For new suppliers/platforms, add their mapping in the GUI or directly in the YAML.
- If you encounter encoding issues, update `config/config_encodings_separateurs.yaml` with additional encodings/separators.
- Keep your config files under version control for easy rollback.

---

## Changelog / Recent Improvements

- **CSV-first processing:** All intermediate/verification files are saved as CSV for speed and reliability.
- **Final output matches platform input extension:** Ensures compatibility with all platforms.
- **Robust error handling:** Merge/type errors, mapping errors, and file read errors are logged and reported, not fatal.
- **Multi-file supplier support:** Aggregates stock from multiple files per supplier.
- **No-header file support:** Allows mapping by column index for files without headers.
- **GUI improvements:** Mapping preview, validation, and configuration of `no_header`/`multi_file` flags.
- **Email/HTML reporting:** Detailed reports with errors, warnings, and file-level results.
- **Extensive logging:** All actions, errors, and warnings are logged for transparency and debugging.

---

## For Developers

- Core logic is in `functions/` and `utils.py`.
- GUI logic is in `gui_app/`.
- Unit tests are in `test_unitaires/`.
- The system is modular and extensible: add new file types, mappings, or processing steps as needed.
- All configuration is in YAML for transparency and version control.

---

## License

See `LICENSE` file for details.

---

For any issues or feature requests, please open an issue or contact the maintainer.

## Code Structure and Function Explanations

### Project Structure

```
ftp-inventory-pipeline/
├── config/                  # YAML configuration files
├── fichiers_fournisseurs/   # Supplier files (input)
├── fichiers_platforms/      # Platform files (input)
├── UPDATED_FILES/           # Output: updated platform files
├── Verifier/                # Verification/intermediate files (CSV)
├── gui_app/                 # GUI application code (see below)
├── functions/               # Core backend logic (see below)
├── utils.py                 # Utilities (file reading, mapping, etc.)
├── main.py                  # Entry point
├── requirements.txt         # Python dependencies
├── README.md                # This file
```

---

### Backend: `functions/` Directory

#### functions_update.py

- **update_plateforme(df_platform, df_fournisseurs, name_platform, name_fournisseur):**

  - Merges supplier stock into the platform DataFrame by product reference.
  - Ensures supplier stock is cleaned and normalized.
  - Handles missing/extra products and updates only where matches are found.

- **mettre_a_jour_Stock(valide_fichiers_platforms, valide_fichiers_fournisseurs, report_gen=None):**

  - Main entry for updating all platforms.
  - Reads all supplier files, aggregates if needed, and updates each platform file.
  - Handles all error logging, output file naming (matches original extension), and reporting.

- **cumule_fournisseurs(data_fournisseurs):**

  - Aggregates stock from multiple supplier files (multi-warehouse).
  - Sums stock by product reference, ensures all references are strings, and saves verification files.

- **read_fournisseur(data_f):**

  - Reads a supplier file (or files), applies mapping, cleans stock values, and returns a standardized DataFrame.

- **read_all_fournisseurs(valide_fichiers_fournisseurs):**
  - Reads and processes all supplier files, returning a dict of processed DataFrames.

#### functions_check_ready_files.py

- **keep_data_with_header_specified(list_fichiers):**
  - Validates and prepares supplier/platform files for processing, extracting mapping and flags.
- **verifier_fichiers_existent(list_files):**
  - Checks that all required files exist before processing.
- **check_ready_files(title_files, downloaded_files, report_gen=None):**
  - Orchestrates file validation and readiness checks.

#### functions_FTP.py

- **download_file_from_ftp(ftp, remote_file, local_file):**
  - Downloads a file from an FTP server.
- **load_fournisseurs_ftp(list_fournisseurs, report_gen=None):**
  - Downloads all supplier files from FTP, supports multi-file suppliers.
- **load_platforms_ftp(list_platforms, report_gen=None):**
  - Downloads all platform files from FTP.

#### functions_report.py

- **ReportGenerator class:**
  - Handles HTML/email report generation, logging, and statistics.

#### function_cumule.py

- **read_data_and_save_params(index, data_f):**
  - Debug/test function for reading and saving supplier data with mapping.

---

### Utilities: `utils.py`

- **save_file(file_name, df, ...):**
  - Saves DataFrames as CSV (default) or Excel (if required for final output).
- **read_dataset_file(file_name, ...):**
  - Reads any supported file type, auto-detects encoding/separator/header.
- **process_stock_value(value):**
  - Cleans and normalizes stock values (handles “AVAILABLE”, “N/A”, “>10”, etc.).
- **get_entity_mappings(entity):**
  - Loads mapping, no_header, and multi_file flags for a supplier/platform.
- **get_column_by_mapping(df, mapping):**
  - Resolves column by name or index.

---

### GUI: `gui_app/` Directory

#### gui_main.py

- **Main entry point for the GUI application.**
- Initializes the main window and navigation.

#### gui_fournisseurs.py

- **FournisseurAdminFrame:**
  - Manages supplier connections and mappings.
  - Allows adding/editing FTP connections, setting column mappings, and flags (`no_header`, `multi_file`).
  - Provides mapping preview and validation.

#### gui_platforms.py

- **PlateformFrame:**
  - Manages platform connections and mappings.
  - Similar features as `gui_fournisseurs.py` but for platforms.

#### gui_ftp.py

- **MajFTPFrame:**
  - Handles the automated FTP update workflow.
  - Orchestrates downloading, processing, updating, and uploading for all suppliers/platforms.

#### gui_manuelle_maj.py

- **MajManuelleFrame:**
  - Handles manual update workflow (user selects files, runs update, previews result).

#### gui_configuration.py

- **ConfigurationFrame:**
  - Manages global settings, email notification configuration, and report content selection.

#### gui_verification.py

- **(Short utility for verification display, if used.)**

---

### How the Pieces Work Together

1. **User configures suppliers/platforms and mappings in the GUI.**
2. **User runs manual or automated update (via GUI).**
3. **Backend functions handle file download, reading, mapping, cleaning, aggregation, and updating.**
4. **All intermediate/verification files are saved as CSV.**
5. **Final output matches the original platform file’s extension and is uploaded to FTP.**
6. **A detailed HTML/email report is generated and sent.**
7. **All errors, warnings, and actions are logged for transparency and debugging.**
