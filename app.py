from datetime import date, datetime, timedelta
from io import BytesIO
import sqlite3

import pandas as pd
from PIL import Image
try:
    import plotly.express as px
except ImportError:
    px = None
import streamlit as st
import streamlit.components.v1 as components
try:
    from supabase import create_client
except ImportError:
    create_client = None

icon = Image.open("icon.png")

st.set_page_config(
    page_title="Tati Finance",
    page_icon=icon,
    layout="wide",
)

# --- Password protection ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

try:
    APP_PASSWORD = st.secrets["APP_PASSWORD"]
except Exception:
    st.error("APP_PASSWORD is missing. Add it in Streamlit Secrets.")
    st.stop()

# 🔐 LOGIN SCREEN
if not st.session_state["logged_in"]:
    st.title("🔐 Tati Finance Login")

    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()  

# ✅ NOW it's in the correct place

# 🔓 AFTER LOGIN
if st.session_state["logged_in"]:
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

components.html(
    """
    <script>
    const iconHref = new URL("app/static/icon.png", window.parent.location.href).href;
    const parentDocument = window.parent.document;

    function upsertIconLink(rel) {
        let link = parentDocument.querySelector(`link[rel="${rel}"]`);
        if (!link) {
            link = parentDocument.createElement("link");
            link.setAttribute("rel", rel);
            parentDocument.head.appendChild(link);
        }
        link.setAttribute("href", iconHref);
        link.setAttribute("sizes", "180x180");
        link.setAttribute("type", "image/png");
    }

    upsertIconLink("apple-touch-icon");
    upsertIconLink("icon");
    </script>
    """,
    height=0,
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


def get_supabase_client():
    if create_client is None:
        st.error("Supabase is not installed yet.")
        st.info("Install the app requirements again with: pip install -r requirements.txt")
        st.stop()

    try:
        supabase_url = str(st.secrets["SUPABASE_URL"]).strip()
        supabase_key = str(st.secrets["SUPABASE_KEY"]).strip()
    except KeyError as error:
        missing_name = str(error).strip("'\"")
        st.error(f"Supabase is missing {missing_name} in Streamlit secrets.")
        st.info("Add SUPABASE_URL and SUPABASE_KEY to .streamlit/secrets.toml, then restart the app.")
        st.stop()

    if not supabase_url or not supabase_key:
        st.error("Supabase is not connected yet.")
        st.info("Add SUPABASE_URL and SUPABASE_KEY to your Streamlit secrets, then restart the app.")
        st.stop()

    if supabase_key.startswith("sb_publishable_"):
        st.error("This app needs the legacy anon public key, not the new publishable key.")
        st.info(
            "In Supabase, go to Settings -> API -> Legacy anon, service_role API keys, "
            "then copy the anon public key into SUPABASE_KEY. Do not use the service_role key."
        )
        st.stop()

    if not supabase_key.startswith("eyJ"):
        st.error("SUPABASE_KEY does not look like a legacy anon public key.")
        st.info(
            "Use the key that starts with eyJ from Supabase -> Settings -> API -> "
            "Legacy anon, service_role API keys -> anon public. Do not use service_role."
        )
        st.stop()

    try:
        client = create_client(supabase_url, supabase_key)
        client.table("cash_flow_entries").select("id").limit(1).execute()
        return client
    except Exception as error:
        st.error("Supabase could not connect.")
        st.info("Please check SUPABASE_URL, the legacy anon public key, and that the cash_flow_entries table exists.")
        with st.expander("Technical details"):
            st.code(str(error))
        st.stop()


supabase = None


# Login section starts
def get_app_password():
    try:
        return str(st.secrets["APP_PASSWORD"])
    except KeyError:
        st.error("APP_PASSWORD is missing from Streamlit secrets.")
        st.info('Add APP_PASSWORD = "my-password-here" to your Streamlit Cloud secrets.')
        st.stop()


def show_login_screen():
    app_password = get_app_password()

    st.markdown(
        """
        <div class="top-header">
            <h1 class="app-title">Tati Finance</h1>
            <div class="app-subtitle">Enter your password to view your dashboard</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("password_login_form"):
        password = st.text_input("Password", type="password")
        login_clicked = st.form_submit_button("Login")

    if login_clicked:
        if password == app_password:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")


def logout_user():
    st.session_state["logged_in"] = False
# Login section ends


st.markdown("""
<style>

/* Force light theme for tables */
[data-testid="stDataFrame"] {
    background-color: white !important;
    color: #1e293b !important;
    border-radius: 12px;
    overflow: hidden;
}

/* Table header */
[data-testid="stDataFrame"] thead tr th {
    background-color: #2563eb !important;
    color: white !important;
    font-weight: 600;
    text-align: left;
}

/* Table rows */
[data-testid="stDataFrame"] tbody tr {
    background-color: #f8fafc !important;
    color: #1e293b !important;
}

/* Zebra effect */
[data-testid="stDataFrame"] tbody tr:nth-child(even) {
    background-color: #eef2ff !important;
}

/* Hover effect */
[data-testid="stDataFrame"] tbody tr:hover {
    background-color: #dbeafe !important;
}

/* Remove dark borders */
[data-testid="stDataFrame"] table {
    border: none !important;
}

/* Fix container padding */
.block-container {
    padding-top: 2rem;
}

</style>
""", unsafe_allow_html=True)

DB_NAME = "expenses.db"
DB_FILE = DB_NAME

SOURCES = [
    "Cash",
    "Bank",
    "Debit",
    "Zelle",
    "Venmo",
    "Citi",
    "Chase United",
    "Chase Freedom",
    "Apple Card",
    "Amazon Card",
    "Amex",
    "Macy's",
    "Pandora",
    "Sephora",
    "Klarna",
    "Affirm",
    "Afterpay",
    "Steven",
    "Other",
]

ENTRY_SOURCE_RADIO_OPTIONS = [
    "Cash",
    "Debit",
    "Zelle",
    "Venmo",
    "Citi",
    "Chase Freedom",
    "Apple Card",
    "Amazon Card",
    "Amex",
    "Other",
]

PLAN_PROVIDERS = ["Klarna", "Affirm", "Afterpay"]
PLAN_CATEGORIES = ["Clothes", "Beauty", "Amazon", "Home", "Other"]
PAYMENT_FREQUENCIES = ["Weekly", "Every 2 Weeks", "Monthly"]
SPENDING_CATEGORIES = [
    "Groceries",
    "Restaurants",
    "Amazon",
    "Beauty",
    "Clothes",
    "Internet",
    "Phone",
    "House",
    "Car",
    "Tyler",
    "Fish Tank",
    "Medical",
    "Travel",
    "Subscriptions",
    "Gifts",
    "Other",
]

SPENDING_CATEGORY_RADIO_OPTIONS = [
    "Groceries",
    "Restaurants",
    "Amazon",
    "Beauty",
    "Clothes",
    "Internet",
    "Phone",
    "House",
    "Car",
    "Other",
]

SPENDING_PAID_WITH_RADIO_OPTIONS = [
    "Cash",
    "Debit",
    "Zelle",
    "Venmo",
    "Citi",
    "Chase Freedom",
    "Apple Card",
    "Amazon Card",
    "Amex",
    "Other",
]

SPENDING_PAID_WITH = [
    "Cash",
    "Debit",
    "Zelle",
    "Venmo",
    "Citi",
    "Chase United",
    "Chase Freedom",
    "Apple Card",
    "Amazon Card",
    "Amex",
    "Macy's",
    "Pandora",
    "Sephora",
    "Klarna",
    "Affirm",
    "Afterpay",
    "Other",
]
CARD_SOURCES = [
    "Citi",
    "Chase United",
    "Chase Freedom",
    "Apple Card",
    "Amazon Card",
    "Amex",
    "Macy's",
    "Pandora",
    "Sephora",
    "Venmo",
    "Klarna",
    "Affirm",
    "Afterpay",
]

PAYMENT_PLAN_PROVIDERS = {"klarna", "affirm", "afterpay"}

MONEY_OUT_TYPES = {
    "money out",
    "expense",
    "credit card payment",
    "debit payment",
    "cash",
    "cash withdrawal",
    "zelle",
    "zelle payment",
    "venmo",
    "venmo payment",
    "steven payment",
    "savings added",
    "klarna",
    "affirm",
    "afterpay",
    "other money out",
}


def connect():
    return sqlite3.connect(DB_FILE)


def money(value):
    return f"${float(value or 0):,.2f}"


def parse_money(value):
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned:
        return 0.0
    return abs(float(cleaned))


def parse_whole_number(value, default=None):
    cleaned = str(value).replace(",", "").strip()
    if not cleaned:
        if default is None:
            raise ValueError("Missing number")
        return default
    number = float(cleaned)
    if number < 0 or not number.is_integer():
        raise ValueError("Whole number required")
    return int(number)


def current_month_value():
    return datetime.now().strftime("%Y-%m")


def normalize_month(value):
    text = str(value or "").strip()
    if not text:
        return current_month_value()

    for month_format in ("%Y-%m", "%B %Y", "%b %Y"):
        try:
            return datetime.strptime(text, month_format).strftime("%Y-%m")
        except ValueError:
            continue
    return text


def display_month(value):
    normalized = normalize_month(value)
    try:
        return datetime.strptime(normalized, "%Y-%m").strftime("%B %Y")
    except ValueError:
        return str(value or "")


def month_matches(series, month):
    normalized_month = normalize_month(month)
    return series.astype(str).apply(normalize_month) == normalized_month


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def ensure_column(conn, table_name, column_name, column_type):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def normalize_entry_type(entry_type):
    return "income" if str(entry_type).strip().lower() == "income" else "expense"


def is_income_type(entry_type):
    return str(entry_type).strip().lower() == "income"


def is_money_out_type(entry_type):
    return not is_income_type(entry_type)


def display_entry_type(entry_type):
    return "Income" if is_income_type(entry_type) else "Money Out"


def init_db():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cash_flow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                type TEXT NOT NULL,
                source TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                legacy_table TEXT,
                legacy_id INTEGER
            )
            """
        )
        ensure_column(conn, "cash_flow", "legacy_table", "TEXT")
        ensure_column(conn, "cash_flow", "legacy_id", "INTEGER")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_cash_flow_legacy ON cash_flow (legacy_table, legacy_id)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS steven_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                tax_quarterly REAL NOT NULL DEFAULT 0,
                tax_monthly_share REAL NOT NULL DEFAULT 0,
                mortgage_monthly REAL NOT NULL DEFAULT 0,
                mortgage_share REAL NOT NULL DEFAULT 0,
                health_insurance REAL NOT NULL DEFAULT 0,
                car_house_insurance REAL NOT NULL DEFAULT 0,
                house_cleaning REAL NOT NULL DEFAULT 0,
                other_deductions REAL NOT NULL DEFAULT 0,
                total_before_deductions REAL NOT NULL DEFAULT 0,
                total_deductions REAL NOT NULL DEFAULT 0,
                final_amount REAL NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        for column, column_type in {
            "tax_quarterly": "REAL NOT NULL DEFAULT 0",
            "tax_monthly_share": "REAL NOT NULL DEFAULT 0",
            "mortgage_monthly": "REAL NOT NULL DEFAULT 0",
            "mortgage_share": "REAL NOT NULL DEFAULT 0",
            "health_insurance": "REAL NOT NULL DEFAULT 0",
            "car_house_insurance": "REAL NOT NULL DEFAULT 0",
            "house_cleaning": "REAL NOT NULL DEFAULT 0",
            "other_deductions": "REAL NOT NULL DEFAULT 0",
            "total_before_deductions": "REAL NOT NULL DEFAULT 0",
            "total_deductions": "REAL NOT NULL DEFAULT 0",
            "final_amount": "REAL NOT NULL DEFAULT 0",
            "created_at": "TEXT NOT NULL DEFAULT ''",
        }.items():
            ensure_column(conn, "steven_calculations", column, column_type)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS savings_tracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                current_balance REAL NOT NULL,
                savings_goal REAL NOT NULL,
                added_this_month REAL NOT NULL,
                taken_this_month REAL NOT NULL,
                net_change REAL NOT NULL,
                remaining_to_goal REAL NOT NULL,
                progress REAL NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS spending_category_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                paid_with TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        ensure_column(conn, "spending_category_entries", "entry_date", "TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                purchase_category TEXT NOT NULL,
                original_amount REAL NOT NULL,
                payment_amount REAL NOT NULL,
                payment_frequency TEXT NOT NULL,
                total_payments INTEGER NOT NULL,
                payments_made INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        migrate_old_cash_flow(conn)


def migrate_old_cash_flow(conn):
    if table_exists(conn, "cash_flow_entries"):
        rows = conn.execute(
            """
            SELECT id, month, type, amount, source_account, notes, created_at
            FROM cash_flow_entries
            """
        ).fetchall()
        for row in rows:
            row_id, month, entry_type, amount, source, notes, created_at = row
            conn.execute(
                """
                INSERT OR IGNORE INTO cash_flow
                    (month, type, source, amount, notes, created_at, legacy_table, legacy_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    month,
                    normalize_entry_type(entry_type),
                    source or "Other",
                    abs(float(amount or 0)),
                    notes or "",
                    created_at or datetime.now().isoformat(),
                    "cash_flow_entries",
                    row_id,
                ),
            )

    if table_exists(conn, "transactions"):
        rows = conn.execute(
            """
            SELECT id, date, type, amount, payment_method, description
            FROM transactions
            """
        ).fetchall()
        for row in rows:
            row_id, txn_date, entry_type, amount, source, notes = row
            month = str(txn_date)[:7]
            conn.execute(
                """
                INSERT OR IGNORE INTO cash_flow
                    (month, type, source, amount, notes, created_at, legacy_table, legacy_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    month,
                    normalize_entry_type(entry_type),
                    source or "Other",
                    abs(float(amount or 0)),
                    notes or "",
                    datetime.now().isoformat(),
                    "transactions",
                    row_id,
                ),
            )


def load_cash_flow():
    response = (
        supabase
        .table("cash_flow")
        .select("id, month, type, source, amount, notes, created_at")
        .order("month", desc=True)
        .order("id", desc=True)
        .execute()
    )

    return pd.DataFrame(response.data or [])


def load_table_if_exists(table_name):
    with connect() as conn:
        if not table_exists(conn, table_name):
            return pd.DataFrame()
        return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


def load_spending_entries():
    with connect() as conn:
        if not table_exists(conn, "spending_category_entries"):
            return pd.DataFrame(
                columns=["id", "month", "category", "amount", "paid_with", "notes", "created_at"]
            )
        return pd.read_sql_query(
            """
            SELECT id, entry_date, month, category, amount, paid_with, notes, created_at
            FROM spending_category_entries
            ORDER BY month DESC, id DESC
            """,
            conn,
        )


def add_spending_entry(entry_date, month, category, amount, paid_with, notes):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO spending_category_entries
                (entry_date, month, category, amount, paid_with, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_date,
                month,
                category,
                abs(float(amount or 0)),
                paid_with,
                notes,
                datetime.now().isoformat(),
            ),
        )


def delete_spending_entry(entry_id):
    with connect() as conn:
        conn.execute("DELETE FROM spending_category_entries WHERE id = ?", (entry_id,))
        conn.commit()


def add_cash_flow(month, entry_type, source, amount, notes):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cash_flow (month, type, source, amount, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                month,
                normalize_entry_type(entry_type),
                source,
                abs(float(amount or 0)),
                notes,
                datetime.now().isoformat(),
            ),
        )


