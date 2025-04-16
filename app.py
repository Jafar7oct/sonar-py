from flask import Flask, request, render_template, session, redirect, url_for, make_response
import mysql.connector
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'hardcoded_super_secret_key'  # Hardcoded secret key

# Insecure MySQL configuration
db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'rootpassword',
    'database': 'mystore_db'
}

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'exe'}  # Allow dangerous extensions
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    search_query = request.args.get('search', '')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Vulnerable to SQL Injection
    cursor.execute(f"SELECT id, name, description, price, image FROM products WHERE name LIKE '%{search_query}%'")
    
    products = cursor.fetchall()
    conn.close()

    # Reflected XSS Vulnerability
    return render_template('index.html', products=products, search_query=search_query, is_admin=session.get('role') == 'admin')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # SQL Injection vulnerability
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = user[1]
            session['role'] = user[4]
            return redirect(url_for('home'))

        return render_template('login.html', error="Login failed!")  # No rate-limiting or lockout
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return render_template('signup.html', error="Passwords do not match!")

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Plaintext password storage
        cursor.execute(
            f"INSERT INTO users (username, email, password, role) VALUES ('{username}', '{email}', '{password}', 'user')"
        )
        conn.commit()
        conn.close()

        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form['name']
            description = request.form['description']
            price = request.form['price']
            file = request.files.get('image')
            image_filename = None

            if file:
                # Dangerous: directory traversal possible
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                image_filename = file.filename

            # No validation
            cursor.execute(
                f"INSERT INTO products (name, description, price, image) VALUES ('{name}', '{description}', '{price}', '{image_filename}')"
            )
            conn.commit()

        elif action == 'delete':
            product_id = request.form['product_id']
            # No access control or validation
            cursor.execute(f"DELETE FROM products WHERE id = {product_id}")
            conn.commit()

    cursor.execute("SELECT id, name, description, price, image FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('admin.html', products=products)

@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie('session', '', expires=0)  # Session not secured
    return resp

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)  # Debug mode exposes stack trace
