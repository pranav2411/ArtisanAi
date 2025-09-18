import os
import json
import uuid
from datetime import datetime
import google.generativeai as genai
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from pyngrok import ngrok
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth as firebase_auth
import markdown
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- FLASK APP INITIALIZATION ---
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# --- SERVICE ACCOUNT INITIALIZATION ---
# --- SERVICE ACCOUNT INITIALIZATION ---
if not firebase_admin._apps:
    # Get the credentials from the environment variable
    firebase_creds_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
    
    if firebase_creds_json:
        # Convert the JSON string from the env var into a dictionary
        creds_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
        })
    else:
        # Fallback for local development (using the file)
        cred_path = "firebase-service-account-key.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
            })
        else:
            print("Firebase service account key not found in file or environment variable.")

db = firestore.client()
bucket = storage.bucket()
# --- API KEY & EMAIL CONFIGURATION ---
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


# --- YOUR WEB APP'S FIREBASE CONFIGURATION (FOR FRONT-END JS) ---
FIREBASE_CONFIG_JSON = json.dumps({
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID")
})

# Pass the config to all templates
@app.context_processor
def inject_firebase_config():
    return dict(firebase_config_json=FIREBASE_CONFIG_JSON)


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


# --- AUTHENTICATION ROUTES ---

@app.route('/auth/firebase', methods=['POST'])
def firebase_login():
    data = request.get_json()
    id_token = data.get('idToken')
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        user_doc = db.collection('users').document(uid).get()

        # If the user document already exists in Firestore, log them in
        if user_doc.exists:
            user_data = user_doc.to_dict()
            session['user_id'] = uid
            session['user_type'] = user_data.get('type')
            session['user_name'] = user_data.get('name')
        # If the user is new (exists in Firebase Auth but not Firestore)
        else:
            user_info = firebase_auth.get_user(uid)
            # Create a default buyer profile for the new user
            new_user_data = {
                'id': uid, 
                'name': 'New User', 
                'email': user_info.email or '', 
                'phone': user_info.phone_number,
                'type': 'buyer',
                'avatar': user_info.photo_url or f'https://placehold.co/100x100/E2E8F0/4A5568?text=NU',
                'shipping_address': '', 
                'cart': []
            }
            db.collection('users').document(uid).set(new_user_data)
            
            # Log them into the session
            session['user_id'] = uid
            session['user_type'] = 'buyer'
            session['user_name'] = 'New User'
            flash('Welcome! Please complete your profile.', 'success')

        # For both new and existing users, update the session cart
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
        'id': uid, 'name': data.get('name'), 'email': data.get('email'), 'phone': data.get('phone'), 'type': data.get('type'),
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

# --- GENERAL & MAIN PAGE ROUTES ---

