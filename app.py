import streamlit as st
import pandas as pd
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

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
creds = Credentials.from_service_account_info(service_info, scopes=scope)
client = gspread.authorize(creds)

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

if selected_option == "📝 أكتب الرسالة يدويًا":
    raw_input = st.text_area("✍️ اكتب أو عدل على الرسالة:", value="")
    msg_template = f"السلام عليكم {{الاسم}}\n\n{raw_input}"
else:
    msg_template = st.text_area("✍️ اكتب أو عدل على الرسالة:", value=preset_messages[selected_option])

# ✅ إضافة الجملة الثابتة في نهاية الرسالة
msg_template += "\n\n👇 يرجى تأكيد استلام الرسالة بالرد بـ \"تم\" أو \"ما وصل\""

# ✅ تحميل بيانات الطلاب
worksheet = sheet.worksheet(selected_sheet)
df = pd.DataFrame(worksheet.get_all_records())
df_filtered = df

# ✅ عرض عدد الطلاب
st.markdown(f"👥 عدد الطلاب: **{len(df_filtered)}** سيتم إرسال الرسائل لهم")

# ✅ تحضير الرسائل
preview_data = []
for _, row in df_filtered.iterrows():
    phone_raw = row.get("الرقم", "")
    if not phone_raw:
        continue

    name = row.get("الاسم", "").strip()
    if not name:
        name = "صديقي"
        row["الاسم"] = name

    try:
        message = msg_template.format(**row)
    except KeyError as e:
        st.error(f"⚠️ يوجد متغير غير موجود في الرسالة: {e}")
        st.stop()

    number = format_phone_number(phone_raw)
    preview_data.append({
        "📞 الرقم": number,
        "👤 الاسم": name,
        "📨 الرسالة": message
    })

# ✅ تقسيم المعاينات إلى مجموعات من 30 طالب
group_size = 30
total_groups = (len(preview_data) + group_size - 1) // group_size

st.markdown("## 🚀 إرسال الرسائل حسب المجموعات")
send_log = sheet.worksheet("send_log")
existing_logs = send_log.get_all_values()
existing_keys = [row[2] + row[1] for row in existing_logs[1:]]

for group_index in range(total_groups):
    group_data = preview_data[group_index * group_size : (group_index + 1) * group_size]

    with st.expander(f"📦 المجموعة {group_index + 1} ({len(group_data)} طالب)"):
        st.dataframe(pd.DataFrame(group_data), use_container_width=True)

        if st.button(f"📨 إرسال المجموعة {group_index + 1}"):
            for row in group_data:
                name = row["👤 الاسم"]
                number = row["📞 الرقم"]
                message = row["📨 الرسالة"]

                key = number + selected_sheet
                timestamp = datetime.now().isoformat()

                if key in existing_keys:
                    continue

                send_log.append_row([selected_sheet, name, number, message, "pending", timestamp])

                # تحديث وقت الإرسال في الـ worksheet الأصلي
                for idx, df_row in df_filtered.iterrows():
                    if format_phone_number(df_row.get("الرقم", "")) == number:
                        worksheet.update_cell(idx + 2, 3, timestamp)

            st.success(f"✅ تم إرسال المجموعة {group_index + 1}")

# ✅ توقيع الحقوق أسفل الصفحة
st.markdown("---")
st.caption("🛡️ تم تطوير هذا النظام بواسطة د. محمد العمري - جميع الحقوق محفوظة")
