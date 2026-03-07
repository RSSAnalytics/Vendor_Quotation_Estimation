from flask import Flask, flash, render_template, request, redirect, url_for, Response, abort, session, jsonify, make_response
import mysql.connector, base64, os, mimetypes, time, atexit, math, re
from apscheduler.schedulers.background import BackgroundScheduler
from collections import defaultdict
from urllib.parse import quote
from datetime import datetime
from decimal import Decimal
from xhtml2pdf import pisa
from io import BytesIO
from uuid import uuid4


app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.secret_key = os.environ.get("SECRET_KEY", "RSS@123")


# DB_CONFIG = {
#     "host": os.environ.get("DB_HOST", "127.0.0.1"),
#     "user": os.environ.get("DB_USER", "vendor_app"),
#     "password": os.environ.get("DB_PASSWORD", "RSS@123"),
#     "database": os.environ.get("DB_NAME", "vendor_quotation"),
#     "port": int(os.environ.get("DB_PORT", 3306))
# }

DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_NAME"),
    "port": int(os.environ.get("DB_PORT", 3306))
}




def cleanup_old_pdfs(max_age_minutes=30):
    pdf_dir = os.path.join(app.root_path, "static/PDFs")
    now = time.time()
    cutoff = now - (max_age_minutes * 60)
    try:
        for filename in os.listdir(pdf_dir):
            filepath = os.path.join(pdf_dir, filename)
            if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
        print("PDF cleanup done.")
    except Exception as e:
        print(f"Cleanup error: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_old_pdfs, trigger="cron", hour=0, minute=0, kwargs={"max_age_minutes": 10080})
scheduler.start()
atexit.register(lambda: scheduler.shutdown())



buffer_rate = 5

def kodimaram_calculation(Apx_SQFT=0):
    condition_1, cost_1 = "Less than 50", 4500
    condition_2, cost_2 = "50 to 100", 4000
    condition_3, cost_3 = "Above 100", 3750

    if Apx_SQFT < 50:
        cost = cost_1
    elif Apx_SQFT >= 50 and Apx_SQFT <= 100:
        cost = cost_2
    else:
        cost = cost_3
    return condition_1, condition_2, condition_3, cost_1, cost_2, cost_3, cost


cat_quot_tables_dic = {
    'thiruvachi': 'quot_thiruvachi',
    'kavasam': 'quot_kavasam',
    'vahanam': 'quot_vahanam',
    'kodimaram': 'quot_kodimaram',
    'sheet_metal': 'quot_sheet_metal',
    'panchaloha_statue': 'quot_panchaloha_statue'
}


quotation_no_category = {
    'thiruvachi': 'THI',
    'kavasam': 'KAV',
    'vahanam': 'VAH',
    'kodimaram': 'KODI',
    'sheet_metal': 'SH_ME',
    'panchaloha_statue': 'PA_ST'
}


GST_rate_dic = {
    'thiruvachi' : 5,
    'kavasam' : 3,
    'vahanam' : 5,
    'kodimaram' : 5,
    'sheet_metal' : 5,
    'panchaloha_statue' : 5
}


thickness_dic = {
    'gauge_20': '20 Gauge',
    'gauge_22': '22 Gauge',
    'gauge_24': '24 Gauge'
}


delivery_days_dic = {
    'kavasam' : '30 - 45 working days (after wax)',
    'kodimaram' : '60 working days',
    'panchaloha_statue' : '45 working days',

    'thiruvachi' : {
        'Regular' : '15 - 20 working days',
        'Customized' : '30 - 45 working days'
        },

    'vahanam' : {
        'wood' : '30 working days',
        'brass' : '60 working days'
        },

    'sheet_metal' : {
        'below 50 SQFT' : '30 working days',
        '51-150 SQFT' : '45 - 60 working days',
        'above 150 SQFT' : '60 - 90 working days'
        }
}


validity_days_dic = {
    'wood' : '30 days',
    'brass' : '30 days',
    'copper' : '30 days',
    'Silver Platting' : '20 days',
    'Gold Platting' : '20 days',
    'Pure Silver' : '7 days'
}



def format_inr(value):
    if value in (None, ""):
        return ""

    try:
        value = int(float(value))
    except (TypeError, ValueError):
        return value

    s = str(value)

    if len(s) <= 3:
        return s

    last3 = s[-3:]
    rest = s[:-3]

    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]

    if rest:
        parts.insert(0, rest)

    return ",".join(parts) + "," + last3

app.jinja_env.filters["inr"] = format_inr


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def image_to_base64(path):
    mime_type, _ = mimetypes.guess_type(path)
    with open(path, "rb") as img:
        return f"data:{mime_type};base64," + base64.b64encode(img.read()).decode("utf-8")


def link_callback(uri, rel):
    if uri.startswith('file:///'):
        return uri.replace('file:///', '')
    return uri


logo_path = os.path.join(app.root_path, "static/assets/img/RSS_logo.png")
logo_base64 = image_to_base64(logo_path)

base_QR_path = os.path.join(app.root_path, "static/assets/img/QR.jpeg")
base_QR_base64 = image_to_base64(base_QR_path)


##################################################################
########################### INDEX PANEL ##########################
##################################################################

@app.route('/')
def index():
    session.clear()   # removes all keys (admin/user)
    return render_template(r"index.html")


##################################################################
########################### ADMIN PANEL ##########################
##################################################################

########################### ADMIN LOGIN ##########################
@app.route('/admin_login', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, name FROM admin WHERE name=%s AND password=%s",
                (name, password)
            )
            admin = cursor.fetchone()

            if admin:
                session["admin_logged_in"] = True
                session["admin_id"] = admin['id']
                session["admin_name"] = admin['name']
                return redirect(url_for("admin_home"))
            else:
                return render_template(r"admin/login.html", msg="Invalid Admin Username or Password!")

        except mysql.connector.Error as e:
            return render_template(r"admin/login.html", msg=f"DB Error: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template(r"admin/login.html")


########################### ADMIN HOME ##########################
@app.route('/admin_home', methods=["GET"])
def admin_home():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    admin_id = session["admin_id"]
    admin_name = session["admin_name"]
    return render_template(r"admin/home.html")


########################### ADMIN USER DETAILS ##########################
@app.route('/users_details', methods=["GET", "POST"])
def users_details():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        id = request.form.get("id")
        status = request.form.get("status")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""UPDATE users SET status=%s WHERE id=%s""", 
                        (status, id))
            conn.commit()

            cursor.execute("""
                SELECT *
                FROM users
                ORDER BY status ASC
            """)
            data = cursor.fetchall()
            
            return render_template("admin/users.html", data=data, msg="Updated Sucessfully!")

        except mysql.connector.Error as e:
            return render_template("admin/users.html", data=[], msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # -------- GET --------
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM users
            ORDER BY status DESC
        """)
        data = cursor.fetchall()

        return render_template("admin/users.html", data=data)

    except mysql.connector.Error as e:
        return render_template("admin/users.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



# ================= ADMIN USER DETAILS UPDATE =================
@app.route("/user/update/<emp_id>", methods=["POST"])
def user_update(emp_id):
    if not session.get("admin_logged_in"):
        return render_template("index.html", msg="Session expired!")

    name = request.form.get("name")
    email = request.form.get("email")
    mobile = request.form.get("mobile")
    branch = request.form.get("branch")
    password = request.form.get("password")

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            UPDATE 
                users
            SET 
                name=%s,
                email=%s,
                mobile=%s,
                branch=%s,
                password=%s
            WHERE 
                emp_id=%s
        """, (name, email, mobile, branch, password, emp_id))
        conn.commit()

    except Exception as e:
        session['msg'] = f"Update error: {e}"
        
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("users_details"))



# ================= ADMIN USER DETAILS DELETE =================
@app.route("/user/delete/<emp_id>", methods=["POST"])
def user_delete(emp_id):
    if not session.get("admin_logged_in"):
        return render_template("index.html", msg="Session expired.")

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM users WHERE emp_id=%s", (emp_id,))
        conn.commit()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return redirect(url_for("users_details"))



########################### ADMIN THIRUVACHI ##########################
@app.route("/thiruvachi", methods=["GET", "POST"])
def thiruvachi():
    if not session.get("admin_logged_in"):
        return render_template("index.html", msg="Session expired. Please login again.")

    if request.method == "POST":
        name = request.form.get("name")
        leg_breadth = int(request.form.get("leg_breadth"))
        sheet_thick = int(request.form.get("sheet_thick"))
        work_type = request.form.get("work_type")
        work_details = request.form.get("work_details")
        cost = float(request.form.get("cost"))
        images = request.files.getlist("images")

        conn = cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Insert model
            cursor.execute("""
                INSERT INTO cat_thiruvachi
                (name, leg_breadth, sheet_thick, work_type, work_details, cost)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, leg_breadth, sheet_thick, work_type, work_details, cost))
            model_id = cursor.lastrowid

            # Insert images
            for i, file in enumerate(images):
                if file and file.filename:
                    cursor.execute("""
                        INSERT INTO cat_thiruvachi_images
                        (cat_thiruvachi_id, img, img_type, is_primary)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        model_id,
                        file.read(),
                        file.mimetype,
                        1 if i == 0 else 0
                    ))

            conn.commit()

        except mysql.connector.Error as e:
            return render_template("admin/thiruvachi.html", data=[], msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for("thiruvachi"))
    

    # ================= GET =================
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_thiruvachi
            ORDER BY id ASC
        """)
        data = cursor.fetchall()

        cursor.execute("""
            SELECT *
            FROM cat_thiruvachi_rates
        """)
        rate_data = cursor.fetchall()

        if rate_data:
            rate_data = rate_data[0]

        for row in data:
            cursor.execute("""
                SELECT id, img, img_type
                FROM cat_thiruvachi_images
                WHERE cat_thiruvachi_id = %s
                ORDER BY is_primary DESC, id ASC
            """, (row["id"],))

            imgs = cursor.fetchall()
            row["images"] = []

            for img in imgs:
                row["images"].append({
                    "id": img["id"],
                    "b64": base64.b64encode(img["img"]).decode(),
                    "type": img["img_type"]
                })

        msg = session.get('msg')
        session['msg'] = False
        return render_template("admin/thiruvachi.html", 
                                data=data,
                                rate_data=rate_data,
                                msg=msg)

    except mysql.connector.Error as e:
        return render_template("admin/thiruvachi.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================= thiruvachi Rates Update =================
@app.route('/thiruvachi_rates/update/', methods=["POST"])
def thiruvachi_rates():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    silver_rate = int(request.form.get("silver_rate") or 0)
    pure_silver_rate = int(request.form.get("pure_silver_rate") or 0)
    pure_silver_margin_rate = int(request.form.get("pure_silver_margin_rate") or 0)
    gold_rate = int(request.form.get("gold_rate") or 0)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_thiruvachi_rates
        """)
        rate_data = cursor.fetchall()

        if rate_data:
            cursor.execute("""
                UPDATE 
                    cat_thiruvachi_rates 
                SET 
                    gold_rate = %s, 
                    silver_rate = %s, 
                    pure_silver_rate = %s, 
                    pure_silver_margin_rate = %s
                WHERE 
                    id = %s
            """, (gold_rate, silver_rate, pure_silver_rate, pure_silver_margin_rate, 1))
            conn.commit()

        else:
            cursor.execute("""
                INSERT INTO 
                    cat_thiruvachi_rates (
                           gold_rate,
                           silver_rate, 
                           pure_silver_rate, 
                           pure_silver_margin_rate
                           )
                VALUES (%s, %s, %s, %s)
            """, (gold_rate, silver_rate, pure_silver_rate, pure_silver_margin_rate))
            conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("thiruvachi"))


# ================= Thiruvachi Update =================
@app.route("/thiruvachi/update/<int:id>", methods=["POST"])
def thiruvachi_update(id):
    if not session.get("admin_logged_in"):
        return render_template("index.html", msg="Session expired!")

    name = request.form.get("name")
    leg_breadth = int(request.form.get("leg_breadth"))
    sheet_thick = int(request.form.get("sheet_thick"))
    work_type = request.form.get("work_type")
    work_details = request.form.get("work_details")
    cost = float(request.form.get("cost"))

    images = request.files.getlist("images")

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            UPDATE cat_thiruvachi
            SET name=%s,
                leg_breadth=%s,
                sheet_thick=%s,
                work_type=%s,
                work_details=%s,
                cost=%s
            WHERE id=%s
        """, (name, leg_breadth, sheet_thick, work_type, work_details, cost, id))
        conn.commit()

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM cat_thiruvachi_images
            WHERE cat_thiruvachi_id=%s AND is_primary=1
        """, (id,))
        result = cursor.fetchone()
        has_primary = result["cnt"] > 0

        for i, file in enumerate(images):
            if file and file.filename:
                cursor.execute("""
                    INSERT INTO cat_thiruvachi_images
                    (cat_thiruvachi_id, img, img_type, is_primary)
                    VALUES (%s, %s, %s, %s)
                """, (
                    id,
                    file.read(),
                    file.mimetype,
                    1 if (i == 0 and not has_primary) else 0
                ))
        conn.commit()
    
    except Exception as e:
        session['msg'] = f"Update error: {e}"
        
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("thiruvachi"))



# ================= Thiruvachi delete =================
@app.route("/thiruvachi/delete/<int:id>", methods=["POST"])
def thiruvachi_delete(id):
    if not session.get("admin_logged_in"):
        return render_template("index.html", msg="Session expired.")

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM cat_thiruvachi WHERE id=%s", (id,))
        conn.commit()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return redirect(url_for("thiruvachi"))


# ================= Thiruvachi Image Delete =================
@app.route("/thiruvachi/image/delete/<int:image_id>", methods=["POST"])
def thiruvachi_image_delete(image_id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "DELETE FROM cat_thiruvachi_images WHERE id = %s",
            (image_id,)
        )
        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================= Thiruvachi Image Update =================
@app.route("/thiruvachi/image/<int:image_id>")
def thiruvachi_image(image_id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT img, img_type
            FROM cat_thiruvachi_images
            WHERE id = %s
        """, (image_id,))
        row = cursor.fetchone()

        if not row:
            abort(404)

        return Response(row["img"], mimetype=row["img_type"])

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


