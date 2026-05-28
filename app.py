from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import re
import time
import pandas as pd
import mysql.connector
import sqlalchemy
from groq import Groq

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

ALLOWED_STARTERS = ("select", "insert", "update", "delete")
ALLOWED_TABLES   = {"customers", "pizzas", "orders", "order_items"}
TABLE_NAME_RE    = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')

groq_client = Groq(api_key=GROQ_API_KEY)

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an expert in converting English questions to accurate, optimized SQL queries
for a pizza sales database called PizzaVault.

Tables:
1. CUSTOMERS   — CUSTOMER_ID (PK), NAME, EMAIL, CITY, PHONE, JOINED_DATE
2. PIZZAS      — PIZZA_ID (PK), NAME, CATEGORY ENUM('Classic','Veggie','Chicken','Supreme'),
                 SIZE ENUM('S','M','L','XL'), PRICE (decimal), CRUST
3. ORDERS      — ORDER_ID (PK), CUSTOMER_ID (FK), ORDER_DATE (datetime), TOTAL_AMOUNT (decimal),
                 PAYMENT ENUM('Cash','Card','UPI','Online'),
                 STATUS ENUM('Pending','Preparing','Delivered','Cancelled')
4. ORDER_ITEMS — ITEM_ID (PK), ORDER_ID (FK), PIZZA_ID (FK), QUANTITY (int), UNIT_PRICE (decimal)

Rules:
- Output ONLY the raw SQL query. No explanation, no markdown, no triple backticks.
- Use proper JOINs when pulling from multiple tables.
- Column and table names must match exactly as defined above.
- Only reference tables listed above. Never query system tables.
- For revenue/sales use: SUM(oi.QUANTITY * oi.UNIT_PRICE) or TOTAL_AMOUNT from ORDERS.
- For date filtering use DATE(ORDER_DATE) or YEAR(ORDER_DATE), MONTH(ORDER_DATE).

Examples:
Q: Show all pizzas in the Chicken category.
A: SELECT NAME, SIZE, PRICE, CRUST FROM PIZZAS WHERE CATEGORY = 'Chicken' ORDER BY PRICE;

