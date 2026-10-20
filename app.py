import json
import os
import random
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Business Simulator - Édition Ultime", layout="wide")

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
# 3. ANALYSE DU NOM D'ENTREPRISE 
# ==========================================
def analyze_company_name(name):
    name_l = name.lower()
    score = 0.0
    troll_words = ["caca", "pipi", "boudin", "prout", "zizi", "bite", "cul", "merde", "con", "fuck", "shit", "mort", "kill", "pute", "salaud", "lol", "mdr", "xd", "ptdr", "swag", "yolo", "test", "truc", "machin", "bidule", "chouette"]
    
    if any(w in name_l for w in troll_words): score -= 0.10
    elif len(name.strip()) <= 2 or name.strip().isdigit(): score -= 0.09
    elif len(set(name_l.replace(" ", ""))) < 3: score -= 0.09
    elif not name.replace(" ", "").replace("-", "").isalnum(): score -= 0.08
    elif len(name) > 25: score -= 0.03
    elif name.strip().lower() in ["entreprise", "societe", "compagnie", "shop", "boite"]: score -= 0.02
    
    if "eco" in name_l or "green" in name_l or "bio" in name_l or "durable" in name_l: score += 0.06
    if "tech" in name_l or "future" in name_l or "inov" in name_l or "smart" in name_l: score += 0.07
    if "global" in name_l or "world" in name_l or "international" in name_l: score += 0.10
    if "premium" in name_l or "luxury" in name_l or "elite" in name_l: score += 0.04
    
    if 4 <= len(name) <= 9 and name.isalnum() and score >= 0: score += 0.05
    return max(-0.10, min(0.10, score))

# ==========================================
# 4. MOTEUR MATHÉMATIQUE
# ==========================================
def fmt_k(amount):
    if amount is None: return "0,0 K€"
    return f"{amount / 1000.0:,.1f} K€".replace(",", " ").replace(".", ",")

def fmt_num(val):
    return f"{val:,.0f}".replace(",", " ")

def get_default_decs(comp, product):
    last = comp["history"][-1] if comp["history"] else {}
    return {
        "price": float(last.get("price", product["benchmark_price"])),
        "forecast_sales": int(last.get("sales", 3000)), "purchase_qty": int(last.get("sales", 3000)),
        "buy_machines": 0, "marketing": 10000.0, "rd_budget": 3000.0, "rse_budget": 2000.0,
        "employees": int(comp.get("employees", 2)), "salary": 30000.0, "quality": 2500.0,
        "training": 1500.0, "client_terms": 30, "supplier_terms": 30, "new_loan_amount": 0.0,
        "new_loan_duration": 3, "espionnage": 0, "sabotage_type": 0, "sabotage_target": "", "sabotage_action": ""
    }

def init_company(name, start_capital, product):
    name_score = analyze_company_name(name)
    return {
        "name": name, "cash": start_capital, "stock": 0, "employees": 2, "machines": 0,
        "brand_awareness": 10.0, "rd_cumul": 0.0, "rse_cumul": 0.0, "loans": [],
        "pending_client_cash": 0.0, "pending_supplier_cash": 0.0, "history": [], "current_decisions": {},
        "draft_decisions": {}, "name_score": name_score, "frozen_fields": []
    }

def get_unit_cost(base_cost, rd_total):
    discount = min(0.25, rd_total / 150000.0)
    return base_cost * (1.0 - discount)

def get_hr_metrics(employees, salary, quality_budget, training_budget, base_time):
    total_hours = employees * 1600
    time_penalty = min(1.20, 1.0 + (quality_budget / 50000.0) * 0.20)
    time_bonus = max(0.85, 1.0 - (training_budget / 20000.0) * 0.15)
    motivation = min(1.10, max(0.80, 1.0 + ((salary - 30000) / 30000.0) * 0.20))
    effective_hours = total_hours * motivation
    time_per_unit = base_time * time_penalty * time_bonus
    hr_cap = effective_hours / time_per_unit if time_per_unit > 0 else 0
    return {
        "time_per_unit": time_per_unit, "effective_hours": effective_hours,
        "hr_cap": hr_cap, "productivity_pct": (1.0 / time_per_unit) / (1.0 / base_time) * 100
    }

def get_popularity_gauges(comp, decs):
    rse_val = decs.get("rse_budget", 0) + comp.get("rse_cumul", 0)
    rse_score = min(100.0, (rse_val / 30000.0) * 100)
    qual_val = decs.get("quality", 0)
    qual_score = min(100.0, (qual_val / 20000.0) * 100)
    popularity = (rse_score * 0.4) + (qual_score * 0.6)
    return rse_score, qual_score, popularity

def get_theo_demand(base_demand, price, bench_price, marketing, quality, rse, client_terms, brand_aw, popularity):
    price_ratio = bench_price / price if price > 0 else 1.0
    price_factor = min(2.5, max(0.3, price_ratio ** 1.8))
    
    suspicion_penalty = 1.0
    if price < bench_price * 0.4:
        suspicion_penalty = (price / (bench_price * 0.4)) ** 2.5 
    
    mkt_factor = min(1.5, 1.0 + (marketing / 40000.0))
    qual_factor = min(1.3, 1.0 + (quality / 30000.0))
    rse_factor = min(1.15, 1.0 + (rse / 20000.0))
    terms_factor = min(1.2, 1.0 + (client_terms / 90.0) * 0.2)
    brand_factor = min(1.5, 1.0 + (brand_aw / 100.0) * 0.5)
    pop_factor = 1.0 + (popularity / 200.0)
    
    demand = base_demand * price_factor * mkt_factor * qual_factor * rse_factor * terms_factor * brand_factor * pop_factor * suspicion_penalty
    return min(demand, base_demand * 4.0)

def generate_monthly_cashflow(comp, decs, revenue, purchases_value, expenses, utopia=False):
    c_terms = 0 if utopia else float(decs.get("client_terms", 0))
    s_terms = 120 if utopia else float(decs.get("supplier_terms", 0))
    monthly_rev = revenue / 12
    monthly_purch = purchases_value / 12
    monthly_exp = expenses / 12
    
    current_cash = comp["cash"] + comp.get("pending_client_cash", 0) - comp.get("pending_supplier_cash", 0) + decs.get("new_loan_amount", 0)
    curve = [comp["cash"]]
    for m in range(1, 13):
        if m > (c_terms / 30): current_cash += monthly_rev
        if m > (s_terms / 30): current_cash -= monthly_purch
        current_cash -= monthly_exp
        curve.append(current_cash)
    return curve

