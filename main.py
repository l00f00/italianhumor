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
    Only works if API Key is valid.
    """
    if not TMDB_API_KEY:
        return None, None
        
    try:
        # Randomly choose between Movie and TV
        is_movie = random.choice([True, False])
        
        # Random page (popular content usually goes up to 500 pages)
        page = random.randint(1, 50) 
        
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
                poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
            else:
                poster_url = None
                
            return title, poster_url
            
    except Exception as e:
        logger.error(f"Error fetching from TMDB: {e}")
        return None, None

    return None, None

def get_poster_from_scraping(title):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        search_query = quote_plus(title)
        url = f"https://www.themoviedb.org/search?query={search_query}"
        response = requests.get(url, headers=headers, timeout=10)
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
    # 1. Try TMDB API first
    title, poster_url = get_random_movie_or_tv()
    
    # 2. Fallback to local files + Scraping
    if not title:
        logger.info("Using local content fallback")
        try:
            content_list = []
            if os.path.exists('movies.json'):
                with open('movies.json', 'r', encoding='utf-8') as f:
                    content_list.extend(json.load(f))
            if os.path.exists('tv_series.json'):
                with open('tv_series.json', 'r', encoding='utf-8') as f:
                    content_list.extend(json.load(f))
            
            if content_list:
                title = random.choice(content_list)
                # Now scrape the poster for this local title
                poster_url = get_poster_from_scraping(title)
            else:
                title = "Titolo Default"
                poster_url = None
        except Exception as e:
            logger.error(f"Error reading local files: {e}")
            title = "Errore Lettura"
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