def delete_cash_flow(entry_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT legacy_table, legacy_id FROM cash_flow WHERE id = ?",
            (entry_id,),
        ).fetchone()
        conn.execute("DELETE FROM cash_flow WHERE id = ?", (entry_id,))
        if row:
            legacy_table, legacy_id = row
            if legacy_table == "cash_flow_entries" and legacy_id is not None:
                conn.execute("DELETE FROM cash_flow_entries WHERE id = ?", (legacy_id,))
            elif legacy_table == "transactions" and legacy_id is not None:
                conn.execute("DELETE FROM transactions WHERE id = ?", (legacy_id,))
        conn.commit()


def load_steven():
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM steven_calculations
            ORDER BY month DESC, id DESC
            """,
            conn,
        )


def steven_breakdown(tax_quarterly, mortgage_monthly, health, insurance, cleaning, other):
    tax_share = tax_quarterly / 3 / 2
    mortgage_share = mortgage_monthly / 2
    before_deductions = tax_share + mortgage_share
    deductions = health + insurance + cleaning + other
    final_amount = before_deductions - deductions
    return tax_share, mortgage_share, before_deductions, deductions, final_amount


def save_steven(month, tax_quarterly, mortgage_monthly, health, insurance, cleaning, other, notes):
    tax_share, mortgage_share, before_deductions, deductions, final_amount = steven_breakdown(
        tax_quarterly,
        mortgage_monthly,
        health,
        insurance,
        cleaning,
        other,
    )
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO steven_calculations
                (
                    month, tax_quarterly, tax_monthly_share, mortgage_monthly,
                    mortgage_share, health_insurance, car_house_insurance,
                    house_cleaning, other_deductions, total_before_deductions,
                    total_deductions, final_amount, notes, created_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                month,
                tax_quarterly,
                tax_share,
                mortgage_monthly,
                mortgage_share,
                health,
                insurance,
                cleaning,
                other,
                before_deductions,
                deductions,
                final_amount,
                notes,
                datetime.now().isoformat(),
            ),
        )


def delete_steven_calculation(calculation_id):
    with connect() as conn:
        conn.execute("DELETE FROM steven_calculations WHERE id = ?", (calculation_id,))
        conn.commit()


def build_steven_pdf(month, tax, mortgage, health, insurance, cleaning, other, notes):
    tax_share, mortgage_share, before_deductions, deductions, final_amount = steven_breakdown(
        tax,
        mortgage,
        health,
        insurance,
        cleaning,
        other,
    )
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    rows = [
        ["Month", month],
        ["Tax Quarterly", money(tax)],
        ["Tax Monthly Share", money(tax_share)],
        ["Mortgage Monthly", money(mortgage)],
        ["Mortgage Share", money(mortgage_share)],
        ["Health Insurance Deduction", f"-{money(health)}"],
        ["Car & House Insurance Deduction", f"-{money(insurance)}"],
        ["House Cleaning Deduction", f"-{money(cleaning)}"],
        ["Other Deductions", f"-{money(other)}"],
        ["Total Before Deductions", money(before_deductions)],
        ["Total Deductions", f"-{money(deductions)}"],
        ["Final Amount To Pay Steven", money(final_amount)],
        ["Notes", notes or ""],
    ]
    table = Table(rows, colWidths=[2.8 * inch, 3.6 * inch])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#222222")),
                ("PADDING", (0, 0), (-1, -1), 7),
                ("BACKGROUND", (0, 11), (-1, 11), colors.HexColor("#f8edf2")),
            ]
        )
    )
    doc.build([
        Paragraph("Steven Calculation", styles["Title"]),
        Spacer(1, 0.2 * inch),
        table,
    ])
    buffer.seek(0)
    return buffer.getvalue()


def latest_steven_for_month(records, month):
    if records.empty:
        return None
    rows = records[month_matches(records["month"], month)]
    if rows.empty:
        return None
    return rows.sort_values("id").iloc[-1]


def load_savings():
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM savings_tracker
            ORDER BY month DESC, id DESC
            """,
            conn,
        )


