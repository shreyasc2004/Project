from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db_connection():
    conn = sqlite3.connect('syst.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            userid INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY,
            userid INTEGER NOT NULL,
            date TEXT NOT NULL,
            purpose TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (userid) REFERENCES user(userid)
        )
    ''')
    conn.commit()
    conn.close()

def register_user(name, email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user (name, email, password) VALUES (?, ?, ?)", (name, email, password))
    conn.commit()
    conn.close()

def get_user(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

def add_expense(userid, date, purpose, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO expenses (userid, date, purpose, amount) VALUES (?, ?, ?, ?)",
                   (userid, date, purpose, amount))
    conn.commit()
    conn.close()

def get_expenses(userid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE userid = ?", (userid,))
    expenses = cursor.fetchall()
    conn.close()
    return expenses

def parse_messages(messages):
    parsed_data = []
    lines = messages.split('\n')
    # Adjusting regex to better handle spaces and patterns
    pattern = re.compile(r'Dear UPI user A/C [A-Z]\d+ debited by ([\d\.]+) on date (\d{2}[A-Za-z]{3}\d{2}) trf to (.+?) Refno \d+\. If not u\? call \d+\. -HDFC')
    
    for line in lines:
        print(f"Processing line: {line}")  # Debug print
        match = pattern.match(line)
        if match:
            amount = float(match.group(1))
            date_str = match.group(2)
            purpose = match.group(3)
            # Convert date to yyyy-mm-dd format
            date_obj = datetime.strptime(date_str, '%d%b%y')
            formatted_date = date_obj.strftime('%Y-%m-%d')
            parsed_data.append((formatted_date, purpose, amount))
            print(f"Parsed data: {formatted_date}, {purpose}, {amount}")  # Debug print
        else:
            print(f"Line did not match: {line}")  # Debug print
    
    return parsed_data


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user')
def user():
    if 'loggedin' not in session:
        return redirect('/login')
    expenses = get_expenses(session['userid'])
    return render_template('user.html',expenses=expenses)

@app.route('/auto_feed_expense', methods=['GET', 'POST'])
def auto_add_expense_route():
    if 'loggedin' not in session:
        return redirect('/login')
    if request.method == 'POST':
        messages = request.form['messages']
        parsed_data = parse_messages(messages)
        print(parsed_data)
        for date, purpose, amount in parsed_data:
            add_expense(session['userid'], date, purpose, amount)
        return redirect('/user')
    return render_template('auto_feed_expense.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        user = get_user(email, password)
        if user:
            session['loggedin'] = True
            session['userid'] = user['userid']
            session['name'] = user['name']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return redirect('/user')
            # return render_template('user.html', message=message)
        else:
            message = 'Please enter correct email/password!'
    return render_template('login.html', message=message)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('name', None)
    session.pop('email', None)
    return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
        elif not name or not password or not email:
            message = 'Please fill out the form!'
        else:
            register_user(name, email, password)
            message = 'You have successfully registered!'
    elif request.method == 'POST':
        message = 'Please fill out the form!'
    return render_template('register.html', message=message)

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense_route():
    if 'loggedin' not in session:
        return redirect('/login')
    if request.method == 'POST':
        date = request.form['date']
        purpose = request.form['purpose']
        amount = request.form['amount']
        add_expense(session['userid'], date, purpose, float(amount))
        return redirect('/user')
    return render_template('add_expense.html')

@app.route('/update_expense', methods=['POST'])
def update_expense():
    if 'loggedin' not in session:
        return redirect('/login')
    expense_id = request.form['id']
    date = request.form['date']
    purpose = request.form['purpose']
    amount = request.form['amount']

    conn = get_db_connection()
    conn.execute('UPDATE expenses SET date = ?, purpose = ?, amount = ? WHERE id = ?',
                 (date, purpose, amount, expense_id))
    conn.commit()
    conn.close()
    return redirect('/user')

@app.route('/delete_expense', methods=['POST'])
def delete_expense():
    if 'loggedin' not in session:
        return redirect('/login')
    expense_id = request.form['id']

    conn = get_db_connection()
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    return redirect('/user')

    
create_tables()

