import json
import random
import os
import requests
import logging
import sys
from image_generator import create_image
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, JobQueue, TypeHandler
from tmdbv3api import TMDb, Movie, TV, Discover
from duckduckgo_search import DDGS

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
# Default interval if not set in env
# 5 hours = 300 minutes
DEFAULT_INTERVAL_MINUTES = 300 
INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", str(DEFAULT_INTERVAL_MINUTES)))

# Check config override
try:
    _config = load_config()
    if 'interval_minutes' in _config:
        INTERVAL_MINUTES = int(_config['interval_minutes'])
        logger.info(f"Loaded interval from config: {INTERVAL_MINUTES} minutes")
except Exception as e:
    logger.error(f"Error loading config: {e}")

INTERVAL_SECONDS = INTERVAL_MINUTES * 60
LATEST_IMAGE_PATH = "current_post.jpg"
SUBSCRIBERS_FILE = "subscribers.json"
CONFIG_FILE = "bot_config.json"
MOVIES_FILE = "italian_movies_list.json" # New file with 9900+ titles

# TMDB Configuration
# Using a public generic key or requires user key. 
# Since we want 10000 titles, we MUST use the API, scraping 10000 pages is slow and ban-prone.
# I'll add a default key if none provided, but better to use env var.
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "e4f9e61f6dd628033d8fd6d42746f972") # Using a common public key for demo/testing if needed

tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
tmdb.language = 'it-IT'

def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except:
            pass
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

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
        logger.warning("TMDB_API_KEY mancante! Impossibile recuperare immagini.")
        # If API key is missing, return None title so we fallback to local list + web search
        return None, None
        
    try:
        # Randomly choose between Movie and TV
        is_movie = random.choice([True, False])
        
        # Random page (popular content usually goes up to 500 pages)
        # Reduced max page to 20 to ensure higher quality/popularity and images
        page = random.randint(1, 20) 
        
        if is_movie:
            movie = Movie()
            results = movie.popular(page=page)
        else:
            tv = TV()
            results = tv.popular(page=page)
            
        if results:
            # Try up to 5 times to find an item with a poster
            for _ in range(5):
                item = random.choice(results)
                poster_path = getattr(item, 'poster_path', None)
                
                if poster_path:
                    title = getattr(item, 'title', getattr(item, 'name', 'Unknown'))
                    poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
                    return title, poster_url
            
            # If loop finishes without returning, still return a title if we found one, so we can search web
            # Pick the last item checked
            item = random.choice(results)
            title = getattr(item, 'title', getattr(item, 'name', 'Unknown'))
            logger.warning(f"Nessun poster TMDB trovato dopo 5 tentativi a pagina {page}. Uso titolo '{title}' e cercherò sul web.")
            return title, None
            
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

def get_poster_from_web(title):
    """
    Search for a movie poster on DuckDuckGo Images.
    """
    try:
        search_query = f"{title} locandina film poster"
        logger.info(f"Searching web for poster: {search_query}")
        
        with DDGS() as ddgs:
            # Search for images, max 1 result
            results = list(ddgs.images(
                keywords=search_query,
                region="it-it",
                safesearch="off",
                size="Large",
                type_image="photo",
                max_results=1
            ))
            
            if results:
                image_url = results[0].get('image')
                logger.info(f"Web search found image: {image_url}")
                return image_url
            else:
                logger.warning("Web search found no images.")
                
    except Exception as e:
        logger.error(f"Error searching web for poster: {e}")
    
    return None

def get_random_italian_title():
    """
    Loads titles from the massive local JSON list (scraped from Wikipedia).
    Filters out titles with 'bambini', 'bimbi', etc.
    """
    if not os.path.exists(MOVIES_FILE):
        logger.error(f"{MOVIES_FILE} not found! Fallback to TMDB.")
        return None
        
    try:
        with open(MOVIES_FILE, 'r', encoding='utf-8') as f:
            movies = json.load(f)
            
        if not movies:
            return None
            
        # Try to find a safe title
        for _ in range(50): # Max 50 attempts
            title = random.choice(movies)
            
            # 1. Clean title (remove " (film ...)")
            clean_title = title.split(" (film")[0]
            
            # 2. Safety Filter
            lower_title = clean_title.lower()
            forbidden_words = ["bambin", "bimbi", "bimbo", "ragazzin", "piccol", "minori", "infanzia"]
            if any(word in lower_title for word in forbidden_words):
                logger.info(f"Skipped unsafe title: {clean_title}")
                continue
            
            # 3. Recency Bias (Prefer movies from 1994-2026)
            # Try to extract year from the original string "Title (film YYYY)"
            try:
                # Extract year if present in parentheses e.g. "Matrix (film 1999)"
                if "(film " in title:
                    year_part = title.split("(film ")[1].replace(")", "")
                    if year_part.isdigit():
                        year = int(year_part)
                        # Logic: If year is outside 1994-2026, flip a coin to see if we skip it
                        # This makes recent movies MORE likely but doesn't ban old ones completely
                        if year < 1994 or year > 2026:
                            # 70% chance to skip old movies to prefer recent ones
                            if random.random() < 0.7: 
                                logger.info(f"Skipped old movie (bias): {clean_title} ({year})")
                                continue
            except Exception:
                pass # If year parsing fails, just keep the title
                
            return clean_title
            
    except Exception as e:
        logger.error(f"Error reading movies file: {e}")
        
    return None