def calculate_forecast(comp, decs, product, is_prod_phase, num_teams, market_growth_rate):
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
    
    esp_costs = {0: 0, 1: 5000, 2: 20000, 3: 50000, 4: 100000}
    sab_costs = {0: 0, 1: 200000, 2: 300000, 3: 500000}
    intel_cost = esp_costs.get(decs.get("espionnage", 0), 0) + sab_costs.get(decs.get("sabotage_type", 0), 0)

    adjusted_base_market = product["base_market_size_per_team"] * (1.0 + market_growth_rate)
    total_market_size_est = adjusted_base_market * num_teams
    
    rse_score, qual_score, popularity = get_popularity_gauges(comp, decs)
    theo_demand = get_theo_demand(adjusted_base_market, price, product["benchmark_price"], marketing, quality, rse_budget, client_terms, comp["brand_awareness"], popularity)
    
    hr_metrics = get_hr_metrics(employees, salary, quality, training, product["base_time_per_unit"])
    hr_cap = hr_metrics["hr_cap"]
    
    total_machines = comp["machines"] + decs.get("buy_machines", 0)
    prod_cap = total_machines * product["machine_capacity"] if is_prod_phase else hr_cap
    max_possible_sales = min(hr_cap, prod_cap)

    available_stock = comp["stock"] + purchase_qty
    sales = min(forecast_sales_input, available_stock, max_possible_sales, theo_demand)
    
    unit_cost = get_unit_cost(product["base_cost"], comp.get("rd_cumul", 0.0) + rd_budget)
    revenue = sales * price
    purchases_value = purchase_qty * unit_cost
    
    hr_cost = employees * salary * 1.45
    depreciation = total_machines * 10000.0 if is_prod_phase else 0.0
    machine_buy_cash = decs.get("buy_machines", 0) * 50000.0 if is_prod_phase else 0.0
    stock_final = available_stock - sales
    storage_cost = stock_final * 4.0
    
    expenses = hr_cost + marketing + quality + training + rd_budget + rse_budget + storage_cost + depreciation + intel_cost
    
    cash_delayed_clients = revenue * (min(client_terms, 365) / 365.0)
    cash_delayed_suppliers = purchases_value * (min(supplier_terms, 365) / 365.0)
    
    loan_amount = decs.get("new_loan_amount", 0.0)
    loan_duration = decs.get("new_loan_duration", 3)
    
    prev_net_income = comp["history"][-1]["net_income"] if comp["history"] else comp["cash"] * 0.2
    interest_rate = 0.05
    if loan_amount > 0:
        if prev_net_income >= loan_amount: interest_rate = 0.01
        elif prev_net_income >= loan_amount / 2: interest_rate = 0.02
        elif prev_net_income >= loan_amount / 3: interest_rate = 0.03
        elif prev_net_income >= loan_amount / 4: interest_rate = 0.04
        else: interest_rate = 0.05
        
    interest = sum([l["amount"] * l["rate"] for l in comp.get("loans", [])])
    if loan_amount > 0: interest += loan_amount * interest_rate
        
    net_before_tax = (revenue - purchases_value) - expenses - interest
    tax = net_before_tax * 0.25 if net_before_tax > 0 else 0.0
    net_income = net_before_tax - tax
    repayments = sum([l["annuity"] for l in comp.get("loans", []) if l["remaining_years"] > 0])
    
    cash_in = (revenue - cash_delayed_clients) + comp.get("pending_client_cash", 0.0) + loan_amount
    cash_out = (purchases_value - cash_delayed_suppliers) + comp.get("pending_supplier_cash", 0.0) + (expenses - depreciation) + machine_buy_cash + interest + tax + repayments
    end_cash = comp["cash"] + cash_in - cash_out
    
    cf_curve = generate_monthly_cashflow(comp, decs, revenue, purchases_value, expenses + interest + tax + repayments + machine_buy_cash)
    hr_cap_utopia = get_hr_metrics(employees, salary, 0, training, product["base_time_per_unit"])["hr_cap"]
    sales_utopia = min(available_stock, hr_cap_utopia, theo_demand * 1.5)
    cf_utopia = generate_monthly_cashflow(comp, decs, sales_utopia * price, purchases_value, expenses, utopia=True)

    est_share = (theo_demand / (total_market_size_est + theo_demand - adjusted_base_market)) * 100
    
    return {
        "sales": sales, "theo_demand": theo_demand, "revenue": revenue, "net_income": net_income,
        "end_cash": end_cash, "stock_final": stock_final, "unit_cost": unit_cost,
        "est_share": est_share, "hr_cap": hr_cap, "target_share": 100.0 / num_teams if num_teams > 0 else 100.0,
        "hr_metrics": hr_metrics, "cogs": purchases_value, "hr_cost": hr_cost, "mkt": marketing, 
        "qual": quality, "train": training, "rd": rd_budget, "rse": rse_budget, "intel_cost": intel_cost,
        "total_market": total_market_size_est, "prod_cap": prod_cap, "depreciation": depreciation, "expenses": expenses,
        "cf_curve": cf_curve, "cf_utopia": cf_utopia, "rse_score": rse_score, "qual_score": qual_score,
        "popularity": popularity, "interest_rate": interest_rate
    }

