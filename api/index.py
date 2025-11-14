import os
import telebot
from openai import OpenAI
from openai import APIError
from flask import Flask, request
import threading
import json

# 1. إعداد مفاتيح API
# يفضل استخدام متغيرات البيئة في بيئة الإنتاج (Vercel)
# سيتم استخدام المفاتيح التي قدمها المستخدم هنا لتبسيط المثال
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4.1-mini") 

# 2. تهيئة البوت ونموذج AI
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False) 
client = OpenAI()
app = Flask(__name__)

# دالة لمعالجة طلب AI في خيط منفصل (لتحسين سرعة الاستجابة)
def process_ai_request(message):
    user_message = message.text
    chat_id = message.chat.id
    
    # إرسال رسالة "جاري الكتابة..." للمستخدم
    bot.send_chat_action(chat_id, 'typing')

    try:
        # إرسال الرسالة إلى نموذج AI
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        # إرسال رد AI إلى المستخدم
        ai_response = response.choices[0].message.content
        bot.reply_to(message, ai_response)

    except APIError as e:
        error_message = f"حدث خطأ في الاتصال بنموذج AI: {e}"
        print(error_message)
        bot.reply_to(message, "عذراً، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى.")
    except Exception as e:
        error_message = f"حدث خطأ غير متوقع: {e}"
        print(error_message)
        bot.reply_to(message, "عذراً، حدث خطأ غير متوقع. يرجى التحقق من سجل الأخطاء.")

# 3. معالج رسالة /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "أهلاً بك في بوت الذكاء الاصطناعي!\n"
        "أنا بوت يعمل بنموذج AI سريع.\n"
        "يمكنك البدء في الدردشة معي الآن. فقط أرسل رسالتك."
    )
    bot.reply_to(message, welcome_text)

# 4. معالج جميع الرسائل النصية الأخرى
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    # إرسال رسالة "جاري الكتابة..." فوراً لتقليل الإحساس بالتأخير
    bot.send_chat_action(message.chat.id, 'typing')
    
    # تشغيل معالجة طلب AI في خيط منفصل لمنع حظر الخيط الرئيسي
    thread = threading.Thread(target=process_ai_request, args=(message,))
    thread.start()

# 5. نقطة نهاية Webhook
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        
        # معالجة التحديثات في خيط منفصل لضمان سرعة استجابة Webhook
        # هذا مهم جداً لمنع Vercel من إنهاء الوظيفة بسبب التأخير
        threading.Thread(target=bot.process_new_updates, args=([update],)).start()
        
        return 'OK', 200
    else:
        return 'Content-Type must be application/json', 403

# 6. نقطة نهاية للتحقق من الصحة (اختياري)
@app.route('/', methods=['GET'])
def index():
    return 'Telegram Bot Webhook is running!', 200

# ملاحظة: لا نحتاج إلى app.run() لأن Vercel تدير تشغيل التطبيق.
# Vercel تبحث عن ملف api/index.py وتقوم بتشغيل تطبيق Flask/FastAPI/etc.