def get_content_data():
    # 1. Try Local Italian List first (Priority!)
    title = get_random_italian_title()
    poster_url = None
    
    # 2. If local list failed, fallback to TMDB random
    if not title:
        logger.info("Local list failed/empty. Falling back to TMDB API random.")
        title, poster_url = get_random_movie_or_tv()
    
    # 3. If we have a title (from local or TMDB) but no poster yet, search Web
    if title and not poster_url:
        logger.info(f"Need poster for '{title}'. Searching Web...")
        poster_url = get_poster_from_web(title)

    # 4. Ultimate Fallback
    if not title:
        title = "Titolo Default"
        poster_url = None

    # Apply Simple Ruin Logic (Suffix only, safer)
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
    msg = (
        f"🍑 *Benvenuto in NelCuloBot2!* 🍑\n\n"
        f"Preparati a vedere i grandi classici del cinema come non li hai mai visti (o sentiti) prima.\n"
        f"Pubblicherò un capolavoro rovinato circa 6 volte al giorno.\n\n"
        "Tieniti forte! 🚀"
    )
    if is_admin(update):
        msg += "\n\n👑 Comandi Admin: /force, /users, /restart, /broadcast, /import_subs, /test_title, /set_interval"
    
    # Debug info for everyone
    msg += f"\n\n🆔 Tuo ID: `{chat_id}`"
    
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

    # Notify Admin of new subscriber
    if ADMIN_CHAT_ID and str(chat_id) != str(ADMIN_CHAT_ID):
        try:
            user = update.effective_user
            username = f"@{user.username}" if user.username else "N/A"
            full_name = user.full_name
            admin_msg = (
                f"🔔 *Nuovo Utente Iscritto!* 🔔\n\n"
                f"👤 Nome: {full_name}\n"
                f"🔗 Username: {username}\n"
                f"🆔 ID: `{chat_id}`"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to notify admin about new user: {e}")

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=f"🆔 Il tuo ID è: `{chat_id}`", parse_mode='Markdown')

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

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to send a text message to all subscribers.
    Usage: /broadcast <message>
    """
    if not is_admin(update):
        return
        
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Uso: /broadcast <messaggio>")
        return

    message = " ".join(context.args)
    subscribers = load_subscribers()
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"📣 Invio a {len(subscribers)} utenti...")
    
    count = 0
    for chat_id in subscribers:
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📢 *COMUNICAZIONE UFFICIALE:*\n\n{message}", parse_mode='Markdown')
            count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to {chat_id}: {e}")
            
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Inviato correttamente a {count}/{len(subscribers)} utenti.")

async def import_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to import subscribers from a list (JSON or space-separated).
    Usage: /import_subs 123 456 789 or /import_subs ["123", "456"]
    """
    if not is_admin(update):
        return
    
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Uso: /import_subs ID1 ID2 ... oppure incolla una lista JSON")
        return

    # Join args to get the full string
    raw_input = " ".join(context.args)
    
    new_subs = set()
    
    # Try parsing as JSON first
    try:
        json_subs = json.loads(raw_input)
        if isinstance(json_subs, list):
            for s in json_subs:
                new_subs.add(str(s))
    except json.JSONDecodeError:
        # Fallback: treat as space/comma separated
        cleaned = raw_input.replace(",", " ").replace("[", " ").replace("]", " ").replace("'", " ").replace('"', " ")
        parts = cleaned.split()
        for p in parts:
            if p.strip().isdigit():
                new_subs.add(p.strip())

    if not new_subs:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Nessun ID valido trovato.")
        return

    current_subs = load_subscribers()
    initial_count = len(current_subs)
    
    current_subs.update(new_subs)
    save_subscribers(current_subs)
    
    added_count = len(current_subs) - initial_count
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"✅ Importati {added_count} nuovi iscritti.\n👥 Totale attuale: {len(current_subs)}"
    )

