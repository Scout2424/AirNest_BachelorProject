from flask import Flask, request, jsonify, session, send_from_directory, make_response
from flask_cors import CORS
from psycopg2 import pool
import psycopg2
import bcrypt
import csv
import io
import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

#  App & Static Files
app = Flask(__name__, static_folder='.')
app.secret_key = 'sample_text'   

#  CORS
CORS(app, supports_credentials=True, origins=[
    #"http://your-ec2-public-ip",
    #"http://your-ec2-public-ip:8080",
    "https://airnest.duckdns.org"
])


MAIL_SENDER       = "guestguy216@gmail.com"   # mail address
MAIL_APP_PASSWORD = "x"         # Gmail App Password (16 chars), original password only on the base code file
SITE_BASE_URL     = "https://airnest.duckdns.org"
#  Admin Credentials (hardcoded, not in DB)
ADMIN_EMAIL    = "adminuser@admin.com"
ADMIN_PASSWORD = "adminuser14"   # stored plain here — never sent anywhere

def is_admin_session():
    return session.get('is_admin', False)

def require_admin(f):
    """Decorator returns 403 if the caller is not the admin."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin_session():
            return jsonify({'success': False, 'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated


def send_email(to_address, subject, html_body):
    """Send an HTML email via Gmail SMTP (port 587 + STARTTLS). Returns True on success."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = MAIL_SENDER
    msg['To']      = to_address
    msg.attach(MIMEText(html_body, 'html'))
    try:
        print(f"[email] Attempting to send '{subject}' to {to_address} ...")
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(MAIL_SENDER, MAIL_APP_PASSWORD)
            server.sendmail(MAIL_SENDER, to_address, msg.as_string())
        print(f"[email] Sent successfully to {to_address}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[email] AUTH ERROR — wrong Gmail address or App Password: {e}")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"[email] CONNECT ERROR — port 587 blocked (check EC2 outbound rules): {e}")
        return False
    except TimeoutError as e:
        print(f"[email] TIMEOUT — port 587 blocked or unreachable: {e}")
        return False
    except Exception as e:
        print(f"[email] UNEXPECTED ERROR ({type(e).__name__}): {e}")
        return False

#  Database Connection Pool
connection_pool = pool.SimpleConnectionPool(1, 10,
    host     = "website-data.c9maac262wfy.eu-north-1.rds.amazonaws.com",
    database = "website_data",
    user     = "postgres",
    password = "guestguy", #original password only on the base code file 
    port     = 5432,
    options  = "-c search_path=public"
)

def get_conn():
    return connection_pool.getconn()

def put_conn(conn):
    connection_pool.putconn(conn)


#  Static File Serving
@app.route('/')
def root():
    return send_from_directory('.', 'index.html')


