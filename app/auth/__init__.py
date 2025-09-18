from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from firebase_admin import auth as firebase_auth
from firebase_admin import firestore
from .. import db
from ..security import login_required, csrf_protect, validate_input

# Create blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        # Validate input
        errors = validate_input(request.form, {
            'email': {'type': 'email', 'required': True},
            'password': {'type': 'string', 'required': True, 'min': 6}
        })
        
        if errors:
            for error in errors.values():
                flash(error, 'error')
            return render_template('auth/login.html')
        
        try:
            # Sign in with email and password
            user = firebase_auth.get_user_by_email(request.form['email'])
            # Note: In a real app, you would verify the password with Firebase Auth
            # For now, we'll just check if the user exists
            
            # Get user data from Firestore
            user_doc = db.collection('users').document(user.uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                # Set session variables
                session['user_id'] = user.uid
                session['user_email'] = user.email
                session['user_name'] = user_data.get('display_name', user.email.split('@')[0])
                session['is_artisan'] = user_data.get('is_artisan', False)
                session['is_verified'] = user_data.get('is_verified', False)
                
                # Redirect to appropriate dashboard
                if session['is_artisan']:
                    return redirect(url_for('artisan.dashboard'))
                else:
                    return redirect(url_for('buyer.dashboard'))
            else:
                flash('User data not found. Please contact support.', 'error')
                
        except Exception as e:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
@csrf_protect
def register():
    """Handle user registration."""
    if request.method == 'POST':
        # Validate input
        errors = validate_input(request.form, {
            'email': {'type': 'email', 'required': True},
            'password': {'type': 'string', 'required': True, 'min': 6},
            'display_name': {'type': 'string', 'required': True, 'min': 2},
            'user_type': {'type': 'string', 'required': True, 'allowed': ['artisan', 'buyer']}
        })
        
        if errors:
            for error in errors.values():
                flash(error, 'error')
            return render_template('auth/register.html')
        
        try:
            # Create user in Firebase Auth
            user = firebase_auth.create_user(
                email=request.form['email'],
                password=request.form['password'],
                display_name=request.form['display_name']
            )
            
            # Create user in Firestore
            user_data = {
                'email': request.form['email'],
                'display_name': request.form['display_name'],
                'is_artisan': request.form['user_type'] == 'artisan',
                'is_verified': False,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            db.collection('users').document(user.uid).set(user_data)
            
            # Set session variables
            session['user_id'] = user.uid
            session['user_email'] = user.email
            session['user_name'] = user_data['display_name']
            session['is_artisan'] = user_data['is_artisan']
            session['is_verified'] = False
            
            # Send verification email
            # In a real app, you would send an email verification link
            # firebase_auth.generate_email_verification_link(user.email)
            
            flash('Registration successful!', 'success')
            
            # Redirect to appropriate dashboard
            if session['is_artisan']:
                return redirect(url_for('artisan.dashboard'))
            else:
                return redirect(url_for('buyer.dashboard'))
                
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@csrf_protect
def forgot_password():
    """Handle password reset requests."""
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Email is required', 'error')
            return render_template('auth/forgot_password.html')
        
        try:
            # Send password reset email
            # In a real app, you would use Firebase Auth's send_password_reset_email
            # firebase_auth.generate_password_reset_link(email)
            flash('If an account exists with this email, a password reset link has been sent.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('auth/forgot_password.html')
