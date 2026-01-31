from flask import Flask, flash, render_template, request, redirect, url_for, Response, abort, session, jsonify
import mysql.connector, base64, os
from flask import send_file
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from datetime import datetime
import io
import time

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.secret_key = os.environ.get("SECRET_KEY", "RSS@123")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "user": os.environ.get("DB_USER", "vendor_app"),
    "password": os.environ.get("DB_PASSWORD", "RSS@123"),
    "database": os.environ.get("DB_NAME", "vendor_quotation"),
    "port": int(os.environ.get("DB_PORT", 3306))
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


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



@app.route('/admin_home', methods=["GET"])
def admin_home():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    admin_id = session["admin_id"]
    admin_name = session["admin_name"]
    return render_template(r"admin/home.html")


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
                SELECT id, name, emp_id, email, mobile, password, status
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
            SELECT id, name, emp_id, email, mobile, password, status
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


@app.route("/thiruvachi", methods=["GET", "POST"])
def thiruvachi():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
        
    if request.method == "POST":
        name = request.form.get("name")
        leg_breadth = int(request.form.get("leg_breadth"))
        sheet_thick = int(request.form.get("sheet_thick"))
        work_details = request.form.get("work_details")
        cost = int(request.form.get("cost"))

        file = request.files.get("img")
        img_bytes = None
        img_type = None

        if file and file.filename:
            img_bytes = file.read()
            img_type = file.mimetype

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO cat_thiruvachi
                (name, leg_breadth, sheet_thick, work_details, cost, img, img_type)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s)
                """,
                (name, leg_breadth, sheet_thick, work_details, cost, img_bytes, img_type)
            )
            conn.commit()

        except mysql.connector.Error as e:
            return render_template("admin/thiruvachi.html", data=[], msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for("thiruvachi"))

    # -------- GET (Display) --------
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT model, name, leg_breadth, sheet_thick, work_details, cost, img, img_type
            FROM cat_thiruvachi
            ORDER BY model ASC
        """)
        data = cursor.fetchall()

        # Convert BLOB -> base64 for display
        for row in data:
            if row["img"]:
                row["img_b64"] = base64.b64encode(row["img"]).decode("utf-8")
                row["img_type"] = row["img_type"] or "image/jpeg"
            else:
                row["img_b64"] = None
                row["img_type"] = None

        return render_template("admin/thiruvachi.html", data=data)

    except mysql.connector.Error as e:
        return render_template("admin/thiruvachi.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/thiruvachi_img/<int:model>")