Q: Which pizza generated the most revenue?
A: SELECT p.NAME, p.SIZE, SUM(oi.QUANTITY * oi.UNIT_PRICE) AS revenue FROM ORDER_ITEMS oi JOIN PIZZAS p ON oi.PIZZA_ID = p.PIZZA_ID GROUP BY p.PIZZA_ID, p.NAME, p.SIZE ORDER BY revenue DESC LIMIT 1;
"""

# ─── DB HELPERS ───────────────────────────────────────────────────────────────
def _conn_kwargs(database: str | None = None) -> dict:
    socket_path = os.getenv("MYSQL_SOCKET", "/run/mysqld/mysqld.sock")
    kwargs = dict(user=os.getenv("MYSQL_USER", "root"), password=os.getenv("MYSQL_PASSWORD", ""))
    if database:
        kwargs["database"] = database
    if os.path.exists(socket_path):
        kwargs["unix_socket"] = socket_path
    else:
        kwargs["host"] = os.getenv("MYSQL_HOST", "localhost")
    return kwargs

def get_connection():
    return mysql.connector.connect(**_conn_kwargs(database=os.getenv("MYSQL_DATABASE", "pizzavault")))

def get_engine():
    u, p = os.getenv("MYSQL_USER","root"), os.getenv("MYSQL_PASSWORD","")
    db   = os.getenv("MYSQL_DATABASE","pizzavault")
    host = os.getenv("MYSQL_HOST","localhost")
    sock = os.getenv("MYSQL_SOCKET","/run/mysqld/mysqld.sock")
    return sqlalchemy.create_engine(f"mysql+mysqlconnector://{u}:{p}@{host}/{db}?unix_socket={sock}")

def execute_query(sql: str):
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute(sql)
        if sql.strip().lower().startswith("select"):
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return cols, rows
        else:
            conn.commit()
            return None, cur.rowcount
    finally:
        cur.close(); conn.close()

# ─── GROQ ─────────────────────────────────────────────────────────────────────
def get_sql_from_groq(question: str) -> str:
    last_exc = None
    for attempt in range(3):
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":question}],
                temperature=0, max_tokens=256, timeout=20,
            )
            return r.choices[0].message.content.strip()
        except Exception as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
    raise last_exc

# ─── VALIDATION ───────────────────────────────────────────────────────────────
def validate_sql(sql: str) -> tuple[bool, str]:
    clean = sql.strip().lower()
    if not any(clean.startswith(op) for op in ALLOWED_STARTERS):
        return False, f"⛔ Only SELECT/INSERT/UPDATE/DELETE allowed. Got: `{sql[:80]}`"
    if ";" in sql.rstrip(";"):
        return False, "⛔ Multiple statements not permitted."
    referenced = re.findall(r'\b(?:from|join|into|update)\s+`?(\w+)`?', clean)
    bad = [t for t in referenced if t not in ALLOWED_TABLES]
    if bad:
        return False, f"⛔ Unauthorized table(s): {', '.join(bad)}"
    return True, ""

# ─── LOGGING ──────────────────────────────────────────────────────────────────
def log_query(question: str, sql: str, status: str):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("INSERT INTO QUERY_LOG (QUESTION,GENERATED_SQL,STATUS) VALUES (%s,%s,%s)",
                    (question, sql, status[:20]))
        conn.commit(); cur.close(); conn.close()
    except Exception:
        pass

# ─── METRICS ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_metrics() -> dict:
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ORDERS WHERE STATUS='Delivered'")
        total_orders = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(TOTAL_AMOUNT),0) FROM ORDERS WHERE STATUS='Delivered'")
        total_revenue = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT CUSTOMER_ID) FROM ORDERS")
        customers = cur.fetchone()[0]
        cur.execute("""SELECT p.NAME, p.SIZE, SUM(oi.QUANTITY) AS sold
            FROM ORDER_ITEMS oi JOIN PIZZAS p ON oi.PIZZA_ID=p.PIZZA_ID
            JOIN ORDERS o ON oi.ORDER_ID=o.ORDER_ID WHERE o.STATUS='Delivered'
            GROUP BY p.PIZZA_ID ORDER BY sold DESC LIMIT 1""")
        row = cur.fetchone()
        cur.close(); conn.close()
        return dict(total_orders=total_orders, total_revenue=float(total_revenue),
                    customers=customers, best=f"{row[0]} ({row[1]})" if row else "—")
    except Exception:
        return {}

# ─── ADMIN MODAL (st.dialog) ──────────────────────────────────────────────────
@st.dialog("🔐 Admin Access")
def admin_dialog():
    st.write("Enter your admin credentials to unlock upload and management tools.")

    username = st.text_input("Username", placeholder="admin username")
    password = st.text_input("Password", type="password", placeholder="••••••••")

    col_login, col_cancel = st.columns([1, 1])

    with col_login:
        if st.button("Login", use_container_width=True):
            if not ADMIN_USERNAME or not ADMIN_PASSWORD:
                st.error("Admin credentials not configured in environment.")
            elif username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.session_state["show_admin_panel"]    = True
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")

    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.session_state["show_admin_panel"] = False
            st.rerun()

# ─── ADMIN PANEL (shown after auth) ───────────────────────────────────────────
def render_admin_panel():
    st.divider()
    st.subheader("⚙️ Admin Panel")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded   = st.file_uploader("Upload CSV", type=["csv"])
        table_name = st.text_input("Target Table", placeholder="e.g. pizzas")
    with col2:
        st.write("**Allowed tables:**")
        for t in sorted(ALLOWED_TABLES):
            st.write(f"- {t}")

    upload_col, logout_col = st.columns([1, 1])
    with upload_col:
        if st.button("⬆️ Upload Data", use_container_width=True):
            if not uploaded or not table_name:
                st.warning("Provide both a CSV file and a table name.")
            elif not TABLE_NAME_RE.match(table_name):
                st.error("❌ Invalid table name.")
            elif table_name.lower() not in ALLOWED_TABLES:
                st.error(f"❌ '{table_name}' not allowed. Use: {', '.join(sorted(ALLOWED_TABLES))}")
            else:
                try:
                    df = pd.read_csv(uploaded)
                    df.to_sql(table_name, con=get_engine(), if_exists="append", index=False)
                    st.success(f"✅ {len(df)} rows uploaded to `{table_name}`")
                    st.dataframe(df, use_container_width=True)
                except Exception as exc:
                    st.error(f"❌ Upload failed: {exc}")
    with logout_col:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["admin_authenticated"] = False
            st.session_state["show_admin_panel"]    = False
            st.rerun()
    st.divider()

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
EXAMPLE_QUERIES = [
    "Show all pizzas in the Chicken category",
    "Which pizza generated the most revenue?",
    "List top 5 customers by total spend",
    "How many orders placed each month in 2024?",
    "Show total revenue by payment method",
    "Which city has the most orders?",
    "List all XL pizzas with prices",
    "Show all Veggie pizzas under ₹400",
    "Which customers are from Chennai?",
]

def _on_sample():
    v = st.session_state.get("sample_select", "")
    if v:
        st.session_state["query_input"]  = v
        st.session_state["sample_select"] = ""

def render_sidebar():
    st.sidebar.title("🍕 PizzaVault")
    st.sidebar.caption("Sales Intelligence · NL → SQL")
    st.sidebar.divider()
    st.sidebar.write("**💡 Sample Questions**")
    for q in EXAMPLE_QUERIES[:6]:
        st.sidebar.write(f"- {q}")
    st.sidebar.divider()
    st.sidebar.selectbox("🎯 Pick a query", [""] + EXAMPLE_QUERIES,
                         key="sample_select", on_change=_on_sample)

# ─── METRICS ROW ──────────────────────────────────────────────────────────────
def render_metrics():
    m = load_metrics()
    if not m:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"₹{m['total_revenue']:,.0f}")
    col2.metric("Orders Delivered", str(m["total_orders"]))
    col3.metric("Active Customers", str(m["customers"]))
    col4.metric("Best Seller", m["best"])

# ─── HANDLE QUERY ─────────────────────────────────────────────────────────────
def handle_query(question: str):
    with st.spinner("Generating SQL…"):
        try:
            sql = get_sql_from_groq(question)
        except Exception as exc:
            st.error(f"⚠️ Groq error: {exc}")
            return

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    valid, err = validate_sql(sql)
    if not valid:
        st.error(err)
        log_query(question, sql, "BLOCKED")
        return

    with st.spinner("Executing…"):
        try:
            cols, result = execute_query(sql)
            log_query(question, sql, "OK")
        except mysql.connector.Error as exc:
            st.error(f"MySQL error: {exc}")
            log_query(question, sql, "ERROR")
            return
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            log_query(question, sql, "ERROR")
            return

    if cols is not None:
        df = pd.DataFrame(result, columns=cols)
        st.success(f"✅ {len(df)} row(s) returned.")
        st.subheader("Results")
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(),
                               "results.csv", "text/csv")
    else:
        st.success(f"✅ Done. Rows affected: {result}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="PizzaVault", page_icon="🍕", layout="wide")
    
    render_sidebar()

    # Session state init
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    if "show_admin_panel" not in st.session_state:
        st.session_state["show_admin_panel"] = False

    # ── Hero ──
    st.title("🍕 PIZZA VAULT")
    st.caption("Sales Intelligence · Natural Language → SQL")
    st.write("") 

    # ── Metrics ──
    render_metrics()
    st.divider()

    # ── Query Box + Admin Button ──
    st.subheader("Ask anything about your data")

    question = st.text_input(
        label     = "query",
        label_visibility = "collapsed",
        key       = "query_input",
        placeholder = 'e.g.  "Which pizza made the most money in March 2024?"',
    )

    btn_col, _, admin_col = st.columns([2, 6, 2])
    with btn_col:
        run = st.button("🔍 Run Query", use_container_width=True)
    with admin_col:
        open_admin = st.button("🔐 Admin Access", use_container_width=True)

    # ── Trigger admin dialog ──
    if open_admin and not st.session_state["admin_authenticated"]:
        admin_dialog()

    # ── Admin Panel (post-auth) ──
    if st.session_state["admin_authenticated"] and st.session_state["show_admin_panel"]:
        render_admin_panel()

    # ── Run Query ──
    if run:
        if not question.strip():
            st.warning("Please enter a question first.")
        else:
            handle_query(question.strip())

if __name__ == "__main__":
    main()
