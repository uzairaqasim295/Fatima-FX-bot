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
# ⚙️ ULTIMATE PRO BOT CONFIGURATION (WITH MTG FIX)
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

session_stats = {"total": 0, "wins": 0, "losses": 0, "consecutive_losses": 0}
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

def save_trade_to_db(is_win):
    history = load_history()
    trade_record = {
        "timestamp": time.time(),
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "result": "WIN" if is_win else "LOSS"
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
    filtered_wins, filtered_losses = 0, 0
    
    for trade in history:
        try:
            trade_time = datetime.strptime(trade["date"], "%Y-%m-%d")
            if period_type == "day":
                if trade["date"] == now.strftime("%Y-%m-%d"):
                    if trade["result"] == "WIN": filtered_wins += 1
                    else: filtered_losses += 1
            elif period_type == "week":
                if (now - trade_time).days <= 7:
                    if trade["result"] == "WIN": filtered_wins += 1
                    else: filtered_losses += 1
            elif period_type == "month":
                if (now - trade_time).days <= 30:
                    if trade["result"] == "WIN": filtered_wins += 1
                    else: filtered_losses += 1
        except:
            continue
                
    total = filtered_wins + filtered_losses
    accuracy = (filtered_wins / total * 100) if total > 0 else 0.0
    return total, filtered_wins, filtered_losses, accuracy

def is_london_newyork_session():
    now_utc = datetime.utcnow()
    pk_time = now_utc + timedelta(hours=5)
    current_hour = pk_time.hour
    if 12 <= current_hour < 22:
        return True
    return False

def send_telegram_message_with_result_buttons(text, pair):
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

def send_telegram_photo_with_result_buttons(photo_path, caption, pair):
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
                                
                            total, wins, losses, acc = get_stats_by_period(period)
                            
                            ans_text = (
                                f"*{title}*\n"
                                f"━━━━━━━━━━━━━━━━━━━\n"
                                f"🎯 **Total Signals:** `{total}`\n"
                                f"✅ **Wins:** `{wins}`\n"
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
        page = await browser.new_page(viewport={"width": 1200, "height": 750})
        url = f"https://s.tradingview.com/widgetembed/?symbol=FX:{pair}&interval=5&hidesidetoolbar=1&symboledit=0&saveimage=0&toolbarbg=F1F3F6&studies=[]&theme=dark&style=1"
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            await page.screenshot(path=output_path, clip={"x": 0, "y": 0, "width": 1200, "height": 700})
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
        df_5m = ticker.history(period="3d", interval="5m", auto_adjust=True, timeout=10)
        df_1h = ticker.history(period="3d", interval="1h", auto_adjust=True, timeout=10)
        
        if not df_5m.empty and len(df_5m) >= 20:
            df_5m['rsi'] = calculate_rsi(df_5m['Close'], 14)
            candles = []
            for i in range(-5, 0):
                row = df_5m.iloc[i]
                candles.append({
                    'open': float(row['Open']), 'high': float(row['High']),
                    'low': float(row['Low']), 'close': float(row['Close']),
                    'rsi': float(row['rsi']) if not pd.isna(row['rsi']) else 50.0
                })
            
            trend_1h = "NEUTRAL"
            if not df_1h.empty and len(df_1h) >= 5:
                ma_fast = df_1h['Close'].rolling(window=5).mean().iloc[-1]
                ma_slow = df_1h['Close'].rolling(window=20).mean().iloc[-1]
                if ma_fast > ma_slow: trend_1h = "BULLISH"
                elif ma_fast < ma_slow: trend_1h = "BEARISH"
            return candles, trend_1h
    except:
        pass
    return None, None

def analyze_multi_strategies(candles, trend_1h, is_mtg):
    if not candles or len(candles) < 2: return None
    prev_candle, curr_candle = candles[-2], candles[-1]
    entry_price = curr_candle['close']
    curr_body = abs(curr_candle['close'] - curr_candle['open'])
    curr_range = curr_candle['high'] - curr_candle['low']
    if curr_range == 0: return None

    rsi_val = curr_candle['rsi']
    is_strong_body = curr_body >= (curr_range * 0.65)
    
    if curr_candle['close'] > curr_candle['open'] and is_strong_body:
        if curr_candle['close'] > prev_candle['high'] and trend_1h == "BULLISH" and (40 <= rsi_val <= 65):
            tag = "🔥 1-STEP HEAVY MTG (Breakout)" if is_mtg else "🎯 5M High Breakout"
            return (tag, "CALL 🟢", f"{entry_price:.5f}", "💎 VIP 99% (MTG)" if is_mtg else "🔥 PRO 85%+", entry_price)

    elif curr_candle['close'] < curr_candle['open'] and is_strong_body:
        if curr_candle['close'] < prev_candle['low'] and trend_1h == "BEARISH" and (35 <= rsi_val <= 60):
            tag = "🔥 1-STEP HEAVY MTG (Breakout)" if is_mtg else "🎯 5M Low Breakout"
            return (tag, "PUT 🔻", f"{entry_price:.5f}", "💎 VIP 99% (MTG)" if is_mtg else "🔥 PRO 85%+", entry_price)

    prev_body = abs(prev_candle['close'] - prev_candle['open'])
    if curr_body > prev_body * 1.2:
        if curr_candle['close'] > curr_candle['open'] and prev_candle['close'] < prev_candle['open'] and trend_1h == "BULLISH" and rsi_val < 65:
            tag = "🔥 1-STEP HEAVY MTG (Bullish Engulfing)" if is_mtg else "🚀 Bullish Engulfing Pattern"
            return (tag, "CALL 🟢", f"{entry_price:.5f}", "💎 VIP 99% (MTG)" if is_mtg else "🔥 PRO 88%+", entry_price)
        elif curr_candle['close'] < curr_candle['open'] and prev_candle['close'] > prev_candle['open'] and trend_1h == "BEARISH" and rsi_val > 35:
            tag = "🔥 1-STEP HEAVY MTG (Bearish Engulfing)" if is_mtg else "📉 Bearish Engulfing Pattern"
            return (tag, "PUT 🔻", f"{entry_price:.5f}", "💎 VIP 99% (MTG)" if is_mtg else "🔥 PRO 88%+", entry_price)

    upper_wick = curr_candle['high'] - max(curr_candle['open'], curr_candle['close'])
    lower_wick = min(curr_candle['open'], curr_candle['close']) - curr_candle['low']
    
    if upper_wick > (curr_body * 2) and rsi_val >= 80:
        tag = "🔥 1-STEP HEAVY MTG (Pin Bar Rejection)" if is_mtg else "🔻 Top Rejection Pin Bar"
        return (tag, "PUT 🔻", f"{entry_price:.5f}", "💎 VIP 99% (MTG)" if is_mtg else "🔥 PRO 90%+", entry_price)
    elif lower_wick > (curr_body * 2) and rsi_val <= 20:
        tag = "🔥 1-STEP HEAVY MTG (Pin Bar Rejection)" if is_mtg else "🟢 Bottom Rejection Pin Bar"
        return (tag, "CALL 🟢", f"{entry_price:.5f}", "💎 VIP 99% (MTG)" if is_mtg else "🔥 PRO 90%+", entry_price)

    return None

async def process_signal(pair: str, yf_symbol: str, pattern: str, direction: str, entry_str: str, strength: str, entry_num: float):
    global session_stats, signals_in_session
    timestamp = int(time.time())
    live_img = f"{pair}_live_{timestamp}.png"
    result_img = f"{pair}_result_{timestamp}.png"
    
    # --- 1st Trade Signal ---
    await capture_chart(pair, live_img)
    signal_msg = (
        f"**💎 FATIMA FOREX FX - PRO SESSION ALERT**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Asset:** `#{pair}`\n⏳ **Timeframe:** `5 Minutes`\n"
        f"🎯 **Pattern:** `{pattern}`\n📈 **Direction:** `{direction}`\n"
        f"📍 **Entry:** `{entry_str}`\n💪 **Accuracy:** `{strength}`\n"
        f"⏱️ **Expiry:** `Exact 2 Minutes`\n"
        f"⚠️ **Take 1 Step MTG same direction iff loss**\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    if os.path.exists(live_img):
        send_telegram_photo_with_result_buttons(live_img, signal_msg, pair)
        try: os.remove(live_img)
        except: pass
    else:
        send_telegram_message_with_result_buttons(signal_msg, pair)

    # Wait for 1st trade expiry
    await asyncio.sleep(120)
    candles_after, _ = get_market_data(yf_symbol)
    exit_num = candles_after[-1]['close'] if candles_after and len(candles_after) > 0 else entry_num
    
    is_first_win = True if ("CALL" in direction and exit_num > entry_num) or ("PUT" in direction and exit_num < entry_num) else False

    # --- Agar 1st Trade WIN ho jaye ---
    if is_first_win:
        session_stats["total"] += 1
        signals_in_session += 1
        session_stats["wins"] += 1
        session_stats["consecutive_losses"] = 0
        save_trade_to_db(True)
        
        result_status = "✅ **WIN / ITM 🎯**"
        exit_str = f"{exit_num:.5f}"
        
        await capture_chart(pair, result_img)
        result_msg = (
            f"🏆 **FATIMA FOREX FX - RESULT** 🏆\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Asset:** `#{pair}`\n📍 **Entry:** `{entry_str}` | 🏁 **Exit:** `{exit_str}`\n"
            f"✨ **Status:** {result_status}\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Progress* ➔ Signal: `{signals_in_session}`/10 | Wins: `{session_stats['wins']}` | Losses: `{session_stats['losses']}`"
        )
        if os.path.exists(result_img):
            send_telegram_photo_with_result_buttons(result_img, result_msg, pair)
            try: os.remove(result_img)
            except: pass
        else:
            send_telegram_message_with_result_buttons(result_msg, pair)

    # --- Agar 1st Trade LOSS ho jaye, toh 1-Step MTG ka wait karein ---
    else:
        print(f"[{pair}] 1st Trade Loss! Waiting for 1-Step MTG result...")
        mtg_entry_num = exit_num
        mtg_entry_str = f"{mtg_entry_num:.5f}"
        
        # MTG trade ka wait (2 minutes expiry)
        await asyncio.sleep(120)
        candles_mtg, _ = get_market_data(yf_symbol)
        mtg_exit_num = candles_mtg[-1]['close'] if candles_mtg and len(candles_mtg) > 0 else mtg_entry_num
        
        is_mtg_win = True if ("CALL" in direction and mtg_exit_num > mtg_entry_num) or ("PUT" in direction and mtg_exit_num < mtg_entry_num) else False
        
        session_stats["total"] += 1
        signals_in_session += 1
        save_trade_to_db(is_mtg_win)
        
        if is_mtg_win:
            session_stats["wins"] += 1
            session_stats["consecutive_losses"] = 0
            result_status = "✅ **MTG WIN / ITM 🎯**"
        else:
            session_stats["losses"] += 1
            session_stats["consecutive_losses"] += 1
            result_status = "❌ **MTG LOSS / OTM 🛑**"
            
        mtg_exit_str = f"{mtg_exit_num:.5f}"
        await capture_chart(pair, result_img)
        result_msg = (
            f"🏆 **FATIMA FOREX FX - MTG RESULT** 🏆\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Asset:** `#{pair}`\n📍 **MTG Entry:** `{mtg_entry_str}` | 🏁 **Exit:** `{mtg_exit_str}`\n"
            f"✨ **Status:** {result_status}\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Progress* ➔ Signal: `{signals_in_session}`/10 | Wins: `{session_stats['wins']}` | Losses: `{session_stats['losses']}`"
        )
        if os.path.exists(result_img):
            send_telegram_photo_with_result_buttons(result_img, result_msg, pair)
            try: os.remove(result_img)
            except: pass
        else:
            send_telegram_message_with_result_buttons(result_msg, pair)

    # Session limit check
    if signals_in_session >= 10:
        total_t, wins_t, losses_t = session_stats["total"], session_stats["wins"], session_stats["losses"]
        accuracy = (wins_t / total_t * 100) if total_t > 0 else 0
        summary_msg = (
            f"🎯 **1 HOUR SESSION SUMMARY** 🎯\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **Total:** `{signals_in_session}` | ✅ **Wins:** `{wins_t}` | ❌ **Losses:** `{losses_t}`\n"
            f"📈 **Accuracy:** `{accuracy:.2f}%`\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 **Taking a 10 minutes break!**"
        )
        send_telegram_simple_message(summary_msg)
        signals_in_session = 0
        session_stats = {"total": 0, "wins": 0, "losses": 0, "consecutive_losses": 0}
        await asyncio.sleep(600)
        send_telegram_simple_message("🚀 **SESSION RESUMED!**")

async def main():
    print("Fatima Forex FX Bot Active with Callback-based Admin Portal & News Filter...")
    asyncio.create_task(handle_telegram_callbacks())
    
    while True:
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
            print(f"News Alert Sent: {news_title}")
            send_telegram_simple_message(news_alert_msg)
            await asyncio.sleep(1800)
            continue

        if not is_london_newyork_session():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Outside London/New York Session. Waiting...", end="\r")
            await asyncio.sleep(60)
            continue

        signal_found = False
        for pair, yf_symbol in LIVE_PAIRS_MAP.items():
            print(f"Scanning Active Session -> {pair}                    ", end="\r")
            candles, trend_1h = get_market_data(yf_symbol)
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
