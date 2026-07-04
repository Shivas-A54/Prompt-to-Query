# 💬 Prompt2Query : Natural Language to SQL Query Generator

> Turn plain-English questions into executable SQL queries and get results back in a clean, interactive table — no SQL knowledge required.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)
![MySQL](https://img.shields.io/badge/Database-MySQL%2FMariaDB-orange.svg)
![Groq](https://img.shields.io/badge/LLM-Groq-green.svg)

---

## 🎥 Demo

Watch a short demo below to see the agent in action:

![Demo](gif.gif)

---

## 🏛️ Architecture

Here is a high-level overview of how the NL2SQL agent processes requests:

![Architecture](nl2sql_architecture.svg)

**Flow:** User prompt → LLM (Groq) converts natural language to SQL → query is validated → executed against MySQL/MariaDB → results rendered in Streamlit.

---

## 🚀 Features

- ✅ **AI Query Generator** – Converts natural language questions into optimized SQL queries using Groq's LLM API.
- ✅ **Database Integration** – Connects securely to a MySQL/MariaDB instance and executes generated queries dynamically.
- ✅ **Automated Setup** – One-command schema initialization via `setup_db.py`.
- ✅ **Beautiful Result Display** – Clean, interactive tabular view for query results built with Streamlit.
- ✅ **Secure Configuration** – Credentials and API keys managed through environment variables (`.env`), never hardcoded.
- ✅ **Admin Access Control** – Configurable admin credentials for restricted operations.

---

## 🧱 Tech Stack

| Layer            | Technology                          |
|-------------------|--------------------------------------|
| Frontend / UI     | Streamlit                            |
| LLM / NL→SQL      | Groq API                             |
| Database          | MySQL / MariaDB                      |
| DB Driver         | mysql-connector-python               |
| Config Management | python-dotenv                        |
| Language          | Python 3.10+                         |

---

## 📁 Project Structure

```text
📦Prompt-to-Query/
├── .env.example              # Template for environment variables
├── LICENSE                   # MIT License file
├── README.md                 # Project documentation (this file)
├── app.py                    # Main application script (Frontend/Logic)
├── gif.gif                   # Demonstration animation
├── nl2sql_architecture.svg   # System architecture diagram
├── requirements.txt          # Python dependencies
└── setup_db.py               # Script to initialize the database
```

---

## ⚙️ Getting Started

### Prerequisites

- Python 3.10 or higher
- A running MySQL or MariaDB server
- A free [Groq API key](https://console.groq.com)

### 1. Clone the repository

```bash
git clone https://github.com/Shivas-A54/Prompt-to-Query.git
cd Prompt-to-Query
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

```env
MYSQL_HOST=localhost
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=student_db
GROQ_API_KEY="your_groq_api_key"
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

### 4. Initialize the database

```bash
python setup_db.py
```

This creates and seeds the schema the app queries against.

### 5. Run the app

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

---


## 👤 Author

**Shivas**
Aspiring Data Engineer specializing in AI — building automated data pipelines and deploying ML models (predictive maintenance, anomaly detection) into production.

- GitHub: [@Shivas-A54](https://github.com/Shivas-A54)
- LinkedIn: [shivas-arulselvam](https://linkedin.com/in/shivas-arulselvam)

---
