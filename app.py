from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "badminton_secret_key_2026"
DATABASE = "badminton.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    connection = get_db()
    
    # 1. Bảng trận đấu
    connection.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            court TEXT NOT NULL,
            player1 TEXT NOT NULL,
            player2 TEXT NOT NULL,
            score1 INTEGER DEFAULT 0,
            score2 INTEGER DEFAULT 0,
            status TEXT DEFAULT 'waiting',
            match_time TEXT DEFAULT '',
            location TEXT DEFAULT 'Nhà thi đấu ĐH Văn Lang'
        )
    """)

    # 2. Bảng vận động viên
    connection.execute("""
        CREATE TABLE IF NOT EXISTS athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT DEFAULT 'Chờ duyệt',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Bảng người dùng (Guest)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # 4. Bảng cấu hình hệ thống
    connection.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    connection.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('tournament_name', 'GIẢI CẦU LÔNG VÔ ĐỊCH TOÀN QUỐC 2026')")
    connection.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('start_date', '2026-09-15')")
    connection.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('end_date', '2026-09-20')")
    connection.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('tournament_location', 'Nhà thi đấu ĐH Văn Lang - TP. Hồ Chí Minh')")
    connection.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fee_single', '100000')")
    connection.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fee_double', '200000')")

    connection.commit()
    connection.close()

def get_settings():
    connection = get_db()
    rows = connection.execute("SELECT key, value FROM settings").fetchall()
    connection.close()
    data = {r["key"]: r["value"] for r in rows}
    return {
        "tournament_name": data.get("tournament_name", "GIẢI CẦU LÔNG MỞ RỘNG 2026"),
        "start_date": data.get("start_date", "2026-09-15"),
        "end_date": data.get("end_date", "2026-09-20"),
        "tournament_location": data.get("tournament_location", "Nhà thi đấu ĐH Văn Lang"),
        "fee_single": int(data.get("fee_single", 100000)),
        "fee_double": int(data.get("fee_double", 200000))
    }

# =========================
# GIAO DIỆN KHÁCH / LIVESCORE
# =========================
@app.route("/")
def home():
    connection = get_db()
    matches = connection.execute("SELECT * FROM matches ORDER BY id DESC").fetchall()
    connection.close()
    settings = get_settings()
    return render_template("index.html", matches=matches, settings=settings)

# =========================
# ĐĂNG KÝ VẬN ĐỘNG VIÊN
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    connection = get_db()
    message = None

    if request.method == "POST":
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        categories = request.form.getlist("category")
        category_str = ", ".join(categories)

        if full_name and phone and category_str:
            connection.execute("""
                INSERT INTO athletes (full_name, phone, category, status)
                VALUES (?, ?, ?, 'Chờ duyệt')
            """, (full_name, phone, category_str))
            connection.commit()
            message = "Đăng ký thành công! BTC sẽ kiểm tra thanh toán và duyệt danh sách."

    settings = get_settings()
    connection.close()
    return render_template("register.html", message=message, fee_single=settings["fee_single"], fee_double=settings["fee_double"], tournament_name=settings["tournament_name"])

# =========================
# XÁC THỰC THÀNH VIÊN (GUEST)
# =========================
@app.route("/login", methods=["GET", "POST"])
def guest_login():
    error = None
    success = None
    if request.method == "POST":
        action = request.form.get("action")

        if action == "login":
            email = request.form.get("email")
            password = request.form.get("password")
            connection = get_db()
            user = connection.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password)).fetchone()
            connection.close()

            if user:
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                return redirect(url_for("home"))
            else:
                error = "Email hoặc mật khẩu không chính xác!"

        elif action == "register":
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")
            connection = get_db()
            try:
                connection.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
                connection.commit()
                success = "Tạo tài khoản thành công! Bạn có thể đăng nhập ngay."
            except sqlite3.IntegrityError:
                error = "Email này đã được sử dụng!"
            finally:
                connection.close()

    return render_template("login.html", error=error, success=success)

@app.route("/auth/<provider>")
def social_auth(provider):
    if provider == "google":
        session["user_name"] = "Google User"
        session["user_email"] = "user@gmail.com"
    elif provider == "facebook":
        session["user_name"] = "Facebook User"
        session["user_email"] = "user@facebook.com"
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop("user_name", None)
    session.pop("user_email", None)
    return redirect(url_for("home"))

# =========================
# XÁC THỰC ADMIN (BTC)
# =========================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        if user == ADMIN_USERNAME and pwd == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        error = "Tài khoản hoặc mật khẩu quản trị không chính xác!"
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("home"))