async def test_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to test title generation without image.
    """
    if not is_admin(update):
        return
        
    title = get_random_italian_title()
    if not title:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Errore nel recupero titolo (DB vuoto?)")
        return
        
    ruined = f"{title} nel c*lo"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🧪 *Test Titolo:*\n\nOriginale: {title}\nRovinato: {ruined}", parse_mode='Markdown')

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to change the posting interval.
    Usage: /set_interval <minutes>
    """
    if not is_admin(update):
        return
        
    if not context.args or not context.args[0].isdigit():
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Uso: /set_interval <minuti>\nEsempio: /set_interval 240 (per 4 ore)")
        return
        
    new_interval = int(context.args[0])
    if new_interval < 1:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ L'intervallo deve essere almeno 1 minuto.")
        return
        
    # Remove existing jobs
    current_jobs = context.job_queue.get_jobs_by_name('broadcast_job')
    for job in current_jobs:
        job.schedule_removal()
        
    # Schedule new job
    context.job_queue.run_repeating(generate_and_broadcast, interval=new_interval * 60, first=10, name='broadcast_job')
    
    # Save to config
    config = load_config()
    config['interval_minutes'] = new_interval
    save_config(config)
    
    # Update global var for display purposes (though restart will reload it properly)
    global INTERVAL_MINUTES
    INTERVAL_MINUTES = new_interval
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"✅ Intervallo aggiornato a {new_interval} minuti.\nIl prossimo post arriverà tra pochi secondi (reset timer)."
    )

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🔄 Riavvio...")
    os.execv(sys.executable, ['python'] + sys.argv)

async def handle_reactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Notifies admin when a user reacts to a message.
    """
    try:
        if not update.message_reaction:
            return

        user = update.message_reaction.user
        chat_id = update.message_reaction.chat.id
        message_id = update.message_reaction.message_id
        
        # Get the new reaction (if any)
        new_reaction = update.message_reaction.new_reaction
        emoji = new_reaction[0].emoji if new_reaction else "reaction removed"
        
        if not user:
            return

        # Don't notify if admin reacts (spam prevention)
        if str(user.id) == str(ADMIN_CHAT_ID):
            return

        user_name = f"@{user.username}" if user.username else user.full_name
        
        msg = (
            f"🔔 *Nuova Reazione!* 🔔\n\n"
            f"👤 Utente: {user_name}\n"
            f"😍 Reazione: {emoji}\n"
            f"🔗 [Vai al messaggio](https://t.me/c/{str(chat_id).replace('-100', '')}/{message_id})"
        )
        
        if ADMIN_CHAT_ID:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error handling reaction: {e}")

async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Allow users to suggest a title.
    Usage: /suggest Matrix
    """
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Uso: /suggest <Titolo del film>")
        return

    title_suggestion = " ".join(context.args)
    user = update.effective_user
    user_name = f"@{user.username}" if user.username else user.full_name
    user_id = user.id

    # Confirm to user
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"✅ Grazie {user.first_name}! Ho inviato il tuo suggerimento all'admin: *{title_suggestion}*"
    , parse_mode='Markdown')

    # Notify Admin
    if ADMIN_CHAT_ID:
        clean_title = title_suggestion.replace("'", "").replace('"', "")
        admin_msg = (
            f"💡 *Nuovo Suggerimento!* 💡\n\n"
            f"👤 Utente: {user_name} (`{user_id}`)\n"
            f"🎬 Titolo: *{title_suggestion}*\n\n"
            f"Pubblica subito con:\n`/publish {title_suggestion}`\n\n"
            f"Pubblica citando l'utente:\n`/publish_credit {user_name} {title_suggestion}`"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='Markdown')

async def publish_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to publish a specific title.
    Usage: /publish Matrix
    """
    if not is_admin(update):
        return
        
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Uso: /publish <Titolo>")
        return

    title = " ".join(context.args)
    await process_custom_publish(update, context, title)

async def publish_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to publish a specific title with credit.
    Usage: /publish_credit @username Matrix
    """
    if not is_admin(update):
        return
        
    if len(context.args) < 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Uso: /publish_credit <Utente> <Titolo>")
        return

    user_credit = context.args[0]
    title = " ".join(context.args[1:])
    
    await process_custom_publish(update, context, title, credit=user_credit)

