from tempfile import tempdir

import streamlit as st
import requests
import json
import os

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Guide Entrepreneur Sénégal",
    page_icon="logo.png",
    layout="wide"
)

api_key = os.environ.get("MISTRAL_API_KEY")
URL     = "https://api.mistral.ai/v1/chat/completions"
MODEL   = "mistral-small-latest"

KNOWLEDGE_DIR = "knowledge"

# ─────────────────────────────────────────────
# CHARGEMENT DES FICHIERS DE CONNAISSANCES
# ─────────────────────────────────────────────
@st.cache_data
def charger_tous_les_modules():
    """Charge et concatène tous les fichiers .txt du dossier knowledge."""
    contenu_total = ""
    fichiers = sorted([
        f for f in os.listdir(KNOWLEDGE_DIR)
        if f.endswith(".txt")
    ])
    for fichier in fichiers:
        chemin = os.path.join(KNOWLEDGE_DIR, fichier)
        with open(chemin, "r", encoding="utf-8") as f:
            contenu_total += f"\n\n{'='*60}\n"
            contenu_total += f.read()
    return contenu_total, fichiers

# ─────────────────────────────────────────────
# ROUTEUR : DÉTECTION DU MODULE CONCERNÉ
# ─────────────────────────────────────────────
def detecter_module(question: str) -> str:
    """Retourne un indice sur le module concerné pour enrichir le prompt."""
    q = question.lower()

    if any(m in q for m in ["ninea", "numéro identification", "identifiant fiscal", "nif"]):
        return "NINEA"
    if any(m in q for m in ["rccm", "registre de commerce", "registre du commerce", "immatriculer", "immatriculation"]):
        return "RCCM"
    if any(m in q for m in ["nom", "dénomination", "oapi", "marque", "enseigne", "nom commercial"]):
        return "NOM_ENTREPRISE"
    if any(m in q for m in ["sarl", "sa ", "gie", "suarl", "sas", "snc", "forme juridique", "type d'entreprise", "quelle entreprise"]):
        return "FORMES_JURIDIQUES"
    if any(m in q for m in ["impôt", "taxe", "tva", "patente", "cgu", "comptable", "fiscale", "après création", "obligation"]):
        return "APRES_CREATION"
    if any(m in q for m in ["créer", "création", "étape", "procédure", "comment faire", "démarche", "coût", "prix", "combien"]):
        return "PROCEDURE_COMPLETE"

    return "GENERAL"


# ─────────────────────────────────────────────
# CONSTRUCTION DU SYSTEM PROMPT
# ─────────────────────────────────────────────
def construire_system_prompt(knowledge: str) -> str:
    return f"""Tu es Jubal ADMIN 🇸🇳, un assistant spécialisé pour les entrepreneurs sénégalais.
"Jubal" signifie "ÉQUITÉ" en wolof - tu réponds donc avec justice, clarté et bienveillance.

Ta mission : Aider les jeunes entrepreneurs à comprendre TOUTES les procédures de création d'entreprise au Sénégal SANS se déplacer.

CE QUE TU DOIS SAVOIR PARFAITEMENT :
- Formes juridiques (EI, SARL, SA, GIE, SUARL)
- Choix du nom d'entreprise et dépôt OAPI
- RCCM (Registre de Commerce)
- NINEA (gratuit sur e-ninea.ansd.sn)
- Procédure complète (6 étapes + coûts)
- Après création (impôts, IPRES, DER/FJ)

RÈGLES D'OR :
1. Réponds TOUJOURS en français
2. Sois précis sur les coûts (en FCFA) et les délais
3. Si tu ne sais pas, dis-le honnêtement et redirige vers un humain
4. Utilise des exemples concrets
5. Termine par une question ouverte pour continuer l'aide

BASE DE CONNAISSANCES OFFICIELLE :
{knowledge}

N'oublie jamais : Jubal = ÉQUITÉ. Traite chaque entrepreneur avec justice.
"""



# ─────────────────────────────────────────────
# STREAMING DE LA RÉPONSE
# ─────────────────────────────────────────────
def stream_reponse(messages_payload: list, temp: float):
    """Génère les chunks de texte via l'API Mistral en streaming."""
    payload = {
        "model":       MODEL,
        "messages":    messages_payload,
        "temperature": temp,
        "stream":      True,
    }
    try:
        with requests.post(
            URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            stream=True,
            timeout=60
        ) as response:
            if response.status_code != 200:
                yield f"❌ Erreur {response.status_code} : {response.text}"
                return

            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line == "data: [DONE]":
                    break
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError):
                        continue
    except requests.exceptions.Timeout:
        yield "\n\n⚠️ La réponse a pris trop de temps. Vérifie ta connexion et réessaie."
    except requests.exceptions.ConnectionError:
        yield "\n\n⚠️ Impossible de contacter le serveur. Vérifie ta connexion internet."


