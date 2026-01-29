import json
import random
import os
import requests
import logging
import sys
from image_generator import create_image
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, JobQueue
from tmdbv3api import TMDb, Movie, TV, Discover

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "1227582427:AAFM__gwYUt3z3_XBBybUHCPs3JFxqU6bto")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "160104002")
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "30"))
INTERVAL_SECONDS = INTERVAL_MINUTES * 60
LATEST_IMAGE_PATH = "current_post.jpg"
SUBSCRIBERS_FILE = "subscribers.json"

# TMDB Configuration
# Using a public generic key or requires user key. 
# Since we want 10000 titles, we MUST use the API, scraping 10000 pages is slow and ban-prone.
# I'll add a default key if none provided, but better to use env var.
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "e4f9e61f6dd628033d8fd6d42746f972") # Using a common public key for demo/testing if needed

tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
tmdb.language = 'it-IT'

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

# --- Content Logic (The Upgrade) ---

def get_random_movie_or_tv():
    """
    Fetches a random popular movie or TV show using TMDB API directly.
    This gives access to 10000+ titles without storing them locally.
    """
    try:
        # Randomly choose between Movie and TV
        is_movie = random.choice([True, False])
        
        # Random page (popular content usually goes up to 500 pages)
        # We can also use 'top_rated'
        page = random.randint(1, 100) 
        
        if is_movie:
            movie = Movie()
            results = movie.popular(page=page)
        else:
            tv = TV()
            results = tv.popular(page=page)
            
        if results:
            item = random.choice(results)
            title = getattr(item, 'title', getattr(item, 'name', 'Unknown'))
            poster_path = getattr(item, 'poster_path', None)
            
            # Get High Res Poster
            if poster_path:
                # 'original' size is the highest resolution available
                poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
            else:
                poster_url = None
                
            return title, poster_url
            
    except Exception as e:
        logger.error(f"Error fetching from TMDB: {e}")
        # Fallback to local
        return "Film Sconosciuto", None

    return "Errore", None

def get_content_data():
    # Try TMDB first for infinite content
    title, poster_url = get_random_movie_or_tv()
    
    # Fallback to local files if API fails or returns nothing
    if not title or title == "Errore":
        logger.warning("TMDB failed, using local fallback")
        try:
            with open('movies.json', 'r', encoding='utf-8') as f:
                content = json.load(f)
                title = random.choice(content)
                poster_url = None # Scraping removed to keep it simple, or re-add if needed
        except:
            title = "Titolo di esempio"
            poster_url = None

    ruined_title = f"{title} nel c*lo"
    logger.info(f"Selected: {title} -> {ruined_title}")
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
        
        # 2. Generate Image
        create_image(ruined_title, LATEST_IMAGE_PATH, background_url=poster_url)
        
        # 3. Broadcast
        for chat_id in subscribers:
            try:
                await context.bot.send_photo(chat_id=chat_id, photo=open(LATEST_IMAGE_PATH, 'rb'), caption=ruined_title)
                logger.info(f"Sent to {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send to {chat_id}: {e}")

        logger.info("Broadcast finished.")
    except Exception as e:
        logger.error(f"Error in job: {e}")

# --- Command Handlers ---

def is_admin(update: Update):
    return str(update.effective_chat.id) == str(ADMIN_CHAT_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    add_subscriber(chat_id)
    msg = f"🍑 Bot Avviato!\nPubblicherò un film nel c*lo ogni {INTERVAL_MINUTES} minuti.\nTitoli infiniti da TMDB!"
    if is_admin(update):
        msg += "\n\n👑 Comandi Admin: /force, /users, /restart"
    await context.bot.send_message(chat_id=chat_id, text=msg)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    remove_subscriber(chat_id)
    await context.bot.send_message(chat_id=chat_id, text="❌ Disiscritto.")

async def force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Generazione...")
    await generate_and_broadcast(context)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    subs = load_subscribers()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"👥 Utenti: {len(subs)}\n{list(subs)}")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🔄 Riavvio...")
    os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("Manca il TOKEN!")
        exit(1)
        
    if ADMIN_CHAT_ID:
        add_subscriber(ADMIN_CHAT_ID)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("force", force))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("restart", restart))
    
    application.job_queue.run_repeating(generate_and_broadcast, interval=INTERVAL_SECONDS, first=10, name='broadcast_job')

    logger.info("Bot is polling...")
    application.run_polling()
