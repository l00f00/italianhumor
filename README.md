# Nel Culo Bot 🍑

Un bot Telegram irriverente che prende titoli di film e serie TV famosi e aggiunge "nel c*lo" alla fine, creando locandine personalizzate.

## Features
- 🎬 Genera titoli "rovinati" da una lista di film e serie TV.
- 🖼️ Scarica la locandina originale da TMDB (via scraping) e applica il testo modificato.
- 📢 Pubblica automaticamente su Telegram a intervalli regolari.
- 👥 Supporta iscritti multipli (`/start`, `/stop`).
- 👑 Comandi Admin (`/force`, `/users`, `/restart`).
- 🐳 Pronto per Docker e Home Assistant.

## Setup Rapido (Docker/Portainer)

1. Crea uno stack su Portainer usando questo repository.
2. Imposta le variabili d'ambiente:
   - `TELEGRAM_TOKEN`: Il token del tuo bot (da @BotFather).
   - `TELEGRAM_CHAT_ID`: (Opzionale) ID chat di default per debug.
   - `ADMIN_CHAT_ID`: Il tuo ID Telegram per i comandi admin.
   - `INTERVAL_MINUTES`: Ogni quanti minuti pubblicare (default: 30).

## Sviluppo Locale
1. `pip install -r requirements.txt`
2. `python main.py`
