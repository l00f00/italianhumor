import requests
from bs4 import BeautifulSoup
import json
import time
import random

def scrape_tmdb_titles(max_pages=50):
    base_url = "https://www.themoviedb.org/movie"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    all_titles = []
    
    print(f"Inizio scraping di {max_pages} pagine da TMDB (lingua IT)...")
    
    for page in range(1, max_pages + 1):
        try:
            url = f"{base_url}?page={page}&language=it-IT"
            r = requests.get(url, headers=headers)
            
            if r.status_code != 200:
                print(f"Errore pagina {page}: {r.status_code}")
                break
                
            soup = BeautifulSoup(r.text, 'lxml')
            
            # Selettori per i titoli nelle card
            # Di solito sono in <h2> o simili dentro .card
            movie_cards = soup.select('.card .content h2 a')
            
            page_titles = [a.text.strip() for a in movie_cards if a.text.strip()] # Filtro vuoti
            
            if not page_titles:
                # Provo selettore alternativo se cambia l'html
                movie_cards = soup.select('.title h2 a')
                page_titles = [a.text.strip() for a in movie_cards if a.text.strip()]
            
            all_titles.extend(page_titles)
            
            print(f"Pagina {page}: Trovati {len(page_titles)} titoli. Totale: {len(all_titles)}")
            
            # Delay per non essere bannati
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"Eccezione pagina {page}: {e}")
            
    return list(set(all_titles)) # Rimuovi duplicati

def main():
    # 1. Scrape
    # Scarichiamo 100 pagine = 2000 film top del momento/storici
    tmdb_titles = scrape_tmdb_titles(max_pages=100)
    
    # 2. Aggiungi i nostri cult manuali (per sicurezza)
    from populate_db import italian_cults
    final_list = tmdb_titles + italian_cults
    
    # 3. Salva
    unique_list = list(set(final_list))
    
    # Filtro titoli troppo lunghi o strani
    clean_list = [t for t in unique_list if len(t) < 60]
    
    print(f"Salvataggio di {len(clean_list)} titoli in movies.json...")
    
    with open('movies.json', 'w', encoding='utf-8') as f:
        json.dump(clean_list, f, ensure_ascii=False)
        
    print("Fatto!")

if __name__ == "__main__":
    main()
