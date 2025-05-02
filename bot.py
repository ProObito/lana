import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext, JobQueue
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests

# Configuration
BOT_TOKEN = '7403693425:AAHaGlkp-zNNPvNeO62xWqwmsRI5apY0Dcs'  # Replace with your bot token
FONT_DIR = 'fonts/'
DATA_DIR = 'data/'
USER_DATA_FILE = os.path.join(DATA_DIR, 'user_data.json')
AUTHORIZED_USERS = [123456789]  # Replace with your Telegram user ID
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

# Send temporary message (auto-delete)
def send_temp_message(update: Update, context: CallbackContext, text: str, delay: int = 30):
    message = update.message.reply_text(text)
    context.job_queue.run_once(delete_message, delay, context={'chat_id': message.chat_id, 'message_id': message.message_id})

def delete_message(context: CallbackContext):
    job = context.job
    try:
        context.bot.delete_message(chat_id=job.context['chat_id'], message_id=job.context['message_id'])
    except:
        pass

# Start banner creation
def create_banner(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        send_temp_message(update, context, "🚫 You are not authorized to use this bot.")
        return

    user_data = init_user_state(user_id)
    user_data[str(user_id)]['step'] = 'image'
    save_user_data(user_data)
    send_temp_message(update, context, "🎨 Please upload an image for the banner.")

# Handle image upload
def handle_image(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = load_user_data()
    if str(user_id) not in user_data or user_data[str(user_id)]['step'] != 'image':
        return

    try:
        photo = update.message.photo[-1]  # Get highest resolution photo
        file = context.bot.get_file(photo.file_id)
        image_path = f"{DATA_DIR}{user_id}_image.jpg"
        file.download(image_path)
        user_data[str(user_id)]['image'] = image_path
        user_data[str(user_id)]['step'] = 'name'
        save_user_data(user_data)
        send_temp_message(update, context, "🖼️ Image received! Please send the name text (use _ for underline, e.g., _Hannah_).")
    except Exception as e:
        send_temp_message(update, context, "❌ Error processing image. Please upload a valid image.")

# Handle text inputs
def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = load_user_data()
    if str(user_id) not in user_data:
        return

    step = user_data[str(user_id)]['step']
    text = update.message.text

    if step == 'name':
        user_data[str(user_id)]['name'] = text
        user_data[str(user_id)]['step'] = 'description'
        save_user_data(user_data)
        send_temp_message(update, context, "✅ Name received! Please send the description text (use _ for underline).")
    elif step == 'description':
        user_data[str(user_id)]['description'] = text
        user_data[str(user_id)]['step'] = 'about'
        save_user_data(user_data)
        send_temp_message(update, context, "✅ Description received! Please send the about text (use _ for underline).")
    elif step == 'about':
        user_data[str(user_id)]['about'] = text
        user_data[str(user_id)]['step'] = 'status'
        save_user_data(user_data)
        send_temp_message(update, context, "✅ About text received! Please send the status text (ONGOING, PUSHED, COMPLETE, AIRING).")
    elif step == 'status':
        if text.upper() in STATUS_OPTIONS:
            user_data[str(user_id)]['status'] = text.upper()
            user_data[str(user_id)]['step'] = 'watermark'
            save_user_data(user_data)
            send_temp_message(update, context, "✅ Status received! Please send the watermark text (or type 'skip' to skip).")
        else:
            send_temp_message(update, context, "❌ Invalid status! Please send one of: ONGOING, PUSHED, COMPLETE, AIRING.")
    elif step == 'watermark':
        user_data[str(user_id)]['watermark_text'] = text if text.lower() != 'skip' else ''
        user_data[str(user_id)]['step'] = 'blur'
        save_user_data(user_data)
        send_temp_message(update, context, "✅ Watermark received! Please send blur intensity (0 for none, 1 for low, 2 for medium, 3 for high).")
    elif step == 'blur':
        try:
            blur = int(text)
            if 0 <= blur <= 3:
                user_data[str(user_id)]['blur_intensity'] = blur
                user_data[str(user_id)]['step'] = 'font'
                save_user_data(user_data)
                # Show font options
                fonts = get_fonts()
                if not fonts:
                    send_temp_message(update, context, "❌ No fonts available. Please contact the developer to add fonts like Montserrat, Poppins, or Bebas Neue.")
                    return
                keyboard = [[InlineKeyboardButton(font.replace('.ttf', ''), callback_data=f"font_{font}")] for font in fonts]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text("✅ Blur intensity received! Please select a font:", reply_markup=reply_markup)
            else:
                send_temp_message(update, context, "❌ Invalid blur intensity! Please send a number between 0 and 3.")
        except ValueError:
            send_temp_message(update, context, "❌ Please send a valid number for blur intensity.")

# Handle font selection
def handle_font_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = load_user_data()
    if str(user_id) not in user_data or user_data[str(user_id)]['step'] != 'font':
        query.answer()
        return

    font = query.data.replace('font_', '')
    user_data[str(user_id)]['font'] = font
    user_data[str(user_id)]['step'] = None
    save_user_data(user_data)

    try:
        # Generate banner
        generate_banner(user_id)
        query.message.reply_photo(photo=open(f"{DATA_DIR}{user_id}_banner.jpg", 'rb'))
        query.message.reply_text("🎉 Banner created successfully!")
    except Exception as e:
        query.message.reply_text("❌ Error generating banner. Please try again.")
    query.answer()

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

    # Text positions (adjust based on your template)
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

# Restart bot (VPS only)
def restart(update: Update, context: CallbackContext):
    if not is_authorized(update.effective_user.id):
        send_temp_message(update, context, "🚫 You are not authorized to restart the bot.")
        return
    send_temp_message(update, context, "🔄 Restarting bot...")
    os.system("nohup python telegram_banner_bot.py &")
    exit()

# Main function
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('create_banner', create_banner))
    dp.add_handler(CommandHandler('restart', restart))
    dp.add_handler(MessageHandler(Filters.photo, handle_image))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(CallbackQueryHandler(handle_font_selection, pattern='font_.*'))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
