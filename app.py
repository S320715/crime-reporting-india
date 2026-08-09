from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

app = Flask(__name__)
import os

database_url = os.environ.get('DATABASE_URL', 'sqlite:///crime_reports.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SECRET_KEY'] = 'change-this-later-to-something-random'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='citizen')

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    crime_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    area = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Received')
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists. Please login instead.')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.')
            return redirect(url_for('register'))

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(name=name, email=email, password_hash=password_hash, role='citizen')
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['role'] = user.role

            if user.role == 'citizen':
                return redirect(url_for('citizen_home'))
            elif user.role == 'police':
                return redirect(url_for('police_map'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect email or password.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/citizen-home')
def citizen_home():
    if 'user_id' not in session or session.get('role') != 'citizen':
        return redirect(url_for('login'))
    return render_template('citizen_home.html', name=session['user_name'])

AREAS = ['Sector 1 - Market', 'Sector 2 - Residential', 'Sector 3 - Industrial', 'Sector 4 - Downtown', 'Sector 5 - Outskirts']
CRIME_TYPES = ['Theft', 'Assault', 'Burglary', 'Vandalism', 'Fraud', 'Other']
AREA_COORDS = {
    'Sector 1 - Market': (28.6139, 77.2090),
    'Sector 2 - Residential': (28.6200, 77.2150),
    'Sector 3 - Industrial': (28.6100, 77.2200),
    'Sector 4 - Downtown': (28.6180, 77.2050),
    'Sector 5 - Outskirts': (28.6250, 77.2250),
}

@app.route('/submit-report', methods=['GET', 'POST'])
def submit_report():
    if 'user_id' not in session or session.get('role') != 'citizen':
        return redirect(url_for('login'))

    if request.method == 'POST':
        if len(request.form['description'].strip()) < 10:
            flash('Please provide a more detailed description (at least 10 characters).')
            return redirect(url_for('submit_report'))

        new_report = Report(
            user_id=session['user_id'],
            crime_type=request.form['crime_type'],
            description=request.form['description'],
            area=request.form['area'],
            status='Received'
        )
        db.session.add(new_report)
        db.session.commit()
        flash('Your report has been submitted successfully.')
        return redirect(url_for('citizen_home'))

    return render_template('report_form.html', areas=AREAS, crime_types=CRIME_TYPES)

@app.route('/my-reports')
def my_reports():
    if 'user_id' not in session or session.get('role') != 'citizen':
        return redirect(url_for('login'))

    reports = Report.query.filter_by(user_id=session['user_id']).order_by(Report.date_submitted.desc()).all()
    return render_template('my_reports.html', reports=reports)

@app.route('/police-map')
def police_map():
    if 'user_id' not in session or session.get('role') not in ['police', 'admin']:
        return redirect(url_for('login'))
    return render_template('police_map.html', name=session['user_name'])

@app.route('/api/reports')
def api_reports():
    if 'user_id' not in session or session.get('role') not in ['police', 'admin']:
        return jsonify([]), 403

    reports = Report.query.all()

    area_counts = {}
    for r in reports:
        area_counts[r.area] = area_counts.get(r.area, 0) + 1

    data = []
    for r in reports:
        lat, lng = AREA_COORDS.get(r.area, (28.6139, 77.2090))
        count = area_counts[r.area]
        if count >= 10:
            hotspot_level = 'red'
        elif count >= 5:
            hotspot_level = 'amber'
        else:
            hotspot_level = 'normal'

        data.append({
            'id': r.id,
            'crime_type': r.crime_type,
            'area': r.area,
            'description': r.description,
            'status': r.status,
            'date': r.date_submitted.strftime('%d %b %Y'),
            'lat': lat,
            'lng': lng,
            'hotspot_level': hotspot_level,
            'area_count': count
        })

    return jsonify(data)

@app.route('/update-status/<int:report_id>', methods=['POST'])
def update_status(report_id):
    if 'user_id' not in session or session.get('role') not in ['police', 'admin']:
        return redirect(url_for('login'))

    report = Report.query.get_or_404(report_id)
    report.status = request.form['status']
    db.session.commit()
    flash('Report status updated.')

    if session.get('role') == 'police':
        return redirect(url_for('police_map'))
    return redirect(url_for('admin_dashboard'))

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    reports = Report.query.all()

    crime_type_counts = {}
    area_counts = {}
    status_counts = {}

    for r in reports:
        crime_type_counts[r.crime_type] = crime_type_counts.get(r.crime_type, 0) + 1
        area_counts[r.area] = area_counts.get(r.area, 0) + 1
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    total_reports = len(reports)
    total_citizens = User.query.filter_by(role='citizen').count()
    total_police = User.query.filter_by(role='police').count()

    return render_template('admin_dashboard.html',
        name=session['user_name'],
        crime_type_labels=list(crime_type_counts.keys()),
        crime_type_values=list(crime_type_counts.values()),
        area_labels=list(area_counts.keys()),
        area_values=list(area_counts.values()),
        status_labels=list(status_counts.keys()),
        status_values=list(status_counts.values()),
        total_reports=total_reports,
        total_citizens=total_citizens,
        total_police=total_police
    )

@app.route('/admin/create-officer', methods=['GET', 'POST'])
def create_officer():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.')
            return redirect(url_for('create_officer'))

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_officer = User(name=name, email=email, password_hash=password_hash, role='police')
        db.session.add(new_officer)
        db.session.commit()
        flash('Police officer account created successfully.')
        return redirect(url_for('admin_dashboard'))

    return render_template('create_officer.html')

@app.route('/admin/users')
def view_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    users = User.query.all()
    return render_template('view_users.html', users=users)

with app.app_context():
    db.create_all()

    if not User.query.filter_by(email='police@test.com').first():
        pw = bcrypt.hashpw('police123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.add(User(name='Officer Test', email='police@test.com', password_hash=pw, role='police'))

    if not User.query.filter_by(email='admin@test.com').first():
        pw = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.add(User(name='Admin Test', email='admin@test.com', password_hash=pw, role='admin'))

    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)