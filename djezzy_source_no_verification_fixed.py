import telebot
import requests
import json
import os
import time
from datetime import datetime, timedelta

# إعدادات البوت
TOKEN = '8158296087:AAFNYc1mfo9ohhWk19YjavaFXsXXdvxhOSc'
ADMIN_ID = 1963100599
bot = telebot.TeleBot(TOKEN)

# مسار ملف البيانات
data_file_path = 'djezzy_data.json'

# تحميل بيانات المستخدمين
def load_user_data():
    if os.path.exists(data_file_path):
        with open(data_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# حفظ بيانات المستخدمين
def save_user_data(data):
    with open(data_file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

# إخفاء رقم الهاتف
def hide_phone_number(phone_number):
    return phone_number[:4] + '*******' + phone_number[-2:]

# إرسال OTP
def send_otp(msisdn):
    url = 'https://apim.djezzy.dz/oauth2/registration'
    payload = f'msisdn={msisdn}&client_id=6E6CwTkp8H1CyQxraPmcEJPQ7xka&scope=smsotp'
    headers = {
        'User-Agent': 'Djezzy/2.6.7',
        'Connection': 'close',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cache-Control': 'no-cache'
    }
    try:
        response = requests.post(url, data=payload, headers=headers, verify=False)
        print('Send OTP Response:', response.text)
        return response.status_code == 200
    except requests.RequestException as error:
        print('Error sending OTP:', error)
        return False

# التحقق من OTP
def verify_otp(msisdn, otp):
    url = 'https://apim.djezzy.dz/oauth2/token'
    payload = f'otp={otp}&mobileNumber={msisdn}&scope=openid&client_id=6E6CwTkp8H1CyQxraPmcEJPQ7xka&client_secret=MVpXHW_ImuMsxKIwrJpoVVMHjRsa&grant_type=mobile'
    headers = {
        'User-Agent': 'Djezzy/2.6.7',
        'Connection': 'close',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cache-Control': 'no-cache'
    }
    try:
        response = requests.post(url, data=payload, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as error:
        print('Error verifying OTP:', error)
        return None

# تطبيق الهدية
def apply_gift(chat_id, msisdn, access_token, username, name):
    user_data = load_user_data()
    last_applied = user_data.get(str(chat_id), {}).get('last_applied')
    if last_applied:
        last_applied_time = datetime.fromisoformat(last_applied)
        if datetime.now() - last_applied_time < timedelta(days=1):
            bot.send_message(chat_id, "⚠️ لا يمكنك استخدام الهدية الآن. الرجاء الانتظار 24 ساعة.")
            return False

    url = f'https://apim.djezzy.dz/djezzy-api/api/v1/subscribers/{msisdn}/subscription-product?include='
    gift_code = 'TransferInternet2Go'
    payload = {
        "data": {
            "id": "TransferInternet2Go",
            "type": "products",
            "meta": {
                "services": {
                    "steps": 10000,
                    "code": "FAMILY4000",
                    "id": "WALKWIN"
                }
            }
        }
    }
    headers = {
        'User-Agent': 'Djezzy/2.6.7',
        'Connection': 'Keep-Alive',
        'Content-Type': 'application/json; charset=utf-8',
        'Host': 'apim.djezzy.dz',
        'Authorization': f'Bearer {access_token}'
    }
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response_data = response.json()
        if "successfully done" in response_data.get('message', ''):
            hidden_phone = hide_phone_number(msisdn)
            success_message = (
                f"🎉 تم تفعيل الأنترنت بنجاح!\n\n"
                f"👤 الاسم: {name}\n"
                f"🧑‍💻 المستخدم: @{username}\n"
                f"📞 الرقم: {hidden_phone}"
            )
            bot.send_message(chat_id, success_message)
            user_data[str(chat_id)]['last_applied'] = datetime.now().isoformat()
            save_user_data(user_data)
            return True
        else:
            bot.send_message(chat_id, f"⚠️ خطأ: {response_data.get('message', 'غير معروف')}")
            return False
    except requests.RequestException as error:
        print('Error applying gift:', error)
        bot.send_message(chat_id, "⚠️ حدث خطأ أثناء تطبيق الهدية.")
        return False

# التحقق من العضوية في المجموعة
# أوامر البداية
@bot.message_handler(commands=['start'])
def handle_start(msg):
    chat_id = msg.chat.id
    user_id = msg.from_user.id

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text='📱 إرسال رقم الهاتف 📱', callback_data='send_number'))
    bot.send_message(chat_id, '👋 مرحبًا! الرجاء إرسال رقم هاتف Djezzy الذي يبدأ بـ 07', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'send_number')
def handle_send_number(callback_query):
    chat_id = callback_query.message.chat.id
    bot.send_message(chat_id, '📱 أرسل رقم هاتفك Djezzy الذي يبدأ بـ 07:')
    bot.register_next_step_handler_by_chat_id(chat_id, handle_phone_number)

def handle_phone_number(msg):
    chat_id = msg.chat.id
    text = msg.text
    if text.startswith('07') and len(text) == 10:
        msisdn = '213' + text[1:]
        if send_otp(msisdn):
            bot.send_message(chat_id, '🔢 تم إرسال رمز OTP. أدخله الآن:')
            bot.register_next_step_handler_by_chat_id(chat_id, lambda msg: handle_otp(msg, msisdn))
        else:
            bot.send_message(chat_id, '⚠️ فشل إرسال رمز OTP. حاول مرة أخرى.')
    else:
        bot.send_message(chat_id, '⚠️ أدخل رقمًا صالحًا يبدأ بـ 07.')

def handle_otp(msg, msisdn):
    chat_id = msg.chat.id
    otp = msg.text
    tokens = verify_otp(msisdn, otp)
    if tokens:
        user_data = load_user_data()
        user_data[str(chat_id)] = {
            'username': msg.from_user.username,
            'telegram_id': chat_id,
            'msisdn': msisdn,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'last_applied': None
        }
        save_user_data(user_data)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(text='Z زيدووووو Z', callback_data='walkwingift'))
        bot.send_message(chat_id, '🎉 تم التحقق بنجاح! اختر الإجراء المطلوب:', reply_markup=markup)
    else:
        bot.send_message(chat_id, '⚠️ رمز OTP غير صحيح.')

@bot.callback_query_handler(func=lambda call: call.data == 'walkwingift')
def handle_walkwingift(callback_query):
    chat_id = callback_query.message.chat.id
    user_data = load_user_data()
    if str(chat_id) in user_data:
        user = user_data[str(chat_id)]
        apply_gift(chat_id, user['msisdn'], user['access_token'], user['username'], callback_query.from_user.first_name)

# running
while True:
    try:
        print('✅ bot running...')
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f"Timed out")
        time.sleep(3)

