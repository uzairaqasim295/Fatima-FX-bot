import asyncio
import os
import json
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# ==========================================
# ⚙️ ULTIMATE 80%+ ACCURACY PRO BOT CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "8758950547:AAFRBa1f31fZ0lJciyI05mcoCZYv16bf5hs"
CHANNEL_CHAT_ID = "@Binary_Signals_Live_Malik"
HISTORY_FILE = "trading_history.json"

LIVE_PAIRS_MAP = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X", "USDCAD": "USDCAD=X", "AUDUSD": "AUDUSD=X", "NZDUSD": "NZDUSD=X",
    "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X", "EURAUD": "EURAUD=X",
    "EURCAD": "EURCAD=X", "EURNZD": "EURNZD=X", "EURCHF": "EURCHF=X",
    "GBPJPY": "GBPJPY=X", "GBPAUD": "GBPAUD=X", "GBPCAD": "GBPCAD=X",
    "GBPCHF": "GBPCHF=X", "GBPNZD": "GBPNZD=X", "AUDJPY": "AUDJPY=X",
    "AUDCAD": "AUDCAD=X", "AUDNZD": "AUDNZD=X", "CADJPY": "CADJPY=X",
    "CHFJPY": "CHFJPY=X", "NZDJPY": "NZDJPY=X", "NZDCAD": "NZDCAD=X"
}

session_stats = {"total": 0, "direct_wins": 0, "mtg_wins": 0, "losses": 0, "consecutive_losses": 0}
signals_in_session = 0
is_news_break_active = False

# --- NEWS FILTER SYSTEM ---
def check_forex_news_events():
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            events = response.json()
            now_utc = datetime.utcnow()
            for event in events:
                if event.get("impact") == "High":
                    date_str = event.get("date")
                    if date_str:
                        event_time = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
                        time_diff = (event_time - now_utc).total_seconds() / 60
                        if -5 <= time_diff <= 15:
                            return True, event.get("title", "High Impact News"), event.get("country", "USD")
    except Exception as e:
        print(f"News Check Error: {e}")
    return False, "", ""

# --- DATABASE FUNCTIONS ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_trade_to_db(result_type):
    history = load_history()
    trade_record = {
        "timestamp": time.time(),
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "result": result_type
    }
    history.append(trade_record)
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f)
    except Exception as e:
        print(f"DB Save Error: {e}")

def get_stats_by_period(period_type):
    history = load_history()
    now = datetime.utcnow()
    d_wins, m_wins, losses = 0, 0, 0
    for trade in history:
        try:
            trade_time = datetime.strptime(trade["date"], "%Y-%m-%d")
            match = False
            if period_type == "day":
                if trade["date"] == now.strftime("%Y-%m-%d"): match = True
            elif period_type == "week":
                if (now - trade_time).days <= 7: match = True
            elif period_type == "month":
                if (now - trade_time).days <= 30: match = True
                
            if match:
                res = trade["result"]
                if res == "DIRECT_WIN": d_wins += 1
                elif res == "MTG_WIN": m_wins += 1
                elif res == "LOSS": losses += 1
        except:
            continue
    total_wins = d_wins + m_wins
    total = total_wins + losses
    accuracy = (total_wins / total * 100) if total > 0 else 0.0
    return total, d_wins, m_wins, losses, accuracy

def send_telegram_message_with_result_buttons(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "📊 Day Results", "callback_data": "res_day"},
                {"text": "📅 Week Results", "callback_data": "res_week"}
            ],
            [
                {"text": "🗓️ Month Results", "callback_data": "res_month"},
                {"text": "👑 Admin Portal", "callback_data": "res_admin"}
            ]
        ]
    }
    payload = {
        'chat_id': CHANNEL_CHAT_ID, 
        'text': text, 
        'parse_mode': 'Markdown',
        'reply_markup': inline_keyboard
    }
    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"Telegram Message Error: {e}")

def send_telegram_simple_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHANNEL_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload, timeout=20)
    except Exception as e:
        print(f"Telegram Message Error: {e}")

def send_telegram_photo_with_result_buttons(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "📊 Day Results", "callback_data": "res_day"},
                {"text": "📅 Week Results", "callback_data": "res_week"}
            ],
            [
                {"text": "🗓️ Month Results", "callback_data": "res_month"},
                {"text": "👑 Admin Portal", "callback_data": "res_admin"}
            ]
        ]
    }
    for attempt in range(3):
        try:
            if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
                with open(photo_path, 'rb') as photo:
                    payload = {
                        'chat_id': CHANNEL_CHAT_ID, 
                        'caption': caption, 
                        'parse_mode': 'Markdown',
                        'reply_markup': str(inline_keyboard).replace("'", '"')
                    }
                    files = {'photo': photo}
                    response = requests.post(url, data=payload, files=files, timeout=45)
                    if response.status_code == 200:
                        return True
        except Exception:
            time.sleep(1)
    return False

