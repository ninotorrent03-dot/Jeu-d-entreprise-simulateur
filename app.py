import json
import os
import random
import time
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURATION, CSS & STATE (STYLE BITLIFE)
# ==========================================
st.set_page_config(page_title="Business Simulator - BitLife Edition", layout="wide", page_icon="💼")

# CSS Inspiré de BitLife (Fonds clairs, textes en gras, jauges, journal chronologique)
st.markdown("""
<style>
    .bitlife-header { font-family: 'Arial', sans-serif; font-weight: 800; font-size: 26px; color: #1a1a1a; margin-bottom: -10px; }
    .bitlife-subtitle { font-family: 'Arial', sans-serif; font-size: 16px; color: #666; margin-bottom: 10px; }
    .bitlife-money { font-family: 'Arial', sans-serif; font-weight: 900; font-size: 32px; color: #2e7d32; text-align: right; }
    .bitlife-log-box { background-color: #f4f4f4; border: 1px solid #ddd; border-radius: 12px; padding: 20px; max-height: 500px; overflow-y: auto; box-shadow: inset 0px 4px 10px rgba(0,0,0,0.05); }
    .bitlife-log-entry { font-family: 'Courier New', monospace; font-size: 15px; color: #333; margin-bottom: 12px; border-bottom: 1px dashed #ccc; padding-bottom: 8px; }
    .bitlife-gauge-container { display: flex; align-items: center; margin-bottom: 8px; }
    .bitlife-gauge-label { width: 120px; font-weight: bold; color: #00509e; font-size: 14px; }
    .bitlife-gauge-bar { flex-grow: 1; background-color: #e0e0e0; border-radius: 10px; height: 20px; overflow: hidden; position: relative; }
    .bitlife-gauge-fill { height: 100%; transition: width 0.5s ease-in-out; }
    .fill-green { background-color: #4caf50; }
    .fill-orange { background-color: #ff9800; }
    .fill-red { background-color: #f44336; }
    .fill-blue { background-color: #2196f3; }
    .bitlife-gauge-pct { position: absolute; right: 10px; top: 0; font-size: 12px; font-weight: bold; color: white; line-height: 20px; text-shadow: 1px 1px 2px black; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_global_games(): return {}

GAMES = get_global_games()

if "faq_chat" not in st.session_state: st.session_state.faq_chat = []

def save_game(room):
    with open(f"save_{room['room_code']}.json", "w", encoding="utf-8") as f:
        json.dump(room, f, indent=4, ensure_ascii=False)

def load_game_from_disk(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

# ==========================================
# 2. DICTIONNAIRES & BULLES D'AIDE (TOOLTIPS)
# ==========================================
HELP_PRICE = """1. Le Prix est le levier psychologique n°1 de votre entreprise.
2. Si vous fixez un prix inférieur à 40% de la moyenne du marché, les clients fuiront en pensant à une arnaque ou contrefaçon.
3. Si vous vendez trop cher sans investir dans la Qualité ou l'Image de Marque, vous ne vendrez rien.
4. Baisser le prix augmente le volume des ventes, mais détruit votre marge bénéficiaire unitaire.
5. STRATÉGIE : Au lancement, alignez-vous sur le prix de référence. Baissez-le ensuite uniquement si vous produisez en masse, ou augmentez-le si vous devenez une marque de luxe."""

HELP_SALES = """1. Ce champ n'impacte PAS la réalité de vos ventes finales, c'est une simple estimation pour vous.
2. Il sert à alimenter l'onglet "Prévisions" pour calculer vos revenus espérés.
3. Soyez réaliste : si le marché compte 10 000 clients et qu'il y a 5 entreprises, espérer 9 000 ventes est suicidaire.
4. Observez l'estimation de demande théorique dans les prévisions pour ajuster ce chiffre.
5. STRATÉGIE : Visez toujours un peu moins que votre capacité de production maximale pour simuler le pire scénario."""

HELP_QTY = """1. Représente la quantité d'unités que vous allez fabriquer ou acheter cette année.
2. Cette quantité viendra s'ajouter à votre stock existant (les invendus de l'année précédente).
3. Produire coûte de l'argent (Matières premières, coûts de fabrication).
4. Attention au sur-stockage : toute unité non vendue à la fin de l'année vous coûtera 4€ en frais d'entrepôt !
5. STRATÉGIE : Fabriquez juste de quoi couvrir vos 'Ventes espérées' + 5% de marge de sécurité au cas où la demande explose."""

HELP_EMP = """1. Les salariés sont le moteur de votre capacité de production.
2. Un salarié standard travaille 1600 heures par an.
3. Leur rendement dépend de trois facteurs : leur salaire (motivation), leur formation (vitesse) et vos exigences de qualité (lenteur).
4. Un salarié mal payé ou surchargé de process qualité produira beaucoup moins.
5. STRATÉGIE : Embauchez uniquement si votre 'Capacité RH' est inférieure à votre demande estimée. Licenciez si vous avez trop de stock."""

HELP_SALARY = """1. Le salaire motive les troupes. Le minimum légal (SMIC) est fixé à 21 000 € brut par an.
2. Payer au SMIC réduit la productivité de 50%. Vos employés traîneront des pieds.
3. Un salaire confortable (autour de 30 000 €) assure un rendement nominal.
4. Les hauts salaires augmentent la productivité jusqu'à un maximum de +30%.
5. STRATÉGIE : Si vous exigez une Qualité extrême (qui ralentit le travail), compensez par de hauts salaires pour regagner en vitesse."""

HELP_TRAIN = """1. La formation permet à vos salariés d'apprendre des méthodes de travail plus rapides.
2. C'est une dépense annuelle. Chaque euro investi réduit le temps de fabrication par produit.
3. Le bonus de vitesse est plafonné à -30% du temps de base (au-delà, l'humain a ses limites).
4. C'est l'antidote parfait contre la lenteur induite par un gros budget Qualité.
5. STRATÉGIE : Investissez un petit montant régulier dès que votre effectif dépasse 5 personnes pour optimiser la masse salariale."""

HELP_QUAL = """1. La Qualité améliore drastiquement votre popularité et fidélise les clients sur le court terme.
2. C'est indispensable si vous souhaitez vendre votre produit plus cher que la concurrence (Premium).
3. DANGER : Exiger de la qualité signifie que vos employés devront être plus minutieux. Cela RALENTIT fortement la production !
4. La baisse de cadence peut aller jusqu'à diviser votre production par 1.5.
5. STRATÉGIE : Ciblez entre 0.5% et 2.5% de votre Chiffre d'Affaires. Formez vos employés pour compenser la perte de vitesse."""

HELP_MKT = """1. La Publicité est le stéroïde de votre entreprise : effet massif et immédiat sur les parts de marché.
2. Cependant, l'effet de la pub ne dure qu'un an. Dès que vous arrêtez de payer, l'effet s'estompe.
3. Elle augmente aussi très légèrement votre 'Notoriété' (Brand Awareness) permanente.
4. Les rendements sont décroissants (mathématique logarithmique) : investir 1 million ne vous donnera pas 100% du marché.
5. STRATÉGIE : Le ratio d'or est d'investir entre 7.5% et 15% de votre CA de l'année précédente pour maintenir la croissance."""

HELP_RD = """1. La R&D (Recherche et Développement) sert à optimiser vos coûts de fabrication à la source.
2. Son effet est CUMULATIF et PERMANENT. L'investissement de l'année N s'ajoute à l'année N-1.
3. À long terme, la R&D peut réduire le coût de revient unitaire de votre produit jusqu'à -70% !
4. C'est l'outil indispensable pour déclencher une "Guerre des prix" et écraser vos concurrents.
5. STRATÉGIE : Sanctuarisez toujours entre 4% et 5% de votre Chiffre d'Affaires pour la R&D, dès la première année."""

HELP_RSE = """1. La RSE (Responsabilité Sociétale des Entreprises) englobe l'écologie, l'éthique et le social.
2. Contrairement à la Pub qui est éphémère, la RSE est CUMULATIVE. Elle construit une base de fans fidèles.
3. Les clients d'aujourd'hui sont très sensibles à la RSE. Cela augmente massivement la demande théorique.
4. Le bonus de PdM est plafonné pour rester réaliste, mais il garantit un flux régulier de clients même si vos prix sont hauts.
5. STRATÉGIE : Investissez entre 2% et 5% du CA annuellement. C'est un marathon, pas un sprint."""

HELP_CTERMS = """1. Délai Clients : Combien de jours accordez-vous à vos clients pour vous payer ?
2. Un délai long (ex: 60 jours) rassure les distributeurs et AUGMENTE VOS VENTES.
3. DANGER MORTEL : Si vous vendez avec 60 jours de délai, l'argent de ces ventes n'arrivera pas dans vos caisses cette année !
4. Cela crée un décalage de trésorerie (BFR) qui peut vous plonger dans un découvert bancaire fatal.
5. STRATÉGIE : Laissez à 30 jours au début. N'augmentez ce délai que si vous avez un gros matelas de Trésorerie."""

HELP_STERMS = """1. Délai Fournisseurs : Combien de jours prenez-vous pour payer vos propres fournisseurs de matières premières ?
2. Un délai long (ex: 60 jours) PRÉSERVE VOTRE TRÉSORERIE immédiate, car vous gardez l'argent plus longtemps.
3. C'est une dette gratuite à court terme. 
4. Les fournisseurs n'aiment pas ça, mais dans ce simulateur, l'impact négatif est limité.
5. STRATÉGIE : Essayez toujours d'avoir un Délai Fournisseur SUPÉRIEUR ou ÉGAL à votre Délai Client pour équilibrer la banque."""

HELP_MACH = """1. ACHAT DE MACHINES LOURDES. (Disponible uniquement en Phase Industrielle).
2. ATTENTION : Les machines coûtent extrêmement cher (450 000 € l'unité).
3. Une machine décuple votre capacité de production en remplaçant la lenteur humaine par l'automatisation.
4. Ces machines subissent une dépréciation (amortissement) de 10 000 € par an qui impactera votre résultat net.
5. STRATÉGIE : Souscrivez obligatoirement à un Emprunt Bancaire pour financer cet achat, sinon c'est la banqueroute immédiate."""

HELP_LOAN = """1. L'Emprunt Bancaire vous apporte du Cash immédiat pour investir (Pub, R&D, Machines).
2. Le taux d'intérêt varie de 1% (entreprise très rentable) à 5% (entreprise au bord du gouffre).
3. Vous paierez des intérêts et rembourserez le capital chaque année selon la durée choisie.
4. À la fin de la simulation (Année 8 ou 10), toute dette restante sera PÉNALISÉE (Le solde est déduit en double de votre score final !).
5. STRATÉGIE : Empruntez fort au début pour conquérir le marché, puis remboursez tout avant la dernière année."""

# ==========================================
# 3. GÉNÉRATEUR DE CONTEXTE DYNAMIQUE
# ==========================================
PRODUCT_UNIVERSES = [
    {
        "name": "Vélos Électriques Urbains", "unit": "vélos",
        "benchmark_price": 1200.0, "base_cost": 650.0, "base_market_size_per_team": 6000,
        "base_time_per_unit": 0.5, "machine_capacity": 4000, "mach_price": 450000.0,
        "desc": "La mobilité douce explose. Les villes ferment leurs centres aux voitures."
    },
    {
        "name": "Smartphones Éco-reconditionnés", "unit": "smartphones",
        "benchmark_price": 480.0, "base_cost": 240.0, "base_market_size_per_team": 12000,
        "base_time_per_unit": 0.25, "machine_capacity": 8000, "mach_price": 450000.0,
        "desc": "Face à la pénurie de puces, le reconditionné est le nouvel eldorado tech."
    },
    {
        "name": "Enceintes Hi-Fi Premium", "unit": "enceintes",
        "benchmark_price": 340.0, "base_cost": 160.0, "base_market_size_per_team": 8000,
        "base_time_per_unit": 0.35, "machine_capacity": 5000, "mach_price": 450000.0,
        "desc": "Un marché de niche pour audiophiles, très sensible à la qualité et au design."
    }
]

MACRO_CONTEXTS = [
    "L'économie mondiale est en pleine relance post-récession. L'inflation est basse et le pouvoir d'achat des ménages est au beau fixe.",
    "Le contexte géopolitique est tendu. Les taux d'intérêts bancaires sont instables et les consommateurs épargnent plus qu'ils ne dépensent.",
    "Une nouvelle loi européenne subventionne fortement votre secteur d'activité, attirant l'attention des médias et des investisseurs.",
    "Une crise logistique mondiale frappe les ports asiatiques, rendant l'approvisionnement en matières premières complexe et coûteux."
]

OPPORTUNITIES = [
    "Cependant, une tendance virale sur TikTok a soudainement mis votre type de produit sous les projecteurs des moins de 25 ans.",
    "Par chance, le principal leader historique du marché vient de faire faillite suite à un scandale, laissant d'énormes parts de marché vacantes.",
    "De plus, les nouvelles normes écologiques poussent les entreprises B2B à acheter vos produits pour leurs propres salariés.",
    "Une récente baisse d'impôts sur les sociétés vous donne un environnement fiscal très favorable pour réinvestir vos profits."
]

def generate_scenario(product):
    return f"**Secteur : {product['name']}**\n\n*Macro-économie :* {random.choice(MACRO_CONTEXTS)}\n\n*Dynamique du marché :* {product['desc']}\n\n*L'Étincelle :* {random.choice(OPPORTUNITIES)}"

EVENTS_POOL = [
    {"type": "neg", "icon": "📉", "txt": "Bad buzz sur les réseaux sociaux concernant un défaut mineur. Perte de popularité.", "cash": -15000, "pop": -10},
    {"type": "neg", "icon": "🔥", "txt": "Incendie mineur dans l'entrepôt détruisant du matériel de stockage.", "cash": -35000, "pop": 0},
    {"type": "neg", "icon": "⚖️", "txt": "L'Inspection du Travail vous inflige une amende pour non-conformité des postes.", "cash": -20000, "pop": 0},
    {"type": "neg", "icon": "🚚", "txt": "Grève des transporteurs. Les expéditions ont pris du retard, les clients râlent.", "cash": -5000, "pop": -5},
    {"type": "pos", "icon": "🌟", "txt": "Un influenceur aux 5 millions d'abonnés porte votre produit dans sa dernière vidéo !", "cash": 25000, "pop": 15},
    {"type": "pos", "icon": "🤝", "txt": "Vous décrochez une subvention 'French Tech' de la région pour votre croissance.", "cash": 50000, "pop": 0},
    {"type": "pos", "icon": "🏆", "txt": "Votre entreprise gagne le prix 'Innovation & Avenir' au salon national.", "cash": 10000, "pop": 20},
    {"type": "neutral", "icon": "☕", "txt": "Grogne syndicale concernant la machine à café en panne. Réparation payée.", "cash": -2000, "pop": 0}
]

def analyze_company_name(name):
    name_l = name.lower()
    score = 0.0
    troll_words = {"caca", "pipi", "boudin", "prout", "zizi", "bite", "cul", "merde", "con", "fuck", "shit", "lol", "mdr", "xd", "test", "truc", "machin", "bidule"}
    
    if any(w in name_l for w in troll_words): score -= 0.15
    elif len(name.strip()) <= 2 or name.strip().isdigit(): score -= 0.10
    elif len(set(name_l.replace(" ", ""))) < 3: score -= 0.10
    elif not name.replace(" ", "").replace("-", "").isalnum(): score -= 0.05
    
    if any(w in name_l for w in ("eco", "green", "bio", "durable", "clean")): score += 0.08
    if any(w in name_l for w in ("tech", "future", "inov", "smart", "next")): score += 0.08
    if any(w in name_l for w in ("global", "world", "international", "corp")): score += 0.05
    if any(w in name_l for w in ("premium", "luxury", "elite", "pro")): score += 0.06
    
    if 4 <= len(name) <= 12 and name.isalnum() and score >= 0: score += 0.05
    return max(-0.15, min(0.15, score))

# ==========================================
# 4. MOTEUR MATHÉMATIQUE & LIMITES (CAPS)
# ==========================================
def fmt_k(amount):
    if amount is None: return "0,0 K€"
    return f"{amount / 1000.0:,.1f} K€".replace(",", " ").replace(".", ",")

def fmt_num(val):
    return f"{val:,.0f}".replace(",", " ")

def init_company(name, start_capital, product):
    return {
        "name": name, "cash": start_capital, "stock": 0, "employees": 2, "machines": 0,
        "brand_awareness": 10.0, "rd_cumul": 0.0, "rse_cumul": 0.0, "loans": [],
        "pending_client_cash": 0.0, "pending_supplier_cash": 0.0, "history": [], 
        "current_decisions": {}, "draft_decisions": {}, "frozen_fields": [], 
        "name_score": analyze_company_name(name), "bitlife_log": [f"Vous avez fondé {name} avec un capital de {fmt_k(start_capital)}."]
    }

def get_default_decs(comp, product):
    last = comp["history"][-1] if comp["history"] else {}
    return {
        "price": float(last.get("price", product["benchmark_price"])),
        "forecast_sales": int(last.get("sales", product["base_market_size_per_team"] // 2)), 
        "purchase_qty": int(last.get("sales", product["base_market_size_per_team"] // 2)),
        "buy_machines": 0, "marketing": float(last.get("mkt", 5000.0)), "rd_budget": float(last.get("rd", 3000.0)), 
        "rse_budget": float(last.get("rse", 2000.0)),
        "employees": int(comp.get("employees", 2)), "salary": float(last.get("salary", 25000.0)), 
        "quality": float(last.get("qual", 2500.0)), "training": float(last.get("train", 1500.0)), 
        "client_terms": int(last.get("client_terms", 30)), "supplier_terms": int(last.get("supplier_terms", 30)), 
        "new_loan_amount": 0.0, "new_loan_duration": 3, 
        "espionnage": 0, "sabotage_type": 0, "sabotage_target": "", "sabotage_action": "Prix",
        "defense_target": "Aucune", "defense_level": 0
    }

def get_unit_cost(base_cost, rd_total):
    if rd_total <= 0: return base_cost
    # Fonction logarithmique asymtotique pour la R&D (cap à -70% des coûts)
    reduction = 0.70 * (1.0 - math.exp(-rd_total / 250000.0))
    return base_cost * (1.0 - reduction)

def get_hr_metrics(employees, salary, quality_budget, training_budget, base_time):
    total_hours = employees * 1600
    
    # Caps réalistes : Qualité ralentit max de 50%, Formation accélère max de 30%
    time_penalty = min(1.50, 1.0 + (math.sqrt(quality_budget) / 2000.0)) if quality_budget > 0 else 1.0
    time_bonus = max(0.70, 1.0 - (math.sqrt(training_budget) / 1500.0)) if training_budget > 0 else 1.0
    
    motivation = min(1.30, max(0.50, 1.0 + ((salary - 21000) / 40000.0))) # SMIC=21k -> 1.0
    
    effective_hours = total_hours * motivation
    time_per_unit = base_time * time_penalty * time_bonus
    hr_cap = effective_hours / time_per_unit if time_per_unit > 0 else 0
    return {
        "time_per_unit": time_per_unit, "effective_hours": effective_hours,
        "hr_cap": hr_cap, "motivation": (motivation - 0.5) / 0.8 * 100, 
        "productivity_pct": (1.0 / time_per_unit) / (1.0 / base_time) * 100 if base_time > 0 else 0
    }

def get_popularity_gauges(comp, decs):
    rse_val = decs.get("rse_budget", 0) + comp.get("rse_cumul", 0)
    # Logarithmique pour que ça s'aplatisse vite. Score sur 100.
    rse_score = min(100.0, 100.0 * (1.0 - math.exp(-rse_val / 100000.0))) if rse_val > 0 else 0.0
    
    qual_val = decs.get("quality", 0)
    qual_score = min(100.0, 100.0 * (1.0 - math.exp(-qual_val / 50000.0))) if qual_val > 0 else 0.0
    
    popularity = (rse_score * 0.4) + (qual_score * 0.6)
    return rse_score, qual_score, popularity

def get_theo_demand(base_demand, price, bench_price, marketing, quality, rse, client_terms, brand_aw, popularity):
    price_ratio = bench_price / price if price > 0 else 1.0
    price_factor = price_ratio ** 1.5 # Moins punitif exponentiellement
    
    suspicion_penalty = (price / (bench_price * 0.4)) ** 2.0 if price < bench_price * 0.4 else 1.0
    
    # Plafonds stricts (Caps) pour empêcher les croissances irréalistes
    # Marketing cap à +80% de demande brute
    mkt_factor = min(1.80, 1.0 + (math.sqrt(marketing) / 500.0)) if marketing > 0 else 1.0
    # Qualité cap à +50%
    qual_factor = min(1.50, 1.0 + (math.sqrt(quality) / 400.0)) if quality > 0 else 1.0
    # RSE cap à +60%
    rse_factor = min(1.60, 1.0 + (math.sqrt(rse) / 600.0)) if rse > 0 else 1.0
    
    terms_factor = min(1.20, 1.0 + (client_terms / 90.0) * 0.2)
    brand_factor = min(1.30, 1.0 + (brand_aw / 100.0) * 0.3)
    
    return base_demand * price_factor * mkt_factor * qual_factor * rse_factor * terms_factor * brand_factor * suspicion_penalty

def calculate_forecast(comp, decs, product, is_prod_phase, num_teams, market_growth_rate):
    price = decs.get("price", product["benchmark_price"])
    mkt = decs.get("marketing", 0.0)
    qual = decs.get("quality", 0.0)
    rd_bud = decs.get("rd_budget", 0.0)
    rse_bud = decs.get("rse_budget", 0.0)
    employees = decs.get("employees", 1)
    salary = decs.get("salary", 30000.0)
    train = decs.get("training", 0.0)
    c_terms = float(decs.get("client_terms", 0))
    s_terms = float(decs.get("supplier_terms", 0))
    forecast_sales_input = decs.get("forecast_sales", 0)
    purchase_qty = decs.get("purchase_qty", 0)
    buy_mach = decs.get("buy_machines", 0)
    loan_amount = decs.get("new_loan_amount", 0.0)
    loan_duration = decs.get("new_loan_duration", 3)
    esp = decs.get("espionnage", 0)
    sab_type = decs.get("sabotage_type", 0)
    def_lvl = decs.get("defense_level", 0)
    
    intel_cost = (0, 5000, 20000, 50000, 100000)[esp] if esp <= 4 else 0
    intel_cost += (0, 200000, 300000, 500000)[sab_type] if sab_type <= 3 else 0
    intel_cost += def_lvl

    adjusted_base_market = product["base_market_size_per_team"] * (1.0 + market_growth_rate)
    total_market_size_est = adjusted_base_market * num_teams
    
    rse_score, qual_score, popularity = get_popularity_gauges(comp, decs)
    
    # Demande estimée (seul contre le marché neutre pour le calcul des jauges)
    theo_demand = get_theo_demand(adjusted_base_market, price, product["benchmark_price"], mkt, qual, rse_bud + comp.get("rse_cumul",0), c_terms, comp["brand_awareness"], popularity)
    
    # Impact normalisé RSE pour les stats
    theo_demand_no_rse = get_theo_demand(adjusted_base_market, price, product["benchmark_price"], mkt, qual, 0, c_terms, comp["brand_awareness"], popularity)
    rse_pdm_gain = (theo_demand - theo_demand_no_rse) / total_market_size_est * 100 if total_market_size_est > 0 else 0
    # Plafond visuel de +25% max pour l'impact de la RSE sur la jauge
    rse_pdm_gain = min(25.0, rse_pdm_gain)
    
    hr_metrics = get_hr_metrics(employees, salary, qual, train, product["base_time_per_unit"])
    hr_cap = hr_metrics["hr_cap"]
    
    total_machines = comp["machines"] + buy_mach
    prod_cap = total_machines * product["machine_capacity"] if is_prod_phase else hr_cap
    
    available_stock = comp["stock"] + purchase_qty
    sales = min(forecast_sales_input, available_stock, hr_cap, prod_cap, theo_demand)
    
    unit_cost = get_unit_cost(product["base_cost"], comp.get("rd_cumul", 0.0) + rd_bud)
    revenue = sales * price
    purchases_value = purchase_qty * unit_cost
    
    hr_cost = employees * salary * 1.45 # Charges patronales
    depreciation = total_machines * 10000.0 if is_prod_phase else 0.0
    machine_buy_cash = buy_mach * product["mach_price"] if is_prod_phase else 0.0
    stock_final = available_stock - sales
    storage_cost = stock_final * 4.0
    
    expenses = hr_cost + mkt + qual + train + rd_bud + rse_bud + storage_cost + depreciation + intel_cost
    
    # Calcul Décalages de trésorerie (BFR)
    cash_delayed_clients = revenue * (min(c_terms, 365) / 365.0)
    cash_delayed_suppliers = purchases_value * (min(s_terms, 365) / 365.0)
    
    prev_net_income = comp["history"][-1]["net_income"] if comp["history"] else comp["cash"] * 0.2
    interest_rate = 0.05
    if loan_amount > 0:
        if prev_net_income >= loan_amount: interest_rate = 0.01
        elif prev_net_income >= loan_amount / 2: interest_rate = 0.02
        elif prev_net_income >= loan_amount / 3: interest_rate = 0.03
        elif prev_net_income >= loan_amount / 4: interest_rate = 0.04
        
    interest = sum(l["amount"] * l["rate"] for l in comp.get("loans", []))
    if loan_amount > 0: interest += loan_amount * interest_rate
        
    net_before_tax = (revenue - purchases_value) - expenses - interest
    tax = net_before_tax * 0.25 if net_before_tax > 0 else 0.0
    net_income = net_before_tax - tax
    
    repayments = sum(l["annuity"] for l in comp.get("loans", []) if l["remaining_years"] > 0)
    
    cash_in = (revenue - cash_delayed_clients) + comp.get("pending_client_cash", 0.0) + loan_amount
    cash_out = (purchases_value - cash_delayed_suppliers) + comp.get("pending_supplier_cash", 0.0) + (expenses - depreciation) + machine_buy_cash + interest + tax + repayments
    end_cash = comp["cash"] + cash_in - cash_out
    
    # Calcul des courbes mensuelles
    monthly_rev = revenue / 12.0
    monthly_purch = purchases_value / 12.0
    monthly_exp = (expenses + interest + tax + repayments + machine_buy_cash) / 12.0
    current_c = comp["cash"] + comp.get("pending_client_cash", 0) - comp.get("pending_supplier_cash", 0) + loan_amount
    cf_curve = [current_c] * 13
    
    rev_month = int(c_terms / 30)
    purch_month = int(s_terms / 30)
    
    for m in range(1, 13):
        if m > rev_month: current_c += monthly_rev
        if m > purch_month: current_c -= monthly_purch
        current_c -= monthly_exp
        cf_curve[m] = current_c
        
    hr_cap_utopia = get_hr_metrics(employees, salary, 0, train, product["base_time_per_unit"])["hr_cap"]
    sales_utopia = min(available_stock, hr_cap_utopia, theo_demand * 1.5)
    
    monthly_rev_u = (sales_utopia * price) / 12.0
    monthly_purch_u = purchases_value / 12.0
    monthly_exp_u = expenses / 12.0
    c_u = comp["cash"] + comp.get("pending_client_cash", 0) - comp.get("pending_supplier_cash", 0) + loan_amount
    cf_utopia = [c_u] * 13
    for m in range(1, 13):
        c_u += monthly_rev_u
        if m > purch_month: c_u -= monthly_purch_u
        c_u -= monthly_exp_u
        cf_utopia[m] = c_u

    est_share = min(99.0, (theo_demand / (total_market_size_est + theo_demand - adjusted_base_market)) * 100) if (total_market_size_est + theo_demand - adjusted_base_market) > 0 else 0
    
    return {
        "sales": sales, "theo_demand": theo_demand, "revenue": revenue, "net_income": net_income,
        "end_cash": end_cash, "stock_final": stock_final, "unit_cost": unit_cost,
        "est_share": est_share, "hr_cap": hr_cap, "target_share": 100.0 / num_teams if num_teams > 0 else 100.0,
        "hr_metrics": hr_metrics, "cogs": purchases_value, "hr_cost": hr_cost, "mkt": mkt, 
        "qual": qual, "train": train, "rd": rd_bud, "rse": rse_bud, "intel_cost": intel_cost,
        "total_market": total_market_size_est, "prod_cap": prod_cap, "depreciation": depreciation, "expenses": expenses,
        "cf_curve": cf_curve, "cf_utopia": cf_utopia, "rse_score": rse_score, "qual_score": qual_score,
        "popularity": popularity, "interest_rate": interest_rate, "rse_pdm_gain": rse_pdm_gain,
        "cash_delayed_clients": cash_delayed_clients, "cash_delayed_suppliers": cash_delayed_suppliers,
        "cash_in": cash_in, "cash_out": cash_out, "machine_buy_cash": machine_buy_cash
    }

def get_diff_messages(old_d, new_d):
    msgs = []
    mapping = {"price": "Prix", "forecast_sales": "Ventes Espérées", "purchase_qty": "Volume Prod", 
               "buy_machines": "Nouv. Machines", "marketing": "Budget Pub", "rd_budget": "Budget R&D",
               "rse_budget": "Budget RSE", "employees": "Salariés", "salary": "Salaire Brut",
               "quality": "Budget Qualité", "training": "Formation", "client_terms": "Délai Clients",
               "supplier_terms": "Délai Fourn.", "new_loan_amount": "Emprunt"}
    for k, v_name in mapping.items():
        v_old = old_d.get(k, 0)
        v_new = new_d.get(k, 0)
        if v_old != v_new:
            diff = v_new - v_old
            sign = "+" if diff > 0 else ""
            msgs.append(f"{v_name}: {v_old} ➔ {v_new} ({sign}{diff})")
    return msgs

def resolve_turn(room):
    product = room["product"]
    companies = room["companies"]
    num_teams = len(companies)
    is_prod_phase = (room["current_year"] >= 5)
    
    market_growth = room.get("market_growths", {}).get(str(room["current_year"]), 0.0)
    adjusted_base_market = product["base_market_size_per_team"] * (1.0 + market_growth)
    total_market_demand = adjusted_base_market * num_teams * random.uniform(0.95, 1.05)
    
    SABOTAGE_FIELDS = {"price", "marketing", "quality", "rd_budget", "rse_budget", "client_terms", "supplier_terms"}
    SABOTAGE_LIST = list(SABOTAGE_FIELDS)
    FIELD_NAMES = {"price": "Prix", "marketing": "Pub", "quality": "Qualité", "rd_budget": "R&D", "rse_budget": "RSE", "client_terms": "Délai Clients", "supplier_terms": "Délai Fournisseurs"}
    
    sabotages_to_apply = []
    
    if room["current_year"] > 1:
        for attacker_name, comp in companies.items():
            dec = comp.get("current_decisions", {})
            s_type = dec.get("sabotage_type", 0)
            if s_type > 0:
                other_teams = [t for t in companies.keys() if t != attacker_name]
                if not other_teams: continue
                
                victim = dec.get("sabotage_target", "")
                action = dec.get("sabotage_action", "")
                
                if s_type == 1:
                    victim = random.choice(other_teams)
                    action = random.choice(SABOTAGE_LIST)
                elif s_type == 2:
                    if victim not in other_teams: victim = random.choice(other_teams)
                    action = random.choice(SABOTAGE_LIST)
                elif s_type == 3:
                    if victim not in other_teams: victim = random.choice(other_teams)
                    if action not in SABOTAGE_FIELDS: action = random.choice(SABOTAGE_LIST)
                    
                sabotages_to_apply.append({"victim": victim, "action": action, "attacker": attacker_name})

    sabotage_messages = {t: [] for t in companies.keys()}
    frozen_fields_map = {t: [] for t in companies.keys()}
    target_map = {"Prix": "price", "Pub": "marketing", "Qualité": "quality", "R&D": "rd_budget", "RSE": "rse_budget"}
    def_chances = {500000: 0.25, 1000000: 0.50, 1500000: 0.75, 2000000: 1.0}
    
    for sab in sabotages_to_apply:
        v = sab["victim"]
        act = sab["action"]
        vic_comp = companies[v]
        
        def_target_name = vic_comp["current_decisions"].get("defense_target", "Aucune")
        def_lvl = vic_comp["current_decisions"].get("defense_level", 0)
        
        blocked = False
        if target_map.get(def_target_name) == act:
            if random.random() < def_chances.get(def_lvl, 0):
                blocked = True
        
        if blocked:
            sabotage_messages[v].append(f"🛡️ Sabotage sur {FIELD_NAMES.get(act, act)} bloqué par votre Bouclier !")
            sabotage_messages[sab["attacker"]].append(f"❌ Votre sabotage sur {v} a été bloqué par son bouclier !")
            vic_comp["bitlife_log"].append(f"🔒 ALERTE : Le bouclier de l'entreprise a bloqué une tentative de sabotage de {sab['attacker']} ciblant notre {FIELD_NAMES.get(act, act)}.")
        elif vic_comp["history"]:
            hist_key = act
            if act == "marketing": hist_key = "mkt"
            elif act == "quality": hist_key = "qual"
            elif act == "rd_budget": hist_key = "rd"
            elif act == "rse_budget": hist_key = "rse"
            
            old_val = vic_comp["history"][-1].get(hist_key, 0)
            vic_comp["current_decisions"][act] = old_val
            frozen_fields_map[v].append(act)
            sabotage_messages[v].append(f"⚠️ SABOTAGE : {FIELD_NAMES.get(act, act)} gelé à l'ancienne valeur !")
            vic_comp["bitlife_log"].append(f"🛑 CATASTROPHE : Nous avons été sabotés ! Notre {FIELD_NAMES.get(act, act)} a été gelé à l'ancienne valeur.")

    for name, comp in companies.items():
        comp["frozen_fields"] = frozen_fields_map[name]

    scores = {}
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        rse_tot = dec.get("rse_budget", 0.0) + comp.get("rse_cumul", 0.0)
        _, _, pop = get_popularity_gauges(comp, dec)
        name_bonus = 1.0 + comp.get("name_score", 0.0) if room["current_year"] == 1 else 1.0
        
        scores[name] = get_theo_demand(
            adjusted_base_market, dec.get("price", product["benchmark_price"]), product["benchmark_price"], 
            dec.get("marketing", 0.0), dec.get("quality", 0.0), rse_tot, 
            float(dec.get("client_terms", 0)), comp["brand_awareness"], pop
        ) * name_bonus

    total_score = sum(scores.values()) if sum(scores.values()) > 0 else 1.0
    hazard_msgs = {name: random.choice(EVENTS_POOL) for name in companies.keys()}

    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        
        rd_bud = dec.get("rd_budget", 0.0)
        mkt = dec.get("marketing", 0.0)
        qual = dec.get("quality", 0.0)
        rse_bud = dec.get("rse_budget", 0.0)
        train = dec.get("training", 0.0)
        price = dec.get("price", product["benchmark_price"])
        employees = dec.get("employees", 1)
        salary = dec.get("salary", 30000.0)
        c_terms = float(dec.get("client_terms", 0))
        s_terms = float(dec.get("supplier_terms", 0))
        purchase_qty = dec.get("purchase_qty", 0)
        
        comp["rd_cumul"] += rd_bud
        comp["rse_cumul"] += rse_bud
        unit_cost = get_unit_cost(product["base_cost"], comp["rd_cumul"])
        
        esp = dec.get("espionnage", 0)
        sab = dec.get("sabotage_type", 0)
        intel_cost = (0, 5000, 20000, 50000, 100000)[esp] if esp <= 4 else 0
        intel_cost += (0, 200000, 300000, 500000)[sab] if sab <= 3 else 0
        intel_cost += dec.get("defense_level", 0)
        
        if is_prod_phase:
            new_mach = dec.get("buy_machines", 0)
            comp["machines"] += new_mach
            mach_cost = new_mach * product["mach_price"]
            comp["cash"] -= mach_cost
            if new_mach > 0: comp["bitlife_log"].append(f"🏭 Nous avons acheté {new_mach} machine(s) lourde(s) pour {fmt_k(mach_cost)}.")
            prod_cap = comp["machines"] * product["machine_capacity"]
            depreciation = comp["machines"] * 10000.0
        else:
            prod_cap = float('inf')
            depreciation = 0.0
            
        team_demand = total_market_demand * (scores[name] / total_score)
        
        available_stock = comp["stock"] + purchase_qty
        hr_cap = get_hr_metrics(employees, salary, qual, train, product["base_time_per_unit"])["hr_cap"]
        
        actual_sales = min(team_demand, available_stock, hr_cap, prod_cap)
        
        if actual_sales >= theo_demand * 0.9: comp["bitlife_log"].append(f"🔥 Succès commercial ! Nous avons vendu la quasi-totalité de nos stocks ({fmt_num(actual_sales)} unités).")
        elif actual_sales < available_stock * 0.5: comp["bitlife_log"].append(f"📉 Année difficile. Beaucoup de stocks invendus. Seulement {fmt_num(actual_sales)} unités écoulées sur {fmt_num(available_stock)} disponibles.")
            
        real_market_share = actual_sales / total_market_demand if total_market_demand > 0 else 0
        revenue = actual_sales * price
        
        cash_delayed_clients = revenue * (min(c_terms, 365) / 365.0)
        cash_in_sales = revenue - cash_delayed_clients + comp.get("pending_client_cash", 0.0)
        comp["pending_client_cash"] = cash_delayed_clients
        
        purchases_value = purchase_qty * unit_cost
        cash_delayed_suppliers = purchases_value * (min(s_terms, 365) / 365.0)
        cash_out_purchases = purchases_value - cash_delayed_suppliers + comp.get("pending_supplier_cash", 0.0)
        comp["pending_supplier_cash"] = cash_delayed_suppliers
        
        hr_cost = employees * salary * 1.45
        
        comp["stock"] = available_stock - actual_sales
        storage_cost = comp["stock"] * 4.0
        
        expenses = hr_cost + mkt + qual + train + rd_bud + rse_bud + storage_cost + depreciation + intel_cost
        
        loan_amount = dec.get("new_loan_amount", 0.0)
        loan_duration = dec.get("new_loan_duration", 3)
        prev_net_income = comp["history"][-1]["net_income"] if comp["history"] else comp["cash"] * 0.2
        
        interest_rate = 0.05
        if loan_amount > 0:
            if prev_net_income >= loan_amount: interest_rate = 0.01
            elif prev_net_income >= loan_amount / 2: interest_rate = 0.02
            elif prev_net_income >= loan_amount / 3: interest_rate = 0.03
            elif prev_net_income >= loan_amount / 4: interest_rate = 0.04
            
        if loan_amount > 0:
            comp["loans"].append({"amount": loan_amount, "annuity": loan_amount / loan_duration, "remaining_years": loan_duration, "rate": interest_rate})
            comp["cash"] += loan_amount
            comp["bitlife_log"].append(f"🏦 Nous avons contracté un emprunt de {fmt_k(loan_amount)} au taux de {interest_rate*100:.0f}%.")
            
        interest = 0
        repayments = 0
        for l in comp["loans"]:
            if l["remaining_years"] > 0:
                interest += l["amount"] * l["rate"]
                repayments += l["annuity"]
                l["amount"] -= l["annuity"]
                l["remaining_years"] -= 1
        
        net_before_tax = (revenue - purchases_value) - expenses - interest
        tax = net_before_tax * 0.25 if net_before_tax > 0 else 0.0
        net_income = net_before_tax - tax
        
        haz = hazard_msgs[name]
        comp["cash"] += cash_in_sales - cash_out_purchases - (expenses - depreciation) - interest - tax - repayments + haz["cash"]
        comp["bitlife_log"].append(f"🎲 ÉVÉNEMENT : {haz['txt']} (Impact : {haz['cash']}€)")
        
        if comp["cash"] < 0:
            overdraft_fee = abs(comp["cash"]) * 0.12
            comp["cash"] -= overdraft_fee
            net_income -= overdraft_fee
            comp["bitlife_log"].append(f"💸 DÉCOUVERT BANCAIRE ! La banque a prélevé {fmt_k(overdraft_fee)} d'agios.")

        comp["employees"] = employees
        comp["brand_awareness"] = max(1.0, min(100.0, comp["brand_awareness"] + (mkt / 20000.0)))
        
        msg_sabot = " | ".join(sabotage_messages[name]) if sabotage_messages[name] else ""
        full_msg = f"{msg_sabot} | 🎲 ALÉA: {haz['icon']} {haz['txt']}" if msg_sabot else f"🎲 ALÉA: {haz['icon']} {haz['txt']}"

        comp["history"].append({
            "year": room["current_year"], "sales": actual_sales, "theo_demand": team_demand, 
            "hr_cap": hr_cap, "prod_cap": prod_cap if is_prod_phase else 0, "available_stock": available_stock,
            "real_market_share": real_market_share, "revenue": revenue, "cogs": purchases_value, 
            "hr_cost": hr_cost, "mkt": mkt, "qual": qual, "train": train, "rd": rd_bud, "rse": rse_bud,
            "client_terms": c_terms, "supplier_terms": s_terms,
            "intel_cost": intel_cost, "depreciation": depreciation, "storage": storage_cost,
            "net_income": net_income, "cash": comp["cash"], "stock": comp["stock"],
            "price": price, "unit_cost": unit_cost, "salary": salary, "employees": employees,
            "espionnage_level": esp, "event_msg": full_msg
        })
        comp["bitlife_log"].append(f"📊 Fin de l'Année {room['current_year']}. Chiffre d'Affaires généré : {fmt_k(revenue)} | Résultat Net : {fmt_k(net_income)}")
        comp["current_decisions"] = {}
        comp["draft_decisions"] = {}

    room["ready_teams"] = []
    room["turn_deadline"] = None
    room["current_year"] += 1
    
    if room["current_year"] > room["max_years"]:
        room["status"] = "ended"
        for name, comp in companies.items():
            remaining_debt = sum(l["amount"] for l in comp["loans"] if l["remaining_years"] > 0)
            if remaining_debt > 0:
                comp["cash"] -= (remaining_debt * 2)
                comp["bitlife_log"].append(f"❌ FIN DE PARTIE : Liquidation de la dette non remboursée avec pénalité double (-{fmt_k(remaining_debt * 2)}).")
                if comp["history"]:
                    comp["history"][-1]["net_income"] -= (remaining_debt * 2)
                    
    save_game(room)

# ==========================================
# 5. ASSISTANT IA & RÈGLES
# ==========================================
def bot_answer(q):
    q = q.lower()
    if any(w in q for w in ("prix", "tarif", "vendre", "vente")): return "Le Prix dicte vos volumes. Un prix très bas attire les masses mais écrase vos marges. Un prix haut nécessite une qualité irréprochable sous peine de boycott. Attention à l'effet 'Arnaque' si vous descendez sous 40% du prix moyen !"
    elif any(w in q for w in ("pub", "marketing", "publicite", "pub")): return "La Pub est le stéroïde des ventes. Ciblez entre 7.5% et 15% de votre CA annuel pour exploser vos parts de marché. Attention, l'effet retombe à zéro l'année suivante !"
    elif any(w in q for w in ("qualité", "qualite", "défaut")): return "La Qualité fidélise (cible: 0.5% à 2.5% du CA). DANGER : Exiger une qualité stricte RALENTIT considérablement la cadence de vos ouvriers ! Formez-les pour compenser."
    elif any(w in q for w in ("rse", "ecologie", "écologie", "social")): return "La RSE construit une clientèle fidèle de manière permanente. Contrairement à la pub, ses effets se cumulent. (Cible: 2% à 5% du CA). C'est le meilleur investissement long terme."
    elif any(w in q for w in ("rh", "employé", "employe", "salarié")): return "Vos employés travaillent 1600h. Leur vitesse est modifiée par : 1) Salaire (Motivation) 2) Formation (Accélération) 3) Qualité (Ralentissement). Ne les payez jamais au SMIC (21k) !"
    elif any(w in q for w in ("delai", "délais", "client", "paiement")): return "Délai Clients : Accordez du temps pour doper les ventes, MAIS vous créez un 'Besoin en Fonds de Roulement' fatal. L'argent des ventes n'arrive pas cette année et vous tombez à découvert."
    elif any(w in q for w in ("fournisseur", "fournisseurs")): return "Délai Fournisseurs : Retardez vos paiements (ex: 60 jours) pour préserver le Cash sur votre compte bancaire. C'est de la dette à court terme 100% gratuite."
    elif any(w in q for w in ("rd", "r&d", "recherche")): return "La R&D (Recherche et Développement) réduit de façon PERMANENTE votre Coût de Fabrication Unitaire. Objectif : 4% à 5% du CA chaque année. Incontournable en phase industrielle."
    elif any(w in q for w in ("emprunt", "banque", "dette", "machine")): return "En phase industrielle, les machines coûtent 450 K€ ! L'emprunt (Taux de 1% à 5%) est indispensable. Remboursez tout avant la fin de la partie pour éviter les doubles pénalités."
    elif any(w in q for w in ("sabotage", "bouclier", "défense")): return "Le Sabotage permet de geler le budget adverse sur une ancienne valeur. Le Bouclier (jusqu'à 2M€) protège une de vos décisions avec un taux de réussite allant de 25% à 100%."
    elif any(w in q for w in ("stock", "stockage", "invendu")): return "Ne surproduisez pas ! Tout invendu en fin d'année vous est facturé 4 € par unité en frais d'entrepôt. Surveillez bien les prévisions."
    else: return "🤖 Bonjour CEO ! Posez-moi des questions claires sur un mécanisme (ex: 'Comment marche le prix ?', 'Stratégie RSE ?', 'Délais clients ?')."

def render_help_and_faq():
    st.sidebar.markdown("---")
    with st.sidebar.expander("📚 Guide & Assistant CEO", expanded=False):
        t_regles, t_ask = st.tabs(["📖 Les 5 Commandements", "❓ Demander à l'IA"])
        with t_regles:
            st.markdown("""
            **🎯 BUT :** Terminer la partie avec la plus haute valeur (Trésorerie Actuelle + Valeur du Stock).
            
            **1️⃣ Gérer ses Marges :** Le Prix impacte le volume. La R&D (4% CA) baisse le coût de fabrication à vie.
            **2️⃣ Attirer & Fidéliser :** La Pub (10% CA) attire massivement sur 1 an. La RSE (3% CA) fidélise lentement pour toujours.
            **3️⃣ Piloter l'Usine :** La Qualité ralentit les employés. Le Salaire (>21k) et la Formation les accélèrent. 
            **4️⃣ Dompter la Trésorerie :** Ne laissez pas 60j de délai aux clients si vous n'avez pas de Cash d'avance (sinon, découvert).
            **5️⃣ Industrialiser (An 5) :** Achetez des machines à 450K€ avec l'aide des Emprunts pour exploser vos volumes.
            """)
        with t_ask:
            faq_input = st.text_input("Posez votre question :", key="faq_in", placeholder="Ex: A quoi sert la Qualité ?")
            if st.button("Envoyer") and faq_input:
                ans = bot_answer(faq_input)
                st.session_state.faq_chat.append({"q": faq_input, "a": ans})
            for chat in reversed(st.session_state.faq_chat[-3:]):
                st.markdown(f"👤 **Vous:** *{chat['q']}*")
                st.info(f"🤖 **Assistant:** {chat['a']}")

# ==========================================
# 6. INTERFACE LOBBY & JEU
# ==========================================
if "room_code" in st.session_state and st.session_state.room_code:
    tmp_room = GAMES.get(st.session_state.room_code)
    if tmp_room and tmp_room.get("turn_deadline") and len(tmp_room["ready_teams"]) == len(tmp_room["companies"]) - 1:
        if time.time() > tmp_room["turn_deadline"]:
            missing_team = [t for t in tmp_room["companies"].keys() if t not in tmp_room["ready_teams"]][0]
            m_comp = tmp_room["companies"][missing_team]
            m_comp["current_decisions"] = m_comp.get("draft_decisions") or get_default_decs(m_comp, tmp_room["product"])
            tmp_room["ready_teams"].append(missing_team)
            tmp_room["turn_deadline"] = None
            save_game(tmp_room)
            st.rerun()

if "room_code" not in st.session_state: st.session_state.room_code = None
if "player_team" not in st.session_state: st.session_state.player_team = None

if not st.session_state.room_code:
    st.markdown("<h1 style='text-align: center; font-family: Arial; font-weight: 900;'>💼 Business Simulator<br><span style='font-size: 20px; color: #666;'>BitLife Edition</span></h1>", unsafe_allow_html=True)
    
    col_c, col_j = st.columns(2)
    with col_c:
        st.subheader("1️⃣ Créer un Salon (Hôte)")
        with st.form("create_form"):
            host_name = st.text_input("Nom de votre Entreprise")
            num_years = st.slider("Durée du jeu (années)", 4, 10, 8)
            capital_k = st.number_input("Capital de départ (K€)", min_value=150, max_value=1000, value=250)
            if st.form_submit_button("Créer la partie", type="primary"):
                if not host_name.strip(): st.error("⚠️ Entrez un nom d'entreprise !")
                else:
                    room_code = f"SALON-{random.randint(1000,9999)}"
                    product = random.choice(PRODUCT_UNIVERSES)
                    market_growths = {str(y): round(random.uniform(0.05, 0.33), 2) for y in range(1, num_years + 1)}
                    room = {
                        "room_code": room_code, "host": host_name.strip(), "product": product,
                        "scenario": generate_scenario(product),
                        "max_years": num_years, "current_year": 1, "status": "waiting",
                        "start_capital": capital_k * 1000.0, "companies": {}, "ready_teams": [],
                        "market_growths": market_growths, "turn_deadline": None
                    }
                    room["companies"][host_name.strip()] = init_company(host_name.strip(), room["start_capital"], product)
                    GAMES[room_code] = room
                    save_game(room)
                    st.session_state.room_code = room_code
                    st.session_state.player_team = host_name.strip()
                    st.rerun()
    with col_j:
        st.subheader("2️⃣ Rejoindre un Salon")
        with st.form("join_form"):
            j_code = st.text_input("Code du Salon")
            player_name = st.text_input("Nom de votre Entreprise")
            if st.form_submit_button("Rejoindre la Partie"):
                room = GAMES.get(j_code)
                if not room and os.path.exists(f"save_{j_code}.json"):
                    room = load_game_from_disk(f"save_{j_code}.json")
                    GAMES[j_code] = room
                if room and player_name.strip():
                    if room["status"] != "waiting": st.error("La partie a déjà commencé !")
                    elif player_name.strip() in room["companies"]: st.error("Nom déjà pris.")
                    else:
                        room["companies"][player_name.strip()] = init_company(player_name.strip(), room["start_capital"], room["product"])
                        save_game(room)
                        st.session_state.room_code = j_code
                        st.session_state.player_team = player_name.strip()
                        st.rerun()
                else: st.error("Code introuvable ou nom vide.")

else:
    room = GAMES[st.session_state.room_code]
    product = room["product"]
    is_prod_phase = (room["current_year"] >= 5)
    num_teams = len(room["companies"])
    
    if room["status"] == "waiting":
        st.title("🏠 Salle d'attente")
        st.info(f"👉 Code à partager : **{room['room_code']}**")
        st.markdown(f"### 📰 Contexte Mondial :\n{room['scenario']}")
        
        p_team = st.session_state.player_team
        if p_team in room["companies"]:
            score_name = room["companies"][p_team].get("name_score", 0.0)
            pct_val = round(score_name * 100, 1)
            if score_name > 0: st.markdown(f"<h4 style='color:green;'>Analyse de votre nom : <span style='color:green;'>+{pct_val}% PDM bonus An 1</span></h4>", unsafe_allow_html=True)
            elif score_name < 0: st.markdown(f"<h4 style='color:red;'>Analyse de votre nom : <span style='color:red;'>{pct_val}% PDM malus An 1</span></h4>", unsafe_allow_html=True)
            
        for name in room["companies"].keys(): st.write(f"• **{name}**" + (" *(Hôte)*" if name == room["host"] else ""))
        if st.session_state.player_team == room["host"] and st.button("🚀 Lancer la Partie !", type="primary"):
            room["status"] = "playing"
            save_game(room)
            st.rerun()
        if st.button("Actualiser l'écran"): st.rerun()
        
    else:
        st.sidebar.markdown(f"**🔑 Salon:** `{room['room_code']}` | **📅 Année:** {room['current_year']}/{room['max_years']}")
        market_g = room.get("market_growths", {}).get(str(room["current_year"]), 0.15)
        st.sidebar.markdown(f"📈 **Croissance du Marché :** `+{int(market_g*100)}%`")
        
        if st.sidebar.button("Déconnexion"):
            st.session_state.room_code = None
            st.rerun()

        if st.session_state.player_team not in room["companies"]: st.session_state.player_team = list(room["companies"].keys())[0]
        selected_team = st.sidebar.selectbox("Changer de vue :", list(room["companies"].keys()), index=list(room["companies"].keys()).index(st.session_state.player_team))
        comp = room["companies"][selected_team]
        has_played = selected_team in room["ready_teams"]
        
        render_help_and_faq()
        
        if room["status"] == "playing" and st.session_state.player_team == room["host"]:
            st.sidebar.markdown("---")
            if len(room["ready_teams"]) == num_teams:
                st.sidebar.success("✅ Tout le monde est prêt !")
                if st.sidebar.button("🟢 Passer à l'année suivante", type="primary", use_container_width=True):
                    resolve_turn(room)
                    st.rerun()
            else:
                st.sidebar.warning(f"En attente... ({len(room['ready_teams'])}/{num_teams})")
                with st.sidebar.expander("🛠️ Options Admin"):
                    if st.button("⚠️ Forcer la fin immédiate"):
                        for m in room["companies"].keys():
                            if m not in room["ready_teams"]:
                                room["companies"][m]["current_decisions"] = room["companies"][m].get("draft_decisions") or get_default_decs(room["companies"][m], product)
                                room["ready_teams"].append(m)
                        resolve_turn(room)
                        st.rerun()

        # UI Type BITLIFE 
        st.markdown(f"<div class='bitlife-header'>🏢 {selected_team}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='bitlife-subtitle'>CEO: {st.session_state.player_team} | Employés: {comp['employees']} | Stock: {fmt_num(comp['stock'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='bitlife-money'>{fmt_k(comp['cash'])}</div>", unsafe_allow_html=True)
        
        if room.get("turn_deadline") and len(room["ready_teams"]) == num_teams - 1 and room["status"] == "playing":
            time_left = int(room["turn_deadline"] - time.time())
            if time_left > 0:
                mins, secs = divmod(time_left, 60)
                st.error(f"⏳ **ATTENTION :** Plus que **{mins}m {secs}s** avant la validation forcée du dernier joueur !")
                components.html(f"<script>setTimeout(function(){{ window.parent.location.reload(); }}, {time_left * 1000 + 1000});</script>", height=0)

        if has_played and room["status"] == "playing":
            st.success("✅ Année validée. En attente de la concurrence...")
            if st.button("Actualiser"): st.rerun()
        elif room["status"] == "ended":
            st.balloons()
            st.header("🏆 Classement Final")
            final_list = [{"Équipe": n, "Valeur Nette Est.": (c["cash"] + c["stock"] * product["base_cost"] * 0.5) / 1000.0} for n, c in room["companies"].items()]
            st.table(pd.DataFrame(final_list).sort_values(by="Valeur Nette Est.", ascending=False).style.format({"Valeur Nette Est.": "{:,.1f} K€"}))

        # Les 5 onglets principaux du Menu
        t_log, t_dec, t_prev, t_treso, t_audit = st.tabs(["📜 Journal", "💼 Activités", "📈 Prévisions", "🏦 Tréso", "🕵️ Audit"])
        
        sim_key = f"sim_{selected_team}_{room['current_year']}"
        frozen = comp.get("frozen_fields", [])
        if sim_key not in st.session_state: st.session_state[sim_key] = get_default_decs(comp, product)

        # Calculer les prévisions pour alimenter les jauges Bitlife
        forecast = calculate_forecast(comp, st.session_state[sim_key], product, is_prod_phase, num_teams, market_g)

        with t_log:
            # Rendu des jauges de performance façon Bitlife
            st.markdown("### Profil de l'Entreprise")
            
            motiv = forecast["hr_metrics"]["motivation"]
            motiv_color = "fill-green" if motiv > 80 else "fill-orange" if motiv > 40 else "fill-red"
            st.markdown(f"""
            <div class="bitlife-gauge-container">
                <div class="bitlife-gauge-label">Motivation 😊</div>
                <div class="bitlife-gauge-bar"><div class="bitlife-gauge-fill {motiv_color}" style="width: {motiv}%;"></div><span class="bitlife-gauge-pct">{int(motiv)}%</span></div>
            </div>""", unsafe_allow_html=True)
            
            aw = min(100.0, comp['brand_awareness'] + (st.session_state[sim_key]['marketing']/10000.0))
            aw_color = "fill-green" if aw > 70 else "fill-orange" if aw > 30 else "fill-red"
            st.markdown(f"""
            <div class="bitlife-gauge-container">
                <div class="bitlife-gauge-label">Notoriété ⭐</div>
                <div class="bitlife-gauge-bar"><div class="bitlife-gauge-fill {aw_color}" style="width: {aw}%;"></div><span class="bitlife-gauge-pct">{int(aw)}%</span></div>
            </div>""", unsafe_allow_html=True)
            
            qual = forecast["qual_score"]
            qual_color = "fill-green" if qual > 70 else "fill-orange" if qual > 30 else "fill-red"
            st.markdown(f"""
            <div class="bitlife-gauge-container">
                <div class="bitlife-gauge-label">Qualité ✨</div>
                <div class="bitlife-gauge-bar"><div class="bitlife-gauge-fill {qual_color}" style="width: {qual}%;"></div><span class="bitlife-gauge-pct">{int(qual)}%</span></div>
            </div>""", unsafe_allow_html=True)
            
            rse = forecast["rse_score"]
            rse_color = "fill-green" if rse > 70 else "fill-orange" if rse > 30 else "fill-red"
            st.markdown(f"""
            <div class="bitlife-gauge-container">
                <div class="bitlife-gauge-label">Score RSE 🌍</div>
                <div class="bitlife-gauge-bar"><div class="bitlife-gauge-fill {rse_color}" style="width: {rse}%;"></div><span class="bitlife-gauge-pct">{int(rse)}%</span></div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown("<br>### 📜 Le Journal de Bord", unsafe_allow_html=True)
            log_html = "<div class='bitlife-log-box'>"
            for entry in reversed(comp.get("bitlife_log", [])):
                log_html += f"<div class='bitlife-log-entry'>👉 {entry}</div>"
            log_html += "</div>"
            st.markdown(log_html, unsafe_allow_html=True)

        with t_dec:
            ca_ref = comp["history"][-1]["revenue"] if comp["history"] else room["start_capital"]
            
            with st.form(f"form_dec_{selected_team}"):
                st.markdown("### 🛒 Commercial & Opérations")
                c1, c2, c3 = st.columns(3)
                with c1: price = st.number_input("🏷️ Prix Vente (€)", min_value=1.0, value=st.session_state[sim_key]["price"], disabled=("price" in frozen), help=HELP_PRICE)
                with c2: forecast_sales = st.number_input("🎯 Ventes espérées", min_value=0, value=st.session_state[sim_key]["forecast_sales"], step=100, help=HELP_SALES)
                with c3: purchase_qty = st.number_input("📦 Quantité à Produire", min_value=0, value=st.session_state[sim_key]["purchase_qty"], step=100, help=HELP_QTY)

                st.markdown("### 🏭 Ressources Humaines & Usine")
                p1, p2, p3 = st.columns(3)
                with p1:
                    employees = st.number_input("👷 Effectif", min_value=1, value=st.session_state[sim_key]["employees"], help=HELP_EMP)
                    salary = st.number_input("💶 Salaire brut/an (€)", min_value=21000.0, value=st.session_state[sim_key]["salary"], step=1000.0, help=HELP_SALARY)
                with p2:
                    training = st.number_input("🎓 Formation (€)", min_value=0.0, value=st.session_state[sim_key]["training"], step=500.0, help=HELP_TRAIN)
                    quality = st.number_input("✨ Qualité (€)", min_value=0.0, value=st.session_state[sim_key]["quality"], step=500.0, disabled=("quality" in frozen), help=HELP_QUAL)
                    st.caption(f"Poids: {quality/ca_ref*100:.1f}% CA Réf.")
                with p3:
                    buy_machines = st.number_input("🏭 Acheter Machines", min_value=0, value=st.session_state[sim_key]["buy_machines"], disabled=not is_prod_phase, help=HELP_MACH)
                    st.caption(f"Prix Unité: {fmt_k(product['mach_price'])}")

                st.markdown("### 🚀 Budgets Stratégiques & Banque")
                f1, f2, f3 = st.columns(3)
                with f1:
                    marketing = st.number_input("📢 Publicité (€)", min_value=0.0, value=st.session_state[sim_key]["marketing"], step=1000.0, disabled=("marketing" in frozen), help=HELP_MKT)
                    rd_budget = st.number_input("🔬 R&D (€)", min_value=0.0, value=st.session_state[sim_key]["rd_budget"], step=1000.0, disabled=("rd_budget" in frozen), help=HELP_RD)
                    rse_budget = st.number_input("🌍 RSE (€)", min_value=0.0, value=st.session_state[sim_key]["rse_budget"], step=1000.0, disabled=("rse_budget" in frozen), help=HELP_RSE)
                with f2:
                    client_terms = st.number_input("⏳ Délai Clients (j)", min_value=0, max_value=120, value=st.session_state[sim_key]["client_terms"], disabled=("client_terms" in frozen), help=HELP_CTERMS)
                    supplier_terms = st.number_input("⏳ Délai Fourn. (j)", min_value=0, max_value=120, value=st.session_state[sim_key]["supplier_terms"], disabled=("supplier_terms" in frozen), help=HELP_STERMS)
                with f3:
                    loan_amount = st.number_input("🏦 Nouvel Emprunt (€)", min_value=0.0, value=st.session_state[sim_key]["new_loan_amount"], step=10000.0, help=HELP_LOAN)
                    loan_duration = st.slider("📅 Durée emprunt (ans)", 1, 5, value=st.session_state[sim_key]["new_loan_duration"])

                if frozen:
                    st.warning(f"🔒 SABOTAGE EN COURS ! Impossible de modifier : {', '.join(frozen)}")

                calc_btn = st.form_submit_button("🔄 Calculer & Sauvegarder", type="secondary")

            if calc_btn:
                new_decs = {
                    "price": price, "forecast_sales": forecast_sales, "purchase_qty": purchase_qty,
                    "buy_machines": buy_machines, "marketing": marketing, "rd_budget": rd_budget,
                    "rse_budget": rse_budget, "employees": employees, "salary": salary,
                    "quality": quality, "training": training, "client_terms": client_terms,
                    "supplier_terms": supplier_terms, "new_loan_amount": loan_amount,
                    "new_loan_duration": loan_duration
                }
                diffs = get_diff_messages(st.session_state[sim_key], new_decs)
                st.session_state[sim_key].update(new_decs)
                comp["draft_decisions"] = st.session_state[sim_key].copy()
                save_game(room)
                if diffs:
                    st.success("✅ Modifié avec succès :\n\n" + "\n".join([f"- {d}" for d in diffs]))
                else:
                    st.info("Aucun changement détecté.")

            st.markdown("---")
            if st.button("🟢 VALIDER ET PASSER L'ANNÉE", type="primary", use_container_width=True):
                comp["current_decisions"] = st.session_state[sim_key].copy()
                room["ready_teams"].append(selected_team)
                if len(room["ready_teams"]) == num_teams - 1: room["turn_deadline"] = time.time() + 300 
                elif len(room["ready_teams"]) == num_teams: room["turn_deadline"] = None
                save_game(room)
                st.rerun()

        with t_prev:
            st.subheader("📊 Grand Tableau de Bord Prévisionnel")
            st.info(f"💡 **Impact RSE Actuel :** La force de vos actions écologiques et sociales vous offre un bonus naturel de **+{forecast['rse_pdm_gain']:.1f}%** de parts de marché.")
            
            c_k1, c_k2, c_k3 = st.columns(3)
            c_k1.metric("🏷️ Coût Prod. Unitaire (-R&D)", f"{forecast['unit_cost']:.2f} €")
            c_k2.metric("🏦 Taux Banquier Actuel", f"{forecast['interest_rate']*100:.0f}%")
            c_k3.metric("🏭 Capacité Salariale RH", f"{fmt_num(forecast['hr_cap'])} unités")
            
            st.markdown("### 🧾 Compte de Résultat Prévisionnel")
            df_pl = pd.DataFrame([
                {"Catégorie": "1. CHIFFRE D'AFFAIRES ESPÉRÉ", "Montant (€)": forecast["revenue"]},
                {"Catégorie": "2. Achats & Coûts de Fabrication", "Montant (€)": -forecast["cogs"]},
                {"Catégorie": ">> MARGE BRUTE (1+2)", "Montant (€)": forecast["revenue"] - forecast["cogs"]},
                {"Catégorie": "3. Masse Salariale (avec charges)", "Montant (€)": -forecast["hr_cost"]},
                {"Catégorie": "4. Budgets (Pub, Qual, Form, R&D, RSE)", "Montant (€)": -(forecast["mkt"] + forecast["qual"] + forecast["train"] + forecast["rd"] + forecast["rse"])},
                {"Catégorie": "5. Amortissement & Stockage", "Montant (€)": -(forecast["depreciation"] + forecast["expenses"] - forecast["hr_cost"] - forecast["mkt"] - forecast["qual"] - forecast["train"] - forecast["rd"] - forecast["rse"] - forecast["depreciation"] - forecast["intel_cost"])},
                {"Catégorie": "6. Frais de Renseignement / Défense", "Montant (€)": -forecast["intel_cost"]},
                {"Catégorie": ">> RÉSULTAT BRUT D'EXPLOITATION", "Montant (€)": forecast["revenue"] - forecast["cogs"] - forecast["expenses"]},
                {"Catégorie": "7. Intérêts Bancaires", "Montant (€)": -(forecast["expenses"] - forecast["revenue"] + forecast["cogs"] + forecast["net_income"] / 0.75 if forecast["net_income"] > 0 else 0) },
                {"Catégorie": ">> RÉSULTAT NET AVANT IMPÔT", "Montant (€)": forecast["net_income"] / 0.75 if forecast["net_income"] > 0 else forecast["net_income"]},
                {"Catégorie": "8. Impôt sur les Sociétés (25%)", "Montant (€)": -(forecast["net_income"] / 0.75 * 0.25) if forecast["net_income"] > 0 else 0},
                {"Catégorie": "==== RÉSULTAT NET FINAL ====", "Montant (€)": forecast["net_income"]}
            ])
            st.table(df_pl.style.format({"Montant (€)": "{:,.0f} €"}))

        with t_treso:
            st.subheader("💸 Analyse du Flux de Trésorerie (BFR)")
            
            with st.expander("📖 Comment lire ces prévisions de trésorerie ?", expanded=True):
                st.markdown(f"""
                Le "Résultat Net" ne veut pas dire "Argent en banque". Tout dépend des **Délais de Paiement**.
                
                * **Argent entrant :** Vous avez réalisé un CA de {fmt_k(forecast['revenue'])}. Mais comme vous laissez {st.session_state[sim_key]['client_terms']} jours à vos clients pour payer, vous allez avoir un trou de {fmt_k(forecast['cash_delayed_clients'])} qui ne rentrera que l'année prochaine !
                * **Argent sortant :** Vos achats coûtent {fmt_k(forecast['cogs'])}. Grâce à votre délai fournisseur de {st.session_state[sim_key]['supplier_terms']} jours, vous repoussez de {fmt_k(forecast['cash_delayed_suppliers'])} la sortie d'argent à l'année prochaine.
                * **Sorties immédiates :** Vous payez {fmt_k(forecast['expenses'] - forecast['depreciation'])} comptant dans l'année (Salaires, Pub, R&D...).
                * **Investissement lourd :** {fmt_k(forecast['machine_buy_cash'])} pour l'achat de vos nouvelles machines.
                """)
                if forecast['end_cash'] < 0:
                    st.error("🚨 DANGER : Vos décalages créent un découvert bancaire massif ! Baissez votre Délai Client, augmentez votre Délai Fournisseur, ou souscrivez un emprunt !")
                else:
                    st.success("✅ Trésorerie saine : Votre BFR est maîtrisé, vous n'êtes pas à découvert.")

            max_overdraft = st.slider("Ajuster la limite de découvert estimée (€)", min_value=0, max_value=int(ca_ref * 0.5), value=20000, step=5000)
            
            months = list(range(0, 13))
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=months, y=forecast["cf_utopia"], mode='lines', name='Utopique (Paiement Comptant)', line=dict(color='green', dash='dot')))
            fig.add_trace(go.Scatter(x=months, y=forecast["cf_curve"], mode='lines+markers', name='Votre Trésorerie Prévue', line=dict(color='blue', width=3)))
            fig.add_trace(go.Scatter(x=months, y=[-max_overdraft]*13, mode='lines', name='Limite Découvert tolérée', line=dict(color='red', dash='dash')))
            fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        with t_audit:
            st.subheader("🕵️ Espionnage, Sabotage & Défense")
            c_esp, c_sab, c_def = st.columns(3)
            with c_esp:
                st.markdown("#### 1. Espionnage Industriel")
                esp = st.selectbox("Niveau d'infiltration", options=[0,1,2,3,4], index=st.session_state[sim_key]["espionnage"], format_func=lambda x: {0:"0€ - Aucun", 1:"5 K€ - Rapport Ventes", 2:"20 K€ - Rapport Budgets", 3:"50 K€ - Rapport Trésorerie", 4:"100 K€ - Audit Comparatif Général"}[x])
                if esp != st.session_state[sim_key]["espionnage"]:
                    st.session_state[sim_key]["espionnage"] = esp; st.rerun()

            with c_sab:
                st.markdown("#### 2. Sabotage Offensif")
                s_type = st.selectbox("Type d'attaque cyber/terrain", options=[0,1,2,3], index=st.session_state[sim_key]["sabotage_type"], format_func=lambda x: {0:"0€ - Pas d'attaque", 1:"200 K€ - Aveugle (Aléatoire)", 2:"300 K€ - Cible spécifique", 3:"500 K€ - Chirurgicale (Cible+Dossier)"}[x], disabled=(room["current_year"] == 1))
                other_teams = [t for t in room["companies"].keys() if t != selected_team]
                if s_type != st.session_state[sim_key]["sabotage_type"]:
                    st.session_state[sim_key]["sabotage_type"] = s_type; st.rerun()
                if s_type in (2, 3) and other_teams:
                    idx_t = other_teams.index(st.session_state[sim_key]["sabotage_target"]) if st.session_state[sim_key]["sabotage_target"] in other_teams else 0
                    s_target = st.selectbox("🎯 Entreprise ciblée", options=other_teams, index=idx_t)
                    if s_target != st.session_state[sim_key]["sabotage_target"]:
                        st.session_state[sim_key]["sabotage_target"] = s_target; st.rerun()
                if s_type == 3:
                    s_action_names = ["Prix", "Pub", "Qualité", "R&D", "RSE", "Délai Clients", "Délai Fournisseurs"]
                    idx_a = s_action_names.index(st.session_state[sim_key].get("sabotage_action_name", "Prix")) if st.session_state[sim_key].get("sabotage_action_name", "Prix") in s_action_names else 0
                    s_act_name = st.selectbox("🎯 Quel pôle paralyser ?", options=s_action_names, index=idx_a)
                    s_act_map = {"Prix": "price", "Pub": "marketing", "Qualité": "quality", "R&D": "rd_budget", "RSE": "rse_budget", "Délai Clients": "client_terms", "Délai Fournisseurs": "supplier_terms"}
                    s_act = s_act_map[s_act_name]
                    if s_act != st.session_state[sim_key]["sabotage_action"]:
                        st.session_state[sim_key]["sabotage_action"] = s_act
                        st.session_state[sim_key]["sabotage_action_name"] = s_act_name
                        st.rerun()

            with c_def:
                st.markdown("#### 3. Bouclier Défensif")
                d_target = st.selectbox("Pôle à surveiller", ["Aucune", "Prix", "Pub", "Qualité", "R&D", "RSE"], index=["Aucune", "Prix", "Pub", "Qualité", "R&D", "RSE"].index(st.session_state[sim_key]["defense_target"]))
                d_level = st.selectbox("Budget Cybersécurité", [0, 500000, 1000000, 1500000, 2000000], index=[0, 500000, 1000000, 1500000, 2000000].index(st.session_state[sim_key]["defense_level"]), format_func=lambda x: {0:"0€ (Pas de bouclier)", 500000:"500 K€ (25% chance blocage)", 1000000:"1 M€ (50% chance)", 1500000:"1.5 M€ (75% chance)", 2000000:"2 M€ (Imparable)"}[x])
                if d_target != st.session_state[sim_key]["defense_target"] or d_level != st.session_state[sim_key]["defense_level"]:
                    st.session_state[sim_key]["defense_target"] = d_target
                    st.session_state[sim_key]["defense_level"] = d_level
                    st.rerun()

            st.markdown("---")
            if room["current_year"] > 1:
                level = comp["history"][-1].get("espionnage_level", 0) if comp["history"] else 0
                if level >= 1:
                    st.markdown("##### Données Récupérées (Fin Année N-1)")
                    data_l1 = [{"Équipe": n, "PdM": f"{c['history'][-1]['real_market_share']*100:.1f}%", "Ventes": f"{c['history'][-1]['sales']:.0f}", "Résultat Net": f"{c['history'][-1]['net_income']:,.0f}"} for n, c in room["companies"].items() if c["history"]]
                    st.table(pd.DataFrame(data_l1))
                if level >= 4:
                    st.markdown("### 🏆 Rapport d'Audit Concurrentiel")
                    max_pdm = max([c['history'][-1]['real_market_share'] for c in room["companies"].values()])
                    leader = [n for n, c in room["companies"].items() if c['history'][-1]['real_market_share'] == max_pdm][0]
                    st.success(f"👑 **Le Leader du marché est {leader}** avec {max_pdm*100:.1f}% de PdM.")
                    
                    my_mkt = comp['history'][-1]['mkt']
                    avg_mkt = sum(c['history'][-1]['mkt'] for c in room["companies"].values()) / num_teams
                    st.write(f"- 📢 **Pub :** Vous avez investi {fmt_k(my_mkt)}. La moyenne du marché est de {fmt_k(avg_mkt)}.")
                    
                    my_qual = comp['history'][-1]['qual']
                    max_qual = max([c['history'][-1]['qual'] for c in room["companies"].values()])
                    st.write(f"- ✨ **Qualité :** Le plus haut standard du marché est de {fmt_k(max_qual)} (Le vôtre : {fmt_k(my_qual)}).")
                    
                    my_price = comp['history'][-1]['price']
                    min_price = min([c['history'][-1]['price'] for c in room["companies"].values()])
                    st.write(f"- 🏷️ **Prix :** Le produit le moins cher du marché s'est vendu à {min_price}€ (Vous : {my_price}€).")
