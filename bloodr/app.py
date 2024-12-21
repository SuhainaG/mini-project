from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')
bcrypt = Bcrypt(app)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'your_telegram_bot_token')
TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'your_bot_username')
TELEGRAM_BOT_LINK = f"https://t.me/{TELEGRAM_BOT_USERNAME}"

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["bloodr"]
users_collection = db["users"]
donation_requests_collection = db["donation_requests"]

# Admin middleware to restrict access to admin pages
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or not session.get('is_admin', False):
            flash('You need to be an admin to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Blood group compatibility function
def get_compatible_blood_groups(blood_group):
    compatibility = {
        'A+': ['A+', 'A-', 'O+', 'O-'],
        'A-': ['A-', 'O-'],
        'B+': ['B+', 'B-', 'O+', 'O-'],
        'B-': ['B-', 'O-'],
        'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'AB-': ['A-', 'B-', 'AB-', 'O-'],
        'O+': ['O+', 'O-'],
        'O-': ['O-']
    }
    return compatibility.get(blood_group, [])

# Function to get donor recommendations
def get_recommendations(user_preferences):
    query = {}
    
    if user_preferences.get('city'):
        query['city'] = user_preferences['city'].lower()

    if user_preferences.get('donor_type') == 'blood':
        query['blood_donor'] = 'yes'
        if user_preferences.get('blood_group'):
            compatible_groups = get_compatible_blood_groups(user_preferences['blood_group'])
            query['blood_group'] = {'$in': compatible_groups}
    else:  # organ donor
        query['organ_donor'] = 'yes'
        if user_preferences.get('organ_type'):
            query['organ_group'] = user_preferences['organ_type']
    
    # Exclude current user from results
    if user_preferences.get('current_user'):
        query['username'] = {'$ne': user_preferences['current_user']}

    # Get recommended donors from DB
    recommended_donors = list(users_collection.find(
        query,
        {
            'username': 1,
            'city': 1,
            'phone': 1,
            'blood_donor': 1,
            'blood_group': 1,
            'organ_donor': 1,
            'organ_group': 1,
            '_id': 1
        }
    ))

    # Calculate match scores for each donor
    for donor in recommended_donors:
        donor['match_score'] = 0
        
        # Location match
        if donor.get('city') == user_preferences.get('city'):
            donor['match_score'] += 3
        
        # Blood type match
        if user_preferences.get('donor_type') == 'blood' and user_preferences.get('blood_group'):
            if donor.get('blood_group') == user_preferences['blood_group']:
                donor['match_score'] += 2
            elif donor.get('blood_group') in get_compatible_blood_groups(user_preferences['blood_group']):
                donor['match_score'] += 1
        
        # Organ type match
        elif user_preferences.get('donor_type') == 'organ' and user_preferences.get('organ_type'):
            if donor.get('organ_group') == user_preferences['organ_type']:
                donor['match_score'] += 2

    # Sort donors by match score (descending order)
    recommended_donors.sort(key=lambda x: x['match_score'], reverse=True)
    
    return recommended_donors

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        city = request.form.get('city', '').lower()
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        blood_donor = request.form.get('blood_donor')
        blood_group = request.form.get('blood_group') if blood_donor == 'yes' else None
        organ_donor = request.form.get('organ_donor')
        organ_group = request.form.getlist('organ_group') if organ_donor == 'yes' else None

        # Check if user already exists
        if users_collection.find_one({'email': email}):
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for('login'))

        # Insert new user into the database
        users_collection.insert_one({
            'username': username,
            'email': email,
            'phone': phone,
            'address': address,
            'city': city,
            'password': password,
            'blood_donor': blood_donor == 'yes',
            'blood_group': blood_group,
            'organ_donor': organ_donor == 'yes',
            'organ_group': organ_group,
            'is_active': True,
            'is_admin': False,  # Set default admin status
            'registration_date': datetime.utcnow()
        })
        
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = users_collection.find_one({'email': email})
        
        if user and bcrypt.check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', False)
            session['user_id'] = str(user['_id'])  # Add user ID to session
            
            if session['is_admin']:
                flash('Welcome Admin!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Logged in successfully!', 'success')
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'username': session['username']})
    
    # Get statistics
    stats = {
        'total_users': users_collection.count_documents({}),
        'blood_donors': users_collection.count_documents({'blood_donor': 'yes'}),
        'organ_donors': users_collection.count_documents({'organ_donor': 'yes'})
    }
    
    return render_template('dashboard.html', username=session['username'], user=user, stats=stats)

