# 💬 SQL-AGENT: Natural Language to SQL Query Generator

> NL2SQL agent — turn natural language prompts into database query results.

---

## 🎥 Demo

Watch a short demo below to see the agent in action:  

![Demo](gif.gif)

---

## 🏛️ Architecture

Here is a high-level overview of how the NL2SQL agent processes requests:

![Architecture](nl2sql_architecture.svg)

---

## 🚀 Features

- ✅ **AI Query Generator** – Converts natural language questions into optimized SQL queries.
- ✅ **Database Integration** – Connects securely to your database to execute queries dynamically.
- ✅ **Automated Setup** – Easy initialization using the provided `setup_db.py` script.
- ✅ **Beautiful Result Display** – Clean and interactive tabular view for query results.
- ✅ **Secure Configuration** – Environment variable management using `.env.example` for secure deployment.

---

## 📁 Project Structure

Here is an overview of the repository files:

```text
📦SQL-AGENT/
├── .env.example              # Template for environment variables
├── LICENSE                   # MIT License file
├── README.md                 # Project documentation (this file)
├── app.py                    # Main application script (Frontend/Logic)
├── gif.gif                   # Demonstration animation
├── nl2sql_architecture.svg   # System architecture diagram
├── requirements.txt          # Python dependencies
└── setup_db.py               # Script to initialize the database
