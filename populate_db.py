import json
import urllib.request
import os

# 1. Lista curata di "Cult Italiani"
italian_cults = [
    "Natale in India", "Natale sul Nilo", "Natale a Miami", "Natale a New York", "Natale in Crociera",
    "Natale a Rio", "Natale a Beverly Hills", "Natale in Sudafrica", "Vacanze di Natale", "Vacanze in America",
    "Yuppies", "Fracchia la belva umana", "Fantozzi", "Il secondo tragico Fantozzi", "Fantozzi contro tutti",
    "Fantozzi subisce ancora", "Fantozzi va in pensione", "Fantozzi alla riscossa", "Fantozzi in paradiso",
    "Tre uomini e una gamba", "Così è la vita", "Chiedimi se sono felice", "La leggenda di Al, John e Jack",
    "Il ricco, il povero e il maggiordomo", "Checco Zalone", "Cado dalle nubi", "Sole a catinelle", "Quo vado?",
    "Tolo Tolo", "Benvenuti al Sud", "Benvenuti al Nord", "Maschi contro femmine", "Femmine contro maschi",
    "Notte prima degli esami", "Ex", "Manuale d'amore", "Immaturi", "Perfetti sconosciuti", "Lo chiamavano Jeeg Robot",
    "Suburra", "Gomorra", "Romanzo Criminale", "Il Padrino", "Il Padrino - Parte II", "Il Padrino - Parte III",
    "La vita è bella", "Nuovo Cinema Paradiso", "La grande bellezza", "8½", "La dolce vita", "Amarcord",
    "Ladri di biciclette", "Riso amaro", "I soliti ignoti", "Amici miei", "Il marchese del grillo", "Bianco, rosso e Verdone",
    "Un sacco bello", "Viaggi di nozze", "Gallo cedrone", "Grande, grosso e Verdone", "Attila flagello di Dio",
    "Eccezzziunale veramente", "Al bar dello sport", "L'allenatore nel pallone", "Mezzo destro mezzo sinistro",
    "Sapore di mare", "Abbronzatissimi", "Rimini Rimini", "Vacanze di Natale '95", "Paparazzi", "Tifosi",
    "Body Guards", "Merry Christmas", "Natale sul Nilo", "Natale in India", "Christmas in Love", "Natale a Miami",
    "Natale a New York", "Natale in Crociera", "Natale a Rio", "Natale a Beverly Hills", "Natale in Sudafrica",
    "Vacanze di Natale a Cortina", "Colpi di fulmine", "Colpi di fortuna", "Un Natale stupefacente", "Natale col boss",
    "Natale a Londra - Dio salvi la regina", "Poveri ma ricchi", "Poveri ma ricchissimi", "Amici come prima",
    "In vacanza su Marte", "Boris - Il film", "Smetto quando voglio", "Smetto quando voglio - Masterclass",
    "Smetto quando voglio - Ad honorem", "Fantaghirò", "L'allenatore nel pallone 2", "Alex l'ariete"
]

def download_wikipedia_movies():
    print("Scaricamento dataset film Wikipedia...")
    url = "https://raw.githubusercontent.com/prust/wikipedia-movie-data/master/movies.json"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        
        # Filtriamo per avere titoli decenti (es. dal 1990 in poi e solo titoli che non sono troppo lunghi)
        titles = []
        for movie in data:
            year = movie.get('year', 0)
            title = movie.get('title', '')
            
            # Prendiamo film dal 1990 in poi per avere roba più pop/conosciuta
            if year >= 1990 and len(title) < 50:
                titles.append(title)
                
        print(f"Trovati {len(titles)} film dal dataset Wikipedia.")
        return titles
    except Exception as e:
        print(f"Errore download: {e}")
        return []

def main():
    # 1. Scarica dataset
    wiki_titles = download_wikipedia_movies()
    
    # 2. Unisci con i cult italiani
    # Aggiungiamo i cult italiani
    final_list = wiki_titles + italian_cults
    
    # 3. Rimuovi duplicati
    unique_list = list(set(final_list))
    print(f"Totale titoli unici: {len(unique_list)}")
    
    # 4. Salva
    with open('movies.json', 'w', encoding='utf-8') as f:
        json.dump(unique_list, f, ensure_ascii=False)
    
    print("movies.json aggiornato con successo!")

if __name__ == "__main__":
    main()