########################### ADMIN KAVASAM ##########################
@app.route('/kavasam', methods=["GET", "POST"])
def kavasam():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        SQFT = int(request.form.get("SQFT"))
        gauge_24 = int(request.form.get("gauge_24"))
        gauge_22 = int(request.form.get("gauge_22"))
        gauge_20 = int(request.form.get("gauge_20"))
        wax_cost = int(request.form.get("wax_cost"))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                INSERT INTO cat_kavasam
                (SQFT, gauge_24, gauge_22, gauge_20, wax_cost)
                VALUES
                (%s, %s, %s, %s, %s)
                """,
                (SQFT, gauge_24, gauge_22, gauge_20, wax_cost)
            )
            conn.commit()

        except mysql.connector.Error as e:
            if e.errno == 1062:
                session['msg'] = f"SQFT Range {SQFT} already exists!"
            else:
                session['msg'] = f"DB Error: {e}"

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for("kavasam"))

    # -------- GET --------
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_kavasam
            ORDER BY SQFT ASC
        """)
        data = cursor.fetchall()

        cursor.execute("""
            SELECT *
            FROM cat_kavasam_rates
        """)
        rate_data = cursor.fetchall()

        if rate_data:
            rate_data = rate_data[0]

        cursor.execute("""
            SELECT id, img, img_type
            FROM cat_kavasam_images
            ORDER BY is_primary DESC, id ASC
        """)

        kavasam_images = cursor.fetchall()

        images = []
        for img in kavasam_images:
            images.append({
                "id": img["id"],
                "b64": base64.b64encode(img["img"]).decode(),
                "type": img["img_type"]
            })

        msg = session.get('msg')
        session['msg'] = False
        return render_template("admin/kavasam.html",
                                data=data,
                                rate_data=rate_data,
                                images=images,
                                msg=msg
                            )

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================= Kavasam Update =================
@app.route("/kavasam/update/<int:id>", methods=["POST"])
def kavasam_update(id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    SQFT = int(request.form.get("SQFT"))
    gauge_24 = int(request.form.get("gauge_24"))
    gauge_22 = int(request.form.get("gauge_22"))
    gauge_20 = int(request.form.get("gauge_20"))
    wax_cost = int(request.form.get("wax_cost"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            UPDATE 
                cat_kavasam
            SET 
                SQFT = %s, 
                gauge_24 = %s, 
                gauge_22 = %s, 
                gauge_20 = %s, 
                wax_cost = %s
            WHERE 
                id = %s
        """, (SQFT, gauge_24, gauge_22, gauge_20, wax_cost, id))
        conn.commit()

    except mysql.connector.Error as e:
        if e.errno == 1062:
            session['msg'] = f"SQFT Range {SQFT} already exists!"
        else:
            session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("kavasam"))


# ================= Kavasam Delete =================
@app.route("/kavasam/delete/<int:id>", methods=["POST"])
def kavasam_delete(id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM cat_kavasam WHERE id=%s", (id,))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("kavasam"))


# ================= Kavasam Rates Update =================
@app.route('/kavasam_rates/update/', methods=["POST"])
def kavasam_rates():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    silver_rate = int(request.form.get("silver_rate") or 0)
    pure_silver_rate = int(request.form.get("pure_silver_rate") or 0)
    pure_silver_margin_rate = int(request.form.get("pure_silver_margin_rate") or 0)
    gold_rate = int(request.form.get("gold_rate") or 0)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_kavasam_rates
        """)
        rate_data = cursor.fetchall()

        if rate_data:
            cursor.execute("""
                UPDATE 
                    cat_kavasam_rates 
                SET 
                    gold_rate = %s, 
                    silver_rate = %s, 
                    pure_silver_rate = %s, 
                    pure_silver_margin_rate = %s
                WHERE 
                    id = %s
            """, (gold_rate, silver_rate, pure_silver_rate, pure_silver_margin_rate, 1))
            conn.commit()

        else:
            cursor.execute("""
                INSERT INTO 
                    cat_kavasam_rates (
                           gold_rate,
                           silver_rate, 
                           pure_silver_rate, 
                           pure_silver_margin_rate
                           )
                VALUES (%s, %s, %s, %s)
            """, (gold_rate, silver_rate, pure_silver_rate, pure_silver_margin_rate))
            conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("kavasam"))


# ================= Kavasam Images Update =================
@app.route('/kavasam_images/update/', methods=["POST"])
def kavasam_images():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    images = request.files.getlist("images")
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM cat_kavasam_images
            WHERE is_primary = 1
        """)

        result = cursor.fetchone()
        has_primary = result["cnt"] > 0

        for i, file in enumerate(images):
            if file and file.filename:
                cursor.execute("""
                    INSERT INTO cat_kavasam_images
                    (img, img_type, is_primary)
                    VALUES (%s, %s, %s)
                """, (
                    file.read(),
                    file.mimetype,
                    1 if (i == 0 and not has_primary) else 0
                ))
        conn.commit()

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("kavasam"))


# ================= Kavasam Images Delete =================
@app.route("/kavasam/image/delete/<int:image_id>", methods=["POST"])
def kavasam_image_delete(image_id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM cat_kavasam_images WHERE id=%s", (image_id,))
        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


########################### ADMIN VAHANAM ##########################
@app.route('/vahanam', methods=["GET", "POST"])
def vahanam():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        name = request.form.get("name")
        specification = request.form.get("specification", "")

        wood_hgt_1_5ft = int(request.form.get("wood_hgt_1_5ft") or 0)
        wood_hgt_2ft = int(request.form.get("wood_hgt_2ft") or 0)
        wood_hgt_2_5ft = int(request.form.get("wood_hgt_2_5ft") or 0)
        wood_hgt_3ft = int(request.form.get("wood_hgt_3ft") or 0)
        wood_hgt_3_5ft = int(request.form.get("wood_hgt_3_5ft") or 0)
        wood_hgt_4ft = int(request.form.get("wood_hgt_4ft") or 0)
        wood_hgt_5ft = int(request.form.get("wood_hgt_5ft") or 0)

        brass_hgt_1_5ft = int(request.form.get("brass_hgt_1_5ft") or 0)
        brass_hgt_2ft = int(request.form.get("brass_hgt_2ft") or 0)
        brass_hgt_2_5ft = int(request.form.get("brass_hgt_2_5ft") or 0)
        brass_hgt_3ft = int(request.form.get("brass_hgt_3ft") or 0)
        brass_hgt_3_5ft = int(request.form.get("brass_hgt_3_5ft") or 0)
        brass_hgt_4ft = int(request.form.get("brass_hgt_4ft") or 0)
        brass_hgt_5ft = int(request.form.get("brass_hgt_5ft") or 0)

        images = request.files.getlist("images")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                INSERT INTO cat_vahanam
                    (name, specification, wood_hgt_1_5ft, wood_hgt_2ft, wood_hgt_2_5ft, wood_hgt_3ft, wood_hgt_3_5ft, wood_hgt_4ft, wood_hgt_5ft, brass_hgt_1_5ft, brass_hgt_2ft, brass_hgt_2_5ft, brass_hgt_3ft, brass_hgt_3_5ft, brass_hgt_4ft, brass_hgt_5ft)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (name, specification, wood_hgt_1_5ft, wood_hgt_2ft, wood_hgt_2_5ft, wood_hgt_3ft, wood_hgt_3_5ft, wood_hgt_4ft, wood_hgt_5ft, brass_hgt_1_5ft, brass_hgt_2ft, brass_hgt_2_5ft, brass_hgt_3ft, brass_hgt_3_5ft, brass_hgt_4ft, brass_hgt_5ft)
            )
            model_id = cursor.lastrowid

            for i, file in enumerate(images):
                if file and file.filename:
                    cursor.execute("""
                        INSERT INTO cat_vahanam_images
                        (cat_vahanam_id, img, img_type, is_primary)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        model_id,
                        file.read(),
                        file.mimetype,
                        1 if i == 0 else 0
                    ))

            conn.commit()

        except mysql.connector.Error as e:
                session['msg'] = f"DB Error: {e}"

        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        return redirect(url_for("vahanam"))
    
    
    # -------- GET (Display) --------
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_vahanam
        """)
        data = cursor.fetchall()

        for row in data:
            cursor.execute("""
                SELECT id, img, img_type
                FROM cat_vahanam_images
                WHERE cat_vahanam_id = %s
                ORDER BY is_primary DESC, id ASC
            """, (row["id"],))

            imgs = cursor.fetchall()
            row["images"] = []

            for img in imgs:
                row["images"].append({
                    "id": img["id"],
                    "b64": base64.b64encode(img["img"]).decode(),
                    "type": img["img_type"]
                })

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"admin/vahanam.html", data=data, msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"admin/vahanam.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================= Vahanam Update =================
@app.route("/vahanam/update/<int:id>", methods=["POST"])
def vahanam_update(id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    name = request.form.get("name")
    specification = request.form.get("specification", "")

    wood_hgt_1_5ft = int(request.form.get("wood_hgt_1_5ft") or 0)
    wood_hgt_2ft = int(request.form.get("wood_hgt_2ft") or 0)
    wood_hgt_2_5ft = int(request.form.get("wood_hgt_2_5ft") or 0)
    wood_hgt_3ft = int(request.form.get("wood_hgt_3ft") or 0)
    wood_hgt_3_5ft = int(request.form.get("wood_hgt_3_5ft") or 0)
    wood_hgt_4ft = int(request.form.get("wood_hgt_4ft") or 0)
    wood_hgt_5ft = int(request.form.get("wood_hgt_5ft") or 0)

    brass_hgt_1_5ft = int(request.form.get("brass_hgt_1_5ft") or 0)
    brass_hgt_2ft = int(request.form.get("brass_hgt_2ft") or 0)
    brass_hgt_2_5ft = int(request.form.get("brass_hgt_2_5ft") or 0)
    brass_hgt_3ft = int(request.form.get("brass_hgt_3ft") or 0)
    brass_hgt_3_5ft = int(request.form.get("brass_hgt_3_5ft") or 0)
    brass_hgt_4ft = int(request.form.get("brass_hgt_4ft") or 0)
    brass_hgt_5ft = int(request.form.get("brass_hgt_5ft") or 0)

    images = request.files.getlist("images")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            UPDATE 
                cat_vahanam
            SET 
                name = %s,
                specification = %s,
                wood_hgt_1_5ft = %s,
                wood_hgt_2ft = %s,
                wood_hgt_2_5ft = %s,
                wood_hgt_3ft = %s,
                wood_hgt_3_5ft = %s,
                wood_hgt_4ft = %s,
                wood_hgt_5ft = %s,
                brass_hgt_1_5ft = %s,
                brass_hgt_2ft = %s,
                brass_hgt_2_5ft = %s,
                brass_hgt_3ft = %s,
                brass_hgt_3_5ft = %s,
                brass_hgt_4ft = %s,
                brass_hgt_5ft = %s
            WHERE 
                id = %s
        """, (name, specification, wood_hgt_1_5ft, wood_hgt_2ft, wood_hgt_2_5ft, wood_hgt_3ft, wood_hgt_3_5ft, wood_hgt_4ft, wood_hgt_5ft, brass_hgt_1_5ft, brass_hgt_2ft, brass_hgt_2_5ft, brass_hgt_3ft, brass_hgt_3_5ft, brass_hgt_4ft, brass_hgt_5ft, id))

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM cat_vahanam_images
            WHERE cat_vahanam_id=%s AND is_primary=1
        """, (id,))

        result = cursor.fetchone()
        has_primary = result["cnt"] > 0

        for i, file in enumerate(images):
            if file and file.filename:
                cursor.execute("""
                    INSERT INTO cat_vahanam_images
                    (cat_vahanam_id, img, img_type, is_primary)
                    VALUES (%s, %s, %s, %s)
                """, (
                    id,
                    file.read(),
                    file.mimetype,
                    1 if (i == 0 and not has_primary) else 0
                ))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("vahanam"))


# ================= Vahanam Delete =================
@app.route("/vahanam/delete/<int:id>", methods=["POST"])
def vahanam_delete(id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM cat_vahanam WHERE id=%s", (id,))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("vahanam"))


# ================= Vahanam Image Delete =================
@app.route("/vahanam/image/delete/<int:image_id>", methods=["POST"])
def vahanam_image_delete(image_id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "DELETE FROM cat_vahanam_images WHERE id = %s",
            (image_id,)
        )
        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


########################################################################
########################### ADMIN SHEET METAL ##########################
########################################################################
@app.route('/sheet_metal', methods=["GET", "POST"])
def sheet_metal():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        heads = request.form.get("heads")
        work_desc = request.form.get("work_desc", None)
        gauge_20__below_21_SQFT = int(request.form.get("gauge_20__below_21_SQFT") or 0)
        gauge_20__21_50_SQFT = int(request.form.get("gauge_20__21_50_SQFT") or 0)
        gauge_20__above_50_SQFT = int(request.form.get("gauge_20__above_50_SQFT") or 0)
        gauge_22__below_21_SQFT = int(request.form.get("gauge_22__below_21_SQFT") or 0)
        gauge_22__21_50_SQFT = int(request.form.get("gauge_22__21_50_SQFT") or 0)
        gauge_22__above_50_SQFT = int(request.form.get("gauge_22__above_50_SQFT") or 0)
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                INSERT INTO cat_sheet_metal
                (heads, work_desc, gauge_20__below_21_SQFT, gauge_20__21_50_SQFT, gauge_20__above_50_SQFT, gauge_22__below_21_SQFT, gauge_22__21_50_SQFT, gauge_22__above_50_SQFT)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (heads, work_desc, gauge_20__below_21_SQFT, gauge_20__21_50_SQFT, gauge_20__above_50_SQFT, gauge_22__below_21_SQFT, gauge_22__21_50_SQFT, gauge_22__above_50_SQFT)
            )
            conn.commit()

        except mysql.connector.Error as e:
            return render_template(r"admin/sheet_metal.html", data=[], msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        return redirect(url_for("sheet_metal"))
    

    # -------- GET (Display) --------
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_sheet_metal
        """)
        data = cursor.fetchall()

        cursor.execute("""
            SELECT id, img, img_type
            FROM cat_sheet_metal_images
            ORDER BY is_primary DESC, id ASC
        """)

        sheet_metal_images = cursor.fetchall()

        images = []
        for img in sheet_metal_images:
            images.append({
                "id": img["id"],
                "b64": base64.b64encode(img["img"]).decode(),
                "type": img["img_type"]
            })

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"admin/sheet_metal.html", 
                               data=data,
                               images=images, 
                               msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"admin/sheet_metal.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================= Sheet Metal Update =================
@app.route("/sheet_metal/update/<int:id>", methods=["POST"])
def sheet_metal_update(id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    heads = request.form.get("heads")
    work_desc = request.form.get("work_desc", None)
    gauge_20__below_21_SQFT = int(request.form.get("gauge_20__below_21_SQFT") or 0)
    gauge_20__21_50_SQFT = int(request.form.get("gauge_20__21_50_SQFT") or 0)
    gauge_20__above_50_SQFT = int(request.form.get("gauge_20__above_50_SQFT") or 0)
    gauge_22__below_21_SQFT = int(request.form.get("gauge_22__below_21_SQFT") or 0)
    gauge_22__21_50_SQFT = int(request.form.get("gauge_22__21_50_SQFT") or 0)
    gauge_22__above_50_SQFT = int(request.form.get("gauge_22__above_50_SQFT") or 0)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        cursor.execute("""
            UPDATE cat_sheet_metal
            SET heads=%s, work_desc=%s, gauge_20__below_21_SQFT=%s, gauge_20__21_50_SQFT=%s, gauge_20__above_50_SQFT=%s, gauge_22__below_21_SQFT=%s, gauge_22__21_50_SQFT=%s, gauge_22__above_50_SQFT=%s
            WHERE id=%s
        """, (heads, work_desc, gauge_20__below_21_SQFT, gauge_20__21_50_SQFT, gauge_20__above_50_SQFT, gauge_22__below_21_SQFT, gauge_22__21_50_SQFT, gauge_22__above_50_SQFT, id))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("sheet_metal"))