def thiruvachi_img(model):
    if not (session.get("admin_logged_in") or session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT img, img_type FROM cat_thiruvachi WHERE model=%s", (model,))
        row = cursor.fetchone()

        print("IMG ROUTE HIT:", model)
        print("ROW FOUND:", bool(row))
        if row:
            print("IMG BYTES:", None if row["img"] is None else len(row["img"]))
            print("IMG TYPE:", row["img_type"])

        if not row or not row["img"]:
            abort(404)

        mime = row["img_type"] or "image/jpeg"
        return Response(row["img"], mimetype=mime)

    except mysql.connector.Error as e:
        print("DB Error:", e)
        abort(500)

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/thiruvachi/update/<int:model>", methods=["POST"])
def thiruvachi_update(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    name = request.form.get("name")
    leg_breadth = int(request.form.get("leg_breadth"))
    sheet_thick = int(request.form.get("sheet_thick"))
    work_details = request.form.get("work_details")
    cost = int(round(float(request.form.get("cost")),0))

    file = request.files.get("img")
    new_img_bytes = None
    new_img_type = None

    if file and file.filename:
        new_img_bytes = file.read()
        new_img_type = file.mimetype

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if new_img_bytes:
            cursor.execute("""
                UPDATE cat_thiruvachi
                SET name=%s, leg_breadth=%s, sheet_thick=%s, work_details=%s, cost=%s,
                    img=%s, img_type=%s
                WHERE model=%s
            """, (name, leg_breadth, sheet_thick, work_details, cost, new_img_bytes, new_img_type, model))
        else:
            cursor.execute("""
                UPDATE cat_thiruvachi
                SET name=%s, leg_breadth=%s, sheet_thick=%s, work_details=%s, cost=%s
                WHERE model=%s
            """, (name, leg_breadth, sheet_thick, work_details, cost, model))

        conn.commit()

    except mysql.connector.Error as e:
        print("DB Error:", e)

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("thiruvachi"))


@app.route("/thiruvachi/delete/<int:model>", methods=["POST"])
def thiruvachi_delete(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cat_thiruvachi WHERE model=%s", (model,))
        conn.commit()

    except mysql.connector.Error as e:
        print("DB Error:", e)

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("thiruvachi"))


@app.route('/kavasam', methods=["GET", "POST"])
def kavasam():
    print(111111111111)
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        print(22222222222)
        sqft = int(request.form.get("sqft"))
        gauge_24 = int(request.form.get("gauge_24"))
        gauge_22 = int(request.form.get("gauge_22"))
        gauge_20 = int(request.form.get("gauge_20"))
        wax_cost = int(request.form.get("wax_cost"))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO cat_kavasam
                (sqft, gauge_24, gauge_22, gauge_20, wax_cost)
                VALUES
                (%s, %s, %s, %s, %s)
                """,
                (sqft, gauge_24, gauge_22, gauge_20, wax_cost)
            )
            conn.commit()

        except mysql.connector.Error as e:
            if e.errno == 1062:
                session['msg'] = f"SQFT Range {sqft} already exists!"
            else:
                session['msg'] = f"DB Error: {e}"

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for("kavasam"))

    # -------- GET (Display) --------
    print(3333333333)
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        print(4444444444)

        cursor.execute("""
            SELECT *
            FROM cat_kavasam
            ORDER BY sqft ASC
        """)
        data = cursor.fetchall()
        print(55555555)

        cursor.execute("""
            SELECT *
            FROM cat_kavasam_rates
        """)
        rate_data = cursor.fetchall()
        print(666666666)

        if rate_data:
            print(77777777777)
            rate_data = rate_data[0]

        msg = session.get('msg')
        session['msg'] = False
        print(8888888888888)
        return render_template("admin/kavasam.html",
                                data = data,
                                rate_data = rate_data,
                                msg = msg)

    # except mysql.connector.Error as e:
    #     return render_template("admin/kavasam.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/kavasam_rates/update/', methods=["POST"])
def kavasam_rates():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    silver_rate = int(request.form.get("silver_rate"))
    pure_silver_rate = int(request.form.get("pure_silver_rate"))
    pure_silver_margin_rate = int(request.form.get("pure_silver_margin_rate"))
    gold_rate = int(request.form.get("gold_rate"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

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


@app.route("/kavasam/update/<int:model>", methods=["POST"])
def kavasam_update(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    sqft = int(request.form.get("sqft"))
    gauge_24 = int(request.form.get("gauge_24"))
    gauge_22 = int(request.form.get("gauge_22"))
    gauge_20 = int(request.form.get("gauge_20"))
    wax_cost = int(request.form.get("wax_cost"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE 
                cat_kavasam
            SET 
                sqft = %s, 
                gauge_24 = %s, 
                gauge_22 = %s, 
                gauge_20 = %s, 
                wax_cost = %s
            WHERE 
                model = %s
        """, (sqft, gauge_24, gauge_22, gauge_20, wax_cost, model))
        conn.commit()

    except mysql.connector.Error as e:
        if e.errno == 1062:
            session['msg'] = f"SQFT Range {sqft} already exists!"
        else:
            session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("kavasam"))


