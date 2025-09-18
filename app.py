import os
import json
import uuid
import markdown
import smtplib
import traceback
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse, urljoin
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import google.generativeai as genai
from flask import (
    Flask, render_template, jsonify, request, 
    redirect, url_for, session, flash, abort
)
import firebase_admin
from firebase_admin import (
    credentials, 
    firestore, 
    storage, 
    auth as firebase_auth
)
from google.cloud.firestore_v1 import ArrayUnion, Increment, SERVER_TIMESTAMP
from dotenv import load_dotenv

# Global variables
db = None
bucket = None
GOOGLE_AI_API_KEY = None
GOOGLE_MAPS_API_KEY = None
GMAIL_ADDRESS = None
GMAIL_APP_PASSWORD = None
model = None
image_model = None

def create_app():
    """Create and configure the Flask application."""
    global db, bucket, GOOGLE_AI_API_KEY, GOOGLE_MAPS_API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, model, image_model
    
    # --- FLASK APP INITIALIZATION ---
    app = Flask(__name__)
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Configure app
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    
    # Initialize Firebase
    db, bucket = initialize_firebase()
    
    # Initialize Google AI
    GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
    
    # Configure the Gemini API client
    if GOOGLE_AI_API_KEY:
        genai.configure(api_key=GOOGLE_AI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        image_model = genai.GenerativeModel('gemini-1.5-flash-image-preview')
    else:
        print("Google AI API Key not found. AI features will be disabled.")
    
    # Register blueprints and routes
    register_blueprints(app)
    register_routes(app)
    
    # Add context processor for Firebase config
    @app.context_processor
    def inject_firebase_config():
        return dict(firebase_config_json=json.dumps({
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": os.getenv("FIREBASE_APP_ID")
        }))
    
    return app

def initialize_firebase():
    """Initialize Firebase services and return db and bucket."""
    # Initialize Firebase Admin SDK if not already initialized
    if not firebase_admin._apps:
        # Get the credentials from the environment variable
        firebase_creds_json_str = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        
        if firebase_creds_json_str:
            # On Vercel: load credentials from the environment variable
            creds_dict = json.loads(firebase_creds_json_str)
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
            })
        else:
            # Locally: fallback to using the file
            cred_path = "firebase-service-account-key.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
                })
            else:
                print("CRITICAL ERROR: Firebase service account key not found in file or environment variable.")
    
    # Initialize Firestore and Storage
    db = firestore.client()
    bucket = storage.bucket()
    
    return db, bucket

def register_blueprints(app):
    """Register Flask blueprints."""
    # Import and register blueprints here if you have any
    # from .routes import main_bp
    # app.register_blueprint(main_bp)
    pass

