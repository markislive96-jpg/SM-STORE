import asyncio
import logging
import random
import requests
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==========================================
# CONFIGURATION (Yahan apni details dalo)
# ==========================================
BOT_TOKEN = "9014327151:AAHzrXEqqF9HY6CDmpdwnuz3N3qsYt-r1Qw"
FIREBASE_URL = "https://tumhara-baap-default-rtdb.firebaseio.com" # End mein / mat lagana
FAM_API_KEY = "fam_77567c5053f8e96c08aab9f1d5670d4e0df13a5c"

# FamGateway URL (Agar unka alag ho toh yahan change karein)
FAM_API_URL = "https://api.famgateway.in" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==========================================
# FIREBASE REST API HELPERS
# ==========================================
def get_db(path):
    try:
        res = requests.get(f"{FIREBASE_URL}/{path}.json", timeout=10)
        return res.json()
    except Exception as e:
        print(f"DB Read Error: {e}")
        return None

def set_db(path, data):
    try:
        requests.put(f"{FIREBASE_URL}/{path}.json", json=data, timeout=10)
    except Exception as e:
        print(f"DB Write Error: {e}")

def update_db(path, data):
    try:
        requests.patch(f"{FIREBASE_URL}/{path}.json", json=data, timeout=10)
    except Exception as e:
        print(f"DB Update Error: {e}")

def get_config(key, default=None):
    val = get_db(f'config/{key}')
    return val if val is not None else default

def set_config(key, val):
    set_db(f'config/{key}', val)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def is_admin(user_id):
    super_admin = get_config('super_admin')
    return str(user_id) == str(super_admin)

def get_user_wallet(user_id):
    bal = get_db(f'users/{user_id}/wallet')
    return float(bal) if bal else 0.0

def update_wallet(user_id, amount):
    current = get_user_wallet(user_id)
    new_bal = round(current + amount, 2)
    set_db(f'users/{user_id}/wallet', new_bal)
    return new_bal

def generate_key():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    seg = lambda: ''.join(random.choices(chars, k=4))
    return f"SM-{seg()}-{seg()}-{seg()}"

# ==========================================
# STATES
# ==========================================
class AdminStates(StatesGroup):
    waiting_for_welcome = State()
    waiting_for_apk = State()
    waiting_for_price = State()
    waiting_for_broadcast = State()

class UserStates(StatesGroup):
    waiting_for_deposit_amt = State()

# ==========================================
# USER COMMANDS & VERIFICATION
# ==========================================
@dp.message(Command("setadmin"))
async def set_admin_cmd(message: types.Message):
    current_admin = get_config('super_admin')
    if current_admin:
        await message.answer("❌ Admin pehle se set hai! Koi aur admin nahi ban sakta.")
        return
    set_config('super_admin', message.from_user.id)
    await message.answer("👑 **Aap ab Super Admin hain!**\nAb aap `/admin` command use kar sakte hain.", parse_mode="Markdown")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if not get_db(f'users/{user_id}'):
        set_db(f'users/{user_id}', {
            'name': message.from_user.full_name,
            'username': message.from_user.username or "N/A",
            'wallet': 0.0,
            'phone': None,
            'joined_at': time.time()
        })

    verify_on = get_config('verify_on', True)
    user_phone = get_db(f'users/{user_id}/phone')

    if verify_on and not user_phone:
        default_welcome = (
            "🔒 **PREMIUM VERIFICATION**\n"
            "✨ _ONE-TIME SECURE ACCESS_ ✨\n\n"
            "👑 WELCOME TO SM STORE\n"
            "🛡️ 100% SECURE • 🌍 ALL COUNTRIES\n\n"
            "1️⃣ TAP 📱 SHARE MY NUMBER BELOW\n"
            "2️⃣ CONFIRM THE TELEGRAM PROMPT\n"
            "3️⃣ 💎 YOUR PREMIUM STORE OPENS INSTANTLY\n\n"
            "⚡ TAKES LESS THAN 5 SECONDS"
        )
        welcome_text = get_config('welcome_msg', default_welcome)
        
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 SHARE MY NUMBER", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await message.answer(welcome_text, reply_markup=kb, parse_mode="Markdown")
    else:
        await show_main_menu(message)

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    set_db(f'users/{user_id}/phone', phone)
    await message.answer("✅ Number Verified! Welcome to SM STORE.", reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message)