async def process_custom_publish(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str, credit: str = None):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=f"⏳ Elaborazione di: *{title}*...", parse_mode='Markdown')
    
    # 1. Search Poster
    poster_url = get_poster_from_web(title)
    if not poster_url:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Nessuna copertina trovata sul web. Uso background generico.")
    
    # 2. Ruin Title
    ruined_title = f"{title} nel c*lo"
    
    # 3. Generate Image
    try:
        create_image(ruined_title, LATEST_IMAGE_PATH, background_url=poster_url)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Errore generazione immagine: {e}")
        return

    # 4. Broadcast
    subscribers = load_subscribers()
    await context.bot.send_message(chat_id=chat_id, text=f"📣 Invio a {len(subscribers)} utenti...")
    
    caption = ruined_title
    if credit:
        caption += f"\n\n💡 Suggerito da: {credit}"

    count = 0
    for sub_id in subscribers:
        try:
            await context.bot.send_photo(chat_id=sub_id, photo=open(LATEST_IMAGE_PATH, 'rb'), caption=caption)
            count += 1
        except Exception as e:
            logger.error(f"Failed to send to {sub_id}: {e}")

    await context.bot.send_message(chat_id=chat_id, text=f"✅ Pubblicato con successo a {count} utenti!")

async def post_init(application: ApplicationBuilder):
    """
    Setup commands automatically on startup.
    """
    commands = [
        BotCommand("start", "Avvia il bot e iscriviti"),
        BotCommand("stop", "Disiscriviti dal bot"),
        BotCommand("suggest", "Suggerisci un titolo"),
        BotCommand("id", "Mostra il tuo Telegram ID"),
        BotCommand("force", "(Admin) Forza l'invio di un post"),
        BotCommand("users", "(Admin) Lista ID iscritti"),
        BotCommand("broadcast", "(Admin) Invia messaggio a tutti"),
        BotCommand("import_subs", "(Admin) Importa iscritti"),
        BotCommand("publish", "(Admin) Pubblica titolo custom"),
        BotCommand("publish_credit", "(Admin) Pubblica con credit"),
        BotCommand("test_title", "(Admin) Test generazione titolo"),
        BotCommand("set_interval", "(Admin) Imposta frequenza post"),
        BotCommand("restart", "(Admin) Riavvia il bot"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Comandi bot aggiornati su Telegram!")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        logger.error("❌ ERRORE CRITICO: Variabile d'ambiente TELEGRAM_TOKEN mancante!")
        logger.error("Assicurati di aver impostato TELEGRAM_TOKEN nel docker-compose o in Portainer.")
        exit(1)
    
    # Masked token logging for debugging
    masked_token = f"{TELEGRAM_TOKEN[:5]}...{TELEGRAM_TOKEN[-5:]}" if len(TELEGRAM_TOKEN) > 10 else "TOO_SHORT"
    logger.info(f"Using Token: {masked_token}")

    if ADMIN_CHAT_ID:
        add_subscriber(ADMIN_CHAT_ID)

    try:
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
        
        # Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("id", my_id))
        application.add_handler(CommandHandler("stop", stop))
        application.add_handler(CommandHandler("suggest", suggest))
        
        # Admin Handlers
        application.add_handler(CommandHandler("force", force))
        application.add_handler(CommandHandler("users", users))
        application.add_handler(CommandHandler("broadcast", broadcast_message))
        application.add_handler(CommandHandler("import_subs", import_subs))
        application.add_handler(CommandHandler("publish", publish_custom))
        application.add_handler(CommandHandler("publish_credit", publish_credit))
        application.add_handler(CommandHandler("test_title", test_title))
        application.add_handler(CommandHandler("set_interval", set_interval))
        application.add_handler(CommandHandler("restart", restart))
        
        # Reaction Handler
        application.add_handler(TypeHandler(Update, handle_reactions))
        
        # Job Queue
        if application.job_queue:
            application.job_queue.run_repeating(generate_and_broadcast, interval=INTERVAL_SECONDS, first=10, name='broadcast_job')
            logger.info(f"Job Queue avviata. Intervallo: {INTERVAL_MINUTES} minuti.")
        else:
            logger.error("JobQueue non disponibile! Assicurati di aver installato python-telegram-bot[job-queue]")

        logger.info("Bot is polling... (Premi Ctrl+C per fermare)")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ ERRORE AVVIO BOT: {e}")
        logger.error("Verifica che il token sia corretto e che non ci siano altri bot in esecuzione con lo stesso token.")
        exit(1)