def register_routes(app):
    """Register all the routes for the application."""
    # Import and register routes here
    from functools import wraps
    
    # --- AUTHENTICATION DECORATORS ---
    
    def login_required(f):
        """Require user to be logged in."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login_page', next=request.url))
            return f(*args, **kwargs)
        return decorated_function
        
    def buyer_required(f):
        """Require user to be logged in as a buyer."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login_page', next=request.url))
            if session.get('user_type') != 'buyer':
                flash('This page is only available to buyers.', 'error')
                return redirect(url_for('marketplace'))
            return f(*args, **kwargs)
        return decorated_function
        
    def artisan_required(f):
        """Require user to be logged in as an artisan."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login_page', next=request.url))
            if session.get('user_type') != 'artisan':
                flash('This page is only available to artisans.', 'error')
                return redirect(url_for('marketplace'))
            return f(*args, **kwargs)
        return decorated_function
        
    def admin_required(f):
        """Require user to be logged in as an admin."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login_page', next=request.url))
                
            # Check if user is admin
            user_doc = db.collection('users').document(session['user_id']).get()
            if not user_doc.exists or user_doc.to_dict().get('role') != 'admin':
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('marketplace'))
                
            return f(*args, **kwargs)
        return decorated_function
    
    # --- HELPER FUNCTIONS ---
    def send_email(to_address, subject, body):
        if not all([GMAIL_ADDRESS, GMAIL_APP_PASSWORD]):
            print("Email credentials not set. Skipping email sending.")
            return
        try:
            msg = MIMEText(body, 'html')
            msg['Subject'] = subject
            msg['From'] = GMAIL_ADDRESS
            msg['To'] = to_address

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
                smtp_server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                smtp_server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())
            print(f"Email sent to {to_address}")
        except Exception as e:
            print(f"Error sending email: {e}")
    
    # Store helpers in app context
    app.send_email = send_email
    
    # --- ROUTES ---
    @app.route('/')
    def index():
        return redirect(url_for('marketplace'))
    
    @app.route('/marketplace')
    def marketplace():
        # Your marketplace logic here
        return render_template('marketplace.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login_page():
        if request.method == 'POST':
            # Handle login form submission
            return redirect(url_for('marketplace'))
        return render_template('auth/login.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register_page():
        if request.method == 'POST':
            # Handle registration form submission
            return redirect(url_for('login_page'))
        return render_template('auth/register.html')
    
    @app.route('/auth/firebase', methods=['POST'])
    def firebase_login():
        data = request.get_json()
        id_token = data.get('idToken')
        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
            uid = decoded_token['uid']
            user_doc = db.collection('users').document(uid).get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                session['user_id'] = uid
                session['user_type'] = user_data.get('type')
                session['user_name'] = user_data.get('name')
            else:
                user_info = firebase_auth.get_user(uid)
                new_user_data = {
                    'id': uid, 'name': 'New User', 'email': user_info.email or '', 'phone': user_info.phone_number,
                    'type': 'buyer',
                    'avatar': user_info.photo_url or f'https://placehold.co/100x100/E2E8F0/4A5568?text=NU',
                    'shipping_address': '', 'cart': []
                }
                db.collection('users').document(uid).set(new_user_data)
                session['user_id'] = uid
                session['user_type'] = 'buyer'
                session['user_name'] = 'New User'
                flash('Welcome! Please complete your profile.', 'success')

            user_data = db.collection('users').document(uid).get().to_dict()
            session['cart'] = user_data.get('cart', [])
            return jsonify({"status": "success"}), 200
        except Exception as e:
            print(f"Firebase login error: {e}")
            return jsonify({"error": str(e)}), 401

    @app.route('/register/firestore', methods=['POST'])
    def register_firestore():
        data = request.get_json()
        uid = data.get('uid')
        user_data = {
            'id': uid, 'name': data.get('name'), 'email': data.get('email'), 
            'phone': data.get('phone'), 'type': data.get('type'),
            'avatar': f'https://placehold.co/100x100/E2E8F0/4A5568?text={data.get("name")[0:2].upper()}',
            'cart': [], 'settings': {}
        }
        if data.get('type') == 'artisan':
            user_data.update({
                'craft': data.get('craft'), 'location': data.get('location'),
                'coords': {'lat': 20.5937, 'lng': 78.9629}, 'verification_status': 'pending'
            })
        else:
            user_data['shipping_address'] = data.get('shipping_address')
        db.collection('users').document(uid).set(user_data)
        return jsonify({"status": "success"}), 201

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been successfully logged out.', 'success')
        return redirect(url_for('login_page'))
    
    # --- CART & ORDER ROUTES (BUYER) ---
    @app.route('/cart')
    @login_required
    def cart_page():
        cart_product_ids = session.get('cart', [])
        cart_items = []
        total = 0
        if cart_product_ids:
            for product_id in cart_product_ids:
                product_doc = db.collection('products').document(product_id).get()
                if product_doc.exists:
                    item = product_doc.to_dict()
                    artisan_doc = db.collection('users').document(item['artisanId']).get()
                    item['artisan'] = artisan_doc.to_dict() if artisan_doc.exists else {}
                    cart_items.append(item)
                    total += item['price']
        return render_template('buyer/cart.html', cart_items=cart_items, total=total)
    
    @app.route('/cart/add/<product_id>')
    @login_required
    def add_to_cart(product_id):
        user_ref = db.collection('users').document(session['user_id'])
        user_ref.update({'cart': firestore.ArrayUnion([product_id])})
        if product_id not in session.get('cart', []):
            session['cart'].append(product_id)
            session.modified = True
        flash('Product added to cart!', 'success')
        return redirect(url_for('marketplace'))
    
    @app.route('/cart/remove/<product_id>')
    @login_required
    def remove_from_cart(product_id):
        user_ref = db.collection('users').document(session['user_id'])
        user_ref.update({'cart': firestore.ArrayRemove([product_id])})
        if 'cart' in session and product_id in session['cart']:
            session['cart'].remove(product_id)
            session.modified = True
        flash('Product removed from cart.', 'success')
        return redirect(url_for('cart_page'))
    
    @app.route('/checkout')
    @login_required
    def checkout_page():
        if session.get('user_type') != 'buyer':
            flash('Only buyers can access the checkout page.', 'warning')
            return redirect(url_for('marketplace'))
            
        cart_product_ids = session.get('cart', [])
        cart_items = []
        total = 0
        if cart_product_ids:
            for product_id in cart_product_ids:
                product_doc = db.collection('products').document(product_id).get()
                if product_doc.exists:
                    item = product_doc.to_dict()
                    artisan_doc = db.collection('users').document(item['artisanId']).get()
                    item['artisan'] = artisan_doc.to_dict() if artisan_doc.exists else {}
                    cart_items.append(item)
                    total += item['price']
        buyer_doc = db.collection('users').document(session['user_id']).get()
        buyer = buyer_doc.to_dict()
        return render_template('buyer/checkout.html', cart_items=cart_items, total=total, buyer=buyer)
    
    @app.route('/confirm_order', methods=['POST'])
    @login_required
    def confirm_order():
        if session.get('user_type') != 'buyer':
            return redirect(url_for('marketplace'))
            
        cart_product_ids = session.get('cart', [])
        if not cart_product_ids:
            flash('Your cart is empty.', 'warning')
            return redirect(url_for('cart_page'))
            
        buyer_doc = db.collection('users').document(session['user_id']).get()
        buyer = buyer_doc.to_dict()
        
        for product_id in cart_product_ids:
            product_doc = db.collection('products').document(product_id).get()
            if product_doc.exists:
                product = product_doc.to_dict()
                order_id = str(uuid.uuid4())
                order_data = {
                    'id': order_id, 
                    'buyerId': session['user_id'], 
                    'artisanId': product['artisanId'],
                    'productId': product_id, 
                    'status': 'Packaging', 
                    'orderDate': datetime.utcnow()
                }
                db.collection('orders').document(order_id).set(order_data)
                
                # Send email notifications
                artisan_doc = db.collection('users').document(product['artisanId']).get()
                artisan = artisan_doc.to_dict()
                
                if buyer.get('email'):
                    app.send_email(
                        buyer['email'],
                        f"Your Artisan AI Order #{order_id[:8]} is Confirmed!",
                        f"Hi {buyer.get('name', 'Customer')},<br><br>Your order for '{product['name']}' has been placed successfully! You can track its status on your 'My Orders' page."
                    )
                
                if artisan.get('email') and artisan.get('settings', {}).get('order_emails', False):
                    app.send_email(
                        artisan['email'],
                        f"New Sale on Artisan AI! Order #{order_id[:8]}",
                        f"Hi {artisan.get('name', 'Artisan')},<br><br>You have a new order for '{product['name']}'. Please visit your dashboard to manage the order."
                    )
        
        # Clear cart after successful order
        db.collection('users').document(session['user_id']).update({'cart': []})
        session['cart'] = []
        flash('Your order has been placed successfully!', 'success')
        return redirect(url_for('my_orders'))
    
    @app.route('/my_orders')
    @login_required
    def my_orders():
        if session.get('user_type') != 'buyer':
            flash('Only buyers can view orders.', 'warning')
            return redirect(url_for('marketplace'))
            
        orders_ref = db.collection('orders').where('buyerId', '==', session['user_id']).stream()
        orders_list = []
        for order_doc in orders_ref:
            order = order_doc.to_dict()
            product_doc = db.collection('products').document(order['productId']).get()
            order['product'] = product_doc.to_dict() if product_doc.exists else {}
            artisan_doc = db.collection('users').document(order['artisanId']).get()
            order['artisan'] = artisan_doc.to_dict() if artisan_doc.exists else {}
            orders_list.append(order)
        return render_template('buyer/my_orders.html', orders=orders_list)

    # --- ARTISAN HUB & TOOLS ROUTES ---
    @app.route('/hub')
    @login_required
    def hub():
        if session.get('user_type') != 'artisan':
            flash('Only artisans can access the hub.', 'warning')
            return redirect(url_for('marketplace'))
            
        artisan_doc = db.collection('users').document(session['user_id']).get()
        artisan = artisan_doc.to_dict()
        
        if artisan.get('verification_status') != 'verified':
            return render_template('artisan/verification.html', artisan=artisan)
        return render_template('artisan/hub.html', artisan=artisan)

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if session.get('user_type') != 'artisan':
            flash('Only artisans can access the dashboard.', 'warning')
            return redirect(url_for('marketplace'))
            
        artisan_doc = db.collection('users').document(session['user_id']).get()
        artisan = artisan_doc.to_dict()
        
        if artisan.get('verification_status') != 'verified':
            return render_template('artisan/verification.html', artisan=artisan)
        
        active_tab = request.args.get('tab', 'tools')
        
        # Fetch products for the sidebar and products tab
        products_ref = db.collection('products').where('artisanId', '==', session['user_id']).stream()
        artisan_products = [p.to_dict() for p in products_ref]
        
        products_json = json.dumps({p['id']: p for p in artisan_products}) if active_tab == 'tools' else '{}'

        return render_template('artisan/dashboard.html', 
                             artisan=artisan, 
                             active_tab=active_tab,
                             artisan_products=artisan_products, 
                             products_json=products_json)

    @app.route('/add_product', methods=['POST'])
    @login_required
    def add_product():
        if session.get('user_type') != 'artisan':
            flash('Only artisans can add products.', 'warning')
            return redirect(url_for('marketplace'))
            
        artisan_doc = db.collection('users').document(session['user_id']).get()
        artisan = artisan_doc.to_dict()
        
        product_id = str(uuid.uuid4())
        product_data = {
            'id': product_id, 
            'name': request.form['name'], 
            'price': float(request.form['price']),
            'stock': int(request.form['stock']), 
            'dimensions': request.form['dimensions'],
            'materials': request.form['materials'], 
            'imageUrl': request.form['imageUrl'],
            'description': request.form['description'], 
            'artisanId': session['user_id'],
            'ai_description': ''
        }
        
        # Generate AI description if API key is available
        if GOOGLE_AI_API_KEY and model:
            try:
                prompt = f"""
                An artisan named {artisan.get('name', 'a local artisan')} from {artisan.get('location', 'India')} 
                who specializes in {artisan.get('craft', 'traditional crafts')} has created a new product.
                
                Product Name: "{product_data['name']}"
                Materials Used: "{product_data['materials']}"
                Artisan's Description: "{product_data['description']}"
                
                Write an engaging, single-paragraph product description that highlights the craftsmanship, 
                materials, and cultural significance. The tone should be warm and inviting, perfect for 
                an e-commerce website. Focus on the unique aspects of this handmade item.
                """
                response = model.generate_content(prompt)
                product_data['ai_description'] = response.text
            except Exception as e:
                print(f"AI description generation failed: {e}")
                product_data['ai_description'] = product_data['description']
        else:
            product_data['ai_description'] = product_data['description']
        
        db.collection('products').document(product_id).set(product_data)
        flash('New product added successfully!', 'success')
        return redirect(url_for('dashboard', tab='products'))

    @app.route('/generate_ai_story/<product_id>', methods=['POST'])
    @login_required
    def generate_ai_story(product_id):
        if session.get('user_type') != 'artisan':
            return jsonify({'error': 'Only artisans can generate AI stories.'}), 403
            
        if not GOOGLE_AI_API_KEY or not model:
            return jsonify({'error': 'AI features are not available.'}), 503
            
        try:
            product_ref = db.collection('products').document(product_id)
            product_doc = product_ref.get()
            
            if not product_doc.exists:
                return jsonify({'error': 'Product not found'}), 404
                
            product = product_doc.to_dict()
            
            # Verify the product belongs to the current artisan
            if product.get('artisanId') != session['user_id']:
                return jsonify({'error': 'Unauthorized access to product'}), 403
            
            artisan = db.collection('users').document(session['user_id']).get().to_dict()
            
            prompt = f"""
            An artisan named {artisan.get('name', 'a local artisan')} from {artisan.get('location', 'India')} 
            who specializes in {artisan.get('craft', 'traditional crafts')} has created a product.
            
            Product: "{product['name']}"
            Materials: "{product.get('materials', 'various materials')}"
            Description: "{product.get('description', '')}"
            
            Write a compelling, single-paragraph product story that captures the essence of this handmade item. 
            Focus on the craftsmanship, cultural significance, and the artisan's unique touch. The tone should be 
            warm, engaging, and perfect for an e-commerce product page. Avoid using headings or markdown.
            """
            
            response = model.generate_content(prompt)
            ai_story = response.text
            
            # Update the product with the new AI-generated story
            product_ref.update({'ai_description': ai_story})
            
            return jsonify({
                'success': True, 
                'ai_story': ai_story,
                'message': 'AI story generated successfully!'
            })
            
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg:
                return jsonify({
                    'error': 'AI service quota exceeded. Please try again later.',
                    'details': str(e)
                }), 429  # Too Many Requests
def update_order_status():
    if session.get('user_type') != 'artisan':
        return jsonify({'error': 'Only artisans can update order status.'}), 403
        
    try:
        order_id = request.form.get('order_id')
        new_status = request.form.get('status')
        
        if not order_id or not new_status:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get the order and verify ownership
        order_ref = db.collection('orders').document(order_id)
        order_doc = order_ref.get()
        
        if not order_doc.exists:
            return jsonify({'error': 'Order not found'}), 404
            
        order = order_doc.to_dict()
        
        # Verify the order belongs to this artisan
        if order.get('artisanId') != session['user_id']:
            return jsonify({'error': 'Unauthorized access to order'}), 403
        
        # Update the order status
        order_ref.update({'status': new_status})
        
        # Get buyer info for notification
        buyer_doc = db.collection('users').document(order['buyerId']).get()
        if buyer_doc.exists:
            buyer = buyer_doc.to_dict()
            # Send email notification to buyer
            if buyer.get('email'):
                product_doc = db.collection('products').document(order['productId']).get()
                product_name = product_doc.get('name') if product_doc.exists else 'your order'
                
                app.send_email(
                    buyer['email'],
                    f'Order #{order_id[:8]} Status Update',
                    f"""
                    <p>Dear {buyer.get('name', 'Customer')},</p>
                    <p>The status of your order for <strong>{product_name}</strong> has been updated to: 
                    <strong>{new_status}</strong>.</p>
                    <p>You can view the latest status in your <a href='{url_for('my_orders', _external=True)}'>Orders</a> page.</p>
                    <p>Thank you for shopping with us!</p>
                    <p>— The Artisan AI Team</p>
                    """
                )
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {new_status}'
        })
        
    except Exception as e:
        print(f"Error updating order status: {e}")
        return jsonify({
            'error': 'An error occurred while updating the order status.',
            'details': str(e)
        }), 500
        buyer_doc = db.collection('users').document(order_data['buyerId']).get()
        buyer = buyer_doc.to_dict()
        product_doc = db.collection('products').document(order_data['productId']).get()
        product = product_doc.to_dict()
        if buyer.get('email'):
            send_email(buyer['email'], f"Your Artisan AI Order #{order_id[:8]} has Shipped!", f"Hi {buyer['name']},<br><br>Good news! Your order for '{product['name']}' has been shipped.")
    flash('Order status updated.', 'success')
    return redirect(url_for('dashboard', tab='orders'))

