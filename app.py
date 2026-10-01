import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import os

# =========================================================
# CẤU HÌNH
# =========================================================

st.set_page_config(
    page_title="Nhà Hàng Cỏ Bốn Lá",
    page_icon="🍀",
    layout="wide"
)

DB_FILE = "co_bon_la.db"


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():

    conn = get_connection()
    cursor = conn.cursor()

    # Bảng hóa đơn
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_code TEXT UNIQUE,
            table_number TEXT,
            customer_name TEXT,
            employee TEXT,
            created_at TEXT,
            subtotal REAL,
            discount REAL,
            service_charge REAL,
            vat REAL,
            total REAL,
            payment_method TEXT,
            money_received REAL,
            change_amount REAL
        )
    """)

    # Bảng chi tiết hóa đơn
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            item_name TEXT,
            quantity INTEGER,
            price REAL,
            amount REAL,
            FOREIGN KEY(invoice_id)
                REFERENCES invoices(id)
        )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# HÀM FORMAT TIỀN
# =========================================================

def money(value):
    return f"{value:,.0f} VNĐ"


# =========================================================
# TẠO MÃ HÓA ĐƠN
# =========================================================

def generate_invoice_code():

    now = datetime.now()

    base = now.strftime("%Y%m%d%H%M%S")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM invoices WHERE invoice_code LIKE ?",
        (f"HD{base}%",)
    )

    count = cursor.fetchone()[0]

    conn.close()

    return f"HD{base}{count + 1:02d}"


# =========================================================
# LƯU HÓA ĐƠN
# =========================================================

def save_invoice(
    invoice_code,
    table_number,
    customer_name,
    employee,
    created_at,
    subtotal,
    discount,
    service_charge,
    vat,
    total,
    payment_method,
    money_received,
    change_amount,
    items
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # -----------------------------
        # Lưu hóa đơn
        # -----------------------------

        cursor.execute("""
            INSERT INTO invoices (
                invoice_code,
                table_number,
                customer_name,
                employee,
                created_at,
                subtotal,
                discount,
                service_charge,
                vat,
                total,
                payment_method,
                money_received,
                change_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_code,
            table_number,
            customer_name,
            employee,
            created_at,
            subtotal,
            discount,
            service_charge,
            vat,
            total,
            payment_method,
            money_received,
            change_amount
        ))

        invoice_id = cursor.lastrowid

        # -----------------------------
        # Lưu từng món
        # -----------------------------

        for item in items:

            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_id,
                    item_name,
                    quantity,
                    price,
                    amount
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                invoice_id,
                item["Tên món"],
                item["Số lượng"],
                item["Đơn giá"],
                item["Thành tiền"]
            ))

        conn.commit()

        return True, invoice_id

    except Exception as e:

        conn.rollback()

        return False, str(e)

    finally:

        conn.close()


# =========================================================
# LẤY DANH SÁCH HÓA ĐƠN
# =========================================================

def get_invoices(search=""):

    conn = get_connection()

    if search:

        query = """
            SELECT *
            FROM invoices
            WHERE invoice_code LIKE ?
               OR table_number LIKE ?
               OR customer_name LIKE ?
               OR employee LIKE ?
            ORDER BY id DESC
        """

        keyword = f"%{search}%"

        df = pd.read_sql_query(
            query,
            conn,
            params=(
                keyword,
                keyword,
                keyword,
                keyword
            )
        )

    else:

        df = pd.read_sql_query("""
            SELECT *
            FROM invoices
            ORDER BY id DESC
        """, conn)

    conn.close()

    return df


# =========================================================
# LẤY CHI TIẾT HÓA ĐƠN
# =========================================================

def get_invoice_detail(invoice_id):

    conn = get_connection()

    invoice = pd.read_sql_query(
        """
        SELECT *
        FROM invoices
        WHERE id = ?
        """,
        conn,
        params=(invoice_id,)
    )

    items = pd.read_sql_query(
        """
        SELECT
            item_name AS 'Tên món',
            quantity AS 'Số lượng',
            price AS 'Đơn giá',
            amount AS 'Thành tiền'
        FROM invoice_items
        WHERE invoice_id = ?
        """,
        conn,
        params=(invoice_id,)
    )

    conn.close()

    return invoice, items


# =========================================================
# XÓA HÓA ĐƠN
# =========================================================

