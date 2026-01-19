
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
    
    # Block access if exam already submitted
    if session.get('exam_submitted'):
        flash('Exam already submitted. View your result.')
        return redirect(url_for('result'))

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
    return render_template('exam.html', questions=safe_questions, exam_submitted=False)

# --- Exam Submission Route (STEP 4: EVALUATION) ---
@app.route('/submit_exam', methods=['POST'])
@login_required
def submit_exam():
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
    
    # Mark exam as submitted to block re-entry to exam page
    session['exam_submitted'] = True
    
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
    # Read exam result from session (computed during submission)
    exam_result = session.get('exam_result')
    
    if not exam_result:
        # No exam result found - redirect to instructions
        flash('No exam result found. Please take the exam first.')
        return redirect(url_for('instructions'))
    
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