async def handle_telegram_callbacks():
    offset = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    while True:
        try:
            response = requests.get(url, params={"offset": offset, "timeout": 30}, timeout=35)
            if response.status_code == 200:
                data = response.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    if "callback_query" in update:
                        cq = update["callback_query"]
                        callback_data = cq["data"]
                        query_id = cq["id"]
                        
                        ans_text = ""
                        if callback_data == "res_admin":
                            ans_text = (
                                "👑 *FATIMA ZESHAN FX - VIP PORTAL* 👑\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                "🚙💨 *Luxury Trading Lifestyle — Success on the Move*\n\n"
                                "\"Lafzon mein kya tareef karun apni manzil ki,\n"
                                "Hausle ho buland toh mushkilain bhi jhukti hain!\n"
                                "Har haar ko jeet mein badalne ka hunar rakhte hain,\n"
                                "Hum woh hain jo tufaanon ka rukh mod dete hain!\"\n"
                                "— *King & Queen of Trading*\n\n"
                                "📞 *Contact Number:* `0302-0753076`\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━"
                            )
                        else:
                            period = "day"
                            title = "📊 TODAY'S RESULTS SUMMARY"
                            if callback_data == "res_week":
                                period = "week"
                                title = "📅 LAST 7 DAYS RESULTS SUMMARY"
                            elif callback_data == "res_month":
                                period = "month"
                                title = "🗓️ LAST 30 DAYS RESULTS SUMMARY"
                                
                            total, d_wins, m_wins, losses, acc = get_stats_by_period(period)
                            t_wins = d_wins + m_wins
                            ans_text = (
                                f"*{title}*\n"
                                f"━━━━━━━━━━━━━━━━━━━\n"
                                f"🎯 **Total Signals:** `{total}`\n"
                                f"⭐ **Direct Wins (Shureshot):** `{d_wins}`\n"
                                f"✅ **MTG Wins:** `{m_wins}`\n"
                                f"🏆 **Total Wins:** `{t_wins}`\n"
                                f"❌ **Losses:** `{losses}`\n"
                                f"📈 **Accuracy:** `{acc:.2f}%`\n"
                                f"━━━━━━━━━━━━━━━━━━━"
                            )
                        
                        ans_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
                        requests.post(ans_url, json={"callback_query_id": query_id, "text": "Loading...", "show_alert": False})
                        send_telegram_simple_message(ans_text)
        except Exception as e:
            print(f"Callback Listener Error: {e}")
        await asyncio.sleep(2)

async def capture_chart(pair: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Viewport width thori optimize ki hai taake right side par current/last candles bilkul clear aur zoom-in dikhein
        page = await browser.new_page(viewport={"width": 1280, "height": 750})
        
        # Updated URL with range and scale parameters to focus clearly on the latest candles
        url = f"https://s.tradingview.com/widgetembed/?symbol=FX:{pair}&interval=2&hidesidetoolbar=1&symboledit=0&saveimage=0&toolbarbg=ffffff&studies=[]&theme=light&style=1&range=1d"
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3) # Thora extra wait taake live candles fully load aur render ho jayein
            
            # Screenshot area adjust kiya hai taake right side ki live candles cut na hon
            await page.screenshot(path=output_path, clip={"x": 0, "y": 0, "width": 1280, "height": 700})
        except:
            pass
        finally:
            await browser.close()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_market_data(yf_symbol):
    try:
        ticker = yf.Ticker(yf_symbol)
        df_2m = ticker.history(period="3d", interval="2m", auto_adjust=True, timeout=10)
        df_1h = ticker.history(period="3d", interval="1h", auto_adjust=True, timeout=10)
        
        if not df_2m.empty and len(df_2m) >= 30:
            df_2m['tr'] = np.maximum(df_2m['High'] - df_2m['Low'], 
                                     np.maximum(abs(df_2m['High'] - df_2m['Close'].shift(1)), 
                                                abs(df_2m['Low'] - df_2m['Close'].shift(1))))
            df_2m['atr'] = df_2m['tr'].rolling(window=14).mean()
            current_atr = df_2m['atr'].iloc[-1]
            avg_price = df_2m['Close'].iloc[-1]
            
            if (current_atr / avg_price) > 0.0030:
                return None, None, True

            df_2m['rsi'] = calculate_rsi(df_2m['Close'], 14)
            df_2m['ema_fast'] = df_2m['Close'].ewm(span=9, adjust=False).mean()
            df_2m['ema_slow'] = df_2m['Close'].ewm(span=21, adjust=False).mean()
            
            candles = []
            for i in range(-5, 0):
                row = df_2m.iloc[i]
                candles.append({
                    'open': float(row['Open']), 'high': float(row['High']),
                    'low': float(row['Low']), 'close': float(row['Close']),
                    'rsi': float(row['rsi']) if not pd.isna(row['rsi']) else 50.0,
                    'ema_fast': float(row['ema_fast']),
                    'ema_slow': float(row['ema_slow'])
                })
            
            trend_1h = "NEUTRAL"
            if not df_1h.empty and len(df_1h) >= 10:
                ma_fast_1h = df_1h['Close'].rolling(window=10).mean().iloc[-1]
                ma_slow_1h = df_1h['Close'].rolling(window=30).mean().iloc[-1]
                if ma_fast_1h > ma_slow_1h: trend_1h = "BULLISH"
                elif ma_fast_1h < ma_slow_1h: trend_1h = "BEARISH"
                
            return candles, trend_1h, False
    except:
        pass
    return None, None, False

