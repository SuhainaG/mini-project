import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    CallbackContext, CallbackQueryHandler, ConversationHandler,
    MessageHandler
)
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
from datetime import datetime
from flask_bcrypt import Bcrypt
import re

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# MongoDB setup
try:
    client = MongoClient("mongodb://localhost:27017/")
    # Test the connection
    client.server_info()
    db = client["bloodr"]
    users_collection = db["users"]
    donation_requests_collection = db["donation_requests"]
    logger = logging.getLogger(__name__)
    logger.info("MongoDB connection successful")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f"MongoDB connection error: {e}")
    raise Exception("Failed to connect to MongoDB")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Bcrypt for password hashing
bcrypt = Bcrypt()

# States for ConversationHandler
(
    USERNAME, EMAIL, PHONE, ADDRESS, CITY, PASSWORD, 
    BLOOD_DONOR, BLOOD_GROUP, ORGAN_DONOR, ORGAN_GROUP
) = range(10)

# Keyboard layouts
blood_groups = [
    ['A+', 'A-', 'B+', 'B-'],
    ['AB+', 'AB-', 'O+', 'O-']
]

organ_options = [
    ['Kidney', 'Liver'],
    ['Heart', 'Corneas'],
    ['Done']
]

yes_no = [['Yes'], ['No']]

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r'^\+?1?\d{9,15}$'
    return re.match(pattern, phone) is not None

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("Find Blood Donor ", callback_data='find_blood'),
            InlineKeyboardButton("Find Organ Donor ", callback_data='find_organ')
        ],
        [
            InlineKeyboardButton("Register as Donor ", callback_data='register'),
            InlineKeyboardButton("Help ", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to Blood & Organ Donor Bot! \n\n"
        "I can help you find blood and organ donors, or register as a donor yourself.\n"
        "Please select an option:",
        reply_markup=reply_markup
    )

async def start_registration(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text(
            "Welcome to the donor registration process! \n\n"
            "I'll guide you through each step. You can cancel anytime by typing /cancel.\n\n"
            "First, please enter your username (how you'd like to be called):"
        )
    else:
        await update.message.reply_text(
            "Welcome to the donor registration process! \n\n"
            "I'll guide you through each step. You can cancel anytime by typing /cancel.\n\n"
            "First, please enter your username (how you'd like to be called):"
        )
    return USERNAME

async def get_email(update: Update, context: CallbackContext):
    username = update.message.text
    if len(username) < 3:
        await update.message.reply_text("Username must be at least 3 characters long. Please try again:")
        return USERNAME
    
    context.user_data['username'] = username
    await update.message.reply_text(
        "Great! Now, please enter your email address.\n"
        "This will be used for logging into the web platform."
    )
    return EMAIL

async def get_phone(update: Update, context: CallbackContext):
    email = update.message.text
    if not validate_email(email):
        await update.message.reply_text(
            "Invalid email format. Please enter a valid email address:"
        )
        return EMAIL
    
    if users_collection.find_one({'email': email}):
        await update.message.reply_text(
            "This email is already registered. Please use a different email address:"
        )
        return EMAIL
    
    context.user_data['email'] = email
    await update.message.reply_text(
        "Please enter your phone number.\n"
        "This will be used to contact you in case of donation requests."
    )
    return PHONE

async def get_address(update: Update, context: CallbackContext):
    phone = update.message.text
    if not validate_phone(phone):
        await update.message.reply_text(
            "Invalid phone number format. Please enter a valid phone number:"
        )
        return PHONE
    
    context.user_data['phone'] = phone
    await update.message.reply_text(
        "Please enter your complete address.\n"
        "This helps us match you with nearby donation requests."
    )
    return ADDRESS

async def get_city(update: Update, context: CallbackContext):
    context.user_data['address'] = update.message.text
    await update.message.reply_text(
        "Please enter your city name.\n"
        "This helps in location-based donor matching."
    )
    return CITY

async def get_password(update: Update, context: CallbackContext):
    context.user_data['city'] = update.message.text
    await update.message.reply_text(
        "Please create a password for your account.\n"
        "This will be used to log in to the web platform.\n"
        "Make sure it's at least 6 characters long."
    )
    return PASSWORD

async def get_blood_donor(update: Update, context: CallbackContext):
    password = update.message.text
    if len(password) < 6:
        await update.message.reply_text(
            "Password must be at least 6 characters long. Please try again:"
        )
        return PASSWORD
    
    context.user_data['password'] = password
    reply_markup = ReplyKeyboardMarkup(yes_no, one_time_keyboard=True)
    await update.message.reply_text(
        "Would you like to register as a blood donor? ",
        reply_markup=reply_markup
    )
    return BLOOD_DONOR

async def get_blood_group(update: Update, context: CallbackContext):
    response = update.message.text.lower()
    context.user_data['blood_donor'] = response == 'yes'
    
    if response == 'yes':
        reply_markup = ReplyKeyboardMarkup(blood_groups, one_time_keyboard=True)
        await update.message.reply_text(
            "What is your blood group? ",
            reply_markup=reply_markup
        )
        return BLOOD_GROUP
    else:
        reply_markup = ReplyKeyboardMarkup(yes_no, one_time_keyboard=True)
        await update.message.reply_text(
            "Would you like to register as an organ donor? ",
            reply_markup=reply_markup
        )
        return ORGAN_DONOR

async def get_organ_donor(update: Update, context: CallbackContext):
    if 'blood_group' not in context.user_data and context.user_data.get('blood_donor'):
        context.user_data['blood_group'] = update.message.text
    
    reply_markup = ReplyKeyboardMarkup(yes_no, one_time_keyboard=True)
    await update.message.reply_text(
        "Would you like to register as an organ donor? ",
        reply_markup=reply_markup
    )
    return ORGAN_DONOR

async def get_organ_group(update: Update, context: CallbackContext):
    response = update.message.text.lower()
    context.user_data['organ_donor'] = response == 'yes'
    context.user_data['organ_group'] = []
    
    if response == 'yes':
        reply_markup = ReplyKeyboardMarkup(organ_options, one_time_keyboard=True)
        await update.message.reply_text(
            "Which organs would you like to donate? Select each option one by one.\n"
            "Click 'Done' when you've selected all organs you wish to donate.",
            reply_markup=reply_markup
        )
        return ORGAN_GROUP
    else:
        return await save_registration(update, context)

async def handle_organ_selection(update: Update, context: CallbackContext):
    choice = update.message.text
    
    if choice == 'Done':
        if not context.user_data.get('organ_group'):
            await update.message.reply_text(
                "Please select at least one organ or choose 'No' for organ donation."
            )
            return ORGAN_GROUP
        return await save_registration(update, context)
    
    if 'organ_group' not in context.user_data:
        context.user_data['organ_group'] = []
    
    if choice not in context.user_data['organ_group']:
        context.user_data['organ_group'].append(choice)
    
    reply_markup = ReplyKeyboardMarkup(organ_options, one_time_keyboard=True)
    await update.message.reply_text(
        f"Added {choice} to your organ donation list. \n"
        "Select another organ or click 'Done' to finish registration.",
        reply_markup=reply_markup
    )
    return ORGAN_GROUP

async def save_registration(update: Update, context: CallbackContext):
    try:
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(context.user_data['password']).decode('utf-8')
        
        # Prepare user data
        user_data = {
            'username': context.user_data['username'],
            'email': context.user_data['email'],
            'phone': context.user_data['phone'],
            'address': context.user_data['address'],
            'city': context.user_data['city'].lower(),
            'password': hashed_password,
            'blood_donor': context.user_data.get('blood_donor', False),
            'blood_group': context.user_data.get('blood_group'),
            'organ_donor': context.user_data.get('organ_donor', False),
            'organ_group': context.user_data.get('organ_group', []),
            'is_active': True,
            'registration_date': datetime.utcnow(),
            'registered_via': 'telegram'
        }
        
        # Log the data being saved (excluding password)
        log_data = user_data.copy()
        log_data.pop('password')
        logger.info(f"Saving user data: {log_data}")
        
        # Save to MongoDB
        result = users_collection.insert_one(user_data)
        
        if result.inserted_id:
            logger.info(f"User registered successfully with ID: {result.inserted_id}")
            await update.message.reply_text(
                " Registration Successful! \n\n"
                "Thank you for registering as a donor. Your information has been saved.\n\n"
                "You can now:\n"
                "1. Log in to the web platform using your email and password\n"
                "2. Update your profile anytime\n"
                "3. Respond to donation requests\n\n"
                "Use /start to return to the main menu.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            raise Exception("Failed to insert user data")
            
    except Exception as e:
        error_msg = f"Registration error: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(
            "Sorry, there was an error during registration. Please try again later.\n"
            f"Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Registration cancelled. Use /start to return to the main menu.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def help_command(update: Update, context: CallbackContext):
    help_text = """
 *Blood & Organ Donor Bot Help*

Available commands:
/start - Start the bot
/help - Show this help message
/find_donor - Search for donors
/register - Register as a donor
/stats - View donation statistics

How to use:
1. Use /register to become a donor
2. Use /find_donor to search for donors
3. Select blood or organ donation
4. Follow the prompts

For emergency assistance, please contact your nearest hospital directly.

Need more help? Contact the admin through the website.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def find_donor(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("Blood Donor ", callback_data='search_blood'),
            InlineKeyboardButton("Organ Donor ", callback_data='search_organ')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "What type of donor are you looking for?",
        reply_markup=reply_markup
    )

async def stats(update: Update, context: CallbackContext):
    total_users = users_collection.count_documents({})
    blood_donors = users_collection.count_documents({'blood_donor': 'yes'})
    organ_donors = users_collection.count_documents({'organ_donor': 'yes'})
    active_requests = donation_requests_collection.count_documents({'status': 'pending'})
    
    stats_text = f"""
 *Current Statistics*

 Total Registered Users: {total_users}
 Blood Donors: {blood_donors}
 Organ Donors: {organ_donors}
 Active Requests: {active_requests}
    """
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        help_text = """
 *Blood & Organ Donor Bot Help*

Available commands:
/start - Start the bot
/help - Show this help message
/find_donor - Search for donors
/register - Register as a donor
/stats - View donation statistics

For emergency assistance, please contact your nearest hospital directly.
        """
        await query.message.reply_text(help_text, parse_mode='Markdown')
    
    elif query.data == 'find_blood':
        keyboard = [
            [InlineKeyboardButton(bg, callback_data=f'blood_{bg}') for bg in ['A+', 'A-']],
            [InlineKeyboardButton(bg, callback_data=f'blood_{bg}') for bg in ['B+', 'B-']],
            [InlineKeyboardButton(bg, callback_data=f'blood_{bg}') for bg in ['AB+', 'AB-']],
            [InlineKeyboardButton(bg, callback_data=f'blood_{bg}') for bg in ['O+', 'O-']]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select blood group needed:", reply_markup=reply_markup)
    
    elif query.data.startswith('blood_'):
        blood_group = query.data.replace('blood_', '')
        donors = users_collection.find({
            'blood_donor': 'yes',
            'blood_group': blood_group
        }).limit(5)
        
        response = f" Found donors for blood group {blood_group}:\n\n"
        found = False
        for donor in donors:
            found = True
            response += f" Name: {donor['username']}\n City: {donor['city']}\n Phone: {donor['phone']}\n\n"
        
        if not found:
            response = f" No donors found for blood group {blood_group}.\nPlease try again later or check our website."
        
        await query.message.reply_text(response)
    
    elif query.data == 'find_organ':
        keyboard = [
            [InlineKeyboardButton("Kidney", callback_data='organ_kidney')],
            [InlineKeyboardButton("Liver", callback_data='organ_liver')],
            [InlineKeyboardButton("Heart", callback_data='organ_heart')],
            [InlineKeyboardButton("Eyes", callback_data='organ_eyes')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select organ type needed:", reply_markup=reply_markup)
    
    elif query.data.startswith('organ_'):
        organ_type = query.data.replace('organ_', '')
        donors = users_collection.find({
            'organ_donor': 'yes',
            'organ_group': organ_type
        }).limit(5)
        
        response = f" Found donors for {organ_type}:\n\n"
        found = False
        for donor in donors:
            found = True
            response += f" Name: {donor['username']}\n City: {donor['city']}\n Phone: {donor['phone']}\n\n"
        
        if not found:
            response = f" No donors found for {organ_type}.\nPlease try again later or check our website."
        
        await query.message.reply_text(response)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_registration, pattern='^register$'),
            CommandHandler('register', start_registration)
        ],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_blood_donor)],
            BLOOD_DONOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_blood_group)],
            BLOOD_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_organ_donor)],
            ORGAN_DONOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_organ_group)],
            ORGAN_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_organ_selection)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("find_donor", find_donor))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