def resolve_turn(room):
    product = room["product"]
    companies = room["companies"]
    num_teams = len(companies)
    is_prod_phase = (room["current_year"] >= 5)
    
    market_growth = room.get("market_growths", {}).get(str(room["current_year"]), 0.0)
    adjusted_base_market = product["base_market_size_per_team"] * (1.0 + market_growth)
    total_market_demand = adjusted_base_market * num_teams * random.uniform(0.95, 1.05)
    
    SABOTAGE_FIELDS = ["price", "marketing", "quality", "rd_budget", "rse_budget", "client_terms", "supplier_terms"]
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
                    action = random.choice(SABOTAGE_FIELDS)
                elif s_type == 2:
                    if victim not in other_teams: victim = random.choice(other_teams)
                    action = random.choice(SABOTAGE_FIELDS)
                elif s_type == 3:
                    if victim not in other_teams: victim = random.choice(other_teams)
                    if action not in SABOTAGE_FIELDS: action = random.choice(SABOTAGE_FIELDS)
                sabotages_to_apply.append({"victim": victim, "action": action})

    sabotage_messages = {t: [] for t in companies.keys()}
    frozen_fields_map = {t: [] for t in companies.keys()}
    
    for sab in sabotages_to_apply:
        v = sab["victim"]
        act = sab["action"]
        vic_comp = companies[v]
        if vic_comp["history"]:
            hist_key = act
            if act == "marketing": hist_key = "mkt"
            if act == "quality": hist_key = "qual"
            if act == "rd_budget": hist_key = "rd"
            if act == "rse_budget": hist_key = "rse"
            old_val = vic_comp["history"][-1].get(hist_key, 0)
            vic_comp["current_decisions"][act] = old_val
            frozen_fields_map[v].append(act)
            sabotage_messages[v].append(FIELD_NAMES[act])

    for name, comp in companies.items():
        comp["frozen_fields"] = frozen_fields_map[name]

    scores = {}
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        price = dec.get("price", product["benchmark_price"])
        rse_tot = dec.get("rse_budget", 0.0) + comp.get("rse_cumul", 0.0)
        _, _, pop = get_popularity_gauges(comp, dec)
        
        name_bonus = 1.0 + comp.get("name_score", 0.0) if room["current_year"] == 1 else 1.0
        
        scores[name] = get_theo_demand(adjusted_base_market, price, product["benchmark_price"], 
                                       dec.get("marketing", 0.0), dec.get("quality", 0.0), rse_tot, 
                                       float(dec.get("client_terms", 0)), comp["brand_awareness"], pop) * name_bonus

    total_score = sum(scores.values()) if sum(scores.values()) > 0 else 1.0
    esp_costs = {0: 0, 1: 5000, 2: 20000, 3: 50000, 4: 100000}
    sab_costs = {0: 0, 1: 200000, 2: 300000, 3: 500000}
    
    hazard_msgs = {}
    for name in companies.keys():
        r_haz = random.random()
        if r_haz < 0.15:
            hazard_msgs[name] = {"type": "neg", "txt": random.choice(["📉 Grève transports (-15 K€).", "🔥 Panne machine (-15 K€).", "⚖️ Contrôle fiscal (-15 K€)."])}
        elif r_haz < 0.25:
            hazard_msgs[name] = {"type": "pos", "txt": random.choice(["🌟 Buzz (+15 K€).", "🤝 Gros contrat (+15 K€).", "💡 Subvention (+15 K€)."])}
        else:
            hazard_msgs[name] = {"type": "none", "txt": ""}

    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        
        rd_bud = dec.get("rd_budget", 0.0)
        comp["rd_cumul"] += rd_bud
        comp["rse_cumul"] += dec.get("rse_budget", 0.0)
        unit_cost = get_unit_cost(product["base_cost"], comp["rd_cumul"])
        intel_cost = esp_costs.get(dec.get("espionnage", 0), 0) + sab_costs.get(dec.get("sabotage_type", 0), 0)
        
        if is_prod_phase:
            new_mach = dec.get("buy_machines", 0)
            comp["machines"] += new_mach
            comp["cash"] -= new_mach * 50000.0
            prod_cap = comp["machines"] * product["machine_capacity"]
        else:
            prod_cap = 0
            
        theo_share = scores[name] / total_score
        team_demand = total_market_demand * theo_share
        
        purchase_qty = dec.get("purchase_qty", 0)
        available_stock = comp["stock"] + purchase_qty
        hr_metrics = get_hr_metrics(comp["employees"], dec.get("salary", 30000.0), dec.get("quality", 0.0), dec.get("training", 0.0), product["base_time_per_unit"])
        hr_cap = hr_metrics["hr_cap"]
        
        if is_prod_phase:
            actual_sales = min(team_demand, available_stock, hr_cap, prod_cap)
        else:
            actual_sales = min(team_demand, available_stock, hr_cap)
            
        real_market_share = actual_sales / total_market_demand
        revenue = actual_sales * dec.get("price", product["benchmark_price"])
        
        client_terms = float(dec.get("client_terms", 0))
        cash_delayed_clients = revenue * (min(client_terms, 365) / 365.0)
        cash_in_sales = revenue - cash_delayed_clients + comp.get("pending_client_cash", 0.0)
        comp["pending_client_cash"] = cash_delayed_clients
        
        purchases_value = purchase_qty * unit_cost
        supplier_terms = float(dec.get("supplier_terms", 0))
        cash_delayed_suppliers = purchases_value * (min(supplier_terms, 365) / 365.0)
        cash_out_purchases = purchases_value - cash_delayed_suppliers + comp.get("pending_supplier_cash", 0.0)
        comp["pending_supplier_cash"] = cash_delayed_suppliers
        
        employees = dec.get("employees", 1)
        salary = dec.get("salary", 30000.0)
        hr_cost = employees * salary * 1.45
        depreciation = comp["machines"] * 10000.0 if is_prod_phase else 0.0
        comp["stock"] = available_stock - actual_sales
        storage_cost = comp["stock"] * 4.0
        
        expenses = hr_cost + dec.get("marketing", 0.0) + dec.get("quality", 0.0) + dec.get("training", 0.0) + rd_bud + dec.get("rse_budget", 0.0) + storage_cost + depreciation + intel_cost
        
        loan_amount = dec.get("new_loan_amount", 0.0)
        loan_duration = dec.get("new_loan_duration", 3)
        prev_net_income = comp["history"][-1]["net_income"] if comp["history"] else comp["cash"] * 0.2
        
        interest_rate = 0.05
        if loan_amount > 0:
            if prev_net_income >= loan_amount: interest_rate = 0.01
            elif prev_net_income >= loan_amount / 2: interest_rate = 0.02
            elif prev_net_income >= loan_amount / 3: interest_rate = 0.03
            elif prev_net_income >= loan_amount / 4: interest_rate = 0.04
            else: interest_rate = 0.05
            
        if loan_amount > 0:
            comp["loans"].append({"amount": loan_amount, "annuity": loan_amount / loan_duration, "remaining_years": loan_duration, "rate": interest_rate})
            comp["cash"] += loan_amount
            
        interest = sum([l["amount"] * l["rate"] for l in comp["loans"] if l["remaining_years"] > 0])
        repayments = sum([l["annuity"] for l in comp["loans"] if l["remaining_years"] > 0])
        for l in comp["loans"]:
            if l["remaining_years"] > 0:
                l["amount"] -= l["annuity"]
                l["remaining_years"] -= 1
        
        net_before_tax = (revenue - purchases_value) - expenses - interest
        tax = net_before_tax * 0.25 if net_before_tax > 0 else 0.0
        net_income = net_before_tax - tax
        
        haz = hazard_msgs[name]
        haz_cash_impact = 0.0
        if haz["type"] == "neg": haz_cash_impact = -15000.0
        elif haz["type"] == "pos": haz_cash_impact = 15000.0
            
        comp["cash"] += cash_in_sales - cash_out_purchases - (expenses - depreciation) - interest - tax - repayments + haz_cash_impact
        
        if comp["cash"] < 0:
            overdraft_fee = abs(comp["cash"]) * 0.12
            comp["cash"] -= overdraft_fee
            net_income -= overdraft_fee

        comp["employees"] = employees
        comp["brand_awareness"] = max(1.0, min(100.0, comp["brand_awareness"] + (dec.get("marketing", 0.0) / 10000.0)))
        
        msg_sabot = f"Vos actions bloquées : {', '.join(sabotage_messages[name])}" if sabotage_messages[name] else ""
        full_msg = f"{msg_sabot} | Aléa : {haz['txt']}" if haz['txt'] else msg_sabot

        comp["history"].append({
            "year": room["current_year"], "sales": actual_sales, "theo_demand": team_demand, 
            "hr_cap": hr_cap, "prod_cap": prod_cap, "available_stock": available_stock,
            "real_market_share": real_market_share, "revenue": revenue, "cogs": purchases_value, 
            "hr_cost": hr_cost, "mkt": dec.get("marketing", 0), "qual": dec.get("quality", 0), 
            "train": dec.get("training", 0), "rd": rd_bud, "rse": dec.get("rse_budget", 0),
            "client_terms": client_terms, "supplier_terms": supplier_terms,
            "intel_cost": intel_cost, "depreciation": depreciation, "storage": storage_cost,
            "net_income": net_income, "cash": comp["cash"], "stock": comp["stock"],
            "price": dec.get("price", product["benchmark_price"]), "unit_cost": unit_cost, 
            "salary": salary, "employees": employees,
            "espionnage_level": dec.get("espionnage", 0), "event_msg": full_msg
        })
        comp["current_decisions"] = {}
        comp["draft_decisions"] = {}

    room["ready_teams"] = []
    room["turn_deadline"] = None
    room["current_year"] += 1
    if room["current_year"] > room["max_years"]:
        room["status"] = "ended"
        for name, comp in companies.items():
            remaining_debt = sum([l["amount"] for l in comp["loans"] if l["remaining_years"] > 0])
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
    if any(w in q for w in ["prix", "tarif", "vendre", "vente"]): 
        return "Le Prix de Vente est l'arme de destruction massive. S'il est sous 40% du prix moyen, vos clients penseront que c'est une arnaque (malus de suspicion et chute des ventes). S'il est très bas mais réaliste, vous raflerez tout le volume. S'il est haut, il faut compenser en ayant beaucoup de budget Pub et Qualité pour justifier votre placement 'Premium'."
    elif any(w in q for w in ["pub", "marketing", "publicite", "pub"]): 
        return "Le Budget Pub augmente drastiquement votre image de marque (notoriété). Son impact est immédiat sur les parts de marché. L'objectif idéal recommandé par les experts est de 7.5% à 15% de votre Chiffre d'Affaires."
    elif any(w in q for w in ["qualité", "qualite", "défaut"]): 
        return "Le Budget Qualité limite les défauts et augmente massivement la popularité auprès des clients (Cible: 0.5% à 2.5% du CA). MAIS attention : exiger de la qualité ralentit vos salariés ! Le temps de production d'un produit va augmenter, ce qui baissera votre capacité de production maximale (Capacité RH)."
    elif any(w in q for w in ["rse", "ecologie", "écologie", "social", "environnement"]): 
        return "Le Budget RSE (Environnement/Social) est un investissement long terme. Contrairement à la pub qui est immédiate, la RSE se cumule d'année en année. Cible idéale : 2% à 5% du CA. C'est parfait pour fidéliser la clientèle."
    elif any(w in q for w in ["rh", "employé", "employe", "salarié", "salarie", "salaire", "formation"]): 
        return "Vos salariés travaillent 1600 heures par an. Leur cadence de production est affectée par 3 choses : 1) Leur motivation (un salaire au-dessus de 30K€ les booste). 2) La Formation (elle accélère leur cadence). 3) L'exigence de Qualité (elle les ralentit, car ils doivent être minutieux)."
    elif any(w in q for w in ["delai", "délais", "client", "paiement client"]): 
        return "Délai Clients : Autoriser vos clients à payer tard (ex: 60 ou 90 jours) va booster énormément vos ventes car c'est un argument commercial fort. CONSÉQUENCE : Votre trésorerie immédiate va s'effondrer car l'argent rentrera avec beaucoup de retard. Vous risquez le découvert bancaire !"
    elif any(w in q for w in ["fournisseur", "fournisseurs", "paiement", "achat"]): 
        return "Délai Fournisseurs : Vous pouvez décider de payer vos fournisseurs tard (ex: 60 jours). AVANTAGE : Cela préserve votre Trésorerie, car l'argent sort plus tard de vos caisses. CONSÉQUENCE : Si vous le faites trop, vous pourriez perdre des remises secrètes. Modérez-le !"
    elif any(w in q for w in ["rd", "r&d", "recherche", "développement"]): 
        return "Le Budget R&D (Recherche) permet de baisser définitivement le Coût Unitaire de fabrication de votre produit. Son effet se cumule ! Très utile sur le long terme pour écraser la concurrence sur les marges."
    elif any(w in q for w in ["emprunt", "banque", "dette", "prêt", "pret", "interet"]): 
        return "L'Emprunt vous donne du Cash immédiat. Le banquier analyse votre Résultat Net de l'Année N-1 pour fixer le Taux (de 1% si vous êtes très rentable, jusqu'à 5% si vous êtes fragile). ATTENTION : À la fin de la partie, toute dette non remboursée est doublée et déduite de votre score final !"
    elif any(w in q for w in ["sabotage", "geler", "frappe"]): 
        return "Le Sabotage permet de forcer le maintien d'une valeur (ex: le prix, ou la pub) d'un adversaire sur ce qu'il a joué l'année dernière. L'adversaire fera sa simulation normalement, mais lors de la validation du tour, son chiffre sera écrasé par l'ancien ! Imparable, mais cher."
    elif any(w in q for w in ["espionnage", "donnée", "audit"]): 
        return "L'espionnage vous donne l'historique exact des autres. Le niveau ultime (100 K€) analyse automatiquement vos choix par rapport à la moyenne du marché en vous donnant un bilan Rouge/Vert très utile pour corriger le tir."
    elif any(w in q for w in ["machine", "prod"]): 
        return "Les machines s'achètent en Phase Production (Année 5). Elles coûtent 50K€ pièce et ont une capacité maximale définie par le secteur. Elles s'amortissent sur 5 ans (10K€ de charge par an)."
    elif any(w in q for w in ["stock", "stockage", "invendu"]): 
        return "Tout produit acheté/produit mais non vendu finira dans votre entrepôt. Chaque unité stockée génère un coût fixe de 4€ par an ! Attention aux surstocks massifs qui ruinent la rentabilité."
    elif any(w in q for w in ["aléa", "alea", "événement", "evenement", "karma"]): 
        return "Chaque année, l'ordinateur tire les dés : vous avez 15% de risque de subir une catastrophe (grève, panne = perte de 15K€ et ralentissements) et 10% de chance d'avoir un miracle (buzz = +15K€)."
    else: 
        return "Je suis l'assistant IA de votre Conseil d'Administration. Précisez votre question avec des mots simples (Ex: 'Comment marche le prix ?', 'Explique moi le délai client', 'A quoi sert la RSE ?', 'Combien coute le stock ?')."

