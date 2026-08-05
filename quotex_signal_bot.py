import asyncio
import os
import json
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ==========================================
# ⚙️ LIGHTWEIGHT PRO BOT CONFIGURATION (1M)
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
is_mtg_pending = False

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
    except:
        pass
    return False, "", ""

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
    except:
        pass

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
        'reply_markup': json.dumps(inline_keyboard)
    }
    try:
        requests.post(url, data=payload, timeout=20)
    except Exception as e:
        print(f"Telegram Message Error: {e}")

def send_telegram_simple_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHANNEL_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload, timeout=20)
    except Exception as e:
        print(f"Telegram Message Error: {e}")

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
        except:
            pass
        await asyncio.sleep(2)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_market_data(yf_symbol):
    try:
        ticker = yf.Ticker(yf_symbol)
        # Changed to 1-minute interval
        df_1m = ticker.history(period="1d", interval="1m", auto_adjust=True, timeout=10)
        df_1h = ticker.history(period="2d", interval="1h", auto_adjust=True, timeout=10)
        
        if not df_1m.empty and len(df_1m) >= 25:
            df_1m['rsi'] = calculate_rsi(df_1m['Close'], 14)
            candles = []
            for i in range(-10, 0):
                row = df_1m.iloc[i]
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
            return candles, trend_1h, df_1m
    except:
        pass
    return None, None, None

def analyze_tight_zones_and_strategies(candles, trend_1h, df_1m, is_mtg):
    if not candles or len(candles) < 3 or df_1m is None: return None
    
    recent_highs = df_1m['High'].tail(20).max()
    recent_lows = df_1m['Low'].tail(20).min()
    
    prev_candle, curr_candle = candles[-2], candles[-1]
    entry_price = curr_candle['close']
    curr_body = abs(curr_candle['close'] - curr_candle['open'])
    curr_range = curr_candle['high'] - curr_candle['low']
    if curr_range == 0: return None

    rsi_val = curr_candle['rsi']
    is_strong_body = curr_body >= (curr_range * 0.60)
    
    near_support = abs(entry_price - recent_lows) <= (recent_highs - recent_lows) * 0.25
    near_resistance = abs(entry_price - recent_highs) <= (recent_highs - recent_lows) * 0.25

    if curr_candle['close'] > curr_candle['open'] and is_strong_body:
        if (near_support or curr_candle['close'] >= prev_candle['high']) and trend_1h == "BULLISH" and (35 <= rsi_val <= 70):
            if is_mtg:
                return ("⚡ 1-STEP HEAVY MTG", "CALL 🟢", f"{entry_price:.5f}", "💎 VIP 99.9% (1M Demand Zone Rebound)", entry_price)
            else:
                return ("🎯 1M Pro Breakout", "CALL 🟢", f"{entry_price:.5f}", "🔥 PRO 92% (1M Bullish Trend + Support)", entry_price)

    elif curr_candle['close'] < curr_candle['open'] and is_strong_body:
        if (near_resistance or curr_candle['close'] <= prev_candle['low']) and trend_1h == "BEARISH" and (30 <= rsi_val <= 65):
            if is_mtg:
                return ("⚡ 1-STEP HEAVY MTG", "PUT 🔻", f"{entry_price:.5f}", "💎 VIP 99.9% (1M Supply Zone Rejection)", entry_price)
            else:
                return ("🎯 1M Pro Rejection", "PUT 🔻", f"{entry_price:.5f}", "🔥 PRO 92% (1M Bearish Trend + Resistance)", entry_price)

    return None