#  API — Contact Form
@app.route('/api/contact', methods=['POST'])
def contact():
    data    = request.get_json()
    name    = data.get('name')
    email   = data.get('email')
    subject = data.get('subject')
    message = data.get('message')

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO contact_messages (name, email, subject, message) VALUES (%s, %s, %s, %s)',
            (name, email, subject, message)
        )
        conn.commit()
        cursor.close()
        return jsonify({'success': True})
    except Exception as e:
        print("contact error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  API — Sign Up
#  Saves user as unverified, sends verification email.
@app.route('/api/signup', methods=['POST'])
def signup():
    data       = request.get_json()
    first_name = data.get('first_name')
    last_name  = data.get('last_name')
    email      = data.get('email')
    password   = data.get('password')

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    token  = secrets.token_urlsafe(32)   # secure random verification token

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO users (first_name, last_name, email, password, verified, verify_token)
               VALUES (%s, %s, %s, %s, FALSE, %s)''',
            (first_name, last_name, email, hashed.decode('utf-8'), token)
        )
        conn.commit()
        cursor.close()
    except Exception as e:
        print("signup error:", e)
        return jsonify({'success': False, 'error': 'Email already registered'}), 409
    finally:
        put_conn(conn)

    # Send verification email
    verify_url = f"{SITE_BASE_URL}/api/verify-email/{token}"
    html = f"""
    <div style="font-family:Georgia,serif;max-width:520px;margin:auto;padding:2rem;color:#1e2a3a;">
      <h2 style="font-size:1.4rem;margin-bottom:0.5rem;">Verify your email</h2>
      <p style="color:#6b7f96;margin-bottom:1.5rem;">Hi {first_name}, thanks for signing up!</p>
      <p style="margin-bottom:1.5rem;">Click the button below to verify your email address.
         The link expires in <strong>24 hours</strong>.</p>
      <a href="{verify_url}"
         style="display:inline-block;padding:0.65rem 1.6rem;background:#4a7fa5;color:#fff;
                text-decoration:none;border-radius:6px;font-weight:600;">
        Verify Email
      </a>
      <p style="margin-top:1.5rem;font-size:0.85rem;color:#6b7f96;">
        If you didn't create an account, you can ignore this email.
      </p>
    </div>
    """
    sent = send_email(email, "Verify your email — AirNest", html)
    if not sent:
        # Account was created but email failed — still tell user to check, log the issue
        print(f"WARNING: verification email failed to send to {email}")

    return jsonify({'success': True})


#  API Email Verification
#  User clicks the link in their email → redirects to site with result.
@app.route('/api/verify-email/<token>', methods=['GET'])
def verify_email(token):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM users WHERE verify_token = %s AND verified = FALSE', (token,)
        )
        user = cursor.fetchone()

        if user is None:
            cursor.close()
            # Token invalid or already used — redirect with error flag
            return send_from_directory('.', 'index.html',
                response_class=app.response_class), \
                302, {'Location': f"{SITE_BASE_URL}/index.html?verified=invalid"}

        cursor.execute(
            'UPDATE users SET verified = TRUE, verify_token = NULL WHERE id = %s', (user[0],)
        )
        conn.commit()
        cursor.close()

        # Redirect to sign-up page with success flag so JS can show a toast
        from flask import redirect
        return redirect(f"{SITE_BASE_URL}/sign_up.html?verified=1")
    except Exception as e:
        print("verify-email error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  API  Log In
#  Blocks login if email is not yet verified.
@app.route('/api/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    # Admin shortcut (hardcoded, not in DB) ──
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session['is_admin']  = True
        session['user_name'] = 'Admin'
        return jsonify({'success': True, 'name': 'Admin', 'is_admin': True})

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, first_name, password, verified FROM users WHERE email = %s', (email,)
        )
        user = cursor.fetchone()

        if user is None:
            cursor.close()
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

        if not bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            cursor.close()
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

        if not user[3]:
            cursor.close()
            return jsonify({
                'success': False,
                'error': 'Please verify your email before logging in. Check your inbox.'
            }), 403

        # Record last login time
        now = datetime.utcnow()
        cursor.execute(
            'UPDATE users SET last_login = %s WHERE id = %s', (now, user[0])
        )
        conn.commit()
        cursor.close()

        session['user_id']   = user[0]
        session['user_name'] = user[1]
        session['is_admin']  = False
        return jsonify({'success': True, 'name': user[1], 'is_admin': False})

    except Exception as e:
        print("login error:", e)
        return jsonify({'success': False, 'error': 'Server error'}), 500
    finally:
        put_conn(conn)


#  API  Log Out
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


#  API  Session Check
@app.route('/api/session', methods=['GET'])
def check_session():
    if session.get('is_admin'):
        return jsonify({'logged_in': True, 'name': 'Admin', 'is_admin': True})
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'name': session.get('user_name'), 'is_admin': False})
    return jsonify({'logged_in': False, 'is_admin': False})


#  API  Forgot Password
#  Accepts an email, generates a reset token, sends reset link.
#  Always returns success to avoid revealing whether an email exists.
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data  = request.get_json()
    email = data.get('email', '').strip()

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, first_name FROM users WHERE email = %s AND verified = TRUE', (email,))
        user = cursor.fetchone()

        if user:
            token      = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)

            # Remove any existing tokens for this user, then insert new one
            cursor.execute('DELETE FROM password_reset_tokens WHERE user_id = %s', (user[0],))
            cursor.execute(
                'INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)',
                (user[0], token, expires_at)
            )
            conn.commit()

            reset_url = f"{SITE_BASE_URL}/reset_password.html?token={token}"
            html = f"""
            <div style="font-family:Georgia,serif;max-width:520px;margin:auto;padding:2rem;color:#1e2a3a;">
              <h2 style="font-size:1.4rem;margin-bottom:0.5rem;">Reset your password</h2>
              <p style="color:#6b7f96;margin-bottom:1.5rem;">Hi {user[1]},</p>
              <p style="margin-bottom:1.5rem;">Click the button below to reset your password.
                 The link expires in <strong>1 hour</strong>.</p>
              <a href="{reset_url}"
                 style="display:inline-block;padding:0.65rem 1.6rem;background:#4a7fa5;color:#fff;
                        text-decoration:none;border-radius:6px;font-weight:600;">
                Reset Password
              </a>
              <p style="margin-top:1.5rem;font-size:0.85rem;color:#6b7f96;">
                If you didn't request this, you can ignore this email. Your password won't change.
              </p>
            </div>
            """
            send_email(email, "Reset your password — AirNest", html)

        cursor.close()
        # Always return success so we don't reveal whether the email is registered
        return jsonify({'success': True})
    except Exception as e:
        print("forgot-password error:", e)
        return jsonify({'success': False, 'error': 'Server error'}), 500
    finally:
        put_conn(conn)


#  API  Reset Password
#  Validates the token, updates the password.
@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data     = request.get_json()
    token    = data.get('token', '').strip()
    password = data.get('password', '')

    if len(password) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters.'}), 400

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT user_id FROM password_reset_tokens
               WHERE token = %s AND expires_at > NOW()''',
            (token,)
        )
        row = cursor.fetchone()

        if row is None:
            cursor.close()
            return jsonify({'success': False, 'error': 'This reset link is invalid or has expired.'}), 400

        user_id = row[0]
        hashed  = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed, user_id))
        cursor.execute('DELETE FROM password_reset_tokens WHERE user_id = %s', (user_id,))
        conn.commit()
        cursor.close()
        return jsonify({'success': True})
    except Exception as e:
        print("reset-password error:", e)
        return jsonify({'success': False, 'error': 'Server error'}), 500
    finally:
        put_conn(conn)