def render_help_and_faq():
    st.sidebar.markdown("---")
    with st.sidebar.expander("📚 Guide, Règles & Assistant", expanded=False):
        t_regles, t_strat, t_ask = st.tabs(["📖 Règles & Paramètres", "♟️ Stratégies", "❓ FAQ / Chat IA"])
        
        with t_regles:
            st.markdown("""
            **🎯 BUT DU JEU**  
            Devenir l'entreprise avec la plus haute valeur (Trésorerie Actuelle + Valeur Estimée du Stock) à la fin des années définies.
            
            **⏳ LES PHASES DE JEU**
            * **Années 1 à 4 (Négoce) :** Pas d'usine. Vous achetez des produits finis, et vos salariés gèrent l'assemblage final/logistique. Votre capacité dépend 100% de vos RH.
            * **Années 5+ (Production) :** Vous devez acheter des **Machines (50 K€ l'unité)** pour fabriquer. Vos salariés opèrent désormais ces machines.

            **⚙️ EXPLICATION DÉTAILLÉE DES MÉCANIQUES**
            * **💰 Prix de Vente :** Le nerf de la guerre. Trop bas (sous 40% de la moyenne) = Arnaque perçue par le client = Malus extrême. Juste prix = fort volume. Prix haut = forte marge mais petit volume.
            * **⏳ Délais Clients (Jours) :** Accepter que le client paie dans 90 jours attire énormément de demande. *Danger :* Votre argent rentre en retard, causant des découverts bancaires fatals.
            * **🚚 Délais Fournisseurs (Jours) :** Payer votre fournisseur tard (ex: 90 jours) garde votre cash au chaud pour vos propres investissements.
            * **🎓 Formation (1-5% Salaires) :** Accélère le temps de travail. Vos employés abattent plus d'unités par heure.
            * **✨ Qualité (0.5-2.5% CA) :** Booste l'attractivité du produit. *Danger :* Les employés doivent être plus minutieux, ce qui ralentit leur temps de production à l'unité !
            * **📢 Publicité (7.5-15% CA) :** L'effet est instantané sur vos ventes et augmente la notoriété de votre marque.
            * **🔬 R&D (0-30% CA) :** Baisse définitivement le coût de fabrication de chaque produit. L'effet est persistant et cumulatif au fil des ans.
            * **🌍 RSE (2-5% CA) :** Investissement vertueux et environnemental. Améliore la popularité à long terme. Effet cumulatif et très stable.
            * **🏦 Emprunt :** Permet de financer l'espionnage, les machines ou de couvrir un déficit. Taux : 1 à 5% selon votre solidité. *Pénalité finale : Dette non remboursée = x2 sur le résultat final.*
            """)
            
        with t_strat:
            st.markdown("""
            **🛡️ Les 3 grandes méthodes pour écraser la concurrence :**
            
            **1️⃣ Le Low-Cost Agressif (Gros Volume)**
            * **Action :** Prix bas, RSE à 0, Qualité faible, beaucoup d'employés sous-payés.
            * **Avantage :** Vous absorbez des parts de marché colossales.
            * **Danger :** Marges minuscules. Si la trésorerie ou le stock coince un mois, c'est la faillite assurée.
            
            **2️⃣ Le Premium Niché (Forte Valeur)**
            * **Action :** Prix très élevé, Pub massive, Qualité et RSE au plafond, grosse R&D.
            * **Avantage :** Peu de volumes à gérer, marges gigantesques, clients fidélisés.
            * **Danger :** Les charges fixes (R&D, Pub) peuvent aspirer toute la trésorerie avant même les premières ventes.
            
            **3️⃣ Le Manipulateur de l'Ombre (Sabotage)**
            * **Action :** Dépenser 300K à 500K dans le sabotage chirurgical et l'espionnage.
            * **Avantage :** Vous copiez les prix, et vous gelez les budgets Pub ou les baisses de prix de vos concurrents au pire moment pour eux.
            """)
            
        with t_ask:
            st.markdown("**Posez vos questions à l'Assistant IA du CEO :**")
            faq_input = st.text_input("Ex: Quel est le bon budget pour la pub ?", key="faq_in")
            if st.button("Demander"):
                if faq_input:
                    ans = bot_answer(faq_input)
                    st.session_state.faq_chat.append({"q": faq_input, "a": ans})
            
            for chat in reversed(st.session_state.faq_chat[-5:]):
                st.markdown(f"👤 **Vous:** *{chat['q']}*")
                st.info(f"🤖 **Assistant:** {chat['a']}")