# =========================
# BẢNG ĐIỀU KHIỂN QUẢN LÝ (ADMIN)
# =========================
@app.route("/admin")
def admin_panel():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    connection = get_db()
    matches = connection.execute("SELECT * FROM matches ORDER BY id DESC").fetchall()
    athletes = connection.execute("SELECT * FROM athletes ORDER BY id DESC").fetchall()
    connection.close()

    settings = get_settings()
    reg_link = url_for("register", _external=True)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={reg_link}"

    return render_template("admin.html", 
                           matches=matches, 
                           athletes=athletes, 
                           reg_link=reg_link, 
                           qr_url=qr_url,
                           settings=settings)

# Cập nhật thông tin giải đấu
@app.route("/admin/settings/update-tournament", methods=["POST"])
def update_tournament_info():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    name = request.form.get("tournament_name", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    location = request.form.get("tournament_location", "").strip()

    connection = get_db()
    connection.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('tournament_name', ?)", (name,))
    connection.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('start_date', ?)", (start_date,))
    connection.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('end_date', ?)", (end_date,))
    connection.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('tournament_location', ?)", (location,))
    connection.commit()
    connection.close()

    flash("Cập nhật thông tin giải đấu thành công!")
    return redirect(url_for("admin_panel"))

# Cập nhật lệ phí thi đấu
@app.route("/admin/settings/update-fee", methods=["POST"])
def update_reg_fee():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    
    fee_single = request.form.get("fee_single", "100000")
    fee_double = request.form.get("fee_double", "200000")

    connection = get_db()
    connection.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('fee_single', ?)", (fee_single,))
    connection.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('fee_double', ?)", (fee_double,))
    connection.commit()
    connection.close()

    flash("Cập nhật lệ phí thi đấu thành công!")
    return redirect(url_for("admin_panel"))

# Tạo trận đấu mới
@app.route("/admin/match/create", methods=["POST"])
def create_match():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    court = request.form.get("court")
    player1 = request.form.get("player1")
    player2 = request.form.get("player2")
    match_time = request.form.get("match_time", "")
    settings = get_settings()
    fixed_location = settings["tournament_location"]

    if court and player1 and player2:
        connection = get_db()
        connection.execute("""
            INSERT INTO matches (court, player1, player2, score1, score2, status, match_time, location)
            VALUES (?, ?, ?, 0, 0, 'waiting', ?, ?)
        """, (court, player1, player2, match_time, fixed_location))
        connection.commit()
        connection.close()
        flash("Thêm trận đấu mới thành công!")
    return redirect(url_for("admin_panel"))

# Lưu tỉ số chung cuộc
@app.route("/admin/match/update-score", methods=["POST"])
def update_final_score():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    match_id = request.form.get("match_id")
    score1 = request.form.get("score1", 0, type=int)
    score2 = request.form.get("score2", 0, type=int)
    status = request.form.get("status")

    connection = get_db()
    connection.execute("""
        UPDATE matches 
        SET score1 = ?, score2 = ?, status = ?
        WHERE id = ?
    """, (score1, score2, status, match_id))
    connection.commit()
    connection.close()

    flash("Cập nhật tỉ số trận đấu thành công!")
    return redirect(url_for("admin_panel"))

# Sửa Sân & Lịch
@app.route("/admin/match/update-info", methods=["POST"])
def update_match_info():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    match_id = request.form.get("match_id")
    court = request.form.get("court")
    match_time = request.form.get("match_time")
    location = request.form.get("location")

    connection = get_db()
    connection.execute("""
        UPDATE matches 
        SET court = ?, match_time = ?, location = ?
        WHERE id = ?
    """, (court, match_time, location, match_id))
    connection.commit()
    connection.close()

    flash("Chỉnh sửa thông tin trận đấu thành công!")
    return redirect(url_for("admin_panel"))

# Xóa trận
@app.route("/admin/match/delete/<int:match_id>")
def delete_match(match_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    connection = get_db()
    connection.execute("DELETE FROM matches WHERE id = ?", (match_id,))
    connection.commit()
    connection.close()

    flash("Đã xóa trận đấu khỏi danh sách!")
    return redirect(url_for("admin_panel"))

# Cập nhật thông tin / Duyệt VĐV
@app.route("/admin/athlete/update", methods=["POST"])
def update_athlete():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    athlete_id = request.form.get("athlete_id")
    category = request.form.get("category")
    status = request.form.get("status")

    connection = get_db()
    connection.execute("UPDATE athletes SET category = ?, status = ? WHERE id = ?", (category, status, athlete_id))
    connection.commit()
    connection.close()

    flash("Cập nhật trạng thái vận động viên thành công!")
    return redirect(url_for("admin_panel"))

# Xóa VĐV
@app.route("/admin/athlete/delete/<int:athlete_id>")
def delete_athlete(athlete_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    connection = get_db()
    connection.execute("DELETE FROM athletes WHERE id = ?", (athlete_id,))
    connection.commit()
    connection.close()

    flash("Đã xóa vận động viên khỏi danh sách!")
    return redirect(url_for("admin_panel"))

init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)