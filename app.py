import streamlit as st
import pandas as pd
import json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ✅ دالة تنسيق الرقم
def format_phone_number(number):
    number = str(number).strip().replace(" ", "").replace("-", "").replace("+", "")
    if number.startswith(("962", "966", "965", "972")):
        return number
    if number.startswith("0"):
        return "962" + number[1:]
    if number.startswith("7") and len(number) == 9:
        return "962" + number
    if len(number) == 10 and number.startswith("07"):
        return "962" + number[1:]
    return number

# ✅ إعداد الاتصال بـ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_info, scope)
client = gspread.authorize(creds)

# ✅ فتح Google Sheet
sheet = client.open_by_key("1gin23ojAkaWviu7zy5wVqMqR2kX1xQDTz2EkQsepdQo")
worksheet_list = sheet.worksheets()
sheet_names = [ws.title for ws in worksheet_list if ws.title != "send_log"]

# ✅ واجهة Streamlit
st.set_page_config(page_title="إرسال واتساب للطلاب", layout="centered")
st.title("📤 إرسال رسالة واتساب للطلاب")
selected_sheet = st.selectbox("📄 اختر الشيت", sheet_names)

# ✅ الرسالة الافتراضية المخصصة
default_message = """السلام عليكم ورحمة الله كيفك {الاسم} 🤍

تم رفع المحاضره عالمنصه ✅"""
msg_template = st.text_area("✍️ اكتب الرسالة", value=default_message)

# ✅ تحميل بيانات الطلاب
worksheet = sheet.worksheet(selected_sheet)
df = pd.DataFrame(worksheet.get_all_records())

# ✅ تصفية الطلاب الذين لم يتم إرسال الرسائل لهم نهائيًا
exclude_keywords = ["تم", "done", "✅", "🚀", "sent", "yes", "إرسال"]
df_filtered = df[
    ~df["تم الارسال؟"].astype(str).str.strip().str.lower().apply(
        lambda val: any(keyword in val for keyword in exclude_keywords)
    )
]

# ✅ عرض عدد الطلاب
st.markdown(f"👥 عدد الطلاب: **{len(df_filtered)}** لم يتم إرسال الرسائل لهم نهائيًا")

# ✅ معاينة الرسائل على شكل جدول
preview_data = []
for _, row in df_filtered.iterrows():
    try:
        message = msg_template.format(**row)
    except KeyError as e:
        st.error(f"⚠️ يوجد متغير غير موجود في الرسالة: {e}")
        break
    number = format_phone_number(row["الرقم"])
    preview_data.append({
        "📞 الرقم": number,
        "👤 الاسم": row["الاسم"],
        "📨 الرسالة": message
    })

if preview_data:
    st.markdown("### 👀 المعاينة:")
    st.dataframe(pd.DataFrame(preview_data), use_container_width=True)

# ✅ زر الإرسال
if st.button("🚀 إرسال الرسائل"):
    send_log = sheet.worksheet("send_log")
    existing_logs = send_log.get_all_values()
    existing_keys = [row[2] + row[1] for row in existing_logs[1:]]

    for i, row in df_filtered.iterrows():
        name = row["الاسم"]
        phone_raw = row["الرقم"]
        number = format_phone_number(phone_raw)
        message = msg_template.format(**row)
        key = number + selected_sheet

        if key in existing_keys:
            continue

        timestamp = datetime.now().isoformat()
        send_log.append_row([selected_sheet, name, number, message, "pending", timestamp])
        worksheet.update_cell(i + 2, 3, "✅ تم الإرسال")

    st.success("✅ تم تجهيز الرسائل وتحديث حالة الإرسال في الشيت.")

# ✅ توقيع الحقوق أسفل الصفحة
st.markdown("---")
st.caption("🛡️ تم تطوير هذا النظام بواسطة د. محمد العمري - جميع الحقوق محفوظة")
