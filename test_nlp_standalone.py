import spacy
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load SpaCy model for Italian
try:
    nlp = spacy.load("it_core_news_sm")
    print("Modello SpaCy caricato correttamente.")
except Exception as e:
    print(f"Errore caricamento SpaCy: {e}")
    exit(1)

def ruin_title_with_nlp(title):
    """
    Uses SpaCy to analyze the title and insert 'nel culo' in a grammatically 'funnier' position.
    """
    if not nlp:
        return f"{title} nel c*lo"

    doc = nlp(title)
    
    tokens = list(doc)
    insertion_index = -1
    
    # Iterate backwards to find the last significant noun
    for i in range(len(tokens) - 1, -1, -1):
        token = tokens[i]
        # print(f"Token: {token.text}, POS: {token.pos_}") # Debug
        if token.pos_ in ["NOUN", "PROPN"]: # Noun or Proper Noun
            insertion_index = i
            break
    
    if insertion_index != -1:
        # Reconstruct string with insertion
        new_title_parts = []
        for i, token in enumerate(tokens):
            new_title_parts.append(token.text_with_ws)
            if i == insertion_index:
                # Logic refined:
                # If we are inserting IN THE MIDDLE, we usually want "nel c*lo " (space after).
                # The 'text_with_ws' of the current token already includes the space AFTER the token.
                
                # Case 1: Insertion at the very end
                if i == len(tokens) - 1:
                     new_title_parts.append(" nel c*lo")
                # Case 2: Insertion in the middle
                else:
                     new_title_parts.append("nel c*lo ")
        
        # Join and clean up double spaces logic
        raw_result = "".join(new_title_parts)
        # Simple normalization to avoid "  "
        return " ".join(raw_result.split())
    
    return f"{title} nel c*lo"

# Test titles (30 titoli famosi vari)
test_titles = [
    "Il Signore degli Anelli",
    "Harry Potter e la Pietra Filosofale",
    "Non è un paese per vecchi",
    "Mamma ho perso l'aereo",
    "La vita è bella",
    "Tre uomini e una gamba",
    "Una settimana da Dio",
    "L'uomo che sussurrava ai cavalli",
    "Biancaneve e i sette nani",
    "Ritorno al futuro",
    "Il buono, il brutto, il cattivo",
    "C'era una volta in America",
    "La dolce vita",
    "Per un pugno di dollari",
    "Il gladiatore",
    "Guerre Stellari",
    "Alla ricerca di Nemo",
    "La grande bellezza",
    "Il Padrino",
    "Forrest Gump",
    "La carica dei 101",
    "Lo chiamavano Trinità",
    "Arancia Meccanica",
    "Il silenzio degli innocenti",
    "Pulp Fiction",
    "Salvate il soldato Ryan",
    "La fabbrica di cioccolato",
    "L'attimo fuggente",
    "Nuovo Cinema Paradiso",
    "A qualcuno piace caldo",
    "I soliti ignoti",
    "Vacanze romane",
    "Ladri di biciclette",
    "Una poltrona per due",
    "La leggenda del pianista sull'oceano",
    "Sette anime",
    "L'era glaciale",
    "Alla ricerca della felicità",
    "Qualcuno volò sul nido del cuculo",
    "Il diavolo veste Prada",
    "Rambo",
    "Rocky",
    "Terminator",
    "Matrix",
    "Shrek",
    "Spider-Man",
    "Il re leone",
    "Frozen - Il regno di ghiaccio",
    "Oceania",
    "Kung Fu Panda",
    "Cattivissimo Me",
    "Madagascar",
    "Avatar",
    "Titanic",
    "Inception",
    "Interstellar",
    "Joker",
    "Parasite",
    "Bohemian Rhapsody",
    "La la land",
    "The Wolf of Wall Street",
    "Django Unchained"
]

print("\n--- TEST GENERAZIONE TITOLI CON SPACY (30+ ESEMPI) ---\n")

for title in test_titles:
    ruined = ruin_title_with_nlp(title)
    print(f"ORIGINALE: {title}")
    print(f"ROVINATO : {ruined}")
    print("-" * 30)
