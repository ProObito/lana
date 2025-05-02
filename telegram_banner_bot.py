import os
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests

# Configuration
API_ID    = os.environ.get("API_ID", "20718334") 
API_HASH  = os.environ.get("API_HASH", "4e81464b29d79c58d0ad8a0c55ece4a5")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7403693425:AAHaGlkp-zNNPvNeO62xWqwmsRI5apY0Dcs")  # From @BotFather
FONT_DIR = 'fonts/'
DATA_DIR = 'data/'
USER_DATA_FILE = os.path.join(DATA_DIR, 'user_data.json')
AUTHORIZED_USERS = [5585016974]  # Replace with your Telegram user ID
STATUS_OPTIONS = ['ONGOING', 'PUSHED', 'COMPLETE', 'AIRING']
STATUS_EMOJIS = {'ONGOING': '🔍', 'PUSHED': '🔍', 'COMPLETE': '🔍', 'AIRING': '🔍'}

# Ensure directories exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
if not os.path.exists(FONT_DIR):
    os.makedirs(FONT_DIR)

# List of fonts to be included in the fonts/ directory
FONTS = [
    'Montserrat-Bold.ttf',  # Alternative for Moon Rising (bold, modern)
    'Poppins-Regular.ttf',  # Alternative for Havitas (geometric, stylish)
    'BebasNeue-Regular.ttf',  # Alternative for Coolveta (condensed, bold)
    'Roboto-Regular.ttf',    # Additional stylish font
    'OpenSans-Bold.ttf'      # Additional versatile font
]

# Initialize Pyrogram client
app = Client("banner_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load or initialize user data
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Get available fonts
def get_fonts():
    available_fonts = [f for f in os.listdir(FONT_DIR) if f.endswith('.ttf')]
    if not available_fonts:
        return FONTS  # Fallback to default font list if directory is empty
    return available_fonts

# Initialize user state
def init_user_state(user_id):
    user_data = load_user_data()
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'step': None,
            'image': None,
            'name': None,
            'description': None,
            'about': None,
            'status': None,
            'font': None,
            'watermark_text': None,
            'blur_intensity': 0
        }
        save_user_data(user_data)
    return user_data

# Check if user is authorized
def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

# Auto-delete message
async def delete_message_later(client, chat_id, message_id, delay=30):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, message_id)
    except:
        pass

# Start banner creation
@app.on_message(filters.command("create_banner") & filters.private)
async def create_banner(client, message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        msg = await message.reply("🚫 You are not authorized to use this bot.")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
        return

    user_data = init_user_state(user_id)
    user_data[str(user_id)]['step'] = 'image'
    save_user_data(user_data)
    msg = await message.reply("🎨 Please upload an image for the banner.")
    asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

# Handle image upload
@app.on_message(filters.photo & filters.private)
async def handle_image(client, message):
    user_id = message.from_user.id
    user_data = load_user_data()
    if str(user_id) not in user_data or user_data[str(user_id)]['step'] != 'image':
        return

    try:
        image_path = f"{DATA_DIR}{user_id}_image.jpg"
        await message.download(image_path)
        user_data[str(user_id)]['image'] = image_path
        user_data[str(user_id)]['step'] = 'name'
        save_user_data(user_data)
        msg = await message.reply("🖼️ Image received! Please send the name text (use _ for underline, e.g., _Hannah_).")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    except Exception as e:
        msg = await message.reply("❌ Error processing image. Please upload a valid image.")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

# Handle text inputs
@app.on_message(filters.text & ~filters.command & filters.private)
async def handle_text(client, message):
    user_id = message.from_user.id
    user_data = load_user_data()
    if str(user_id) not in user_data:
        return

    step = user_data[str(user_id)]['step']
    text = message.text

    if step == 'name':
        user_data[str(user_id)]['name'] = text
        user_data[str(user_id)]['step'] = 'description'
        save_user_data(user_data)
        msg = await message.reply("✅ Name received! Please send the description text (use _ for underline).")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    elif step == 'description':
        user_data[str(user_id)]['description'] = text
        user_data[str(user_id)]['step'] = 'about'
        save_user_data(user_data)
        msg = await message.reply("✅ Description received! Please send the about text (use _ for underline).")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    elif step == 'about':
        user_data[str(user_id)]['about'] = text
        user_data[str(user_id)]['step'] = 'status'
        save_user_data(user_data)
        msg = await message.reply("✅ About text received! Please send the status text (ONGOING, PUSHED, COMPLETE, AIRING).")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    elif step == 'status':
        if text.upper() in STATUS_OPTIONS:
            user_data[str(user_id)]['status'] = text.upper()
            user_data[str(user_id)]['step'] = 'watermark'
            save_user_data(user_data)
            msg = await message.reply("✅ Status received! Please send the watermark text (or type 'skip' to skip).")
            asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
        else:
            msg = await message.reply("❌ Invalid status! Please send one of: ONGOING, PUSHED, COMPLETE, AIRING.")
            asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    elif step == 'watermark':
        user_data[str(user_id)]['watermark_text'] = text if text.lower() != 'skip' else ''
        user_data[str(user_id)]['step'] = 'blur'
        save_user_data(user_data)
        msg = await message.reply("✅ Watermark received! Please send blur intensity (0 for none, 1 for low, 2 for medium, 3 for high).")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    elif step == 'blur':
        try:
            blur = int(text)
            if 0 <= blur <= 3:
                user_data[str(user_id)]['blur_intensity'] = int(text)
                user_data[str(user_id)]['step'] = 'font'
                save_user_data(user_data)
                # Show font options
                fonts = get_fonts()
                if not fonts:
                    msg = await message.reply("❌ No fonts available. Please contact the developer to add fonts like Montserrat, Poppins
