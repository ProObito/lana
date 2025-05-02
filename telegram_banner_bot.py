import os
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import pymongo
from bson import ObjectId

# Configuration
API_ID    = os.environ.get("API_ID", "20718334")
API_HASH  = os.environ.get("API_HASH", "4e81464b29d79c58d0ad8a0c55ece4a5")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7830743177:AAHkVvb0AwI-bDqa7O0JUZdb_tvSdS4E0fA") 
ADMIN_ID = 5585016974  
START_PIC = os.environ.get("START_PIC", "https://graph.org/file/29a3acbbab9de5f45a5fe.jpg")
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://obito:umaid2008@cluster0.engyc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')  # MongoDB Atlas connection string
FONT_DIR = 'fonts/'
DATA_DIR = 'data/'
USER_DATA_FILE = os.path.join(DATA_DIR, 'user_data.json')
AUTHO_USERS_FILE = os.path.join(DATA_DIR, 'autho_users.json')
STATUS_OPTIONS = ['ONGOING', 'PUSHED', 'COMPLETE', 'AIRING']
STATUS_EMOJIS = {'ONGOING': '🔍', 'PUSHED': '🔍', 'COMPLETE': '🔍', 'AIRING': '🔍'}
START_TXT = """<b>Hey! {}  

» I am an advanced rename bot! Which can autorename your files with custom caption and thumbnail and also sequence them perfectly</b>"""
HELP_TXT = """<b>Here is help menu important commands:

Awesome features🫧

Rename bot is a handy tool that helps you rename and manage your files effortlessly. """
# Ensure directories exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
if not os.path.exists(FONT_DIR):
    os.makedirs(FONT_DIR)

# MongoDB setup
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client['BannerBotDB']
fonts_collection = db['fonts']