# --- AI TOOL ROUTES (ARTISAN & BUYER) ---

@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    user_message = data.get('message', '')
    image_data = data.get('image_data')
    try:
        if user_message.lower().strip().startswith('/imagine'):
            prompt = user_message.replace('/imagine', '').strip()
            if not prompt:
                 return jsonify({'reply_type': 'text', 'reply_content': '<p>Please provide a description for the image you want to create. For example: <code>/imagine a rustic wooden bowl filled with spices</code></p>'})
            response = image_model.generate_content(prompt)
            image_url = response.candidates[0].content.parts[0].uri
            return jsonify({'reply_type': 'image', 'reply_content': image_url})
        prompt = f"You are a helpful AI assistant for an artisan on an e-commerce platform. The user's question is: '{user_message}'. Provide a concise, helpful, and encouraging answer in Markdown format."
        if image_data:
            image_part = {"mime_type": "image/jpeg", "data": image_data}
            prompt = f"You are a helpful AI assistant for an artisan. Analyze the provided image and the user's question. The question is: '{user_message}'. Provide a helpful, encouraging critique or answer in Markdown format."
            response = model.generate_content([prompt, image_part])
        else:
            response = model.generate_content(prompt)
        reply_html = markdown.markdown(response.text)
        return jsonify({'reply_type': 'text', 'reply_content': reply_html})
    except Exception as e:
        print(f"AI Chat Error: {e}")
        return jsonify({'reply_type': 'text', 'reply_content': f"<p>Sorry, I encountered an error. It might be due to API limits. Please try again later.</p>"})