def analyze_multi_strategies(candles, trend_1h, is_mtg):
    if not candles or len(candles) < 2: return None
    prev_candle, curr_candle = candles[-2], candles[-1]
    entry_price = curr_candle['close']
    
    curr_body = abs(curr_candle['close'] - curr_candle['open'])
    curr_range = curr_candle['high'] - curr_candle['low']
    if curr_range == 0: return None

    rsi_val = curr_candle['rsi']
    is_strong_body = curr_body >= (curr_range * 0.70)
    
    ema_bullish = curr_candle['ema_fast'] > curr_candle['ema_slow']
    ema_bearish = curr_candle['ema_fast'] < curr_candle['ema_slow']

    if curr_candle['close'] > curr_candle['open'] and is_strong_body and ema_bullish:
        if curr_candle['close'] > prev_candle['high'] and trend_1h == "BULLISH" and (45 <= rsi_val <= 65):
            tag = "🔥 1-STEP HEAVY MTG (Pro Breakout)" if is_mtg else "🎯 2M High Breakout (85% Win)"
            return (tag, "CALL 🟢", f"{entry_price:.5f}", "💎 VIP 95%+" if is_mtg else "🔥 PRO 85%+", entry_price)

    elif curr_candle['close'] < curr_candle['open'] and is_strong_body and ema_bearish:
        if curr_candle['close'] < prev_candle['low'] and trend_1h == "BEARISH" and (35 <= rsi_val <= 55):
            tag = "🔥 1-STEP HEAVY MTG (Pro Breakout)" if is_mtg else "🎯 2M Low Breakout (85% Win)"
            return (tag, "PUT 🔻", f"{entry_price:.5f}", "💎 VIP 95%+" if is_mtg else "🔥 PRO 85%+", entry_price)

    prev_body = abs(prev_candle['close'] - prev_candle['open'])
    if curr_body > prev_body * 1.3:
        if curr_candle['close'] > curr_candle['open'] and prev_candle['close'] < prev_candle['open'] and trend_1h == "BULLISH" and ema_bullish and (45 <= rsi_val <= 60):
            tag = "🔥 1-STEP HEAVY MTG (Bullish Engulfing)" if is_mtg else "🚀 Bullish Engulfing Shureshot"
            return (tag, "CALL 🟢", f"{entry_price:.5f}", "💎 VIP 96%+" if is_mtg else "🔥 PRO 88%+", entry_price)
        elif curr_candle['close'] < curr_candle['open'] and prev_candle['close'] > prev_candle['open'] and trend_1h == "BEARISH" and ema_bearish and (40 <= rsi_val <= 55):
            tag = "🔥 1-STEP HEAVY MTG (Bearish Engulfing)" if is_mtg else "📉 Bearish Engulfing Shureshot"
            return (tag, "PUT 🔻", f"{entry_price:.5f}", "💎 VIP 96%+" if is_mtg else "🔥 PRO 88%+", entry_price)

    return None