#  API  Sensor Data Ingest (from Raspberry Pi)
@app.route('/api/sensor', methods=['POST'])
def receive_sensor():
    data = request.get_json()

    def safe_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sensor_data (
                year, month, day, time,
                neighbourhood, city, country,
                temperature_c, temperature_f, humidity, weather,
                mq135_raw, mq3_raw, mq6_raw, mq7_raw, mq8_raw,
                mq135_v, mq3_v, mq6_v, mq7_v, mq8_v,
                mq135_ppm, mq3_ppm, mq6_ppm, mq7_ppm, mq8_ppm,
                sound_raw, sound_v, sound_events, warning
            ) VALUES (
                %s,%s,%s,%s, %s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s
            )
        """, (
            data.get("Year"),   data.get("Month"),
            data.get("Day"),    data.get("Time"),
            data.get("Neighbourhood"), data.get("City"), data.get("Country"),
            safe_float(data.get("Temperature_C")),
            safe_float(data.get("Temperature_F")),
            safe_float(data.get("Humidity")),
            data.get("Weather"),
            data.get("MQ135_raw"), data.get("MQ3_raw"),
            data.get("MQ6_raw"),   data.get("MQ7_raw"), data.get("MQ8_raw"),
            safe_float(data.get("MQ135_V")), safe_float(data.get("MQ3_V")),
            safe_float(data.get("MQ6_V")),   safe_float(data.get("MQ7_V")),
            safe_float(data.get("MQ8_V")),
            safe_float(data.get("MQ135_ppm")), safe_float(data.get("MQ3_ppm")),
            safe_float(data.get("MQ6_ppm")),   safe_float(data.get("MQ7_ppm")),
            safe_float(data.get("MQ8_ppm")),
            data.get("Sound_raw"),
            safe_float(data.get("Sound_V")),
            data.get("Sound_events"),
            data.get("Warning")
        ))
        conn.commit()
        cursor.close()
        return jsonify({'success': True})
    except Exception as e:
        print("sensor insert error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  API  Sensor Filter Dropdown Values (chained)
#  ?year=2026             returns months available in that year
#  ?year=2026&month=May   returns days available in that year+month
#  No params              returns all years (months/days empty until chosen)
@app.route('/api/sensor-filters', methods=['GET'])
def get_sensor_filters():
    year  = request.args.get('year',  '').strip()
    month = request.args.get('month', '').strip()

    conn = get_conn()
    try:
        cursor = conn.cursor()

        # Years 
        cursor.execute("SELECT DISTINCT year FROM sensor_data ORDER BY year DESC")
        years = [r[0] for r in cursor.fetchall()]

        # Months — filtered by year if provided
        if year:
            cursor.execute(
                "SELECT DISTINCT month FROM sensor_data WHERE year = %s ORDER BY month", (year,)
            )
        else:
            cursor.execute("SELECT DISTINCT month FROM sensor_data ORDER BY month")
        months = [r[0] for r in cursor.fetchall()]

        # Days — filtered by year+month if both provided, year 
        if year and month:
            cursor.execute(
                "SELECT DISTINCT day FROM sensor_data WHERE year = %s AND month = %s ORDER BY day",
                (year, month)
            )
        elif year:
            cursor.execute(
                "SELECT DISTINCT day FROM sensor_data WHERE year = %s ORDER BY day", (year,)
            )
        else:
            cursor.execute("SELECT DISTINCT day FROM sensor_data ORDER BY day")
        days = [r[0] for r in cursor.fetchall()]

        # Location filters — always return all
        cursor.execute("SELECT DISTINCT neighbourhood FROM sensor_data ORDER BY neighbourhood")
        neighbourhoods = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT city FROM sensor_data ORDER BY city")
        cities = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT country FROM sensor_data ORDER BY country")
        countries = [r[0] for r in cursor.fetchall()]

        cursor.close()
        return jsonify({
            'success':        True,
            'years':          years,
            'months':         months,
            'days':           days,
            'neighbourhoods': neighbourhoods,
            'cities':         cities,
            'countries':      countries
        })
    except Exception as e:
        print("sensor-filters error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  API  Sensor Chart Data
@app.route('/api/sensor-data', methods=['GET'])
def get_sensor_data():
    year          = request.args.get('year')
    month         = request.args.get('month')
    day           = request.args.get('day')
    neighbourhood = request.args.get('neighbourhood')
    city          = request.args.get('city')
    country       = request.args.get('country')

    filters = []
    values  = []
    if year:          filters.append("year = %s");          values.append(year)
    if month:         filters.append("month = %s");         values.append(month)
    if day:           filters.append("day LIKE %s");        values.append(f"%{day}%")
    if neighbourhood: filters.append("neighbourhood = %s"); values.append(neighbourhood)
    if city:          filters.append("city = %s");          values.append(city)
    if country:       filters.append("country = %s");       values.append(country)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT time, temperature_c, humidity,
                   mq135_ppm, mq3_ppm, mq6_ppm, mq7_ppm, mq8_ppm,
                   sound_v, sound_events, weather, warning
            FROM sensor_data {where}
            ORDER BY recorded_at ASC
            LIMIT 500
        """, values)
        rows = cursor.fetchall()
        cursor.close()

        keys = [
            "time", "temperature_c", "humidity",
            "mq135_ppm", "mq3_ppm", "mq6_ppm", "mq7_ppm", "mq8_ppm",
            "sound_v", "sound_events", "weather", "warning"
        ]
        return jsonify({'success': True, 'data': [dict(zip(keys, r)) for r in rows]})
    except Exception as e:
        print("sensor-data error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  API  Sensor Record Count
@app.route('/api/sensor-count', methods=['GET'])
def sensor_count():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensor_data")
        count = cursor.fetchone()[0]
        cursor.close()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        print("sensor-count error:", e)
        return jsonify({'success': False}), 500
    finally:
        put_conn(conn)


#  API  CSV Download (login required)
@app.route('/api/download-csv', methods=['GET'])
def download_csv():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Login required'}), 401

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT year, month, day, time,
                   neighbourhood, city, country,
                   temperature_c, temperature_f, humidity, weather,
                   mq135_raw, mq3_raw, mq6_raw, mq7_raw, mq8_raw,
                   mq135_v, mq3_v, mq6_v, mq7_v, mq8_v,
                   mq135_ppm, mq3_ppm, mq6_ppm, mq7_ppm, mq8_ppm,
                   sound_raw, sound_v, sound_events, warning
            FROM sensor_data
            ORDER BY recorded_at ASC
        """)
        rows    = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)

        response = make_response(output.getvalue())
        response.headers['Content-Type']        = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=sensor_data.csv'
        return response
    except Exception as e:
        print("download-csv error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  API  Debug
@app.route('/api/debug', methods=['GET'])
def debug():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT current_database(), current_schema(),
                   current_user, version()
        """)
        row = cursor.fetchone()
        cursor.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'sensor_data'
        """)
        tables = cursor.fetchall()
        cursor.close()
        return jsonify({
            'database':    row[0],
            'schema':      row[1],
            'user':        row[2],
            'version':     row[3],
            'sensor_data_found_in': tables
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        put_conn(conn)


#  ADMIN  Get registered users
#  Optional filters: ?search=name_or_email&from=YYYY-MM-DD&to=YYYY-MM-DD
@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users():
    search    = request.args.get('search', '').strip()
    date_from = request.args.get('from', '').strip()
    date_to   = request.args.get('to', '').strip()

    filters = []
    values  = []
    if search:
        filters.append("(first_name ILIKE %s OR last_name ILIKE %s OR email ILIKE %s)")
        like = f"%{search}%"
        values += [like, like, like]
    if date_from:
        filters.append("created_at >= %s")
        values.append(date_from)
    if date_to:
        filters.append("created_at <= %s")
        values.append(date_to + ' 23:59:59')

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, first_name, last_name, email, verified, created_at, last_login
            FROM users
            {where}
            ORDER BY created_at DESC
        """, values)
        rows = cursor.fetchall()
        cursor.close()
        users = [
            {
                'id':         r[0],
                'first_name': r[1],
                'last_name':  r[2],
                'email':      r[3],
                'verified':   r[4],
                'created_at': r[5].strftime('%Y-%m-%d %H:%M') if r[5] else '—',
                'last_login': r[6].strftime('%Y-%m-%d %H:%M') if r[6] else 'Never'
            }
            for r in rows
        ]
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        print("admin-users error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  ADMIN  Get / Set maintenance mode
@app.route('/api/admin/maintenance', methods=['GET'])
def get_maintenance():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT value FROM site_settings WHERE key = 'maintenance_mode'
        """)
        row = cursor.fetchone()
        cursor.close()
        is_on = bool(row and row[0] == 'true')
        return jsonify({'success': True, 'maintenance': is_on})
    except Exception as e:
        print("get-maintenance error:", e)
        # Table may not exist yet — treat as off so site stays accessible
        return jsonify({'success': True, 'maintenance': False})
    finally:
        put_conn(conn)


@app.route('/api/admin/maintenance', methods=['POST'])
@require_admin
def set_maintenance():
    data  = request.get_json()
    value = 'true' if data.get('maintenance') else 'false'
    conn  = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO site_settings (key, value) VALUES ('maintenance_mode', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (value,))
        conn.commit()
        cursor.close()
        return jsonify({'success': True, 'maintenance': value == 'true'})
    except Exception as e:
        print("set-maintenance error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  ADMIN  Get contact form messages
#  ?order=desc (newest first, default) or ?order=asc (oldest first)
@app.route('/api/admin/messages', methods=['GET'])
@require_admin
def admin_messages():
    order = request.args.get('order', 'desc').strip().lower()
    if order not in ('asc', 'desc'):
        order = 'desc'
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, name, email, subject, message, created_at
            FROM contact_messages
            ORDER BY created_at {order.upper()}
        """)
        rows = cursor.fetchall()
        cursor.close()
        messages = [
            {
                'id':         r[0],
                'name':       r[1],
                'email':      r[2],
                'subject':    r[3],
                'message':    r[4],
                'created_at': r[5].strftime('%Y-%m-%d %H:%M') if r[5] else '—'
            }
            for r in rows
        ]
        return jsonify({'success': True, 'messages': messages})
    except Exception as e:
        print("admin-messages error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  API  Receive Predictions from Raspberry Pi
PREDICTION_SECRET = "airquality2026"   # must match predict.py on the Pi

@app.route('/api/predictions', methods=['POST'])
def receive_predictions():
    if request.headers.get("X-Secret") != PREDICTION_SECRET:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.get_json(force=True)
    rows = data.get("predictions", [])
    if not rows:
        return jsonify({'success': False, 'error': 'Empty predictions'}), 400

    conn = get_conn()
    try:
        cursor = conn.cursor()
        for row in rows:
            cursor.execute("""
                INSERT INTO aq_predictions
                    (date, temp_forecast_c, temp_low_c, temp_high_c,
                     humidity_forecast, danger_predicted, danger_label,
                     danger_probability, is_rainy_forecast, generated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (date) DO UPDATE SET
                    temp_forecast_c    = EXCLUDED.temp_forecast_c,
                    temp_low_c         = EXCLUDED.temp_low_c,
                    temp_high_c        = EXCLUDED.temp_high_c,
                    humidity_forecast  = EXCLUDED.humidity_forecast,
                    danger_predicted   = EXCLUDED.danger_predicted,
                    danger_label       = EXCLUDED.danger_label,
                    danger_probability = EXCLUDED.danger_probability,
                    is_rainy_forecast  = EXCLUDED.is_rainy_forecast,
                    generated_at       = EXCLUDED.generated_at,
                    received_at        = NOW()
            """, (
                row.get("date"),
                row.get("temp_forecast_c"),
                row.get("temp_low_c"),
                row.get("temp_high_c"),
                row.get("humidity_forecast"),
                row.get("danger_predicted"),
                row.get("danger_label"),
                row.get("danger_probability"),
                row.get("is_rainy_forecast"),
                row.get("generated_at"),
            ))
        conn.commit()
        cursor.close()
        return jsonify({'success': True, 'saved': len(rows)})
    except Exception as e:
        print("predictions insert error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


@app.route('/api/predictions', methods=['GET'])
def get_predictions():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, temp_forecast_c, temp_low_c, temp_high_c,
                   humidity_forecast, danger_predicted, danger_label,
                   danger_probability, is_rainy_forecast, generated_at
            FROM aq_predictions
            WHERE date >= CURRENT_DATE::TEXT
            ORDER BY date ASC
            LIMIT 7
        """)
        rows = cursor.fetchall()
        cursor.close()
        keys = ["date", "temp_forecast_c", "temp_low_c", "temp_high_c",
                "humidity_forecast", "danger_predicted", "danger_label",
                "danger_probability", "is_rainy_forecast", "generated_at"]
        return jsonify({'success': True, 'predictions': [dict(zip(keys, r)) for r in rows]})
    except Exception as e:
        print("get-predictions error:", e)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        put_conn(conn)


#  Static File Catch-All 
@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


#  Run
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)