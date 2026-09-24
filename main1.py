import csv
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

# ============================================
# 0. ИСПРАВЛЕНИЕ ДЛЯ RENDER / RAILWAY (PORT FIX)
# ============================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass

def run_health_check_server():
    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        logging.error(f"Сбой запуска HealthCheck сервера: {e}")

# ============================================
# 1. НАСТРОЙКИ И ТОЧКИ МОНИТОРИНГА
# ============================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

CSV_FILE = "flood_data.csv"
LOG_FILE = "system.log"
SUBSCRIBERS_FILE = "subscribers.txt"
LANGUAGES_FILE = "user_languages.json"

AUTO_CHECK_INTERVAL = 900 

LOCATIONS = [
    # 🏔️ Казахстан (Алматинская область)
    {"name": "Медеу (Алматы, КЗ)", "lat": 43.1575, "lon": 77.0589, "elevation": 1690},
    {"name": "Талгар (Ущелье, КЗ)", "lat": 43.2500, "lon": 77.2300, "elevation": 1200},
    {"name": "Есик (Ущелье, КЗ)", "lat": 43.2514, "lon": 77.4851, "elevation": 1750},
    {"name": "Каскелен (Ущелье, КЗ)", "lat": 43.1300, "lon": 76.6100, "elevation": 1100},    
    # 🌊 Казахстан (Запад - зона паводков)
    {"name": "Кульсары (Атырау, КЗ)", "lat": 46.9800, "lon": 54.0200},
    # 🇰🇬 Кыргызстан (Предгорья Тянь-Шаня)
    {"name": "Ала-Арча (Бишкек, КР)", "lat": 42.6400, "lon": 74.4800, "elevation": 2100},
    # 🇪🇺 Международный пример (Альпы)
    {"name": "Инсбрук (Альпы, Австрия)", "lat": 47.2692, "lon": 11.4041, "elevation": 574},
]