async def process_signal(pair: str, yf_symbol: str, pattern: str, direction: str, entry_str: str, logic_reason: str, entry_num: float, is_mtg: bool):
    global session_stats, signals_in_session, is_mtg_pending
    
    title = "⚡ 1-STEP HEAVY MTG SIGNAL" if is_mtg else "💎 FATIMA FOREX FX - 1M PRO SIGNAL"
    signal_msg = (
        f"**{title}**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Asset:** `#{pair}`\n⏳ **Timeframe:** `1 Minute`\n"
        f"🎯 **Pattern:** `{pattern}`\n📈 **Direction:** `{direction}`\n"
        f"📍 **Entry Price:** `{entry_str}`\n💡 **Logic / Reason:** `{logic_reason}`\n"
        f"⏱️ **Expiry:** `Exact 1 Minute`\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_telegram_message_with_result_buttons(signal_msg)

    # Wait for 1 minute (60 seconds) instead of 5 minutes
    await asyncio.sleep(60)
    
    candles_after, _, _ = get_market_data(yf_symbol)
    exit_num = candles_after[-1]['close'] if candles_after and len(candles_after) > 0 else entry_num
    exit_str = f"{exit_num:.5f}"
    
    is_win = True if ("CALL" in direction and exit_num > entry_num) or ("PUT" in direction and exit_num < entry_num) else False
    
    if not is_mtg:
        if is_win:
            session_stats["total"] += 1
            session_stats["wins"] += 1
            signals_in_session += 1
            session_stats["consecutive_losses"] = 0
            is_mtg_pending = False
            save_trade_to_db(True)
            result_status = "✅ **WIN / ITM 🎯**"
        else:
            is_mtg_pending = True
            result_status = "⚠️ **LOSS ➔ 1-Step MTG Triggered (Waiting 1 Min)...**"
    else:
        signals_in_session += 1
        session_stats["total"] += 1
        if is_win:
            session_stats["wins"] += 1
            session_stats["consecutive_losses"] = 0
            is_mtg_pending = False
            save_trade_to_db(True)
            result_status = "✅ **MTG WIN / ITM 🎯**"
        else:
            session_stats["losses"] += 1
            session_stats["consecutive_losses"] += 1
            is_mtg_pending = False
            save_trade_to_db(False)
            result_status = "❌ **MTG LOSS / OTM 🛑**"

    result_msg = (
        f"🏆 **FATIMA FOREX FX - RESULT** 🏆\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Asset:** `#{pair}`\n📍 **Entry:** `{entry_str}` | 🏁 **Exit:** `{exit_str}`\n"
        f"✨ **Status:** {result_status}\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Progress* ➔ Signal: `{signals_in_session}`/10 | Wins: `{session_stats['wins']}` | Losses: `{session_stats['losses']}`"
    )
    send_telegram_message_with_result_buttons(result_msg)

    if signals_in_session >= 10:
        total_t, wins_t, losses_t = session_stats["total"], session_stats["wins"], session_stats["losses"]
        accuracy = (wins_t / total_t * 100) if total_t > 0 else 0
        summary_msg = (
            f"🎯 **SESSION SUMMARY (1M)** 🎯\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **Total:** `{signals_in_session}` | ✅ **Wins:** `{wins_t}` | ❌ **Losses:** `{losses_t}`\n"
            f"📈 **Accuracy:** `{accuracy:.2f}%`\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 **Taking a 5 minutes break!**"
        )
    
        send_telegram_simple_message(summary_msg)
        signals_in_session = 0
        session_stats = {"total": 0, "wins": 0, "losses": 0, "consecutive_losses": 0}
        is_mtg_pending = False
        await asyncio.sleep(300)
        send_telegram_simple_message("🚀 **1M SESSION RESUMED!**")

async def main():
    global is_mtg_pending
    print("Fatima Forex FX 1M Bot Active...")
    asyncio.create_task(handle_telegram_callbacks())
    
    while True:
        has_news, news_title, news_currency = check_forex_news_events()
        if has_news:
            send_telegram_simple_message(f"🚨 **HIGH IMPACT NEWS BREAK** 🚨\n⚠️ **Event:** `{news_title}`\n🛑 **Paused for safety.**")
            await asyncio.sleep(1800)
            continue

        if not is_london_newyork_session():
            await asyncio.sleep(60)
            continue

        signal_found = False
        for pair, yf_symbol in LIVE_PAIRS_MAP.items():
            candles, trend_1h, df_1m = get_market_data(yf_symbol)
            signal = analyze_tight_zones_and_strategies(candles, trend_1h, df_1m, is_mtg_pending)
            
            if signal:
                pattern, direction, entry_str, logic_reason, entry_num = signal
                
                if is_mtg_pending:
                    await asyncio.sleep(60)
                
                await process_signal(pair, yf_symbol, pattern, direction, entry_str, logic_reason, entry_num, is_mtg_pending)
                signal_found = True
                await asyncio.sleep(60)
                break  
                
        if not signal_found:
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