@app.route('/')
def marketplace():
    products_ref = db.collection('products').stream()
    users_ref = db.collection('users').stream()
    products = []
    users = {u.id: u.to_dict() for u in users_ref}
    for p in products_ref:
        product_data = p.to_dict()
        artisan_id = product_data.get('artisanId')
        if artisan_id in users and users[artisan_id].get('verification_status') == 'verified':
            products.append(product_data)
    artisans_for_map = {k: v for k, v in users.items() if v.get('type') == 'artisan' and v.get('verification_status') == 'verified' and 'coords' in v}
    artisans_json = json.dumps(artisans_for_map)
    return render_template('marketplace.html', users=users, products=products, artisans_json=artisans_json, maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/product/<product_id>')
def product_page(product_id):
    product_doc = db.collection('products').document(product_id).get()
    if not product_doc.exists: return 'Product not found', 404
    product = product_doc.to_dict()
    artisan_doc = db.collection('users').document(product['artisanId']).get()
    artisan = artisan_doc.to_dict() if artisan_doc.exists else {}
    return render_template('product_page.html', product=product, artisan=artisan)


# --- USER PROFILE & SETTINGS ROUTES ---

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    user_doc = db.collection('users').document(session['user_id']).get()
    if not user_doc.exists: return redirect(url_for('logout'))
    user = user_doc.to_dict()
    unverified_artisans = []
    if user.get('type') == 'buyer':
        artisans_ref = db.collection('users').where('type', '==', 'artisan').where('verification_status', 'in', ['pending', 'submitted']).stream()
        unverified_artisans = [a.to_dict() for a in artisans_ref]
    return render_template('shared/profile.html', user=user, unverified_artisans=unverified_artisans)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    user_doc_ref = db.collection('users').document(session['user_id'])
    if request.method == 'POST':
        update_data = {'name': request.form['name']}
        if session.get('user_type') == 'artisan':
            update_data['craft'] = request.form['craft']
            update_data['location'] = request.form['location']
        else:
            update_data['shipping_address'] = request.form['shipping_address']
        user_doc_ref.update(update_data)
        flash('Profile updated successfully!', 'success')
        session['user_name'] = request.form['name']
        return redirect(url_for('profile'))
    user = user_doc_ref.get().to_dict()
    return render_template('shared/edit_profile.html', user=user)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    user_doc_ref = db.collection('users').document(session['user_id'])
    if request.method == 'POST':
        settings_data = {'order_emails': 'order_emails' in request.form}
        user_doc_ref.set({'settings': settings_data}, merge=True)
        flash('Settings saved!', 'success')
        return redirect(url_for('settings'))
    user = user_doc_ref.get().to_dict()
    if 'settings' not in user:
        user['settings'] = {}
    return render_template('shared/settings.html', user=user)

# --- CART & ORDER ROUTES (BUYER) ---

@app.route('/cart')
def cart_page():
    if 'user_id' not in session:
        flash('Please log in to view your cart.', 'warning')
        return redirect(url_for('login_page'))
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
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please log in to add items to your cart.', 'warning')
        return redirect(url_for('login_page'))
    user_ref = db.collection('users').document(session['user_id'])
    user_ref.update({'cart': firestore.ArrayUnion([product_id])})
    if product_id not in session.get('cart', []):
        session['cart'].append(product_id)
        session.modified = True
    flash('Product added to cart!', 'success')
    return redirect(url_for('marketplace'))

@app.route('/cart/remove/<product_id>')
def remove_from_cart(product_id):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    user_ref = db.collection('users').document(session['user_id'])
    user_ref.update({'cart': firestore.ArrayRemove([product_id])})
    if 'cart' in session and product_id in session['cart']:
        session['cart'].remove(product_id)
        session.modified = True
    flash('Product removed from cart.', 'success')
    return redirect(url_for('cart_page'))

@app.route('/checkout')
def checkout_page():
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        flash('You must be logged in to view your cart.', 'warning')
        return redirect(url_for('login_page'))
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
def confirm_order():
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        return redirect(url_for('login_page'))
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
                'id': order_id, 'buyerId': session['user_id'], 'artisanId': product['artisanId'],
                'productId': product_id, 'status': 'Packaging', 'orderDate': datetime.utcnow()
            }
            db.collection('orders').document(order_id).set(order_data)
            artisan_doc = db.collection('users').document(product['artisanId']).get()
            artisan = artisan_doc.to_dict()
            if buyer.get('email'):
                send_email(buyer['email'], f"Your Artisan AI Order #{order_id[:8]} is Confirmed!", f"Hi {buyer['name']},<br><br>Your order for '{product['name']}' has been placed successfully! You can track its status on your 'My Orders' page.")
            if artisan.get('email') and artisan.get('settings', {}).get('order_emails', False):
                send_email(artisan['email'], f"New Sale on Artisan AI! Order #{order_id[:8]}", f"Hi {artisan['name']},<br><br>You have a new order for '{product['name']}'. Please visit your dashboard to manage the order.")
    db.collection('users').document(session['user_id']).update({'cart': []})
    session['cart'] = []
    flash('Your order has been placed successfully!', 'success')
    return redirect(url_for('my_orders'))

