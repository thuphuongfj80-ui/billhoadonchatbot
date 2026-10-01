import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# ============================================================
# 1. CẤU HÌNH ỨNG DỤNG
# ============================================================

st.set_page_config(
    page_title="Nhà Hàng Cỏ Bốn Lá",
    page_icon="🍀",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "co_bon_la.db"


# ============================================================
# 2. DATABASE
# ============================================================

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
            invoice_code TEXT UNIQUE NOT NULL,
            table_number TEXT,
            customer_name TEXT,
            employee TEXT,
            created_at TEXT,
            subtotal REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            service_charge REAL DEFAULT 0,
            vat REAL DEFAULT 0,
            total REAL DEFAULT 0,
            payment_method TEXT,
            money_received REAL DEFAULT 0,
            change_amount REAL DEFAULT 0
        )
    """)

    # Bảng chi tiết hóa đơn
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (invoice_id)
                REFERENCES invoices(id)
                ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


init_database()


# ============================================================
# 3. HÀM HỖ TRỢ
# ============================================================

def format_money(value):
    return f"{value:,.0f} VNĐ"


def generate_invoice_code():
    now = datetime.now()
    prefix = "HD" + now.strftime("%Y%m%d%H%M%S")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM invoices
        WHERE invoice_code LIKE ?
        """,
        (prefix + "%",)
    )

    count = cursor.fetchone()[0]

    conn.close()

    return f"{prefix}{count + 1:02d}"


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

        # Lưu hóa đơn chính
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

        # Lưu từng món
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

    except Exception as error:

        conn.rollback()

        return False, str(error)

    finally:

        conn.close()


def get_all_invoices(search_text=""):

    conn = get_connection()

    if search_text.strip():

        keyword = f"%{search_text.strip()}%"

        query = """
            SELECT *
            FROM invoices
            WHERE invoice_code LIKE ?
               OR table_number LIKE ?
               OR customer_name LIKE ?
               OR employee LIKE ?
            ORDER BY id DESC
        """

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

        df = pd.read_sql_query(
            """
            SELECT *
            FROM invoices
            ORDER BY id DESC
            """,
            conn
        )

    conn.close()

    return df


def get_invoice(invoice_id):

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


# ============================================================
# 4. CSS
# ============================================================

