# FTP Inventory Pipeline

## Overview

**FTP Inventory Pipeline** is a robust, configurable system for synchronizing inventory (stock) data between suppliers (fournisseurs) and sales platforms (plateformes). It supports a wide range of file formats, flexible column mapping (by name or index), and both manual and automated (FTP) workflows. The project is designed for businesses that need to keep platform stock levels up-to-date using supplier data.

---

## Features

- Download/upload files via FTP or select files locally
- Supports CSV, TXT, XLS, XLSX files (with or without headers)
- Flexible column mapping: by column name (header) or by index (no header)
- Data cleaning and normalization (handles special stock values)
- Aggregation of stock from multiple suppliers
- GUI for configuration, mapping, and manual updates
- Logging and error reporting
- Email notifications (optional)

---

## Folder & File Structure

```
ftp-inventory-pipeline/
├── config/                  # Configuration files (YAML, Python)
├── fichiers_fournisseurs/   # Supplier files (input)
├── fichiers_platforms/      # Platform files (input)
├── UPDATED_FILES/           # Output: updated platform files
├── gui_app/                 # GUI application code
├── functions/               # Core processing functions
├── test_unitaires/          # Unit tests
├── utils.py                 # Utilities (file reading, mapping, etc.)
├── main.py                  # Entry point (prints config paths)
├── requirements.txt         # Python dependencies
├── README.md                # This file
```

---

## Configuration

### 1. **FTP Connections**

- `config/fournisseurs_connexions.yaml`: FTP info for suppliers
- `config/plateformes_connexions.yaml`: FTP info for platforms

### 2. **Column Mappings**

- `config/header_mappings.yaml`: Maps each supplier/platform to its reference and stock columns.
  - Example (by name):
    ```yaml
    AS-PL:
      - source: name
        target: nom_reference
      - source: on_depot
        target: quantite_stock
    ```
  - Example (by index, for files without header):
    ```yaml
    SKV:
      - source: 0
        target: nom_reference
      - source: 2
        target: quantite_stock
    ```

### 3. **Encodings & Separators**

- `config/config_encodings_separateurs.yaml`: List of encodings and separators to try for CSV/TXT files.

---

## How to Use

### 1. **Start the GUI**

- Run the GUI app (e.g., `python -m gui_app.gui_main` or via your preferred method).

### 2. **Configure Connections**

- Use the GUI to add/edit supplier and platform FTP connections.

### 3. **Set Up Mappings**

- For each supplier/platform, click “Gérer les mappings de colonnes”.
- If your file **has a header row**: map by column name (e.g., `ProductReference`).
- If your file **does NOT have a header**: check the box “Fichier sans en-tête (mapper par index)” and select the column index (0 = first column, 1 = second, etc.).
- You can preview and validate your mapping with a sample file.

### 4. **Manual Update**

- Use the “Mise à Jour Manuelle” tab to select a platform and upload a supplier file for update.
- The system will apply the mapping, update the stock, and save the result.

### 5. **Automated FTP Update**

- Use the “Synchronisation des Stocks” tab to download/upload files via FTP for all configured suppliers/platforms.
- The system will process all files, update stock, and upload results.

### 6. **GUI-Based Configuration**

- Navigate to the **"⚙️ configuration"** tab to manage application-wide settings directly from the GUI.

#### Email Notification Settings

- **Enable/Disable:** Use the switch to turn email notifications on or off.
- **Recipients:** Enter a comma-separated list of email addresses that should receive the report (e.g., `email1@example.com, email2@example.com`).
- **SMTP Credentials:** Provide your SMTP username and an "App Password" (for Gmail) or standard password for other services.

#### Report Content Settings

- Use the checkboxes to select which sections you want to include in the HTML email report. Unchecked sections will be omitted from the final report.

#### Saving and Testing

- **Enregistrer (Save):** Click this button to save your changes to the configuration files (`notification_settings.yaml` and `report_settings.yaml`). The new settings are applied immediately for the next operation.
- **Tester l'Email (Test Email):** Click this to send a test email to all listed recipients to verify your SMTP settings are correct.

---

## Data Processing Flow

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
   - If multiple suppliers, sum stock by product reference.
6. **Platform Update**
   - Update platform file’s stock column using supplier data.
7. **Save/Upload**
   - Save updated files locally and/or upload via FTP.
8. **Reporting**
   - Log actions, errors, and optionally send email notifications.

---

## Error Handling & Troubleshooting

- All errors are logged (see the `logs/` directory).
- If a file cannot be read, the system tries multiple encodings and separators.
- If mapping fails (column not found), you’ll see a clear error in the GUI.
- If you don’t see expected changes in the GUI, ensure you are running the latest code and restart the app after changes.
- For files without headers, always use index mapping and check your sample file in the mapping modal.

---

## Tips & Best Practices

- Always validate your mapping with a real sample file before running updates.
- Use the preview feature to check the first 10 rows of mapped data.
- For new suppliers/platforms, add their mapping in the GUI or directly in the YAML.
- If you encounter encoding issues, update `config/config_encodings_separateurs.yaml` with additional encodings/separators.
- Keep your config files under version control for easy rollback.

---

## Example: Mapping for No-Header File

Suppose you have a file like this (no header row):

```
12345, 10, 2023-07-01
67890, 5, 2023-07-01
```

- In the mapping modal, check “Fichier sans en-tête (mapper par index)”
- Map `nom_reference` to index 0 (first column), `quantite_stock` to index 1 (second column)

---

## For Developers

- Core logic is in `functions/` and `utils.py`.
- GUI logic is in `gui_app/`.
- Unit tests are in `test_unitaires/`.
- The system is extensible: add new file types, mappings, or processing steps as needed.

---

## License

See `LICENSE` file for details.

---

For any issues or feature requests, please open an issue or contact the maintainer.
