import json
import os
raw_key = os.environ.get("GOOGLE_SERVICE_ACCOUNT", "❌ لم يتم تحميل المتغير")
print("🔍 RAW_KEY (أول 300 حرف):\n", raw_key[:300])
import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ✅ تحميل مفتاح الخدمة من متغير البيئة (Railway)
raw_key = os.environ.get("GOOGLE_SERVICE_ACCOUNT", "").strip()

# ✅ تنظيف البداية إذا فيها "="
if raw_key.startswith("="):
    raw_key = raw_key[1:].strip()

# ✅ استبدال \\n بـ \n لتحويل المفتاح إلى شكل صحيح
raw_key = raw_key.replace('\\n', '\n')

# ✅ محاولة فك JSON مع معالجة الخطأ
try:
    service_info = json.loads(raw_key)
except json.JSONDecodeError:
    st.error("❌ خطأ في تحميل GOOGLE_SERVICE_ACCOUNT. تأكد من أن المفتاح محفوظ بصيغة JSON صحيحة كسطر واحد.")
    st.stop()

# ✅ إعداد الاتصال بـ Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(service_info, scopes=scope)
client = gspread.authorize(creds)

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

# ✅ فتح Google Sheet
sheet = client.open_by_key("1gin23ojAkaWviu7zy5wVqMqR2kX1xQDTz2EkQsepdQo")
worksheet_list = sheet.worksheets()
sheet_names = [ws.title for ws in worksheet_list if ws.title != "send_log"]

# ✅ واجهة Streamlit
st.set_page_config(page_title="إرسال واتساب للطلاب", layout="centered")
st.title("📤 إرسال رسالة واتساب للطلاب")
selected_sheet = st.selectbox("📄 اختر الشيت", sheet_names)

# ✅ المسجات الجاهزة
preset_messages = {
    "📥 نزل المكثف عالمنصة": "السلام عليكم ورحمة الله كيفك {الاسم} 🤍\n\nنزل المكثف عالمنصة، تأكد إنك تحضره بأقرب وقت لأنه شامل ومفيد جدًا قبل الامتحان ✅",
    "📚 المكمل موجود بالمكتبات": "السلام عليكم ورحمة الله كيفك {الاسم} 🤍\n\nالمكمل نزل رسميًا بالمكتبات، بإمكانك تجيبه وتبلش تحل منه ✨📘",
    "📢 رح ننزل ملاحظات عالتليجرام": "السلام عليكم ورحمة الله كيفك {الاسم} 🤍\n\nرح ننزل ملاحظات مهمة عالتليجرام خلال الساعات الجاية، فعل التنبيهات ضروري جدًا حتى توصلك أول بأول 📲🚀",
    "📞 إذا في أي سؤال": "السلام عليكم ورحمة الله كيفك {الاسم} 🤍\n\nإذا في أي سؤال أو نقطة مش واضحة، لا تتردد تراسلني بأي وقت، أنا معك خطوة بخطوة 🙌",
    "📝 أكتب الرسالة يدويًا": ""
}

selected_option = st.selectbox("اختر رسالة جاهزة أو اكتب واحدة مخصصة:", list(preset_messages.keys()))
msg_template = st.text_area("✍️ اكتب أو عدل على الرسالة:", value=preset_messages[selected_option])

# ✅ تحميل بيانات الطلاب
worksheet = sheet.worksheet(selected_sheet)
df = pd.DataFrame(worksheet.get_all_records())
df_filtered = df

# ✅ عرض عدد الطلاب
st.markdown(f"👥 عدد الطلاب: **{len(df_filtered)}** سيتم إرسال الرسائل لهم")

# ✅ معاينة الرسائل
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
        timestamp = datetime.now().isoformat()

        if key in existing_keys:
            continue

        send_log.append_row([selected_sheet, name, number, message, "pending", timestamp])
        worksheet.update_cell(i + 2, 3, timestamp)

    st.success("✅ تم تجهيز الرسائل وتحديث وقت الإرسال في الشيت.")

# ✅ التوقيع
st.markdown("---")
st.caption("🛡️ تم تطوير هذا النظام بواسطة د. محمد العمري - جميع الحقوق محفوظة")
