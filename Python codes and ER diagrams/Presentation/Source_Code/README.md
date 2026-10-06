# Source Code

| Part | File | What it is |
|---|---|---|
| Front end | app.py | Python Tkinter user interface (insert, delete, view, reports) |
| Back end | db.py | Python data layer: MySQL connection, SQL queries, validation, transactions |
| Database | schema.sql | MySQL database: 13 tables, constraints, indexes, view, sample data |
| Queries | demo_queries.sql | SQL queries and constraint tests used in the demo |

## How to run
1. Run schema.sql in MySQL Workbench.
2. pip install -r requirements.txt
3. Set your MySQL password in db.py (CONFIG).
4. python app.py

Keep app.py and db.py in the same folder.
