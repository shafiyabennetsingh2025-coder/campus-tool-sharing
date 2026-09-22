# CampusShare — Campus Tool Sharing Management System

A DBMS project prototype for college students to lend, reserve and borrow academic/technical tools.

## Stack
- Frontend: HTML + CSS
- Backend: Python Flask
- Database: SQLite (`campus_tools.db`)

## Run
1. Install Python 3.
2. Open Terminal in this folder.
3. `python3 -m venv venv`
4. `source venv/bin/activate` (Windows: `venv\\Scripts\\activate`)
5. `pip install -r requirements.txt`
6. `python app.py`
7. Open `http://127.0.0.1:5000`

The database is created automatically the first time the application runs. Demo student, category and tool records are inserted only when the tables are empty.

## Main database relationships
Students 1---N Tools
Categories 1---N Tools
Tools 1---N BorrowRequests
Students 1---N BorrowRequests
Tools 1---N Reservations
Tools 1---N Maintenance
Tools 1---N Feedback

## Demo flow
Browse an available tool -> select a due date -> Request to Borrow -> Admin Dashboard -> Approve -> tool becomes Borrowed -> Mark Returned -> tool becomes Available.