# ─────────────────────────────────────────────
# INTERFACE STREAMLIT
# ─────────────────────────────────────────────

# --- Sidebar ---
with st.sidebar:
    st.image("logo.png", width=80)
    st.title("Jubal ADMIN")
    st.markdown("**Guide officieux de création d'entreprise au Sénégal**")

   #--- temp = st.slider("Température IA", 0.0, 1.0, 0.2,  help="Basse = réponses plus précises, Haute = plus créatif")---

    st.divider()
    st.markdown("### 📂 Modules chargés")

    try:
        _, fichiers = charger_tous_les_modules()
        noms_modules = {
            "01_formes_juridiques.txt": " Formes juridiques",
            "02_nom_entreprise.txt":    " Nom d'entreprise",
            "03_rccm.txt":              " RCCM",
            "04_ninea.txt":             " NINEA",
            "05_procedure_complete.txt":"Procédure complète",
            "06_apres_creation.txt":    " Après la création",
        }
        for f in fichiers:
            label = noms_modules.get(f, f"📄 {f}")
            st.success(label)
    except Exception:
        st.error("Dossier 'knowledge' introuvable.")

    st.divider()
    if st.button("🗑️ Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Sources : APIX · ANSD · OAPI · finances.gouv.sn · senegalservices.sn")

# --- En-tête principal ---
#st.title("🇸🇳 Guide Création d'Entreprise au Sénégal")
st.title("🇸🇳L'équité (Jubal) au service des entrepreneurs sénégalais")
st.markdown(
        "<h4 style='text-align: center;'>L'équité (Jubal) au service des entrepreneurs sénégalais🇸🇳</h4>",
        unsafe_allow_html=True
    )






st.markdown(
    "Pose ta question sur la **création d'entreprise** : NINEA, RCCM, formes juridiques, "
    "nom commercial, coûts, procédures… Je t'explique tout simplement."
)

# --- Questions rapides ---
st.markdown("**Questions fréquentes :**")
cols = st.columns(3)
questions_rapides = [
    ("Coût total création", "Combien coûte au total la création d'une entreprise individuelle au Sénégal ?"),
    ("NINEA gratuit ?",     "Le NINEA est-il gratuit au Sénégal ? Comment l'obtenir ?"),
    ("SARL ou EI ?",       "Quelle est la différence entre une entreprise individuelle et une SARL ? Laquelle choisir ?"),
    ("Choisir un nom",     "Comment choisir et enregistrer le nom de mon entreprise au Sénégal ?"),
    ("Étapes RCCM",         "Quelles sont les étapes pour obtenir le registre de commerce (RCCM) au Sénégal ?"),
    ("Procédure complète", "Donne-moi la procédure complète pour créer une entreprise au Sénégal étape par étape."),
]
for i, (label, question) in enumerate(questions_rapides):
    col = cols[i % 3]
    if col.button(label, use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": question})
        st.rerun()

st.divider()

# --- Initialisation historique ---

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Affichage de l'historique ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Saisie et réponse ---
if prompt := st.chat_input("Ex : Comment obtenir mon NINEA ? Combien coûte une SARL ?"):

    # Ajout et affichage du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Chargement des connaissances
    try:
        contenu_knowledge, _ = charger_tous_les_modules()
    except Exception as e:
        st.error(f"❌ Impossible de charger les fichiers de connaissances : {e}")
        st.stop()

    # Construction des messages pour l'API
    module_detecte = detecter_module(prompt)
    system_prompt  = construire_system_prompt(contenu_knowledge)
    

    # Contexte enrichi si module détecté
    prompt_enrichi = prompt
    if module_detecte != "GENERAL":
        prompt_enrichi = f"[Question liée au module : {module_detecte}]\n{prompt}"

    MAX_HISTORIQUE = 10
    historique_recent = st.session_state.messages[-(MAX_HISTORIQUE + 1):-1]

    messages_api = (
    [{"role": "system", "content": system_prompt}]
    + [
        {"role": m["role"], "content": m["content"]}
        for m in historique_recent
    ]
    + [{"role": "user", "content": prompt_enrichi}]
)

    # Streaming de la réponse
    with st.chat_message("assistant"):
        reponse_complete = st.write_stream(stream_reponse(messages_api, tempdir))

    # Sauvegarde dans l'historique
    st.session_state.messages.append({
        "role":    "assistant",
        "content": reponse_complete
    })