def save_savings(month, balance, goal, added, taken, notes):
    net = added - taken
    remaining = max(goal - balance, 0)
    progress = (balance / goal * 100) if goal > 0 else 0
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO savings_tracker
                (
                    month, current_balance, savings_goal, added_this_month,
                    taken_this_month, net_change, remaining_to_goal, progress,
                    notes, created_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                month,
                balance,
                goal,
                added,
                taken,
                net,
                remaining,
                min(progress, 100),
                notes,
                datetime.now().isoformat(),
            ),
        )


def delete_savings_record(record_id):
    with connect() as conn:
        conn.execute("DELETE FROM savings_tracker WHERE id = ?", (record_id,))
        conn.commit()


def latest_savings_for_month(records, month):
    if records.empty:
        return None
    rows = records[month_matches(records["month"], month)]
    if rows.empty:
        return records.sort_values("id").iloc[-1]
    return rows.sort_values("id").iloc[-1]


def load_payment_plans():
    with connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT *
            FROM payment_plans
            ORDER BY id DESC
            """,
            conn,
        )
    if not df.empty:
        df["start_date"] = pd.to_datetime(df["start_date"]).dt.date
    return df


def save_payment_plan(plan_name, provider, category, original, frequency, total, made, start_date, notes):
    payment_amount = original / total
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO payment_plans
                (
                    plan_name, provider, purchase_category, original_amount,
                    payment_amount, payment_frequency, total_payments,
                    payments_made, start_date, notes, created_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_name,
                provider,
                category,
                original,
                payment_amount,
                frequency,
                total,
                made,
                start_date.isoformat(),
                notes,
                datetime.now().isoformat(),
            ),
        )


def delete_payment_plan(plan_id):
    with connect() as conn:
        conn.execute("DELETE FROM payment_plans WHERE id = ?", (plan_id,))
        conn.commit()


def payment_plan_numbers(row):
    total = int(row["total_payments"])
    made = int(row["payments_made"])
    payment_amount = float(row["payment_amount"])
    if payment_amount <= 0 and total > 0:
        payment_amount = float(row["original_amount"]) / total
    remaining_payments = max(total - made, 0)
    return {
        "payment_amount": payment_amount,
        "remaining_payments": remaining_payments,
        "remaining_balance": payment_amount * remaining_payments,
        "total_paid": payment_amount * min(made, total),
    }


def add_months(day, months):
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    month_lengths = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                     31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(day.day, month_lengths[month - 1]))


def next_month_value(month):
    try:
        first_day = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
    except ValueError:
        first_day = datetime.now().date().replace(day=1)
    return add_months(first_day, 1).strftime("%Y-%m")


def payment_plan_schedule(row):
    values = row._asdict() if hasattr(row, "_asdict") else dict(row)
    total = int(values.get("total_payments", 0) or 0)
    made = int(values.get("payments_made", 0) or 0)
    if total <= 0:
        return []

    payment_amount = float(values.get("payment_amount", 0) or 0)
    if payment_amount <= 0:
        payment_amount = float(values.get("original_amount", 0) or 0) / total

    start_value = values.get("start_date")
    if isinstance(start_value, str):
        start_day = datetime.strptime(start_value[:10], "%Y-%m-%d").date()
    else:
        start_day = start_value

    frequency = str(values.get("payment_frequency", "") or "").lower()
    schedule = []
    for index in range(made, total):
        if "week" in frequency and "2" not in frequency and "every 2" not in frequency:
            due_date = start_day + timedelta(days=7 * index)
        elif "2" in frequency or "bi" in frequency:
            due_date = start_day + timedelta(days=14 * index)
        else:
            due_date = add_months(start_day, index)

        deduction_month = due_date.strftime("%Y-%m") if due_date.day <= 15 else next_month_value(due_date.strftime("%Y-%m"))
        schedule.append(
            {
                "plan_name": values.get("plan_name", ""),
                "provider": values.get("provider", ""),
                "due_date": due_date,
                "deduction_month": deduction_month,
                "payment_amount": payment_amount,
            }
        )
    return schedule


def payment_plan_details_for_month(plans, month):
    if plans is None or plans.empty:
        return pd.DataFrame(columns=["plan_name", "provider", "amount_due", "next_payment_date", "remaining_balance"])

    target_month = normalize_month(month)
    rows = []
    for plan in plans.itertuples(index=False):
        values = plan._asdict()
        numbers = payment_plan_numbers(values)
        schedule = payment_plan_schedule(values)
        month_payments = [item for item in schedule if item["deduction_month"] == target_month]
        if not month_payments:
            continue
        next_payment_date = min(item["due_date"] for item in schedule) if schedule else None
        rows.append(
            {
                "plan_name": values.get("plan_name", ""),
                "provider": values.get("provider", ""),
                "amount_due": sum(item["payment_amount"] for item in month_payments),
                "next_payment_date": next_payment_date.isoformat() if next_payment_date else "",
                "remaining_balance": numbers["remaining_balance"],
            }
        )
    return pd.DataFrame(rows)


def payment_plans_due_for_month(plans, month):
    details = payment_plan_details_for_month(plans, month)
    if details.empty:
        return 0.0
    return float(details["amount_due"].sum())


def active_payment_plan_providers(plans):
    if plans is None or plans.empty:
        return set()
    providers = set()
    for row in plans.itertuples(index=False):
        numbers = payment_plan_numbers(row._asdict())
        if numbers["remaining_payments"] > 0:
            provider = str(row.provider or "").strip().lower()
            if provider in PAYMENT_PLAN_PROVIDERS:
                providers.add(provider)
    return providers


def remove_saved_payment_plan_sources(rows, plans):
    providers = active_payment_plan_providers(plans)
    if rows.empty or not providers:
        return rows
    return rows[~rows["source"].astype(str).str.strip().str.lower().isin(providers)].copy()


def month_options(cash_flow, steven, savings):
    current_month = current_month_value()
    months = {current_month}
    for table in (cash_flow, steven, savings, load_spending_entries()):
        if table is not None and not table.empty and "month" in table.columns:
            months.update(table["month"].dropna().astype(str).tolist())
    return sorted(months, reverse=True)


def monthly_summary(cash_flow, steven, savings, month, plans=None):
    rows = cash_flow[month_matches(cash_flow["month"], month)] if not cash_flow.empty else cash_flow
    rows = remove_saved_payment_plan_sources(rows, plans)
    if rows.empty:
        income = 0.0
        cash_flow_money_out = 0.0
    else:
        income_mask = rows["type"].apply(is_income_type)
        money_out_mask = rows["type"].apply(is_money_out_type)
        income = float(rows.loc[income_mask, "amount"].abs().sum())
        cash_flow_money_out = float(rows.loc[money_out_mask, "amount"].abs().sum())

    savings_row = latest_savings_for_month(savings, month)
    steven_row = latest_steven_for_month(steven, month)
    savings_balance = float(savings_row["current_balance"]) if savings_row is not None else 0.0
    savings_added = float(savings_row["added_this_month"]) if savings_row is not None else 0.0
    savings_taken = float(savings_row["taken_this_month"]) if savings_row is not None else 0.0
    steven_amount = float(steven_row["final_amount"]) if steven_row is not None else 0.0
    savings_already_in_cash_flow = False
    steven_already_in_cash_flow = False
    if not rows.empty:
        savings_already_in_cash_flow = rows["type"].astype(str).str.lower().str.contains("savings").any() or rows[
            "source"
        ].astype(str).str.lower().str.contains("savings").any()
        steven_already_in_cash_flow = rows["type"].astype(str).str.lower().str.contains("steven").any() or rows[
            "source"
        ].astype(str).str.lower().str.contains("steven").any()
    savings_money_out = 0.0 if savings_already_in_cash_flow else savings_added
    steven_money_out = 0.0 if steven_already_in_cash_flow else steven_amount
    payment_plans_due = payment_plans_due_for_month(plans, month)
    payment_plans_next_month = payment_plans_due_for_month(plans, next_month_value(month))
    money_out = cash_flow_money_out + savings_money_out + steven_money_out + payment_plans_due
    return {
        "income": income,
        "money_out": money_out,
        "bills_card_payments": cash_flow_money_out,
        "steven_money_out": steven_money_out,
        "savings_money_out": savings_money_out,
        "payment_plans_due": payment_plans_due,
        "payment_plans_next_month": payment_plans_next_month,
        "cash_left": income - money_out,
        "savings_balance": savings_balance,
        "savings_added": savings_added,
        "savings_taken": savings_taken,
        "steven_amount": steven_amount,
    }


def money_out_by_source(cash_flow, month, plans=None):
    if cash_flow.empty:
        return pd.DataFrame(columns=["source", "amount"])
    rows = cash_flow[month_matches(cash_flow["month"], month) & (cash_flow["type"].apply(is_money_out_type))].copy()
    rows = remove_saved_payment_plan_sources(rows, plans)
    if rows.empty:
        return pd.DataFrame(columns=["source", "amount"])
    rows["amount"] = rows["amount"].abs()
    return rows.groupby("source", as_index=False)["amount"].sum().sort_values("amount", ascending=False)


def spending_by_category(spending_entries, month):
    if spending_entries.empty:
        return pd.DataFrame(columns=["category", "amount"])
    rows = spending_entries[month_matches(spending_entries["month"], month)].copy()
    if rows.empty:
        return pd.DataFrame(columns=["category", "amount"])
    rows["amount"] = rows["amount"].abs()
    return rows.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)


def card_payments_by_source(cash_flow, month, plans=None):
    if cash_flow.empty:
        return pd.DataFrame(columns=["source", "amount"])
    rows = cash_flow[
        month_matches(cash_flow["month"], month)
        & (cash_flow["type"].apply(is_money_out_type))
        & (cash_flow["source"].isin(CARD_SOURCES))
    ].copy()
    rows = remove_saved_payment_plan_sources(rows, plans)
    if rows.empty:
        return pd.DataFrame(columns=["source", "amount"])
    rows["amount"] = rows["amount"].abs()
    return rows.groupby("source", as_index=False)["amount"].sum().sort_values("amount", ascending=False)


def apply_styles():
    st.markdown(
        """
        <style>
        .stApp {
            background: #f7f9fc;
            color: #1e293b;
        }

        .block-container {
            max-width: 950px;
            padding-top: 1.2rem;
            padding-bottom: 1.5rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        div[data-testid="column"],
        div[data-testid="stHorizontalBlock"],
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border-left: 0 !important;
            border-right: 0 !important;
            border-color: transparent !important;
            outline: none !important;
        }

        hr,
        [data-testid="stMarkdownContainer"] hr {
            width: 100% !important;
            height: 1px !important;
            margin: 24px 0 !important;
            border: 0 !important;
            background: #E5E7EB !important;
        }

        div[data-testid="stForm"] {
            border: 0 !important;
            padding: 0 !important;
        }

        div[data-testid="stForm"] div[data-testid="stVerticalBlock"] {
            gap: 16px !important;
        }

        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            gap: 24px !important;
            align-items: stretch !important;
        }

        div[data-testid="stFormSubmitButton"] {
            margin-top: 20px !important;
            margin-bottom: 24px !important;
            text-align: left !important;
        }

        .top-header {
            padding: 0 0 0.45rem;
            text-align: center;
        }

        .app-title {
            text-align: center;
            font-size: 2rem;
            font-weight: 750;
            margin: 0 0 0.15rem;
            color: #1e293b;
            line-height: 1.15;
        }

        .app-subtitle {
            text-align: center;
            color: #64748b;
            font-size: 0.92rem;
            margin: 0;
        }

        div[data-testid="stTabs"] {
            margin-top: 0.25rem;
            overflow-x: auto !important;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            gap: 0.15rem;
            padding: 0 0 0.2rem;
            overflow-x: auto !important;
        }

        div[data-testid="stTabs"] button[role="tab"] {
            background: transparent !important;
            color: #1e293b !important;
            min-height: 34px !important;
            border-radius: 0 !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            padding: 6px 8px !important;
            white-space: nowrap !important;
            border: 0 !important;
            border-bottom: 2px solid transparent !important;
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: #dbeafe !important;
            border-bottom: 2px solid #2563eb !important;
            color: #1e293b !important;
        }

        h1 {
            font-size: 2rem !important;
            font-weight: 750 !important;
            margin-bottom: 0.25rem !important;
            color: #1e293b !important;
        }

        h2 {
            font-size: 1.45rem !important;
            margin-top: 0.8rem !important;
            color: #1e293b !important;
        }

        h3 {
            font-size: 1.05rem !important;
            color: #1e293b !important;
        }

        div[data-testid="stHeadingWithActionElements"] {
            margin-top: 24px !important;
            padding-top: 20px !important;
            border-top: 1px solid #E5E7EB !important;
        }

        p, label {
            font-size: 0.94rem;
            color: #1e293b !important;
        }

        .metric-card {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 18px;
            padding: 0.9rem 1rem;
            min-height: 98px;
            margin-bottom: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        }

        .cash-card {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            margin-bottom: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        }

        .metric-label {
            color: #64748b;
            font-size: 0.7rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.035rem;
            line-height: 1.25;
        }

        .metric-value {
            color: #1e293b;
            font-size: 1.48rem;
            font-weight: 850;
            margin-top: 0.34rem;
            white-space: nowrap;
            line-height: 1.15;
        }

        .cash-value {
            color: #1e293b;
            font-size: 2.35rem;
            font-weight: 850;
            line-height: 1.05;
            margin-top: 0.32rem;
            white-space: nowrap;
        }

        .metric-sub {
            color: #64748b;
            margin-top: 0.28rem;
            font-size: 0.8rem;
            line-height: 1.3;
        }

        .panel {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 18px;
            padding: 1rem;
            margin: 32px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        }

        .section-title {
            color: #1e293b;
            font-size: 1.2rem;
            font-weight: 800;
            margin: 24px 0 16px;
        }

        input, textarea {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 10px !important;
            color: #1F2937 !important;
            min-height: 44px !important;
            box-shadow: none !important;
            font-size: 14px !important;
            width: 100% !important;
            outline: none !important;
        }

        input, textarea {
            color: #1F2937 !important;
            background-color: #ffffff !important;
            padding: 10px 14px !important;
            font-size: 14px !important;
            line-height: 1.35 !important;
        }

        input:focus, textarea:focus,
        input:focus-visible, textarea:focus-visible {
            outline: none !important;
            border: 1px solid #2563eb !important;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12) !important;
            background-color: #ffffff !important;
        }

        div[role="radiogroup"] {
            flex-wrap: wrap !important;
            align-items: center !important;
        }

        div[role="radiogroup"] label,
        div[role="radiogroup"] label * {
            color: #1e293b !important;
            font-size: 14px !important;
        }

        button[data-testid="baseButton-secondary"] {
            background-color: #dc2626 !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 6px 12px !important;
            width: auto !important;
            min-height: 32px !important;
            font-size: 13px !important;
        }

        .stButton > button,
        .stFormSubmitButton > button,
        .stDownloadButton > button {
            background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 10px 20px !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.25) !important;
        }

        .stButton > button *,
        .stFormSubmitButton > button *,
        .stDownloadButton > button * {
            color: #ffffff !important;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #1D4ED8, #1E40AF) !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: 0 6px 14px rgba(37, 99, 235, 0.32) !important;
        }

        button[data-testid="baseButton-secondary"] *,
        button[data-testid="baseButton-primary"] * {
            color: #ffffff !important;
        }

        .stButton > button:active,
        .stFormSubmitButton > button:active,
        .stDownloadButton > button:active {
            transform: scale(0.98);
        }

        .entry-row {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 14px;
            padding: 0.7rem 0.85rem;
            margin-bottom: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            line-height: 1.35;
            color: #1e293b;
        }

        [data-testid="stDataFrame"] {
            background-color: white !important;
            color: #1e293b !important;
            border-radius: 12px;
            overflow: hidden;
        }

        [data-testid="stDataFrame"] thead tr th {
            background-color: #2563eb !important;
            color: white !important;
            font-weight: 600;
            text-align: left;
        }

        [data-testid="stDataFrame"] td,
        [data-testid="stDataFrame"] th {
            color: #1e293b !important;
            border-color: #dbeafe !important;
        }

        [data-testid="stDataFrame"] tbody tr {
            background-color: #f8fafc !important;
            color: #1e293b !important;
        }

        [data-testid="stDataFrame"] tbody tr:nth-child(even) {
            background-color: #eef2ff !important;
        }

        [data-testid="stDataFrame"] tbody tr:hover {
            background-color: #dbeafe !important;
        }

        [data-testid="stDataFrame"] table {
            border: none !important;
        }

        [data-testid="stDataFrame"] * {
            background-color: transparent !important;
        }

        @media (max-width: 640px) {
            .block-container {
                padding: 0.85rem 0.8rem 1.4rem;
            }

            .app-title {
                font-size: 1.65rem;
            }

            .cash-value {
                font-size: 1.85rem;
            }

            .metric-value {
                font-size: 1.2rem;
            }

            .stButton > button,
            .stFormSubmitButton > button,
            .stDownloadButton > button {
                width: 100%;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, subtext):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cash_left_card(value, month):
    st.markdown(
        f"""
        <div class="cash-card">
            <div class="metric-label">Cash Left</div>
            <div class="cash-value">{value}</div>
            <div class="metric-sub">{display_month(month)} snapshot</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_value(value):
    if pd.isna(value):
        return ""
    return str(value)


def render_info_card(items):
    lines = []
    for label, value in items:
        lines.append(f"<strong>{label}:</strong> {card_value(value)}")
    st.markdown(
        f"""
        <div class="entry-row">
            {"<br>".join(lines)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def confirm_delete(delete_key, label="Delete"):
    confirming_key = f"confirming_{delete_key}"
    if st.session_state.get(confirming_key):
        st.warning("Are you sure you want to delete this?")
        yes_col, cancel_col = st.columns(2)
        with yes_col:
            if st.button("Yes, delete", key=f"{delete_key}_yes"):
                st.session_state[confirming_key] = False
                return True
        with cancel_col:
            if st.button("Cancel", key=f"{delete_key}_cancel"):
                st.session_state[confirming_key] = False
                st.rerun()
        return False

    if st.button(label, key=f"{delete_key}_start"):
        st.session_state[confirming_key] = True
        st.rerun()
    return False


def show_pie_chart(cash_flow, month, plans=None):
    data = money_out_by_source(cash_flow, month, plans)
    if data.empty:
        st.info("No spending data yet.")
        return

    if px is None:
        st.info("Install Plotly to see the pie chart: pip install plotly")
        return

    fig = px.pie(
        data,
        names="source",
        values="amount",
        title="Where Your Money Went This Month",
        hole=0.4,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#252326"},
    )
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{month}_money_out")


def show_spending_category_pie(spending_entries, month, chart_key):
    st.subheader("Spending Categories")
    data = spending_by_category(spending_entries, month)
    if data.empty:
        st.info("No spending category data yet.")
        return

    if px is None:
        st.info("Install Plotly to see category pie chart: pip install plotly")
        return

    fig = px.pie(
        data,
        names="category",
        values="amount",
        title="Spending Categories",
        hole=0.4,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#252326"},
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


def show_dashboard(cash_flow, steven, savings, spending_entries, plans):
    st.markdown('<div class="section-title">📊 Dashboard</div>', unsafe_allow_html=True)
    current_month = current_month_value()
    selected_month = st.text_input(
        "Month",
        value=current_month,
        placeholder="YYYY-MM or May 2026",
        help="Format: YYYY-MM or Month YYYY",
        key="dashboard_month",
    )
    selected_month = normalize_month(selected_month)
    summary = monthly_summary(cash_flow, steven, savings, selected_month, plans)

    cash_left_card(money(summary["cash_left"]), selected_month)

    c1, c2 = st.columns(2)
    with c1:
        metric_card("💵 Income", money(summary["income"]), "Money in")
    with c2:
        metric_card("💳 Bills / Card Payments", money(summary["bills_card_payments"]), "Cash flow money out")

    c3, c4 = st.columns(2)
    with c3:
        metric_card("🏠 House / Steven", money(summary["steven_money_out"]), "House share / Steven amount")
    with c4:
        metric_card("💰 Savings Added", money(summary["savings_money_out"]), "Reduces cash left")

    c5, c6 = st.columns(2)
    with c5:
        metric_card("📆 Payment Plans Due This Month", money(summary["payment_plans_due"]), selected_month)
    with c6:
        metric_card("📆 Payment Plans Next Month", money(summary["payment_plans_next_month"]), next_month_value(selected_month))

    metric_card("✅ Cash Left", money(summary["cash_left"]), "Income minus bills, Steven, savings added, and payment plans")
    st.caption(
        f"{money(summary['income'])} - {money(summary['bills_card_payments'])} - "
        f"{money(summary['steven_money_out'])} - {money(summary['savings_money_out'])} - "
        f"{money(summary['payment_plans_due'])} = "
        f"{money(summary['cash_left'])}"
    )

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    show_pie_chart(cash_flow, selected_month, plans)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    show_spending_category_pie(
        spending_entries,
        selected_month,
        chart_key=f"chart_{selected_month}_dashboard_spending_categories",
    )
    st.caption("Informational only. This does not affect Cash Left.")
    st.markdown("</div>", unsafe_allow_html=True)


def show_add_entry():
    st.markdown('<div class="section-title">➕ Add Entry</div>', unsafe_allow_html=True)
    st.caption("One simple place for daily money movement. Income adds money. Expense is money out.")
    current_month = current_month_value()
    with st.form("simple_cash_flow_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            month = st.text_input("Month", value=current_month, placeholder="YYYY-MM or May 2026")
            entry_type = st.radio("Type", ["Income", "Money Out"], horizontal=True)
            source = st.radio("Source", ENTRY_SOURCE_RADIO_OPTIONS, horizontal=True)
            submitted = st.form_submit_button("Save Entry")
        with c2:
            amount_text = st.text_input("Amount", value="", placeholder="0.00")
            notes = st.text_area("Notes", placeholder="Optional notes")

    if submitted:
        try:
            amount = parse_money(amount_text)
        except ValueError:
            amount = 0.0

        if not month.strip():
            st.error("Please enter a month.")
        elif amount <= 0:
            st.error("Please enter an amount greater than 0.")
        else:
            add_cash_flow(normalize_month(month), entry_type, source.strip() or "Other", amount, notes.strip())
            st.success("Entry saved.")
            st.rerun()


def show_recent_entries(cash_flow):
    st.subheader("Recent Entries")
    if cash_flow.empty:
        st.info("No entries yet.")
        return

    for row in cash_flow.head(25).itertuples(index=False):
        sign = "" if row.type == "income" else "-"
        st.markdown(
            f"""
            <div class="entry-row">
                <strong>{row.month}</strong> | {display_entry_type(row.type)} | {row.source}
                | <strong>{sign}{money(row.amount)}</strong><br>
                <span>{row.notes or "No notes"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if confirm_delete(f"delete_cash_{row.id}"):
            delete_cash_flow(row.id)
            load_cash_flow()
            st.success("Entry deleted.")
            st.rerun()


def show_steven_calculator():
    st.markdown('<div class="section-title">🏠 House / Steven</div>', unsafe_allow_html=True)
    current_month = current_month_value()
    month = st.text_input("Month", value=current_month, placeholder="YYYY-MM or May 2026", key="steven_month")
    c1, c2 = st.columns(2)
    with c1:
        tax_text = st.text_input("Tax Quarterly", placeholder="0.00")
        health_text = st.text_input("Health Insurance Deduction", placeholder="0.00")
        cleaning_text = st.text_input("House Cleaning Deduction", placeholder="0.00")
    with c2:
        mortgage_text = st.text_input("Mortgage Monthly", placeholder="0.00")
        insurance_text = st.text_input("Car & House Insurance Deduction", placeholder="0.00")
        other_text = st.text_input("Other Deductions", placeholder="0.00")
    notes = st.text_area("Notes", placeholder="Optional notes", key="steven_notes")

    try:
        tax = parse_money(tax_text)
        mortgage = parse_money(mortgage_text)
        health = parse_money(health_text)
        insurance = parse_money(insurance_text)
        cleaning = parse_money(cleaning_text)
        other = parse_money(other_text)
    except ValueError:
        tax = mortgage = health = insurance = cleaning = other = 0.0

    tax_share, mortgage_share, before_deductions, deductions, final_amount = steven_breakdown(
        tax,
        mortgage,
        health,
        insurance,
        cleaning,
        other,
    )
    metric_card(
        "Final Amount To Pay Steven",
        money(final_amount),
        f"Tax share: {money(tax_share)} | Mortgage share: {money(mortgage_share)}",
    )
    st.markdown(
        f"""
        <div class="entry-row">
            Tax Monthly Share: <strong>{money(tax_share)}</strong><br>
            Mortgage Share: <strong>{money(mortgage_share)}</strong><br>
            Total Before Deductions: <strong>{money(before_deductions)}</strong><br>
            Total Deductions: <strong>-{money(deductions)}</strong><br>
            Final Amount To Pay Steven: <strong>{money(final_amount)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Amount Already Deducted", money(deductions), "Health, insurance, cleaning, other")
    with c2:
        metric_card("Remaining To Pay", money(final_amount), "After deductions")
    with c3:
        metric_card("Before Deductions", money(before_deductions), "Tax share plus mortgage share")

    save_clicked = st.button("Save Steven Calculation", use_container_width=True)

    if save_clicked:
        save_steven(normalize_month(month), tax, mortgage, health, insurance, cleaning, other, notes.strip())
        st.success("Steven calculation saved.")
        st.rerun()

    records = load_steven()
    if not records.empty:
        st.subheader("Saved Steven Calculations")
        for row in records.itertuples(index=False):
            created = getattr(row, "created_at", "") or ""
            st.markdown(
                f"""
                <div class="entry-row">
                    <strong>Month:</strong> {display_month(row.month)}<br>
                    <strong>Final Amount:</strong> {money(row.final_amount)}<br>
                    <strong>Notes:</strong> {row.notes or "No notes"}<br>
                    <strong>Created:</strong> {created or "Not available"}
                </div>
                """,
                unsafe_allow_html=True,
            )
            if confirm_delete(f"delete_steven_{row.id}", "Delete Steven Calculation"):
                delete_steven_calculation(row.id)
                st.success("Steven calculation deleted.")
                st.rerun()

        st.subheader("Print Saved Steven Calculation")
        print_options = records.sort_values(["month", "id"], ascending=[False, False])
        current_month = current_month_value()
        print_month = st.text_input("Steven Report Month", value=current_month, placeholder="YYYY-MM or May 2026", key="saved_steven_print_month")
        print_month = normalize_month(print_month)
        matching_print_options = print_options[print_options["month"].astype(str) == print_month]
        if matching_print_options.empty:
            st.info("No saved Steven calculation found for that month.")
        else:
            selected = matching_print_options.iloc[0]
            saved_pdf = build_steven_pdf(
                str(selected["month"]),
                float(selected.get("tax_quarterly", 0) or 0),
                float(selected.get("mortgage_monthly", 0) or 0),
                float(selected.get("health_insurance", 0) or 0),
                float(selected.get("car_house_insurance", 0) or 0),
                float(selected.get("house_cleaning", 0) or 0),
                float(selected.get("other_deductions", 0) or 0),
                str(selected.get("notes", "") or ""),
            )
            if saved_pdf is None:
                st.info("Install reportlab to print saved Steven calculations: pip install reportlab")
            else:
                st.download_button(
                    "Print Steven Report",
                    data=saved_pdf,
                    file_name=f"steven-calculation-{selected['month']}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"steven_saved_report_download_{selected['id']}",
                )


def show_savings():
    st.markdown('<div class="section-title">💰 Savings</div>', unsafe_allow_html=True)
    records = load_savings()
    current_month = current_month_value()
    saved = latest_savings_for_month(records, current_month)
    saved_balance = float(saved["current_balance"]) if saved is not None else 0.0
    saved_goal = float(saved["savings_goal"]) if saved is not None else 0.0
    saved_added = float(saved["added_this_month"]) if saved is not None else 0.0
    saved_taken = float(saved["taken_this_month"]) if saved is not None else 0.0
    saved_progress = (saved_balance / saved_goal * 100) if saved_goal > 0 else 0
    saved_remaining = max(saved_goal - saved_balance, 0)

    metric_card(
        "Savings Balance",
        money(saved_balance),
        f"Goal: {money(saved_goal)} | Added this month: {money(saved_added)}",
    )
    if saved_goal > 0:
        st.progress(min(saved_progress, 100) / 100)
        st.caption(f"{saved_progress:.1f}% complete | {money(saved_remaining)} remaining")

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    month = st.text_input("Month", value=current_month, placeholder="YYYY-MM or May 2026", key="savings_month")
    c1, c2 = st.columns(2)
    with c1:
        balance_text = st.text_input("Current savings balance", value=f"{saved_balance:.2f}", placeholder="0.00")
        added_text = st.text_input("Amount added this month", value=f"{saved_added:.2f}", placeholder="0.00")
    with c2:
        goal_text = st.text_input("Savings goal", value=f"{saved_goal:.2f}", placeholder="0.00")
        taken_text = st.text_input("Amount taken this month", value=f"{saved_taken:.2f}", placeholder="0.00")
    notes = st.text_area("Notes", placeholder="Optional notes", key="savings_notes")

    try:
        balance = parse_money(balance_text)
        goal = parse_money(goal_text)
        added = parse_money(added_text)
        taken = parse_money(taken_text)
    except ValueError:
        balance = goal = added = taken = 0.0

    if st.button("Save Savings", use_container_width=True):
        save_savings(normalize_month(month), balance, goal, added, taken, notes.strip())
        st.success("Savings saved.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if not records.empty:
        st.subheader("Savings History")
        for row in records.itertuples(index=False):
            render_info_card(
                [
                    ("Month", display_month(row.month)),
                    ("Balance", money(row.current_balance)),
                    ("Goal", money(row.savings_goal)),
                    ("Added", money(row.added_this_month)),
                    ("Taken", money(row.taken_this_month)),
                    ("Notes", row.notes or "No notes"),
                ]
            )
            if confirm_delete(f"delete_savings_record_{row.id}", "Delete Savings Record"):
                delete_savings_record(row.id)
                st.success("Savings record deleted.")
                st.rerun()

def show_spending(spending_entries):
    st.markdown('<div class="section-title">🧾 Spending Categories</div>', unsafe_allow_html=True)
    st.caption("Informational only — does not affect cash left.")
    current_month = current_month_value()
    with st.form("spending_entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            entry_date = st.date_input("Date", value=date.today())
            month = st.text_input("Month", value=current_month, placeholder="YYYY-MM or May 2026")
            category = st.radio("Category", SPENDING_CATEGORY_RADIO_OPTIONS, horizontal=True)
        with c2:
            paid_with = st.radio("Paid With", SPENDING_PAID_WITH_RADIO_OPTIONS, horizontal=True)
            amount_text = st.text_input("Amount", value="", placeholder="0.00")
            notes = st.text_area("Notes", placeholder="Optional notes")
        submitted = st.form_submit_button("Save Spending Category")

    if submitted:
        try:
            amount = parse_money(amount_text)
        except ValueError:
            amount = 0.0

        if not month.strip():
            st.error("Please enter a month.")
        elif amount <= 0:
            st.error("Please enter an amount greater than 0.")
        else:
            add_spending_entry(entry_date.strftime("%Y-%m-%d"), normalize_month(month), category, amount, paid_with, notes.strip())
            st.success("Spending category saved.")
            st.rerun()

    selected_month = st.text_input("Spending Month", value=current_month, placeholder="YYYY-MM or May 2026", key="spending_month")
    selected_month = normalize_month(selected_month)
    summary = spending_by_category(spending_entries, selected_month)
    if summary.empty:
        st.info("No spending category entries for this month.")
    else:
        show_spending_category_pie(
            spending_entries,
            selected_month,
            chart_key=f"chart_{selected_month}_spending_categories_tab",
        )
        st.subheader("Spending Category Summary")
        for row in summary.itertuples(index=False):
            st.markdown(
                f"""
                <div class="entry-row">
                    <strong>{row.category}</strong> — <strong>{money(row.amount)}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.subheader("Spending History")
    if spending_entries.empty:
        st.info("No spending entries yet.")
        return

    for row in spending_entries.head(30).itertuples(index=False):
        st.markdown(
            f"""
            <div class="entry-row">
                <strong>{row.month}</strong> | {row.category} | {row.paid_with}
                | <strong>{money(row.amount)}</strong><br>
                <span>{row.notes or "No notes"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if confirm_delete(f"delete_spending_{row.id}", "Delete Spending Entry"):
            delete_spending_entry(row.id)
            st.success("Spending entry deleted.")
            st.rerun()


def show_cards(cash_flow, plans):
    st.markdown('<div class="section-title">💳 Cards</div>', unsafe_allow_html=True)
    st.caption("Credit card and payment-plan payments from real cash flow.")
    current_month = current_month_value()
    selected_month = st.text_input("Cards Month", value=current_month, placeholder="YYYY-MM or May 2026", key="cards_month")
    selected_month = normalize_month(selected_month)
    card_summary = card_payments_by_source(cash_flow, selected_month, plans)
    total_cards = float(card_summary["amount"].sum()) if not card_summary.empty else 0.0
    metric_card("Credit Card Payments", money(total_cards), selected_month)

    if card_summary.empty:
        st.info("No card payments saved for this month.")
        return

    for row in card_summary.itertuples(index=False):
        st.markdown(
            f"""
            <div class="entry-row">
                <strong>{row.source}</strong> | <strong>{money(row.amount)}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )


def show_payment_plans():
    st.markdown('<div class="section-title">📆 Plans</div>', unsafe_allow_html=True)
    with st.form("payment_plan_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            plan_name = st.text_input("Payment name", placeholder="Dress, Amazon computer, Sephora order, Shoes")
            provider = st.radio("Provider", PLAN_PROVIDERS, horizontal=True)
            category = st.radio("Purchase category", PLAN_CATEGORIES, horizontal=True)
            original_text = st.text_input("Original purchase amount", placeholder="0.00")
        with c2:
            frequency = st.radio("Payment frequency", PAYMENT_FREQUENCIES, horizontal=True)
            total_text = st.text_input("Total number of payments", placeholder="4")
            made_text = st.text_input("Payments already made", placeholder="0")
            start_date = st.date_input("Start date", value=date.today())
        notes = st.text_area("Notes", placeholder="Optional notes", key="plan_notes")
        save_plan = st.form_submit_button("Save Payment Plan")

    try:
        original = parse_money(original_text)
        total = parse_whole_number(total_text)
        made = parse_whole_number(made_text, default=0)
        payment_amount = original / total if total > 0 else 0.0
    except ValueError:
        original = payment_amount = 0.0
        total = 0
        made = -1

    remaining_payments = max(total - max(made, 0), 0)
    remaining_balance = payment_amount * remaining_payments
    total_paid = payment_amount * min(max(made, 0), total)
    metric_card("Payment Plan Preview", money(remaining_balance), f"Payment: {money(payment_amount)} | Paid: {money(total_paid)} | Remaining payments: {remaining_payments}")

    if save_plan:
        if not plan_name.strip():
            st.error("Please enter a payment name.")
        elif original <= 0:
            st.error("Original purchase amount must be greater than 0.")
        elif total <= 0:
            st.error("Total number of payments must be greater than 0.")
        elif made < 0:
            st.error("Payments already made must be 0 or more.")
        elif made > total:
            st.error("Payments already made cannot be more than total payments.")
        else:
            save_payment_plan(plan_name.strip(), provider, category, original, frequency, total, made, start_date, notes.strip())
            st.success("Payment plan saved.")
            st.rerun()

    plans = load_payment_plans()
    if plans.empty:
        st.info("No payment plans yet.")
        return

    st.subheader("Active Payment Plans")
    for row in plans.itertuples(index=False):
        numbers = payment_plan_numbers(row._asdict())
        if numbers["remaining_payments"] <= 0:
            continue
        st.markdown(
            f"""
            <div class="entry-row">
                <strong>{row.plan_name}</strong> | {row.provider} | {row.purchase_category}<br>
                Payment: {money(numbers["payment_amount"])} | Remaining: {money(numbers["remaining_balance"])}
                | Remaining payments: {numbers["remaining_payments"]}<br>
                <span>{row.notes or "No notes"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if confirm_delete(f"delete_plan_{row.id}", "Delete Plan"):
            delete_payment_plan(row.id)
            st.success("Payment plan deleted.")
            st.rerun()


def build_monthly_pdf(cash_flow, spending_entries, steven, savings, plans, month):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return None

    summary = monthly_summary(cash_flow, steven, savings, month, plans)
    month_rows = cash_flow[month_matches(cash_flow["month"], month)].copy() if not cash_flow.empty else cash_flow
    month_rows = remove_saved_payment_plan_sources(month_rows, plans)
    source_rows = money_out_by_source(cash_flow, month, plans)
    spending_rows = spending_by_category(spending_entries, month)
    steven_row = latest_steven_for_month(steven, month)
    savings_row = latest_savings_for_month(savings, month)
    plan_due_rows = payment_plan_details_for_month(plans, month)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.55 * inch, bottomMargin=0.55 * inch)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Tati Finance Monthly Report", styles["Title"]),
        Paragraph(f"Month: {display_month(month)}", styles["BodyText"]),
        Spacer(1, 0.2 * inch),
    ]

    summary_table = Table(
        [
            ["Income", "Money Out", "Cash Left", "Savings", "Steven", "Payment Plans"],
            [
                money(summary["income"]),
                money(summary["money_out"]),
                money(summary["cash_left"]),
                money(summary["savings_balance"]),
                money(summary["steven_amount"]),
                money(summary["payment_plans_due"]),
            ],
        ],
        colWidths=[1.05 * inch] * 6,
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8edf2")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 0.22 * inch)])

    story.append(Paragraph("Money Out by Source", styles["Heading2"]))
    if source_rows.empty:
        story.append(Paragraph("No money-out entries for this month.", styles["BodyText"]))
    else:
        table = Table(
            [["Source", "Amount"]] + [[row.source, money(row.amount)] for row in source_rows.itertuples(index=False)],
            colWidths=[3.2 * inch, 2.4 * inch],
        )
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")), ("PADDING", (0, 0), (-1, -1), 6)]))
        story.extend([table, Spacer(1, 0.22 * inch)])

    story.append(Paragraph("Cash Flow Entries", styles["Heading2"]))
    if month_rows.empty:
        story.append(Paragraph("No entries for this month.", styles["BodyText"]))
    else:
        rows = [["Type", "Source", "Amount", "Notes"]]
        for row in month_rows.itertuples(index=False):
            sign = "" if row.type == "income" else "-"
            rows.append([display_entry_type(row.type), row.source, f"{sign}{money(row.amount)}", row.notes or ""])
        table = Table(rows, colWidths=[1.2 * inch, 1.5 * inch, 1.1 * inch, 2.8 * inch], repeatRows=1)
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dddddd")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8edf2")), ("PADDING", (0, 0), (-1, -1), 5)]))
        story.extend([table, Spacer(1, 0.22 * inch)])

    story.append(Paragraph("Steven and Savings", styles["Heading2"]))
    detail_rows = [
        ["Steven Amount", money(float(steven_row["final_amount"])) if steven_row is not None else "$0.00"],
        ["Savings Balance", money(float(savings_row["current_balance"])) if savings_row is not None else "$0.00"],
        ["Savings Goal", money(float(savings_row["savings_goal"])) if savings_row is not None else "$0.00"],
    ]
    table = Table(detail_rows, colWidths=[2.6 * inch, 3.2 * inch])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dddddd")), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.append(table)

    story.extend([Spacer(1, 0.22 * inch), Paragraph("Spending Categories (Informational Only)", styles["Heading2"])])
    if spending_rows.empty:
        story.append(Paragraph("No spending category entries for this month.", styles["BodyText"]))
    else:
        table = Table(
            [["Category", "Amount"]] + [[row.category, money(row.amount)] for row in spending_rows.itertuples(index=False)],
            colWidths=[3.2 * inch, 2.4 * inch],
        )
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dddddd")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8edf2")), ("PADDING", (0, 0), (-1, -1), 6)]))
        story.append(table)

    if not plan_due_rows.empty:
        story.extend([Spacer(1, 0.22 * inch), Paragraph("Payment Plans Due", styles["Heading2"])])
        plan_table_rows = [["Plan", "Provider", "Due This Month", "Next Payment", "Remaining"]]
        for row in plan_due_rows.itertuples(index=False):
            plan_table_rows.append([
                row.plan_name,
                row.provider,
                money(row.amount_due),
                row.next_payment_date,
                money(row.remaining_balance),
            ])
        table = Table(plan_table_rows, colWidths=[1.6 * inch, 1.1 * inch, 1.25 * inch, 1.25 * inch, 1.25 * inch])
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dddddd")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8edf2")), ("PADDING", (0, 0), (-1, -1), 6)]))
        story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def show_reports(cash_flow, spending_entries, steven, savings, plans):
    st.markdown('<div class="section-title">📄 Reports</div>', unsafe_allow_html=True)
    current_month = current_month_value()
    selected_month = st.text_input("Report Month", value=current_month, placeholder="YYYY-MM or May 2026", key="report_month")
    selected_month = normalize_month(selected_month)
    month_rows = cash_flow[month_matches(cash_flow["month"], selected_month)].copy() if not cash_flow.empty else cash_flow
    month_rows = remove_saved_payment_plan_sources(month_rows, plans)
    summary = monthly_summary(cash_flow, steven, savings, selected_month, plans)
    plan_due_rows = payment_plan_details_for_month(plans, selected_month)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Monthly Summary")
    render_info_card(
        [
            ("Income", money(summary["income"])),
            ("Bills / Card Payments", money(summary["bills_card_payments"])),
            ("House / Steven", money(summary["steven_money_out"])),
            ("Savings Added", money(summary["savings_money_out"])),
            ("Payment Plans Due This Month", money(summary["payment_plans_due"])),
            ("Payment Plans Next Month", money(summary["payment_plans_next_month"])),
            ("Cash Left", money(summary["cash_left"])),
        ]
    )

    st.subheader("Payment Plans Due")
    if plan_due_rows.empty:
        st.info("No payment plan deductions for this month.")
    else:
        for row in plan_due_rows.itertuples(index=False):
            render_info_card(
                [
                    ("Plan", row.plan_name),
                    ("Provider", row.provider),
                    ("Amount Due This Month", money(row.amount_due)),
                    ("Next Payment Date", row.next_payment_date or "Not available"),
                    ("Remaining Balance", money(row.remaining_balance)),
                ]
            )
    st.subheader("CSV Export")
    csv_data = month_rows.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Cash Flow CSV",
        data=csv_data,
        file_name=f"tati-finance-{selected_month}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"cash_flow_csv_download_{selected_month}",
    )
    month_spending = (
        spending_entries[month_matches(spending_entries["month"], selected_month)].copy()
        if not spending_entries.empty
        else spending_entries
    )
    spending_csv = month_spending.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Spending CSV",
        data=spending_csv,
        file_name=f"tati-spending-{selected_month}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"spending_csv_download_{selected_month}",
    )

    st.subheader("Print History Report")
    pdf_bytes = build_monthly_pdf(cash_flow, spending_entries, steven, savings, plans, selected_month)
    if pdf_bytes is None:
        st.info("Install reportlab to create PDF reports: pip install reportlab")
    else:
        st.download_button(
            "Download Monthly PDF",
            data=pdf_bytes,
            file_name=f"tati-finance-{selected_month}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"monthly_pdf_download_{selected_month}",
        )
    st.markdown("</div>", unsafe_allow_html=True)
    show_history(cash_flow, spending_entries, steven, savings, plans, show_title=False)