st.markdown("""
<style>

.main-title {
    text-align: center;
    font-size: 34px;
    font-weight: 800;
    margin-top: 5px;
}

.sub-title {
    text-align: center;
    color: #666;
    font-size: 17px;
    margin-bottom: 15px;
}

.total-card {
    border: 1px solid #dddddd;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    background-color: #fafafa;
}

.total-number {
    font-size: 28px;
    font-weight: 800;
}

.invoice-header {
    text-align: center;
    font-size: 25px;
    font-weight: bold;
}

.success-box {
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #b7dfc0;
    background-color: #f0fff4;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# 5. SESSION STATE
# ============================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "invoice_code" not in st.session_state:
    st.session_state.invoice_code = generate_invoice_code()


# ============================================================
# 6. SIDEBAR
# ============================================================

with st.sidebar:

    # Logo
    if os.path.exists("Logo1.JPG"):
        st.image(
            "Logo1.JPG",
            use_container_width=True
        )

    st.markdown(
        "## 🍀 Nhà Hàng Cỏ Bốn Lá"
    )

    st.divider()

    menu_page = st.radio(
        "📌 Chức năng",
        [
            "🧾 Bán hàng",
            "📋 Lịch sử hóa đơn",
            "📊 Doanh thu"
        ]
    )

    st.divider()

    st.markdown("### 👨‍🍳 Nhân viên")

    employee = st.selectbox(
        "Nhân viên đang sử dụng",
        [
            "Nhân viên 01",
            "Nhân viên 02",
            "Nhân viên 03",
            "Thu ngân",
            "Quản lý"
        ]
    )


# ============================================================
# 7. TRANG BÁN HÀNG
# ============================================================

if menu_page == "🧾 Bán hàng":

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    col_logo, col_title = st.columns([1, 4])

    with col_logo:

        if os.path.exists("Logo1.JPG"):
            st.image(
                "Logo1.JPG",
                width=130
            )

    with col_title:

        st.markdown(
            '<div class="main-title">'
            'NHÀ HÀNG CỎ BỐN LÁ'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="sub-title">'
            'Hệ thống quản lý bán hàng & hóa đơn'
            '</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # --------------------------------------------------------
    # THÔNG TIN HÓA ĐƠN
    # --------------------------------------------------------

    st.subheader("🧾 Thông tin hóa đơn")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        table_number = st.text_input(
            "🪑 Số bàn",
            placeholder="Ví dụ: 01"
        )

    with col2:

        customer_name = st.text_input(
            "👤 Khách hàng",
            value="Khách lẻ"
        )

    with col3:

        st.text_input(
            "🧾 Mã hóa đơn",
            value=st.session_state.invoice_code,
            disabled=True
        )

    with col4:

        current_time = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        st.text_input(
            "🕐 Thời gian",
            value=current_time,
            disabled=True
        )

    st.divider()

    # --------------------------------------------------------
    # THÊM MÓN
    # --------------------------------------------------------

    st.subheader("🍜 Thêm món")

    col1, col2, col3, col4 = st.columns(
        [4, 1, 2, 1]
    )

    with col1:

        item_name = st.text_input(
            "Tên món",
            placeholder="Nhập tên món..."
        )

    with col2:

        quantity = st.number_input(
            "SL",
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

        add_button = st.button(
            "➕ Thêm món",
            use_container_width=True
        )

    if add_button:

        if not item_name.strip():

            st.warning(
                "⚠️ Vui lòng nhập tên món."
            )

        elif price <= 0:

            st.warning(
                "⚠️ Vui lòng nhập đơn giá."
            )

        else:

            amount = quantity * price

            st.session_state.cart.append({
                "Tên món": item_name.strip(),
                "Số lượng": quantity,
                "Đơn giá": price,
                "Thành tiền": amount
            })

            st.success(
                f"✅ Đã thêm: {item_name}"
            )

            st.rerun()

    # --------------------------------------------------------
    # GIỎ HÀNG
    # --------------------------------------------------------

    st.subheader("🛒 Danh sách món")

    if len(st.session_state.cart) > 0:

        cart_df = pd.DataFrame(
            st.session_state.cart
        )

        st.dataframe(
            cart_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Đơn giá": st.column_config.NumberColumn(
                    "Đơn giá",
                    format="%,d VNĐ"
                ),
                "Thành tiền": st.column_config.NumberColumn(
                    "Thành tiền",
                    format="%,d VNĐ"
                )
            }
        )

        if st.button(
            "🗑️ Xóa toàn bộ món",
            use_container_width=False
        ):

            st.session_state.cart = []

            st.rerun()

    else:

        st.info(
            "Chưa có món nào trong hóa đơn."
        )

    # --------------------------------------------------------
    # TÍNH TIỀN
    # --------------------------------------------------------

    subtotal = sum(
        item["Thành tiền"]
        for item in st.session_state.cart
    )

    st.divider()

    st.subheader("💰 Tính tiền")

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

    # --------------------------------------------------------
    # THANH TOÁN
    # --------------------------------------------------------

    st.subheader("💳 Thanh toán")

    col1, col2, col3 = st.columns(3)

    with col1:

        payment_method = st.selectbox(
            "Phương thức thanh toán",
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

        change_amount = money_received - total

        if change_amount >= 0:

            st.metric(
                "💰 Tiền thừa",
                format_money(change_amount)
            )

        else:

            st.metric(
                "⚠️ Khách còn thiếu",
                format_money(abs(change_amount))
            )

    # --------------------------------------------------------
    # TỔNG
    # --------------------------------------------------------

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            f"**Tạm tính:** "
            f"{format_money(subtotal)}"
        )

        st.write(
            f"**Giảm giá:** "
            f"-{format_money(discount)}"
        )

        st.write(
            f"**Phí phục vụ:** "
            f"{format_money(service_charge)}"
        )

        st.write(
            f"**VAT:** "
            f"{format_money(vat)}"
        )

    with col2:

        st.markdown(
            f"""
            <div class="total-card">

            <div>TỔNG THANH TOÁN</div>

            <div class="total-number">
            {format_money(total)}
            </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # --------------------------------------------------------
    # NÚT LƯU HÓA ĐƠN
    # --------------------------------------------------------

    save_button = st.button(
        "💾 LƯU & HOÀN TẤT HÓA ĐƠN",
        type="primary",
        use_container_width=True
    )

    if save_button:

        if not table_number.strip():

            st.error(
                "⚠️ Vui lòng nhập số bàn."
            )

        elif len(st.session_state.cart) == 0:

            st.error(
                "⚠️ Hóa đơn chưa có món."
            )

        elif money_received < total:

            st.error(
                "⚠️ Tiền khách đưa chưa đủ."
            )

        else:

            success, result = save_invoice(
                invoice_code=st.session_state.invoice_code,
                table_number=table_number,
                customer_name=customer_name,
                employee=employee,
                created_at=current_time,
                subtotal=subtotal,
                discount=discount,
                service_charge=service_charge,
                vat=vat,
                total=total,
                payment_method=payment_method,
                money_received=money_received,
                change_amount=change_amount,
                items=st.session_state.cart
            )

            if success:

                st.success(
                    f"✅ Đã lưu hóa đơn "
                    f"{st.session_state.invoice_code}"
                )

                st.info(
                    "Hóa đơn đã được lưu vào hệ thống."
                )

                # Xóa bill cũ
                st.session_state.cart = []

                # Tạo mã hóa đơn mới
                st.session_state.invoice_code = (
                    generate_invoice_code()
                )

                st.balloons()

            else:

                st.error(
                    f"❌ Không thể lưu hóa đơn: {result}"
                )


# ============================================================
# 8. LỊCH SỬ HÓA ĐƠN
# ============================================================

elif menu_page == "📋 Lịch sử hóa đơn":

    st.title("📋 Lịch sử hóa đơn")

    st.write(
        "Tất cả hóa đơn đã được lưu trong hệ thống."
    )

    search = st.text_input(
        "🔎 Tìm kiếm",
        placeholder=(
            "Mã hóa đơn, số bàn, "
            "khách hàng hoặc nhân viên..."
        )
    )

    invoices = get_all_invoices(search)

    if invoices.empty:

        st.info(
            "Chưa có hóa đơn nào."
        )

    else:

        total_invoices = len(invoices)

        total_revenue = invoices["total"].sum()

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "🧾 Số hóa đơn",
                total_invoices
            )

        with col2:

            st.metric(
                "💰 Tổng tiền",
                format_money(total_revenue)
            )

        st.divider()

        display_df = invoices[
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
        ].apply(format_money)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ----------------------------------------------------
        # XEM CHI TIẾT
        # ----------------------------------------------------

        st.subheader("🔍 Xem chi tiết hóa đơn")

        invoice_choices = invoices[
            ["id", "invoice_code"]
        ].values.tolist()

        selected = st.selectbox(
            "Chọn hóa đơn",
            invoice_choices,
            format_func=lambda x: x[1]
        )

        if selected:

            invoice_id = selected[0]

            invoice, items = get_invoice(
                invoice_id
            )

            if not invoice.empty:

                row = invoice.iloc[0]

                st.markdown(
                    f"""
                    <div class="invoice-header">
                    HÓA ĐƠN {row['invoice_code']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col1, col2, col3, col4 = st.columns(4)

                col1.metric(
                    "🪑 Bàn",
                    row["table_number"]
                )

                col2.metric(
                    "👤 Khách",
                    row["customer_name"]
                )

                col3.metric(
                    "👨‍🍳 Nhân viên",
                    row["employee"]
                )

                col4.metric(
                    "💰 Tổng",
                    format_money(row["total"])
                )

                st.write(
                    f"**Thời gian:** {row['created_at']}"
                )

                st.write(
                    f"**Phương thức:** "
                    f"{row['payment_method']}"
                )

                st.subheader("🍜 Chi tiết món")

                st.dataframe(
                    items,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Đơn giá":
                            st.column_config.NumberColumn(
                                format="%,d VNĐ"
                            ),
                        "Thành tiền":
                            st.column_config.NumberColumn(
                                format="%,d VNĐ"
                            )
                    }
                )

                st.divider()

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        f"**Tạm tính:** "
                        f"{format_money(row['subtotal'])}"
                    )

                    st.write(
                        f"**Giảm giá:** "
                        f"-{format_money(row['discount'])}"
                    )

                    st.write(
                        f"**Phí phục vụ:** "
                        f"{format_money(row['service_charge'])}"
                    )

                    st.write(
                        f"**VAT:** "
                        f"{format_money(row['vat'])}"
                    )

                with col2:

                    st.markdown(
                        f"""
                        ### Tổng thanh toán

                        ## {format_money(row['total'])}

                        Khách đưa:

                        **{format_money(row['money_received'])}**

                        Tiền thừa:

                        **{format_money(row['change_amount'])}**
                        """
                    )


# ============================================================
# 9. DOANH THU
# ============================================================

elif menu_page == "📊 Doanh thu":

    st.title("📊 Báo cáo doanh thu")

    conn = get_connection()

    revenue_df = pd.read_sql_query(
        """
        SELECT *
        FROM invoices
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()

    if revenue_df.empty:

        st.info(
            "Chưa có dữ liệu doanh thu."
        )

    else:

        # ----------------------------------------------------
        # TỔNG QUAN
        # ----------------------------------------------------

        total_revenue = revenue_df["total"].sum()

        total_orders = len(revenue_df)

        average_bill = (
            total_revenue / total_orders
            if total_orders > 0
            else 0
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "💰 Tổng doanh thu",
                format_money(total_revenue)
            )

        with col2:

            st.metric(
                "🧾 Tổng hóa đơn",
                total_orders
            )

        with col3:

            st.metric(
                "📈 Giá trị bill TB",
                format_money(average_bill)
            )

        st.divider()

        # ----------------------------------------------------
        # DOANH THU THEO NGÀY
        # ----------------------------------------------------

        revenue_df["Ngày"] = pd.to_datetime(
            revenue_df["created_at"],
            dayfirst=True
        ).dt.date

        daily_revenue = (
            revenue_df
            .groupby("Ngày")["total"]
            .sum()
            .reset_index()
        )

        daily_revenue.columns = [
            "Ngày",
            "Doanh thu"
        ]

        st.subheader(
            "📅 Doanh thu theo ngày"
        )

        st.dataframe(
            daily_revenue,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Doanh thu":
                    st.column_config.NumberColumn(
                        format="%,d VNĐ"
                    )
            }
        )

        # ----------------------------------------------------
        # DOANH THU THEO NHÂN VIÊN
        # ----------------------------------------------------

        st.subheader(
            "👨‍🍳 Doanh thu theo nhân viên"
        )

        employee_revenue = (
            revenue_df
            .groupby("employee")["total"]
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
            hide_index=True,
            column_config={
                "Doanh thu":
                    st.column_config.NumberColumn(
                        format="%,d VNĐ"
                    )
            }
        )

        # ----------------------------------------------------
        # PHƯƠNG THỨC THANH TOÁN
        # ----------------------------------------------------

        st.subheader(
            "💳 Doanh thu theo phương thức thanh toán"
        )

        payment_revenue = (
            revenue_df
            .groupby("payment_method")["total"]
            .sum()
            .reset_index()
        )

        payment_revenue.columns = [
            "Phương thức",
            "Doanh thu"
        ]

        st.dataframe(
            payment_revenue,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Doanh thu":
                    st.column_config.NumberColumn(
                        format="%,d VNĐ"
                    )
            }
        )