# ==========================================
# 6. INTERFACE LOBBY ET JEU MAIN
# ==========================================
# Vérification automatique des timers (Auto-validation)
if "room_code" in st.session_state and st.session_state.room_code:
    tmp_room = GAMES.get(st.session_state.room_code)
    if tmp_room and tmp_room.get("turn_deadline") and len(tmp_room["ready_teams"]) == len(tmp_room["companies"]) - 1:
        if time.time() > tmp_room["turn_deadline"]:
            missing_team = [t for t in tmp_room["companies"].keys() if t not in tmp_room["ready_teams"]][0]
            m_comp = tmp_room["companies"][missing_team]
            draft = m_comp.get("draft_decisions")
            if not draft:
                draft = get_default_decs(m_comp, tmp_room["product"])
            m_comp["current_decisions"] = draft
            tmp_room["ready_teams"].append(missing_team)
            tmp_room["turn_deadline"] = None
            save_game_to_disk(tmp_room)
            st.rerun()

if "room_code" not in st.session_state: st.session_state.room_code = None
if "player_team" not in st.session_state: st.session_state.player_team = None

if not st.session_state.room_code:
    st.title("🚀 Business Simulator - Édition Ultime")
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
    
    render_help_and_faq()

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
            score_name = room["companies"][p_team]["name_score"]
            pct_val = round(score_name * 100, 1)
            if score_name > 0:
                st.markdown(f"<h3 style='color:green;'>Analyse de votre nom d'entreprise : <span style='color:green;'>+{pct_val}% PDM</span></h3>", unsafe_allow_html=True)
            elif score_name < 0:
                st.markdown(f"<h3 style='color:red;'>Analyse de votre nom d'entreprise : <span style='color:red;'>{pct_val}% PDM</span></h3>", unsafe_allow_html=True)
            else:
                st.markdown(f"<h3>Analyse de votre nom d'entreprise : <span>0.0% PDM (Neutre)</span></h3>", unsafe_allow_html=True)

        st.markdown("---")
        for name in room["companies"].keys(): st.write(f"• **{name}**" + (" *(Hôte)*" if name == room["host"] else ""))
        if st.session_state.player_team == room["host"] and st.button("🚀 Lancer la Partie !", type="primary"):
            room["status"] = "playing"
            save_game_to_disk(room)
            st.rerun()
        if st.button("Actualiser l'écran"): st.rerun()
        
        render_help_and_faq()
        
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
        
        # Gestion du bouton Administrateur (Hôte) pour passer le tour
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
                                room["companies"][m]["current_decisions"] = room["companies"][m].get("draft_decisions", get_default_decs(room["companies"][m], product))
                                room["ready_teams"].append(m)
                        resolve_turn(room)
                        st.rerun()

        render_help_and_faq()
        
        st.title(f"🏢 {selected_team}")
        
        # Affichage du Timer si l'avant-dernier joueur a validé
        if room.get("turn_deadline") and len(room["ready_teams"]) == num_teams - 1 and room["status"] == "playing":
            time_left = int(room["turn_deadline"] - time.time())
            if time_left > 0:
                mins, secs = divmod(time_left, 60)
                st.error(f"⏳ **ATTENTION :** Plus que **{mins}m {secs}s** avant la validation forcée du dernier joueur !")
                # Hack JS pour forcer le rafraîchissement de la page de tout le monde quand le chrono tombe à zéro
                components.html(f"<script>setTimeout(function(){{ window.parent.location.reload(); }}, {time_left * 1000 + 1000});</script>", height=0)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Trésorerie", fmt_k(comp['cash']))
        m2.metric("Stock Actuel", f"{fmt_num(comp['stock'])} un.")
        m3.metric("Effectif", f"{comp['employees']} sal.")
        m4.metric("Machines", f"{comp['machines']}" if is_prod_phase else "N/A")
        m5.metric("Coût Unit. de Base", f"{get_unit_cost(product['base_cost'], comp['rd_cumul']):.1f} €")

        if comp["history"] and comp["history"][-1].get("event_msg"):
            st.warning(f"🔔 **ÉVÉNEMENT DE L'ANNÉE :** {comp['history'][-1]['event_msg']}")

        if has_played and room["status"] == "playing":
            st.success("✅ Vos décisions sont validées. En attente de la résolution du tour par l'Hôte...")
            st.progress(len(room['ready_teams']) / num_teams)
            if st.button("Actualiser"): st.rerun()
            
        elif room["status"] == "ended":
            st.balloons()
            st.header("🏆 Bilan des Performances & Classement Final")
            
            final_list = [{"Équipe": n, "Valeur Totale Est.": (c["cash"] + c["stock"] * product["base_cost"] * 0.5) / 1000.0} for n, c in room["companies"].items()]
            st.table(pd.DataFrame(final_list).sort_values(by="Valeur Totale Est.", ascending=False).style.format({"Valeur Totale Est.": "{:,.1f} K€"}))
            
            st.markdown("---")
            st.subheader("📈 Graphiques comparatifs sur toutes les années")
            
            df_cash, df_rev, df_share, df_sales, df_net = [], [], [], [], []
            for name, c in room["companies"].items():
                for h in c["history"]:
                    df_cash.append({"Équipe": name, "Année": h["year"], "Trésorerie (€)": h["cash"]})
                    df_rev.append({"Équipe": name, "Année": h["year"], "CA (€)": h["revenue"]})
                    df_share.append({"Équipe": name, "Année": h["year"], "Part de Marché (%)": h["real_market_share"] * 100})
                    df_sales.append({"Équipe": name, "Année": h["year"], "Ventes (unités)": h["sales"]})
                    df_net.append({"Équipe": name, "Année": h["year"], "Résultat Net (€)": h["net_income"]})
                    
            g1, g2 = st.columns(2)
            with g1:
                fig_c = px.line(pd.DataFrame(df_cash), x="Année", y="Trésorerie (€)", color="Équipe", title="Évolution de la Trésorerie")
                st.plotly_chart(fig_c, use_container_width=True)
            with g2:
                fig_r = px.line(pd.DataFrame(df_rev), x="Année", y="CA (€)", color="Équipe", title="Évolution du Chiffre d'Affaires")
                st.plotly_chart(fig_r, use_container_width=True)
                
            g3, g4 = st.columns(2)
            with g3:
                fig_s = px.line(pd.DataFrame(df_share), x="Année", y="Part de Marché (%)", color="Équipe", title="Évolution des Parts de Marché")
                st.plotly_chart(fig_s, use_container_width=True)
            with g4:
                fig_sa = px.bar(pd.DataFrame(df_sales), x="Année", y="Ventes (unités)", color="Équipe", barmode="group", title="Ventes Atteintes par Année")
                st.plotly_chart(fig_sa, use_container_width=True)
                
            fig_n = px.line(pd.DataFrame(df_net), x="Année", y="Résultat Net (€)", color="Équipe", title="Évolution du Résultat Net")
            st.plotly_chart(fig_n, use_container_width=True)

        else:
            tab_dec, tab_sim, tab_treso, tab_conseils, tab_bilan = st.tabs(["✍️ Décisions", "📊 Prévisionnel", "💸 Trésorerie", "💡 Conseils (N-1)", "🔍 Opérations & Espionnage"])
            
            sim_key = f"sim_{selected_team}_{room['current_year']}"
            frozen = comp.get("frozen_fields", [])
            
            if sim_key not in st.session_state:
                st.session_state[sim_key] = get_default_decs(comp, product)
            
            with tab_dec:
                with st.expander("📖 INDICATEURS DE BASE (Voir Menu Gauche pour les Règles Complètes)", expanded=True):
                    st.write(f"**Secteur :** {product['name']}")
                    st.write(f"**Taille Globale du Marché (100%) :** ~{fmt_num(product['base_market_size_per_team'] * (1.0+market_g) * num_teams)} {product['unit']}/an.")
                    st.write(f"**Prix repère moyen :** {product['benchmark_price']} €")
                    st.write(f"⏱️ **Temps de production par salarié :** `{product['base_time_per_unit']} heures / unité`")
                    st.write(f"🏭 **Capacité d'une machine :** `{product['machine_capacity']} unités / an`")

                with st.form(f"form_dec_{selected_team}"):
                    st.markdown("### 🛒 1. Commercial & Logistique")
                    c1, c2, c3 = st.columns(3)
                    with c1: price = st.number_input("Prix de Vente (€)", min_value=1.0, value=st.session_state[sim_key]["price"], disabled=("price" in frozen))
                    with c2: forecast_sales = st.number_input("Objectif Ventes Prévues", min_value=0, value=st.session_state[sim_key]["forecast_sales"], step=100)
                    with c3: purchase_qty = st.number_input("Quantité à Produire/Acheter", min_value=0, value=st.session_state[sim_key]["purchase_qty"], step=100)

                    st.markdown("### 🏭 2. Production & RH *(Protégé du sabotage)*")
                    p1, p2, p3 = st.columns(3)
                    with p1:
                        employees = st.number_input("Effectif (Salariés)", min_value=1, value=st.session_state[sim_key]["employees"])
                        salary = st.number_input("Salaire brut/an (€)", min_value=20000.0, value=st.session_state[sim_key]["salary"], step=1000.0)
                    with p2:
                        training = st.number_input("Budget Formation (€)", min_value=0.0, value=st.session_state[sim_key]["training"], step=500.0)
                        quality = st.number_input("Budget Qualité (€)", min_value=0.0, value=st.session_state[sim_key]["quality"], step=500.0, disabled=("quality" in frozen))
                    with p3:
                        buy_machines = st.number_input("Acheter Machines (50K€/u)", min_value=0, value=st.session_state[sim_key]["buy_machines"], disabled=not is_prod_phase)

                    st.markdown("### 🚀 3. Stratégie & Finance")
                    f1, f2, f3 = st.columns(3)
                    with f1:
                        marketing = st.number_input("Budget Pub (€)", min_value=0.0, value=st.session_state[sim_key]["marketing"], step=1000.0, disabled=("marketing" in frozen))
                        rd_budget = st.number_input("Budget R&D (€)", min_value=0.0, value=st.session_state[sim_key]["rd_budget"], step=1000.0, disabled=("rd_budget" in frozen))
                        rse_budget = st.number_input("Budget RSE (€)", min_value=0.0, value=st.session_state[sim_key]["rse_budget"], step=1000.0, disabled=("rse_budget" in frozen))
                    with f2:
                        client_terms = st.number_input("Délai Clients (jours)", min_value=0, max_value=120, value=st.session_state[sim_key]["client_terms"], disabled=("client_terms" in frozen))
                        supplier_terms = st.number_input("Délai Fournisseurs (jours)", min_value=0, max_value=120, value=st.session_state[sim_key]["supplier_terms"], disabled=("supplier_terms" in frozen))
                    with f3:
                        loan_amount = st.number_input("Emprunt Banque (€)", min_value=0.0, value=st.session_state[sim_key]["new_loan_amount"], step=5000.0)
                        loan_duration = st.slider("Durée emprunt", 1, 5, value=st.session_state[sim_key]["new_loan_duration"])

                    if frozen:
                        st.warning(f"🔒 L'action de sabotage ennemie a gelé ces champs sur leur ancienne valeur : {', '.join(frozen)}")

                    calc_btn = st.form_submit_button("🔄 Calculer mes prévisions (Brouillon sauvegardé)")

                if calc_btn:
                    st.session_state[sim_key].update({
                        "price": price, "forecast_sales": forecast_sales, "purchase_qty": purchase_qty,
                        "buy_machines": buy_machines, "marketing": marketing, "rd_budget": rd_budget,
                        "rse_budget": rse_budget, "employees": employees, "salary": salary,
                        "quality": quality, "training": training, "client_terms": client_terms,
                        "supplier_terms": supplier_terms, "new_loan_amount": loan_amount,
                        "new_loan_duration": loan_duration
                    })
                    # Sauvegarde du brouillon côté serveur pour le chronomètre auto
                    comp["draft_decisions"] = st.session_state[sim_key].copy()
                    save_game_to_disk(room)
                    
                    cf_key = f"cf_{selected_team}_{room['current_year']}"
                    if cf_key in st.session_state:
                        st.session_state[f"cf_prev_{selected_team}_{room['current_year']}"] = st.session_state[cf_key]

                st.markdown("---")
                if st.button("🔒 VALIDER DÉFINITIVEMENT MES CHOIX", type="primary"):
                    comp["current_decisions"] = st.session_state[sim_key].copy()
                    room["ready_teams"].append(selected_team)
                    
                    # Logique du compte à rebours
                    if len(room["ready_teams"]) == num_teams - 1:
                        room["turn_deadline"] = time.time() + 300 # 5 minutes en secondes
                    elif len(room["ready_teams"]) == num_teams:
                        room["turn_deadline"] = None
                        
                    save_game_to_disk(room)
                    st.rerun()

            forecast = calculate_forecast(comp, st.session_state[sim_key], product, is_prod_phase, num_teams, market_g)
            st.session_state[f"cf_{selected_team}_{room['current_year']}"] = forecast["cf_curve"]
            
            with tab_sim:
                st.subheader("📊 Compte de Résultat & Prévisions Détaillées")
                st.metric("Coût de Production Unitaire (après R&D)", f"{forecast['unit_cost']:.2f} €")
                st.metric("Taux d'intérêt de l'emprunt calculé", f"{forecast['interest_rate']*100:.0f}%")
                
                df_pl = pd.DataFrame([
                    {"Poste": "Chiffre d'Affaires", "Prévu N": forecast["revenue"]},
                    {"Poste": "Coût Achats/Prod", "Prévu N": forecast["cogs"]},
                    {"Poste": "Marge Brute", "Prévu N": forecast["revenue"] - forecast["cogs"]},
                    {"Poste": "Masse Salariale", "Prévu N": forecast["hr_cost"]},
                    {"Poste": "Charges Fixes (Pub, R&D, Intel...)", "Prévu N": forecast["expenses"] - forecast["hr_cost"] - forecast["depreciation"]},
                    {"Poste": "RÉSULTAT NET", "Prévu N": forecast["net_income"]}
                ])
                st.table(df_pl.style.format({"Prévu N": "{:,.0f} €"}))

                st.markdown("---")
                st.subheader("🎯 Indicateurs & Jauges Clés")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Ventes Prévues", fmt_num(forecast["sales"]))
                r2.metric("Demande Théorique", fmt_num(forecast["theo_demand"]))
                r3.metric("PdM Estimée", f"{forecast['est_share']:.1f}%")
                r4.metric("Trésorerie Finale", fmt_k(forecast["end_cash"]))

                j1, j2, j3 = st.columns(3)
                j1.metric("Jauge RSE", f"{forecast['rse_score']:.1f} / 100")
                j2.metric("Jauge Qualité", f"{forecast['qual_score']:.1f} / 100")
                j3.metric("Popularité Globale", f"{forecast['popularity']:.1f} / 100")

            with tab_treso:
                st.subheader("💸 Évolution de la Trésorerie sur 12 Mois")
                max_overdraft = st.slider("Ajuster la limite de découvert autorisé (€)", min_value=0, max_value=int((comp["history"][-1]["revenue"] if comp["history"] else comp["cash"]) * 0.25), value=10000, step=1000)
                
                months = list(range(0, 13))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=months, y=forecast["cf_utopia"], mode='lines', name='Utopique (Parfait)', line=dict(color='green', dash='dot')))
                
                prev_cf_key = f"cf_prev_{selected_team}_{room['current_year']}"
                if prev_cf_key in st.session_state:
                    fig.add_trace(go.Scatter(x=months, y=st.session_state[prev_cf_key], mode='lines', name='Dernier Calcul', line=dict(color='lightgrey')))
                
                fig.add_trace(go.Scatter(x=months, y=forecast["cf_curve"], mode='lines+markers', name='Prévision Actuelle', line=dict(color='blue', width=3)))
                fig.add_trace(go.Scatter(x=months, y=[-max_overdraft]*13, mode='lines', name='Limite Découvert', line=dict(color='red', dash='dash')))
                
                fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

            with tab_conseils:
                st.subheader("💡 Rapport du Conseil d'Administration")
                if not comp["history"]: st.info("Première année : pas d'historique.")
                else:
                    last = comp["history"][-1]
                    rev = last["revenue"]
                    if last["price"] < product["benchmark_price"] * 0.4: st.error("🚨 L'an dernier votre prix était si bas que les clients ont fui par méfiance.")
                    elif last["price"] < last["unit_cost"]: st.error("🚨 Vous avez vendu à perte !")
                    if last["sales"] < last["theo_demand"]: st.warning("⚠️ Vous avez raté des ventes par manque de stock ou de RH.")
                    if last["stock"] > last["sales"] * 0.5: st.warning("📦 Vous avez beaucoup trop de stock dormant.")

            with tab_bilan:
                st.subheader("🕵️ Centre d'Opérations Secrètes & Sabotage")
                
                c_esp, c_sab = st.columns(2)
                with c_esp:
                    st.markdown("#### 1. Espionnage Industriel")
                    esp = st.selectbox("Acheter les données (An N-1)", options=[0,1,2,3,4], index=st.session_state[sim_key]["espionnage"], format_func=lambda x: {0:"0€ - Aucun", 1:"5K€ - Performances", 2:"20K€ - Budgets", 3:"50K€ - Compte Résultat", 4:"100K€ - Audit Comparatif"}[x])
                    
                    esp_costs_map = {0: 0, 1: 5000, 2: 20000, 3: 50000, 4: 100000}
                    cost_esp = esp_costs_map.get(esp, 0)
                    if cost_esp > comp["cash"]:
                        st.markdown("<p style='color:red;'>Fonds insuffisants</p>", unsafe_allow_html=True)
                        
                    if esp != st.session_state[sim_key]["espionnage"]:
                        st.session_state[sim_key]["espionnage"] = esp
                        st.rerun()

                with c_sab:
                    st.markdown("#### 2. Sabotage & Lobbying")
                    s_type = st.selectbox("Acheter une frappe de Sabotage", options=[0,1,2,3], index=st.session_state[sim_key]["sabotage_type"], format_func=lambda x: {0:"0€ - Aucun", 1:"200K€ - Aléatoire", 2:"300K€ - Semi-Ciblée", 3:"500K€ - Chirurgicale"}[x], disabled=(room["current_year"] == 1))
                    
                    sab_costs_map = {0: 0, 1: 200000, 2: 300000, 3: 500000}
                    cost_sab = sab_costs_map.get(s_type, 0)
                    if cost_sab > comp["cash"]:
                        st.markdown("<p style='color:red;'>Fonds insuffisants</p>", unsafe_allow_html=True)
                        
                    other_teams = [t for t in room["companies"].keys() if t != selected_team]
                    
                    if s_type != st.session_state[sim_key]["sabotage_type"]:
                        st.session_state[sim_key]["sabotage_type"] = s_type
                        st.rerun()

                    if s_type in [2, 3] and other_teams:
                        idx_t = other_teams.index(st.session_state[sim_key]["sabotage_target"]) if st.session_state[sim_key]["sabotage_target"] in other_teams else 0
                        s_target = st.selectbox("🎯 Entreprise à cibler", options=other_teams, index=idx_t)
                        if s_target != st.session_state[sim_key]["sabotage_target"]:
                            st.session_state[sim_key]["sabotage_target"] = s_target
                            st.rerun()
                            
                    if s_type == 3:
                        s_actions = ["price", "marketing", "quality", "rd_budget", "rse_budget", "client_terms", "supplier_terms"]
                        s_action_names = ["Prix de Vente", "Budget Pub", "Budget Qualité", "Budget R&D", "Budget RSE", "Délai Clients", "Délai Fournisseurs"]
                        idx_a = s_actions.index(st.session_state[sim_key]["sabotage_action"]) if st.session_state[sim_key]["sabotage_action"] in s_actions else 0
                        s_act_name = st.selectbox("🎯 Action à figer", options=s_action_names, index=idx_a)
                        s_act = s_actions[s_action_names.index(s_act_name)]
                        if s_act != st.session_state[sim_key]["sabotage_action"]:
                            st.session_state[sim_key]["sabotage_action"] = s_act
                            st.rerun()

                st.markdown("---")
                st.markdown("#### 📂 Données Interceptées (N-1)")
                if room["current_year"] == 1:
                    st.info("Aucun historique disponible.")
                else:
                    level = comp["history"][-1].get("espionnage_level", 0) if comp["history"] else 0
                    if level == 0: st.warning("Achetez un niveau d'espionnage pour voir les données concurrentes au prochain tour.")
                    
                    if level >= 1:
                        data_l1 = [{"Équipe": n, "PdM": f"{c['history'][-1]['real_market_share']*100:.1f}%", "Ventes (u)": f"{c['history'][-1]['sales']:.0f}", "Résultat Net (€)": f"{c['history'][-1]['net_income']:,.0f}"} for n, c in room["companies"].items() if c["history"]]
                        st.table(pd.DataFrame(data_l1))
                    if level >= 2:
                        data_l2 = [{"Équipe": n, "Prix (€)": c['history'][-1]['price'], "Pub (€)": c['history'][-1]['mkt'], "Qualité (€)": c['history'][-1]['qual']} for n, c in room["companies"].items() if c["history"]]
                        st.table(pd.DataFrame(data_l2))
                    if level >= 3:
                        data_l3 = [{"Équipe": n, "CA (€)": c['history'][-1]['revenue'], "Coûts Achat (€)": c['history'][-1]['cogs'], "Frais RH (€)": c['history'][-1]['hr_cost']} for n, c in room["companies"].items() if c["history"]]
                        st.table(pd.DataFrame(data_l3))
                    if level >= 4:
                        st.markdown("🔴 **Audit Comparatif (Niveau 100k)**")
                        
                        all_prices = [c['history'][-1]['price'] for c in room["companies"].values() if c["history"]]
                        avg_price = sum(all_prices) / len(all_prices) if all_prices else 1
                        my_price = comp["history"][-1]["price"]
                        
                        if my_price > avg_price * 1.1: st.markdown("🔴 **Prix :** Trop cher par rapport au marché.")
                        elif my_price < avg_price * 0.9: st.markdown("🟢 **Prix :** Très compétitif sur les prix.")
                        else: st.markdown("⚪ **Prix :** Parfaitement aligné.")
