from flask import Flask, request, render_template, session, redirect, url_for
import mysql.connector
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# MySQL configuration (for Docker Compose)
db_config = {
    'host': 'db',
    'user': 'root',
    'password': 'rootpassword',
    'database': 'mystore_db'
}

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    search_query = request.args.get('search', '')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    if search_query:
        cursor.execute("SELECT id, name, description, price, image FROM products WHERE name LIKE %s", (f"%{search_query}%",))
    else:
        cursor.execute("SELECT id, name, description, price, image FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('index.html', products=products, is_admin=session.get('role') == 'admin', search_query=search_query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()
        if user:
            session['username'] = user[1]
            session['role'] = user[4]
            return redirect(url_for('home'))
        return render_template('login.html', error="Login failed!")
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
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, 'user')",
                (username, email, password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            conn.close()
            return render_template('signup.html', error="Username or email already exists!")
    return render_template('signup.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, image FROM products")
    products = cursor.fetchall()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form['name']
            description = request.form['description']
            price = request.form['price']
            file = request.files.get('image')
            image_filename = None
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
            cursor.execute(
                "INSERT INTO products (name, description, price, image) VALUES (%s, %s, %s, %s)",
                (name, description, price, image_filename)
            )
            conn.commit()
        elif action == 'edit':
            product_id = request.form['product_id']
            name = request.form['name']
            description = request.form['description']
            price = request.form['price']
            file = request.files.get('image')
            image_filename = request.form.get('existing_image')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
            cursor.execute(
                "UPDATE products SET name=%s, description=%s, price=%s, image=%s WHERE id=%s",
                (name, description, price, image_filename, product_id)
            )
            conn.commit()
        elif action == 'delete':
            product_id = request.form['product_id']
            cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))
            conn.commit()
        return redirect(url_for('admin'))
    
    conn.close()
    return render_template('admin.html', products=products)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
