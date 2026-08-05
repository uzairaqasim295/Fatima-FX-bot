import asyncio
import os
import json
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ==========================================
# ⚙️ FLEXIBLE STRATEGY BOT (LOOSE CONDITIONS)
# ==========================================
TELEGRAM_BOT_TOKEN = "8758950547:AAFRBa1f31fZ0lJciyI05mcoCZYv16bf5hs"
CHANNEL_CHAT_ID = "@Binary_Signals_Live_Malik"
HISTORY_FILE = "trading_history.json"
SCREENSHOT_FILE = "trade_result_chart.png"

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

session_stats = {"total": 0, "wins": 0, "losses": 0}
signals_in_session = 0
is_mtg_pending = False
pending_pair = None
pending_direction = None

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

def is_allowed_time_session():
    now_utc = datetime.utcnow()
    pk_time = now_utc + timedelta(hours=5)
    current_hour = pk_time.hour
    if 10 <= current_hour < 21:
        return True
    return False

def get_inline_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📊 Day Results", "callback_data": "res_day"},
                {"text": "📅 Week Results", "callback_data": "res_week"}
            ],
            [
                {"text": "🗓️ Month Results", "callback_data": "res_month"},
                {"text": "📋 Active Pairs Status", "callback_data": "res_pairs"}
            ],
            [
                {"text": "👑 Admin Portal", "callback_data": "res_admin"}
            ]
        ]
    }

def send_telegram_message_with_result_buttons(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHANNEL_CHAT_ID, 
        'text': text, 
        'parse_mode': 'Markdown',
        'reply_markup': json.dumps(get_inline_keyboard())
    }
    try:
        response = requests.post(url, data=payload, timeout=20)
        if response.status_code == 200:
            return response.json().get('result', {}).get('message_id')
    except:
        pass
    return None

def edit_telegram_message_with_result_buttons(message_id, text):
    if not message_id: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        'chat_id': CHANNEL_CHAT_ID,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'Markdown',
        'reply_markup': json.dumps(get_inline_keyboard())
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def send_telegram_photo_with_caption(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {
                'chat_id': CHANNEL_CHAT_ID,
                'caption': caption,
                'parse_mode': 'Markdown',
                'reply_markup': json.dumps(get_inline_keyboard())
            }
            files = {'photo': photo}
            requests.post(url, data=payload, files=files, timeout=30)
    except Exception as e:
        print(f"Photo error: {e}")

def send_telegram_simple_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHANNEL_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload, timeout=20)
    except:
        pass

def generate_trade_chart(df, pair, entry_price, exit_price, is_win):
    try:
        plt.figure(figsize=(8, 4))
        plt.plot(df.index, df['Close'], label='Price', color='#00d2ff', linewidth=2)
        plt.axhline(y=entry_price, color='orange', linestyle='--', label=f'Entry: {entry_price:.5f}')
        plt.axhline(y=exit_price, color='green' if is_win else 'red', linestyle='-', label=f'Exit: {exit_price:.5f}')
        
        plt.title(f"Fatima Forex FX - #{pair} Result Chart", color='white', fontsize=12)
        plt.legend(loc='upper left', facecolor='#222', edgecolor='none', labelcolor='white')
        plt.grid(True, linestyle=':', alpha=0.3)
        
        ax = plt.gca()
        ax.set_facecolor('#111827')
        plt.gcf().patch.set_facecolor('#1f2937')
        ax.tick_params(colors='white')
        
        plt.tight_layout()
        plt.savefig(SCREENSHOT_FILE, dpi=150, facecolor=plt.gcf().get_facecolor(), edgecolor='none')
        plt.close()
        return True
    except:
        return False

def get_all_pairs_status_text():
    status_lines = ["📋 *LIVE PAIRS & CONDITIONS STATUS* 📋\n━━━━━━━━━━━━━━━━━━━━━━━━━"]
    for pair, yf_symbol in LIVE_PAIRS_MAP.items():
        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period="1d", interval="1m", auto_adjust=True, timeout=5)
            if not df.empty and len(df) >= 10:
                curr_price = float(df.iloc[-1]['Close'])
                prev_price = float(df.iloc[-2]['Close'])
                sup = float(df['Low'].tail(15).min())
                res = float(df['High'].tail(15).max())
                
                trend = "🟢 BULLISH" if curr_price > prev_price else "🔴 BEARISH"
                status_lines.append(f"• `#{pair}` ➔ Price: `{curr_price:.5f}` | {trend}\n  Support: `{sup:.5f}` | Res: `{res:.5f}`")
            else:
                status_lines.append(f"• `#{pair}` ➔ `Syncing...`")
        except:
            status_lines.append(f"• `#{pair}` ➔ `Checking...`")
        
    status_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(status_lines)

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
                        elif callback_data == "res_pairs":
                            ans_text = get_all_pairs_status_text()
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

def get_market_data(yf_symbol):
    try:
        ticker = yf.Ticker(yf_symbol)
        df_1m = ticker.history(period="1d", interval="1m", auto_adjust=True, timeout=10)
        if not df_1m.empty and len(df_1m) >= 10:
            return df_1m
    except:
        pass
    return None

def analyze_support_resistance_loose(df_1m):
    if df_1m is None or len(df_1m) < 15: return None
    
    # Range ko loose kar diya hai taake jaldi signal mil sakein
    support_level = df_1m['Low'].tail(15).min()
    resistance_level = df_1m['High'].tail(15).max()
    
    curr = df_1m.iloc[-1]
    entry_price = float(curr['Close'])
    
    # 35% tak ka gap allow kiya hai
    near_support = abs(entry_price - support_level) <= (resistance_level - support_level) * 0.35
    near_resistance = abs(entry_price - resistance_level) <= (resistance_level - support_level) * 0.35
    
    is_green = curr['Close'] > curr['Open']
    is_red = curr['Close'] < curr['Open']
    
    if near_support and is_green:
        return "CALL 🟢", entry_price, "Support Zone Rebound"
    elif near_resistance and is_red:
        return "PUT 🔻", entry_price, "Resistance Zone Rejection"
        
    return None

