import telebot
import os
import logging
import uuid  # Для генерации уникальных ID сделок
import json  # Для сохранения и загрузки данных о сделках
import threading
import re

# ==========================================
# 1. НАСТРОЙКА НАДЁЖНОГО ЛОГИРОВАНИЯ
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ==========================================
# 2. НАСТРОЙКА АДМИНИСТРАТОРА, ТОКЕНА И ПОДДЕРЖКИ
# ==========================================
OWNER_ID = 993051853
DEFAULT_ADMIN_IDS = [OWNER_ID]  # Овнер всегда админ по умолчанию

BOT_TOKEN = "8737283848:AAG8188B1g6AnJesXBC_J4Nv6AOeeY8mlJk"
IMAGE_PATH = "image.jpg" 
SUPPORT_USERNAME = "otcelftosupport" 

bot = telebot.TeleBot(BOT_TOKEN)
deals_lock = threading.Lock()

# Файлы базы данных
DEALS_FILE = "deals.json"
USER_DATA_FILE = "user_data.json"
USER_DEALS_FILE = "user_deals.json"
ADMINS_FILE = "admins_json.json"

# Функция для загрузки и сохранения динамического списка админов
def load_admin_ids():
    try:
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [int(x) for x in data]
    except Exception:
        # Если файла нет, создаем его с дефолтным OWNER_ID
        with open(ADMINS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_ADMIN_IDS, f)
        return DEFAULT_ADMIN_IDS