# Initialize Pyrogram client
app = Client("banner_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load or initialize user data (file-based)
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load or initialize authorized users (file-based)
def load_autho_users():
    if os.path.exists(AUTHO_USERS_FILE):
        with open(AUTHO_USERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_autho_users(users):
    with open(AUTHO_USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Authorization functions
async def add_autho_user(user_id):
    users = load_autho_users()
    if user_id not in users:
        users.append(user_id)
        save_autho_users(users)

async def remove_autho_user(user_id):
    users = load_autho_users()
    if user_id in users:
        users.remove(user_id)
        save_autho_users(users)

async def is_autho_user_exist(user_id):
    users = load_autho_users()
    return user_id in users

async def get_all_autho_users():
    return load_autho_users()

# Get available fonts from MongoDB
def get_fonts():
    fonts = fonts_collection.find()
    return [font['filename'] for font in fonts]

# Initialize user state (file-based)
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

# Auto-delete message
async def delete_message_later(client, chat_id, message_id, delay=30):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, message_id)
    except:
        pass

# Custom filter for non-command text messages
def non_command_text():
    async def func(flt, client, message):
        return filters.text.filter(flt, client, message) and not message.text.startswith('/')
    return filters.create(func)

# Save font to MongoDB and fonts/ directory
@app.on_message(filters.command("save") & filters.private & filters.reply & filters.user(ADMIN_ID))
async def save_font(client, message):
    if not message.reply_to_message.document or not message.reply_to_message.document.file_name.endswith('.ttf'):
        msg = await message.reply("❌ Please reply to a `.ttf` font file with `/save`.")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
        return

    user_id = message.from_user.id
    document = message.reply_to_message.document
    font_filename = document.file_name
    font_path = os.path.join(FONT_DIR, font_filename)

    try:
        # Download font file
        await document.download(font_path)

        # Save font metadata to MongoDB
        font_data = {
            'filename': font_filename,
            'file_id': document.file_id
        }
        fonts_collection.update_one({'filename': font_filename}, {'$set': font_data}, upsert=True)

        msg = await message.reply(f"✅ Font `{font_filename}` saved successfully and added to selection!")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    except Exception as e:
        msg = await message.reply(f"❌ Error saving font: {str(e)}")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

# Start banner creation
@app.on_message(filters.command("create_banner") & filters.private)
async def create_banner(client, message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID and not await is_autho_user_exist(user_id):
        msg = await message.reply("🚫 You are not authorized to use this bot. Contact the admin to be added.")
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
@app.on_message(non_command_text() & filters.private)
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
                user_data[str(user_id)]['blur_intensity'] = blur
                user_data[str(user_id)]['step'] = 'font'
                save_user_data(user_data)
                # Show font options from MongoDB
                fonts = get_fonts()
                if not fonts:
                    msg = await message.reply("❌ No fonts available. Please upload and save fonts using `/save`.")
                    asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
                    return
                keyboard = [[InlineKeyboardButton(font.replace('.ttf', ''), callback_data=f"font_{font}")] for font in fonts]
                reply_markup = InlineKeyboardMarkup(keyboard)
                msg = await message.reply("✅ Blur intensity received! Please select a font:", reply_markup=reply_markup)
                asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
            else:
                msg = await message.reply("❌ Invalid blur intensity! Please send a number between 0 and 3.")
                asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
        except ValueError:
            msg = await message.reply("❌ Please send a valid number for blur intensity.")
            asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

# Handle font selection
@app.on_message(filters.command("font") & filters.private)
async def handle_font_selection(client, message):
    user_id = message.from_user.id
    user_data = load_user_data()
    if str(user_id) not in user_data or user_data[str(user_id)]['step'] != 'font':
        msg = await message.reply("❌ Please complete the banner creation process to select a font.")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
        return

    font = message.text.replace('/font ', '')
    if font not in get_fonts():
        msg = await message.reply(f"❌ Font `{font}` not found. Please select a valid font from the list.")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
        return

    user_data[str(user_id)]['font'] = font
    user_data[str(user_id)]['step'] = None
    save_user_data(user_data)

    try:
        # Generate banner
        generate_banner(user_id)
        await message.reply_photo(photo=f"{DATA_DIR}{user_id}_banner.jpg")
        msg = await message.reply("🎉 Banner created successfully!")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    except Exception as e:
        msg = await message.reply("❌ Error generating banner. Please try again.")
        asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

# Generate banner
def generate_banner(user_id):
    user_data = load_user_data()[str(user_id)]
    image_path = user_data['image']
    name = user_data['name']
    description = user_data['description']
    about = user_data['about']
    status = user_data['status']
    font = user_data['font']
    watermark_text = user_data['watermark_text']
    blur_intensity = user_data['blur_intensity']

    # Load image
    img = Image.open(image_path)
    
    # Apply blur if requested
    if blur_intensity > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_intensity))

    draw = ImageDraw.Draw(img)
    font_path = os.path.join(FONT_DIR, font)
    font_size = 40
    font_obj = ImageFont.truetype(font_path, font_size)

    # Text positions (hardcoded, not stored in DB)
    positions = {
        'name': (50, 50),
        'description': (50, 150),
        'about': (50, 250),
        'status': (50, 350),
        'watermark': (50, 450)
    }

    # Draw text with underline support
    for key, text in [('name', name), ('description', description), ('about', about), ('status', f"{status} {STATUS_EMOJIS[status]}")]:
        if text:
            if '_' in text:
                text = text.replace('_', '')  # Remove underscore for display
                draw.text(positions[key], text, font=font_obj, fill='white')
                # Add underline
                text_width, text_height = draw.textsize(text, font=font_obj)
                draw.line((positions[key][0], positions[key][1] + text_height, 
                           positions[key][0] + text_width, positions[key][1] + text_height), fill='white', width=2)
            else:
                draw.text(positions[key], text, font=font_obj, fill='white')

    # Add watermark
    if watermark_text:
        draw.text(positions['watermark'], watermark_text, font=font_obj, fill=(255, 255, 255, 128))  # Semi-transparent

    # Save banner
    banner_path = f"{DATA_DIR}{user_id}_banner.jpg"
    img.save(banner_path)

# Authorization Commands
@app.on_message(filters.command("addautho_user") & filters.private & filters.user(ADMIN_ID))
async def addauthorise_user(client, message):
    ids = message.text.removeprefix("/addautho_user").strip().split()
    check = 1

    try:
        if len(ids) > 0:
            for id in ids:
                if len(id) == 10 and id.isdigit():
                    await add_autho_user(int(id))
                else:
                    check = 0
                    break
        else:
            check = 0
    except ValueError:
        check = 0

    if check == 1:
        msg = await message.reply(f'**Authorised Users Added ✅**\n<blockquote>`{" ".join(ids)}`</blockquote>')
    else:
        msg = await message.reply(f"**INVALID USE OF COMMAND:**\n"
                                 "<blockquote>**➪ Check if the command is empty OR the added ID should be correct (10 digit numbers)**</blockquote>")
    asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

@app.on_message(filters.command("delautho_user") & filters.private & filters.user(ADMIN_ID))
async def deleteauthorise_user(client, message):
    ids = message.text.removeprefix("/delautho_user").strip().split()
    check = 1

    try:
        if len(ids) > 0:
            for id in ids:
                if len(id) == 10 and id.isdigit():
                    await remove_autho_user(int(id))
                else:
                    check = 0
                    break
        else:
            check = 0
    except ValueError:
        check = 0

    if check == 1:
        msg = await message.reply(f'**Delete Authorised Users 🆑**\n<blockquote>`{" ".join(ids)}`</blockquote>')
    else:
        msg = await message.reply(f"**INVALID USE OF COMMAND:**\n"
                                 "<blockquote>**➪ Check if the command is empty OR the added ID should be correct (10 digit numbers)**</blockquote>")
    asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

@app.on_message(filters.command("autho_users") & filters.private & filters.user(ADMIN_ID))
async def authorise_user_list(client, message):
    autho_users = await get_all_autho_users()
    if autho_users:
        autho_users_str = "\n".join(map(str, autho_users))
        msg = await message.reply(f"🚻 **AUTHORIZED USERS:** 🌀\n\n`{autho_users_str}`")
    else:
        msg = await message.reply("No authorized users found.")
    asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

@app.on_message(filters.command("check_autho") & filters.private)
async def check_authorise_user(client, message):
    user_id = message.from_user.id
    check = await is_autho_user_exist(user_id)
    if check:
        msg = await message.reply("**Yes, You are Authorised user 🟢**\n**<blockquote>You can send files to create banners.</blockquote>**")
    else:
        msg = await message.reply("**Nope, You are not Authorised user 🔴**\n<blockquote>**You can't create banners.**</blockquote>\n**Contact the admin to add you as an Authorised user.**")
    asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))

# Restart bot (VPS only)
@app.on_message(filters.command("restart") & filters.private & filters.user(ADMIN_ID))
async def restart(client, message):
    msg = await message.reply("🔄 Restarting bot...")
    asyncio.create_task(delete_message_later(client, message.chat.id, msg.id))
    os.system("nohup python telegram_banner_bot.py &")
    exit()

# Main function
async def main():
    await app.start()
    print("Bot is running...")
    # Keep the bot running without idle()
    while True:
        await asyncio.sleep(3600)  # Sleep for an hour to keep the loop alive

if __name__ == '__main__':
    asyncio.run(main())
