
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
            
            # Clear any previous exam state for fresh start
            session.pop('exam_submitted', None)
            session.pop('exam_started', None)
            session.pop('exam_result', None)
            session.pop('system_check_passed', None)
            session.pop('exam_start_time', None)
            session.pop('exam_end_time', None)
            session.modified = True
            
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
    # PRIORITY 1: If exam already submitted, go to result
    if session.get('exam_submitted'):
        return redirect(url_for('result'))
    
    # PRIORITY 2: If exam already started, go to exam page
    if session.get('exam_started'):
        return redirect(url_for('exam'))
    
    # PRIORITY 3: Otherwise show instructions (exam not started)
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
        # TESTING: 2 minutes timer (change to 45 for production)
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=1)

        session['exam_start_time'] = start_time.isoformat()
        session['exam_end_time'] = end_time.isoformat()
        session['exam_started'] = True  # Mark exam as started
        session.modified = True

        return jsonify({"status": "passed"}), 200

    session['system_check_passed'] = False
    return jsonify({"status": "failed"}), 403

# --- ExamPage (Protected) ---
@app.route('/exam')
@login_required
def exam():
    # PRIORITY 1: If exam already submitted, go to result
    if session.get('exam_submitted'):
        return redirect(url_for('result'))
    
    # PRIORITY 2: If exam not started yet, go to instructions
    if not session.get('exam_started'):
        return redirect(url_for('instructions'))
    
    # PRIORITY 3: Check system check passed
    if not session.get('system_check_passed'):
        flash('Complete system checks first.')
        return redirect(url_for('checking'))

    # PRIORITY 4: Exam is valid, show exam page
    # Import questions and prepare safe version (without 'correct' options)
    from questions import questions as all_questions
    safe_questions = [
        {
            'id': q['id'],
            'question': q['question'],
            'options': q['options']
        }
        for q in all_questions
    ]
    return render_template('exam.html', questions=safe_questions, exam_submitted=False, username=session.get('username'))

# --- Exam Submission Route (STEP 4: EVALUATION) ---
@app.route('/submit_exam', methods=['POST'])
@login_required
def submit_exam():
    # STEP B3: Idempotent check - if already submitted, redirect
    if session.get('exam_submitted'):
        return redirect(url_for('result'))
    
    from questions import questions as all_questions
    
    # Get all submitted answers from form
    submitted = dict(request.form)
    
    # Initialize counters
    total = len(all_questions)
    correct_count = 0
    wrong_count = 0
    unanswered_count = 0
    
    # Evaluate each question (loop through question list, not answers)
    for q in all_questions:
        q_key = f"q_{q['id']}"
        
        if q_key not in submitted:
            # Question was not answered
            unanswered_count += 1
        else:
            # Question was answered - compare with correct answer
            submitted_answer = int(submitted[q_key])
            correct_answer = q['correct']
            
            if submitted_answer == correct_answer:
                correct_count += 1
            else:
                wrong_count += 1
    
    # Store evaluation result in session (for result page to read)
    session['exam_result'] = {
        'total_questions': total,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'unanswered_count': unanswered_count,
        'score': correct_count
    }
    
    # Mark exam as submitted - this is the ONLY place where exam_submitted is set to True
    session['exam_submitted'] = True
    session.modified = True
    
    # Redirect to result page
    return redirect(url_for('result'))

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



# --- Result Page (STEP 5: DISPLAY RESULTS) ---
@app.route('/result')
@login_required
def result():
    # PRIORITY 1: If exam not submitted, go to instructions
    if not session.get('exam_submitted'):
        return redirect(url_for('instructions'))
    
    # PRIORITY 2: Exam submitted, show result
    # Read exam result from session (computed during submission)
    exam_result = session.get('exam_result')
    
    # Pass result and username to template
    return render_template('result.html', 
                         result=exam_result,
                         username=session.get('username'))

# --- Logout Route ---

@app.route('/logout')
@login_required
def logout():
    # Clear session and redirect to login
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
