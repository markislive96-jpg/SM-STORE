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
import os
from flask import Flask
import threading

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "9014327151:AAHzrXEqqF9HY6CDmpdwnuz3N3qsYt-r1Qw")
FIREBASE_URL = os.getenv("FIREBASE_URL", "https://tumhara-baap-default-rtdb.firebaseio.com")
FAM_API_KEY = os.getenv("FAM_API_KEY", "fam_77567c5053f8e96c08aab9f1d5670d4e0df13a5c")

# ✅ FamGateway URL (Bina 'api.' ke)
FAM_API_URL = "https://famgateway.in" 

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

# Default Texts (Admin change kar sakta hai)
DEFAULT_TEXTS = {
    "welcome": "🔒 **PREMIUM VERIFICATION**\n✨ _ONE-TIME SECURE ACCESS_ ✨\n\n👑 WELCOME TO SM STORE\n🛡️ 100% SECURE • 🌍 ALL COUNTRIES\n\n1️⃣ TAP 📱 SHARE MY NUMBER BELOW\n2️⃣ CONFIRM THE TELEGRAM PROMPT\n3️⃣ 💎 YOUR PREMIUM STORE OPENS INSTANTLY\n\n⚡ TAKES LESS THAN 5 SECONDS",
    "shop_title": "🛍 **SELECT YOUR PLAN**\nWallet se paise deduct honge.",
    "success_msg": "✅ **PURCHASE SUCCESSFUL!**\n\n🔑 **Your Key:** `{key}`\n⏱ **Plan:** {plan}\n💰 **Price:** ₹{price}\n\nAPK download karne ke liye niche button dabayein:",
    "main_menu": "🏪 **SM STORE MAIN MENU**\n\nApna option chunein:"
}

# ==========================================
# STATES
# ==========================================
class AdminStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_product_name = State()
    waiting_for_product_price = State()
    waiting_for_product_apk = State()
    waiting_for_product_id = State()
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
        await message.answer("❌ Admin pehle se set hai!")
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
        welcome_text = get_config('text_welcome', DEFAULT_TEXTS['welcome'])
        
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
    menu_text = get_config('text_main_menu', DEFAULT_TEXTS['main_menu'])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Products", callback_data="shop"), InlineKeyboardButton(text="👤 Profile", callback_data="profile")],
        [InlineKeyboardButton(text="💰 Deposit", callback_data="deposit"), InlineKeyboardButton(text="📜 History", callback_data="history")],
        [InlineKeyboardButton(text="🆘 Support", url="https://t.me/dark_config001")]
    ])
    await message.answer(menu_text, reply_markup=kb, parse_mode="Markdown")

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
    products = get_db('products') or {}
    
    # Default products agar DB khali hai
    if not products:
        default_products = {
            "1hour": {"name": "1 Hour", "price": 9, "apk": ""},
            "2hour": {"name": "2 Hours", "price": 19, "apk": ""},
            "3hour": {"name": "3 Hours", "price": 29, "apk": ""},
            "6hour": {"name": "6 Hours", "price": 50, "apk": ""},
            "1day": {"name": "1 Day", "price": 90, "apk": ""}
        }
        for pid, pdata in default_products.items():
            set_db(f'products/{pid}', pdata)
        products = default_products

    buttons = []
    for pid, pdata in products.items():
        btn_text = f"{pdata.get('name', pid)} - ₹{pdata.get('price', 0)}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"buy_{pid}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_main")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    shop_text = get_config('text_shop_title', DEFAULT_TEXTS['shop_title'])
    await call.message.edit_text(shop_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(call: types.CallbackQuery):
    product_id = call.data.split("_")[1]
    product = get_db(f'products/{product_id}')
    
    if not product:
        await call.answer("❌ Product not found!", show_alert=True)
        return

    price = float(product.get('price', 0))
    apk_link = product.get('apk', '')
    uid = call.from_user.id
    
    bal = get_user_wallet(uid)
    if bal < price:
        await call.answer(f"❌ Insufficient Balance! You need ₹{round(price - bal, 2)} more.", show_alert=True)
        return
    
    update_wallet(uid, -price)
    key = generate_key()
    
    unit = 'hours' if 'hour' in product_id else 'days'
    val = int(''.join(filter(str.isdigit, product_id))) if any(c.isdigit() for c in product_id) else 1
    
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
        'key': key, 'plan': product.get('name', product_id), 'price': price, 'date': time.time()
    })
    
    if apk_link:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 DOWNLOAD APK", url=apk_link)],
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="back_main")]
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="back_main")]
        ])
    
    success_template = get_config('text_success_msg', DEFAULT_TEXTS['success_msg'])
    success_text = success_template.format(key=key, plan=product.get('name', product_id), price=price)
    
    await call.message.edit_text(success_text, reply_markup=kb, parse_mode="Markdown")

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
    
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": FAM_API_KEY
    }
    payload = {
        "amount": amount,
        "customer_name": message.from_user.full_name
    }
    
    try:
        res = requests.post(f"{FAM_API_URL}/api/create-order", json=payload, headers=headers, timeout=15).json()
        
        if res.get("status") == "success" or res.get("success"):
            data = res.get("data", res)
            qr_url = data.get("qr_url") or data.get("qr_image")
            order_id = data.get("order_id", order_id)
            upi_id = data.get("upi_id", "Check QR")
            
            set_db(f'orders/{order_id}', {
                'uid': uid, 'amount': amount, 'status': 'pending', 'date': time.time()
            })
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ I HAVE PAID (Verify)", callback_data=f"verify_{order_id}")],
                [InlineKeyboardButton(text="🔙 Cancel", callback_data="back_main")]
            ])
            
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
        
    try:
        res = requests.get(f"{FAM_API_URL}/api/checkout-status.php?order_id={order_id}", timeout=15).json()
        
        if res.get("status") == "success" or res.get("success") or res.get("payment_status") == "SUCCESS":
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
# ADMIN PANEL (Fully Customizable)
# ==========================================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="adm_stats"), InlineKeyboardButton(text="👥 Users", callback_data="adm_users")],
        [InlineKeyboardButton(text="🛍 Manage Products", callback_data="adm_products"), InlineKeyboardButton(text="📝 Edit Texts", callback_data="adm_texts")],
        [InlineKeyboardButton(text="📢 Announcement", callback_data="adm_broadcast"), InlineKeyboardButton(text="🛠 Maintenance", callback_data="adm_maint")],
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

