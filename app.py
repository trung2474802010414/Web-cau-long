```python
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import random
import time
import smtplib
import re
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = "badminton_secret_key_2026"

DATABASE = "badminton.db"

# =========================================================
# TÀI KHOẢN ADMIN
# =========================================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"

# =========================================================
# CẤU HÌNH EMAIL OTP
# =========================================================
# THAY 2 DÒNG NÀY BẰNG GMAIL CỦA BẠN
#
# Ví dụ:
# SMTP_EMAIL = "abc@gmail.com"
# SMTP_PASSWORD = "xxxx xxxx xxxx xxxx"
#
# SMTP_PASSWORD phải là App Password của Gmail,
# KHÔNG phải mật khẩu Gmail thông thường.
# =========================================================

SMTP_EMAIL = "YOUR_GMAIL@gmail.com"
SMTP_PASSWORD = "YOUR_GMAIL_APP_PASSWORD"

OTP_EXPIRE_SECONDS = 300


# =========================================================
# DATABASE
# =========================================================

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = get_db()

    # =====================================================
    # 1. BẢNG TRẬN ĐẤU
    # =====================================================

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

    # =====================================================
    # 2. BẢNG VẬN ĐỘNG VIÊN
    # =====================================================

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

    # =====================================================
    # 3. BẢNG USERS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT UNIQUE,
            password TEXT,
            verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # TỰ KIỂM TRA DATABASE CŨ
    # Nếu bảng users cũ chưa có cột mới thì tự thêm.
    # =====================================================

    columns = connection.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "phone" not in column_names:
        connection.execute(
            "ALTER TABLE users ADD COLUMN phone TEXT"
        )

    if "verified" not in column_names:
        connection.execute(
            "ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0"
        )

    if "created_at" not in column_names:
        connection.execute(
            "ALTER TABLE users ADD COLUMN created_at TIMESTAMP"
        )

    # =====================================================
    # 4. BẢNG SETTINGS
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    connection.execute("""
        INSERT OR IGNORE INTO settings
        (key, value)
        VALUES
        ('tournament_name',
        'GIẢI CẦU LÔNG VÔ ĐỊCH TOÀN QUỐC 2026')
    """)

    connection.execute("""
        INSERT OR IGNORE INTO settings
        (key, value)
        VALUES
        ('start_date', '2026-09-15')
    """)

    connection.execute("""
        INSERT OR IGNORE INTO settings
        (key, value)
        VALUES
        ('end_date', '2026-09-20')
    """)

    connection.execute("""
        INSERT OR IGNORE INTO settings
        (key, value)
        VALUES
        ('tournament_location',
        'Nhà thi đấu ĐH Văn Lang - TP. Hồ Chí Minh')
    """)

    connection.execute("""
        INSERT OR IGNORE INTO settings
        (key, value)
        VALUES
        ('fee_single', '100000')
    """)

    connection.execute("""
        INSERT OR IGNORE INTO settings
        (key, value)
        VALUES
        ('fee_double', '200000')
    """)

    connection.commit()
    connection.close()


# =========================================================
# SETTINGS
# =========================================================

def get_settings():

    connection = get_db()

    rows = connection.execute(
        "SELECT key, value FROM settings"
    ).fetchall()

    connection.close()

    data = {
        row["key"]: row["value"]
        for row in rows
    }

    return {
        "tournament_name":
            data.get(
                "tournament_name",
                "GIẢI CẦU LÔNG MỞ RỘNG 2026"
            ),

        "start_date":
            data.get(
                "start_date",
                "2026-09-15"
            ),

        "end_date":
            data.get(
                "end_date",
                "2026-09-20"
            ),

        "tournament_location":
            data.get(
                "tournament_location",
                "Nhà thi đấu ĐH Văn Lang"
            ),

        "fee_single":
            int(
                data.get(
                    "fee_single",
                    100000
                )
            ),

        "fee_double":
            int(
                data.get(
                    "fee_double",
                    200000
                )
            )
    }


# =========================================================
# KIỂM TRA EMAIL
# =========================================================

def is_email(value):

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return re.match(pattern, value) is not None


# =========================================================
# KIỂM TRA SỐ ĐIỆN THOẠI
# =========================================================

def is_phone(value):

    value = value.replace(" ", "")

    pattern = r"^(0|\+84)[0-9]{9,10}$"

    return re.match(pattern, value) is not None


# =========================================================
# TẠO OTP
# =========================================================

def generate_otp():

    return str(
        random.randint(
            100000,
            999999
        )
    )


# =========================================================
# GỬI OTP QUA EMAIL
# =========================================================

def send_email_otp(email, otp):

    try:

        if (
            SMTP_EMAIL == "YOUR_GMAIL@gmail.com"
            or SMTP_PASSWORD == "YOUR_GMAIL_APP_PASSWORD"
        ):
            print("--------------------------------")
            print("CHƯA CẤU HÌNH GMAIL OTP")
            print("Email:", email)
            print("OTP:", otp)
            print("--------------------------------")

            return False

        message = EmailMessage()

        message["Subject"] = "Mã OTP - BWF LiveScore"
        message["From"] = SMTP_EMAIL
        message["To"] = email

        message.set_content(
            f"""
Xin chào,

Bạn đang đăng ký tài khoản BWF LiveScore.

Mã OTP của bạn là:

{otp}

Mã OTP có hiệu lực trong 5 phút.

Nếu bạn không thực hiện yêu cầu này,
vui lòng bỏ qua email.

-----------------------------
BWF LiveScore
Official Tournament Live
-----------------------------
"""
        )

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as server:

            server.login(
                SMTP_EMAIL,
                SMTP_PASSWORD
            )

            server.send_message(message)

        return True

    except Exception as error:

        print(
            "LỖI GỬI EMAIL OTP:",
            error
        )

        return False


# =========================================================
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    connection = get_db()

    matches = connection.execute(
        """
        SELECT *
        FROM matches
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    settings = get_settings()

    return render_template(
        "index.html",
        matches=matches,
        settings=settings
    )


# =========================================================
# ĐĂNG KÝ VẬN ĐỘNG VIÊN
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    connection = get_db()

    message = None

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        categories = request.form.getlist(
            "category"
        )

        category_str = ", ".join(
            categories
        )

        if (
            full_name
            and phone
            and category_str
        ):

            connection.execute(
                """
                INSERT INTO athletes
                (
                    full_name,
                    phone,
                    category,
                    status
                )
                VALUES (?, ?, ?, 'Chờ duyệt')
                """,
                (
                    full_name,
                    phone,
                    category_str
                )
            )

            connection.commit()

            message = (
                "Đăng ký thành công! "
                "BTC sẽ kiểm tra thanh toán "
                "và duyệt danh sách."
            )

    settings = get_settings()

    connection.close()

    return render_template(
        "register.html",
        message=message,
        fee_single=settings["fee_single"],
        fee_double=settings["fee_double"],
        tournament_name=settings["tournament_name"]
    )


# =========================================================
# LOGIN / REGISTER CHUNG
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def guest_login():

    error = None
    success = None

    if request.method == "POST":

        action = request.form.get(
            "action"
        )

        # =================================================
        # ĐĂNG NHẬP
        # =================================================

        if action == "login":

            login_value = request.form.get(
                "login_value",
                ""
            ).strip()

            password = request.form.get(
                "password",
                ""
            )

            # ---------------------------------------------
            # ADMIN
            # ---------------------------------------------

            if (
                login_value == ADMIN_USERNAME
                and password == ADMIN_PASSWORD
            ):

                session.clear()

                session["is_admin"] = True

                return redirect(
                    url_for("admin_panel")
                )

            # ---------------------------------------------
            # USER
            # ---------------------------------------------

            connection = get_db()

            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE
                    (
                        email = ?
                        OR phone = ?
                    )
                    AND password = ?
                    AND verified = 1
                """,
                (
                    login_value,
                    login_value,
                    password
                )
            ).fetchone()

            connection.close()

            if user:

                session.clear()

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]

                if user["email"]:
                    session["user_email"] = user["email"]

                if user["phone"]:
                    session["user_phone"] = user["phone"]

                return redirect(
                    url_for("home")
                )

            error = (
                "Tài khoản hoặc mật khẩu "
                "không chính xác!"
            )

        # =================================================
        # ĐĂNG KÝ → GỬI OTP
        # =================================================

        elif action == "send_otp":

            name = request.form.get(
                "name",
                ""
            ).strip()

            contact = request.form.get(
                "contact",
                ""
            ).strip()

            password = request.form.get(
                "password",
                ""
            )

            # ---------------------------------------------
            # KIỂM TRA DỮ LIỆU
            # ---------------------------------------------

            if not name or not contact or not password:

                error = (
                    "Vui lòng nhập đầy đủ thông tin."
                )

            elif len(password) < 6:

                error = (
                    "Mật khẩu phải có ít nhất 6 ký tự."
                )

            elif (
                not is_email(contact)
                and not is_phone(contact)
            ):

                error = (
                    "Vui lòng nhập Gmail "
                    "hoặc số điện thoại hợp lệ."
                )

            else:

                connection = get_db()

                existing = connection.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE email = ?
                    OR phone = ?
                    """,
                    (
                        contact,
                        contact
                    )
                ).fetchone()

                connection.close()

                if existing:

                    error = (
                        "Gmail hoặc số điện thoại "
                        "này đã được sử dụng."
                    )

                else:

                    otp = generate_otp()

                    # -------------------------------------
                    # LƯU THÔNG TIN TẠM THỜI
                    # -------------------------------------

                    session["register_name"] = name
                    session["register_contact"] = contact
                    session["register_password"] = password
                    session["register_otp"] = otp
                    session["register_otp_time"] = time.time()

                    # -------------------------------------
                    # EMAIL
                    # -------------------------------------

                    if is_email(contact):

                        session["register_type"] = "email"

                        sent = send_email_otp(
                            contact,
                            otp
                        )

                        if sent:

                            return redirect(
                                url_for(
                                    "verify_otp"
                                )
                            )

                        else:

                            error = (
                                "Không thể gửi OTP Gmail. "
                                "Hãy kiểm tra cấu hình "
                                "Gmail trong app.py."
                            )

                    # -------------------------------------
                    # PHONE
                    # -------------------------------------

                    elif is_phone(contact):

                        session["register_type"] = "phone"

                        # Hiện tại chưa có SMS provider.
                        # In OTP ra terminal để test.

                        print(
                            "================================"
                        )

                        print(
                            "OTP ĐĂNG KÝ SỐ ĐIỆN THOẠI"
                        )

                        print(
                            "Số điện thoại:",
                            contact
                        )

                        print(
                            "MÃ OTP:",
                            otp
                        )

                        print(
                            "================================"
                        )

                        return redirect(
                            url_for(
                                "verify_otp"
                            )
                        )

    return render_template(
        "login.html",
        error=error,
        success=success
    )


# =========================================================
# XÁC THỰC OTP
# =========================================================

@app.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    error = None

    if "register_otp" not in session:

        return redirect(
            url_for("guest_login")
        )

    if request.method == "POST":

        input_otp = request.form.get(
            "otp",
            ""
        ).strip()

        saved_otp = session.get(
            "register_otp"
        )

        otp_time = session.get(
            "register_otp_time",
            0
        )

        # =================================================
        # KIỂM TRA THỜI GIAN
        # =================================================

        if (
            time.time() - otp_time
            > OTP_EXPIRE_SECONDS
        ):

            session.pop(
                "register_otp",
                None
            )

            session.pop(
                "register_otp_time",
                None
            )

            error = (
                "Mã OTP đã hết hạn. "
                "Vui lòng đăng ký lại."
            )

        # =================================================
        # KIỂM TRA OTP
        # =================================================

        elif input_otp != saved_otp:

            error = (
                "Mã OTP không chính xác!"
            )

        # =================================================
        # OTP ĐÚNG
        # =================================================

        else:

            name = session.get(
                "register_name"
            )

            contact = session.get(
                "register_contact"
            )

            password = session.get(
                "register_password"
            )

            register_type = session.get(
                "register_type"
            )

            connection = get_db()

            try:

                if register_type == "email":

                    connection.execute(
                        """
                        INSERT INTO users
                        (
                            name,
                            email,
                            phone,
                            password,
                            verified
                        )
                        VALUES (?, ?, NULL, ?, 1)
                        """,
                        (
                            name,
                            contact,
                            password
                        )
                    )

                else:

                    connection.execute(
                        """
                        INSERT INTO users
                        (
                            name,
                            email,
                            phone,
                            password,
                            verified
                        )
                        VALUES (?, NULL, ?, ?, 1)
                        """,
                        (
                            name,
                            contact,
                            password
                        )
                    )

                connection.commit()

            except sqlite3.IntegrityError:

                connection.close()

                return render_template(
                    "verify_otp.html",
                    error=(
                        "Email hoặc số điện thoại "
                        "đã tồn tại."
                    )
                )

            connection.close()

            # =================================================
            # LẤY USER VỪA TẠO
            # =================================================

            connection = get_db()

            if register_type == "email":

                user = connection.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE email = ?
                    """,
                    (contact,)
                ).fetchone()

            else:

                user = connection.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE phone = ?
                    """,
                    (contact,)
                ).fetchone()

            connection.close()

            # =================================================
            # XÓA SESSION OTP
            # =================================================

            session.clear()

            # =================================================
            # ĐĂNG NHẬP USER
            # =================================================

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            if user["email"]:
                session["user_email"] = user["email"]

            if user["phone"]:
                session["user_phone"] = user["phone"]

            return redirect(
                url_for("home")
            )

    return render_template(
        "verify_otp.html",
        error=error
    )


# =========================================================
# LOGOUT USER
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# FACEBOOK
# =========================================================
# Đây là route chờ tích hợp Facebook OAuth thật.
# Không giả lập user nữa.
# =========================================================

@app.route("/auth/facebook")
def facebook_login():

    flash(
        "Facebook Login cần cấu hình "
        "Facebook App ID và App Secret."
    )

    return redirect(
        url_for("guest_login")
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@app.route("/admin")
def admin_panel():

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    connection = get_db()

    matches = connection.execute(
        """
        SELECT *
        FROM matches
        ORDER BY id DESC
        """
    ).fetchall()

    athletes = connection.execute(
        """
        SELECT *
        FROM athletes
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    settings = get_settings()

    reg_link = url_for(
        "register",
        _external=True
    )

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=180x180&data={reg_link}"
    )

    return render_template(
        "admin.html",
        matches=matches,
        athletes=athletes,
        reg_link=reg_link,
        qr_url=qr_url,
        settings=settings
    )


# =========================================================
# CẬP NHẬT THÔNG TIN GIẢI
# =========================================================

@app.route(
    "/admin/settings/update-tournament",
    methods=["POST"]
)
def update_tournament_info():

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    name = request.form.get(
        "tournament_name",
        ""
    ).strip()

    start_date = request.form.get(
        "start_date",
        ""
    ).strip()

    end_date = request.form.get(
        "end_date",
        ""
    ).strip()

    location = request.form.get(
        "tournament_location",
        ""
    ).strip()

    connection = get_db()

    connection.execute(
        """
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES ('tournament_name', ?)
        """,
        (name,)
    )

    connection.execute(
        """
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES ('start_date', ?)
        """,
        (start_date,)
    )

    connection.execute(
        """
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES ('end_date', ?)
        """,
        (end_date,)
    )

    connection.execute(
        """
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES ('tournament_location', ?)
        """,
        (location,)
    )

    connection.commit()
    connection.close()

    flash(
        "Cập nhật thông tin giải đấu thành công!"
    )

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# CẬP NHẬT LỆ PHÍ
# =========================================================

@app.route(
    "/admin/settings/update-fee",
    methods=["POST"]
)
def update_reg_fee():

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    fee_single = request.form.get(
        "fee_single",
        "100000"
    )

    fee_double = request.form.get(
        "fee_double",
        "200000"
    )

    connection = get_db()

    connection.execute(
        """
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES ('fee_single', ?)
        """,
        (fee_single,)
    )

    connection.execute(
        """
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES ('fee_double', ?)
        """,
        (fee_double,)
    )

    connection.commit()
    connection.close()

    flash(
        "Cập nhật lệ phí thi đấu thành công!"
    )

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# TẠO TRẬN ĐẤU
# =========================================================

@app.route(
    "/admin/match/create",
    methods=["POST"]
)
def create_match():

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    court = request.form.get(
        "court"
    )

    player1 = request.form.get(
        "player1"
    )

    player2 = request.form.get(
        "player2"
    )

    match_time = request.form.get(
        "match_time",
        ""
    )

    settings = get_settings()

    fixed_location = settings[
        "tournament_location"
    ]

    if (
        court
        and player1
        and player2
    ):

        connection = get_db()

        connection.execute(
            """
            INSERT INTO matches
            (
                court,
                player1,
                player2,
                score1,
                score2,
                status,
                match_time,
                location
            )
            VALUES (?, ?, ?, 0, 0, 'waiting', ?, ?)
            """,
            (
                court,
                player1,
                player2,
                match_time,
                fixed_location
            )
        )

        connection.commit()
        connection.close()

        flash(
            "Thêm trận đấu mới thành công!"
        )

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# CẬP NHẬT TỈ SỐ
# =========================================================

@app.route(
    "/admin/match/update-score",
    methods=["POST"]
)
def update_final_score():

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    match_id = request.form.get(
        "match_id"
    )

    score1 = request.form.get(
        "score1",
        0,
        type=int
    )

    score2 = request.form.get(
        "score2",
        0,
        type=int
    )

    status = request.form.get(
        "status"
    )

    connection = get_db()

    connection.execute(
        """
        UPDATE matches

        SET
            score1 = ?,
            score2 = ?,
            status = ?

        WHERE id = ?
        """,
        (
            score1,
            score2,
            status,
            match_id
        )
    )

    connection.commit()
    connection.close()

    flash(
        "Cập nhật tỉ số trận đấu thành công!"
    )

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# SỬA SÂN / LỊCH
# =========================================================

@app.route(
    "/admin/match/update-info",
    methods=["POST"]
)
def update_match_info():

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    match_id = request.form.get(
        "match_id"
    )

    court = request.form.get(
        "court"
    )

    match_time = request.form.get(
        "match_time"
    )

    location = request.form.get(
        "location"
    )

    connection = get_db()

    connection.execute(
        """
        UPDATE matches

        SET
            court = ?,
            match_time = ?,
            location = ?

        WHERE id = ?
        """,
        (
            court,
            match_time,
            location,
            match_id
        )
    )

    connection.commit()
    connection.close()

    flash(
        "Chỉnh sửa thông tin trận đấu thành công!"
    )

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# XÓA TRẬN
# =========================================================

@app.route(
    "/admin/match/delete/<int:match_id>"
)
def delete_match(match_id):

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    connection = get_db()

    connection.execute(
        """
        DELETE FROM matches
        WHERE id = ?
        """,
        (match_id,)
    )

    connection.commit()
    connection.close()

    flash(
        "Đã xóa trận đấu khỏi danh sách!"
    )

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# CẬP NHẬT VĐV
# =========================================================

@app.route(
    "/admin/athlete/update",
    methods=["POST"]
)
def update_athlete():

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    athlete_id = request.form.get(
        "athlete_id"
    )

    category = request.form.get(
        "category"
    )

    status = request.form.get(
        "status"
    )

    connection = get_db()

    connection.execute(
        """
        UPDATE athletes

        SET
            category = ?,
            status = ?

        WHERE id = ?
        """,
        (
            category,
            status,
            athlete_id
        )
    )

    connection.commit()
    connection.close()

    flash(
        "Cập nhật trạng thái vận động viên thành công!"
    )

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# XÓA VĐV
# =========================================================

@app.route(
    "/admin/athlete/delete/<int:athlete_id>"
)
def delete_athlete(athlete_id):

    if not session.get("is_admin"):

        return redirect(
            url_for("guest_login")
        )

    connection = get_db()

    connection.execute(
        """
        DELETE FROM athletes
        WHERE id = ?
        """,
        (athlete_id,)
    )

    connection.commit()
    connection.close()

    flash(
        "Đã xóa vận động viên khỏi danh sách!"
    )

    return redirect(
        url_for("admin_panel")
    )


# =========================================================
# KHỞI TẠO DATABASE
# =========================================================

init_db()


# =========================================================
# CHẠY SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
```