# ================= Sheet Metal Delete =================
@app.route("/sheet_metal/delete/<int:id>", methods=["POST"])
def sheet_metal_delete(id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM cat_sheet_metal WHERE id=%s", (id,))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("sheet_metal"))


# ================= Sheet Metal Images Update =================
@app.route('/sheet_metal_images/update/', methods=["POST"])
def sheet_metal_images():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    images = request.files.getlist("images")

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM cat_sheet_metal_images
            WHERE is_primary = 1
        """)

        result = cursor.fetchone()
        has_primary = result["cnt"] > 0

        for i, file in enumerate(images):
            if file and file.filename:
                cursor.execute("""
                    INSERT INTO cat_sheet_metal_images
                    (img, img_type, is_primary)
                    VALUES (%s, %s, %s)
                """, (
                    file.read(),
                    file.mimetype,
                    1 if (i == 0 and not has_primary) else 0
                ))
        conn.commit()

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("sheet_metal"))


# ================= Sheet Metal Images Delete =================
@app.route("/sheet_metal/image/delete/<int:image_id>", methods=["POST"])
def sheet_metal_image_delete(image_id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM cat_sheet_metal_images WHERE id=%s", (image_id,))
        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    


##############################################################################
########################### ADMIN PANCHALOHA STATUE ##########################
##############################################################################
@app.route('/panchaloha_statue', methods=["GET", "POST"])
def panchaloha_statue():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        name = request.form.get("name")
        prabavali = request.form.get("prabavali")
        position = request.form.get("position")
        model = request.form.get("model")
        hands = int(request.form.get("hands"))
        height = float(request.form.get("height"))
        weight = float(request.form.get("weight"))
        cost = int(request.form.get("cost"))
        images = request.files.getlist("images")
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """INSERT INTO 
                    cat_panchaloha_statue 
                        (name, prabavali, position, model, hands, height, weight, cost) 
                    VALUES 
                        (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, prabavali, position, model, hands, height, weight, cost)
            )
            model_id = cursor.lastrowid

            for i, file in enumerate(images):
                if file and file.filename:
                    cursor.execute("""
                        INSERT INTO cat_panchaloha_statue_images
                        (cat_panchaloha_statue_id, img, img_type, is_primary)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        model_id,
                        file.read(),
                        file.mimetype,
                        1 if i == 0 else 0
                    ))
            conn.commit()

        except mysql.connector.Error as e:
            return render_template(r"admin/panchaloha_statue.html", msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for("panchaloha_statue"))


    # -------- GET (Display) --------
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_panchaloha_statue
        """)
        data = cursor.fetchall()

        for row in data:
            cursor.execute("""
                SELECT id, img, img_type
                FROM cat_panchaloha_statue_images
                WHERE cat_panchaloha_statue_id = %s
                ORDER BY is_primary DESC, id ASC
            """, (row["id"],))

            imgs = cursor.fetchall()
            row["images"] = []

            for img in imgs:
                row["images"].append({
                    "id": img["id"],
                    "b64": base64.b64encode(img["img"]).decode(),
                    "type": img["img_type"]
                })

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"admin/panchaloha_statue.html", get_data=data, msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"admin/panchaloha_statue.html", get_data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================= Panchaloha Statue Update =================
@app.route("/panchaloha_statue/update/<int:id>", methods=["POST"])
def panchaloha_statue_update(id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    name = request.form.get("name")
    prabavali = request.form.get("prabavali")
    position = request.form.get("position")
    model = request.form.get("model")
    hands = int(request.form.get("hands"))
    height = float(request.form.get("height"))
    weight = float(request.form.get("weight"))
    cost = int(request.form.get("cost"))
    images = request.files.getlist("images")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        cursor.execute("""
            UPDATE 
                cat_panchaloha_statue
            SET 
                name=%s,
                prabavali=%s,
                position=%s,
                model=%s,
                hands=%s,
                height=%s,
                weight=%s,
                cost=%s
            WHERE 
                id=%s
        """, (name, prabavali, position, model, hands, height, weight, cost, id))

        if images:
            cursor.execute("""
                SELECT COUNT(*) AS cnt
                FROM cat_panchaloha_statue_images
                WHERE cat_panchaloha_statue_id=%s AND is_primary=1
            """, (id,))

            row = cursor.fetchone()
            has_primary = row["cnt"] > 0

            for i, file in enumerate(images):
                if file and file.filename:
                    cursor.execute("""
                        INSERT INTO cat_panchaloha_statue_images
                        (cat_panchaloha_statue_id, img, img_type, is_primary)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        id,
                        file.read(),
                        file.mimetype,
                        1 if (i == 0 and not has_primary) else 0
                    ))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("panchaloha_statue"))


# ================= Panchaloha Statue Delete =================
@app.route("/panchaloha_statue/delete/<int:id>", methods=["POST"])
def panchaloha_statue_delete(id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM cat_panchaloha_statue WHERE id=%s", (id,))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("panchaloha_statue"))


# ================= Panchaloha Statue Image Delete =================
@app.route("/panchaloha_statue/image/delete/<int:image_id>", methods=["POST"])
def panchaloha_statue_image_delete(image_id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "DELETE FROM cat_panchaloha_statue_images WHERE id = %s",
            (image_id,)
        )
        conn.commit()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================= panchaloha_statue Image Update =================
@app.route("/panchaloha_statue/image/<int:image_id>")
def panchaloha_statue_image(image_id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT img, img_type
            FROM cat_panchaloha_statue_images
            WHERE id = %s
        """, (image_id,))
        row = cursor.fetchone()

        if not row:
            abort(404)

        return Response(row["img"], mimetype=row["img_type"])

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


##############################################################################
############################### ADMIN KODIMARAM ##############################
##############################################################################

    
@app.route('/kodimaram', methods=["GET", "POST"])
def kodimaram():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        name = request.form.get("name")
        sit_or_stand = request.form.get("sit_or_stand")
        position = request.form.get("position")
        height = float(request.form.get("height"))
        hands = int(request.form.get("hands"))
        prabavali = request.form.get("prabavali")
        weight = float(request.form.get("weight"))
        cost = int(request.form.get("cost"))
        images = request.files.getlist("images")
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """INSERT INTO 
                    cat_kodimaram 
                        (name, sit_or_stand, position, height, hands, prabavali, weight, cost) 
                    VALUES 
                        (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, sit_or_stand, position, height, hands, prabavali, weight, cost)
            )
            model_id = cursor.lastrowid

            for i, file in enumerate(images):
                if file and file.filename:
                    cursor.execute("""
                        INSERT INTO cat_kodimaram_images
                        (cat_kodimaram_id, img, img_type, is_primary)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        model_id,
                        file.read(),
                        file.mimetype,
                        1 if i == 0 else 0
                    ))
            conn.commit()

        except mysql.connector.Error as e:
            return render_template(r"admin/kodimaram.html", msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        return redirect(url_for("kodimaram"))


    # -------- GET (Display) --------
    condition_1, condition_2, condition_3, cost_1, cost_2, cost_3, cost = kodimaram_calculation()

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, img, img_type
            FROM cat_kodimaram_images
            ORDER BY is_primary DESC, id ASC
        """)

        kodimaram_images = cursor.fetchall()

        images = []
        for img in kodimaram_images:
            images.append({
                "id": img["id"],
                "b64": base64.b64encode(img["img"]).decode(),
                "type": img["img_type"]
            })

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"admin/kodimaram.html", 
                               images=images,
                               condition_1=condition_1, 
                               condition_2=condition_2, 
                               condition_3=condition_3, 
                               cost_1=cost_1, 
                               cost_2=cost_2, 
                               cost_3=cost_3, 
                               msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"admin/kodimaram.html", get_data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================= Kodimaram Images Update =================
@app.route('/kodimaram_images/update/', methods=["POST"])
def kodimaram_images():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    images = request.files.getlist("images")
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM cat_kodimaram_images
            WHERE is_primary = 1
        """)

        row = cursor.fetchone()
        has_primary = row["cnt"] > 0

        for i, file in enumerate(images):
            if file and file.filename:
                cursor.execute("""
                    INSERT INTO cat_kodimaram_images
                    (img, img_type, is_primary)
                    VALUES (%s, %s, %s)
                """, (
                    file.read(),
                    file.mimetype,
                    1 if (i == 0 and not has_primary) else 0
                ))
        conn.commit()

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("kodimaram"))


# ================= kodimaram Images Delete =================
@app.route("/kodimaram/image/delete/<int:image_id>", methods=["POST"])
def kodimaram_image_delete(image_id):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("DELETE FROM cat_kodimaram_images WHERE id=%s", (image_id,))
        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



##################################################################
########################### USER PANEL ###########################
##################################################################