# ============================================
# 2. МУЛЬТИЯЗЫЧНЫЙ СЛОВАРЬ (HTML РАЗМЕТКА)
# ============================================
MESSAGES = {
    "kz": {
        "btn_status": "📊 Ауа райы статусы",
        "btn_help": "ℹ️ Көмек / Жүйе туралы",
        "btn_lang": "🌐 Тілді ауыстыру",
        "select_lang_prompt": "👋 Қош келдіңіз! Мәтіндер қай тілде көрсетілсін? Тілді таңдаңыз:",
        "lang_saved": "✅ Тіл орнатылды: Қазақша 🇰🇿",
        "error_fetch": "⚠️ Ауа райы мәліметтерін алу мүмкін болмады. Сәлден соң қайталап көріңіз.",
        "header": "🌊 <b>СППР FloodWatch KZ: АҒЫМДАҒЫ МОНИТОРИНГ</b>\n",
        "time_prefix": "🕒 <i>Тексеру уақыты (Алматы): ",
        "risk_labels": {
            "HIGH_RISK": "🚨 ЖОҒАРЫ ҚАУІП",
            "MEDIUM_RISK": "⚠️ ЖОҒАРЫ НАЗАР",
            "NORMAL": "✅ ҚАЛЫПТЫ",
            "UNKNOWN": "❓ ҚАТЕ МӘЛІМЕТ",
        },
        "alert_title": "🚨 <b>СППР FloodWatch KZ АВТОМАТТЫ ДАБЫЛ СИГНАЛЫ</b>\n\n",
        "alert_high": "🚨 <b>КРИТИКАЛЫҚ ҚАУІП</b>: <b>{name}</b> нүктесінде ({temp}°C, {rain} мм жауын-шашын)!",
        "alert_med": "⚠️ <b>НАЗАР АУДАРЫҢЫЗ</b>: <b>{name}</b> нүктесінде қауіп деңгейі көтерілді ({temp}°C, {rain} мм).",
        "help": (
            "ℹ️ <b>ШЕШІМ ҚАБЫЛДАУДЫ ҚОЛДАУ ЖҮЙЕСІ (FloodWatch KZ)</b>\n\n"
            "Жүйе тау бөктері мен қауіпті аймақтарда үздіксіз фондық мониторинг жүргізеді.\n\n"
            "• Мәлімет алу үшін <b>📊 Ауа райы статусы</b> батырмасын басыңыз.\n"
            "• Автоматты тексеру әр 15 минут сайын орындалады.\n"
            "• Ескертулер тек нақты қауіп төнгенде жіберіледі."
        )
    },
    "ru": {
        "btn_status": "📊 Статус погоды",
        "btn_help": "ℹ️ Помощь / О системе",
        "btn_lang": "🌐 Сменить язык",
        "select_lang_prompt": "👋 Добро пожаловать! Выберите удобный язык интерфейса:",
        "lang_saved": "✅ Язык установлен: Русский 🇷🇺",
        "error_fetch": "⚠️ Не удалось получить данные о погоде. Попробуйте позже.",
        "header": "🌊 <b>СППР FloodWatch KZ: ТЕКУЩИЙ МОНИТОРИНГ</b>\n",
        "time_prefix": "🕒 <i>Время проверки (Алматы): ",
        "risk_labels": {
            "HIGH_RISK": "🚨 ВЫСОКИЙ РИСК",
            "MEDIUM_RISK": "⚠️ ПОВЫШЕННОЕ ВНИМАНИЕ",
            "NORMAL": "✅ НОРМА",
            "UNKNOWN": "❓ ОШИБКА ДАННЫХ",
        },
        "alert_title": "🚨 <b>АВТОМАТИЧЕСКИЙ СИГНАЛ ТРЕВОГИ FloodWatch KZ</b>\n\n",
        "alert_high": "🚨 <b>КРИТИЧЕСКАЯ УГРОЗА</b>: В точке <b>{name}</b> ({temp}°C, {rain} мм осадков)!",
        "alert_med": "⚠️ <b>ВНИМАНИЕ</b>: В точке <b>{name}</b> повышен уровень риска ({temp}°C, {rain} мм).",
        "help": (
            "ℹ️ <b>СИСТЕМА ПОДДЕРЖКИ ПРИНЯТИЯ РЕШЕНИЙ (FloodWatch KZ)</b>\n\n"
            "Система выполняет непрерывный фоновый мониторинг метеорологических сеток "
            "в предгорных и опасных зонах.\n\n"
            "• Нажмите <b>📊 Статус погоды</b> для мгновенного сбора данных по всем точкам.\n"
            "• Автоматическая проверка выполняется каждые 15 минут.\n"
            "• Уведомления поступают только при возникновении реального риска."
        )
    },
    "en": {
        "btn_status": "📊 Weather Status",
        "btn_help": "ℹ️ Help / About",
        "btn_lang": "🌐 Change Language",
        "select_lang_prompt": "👋 Welcome! Please select your preferred language:",
        "lang_saved": "✅ Language set: English 🇬🇧",
        "error_fetch": "⚠️ Failed to fetch weather data. Please try again later.",
        "header": "🌊 <b>DSS FloodWatch KZ: CURRENT MONITORING</b>\n",
        "time_prefix": "🕒 <i>Check time (Almaty): ",
        "risk_labels": {
            "HIGH_RISK": "🚨 HIGH RISK",
            "MEDIUM_RISK": "⚠️ MEDIUM RISK",
            "NORMAL": "✅ NORMAL",
            "UNKNOWN": "❓ DATA ERROR",
        },
        "alert_title": "🚨 <b>AUTOMATIC ALERT FloodWatch KZ</b>\n\n",
        "alert_high": "🚨 <b>CRITICAL RISK</b>: At <b>{name}</b> ({temp}°C, {rain} mm precipitation)!",
        "alert_med": "⚠️ <b>WARNING</b>: Elevated risk level at <b>{name}</b> ({temp}°C, {rain} mm).",
        "help": (
            "ℹ️ <b>DECISION SUPPORT SYSTEM (FloodWatch KZ)</b>\n\n"
            "The system continuously performs background monitoring of meteorological grids "
            "in foothill and high-risk zones.\n\n"
            "• Press <b>📊 Weather Status</b> for instant data collection across all points.\n"
            "• Automatic checks run every 15 minutes.\n"
            "• Alerts are sent only when an actual risk occurs."
        )
    }
}