async def show_main_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Products", callback_data="shop"), InlineKeyboardButton(text="👤 Profile", callback_data="profile")],
        [InlineKeyboardButton(text="💰 Deposit", callback_data="deposit"), InlineKeyboardButton(text="📜 History", callback_data="history")],
        [InlineKeyboardButton(text="🆘 Support", url="https://t.me/YourSupportUsername")]
    ])
    await message.answer("🏪 **SM STORE MAIN MENU**\n\nApna option chunein:", reply_markup=kb, parse_mode="Markdown")

# ==========================================
# USER FLOWS
# ==========================================
@dp.callback_query(F.data == "profile")
async def show_profile(call: types.CallbackQuery):
    uid = call.from_user.id
    user = get_db(f'users/{uid}') or {}
    bal = get_user_wallet(uid)
    phone = user.get('phone', 'Not Verified')
    
    text = (
        f"👤 **YOUR PROFILE**\n\n"
        f"🆔 **ID:** `{uid}`\n"
        f"📞 **Phone:** {phone}\n"
        f"💰 **Wallet Balance:** ₹{bal}\n"
        f"📅 **Joined:** {datetime.fromtimestamp(user.get('joined_at', time.time())).strftime('%Y-%m-%d')}"
    )
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_main")]]))

@dp.callback_query(F.data == "shop")
async def show_shop(call: types.CallbackQuery):
    p1h = get_config('price_1hour', 9)
    p2h = get_config('price_2hour', 19)
    p3h = get_config('price_3hour', 29)
    p6h = get_config('price_6hour', 50)
    p1d = get_config('price_1day', 90)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⏱ 1 Hour - ₹{p1h}", callback_data="buy_1hour")],
        [InlineKeyboardButton(text=f"⏱ 2 Hours - ₹{p2h}", callback_data="buy_2hour")],
        [InlineKeyboardButton(text=f"⏱ 3 Hours - ₹{p3h}", callback_data="buy_3hour")],
        [InlineKeyboardButton(text=f"⏱ 6 Hours - ₹{p6h}", callback_data="buy_6hour")],
        [InlineKeyboardButton(text=f"📅 1 Day - ₹{p1d}", callback_data="buy_1day")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")]
    ])
    await call.message.edit_text("🛍 **SELECT YOUR PLAN**\nWallet se paise deduct honge.", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(call: types.CallbackQuery):
    duration = call.data.split("_")[1]
    price = float(get_config(f'price_{duration}', 10))
    uid = call.from_user.id
    
    bal = get_user_wallet(uid)
    if bal < price:
        await call.answer(f"❌ Insufficient Balance! You need ₹{round(price - bal, 2)} more.", show_alert=True)
        return
    
    update_wallet(uid, -price)
    key = generate_key()
    
    unit = 'hours' if 'hour' in duration else 'days'
    val = int(duration.replace('hour', '').replace('day', ''))
    
    set_db(f'licenses/{key}', {
        'status': 'active',
        'duration': val,
        'durationUnit': unit,
        'deviceLimit': 1,
        'devices': {},
        'createdAt': int(time.time() * 1000),
        'expiresAt': 0,
        'startedAt': 0,
        'note': f"Bought by {uid}",
        'lastLogin': 0,
        'lastDevice': ''
    })
    
    set_db(f'users/{uid}/history/{int(time.time())}', {
        'key': key, 'plan': duration, 'price': price, 'date': time.time()
    })
    
    apk_link = get_config('apk_link', 'https://t.me/YourSupportUsername')
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 DOWNLOAD APK", url=apk_link)],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="back_main")]
    ])
    
    await call.message.edit_text(
        f"✅ **PURCHASE SUCCESSFUL!**\n\n"
        f"🔑 **Your Key:** `{key}`\n"
        f"⏱ **Plan:** {duration.upper()}\n"
        f"💰 **Price:** ₹{price}\n\n"
        f"APK download karne ke liye niche button dabayein:",
        reply_markup=kb, parse_mode="Markdown"
    )

