# Nel Culo Bot 🍑

Un bot Telegram irriverente che prende titoli di film e serie TV famosi e aggiunge "nel c*lo" alla fine, creando locandine personalizzate.

## Features
- 🎬 Genera titoli "rovinati" usando l'API di TMDB o una lista locale.
- 🖼️ Scarica la locandina originale da TMDB o cerca su DuckDuckGo se manca.
- 📢 Pubblica automaticamente su Telegram a intervalli regolari.
- 👥 Supporta iscritti multipli (`/start`, `/stop`).
- 👑 Comandi Admin (`/force`, `/users`, `/restart`).
- 🐳 Pronto per Docker e Home Assistant.

## Setup Rapido (Docker/Portainer)

1. Crea uno stack su Portainer usando questo repository.
2. Imposta le variabili d'ambiente:
   - `TELEGRAM_TOKEN`: Il token del tuo bot (da @BotFather).
   - `ADMIN_CHAT_ID`: Il tuo ID Telegram per i comandi admin.
   - `INTERVAL_MINUTES`: Ogni quanti minuti pubblicare (default: 30).
   - `TMDB_API_KEY`: (Opzionale) La tua chiave API TMDB per risultati migliori.

## 🚀 Deployment Automatico (CI/CD)

Abbiamo configurato una pipeline "magica" con GitHub Actions per aggiornare il bot automaticamente!

### Come funziona:
1. Ogni volta che facciamo un `push` sul branch `main` di GitHub...
2. ...parte un'azione automatica (`.github/workflows/deploy.yml`) sui server di GitHub.
3. Questa azione chiama un **Webhook** segreto sul nostro Portainer.
4. Portainer riceve la chiamata, scarica il nuovo codice e ricrea il container da zero.

### Configurazione:
Per far funzionare la magia, devi aggiungere il segreto su GitHub:
1. Vai su **Settings** -> **Secrets and variables** -> **Actions** nel repository.
2. Crea un nuovo secret chiamato `PORTAINER_WEBHOOK`.
3. Incolla l'URL completo del webhook di Portainer.

**⚠️ Nota Importante:**
Se il tuo Portainer è su una rete locale (es. `homeassistant.local`), GitHub non può vederlo! 
Devi usare un tunnel (es. Cloudflare Tunnel) o esporre la porta (sconsigliato senza HTTPS) per far arrivare il segnale da GitHub a casa tua.

## Sviluppo Locale
1. `pip install -r requirements.txt`
2. `python main.py`
