from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a secure random string in production

# File paths
USER_FILE = 'users.json'
PRODUCT_FILE = 'data/products.json'

# ----------------------- Helpers -----------------------

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_products():
    if not os.path.exists(PRODUCT_FILE):
        return []
    try:
        with open(PRODUCT_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_products(products):
    with open(PRODUCT_FILE, 'w') as f:
        json.dump(products, f, indent=2)

def get_next_product_id():
    products = load_products()
    return max([p['id'] for p in products], default=0) + 1

# ----------------------- Public -----------------------

@app.route('/')
def home():
    products = load_products()
    return render_template('index.html', products=products)

@app.route('/wishlist')
def wishlist():
    products = load_products()
    return render_template('wishlist.html', products=products)

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/go/<int:product_id>')
def track_click(product_id):
    products = load_products()
    for product in products:
        if product['id'] == product_id:
            product['clicks'] = product.get('clicks', 0) + 1
            save_products(products)
            return redirect(product['affiliate_link'])
    return "Product not found", 404

# ----------------------- Auth -----------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if users.get(username) == password:
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        flash("Invalid credentials")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        users = load_users()
        if email in users:
            session['reset_email'] = email
            return redirect(url_for('reset_password'))
        flash("Email not found")
        return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/reset', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')
    if not email:
        flash("Session expired. Please try again.")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        users = load_users()
        users[email] = new_password
        save_users(users)
        session.pop('reset_email', None)
        flash("Password reset successful.")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# ----------------------- Admin Dashboard -----------------------

@app.route('/admin')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    products = load_products()
    return render_template('admin.html', products=products)

@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if 'admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_product = {
            "id": get_next_product_id(),
            "title": request.form['title'],
            "image": request.form['image'],
            "price": request.form['price'],
            "category": request.form['category'],
            "affiliate_link": request.form['affiliate_link'],
            "clicks": 0
        }
        products = load_products()
        products.append(new_product)
        save_products(products)
        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')

@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    products = load_products()
    product = next((p for p in products if p['id'] == product_id), None)

    if not product:
        return "Product not found", 404

    if request.method == 'POST':
        product['title'] = request.form['title']
        product['image'] = request.form['image']
        product['price'] = request.form['price']
        product['category'] = request.form['category']
        product['affiliate_link'] = request.form['affiliate_link']
        save_products(products)
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_product.html', product=product)

@app.route('/admin/delete/<int:product_id>')
def delete_product(product_id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    products = load_products()
    products = [p for p in products if p['id'] != product_id]
    save_products(products)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/stats')
def product_stats():
    if 'admin' not in session:
        return redirect(url_for('login'))
    products = load_products()
    return render_template('stats.html', products=products)

# ----------------------- API Endpoint -----------------------

@app.route('/api/fetch', methods=['POST'])
def fetch_product_data():
    url = request.json.get('url')
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.find(id="productTitle")
        image = soup.find(id="landingImage")
        price = soup.find(class_="a-offscreen")

        return {
            "title": title.get_text(strip=True) if title else "",
            "image": image['src'] if image else "",
            "price": price.get_text(strip=True) if price else ""
        }

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------- Run App -----------------------

if __name__ == '__main__':
    app.run(debug=True)