def delete_invoice(invoice_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "DELETE FROM invoice_items WHERE invoice_id = ?",
            (invoice_id,)
        )

        cursor.execute(
            "DELETE FROM invoices WHERE id = ?",
            (invoice_id,)
        )

        conn.commit()

        return True

    except:

        conn.rollback()

        return False

    finally:

        conn.close()


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.main-title {
    text-align: center;
    font-size: 34px;
    font-weight: 800;
}

.sub-title {
    text-align: center;
    font-size: 18px;
    color: #666;
}

.total-box {
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #ddd;
    background: #f8f8f8;
}

.big-total {
    font-size: 28px;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION STATE
# =========================================================

if "items" not in st.session_state:
    st.session_state.items = []

if "invoice_saved" not in st.session_state:
    st.session_state.invoice_saved = False


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("## 🍀 CỎ BỐN LÁ")

    page = st.radio(
        "Chức năng",
        [
            "🧾 Tạo hóa đơn",
            "📋 Lịch sử hóa đơn",
            "📊 Doanh thu"
        ]
    )

    st.divider()

    employee = st.selectbox(
        "👨‍🍳 Nhân viên",
        [
            "Nhân viên 01",
            "Nhân viên 02",
            "Nhân viên 03",
            "Thu ngân",
            "Quản lý"
        ]
    )


# =========================================================
# TRANG TẠO HÓA ĐƠN
# =========================================================

if page == "🧾 Tạo hóa đơn":

    st.markdown(
        '<div class="main-title">🍀 NHÀ HÀNG CỎ BỐN LÁ</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sub-title">Hệ thống quản lý bán hàng</div>',
        unsafe_allow_html=True
    )

    st.divider()

    # -----------------------------------------
    # THÔNG TIN BILL
    # -----------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        table_number = st.text_input(
            "🪑 Số bàn",
            "01"
        )

    with col2:

        customer_name = st.text_input(
            "👤 Khách hàng",
            "Khách lẻ"
        )

    with col3:

        invoice_code = st.text_input(
            "🧾 Mã hóa đơn",
            generate_invoice_code()
        )

    with col4:

        created_at = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        st.text_input(
            "🕐 Thời gian",
            created_at,
            disabled=True
        )

    st.divider()

    # -----------------------------------------
    # THÊM MÓN
    # -----------------------------------------

    st.subheader("🍜 Thêm món")

    col1, col2, col3, col4 = st.columns(
        [4, 1, 2, 1]
    )

    with col1:

        item_name = st.text_input(
            "Tên món",
            placeholder="Ví dụ: Cơm chiên hải sản"
        )

    with col2:

        quantity = st.number_input(
            "Số lượng",
            min_value=1,
            value=1,
            step=1
        )

    with col3:

        price = st.number_input(
            "Đơn giá",
            min_value=0,
            value=0,
            step=1000
        )

    with col4:

        st.write("")

        if st.button(
            "➕ Thêm món",
            use_container_width=True
        ):

            if item_name.strip() == "":
                st.warning(
                    "Vui lòng nhập tên món."
                )

            elif price <= 0:
                st.warning(
                    "Vui lòng nhập đơn giá."
                )

            else:

                amount = quantity * price

                st.session_state.items.append({
                    "Tên món": item_name,
                    "Số lượng": quantity,
                    "Đơn giá": price,
                    "Thành tiền": amount
                })

                st.success(
                    f"Đã thêm {item_name}"
                )

    # -----------------------------------------
    # DANH SÁCH MÓN
    # -----------------------------------------

    if st.session_state.items:

        st.subheader("🛒 Danh sách món")

        df_items = pd.DataFrame(
            st.session_state.items
        )

        st.dataframe(
            df_items,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Đơn giá": st.column_config.NumberColumn(
                    format="%,d VNĐ"
                ),
                "Thành tiền": st.column_config.NumberColumn(
                    format="%,d VNĐ"
                )
            }
        )

        if st.button("🗑️ Xóa toàn bộ món"):

            st.session_state.items = []

            st.rerun()

    else:

        st.info(
            "Chưa có món nào trong hóa đơn."
        )

    st.divider()

    # -----------------------------------------
    # TÍNH TIỀN
    # -----------------------------------------

    subtotal = sum(
        item["Thành tiền"]
        for item in st.session_state.items
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        discount_percent = st.number_input(
            "🎁 Giảm giá (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0
        )

    with col2:

        service_percent = st.number_input(
            "🍽️ Phí phục vụ (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0
        )

    with col3:

        vat_percent = st.number_input(
            "🧾 VAT (%)",
            min_value=0.0,
            max_value=100.0,
            value=8.0,
            step=1.0
        )

    discount = subtotal * discount_percent / 100

    after_discount = subtotal - discount

    service_charge = (
        after_discount *
        service_percent /
        100
    )

    vat = (
        after_discount *
        vat_percent /
        100
    )

    total = (
        after_discount
        + service_charge
        + vat
    )

    # -----------------------------------------
    # THANH TOÁN
    # -----------------------------------------

    st.subheader("💳 Thanh toán")

    col1, col2, col3 = st.columns(3)

    with col1:

        payment_method = st.selectbox(
            "Phương thức",
            [
                "Tiền mặt",
                "Chuyển khoản",
                "Thẻ ngân hàng"
            ]
        )

    with col2:

        money_received = st.number_input(
            "💵 Tiền khách đưa",
            min_value=0,
            value=0,
            step=10000
        )

    with col3:

        change_amount = (
            money_received - total
        )

        if change_amount >= 0:

            st.metric(
                "💰 Tiền thừa",
                money(change_amount)
            )

        else:

            st.metric(
                "⚠️ Còn thiếu",
                money(abs(change_amount))
            )

    # -----------------------------------------
    # TỔNG BILL
    # -----------------------------------------

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            f"**Tạm tính:** {money(subtotal)}"
        )

        st.write(
            f"**Giảm giá:** -{money(discount)}"
        )

        st.write(
            f"**Phí phục vụ:** {money(service_charge)}"
        )

        st.write(
            f"**VAT:** {money(vat)}"
        )

    with col2:

        st.markdown(
            f"""
            <div class="total-box">

            <div>TỔNG THANH TOÁN</div>

            <div class="big-total">
            {money(total)}
            </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # -----------------------------------------
    # LƯU HÓA ĐƠN
    # -----------------------------------------

    if st.button(
        "💾 LƯU & HOÀN TẤT HÓA ĐƠN",
        type="primary",
        use_container_width=True
    ):

        if not st.session_state.items:

            st.error(
                "Không thể lưu hóa đơn vì chưa có món."
            )

        elif money_received < total:

            st.error(
                "Số tiền khách đưa chưa đủ."
            )

        else:

            success, result = save_invoice(
                invoice_code,
                table_number,
                customer_name,
                employee,
                created_at,
                subtotal,
                discount,
                service_charge,
                vat,
                total,
                payment_method,
                money_received,
                change_amount,
                st.session_state.items
            )

            if success:

                st.success(
                    f"✅ Đã lưu hóa đơn {invoice_code}"
                )

                st.info(
                    "Hóa đơn đã được lưu vào hệ thống."
                )

                # Xóa bill hiện tại
                st.session_state.items = []

                st.session_state.invoice_saved = True

                st.balloons()

            else:

                st.error(
                    f"Lỗi khi lưu hóa đơn: {result}"
                )


# =========================================================
# LỊCH SỬ HÓA ĐƠN
# =========================================================

elif page == "📋 Lịch sử hóa đơn":

    st.title("📋 Lịch sử hóa đơn")

    search = st.text_input(
        "🔎 Tìm hóa đơn",
        placeholder="Mã hóa đơn / bàn / khách hàng / nhân viên"
    )

    df = get_invoices(search)

    if df.empty:

        st.info(
            "Chưa có hóa đơn nào."
        )

    else:

        st.metric(
            "Tổng số hóa đơn",
            len(df)
        )

        display_df = df[
            [
                "invoice_code",
                "table_number",
                "customer_name",
                "employee",
                "created_at",
                "total",
                "payment_method"
            ]
        ].copy()

        display_df.columns = [
            "Mã hóa đơn",
            "Bàn",
            "Khách hàng",
            "Nhân viên",
            "Thời gian",
            "Tổng tiền",
            "Thanh toán"
        ]

        display_df["Tổng tiền"] = display_df[
            "Tổng tiền"
        ].apply(money)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # -----------------------------------------
        # XEM CHI TIẾT
        # -----------------------------------------

        invoice_options = df[
            ["id", "invoice_code"]
        ].values.tolist()

        selected_invoice = st.selectbox(
            "Chọn hóa đơn để xem chi tiết",
            invoice_options,
            format_func=lambda x: x[1]
        )

        if selected_invoice:

            invoice_id = selected_invoice[0]

            invoice, items = get_invoice_detail(
                invoice_id
            )

            if not invoice.empty:

                row = invoice.iloc[0]

                st.subheader(
                    f"🧾 Hóa đơn {row['invoice_code']}"
                )

                col1, col2, col3, col4 = st.columns(4)

                col1.metric(
                    "Bàn",
                    row["table_number"]
                )

                col2.metric(
                    "Nhân viên",
                    row["employee"]
                )

                col3.metric(
                    "Thanh toán",
                    row["payment_method"]
                )

                col4.metric(
                    "Tổng tiền",
                    money(row["total"])
                )

                st.dataframe(
                    items,
                    use_container_width=True,
                    hide_index=True
                )

                st.write(
                    f"**Tạm tính:** {money(row['subtotal'])}"
                )

                st.write(
                    f"**Giảm giá:** -{money(row['discount'])}"
                )

                st.write(
                    f"**Phí phục vụ:** {money(row['service_charge'])}"
                )

                st.write(
                    f"**VAT:** {money(row['vat'])}"
                )

                st.markdown(
                    f"### Tổng: {money(row['total'])}"
                )

                st.write(
                    f"Khách đưa: {money(row['money_received'])}"
                )

                st.write(
                    f"Tiền thừa: {money(row['change_amount'])}"
                )

                # -----------------------------------------
                # XÓA HÓA ĐƠN
                # -----------------------------------------

                if st.button(
                    "🗑️ Xóa hóa đơn này",
                    type="secondary"
                ):

                    if delete_invoice(
                        invoice_id
                    ):

                        st.success(
                            "Đã xóa hóa đơn."
                        )

                        st.rerun()


# =========================================================
# DOANH THU
# =========================================================

elif page == "📊 Doanh thu":

    st.title("📊 Báo cáo doanh thu")

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM invoices
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()

    if df.empty:

        st.info(
            "Chưa có dữ liệu doanh thu."
        )

    else:

        # -----------------------------------------
        # TỔNG QUAN
        # -----------------------------------------

        total_revenue = df["total"].sum()

        total_invoices = len(df)

        average_bill = (
            total_revenue /
            total_invoices
            if total_invoices > 0
            else 0
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "💰 Tổng doanh thu",
            money(total_revenue)
        )

        col2.metric(
            "🧾 Số hóa đơn",
            total_invoices
        )

        col3.metric(
            "📈 Bill trung bình",
            money(average_bill)
        )

        st.divider()

        # -----------------------------------------
        # DOANH THU THEO NGÀY
        # -----------------------------------------

        df["date"] = pd.to_datetime(
            df["created_at"],
            dayfirst=True
        ).dt.date

        daily = (
            df.groupby("date")["total"]
            .sum()
            .reset_index()
        )

        daily.columns = [
            "Ngày",
            "Doanh thu"
        ]

        st.subheader(
            "📅 Doanh thu theo ngày"
        )

        st.dataframe(
            daily,
            use_container_width=True,
            hide_index=True
        )

        # -----------------------------------------
        # PHƯƠNG THỨC THANH TOÁN
        # -----------------------------------------

        st.subheader(
            "💳 Theo phương thức thanh toán"
        )

        payment = (
            df.groupby(
                "payment_method"
            )["total"]
            .sum()
            .reset_index()
        )

        payment.columns = [
            "Phương thức",
            "Doanh thu"
        ]

        st.dataframe(
            payment,
            use_container_width=True,
            hide_index=True
        )

        # -----------------------------------------
        # DOANH THU NHÂN VIÊN
        # -----------------------------------------

        st.subheader(
            "👨‍🍳 Doanh thu theo nhân viên"
        )

        employee_revenue = (
            df.groupby(
                "employee"
            )["total"]
            .sum()
            .reset_index()
        )

        employee_revenue.columns = [
            "Nhân viên",
            "Doanh thu"
        ]

        st.dataframe(
            employee_revenue,
            use_container_width=True,
            hide_index=True
        )