@app.route('/my_orders')
def my_orders():
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        return redirect(url_for('login_page'))
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
def hub():
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return redirect(url_for('login_page'))
    artisan_doc = db.collection('users').document(session['user_id']).get()
    artisan = artisan_doc.to_dict()
    if artisan.get('verification_status') != 'verified':
        return render_template('artisan/verification.html', artisan=artisan)
    else:
        return render_template('artisan/hub.html', artisan=artisan)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return redirect(url_for('login_page'))
    artisan_doc = db.collection('users').document(session['user_id']).get()
    artisan = artisan_doc.to_dict()
    if artisan.get('verification_status') != 'verified':
        return render_template('artisan/verification.html', artisan=artisan)
    active_tab = request.args.get('tab', 'tools')
    orders_list = []
    artisan_products = []
    products_json = '{}'
    if active_tab == 'orders':
        orders_ref = db.collection('orders').where('artisanId', '==', session['user_id']).stream()
        for doc in orders_ref:
            order = doc.to_dict()
            buyer_doc = db.collection('users').document(order['buyerId']).get()
            product_doc = db.collection('products').document(order['productId']).get()
            order['buyer'] = buyer_doc.to_dict() if buyer_doc.exists else {}
            order['product'] = product_doc.to_dict() if product_doc.exists else {}
            orders_list.append(order)
    else:
        products_ref = db.collection('products').where('artisanId', '==', session['user_id']).stream()
        artisan_products = [p.to_dict() for p in products_ref]
        products_json = json.dumps({p['id']: p for p in artisan_products})
    return render_template('artisan/dashboard.html', artisan=artisan, active_tab=active_tab,
                           artisan_products=artisan_products, products_json=products_json, orders=orders_list)

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return redirect(url_for('login_page'))

    product_id = str(uuid.uuid4())
    product_data = {
        'id': product_id, 'name': request.form['name'], 'price': float(request.form['price']),
        'stock': int(request.form['stock']), 'dimensions': request.form['dimensions'],
        'materials': request.form['materials'], 'imageUrl': request.form['imageUrl'],
        'description': request.form['description'], 'artisanId': session['user_id'],
        'ai_description': '' # Create an empty field for the AI story
    }
    db.collection('products').document(product_id).set(product_data)
    flash('New product added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/generate_ai_story/<product_id>', methods=['POST'])
def generate_ai_story(product_id):
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        product_ref = db.collection('products').document(product_id)
        product_doc = product_ref.get()
        if not product_doc.exists:
            return jsonify({'error': 'Product not found'}), 404
        
        product = product_doc.to_dict()
        artisan = db.collection('users').document(product['artisanId']).get().to_dict()

        prompt = f"""
        An artisan named {artisan.get('name')} from {artisan.get('location')} who specializes in {artisan.get('craft')} has created a product.
        Product Name: "{product['name']}"
        Materials Used: "{product['materials']}"
        Artisan's Description: "{product['description']}"
        Write an enhanced, single-paragraph product story for an e-commerce website. The tone should be warm and evocative, focusing on craftsmanship and cultural heritage. Do not use headings or markdown.
        """
        response = model.generate_content(prompt)
        ai_story = response.text

        # Save the new story to the database
        product_ref.update({'ai_description': ai_story})
        
        return jsonify({'success': True, 'ai_story': ai_story})
    except Exception as e:
        # Check for quota error specifically
        if "quota" in str(e).lower():
            return jsonify({'error': 'You have exceeded your daily AI quota. Please try again tomorrow.'}), 429
        print(f"AI story generation failed: {e}")
        return jsonify({'error': 'An error occurred while generating the story.'}), 500
    
    
@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return redirect(url_for('login_page'))
    order_id = request.form['order_id']
    new_status = request.form['status']
    order_ref = db.collection('orders').document(order_id)
    order_ref.update({'status': new_status})
    if new_status == 'Shipped':
        order_doc = order_ref.get()
        order_data = order_doc.to_dict()
        buyer_doc = db.collection('users').document(order_data['buyerId']).get()
        buyer = buyer_doc.to_dict()
        product_doc = db.collection('products').document(order_data['productId']).get()
        product = product_doc.to_dict()
        if buyer.get('email'):
            send_email(buyer['email'], f"Your Artisan AI Order #{order_id[:8]} has Shipped!", f"Hi {buyer['name']},<br><br>Good news! Your order for '{product['name']}' has been shipped.")
    flash('Order status updated.', 'success')
    return redirect(url_for('dashboard', tab='orders'))


# --- AI TOOL ROUTES (ARTISAN) ---

@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    user_message = data.get('message', '')
    image_data = data.get('image_data')

    try:
        # --- Image Generation Request ---
        if user_message.lower().strip().startswith('/imagine'):
            prompt = user_message.replace('/imagine', '').strip()
            if not prompt:
                 return jsonify({'reply_type': 'text', 'reply_content': '<p>Please provide a description for the image you want to create. For example: <code>/imagine a rustic wooden bowl filled with spices</code></p>'})
            
            response = image_model.generate_content(prompt)
            image_url = response.candidates[0].content.parts[0].uri
            return jsonify({'reply_type': 'image', 'reply_content': image_url})

        # --- Standard or Vision-based Chat ---
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
        return jsonify({'reply_type': 'text', 'reply_content': f"<p>Sorry, I encountered an error: {e}</p>"})
    
    
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
        return jsonify({'result_html': f"An error occurred: {e}"}), 500

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