@dp.callback_query(F.data == "deposit")
async def deposit_menu(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₹10", callback_data="dep_10"), InlineKeyboardButton(text="₹50", callback_data="dep_50"), InlineKeyboardButton(text="₹100", callback_data="dep_100")],
        [InlineKeyboardButton(text="₹200", callback_data="dep_200"), InlineKeyboardButton(text="₹500", callback_data="dep_500")],
        [InlineKeyboardButton(text="💵 Custom Amount", callback_data="dep_custom")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")]
    ])
    await call.message.edit_text("💰 **DEPOSIT MONEY**\nKitna amount deposit karna hai? (Min ₹10, Max ₹1000)", reply_markup=kb)

@dp.callback_query(F.data.startswith("dep_"))
async def process_deposit(call: types.CallbackQuery, state: FSMContext):
    if call.data == "dep_custom":
        await state.set_state(UserStates.waiting_for_deposit_amt)
        await call.message.edit_text("💵 Apna amount type karein (₹10 se ₹1000 ke beech):")
        return
    
    amount = int(call.data.split("_")[1])
    await create_fam_order(call.message, amount)

@dp.message(UserStates.waiting_for_deposit_amt)
async def custom_deposit_amt(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 10 or amount > 1000:
            return await message.answer("❌ Amount ₹10 se ₹1000 ke beech hona chahiye.")
        await state.clear()
        await create_fam_order(message, amount)
    except ValueError:
        await message.answer("❌ Sirf number type karein.")

async def create_fam_order(message: types.Message, amount: int):
    uid = message.from_user.id
    order_id = f"SM{int(time.time())}{random.randint(100,999)}"
    
    # FamGateway API call
    payload = {
        "api_key": FAM_API_KEY,  # Key direct payload mein jati hai
        "amount": amount,
        "order_id": order_id,
        "customer_name": message.from_user.full_name
    }
    
    try:
        res = requests.post(f"{FAM_API_URL}/api/create-order", json=payload, timeout=10).json()
        
        # Check response (FamGateway status true/false bhejta hai)
        if res.get("status") == True or res.get("status") == "success":
            qr_url = res.get("qr_url") or res.get("payment_url") 
            upi_id = res.get("upi_id", "Check QR")
            
            # Save order in DB
            set_db(f'orders/{order_id}', {
                'uid': uid, 'amount': amount, 'status': 'pending', 'date': time.time()
            })
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ I HAVE PAID (Verify)", callback_data=f"verify_{order_id}")],
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="back_main")]
            ])
            
            # Agar QR URL hai toh photo bhejenge, warna text
            if qr_url:
                await message.answer_photo(
                    photo=qr_url,
                    caption=f"💳 **PAYMENT ORDER CREATED**\n\nAmount: ₹{amount}\nOrder ID: `{order_id}`\n\nPayment ke baad niche **I HAVE PAID** dabayein!",
                    reply_markup=kb, parse_mode="Markdown"
                )
            else:
                await message.answer(
                    f"💳 **PAYMENT ORDER CREATED**\n\nAmount: ₹{amount}\nOrder ID: `{order_id}`\n\nUPI: `{upi_id}`\nPayment ke baad niche **I HAVE PAID** dabayein!",
                    reply_markup=kb, parse_mode="Markdown"
                )
        else:
            await message.answer(f"❌ Payment Error: {res.get('message', 'Unknown Error')}")
    except Exception as e:
        await message.answer(f"❌ API Error: {str(e)}")

