from flask import Flask, request, render_template_string, make_response, redirect
from datetime import datetime, timedelta
import sqlite3
import os

app = Flask(__name__)
DB_FILE = "laundry.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'Available',
                current_user_name TEXT,
                current_user_phone TEXT,
                start_time TEXT,
                reserved_for_name TEXT,
                reserved_for_phone TEXT,
                reservation_expiry TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                status TEXT DEFAULT 'Waiting'
            )
        ''')
        if not conn.execute("SELECT COUNT(*) FROM machines").fetchone()[0]:
            floors = ["First Floor", "Fifth Floor", "Seventh Floor"]
            for floor in floors:
                conn.execute("INSERT INTO machines (name) VALUES (?)", (floor,))
        conn.commit()

def refresh_system_states(conn):
    now = datetime.now()
    now_str = now.isoformat()
    
    # 1. Reservation Expired Logic
    expired = conn.execute(
        "SELECT id, reserved_for_name, reserved_for_phone FROM machines WHERE status = 'Reserved' AND reservation_expiry < ?",
        (now_str,)
    ).fetchall()
    
    for row in expired:
        conn.execute(
            "UPDATE machines SET status = 'Available', reserved_for_name = NULL, reserved_for_phone = NULL, reservation_expiry = NULL WHERE id = ?",
            (row['id'],)
        )
        conn.execute("DELETE FROM queue WHERE name = ? AND phone = ? AND status = 'Notified'", (row['reserved_for_name'], row['reserved_for_phone']))

    # 2. Queue Assignment Logic
    available_machines = conn.execute("SELECT id FROM machines WHERE status = 'Available'").fetchall()
    for mach in available_machines:
        current_mach = conn.execute("SELECT reserved_for_name FROM machines WHERE id = ?", (mach['id'],)).fetchone()
        if not current_mach['reserved_for_name']:
            next_waiter = conn.execute("SELECT id, name, phone FROM queue WHERE status = 'Waiting' ORDER BY joined_at ASC LIMIT 1").fetchone()
            if next_waiter:
                expiry_time = (now + timedelta(minutes=5)).isoformat()
                conn.execute(
                    "UPDATE machines SET status = 'Reserved', reserved_for_name = ?, reserved_for_phone = ?, reservation_expiry = ? WHERE id = ?",
                    (next_waiter['name'], next_waiter['phone'], expiry_time, mach['id'])
                )
                conn.execute("UPDATE queue SET status = 'Notified' WHERE id = ?", (next_waiter['id'],))

def format_elapsed(start_time_str):
    if not start_time_str:
        return ""
    try:
        start_dt = datetime.fromisoformat(start_time_str)
        diff = datetime.now() - start_dt
        total_seconds = int(diff.total_seconds())
        if total_seconds < 0:
            return "Just started spinning"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours > 0:
            return f"Spinning for {hours}h {minutes}m"
        else:
            return f"Spinning for {minutes} min(s)"
    except Exception:
        return ""

app.jinja_env.globals.update(format_elapsed=format_elapsed)

@app.route('/')
def dashboard():
    conn = get_db()
    refresh_system_states(conn)
    machines = conn.execute("SELECT * FROM machines").fetchall()
    queue = conn.execute("SELECT * FROM queue WHERE status IN ('Waiting', 'Notified') ORDER BY joined_at ASC").fetchall()
    
    # Check if user has active session cookies stored
    user_name = request.cookies.get('laundry_user_name')
    user_phone = request.cookies.get('laundry_user_phone')
    
    my_active_machine = None
    my_queue_status = None
    
    if user_name and user_phone:
        my_active_machine = conn.execute(
            "SELECT * FROM machines WHERE (current_user_name = ? AND current_user_phone = ?) OR (reserved_for_name = ? AND reserved_for_phone = ?)",
            (user_name, user_phone, user_name, user_phone)
        ).fetchone()
        
        my_queue_status = conn.execute(
            "SELECT * FROM queue WHERE name = ? AND phone = ? AND status IN ('Waiting', 'Notified')",
            (user_name, user_phone)
        ).fetchone()

    conn.commit()
    conn.close()
    return render_template_string(DASHBOARD_TEMPLATE, machines=machines, queue=queue, user_name=user_name, my_active_machine=my_active_machine, my_queue_status=my_queue_status)

@app.route('/logout')
def logout():
    resp = make_response(redirect('/'))
    resp.set_cookie('laundry_user_name', '', expires=0)
    resp.set_cookie('laundry_user_phone', '', expires=0)
    return resp

@app.route('/reset-db')
def reset_db():
    conn = get_db()
    conn.execute("""
        UPDATE machines 
        SET status = 'Available', 
            current_user_name = NULL, 
            current_user_phone = NULL, 
            start_time = NULL, 
            reserved_for_name = NULL, 
            reserved_for_phone = NULL, 
            reservation_expiry = NULL
    """)
    conn.execute("DELETE FROM queue")
    conn.commit()
    conn.close()
    return "✨ Database reset successfully! All machines are now Available and the queue is empty. <a href='/'>Go to Dashboard</a>"

@app.route('/machine/<int:machine_id>', methods=['GET', 'POST'])
def scan_qr(machine_id):
    conn = get_db()
    refresh_system_states(conn)
    machine = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    
    if not machine:
        conn.close()
        return "Machine not found", 404
        
    # Pre-fill from cookies if available
    cookie_name = request.cookies.get('laundry_user_name', '')
    cookie_phone = request.cookies.get('laundry_user_phone', '')
    
    message = None
    resp = None

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        action = request.form.get('action')
        now = datetime.now()
        
        if action == 'start':
            if machine['status'] == 'Reserved' and (machine['reserved_for_name'] != name or machine['reserved_for_phone'] != phone):
                message = "🧼 Hold your foam! This machine is reserved for someone else in queue."
            else:
                start_time_str = now.isoformat()
                conn.execute(
                    """UPDATE machines SET status = 'In-Use', current_user_name = ?, current_user_phone = ?, 
                       start_time = ?, reserved_for_name = NULL, reserved_for_phone = NULL, reservation_expiry = NULL WHERE id = ?""",
                    (name, phone, start_time_str, machine_id)
                )
                conn.execute("UPDATE queue SET status = 'Completed' WHERE name = ? AND phone = ? AND status IN ('Waiting', 'Notified')", (name, phone))
                conn.commit()
                message = "🌀 Spin cycle initiated! Wash in progress."
                
        elif action == 'join_queue':
            existing = conn.execute("SELECT id FROM queue WHERE name = ? AND phone = ? AND status IN ('Waiting', 'Notified')", (name, phone)).fetchone()
            if existing:
                message = "🫧 You are already soaking in the virtual queue!"
            else:
                conn.execute("INSERT INTO queue (name, phone, joined_at) VALUES (?, ?, ?)", (name, phone, now.isoformat()))
                conn.commit()
                message = "⏳ Hopped into the virtual queue successfully!"
                
        elif action == 'leave_queue':
            conn.execute("DELETE FROM queue WHERE name = ? AND phone = ? AND status IN ('Waiting', 'Notified')", (name, phone))
            if machine['status'] == 'Reserved' and machine['reserved_for_name'] == name and machine['reserved_for_phone'] == phone:
                conn.execute("UPDATE machines SET status = 'Available', reserved_for_name = NULL, reserved_for_phone = NULL, reservation_expiry = NULL WHERE id = ?", (machine_id,))
            conn.commit()
            message = "🧼 You left the queue. Clean break!"
            
        elif action == 'clear':
            conn.execute(
                "UPDATE machines SET status = 'Available', current_user_name = NULL, current_user_phone = NULL, start_time = NULL WHERE id = ?", 
                (machine_id,)
            )
            conn.commit()
            message = "✨ Clothes removed! Machine is squeaky clean and available."

        # Set cookies to remember user across pages
        updated_machine = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
        updated_queue = conn.execute("SELECT * FROM queue WHERE status IN ('Waiting', 'Notified') ORDER BY joined_at ASC").fetchall()
        resp = make_response(render_template_string(MACHINE_TEMPLATE, machine=updated_machine, queue=updated_queue, message=message, default_name=name, default_phone=phone))
        resp.set_cookie('laundry_user_name', name, max_age=60*60*24*30)
        resp.set_cookie('laundry_user_phone', phone, max_age=60*60*24*30)
        conn.close()
        return resp

    machine = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    queue = conn.execute("SELECT * FROM queue WHERE status IN ('Waiting', 'Notified') ORDER BY joined_at ASC").fetchall()
    conn.close()
    return render_template_string(MACHINE_TEMPLATE, machine=machine, queue=queue, message=message, default_name=cookie_name, default_phone=cookie_phone)

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Washing MUchine Hub</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <link rel="icon" href="https://fav.farm/🧺">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes floatBubble {
            0% { transform: translateY(0) scale(1); opacity: 0.8; }
            50% { opacity: 0.4; }
            100% { transform: translateY(-120px) scale(1.4); opacity: 0; }
        }
        .bubble {
            position: absolute;
            background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.9), rgba(186, 230, 253, 0.4));
            border: 1px solid rgba(255, 255, 255, 0.8);
            border-radius: 50%;
            pointer-events: none;
            box-shadow: inset 0 0 10px rgba(255, 255, 255, 0.8);
            animation: floatBubble 5s infinite ease-in-out;
        }
    </style>
</head>
<body class="bg-gradient-to-tr from-sky-200 via-cyan-100 to-indigo-100 text-slate-800 min-h-screen p-4 sm:p-8 relative overflow-x-hidden">
    <!-- Bubbly background elements -->
    <div class="bubble w-8 h-8 top-12 left-8" style="animation-delay: 0s;"></div>
    <div class="bubble w-12 h-12 top-32 right-16" style="animation-delay: 1.2s;"></div>
    <div class="bubble w-6 h-6 top-64 left-1/3" style="animation-delay: 2.5s;"></div>
    <div class="bubble w-10 h-10 bottom-24 right-1/4" style="animation-delay: 0.8s;"></div>
    <div class="bubble w-5 h-5 bottom-12 left-16" style="animation-delay: 3.1s;"></div>

    <div class="max-w-3xl mx-auto relative z-10">
        <header class="text-center mb-8">
            <span class="bg-sky-200/90 text-sky-900 text-xs font-extrabold px-3.5 py-1.5 rounded-full uppercase tracking-widest shadow-sm">
                🫧 Phase 4A Hostel
            </span>
            <h1 class="text-4xl font-extrabold mt-3 tracking-tight text-sky-950 flex items-center justify-center gap-2">
                🧼 Washing MUchine Live
            </h1>
            <p class="text-sm text-sky-800 font-semibold mt-1">Real-time Laundry Hub • Auto-refreshes every 30s</p>
            
            {% if user_name %}
            <div class="mt-4 inline-flex items-center gap-2 bg-white/80 backdrop-blur px-4 py-2 rounded-2xl shadow-sm border border-sky-200 text-xs">
                <span>👋 Welcome back, <strong>{{user_name}}</strong>!</span>
                <a href="/logout" class="text-rose-600 font-bold hover:underline ml-2">Switch User</a>
            </div>
            {% endif %}
        </header>

        {% if my_active_machine or my_queue_status %}
        <div class="bg-gradient-to-r from-sky-500 to-cyan-600 text-white rounded-3xl p-5 shadow-lg mb-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
                <span class="bg-white/20 text-xs font-black px-2.5 py-1 rounded-full uppercase tracking-wider">Your Active Status</span>
                <h3 class="text-lg font-extrabold mt-2">
                    {% if my_active_machine %}
                        🧺 Using/Reserved: {{my_active_machine.name}} ({{my_active_machine.status}})
                    {% elif my_queue_status %}
                        ⏳ Waiting in Virtual Queue
                    {% endif %}
                </h3>
            </div>
            {% if my_active_machine %}
                <a href="/machine/{{my_active_machine.id}}" class="bg-white text-sky-900 font-extrabold text-xs px-5 py-3 rounded-xl shadow hover:bg-sky-50 transition">
                    Manage Machine ➔
                </a>
            {% endif %}
        </div>
        {% endif %}

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
            {% for m in machines %}
            <div class="bg-white/90 backdrop-blur rounded-3xl p-5 shadow-lg border-2 
                {% if m.status == 'In-Use' %} border-sky-400 ring-4 ring-sky-100 
                {% elif m.status == 'Available' %} border-emerald-300 
                {% elif m.status == 'Idle' %} border-rose-300 
                {% else %} border-amber-300 {% endif %} relative flex flex-col justify-between">
                
                <div>
                    <div class="flex items-center justify-between mb-3">
                        <h3 class="font-extrabold text-lg text-slate-900 tracking-tight">{{m.name}}</h3>
                        <div class="w-10 h-10 rounded-full border-4 border-slate-200 bg-sky-50 flex items-center justify-center relative shadow-inner overflow-hidden">
                            {% if m.status == 'In-Use' %}
                                <div class="absolute inset-0 bg-sky-300/40 animate-pulse"></div>
                                <svg class="w-6 h-6 text-sky-600 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                            {% else %}
                                <span class="text-lg">🧺</span>
                            {% endif %}
                        </div>
                    </div>

                    <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider
                        {% if m.status == 'Available' %} bg-emerald-100 text-emerald-700 
                        {% elif m.status == 'In-Use' %} bg-sky-100 text-sky-700 
                        {% elif m.status == 'Idle' %} bg-rose-100 text-rose-700 
                        {% else %} bg-amber-100 text-amber-800 {% endif %}">
                        {% if m.status == 'In-Use' %}🌀 Spin Cycle Active{% elif m.status == 'Available' %}✨ Ready to Wash{% else %}{{m.status}}{% endif %}
                    </span>
                </div>

                <div class="mt-5 pt-4 border-t border-sky-100 text-sm">
                    {% if m.status == 'In-Use' %}
                        <p class="text-slate-700 font-semibold">User: <strong class="text-slate-900">{{m.current_user_name}}</strong></p>
                        <p class="text-sky-600 font-bold mt-1 flex items-center gap-1">⏱️ {{ format_elapsed(m.start_time) }}</p>
                        <p class="text-xs text-slate-500 mt-1">📞 <a href="tel:{{m.current_user_phone}}" class="underline font-bold text-sky-700">{{m.current_user_phone}}</a></p>
                    {% elif m.status == 'Idle' %}
                        <p class="text-rose-600 font-bold text-xs">🔔 Unload Needed!</p>
                        <p class="text-slate-600 text-xs mt-1">{{m.current_user_name}} (📞 <a href="tel:{{m.current_user_phone}}" class="underline">{{m.current_user_phone}}</a>)</p>
                    {% elif m.status == 'Reserved' %}
                        <p class="text-amber-700 text-xs font-bold">Reserved for {{m.reserved_for_name}}</p>
                        <p class="text-xs text-rose-600 mt-0.5 font-extrabold animate-pulse">⏰ Expires in 5 mins!</p>
                    {% else %}
                        <p class="text-xs text-slate-400 italic">Drum is empty & ready for load</p>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>

        <section class="bg-white/90 backdrop-blur rounded-3xl p-6 shadow-lg border border-sky-100 mb-8">
            <h2 class="text-xl font-extrabold text-slate-900 mb-4 flex items-center gap-2">
                ⏳ Virtual Queue <span class="text-xs font-normal text-sky-600 bg-sky-100 px-2.5 py-0.5 rounded-full font-bold">Soaking...</span>
            </h2>
            <ul class="divide-y divide-sky-100">
                {% for q in queue %}
                <li class="py-3 flex justify-between items-center text-sm">
                    <div class="flex items-center gap-2">
                        <span class="text-lg">👕</span>
                        <div>
                            <span class="font-bold text-slate-900">{{q.name}}</span>
                            <span class="text-slate-400 text-xs ml-1">({{q.phone}})</span>
                        </div>
                    </div>
                    <span class="text-xs font-black px-3 py-1 rounded-full {% if q.status == 'Notified' %} bg-amber-200 text-amber-900 animate-bounce {% else %} bg-sky-100 text-sky-800 {% endif %}">
                        {{ '⭐ Your Turn! (Notified)' if q.status == 'Notified' else 'Waiting in Soap Suds' }}
                    </span>
                </li>
                {% else %}
                <li class="py-6 text-center text-sky-600/70 font-medium text-sm">No clothes waiting in queue right now!</li>
                {% endfor %}
            </ul>
        </section>

        <section class="bg-sky-900 text-white rounded-3xl p-6 text-center shadow-xl">
            <h3 class="text-xs font-bold text-sky-300 uppercase tracking-widest mb-3">🫧 Pick Your Washing Machine 🧼</h3>
            <div class="flex flex-wrap justify-center gap-3">
                {% for m in machines %}
                    <a href="/machine/{{m.id}}" class="bg-sky-500 hover:bg-sky-400 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow transition transform hover:-translate-y-0.5 active:translate-y-0">
                        {{m.name}}
                    </a>
                {% endfor %}
            </div>
        </section>
    </div>
</body>
</html>
"""

MACHINE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{machine.name}} Portal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="https://fav.farm/🧺">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-tr from-sky-200 via-cyan-100 to-indigo-100 text-slate-800 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white/95 backdrop-blur w-full max-w-md rounded-3xl shadow-xl border border-sky-100 p-6 text-center relative overflow-hidden">
        
        <div class="w-16 h-16 rounded-full border-4 border-sky-200 bg-sky-50 mx-auto flex items-center justify-center mb-3 shadow-inner">
            {% if machine.status == 'In-Use' %}
                <svg class="w-9 h-9 text-sky-600 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
            {% else %}
                <span class="text-3xl">🫧</span>
            {% endif %}
        </div>

        <h1 class="text-2xl font-extrabold text-slate-900 mb-1">🧺 {{machine.name}}</h1>
        <p class="text-xs font-bold uppercase tracking-widest text-sky-600 mb-4">{{machine.status}}</p>
        
        {% if machine.status == 'In-Use' %}
            <div class="bg-sky-50 border border-sky-200 rounded-2xl p-3 mb-4 text-sm">
                <p class="text-sky-800 font-extrabold">⏱️ {{ format_elapsed(machine.start_time) }}</p>
                <p class="text-slate-600 text-xs mt-1">In use by <strong>{{machine.current_user_name}}</strong> (<a href="tel:{{machine.current_user_phone}}" class="underline">{{machine.current_user_phone}}</a>)</p>
            </div>
        {% endif %}

        {% if message %}
            <div class="p-3 mb-4 rounded-2xl bg-amber-100 border border-amber-200 text-amber-900 text-xs font-bold">
                {{ message }}
            </div>
        {% endif %}

        <div class="bg-sky-50/50 border border-sky-100 p-4 rounded-2xl text-left">
            <form method="POST" class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-sky-800 uppercase tracking-wider mb-1">Your Name</label>
                    <input type="text" name="name" value="{{ default_name }}" placeholder="e.g. Alex Smith" required class="w-full px-3.5 py-2.5 bg-white border border-sky-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-sm">
                </div>
                
                <div>
                    <label class="block text-xs font-bold text-sky-800 uppercase tracking-wider mb-1">Phone Number</label>
                    <input type="text" name="phone" value="{{ default_phone }}" placeholder="e.g. 9876543210" required class="w-full px-3.5 py-2.5 bg-white border border-sky-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-sm">
                </div>

                <hr class="border-sky-200/60 my-2">

                <div class="space-y-2 pt-1">
                    {% if machine.status in ['Available', 'Reserved'] %}
                        <button type="submit" name="action" value="start" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-black rounded-xl text-sm shadow-md transition transform hover:-translate-y-0.5">
                            🌀 Start Wash Cycle
                        </button>
                    {% endif %}
                    
                    <button type="submit" name="action" value="join_queue" class="w-full py-3 bg-sky-500 hover:bg-sky-600 text-white font-black rounded-xl text-sm shadow-md transition transform hover:-translate-y-0.5">
                        ⏳ Get in Queue
                    </button>
                    
                    <button type="submit" name="action" value="leave_queue" class="w-full py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold rounded-xl text-xs transition">
                        ❌ Leave Queue
                    </button>

                    {% if machine.status in ['In-Use', 'Idle'] %}
                        <button type="submit" name="action" value="clear" class="w-full py-3 bg-rose-500 hover:bg-rose-600 text-white font-black rounded-xl text-sm shadow-md transition transform hover:-translate-y-0.5">
                            ✨ Emptied / Ready for Next Load
                        </button>
                    {% endif %}
                </div>
            </form>
        </div>

        <a class="inline-block mt-5 text-xs text-sky-700 font-bold hover:underline" href="/">⬅️ Back to Main Laundry Dashboard</a>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)