@app.route('/generate', methods=['POST'])
def generate():
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    product_doc = db.collection('products').document(data['product_id']).get()
    if not product_doc.exists:
        return jsonify({'result_html': 'Product not found.'}), 404
    product = product_doc.to_dict()
    artisan_doc = db.collection('users').document(product['artisanId']).get()
    artisan = artisan_doc.to_dict()
    try:
        if data['tool'] == 'vision':
            if not data.get('image_data'):
                return jsonify({'result_html': 'Please upload an image for analysis.'}), 400
            image_part = {"mime_type": "image/jpeg", "data": data['image_data']}
            prompt = f"""Act as a world-class product photography consultant. Analyze this image of a "{product['name']}". Provide your response in Markdown format. Give a professional critique with 3 actionable improvements as a numbered list under the heading '### Photography Feedback'. Then, under a second heading '### AI Photo Prompt', write a detailed prompt for an AI image generator to create the PERFECT photo for this product."""
            response = model.generate_content([prompt, image_part])
            result_html = markdown.markdown(response.text)
            return jsonify({'result_html': result_html})
        elif data['tool'] == 'story':
            prompt = f"""Generate a compelling, SEO-friendly product description for: "{product['name']}". It's a piece of {artisan.get('craft', '')} from {artisan.get('location', '')}, made of {product.get('materials', '')}. Provide the response in Markdown. Start with a title as a H2 heading. Follow with a short, bolded, emotional tagline. Then, write 2-3 paragraphs weaving a story about its heritage. Finally, under a H3 heading 'Keywords', provide a comma-separated list of 5 relevant SEO keywords."""
            response = model.generate_content(prompt)
            result_html = markdown.markdown(response.text)
            return jsonify({'result_html': result_html})
        elif data['tool'] == 'photo':
            prompt = f"Create a beautiful, professional lifestyle photograph of a handcrafted '{product['name']}'. It is made of {product['materials']}. The photo should be in a bright, airy setting that feels authentic and high-end. The product should be the clear focus."
            response = image_model.generate_content(prompt)
            image_url = response.candidates[0].content.parts[0].uri
            return jsonify({'image_url': image_url})
    except Exception as e:
        print(f"Error in /generate route: {e}")
        return jsonify({'result_html': f"An error occurred. It might be due to API limits. Please try again later."}), 500

