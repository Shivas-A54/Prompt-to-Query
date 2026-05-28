import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# ─── CONNECTION CONFIG ─────────────────────────────────────────────────────────
socket_path = os.getenv("MYSQL_SOCKET", "/run/mysqld/mysqld.sock")
host        = os.getenv("MYSQL_HOST", "localhost")
user        = os.getenv("MYSQL_USER", "root")
password    = os.getenv("MYSQL_PASSWORD", "")
db_name     = os.getenv("MYSQL_DATABASE", "pizzavault")
app_user    = os.getenv("MYSQL_APP_USER", "pizzavault_app")
app_pass    = os.getenv("MYSQL_APP_PASSWORD", "")

def make_connection(database: str | None = None) -> mysql.connector.MySQLConnection:
    kwargs = dict(user=user, password=password)
    if database:
        kwargs["database"] = database
    if os.path.exists(socket_path):
        kwargs["unix_socket"] = socket_path
    else:
        kwargs["host"] = host
    return mysql.connector.connect(**kwargs)

try:
    conn = make_connection()
except Exception as e:
    print(f"❌ Failed to connect to MySQL: {e}")
    exit(1)

cur = conn.cursor()

# ─── DATABASE ─────────────────────────────────────────────────────────────────
cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
cur.execute(f"USE `{db_name}`")