def save_admin_ids(admins_list):
    try:
        with open(ADMINS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(set(admins_list)), f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения админов: {e}")

ADMIN_IDS = load_admin_ids()

def is_admin(user_id):
    return user_id in ADMIN_IDS or user_id == OWNER_ID

#=== Language settings ===
user_language = {}  
language_message_ids = {} 

def get_language(user_id):
    return user_language.get(user_id, 'ru')  

def set_language(user_id, language):
    user_language[user_id] = language

def generate_deal_id():
    return uuid.uuid4().hex[:10]

#=== Language dictionary ===
localized_text = {
    'ru': {
        'welcome_message': "*Добро пожаловать в ELF OTC – надежный P2P-гарант*\n\n"
                           "*💼 Покупайте и продавайте всё, что угодно – безопасно!*\n"
                           "От Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n"
                           "🔹 Удобное управление кошельками\n"
                           "🔹 Реферальная система\n\n"
                           "Выберите нужный раздел ниже:",
        'requisites_menu': "🔑 Добавьте ваши реквизиты:\n\nПожалуйста, выберите метод ниже.",
        'ton_wallet_prompt_new': "🔑 Добавьте ваш TON-кошелек:\n\nПожалуйста, отправьте адрес вашего кошелька",
        'ton_wallet_prompt_existing': "💼 Ваш текущий кошелек: `{}`\n\nОтправьте новый адрес кошелька для изменения или нажмите кнопку ниже для возврата в меню.",
        'create_deal_amount_prompt': "💼 Создание сделки\n\nВведите сумму сделки (число, например 500):",
        'deal_created_message': "*✅ Сделка успешно создана!*\n\n💰 Сумма: {}\n📜 Описание: {}\n💳 Валюта оплаты: {}\n🔗 Ссылка для покупателя: https://t.me{}?start={}",
        'deal_info_buyer': """💳 Информация о сделке #{}\n\n👤 Вы покупатель в сделке.\n📌 Продавец: @{} ({})\n• Успешные сделки: {}\n\n• Вы покупаете: {}\n\n🏦 Реквизиты для оплаты:\n`{}`\n\n💰 Сумма к оплате: *{}*\n\n📝 Комментарий к платежу (ID сделки): `{}`\n\n⚠️ Пожалуйста, убедитесь в правильности данных перед оплатой. Обязательно укажите ID сделки в комментарии к переводу!\n\nПосле оплаты ожидайте автоматического подтверждения""",
        'cancel_deal_confirmation': "❌ Вы уверены, что хотите отменить сделку #{}?\n\nЭто действие нельзя будет отменить.",
        'success_leave_deal': "Сделка успешно отменена.",
        'referral_message': """🔗 Ваша реферальная ссылка:\n\n{}\n\n👥 Количество рефералов: {}\n💰 Заработано с рефералов: {:.2f} TON\n20% от комиссии бота""",
        'admin_payment_confirmation': "💼 Панель управления сделкой #{}\n\nПодтвердить получение оплаты от покупателя на счета гаранта?",
        'admin_payment_confirmed': "✅ Оплата подтверждена для сделки #{}.\nОжидайте подтверждения от покупателя.",
        'admin_payment_confirmed_buyer': "💳 Оплата по сделке #{} подтверждена.\nПродавец: @{}\nСумма: {}\nОписание: {}\n\nОжидайте, пока продавец отправит товар/услугу.",
        'seller_payment_confirmation': "✅ Оплата подтверждена для сделки {}.\nСумма: {}\nОписание: {}\nПокупатель: @{}\n\nСледуйте указаниям, согласованным в сделке.\n\n⚠️ После отправки подарка нажмите кнопку ниже:",
        'seller_sent_confirmation': "✅ Вы подтвердили отправку подарка для сделки #{}.\nОжидайте подтверждение от покупателя.",
        'buyer_received_confirmation': "✅ Вы подтвердили получение подарка для сделки #{}. Сделка успешно завершена!",
        'set_deals_success': "Успешные сделки установлены на {}.",
        'buy_command_usage': "Пожалуйста, укажите код сделки после команды /buy",
        'deal_not_found': "Сделка не найдена.",
        'payment_confirmed_for_seller': "✅ Сделка {} успешно завершена!\nПокупатель @{} подтвердил получение подарка.",
        "wallet_added_successfully": "✅ Реквизиты успешно изменены!",
        "no_wallet_message": "❌ Сначала добавьте ваши реквизиты (TON или СНГ) перед созданием сделки.",
        "add_wallet_button_text": "Добавить реквизиты",
        'create_deal_prompt': "*💼 Создание сделки*\n\nВведите сумму сделки в формате числа.\n\n*📝 Укажите, что вы предлагаете в этой сделке:*\n\nПример: 10 Кепок и Пепе...",
        "invalid_wallet_format": "❌ Неверный формат TON-кошелька. Попробуйте еще раз.",
        "wait_buyer": "Ожидайте подтверждение от покупателя"
    },
    'en': {
        'welcome_message': "*Welcome to ELF OTC - a reliable P2P guarantor*\n\n*💼 Buy and sell anything safely!*",
        'requisites_menu': "🔑 Add your requisites:\n\nPlease select a method below.",
        'ton_wallet_prompt_new': "🔑 Add your TON wallet:\n\nPlease send your wallet address",
        'ton_wallet_prompt_existing': "*💼 Your current wallet:* `{}`\n\nSend a new wallet address to change or click the button below to return to the menu.",
        'create_deal_amount_prompt': "*💼 Creating a deal*\n\nEnter the deal amount:",
        'deal_created_message': "*✅ Deal created successfully!*\n\n💰 Amount: {}\n📜 Description: {}\n💳 Currency Type: {}\n🔗 Buyer link: https://t.me{}?start={}",
        'deal_info_buyer': """CNG Deal information #{}\n\nYou are the buyer in the deal.\nSeller: @{} ({})\n• Successful deals: {}\n\n• You are buying: {}\n\nPayment requisites:\n`{}`\n\n💰 Amount to pay: *{}*\n\n📝 Payment comment (ID): `{}`\n\n⚠️ Please ensure the correctness of the data before paying. Make sure to specify Deal ID in payment comment!""",
        'cancel_deal_confirmation': "❌ Are you sure you want to cancel deal #{}?\n\nThis action cannot be undone.",
        'success_leave_deal': "✅ Deal cancelled successfully.",
        'referral_message': """🔗 Your referral link:\n\n{}\n\n👥 Number of referrals: {}\n💰 Earned from referrals: {:.2f} TON\n20% of the bot's commission""",
        'admin_payment_confirmation': "💼 Admin Deal Manager #{}\n\nConfirm payment?",
        'admin_payment_confirmed': "✅ Payment confirmed for deal #{}.\nWait for confirmation from the buyer.",
        'admin_payment_confirmed_buyer': "💳 Payment for deal #{} confirmed.\nSeller: @{}\nAmount: {}\nDescription: {}\n\nWait for the seller to send the product/service.",
        'seller_payment_confirmation': "✅ Payment confirmed for deal {}.\nAmount: {}\nDescription: {}\nBuyer: @{}\n\nFollow the instructions agreed upon in the deal.\n\n⚠️ After sending the gift, click the button below:",
        'seller_sent_confirmation': "✅ You have confirmed sending the gift for deal #{}.\nWait for confirmation from the buyer.",
        'buyer_received_confirmation': "✅ You have confirmed receipt of the gift for deal #{}. The deal is completed successfully!",
        'set_deals_success': "Successful deals set to {}.",
        'buy_command_usage': "Please specify the deal code after the /buy command",
        'deal_not_found': "Deal not found.",
        'payment_confirmed_for_seller': "✅ Deal #{} completed successfully!\nBuyer @{} has confirmed receipt of the gift.",
        "wallet_added_successfully": "✅ Requisites updated successfully!",
        "no_wallet_message": "❌ Please add your requisites (TON or CIS) before creating a deal.",
        "add_wallet_button_text": "Add requisites",
        'create_deal_prompt': "*💼 Creating a deal*\n\nEnter the deal amount.\n\n*📝 Specify what you are offering in this deal:*\n\nExample: 10 Caps and Pepe...",
        "invalid_wallet_format": "❌ Invalid TON wallet format. Please try again.",
        "wait_buyer": "Waiting for confirmation from the buyer"
    }
}

def get_localized_text(key, user_id, *args):
    """
    Возвращает локализованный текст для данного ключа и ID пользователя.
    Если язык не установлен, используется русский язык по умолчанию.
    """
    language = get_language(user_id)  # Получаем язык пользователя
    try:
        # Поддержка СНГ текстов
        if key == 'requisites_type_menu':
            if language == 'ru':
                return "⚙️ **Выбор типа реквизитов**\n\nВыберите, какие реквизиты вы хотите настроить:"
            else:
                return "⚙️ **Select Requisites Type**\n\nChoose which requisites you want to configure:"
                
        if key == 'cng_wallet_prompt_new':
            if language == 'ru':
                return "💳 **Добавление карты СНГ**\n\nПожалуйста, отправьте реквизиты вашей карты СНГ в формате:\n`Банк (Страна) - Номер карты`\n\n*Пример:* `Kaspi (Казахстан) - 4400123456789012` или `Uzcard - 8600123456789012`"
            else:
                return "💳 **Adding CIS Card**\n\nPlease send your CIS card details in the format:\n`Bank (Country) - Card Number`\n\n*Example:* `Kaspi (Kazakhstan) - 4400123456789012`"
                
        if key == 'cng_wallet_prompt_existing':
            if language == 'ru':
                return "💳 **Ваша текущая карта СНГ:** `{}`\n\nОтправьте новые реквизиты для изменения или нажмите кнопку ниже для возврата."
            else:
                return "💳 **Your current CIS card:** `{}`\n\nSend new details to change or click below to return."
                
        if key == 'cng_added_successfully':
            if language == 'ru':
                return "✅ Карта СНГ успешно сохранена!"
            else:
                return "✅ CIS Card details saved successfully!"
                
        if key == 'invalid_cng_format':
            if language == 'ru':
                return "❌ Неверный формат. Пожалуйста, укажите банк и номер карты через дефис.\n*Пример:* `Kaspi - 4400123456789012`"
            else:
                return "❌ Invalid format. Please specify bank and card number separated by a hyphen.\n*Example:* `Kaspi - 4400123456789012`"

        return localized_text[language][key].format(*args)
    except KeyError:
        logging.warning(f"Key '{key}' not found for language '{language}'. Using Russian instead.")
        fallback_texts = {
            'requisites_type_menu': "⚙️ **Выбор типа реквизитов**\n\nВыберите, какие реквизиты вы хотите настроить:",
            'cng_wallet_prompt_new': "💳 **Добавление карты СНГ**\n\nПожалуйста, отправьте реквизиты вашей карты СНГ в формате:\n`Банк (Страна) - Номер карты`\n\n*Пример:* `Kaspi (Казахстан) - 4400123456789012`",
            'cng_wallet_prompt_existing': "💳 **Ваша текущая карта СНГ:** `{}`\n\nОтправьте новые реквизиты для изменения или нажмите кнопку ниже для возврата.",
            'cng_added_successfully': "✅ Карта СНГ успешно сохранена!",
            'invalid_cng_format': "❌ Неверный формат. Пожалуйста, укажите банк и номер карты через дефис.\n*Пример:* `Kaspi - 4400123456789012`"
        }
        if key in fallback_texts:
            return fallback_texts[key]
        return localized_text['ru'].get(key, "Ошибка локализации").format(*args)
    except Exception as e:
        logging.error(f"Error while getting localized text for key '{key}' and language '{language}': {e}")
        return "Ошибка локализации"

# Имена файлов для хранения данных
DEALS_FILE = "deals.json"
USER_DATA_FILE = "user_data.json"
USER_DEALS_FILE = "user_deals.json"
ADMINS_FILE = "admins.txt"

def load_deals():
    with deals_lock:
        try:
            with open(DEALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

def save_deals(deals_to_save):
    try:
        with open(DEALS_FILE, "w", encoding="utf-8") as f:
            json.dump(deals_to_save, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user_data(data_to_save):
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def load_user_deals():
    try:
        with open(USER_DEALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user_deals(deals_counts):
    try:
        with open(USER_DEALS_FILE, "w", encoding="utf-8") as f:
            json.dump(deals_counts, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def save_admin_ids(admin_list):
    try:
        with open(ADMINS_FILE, "w") as f:
            for admin_id in admin_list:
                f.write(f"{admin_id}\n")
    except Exception as e:
        logging.error(f"Ошибка при записи админов в файл: {e}")

deals = load_deals()
user_data = load_user_data()
referrals = {}  
user_deals = load_user_deals()

def generate_admin_payment_keyboard(deal_id):
    markup = telebot.types.InlineKeyboardMarkup()
    confirm_button = telebot.types.InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_payment_{deal_id}")
    markup.add(confirm_button)
    return markup

def generate_seller_keyboard(deal_id, language, sent=False, chat_id=None):
    markup = telebot.types.InlineKeyboardMarkup()
    if not sent:
        sent_button = telebot.types.InlineKeyboardButton(text="✅ Я отправил подарок" if language == 'ru' else "I sent the gift", callback_data=f"seller_sent_{deal_id}")
        markup.add(sent_button)
    else:
        wait_text = get_localized_text("wait_buyer", chat_id)
        wait_button = telebot.types.InlineKeyboardButton(text=wait_text, callback_data="wait_buyer")
        markup.add(wait_button)
    support_button = telebot.types.InlineKeyboardButton(text="🆘 Тех. Поддержка" if language == 'ru' else "SUPPORT", url=f"https://t.me{SUPPORT_USERNAME}")
    markup.add(support_button)
    return markup

def generate_buyer_keyboard(deal_id, language):
    markup = telebot.types.InlineKeyboardMarkup()
    received_button = telebot.types.InlineKeyboardButton(text="✅ Подтвердить получение" if language == 'ru' else "CONFIRM RECEIPT", callback_data=f"buyer_received_{deal_id}")
    markup.add(received_button)
    return markup

def edit_message_with_photo(chat_id, message_id, photo_path, caption, reply_markup=None):
    try:
        with open(photo_path, 'rb') as photo:
            bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=telebot.types.InputMediaPhoto(photo, caption=caption), reply_markup=reply_markup)
    except Exception:
        pass

def send_photo_with_caption(chat_id, photo_path, caption, reply_markup=None):
    try:
        with open(photo_path, 'rb') as photo:
            bot.send_photo(chat_id, photo=photo, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        pass

def send_create_deal_amount_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("🔙Back to menu" if language == 'en' else "🔙Вернуться в меню", callback_data='back_to_menu')
    markup.add(item1)

    text = get_localized_text('create_deal_amount_prompt', chat_id)

    if message_id:
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else:
        send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_deal_payment_type_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'ton_wallet' in user_data[str_chat_id]:
        markup.add(telebot.types.InlineKeyboardButton("💎 TON" if language == 'ru' else "💎 TON", callback_data='set_deal_currency_ton'))
    if str_chat_id in user_data and 'cng_wallet' in user_data[str_chat_id]:
        markup.add(telebot.types.InlineKeyboardButton("💳 Рубли (RUB)" if language == 'ru' else "💳 Rubles (RUB)", callback_data='set_deal_currency_rub'))
        markup.add(telebot.types.InlineKeyboardButton("💳 Тенге (KZT)" if language == 'ru' else "💳 Tenge (KZT)", callback_data='set_deal_currency_kzt'))
        markup.add(telebot.types.InlineKeyboardButton("💳 Гривны (UAH)" if language == 'ru' else "💳 Hryvnia (UAH)", callback_data='set_deal_currency_uah'))
        markup.add(telebot.types.InlineKeyboardButton("💳 Буни (BYN)" if language == 'ru' else "💳 BYN", callback_data='set_deal_currency_byn'))
        
    markup.add(telebot.types.InlineKeyboardButton("❌ Отмена" if language == 'ru' else "❌ Cancel", callback_data='back_to_menu'))
    
    text = "💳 **Выберите валюту для проведения этой сделки:**\n\nПокупатель получит те реквизиты, которые вы укажете." if language == 'ru' else "💳 **Select currency for this deal:**"
    
    if message_id:
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else:
        send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)
def send_main_menu(chat_id, message_id=None, full_menu=True):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    item1 = telebot.types.InlineKeyboardButton("⚙️Requisites" if language == 'en' else "⚙️Настройка реквизитов", callback_data='ton_wallet')
    item2 = telebot.types.InlineKeyboardButton("📄Create deal" if language == 'en' else "📄Создать сделку", callback_data='create_deal')
    item4 = telebot.types.InlineKeyboardButton("📎Refreral link" if language == 'en' else "📎Реферальная ссылка", callback_data='referral')
    markup.add(item1, item2, item4)

    if is_admin(chat_id):
        item_panel = telebot.types.InlineKeyboardButton("👑 Админ-панель", callback_data='open_admin_panel')
        markup.add(item_panel)

    if full_menu:
        item6 = telebot.types.InlineKeyboardButton("🌐Change language", callback_data='change_language')
        item5 = telebot.types.InlineKeyboardButton("📞Support" if language == 'en' else "📞Поддержка", url=f"https://t.me/otcelftosupport")
        markup.add(item6, item5)

    text = get_localized_text('welcome_message', chat_id)

    if message_id:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)
def send_ton_wallet_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    item1 = telebot.types.InlineKeyboardButton("💎 TON кошелек" if language == 'ru' else "💎 TON Wallet", callback_data='setup_ton_only')
    item2 = telebot.types.InlineKeyboardButton("💳 Карты СНГ (Kaspi, Uzcard...)" if language == 'ru' else "💳 CIS Cards", callback_data='setup_cng_only')
    item3 = telebot.types.InlineKeyboardButton("🔙Назад в меню" if language == 'ru' else "🔙Back to menu", callback_data='back_to_menu')
    markup.add(item1, item2, item3)

    text = get_localized_text('requisites_type_menu', chat_id)

    if message_id:
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else:
        send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_actual_ton_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("🔙Назад к типам" if language == 'ru' else "🔙Back", callback_data='ton_wallet')
    markup.add(item1)

    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'ton_wallet' in user_data[str_chat_id]:
        text = get_localized_text('ton_wallet_prompt_existing', chat_id, user_data[str_chat_id]['ton_wallet'])
    else:
        text = get_localized_text('ton_wallet_prompt_new', chat_id)

    if message_id:
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else:
        send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_cng_wallet_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("🔙Назад к типам" if language == 'ru' else "🔙Back", callback_data='ton_wallet')
    markup.add(item1)

    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'cng_wallet' in user_data[str_chat_id]:
        text = get_localized_text('cng_wallet_prompt_existing', chat_id, user_data[str_chat_id]['cng_wallet'])
    else:
        text = get_localized_text('cng_wallet_prompt_new', chat_id)

    if message_id:
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else:
        send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def send_deal_payment_type_prompt(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    str_chat_id = str(chat_id)
    if str_chat_id in user_data and 'ton_wallet' in user_data[str_chat_id]:
        markup.add(telebot.types.InlineKeyboardButton("💎 TON" if language == 'ru' else "💎 TON", callback_data='set_deal_currency_ton'))
    if str_chat_id in user_data and 'cng_wallet' in user_data[str_chat_id]:
        markup.add(telebot.types.InlineKeyboardButton("💳 Рубли (RUB)" if language == 'ru' else "💳 Rubles (RUB)", callback_data='set_deal_currency_rub'))
        markup.add(telebot.types.InlineKeyboardButton("💳 Тенге (KZT)" if language == 'ru' else "💳 Tenge (KZT)", callback_data='set_deal_currency_kzt'))
        markup.add(telebot.types.InlineKeyboardButton("💳 Гривны (UAH)" if language == 'ru' else "💳 Hryvnia (UAH)", callback_data='set_deal_currency_uah'))
        markup.add(telebot.types.InlineKeyboardButton("💳 Буни (BYN)" if language == 'ru' else "💳 BYN", callback_data='set_deal_currency_byn'))
        
    markup.add(telebot.types.InlineKeyboardButton("❌ Отмена" if language == 'ru' else "❌ Cancel", callback_data='back_to_menu'))
    
    text = "💳 **Выберите валюту для проведения этой сделки:**\n\nПокупатель получит те реквизиты, которые вы укажете." if language == 'ru' else "💳 **Select currency for this deal:**"
    
    if message_id:
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else:
        send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)
def send_cancel_deal_confirmation(chat_id, deal_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("✅Yes, cancel" if language == 'en' else "✅Да, отменить", callback_data=f"confirm_leave_deal_{deal_id}")
    item2 = telebot.types.InlineKeyboardButton("NO" if language == 'en' else "НЕТ", callback_data=f"deal_info_{deal_id}")  
    markup.add(item1, item2)
    text = get_localized_text('cancel_deal_confirmation', chat_id, deal_id)
    if message_id:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

def send_buyer_leave_deal_confirmation(chat_id, deal_id, message_id):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton("✅YES, LEAVE" if language == 'en' else "✅ДА, ПОКИНУТЬ", callback_data=f"confirm_buyer_leave_deal_{deal_id}_{message_id}") 
    item2 = telebot.types.InlineKeyboardButton("NO" if language == 'en' else "НЕТ", callback_data=f"deal_info_{deal_id}")  
    markup.add(item1, item2)
    text = get_localized_text('cancel_deal_confirmation', chat_id, deal_id)
    edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)

def send_admin_panel_menu(chat_id, message_id=None):
    language = get_language(chat_id)
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    item1 = telebot.types.InlineKeyboardButton("📝 Посмотреть активные сделки", callback_data='admin_view_active_deals')
    item2 = telebot.types.InlineKeyboardButton("➕ Добавить администратора", callback_data='admin_add_new_id')
    item3 = telebot.types.InlineKeyboardButton("➖ Удалить администратора", callback_data='admin_remove_id')
    item4 = telebot.types.InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_menu')
    markup.add(item1, item2, item3, item4)
    
    text = "👑 **Панель управления проектом ELF OTC**\n\nВы можете просматривать/подтверждать сделки и управлять доступом к системе."
    if message_id:
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else:
        send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)

def is_valid_ton_address(address):
    pattern = r"^(EQ|UQ)[a-zA-Z0-9_-]{46}$"
    return bool(re.match(pattern, address))


# === Обработчики ===
def send_no_wallet_message(chat_id, message_id=None):
    markup = telebot.types.InlineKeyboardMarkup()
    item1 = telebot.types.InlineKeyboardButton(get_localized_text('add_wallet_button_text', chat_id), callback_data='ton_wallet')
    markup.add(item1)
    text = get_localized_text('no_wallet_message', chat_id)
    if message_id:
        edit_message_with_photo(chat_id, message_id, IMAGE_PATH, text, markup)
    else:
        send_photo_with_caption(chat_id, IMAGE_PATH, text, markup)
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    language = get_language(chat_id)
    parts = message.text.split()

    if len(parts) > 1:
        param = parts[1]
        if param.startswith('ref='):
            referrer_id = int(param[4:])  
            if referrer_id != chat_id:  
                if referrer_id not in referrals:
                    referrals[referrer_id] = {'referrals': 0, 'earned': 0.0}
                referrals[referrer_id]['referrals'] += 1
                send_main_menu(chat_id, full_menu=True)
            else:
                send_main_menu(chat_id, full_menu=True)
        else:  
            deal_id = param  
            with deals_lock:
                if deal_id in deals:
                    if chat_id == deals[deal_id].get('seller_id'):  
                        bot.send_message(chat_id, "❌ Вы не можете участвовать в своей же сделке." if language == 'ru' else "You cannot be the buyer in your own deal.")
                        return
                    if 'buyer_id' in deals[deal_id] and deals[deal_id]['buyer_id'] is not None:
                        bot.send_message(chat_id, "К этой сделке уже присоединился покупатель." if language == 'ru' else "This deal already has a buyer.")
                        return

                    deals[deal_id]['buyer_id'] = chat_id  
                    save_deals(deals)
                    send_deal_info_for_buyer(chat_id, deal_id, None)  
                    
                    seller_id = deals[deal_id]['seller_id']
                    try:
                        buyer_username = message.from_user.username or f"id{chat_id}"
                    except Exception:
                        buyer_username = f"id{chat_id}"
                    bot.send_message(seller_id, f"Пользователь @{buyer_username} присоединился к сделке #{deal_id}\nНе переводите товар до подтверждения оплаты!")
                else:
                    bot.send_message(chat_id, "Сделка не найдена.")
    else:
        send_main_menu(chat_id, full_menu=True)

@bot.message_handler(commands=['buy'])
def buy_command(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    parts = message.text.split()
    if len(parts) == 2:
        deal_id = parts[1]
        if deal_id in deals:
            bot.send_message(chat_id, get_localized_text('admin_payment_confirmation', chat_id, deal_id), reply_markup=generate_admin_payment_keyboard(deal_id))

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global deals, user_data, ADMIN_IDS
    if call.message:
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        data = call.data
        language = get_language(chat_id)
        str_chat_id = str(chat_id)

        if data in ['back_to_menu', 'ton_wallet', 'open_admin_panel']:
            if str_chat_id in user_data:
                user_data[str_chat_id]['state'] = None
                save_user_data(user_data)

        if data == 'ton_wallet':
            send_ton_wallet_prompt(chat_id, message_id)  
        elif data == 'open_admin_panel':
            if not is_admin(chat_id): return
            send_admin_panel_menu(chat_id, message_id)
        elif data == 'admin_view_active_deals':
            if not is_admin(chat_id): return
            if not deals:
                bot.answer_callback_query(call.id, "В данный момент активных сделок нет.", show_alert=True)
                return
            for d_id, d_data in deals.items():
                m_up = generate_admin_payment_keyboard(d_id)
                bot.send_message(chat_id, f"Сделка #{d_id}\nПродавец: id{d_data['seller_id']}\nСумма: {d_data['amount']} {d_data.get('currency', 'TON')}\nОписание: {d_data['description']}", reply_markup=m_up)
            bot.answer_callback_query(call.id)
        elif data in ['admin_add_new_id', 'admin_remove_id']:
            if chat_id != OWNER_ID:
                bot.answer_callback_query(call.id, "Управлять списком админов может только владелец проекта.", show_alert=True)
                return
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_add_id' if data == 'admin_add_new_id' else 'waiting_for_remove_id'
            save_user_data(user_data)
            bot.send_message(chat_id, "Введите Telegram ID пользователя:")
            bot.answer_callback_query(call.id)
        elif data == 'setup_ton_only':
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_ton_wallet'
            save_user_data(user_data)
            send_actual_ton_prompt(chat_id, message_id)
        elif data == 'setup_cng_only':
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_cng_wallet'
            save_user_data(user_data)
            send_cng_wallet_prompt(chat_id, message_id)
        elif data == 'create_deal':
            has_requisites = str_chat_id in user_data and ('ton_wallet' in user_data[str_chat_id] or 'cng_wallet' in user_data[str_chat_id])
            if not has_requisites:
                send_no_wallet_message(chat_id, message_id)
                return
            user_data.setdefault(str_chat_id, {})['state'] = 'waiting_for_deal_amount'
            save_user_data(user_data)
            send_create_deal_amount_prompt(chat_id, message_id)
            
        elif data.startswith('set_deal_currency_'):
            curr_code = data.split('_')[3].upper()
            p_type = 'TON' if curr_code == 'TON' else 'СНГ'
            amount = user_data[str_chat_id]['deal_amount']
            description = user_data[str_chat_id]['deal_desc']
            deal_id = generate_deal_id()
            
            with deals_lock:
                deals[deal_id] = {
                    'seller_id': chat_id,
                    'amount': amount,
                    'description': description,
                    'payment_type': p_type,
                    'currency': curr_code,
                    'seller_sent': False 
                }
                save_deals(deals)
                
            # ИСПРАВЛЕНО: Строки разделены, markup перенесён на новую строчку с правильным отступом
            bot_username = bot.get_me().username
            full_amt_str = f"{amount} {curr_code}"
            text = get_localized_text('deal_created_message', chat_id, full_amt_str, description, f"{p_type} ({curr_code})", bot_username, deal_id)
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("❌Отменить сделку" if language == 'ru' else "❌Cancel deal", callback_data=f"cancel_deal_{deal_id}"))
            
            bot.delete_message(chat_id, message_id)
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
            
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)

        elif data == 'back_to_menu':
            send_main_menu(chat_id, message_id, full_menu=True)  
        elif data.startswith('cancel_deal_'):
            deal_id = data.split('_')[2]
            send_cancel_deal_confirmation(chat_id, deal_id) 
        elif data.startswith('confirm_leave_deal_'):
            deal_id = data.split('_')[3]
            if deal_id in deals:
                del deals[deal_id]
                save_deals(deals)  
                send_main_menu(chat_id, full_menu=True)
        elif data.startswith('admin_confirm_payment_'):
            deal_id = data.split('_')[3]
            if deal_id in deals:
                seller_id = deals[deal_id]['seller_id']
                amount = deals[deal_id]['amount']  
                description = deals[deal_id]['description']  
                curr_code = deals[deal_id].get('currency', 'TON')
                buyer_id = deals[deal_id].get('buyer_id')  
                
                amt_str = f"{amount} {curr_code}"
                
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"✅ Оплата сделки #{deal_id} подтверждена.")
                if buyer_id:
                    bot.send_message(buyer_id, get_localized_text('admin_payment_confirmed_buyer', language, deal_id, f"id{seller_id}", amt_str, description), parse_mode="Markdown")
                bot.send_message(seller_id, get_localized_text('seller_payment_confirmation', language, deal_id, amt_str, description, f"id{buyer_id}"), reply_markup=generate_seller_keyboard(deal_id, language))  
        elif data.startswith('seller_sent_'):
            deal_id = data.split('_')[2]
            if deal_id in deals:
                deals[deal_id]['seller_sent'] = True  
                save_deals(deals)
                buyer_id = deals[deal_id].get('buyer_id')
                bot.send_message(chat_id, "Вы подтвердили отправку!") 
                if buyer_id:
                    bot.send_message(buyer_id, "🎁Продавец отправку подтвердил!", reply_markup=generate_buyer_keyboard(deal_id, language))
        elif data.startswith('buyer_received_'):
            deal_id = data.split('_')[2]
            if deal_id in deals:
                seller_id = deals[deal_id]['seller_id']
                user_deals[str(seller_id)] = user_deals.get(str(seller_id), 0) + 1
                save_user_deals(user_deals)
                del deals[deal_id]
                save_deals(deals)  
                send_main_menu(chat_id, None, True)
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_messages(message):
    global deals, user_data, ADMIN_IDS
    chat_id = message.chat.id
    text = message.text
    language = get_language(chat_id)
    str_chat_id = str(chat_id)

    if str_chat_id in user_data and 'state' in user_data[str_chat_id]:
        state = user_data[str_chat_id]['state']

        if state == 'waiting_for_add_id':
            try:
                new_id = int(text)
                if new_id not in ADMIN_IDS:
                    ADMIN_IDS.append(new_id)
                    save_admin_ids(ADMIN_IDS)
                    bot.send_message(chat_id, f"✅ Администратор с ID {new_id} успешно добавлен.")
                else:
                    bot.send_message(chat_id, "Этот ID уже есть в списке админов.")
            except ValueError:
                bot.send_message(chat_id, "ID должен содержать только цифры.")
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)
            return

        elif state == 'waiting_for_remove_id':
            try:
                rem_id = int(text)
                if rem_id in ADMIN_IDS:
                    ADMIN_IDS.remove(rem_id)
                    save_admin_ids(ADMIN_IDS)
                    bot.send_message(chat_id, f"✅ Администратор с ID {rem_id} успешно удален.")
                else:
                    bot.send_message(chat_id, "Этот ID не найден в списке админов.")
            except ValueError:
                bot.send_message(chat_id, "ID должен содержать только цифры.")
            user_data[str_chat_id]['state'] = None
            save_user_data(user_data)
            return

        elif state == 'waiting_for_deal_amount':
            try:
                amount = float(text)
                if amount <= 0: return
                user_data[str_chat_id]['deal_amount'] = amount
                user_data[str_chat_id]['state'] = 'waiting_for_deal_description' 
                save_user_data(user_data)
                bot.send_message(chat_id, "Укажите описание сделки:" if language == 'ru' else "Specify deal description:")
            except ValueError:
                bot.send_message(chat_id, "Сумма должна быть числом." if language == 'ru' else "Amount must be a number.")

        elif state == 'waiting_for_deal_description':
            user_data[str_chat_id]['deal_desc'] = text
            save_user_data(user_data)
            send_deal_payment_type_prompt(chat_id, None)

        elif state == 'waiting_for_ton_wallet':
            if is_valid_ton_address(text):
                user_data[str_chat_id]['ton_wallet'] = text
                user_data[str_chat_id]['state'] = None  
                save_user_data(user_data)  
                send_main_menu(chat_id, None, True)
            else:
                bot.send_message(chat_id, "Неверный формат." if language == 'ru' else "Invalid format.")

        elif state == 'waiting_for_cng_wallet':
            if '-' in text and len(text) > 10:
                user_data[str_chat_id]['cng_wallet'] = text
                user_data[str_chat_id]['state'] = None  
                save_user_data(user_data)
                send_main_menu(chat_id, None, True)
            else:
                bot.send_message(chat_id, "Формат: Банк - Номер" if language == 'ru' else "Format: Bank - Number")

if __name__ == '__main__':
    logging.info("Бот успешно инициализирован и готов к работе!")
    bot.polling(none_stop=True)