@app.route('/brand_kit', methods=['GET'])
def brand_kit_page():
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return redirect(url_for('login_page'))
    return render_template('artisan/brand_kit_generator.html')

@app.route('/brand_kit/generate', methods=['POST'])
def generate_brand_kit():
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return redirect(url_for('login_page'))
    artisan_doc = db.collection('users').document(session['user_id']).get()
    artisan = artisan_doc.to_dict()
    story = request.form['story']
    values = request.form['values']
    prompt = f"""
    Act as a world-class branding expert for a local artisan.
    The artisan's craft is: {artisan.get('craft', 'not specified')}.
    Their story is: "{story}". Their core values are: "{values}".
    Based ONLY on this information, generate a complete Brand Kit in JSON format. The JSON object must have exactly these three keys: "logo_concept", "brand_voice", "color_palette".
    1. "logo_concept": A one-sentence, descriptive concept for a simple, meaningful logo. Use Markdown for bolding.
    2. "brand_voice": An object with three keys: "name" (a one-word summary like "Authentic"), "description" (a one-sentence explanation), and "example" (a sample tagline).
    3. "color_palette": An array of exactly four objects, each with a "name" (e.g., "Terracotta Clay") and its corresponding "hex" code.
    Do not include any introductory text or markdown formatting. The output must be only the raw JSON.
    """
    try:
        response = model.generate_content(prompt)
        clean_json_string = response.text.strip().replace('```json', '').replace('```', '')
        brand_kit_data = json.loads(clean_json_string)
        brand_kit_data['logo_concept'] = markdown.markdown(brand_kit_data.get('logo_concept', ''))
        if 'brand_voice' in brand_kit_data and 'description' in brand_kit_data['brand_voice']:
            brand_kit_data['brand_voice']['description'] = markdown.markdown(brand_kit_data['brand_voice'].get('description', ''))
        db.collection('users').document(session['user_id']).set({'brand_kit': brand_kit_data}, merge=True)
        return render_template('artisan/brand_kit_result.html', brand_kit=brand_kit_data)
    except Exception as e:
        flash(f"An AI error occurred: {e}", "error")
        return redirect(url_for('brand_kit_page'))

