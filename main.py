import json
import random
import os
import requests
import logging
import sys
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from image_generator import create_image
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, JobQueue

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "1227582427:AAFM__gwYUt3z3_XBBybUHCPs3JFxqU6bto")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "160104002")
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "30"))
INTERVAL_SECONDS = INTERVAL_MINUTES * 60
LATEST_IMAGE_PATH = "current_post.jpg"
SUBSCRIBERS_FILE = "/app/data/subscribers.json" if os.path.exists("/app/data") else "subscribers.json"

# --- Subscribers Management ---

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump(list(subs), f)

def add_subscriber(chat_id):
    subs = load_subscribers()
    subs.add(str(chat_id))
    save_subscribers(subs)

def remove_subscriber(chat_id):
    subs = load_subscribers()
    chat_id_str = str(chat_id)
    if chat_id_str in subs:
        subs.remove(chat_id_str)
        save_subscribers(subs)

# --- Content Logic ---

def load_content():
    content = []
    # Load Movies
    try:
        with open('movies.json', 'r', encoding='utf-8') as f:
            content.extend(json.load(f))
    except FileNotFoundError:
        pass
        
    # Load TV Series
    try:
        with open('tv_series.json', 'r', encoding='utf-8') as f:
            content.extend(json.load(f))
    except FileNotFoundError:
        pass
        
    if not content:
        return ["Titolo di esempio"]
    return content

def get_poster_from_scraping(title):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        search_query = quote_plus(title)
        url = f"https://www.themoviedb.org/search?query={search_query}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        img_tag = soup.select_one("div.card div.image img.poster")
        if not img_tag:
            img_tag = soup.select_one(".results .card img")
        if img_tag:
            poster_url = img_tag.get('src') or img_tag.get('data-src')
            if poster_url:
                if poster_url.startswith('/'):
                    poster_url = f"https://www.themoviedb.org{poster_url}"
                poster_url = poster_url.replace("w220_and_h330_face", "original")
                poster_url = poster_url.replace("w94_and_h141_bestv2", "original")
                return poster_url
    except Exception as e:
        logger.error(f"Error scraping poster: {e}")
    return None

def get_content_data():
    content_list = load_content()
    title = random.choice(content_list)
    ruined_title = f"{title} nel c*lo"
    logger.info(f"Searching poster for: {title}")
    poster_url = get_poster_from_scraping(title)
    return title, ruined_title, poster_url

async def generate_and_broadcast(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Starting broadcast job...")
    
    # Get subscribers
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("No subscribers. Skipping.")
        return

    try:
        # 1. Generate Content (Once for everyone)
        original_title, ruined_title, poster_url = get_content_data()
        logger.info(f"Selected: {original_title} -> {ruined_title}")
        
        # 2. Generate Image
        create_image(ruined_title, LATEST_IMAGE_PATH, background_url=poster_url)
        
        # 3. Broadcast
        for chat_id in subscribers:
            try:
                await context.bot.send_photo(chat_id=chat_id, photo=open(LATEST_IMAGE_PATH, 'rb'), caption=ruined_title)
                logger.info(f"Sent to {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send to {chat_id}: {e}")
                # Optional: Remove user if blocked
                # remove_subscriber(chat_id) 

        logger.info("Broadcast finished.")
    except Exception as e:
        logger.error(f"Error in job: {e}")

# --- Command Handlers ---

def is_admin(update: Update):
    return str(update.effective_chat.id) == str(ADMIN_CHAT_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    add_subscriber(chat_id)
    msg = f"🍑 Bot Avviato!\nSei iscritto alla lista di distribuzione.\nPubblicherò un film nel c*lo ogni {INTERVAL_MINUTES} minuti.\nComandi:\n/stop - Disiscriviti"
    
    if is_admin(update):
        msg += "\n\n👑 Comandi Admin:\n/users - Lista utenti\n/force - Invia subito\n/restart - Riavvia bot"
        
    await context.bot.send_message(chat_id=chat_id, text=msg)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    remove_subscriber(chat_id)
    await context.bot.send_message(chat_id=chat_id, text="❌ Ti sei disiscritto. Non riceverai più aggiornamenti.")

# --- Admin Commands ---

async def force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return # Ignore non-admins
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Generazione e invio a TUTTI in corso...")
    # Trigger manually
    await generate_and_broadcast(context)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
        
    subs = load_subscribers()
    count = len(subs)
    
    msg = f"👥 Utenti iscritti: {count}\n\n"
    for sub in subs:
        msg += f"- `{sub}`\n"
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
        
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🔄 Riavvio del bot in corso...")
    
    # Restart the script
    os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("Manca il TOKEN!")
        exit(1)
        
    # Ensure admin is subscribed
    if ADMIN_CHAT_ID:
        add_subscriber(ADMIN_CHAT_ID)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    
    # Admin Handlers
    application.add_handler(CommandHandler("force", force))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("restart", restart))
    
    # Start the periodic job
    application.job_queue.run_repeating(generate_and_broadcast, interval=INTERVAL_SECONDS, first=10, name='broadcast_job')

    logger.info("Bot is polling...")
    application.run_polling()
