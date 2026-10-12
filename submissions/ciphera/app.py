from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import time

app = Flask(__name__)

import os

# =======================================================
# GMAIL SSL CONFIGURATION (Uses Environment Variables)
# =======================================================
SENDER_GMAIL = os.environ.get("SENDER_GMAIL", "your_gmail@gmail.com")
SENDER_APP_PASSWORD = os.environ.get("SENDER_APP_PASSWORD", "xxxx xxxx xxxx xxxx")

def send_mentor_email_ssl(mentor_email, mentor_name, learner_name, learner_email, course_name, credits_locked, otp, slot):
    """Sends a formatted HTML email notification directly to the mentor via Gmail SSL."""
    # Check if user forgot to replace placeholders
    if "your_actual_gmail" in SENDER_GMAIL or "xxxx" in SENDER_APP_PASSWORD:
        err_msg = "Gmail credentials not configured in app.py. Please provide your Gmail and App Password."
        print(f"[!] Warning: {err_msg}")
        return False, err_msg

    try:
        msg = MIMEMultipart("alternative")
        msg['From'] = f"MU Skill Barter <{SENDER_GMAIL}>"
        msg['To'] = mentor_email
        msg['Subject'] = f"🔔 [Booking Alert] {learner_name} booked your course '{course_name}'!"

        # Plaintext Fallback
        text_content = f"""Hello {mentor_name},

{learner_name} ({learner_email}) has booked your session for '{course_name}'.
Venue & Slot: {slot}
Credits Locked in Escrow: {credits_locked} Credit(s)
Your Session Completion OTP: {otp}

Meet with {learner_name} on campus. Once they enter your OTP ({otp}), the {credits_locked} credit(s) will transfer to your wallet!
"""

        # Rich HTML Campus Email Template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b1120; color: #f8fafc; padding: 24px; margin: 0;">
            <div style="max-width: 560px; margin: 0 auto; background-color: #131d33; border: 1px solid #1e2e4e; border-radius: 12px; padding: 28px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                <div style="display: inline-block; background-color: #4f46e5; color: white; font-size: 11px; font-weight: 800; padding: 4px 8px; border-radius: 4px; letter-spacing: 0.5px; margin-bottom: 12px;">
                    MAHINDRA UNIVERSITY P2P
                </div>
                <h2 style="color: #ffffff; font-size: 20px; margin: 0 0 10px 0;">New Course Session Booked!</h2>
                <p style="color: #94a3b8; font-size: 14px; line-height: 1.5; margin: 0 0 20px 0;">
                    Hello <strong style="color: #fff;">{mentor_name}</strong>, a fellow student has locked credits to learn from you.
                </p>

                <div style="background-color: #0b1222; border: 1px solid #1e2e4e; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr>
                            <td style="color: #94a3b8; padding: 6px 0;">Learner:</td>
                            <td style="color: #fff; font-weight: 600; text-align: right;">{learner_name} ({learner_email})</td>
                        </tr>
                        <tr>
                            <td style="color: #94a3b8; padding: 6px 0;">Course:</td>
                            <td style="color: #38bdf8; font-weight: 700; text-align: right;">{course_name}</td>
                        </tr>
                        <tr>
                            <td style="color: #94a3b8; padding: 6px 0;">Venue & Time:</td>
                            <td style="color: #fff; text-align: right;">{slot}</td>
                        </tr>
                        <tr>
                            <td style="color: #94a3b8; padding: 6px 0;">Escrow Fee:</td>
                            <td style="color: #f59e0b; font-weight: 700; text-align: right;">{credits_locked} Credit(s) Locked</td>
                        </tr>
                    </table>
                </div>

                <div style="background-color: #1e1b4b; border: 1px dashed #6366f1; border-radius: 8px; padding: 16px; text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 12px; color: #c7d2fe; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">Your Secret Handshake Code</div>
                    <div style="font-size: 28px; font-weight: 800; font-family: monospace; color: #f59e0b; letter-spacing: 6px;">{otp}</div>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">Show this OTP to {learner_name} once the session concludes to release your credits.</div>
                </div>

                <p style="font-size: 11px; color: #64748b; margin: 0; text-align: center;">
                    Mahindra University Campus Time-Credit System · Decentralized Peer Liquidity Engine
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        # Immediate SSL connection on Port 465 (Never hangs or times out)
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
        server.login(SENDER_GMAIL, SENDER_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"[✓] Email dispatched successfully to {mentor_email}")
        return True, "Email dispatched to mentor's inbox."
    except Exception as e:
        print(f"[!] SMTP Error while dispatching email: {e}")
        return False, str(e)

# =======================================================
# IN-MEMORY DATA STORE (Zero pre-stored fake users)
# =======================================================
users = {}
sessions = []

def is_valid_college_email(email):
    email = email.strip().lower()
    return email.endswith("mahindrauniversity.edu.in") or email.endswith(".edu.in") or email.endswith(".edu")

@app.route('/')
def home():
    return render_template('index.html')

# 1. Login / Sign Up
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()

    if not is_valid_college_email(email):
        return jsonify({"error": "Access Denied: Please use your @mahindrauniversity.edu.in email ID."}), 400

    if email not in users:
        # Every new student gets 2 free welcome credits
        users[email] = {
            "name": name if name else email.split('@')[0],
            "email": email,
            "credits": 2,
            "courses_offered": [],
            "wanted_skills": []
        }

    return jsonify({"user": users[email]})

