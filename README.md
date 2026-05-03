# Tati Simple Mode

A simple personal money dashboard built with Python, Streamlit, SQLite, pandas, Plotly, and reportlab.

## What It Does

- Shows a clean Dashboard with income, money out, cash left, savings balance, and Steven amount.
- Adds daily money movement in one simple Add Entry form.
- Saves everything to a local SQLite database named `expenses.db`.
- Uses one main cash flow table for income and expenses.
- Shows a pie chart of money out by source.
- Uses clear mobile-friendly tabs: Dashboard, Add Entry, Steven, Savings, Plans, and Reports.
- Creates CSV exports and monthly PDF reports.
- Preserves older data by migrating old cash flow and transaction records into the new simple cash flow table.

## Install and Run

1. Install Python 3.10 or newer from <https://www.python.org/downloads/>.

   During installation, check the box named `Add python.exe to PATH`.

2. Open a terminal in this folder:

   ```powershell
   cd "C:\Users\tatia\Documents\New project 2"
   ```

3. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

4. Activate the virtual environment:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

5. Install the required packages:

   ```powershell
   pip install streamlit pandas plotly reportlab
   ```

6. Run the app:

   ```powershell
   streamlit run app.py
   ```

7. Open the local URL shown in the terminal, usually:

   ```text
   http://localhost:8501
   ```

## Faster Windows Launch

After you finish the install steps above, you can create a small batch file and desktop shortcut.

1. In the same folder as `app.py`, create a new file named:

   ```text
   run_tati_simple_mode.bat
   ```

2. Open `run_tati_simple_mode.bat` in Notepad and paste this:

   ```bat
   @echo off
   cd /d "%~dp0"
   call .venv\Scripts\activate.bat
   streamlit run app.py
   ```

3. Save and close the file.

4. Double-click `run_tati_simple_mode.bat` to start the app.

5. To make a desktop shortcut:

   - Right-click `run_tati_simple_mode.bat`.
   - Choose `Show more options`.
   - Choose `Send to`.
   - Choose `Desktop (create shortcut)`.

6. Rename the desktop shortcut to:

   ```text
   Tati Simple Mode
   ```

## Notes

- The app creates `expenses.db` automatically the first time it runs.
- Your data stays on your computer.
- Older saved records are not deleted.
- To start over, close the app and delete `expenses.db`.