@dp.callback_query(F.data == "adm_texts")
async def adm_texts(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👋 Welcome Text", callback_data="edit_text_welcome")],
        [InlineKeyboardButton(text="🛍 Shop Title Text", callback_data="edit_text_shop_title")],
        [InlineKeyboardButton(text="✅ Success Message", callback_data="edit_text_success_msg")],
        [InlineKeyboardButton(text="🏪 Main Menu Text", callback_data="edit_text_main_menu")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="adm_back")]
    ])
    await call.message.edit_text("📝 **EDIT TEXTS**\nKaunsa text change karna hai?", reply_markup=kb)

@dp.callback_query(F.data.startswith("edit_text_"))
async def edit_text_prompt(call: types.CallbackQuery, state: FSMContext):
    text_key = call.data.replace("edit_text_", "")
    await state.set_state(AdminStates.waiting_for_text)
    await state.update_data(text_key=text_key)
    
    current_text = get_config(f'text_{text_key}', DEFAULT_TEXTS.get(text_key, 'Not set'))
    await call.message.edit_text(f"✏️ **Current Text ({text_key}):**\n\n`{current_text}`\n\nNaya text type karein (Markdown allowed):")

@dp.message(AdminStates.waiting_for_text)
async def save_custom_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    text_key = data['text_key']
    set_config(f'text_{text_key}', message.text)
    await state.clear()
    await message.answer("✅ Text updated successfully!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin Menu", callback_data="adm_back")]]))

# --- Products Manage ---
@dp.callback_query(F.data == "adm_products")
async def adm_products(call: types.CallbackQuery):
    products = get_db('products') or {}
    buttons = []
    for pid, pdata in products.items():
        buttons.append([InlineKeyboardButton(text=f"✏️ {pdata.get('name', pid)}", callback_data=f"editprod_{pid}")])
    buttons.append([InlineKeyboardButton(text="➕ Add New Product", callback_data="addprod")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="adm_back")])
    await call.message.edit_text("🛍 **MANAGE PRODUCTS**\nKis product ko edit karna hai?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("editprod_"))
async def edit_product(call: types.CallbackQuery, state: FSMContext):
    pid = call.data.split("_")[1]
    product = get_db(f'products/{pid}')
    if not product:
        await call.answer("Product not found!", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_product_name)
    await state.update_data(pid=pid)
    await call.message.edit_text(f"Product: {product.get('name')}\nCurrent Price: ₹{product.get('price')}\nCurrent APK: {product.get('apk', 'Not set')}\n\nNaya **Product Name** type karein:")

@dp.message(AdminStates.waiting_for_product_name)
async def save_product_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    pid = data['pid']
    update_db(f'products/{pid}', {'name': message.text})
    await state.set_state(AdminStates.waiting_for_product_price)
    await message.answer(f"✅ Name updated!\nAb is product ka **Price (₹)** type karein:")

@dp.message(AdminStates.waiting_for_product_price)
async def save_product_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    pid = data['pid']
    try:
        price = int(message.text)
        update_db(f'products/{pid}', {'price': price})
        await state.set_state(AdminStates.waiting_for_product_apk)
        await message.answer(f"✅ Price set to ₹{price}!\nAb is product ka **APK Link** type karein (ya 'skip' likhein):")
    except ValueError:
        await message.answer("❌ Sirf number type karein.")

@dp.message(AdminStates.waiting_for_product_apk)
async def save_product_apk(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    pid = data['pid']
    apk = message.text if message.text.lower() != 'skip' else ''
    update_db(f'products/{pid}', {'apk': apk})
    await state.clear()
    await message.answer("✅ Product updated successfully!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin Menu", callback_data="adm_back")]]))

@dp.callback_query(F.data == "addprod")
async def add_product(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_product_id)
    await call.message.edit_text("🆕 Naya Product ID type karein (jaise: 2hour, 5day, 1month):")

@dp.message(AdminStates.waiting_for_product_id)
async def save_product_id(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    pid = message.text.lower().strip()
    if get_db(f'products/{pid}'):
        return await message.answer("❌ Ye Product ID pehle se hai. Dusra ID daalein.")
    
    set_db(f'products/{pid}', {'name': pid, 'price': 10, 'apk': ''})
    await state.clear()
    await message.answer(f"✅ Product '{pid}' created!\nAb isko edit karke naam, price aur APK set karein.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛍 Manage Products", callback_data="adm_products")]]))

# --- Broadcast & Maintenance ---
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
            await asyncio.sleep(0.05)
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
# FLASK SERVER FOR RENDER
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "SM STORE Bot is alive!"

def run_bot():
    print("🚀 SM STORE Bot Started!")
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