@app.route("/kavasam/delete/<int:model>", methods=["POST"])
def kavasam_delete(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cat_kavasam WHERE model=%s", (model,))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("kavasam"))



@app.route('/vahanam', methods=["GET", "POST"])
def vahanam():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        name = request.form.get("name")
        specification = request.form.get("specification")
        height_1_5ft = int(request.form.get("height_1_5ft"))
        height_2ft = int(request.form.get("height_2ft"))
        height_2_5ft = int(request.form.get("height_2_5ft"))
        height_3ft = int(request.form.get("height_3ft"))
        height_3_5ft = int(request.form.get("height_3_5ft"))
        height_4ft = int(request.form.get("height_4ft"))
        height_5ft = int(request.form.get("height_5ft"))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO cat_vahanam
                (name, specification, height_1_5ft, height_2ft, height_2_5ft, height_3ft, height_3_5ft, height_4ft, height_5ft)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (name, specification, height_1_5ft, height_2ft, height_2_5ft, height_3ft, height_3_5ft, height_4ft, height_5ft)
            )
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

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"admin/vahanam.html", data=data, msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"admin/vahanam.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/vahanam/update/<int:model>", methods=["POST"])
def vahanam_update(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    name = request.form.get("name")
    specification = request.form.get("specification")
    height_1_5ft = int(request.form.get("height_1_5ft"))
    height_2ft = int(request.form.get("height_2ft"))
    height_2_5ft = int(request.form.get("height_2_5ft"))
    height_3ft = int(request.form.get("height_3ft"))
    height_3_5ft = int(request.form.get("height_3_5ft"))
    height_4ft = int(request.form.get("height_4ft"))
    height_5ft = int(request.form.get("height_5ft"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE 
                cat_vahanam
            SET 
                name = %s,
                specification = %s,
                height_1_5ft = %s,
                height_2ft = %s,
                height_2_5ft = %s,
                height_3ft = %s,
                height_3_5ft = %s,
                height_4ft = %s,
                height_5ft = %s
            WHERE 
                model = %s
        """, (name, specification, height_1_5ft, height_2ft, height_2_5ft, height_3ft, height_3_5ft, height_4ft, height_5ft, model))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("vahanam"))


@app.route("/vahanam/delete/<int:model>", methods=["POST"])
def vahanam_delete(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cat_vahanam WHERE model=%s", (model,))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("vahanam"))



@app.route('/sheet_metal', methods=["GET", "POST"])
def sheet_metal():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        heads = request.form.get("heads")
        work_desc = request.form.get("work_desc", None)
        gauge_20__below_21_sqft = int(request.form.get("gauge_20__below_21_sqft"), 0)
        gauge_20__21_50_sqft = int(request.form.get("gauge_20__21_50_sqft"), 0)
        gauge_20__above_50_sqft = int(request.form.get("gauge_20__above_50_sqft"), 0)
        gauge_22__below_21_sqft = int(request.form.get("gauge_22__below_21_sqft"), 0)
        gauge_22__21_50_sqft = int(request.form.get("gauge_22__21_50_sqft"), 0)
        gauge_22__above_50_sqft = int(request.form.get("gauge_22__above_50_sqft"), 0)
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO cat_sheet_metal
                (heads, work_desc, gauge_20__below_21_sqft, gauge_20__21_50_sqft, gauge_20__above_50_sqft, gauge_22__below_21_sqft, gauge_22__21_50_sqft, gauge_22__above_50_sqft)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (heads, work_desc, gauge_20__below_21_sqft, gauge_20__21_50_sqft, gauge_20__above_50_sqft, gauge_22__below_21_sqft, gauge_22__21_50_sqft, gauge_22__above_50_sqft)
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

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"admin/sheet_metal.html", data=data, msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"admin/sheet_metal.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/sheet_metal/update/<int:model>", methods=["POST"])
def sheet_metal_update(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    heads = request.form.get("heads")
    work_desc = request.form.get("work_desc", None)
    gauge_20__below_21_sqft = int(request.form.get("gauge_20__below_21_sqft"), 0)
    gauge_20__21_50_sqft = int(request.form.get("gauge_20__21_50_sqft"), 0)
    gauge_20__above_50_sqft = int(request.form.get("gauge_20__above_50_sqft"), 0)
    gauge_22__below_21_sqft = int(request.form.get("gauge_22__below_21_sqft"), 0)
    gauge_22__21_50_sqft = int(request.form.get("gauge_22__21_50_sqft"), 0)
    gauge_22__above_50_sqft = int(request.form.get("gauge_22__above_50_sqft"), 0)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    
        cursor.execute("""
            UPDATE cat_sheet_metal
            SET heads=%s, work_desc=%s, gauge_20__below_21_sqft=%s, gauge_20__21_50_sqft=%s, gauge_20__above_50_sqft=%s, gauge_22__below_21_sqft=%s, gauge_22__21_50_sqft=%s, gauge_22__above_50_sqft=%s
            WHERE model=%s
        """, (heads, work_desc, gauge_20__below_21_sqft, gauge_20__21_50_sqft, gauge_20__above_50_sqft, gauge_22__below_21_sqft, gauge_22__21_50_sqft, gauge_22__above_50_sqft, model))
        conn.commit()

    except mysql.connector.Error as e:
        print("DB Error:", e)
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("sheet_metal"))


@app.route("/sheet_metal/delete/<int:model>", methods=["POST"])
def sheet_metal_delete(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cat_sheet_metal WHERE model=%s", (model,))
        conn.commit()

    except mysql.connector.Error as e:
        print("DB Error:", e)

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("sheet_metal"))
    

@app.route('/panchaloha_statue', methods=["GET", "POST"])
def panchaloha_statue():
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
        idol_name = request.form.get("idol_name")
        position = request.form.get("position")
        height = float(request.form.get("height"))
        hands = int(request.form.get("hands"))
        with_prabhavalli = request.form.get("with_prabhavalli")
        apx_weight = float(request.form.get("apx_weight"))
        cost = int(request.form.get("cost"))
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO 
                    cat_panchaloha_statue 
                        (idol_name, position, height, hands, with_prabhavalli, apx_weight, cost) 
                    VALUES 
                        (%s, %s, %s, %s, %s, %s, %s)""",
                (idol_name, position, height, hands, with_prabhavalli, apx_weight, cost)
            )
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

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"admin/panchaloha_statue.html", get_data=data, msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"admin/panchaloha_statue.html", get_data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/panchaloha_statue/update/<int:model>", methods=["POST"])
def panchaloha_statue_update(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    idol_name = request.form.get("idol_name")
    position = request.form.get("position")
    height = float(request.form.get("height"))
    hands = int(request.form.get("hands"))
    with_prabhavalli = request.form.get("with_prabhavalli")
    apx_weight = float(request.form.get("apx_weight"))
    cost = int(request.form.get("cost"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    
        cursor.execute("""
            UPDATE 
                cat_panchaloha_statue
            SET 
                idol_name=%s,
                position=%s,
                height=%s,
                hands=%s,
                with_prabhavalli=%s,
                apx_weight=%s,
                cost=%s
            WHERE 
                model=%s
        """, (idol_name, position, height, hands, with_prabhavalli, apx_weight, cost, model))
        conn.commit()

    except mysql.connector.Error as e:
        session['msg'] = f"DB Error: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("panchaloha_statue"))


@app.route("/panchaloha_statue/delete/<int:model>", methods=["POST"])
def panchaloha_statue_delete(model):
    if not(session.get("admin_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cat_panchaloha_statue WHERE model=%s", (model,))
        conn.commit()

    except mysql.connector.Error as e:
        print("DB Error:", e)

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("panchaloha_statue"))

##################################################################
########################### USER PANEL ###########################
##################################################################

@app.route('/user_register', methods=["GET", "POST"])
def user_register():
    if request.method == "POST":
        name = request.form.get("name")
        emp_id = request.form.get("emp_id")
        email = request.form.get("email")
        mobile = request.form.get("mobile")
        password = request.form.get("password")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

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
                  (name, emp_id, email, mobile, password)
                VALUES
                  (%s, %s, %s, %s, %s)
                """,
                (name, emp_id, email, mobile, password)
            )
            conn.commit()

        except mysql.connector.Error as e:
            return render_template(r"user/register.html", msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return render_template(r"user/register.html", msg=f"Registered successfully! Please wait for admin approval to logIn!")
    return render_template(r"user/register.html")


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
                "SELECT id, name, status FROM users WHERE email=%s AND password=%s",
                (email, password)
            )
            user = cursor.fetchone()

            if user:
                if user['status'] == 'approved':
                    session["user_logged_in"] = True
                    session["user_id"] = user["id"]
                    session["user_name"] = user["name"]
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


@app.route('/user_home', methods=["GET"])
def user_home():
    if session.get("user_logged_in"):
        user_id = session["user_id"]
        user_name = session["user_name"]
        return render_template(r"user/home.html", user_id=user_id, user_name=user_name)
    else:
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)



@app.route("/user_thiruvachi", methods=["GET", "POST"])
def user_thiruvachi():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":

        height = float(request.form.get("height"))
        UOM_Height = request.form.get("UOM_Height")

        if UOM_Height == 'Feet':
            deity_height = height * 12
        else:
            deity_height = height

        if deity_height < 60:
            prabhavali_inner_height = deity_height + 6
        else:
            prabhavali_inner_height = deity_height + 10

        ###############

        width = float(request.form.get("width"))
        UOM_Width = request.form.get("UOM_Width")

        if UOM_Width == 'Feet':
            deity_width = width * 12
        else:
            deity_width = width

        if deity_width < 60:
            prabhavali_inner_width = deity_width + 6
        else:
            prabhavali_inner_width = deity_width + 10

        no_of_Square_feet = (prabhavali_inner_height + prabhavali_inner_width) / 12

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT model, name, leg_breadth, sheet_thick, work_details, cost, img, img_type
                FROM cat_thiruvachi
                ORDER BY model ASC
            """)
            data = cursor.fetchall()
            
            for row in data:
                if row["img"]:
                    row["img_b64"] = base64.b64encode(row["img"]).decode("utf-8")
                    row["img_type"] = row["img_type"] or "image/jpeg"
                else:
                    row["img_b64"] = None
                    row["img_type"] = None

            return render_template("user/thiruvachi.html", data=data, no_of_Square_feet=no_of_Square_feet)

        except mysql.connector.Error as e:
            return render_template("user/thiruvachi.html", data=[], msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # -------- GET (Display) --------
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_thiruvachi
            ORDER BY model ASC
        """)
        data = cursor.fetchall()

        for row in data:
            if row["img"]:
                row["img_b64"] = base64.b64encode(row["img"]).decode("utf-8")
                row["img_type"] = row["img_type"] or "image/jpeg"
            else:
                row["img_b64"] = None
                row["img_type"] = None

        msg = session.get('msg')
        session['msg'] = False
        return render_template("user/thiruvachi.html", get_data=data, msg=msg)

    except mysql.connector.Error as e:
        return render_template("user/thiruvachi.html", get_data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/user_kavasam', methods=["GET", "POST"])
def user_kavasam():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    if request.method == "POST":
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

        total_sqft = 0
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

            sqft = (deity_height * deity_width) / 144
            total_sqft += sqft

            m["height_ft"] = float(height)
            m["width_ft"] = float(width)
            m["sqft"] = float(sqft)


        # height = float(request.form.get("height"))
        # UOM_Height = request.form.get("UOM_Height")

        # width = float(request.form.get("width"))
        # UOM_Width = request.form.get("UOM_Width")


        # if UOM_Height == 'Feet':
        #     deity_height = height * 12
        # else:
        #     deity_height = height

        # if UOM_Width == 'Feet':
        #     deity_width = width * 12
        # else:
        #     deity_width = width

        # total_sqft = (deity_height * deity_width) / 144

        if total_sqft % 1 != 0:
            SQFT_Range = int(total_sqft) + 1
        else:
            SQFT_Range = int(total_sqft)

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT *
                FROM cat_kavasam
                WHERE sqft=%s
            """, (SQFT_Range,))
            data = cursor.fetchall()

            cursor.execute("""
                SELECT *
                FROM cat_kavasam_rates
            """)
            rate_data = cursor.fetchall()

            if data:
                data = data[0]

            if rate_data:
                rate_data = rate_data[0]
                
            flash(f"Actual no of Square Feet : {total_sqft}", "info")
            return render_template("user/kavasam.html", 
                                   data = data, 
                                   rate_data = rate_data, 
                                   SQFT_Range = SQFT_Range, 
                                   total_sqft = total_sqft)

        except mysql.connector.Error as e:
            return render_template("user/kavasam.html", data=[], msg=f"DB Error: {e}")

        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # -------- GET (Display) --------
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM cat_kavasam
            ORDER BY sqft ASC
        """)
        data = cursor.fetchall()

        cursor.execute("""
            SELECT *
            FROM cat_kavasam_rates
        """)
        rate_data = cursor.fetchall()

        if rate_data:
            rate_data = rate_data[0]

        msg = session.get('msg')
        session['msg'] = False
        return render_template("user/kavasam.html",
                                get_data = data,
                                get_rate_data = rate_data,
                                msg = msg)

    except mysql.connector.Error as e:
        return render_template("user/kavasam.html", data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/user_vahanam', methods=["GET", "POST"])
def user_vahanam():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
        
    if request.method == "POST":
        name = request.form.get("name")
        height_range = request.form.get("height_range")

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT specification, {height_range}
                FROM cat_vahanam
                WHERE name=%s
            """, (name,))

            data = cursor.fetchall()
            specification = data[0][0]
            cost = data[0][1]

            height = {
                'height_1_5ft' : '1.5 Feet',
                'height_2ft' : '2 Feet',
                'height_2_5ft' : '2.5 Feet',
                'height_3ft' : '3 Feet',
                'height_3_5ft' : '3.5 Feet',
                'height_4ft' : '4 Feet',
                'height_5ft' : '5 Feet'
            }
            height = height[height_range]
            
            return render_template(r"user/vahanam.html", 
                                   name = name,
                                   specification = specification,
                                   height = height,
                                   cost = cost)

        except mysql.connector.Error as e:
                session['msg'] = f"DB Error: {e}"

        finally:
            if cursor: cursor.close()
            if conn: conn.close()


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

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"user/vahanam.html", get_data=data, msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"user/vahanam.html", get_data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



@app.route('/user_kodimaram', methods=["GET", "POST"])
def user_kodimaram():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    data = None
    if request.method == "POST":
        height = float(request.form.get("height"))
        UOM_Height = request.form.get("UOM_Height")

        diameter = float(request.form.get("diameter"))
        UOM_Diameter = request.form.get("UOM_Diameter")

        if UOM_Height == 'Feet':
            deity_height = height * 12
        else:
            deity_height = height

        if UOM_Diameter == 'Feet':
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

        if Apx_SQFT < 50:
            cost = 4000
        elif Apx_SQFT >= 50 and Apx_SQFT <= 100:
            cost = 3750
        else:
            cost = 3500
        
        Total_cost = Apx_SQFT * cost

        Total_cost_with_GST = round(Total_cost * 1.05, 2)

        data = {
            "height" : deity_height,
            "diameter" : deity_diameter,

            "Batmam_Hgt_perc" : Batmam_Hgt_perc,
            "Batmam_Hgt" : Batmam_Hgt,
            "Batmam_Dia_perc" : Batmam_Dia_perc,
            "Batmam_Dia" : Batmam_Dia,
            "Batmam_KM_SQFT" : Batmam_KM_SQFT,
            "Small_Arada_1_Hgt_perc" : Small_Arada_1_Hgt_perc,
            "Small_Arada_1_Hgt" : Small_Arada_1_Hgt,
            "Small_Arada_1_Dia_perc" : Small_Arada_1_Dia_perc,
            "Small_Arada_1_Dia" : Small_Arada_1_Dia,
            "Small_Arada_1_KM_SQFT" : Small_Arada_1_KM_SQFT,
            "Arada_Hgt_perc" : Arada_Hgt_perc,
            "Arada_Hgt" : Arada_Hgt,
            "Arada_Dia_perc" : Arada_Dia_perc,
            "Arada_Dia" : Arada_Dia,
            "Arada_KM_SQFT" : Arada_KM_SQFT,
            "Small_Arada_2_Hgt_perc" : Small_Arada_2_Hgt_perc,
            "Small_Arada_2_Hgt" : Small_Arada_2_Hgt,
            "Small_Arada_2_Dia_perc" : Small_Arada_2_Dia_perc,
            "Small_Arada_2_Dia" : Small_Arada_2_Dia,
            "Small_Arada_2_KM_SQFT" : Small_Arada_2_KM_SQFT,
            "Box_Hgt_perc" : Box_Hgt_perc,
            "Box_Hgt" : Box_Hgt,
            "Box_Dia_perc" : Box_Dia_perc,
            "Box_Dia" : Box_Dia,
            "Box_KM_SQFT" : Box_KM_SQFT,
            "Nagabanthanam_1_Hgt_perc" : Nagabanthanam_1_Hgt_perc,
            "Nagabanthanam_1_Hgt" : Nagabanthanam_1_Hgt,
            "Nagabanthanam_1_Dia_perc" : Nagabanthanam_1_Dia_perc,
            "Nagabanthanam_1_Dia" : Nagabanthanam_1_Dia,
            "Nagabanthanam_1_KM_SQFT" : Nagabanthanam_1_KM_SQFT,
            "Kuvalai_Hgt_perc" : Kuvalai_Hgt_perc,
            "Kuvalai_Hgt" : Kuvalai_Hgt,
            "Kuvalai_Dia_perc" : Kuvalai_Dia_perc,
            "Kuvalai_Dia" : Kuvalai_Dia,
            "Kuvalai_KM_SQFT" : Kuvalai_KM_SQFT,
            "Nagabanthanam_2_Hgt_perc" : Nagabanthanam_2_Hgt_perc,
            "Nagabanthanam_2_Hgt" : Nagabanthanam_2_Hgt,
            "Nagabanthanam_2_Dia_perc" : Nagabanthanam_2_Dia_perc,
            "Nagabanthanam_2_Dia" : Nagabanthanam_2_Dia,
            "Nagabanthanam_2_KM_SQFT" : Nagabanthanam_2_KM_SQFT,
            "manipalagai_Hgt_perc" : manipalagai_Hgt_perc,
            "manipalagai_Hgt" : manipalagai_Hgt,
            "manipalagai_Dia_perc" : manipalagai_Dia_perc,
            "manipalagai_Dia" : manipalagai_Dia,
            "manipalagai_KM_SQFT" : manipalagai_KM_SQFT,
            "kalasam_Hgt_perc" : kalasam_Hgt_perc,
            "kalasam_Hgt" : kalasam_Hgt,
            "kalasam_Dia_perc" : kalasam_Dia_perc,
            "kalasam_Dia" : kalasam_Dia,
            "Visiribalagai_Hgt_perc" : Visiribalagai_Hgt_perc,
            "Visiribalagai_Hgt" : Visiribalagai_Hgt,
            "Visiribalagai_Dia_perc" : Visiribalagai_Dia_perc,
            "Visiribalagai_Dia" : Visiribalagai_Dia,
            "Visiribalagai_side_Hgt_perc" : Visiribalagai_side_Hgt_perc,
            "Visiribalagai_side_Hgt" : Visiribalagai_side_Hgt,
            "Visiribalagai_side_Dia_perc" : Visiribalagai_side_Dia_perc,
            "Visiribalagai_side_Dia" : Visiribalagai_side_Dia,
            "Visiribalagai_VB_SQFT" : Visiribalagai_VB_SQFT,
            "Visiribalagai_side_VB_SQFT" : Visiribalagai_side_VB_SQFT,
            "Total_Hgt" : Total_Hgt,
            "Total_Dia" : Total_Dia,
            "Total_KM_SQFT" : Total_KM_SQFT,
            "Total_VB_SQFT" : Total_VB_SQFT,

            "Apx_SQFT" : Apx_SQFT,
            "Apx_Wgt" : Apx_Wgt,
            "cost" : cost,
            "Total_cost" : Total_cost,
            "Total_cost_with_GST" : Total_cost_with_GST
        }
        
    return render_template(r"user/kodimaram.html", data=data)


@app.route('/user_sheet_metal', methods=["GET", "POST"])
def user_sheet_metal():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
    
    data = None
    if request.method == "POST":
        Gauge = request.form.get("Gauge")

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

        nilai_padi_20_total_sqft = 0
        nilai_padi_vargam_total_sqft = 0
        pic_count = 0

        for m in measures:
            if m["type"] == "nilai_padi_20":
                nilai_padi_20_height = float(m["height"])
                nilai_padi_20_width = float(m["width"])

                if m["uom_height"].lower().startswith("inch"):
                    nilai_padi_20_height = nilai_padi_20_height / 12

                if m["uom_width"].lower().startswith("inch"):
                    nilai_padi_20_width = nilai_padi_20_width / 12

                sqft = nilai_padi_20_height * nilai_padi_20_width
                nilai_padi_20_total_sqft += sqft

                m["height_ft"] = float(nilai_padi_20_height)
                m["width_ft"] = float(nilai_padi_20_width)
                m["sqft"] = float(sqft)

            if m["type"] == "nilai_padi_vargam":
                nilai_padi_vargam_height = float(m["height"])
                nilai_padi_vargam_width = float(m["width"])

                if m["uom_height"].lower().startswith("inch"):
                    nilai_padi_vargam_height = nilai_padi_vargam_height / 12

                if m["uom_width"].lower().startswith("inch"):
                    nilai_padi_vargam_width = nilai_padi_vargam_width / 12

                sqft = nilai_padi_vargam_height * nilai_padi_vargam_width
                nilai_padi_vargam_total_sqft += sqft

                m["height_ft"] = float(nilai_padi_vargam_height)
                m["width_ft"] = float(nilai_padi_vargam_width)
                m["sqft"] = float(sqft)

            if m["type"] == 'custom_picture':
                count = float(m["count"])
                pic_count += count
        
        if (pic_count > 0 and nilai_padi_20_total_sqft == 0 and nilai_padi_vargam_total_sqft == 0): 
            return render_template(r"user/sheet_metal.html", data=[], msg="Please add 'Nilai Padi -20% Picture' or 'Nilai Padi Normal + Vargam + 20% Picture' measure before giving 'Additional Customized Picture")

        if nilai_padi_20_total_sqft:
            if Gauge == "20 Gauge" and nilai_padi_20_total_sqft < 21:
                nilai_padi_20_col = 'gauge_20__below_21_sqft'
            elif Gauge == "20 Gauge" and nilai_padi_20_total_sqft >= 21 and nilai_padi_20_total_sqft <= 50:
                nilai_padi_20_col = 'gauge_20__21_50_sqft'
            elif Gauge == "20 Gauge" and nilai_padi_20_total_sqft > 50:
                nilai_padi_20_col = 'gauge_20__above_50_sqft'
            elif Gauge == "22 Gauge" and nilai_padi_20_total_sqft < 21:
                nilai_padi_20_col = 'gauge_22__below_21_sqft'
            elif Gauge == "22 Gauge" and nilai_padi_20_total_sqft >= 21 and nilai_padi_20_total_sqft <= 50:
                nilai_padi_20_col = 'gauge_22__21_50_sqft'
            elif Gauge == "22 Gauge" and nilai_padi_20_total_sqft > 50:
                nilai_padi_20_col = 'gauge_22__above_50_sqft'
        else:
            nilai_padi_20_col = None

        if nilai_padi_vargam_total_sqft:
            if Gauge == "20 Gauge" and nilai_padi_vargam_total_sqft < 21:
                nilai_padi_vargam_col = 'gauge_20__below_21_sqft'
            elif Gauge == "20 Gauge" and nilai_padi_vargam_total_sqft >= 21 and nilai_padi_vargam_total_sqft <= 50:
                nilai_padi_vargam_col = 'gauge_20__21_50_sqft'
            elif Gauge == "20 Gauge" and nilai_padi_vargam_total_sqft > 50:
                nilai_padi_vargam_col = 'gauge_20__above_50_sqft'
            elif Gauge == "22 Gauge" and nilai_padi_vargam_total_sqft < 21:
                nilai_padi_vargam_col = 'gauge_22__below_21_sqft'
            elif Gauge == "22 Gauge" and nilai_padi_vargam_total_sqft >= 21 and nilai_padi_vargam_total_sqft <= 50:
                nilai_padi_vargam_col = 'gauge_22__21_50_sqft'
            elif Gauge == "22 Gauge" and nilai_padi_vargam_total_sqft > 50:
                nilai_padi_vargam_col = 'gauge_22__above_50_sqft'
        else:
            nilai_padi_vargam_col = None
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            if nilai_padi_20_col:
                cursor.execute(f"""SELECT {nilai_padi_20_col} FROM cat_sheet_metal""")
                nilai_padi_20_data = cursor.fetchall()
            else:
                nilai_padi_20_data = None

            if nilai_padi_vargam_col:
                cursor.execute(f"""SELECT {nilai_padi_vargam_col} FROM cat_sheet_metal""")
                nilai_padi_vargam_data = cursor.fetchall()
            else:
                nilai_padi_vargam_data = None
        
        except mysql.connector.Error as e:
            return render_template(r"user/sheet_metal.html", data=[], msg=f"DB Error: {e}")
        
        nilai_padi_20_total_cost = 0
        if nilai_padi_20_data:
            nilai_padi_20_cost = nilai_padi_20_data[0][0]
            nilai_padi_20_total_cost = nilai_padi_20_total_sqft * nilai_padi_20_cost

        nilai_padi_vargam_total_cost = 0
        if nilai_padi_vargam_data:
            nilai_padi_vargam_cost = nilai_padi_vargam_data[1][0]
            nilai_padi_vargam_total_cost = nilai_padi_vargam_total_sqft * nilai_padi_vargam_cost

        nilai_padi_total_cost = nilai_padi_20_total_cost + nilai_padi_vargam_total_cost

        custom_pic_total_cost = 0
        if pic_count:
            if nilai_padi_20_data:
                custom_pic_cost = nilai_padi_20_data[2][0]
            elif nilai_padi_vargam_data:
                custom_pic_cost = nilai_padi_vargam_data[2][0]
            custom_pic_total_cost = pic_count * custom_pic_cost

        total_cost = nilai_padi_total_cost + custom_pic_total_cost
        total_cost_with_GST = total_cost * 1.05

        data = {
            'Gauge' : Gauge,
            'nilai_padi_20_SQFT' : nilai_padi_20_total_sqft,
            'nilai_padi_vargam_SQFT' : nilai_padi_vargam_total_sqft,
            'pic' : pic_count,
            'total_cost' : total_cost,
            'total_cost_with_GST' : total_cost_with_GST
        }
        return render_template(r"user/sheet_metal.html", data = data)

    # --- GET ---
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(f"""SELECT * FROM cat_sheet_metal""")
        data = cursor.fetchall()
    
    except mysql.connector.Error as e:
        return render_template(r"user/sheet_metal.html", get_data=[], msg=f"DB Error: {e}")
    
    msg = session.get('msg')
    session['msg'] = False
    return render_template(r"user/sheet_metal.html", 
                           get_data = data,
                           msg = msg)



@app.route('/user_panchaloha_status', methods=["GET", "POST"])
def user_panchaloha_status():
    if not(session.get("user_logged_in")):
        msg = "Your session expired! Please login again!"
        return render_template(r"index.html", msg=msg)
        
    if request.method == "POST":
        idol_name = request.form.get("idol_name")
        height = float(request.form.get("height"))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(f"""
                SELECT *
                FROM cat_panchaloha_statue
                WHERE idol_name=%s and height=%s
            """, (idol_name, height))
            data = cursor.fetchall()

            cursor.execute("""
                SELECT DISTINCT idol_name
                FROM cat_panchaloha_statue
                ORDER BY idol_name
            """)
            idol_data = cursor.fetchall()
            
            return render_template(r"user/panchaloha_status.html", data=data[0], idol_data=idol_data)

        except mysql.connector.Error as e:
                session['msg'] = f"DB Error: {e}"

        finally:
            if cursor: cursor.close()
            if conn: conn.close()


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

        cursor.execute("""
            SELECT DISTINCT idol_name
            FROM cat_panchaloha_statue
            ORDER BY idol_name
        """)
        idol_data = cursor.fetchall()

        msg = session.get('msg')
        session['msg'] = False
        return render_template(r"user/panchaloha_status.html", get_data=data, idol_data=idol_data, msg=msg)

    except mysql.connector.Error as e:
        return render_template(r"user/panchaloha_status.html", get_data=[], msg=f"DB Error: {e}")

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/get_panchaloha_heights')
def get_panchaloha_heights():
    idol_name = request.args.get("idol_name")

    conn = cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT DISTINCT height
            FROM cat_panchaloha_statue
            WHERE idol_name = %s
            ORDER BY height
        """, (idol_name,))

        heights = cursor.fetchall()
        return jsonify(heights)

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


##################################################################
##################################################################
##################################################################

if __name__ == "__main__":
    app.run()