LANG_KEYBOARD = {
    "keyboard": [
        [{"text": "🇰🇿 Қазақша"}, {"text": "🇷🇺 Русский"}, {"text": "🇬🇧 English"}]
    ],
    "resize_keyboard": True,
}

def get_main_keyboard(lang: str) -> dict:
    msg = MESSAGES.get(lang, MESSAGES["ru"])
    return {
        "keyboard": [
            [{"text": msg["btn_status"]}],
            [{"text": msg["btn_help"]}, {"text": msg["btn_lang"]}]
        ],
        "resize_keyboard": True,
    }

last_known_risks = {loc["name"]: "NORMAL" for loc in LOCATIONS}

# ============================================
# 3. ЖУРНАЛИРОВАНИЕ И ХРАНЕНИЕ НАСТРОЕК
# ============================================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)

def load_subscribers() -> set:
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    except FileNotFoundError:
        return set()

def save_subscriber(chat_id: int):
    subscribers.add(chat_id)
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        for s in subscribers:
            f.write(f"{s}\n")

def load_user_languages() -> dict:
    try:
        with open(LANGUAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user_language(chat_id: int, lang: str):
    user_languages[str(chat_id)] = lang
    with open(LANGUAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(user_languages, f, ensure_ascii=False, indent=2)

subscribers = load_subscribers()
user_languages = load_user_languages()

def get_user_lang(chat_id: int) -> str:
    return user_languages.get(str(chat_id), "ru")

# ============================================
# 4. ВАЛИДАЦИЯ И ЗАПРОСЫ К OPEN-METEO API
# ============================================
def validate_weather(temp: float, rain: float) -> bool:
    if temp is None or rain is None:
        return False
    if temp < -50 or temp > 50 or rain < 0 or rain > 300:
        logging.warning(f"Аномалия/Сбой датчика: temp={temp}, rain={rain}")
        return False
    return True

def get_current_weather(lat: float, lon: float, elevation: int = None):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation",
    }
    if elevation:
        params["elevation"] = elevation

    try:
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json()
        return data["current"]["temperature_2m"], data["current"]["precipitation"]
    except Exception as e:
        logging.error(f"Ошибка запроса Open-Meteo ({lat}, {lon}): {e}")
        return None, None

# ============================================
# 5. ОЦЕНКА РИСКОВ (СППР ЛОГИКА)
# ============================================
def check_flood_risk(temp: float, rain: float) -> str:
    if not validate_weather(temp, rain):
        return "UNKNOWN"

    if rain >= 20.0 or (temp >= 18.0 and rain >= 15.0):
        return "HIGH_RISK"
    elif temp >= 15.0 and rain >= 5.0:
        return "MEDIUM_RISK"
    else:
        return "NORMAL"

# ============================================
# 6. СОХРАНЕНИЕ В CSV
# ============================================
def save_to_csv(row: list):
    file_exists = os.path.exists(CSV_FILE)
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Дата_Время", "Локация", "Температура_C", "Осадки_мм", "Уровень_Риска"])
            writer.writerow(row)
    except Exception as e:
        logging.error(f"Ошибка записи в CSV: {e}")

# ============================================
# 7. СЕРВИС УВЕДОМЛЕНИЙ И МОНИТОРИНГА
# ============================================
def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None):
    if reply_markup is None:
        reply_markup = get_main_keyboard(get_user_lang(chat_id))

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения пользователю {chat_id}: {e}")

