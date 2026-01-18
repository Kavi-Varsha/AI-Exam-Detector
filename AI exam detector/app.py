from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from functools import wraps
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = 'ai_exam_detector_secret_key_0229'  

# --- Dummy User Data (for demonstration purposes) ---
USERS = {
    "student1": "pass123",
    "student2": "exam456",
    "kavi" : "kavi123",
    "kushi": "kushi456"
}

# --- Login Required Decorator (It is a reusable gatekeeper.Any route decorated with @login_required becomes protected) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in (If not, redirect to login)
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Root Route: Redirect to Login ---
@app.route('/')
def root():
    return redirect(url_for('login'))

# --- Login Route ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Receive form data (HTML form submission)
        username = request.form['username']
        password = request.form['password']
        # Validate credentials (present in dummy data)
        if username in USERS and USERS[username] == password:
            # On success: create session variables
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('instructions'))
        else:
            # On failure: show error
            flash('Invalid credentials. Please try again.')
            return render_template('login.html')
    # GET: show login form 
    return render_template('login.html')

# --- Instructions Page (Protected) ---
@app.route('/instructions')
@login_required
def instructions():
    return render_template('instructions.html')

# --- Checking Page (Protected) ---
@app.route('/checking')
@login_required
def checking():
    return render_template('checking.html')

# --- Checking Page submit ---
@app.route('/api/checking/submit', methods=['POST'])
@login_required
def submit_checking():
    data = request.get_json(silent=True) or {}

    camera = bool(data.get('camera'))
    microphone = bool(data.get('microphone'))
    fullscreen = bool(data.get('fullscreen'))
    network = bool(data.get('network'))   

    if camera and microphone and fullscreen and network:
        session['system_check_passed'] = True

        # Start exam timer here (as you wanted)
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=45)

        session['exam_start_time'] = start_time.isoformat()
        session['exam_end_time'] = end_time.isoformat()

        return jsonify({"status": "passed"}), 200

    session['system_check_passed'] = False
    return jsonify({"status": "failed"}), 403

# --- ExamPage (Protected) ---

@app.route('/exam')
@login_required
def exam():
    if not session.get('system_check_passed'):
        flash('Complete system checks first.')
        return redirect(url_for('checking'))

   
    return render_template('exam.html')

# --- Exam Timer Status API ---
@app.route('/api/exam/time')
@login_required
def exam_time():
    start = session.get('exam_start_time')
    end = session.get('exam_end_time')

    if not start or not end:
        return jsonify({"active": False}), 200

    end_time = datetime.fromisoformat(end)
    now = datetime.utcnow()

    remaining_seconds = int((end_time - now).total_seconds())

    return jsonify({
        "active": True,
        "remaining_seconds": max(0, remaining_seconds)
    }), 200



# --- Result Page (Protected, placeholder) ---
@app.route('/result')
@login_required
def result():
    return 'Result Page - Only for logged in users.'

# --- Logout Route ---

@app.route('/logout')
@login_required
def logout():
    # Clear session and redirect to login
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