# 2. Add Course Offered OR Skill in Demand
@app.route('/api/courses/add', methods=['POST'])
def add_course():
    data = request.json
    email = data.get('email', '').strip().lower()
    course_type = data.get('type')  # 'offer' or 'want'
    course_name = data.get('name', '').strip()
    course_credits = int(data.get('credits', 1))

    if email not in users or not course_name:
        return jsonify({"error": "Invalid course or email parameters"}), 400

    user = users[email]
    if course_type == 'offer':
        # Don't add duplicates
        if not any(c['name'].lower() == course_name.lower() for c in user['courses_offered']):
            user['courses_offered'].append({
                "name": course_name,
                "credits": max(1, course_credits)
            })
    else:
        if course_name.lower() not in [w.lower() for w in user['wanted_skills']]:
            user['wanted_skills'].append(course_name)

    return jsonify({"user": user})

# 3. Catalog of Available Courses from Mentors
@app.route('/api/courses/available', methods=['GET'])
def get_available_courses():
    current_email = request.args.get('email', '').strip().lower()
    catalog = []

    for email, user in users.items():
        if email != current_email:
            for course in user['courses_offered']:
                catalog.append({
                    "mentor_name": user['name'],
                    "mentor_email": user['email'],
                    "course_name": course['name'],
                    "course_credits": course['credits']
                })

    return jsonify({"catalog": catalog})

# 4. Book Session, Hold Credits in Escrow & Dispatch Email
@app.route('/api/sessions/book', methods=['POST'])
def book_session():
    data = request.json
    learner_email = data.get('learner_email', '').strip().lower()
    mentor_email = data.get('mentor_email', '').strip().lower()
    course_name = data.get('course_name', '').strip()
    course_credits = int(data.get('course_credits', 1))
    slot = data.get('slot', 'Campus Library / Lab')

    learner = users.get(learner_email)
    mentor = users.get(mentor_email)

    if not learner or not mentor:
        return jsonify({"error": "Student record not found"}), 404

    if learner['credits'] < course_credits:
        return jsonify({
            "error": f"Insufficient Credits! You have {learner['credits']} credits, but this course requires {course_credits} credit(s)."
        }), 400

    # Escrow holding: Deduct from learner immediately
    learner['credits'] -= course_credits
    otp = str(random.randint(1000, 9999))

    session_obj = {
        "id": f"ses_{int(time.time())}_{random.randint(10, 99)}",
        "learner_name": learner['name'],
        "learner_email": learner['email'],
        "mentor_name": mentor['name'],
        "mentor_email": mentor['email'],
        "course_name": course_name,
        "course_credits": course_credits,
        "slot": slot,
        "otp": otp,
        "status": "scheduled",
        "timestamp": time.strftime("%H:%M")
    }
    sessions.insert(0, session_obj)

    # Dispatch Email to Mentor
    email_success, email_msg = send_mentor_email_ssl(
        mentor_email=mentor['email'],
        mentor_name=mentor['name'],
        learner_name=learner['name'],
        learner_email=learner['email'],
        course_name=course_name,
        credits_locked=course_credits,
        otp=otp,
        slot=slot
    )

    return jsonify({
        "message": f"Booked! {course_credits} credit(s) held in escrow.",
        "email_sent": email_success,
        "email_status": email_msg,
        "session": session_obj,
        "remaining_credits": learner['credits']
    })

# 5. List Sessions for Active User
@app.route('/api/sessions/list', methods=['GET'])
def list_sessions():
    email = request.args.get('email', '').strip().lower()
    user_sessions = [s for s in sessions if s['learner_email'] == email or s['mentor_email'] == email]
    return jsonify({"sessions": user_sessions})

# 6. Verify Session with OTP & Release Credits
@app.route('/api/sessions/verify', methods=['POST'])
def verify_session():
    data = request.json
    session_id = data.get('session_id')
    entered_otp = str(data.get('otp')).strip()

    target_session = next((s for s in sessions if s['id'] == session_id), None)
    if not target_session:
        return jsonify({"error": "Session not found."}), 404

    if target_session['status'] == 'completed':
        return jsonify({"error": "This session has already been completed."}), 400

    if target_session['otp'] != entered_otp:
        return jsonify({"error": "Invalid OTP! Ask your mentor for the 4-digit code sent to their email."}), 400

    # Escrow Release: Transfer credits to mentor
    target_session['status'] = 'completed'
    mentor = users.get(target_session['mentor_email'])
    if mentor:
        mentor['credits'] += target_session['course_credits']

    return jsonify({
        "message": f"Verification successful! {target_session['course_credits']} credit(s) transferred to {mentor['name']}."
    })

# 7. Real-Time Demand vs Supply Analytics API
@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    demand_counts = {}
    supply_counts = {}

    for email, u in users.items():
        for want in u['wanted_skills']:
            w_clean = want.title()
            demand_counts[w_clean] = demand_counts.get(w_clean, 0) + 1
        for offer in u['courses_offered']:
            o_clean = offer['name'].title()
            supply_counts[o_clean] = supply_counts.get(o_clean, 0) + 1

    all_keys = sorted(list(set(list(demand_counts.keys()) + list(supply_counts.keys()))))

    return jsonify({
        "labels": all_keys if all_keys else ["Python", "DSA", "Web Dev", "Figma", "ML"],
        "demand": [demand_counts.get(k, 0) for k in all_keys] if all_keys else [3, 5, 2, 4, 1],
        "supply": [supply_counts.get(k, 0) for k in all_keys] if all_keys else [2, 1, 4, 2, 3]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)