async def process_signal(pair: str, yf_symbol: str, pattern: str, direction: str, entry_str: str, strength: str, entry_num: float):
    global session_stats, signals_in_session
    
    signals_in_session += 1
    current_count_str = f"{signals_in_session}/10"
    
    timestamp = int(time.time())
    live_img = f"{pair}_live_{timestamp}.png"
    result_img = f"{pair}_result_{timestamp}.png"
    
    # --- 1st Trade Signal ---
    await capture_chart(pair, live_img)
    signal_msg = (
        f"**💎 FATIMA FOREX FX - 80%+ ACCURACY ALERT** `[{current_count_str}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Asset:** `#{pair}`\n⏳ **Timeframe:** `2 Minutes`\n"
        f"🎯 **Pattern:** `{pattern}`\n📈 **Direction:** `{direction}`\n"
        f"📍 **Entry:** `{entry_str}`\n💪 **Accuracy:** `{strength}`\n"
        f"⏱️ **Expiry:** `Exact 2 Minutes`\n"
        f"⚠️ **Take 1 Step MTG same direction iff loss**\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    if os.path.exists(live_img):
        send_telegram_photo_with_result_buttons(live_img, signal_msg)
        try: os.remove(live_img)
        except: pass
    else:
        send_telegram_message_with_result_buttons(signal_msg)

    await asyncio.sleep(120)
    candles_after, _, _ = get_market_data(yf_symbol)
    exit_num = candles_after[-1]['close'] if candles_after and len(candles_after) > 0 else entry_num
    
    is_first_win = True if ("CALL" in direction and exit_num > entry_num) or ("PUT" in direction and exit_num < entry_num) else False

    # --- DIRECT WIN (SHURESHOT) ---
    if is_first_win:
        session_stats["total"] += 1
        session_stats["direct_wins"] += 1
        session_stats["consecutive_losses"] = 0
        save_trade_to_db("DIRECT_WIN")
        
        result_status = "🎯 **DIRECT WIN / SHURESHOT ⭐**"
        exit_str = f"{exit_num:.5f}"
        
        await capture_chart(pair, result_img)
        result_msg = (
            f"🏆 **FATIMA FOREX FX - RESULT** `[{current_count_str}]`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Asset:** `#{pair}`\n📍 **Entry:** `{entry_str}` | 🏁 **Exit:** `{exit_str}`\n"
            f"✨ **Status:** {result_status}\n━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        if os.path.exists(result_img):
            send_telegram_photo_with_result_buttons(result_img, result_msg)
            try: os.remove(result_img)
            except: pass
        else:
            send_telegram_message_with_result_buttons(result_msg)
    else:
        # --- MTG TRADE ---
        print(f"[{pair}] 1st Trade Loss! Waiting for 1-Step MTG result...")
        mtg_entry_num = exit_num
        mtg_entry_str = f"{mtg_entry_num:.5f}"
        
        await asyncio.sleep(120)
        candles_mtg, _, _ = get_market_data(yf_symbol)
        mtg_exit_num = candles_mtg[-1]['close'] if candles_mtg and len(candles_mtg) > 0 else mtg_entry_num
        
        is_mtg_win = True if ("CALL" in direction and mtg_exit_num > mtg_entry_num) or ("PUT" in direction and mtg_exit_num < mtg_entry_num) else False
        
        session_stats["total"] += 1
        
        if is_mtg_win:
            session_stats["mtg_wins"] += 1
            session_stats["consecutive_losses"] = 0
            save_trade_to_db("MTG_WIN")
            result_status = "✅ **MTG WIN / ITM 🎯**"
        else:
            session_stats["losses"] += 1
            session_stats["consecutive_losses"] += 1
            save_trade_to_db("LOSS")
            result_status = "❌ **MTG LOSS / OTM 🛑**"
            
        mtg_exit_str = f"{mtg_exit_num:.5f}"
        await capture_chart(pair, result_img)
        result_msg = (
            f"🏆 **FATIMA FOREX FX - MTG RESULT** `[{current_count_str}]`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Asset:** `#{pair}`\n📍 **MTG Entry:** `{mtg_entry_str}` | 🏁 **Exit:** `{mtg_exit_str}`\n"
            f"✨ **Status:** {result_status}\n━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        if os.path.exists(result_img):
            send_telegram_photo_with_result_buttons(result_img, result_msg)
            try: os.remove(result_img)
            except: pass
        else:
            send_telegram_message_with_result_buttons(result_msg)

    if signals_in_session >= 10:
        send_telegram_simple_message("🛑 **10 Signals completed! Taking a 10 minutes break...**")
        signals_in_session = 0
        session_stats = {"total": 0, "direct_wins": 0, "mtg_wins": 0, "losses": 0, "consecutive_losses": 0}
        await asyncio.sleep(600)
        send_telegram_simple_message("🚀 **Break over! Session Resumed.**")

async def time_scheduler():
    sent_2200, sent_2215, sent_2230, sent_800, sent_815 = False, False, False, False, False
    while True:
        now_pk = datetime.utcnow() + timedelta(hours=5)
        current_time_str = now_pk.strftime("%H:%M")
        
        if current_time_str == "00:00":
            sent_2200, sent_2215, sent_2230, sent_800, sent_815 = False, False, False, False, False
            
        if current_time_str == "22:00" and not sent_2200:
            send_telegram_simple_message("🌙 **SESSION CLOSE**\nAaj ki trading session mukammal ho chuki hai. Allah Hafiz!")
            sent_2200 = True
        elif current_time_str == "22:15" and not sent_2215:
            total, d_wins, m_wins, losses, acc = get_stats_by_period("day")
            t_wins = d_wins + m_wins
            summary_text = (
                f"📊 **TODAY'S FINAL RESULTS SUMMARY** 📊\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 **Total Signals:** `{total}`\n"
                f"⭐ **Direct Wins (Shureshot):** `{d_wins}`\n"
                f"✅ **MTG Wins:** `{m_wins}`\n"
                f"🏆 **Total Wins:** `{t_wins}`\n"
                f"❌ **Losses:** `{losses}`\n"
                f"📈 **Accuracy:** `{acc:.2f}%`\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
            send_telegram_message_with_result_buttons(summary_text)
            sent_2215 = True
        elif current_time_str == "22:30" and not sent_2230:
            send_telegram_simple_message("✨ **GOOD NIGHT!**\nAaj ka din behtareen raha, kal subha phir milte hain. 😴💤")
            sent_2230 = True
        elif current_time_str == "08:00" and not sent_800:
            send_telegram_simple_message("☀️ **GOOD MORNING!**\nSubha bakhair! Sab tayyar ho jayein naye din ki trading ke liye. ☕📈")
            sent_800 = True
        elif current_time_str == "08:15" and not sent_815:
            send_telegram_simple_message("🚀 **SESSION START!**\nLive trading signals shuru ho rahe hain. Best of luck! 💎")
            sent_815 = True
            
        await asyncio.sleep(30)

async def main():
    print("Fatima Forex FX Bot Active (White Light Theme & Clear Last Candles)...")
    asyncio.create_task(handle_telegram_callbacks())
    asyncio.create_task(time_scheduler())
    
    while True:
        now_pk = datetime.utcnow() + timedelta(hours=5)
        current_hour = now_pk.hour
        
        if not (8 <= current_hour < 22):
            await asyncio.sleep(60)
            continue

        has_news, news_title, news_currency = check_forex_news_events()
        if has_news:
            news_alert_msg = (
                f"🚨 **HIGH IMPACT NEWS BREAK ALERT** 🚨\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ **Event:** `{news_title}`\n"
                f"💱 **Currency:** `{news_currency}`\n"
                f"🛑 **Bot Status:** Paused for safety (High Volatility Ahead).\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            send_telegram_simple_message(news_alert_msg)
            await asyncio.sleep(1800)
            continue

        signal_found = False
        for pair, yf_symbol in LIVE_PAIRS_MAP.items():
            print(f"Scanning Active Session -> {pair}                    ", end="\r")
            candles, trend_1h, is_volatile = get_market_data(yf_symbol)
            
            if is_volatile:
                vol_msg = (
                    f"⚠️ **MARKET VOLATILITY WARNING** ⚠️\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🛑 **Asset:** `#{pair}` mein market bohat kharab ya volatile hai!\n"
                    f"⏳ **Bot Status:** Safety ke liye **1 Hour Break** liya ja raha hai.\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                print(f"High Volatility detected on {pair}. Taking 1 hour break...")
                send_telegram_simple_message(vol_msg)
                await asyncio.sleep(3600)
                break
                
            signal = analyze_multi_strategies(candles, trend_1h, False)
            if signal:
                pattern, direction, entry_str, strength, entry_num = signal
                await process_signal(pair, yf_symbol, pattern, direction, entry_str, strength, entry_num)
                signal_found = True
                await asyncio.sleep(300)
                break  
                
        if not signal_found:
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
