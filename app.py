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
# 1. CONFIGURATION & STATE
# ==========================================
st.set_page_config(page_title="Business Simulator - Édition Ultime", layout="wide", page_icon="💼")

@st.cache_resource
def get_global_games():
    return {}

GAMES = get_global_games()

if "faq_chat" not in st.session_state:
    st.session_state.faq_chat = []

def save_game_to_disk(room):
    with open(f"save_{room['room_code']}.json", "w", encoding="utf-8") as f:
        json.dump(room, f, indent=4, ensure_ascii=False)

def load_game_from_disk(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

# ==========================================
# 2. PRODUITS & CONTEXTE
# ==========================================
PRODUCT_UNIVERSES = [
    {
        "name": "Vélos Électriques Urbains", "unit": "vélos",
        "benchmark_price": 1200.0, "base_cost": 650.0, "base_market_size_per_team": 6000,
        "base_time_per_unit": 0.5, "machine_capacity": 2500, "context": "Mobilité douce en forte croissance."
    },
    {
        "name": "Smartphones Éco-reconditionnés", "unit": "smartphones",
        "benchmark_price": 480.0, "base_cost": 240.0, "base_market_size_per_team": 12000,
        "base_time_per_unit": 0.25, "machine_capacity": 5000, "context": "Forte sensibilité au prix et aux garanties."
    },
    {
        "name": "Enceintes Hi-Fi Premium", "unit": "enceintes",
        "benchmark_price": 340.0, "base_cost": 160.0, "base_market_size_per_team": 8000,
        "base_time_per_unit": 0.35, "machine_capacity": 3500, "context": "Marché de niche audiophile."
    }
]

# ==========================================
# 3. ALÉAS & ANALYSE DE NOM
# ==========================================
EVENTS_POOL = [
    {"type": "neg", "icon": "📉", "txt": "Bad buzz sur Twitter ! Les clients fuient.", "cash": -10000, "pop": -10},
    {"type": "neg", "icon": "🔥", "txt": "Incendie mineur dans l'entrepôt. Pertes sèches.", "cash": -25000, "pop": 0},
    {"type": "neg", "icon": "⚖️", "txt": "Contrôle de l'URSSAF. Amende pour oubli administratif.", "cash": -15000, "pop": 0},
    {"type": "neg", "icon": "🤢", "txt": "Intoxication à la cantine. Salariés ralentis.", "cash": -5000, "pop": -5},
    {"type": "pos", "icon": "🌟", "txt": "Un gros influenceur valide votre produit !", "cash": 20000, "pop": 15},
    {"type": "pos", "icon": "🤝", "txt": "Subvention surprise de l'État pour l'innovation.", "cash": 40000, "pop": 0},
    {"type": "pos", "icon": "🏆", "txt": "Prix de 'L'Entreprise de l'Année' remporté !", "cash": 10000, "pop": 20},
    {"type": "neutral", "icon": "🤷", "txt": "Panne de la machine à café. Grogne des employés.", "cash": -1000, "pop": 0}
]

def analyze_company_name(name):
    name_l = name.lower()
    score = 0.0
    # Utilisation d'un set pour une recherche plus rapide (O(1) au lieu de O(N))
    troll_words = {"caca", "pipi", "boudin", "prout", "zizi", "bite", "cul", "merde", "con", "fuck", "shit", "lol", "mdr", "xd", "test", "truc", "machin", "bidule"}
    
    if any(w in name_l for w in troll_words): score -= 0.10
    elif len(name.strip()) <= 2 or name.strip().isdigit(): score -= 0.09
    elif len(set(name_l.replace(" ", ""))) < 3: score -= 0.09
    elif not name.replace(" ", "").replace("-", "").isalnum(): score -= 0.08
    
    # Remplacement des if multiples par des any() sur des tuples
    if any(w in name_l for w in ("eco", "green", "bio", "durable")): score += 0.06
    if any(w in name_l for w in ("tech", "future", "inov", "smart")): score += 0.07
    if any(w in name_l for w in ("global", "world", "international")): score += 0.10
    if any(w in name_l for w in ("premium", "luxury", "elite")): score += 0.04
    
    if 4 <= len(name) <= 9 and name.isalnum() and score >= 0: score += 0.05
    return max(-0.10, min(0.10, score))

# ==========================================
# 4. MOTEUR MATHÉMATIQUE
# ==========================================
def fmt_k(amount):
    if amount is None: return "0,0 K€"
    # Formatage de chaîne f-string optimisé
    return f"{amount / 1000.0:,.1f} K€".replace(",", " ").replace(".", ",")

def fmt_num(val):
    return f"{val:,.0f}".replace(",", " ")

def init_company(name, start_capital, product):
    return {
        "name": name, "cash": start_capital, "stock": 0, "employees": 2, "machines": 0,
        "brand_awareness": 10.0, "rd_cumul": 0.0, "rse_cumul": 0.0, "loans": [],
        "pending_client_cash": 0.0, "pending_supplier_cash": 0.0, "history": [], "current_decisions": {},
        "draft_decisions": {}, "frozen_fields": [], "name_score": analyze_company_name(name)
    }

def get_default_decs(comp, product):
    last = comp["history"][-1] if comp["history"] else {}
    return {
        "price": float(last.get("price", product["benchmark_price"])),
        "forecast_sales": int(last.get("sales", 3000)), "purchase_qty": int(last.get("sales", 3000)),
        "buy_machines": 0, "marketing": float(last.get("mkt", 10000.0)), "rd_budget": float(last.get("rd", 3000.0)), 
        "rse_budget": float(last.get("rse", 2000.0)),
        "employees": int(comp.get("employees", 2)), "salary": float(last.get("salary", 25000.0)), 
        "quality": float(last.get("qual", 2500.0)), "training": float(last.get("train", 1500.0)), 
        "client_terms": int(last.get("client_terms", 30)), "supplier_terms": int(last.get("supplier_terms", 30)), 
        "new_loan_amount": 0.0, "new_loan_duration": 3, 
        "espionnage": 0, "sabotage_type": 0, "sabotage_target": "", "sabotage_action": "",
        "defense_target": "Aucune", "defense_level": 0
    }

def get_unit_cost(base_cost, rd_total):
    # Remplacement des appels à min/max/math.sqrt par un calcul direct et optimisé si rd_total = 0
    if rd_total <= 0: return base_cost
    reduction = min(0.70, math.sqrt(rd_total) / 2000.0)
    return base_cost * (1.0 - reduction)

def get_hr_metrics(employees, salary, quality_budget, training_budget, base_time):
    total_hours = employees * 1600
    
    # Calculs conditionnels pour éviter des math.sqrt inutiles si le budget est de 0
    time_penalty = min(1.50, 1.0 + (math.sqrt(quality_budget) / 1000.0)) if quality_budget > 0 else 1.0
    time_bonus = max(0.70, 1.0 - (math.sqrt(training_budget) / 1000.0)) if training_budget > 0 else 1.0
    
    motivation = min(1.30, max(0.50, 1.0 + ((salary - 25000) / 25000.0)))
    
    effective_hours = total_hours * motivation
    time_per_unit = base_time * time_penalty * time_bonus
    hr_cap = effective_hours / time_per_unit if time_per_unit > 0 else 0
    return {
        "time_per_unit": time_per_unit, "effective_hours": effective_hours,
        "hr_cap": hr_cap, "productivity_pct": (1.0 / time_per_unit) / (1.0 / base_time) * 100 if base_time > 0 else 0
    }

def get_popularity_gauges(comp, decs):
    rse_val = decs.get("rse_budget", 0) + comp.get("rse_cumul", 0)
    rse_score = min(100.0, math.sqrt(rse_val) / 5.0) if rse_val > 0 else 0.0
    
    qual_val = decs.get("quality", 0)
    qual_score = min(100.0, math.sqrt(qual_val) / 3.0) if qual_val > 0 else 0.0
    
    popularity = (rse_score * 0.4) + (qual_score * 0.6)
    return rse_score, qual_score, popularity

def get_theo_demand(base_demand, price, bench_price, marketing, quality, rse, client_terms, brand_aw, popularity):
    price_ratio = bench_price / price if price > 0 else 1.0
    price_factor = price_ratio ** 1.8
    
    suspicion_penalty = (price / (bench_price * 0.4)) ** 2.5 if price < bench_price * 0.4 else 1.0
    
    # Éviter sqrt(0)
    mkt_factor = 1.0 + (math.sqrt(marketing) / 150.0) if marketing > 0 else 1.0
    qual_factor = 1.0 + (math.sqrt(quality) / 200.0) if quality > 0 else 1.0
    rse_factor = 1.0 + (math.sqrt(rse) / 250.0) if rse > 0 else 1.0
    
    terms_factor = 1.0 + (client_terms / 90.0) * 0.3
    brand_factor = 1.0 + (brand_aw / 100.0) * 0.5
    
    return base_demand * price_factor * mkt_factor * qual_factor * rse_factor * terms_factor * brand_factor * suspicion_penalty

def generate_monthly_cashflow(comp, decs, revenue, purchases_value, expenses, utopia=False):
    c_terms = 0 if utopia else float(decs.get("client_terms", 0))
    s_terms = 120 if utopia else float(decs.get("supplier_terms", 0))
    
    monthly_rev = revenue / 12.0
    monthly_purch = purchases_value / 12.0
    monthly_exp = expenses / 12.0
    
    current_cash = comp["cash"] + comp.get("pending_client_cash", 0) - comp.get("pending_supplier_cash", 0) + decs.get("new_loan_amount", 0)
    
    # Pré-allocation de la liste pour de meilleures performances (bien que minime ici, c'est une bonne pratique)
    curve = [current_cash] * 13
    
    rev_month = int(c_terms / 30)
    purch_month = int(s_terms / 30)
    
    for m in range(1, 13):
        if m > rev_month: current_cash += monthly_rev
        if m > purch_month: current_cash -= monthly_purch
        current_cash -= monthly_exp
        curve[m] = current_cash
        
    return curve

def calculate_forecast(comp, decs, product, is_prod_phase, num_teams, market_growth_rate):
    # Extraction des valeurs avec .get() une seule fois
    price = decs.get("price", product["benchmark_price"])
    marketing = decs.get("marketing", 0.0)
    quality = decs.get("quality", 0.0)
    rd_budget = decs.get("rd_budget", 0.0)
    rse_budget = decs.get("rse_budget", 0.0)
    employees = decs.get("employees", 1)
    salary = decs.get("salary", 30000.0)
    training = decs.get("training", 0.0)
    client_terms = float(decs.get("client_terms", 0))
    supplier_terms = float(decs.get("supplier_terms", 0))
    forecast_sales_input = decs.get("forecast_sales", 0)
    purchase_qty = decs.get("purchase_qty", 0)
    esp = decs.get("espionnage", 0)
    sab_type = decs.get("sabotage_type", 0)
    def_lvl = decs.get("defense_level", 0)
    loan_amount = decs.get("new_loan_amount", 0.0)
    loan_duration = decs.get("new_loan_duration", 3)
    buy_mach = decs.get("buy_machines", 0)
    
    # Calcul des coûts avec des conditions ternaires (plus rapide qu'un lookup dictionnaire)
    intel_cost = (0, 5000, 20000, 50000, 100000)[esp] if esp <= 4 else 0
    intel_cost += (0, 200000, 300000, 500000)[sab_type] if sab_type <= 3 else 0
    intel_cost += def_lvl

    adjusted_base_market = product["base_market_size_per_team"] * (1.0 + market_growth_rate)
    total_market_size_est = adjusted_base_market * num_teams
    
    rse_score, qual_score, popularity = get_popularity_gauges(comp, decs)
    
    theo_demand = get_theo_demand(adjusted_base_market, price, product["benchmark_price"], marketing, quality, rse_budget + comp.get("rse_cumul",0), client_terms, comp["brand_awareness"], popularity)
    theo_demand_no_rse = get_theo_demand(adjusted_base_market, price, product["benchmark_price"], marketing, quality, 0, client_terms, comp["brand_awareness"], popularity)
    
    rse_pdm_gain = (theo_demand - theo_demand_no_rse) / total_market_size_est * 100 if total_market_size_est > 0 else 0
    
    hr_metrics = get_hr_metrics(employees, salary, quality, training, product["base_time_per_unit"])
    hr_cap = hr_metrics["hr_cap"]
    
    total_machines = comp["machines"] + buy_mach
    prod_cap = total_machines * product["machine_capacity"] if is_prod_phase else hr_cap
    
    available_stock = comp["stock"] + purchase_qty
    sales = min(forecast_sales_input, available_stock, hr_cap, prod_cap, theo_demand)
    
    unit_cost = get_unit_cost(product["base_cost"], comp.get("rd_cumul", 0.0) + rd_budget)
    revenue = sales * price
    purchases_value = purchase_qty * unit_cost
    
    hr_cost = employees * salary * 1.45
    depreciation = total_machines * 10000.0 if is_prod_phase else 0.0
    machine_buy_cash = buy_mach * 50000.0 if is_prod_phase else 0.0
    stock_final = available_stock - sales
    storage_cost = stock_final * 4.0
    
    expenses = hr_cost + marketing + quality + training + rd_budget + rse_budget + storage_cost + depreciation + intel_cost
    
    cash_delayed_clients = revenue * (min(client_terms, 365) / 365.0)
    cash_delayed_suppliers = purchases_value * (min(supplier_terms, 365) / 365.0)
    
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
    
    cf_curve = generate_monthly_cashflow(comp, decs, revenue, purchases_value, expenses + interest + tax + repayments + machine_buy_cash)
    hr_cap_utopia = get_hr_metrics(employees, salary, 0, training, product["base_time_per_unit"])["hr_cap"]
    sales_utopia = min(available_stock, hr_cap_utopia, theo_demand * 1.5)
    cf_utopia = generate_monthly_cashflow(comp, decs, sales_utopia * price, purchases_value, expenses, utopia=True)

    est_share = (theo_demand / (total_market_size_est + theo_demand - adjusted_base_market)) * 100 if (total_market_size_est + theo_demand - adjusted_base_market) > 0 else 0
    
    return {
        "sales": sales, "theo_demand": theo_demand, "revenue": revenue, "net_income": net_income,
        "end_cash": end_cash, "stock_final": stock_final, "unit_cost": unit_cost,
        "est_share": est_share, "hr_cap": hr_cap, "target_share": 100.0 / num_teams if num_teams > 0 else 100.0,
        "hr_metrics": hr_metrics, "cogs": purchases_value, "hr_cost": hr_cost, "mkt": marketing, 
        "qual": quality, "train": training, "rd": rd_budget, "rse": rse_budget, "intel_cost": intel_cost,
        "total_market": total_market_size_est, "prod_cap": prod_cap, "depreciation": depreciation, "expenses": expenses,
        "cf_curve": cf_curve, "cf_utopia": cf_utopia, "rse_score": rse_score, "qual_score": qual_score,
        "popularity": popularity, "interest_rate": interest_rate, "rse_pdm_gain": rse_pdm_gain
    }

def resolve_turn(room):
    product = room["product"]
    companies = room["companies"]
    num_teams = len(companies)
    is_prod_phase = (room["current_year"] >= 5)
    
    market_growth = room.get("market_growths", {}).get(str(room["current_year"]), 0.0)
    adjusted_base_market = product["base_market_size_per_team"] * (1.0 + market_growth)
    total_market_demand = adjusted_base_market * num_teams * random.uniform(0.95, 1.05)
    
    # Utilisation d'un set pour des vérifications 'in' O(1)
    SABOTAGE_FIELDS = {"price", "marketing", "quality", "rd_budget", "rse_budget", "client_terms", "supplier_terms"}
    SABOTAGE_LIST = list(SABOTAGE_FIELDS) # Pour le random.choice
    FIELD_NAMES = {"price": "Prix", "marketing": "Pub", "quality": "Qualité", "rd_budget": "R&D", "rse_budget": "RSE", "client_terms": "Délai Clients", "supplier_terms": "Délai Fournisseurs"}
    
    sabotages_to_apply = []
    
    if room["current_year"] > 1:
        # Phase 1: Collecte des attaques
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
    
    # Phase 2: Résolution des attaques vs défenses
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
            sabotage_messages[v].append(f"🛡️ Sabotage sur {FIELD_NAMES.get(act, act)} bloqué avec succès par votre Bouclier !")
            sabotage_messages[sab["attacker"]].append(f"❌ Votre sabotage sur {v} a été bloqué par son bouclier !")
        elif vic_comp["history"]:
            # On applique le gel si l'historique existe
            hist_key = act
            if act == "marketing": hist_key = "mkt"
            elif act == "quality": hist_key = "qual"
            elif act == "rd_budget": hist_key = "rd"
            elif act == "rse_budget": hist_key = "rse"
            
            old_val = vic_comp["history"][-1].get(hist_key, 0)
            vic_comp["current_decisions"][act] = old_val
            frozen_fields_map[v].append(act)
            sabotage_messages[v].append(f"⚠️ SABOTAGE : {FIELD_NAMES.get(act, act)} gelé à l'ancienne valeur !")

    for name, comp in companies.items():
        comp["frozen_fields"] = frozen_fields_map[name]

    # Phase 3: Pré-calcul des scores de demande
    scores = {}
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        rse_tot = dec.get("rse_budget", 0.0) + comp.get("rse_cumul", 0.0)
        _, _, pop = get_popularity_gauges(comp, dec)
        
        name_bonus = 1.0 + comp.get("name_score", 0.0) if room["current_year"] == 1 else 1.0
        
        scores[name] = get_theo_demand(
            adjusted_base_market, 
            dec.get("price", product["benchmark_price"]), 
            product["benchmark_price"], 
            dec.get("marketing", 0.0), 
            dec.get("quality", 0.0), 
            rse_tot, 
            float(dec.get("client_terms", 0)), 
            comp["brand_awareness"], 
            pop
        ) * name_bonus

    total_score = sum(scores.values()) if sum(scores.values()) > 0 else 1.0
    
    # Pré-génération des événements aléatoires
    hazard_msgs = {name: random.choice(EVENTS_POOL) for name in companies.keys()}

    # Phase 4: Résolution principale de chaque entreprise
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        
        # Extraction locale pour éviter les lookups répétés
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
            comp["cash"] -= new_mach * 50000.0
            prod_cap = comp["machines"] * product["machine_capacity"]
            depreciation = comp["machines"] * 10000.0
        else:
            prod_cap = float('inf') # Pas de limite de prod_cap en phase 1
            depreciation = 0.0
            
        team_demand = total_market_demand * (scores[name] / total_score)
        
        available_stock = comp["stock"] + purchase_qty
        hr_cap = get_hr_metrics(employees, salary, qual, train, product["base_time_per_unit"])["hr_cap"]
        
        actual_sales = min(team_demand, available_stock, hr_cap, prod_cap)
            
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
        
        if comp["cash"] < 0:
            overdraft_fee = abs(comp["cash"]) * 0.12
            comp["cash"] -= overdraft_fee
            net_income -= overdraft_fee

        comp["employees"] = employees
        comp["brand_awareness"] = max(1.0, min(100.0, comp["brand_awareness"] + (mkt / 10000.0)))
        
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
                if comp["history"]:
                    comp["history"][-1]["net_income"] -= (remaining_debt * 2)
                    
    save_game_to_disk(room)

# ==========================================
# 5. ASSISTANT & RÈGLES (FAQ BOT)
# ==========================================
def bot_answer(q):
    q = q.lower()
    if any(w in q for w in ("prix", "tarif", "vendre", "vente")): return "Le Prix de Vente est l'arme de destruction massive. Sous 40% du prix moyen = arnaque perçue. Haut = grosse marge mais petit volume."
    elif any(w in q for w in ("pub", "marketing", "publicite", "pub")): return "La Pub booste instantanément les ventes. Objectif idéal : 7.5% à 15% de votre CA."
    elif any(w in q for w in ("qualité", "qualite", "défaut")): return "La Qualité augmente la popularité (Cible: 0.5% à 2.5% du CA). DANGER : exiger de la qualité ralentit vos salariés !"
    elif any(w in q for w in ("rse", "ecologie", "écologie", "social")): return "La RSE est un investissement long terme qui se cumule (Cible : 2% à 5% du CA). Parfait pour fidéliser."
    elif any(w in q for w in ("rh", "employé", "employe", "salarié")): return "Cadence affectée par 3 choses : 1) Motivation (Salaire > 21K). 2) Formation (accélère). 3) Qualité (ralentit)."
    elif any(w in q for w in ("delai", "délais", "client", "paiement")): return "Délai Clients : Booste les ventes, mais vous risquez le découvert bancaire car l'argent rentre tard !"
    elif any(w in q for w in ("fournisseur", "fournisseurs")): return "Délai Fournisseurs : Payer tard préserve votre Trésorerie immédiate."
    elif any(w in q for w in ("rd", "r&d", "recherche")): return "La R&D baisse définitivement le Coût de fabrication (Cible 4% à 5%). L'effet se cumule d'année en année !"
    elif any(w in q for w in ("emprunt", "banque", "dette")): return "Taux de 1% (rentable) à 5% (fragile). À la fin, toute dette non remboursée est doublée et déduite de votre score !"
    elif any(w in q for w in ("sabotage", "bouclier", "défense")): return "Le Sabotage gèle les budgets adverses. Le Bouclier (jusqu'à 2M€) permet de bloquer ces attaques avec 100% de chance."
    elif any(w in q for w in ("stock", "stockage", "invendu")): return "Tout invendu coûte 4€ par an de stockage. Ne produisez pas trop !"
    else: return "Posez votre question avec des mots simples (Ex: 'Comment marche le prix ?', 'A quoi sert la RSE ?', 'Combien coute le stock ?')."

def render_help_and_faq():
    st.sidebar.markdown("---")
    with st.sidebar.expander("📚 Guide, Règles & Assistant", expanded=False):
        t_regles, t_ask = st.tabs(["📖 Règles Rapides", "❓ Poser une question à l'IA"])
        with t_regles:
            st.markdown("""
            **🎯 BUT :** Avoir la plus haute valeur (Cash + Stock) à la fin.
            * **💰 Prix :** Attention à l'effet "arnaque" si trop bas.
            * **📢 Pub :** Effet puissant et immédiat.
            * **🌍 RSE & 🔬 R&D :** Leurs effets se cumulent chaque année.
            * **✨ Qualité :** Booste les ventes mais ralentit le travail en usine.
            * **🎓 Formation :** Accélère le travail en usine.
            * **📦 Stock :** Vous payez 4€ par unité invendue chaque année.
            """)
        with t_ask:
            faq_input = st.text_input("Posez votre question à l'IA du CEO :", key="faq_in")
            if st.button("Demander") and faq_input:
                ans = bot_answer(faq_input)
                st.session_state.faq_chat.append({"q": faq_input, "a": ans})
            for chat in reversed(st.session_state.faq_chat[-3:]):
                st.markdown(f"👤 **Vous:** *{chat['q']}*")
                st.info(f"🤖 **Assistant:** {chat['a']}")

# ==========================================
# 6. UI LOBBY & MAIN
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
            save_game_to_disk(tmp_room)
            st.rerun()

if "room_code" not in st.session_state: st.session_state.room_code = None
if "player_team" not in st.session_state: st.session_state.player_team = None

if not st.session_state.room_code:
    st.markdown("<h1 style='text-align: center;'>💼 Business Simulator - Édition Ultime</h1>", unsafe_allow_html=True)
    
    with st.expander("🎓 TUTO POUR LES DÉBUTANTS - À LIRE AVANT DE JOUER", expanded=False):
        st.markdown("""
        **Bienvenue CEO ! Voici comment ne pas faire faillite dès la 1ère année :**
        
        * 💸 **Le Prix :** S'il est trop bas, vos clients penseront à une arnaque. S'il est trop haut, ils iront chez la concurrence. Trouvez le juste milieu !
        * 📢 **La Pub :** Ça coûte cher, mais ça booste instantanément vos parts de marché. Les experts disent : 7,5% à 15% de votre Chiffre d'Affaires !
        * ✨ **La Qualité :** C'est super pour l'image de marque... MAIS ça demande d'être minutieux. Vos employés produiront **beaucoup moins vite**.
        * 🎓 **La Formation :** À l'inverse de la qualité, elle permet à vos salariés de travailler **plus vite**.
        * 🤝 **La RSE (Écologie/Social) :** La Pub s'oublie vite, mais la RSE se **cumule** chaque année ! C'est le meilleur investissement à long terme pour fidéliser vos clients.
        * 🔬 **La R&D :** Mettez entre 4% et 5% de votre Chiffre d'Affaires pour inventer de nouvelles méthodes de fabrication. Ça réduira drastiquement le coût de fabrication unitaire de vos produits !
        * 📦 **Le Stock :** Attention ! Chaque produit non vendu qui dort dans l'entrepôt vous coûte 4€ de frais de stockage annuel. Ne produisez pas trop !
        
        *Astuce : Vous trouverez des bulles "❓" à côté de chaque bouton dans le jeu pour vous rappeler ces règles !*
        """)

    col_c, col_j = st.columns(2)
    with col_c:
        st.subheader("1️⃣ Créer un Salon (Hôte)")
        with st.form("create_form"):
            host_name = st.text_input("Nom de votre Entreprise")
            num_years = st.slider("Durée du jeu (années)", 4, 10, 8)
            capital_k = st.number_input("Capital de départ (K€)", min_value=50, max_value=500, value=150)
            if st.form_submit_button("Créer la partie", type="primary"):
                if not host_name.strip(): st.error("⚠️ Entrez un nom d'entreprise !")
                else:
                    room_code = f"SALON-{random.randint(1000,9999)}"
                    product = random.choice(PRODUCT_UNIVERSES)
                    market_growths = {str(y): round(random.uniform(0.05, 0.33), 2) for y in range(1, num_years + 1)}
                    room = {
                        "room_code": room_code, "host": host_name.strip(), "product": product,
                        "max_years": num_years, "current_year": 1, "status": "waiting",
                        "start_capital": capital_k * 1000.0, "companies": {}, "ready_teams": [],
                        "market_growths": market_growths, "turn_deadline": None
                    }
                    room["companies"][host_name.strip()] = init_company(host_name.strip(), room["start_capital"], product)
                    GAMES[room_code] = room
                    save_game_to_disk(room)
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
                        save_game_to_disk(room)
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
        
        p_team = st.session_state.player_team
        if p_team in room["companies"]:
            score_name = room["companies"][p_team].get("name_score", 0.0)
            pct_val = round(score_name * 100, 1)
            if score_name > 0: st.markdown(f"<h4 style='color:green;'>Analyse de votre nom : <span style='color:green;'>+{pct_val}% PDM bonus An 1</span></h4>", unsafe_allow_html=True)
            elif score_name < 0: st.markdown(f"<h4 style='color:red;'>Analyse de votre nom : <span style='color:red;'>{pct_val}% PDM malus An 1</span></h4>", unsafe_allow_html=True)
            
        for name in room["companies"].keys(): st.write(f"• **{name}**" + (" *(Hôte)*" if name == room["host"] else ""))
        if st.session_state.player_team == room["host"] and st.button("🚀 Lancer la Partie !", type="primary"):
            room["status"] = "playing"
            save_game_to_disk(room)
            st.rerun()
        if st.button("Actualiser l'écran"): st.rerun()
        
    else:
        st.sidebar.markdown(f"**🔑 Salon:** `{room['room_code']}` | **📅 Année:** {room['current_year']}/{room['max_years']}")
        market_g = room.get("market_growths", {}).get(str(room["current_year"]), 0.15)
        st.sidebar.markdown(f"📈 **Croissance Marché (An {room['current_year']}) :** `+{int(market_g*100)}%`")
        
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
        
        st.title(f"🏢 {selected_team}")
        
        if room.get("turn_deadline") and len(room["ready_teams"]) == num_teams - 1 and room["status"] == "playing":
            time_left = int(room["turn_deadline"] - time.time())
            if time_left > 0:
                mins, secs = divmod(time_left, 60)
                st.error(f"⏳ **ATTENTION :** Plus que **{mins}m {secs}s** avant la validation forcée du dernier joueur !")
                components.html(f"<script>setTimeout(function(){{ window.parent.location.reload(); }}, {time_left * 1000 + 1000});</script>", height=0)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("💸 Trésorerie", fmt_k(comp['cash']))
        m2.metric("📦 Stock Actuel", f"{fmt_num(comp['stock'])} un.")
        m3.metric("👷 Effectif", f"{comp['employees']} sal.")
        m4.metric("🏭 Machines", f"{comp['machines']}" if is_prod_phase else "N/A")
        m5.metric("🏷️ Coût Fab. Base", f"{get_unit_cost(product['base_cost'], comp['rd_cumul']):.1f} €")

        if comp["history"] and comp["history"][-1].get("event_msg"):
            st.warning(f"{comp['history'][-1]['event_msg']}")

        if has_played and room["status"] == "playing":
            st.success("✅ Vos décisions sont validées. En attente des autres joueurs...")
            st.progress(len(room['ready_teams']) / num_teams)
            if st.button("Actualiser"): st.rerun()
            
        elif room["status"] == "ended":
            st.balloons()
            st.header("🏆 Bilan des Performances & Classement Final")
            final_list = [{"Équipe": n, "Valeur Totale Est.": (c["cash"] + c["stock"] * product["base_cost"] * 0.5) / 1000.0} for n, c in room["companies"].items()]
            st.table(pd.DataFrame(final_list).sort_values(by="Valeur Totale Est.", ascending=False).style.format({"Valeur Totale Est.": "{:,.1f} K€"}))

        else:
            tab_recap, tab_dec, tab_sim, tab_treso, tab_bilan = st.tabs(["⏪ Bilan N-1", "✍️ Saisie", "📊 Prévisions", "💸 Tréso", "🕵️ Opérations & Audit"])
            
            sim_key = f"sim_{selected_team}_{room['current_year']}"
            frozen = comp.get("frozen_fields", [])
            if sim_key not in st.session_state: st.session_state[sim_key] = get_default_decs(comp, product)
            
            with tab_recap:
                st.subheader("⏪ Rétrospective : Votre Année N-1")
                if not comp["history"]:
                    st.info("C'est la première année ! Pas encore d'historique.")
                else:
                    last = comp["history"][-1]
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Vos actions N-1 :**\n* Prix : {last['price']} €\n* Pub : {fmt_num(last['mkt'])} €\n* Qualité : {fmt_num(last['qual'])} €\n* R&D : {fmt_num(last['rd'])} €\n* Salaires : {last['salary']} €")
                    with c2:
                        st.markdown(f"**Résultats obtenus :**\n* Ventes : {fmt_num(last['sales'])} unités\n* Chiffre d'Affaires : {fmt_k(last['revenue'])}\n* Parts de marché : {last['real_market_share']*100:.1f}%\n* Résultat Net : {fmt_k(last['net_income'])}")
                    
                    st.markdown("### 🤖 Analyse de vos choix :")
                    if last["price"] < product["benchmark_price"] * 0.4: st.error("🚨 Votre prix est tellement bas que les clients croient à une arnaque (malus de suspicion).")
                    elif last["price"] < last["unit_cost"]: st.error("🚨 Vous avez vendu à perte ! Prix inférieur au coût de fabrication.")
                    else: st.success("✅ Votre tarification est cohérente par rapport à vos coûts.")
                    if last["sales"] < last["theo_demand"]: st.warning(f"⚠️ Vous aviez {fmt_num(last['theo_demand'])} clients potentiels, mais vous n'avez pu en servir que {fmt_num(last['sales'])}. Embauchez ou achetez du stock/machines !")
                    if last["stock"] > last["sales"] * 0.3: st.warning("📦 Beaucoup d'invendus ! Vous payez des frais de stockage (4€/u). Baissez les prix ou la cadence.")
                    if last["salary"] < 21000: st.error("⚠️ Salaire sous le SMIC ! Vos employés sont démotivés et lents.")

            with tab_dec:
                st.write(f"⏱️ **Temps par salarié :** `{product['base_time_per_unit']}h/u` | 🏭 **Capacité machine :** `{product['machine_capacity']} u/an`")
                ca_ref = comp["history"][-1]["revenue"] if comp["history"] else room["start_capital"]

                with st.form(f"form_dec_{selected_team}"):
                    st.markdown("### 🛒 1. Commercial & Logistique")
                    c1, c2, c3 = st.columns(3)
                    with c1: price = st.number_input("🏷️ Prix de Vente (€)", min_value=1.0, value=st.session_state[sim_key]["price"], disabled=("price" in frozen), help=f"Le prix normal est autour de {product['benchmark_price']}€. Trop bas = suspect. Trop haut = besoin de qualité.")
                    with c2: forecast_sales = st.number_input("🎯 Ventes espérées", min_value=0, value=st.session_state[sim_key]["forecast_sales"], step=100, help="Sert uniquement à calculer les prévisions dans l'onglet suivant.")
                    with c3: purchase_qty = st.number_input("📦 Quantité à Produire/Acheter", min_value=0, value=st.session_state[sim_key]["purchase_qty"], step=100, help="Combien d'unités voulez-vous créer cette année ? (S'ajoute au stock existant).")

                    st.markdown("### 🏭 2. Usine, RH & Salaires")
                    p1, p2, p3 = st.columns(3)
                    with p1:
                        employees = st.number_input("👷 Effectif", min_value=1, value=st.session_state[sim_key]["employees"], help="Ils travaillent 1600h par an.")
                        salary = st.number_input("💶 Salaire brut/an (€)", min_value=21000.0, value=st.session_state[sim_key]["salary"], step=1000.0, help="Motive et accélère le rythme (SMIC = 21000€).")
                    with p2:
                        training = st.number_input("🎓 Formation (€)", min_value=0.0, value=st.session_state[sim_key]["training"], step=500.0, help="Accélère le temps de fabrication des salariés.")
                        quality = st.number_input("✨ Qualité (€)", min_value=0.0, value=st.session_state[sim_key]["quality"], step=500.0, disabled=("quality" in frozen), help="Booste les ventes. DANGER : Ralentit vos salariés qui doivent être plus minutieux !")
                        st.caption(f"Ratio Qualité: {quality/ca_ref*100:.1f}% du CA de réf. (Cible: 0.5-2.5%)")
                    with p3:
                        buy_machines = st.number_input("🏭 Acheter Machines (50K€)", min_value=0, value=st.session_state[sim_key]["buy_machines"], disabled=not is_prod_phase, help=f"Dispo à l'Année 5. 1 machine fait {product['machine_capacity']} unités/an.")

                    st.markdown("### 🚀 3. Stratégie, Budget & Banque")
                    f1, f2, f3 = st.columns(3)
                    with f1:
                        marketing = st.number_input("📢 Pub (€)", min_value=0.0, value=st.session_state[sim_key]["marketing"], step=1000.0, disabled=("marketing" in frozen), help="Booste vos parts de marché immédiatement.")
                        st.caption(f"Ratio Pub: {marketing/ca_ref*100:.1f}% du CA de réf. (Cible: 7.5-15%)")
                        rd_budget = st.number_input("🔬 R&D (€)", min_value=0.0, value=st.session_state[sim_key]["rd_budget"], step=1000.0, disabled=("rd_budget" in frozen), help="Baisse le coût unitaire à VIE ! Se cumule d'année en année.")
                        st.caption(f"Ratio R&D: {rd_budget/ca_ref*100:.1f}% du CA de réf. (Cible: 4-5%)")
                        rse_budget = st.number_input("🌍 RSE (€)", min_value=0.0, value=st.session_state[sim_key]["rse_budget"], step=1000.0, disabled=("rse_budget" in frozen), help="Fidélise les clients durablement. Effet cumulatif !")
                        st.caption(f"Ratio RSE: {rse_budget/ca_ref*100:.1f}% du CA de réf. (Cible: 2-5%)")
                    with f2:
                        client_terms = st.number_input("⏳ Délai Clients (j)", min_value=0, max_value=120, value=st.session_state[sim_key]["client_terms"], disabled=("client_terms" in frozen), help="Autoriser à payer tard augmente VOS VENTES, mais retarde VOTRE CASH.")
                        supplier_terms = st.number_input("⏳ Délai Fournisseurs (j)", min_value=0, max_value=120, value=st.session_state[sim_key]["supplier_terms"], disabled=("supplier_terms" in frozen), help="Payer tard préserve votre trésorerie immédiate.")
                    with f3:
                        loan_amount = st.number_input("🏦 Emprunt (€)", min_value=0.0, value=st.session_state[sim_key]["new_loan_amount"], step=5000.0, help="Taux de 1% à 5% selon votre Résultat N-1.")
                        loan_duration = st.slider("📅 Durée emprunt", 1, 5, value=st.session_state[sim_key]["new_loan_duration"])

                    if frozen:
                        st.warning(f"🔒 SABOTAGE EN COURS ! Impossible de modifier : {', '.join(frozen)}")

                    calc_btn = st.form_submit_button("🔄 Calculer & Sauvegarder (Brouillon)")

                if calc_btn:
                    st.session_state[sim_key].update({
                        "price": price, "forecast_sales": forecast_sales, "purchase_qty": purchase_qty,
                        "buy_machines": buy_machines, "marketing": marketing, "rd_budget": rd_budget,
                        "rse_budget": rse_budget, "employees": employees, "salary": salary,
                        "quality": quality, "training": training, "client_terms": client_terms,
                        "supplier_terms": supplier_terms, "new_loan_amount": loan_amount,
                        "new_loan_duration": loan_duration
                    })
                    comp["draft_decisions"] = st.session_state[sim_key].copy()
                    save_game_to_disk(room)

                st.markdown("---")
                if st.button("🔒 VALIDER DÉFINITIVEMENT L'ANNÉE", type="primary"):
                    comp["current_decisions"] = st.session_state[sim_key].copy()
                    room["ready_teams"].append(selected_team)
                    if len(room["ready_teams"]) == num_teams - 1: room["turn_deadline"] = time.time() + 300 
                    elif len(room["ready_teams"]) == num_teams: room["turn_deadline"] = None
                    save_game_to_disk(room)
                    st.rerun()

            forecast = calculate_forecast(comp, st.session_state[sim_key], product, is_prod_phase, num_teams, market_g)
            st.session_state[f"cf_{selected_team}_{room['current_year']}"] = forecast["cf_curve"]
            
            with tab_sim:
                st.subheader("📊 Prévisions de l'Année")
                st.info(f"💡 **Impact RSE :** Votre politique RSE vous fait gagner virtuellement **+{forecast['rse_pdm_gain']:.1f}%** de parts de marché cette année !")
                
                c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
                c_kpi1.metric("🏷️ Coût de Prod. Unitaire (baisse grâce à R&D)", f"{forecast['unit_cost']:.2f} €")
                c_kpi2.metric("🏦 Taux d'intérêt estimé", f"{forecast['interest_rate']*100:.0f}%")
                c_kpi3.metric("🏭 Capacité de vos employés", f"{fmt_num(forecast['hr_cap'])} unités")
                
                df_pl = pd.DataFrame([
                    {"Poste": "Chiffre d'Affaires", "Prévu N": forecast["revenue"]},
                    {"Poste": "Coût Achats/Prod", "Prévu N": forecast["cogs"]},
                    {"Poste": "Marge Brute", "Prévu N": forecast["revenue"] - forecast["cogs"]},
                    {"Poste": "Masse Salariale", "Prévu N": forecast["hr_cost"]},
                    {"Poste": "Charges Fixes (Pub, R&D, Intel...)", "Prévu N": forecast["expenses"] - forecast["hr_cost"] - forecast["depreciation"]},
                    {"Poste": "RÉSULTAT NET", "Prévu N": forecast["net_income"]}
                ])
                st.table(df_pl.style.format({"Prévu N": "{:,.0f} €"}))

            with tab_treso:
                st.subheader("💸 Flux de Trésorerie (12 Mois)")
                max_overdraft = st.slider("Ajuster la limite de découvert estimée (€)", min_value=0, max_value=int(ca_ref * 0.25), value=10000, step=1000)
                
                months = list(range(0, 13))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=months, y=forecast["cf_utopia"], mode='lines', name='Utopique (0 Jours clients)', line=dict(color='green', dash='dot')))
                fig.add_trace(go.Scatter(x=months, y=forecast["cf_curve"], mode='lines+markers', name='Votre Trésorerie Prévue', line=dict(color='blue', width=3)))
                fig.add_trace(go.Scatter(x=months, y=[-max_overdraft]*13, mode='lines', name='Limite Découvert', line=dict(color='red', dash='dash')))
                
                fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

            with tab_bilan:
                st.subheader("🕵️ Espionnage, Sabotage & Défense")
                c_esp, c_sab, c_def = st.columns(3)
                with c_esp:
                    st.markdown("#### 1. Espionnage (N-1)")
                    esp = st.selectbox("Niveau", options=[0,1,2,3,4], index=st.session_state[sim_key]["espionnage"], format_func=lambda x: {0:"0€ - Rien", 1:"5K€ - Ventes", 2:"20K€ - Budgets", 3:"50K€ - Tréso", 4:"100K€ - L'Audit Comparatif"}[x])
                    if esp != st.session_state[sim_key]["espionnage"]:
                        st.session_state[sim_key]["espionnage"] = esp; st.rerun()

                with c_sab:
                    st.markdown("#### 2. Sabotage Offensif")
                    s_type = st.selectbox("Frappe", options=[0,1,2,3], index=st.session_state[sim_key]["sabotage_type"], format_func=lambda x: {0:"0€ - Rien", 1:"200K€ - Aléatoire", 2:"300K€ - Cible fixée", 3:"500K€ - Chirurgical (Cible+Action)"}[x], disabled=(room["current_year"] == 1))
                    other_teams = [t for t in room["companies"].keys() if t != selected_team]
                    if s_type != st.session_state[sim_key]["sabotage_type"]:
                        st.session_state[sim_key]["sabotage_type"] = s_type; st.rerun()
                    if s_type in (2, 3) and other_teams:
                        idx_t = other_teams.index(st.session_state[sim_key]["sabotage_target"]) if st.session_state[sim_key]["sabotage_target"] in other_teams else 0
                        s_target = st.selectbox("🎯 Cible", options=other_teams, index=idx_t)
                        if s_target != st.session_state[sim_key]["sabotage_target"]:
                            st.session_state[sim_key]["sabotage_target"] = s_target; st.rerun()
                    if s_type == 3:
                        s_action_names = ["Prix", "Pub", "Qualité", "R&D", "RSE", "Délai Clients", "Délai Fournisseurs"]
                        idx_a = s_action_names.index(st.session_state[sim_key].get("sabotage_action_name", "Prix")) if st.session_state[sim_key].get("sabotage_action_name", "Prix") in s_action_names else 0
                        s_act_name = st.selectbox("🎯 Geler quoi ?", options=s_action_names, index=idx_a)
                        s_act_map = {"Prix": "price", "Pub": "marketing", "Qualité": "quality", "R&D": "rd_budget", "RSE": "rse_budget", "Délai Clients": "client_terms", "Délai Fournisseurs": "supplier_terms"}
                        s_act = s_act_map[s_act_name]
                        if s_act != st.session_state[sim_key]["sabotage_action"]:
                            st.session_state[sim_key]["sabotage_action"] = s_act
                            st.session_state[sim_key]["sabotage_action_name"] = s_act_name
                            st.rerun()

                with c_def:
                    st.markdown("#### 3. Bouclier Défensif")
                    d_target = st.selectbox("Protéger quoi ?", ["Aucune", "Prix", "Pub", "Qualité", "R&D", "RSE"], index=["Aucune", "Prix", "Pub", "Qualité", "R&D", "RSE"].index(st.session_state[sim_key]["defense_target"]))
                    d_level = st.selectbox("Budget Bouclier", [0, 500000, 1000000, 1500000, 2000000], index=[0, 500000, 1000000, 1500000, 2000000].index(st.session_state[sim_key]["defense_level"]), format_func=lambda x: {0:"0€ (Désactivé)", 500000:"500 K€ (25% block)", 1000000:"1 M€ (50% block)", 1500000:"1.5 M€ (75% block)", 2000000:"2 M€ (100% Imparable)"}[x])
                    if d_target != st.session_state[sim_key]["defense_target"] or d_level != st.session_state[sim_key]["defense_level"]:
                        st.session_state[sim_key]["defense_target"] = d_target
                        st.session_state[sim_key]["defense_level"] = d_level
                        st.rerun()

                st.markdown("---")
                if room["current_year"] > 1:
                    level = comp["history"][-1].get("espionnage_level", 0) if comp["history"] else 0
                    if level >= 1:
                        st.markdown("##### Données Récupérées (Année N-1)")
                        data_l1 = [{"Équipe": n, "PdM": f"{c['history'][-1]['real_market_share']*100:.1f}%", "Ventes": f"{c['history'][-1]['sales']:.0f}", "Résultat Net": f"{c['history'][-1]['net_income']:,.0f}"} for n, c in room["companies"].items() if c["history"]]
                        st.table(pd.DataFrame(data_l1))
                    if level >= 4:
                        st.markdown("### 🏆 L'Audit Comparatif Détaillé")
                        max_pdm = max([c['history'][-1]['real_market_share'] for c in room["companies"].values()])
                        leader = [n for n, c in room["companies"].items() if c['history'][-1]['real_market_share'] == max_pdm][0]
                        st.success(f"👑 **Le Leader du marché est {leader}** avec {max_pdm*100:.1f}% de PdM.")
                        
                        my_mkt = comp['history'][-1]['mkt']
                        avg_mkt = sum(c['history'][-1]['mkt'] for c in room["companies"].values()) / num_teams
                        st.write(f"- 📢 **Pub :** Vous avez investi {fmt_k(my_mkt)}. La moyenne du marché est de {fmt_k(avg_mkt)}.")
                        if my_mkt < avg_mkt: st.markdown("👉 *Conseil : Vous êtes en dessous de la moyenne. Si vous voulez des volumes, rattrapez votre retard.*")
                        
                        my_qual = comp['history'][-1]['qual']
                        max_qual = max([c['history'][-1]['qual'] for c in room["companies"].values()])
                        st.write(f"- ✨ **Qualité :** Le plus haut standard du marché est de {fmt_k(max_qual)} (Le vôtre : {fmt_k(my_qual)}).")
                        
                        my_price = comp['history'][-1]['price']
                        min_price = min([c['history'][-1]['price'] for c in room["companies"].values()])
                        st.write