@app.route('/product_chat', methods=['POST'])
def product_chat():
    data = request.get_json()
    user_message = data['message']
    product_id = data['product_id']
    product_doc = db.collection('products').document(product_id).get()
    if not product_doc.exists:
        return jsonify({'reply_html': '<p>Sorry, I cannot find details for this product.</p>'})
    product = product_doc.to_dict()
    artisan_doc = db.collection('users').document(product['artisanId']).get()
    artisan = artisan_doc.to_dict()
    prompt = f"""
    You are a friendly and helpful shopping assistant chatbot on an e-commerce page for a specific handcrafted product.
    Your goal is to answer the potential buyer's questions based ONLY on the detailed information provided below.
    Do not make up information. If the answer isn't in the details, say "I don't have that specific information, but it's a lovely piece crafted by {artisan.get('name')}."

    PRODUCT DETAILS:
    - Name: {product.get('name')}
    - Artisan: {artisan.get('name')} from {artisan.get('location')}
    - Craft: {artisan.get('craft')}
    - Materials: {product.get('materials')}
    - Dimensions: {product.get('dimensions')}
    - Price: ₹{product.get('price')}
    - Stock: {product.get('stock')} available
    - Artisan's Description: {product.get('description')}
    - AI-Generated Story: {product.get('ai_description')}

    The buyer's question is: "{user_message}"

    Answer the question in a concise and friendly manner using Markdown.
    """
    try:
        response = model.generate_content(prompt)
        reply_html = markdown.markdown(response.text)
        return jsonify({'reply_html': reply_html})
    except Exception as e:
        print(f"Product chat error: {e}")
        return jsonify({'reply_html': '<p>Sorry, I had a little trouble thinking of a reply. Please try again.</p>'})

    # --- TRENDS & COMMUNITY SCOUTING ROUTES ---
    @app.route('/trends')
    @login_required
    def trends_page():
        if session.get('user_type') != 'artisan':
            flash('Only artisans can access market trends.', 'warning')
            return redirect(url_for('marketplace'))
            
        artisan_doc = db.collection('users').document(session['user_id']).get()
        artisan = artisan_doc.to_dict()
        return render_template('artisan/trends_generator.html', artisan=artisan)

    @app.route('/trends/generate', methods=['POST'])
    @login_required
    def generate_trends():
        if session.get('user_type') != 'artisan':
            return redirect(url_for('marketplace'))
            
        craft_category = request.form.get('craft_category', '').strip()
        if not craft_category:
            flash('Please specify a craft category.', 'error')
            return redirect(url_for('trends_page'))
            
        try:
            prompt = f"""
            Act as a senior e-commerce market trend analyst for Indian handicrafts. The artisan's craft is '{craft_category}'.
            Provide a detailed market trend report in Markdown format. The report must include the following sections:
            ### Emerging Style Trends
            - A bulleted list of 3-4 current style trends relevant to '{craft_category}'.
            ### Popular Color Palettes
            - A bulleted list of 2-3 trending color palettes. For each, describe the feel and provide example hex codes.
            ### New Product Ideas
            - A bulleted list of 3 innovative product ideas based on these trends that a '{craft_category}' artisan could create.
            ### Marketing Angle
            - A short paragraph suggesting how to market products based on these trends.
            """
            response = model.generate_content(prompt)
            trend_report_html = markdown.markdown(response.text)
            return render_template('artisan/trends_result.html', 
                                craft_category=craft_category, 
                                trend_report=trend_report_html)
                                
        except Exception as e:
            print(f"Error generating trends: {e}")
            flash('An error occurred while generating trends. Please try again later.', 'error')
            return redirect(url_for('trends_page'))

    # --- COMMUNITY SCOUTING ROUTES ---
    @app.route('/scout/submit', methods=['POST'])
    @login_required
    def submit_scout_verification():
        if 'workshop_photo' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('profile'))
            
        buyer_id = session['user_id']
        artisan_id = request.form.get('artisan_id')
        photo = request.files['workshop_photo']
        
        if not artisan_id:
            flash('Invalid artisan ID', 'error')
            return redirect(url_for('profile'))
            
        if photo.filename == '':
            flash('Please select a file to upload', 'error')
            return redirect(url_for('profile'))
            
        try:
            # Generate a unique filename and upload to Firebase Storage
            filename = f"scout_verification/{artisan_id}/scout_{buyer_id}_{uuid.uuid4()}_{secure_filename(photo.filename)}"
            blob = bucket.blob(filename)
            blob.upload_from_file(photo, content_type=photo.content_type)
            blob.make_public()
            
            # Update artisan's document with the new submission
            db.collection('users').document(artisan_id).set({
                'scout_submissions': firestore.ArrayUnion([{
                    'buyerId': buyer_id, 
                    'photoUrl': blob.public_url, 
                    'date': datetime.utcnow(),
                    'status': 'pending'
                }])
            }, merge=True)
            
            flash('Thank you for being a Community Scout! Your submission is under review.', 'success')
            
        except Exception as e:
            print(f"Error submitting scout verification: {e}")
            flash('An error occurred while submitting your verification. Please try again.', 'error')
            
        return redirect(url_for('profile'))

    # --- ADMIN ROUTES ---
    # --- ADMIN ROUTES ---
    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        """Admin dashboard showing key metrics and actions."""
        try:
            # Get pending verifications count
            pending_query = db.collection('users')
            pending_query = pending_query.where('type', '==', 'artisan')
            pending_query = pending_query.where('verification_status', 'in', ['pending', 'submitted'])
            pending_count = len(list(pending_query.stream()))
            
            # Get recent orders
            orders_query = db.collection('orders')
            orders_query = orders_query.order_by('orderDate', direction='DESCENDING')
            orders_query = orders_query.limit(10)
            recent_orders = [order.to_dict() for order in orders_query.stream()]
            
            # Get user stats
            user_stats = {
                'total': len(list(db.collection('users').stream())),
                'artisans': len(list(db.collection('users').where('type', '==', 'artisan').stream())),
                'buyers': len(list(db.collection('users').where('type', '==', 'buyer').stream())),
                'pending_verification': pending_count
            }
            
            return render_template('admin/dashboard.html',
                                user_stats=user_stats,
                                recent_orders=recent_orders)
                                
        except Exception as e:
            print(f"Error loading admin dashboard: {e}")
            flash('An error occurred while loading the admin dashboard.', 'error')
            return redirect(url_for('marketplace'))
    
    @app.route('/admin/verify')
    @admin_required
    def admin_verify():
        """View and manage artisan verification requests."""
        try:
            # Get all artisans pending verification
            query = db.collection('users')
            query = query.where('type', '==', 'artisan')
            query = query.where('verification_status', 'in', ['pending', 'submitted'])
            artisans_ref = query.stream()
                
            pending_artisans = []
            for artisan in artisans_ref:
                artisan_data = artisan.to_dict()
                artisan_data['id'] = artisan.id
                
                # Get verification documents
                verification_docs = artisan_data.get('verification_docs', {})
                artisan_data['has_documents'] = bool(
                    verification_docs.get('identity_proof') or 
                    verification_docs.get('business_proof') or 
                    verification_docs.get('work_proof')
                )
                
                pending_artisans.append(artisan_data)
                
            return render_template('admin/verify.html', artisans=pending_artisans)
            
        except Exception as e:
            print(f"Error loading verification page: {e}")
            flash('An error occurred while loading verification requests.', 'error')
            return redirect(url_for('admin_dashboard'))

    @app.route('/admin/approve/<uid>')
    @admin_required
    def admin_approve(uid):
        """Approve an artisan's verification request."""
        try:
            artisan_ref = db.collection('users').document(uid)
            artisan_doc = artisan_ref.get()
            
            if not artisan_doc.exists:
                flash('Artisan not found', 'error')
                return redirect(url_for('admin_verify'))
                
            artisan_data = artisan_doc.to_dict()
            
            # Update artisan's verification status
            updates = {
                'verification_status': 'verified',
                'verified_at': datetime.utcnow(),
                'is_active': True
            }
            
            # If this is their first verification, set their shop as active
            if not artisan_data.get('verified_at'):
                updates['shop_active'] = True
                
                # Reward scouts who verified this artisan
                if 'scout_submissions' in artisan_data:
                    updated_submissions = []
                    for submission in artisan_data['scout_submissions']:
                        if submission.get('status') == 'pending':
                            # Reward the scout
                            buyer_ref = db.collection('users').document(submission['buyerId'])
                            buyer_ref.set({
                                'reward_balance': firestore.Increment(50),
                                'last_rewarded': datetime.utcnow()
                            }, merge=True)
                            
                            # Mark submission as rewarded
                            submission['status'] = 'rewarded'
                            submission['rewarded_at'] = datetime.utcnow()
                        updated_submissions.append(submission)
                    
                    updates['scout_submissions'] = updated_submissions
            
            # Apply all updates
            artisan_ref.update(updates)
            
            # Send notification to artisan
            if artisan_data.get('email'):
                app.send_email(
                    artisan_data['email'],
                    'Your Artisan Profile is Verified!',
                    f"""
                    <p>Congratulations {artisan_data.get('name', 'Artisan')}!</p>
                    <p>Your artisan profile has been successfully verified. You can now access all artisan features.</p>
                    <p>Start by setting up your shop and adding your products.</p>
                    <p>— The Artisan AI Team</p>
                    """
                )
            
            flash(f"Artisan {artisan_data.get('name', '')} has been approved and verified!", "success")
            
        except Exception as e:
            print(f"Error approving artisan: {e}")
            flash('An error occurred while approving the artisan.', 'error')
            
        return redirect(url_for('admin_verify'))

    @app.route('/admin/reject/<uid>', methods=['POST'])
    @admin_required
    def admin_reject(uid):
        """Reject an artisan's verification request."""
        try:
            reason = request.form.get('reason', 'Verification requirements not met.')
            
            # Update artisan's status
            updates = {
                'verification_status': 'rejected',
                'verification_reviewed_at': datetime.utcnow(),
                'verification_notes': reason
            }
            
            db.collection('users').document(uid).update(updates)
            
            # Get artisan data for notification
            artisan_doc = db.collection('users').document(uid).get()
            if artisan_doc.exists:
                artisan_data = artisan_doc.to_dict()
                
                # Send notification to artisan
                if artisan_data.get('email'):
                    app.send_email(
                        artisan_data['email'],
                        'Verification Request Update',
                        f"""
                        <p>Dear {artisan_data.get('name', 'Artisan')},</p>
                        <p>Your verification request has been reviewed but unfortunately we couldn't approve it at this time.</p>
                        <p><strong>Reason:</strong> {reason}</p>
                        <p>You may submit a new verification request after addressing the issues mentioned above.</p>
                        <p>If you believe this is a mistake, please contact our support team.</p>
                        <p>— The Artisan AI Team</p>
                        """
                    )
            
            flash("Artisan verification has been rejected.", "warning")
            
        except Exception as e:
            print(f"Error rejecting artisan: {e}")
            flash('An error occurred while rejecting the verification.', 'error')
            
        return redirect(url_for('admin_verify'))

# --- APP EXECUTION ---

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    port = int(os.getenv('PORT', 5000))
    if os.getenv('USE_NGROK', 'False').lower() in ['true', '1', 't']:
        ngrok_token = os.getenv('NGROK_AUTH_TOKEN')
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)
            public_url = ngrok.connect(port)
            print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\"")
        else:
            print(" * NGROK_AUTH_TOKEN not found, ngrok tunnel disabled.")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)