@app.route('/toggle-theme')
def toggle_theme():
    # Get the current theme from the session, default to 'light'
    current_theme = session.get('theme', 'light')
    
    # Flip the theme
    if current_theme == 'dark':
        session['theme'] = 'light'
    else:
        session['theme'] = 'dark'
        
    # Redirect back to the page the user was on
    return redirect(request.referrer or url_for('marketplace'))


@app.route('/trends')
def trends_page():
    if 'user_id' not in session or session.get('user_type') != 'artisan': return redirect(url_for('login_page'))
    artisan_doc = db.collection('users').document(session['user_id']).get()
    artisan = artisan_doc.to_dict()
    return render_template('artisan/trends_generator.html', artisan=artisan)

@app.route('/trends/generate', methods=['POST'])
def generate_trends():
    if 'user_id' not in session or session.get('user_type') != 'artisan': return redirect(url_for('login_page'))
    craft_category = request.form['craft_category']
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
    try:
        response = model.generate_content(prompt)
        trend_report_html = markdown.markdown(response.text)
        return render_template('artisan/trends_result.html', craft_category=craft_category, trend_report=trend_report_html)
    except Exception as e:
        flash(f"An AI error occurred while analyzing trends: {e}", "error")
        return redirect(url_for('trends_page'))

# --- VERIFICATION & ADMIN ROUTES ---

@app.route('/upload_verification_docs', methods=['POST'])
def upload_verification_docs():
    if 'user_id' not in session or session.get('user_type') != 'artisan':
        return redirect(url_for('login_page'))
    uid = session['user_id']
    uploaded_files = {}
    for field in ['identity_proof', 'business_proof', 'work_proof']:
        files = request.files.getlist(field)
        if not files or files[0].filename == '': continue
        file_urls = []
        for file in files:
            filename = f"verification/{uid}/{field}_{uuid.uuid4()}_{file.filename}"
            blob = bucket.blob(filename)
            blob.upload_from_file(file, content_type=file.content_type)
            blob.make_public()
            file_urls.append(blob.public_url)
        uploaded_files[field] = file_urls[0] if len(file_urls) == 1 else file_urls
    if uploaded_files:
        db.collection('users').document(uid).update({
            'verification_docs': uploaded_files, 'verification_status': 'submitted'
        })
        flash('Your documents have been submitted for review!', 'success')
    else:
        flash('You did not upload any files.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/scout_upload', methods=['POST'])
def scout_upload():
    if 'user_id' not in session or session.get('user_type') != 'buyer':
        return redirect(url_for('login_page'))
    buyer_id = session['user_id']
    artisan_id = request.form['artisan_id']
    photo = request.files['workshop_photo']
    if photo and photo.filename != '':
        filename = f"scout_verification/{artisan_id}/scout_{buyer_id}_{uuid.uuid4()}_{photo.filename}"
        blob = bucket.blob(filename)
        blob.upload_from_file(photo, content_type=photo.content_type)
        blob.make_public()
        db.collection('users').document(artisan_id).set({
            'scout_submissions': firestore.ArrayUnion([{
                'buyerId': buyer_id, 'photoUrl': blob.public_url, 'date': datetime.utcnow()
            }])
        }, merge=True)
        flash('Thank you for being a Community Scout! Your submission is under review.', 'success')
    else:
        flash('Please select a file to upload.', 'error')
    return redirect(url_for('profile'))

@app.route('/admin/verify')
def admin_verify():
    # In a real app, you'd protect this route with an admin login
    artisans_ref = db.collection('users').where('type', '==', 'artisan').where('verification_status', 'in', ['pending', 'submitted']).stream()
    pending_artisans = [a.to_dict() for a in artisans_ref]
    return render_template('admin/verify.html', artisans=pending_artisans)

@app.route('/admin/approve/<uid>')
def admin_approve(uid):
    artisan_ref = db.collection('users').document(uid)
    artisan_doc = artisan_ref.get()
    if artisan_doc.exists:
        artisan_data = artisan_doc.to_dict()
        if 'scout_submissions' in artisan_data:
            for submission in artisan_data['scout_submissions']:
                buyer_ref = db.collection('users').document(submission['buyerId'])
                buyer_ref.set({'reward_balance': firestore.Increment(50)}, merge=True)
    artisan_ref.update({'verification_status': 'verified'})
    flash(f"Artisan {uid} approved.", "success")
    return redirect(url_for('admin_verify'))

@app.route('/admin/reject/<uid>')
def admin_reject(uid):
    db.collection('users').document(uid).update({'verification_status': 'rejected'})
    flash(f"Artisan {uid} rejected.", "warning")
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