@app.route('/find_donor', methods=['GET', 'POST'])
def find_donor():
    if 'username' not in session:
        flash("Please log in to search for donors.", "warning")
        return redirect(url_for('login'))

    recommendations = []
    searched = False

    if request.method == 'POST':
        searched = True
        user_preferences = {
            'donor_type': request.form.get('donor_type'),
            'city': request.form.get('city', '').lower(),
            'current_user': session['username']
        }

        if user_preferences['donor_type'] == 'blood':
            user_preferences['blood_group'] = request.form.get('blood_group')
        else:
            user_preferences['organ_type'] = request.form.get('organ_type')

        # Get recommendations based on user preferences
        recommendations = get_recommendations(user_preferences)

        if not recommendations:
            flash(f"No matching donors found. Try broadening your search criteria.", "info")
        else:
            flash(f"Found {len(recommendations)} potential matches!", "success")

    # Get all cities with donors for the dropdown
    cities = users_collection.distinct('city')
    
    return render_template('find_donor.html', 
                         recommendations=recommendations, 
                         searched=searched, 
                         cities=cities)

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    # Get statistics
    stats = {
        'total_users': users_collection.count_documents({}),
        'blood_donors': users_collection.count_documents({'blood_donor': 'yes'}),
        'organ_donors': users_collection.count_documents({'organ_donor': 'yes'}),
        'active_requests': donation_requests_collection.count_documents({'status': 'pending'})
    }
    
    # Get all users
    users = list(users_collection.find())
    
    # Get blood donors
    blood_donors = list(users_collection.find({'blood_donor': 'yes'}, {'username': 1, 'city': 1, 'phone': 1, 'blood_group': 1}))
    # Get organ donors
    organ_donors = list(users_collection.find({'organ_donor': 'yes'}, {'username': 1, 'city': 1, 'phone': 1, 'organ_group': 1}))
    
    # Get all donation requests
    requests = list(donation_requests_collection.find().sort('date', -1))
    for request in requests:
        request['status_color'] = {
            'pending': 'warning',
            'approved': 'success',
            'completed': 'info',
            'cancelled': 'danger'
        }.get(request['status'], 'secondary')
    
    return render_template('admin_dashboard.html', stats=stats, users=users, blood_donors=blood_donors, organ_donors=organ_donors, requests=requests)

@app.route('/admin/toggle_user/<user_id>', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if user:
        new_status = not user.get('is_active', True)
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_active': new_status}}
        )
        flash(f"User status updated successfully", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/analytics_dashboard')
@admin_required
def analytics_dashboard():
    # Implement the logic for the analytics dashboard here
    stats = {
        'total_users': users_collection.count_documents({}),
        'blood_donors': users_collection.count_documents({'blood_donor': 'yes'}),
        'organ_donors': users_collection.count_documents({'organ_donor': 'yes'}),
    }
    
    return render_template('dashboard_analytics.html', stats=stats)

@app.route('/telegram_bot')
def telegram_bot():
    """Redirect to Telegram bot"""
    return redirect(TELEGRAM_BOT_LINK)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Process incoming message data
    print('Received message:', data)
    return jsonify({'status': 'received'}), 200

@app.route('/send', methods=['POST'])
def send_message():
    # Logic to send message via WhatsApp API
    message_data = request.json
    print('Sending message:', message_data)
    return jsonify({'status': 'sent'}), 200

# Create admin user if it doesn't exist
def create_admin_user():
    admin_email = "admin@bloodr.com"
    if not users_collection.find_one({'email': admin_email}):
        password = bcrypt.generate_password_hash("admin123").decode('utf-8')
        users_collection.insert_one({
            'username': 'admin',
            'email': admin_email,
            'phone': 'N/A',
            'address': 'N/A',
            'city': 'N/A',
            'password': password,
            'blood_donor': False,
            'organ_donor': False,
            'is_active': True,
            'is_admin': True,
            'registration_date': datetime.utcnow()
        })
        print("Admin user created successfully!")

if __name__ == '__main__':
    create_admin_user()  # Create admin user before running the app
    app.run(debug=True, use_reloader=True)
