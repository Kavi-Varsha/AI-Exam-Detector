from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

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
    # Only accessible if logged in
    return 'Instructions Page - Only for logged in users.'

# --- Exam Page (Protected, placeholder) ---
@app.route('/exam')
@login_required
def exam():
    return 'Exam Page - Only for logged in users.'

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