async def execute_trade(pair, yf_symbol, direction, is_mtg=False):
    global session_stats, signals_in_session, is_mtg_pending, pending_pair, pending_direction
    
    df_pre = get_market_data(yf_symbol)
    if df_pre is None: return
    entry_num = float(df_pre.iloc[-1]['Close'])
    entry_str = f"{entry_num:.5f}"
    
    title = "⚡ 1-STEP HEAVY MTG" if is_mtg else "💎 FATIMA FOREX FX - 1M SIGNAL"
    base_msg = (
        f"**{title}**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Asset:** `#{pair}`\n⏳ **Timeframe:** `1 Minute`\n"
        f"📈 **Direction:** `{direction}`\n"
        f"📍 **Entry Price:** `{entry_str}`\n"
    )
    
    full_msg = base_msg + f"⏱️ **Timer:** `⏳ 60 Seconds Left...`\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    msg_id = send_telegram_message_with_result_buttons(full_msg)
    
    for rem in range(50, 0, -10):
        await asyncio.sleep(10)
        up_msg = base_msg + f"⏱️ **Timer:** `⏳ {rem} Seconds Left...`\n━━━━━━━━━━━━━━━━━━━━━━━━━"
        edit_telegram_message_with_result_buttons(msg_id, up_msg)
        
    await asyncio.sleep(10)
    
    df_post = get_market_data(yf_symbol)
    exit_num = float(df_post.iloc[-1]['Close']) if df_post is not None else entry_num
    exit_str = f"{exit_num:.5f}"
    
    is_win = True if ("CALL" in direction and exit_num > entry_num) or ("PUT" in direction and exit_num < entry_num) else False
    
    if not is_mtg:
        if is_win:
            session_stats["total"] += 1
            session_stats["wins"] += 1
            signals_in_session += 1
            is_mtg_pending = False
            save_trade_to_db(True)
            res_status = "✅ **WIN / ITM 🎯**"
        else:
            is_mtg_pending = True
            pending_pair = pair
            pending_direction = direction
            res_status = "⚠️ **LOSS ➔ 1-Step MTG Triggered (Same Direction)...**"
    else:
        signals_in_session += 1
        session_stats["total"] += 1
        if is_win:
            session_stats["wins"] += 1
            is_mtg_pending = False
            save_trade_to_db(True)
            res_status = "✅ **MTG WIN / ITM 🎯**"
        else:
            session_stats["losses"] += 1
            is_mtg_pending = False
            save_trade_to_db(False)
            res_status = "❌ **MTG LOSS / OTM 🛑**"
            
    res_msg = (
        f"🏆 **FATIMA FOREX FX - RESULT** 🏆\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Asset:** `#{pair}`\n📍 **Entry:** `{entry_str}` | 🏁 **Exit:** `{exit_str}`\n"
        f"✨ **Status:** {res_status}\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Progress* ➔ Signal: `{signals_in_session}`/10 | Wins: `{session_stats['wins']}` | Losses: `{session_stats['losses']}`"
    )
    
    if df_post is not None:
        chart_created = generate_trade_chart(df_post, pair, entry_num, exit_num, is_win)
        if chart_created and os.path.exists(SCREENSHOT_FILE):
            send_telegram_photo_with_caption(SCREENSHOT_FILE, res_msg)
        else:
            send_telegram_message_with_result_buttons(res_msg)
    else:
            send_telegram_message_with_result_buttons(res_msg)

    if signals_in_session >= 10:
        tot, w, l = session_stats["total"], session_stats["wins"], session_stats["losses"]
        acc = (w / tot * 100) if tot > 0 else 0
        summary = (
            f"🎯 **SESSION SUMMARY** 🎯\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **Total:** `{signals_in_session}` | ✅ **Wins:** `{w}` | ❌ **Losses:** `{l}`\n"
            f"📈 **Accuracy:** `{acc:.2f}%`\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 **Taking a 5 minutes break!**"
        )
        send_telegram_simple_message(summary)
        signals_in_session = 0
        session_stats = {"total": 0, "wins": 0, "losses": 0}
        await asyncio.sleep(300)
        send_telegram_simple_message("🚀 **SESSION RESUMED!**")

async def main():
    global is_mtg_pending, pending_pair, pending_direction
    print("Bot Active with Flexible Strategy...")
    asyncio.create_task(handle_telegram_callbacks())
    
    while True:
        try:
            if not is_allowed_time_session():
                await asyncio.sleep(60)
                continue
                
            if is_mtg_pending and pending_pair:
                yf_sym = LIVE_PAIRS_MAP.get(pending_pair)
                await execute_trade(pending_pair, yf_sym, pending_direction, is_mtg=True)
                is_mtg_pending = False
                pending_pair = None
                pending_direction = None
                await asyncio.sleep(20)
                continue

            signal_found = False
            for pair, yf_symbol in LIVE_PAIRS_MAP.items():
                df_1m = get_market_data(yf_symbol)
                res = analyze_support_resistance_loose(df_1m)
                
                if res:
                    direction, _, _ = res
                    await execute_trade(pair, yf_symbol, direction, is_mtg=False)
                    signal_found = True
                    await asyncio.sleep(15)
                    break
                    
            if not signal_found:
                await asyncio.sleep(10)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