########################### USER REGISTRATION ###########################
@app.route('/user_register', methods=["GET", "POST"])
def user_register():
    if request.method == "POST":
        name = request.form.get("name")
        emp_id = request.form.get("emp_id")
        email = request.form.get("email")
        mobile = request.form.get("mobile")
        password = request.form.get("password")
        branch = request.form.get("branch")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM users WHERE emp_id=%s",
                (emp_id,)
            )
            emp_id_data = cursor.fetchone()

            if emp_id_data:
                return render_template(r"user/register.html", msg=f"This employee ID ({emp_id}) is already registered!")

            cursor.execute(
                "SELECT * FROM users WHERE email=%s",
                (email,)
            )
            email_data = cursor.fetchone()

            if email_data:
                return render_template(r"user/register.html", msg=f"This Email ({email}) is already registered!")

            cursor.execute(
                """
                INSERT INTO users
                  (name, emp_id, email, mobile, password, branch)
                VALUES
                  (%s, %s, %s, %s, %s, %s)
                """,
                (name, emp_id, email, mobile, password, branch)
            )
            conn.commit()

        except mysql.connector.Error as e:
            return render_template(r"user/register.html", msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return render_template(r"user/register.html", msg=f"Registered successfully! Please wait for admin approval to logIn!")
    return render_template(r"user/register.html")


########################### USER LOGIN ###########################
@app.route('/user_login', methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM users WHERE email=%s AND password=%s",
                (email, password)
            )
            user = cursor.fetchone()

            if user:
                if user['status'] == 'approved':
                    session["user_logged_in"] = True
                    session["user_id"] = user["id"]
                    session["user_name"] = user["name"]
                    session["user_emp_id"] = user["emp_id"]
                    session["user_mobile"] = user["mobile"]
                    session["user_branch"] = user["branch"]
                    session["user_status"] = user["status"]
                    return redirect(url_for("user_home"))
                else:
                    return render_template(r"user/login.html", msg="Admin approval is pending!")
            else:
                return render_template(r"user/login.html", msg="Invalid Email ID or Password!")

        except mysql.connector.Error as e:
            return render_template(r"user/login.html", msg=f"DB Error: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template(r"user/login.html")


########################### USER HOME ###########################
@app.route('/user_home', methods=["GET"])
def user_home():
    if session.get("user_logged_in"):
        user_id = session["user_id"]
        user_name = session["user_name"]
        return render_template(r"user/home.html", user_id=user_id, user_name=user_name)
    else:
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)



########################### USER THIRUVACHI ###########################
@app.route("/user_thiruvachi", methods=["GET", "POST"])
def user_thiruvachi():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)

    no_of_Square_feet = None

    # ------------------- POST -------------------
    if request.method == "POST":
        global delivery_days

        model = int(request.form.get("model"))
        material = request.form.get("material")
        height = float(request.form.get("height"))
        width = float(request.form.get("width"))
        UOM = request.form.get("UOM")

        if UOM == 'Feet':
            no_of_Square_feet = height + width
        else:
            no_of_Square_feet = (height + width) / 12


        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT *
                FROM cat_thiruvachi_rates
            """)
            rate_data = cursor.fetchall()
        
            gold_rate = rate_data[0]['gold_rate']
            silver_rate = rate_data[0]['silver_rate']
            # pure_silver_rate = rate_data[0]['pure_silver_rate']
            # pure_silver_margin_rate = rate_data[0]['pure_silver_margin_rate']


            cursor.execute("""
                SELECT *
                FROM cat_thiruvachi
                WHERE id=%s
                ORDER BY id ASC
            """, (model,))
            data = cursor.fetchall()


            cursor.execute("""
                SELECT id
                FROM cat_thiruvachi
                ORDER BY id ASC
            """)
            model_data = cursor.fetchall()
            

            for row in data:
                cursor.execute("""
                    SELECT id
                    FROM cat_thiruvachi_images
                    WHERE cat_thiruvachi_id = %s
                    ORDER BY is_primary DESC, id ASC
                """, (row["id"],))

                row["image_list"] = cursor.fetchall()

            SQFT = no_of_Square_feet or 0

            if material == "brass":
                base_cost = SQFT * data[0]["cost"]
            elif material == "copper":
                base_cost = SQFT * (data[0]["cost"] * 1.1)  # copper cost = brass cost + 10% of brass cost
            elif material == "Silver Platting":
                base_cost = SQFT * (data[0]["cost"] + silver_rate)
            elif material == "Gold Platting":
                base_cost = SQFT * (data[0]["cost"] + gold_rate)
            # elif material == "Pure Silver":
            #     base_cost = data['pure_silver_rate'] + data['pure_silver_margin_rate'] * ((SQFT * 0.5) * 1000)
            

            buffer_amount = base_cost * buffer_rate / 100
            cost_with_buffer = base_cost + buffer_amount
            GST_amount = cost_with_buffer * GST_rate_dic['thiruvachi'] / 100
            final_cost = round(cost_with_buffer + GST_amount)


            now = datetime.now().strftime("%d-%m-%Y")
            emp_id = session["user_emp_id"]
            date_str = datetime.now().strftime("%Y%m%d")
            time_hhmmss = datetime.now().strftime("%H%M%S")
            quotation_no = f"RSS-{emp_id}-{quotation_no_category['thiruvachi']}-{date_str}-{time_hhmmss}"


            cursor.execute("""
                SELECT *
                FROM customers
                WHERE user_emp_id=%s
                ORDER BY id ASC
            """, (emp_id,))
            customer_data = cursor.fetchall()


            return render_template("user/thiruvachi.html", 
                                    data = data, 
                                    rate_data = rate_data, 
                                    model_data = model_data, 
                                    material = material, 
                                    gold_rate = gold_rate,
                                    silver_rate = silver_rate,
                                    # pure_silver_rate = pure_silver_rate,
                                    # pure_silver_margin_rate = pure_silver_margin_rate,
                                    no_of_Square_feet = no_of_Square_feet,
                                    final_cost = final_cost,
                                    delivery_days = delivery_days_dic['thiruvachi'][data[0]['work_type']],
                                    validity_days = validity_days_dic[material],
                                    now = now,
                                    quotation_no = quotation_no,
                                    customer_data = customer_data,
                                    model_id = model
                                    )                                    

        except mysql.connector.Error as e:
            session['msg'] = f"DB Error: {e}"
            return redirect(url_for("user_thiruvachi"))

        finally:
            if cursor: cursor.close()
            if conn: conn.close()


    # ------------------- GET -------------------
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_thiruvachi
            ORDER BY id ASC
        """)
        data = cursor.fetchall()


        cursor.execute("""
            SELECT id
            FROM cat_thiruvachi
            ORDER BY id ASC
        """)
        model_data = cursor.fetchall()


        for row in data:
            cursor.execute("""
                SELECT id
                FROM cat_thiruvachi_images
                WHERE cat_thiruvachi_id = %s
                ORDER BY is_primary DESC, id ASC
            """, (row["id"],))

            images = cursor.fetchall()
            row["image_list"] = images

        return render_template(
            "user/thiruvachi.html",
            get_data = data,
            model_data = model_data,
            no_of_Square_feet = no_of_Square_feet
        )

    except mysql.connector.Error as e:
        return render_template("user/thiruvachi.html", get_data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/user_thiruvachi_image/<int:image_id>")
def user_thiruvachi_image(image_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT img, img_type
        FROM cat_thiruvachi_images
        WHERE id = %s
    """, (image_id,))

    image = cursor.fetchone()

    cursor.close()
    conn.close()

    if image and image["img"]:
        mime = image["img_type"]

        if mime in ["jpg", "jpeg"]:
            mime = "image/jpeg"
        elif mime == "png":
            mime = "image/png"
        elif mime == "webp":
            mime = "image/webp"
        elif not mime.startswith("image/"):
            mime = "image/jpeg"

        return Response(image["img"], mimetype=mime)

    return "Image not found", 404



@app.route("/thiruvachi/pdf", methods=["POST"])
def thiruvachi_pdf():
    transportation_cost = int(float(request.form.get("transportation_cost") or 0))

    # Cost from form (already includes GST)
    unit = round(Decimal(request.form.get("unit")), 2)
    cost = round(Decimal(request.form.get("cost")), 2)
    unit_price = int(cost / unit)
    total_cost = int(unit_price * unit)
    grand_total = int(cost + transportation_cost)

    material = request.form.get("material")
    name = request.form.get("name")
    leg_breadth = int(request.form.get("leg_breadth"))
    sheet_thick = int(request.form.get("sheet_thick"))
    work_type = request.form.get("work_type")
    work_details = request.form.get("work_details")
    no_of_Square_feet = round(Decimal(request.form.get("no_of_Square_feet")), 2)
    delivery_days = request.form.get("delivery_days")
    validity_days = request.form.get("validity_days")
    now = request.form.get("now")
    quotation_no = request.form.get("quotation_no")
    customer_id_raw = request.form.get("customer_id")

    if not customer_id_raw:
        return jsonify({"error": "Customer not selected"}), 400

    customer_id = int(customer_id_raw)
    model_id = int(request.form.get("model_id"))

    sales_id = session["user_id"]
    sales_emp_id = session["user_emp_id"]
    sales_name = session["user_name"]
    sales_mobile = session["user_mobile"]
    sales_branch = session["user_branch"]
    
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                *
            FROM 
                customers
            WHERE 
                id=%s
        """, (customer_id,))
        customers_data = cursor.fetchall()

        cust_name=customers_data[0]['name']
        cust_mobile=customers_data[0]['mobile']
        temple_name=customers_data[0]['temple']
        address=customers_data[0]['address']

    except mysql.connector.Error as e:
        session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_thiruvachi"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    
    action = request.form.get("submit_action")

    if action == "download_pdf":
        html = render_template(
            "user/pdf/thiruvachi_quotation.html",
            category = "Thiruvachi",
            material = material,
            name = name,
            leg_breadth = leg_breadth,
            sheet_thick = sheet_thick,
            work_type = work_type,
            work_details = work_details,
            no_of_Square_feet = no_of_Square_feet,
            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,
            delivery_days = delivery_days,
            validity_days = validity_days,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,
            now = now,
            quotation_no = quotation_no,
            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64,
        )

        pdf_io = BytesIO()
        pisa.CreatePDF(
            html,
            dest=pdf_io,
            link_callback=link_callback
        )
        response = make_response(pdf_io.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "attachment; filename=Thiruvachi_Quotation.pdf"
        return response
    
    
    elif action == "share_whatsapp":
        wa_cust_mobile = request.form.get("wa_cust_mobile")

        html = render_template(
            "user/pdf/thiruvachi_quotation.html",
            category="Thiruvachi",
            material=material,
            name=name,
            leg_breadth=leg_breadth,
            sheet_thick=sheet_thick,
            work_type=work_type,
            work_details=work_details,
            no_of_Square_feet=no_of_Square_feet,
            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,
            delivery_days=delivery_days,
            validity_days=validity_days,
            cust_name=cust_name,
            cust_mobile=cust_mobile,
            temple_name=temple_name,
            address=address,
            sales_name=sales_name,
            sales_mobile=sales_mobile,
            sales_branch=sales_branch,
            now=now,
            quotation_no=quotation_no,
            logo_path=logo_path,
            logo_base64=logo_base64,
            base_QR_base64=base_QR_base64,
        )

        filename = f"Thiruvachi_Quotation_{uuid4().hex}.pdf"
        pdf_path = os.path.join(app.root_path, "static/PDFs", filename)

        with open(pdf_path, "wb") as f:
            pisa.CreatePDF(html, dest=f, link_callback=link_callback)

        pdf_url = url_for("static", filename=f"PDFs/{filename}", _external=True)

        text = f"😊 Dear {cust_name},\nPlease find your quotation below:\n {pdf_url} \n\n🙏 Thank you for choosing Raja Spiritual"
        whatsapp_url = f"https://wa.me/91{wa_cust_mobile}?text={quote(text)}"

        return jsonify({"whatsapp_url": whatsapp_url})


    elif action == "save_quotation":
        conn = cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO 
                    quot_thiruvachi 
                        (user_emp_id, cust_id, model_id, material, leg_breadth, sheet_thick, work_type, work_details, SQFT, unit, cost, transport_cost, delivery_days, validity_days) 
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (sales_emp_id, customer_id, model_id, material, leg_breadth, sheet_thick, work_type, work_details, no_of_Square_feet, unit, total_cost, transportation_cost, delivery_days, validity_days))
            quot_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO 
                    quotations 
                        (category, quot_id, user_emp_id, cust_id) 
                VALUES 
                    (%s, %s, %s, %s)
            """, ('thiruvachi', quot_id, sales_emp_id, customer_id))
            conn.commit()
        
            flash("Quotation added successfully!", "success")
            return redirect(url_for("user_thiruvachi"))

        except mysql.connector.Error as e:
            session["msg"] = f"DB Error: {e}"
            return redirect(url_for("user_thiruvachi"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        

    


########################### USER KAVASAM ###########################
@app.route('/user_kavasam', methods=["GET", "POST"])
def user_kavasam():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        global thickness

        form = request.form
        measures = {}

        for key, value in form.items():
            if key.startswith("measures"):
                index = int(key.split("[")[1].split("]")[0])
                field = key.split("[")[2].replace("]", "")

                if index not in measures:
                    measures[index] = {}

                measures[index][field] = value

        measures = [measures[i] for i in sorted(measures.keys())]

        total_SQFT = 0
        for m in measures:
            height = float(m["height"])
            width = float(m["width"])

            if m["uom_height"].lower().startswith("feet"):
                deity_height = height * 12
            else:
                deity_height = height

            if m["uom_width"].lower().startswith("feet"):
                deity_width = width * 12
            else:
                deity_width = width

            SQFT = (deity_height * deity_width) / 144
            total_SQFT += SQFT

            m["height_ft"] = float(height)
            m["width_ft"] = float(width)
            m["SQFT"] = float(SQFT)


        if total_SQFT % 1 != 0:
            SQFT_Range = int(total_SQFT) + 1
        else:
            SQFT_Range = int(total_SQFT)
        
        if SQFT_Range > 15:
            SQFT_Range = 15

        thickness = request.form.get("thickness")
        material = request.form.get("material")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(f"""
                SELECT {thickness}, wax_cost
                FROM cat_kavasam
                WHERE SQFT=%s
            """, (SQFT_Range,))
            cost = cursor.fetchone()
            wax_cost = cost['wax_cost']
            cost = cost[thickness]

            cursor.execute("""
                SELECT *
                FROM cat_kavasam_rates
            """)
            rate_data = cursor.fetchall()


            if rate_data:
                rate_data = rate_data[0]
            else:
                flash("Admin still not added price information!", "danger")
                return render_template("user/kavasam.html")

            if material == 'brass':
                base_cost = total_SQFT * cost
            elif material == 'copper':
                base_cost = total_SQFT * (cost * 1.1) # copper cost = brass cost + 10% of brass cost
            elif material == 'Silver Platting':
                base_cost = total_SQFT * (cost + (cost * 0.1) + rate_data['silver_rate'])
            elif material == 'Gold Platting':
                base_cost = total_SQFT * (cost + (cost * 0.1) + rate_data['gold_rate'])
            elif material == 'Pure Silver':
                if thickness == 'gauge_24':  
                    base_cost = rate_data['pure_silver_rate'] + rate_data['pure_silver_margin_rate'] * ((total_SQFT * 0.5) * 1000)
                elif thickness == 'gauge_22':
                    base_cost = rate_data['pure_silver_rate'] + rate_data['pure_silver_margin_rate'] * ((total_SQFT * 0.625) * 1000)
                elif thickness == 'gauge_20':
                    base_cost = rate_data['pure_silver_rate'] + rate_data['pure_silver_margin_rate'] * ((total_SQFT * 0.75) * 1000)


            base_cost = base_cost + wax_cost
            buffer_amount = base_cost * buffer_rate / 100
            cost_with_buffer = base_cost + buffer_amount
            GST_amount = cost_with_buffer * GST_rate_dic['kavasam'] / 100
            final_cost = round(cost_with_buffer + GST_amount)

        
            now = datetime.now().strftime("%d-%m-%Y")
            date_str = datetime.now().strftime("%Y%m%d")
            emp_id = session["user_emp_id"]
            time_hhmmss = datetime.now().strftime("%H%M%S")
            quotation_no = f"RSS-{emp_id}-{quotation_no_category['kavasam']}-{date_str}-{time_hhmmss}"


            cursor.execute("""
                SELECT *
                FROM customers
                WHERE user_emp_id=%s
                ORDER BY id ASC
            """, (emp_id,))
            customer_data = cursor.fetchall()

            return render_template("user/kavasam.html", 
                                final_cost = int(final_cost),
                                wax_cost = wax_cost,
                                rate_data = rate_data, 
                                SQFT_Range = SQFT_Range, 
                                total_SQFT = total_SQFT,
                                material = material,
                                thickness = thickness_dic[thickness],
                                validity_days = validity_days_dic[material],
                                delivery_days = delivery_days_dic['kavasam'],
                                now = now,
                                quotation_no = quotation_no,
                                customer_data = customer_data)

        except mysql.connector.Error as e:
            return render_template("user/kavasam.html", data=[], msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()


    # ------------------- GET -------------------
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM cat_kavasam_images")
        images = cursor.fetchall()

        for img in images:
            if img["img"]:
                img["img_b64"] = base64.b64encode(img["img"]).decode("utf-8")
            else:
                img["img_b64"] = ""

        msg = session.get('msg')
        session['msg'] = False
        return render_template("user/kavasam.html", images = images, msg = msg)

    except mysql.connector.Error as e:
        return render_template("user/kavasam.html", msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/kavasam_image/<int:image_id>")
def kavasam_image(image_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT img, img_type FROM cat_kavasam_images WHERE id=%s", (image_id,))
    image = cursor.fetchone()

    cursor.close()
    conn.close()

    if image and image["img"]:
        mime = image["img_type"]

        # 🔥 Fix incorrect mime types
        if mime in ["jpg", "jpeg"]:
            mime = "image/jpeg"
        elif mime == "png":
            mime = "image/png"
        elif mime == "webp":
            mime = "image/webp"
        elif not mime.startswith("image/"):
            mime = "image/jpeg"  # fallback

        return Response(
                        image["img"],
                        mimetype=mime,
                        headers={
                            "Cache-Control": "no-store"
                        })
    return "Image not found", 404



@app.route("/kavasam/pdf", methods=["POST"])
def kavasam_pdf():
    wax_cost = int(float(request.form.get("wax_cost") or 0))
    transportation_cost = int(float(request.form.get("transportation_cost") or 0))

    # Cost from form (already includes GST)
    unit = round(Decimal(request.form.get("unit")), 2)
    cost = round(Decimal(request.form.get("cost")), 2)
    unit_price = int(cost / unit)
    total_cost = int(unit_price * unit)
    grand_total = int(cost + transportation_cost + wax_cost)

    material = request.form.get("material")
    thickness = request.form.get("thickness")
    thickness = int(thickness[:2])
    total_SQFT = round(Decimal(request.form.get("total_SQFT")), 2)
    delivery_days = request.form.get("delivery_days")
    validity_days = request.form.get("validity_days")
    now = request.form.get("now")
    quotation_no = request.form.get("quotation_no")
    customer_id_raw = request.form.get("customer_id")

    if not customer_id_raw:
        return jsonify({"error": "Customer not selected"}), 400

    customer_id = int(customer_id_raw)

    sales_id = session["user_id"]
    sales_emp_id = session["user_emp_id"]
    sales_name = session["user_name"]
    sales_mobile = session["user_mobile"]
    sales_branch = session["user_branch"]
    
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                *
            FROM 
                customers
            WHERE 
                id=%s
        """, (customer_id,))
        customers_data = cursor.fetchall()

        cust_name = customers_data[0]['name']
        cust_mobile = customers_data[0]['mobile']
        temple_name = customers_data[0]['temple']
        address = customers_data[0]['address']

    except mysql.connector.Error as e:
        session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_kavasam"))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    
    action = request.form.get("submit_action")

    if action == "download_pdf":
        html = render_template(
            "user/pdf/kavasam_quotation.html",
            category = "kavasam",
            material = material,
            sheet_thick = thickness,
            no_of_Square_feet = total_SQFT,
            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            wax_cost = wax_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,
            delivery_days = delivery_days,
            validity_days = validity_days,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,
            now = now,
            quotation_no = quotation_no,
            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64,
        )

        pdf_io = BytesIO()
        pisa.CreatePDF(
            html,
            dest=pdf_io,
            link_callback=link_callback
        )
        response = make_response(pdf_io.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "attachment; filename=kavasam_Quotation.pdf"
        return response
    
    
    elif action == "share_whatsapp":
        wa_cust_mobile = request.form.get("wa_cust_mobile")

        html = render_template(
            "user/pdf/kavasam_quotation.html",
            category="kavasam",
            material=material,
            sheet_thick=thickness,
            no_of_Square_feet=total_SQFT,
            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            wax_cost = wax_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,
            delivery_days=delivery_days,
            validity_days=validity_days,
            cust_name=cust_name,
            cust_mobile=cust_mobile,
            temple_name=temple_name,
            address=address,
            sales_name=sales_name,
            sales_mobile=sales_mobile,
            sales_branch=sales_branch,
            now=now,
            quotation_no=quotation_no,
            logo_path=logo_path,
            logo_base64=logo_base64,
            base_QR_base64=base_QR_base64,
        )

        filename = f"kavasam_Quotation_{uuid4().hex}.pdf"
        pdf_path = os.path.join(app.root_path, "static/PDFs", filename)

        with open(pdf_path, "wb") as f:
            pisa.CreatePDF(html, dest=f, link_callback=link_callback)

        pdf_url = url_for("static", filename=f"PDFs/{filename}", _external=True)

        text = f"😊 Dear {cust_name},\nPlease find your quotation below:\n {pdf_url} \n\n🙏 Thank you for choosing Raja Spiritual"
        whatsapp_url = f"https://wa.me/91{wa_cust_mobile}?text={quote(text)}"
        return jsonify({"whatsapp_url": whatsapp_url})


    elif action == "save_quotation":
        conn = cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO 
                    quot_kavasam 
                        (user_emp_id, cust_id, material, sheet_thick, SQFT, unit, cost, wax_cost, transport_cost, delivery_days, validity_days) 
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (sales_emp_id, customer_id, material, thickness, total_SQFT, unit, total_cost, wax_cost, transportation_cost, delivery_days, validity_days))
            quot_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO 
                    quotations 
                        (category, quot_id, user_emp_id, cust_id) 
                VALUES 
                    (%s, %s, %s, %s)
            """, ('kavasam', quot_id, sales_emp_id, customer_id))
            conn.commit()
        
            flash("Quotation added successfully!", "success")
            return redirect(url_for("user_kavasam"))

        except mysql.connector.Error as e:
            session["msg"] = f"DB Error: {e}"
            return redirect(url_for("user_kavasam"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    flash("Invalid action submitted!", "danger")
    return redirect(url_for("user_kavasam"))




########################### USER VAHANAM ###########################
@app.route('/user_vahanam', methods=["GET", "POST"])
def user_vahanam():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    msg = None
    if request.method == "POST":
        name = request.form.get("name")
        height = float(request.form.get("height")) or 0
        material = request.form.get("material")

        if height <= 1.5:
            sta_hgt = '1_5'
        elif height <= 2:
            sta_hgt = '2'
        elif height <= 2.5:
            sta_hgt = '2_5'
        elif height <= 3:
            sta_hgt = '3'
        elif height <= 3.5:
            sta_hgt = '3_5'
        elif height <= 4:
            sta_hgt = '4'
        else:
            sta_hgt = '5'
        
        height_col = f"{material}_hgt_{sta_hgt}ft"


        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(f"""
                SELECT name, specification, {height_col}
                FROM cat_vahanam
                WHERE UPPER(name)=UPPER(%s)
            """, (name,))
            data = cursor.fetchall()

            specification = data[0]['specification']
            base_cost = int(data[0][height_col])

            buffer_amount = base_cost * buffer_rate / 100
            cost_with_buffer = base_cost + buffer_amount
            GST_amount = cost_with_buffer * GST_rate_dic['vahanam'] / 100
            final_cost = round(cost_with_buffer + GST_amount)


            now = datetime.now().strftime("%d-%m-%Y")
            emp_id = session["user_emp_id"]
            date_str = datetime.now().strftime("%Y%m%d")
            time_hhmmss = datetime.now().strftime("%H%M%S")
            quotation_no = f"RSS-{emp_id}-{quotation_no_category['vahanam']}-{date_str}-{time_hhmmss}"


            cursor.execute("""
                SELECT *
                FROM customers
                WHERE user_emp_id=%s
                ORDER BY id ASC
            """, (emp_id,))
            customer_data = cursor.fetchall()
            
            return render_template(r"user/vahanam.html", 
                                    name = name,
                                    specification = specification,
                                    material = material,
                                    height = height,
                                    cost = final_cost,
                                    delivery_days = delivery_days_dic['vahanam'][material],
                                    validity_days = validity_days_dic[material],
                                    now = now,
                                    quotation_no = quotation_no,
                                    customer_data = customer_data)

        except mysql.connector.Error as e:
                session['msg'] = f"DB Error: {e}"
                return redirect(url_for("user_vahanam"))

        finally:
            if cursor: cursor.close()
            if conn: conn.close()


    # ------------------- GET -------------------
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_vahanam
            ORDER BY id ASC
        """)
        data = cursor.fetchall()


        for row in data:
            cursor.execute("""
                SELECT id
                FROM cat_vahanam_images
                WHERE cat_vahanam_id = %s
                ORDER BY is_primary DESC, id ASC
            """, (row["id"],))

            images = cursor.fetchall()
            row["image_list"] = images

        msg = session.get('msg')
        session['msg'] = False
        return render_template("user/vahanam.html", images = data, msg = msg)

    except mysql.connector.Error as e:
        return render_template("user/vahanam.html", get_data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



@app.route("/user_vahanam_image/<int:image_id>")
def user_vahanam_image(image_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT img, img_type
        FROM cat_vahanam_images
        WHERE id = %s
    """, (image_id,))

    image = cursor.fetchone()

    cursor.close()
    conn.close()

    if image and image["img"]:
        mime = image["img_type"]

        if mime in ["jpg", "jpeg"]:
            mime = "image/jpeg"
        elif mime == "png":
            mime = "image/png"
        elif mime == "webp":
            mime = "image/webp"
        elif not mime.startswith("image/"):
            mime = "image/jpeg"

        return Response(image["img"], mimetype=mime)
    return "Image not found", 404



@app.route("/vahanam/pdf", methods=["POST"])
def vahanam_pdf():

    sales_id = session["user_id"]
    sales_emp_id = session["user_emp_id"]
    sales_name = session["user_name"]
    sales_mobile = session["user_mobile"]
    sales_branch = session["user_branch"]

    name = request.form.get("name")
    material = request.form.get("material")
    specification = request.form.get("specification")
    height = round(Decimal(request.form.get("height")), 2)
    delivery_days = request.form.get("delivery_days")
    validity_days = request.form.get("validity_days")
    now = request.form.get("now")
    quotation_no = request.form.get("quotation_no")
    customer_id_raw = request.form.get("customer_id")
    
    if not customer_id_raw:
        return jsonify({"error": "Customer not selected"}), 400
    else:
        customer_id = int(customer_id_raw)


    unit = round(Decimal(request.form.get("unit")), 2)
    cost = int(request.form.get("cost") or 0)
    transportation_cost = int(request.form.get("transportation_cost") or 0)

    unit_price = int(cost / unit)
    total_cost = int(unit_price * unit)
    grand_total = int(total_cost + transportation_cost)

    
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                *
            FROM 
                customers
            WHERE 
                id=%s
        """, (customer_id,))
        customers_data = cursor.fetchall()

        cust_name=customers_data[0]['name']
        cust_mobile=customers_data[0]['mobile']
        temple_name=customers_data[0]['temple']
        address=customers_data[0]['address']

    except mysql.connector.Error as e:
        session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_vahanam"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    action = request.form.get("submit_action")

    if action == "download_pdf":
        html = render_template(
            "user/pdf/vahanam_quotation.html",
            category = "vahanam",
            name = name,
            material = material,
            specification = specification,
            height = height,
            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,
            delivery_days = delivery_days,
            validity_days = validity_days,
            now = now,
            quotation_no = quotation_no,
            customer_id = customer_id,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,
            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64
        )

        pdf_io = BytesIO()
        pisa.CreatePDF(
            html,
            dest=pdf_io,
            link_callback=link_callback
        )
        response = make_response(pdf_io.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "attachment; filename=Vahanam_Quotation.pdf"
        return response
    
    
    elif action == "share_whatsapp":
        wa_cust_mobile = request.form.get("wa_cust_mobile")

        html = render_template(
            "user/pdf/vahanam_quotation.html",
            category = "vahanam",
            name = name,
            material = material,
            specification = specification,
            height = height,
            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,
            delivery_days = delivery_days,
            validity_days = validity_days,
            now = now,
            quotation_no = quotation_no,
            customer_id = customer_id,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,
            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64
        )

        filename = f"Vahanam_Quotation_{uuid4().hex}.pdf"
        pdf_path = os.path.join(app.root_path, "static/PDFs", filename)

        with open(pdf_path, "wb") as f:
            pisa.CreatePDF(html, dest=f, link_callback=link_callback)

        pdf_url = url_for("static", filename=f"PDFs/{filename}", _external=True)

        text = f"😊 Dear {cust_name},\nPlease find your quotation below:\n {pdf_url} \n\n🙏 Thank you for choosing Raja Spiritual"
        whatsapp_url = f"https://wa.me/91{wa_cust_mobile}?text={quote(text)}"
        return jsonify({"whatsapp_url": whatsapp_url})


    elif action == "save_quotation":
        conn = cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO 
                    quot_vahanam 
                        (user_emp_id, cust_id, name, specification, material, height, unit, cost, transport_cost, delivery_days, validity_days)
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (sales_emp_id, customer_id, name, specification, material, height, unit, total_cost, transportation_cost, delivery_days, validity_days))
            quot_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO 
                    quotations 
                        (category, quot_id, user_emp_id, cust_id) 
                VALUES 
                    (%s, %s, %s, %s)
            """, ('vahanam', quot_id, sales_emp_id, customer_id))
            conn.commit()
        
            flash("Quotation added successfully!", "success")
            return redirect(url_for("user_vahanam"))

        except mysql.connector.Error as e:
            session["msg"] = f"DB Error: {e}"
            return redirect(url_for("user_vahanam"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()



########################### USER KODIMARAM ###########################
@app.route('/user_kodimaram', methods=["GET", "POST"])
def user_kodimaram():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    material = "brass"
    thickness = "20 Gauge"
    
    data = None
    if request.method == "POST":
        height = float(request.form.get("height"))
        UOM_height = request.form.get("UOM_height")

        diameter = float(request.form.get("diameter"))
        UOM_type = request.form.get("UOM_type")
        UOM_measure = request.form.get("UOM_measure")

        if UOM_type == 'cir':
            circumference = diameter
            diameter = circumference / math.pi


        if UOM_height == 'Feet':
            deity_height = height * 12
        else:
            deity_height = height


        if UOM_measure == 'Feet':
            deity_diameter = diameter * 12
        else:
            deity_diameter = diameter


        Batmam_Hgt_perc = 8
        Batmam_Hgt = (deity_height * Batmam_Hgt_perc) / 100
        Batmam_Dia_perc = 270
        Batmam_Dia = (deity_diameter * Batmam_Dia_perc) / 100
        Batmam_KM_SQFT = (Batmam_Dia * 3) * Batmam_Hgt / 144

        Small_Arada_1_Hgt_perc = 3
        Small_Arada_1_Hgt = (deity_height * Small_Arada_1_Hgt_perc) / 100
        Small_Arada_1_Dia_perc = 117
        Small_Arada_1_Dia = (deity_diameter * Small_Arada_1_Dia_perc) / 100
        Small_Arada_1_KM_SQFT = (Small_Arada_1_Dia * 3) * Small_Arada_1_Hgt / 144

        Arada_Hgt_perc = 10
        Arada_Hgt = (deity_height * Arada_Hgt_perc) / 100
        Arada_Dia_perc = 200
        Arada_Dia = (deity_diameter * Arada_Dia_perc) / 100
        Arada_KM_SQFT = (Arada_Dia * 3) * Arada_Hgt / 144

        Small_Arada_2_Hgt_perc = 3
        Small_Arada_2_Hgt = (deity_height * Small_Arada_2_Hgt_perc) / 100
        Small_Arada_2_Dia_perc = 117
        Small_Arada_2_Dia = (deity_diameter * Small_Arada_2_Dia_perc) / 100
        Small_Arada_2_KM_SQFT = (Small_Arada_2_Dia * 3) * Small_Arada_2_Hgt / 144

        Box_Hgt_perc = 8
        Box_Hgt = (deity_height * Box_Hgt_perc) / 100
        Box_Dia_perc = 120
        Box_Dia = (deity_diameter * Box_Dia_perc) / 100
        Box_KM_SQFT = (Box_Dia * 4) * Box_Hgt / 144

        Nagabanthanam_1_Hgt_perc = 3
        Nagabanthanam_1_Hgt = (deity_height * Nagabanthanam_1_Hgt_perc) / 100
        Nagabanthanam_1_Dia_perc = 110
        Nagabanthanam_1_Dia = (deity_diameter * Nagabanthanam_1_Dia_perc) / 100
        Nagabanthanam_1_KM_SQFT = (Nagabanthanam_1_Dia * 3) * Nagabanthanam_1_Hgt / 144

        Kuvalai_Hgt_perc = 39.5
        Kuvalai_Hgt = (deity_height * Kuvalai_Hgt_perc) / 100
        Kuvalai_Dia_perc = 105
        Kuvalai_Dia = (deity_diameter * Kuvalai_Dia_perc) / 100
        Kuvalai_KM_SQFT = (Kuvalai_Dia * 3) * Kuvalai_Hgt / 144

        Nagabanthanam_2_Hgt_perc = 3
        Nagabanthanam_2_Hgt = (deity_height * Nagabanthanam_2_Hgt_perc) / 100
        Nagabanthanam_2_Dia_perc = 110
        Nagabanthanam_2_Dia = (deity_diameter * Nagabanthanam_2_Dia_perc) / 100
        Nagabanthanam_2_KM_SQFT = (Nagabanthanam_2_Dia * 3) * Nagabanthanam_2_Hgt / 144

        manipalagai_Hgt_perc = 1.5
        manipalagai_Hgt = (deity_height * manipalagai_Hgt_perc) / 100
        manipalagai_Dia_perc = 200
        manipalagai_Dia = (deity_diameter * manipalagai_Dia_perc) / 100
        manipalagai_KM_SQFT = (manipalagai_Dia * manipalagai_Dia / 144) + (manipalagai_Dia * manipalagai_Dia / 144)

        kalasam_Hgt_perc = 6
        kalasam_Hgt = (deity_height * kalasam_Hgt_perc) / 100
        kalasam_Dia_perc = 0
        kalasam_Dia = (deity_diameter * kalasam_Dia_perc) / 100

        Visiribalagai_Hgt_perc = 15
        Visiribalagai_Hgt = (deity_height * Visiribalagai_Hgt_perc) / 100
        Visiribalagai_Dia_perc = 423
        Visiribalagai_Dia = (deity_diameter * Visiribalagai_Dia_perc) / 100

        Visiribalagai_side_Hgt_perc = 0
        Visiribalagai_side_Hgt = (deity_height * Visiribalagai_side_Hgt_perc) / 100
        Visiribalagai_side_Dia_perc = 110
        Visiribalagai_side_Dia = (deity_diameter * Visiribalagai_side_Dia_perc) / 100
        
        Visiribalagai_VB_SQFT = ((Visiribalagai_Dia * Visiribalagai_side_Dia) * 6) / 144
        Visiribalagai_side_VB_SQFT = ((Visiribalagai_Dia * Visiribalagai_side_Dia) * 6) * 0.4 / 144
        
        Total_Hgt = Batmam_Hgt + Small_Arada_1_Hgt + Arada_Hgt + Small_Arada_2_Hgt + Box_Hgt + Nagabanthanam_1_Hgt + Kuvalai_Hgt + Nagabanthanam_2_Hgt + manipalagai_Hgt + kalasam_Hgt + Visiribalagai_Hgt + Visiribalagai_side_Hgt
        
        Total_Dia = Batmam_Dia + Small_Arada_1_Dia + Arada_Dia + Small_Arada_2_Dia + Box_Dia + Nagabanthanam_1_Dia + Kuvalai_Dia + Nagabanthanam_2_Dia + manipalagai_Dia + kalasam_Dia + Visiribalagai_Dia + Visiribalagai_side_Dia

        Total_KM_SQFT = Batmam_KM_SQFT + Small_Arada_1_KM_SQFT + Arada_KM_SQFT + Small_Arada_2_KM_SQFT + Box_KM_SQFT + Nagabanthanam_1_KM_SQFT + Kuvalai_KM_SQFT + Nagabanthanam_2_KM_SQFT + manipalagai_KM_SQFT

        Total_VB_SQFT = Visiribalagai_VB_SQFT + Visiribalagai_side_VB_SQFT 

        Apx_SQFT = Total_KM_SQFT + Total_VB_SQFT
        Apx_Wgt = Apx_SQFT * 0.9

        condition_1, condition_2, condition_3, cost_1, cost_2, cost_3, cost = kodimaram_calculation(Apx_SQFT)

        total_cost = Apx_SQFT * cost
        buffer_amount = total_cost * buffer_rate / 100
        final_cost = total_cost + buffer_amount # For kodimaram GST already added in price. So need to add now


        now = datetime.now().strftime("%d-%m-%Y")
        emp_id = session["user_emp_id"]
        date_str = datetime.now().strftime("%Y%m%d")
        time_hhmmss = datetime.now().strftime("%H%M%S")
        quotation_no = f"RSS-{emp_id}-{quotation_no_category['kodimaram']}-{date_str}-{time_hhmmss}"

        sales_id = session["user_id"]
        sales_emp_id = session["user_emp_id"]
        sales_name = session["user_name"]
        sales_mobile = session["user_mobile"]
        sales_branch = session["user_branch"]

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT *
                FROM customers
                WHERE user_emp_id=%s
                ORDER BY id ASC
            """, (emp_id,))
            customer_data = cursor.fetchall()

            return render_template(r"user/kodimaram.html", 
                                        sales_id = sales_id,
                                        sales_emp_id = sales_emp_id,
                                        sales_name = sales_name,
                                        sales_mobile = sales_mobile,
                                        sales_branch = sales_branch,
                                        customer_data = customer_data,

                                        height = deity_height,
                                        diameter = deity_diameter,

                                        Batmam_Hgt_perc = Batmam_Hgt_perc,
                                        Batmam_Hgt = Batmam_Hgt,
                                        Batmam_Dia_perc = Batmam_Dia_perc,
                                        Batmam_Dia = Batmam_Dia,
                                        Batmam_KM_SQFT = Batmam_KM_SQFT,
                                        Small_Arada_1_Hgt_perc = Small_Arada_1_Hgt_perc,
                                        Small_Arada_1_Hgt = Small_Arada_1_Hgt,
                                        Small_Arada_1_Dia_perc = Small_Arada_1_Dia_perc,
                                        Small_Arada_1_Dia = Small_Arada_1_Dia,
                                        Small_Arada_1_KM_SQFT = Small_Arada_1_KM_SQFT,
                                        Arada_Hgt_perc = Arada_Hgt_perc,
                                        Arada_Hgt = Arada_Hgt,
                                        Arada_Dia_perc = Arada_Dia_perc,
                                        Arada_Dia = Arada_Dia,
                                        Arada_KM_SQFT = Arada_KM_SQFT,
                                        Small_Arada_2_Hgt_perc = Small_Arada_2_Hgt_perc,
                                        Small_Arada_2_Hgt = Small_Arada_2_Hgt,
                                        Small_Arada_2_Dia_perc = Small_Arada_2_Dia_perc,
                                        Small_Arada_2_Dia = Small_Arada_2_Dia,
                                        Small_Arada_2_KM_SQFT = Small_Arada_2_KM_SQFT,
                                        Box_Hgt_perc = Box_Hgt_perc,
                                        Box_Hgt = Box_Hgt,
                                        Box_Dia_perc = Box_Dia_perc,
                                        Box_Dia = Box_Dia,
                                        Box_KM_SQFT = Box_KM_SQFT,
                                        Nagabanthanam_1_Hgt_perc = Nagabanthanam_1_Hgt_perc,
                                        Nagabanthanam_1_Hgt = Nagabanthanam_1_Hgt,
                                        Nagabanthanam_1_Dia_perc = Nagabanthanam_1_Dia_perc,
                                        Nagabanthanam_1_Dia = Nagabanthanam_1_Dia,
                                        Nagabanthanam_1_KM_SQFT = Nagabanthanam_1_KM_SQFT,
                                        Kuvalai_Hgt_perc = Kuvalai_Hgt_perc,
                                        Kuvalai_Hgt = Kuvalai_Hgt,
                                        Kuvalai_Dia_perc = Kuvalai_Dia_perc,
                                        Kuvalai_Dia = Kuvalai_Dia,
                                        Kuvalai_KM_SQFT = Kuvalai_KM_SQFT,
                                        Nagabanthanam_2_Hgt_perc = Nagabanthanam_2_Hgt_perc,
                                        Nagabanthanam_2_Hgt = Nagabanthanam_2_Hgt,
                                        Nagabanthanam_2_Dia_perc = Nagabanthanam_2_Dia_perc,
                                        Nagabanthanam_2_Dia = Nagabanthanam_2_Dia,
                                        Nagabanthanam_2_KM_SQFT = Nagabanthanam_2_KM_SQFT,
                                        manipalagai_Hgt_perc = manipalagai_Hgt_perc,
                                        manipalagai_Hgt = manipalagai_Hgt,
                                        manipalagai_Dia_perc = manipalagai_Dia_perc,
                                        manipalagai_Dia = manipalagai_Dia,
                                        manipalagai_KM_SQFT = manipalagai_KM_SQFT,
                                        kalasam_Hgt_perc = kalasam_Hgt_perc,
                                        kalasam_Hgt = kalasam_Hgt,
                                        kalasam_Dia_perc = kalasam_Dia_perc,
                                        kalasam_Dia = kalasam_Dia,
                                        Visiribalagai_Hgt_perc = Visiribalagai_Hgt_perc,
                                        Visiribalagai_Hgt = Visiribalagai_Hgt,
                                        Visiribalagai_Dia_perc = Visiribalagai_Dia_perc,
                                        Visiribalagai_Dia = Visiribalagai_Dia,
                                        Visiribalagai_side_Hgt_perc = Visiribalagai_side_Hgt_perc,
                                        Visiribalagai_side_Hgt = Visiribalagai_side_Hgt,
                                        Visiribalagai_side_Dia_perc = Visiribalagai_side_Dia_perc,
                                        Visiribalagai_side_Dia = Visiribalagai_side_Dia,
                                        Visiribalagai_VB_SQFT = Visiribalagai_VB_SQFT,
                                        Visiribalagai_side_VB_SQFT = Visiribalagai_side_VB_SQFT,
                                        Total_Hgt = Total_Hgt,
                                        Total_Dia = Total_Dia,
                                        Total_KM_SQFT = Total_KM_SQFT,
                                        Total_VB_SQFT = Total_VB_SQFT,

                                        Apx_SQFT = Apx_SQFT,
                                        Apx_Wgt = Apx_Wgt,
                                        cost = cost,
                                        final_cost = final_cost,
                                        delivery_days = delivery_days_dic['kodimaram'],
                                        validity_days = validity_days_dic[material],
                                        now = now,
                                        quotation_no = quotation_no)
    
        except mysql.connector.Error as e:
                session['msg'] = f"DB Error: {e}"
                return redirect(url_for("user_kodimaram"))

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ------------------- GET -------------------
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM cat_kodimaram_images")
        images = cursor.fetchall()

        for img in images:
            if img["img"]:
                img["img_b64"] = base64.b64encode(img["img"]).decode("utf-8")
            else:
                img["img_b64"] = ""

        msg = session.get('msg')
        session['msg'] = False
        return render_template("user/kodimaram.html", images = images, msg = msg)

    except mysql.connector.Error as e:
        return render_template("user/kodimaram.html", msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



@app.route("/kodimaram_image/<int:image_id>")
def kodimaram_image(image_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT img, img_type FROM cat_kodimaram_images WHERE id=%s", (image_id,))
    image = cursor.fetchone()

    cursor.close()
    conn.close()

    if image and image["img"]:
        mime = image["img_type"]

        if mime in ["jpg", "jpeg"]:
            mime = "image/jpeg"
        elif mime == "png":
            mime = "image/png"
        elif mime == "webp":
            mime = "image/webp"
        elif not mime.startswith("image/"):
            mime = "image/jpeg"

        return Response(
                        image["img"],
                        mimetype=mime,
                        headers={
                            "Cache-Control": "no-store"
                        })
    return "Image not found", 404




@app.route("/kodimaram/pdf", methods=["POST"])
def kodimaram_pdf():
    material = "brass"
    thickness = "20 Gauge"

    height = round(Decimal(request.form.get("height")), 2)
    diameter = round(Decimal(request.form.get("diameter")), 2)
    SQFT = round(Decimal(request.form.get("SQFT")), 2)
    weight = round(Decimal(request.form.get("weight")), 2)

    delivery_days = request.form.get("delivery_days")
    validity_days = request.form.get("validity_days")
    now = request.form.get("now")
    quotation_no = request.form.get("quotation_no")
    customer_id_raw = request.form.get("customer_id")
    transportation_cost = int(request.form.get("transportation_cost") or 0)

    if not customer_id_raw:
        return jsonify({"error": "Customer not selected"}), 400
    else:
        customer_id = int(customer_id_raw)

    # Cost from form (already includes GST)
    unit = round(Decimal(request.form.get("unit")), 2)
    cost = round(Decimal(request.form.get("cost")), 2)
    unit_price = int(cost / unit)
    total_cost = int(unit_price * unit)
    grand_total = int(cost + transportation_cost)

    sales_id = session["user_id"]
    sales_emp_id = session["user_emp_id"]
    sales_name = session["user_name"]
    sales_mobile = session["user_mobile"]
    sales_branch = session["user_branch"]
    
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                *
            FROM 
                customers
            WHERE 
                id=%s
        """, (customer_id,))
        customers_data = cursor.fetchall()

        cust_name=customers_data[0]['name']
        cust_mobile=customers_data[0]['mobile']
        temple_name=customers_data[0]['temple']
        address=customers_data[0]['address']

    except mysql.connector.Error as e:
        session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_kodimaram"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    
    action = request.form.get("submit_action")

    if action == "download_pdf":
        html = render_template(
            "user/pdf/kodimaram_quotation.html",
            category = "kodimaram",
            height = height,
            diameter = diameter,
            no_of_Square_feet = SQFT,
            weight = weight,

            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,
            delivery_days = delivery_days,
            validity_days = validity_days,

            customer_id = customer_id,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,

            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,

            now = now,
            quotation_no = quotation_no,
            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64
        )

        pdf_io = BytesIO()
        pisa.CreatePDF(
            html,
            dest=pdf_io,
            link_callback=link_callback
        )
        response = make_response(pdf_io.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "attachment; filename=Kodimaram_Quotation.pdf"
        return response
    
    
    elif action == "share_whatsapp":
        wa_cust_mobile = request.form.get("wa_cust_mobile")

        html = render_template(
            "user/pdf/kodimaram_quotation.html",
            category = "kodimaram",
            height = height,
            diameter = diameter,
            no_of_Square_feet = SQFT,
            weight = weight,

            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,
            delivery_days = delivery_days,
            validity_days = validity_days,

            customer_id = customer_id,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,
            
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,

            now = now,
            quotation_no = quotation_no,
            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64,
        )

        filename = f"Kodimaram_Quotation_{uuid4().hex}.pdf"
        pdf_path = os.path.join(app.root_path, "static/PDFs", filename)

        with open(pdf_path, "wb") as f:
            pisa.CreatePDF(html, dest=f, link_callback=link_callback)

        pdf_url = url_for("static", filename=f"PDFs/{filename}", _external=True)

        text = f"😊 Dear {cust_name},\nPlease find your quotation below:\n {pdf_url} \n\n🙏 Thank you for choosing Raja Spiritual"
        whatsapp_url = f"https://wa.me/91{wa_cust_mobile}?text={quote(text)}"

        return jsonify({"whatsapp_url": whatsapp_url})


    elif action == "save_quotation":
        conn = cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO 
                    quot_kodimaram 
                        (user_emp_id, cust_id, height, diameter, SQFT, weight, unit, cost, transport_cost, delivery_days, validity_days)
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (sales_emp_id, customer_id, height, diameter, SQFT, weight, unit, cost, transportation_cost, delivery_days, validity_days))
            quot_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO 
                    quotations 
                        (category, quot_id, user_emp_id, cust_id) 
                VALUES 
                    (%s, %s, %s, %s)
            """, ('kodimaram', quot_id, sales_emp_id, customer_id))
            conn.commit()
        
            flash("Quotation added successfully!", "success")
            return redirect(url_for("user_kodimaram"))

        except mysql.connector.Error as e:
            session["msg"] = f"DB Error: {e}"
            return redirect(url_for("user_kodimaram"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()




########################### USER SHEET METAL ###########################
@app.route('/user_sheet_metal', methods=["GET", "POST"])
def user_sheet_metal():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    data = None
    if request.method == "POST":
        thickness = request.form.get("thickness")
        material = request.form.get("material")

        form = request.form
        measures = {}

        for key, value in form.items():
            if key.startswith("measures"):
                index = int(key.split("[")[1].split("]")[0])
                field = key.split("[")[2].replace("]", "")

                if index not in measures:
                    measures[index] = {}
                measures[index][field] = value

        measures = [measures[i] for i in sorted(measures.keys())]

        nilai_padi_plain_total_SQFT = 0
        nilai_padi_vargam_total_SQFT = 0
        custom_picture_total_SQFT = 0

        for m in measures:
            if m["type"] == "nilai_padi_plain":
                nilai_padi_plain_height = round(float(m["height"]), 2)
                nilai_padi_plain_width = round(float(m["width"]), 2)

                if m["uom_height"].lower().startswith("inch"):
                    nilai_padi_plain_height = nilai_padi_plain_height / 12

                if m["uom_width"].lower().startswith("inch"):
                    nilai_padi_plain_width = nilai_padi_plain_width / 12

                SQFT = nilai_padi_plain_height * nilai_padi_plain_width
                nilai_padi_plain_total_SQFT += SQFT

                m["height_ft"] = round(float(nilai_padi_plain_height), 2)
                m["width_ft"] = round(float(nilai_padi_plain_width), 2)
                m["SQFT"] = round(float(SQFT), 2)

            if m["type"] == "nilai_padi_vargam":
                nilai_padi_vargam_height = round(float(m["height"]), 2)
                nilai_padi_vargam_width = round(float(m["width"]), 2)

                if m["uom_height"].lower().startswith("inch"):
                    nilai_padi_vargam_height = nilai_padi_vargam_height / 12

                if m["uom_width"].lower().startswith("inch"):
                    nilai_padi_vargam_width = nilai_padi_vargam_width / 12

                SQFT = nilai_padi_vargam_height * nilai_padi_vargam_width
                nilai_padi_vargam_total_SQFT += SQFT

                m["height_ft"] = round(float(nilai_padi_vargam_height), 2)
                m["width_ft"] = round(float(nilai_padi_vargam_width), 2)
                m["SQFT"] = round(float(SQFT), 2)

            if m["type"] == "custom_picture":
                custom_picture_height = round(float(m["height"]), 2)
                custom_picture_width = round(float(m["width"]), 2)

                if m["uom_height"].lower().startswith("inch"):
                    custom_picture_height = custom_picture_height / 12

                if m["uom_width"].lower().startswith("inch"):
                    custom_picture_width = custom_picture_width / 12

                SQFT = custom_picture_height * custom_picture_width
                custom_picture_total_SQFT += SQFT

                m["height_ft"] = round(float(custom_picture_height), 2)
                m["width_ft"] = round(float(custom_picture_width), 2)
                m["SQFT"] = round(float(SQFT), 2)

        if nilai_padi_plain_total_SQFT:
            if thickness == "20 Gauge" and nilai_padi_plain_total_SQFT < 21:
                nilai_padi_plain_col = 'gauge_20__below_21_SQFT'
            elif thickness == "20 Gauge" and nilai_padi_plain_total_SQFT >= 21 and nilai_padi_plain_total_SQFT <= 50:
                nilai_padi_plain_col = 'gauge_20__21_50_SQFT'
            elif thickness == "20 Gauge" and nilai_padi_plain_total_SQFT > 50:
                nilai_padi_plain_col = 'gauge_20__above_50_SQFT'
            elif thickness == "22 Gauge" and nilai_padi_plain_total_SQFT < 21:
                nilai_padi_plain_col = 'gauge_22__below_21_SQFT'
            elif thickness == "22 Gauge" and nilai_padi_plain_total_SQFT >= 21 and nilai_padi_plain_total_SQFT <= 50:
                nilai_padi_plain_col = 'gauge_22__21_50_SQFT'
            elif thickness == "22 Gauge" and nilai_padi_plain_total_SQFT > 50:
                nilai_padi_plain_col = 'gauge_22__above_50_SQFT'
        else:
            nilai_padi_plain_col = None

        if nilai_padi_vargam_total_SQFT:
            if thickness == "20 Gauge" and nilai_padi_vargam_total_SQFT < 21:
                nilai_padi_vargam_col = 'gauge_20__below_21_SQFT'
            elif thickness == "20 Gauge" and nilai_padi_vargam_total_SQFT >= 21 and nilai_padi_vargam_total_SQFT <= 50:
                nilai_padi_vargam_col = 'gauge_20__21_50_SQFT'
            elif thickness == "20 Gauge" and nilai_padi_vargam_total_SQFT > 50:
                nilai_padi_vargam_col = 'gauge_20__above_50_SQFT'
            elif thickness == "22 Gauge" and nilai_padi_vargam_total_SQFT < 21:
                nilai_padi_vargam_col = 'gauge_22__below_21_SQFT'
            elif thickness == "22 Gauge" and nilai_padi_vargam_total_SQFT >= 21 and nilai_padi_vargam_total_SQFT <= 50:
                nilai_padi_vargam_col = 'gauge_22__21_50_SQFT'
            elif thickness == "22 Gauge" and nilai_padi_vargam_total_SQFT > 50:
                nilai_padi_vargam_col = 'gauge_22__above_50_SQFT'
        else:
            nilai_padi_vargam_col = None

        if custom_picture_total_SQFT:
            if thickness == "20 Gauge" and custom_picture_total_SQFT < 21:
                custom_picture_col = 'gauge_20__below_21_SQFT'
            elif thickness == "20 Gauge" and custom_picture_total_SQFT >= 21 and custom_picture_total_SQFT <= 50:
                custom_picture_col = 'gauge_20__21_50_SQFT'
            elif thickness == "20 Gauge" and custom_picture_total_SQFT > 50:
                custom_picture_col = 'gauge_20__above_50_SQFT'
            elif thickness == "22 Gauge" and custom_picture_total_SQFT < 21:
                custom_picture_col = 'gauge_22__below_21_SQFT'
            elif thickness == "22 Gauge" and custom_picture_total_SQFT >= 21 and custom_picture_total_SQFT <= 50:
                custom_picture_col = 'gauge_22__21_50_SQFT'
            elif thickness == "22 Gauge" and custom_picture_total_SQFT > 50:
                custom_picture_col = 'gauge_22__above_50_SQFT'
        else:
            custom_picture_col = None
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if nilai_padi_plain_col:
                cursor.execute(f"""SELECT {nilai_padi_plain_col} FROM cat_sheet_metal WHERE heads=%s""", ('Nilai Padi Plain',))
                nilai_padi_plain_data = cursor.fetchall()
                nilai_padi_plain_cost = nilai_padi_plain_data[0][nilai_padi_plain_col]

                if material == "copper":
                    nilai_padi_plain_cost = nilai_padi_plain_cost * 1.1 # copper cost = brass cost + 10% of brass cost

                nilai_padi_plain_total_cost = nilai_padi_plain_total_SQFT * nilai_padi_plain_cost
                buffer_amount = nilai_padi_plain_total_cost * buffer_rate / 100
                cost_with_buffer = nilai_padi_plain_total_cost + buffer_amount
                GST_amount = cost_with_buffer * GST_rate_dic['sheet_metal'] / 100
                nilai_padi_plain_final_cost = round(cost_with_buffer + GST_amount)
            else:
                nilai_padi_plain_final_cost = 0
            

            if nilai_padi_vargam_col:
                cursor.execute(f"""SELECT {nilai_padi_vargam_col} FROM cat_sheet_metal WHERE heads=%s""", ('Nilai Padi Vargam',))
                nilai_padi_vargam_data = cursor.fetchall()
                nilai_padi_vargam_cost = nilai_padi_vargam_data[0][nilai_padi_vargam_col]

                if material == "copper":
                    nilai_padi_vargam_cost = nilai_padi_vargam_cost * 1.1 # copper cost = brass cost + 10% of brass cost

                nilai_padi_vargam_total_cost = nilai_padi_vargam_total_SQFT * nilai_padi_vargam_cost
                buffer_amount = nilai_padi_vargam_total_cost * buffer_rate / 100
                cost_with_buffer = nilai_padi_vargam_total_cost + buffer_amount
                GST_amount = cost_with_buffer * GST_rate_dic['sheet_metal'] / 100
                nilai_padi_vargam_final_cost = round(cost_with_buffer + GST_amount)
            else:
                nilai_padi_vargam_final_cost = 0
            

            if custom_picture_col:
                cursor.execute(f"""SELECT {custom_picture_col} FROM cat_sheet_metal WHERE heads=%s""", ('Additional Customized Picture',))
                custom_picture_data = cursor.fetchall()
                custom_picture_cost = custom_picture_data[0][custom_picture_col]

                if material == "copper":
                    custom_picture_cost = custom_picture_cost * 1.1 # copper cost = brass cost + 10% of brass cost

                custom_picture_total_cost = custom_picture_total_SQFT * custom_picture_cost
                buffer_amount = custom_picture_total_cost * buffer_rate / 100
                cost_with_buffer = custom_picture_total_cost + buffer_amount
                GST_amount = cost_with_buffer * GST_rate_dic['sheet_metal'] / 100
                custom_picture_final_cost = round(cost_with_buffer + GST_amount)
            else:
                custom_picture_final_cost = 0
            

            final_cost = nilai_padi_plain_final_cost + nilai_padi_vargam_final_cost + custom_picture_final_cost

            now = datetime.now().strftime("%d-%m-%Y")
            emp_id = session["user_emp_id"]
            date_str = datetime.now().strftime("%Y%m%d")
            time_hhmmss = datetime.now().strftime("%H%M%S")
            quotation_no = f"RSS-{emp_id}-{quotation_no_category['sheet_metal']}-{date_str}-{time_hhmmss}"

            sales_id = session["user_id"]
            sales_emp_id = session["user_emp_id"]
            sales_name = session["user_name"]
            sales_mobile = session["user_mobile"]
            sales_branch = session["user_branch"]

            cursor.execute("""
                SELECT *
                FROM customers
                WHERE user_emp_id=%s
                ORDER BY id ASC
            """, (emp_id,))
            customer_data = cursor.fetchall()

            total_SQFT = nilai_padi_plain_total_SQFT + nilai_padi_vargam_total_SQFT + custom_picture_total_SQFT
            if total_SQFT <= 50:
                total_SQFT = 'below 50 SQFT'
            elif total_SQFT > 50 and total_SQFT <= 150:
                total_SQFT = '51-150 SQFT'
            else:
                total_SQFT = 'above 150 SQFT'

            return render_template(r"user/sheet_metal.html", 
                                material = material,
                                thickness = thickness,

                                nilai_padi_plain_total_SQFT = nilai_padi_plain_total_SQFT,
                                nilai_padi_plain_final_cost = nilai_padi_plain_final_cost,

                                nilai_padi_vargam_total_SQFT = nilai_padi_vargam_total_SQFT,
                                nilai_padi_vargam_final_cost = nilai_padi_vargam_final_cost,

                                custom_picture_total_SQFT = custom_picture_total_SQFT,
                                custom_picture_final_cost = custom_picture_final_cost,

                                final_cost = final_cost,
                                customer_data = customer_data,
                                now = now,
                                quotation_no = quotation_no,

                                sales_id = sales_id,
                                sales_emp_id = sales_emp_id,
                                sales_name = sales_name,
                                sales_mobile = sales_mobile,
                                sales_branch = sales_branch,
                                
                                delivery_days = delivery_days_dic['sheet_metal'][total_SQFT],
                                validity_days = validity_days_dic[material])
        
        except mysql.connector.Error as e:
                session['msg'] = f"DB Error: {e}"
                return redirect(url_for("user_sheet_metal"))

        finally:
            if cursor: cursor.close()
            if conn: conn.close()


    # ------------------- GET -------------------
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM cat_sheet_metal_images")
        images = cursor.fetchall()

        for img in images:
            if img["img"]:
                img["img_b64"] = base64.b64encode(img["img"]).decode("utf-8")
            else:
                img["img_b64"] = ""

        msg = session.get('msg')
        session['msg'] = False
        return render_template("user/sheet_metal.html", images = images, msg = msg)

    except mysql.connector.Error as e:
        return render_template("user/sheet_metal.html", msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



@app.route("/sheet_metal_image/<int:image_id>")
def sheet_metal_image(image_id):
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT img, img_type FROM cat_sheet_metal_images WHERE id=%s", (image_id,))
        image = cursor.fetchone()

        cursor.close()
        conn.close()

        if image and image["img"]:
            mime = image["img_type"]

            if mime in ["jpg", "jpeg"]:
                mime = "image/jpeg"
            elif mime == "png":
                mime = "image/png"
            elif mime == "webp":
                mime = "image/webp"
            elif not mime.startswith("image/"):
                mime = "image/jpeg"

            return Response(
                            image["img"],
                            mimetype=mime,
                            headers={
                                "Cache-Control": "no-store"
                            })
        return "Image not found", 404
    
    except:
        return "Image not found", 404
    


@app.route("/sheet_metal/pdf", methods=["POST"])
def sheet_metal_pdf():
    customer_id_raw = request.form.get("customer_id")
    if not customer_id_raw:
        return jsonify({"error": "Customer not selected"}), 400
    
    customer_id = int(customer_id_raw)

    transportation_cost = int(request.form.get("transportation_cost", 0) or 0)

    nilai_padi_plain_total_SQFT = float(request.form.get("nilai_padi_plain_total_SQFT")  or 0)
    nilai_padi_vargam_total_SQFT = float(request.form.get("nilai_padi_vargam_total_SQFT")  or 0)
    custom_picture_total_SQFT = float(request.form.get("custom_picture_total_SQFT")  or 0)
   
    nilai_padi_plain_unit = round(float(request.form.get("nilai_padi_plain_unit", 0) or 0))
    nilai_padi_vargam_unit = round(float(request.form.get("nilai_padi_vargam_unit", 0) or 0))
    custom_picture_unit = round(float(request.form.get("custom_picture_unit", 0) or 0))

    nilai_padi_plain_cost_per_Qty = round(float(request.form.get("nilai_padi_plain_final_cost", 0) or 0))
    nilai_padi_vargam_cost_per_Qty = round(float(request.form.get("nilai_padi_vargam_final_cost", 0) or 0))
    custom_picture_cost_per_Qty = round(float(request.form.get("custom_picture_final_cost", 0) or 0))
   
    nilai_padi_plain_final_cost = nilai_padi_plain_unit * nilai_padi_plain_cost_per_Qty
    nilai_padi_vargam_final_cost = nilai_padi_vargam_unit * nilai_padi_vargam_cost_per_Qty
    custom_picture_final_cost = custom_picture_unit * custom_picture_cost_per_Qty

    total_SQFT = nilai_padi_plain_total_SQFT + nilai_padi_vargam_total_SQFT + custom_picture_total_SQFT
    total_unit = nilai_padi_plain_unit + nilai_padi_vargam_unit + custom_picture_unit
    total_cost_per_Qty = nilai_padi_plain_cost_per_Qty + nilai_padi_vargam_cost_per_Qty + custom_picture_cost_per_Qty
    total_cost = nilai_padi_plain_final_cost + nilai_padi_vargam_final_cost + custom_picture_final_cost

   # Cost from form (already includes GST)
    grand_total = int(total_cost + transportation_cost)


    thickness = request.form.get("thickness")
    material = request.form.get("material")
    delivery_days = request.form.get("delivery_days")
    validity_days = request.form.get("validity_days")
    now = request.form.get("now")
    quotation_no = request.form.get("quotation_no")

    sales_id = session["user_id"]
    sales_emp_id = session["user_emp_id"]
    sales_name = session["user_name"]
    sales_mobile = session["user_mobile"]
    sales_branch = session["user_branch"]
    
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                *
            FROM 
                customers
            WHERE 
                id=%s
        """, (customer_id,))
        customers_data = cursor.fetchall()

        cust_name=customers_data[0]['name']
        cust_mobile=customers_data[0]['mobile']
        temple_name=customers_data[0]['temple']
        address=customers_data[0]['address']

    except mysql.connector.Error as e:
        session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_sheet_metal"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    

    action = request.form.get("submit_action")

    if action == "download_pdf":
        html = render_template(
            "user/pdf/sheet_metal_quotation.html",
            category = "sheet_metal",
            customer_id = customer_id,
            transportation_cost = transportation_cost,
            nilai_padi_plain_total_SQFT = nilai_padi_plain_total_SQFT,
            nilai_padi_vargam_total_SQFT = nilai_padi_vargam_total_SQFT,
            custom_picture_total_SQFT = custom_picture_total_SQFT,
            nilai_padi_plain_unit = nilai_padi_plain_unit,
            nilai_padi_vargam_unit = nilai_padi_vargam_unit,
            custom_picture_unit = custom_picture_unit,
            nilai_padi_plain_cost_per_Qty = nilai_padi_plain_cost_per_Qty,
            nilai_padi_vargam_cost_per_Qty = nilai_padi_vargam_cost_per_Qty,
            custom_picture_cost_per_Qty = custom_picture_cost_per_Qty,
            nilai_padi_plain_final_cost = nilai_padi_plain_final_cost,
            nilai_padi_vargam_final_cost = nilai_padi_vargam_final_cost,
            custom_picture_final_cost = custom_picture_final_cost,
            total_SQFT = total_SQFT,
            total_unit = total_unit,
            unit_price = total_cost_per_Qty,
            total_cost = total_cost,
            grand_total = grand_total,
            thickness = thickness,
            material = material,
            delivery_days = delivery_days,
            validity_days = validity_days,
            now = now,
            quotation_no = quotation_no,
            sales_id = sales_id,
            sales_emp_id = sales_emp_id,
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,
            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64,
        )

        pdf_io = BytesIO()
        pisa.CreatePDF(
            html,
            dest=pdf_io,
            link_callback=link_callback
        )
        response = make_response(pdf_io.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "attachment; filename=sheet_metal_Quotation.pdf"
        return response
    
    
    elif action == "share_whatsapp":
        wa_cust_mobile = request.form.get("wa_cust_mobile")

        html = render_template(
            "user/pdf/sheet_metal_quotation.html",
            category="sheet_metal",
            customer_id = customer_id,
            transportation_cost = transportation_cost,
            nilai_padi_plain_total_SQFT = nilai_padi_plain_total_SQFT,
            nilai_padi_vargam_total_SQFT = nilai_padi_vargam_total_SQFT,
            custom_picture_total_SQFT = custom_picture_total_SQFT,
            nilai_padi_plain_unit = nilai_padi_plain_unit,
            nilai_padi_vargam_unit = nilai_padi_vargam_unit,
            custom_picture_unit = custom_picture_unit,
            nilai_padi_plain_cost_per_Qty = nilai_padi_plain_cost_per_Qty,
            nilai_padi_vargam_cost_per_Qty = nilai_padi_vargam_cost_per_Qty,
            custom_picture_cost_per_Qty = custom_picture_cost_per_Qty,
            nilai_padi_plain_final_cost = nilai_padi_plain_final_cost,
            nilai_padi_vargam_final_cost = nilai_padi_vargam_final_cost,
            custom_picture_final_cost = custom_picture_final_cost,
            total_SQFT = total_SQFT,
            total_unit = total_unit,
            unit_price = total_cost_per_Qty,
            total_cost = total_cost,
            grand_total = grand_total,
            thickness = thickness,
            material = material,
            delivery_days = delivery_days,
            validity_days = validity_days,
            now = now,
            quotation_no = quotation_no,
            sales_id = sales_id,
            sales_emp_id = sales_emp_id,
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,
            logo_path=logo_path,
            logo_base64=logo_base64,
            base_QR_base64=base_QR_base64,
        )

        filename = f"sheet_metal_Quotation_{uuid4().hex}.pdf"
        pdf_path = os.path.join(app.root_path, "static/PDFs", filename)

        with open(pdf_path, "wb") as f:
            pisa.CreatePDF(html, dest=f, link_callback=link_callback)

        pdf_url = url_for("static", filename=f"PDFs/{filename}", _external=True)

        text = f"😊 Dear {cust_name},\nPlease find your quotation below:\n {pdf_url} \n\n🙏 Thank you for choosing Raja Spiritual"
        whatsapp_url = f"https://wa.me/91{wa_cust_mobile}?text={quote(text)}"

        return jsonify({"whatsapp_url": whatsapp_url})


    elif action == "save_quotation":
        conn = cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO 
                    quot_sheet_metal 
                        (user_emp_id, cust_id, material, thickness, nilai_padi_plain_total_SQFT, nilai_padi_vargam_total_SQFT, custom_picture_total_SQFT, nilai_padi_plain_unit, nilai_padi_vargam_unit, custom_picture_unit, nilai_padi_plain_final_cost, nilai_padi_vargam_final_cost, custom_picture_final_cost, transport_cost, delivery_days, validity_days) 
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (sales_emp_id, customer_id, material, thickness, nilai_padi_plain_total_SQFT, nilai_padi_vargam_total_SQFT, custom_picture_total_SQFT, nilai_padi_plain_unit, nilai_padi_vargam_unit, custom_picture_unit, nilai_padi_plain_final_cost, nilai_padi_vargam_final_cost, custom_picture_final_cost, transportation_cost, delivery_days, validity_days))
            
            quot_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO 
                    quotations 
                        (category, quot_id, user_emp_id, cust_id) 
                VALUES 
                    (%s, %s, %s, %s)
            """, ('sheet_metal', quot_id, sales_emp_id, customer_id))
            conn.commit()
        
            flash("Quotation added successfully!", "success")
            return redirect(url_for("user_sheet_metal"))

        except mysql.connector.Error as e:
            session["msg"] = f"DB Error: {e}"
            return redirect(url_for("user_sheet_metal"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()




########################### USER PANCHALOHA STATUE ###########################
@app.route('/user_panchaloha_statue', methods=["GET", "POST"])
def user_panchaloha_statue():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
        
    if request.method == "POST":
        statue_id = request.form.get("statue_id")

        if not statue_id:
            return "No statue selected", 400
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT *
                FROM cat_panchaloha_statue
                WHERE id = %s
            """, (statue_id,))
            row = cursor.fetchone()

            if not row:
                return "Statue not found", 404

            name = row["name"]
            prabavali = row["prabavali"]
            position = row["position"]
            model = row["model"]
            hands = row["hands"]
            height = row["height"]
            weight = row["weight"]
            base_cost = row["cost"]
            
            buffer_amount = base_cost * buffer_rate / 100
            cost_with_buffer = base_cost + buffer_amount
            GST_amount = cost_with_buffer * GST_rate_dic['panchaloha_statue'] / 100
            final_cost = round(cost_with_buffer + GST_amount)


            cursor.execute("""
                SELECT DISTINCT name
                FROM cat_panchaloha_statue
                ORDER BY name
            """)
            idol_data = cursor.fetchall()

            now = datetime.now().strftime("%d-%m-%Y")
            emp_id = session["user_emp_id"]
            date_str = datetime.now().strftime("%Y%m%d")
            time_hhmmss = datetime.now().strftime("%H%M%S")
            quotation_no = f"RSS-{emp_id}-{quotation_no_category['panchaloha_statue']}-{date_str}-{time_hhmmss}"


            cursor.execute("""
                SELECT *
                FROM customers
                WHERE user_emp_id=%s
                ORDER BY id ASC
            """, (emp_id,))
            customer_data = cursor.fetchall()
            
            return render_template(r"user/panchaloha_statue.html", 
                                    idol_data = idol_data,
                                    statue_id = statue_id,
                                    name = name,
                                    prabavali = prabavali,
                                    position = position,
                                    model = model,
                                    hands = hands,
                                    height = height,
                                    weight = weight,
                                    cost = final_cost,
                                    delivery_days = delivery_days_dic['panchaloha_statue'],
                                    validity_days = validity_days_dic['brass'],
                                    now = now,
                                    quotation_no = quotation_no,
                                    customer_data = customer_data)

        except mysql.connector.Error as e:
                session['msg'] = f"DB Error: {e}"

        finally:
            if cursor: cursor.close()
            if conn: conn.close()


    # ------------------- GET -------------------
    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_panchaloha_statue
            ORDER BY name, prabavali, position, model, hands, height, weight, cost ASC
        """)
        data = cursor.fetchall()


        for row in data:
            cursor.execute("""
                SELECT id
                FROM cat_panchaloha_statue_images
                WHERE cat_panchaloha_statue_id = %s
                ORDER BY is_primary DESC, id ASC
            """, (row["id"],))

            images = cursor.fetchall()
            row["image_list"] = images

        cursor.execute("""
            SELECT DISTINCT name
            FROM cat_panchaloha_statue
            ORDER BY name
        """)
        idol_data = cursor.fetchall()

        msg = session.get('msg')
        session['msg'] = False
        return render_template("user/panchaloha_statue.html", images = data, idol_data = idol_data, msg = msg)

    except mysql.connector.Error as e:
        return render_template("user/panchaloha_statue.html", msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



@app.route("/user_panchaloha_statue_image/<int:image_id>")
def user_panchaloha_statue_image(image_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT img, img_type
        FROM cat_panchaloha_statue_images
        WHERE id = %s
    """, (image_id,))

    image = cursor.fetchone()

    cursor.close()
    conn.close()

    if image and image["img"]:
        mime = image["img_type"]

        if mime in ["jpg", "jpeg"]:
            mime = "image/jpeg"
        elif mime == "png":
            mime = "image/png"
        elif mime == "webp":
            mime = "image/webp"
        elif not mime.startswith("image/"):
            mime = "image/jpeg"

        return Response(image["img"], mimetype=mime)

    return "Image not found", 404


@app.route("/get_panchaloha_options", methods=["POST"])
def get_panchaloha_options():
    filters = request.json  # receive selected values as JSON

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM cat_panchaloha_statue WHERE 1=1"
    values = []

    for key, value in filters.items():
        if value:
            query += f" AND {key} = %s"
            values.append(value)

    cursor.execute(query, values)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return jsonify({"status": "no_data"})

    # If only 1 row left → return final row
    if len(rows) == 1:
        return jsonify({
            "status": "final",
            "data": rows[0]
        })

    # If multiple rows → find next unique fields
    fields = ["prabavali", "position", "model", "hands", "height"]

    next_options = {}

    for field in fields:
        if field not in filters:
            unique_values = list(set(row[field] for row in rows))
            if len(unique_values) > 1:
                next_options[field] = sorted(unique_values)

    return jsonify({
        "status": "options",
        "options": next_options
    })




@app.route("/panchaloha_statue/pdf", methods=["POST"])
def panchaloha_statue_pdf():
    from decimal import Decimal, ROUND_HALF_UP
    def get_decimal(field):
        return Decimal(request.form.get(field) or 0).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    name = request.form.get("name") or 0
    prabavali = request.form.get("prabavali") or 0
    position = request.form.get("position") or 0
    model = request.form.get("model") or 0
    hands = int(request.form.get("hands")) or 0
    height = get_decimal("height")
    weight = get_decimal("weight")
    transportation_cost = int(get_decimal("transportation_cost"))

    # Cost from form (already includes GST)
    cost = int(get_decimal("cost"))
    unit = get_decimal("unit")
    unit_price = int(cost / unit)
    total_cost = int(unit_price * unit)
    grand_total = int(cost + transportation_cost)

    delivery_days = request.form.get("delivery_days") or 0
    validity_days = request.form.get("validity_days") or 0
    now = request.form.get("now") or 0
    quotation_no = request.form.get("quotation_no") or 0

    customer_id_raw = request.form.get("customer_id") or 0
    if not customer_id_raw:
        return jsonify({"error": "Customer not selected"}), 400
    customer_id = int(customer_id_raw)

    sales_id = session["user_id"]
    sales_emp_id = session["user_emp_id"]
    sales_name = session["user_name"]
    sales_mobile = session["user_mobile"]
    sales_branch = session["user_branch"]
    

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                *
            FROM 
                customers
            WHERE 
                id=%s
        """, (customer_id,))
        customers_data = cursor.fetchall()

        cust_name=customers_data[0]['name']
        cust_mobile=customers_data[0]['mobile']
        temple_name=customers_data[0]['temple']
        address=customers_data[0]['address']

    except mysql.connector.Error as e:
        session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_panchaloha_statue"))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    
    action = request.form.get("submit_action")

    if action == "download_pdf":
        html = render_template(
            "user/pdf/panchaloha_statue_quotation.html",
            category = "panchaloha_statue",

            name = name,
            prabavali = prabavali,
            position = position,
            model = model,
            hands = hands,
            height = height,
            weight = weight,

            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,

            customer_id = customer_id,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,

            sales_id = sales_id,
            sales_emp_id = sales_emp_id,
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,
            
            now = now,
            quotation_no = quotation_no,

            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64,
        )

        pdf_io = BytesIO()
        pisa.CreatePDF(
            html,
            dest=pdf_io,
            link_callback=link_callback
        )
        response = make_response(pdf_io.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "attachment; filename=panchaloha_statue_Quotation.pdf"
        return response
    
    
    elif action == "share_whatsapp":
        wa_cust_mobile = request.form.get("wa_cust_mobile")

        html = render_template(
            "user/pdf/panchaloha_statue_quotation.html",
            category="panchaloha_statue",

            name = name,
            prabavali = prabavali,
            position = position,
            model = model,
            hands = hands,
            height = height,
            weight = weight,

            unit = unit,
            unit_price = unit_price,
            total_cost = total_cost,
            transportation_cost = transportation_cost,
            grand_total = grand_total,

            customer_id = customer_id,
            cust_name = cust_name,
            cust_mobile = cust_mobile,
            temple_name = temple_name,
            address = address,

            sales_id = sales_id,
            sales_emp_id = sales_emp_id,
            sales_name = sales_name,
            sales_mobile = sales_mobile,
            sales_branch = sales_branch,
            
            now = now,
            quotation_no = quotation_no,
            
            logo_path = logo_path,
            logo_base64 = logo_base64,
            base_QR_base64 = base_QR_base64,
        )

        filename = f"Panchaloha_Statue_Quotation_{uuid4().hex}.pdf"
        pdf_path = os.path.join(app.root_path, "static/PDFs", filename)

        with open(pdf_path, "wb") as f:
            pisa.CreatePDF(html, dest=f, link_callback=link_callback)

        pdf_url = url_for("static", filename=f"PDFs/{filename}", _external=True)

        text = f"😊 Dear {cust_name},\nPlease find your quotation below:\n {pdf_url} \n\n🙏 Thank you for choosing Raja Spiritual"
        whatsapp_url = f"https://wa.me/91{wa_cust_mobile}?text={quote(text)}"

        return jsonify({"whatsapp_url": whatsapp_url})


    elif action == "save_quotation":
        conn = cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO 
                    quot_panchaloha_statue 
                        (user_emp_id, cust_id, name, prabavali, position, model, hands, height, weight, unit, cost, transport_cost, delivery_days, validity_days)
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (sales_emp_id, customer_id, name, prabavali, position, model, hands, height, weight, unit, cost, transportation_cost, delivery_days, validity_days))
            quot_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO 
                    quotations 
                        (category, quot_id, user_emp_id, cust_id) 
                VALUES 
                    (%s, %s, %s, %s)
            """, ('panchaloha_statue', quot_id, sales_emp_id, customer_id))
            conn.commit()
        
            flash("Quotation added successfully!", "success")
            return redirect(url_for("user_panchaloha_statue"))

        except mysql.connector.Error as e:
            session["msg"] = f"DB Error: {e}"
            return redirect(url_for("user_panchaloha_statue"))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


#######################################################################
########################### USER QUOTATIONS ###########################
#######################################################################

def get_quotation_data(master_id):

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ---------------- MASTER ----------------
        cursor.execute("""
            SELECT 
                mq.*,
                c.name AS customer_name,
                c.mobile,
                c.address,
                c.temple,
                u.name AS sales_name,
                u.mobile AS sales_mobile,
                u.branch AS sales_branch
            FROM master_quotations mq
            JOIN customers c ON c.id = mq.cust_id
            JOIN users u ON u.emp_id = mq.user_emp_id
            WHERE mq.id=%s
        """, (master_id,))
        master = cursor.fetchone()

        if not master:
            return None, []

        # ---------------- ITEMS ----------------
        cursor.execute("""
            SELECT q.*
            FROM master_quotation_items mqi
            JOIN quotations q ON q.id = mqi.quotation_id
            WHERE mqi.master_quotation_id=%s
            ORDER BY q.category
        """, (master_id,))
        quotation_rows = cursor.fetchall()

        cat_tables = {
            'thiruvachi': 'quot_thiruvachi',
            'kavasam': 'quot_kavasam',
            'vahanam': 'quot_vahanam',
            'kodimaram': 'quot_kodimaram',
            'sheet_metal': 'quot_sheet_metal',
            'panchaloha_statue': 'quot_panchaloha_statue'
        }

        items = []

        for q in quotation_rows:
            table = cat_tables.get(q["category"])
            if not table:
                continue

            cursor.execute(
                f"SELECT * FROM {table} WHERE id=%s",
                (q["quot_id"],)
            )
            d = cursor.fetchone()
            if not d:
                continue

            # merge quotation + details
            item = {
                "category": q["category"],
                **d
            }
            items.append(item)

        return master, items

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/user_quotation_1')
def user_quotation_1():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
        
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        emp_id = session["user_emp_id"]

        cursor.execute("""
            SELECT *
            FROM customers
            WHERE user_emp_id=%s
            ORDER BY id ASC
        """, (emp_id,))
        data = cursor.fetchall()

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"user/quotation_1.html", data=data, msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"user/quotation_1.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



@app.route('/user_quotation_2/<int:cust_id>', methods=["GET"])
def user_quotation_2(cust_id):

    if not session.get("user_logged_in"):
        return render_template("index.html", msg="Your session expired! Please login again!")

    emp_id = session["user_emp_id"]

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM quotations
            WHERE user_emp_id=%s AND cust_id=%s
            ORDER BY id DESC
        """, (emp_id, cust_id))
        quotations_data = cursor.fetchall()

        final_data = []
        for q in quotations_data:
            table_name = cat_quot_tables_dic.get(q["category"])
            if not table_name:
                continue

            cursor.execute(f"""
                SELECT *
                FROM {table_name}
                WHERE id=%s
            """, (q["quot_id"],))
            details = cursor.fetchone()

            if details:
                final_data.append({
                    "quotation": q,
                    "details": details
                })

        return render_template("user/quotation_2.html", 
                               data = final_data, 
                               cust_id = cust_id)

    except mysql.connector.Error as e:
        return render_template("user/quotation_2.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/create_quotations", methods=["POST"])
def create_quotations():

    if not session.get("user_logged_in"):
        return render_template("index.html", msg="Session expired")

    cust_id = request.form.get("cust_id")
    quotation_ids = request.form.get("quotation_ids")

    if not quotation_ids:
        return redirect(url_for("user_quotation_2", cust_id=cust_id))

    quotation_ids = [int(q) for q in quotation_ids.split(",")]
    emp_id = session["user_emp_id"]

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"""
            SELECT *
            FROM quotations
            WHERE id IN ({','.join(['%s']*len(quotation_ids))})
              AND cust_id=%s
              AND user_emp_id=%s
            """,
            (*quotation_ids, cust_id, emp_id)
        )
        quotations = cursor.fetchall()
        if not quotations:
            flash("No valid quotations found.", "warning")
            return redirect(url_for("user_quotation_2", cust_id=cust_id))


        total_SQFT = total_unit = total_cost = total_transport = total_wax_cost = 0
        nilai_padi_plain_total_SQFT = nilai_padi_vargam_total_SQFT = custom_picture_total_SQFT = nilai_padi_plain_unit = nilai_padi_vargam_unit = custom_picture_unit = nilai_padi_plain_final_cost = nilai_padi_vargam_final_cost = custom_picture_final_cost = 0
        
        for q in quotations:
            table = cat_quot_tables_dic[q["category"]]

            cursor.execute(f"""
                SELECT *
                FROM {table}
                WHERE id=%s
            """, (q["quot_id"],))
            d = cursor.fetchone()

            if q["category"] == "thiruvachi":
                total_SQFT += d["SQFT"]
                total_unit += d["unit"]
                total_cost += d["cost"]

            elif q["category"] == "kavasam":
                total_SQFT += d["SQFT"]
                total_wax_cost += d["wax_cost"]
                total_unit += d["unit"]
                total_cost += d["cost"]

            elif q["category"] == "vahanam":
                total_unit += d["unit"]
                total_cost += d["cost"]

            elif q["category"] == "kodimaram":
                total_SQFT += d["SQFT"]
                total_unit += d["unit"]
                total_cost += d["cost"]

            elif q["category"] == "sheet_metal":
                total_SQFT += ((d["nilai_padi_plain_total_SQFT"] or 0)+ (d["nilai_padi_vargam_total_SQFT"] or 0)+ (d["custom_picture_total_SQFT"] or 0))
                total_unit += ((d["nilai_padi_plain_unit"] or 0)+ (d["nilai_padi_vargam_unit"] or 0)+ (d["custom_picture_unit"] or 0))
                total_cost += ((d["nilai_padi_plain_final_cost"] or 0)+ (d["nilai_padi_vargam_final_cost"] or 0)+ (d["custom_picture_final_cost"] or 0))

                nilai_padi_plain_total_SQFT += d["nilai_padi_plain_total_SQFT"]
                nilai_padi_vargam_total_SQFT += d["nilai_padi_vargam_total_SQFT"]
                custom_picture_total_SQFT += d["custom_picture_total_SQFT"]
                nilai_padi_plain_unit += d["nilai_padi_plain_unit"]
                nilai_padi_vargam_unit += d["nilai_padi_vargam_unit"]
                custom_picture_unit += d["custom_picture_unit"]
                nilai_padi_plain_final_cost += d["nilai_padi_plain_final_cost"]
                nilai_padi_vargam_final_cost += d["nilai_padi_vargam_final_cost"]
                custom_picture_final_cost += d["custom_picture_final_cost"]
                thickness = d["thickness"]

            elif q["category"] == "panchaloha_statue":
                total_unit += d["unit"]
                total_cost += d["cost"]
            
            total_transport += d["transport_cost"]


        date_str = datetime.now().strftime("%Y%m%d")
        time_hhmmss = datetime.now().strftime("%H%M%S")
        quotation_no = f"RSS-{emp_id}-{cust_id}-{date_str}-{time_hhmmss}"
        grand_total = total_cost + total_transport + total_wax_cost

        cursor.execute("""
            INSERT INTO master_quotations
            (quotation_no, user_emp_id, cust_id, total_SQFT, total_cost, total_transport, grand_total)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            quotation_no, emp_id, cust_id, total_SQFT, total_cost, total_transport, grand_total
        ))
        master_id = cursor.lastrowid

        for qid in quotation_ids:
            cursor.execute("""
                INSERT INTO 
                    master_quotation_items
                        (master_quotation_id, quotation_id)
                VALUES (%s,%s)
            """, (master_id, qid))

        conn.commit()

        return redirect(url_for("quotation_preview", id=master_id))

    except mysql.connector.Error as e:
        session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_quotation_1"))

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/quotation_preview/<int:id>")
def quotation_preview(id):

    if not session.get("user_logged_in"):
        return redirect(url_for("index"))

    master, items = get_quotation_data(id)

    for item in items:
        if item["category"] == "sheet_metal":
            item["unit"] = (
                (item.get("nilai_padi_plain_unit") or 0)
                + (item.get("nilai_padi_vargam_unit") or 0)
                + (item.get("custom_picture_unit") or 0)
            )

            item["cost"] = (
                (item.get("nilai_padi_plain_final_cost") or 0)
                + (item.get("nilai_padi_vargam_final_cost") or 0)
                + (item.get("custom_picture_final_cost") or 0)
            )

            item["thickness"] = (item.get("thickness") or 0)

    return render_template(
        "user/pdf/quotation_preview.html",
        master=master,
        items=items,
        sales_id=session["user_id"],
        sales_emp_id=session["user_emp_id"],
        sales_name=session["user_name"],
        sales_mobile=session["user_mobile"],
        sales_branch=session["user_branch"]
    )



@app.route("/quotation_pdf", methods=["POST"])
def quotation_pdf():

    quotation_no = request.form.get("quotation_no")

    # -------- Extract date from quotation number --------
    match = re.search(r"\d{8}", quotation_no)
    formatted_date = ""
    if match:
        raw_date = match.group()
        date_obj = datetime.strptime(raw_date, "%Y%m%d")
        formatted_date = date_obj.strftime("%d/%b/%Y")


    items_dict = defaultdict(dict)
    for key, value in request.form.items():
        if key.startswith("items["):
            index = int(key.split("[")[1].split("]")[0])
            field = key.split("[")[2].replace("]", "")
            items_dict[index][field] = value

    items = list(items_dict.values())

    for item in items:
        if item['category'] == 'sheet_metal':
            nilai_padi_plain_total_SQFT = float(item.get("nilai_padi_plain_total_SQFT", 0) or 0)
            nilai_padi_vargam_total_SQFT = float(item.get("nilai_padi_vargam_total_SQFT", 0) or 0)
            custom_picture_total_SQFT = float(item.get("custom_picture_total_SQFT", 0) or 0)

            nilai_padi_plain_unit = float(item.get("nilai_padi_plain_unit", 0))
            nilai_padi_vargam_unit = float(item.get("nilai_padi_vargam_unit", 0))
            custom_picture_unit = float(item.get("custom_picture_unit", 0))

            nilai_padi_plain_final_cost = float(item.get("nilai_padi_plain_final_cost", 0))
            nilai_padi_vargam_final_cost = float(item.get("nilai_padi_vargam_final_cost", 0))
            custom_picture_final_cost = float(item.get("custom_picture_final_cost", 0))

            item["SQFT"] = float(nilai_padi_plain_total_SQFT + nilai_padi_vargam_total_SQFT + custom_picture_total_SQFT)
            item["unit"] = float(nilai_padi_plain_unit + nilai_padi_vargam_unit + custom_picture_unit)
            item["cost_per_qty"] = int((nilai_padi_plain_final_cost + nilai_padi_vargam_final_cost + custom_picture_final_cost) / (nilai_padi_plain_unit + nilai_padi_vargam_unit + custom_picture_unit))
            item["cost"] = int(nilai_padi_plain_final_cost + nilai_padi_vargam_final_cost + custom_picture_final_cost)
        
        else:
            unit = float(item.get("unit", 0))
            cost_per_qty = float(item.get("cost_per_qty", 0))
            item["cost_per_qty"] = int(cost_per_qty)
            item["cost"] = int(unit * cost_per_qty)

    
    # -------- Calculate totals --------
    master_total_items = len(items)
    master_total_qty = 0
    master_total_cost = 0
    master_total_transport = 0

    for item in items:
        master_total_qty += int(item.get("unit", 0))
        master_total_cost += int(float(item.get("cost", 0)))
        master_total_transport += int(float(item.get("transport_cost", 0)))

    master_grand_total = master_total_cost + master_total_transport

    # -------- Render PDF --------
    html = render_template(
        "user/pdf/quotation_pdf.html",

        quotation_no = quotation_no,
        formatted_date = formatted_date,
        items = items,

        sales_name = request.form.get("sales_name"),
        sales_mobile = request.form.get("sales_mobile"),
        branch = request.form.get("branch"),
        company = request.form.get("company"),

        cust_name = request.form.get("cust_name"),
        cust_mobile = request.form.get("cust_mobile"),
        cust_temple = request.form.get("cust_temple"),
        cust_address = request.form.get("cust_address"),

        master_total_items = master_total_items,
        master_total_qty = master_total_qty,
        master_total_cost = master_total_cost,
        master_total_transport = master_total_transport,
        master_grand_total = master_grand_total,

        logo_path = os.path.join(app.root_path, "static/assets/img/RSS_logo.png"),
        base_QR_base64 = image_to_base64(
            os.path.join(app.root_path, "static/assets/img/QR.jpeg")
        )
    )

    pdf = BytesIO()
    pisa.CreatePDF(html, dest=pdf)
    pdf.seek(0)

    response = make_response(pdf.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{quotation_no}.pdf"'
    )
    return response


@app.route("/quotation_pdf/<int:quotation_id>")
def quotation_pdf_share(quotation_id):

    master, items = get_quotation_data(quotation_id)
    # master is a dict
    # items is list of dicts

    # -------- Extract date from quotation number --------
    formatted_date = ""
    match = re.search(r"\d{8}", master["quotation_no"])
    if match:
        formatted_date = datetime.strptime(
            match.group(), "%Y%m%d"
        ).strftime("%d/%b/%Y")

    for row in items:
        unit = row.get("unit", 0)
        cost = row.get("cost", 0)

        if unit:
            row["cost_per_qty"] = int(cost / unit)
        else:
            row["cost_per_qty"] = 0

    html = render_template(
        "user/pdf/quotation_pdf.html",

        quotation_no=master["quotation_no"],
        formatted_date=formatted_date,
        items=items,

        sales_name=master["sales_name"],
        sales_mobile=master["sales_mobile"],
        branch=master["sales_branch"],
        company="Raja Spiritual Pvt Ltd",

        cust_name=master["customer_name"],
        cust_mobile=master["mobile"],
        cust_temple=master["temple"],
        cust_address=master["address"],

        master_total_items=len(items),
        master_total_qty=sum(int(i.get("unit", 0)) for i in items),
        master_total_cost=master["total_cost"],
        master_total_transport=master["total_transport"],
        master_grand_total=master["grand_total"],

        logo_path=os.path.join(
            app.root_path, "static/assets/img/RSS_logo.png"
        ),
        base_QR_base64=image_to_base64(
            os.path.join(app.root_path, "static/assets/img/QR.jpeg")
        )
    )

    pdf = BytesIO()
    pisa.CreatePDF(html, dest=pdf)
    pdf.seek(0)

    response = make_response(pdf.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'inline; filename="{master["quotation_no"]}.pdf"'
    )

    return response


#########################################################


@app.route('/add_customer', methods=["POST"])
def add_customer():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    user_emp_id = session["user_emp_id"]
        
    name = request.form.get("name")
    mobile = request.form.get("mobile")
    temple = request.form.get("temple")
    address = request.form.get("address")

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Insert model
        cursor.execute("""
            INSERT INTO 
                customers
                    (name, mobile, temple, address, user_emp_id)
            VALUES 
                (%s, %s, %s, %s, %s)
        """, (name, mobile, temple, address, user_emp_id))
        conn.commit()
    
    except mysql.connector.Error as e:
        if e.errno == 1062:
            session["msg"] = "Mobile number already exists!"
        else:
            session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_quotation_1"))

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("user_quotation_1"))



@app.route('/update_customer/<int:id>', methods=["POST"])
def update_customer(id):
    if not session.get("user_logged_in"):
        return render_template("index.html", msg="Your session expired! Please login again!")

    user_emp_id = session["user_emp_id"]

    name = request.form.get("name")
    mobile = request.form.get("mobile")
    temple = request.form.get("temple")
    address = request.form.get("address")

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            UPDATE 
                customers
            SET
                name=%s,
                mobile=%s,
                temple=%s,
                address=%s,
                user_emp_id=%s
            WHERE 
                id=%s
        """, (name, mobile, temple, address, user_emp_id, id))
        conn.commit()

    except mysql.connector.Error as e:
        if e.errno == 1062:
            session["msg"] = "Mobile number already exists!"
        else:
            session["msg"] = f"DB Error: {e}"
        return redirect(url_for("user_quotation_1"))

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("user_quotation_1"))



########################### USER QUOTATION HISTORY ###########################
@app.route('/user_history_1', methods=["GET", "POST"])
def user_history_1():
    return render_template(r"user/history_1.html")


##################################################################
##################################################################

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