@dp.callback_query(F.data.startswith("verify_"))
async def verify_payment(call: types.CallbackQuery):
    order_id = call.data.split("_")[1]
    order = get_db(f'orders/{order_id}')
    
    if not order or order.get('status') == 'paid':
        await call.answer("❌ Invalid or already paid order!", show_alert=True)
        return
        
    # FamGateway verify URL format
    try:
        res = requests.get(f"{FAM_API_URL}/api/verify-order.php?api_key={FAM_API_KEY}&order_id={order_id}", timeout=10).json()
        
        # Check if paid
        if res.get("status") == True or res.get("status") == "success" or res.get("payment_status") == "SUCCESS":
            update_wallet(call.from_user.id, order['amount'])
            set_db(f'orders/{order_id}/status', 'paid')
            await call.message.edit_text(f"✅ **Payment Verified!**\n₹{order['amount']} added to your wallet.")
        else:
            await call.answer("⏳ Payment abhi receive nahi hua. Thoda intezar karein.", show_alert=True)
    except Exception as e:
        await call.answer(f"Error: {str(e)}", show_alert=True)

@dp.callback_query(F.data == "history")
async def show_history(call: types.CallbackQuery):
    uid = call.from_user.id
    hist = get_db(f'users/{uid}/history')
    
    if not hist:
        await call.message.edit_text("📜 Aapne abhi tak kuch purchase nahi kiya.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_main")]]))
        return
        
    text = "📜 **PURCHASE HISTORY**\n\n"
    # Sort by newest
    sorted_hist = sorted(hist.values(), key=lambda x: x.get('date', 0), reverse=True)
    for v in sorted_hist[:5]:
        date = datetime.fromtimestamp(v['date']).strftime('%d %b, %H:%M')
        text += f"🔑 `{v['key']}`\n📅 {date} | 💰 ₹{v['price']}\n\n"
        
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_main")]]))

@dp.callback_query(F.data == "back_main")
async def back_to_main(call: types.CallbackQuery):
    await call.message.delete()
    await show_main_menu(call.message)

# ==========================================
# ADMIN PANEL
# ==========================================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="adm_stats"), InlineKeyboardButton(text="👥 Users", callback_data="adm_users")],
        [InlineKeyboardButton(text="⚙️ Welcome Message", callback_data="adm_welcome"), InlineKeyboardButton(text="🛍 Prices", callback_data="adm_prices")],
        [InlineKeyboardButton(text="📥 Set APK Link", callback_data="adm_apk"), InlineKeyboardButton(text="📢 Announcement", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🛠 Maintenance", callback_data="adm_maint")],
    ])
    await message.answer("👑 **SM STORE ADMIN PANEL**\n\nSelect an option:", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "adm_stats")
async def adm_stats(call: types.CallbackQuery):
    users = get_db('users') or {}
    total_users = len(users)
    total_bal = sum(float(u.get('wallet', 0)) for u in users.values())
    
    await call.message.edit_text(f"📊 **STATS**\n\n👥 Total Users: {total_users}\n💰 Total Balance: ₹{total_bal:.2f}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="adm_back")]]), parse_mode="Markdown")

@dp.callback_query(F.data == "adm_users")
async def adm_users(call: types.CallbackQuery):
    users = get_db('users') or {}
    text = "👥 **USERS LIST** (Max 10)\n\n"
    for uid, data in list(users.items())[:10]:
        text += f"🆔 `{uid}`\n📞 {data.get('phone', 'N/A')}\n💰 ₹{data.get('wallet', 0)}\n\n"
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="adm_back")]]))

@dp.callback_query(F.data == "adm_welcome")
async def adm_welcome(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_welcome)
    await call.message.edit_text("✏️ Naya Welcome Message type karein:")

@dp.message(AdminStates.waiting_for_welcome)
async def save_welcome(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    set_config('welcome_msg', message.text)
    await state.clear()
    await message.answer("✅ Welcome Message updated!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin Menu", callback_data="adm_back")]]))

