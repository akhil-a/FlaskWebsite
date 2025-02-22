from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_session import Session
from werkzeug.utils import secure_filename
import mysql.connector
import redis
import socket
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

# ================= Configuration =================
# Configure session to use Redis
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://172.31.15.0:6379')
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['SESSION_COOKIE_NAME'] = 'CARTCOOKIE'
Session(app)

# Cart list to temporarily store selected products
cart = []

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# ================= Database Functions =================
# Establish a database connection
def get_db_connection():
    return mysql.connector.connect(
        host="172.31.8.84",
        user="shopping_user",
        password="shopping_password",
        database="shopping_app"
    )

# Fetch user credentials from MySQL
def get_user_credentials(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, password FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user:
        return {"user": None, "password": None}
    return {"user": user["username"], "password": user["password"]}

# Fetch product data from MySQL
def get_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return products

# ================= Routes =================
@app.route('/')
def home():
    return redirect(url_for('dashboard') if 'username' in session else 'login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        user_data = get_user_credentials(username)  # Fetch from MySQL
        if user_data["user"] and user_data["password"] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', hostname=socket.gethostname())

@app.route('/about')
def about():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('about.html', hostname=socket.gethostname())

@app.route('/products', methods=['GET', 'POST'])
def product_list():
    if 'username' not in session:
        return redirect(url_for('login'))
    products = get_products()  # Fetch from MySQL
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        for product in products:
            if product['name'] == product_name:
                cart.append(product)
                break
    return render_template('products.html', hostname=socket.gethostname(), products=products)

@app.route('/cart')
def view_cart():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('cart.html', cart=cart)

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'username' not in session:
        return redirect(url_for('login'))
    product_name = request.form.get('product_name')
    cart[:] = [p for p in cart if p['name'] != product_name]
    return redirect(url_for('view_cart'))

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'username' not in session:
        return redirect(url_for('login'))
    cart.clear()
    return render_template('order_success.html')

@app.route('/add_mobile', methods=['GET', 'POST'])
def add_mobile():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name, price, company = request.form.get('name'), request.form.get('price'), request.form.get('company')
        image = request.files['image']
        image_filename = 'default.png'
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_filename = f'static/images/{filename}'
        if name and price and company:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products (name, company, price, image) VALUES (%s, %s, %s, %s)", 
                           (name, company, price, image_filename))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('product_list'))
    return render_template('add_mobile.html')

@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))
    purchases = [
        {'id': 'ORD128763', 'date': '2024-02-15', 'model': 'iPhone 15', 'amount': '$999', 'status': 'Delivered'},
        {'id': 'ORD128764', 'date': '2024-02-18', 'model': 'Galaxy S23', 'amount': '$799', 'status': 'Shipped'},
        {'id': 'ORD128765', 'date': '2024-02-20', 'model': 'Pixel 8, Phone Case', 'amount': '$734', 'status': 'Processing'},
        {'id': 'ORD128766', 'date': '2024-02-22', 'model': 'Wireless Earbuds', 'amount': '$149', 'status': 'Delivered'},
        {'id': 'ORD128767', 'date': '2024-02-25', 'model': 'Screen Protector', 'amount': '$19', 'status': 'Cancelled'}
    ]
    return render_template('history.html', purchases=purchases, hostname=socket.gethostname())

@app.route('/status')
def status():
    return jsonify({"status": "OK"}), 200

# ================= Main =================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

