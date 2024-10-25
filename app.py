# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vicoba.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    loans = db.relationship('Loan', backref='user', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date_issued = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
@login_required
def dashboard():
    # Get user's financial summary
    total_savings = sum(t.amount for t in current_user.transactions if t.type == 'savings')
    active_loans = sum(l.amount for l in current_user.loans if l.status == 'active')
    
    # Get next meeting
    next_meeting = Meeting.query.filter(Meeting.date > datetime.utcnow()).first()
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         total_savings=total_savings,
                         active_loans=active_loans,
                         next_meeting=next_meeting,
                         recent_transactions=recent_transactions)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return redirect(url_for('signup'))
        
        # Hash the password and create a new user
        password_hash = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=password_hash)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/savings')
@login_required
def savings():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id, 
        type='savings'
    ).order_by(Transaction.date.desc()).all()
    return render_template('savings.html', transactions=transactions)

@app.route('/add_savings', methods=['POST'])
@login_required
def add_savings():
    amount = float(request.form.get('amount'))
    transaction = Transaction(
        type='savings',
        amount=amount,
        description='Savings deposit',
        user_id=current_user.id
    )
    db.session.add(transaction)
    db.session.commit()
    flash('Savings added successfully')
    return redirect(url_for('savings'))

@app.route('/loans')
@login_required
def loans():
    active_loans = Loan.query.filter_by(
        user_id=current_user.id, 
        status='active'
    ).all()
    return render_template('loans.html', loans=active_loans)

@app.route('/apply_loan', methods=['POST'])
@login_required
def apply_loan():
    amount = float(request.form.get('amount'))
    due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d')
    
    loan = Loan(
        amount=amount,
        due_date=due_date,
        user_id=current_user.id
    )
    db.session.add(loan)
    
    # Record loan disbursement as a transaction
    transaction = Transaction(
        type='loan_disbursement',
        amount=amount,
        description='Loan disbursement',
        user_id=current_user.id
    )
    db.session.add(transaction)
    db.session.commit()
    
    flash('Loan application submitted successfully')
    return redirect(url_for('loans'))

@app.route('/meetings')
@login_required
def meetings():
    upcoming_meetings = Meeting.query.filter(
        Meeting.date > datetime.utcnow()
    ).order_by(Meeting.date).all()
    return render_template('meetings.html', meetings=upcoming_meetings)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.email = request.form.get('email')
    if request.form.get('new_password'):
        current_user.password_hash = generate_password_hash(request.form.get('new_password'))
    db.session.commit()
    flash('Profile updated successfully')
    return redirect(url_for('profile'))

# Mock data for demonstration purposes
mock_data = {
    'total_members': 100,
    'total_savings': 5000000,
    'active_loans_count': 10,
    'pending_loans_count': 5,
    'pending_loans': [
        {'id': 1, 'user': {'username': 'john_doe'}, 'amount': 100000, 'date_issued': '2023-10-01', 'status': 'pending'},
        # Add more mock loans here
    ],
    'recent_activities': [
        {'date': '2023-10-01', 'user': {'username': 'john_doe'}, 'description': 'Loan request', 'amount': 100000},
        # Add more mock activities here
    ]
}

# Convert date strings to datetime objects
for loan in mock_data['pending_loans']:
    loan['date_issued'] = datetime.strptime(loan['date_issued'], '%Y-%m-%d')

for activity in mock_data['recent_activities']:
    activity['date'] = datetime.strptime(activity['date'], '%Y-%m-%d')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin.html', **mock_data)

@app.route('/admin/loans')
def admin_loans():
    return render_template('admin_loans.html', **mock_data)

@app.route('/admin/members')
def admin_members():
    return render_template('admin_members.html', **mock_data)

@app.route('/admin/meetings')
def admin_meetings():
    return render_template('admin_meetings.html', **mock_data)

@app.route('/admin/transactions')
def admin_transactions():
    return render_template('admin_transactions.html', **mock_data)

@app.route('/admin/reports')
def admin_reports():
    return render_template('admin_reports.html', **mock_data)

@app.route('/admin/settings')
def admin_settings():
    return render_template('admin_settings.html', **mock_data)

# @app.route('/logout')
# def logout():
#     # Handle logout logic here
#     return redirect(url_for('admin_dashboard'))

@app.route('/admin/schedule_meeting', methods=['POST'])
def admin_schedule_meeting():
    # Handle scheduling a new meeting
    meeting_date = request.form['date']
    meeting_location = request.form['location']
    meeting_description = request.form['description']
    # Save the meeting details to the database
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/loans/<int:loan_id>/approve', methods=['POST'])
def approve_loan(loan_id):
    # Handle loan approval logic
    # Update loan status in the database
    return jsonify({'status': 'success'})

@app.route('/admin/loans/<int:loan_id>/reject', methods=['POST'])
def reject_loan(loan_id):
    # Handle loan rejection logic
    # Update loan status in the database
    return jsonify({'status': 'success'})

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Initialize the database
def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)