def show_history(cash_flow, spending_entries, steven, savings, plans, show_title=True):
    if show_title:
        st.markdown('<div class="section-title">🕘 History</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Cash Flow History")
    if cash_flow.empty:
        st.info("No cash flow entries yet.")
    else:
        for row in cash_flow.sort_values(["month", "id"], ascending=[False, False]).itertuples(index=False):
            display_type = display_entry_type(row.type)
            display_amount = money(row.amount) if display_type == "Income" else f"-{money(row.amount)}"
            st.markdown(
                f"""
                <div class="entry-row">
                    <strong>{row.month}</strong> | {display_type} | {row.source}
                    | <strong>{display_amount}</strong><br>
                    <span>{row.notes or "No notes"}</span><br>
                    <span>{row.created_at}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Spending Category History")
    if spending_entries.empty:
        st.info("No spending category entries yet.")
    else:
        for row in spending_entries.sort_values(["month", "id"], ascending=[False, False]).itertuples(index=False):
            render_info_card(
                [
                    ("Date", getattr(row, "entry_date", "") or "Not available"),
                    ("Month", row.month),
                    ("Category", row.category),
                    ("Amount", money(row.amount)),
                    ("Paid With", row.paid_with),
                    ("Notes", row.notes or "No notes"),
                ]
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("House / Steven History")
    if steven.empty:
        st.info("No Steven calculations saved yet.")
    else:
        for row in steven.itertuples(index=False):
            render_info_card(
                [
                    ("Month", row.month),
                    ("Final Amount", money(row.final_amount)),
                    ("Total Deductions", money(getattr(row, "total_deductions", 0))),
                    ("Notes", row.notes or "No notes"),
                    ("Created At", getattr(row, "created_at", "") or "Not available"),
                ]
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Savings History")
    if savings.empty:
        st.info("No savings records saved yet.")
    else:
        for row in savings.itertuples(index=False):
            render_info_card(
                [
                    ("Month", row.month),
                    ("Balance", money(row.current_balance)),
                    ("Goal", money(row.savings_goal)),
                    ("Added", money(row.added_this_month)),
                    ("Taken", money(row.taken_this_month)),
                    ("Notes", row.notes or "No notes"),
                    ("Created At", row.created_at),
                ]
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Payment Plans History")
    if plans.empty:
        st.info("No payment plans saved yet.")
    else:
        for row in plans.itertuples(index=False):
            render_info_card(
                [
                    ("Plan", row.plan_name),
                    ("Provider", row.provider),
                    ("Category", row.purchase_category),
                    ("Original Amount", money(row.original_amount)),
                    ("Payment Amount", money(row.payment_amount)),
                    ("Payments", f"{row.payments_made} of {row.total_payments}"),
                    ("Start Date", row.start_date),
                    ("Notes", row.notes or "No notes"),
                ]
            )
    st.markdown("</div>", unsafe_allow_html=True)


def main():
    global supabase

    init_db()
    apply_styles()

    # Login section starts
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        show_login_screen()
        return
    # Login section ends

    if supabase is None:
        supabase = get_supabase_client()

    cash_flow = load_cash_flow()
    spending_entries = load_spending_entries()
    steven = load_steven()
    savings = load_savings()
    plans = load_payment_plans()

    st.markdown(
        """
        <div class="top-header">
            <h1 class="app-title">💰 My Money Dashboard</h1>
            <div class="app-subtitle">Tati's simple monthly money tracker</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Logout", key="logout_button"):
        logout_user()
        st.rerun()

    with st.sidebar:
        if st.button("Logout", key="sidebar_logout_button"):
            logout_user()
            st.rerun()

    (
        dashboard_tab,
        add_tab,
        spending_tab,
        steven_tab,
        savings_tab,
        plans_tab,
        reports_tab,
    ) = st.tabs(
        [
            "📊 Dashboard",
            "➕ Add Entry",
            "🧾 Spending Categories",
            "🏠 House / Steven",
            "💰 Savings",
            "📆 Plans",
            "📄 Reports",
        ]
    )

    with dashboard_tab:
        show_dashboard(cash_flow, steven, savings, spending_entries, plans)

    with add_tab:
        show_add_entry()
        show_recent_entries(cash_flow)

    with spending_tab:
        show_spending(spending_entries)

    with steven_tab:
        show_steven_calculator()

    with savings_tab:
        show_savings()

    with plans_tab:
        show_payment_plans()

    with reports_tab:
        show_reports(cash_flow, spending_entries, steven, savings, plans)



if __name__ == "__main__":
    main()