@dp.callback_query(F.data == "adm_apk")
async def adm_apk(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_apk)
    await call.message.edit_text("📥 APK ka direct link bhejein (URL):")

@dp.message(AdminStates.waiting_for_apk)
async def save_apk(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    set_config('apk_link', message.text)
    await state.clear()
    await message.answer("✅ APK Link updated!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin Menu", callback_data="adm_back")]]))

@dp.callback_query(F.data == "adm_prices")
async def adm_prices(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1h - ₹{get_config('price_1hour', 9)}", callback_data="price_1hour"), InlineKeyboardButton(text=f"2h - ₹{get_config('price_2hour', 19)}", callback_data="price_2hour")],
        [InlineKeyboardButton(text=f"3h - ₹{get_config('price_3hour', 29)}", callback_data="price_3hour"), InlineKeyboardButton(text=f"6h - ₹{get_config('price_6hour', 50)}", callback_data="price_6hour")],
        [InlineKeyboardButton(text=f"1d - ₹{get_config('price_1day', 90)}", callback_data="price_1day")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="adm_back")]
    ])
    await call.message.edit_text("💰 **MANAGE PRICES**\nKis plan ka price change karna hai?", reply_markup=kb)

@dp.callback_query(F.data.startswith("price_"))
async def edit_price(call: types.CallbackQuery, state: FSMContext):
    plan = call.data.split("_")[1]
    await state.set_state(AdminStates.waiting_for_price)
    await state.update_data(plan=plan)
    await call.message.edit_text(f"💵 `{plan}` ka naya price (₹) type karein:")

@dp.message(AdminStates.waiting_for_price)
async def save_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    plan = data['plan']
    try:
        price = int(message.text)
        set_config(f'price_{plan}', price)
        await state.clear()
        await message.answer(f"✅ `{plan}` price set to ₹{price}!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin Menu", callback_data="adm_back")]]))
    except:
        await message.answer("❌ Invalid amount. Sirf number bhejein.")

@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_broadcast)
    await call.message.edit_text("📢 Jo message sabko bhejna hai, wo type karein:")

@dp.message(AdminStates.waiting_for_broadcast)
async def send_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    users = get_db('users') or {}
    count = 0
    await message.answer("⏳ Broadcasting started...")
    for uid in users.keys():
        try:
            await bot.send_message(chat_id=uid, text=message.text)
            count += 1
            await asyncio.sleep(0.05) # Rate limit avoid karne ke liye
        except:
            pass
    await state.clear()
    await message.answer(f"✅ Broadcast sent to {count} users.")

@dp.callback_query(F.data == "adm_maint")
async def adm_maint(call: types.CallbackQuery):
    current = get_config('maintenance', False)
    status = "ON 🟢" if current else "OFF 🔴"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Maintenance is {status}. Click to Toggle", callback_data="toggle_maint")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="adm_back")]
    ])
    await call.message.edit_text("🛠 **MAINTENANCE MODE**", reply_markup=kb)

@dp.callback_query(F.data == "toggle_maint")
async def toggle_maint(call: types.CallbackQuery):
    current = get_config('maintenance', False)
    set_config('maintenance', not current)
    await adm_maint(call)

@dp.callback_query(F.data == "adm_back")
async def adm_back(call: types.CallbackQuery):
    await call.message.delete()
    await admin_panel(call.message)

# ==========================================
# MAINTENANCE MIDDLEWARE
# ==========================================
@dp.message()
async def maint_check(message: types.Message):
    if not is_admin(message.from_user.id) and get_config('maintenance', False):
        await message.answer("🛠 **BOT UNDER MAINTENANCE**\nHum jald wapas aayenge!")
        return

# ==========================================
# RUN BOT
# ==========================================
if __name__ == "__main__":
    print("🚀 SM STORE Bot Started!")
    asyncio.run(dp.start_polling(bot))