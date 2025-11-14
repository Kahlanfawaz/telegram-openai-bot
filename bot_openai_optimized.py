import os
import telebot
from openai import OpenAI
from openai import APIError
import threading
import time

# 1. إعداد مفاتيح API
# سيتم استخدام مفتاح Telegram الذي قدمه المستخدم، ونموذج AI متوفر في البيئة
TELEGRAM_BOT_TOKEN = "8409006196:AAFziSkuWb-AA2yaXwYcHq6IUK30B5WilT0"
# استخدام نموذج سريع ومتوفر في البيئة
AI_MODEL = "gpt-4.1-mini" 

# 2. تهيئة البوت ونموذج AI
# استخدام وضع "threaded=False" لتعطيل تعدد الخيوط الافتراضي والاعتماد على Threading اليدوي
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False) 
# تهيئة عميل OpenAI. المفتاح والإعدادات الأخرى يتم تحميلها تلقائيًا من متغيرات البيئة.
client = OpenAI()

# 3. معالج رسالة /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "أهلاً بك في بوت الذكاء الاصطناعي!\n"
        "أنا بوت يعمل بنموذج AI سريع.\n"
        "يمكنك البدء في الدردشة معي الآن. فقط أرسل رسالتك."
    )
    bot.reply_to(message, welcome_text)

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
        error_message = f"حدث خطأ في الاتصال بنموذج AI: {e}"
        print(error_message)
        bot.reply_to(message, "عذراً، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى.")
    except Exception as e:
        error_message = f"حدث خطأ غير متوقع: {e}"
        print(error_message)
        bot.reply_to(message, "عذراً، حدث خطأ غير متوقع. يرجى التحقق من سجل الأخطاء.")

# 4. معالج جميع الرسائل النصية الأخرى
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    # إرسال رسالة "جاري الكتابة..." فوراً لتقليل الإحساس بالتأخير
    bot.send_chat_action(message.chat.id, 'typing')
    
    # تشغيل معالجة طلب AI في خيط منفصل لمنع حظر الخيط الرئيسي
    thread = threading.Thread(target=process_ai_request, args=(message,))
    thread.start()

# 5. بدء تشغيل البوت
print("البوت قيد التشغيل...")
bot.infinity_polling()
