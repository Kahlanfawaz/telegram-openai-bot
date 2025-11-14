import os
import telebot
from openai import OpenAI
from openai import APIError
from flask import Flask, request
import threading
import json
from concurrent.futures import ThreadPoolExecutor
import logging

# إعداد التسجيل (Logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 1. إعداد مفاتيح API
# يجب أن يتم تعيين هذه المتغيرات في إعدادات Vercel
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# يفضل استخدام نموذج أحدث وأكثر كفاءة
AI_MODEL = os.environ.get("AI_MODEL", "gpt-3.5-turbo") # نموذج افتراضي متاح
VERCEL_URL = os.environ.get("VERCEL_URL") # عنوان URL الخاص بـ Vercel 

# 2. تهيئة البوت ونموذج AI
# استخدام وضع "threaded=False" ضروري لـ Webhook
if not TELEGRAM_BOT_TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN is not set.")
    # يمكن الخروج أو رفع استثناء هنا، لكن سنستمر للسماح لنقطة نهاية GET بالعمل
    bot = None
else:
    # استخدام وضع "threaded=False" ضروري لـ Webhook
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False) 

# تهيئة عميل OpenAI. المفتاح والإعدادات الأخرى يتم تحميلها تلقائيًا من متغيرات البيئة.
client = OpenAI()
app = Flask(__name__)

# استخدام مجمع خيوط (ThreadPoolExecutor) لإدارة الطلبات المتزامنة بكفاءة
executor = ThreadPoolExecutor(max_workers=10)

# دالة لمعالجة طلب AI في خيط منفصل
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
        # معالجة أخطاء OpenAI API
        error_message = f"حدث خطأ في الاتصال بنموذج AI: {e}"
        logging.error(error_message)
        bot.reply_to(message, "عذراً، حدث خطأ في الاتصال بخدمة الذكاء الاصطناعي. يرجى المحاولة مرة أخرى.")
    except Exception as e:
        # معالجة الأخطاء العامة
        error_message = f"حدث خطأ غير متوقع: {e}"
        logging.error(error_message)
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
    # إرسال رسالة "جاري الكتابة..." فوراً
    bot.send_chat_action(message.chat.id, 'typing')
    
    # إرسال مهمة معالجة طلب AI إلى مجمع الخيوط
    executor.submit(process_ai_request, message)

# 5. نقطة نهاية Webhook
# 5. نقطة نهاية Webhook
@app.route('/', methods=['POST'])
def webhook():
    if not bot:
        return 'Bot not initialized', 500
    
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        
        # معالجة التحديثات في خيط منفصل لضمان سرعة استجابة Webhook
        # هذا مهم جداً لمنع Vercel من إنهاء الوظيفة بسبب التأخير
        executor.submit(bot.process_new_updates, [update])
        
        return 'OK', 200
    else:
        return 'Content-Type must be application/json', 403

# 6. نقطة نهاية لتعيين Webhook (يجب استدعاؤها مرة واحدة بعد النشر)
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    if not bot:
        return 'Bot not initialized', 500
    
    if not VERCEL_URL:
        return 'VERCEL_URL environment variable is not set.', 500

    webhook_url = f"https://{VERCEL_URL}/"
    
    try:
        # محاولة تعيين Webhook
        success = bot.set_webhook(url=webhook_url)
        
        if success:
            logging.info(f"Webhook set successfully to: {webhook_url}")
            return f"Webhook set successfully to: {webhook_url}", 200
        else:
            logging.error(f"Failed to set webhook to: {webhook_url}")
            return f"Failed to set webhook to: {webhook_url}", 500
    except Exception as e:
        logging.error(f"Error setting webhook: {e}")
        return f"Error setting webhook: {e}", 500

# 7. نقطة نهاية للتحقق من الصحة (اختياري)
@app.route('/', methods=['GET'])
def index():
    return 'Telegram Bot Webhook is running! Access /set_webhook to configure the bot.', 200
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        
        # معالجة التحديثات في خيط منفصل لضمان سرعة استجابة Webhook
        # هذا مهم جداً لمنع Vercel من إنهاء الوظيفة بسبب التأخير
        executor.submit(bot.process_new_updates, [update])
        
        return 'OK', 200
    else:
        return 'Content-Type must be application/json', 403

# 6. نقطة نهاية للتحقق من الصحة (اختياري)
# تم نقل نقطة نهاية GET إلى الدالة index الجديدة في السطر 100