# ─── APP USER ─────────────────────────────────────────────────────────────────
if app_pass:
    try:
        cur.execute(f"CREATE USER IF NOT EXISTS '{app_user}'@'localhost' IDENTIFIED BY '{app_pass}'")
        cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{db_name}`.* TO '{app_user}'@'localhost'")
        cur.execute("FLUSH PRIVILEGES")
        print(f"✅ App user '{app_user}' created/verified.")
    except Exception as e:
        print(f"⚠️  Could not create app user: {e}")
else:
    print("⚠️  MYSQL_APP_PASSWORD not set — skipping app user creation.")

# ─── DROP TABLES (FK-safe order) ──────────────────────────────────────────────
cur.execute("SET FOREIGN_KEY_CHECKS = 0")
for t in ("ORDER_ITEMS", "ORDERS", "PIZZAS", "CUSTOMERS", "QUERY_LOG"):
    cur.execute(f"DROP TABLE IF EXISTS `{t}`")
cur.execute("SET FOREIGN_KEY_CHECKS = 1")

# ─── CREATE TABLES ─────────────────────────────────────────────────────────────
cur.execute("""
CREATE TABLE CUSTOMERS (
    CUSTOMER_ID   INT          NOT NULL AUTO_INCREMENT,
    NAME          VARCHAR(100) NOT NULL,
    EMAIL         VARCHAR(120),
    CITY          VARCHAR(60),
    PHONE         VARCHAR(20),
    JOINED_DATE   DATE,
    PRIMARY KEY (CUSTOMER_ID)
) ENGINE=InnoDB""")

cur.execute("""
CREATE TABLE PIZZAS (
    PIZZA_ID      INT          NOT NULL AUTO_INCREMENT,
    NAME          VARCHAR(100) NOT NULL,
    CATEGORY      ENUM('Classic','Veggie','Chicken','Supreme') NOT NULL,
    SIZE          ENUM('S','M','L','XL') NOT NULL,
    PRICE         DECIMAL(6,2) NOT NULL,
    CRUST         VARCHAR(40),
    PRIMARY KEY (PIZZA_ID)
) ENGINE=InnoDB""")

cur.execute("""
CREATE TABLE ORDERS (
    ORDER_ID      INT          NOT NULL AUTO_INCREMENT,
    CUSTOMER_ID   INT,
    ORDER_DATE    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    TOTAL_AMOUNT  DECIMAL(8,2),
    PAYMENT       ENUM('Cash','Card','UPI','Online') DEFAULT 'Cash',
    STATUS        ENUM('Pending','Preparing','Delivered','Cancelled') DEFAULT 'Delivered',
    PRIMARY KEY (ORDER_ID),
    CONSTRAINT fk_order_customer
        FOREIGN KEY (CUSTOMER_ID) REFERENCES CUSTOMERS(CUSTOMER_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB""")

cur.execute("""
CREATE TABLE ORDER_ITEMS (
    ITEM_ID       INT          NOT NULL AUTO_INCREMENT,
    ORDER_ID      INT          NOT NULL,
    PIZZA_ID      INT          NOT NULL,
    QUANTITY      INT          NOT NULL DEFAULT 1,
    UNIT_PRICE    DECIMAL(6,2) NOT NULL,
    PRIMARY KEY (ITEM_ID),
    CONSTRAINT fk_item_order
        FOREIGN KEY (ORDER_ID)  REFERENCES ORDERS(ORDER_ID)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_item_pizza
        FOREIGN KEY (PIZZA_ID)  REFERENCES PIZZAS(PIZZA_ID)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB""")

cur.execute("""
CREATE TABLE QUERY_LOG (
    ID            INT          NOT NULL AUTO_INCREMENT,
    TIMESTAMP     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    QUESTION      TEXT,
    GENERATED_SQL TEXT,
    STATUS        VARCHAR(20),
    PRIMARY KEY (ID)
) ENGINE=InnoDB""")

# ─── SEED: CUSTOMERS ──────────────────────────────────────────────────────────
cur.executemany(
    "INSERT INTO CUSTOMERS (NAME,EMAIL,CITY,PHONE,JOINED_DATE) VALUES (%s,%s,%s,%s,%s)",
    [
        ("Arjun Sharma",    "arjun@mail.com",   "Chennai",   "9876543210", "2023-01-15"),
        ("Priya Nair",      "priya@mail.com",   "Bangalore", "9876543211", "2023-03-08"),
        ("Ravi Kumar",      "ravi@mail.com",    "Mumbai",    "9876543212", "2023-05-20"),
        ("Sneha Patel",     "sneha@mail.com",   "Delhi",     "9876543213", "2023-07-11"),
        ("Karthik Raj",     "karthik@mail.com", "Chennai",   "9876543214", "2023-09-02"),
        ("Meera Iyer",      "meera@mail.com",   "Hyderabad", "9876543215", "2024-01-10"),
        ("Vikram Singh",    "vikram@mail.com",  "Pune",      "9876543216", "2024-02-14"),
        ("Anjali Reddy",    "anjali@mail.com",  "Chennai",   "9876543217", "2024-03-05"),
    ]
)

# ─── SEED: PIZZAS ─────────────────────────────────────────────────────────────
cur.executemany(
    "INSERT INTO PIZZAS (NAME,CATEGORY,SIZE,PRICE,CRUST) VALUES (%s,%s,%s,%s,%s)",
    [
        ("Margherita",          "Classic",  "S",  199.00, "Thin"),
        ("Margherita",          "Classic",  "M",  299.00, "Thin"),
        ("Margherita",          "Classic",  "L",  399.00, "Thin"),
        ("Pepperoni",           "Classic",  "M",  399.00, "Regular"),
        ("Pepperoni",           "Classic",  "L",  499.00, "Regular"),
        ("BBQ Classic",         "Classic",  "L",  549.00, "Stuffed"),
        ("Veggie Supreme",      "Veggie",   "M",  349.00, "Thin"),
        ("Veggie Supreme",      "Veggie",   "L",  449.00, "Thin"),
        ("Paneer Tikka",        "Veggie",   "M",  379.00, "Regular"),
        ("Paneer Tikka",        "Veggie",   "L",  479.00, "Regular"),
        ("Garden Fresh",        "Veggie",   "S",  229.00, "Thin"),
        ("Chicken BBQ",         "Chicken",  "M",  449.00, "Regular"),
        ("Chicken BBQ",         "Chicken",  "L",  549.00, "Regular"),
        ("Peri Peri Chicken",   "Chicken",  "M",  429.00, "Stuffed"),
        ("Peri Peri Chicken",   "Chicken",  "L",  529.00, "Stuffed"),
        ("Chicken Tikka",       "Chicken",  "L",  579.00, "Regular"),
        ("Meat Lovers",         "Supreme",  "L",  699.00, "Stuffed"),
        ("Meat Lovers",         "Supreme",  "XL", 849.00, "Stuffed"),
        ("Double Cheese Burst", "Supreme",  "L",  649.00, "Stuffed"),
        ("The Works",           "Supreme",  "XL", 899.00, "Stuffed"),
    ]
)

# ─── SEED: ORDERS ─────────────────────────────────────────────────────────────
orders = [
    (1, "2024-01-05 12:30:00", 698.00,  "UPI",    "Delivered"),
    (2, "2024-01-10 19:15:00", 449.00,  "Card",   "Delivered"),
    (3, "2024-01-22 20:00:00", 1048.00, "Online", "Delivered"),
    (4, "2024-02-03 13:45:00", 299.00,  "Cash",   "Delivered"),
    (1, "2024-02-14 21:00:00", 1398.00, "Card",   "Delivered"),
    (5, "2024-02-20 18:30:00", 579.00,  "UPI",    "Delivered"),
    (6, "2024-03-01 12:00:00", 899.00,  "Online", "Delivered"),
    (2, "2024-03-08 20:30:00", 958.00,  "Card",   "Delivered"),
    (7, "2024-03-15 19:00:00", 649.00,  "Cash",   "Delivered"),
    (3, "2024-04-01 13:00:00", 478.00,  "UPI",    "Delivered"),
    (8, "2024-04-12 21:30:00", 1748.00, "Online", "Delivered"),
    (4, "2024-04-20 18:00:00", 549.00,  "Card",   "Delivered"),
    (5, "2024-05-02 12:30:00", 829.00,  "UPI",    "Delivered"),
    (1, "2024-05-18 20:00:00", 449.00,  "Cash",   "Delivered"),
    (6, "2024-06-01 19:15:00", 1198.00, "Card",   "Delivered"),
    (2, "2024-06-15 13:30:00", 399.00,  "UPI",    "Cancelled"),
    (7, "2024-07-04 20:45:00", 699.00,  "Online", "Delivered"),
    (3, "2024-07-20 18:00:00", 1448.00, "Card",   "Delivered"),
    (8, "2024-08-05 12:00:00", 479.00,  "Cash",   "Delivered"),
    (4, "2024-08-22 21:00:00", 899.00,  "UPI",    "Delivered"),
]
cur.executemany(
    "INSERT INTO ORDERS (CUSTOMER_ID,ORDER_DATE,TOTAL_AMOUNT,PAYMENT,STATUS) VALUES (%s,%s,%s,%s,%s)",
    orders
)

# ─── SEED: ORDER_ITEMS ────────────────────────────────────────────────────────
order_items = [
    (1,  3,  1, 399.00), (1,  7,  1, 299.00),
    (2,  12, 1, 449.00),
    (3,  5,  1, 499.00), (3,  13, 1, 549.00),
    (4,  2,  1, 299.00),
    (5,  17, 2, 699.00),
    (6,  16, 1, 579.00),
    (7,  20, 1, 899.00),
    (8,  14, 1, 429.00), (8,  10, 1, 479.00), (8, 2, 1, 299.00),
    (9,  19, 1, 649.00),
    (10, 9,  1, 379.00), (10, 1,  1, 199.00),
    (11, 18, 2, 849.00), (11, 6,  1, 549.00),
    (12, 6,  1, 549.00),
    (13, 15, 1, 529.00), (13, 2,  1, 299.00),
    (14, 12, 1, 449.00),
    (15, 5,  1, 499.00), (15, 13, 1, 549.00), (15, 3, 1, 399.00),
    (16, 3,  1, 399.00),
    (17, 17, 1, 699.00),
    (18, 18, 1, 849.00), (18, 15, 1, 529.00), (18, 8, 1, 449.00),
    (19, 10, 1, 479.00),
    (20, 20, 1, 899.00),
]
cur.executemany(
    "INSERT INTO ORDER_ITEMS (ORDER_ID,PIZZA_ID,QUANTITY,UNIT_PRICE) VALUES (%s,%s,%s,%s)",
    order_items
)

conn.commit()
cur.close()
conn.close()
print("🍕 PizzaVault database seeded successfully!")
