import os
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio

# Загружаем токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения")

bot = Bot(token=BOT_TOKEN)

# Путь к файлу с данными (в Vercel используем tmp директорию для временных файлов)
USERS_DATA_FILE = '/tmp/users_data.json'

def load_users_data():
    """Загрузка данных пользователей из файла"""
    if os.path.exists(USERS_DATA_FILE):
        with open(USERS_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users_data(data):
    """Сохранение данных пользователей в файл"""
    with open(USERS_DATA_FILE, 'w') as f:
        json.dump(data, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    users_data = load_users_data()
    user_id = str(update.effective_user.id)
    
    if user_id not in users_data:
        users_data[user_id] = {
            'last_walk': None,
            'days_without_walk': 0
        }
        save_users_data(users_data)
    
    await update.message.reply_text(
        "Привет! Я буду отслеживать твои прогулки с @ilkome.\n"
        "Используй /walk чтобы отметить прогулку\n"
        "Используй /status чтобы узнать статус прогулок"
    )

async def walk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /walk"""
    users_data = load_users_data()
    user_id = str(update.effective_user.id)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    if user_id not in users_data:
        users_data[user_id] = {}
    
    users_data[user_id]['last_walk'] = current_date
    users_data[user_id]['days_without_walk'] = 0
    
    save_users_data(users_data)
    
    await update.message.reply_text("Отлично! Прогулка отмечена.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    users_data = load_users_data()
    user_id = str(update.effective_user.id)
    
    if user_id not in users_data or users_data[user_id].get('last_walk') is None:
        await update.message.reply_text("У вас пока нет отмеченных прогулок!")
        return
    
    last_walk = datetime.strptime(users_data[user_id]['last_walk'], '%Y-%m-%d')
    days_passed = (datetime.now() - last_walk).days
    
    await update.message.reply_text(
        f"Последняя прогулка была: {users_data[user_id]['last_walk']}\n"
        f"Дней без прогулки: {days_passed}"
    )

async def setup_application():
    """Настройка приложения"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("walk", walk))
    application.add_handler(CommandHandler("status", status))
    
    return application

async def process_update(update_data):
    """Обработка входящего обновления"""
    application = await setup_application()
    await application.initialize()
    await application.process_update(
        Update.de_json(json.loads(update_data), application.bot)
    )
    await application.shutdown()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Обработка входящих POST запросов"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        asyncio.run(process_update(post_data))
        
        self.send_response(200)
        self.end_headers()
        return

    def do_GET(self):
        """Обработка входящих GET запросов"""
        self.send_response(200)
        self.end_headers()
        self.wfile.write('Бот работает!'.encode()) 