def get_almaty_time() -> str:
    """Точное время Алматы (UTC+5)"""
    return (datetime.now(timezone.utc) + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")

def generate_manual_report(lang: str):
    msg = MESSAGES.get(lang, MESSAGES["ru"])
    now_str = get_almaty_time()
    lines = []
    
    for place in LOCATIONS:
        temp, rain = get_current_weather(place["lat"], place["lon"], place.get("elevation"))
        risk = check_flood_risk(temp, rain)
        
        t_str = f"{temp}°C" if temp is not None else "N/A"
        r_str = f"{rain} мм" if rain is not None else "N/A"
        risk_text = msg["risk_labels"][risk]
        
        lines.append(f"• <b>{place['name']}</b>: {t_str} | {r_str} ({risk_text})")
        save_to_csv([now_str, place["name"], temp, rain, risk])

    header = msg["header"] + msg["time_prefix"] + f"{now_str}</i>\n\n"
    return header + "\n".join(lines)

def process_background_check():
    now_str = get_almaty_time()
    raw_alerts = []

    for place in LOCATIONS:
        name = place["name"]
        temp, rain = get_current_weather(place["lat"], place["lon"], place.get("elevation"))
        
        new_risk = check_flood_risk(temp, rain)
        old_risk = last_known_risks.get(name, "NORMAL")

        save_to_csv([now_str, name, temp, rain, new_risk])

        if new_risk == "HIGH_RISK" and old_risk != "HIGH_RISK":
            raw_alerts.append(("high", name, temp, rain))
        elif new_risk == "MEDIUM_RISK" and old_risk == "NORMAL":
            raw_alerts.append(("med", name, temp, rain))

        last_known_risks[name] = new_risk

    if raw_alerts:
        for chat_id in subscribers:
            lang = get_user_lang(chat_id)
            msg = MESSAGES.get(lang, MESSAGES["ru"])
            
            user_lines = []
            for alert_type, name, temp, rain in raw_alerts:
                if alert_type == "high":
                    user_lines.append(msg["alert_high"].format(name=name, temp=temp, rain=rain))
                else:
                    user_lines.append(msg["alert_med"].format(name=name, temp=temp, rain=rain))

            full_alert = msg["alert_title"] + "\n".join(user_lines)
            send_telegram_message(chat_id, full_alert)

# ============================================
# 8. ГЛАВНЫЙ ЦИКЛ
# ============================================
def main():
    print("=" * 60)
    print("🤖 Запуск СППР FloodWatch KZ (Мультиязычный режим + Time Fix)...")
    
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    print(f"Активных подписчиков: {len(subscribers)}")
    print(f"Интервал фонового мониторинга: каждые {AUTO_CHECK_INTERVAL} сек.")
    print("=" * 60)

    last_update_id = 0
    last_auto_check = time.time()

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 5}

            try:
                res = requests.get(url, params=params, timeout=10).json()
            except requests.exceptions.RequestException:
                time.sleep(3)
                continue

            if res.get("ok") and res.get("result"):
                for update in res["result"]:
                    last_update_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"]["text"].strip()

                        if chat_id not in subscribers:
                            save_subscriber(chat_id)

                        lang = get_user_lang(chat_id)
                        msg = MESSAGES.get(lang, MESSAGES["ru"])

                        logging.info(f"Команда '{text}' от chat_id: {chat_id} (Язык: {lang})")

                        if text == "/start" or text in ["🌐 Сменить язык", "🌐 Тілді ауыстыру", "🌐 Change Language", "/lang"]:
                            send_telegram_message(chat_id, msg["select_lang_prompt"], reply_markup=LANG_KEYBOARD)

                        elif text == "🇰🇿 Қазақша":
                            save_user_language(chat_id, "kz")
                            send_telegram_message(chat_id, MESSAGES["kz"]["lang_saved"])
                        elif text == "🇷🇺 Русский":
                            save_user_language(chat_id, "ru")
                            send_telegram_message(chat_id, MESSAGES["ru"]["lang_saved"])
                        elif text == "🇬🇧 English":
                            save_user_language(chat_id, "en")
                            send_telegram_message(chat_id, MESSAGES["en"]["lang_saved"])

                        elif text in ["/status", "📊 Статус погоды", "📊 Ауа райы статусы", "📊 Weather Status"]:
                            try:
                                report = generate_manual_report(lang)
                                send_telegram_message(chat_id, report)
                            except Exception as err:
                                logging.error(f"Ошибка сбора статуса: {err}")
                                send_telegram_message(chat_id, msg["error_fetch"])

                        elif text in ["/help", "ℹ️ Помощь / О системе", "ℹ️ Көмек / Жүйе туралы", "ℹ️ Help / About"]:
                            send_telegram_message(chat_id, msg["help"])

                        else:
                            send_telegram_message(chat_id, msg["select_lang_prompt"], reply_markup=LANG_KEYBOARD)

            now_t = time.time()
            if now_t - last_auto_check >= AUTO_CHECK_INTERVAL:
                process_background_check()
                last_auto_check = now_t

        except Exception as e:
            logging.error(f"Сбой в главном цикле: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
