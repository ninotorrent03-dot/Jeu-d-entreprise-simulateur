import json
import os
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Business Simulator - Édition Réaliste", layout="wide")

@st.cache_resource
def get_global_games():
    return {}

GAMES = get_global_games()

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
        "name": "Vélos Électriques Urbains",
        "unit": "vélos",
        "benchmark_price": 1200.0,
        "base_cost": 650.0,
        "base_market_size_per_team": 6000,
        "base_time_per_unit": 0.5,
        "context": "Mobilité douce en forte croissance. Les clients comparent beaucoup les prix et la qualité."
    },
    {
        "name": "Smartphones Éco-reconditionnés",
        "unit": "smartphones",
        "benchmark_price": 480.0,
        "base_cost": 240.0,
        "base_market_size_per_team": 12000,
        "base_time_per_unit": 0.25,
        "context": "Forte sensibilité au prix et aux garanties de reconditionnement."
    },
    {
        "name": "Enceintes Hi-Fi Premium",
        "unit": "enceintes",
        "benchmark_price": 340.0,
        "base_cost": 160.0,
        "base_market_size_per_team": 8000,
        "base_time_per_unit": 0.35,
        "context": "Marché de niche. La qualité acoustique et la R&D priment sur le prix."
    }
]

# ==========================================
# 3. MOTEUR MATHÉMATIQUE & INTELLIGENCE CLIENT
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
        "pending_client_cash": 0.0, "pending_supplier_cash": 0.0, "history": [], "current_decisions": {}
    }

def get_unit_cost(base_cost, rd_total):
    discount = min(0.25, rd_total / 150000.0)
    return base_cost * (1.0 - discount)

def get_hr_metrics(employees, salary, quality_budget, training_budget, base_time, karma_penalty=1.0):
    total_hours = employees * 1600
    time_penalty = min(1.20, 1.0 + (quality_budget / 50000.0) * 0.20)
    time_bonus = max(0.85, 1.0 - (training_budget / 20000.0) * 0.15)
    motivation = min(1.10, max(0.80, 1.0 + ((salary - 30000) / 30000.0) * 0.20))
    effective_hours = total_hours * motivation * karma_penalty
    time_per_unit = base_time * time_penalty * time_bonus
    hr_cap = effective_hours / time_per_unit if time_per_unit > 0 else 0
    return {
        "time_per_unit": time_per_unit, "effective_hours": effective_hours,
        "hr_cap": hr_cap, "productivity_pct": (1.0 / time_per_unit) / (1.0 / base_time) * 100
    }

def get_theo_demand(base_demand, price, bench_price, marketing, quality, rse, client_terms, brand_aw, karma_bonus=1.0):
    price_ratio = bench_price / price if price > 0 else 1.0
    price_factor = min(2.5, max(0.3, price_ratio ** 1.8))
    
    # --- INTELLIGENCE CLIENT INVISIBLE ---
    # Si le prix est inférieur à 40% du prix normal, les clients trouvent ça trop louche et n'achètent pas
    suspicion_penalty = 1.0
    if price < bench_price * 0.4:
        suspicion_penalty = (price / (bench_price * 0.4)) ** 2.5 
    
    mkt_factor = min(1.5, 1.0 + (marketing / 40000.0))
    qual_factor = min(1.3, 1.0 + (quality / 30000.0))
    rse_factor = min(1.15, 1.0 + (rse / 20000.0))
    terms_factor = min(1.2, 1.0 + (client_terms / 90.0) * 0.2)
    brand_factor = min(1.5, 1.0 + (brand_aw / 100.0) * 0.5)
    
    demand = base_demand * price_factor * mkt_factor * qual_factor * rse_factor * terms_factor * brand_factor * karma_bonus * suspicion_penalty
    return min(demand, base_demand * 4.0)

def calculate_forecast(comp, decs, product, is_prod_phase, num_teams):
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
    espionnage_level = decs.get("espionnage", 0)

    espionnage_costs = {0: 0, 1: 5000, 2: 20000, 3: 50000, 4: 100000}
    intel_cost = espionnage_costs.get(espionnage_level, 0)

    total_market_size_est = product["base_market_size_per_team"] * num_teams
    base_demand = product["base_market_size_per_team"]
    
    theo_demand = get_theo_demand(base_demand, price, product["benchmark_price"], marketing, quality, rse_budget, client_terms, comp["brand_awareness"])
    
    hr_metrics = get_hr_metrics(employees, salary, quality, training, product["base_time_per_unit"])
    hr_cap = hr_metrics["hr_cap"]
    
    total_machines = comp["machines"] + decs.get("buy_machines", 0)
    prod_cap = total_machines * 2500 if is_prod_phase else hr_cap
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
    
    interest = sum([l["amount"] * 0.05 for l in comp.get("loans", [])])
    if decs.get("new_loan_amount", 0) > 0: interest += decs["new_loan_amount"] * 0.05
        
    net_before_tax = (revenue - purchases_value) - expenses - interest
    tax = net_before_tax * 0.25 if net_before_tax > 0 else 0.0
    net_income = net_before_tax - tax
    
    repayments = sum([l["annuity"] for l in comp.get("loans", []) if l["remaining_years"] > 0])
    
    cash_in = (revenue - cash_delayed_clients) + comp.get("pending_client_cash", 0.0) + decs.get("new_loan_amount", 0)
    cash_out = (purchases_value - cash_delayed_suppliers) + comp.get("pending_supplier_cash", 0.0) + (expenses - depreciation) + machine_buy_cash + interest + tax + repayments
    
    end_cash = comp["cash"] + cash_in - cash_out
    est_share = (theo_demand / (total_market_size_est + theo_demand - base_demand)) * 100
    
    return {
        "sales": sales, "theo_demand": theo_demand, "revenue": revenue, "net_income": net_income,
        "end_cash": end_cash, "stock_final": stock_final, "unit_cost": unit_cost,
        "est_share": est_share, "hr_cap": hr_cap, "target_share": 100.0 / num_teams if num_teams > 0 else 100.0,
        "delayed_cash_impact": cash_delayed_clients, "hr_metrics": hr_metrics,
        "cogs": purchases_value, "hr_cost": hr_cost, "mkt": marketing, "qual": quality, 
        "train": training, "rd": rd_budget, "rse": rse_budget, "intel_cost": intel_cost,
        "total_market": total_market_size_est, "prod_cap": prod_cap, "depreciation": depreciation, "expenses": expenses
    }

def resolve_turn(room):
    product = room["product"]
    companies = room["companies"]
    num_teams = len(companies)
    is_prod_phase = (room["current_year"] >= 5)
    
    total_market_demand = product["base_market_size_per_team"] * num_teams * random.uniform(0.95, 1.05)
    
    scores = {}
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        price = dec.get("price", product["benchmark_price"])
        rse_tot = dec.get("rse_budget", 0.0) + comp.get("rse_cumul", 0.0)
        
        scores[name] = get_theo_demand(product["base_market_size_per_team"], price, product["benchmark_price"], 
                                       dec.get("marketing", 0.0), dec.get("quality", 0.0), rse_tot, 
                                       float(dec.get("client_terms", 0)), comp["brand_awareness"])

    total_score = sum(scores.values()) if sum(scores.values()) > 0 else 1.0
    espionnage_costs = {0: 0, 1: 5000, 2: 20000, 3: 50000, 4: 100000}
    
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        
        rd_bud = dec.get("rd_budget", 0.0)
        comp["rd_cumul"] += rd_bud
        comp["rse_cumul"] += dec.get("rse_budget", 0.0)
        unit_cost = get_unit_cost(product["base_cost"], comp["rd_cumul"])
        intel_cost = espionnage_costs.get(dec.get("espionnage", 0), 0)
        
        if is_prod_phase:
            new_mach = dec.get("buy_machines", 0)
            comp["machines"] += new_mach
            comp["cash"] -= new_mach * 50000.0
            
        theo_share = scores[name] / total_score
        team_demand = total_market_demand * theo_share
        
        purchase_qty = dec.get("purchase_qty", 0)
        available_stock = comp["stock"] + purchase_qty
        
        hr_metrics = get_hr_metrics(dec.get("employees", 1), dec.get("salary", 30000.0), dec.get("quality", 0.0), dec.get("training", 0.0), product["base_time_per_unit"])
        hr_cap = hr_metrics["hr_cap"]
        
        if is_prod_phase:
            prod_cap = comp["machines"] * 2500
            actual_sales = min(team_demand, available_stock, hr_cap, prod_cap)
        else:
            prod_cap = 9999999
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
        
        hr_cost = dec.get("employees", 1) * dec.get("salary", 30000.0) * 1.45
        depreciation = comp["machines"] * 10000.0 if is_prod_phase else 0.0
        comp["stock"] = available_stock - actual_sales
        storage_cost = comp["stock"] * 4.0
        
        expenses = hr_cost + dec.get("marketing", 0.0) + dec.get("quality", 0.0) + dec.get("training", 0.0) + rd_bud + dec.get("rse_budget", 0.0) + storage_cost + depreciation + intel_cost
        
        if dec.get("new_loan_amount", 0) > 0:
            dur = max(1, dec.get("new_loan_duration", 3))
            comp["loans"].append({"amount": dec["new_loan_amount"], "annuity": dec["new_loan_amount"] / dur, "remaining_years": dur})
            comp["cash"] += dec["new_loan_amount"]
            
        interest = sum([l["amount"] * 0.05 for l in comp["loans"] if l["remaining_years"] > 0])
        repayments = sum([l["annuity"] for l in comp["loans"] if l["remaining_years"] > 0])
        for l in comp["loans"]:
            if l["remaining_years"] > 0:
                l["amount"] -= l["annuity"]
                l["remaining_years"] -= 1
        
        net_before_tax = (revenue - purchases_value) - expenses - interest
        tax = net_before_tax * 0.25 if net_before_tax > 0 else 0.0
        net_income = net_before_tax - tax
        
        comp["cash"] += cash_in_sales - cash_out_purchases - (expenses - depreciation) - interest - tax - repayments
        
        if comp["cash"] < 0:
            overdraft_fee = abs(comp["cash"]) * 0.12
            comp["cash"] -= overdraft_fee
            net_income -= overdraft_fee

        comp["employees"] = dec.get("employees", 1)
        comp["brand_awareness"] = max(1.0, min(100.0, comp["brand_awareness"] + (dec.get("marketing", 0.0) / 10000.0)))
        
        comp["history"].append({
            "year": room["current_year"], "sales": actual_sales, "theo_demand": team_demand, 
            "hr_cap": hr_cap, "prod_cap": prod_cap, "available_stock": available_stock,
            "real_market_share": real_market_share, "revenue": revenue, "cogs": purchases_value, 
            "hr_cost": hr_cost, "mkt": dec.get("marketing", 0), "qual": dec.get("quality", 0), 
            "train": dec.get("training", 0), "rd": rd_bud, "rse": dec.get("rse_budget", 0),
            "intel_cost": intel_cost, "depreciation": depreciation, "storage": storage_cost,
            "net_income": net_income, "cash": comp["cash"], "stock": comp["stock"],
            "price": dec.get("price", product["benchmark_price"]), "unit_cost": unit_cost, 
            "salary": dec.get("salary", 30000), "employees": dec.get("employees", 1),
            "espionnage_level": dec.get("espionnage", 0)
        })
        comp["current_decisions"] = {}

    room["ready_teams"] = []
    room["current_year"] += 1
    if room["current_year"] > room["max_years"]: room["status"] = "ended"
    save_game_to_disk(room)

# ==========================================
# 4. INTERFACE
# ==========================================
if "room_code" not in st.session_state: st.session_state.room_code = None
if "player_team" not in st.session_state: st.session_state.player_team = None

if not st.session_state.room_code:
    st.title("🚀 Business Simulator - Édition Réaliste")
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
                    room = {"room_code": room_code, "host": host_name.strip(), "product": product, "max_years": num_years, "current_year": 1, "status": "waiting", "start_capital": capital_k * 1000.0, "companies": {}, "ready_teams": []}
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
        for name in room["companies"].keys(): st.write(f"• **{name}**")
        if st.session_state.player_team == room["host"] and st.button("🚀 Lancer la Partie !", type="primary"):
            room["status"] = "playing"
            save_game_to_disk(room)
            st.rerun()
        if st.button("Actualiser l'écran"): st.rerun()
    else:
        st.sidebar.markdown(f"**🔑 Salon:** `{room['room_code']}` | **📅 Année:** {room['current_year']}/{room['max_years']}")
        if st.sidebar.button("Déconnexion"):
            st.session_state.room_code = None
            st.rerun()

        if st.session_state.player_team not in room["companies"]: st.session_state.player_team = list(room["companies"].keys())[0]
        selected_team = st.sidebar.selectbox("Changer de vue :", list(room["companies"].keys()), index=list(room["companies"].keys()).index(st.session_state.player_team))
        comp = room["companies"][selected_team]
        has_played = selected_team in room["ready_teams"]
        
        st.title(f"🏢 {selected_team}")
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Trésorerie", fmt_k(comp['cash']))
        m2.metric("Stock Actuel", f"{fmt_num(comp['stock'])} un.")
        m3.metric("Effectif", f"{comp['employees']} sal.")
        m4.metric("Machines", f"{comp['machines']}" if is_prod_phase else "N/A")
        m5.metric("Coût Unit. Actuel", f"{get_unit_cost(product['base_cost'], comp['rd_cumul']):.1f} €")

        if has_played and room["status"] == "playing":
            st.success("✅ Vos décisions sont validées. En attente des concurrents...")
            st.progress(len(room['ready_teams']) / num_teams)
            if st.button("Actualiser"): st.rerun()
            
        elif room["status"] == "ended":
            st.balloons()
            st.header("🏆 Classement Final")
            final_list = [{"Équipe": n, "Valeur Totale Est.": (c["cash"] + c["stock"] * product["base_cost"] * 0.5) / 1000.0} for n, c in room["companies"].items()]
            st.table(pd.DataFrame(final_list).sort_values(by="Valeur Totale Est.", ascending=False).style.format({"Valeur Totale Est.": "{:,.1f} K€"}))

        else:
            tab_dec, tab_sim, tab_conseils, tab_bilan = st.tabs(["✍️ Décisions", "📊 Prévisionnel", "💡 Conseils du CA (N-1)", "🔍 Espionnage Concurrentiel"])
            
            sim_key = f"sim_{selected_team}_{room['current_year']}"
            if sim_key not in st.session_state:
                last_decs = comp.get("history", [{}])[-1] if comp.get("history") else {}
                st.session_state[sim_key] = {
                    "price": float(last_decs.get("price", product["benchmark_price"])),
                    "forecast_sales": int(last_decs.get("sales", 3000)), "purchase_qty": int(last_decs.get("sales", 3000)),
                    "buy_machines": 0, "marketing": 10000.0, "rd_budget": 3000.0, "rse_budget": 2000.0,
                    "employees": int(comp.get("employees", 2)), "salary": 30000.0, "quality": 2500.0,
                    "training": 1500.0, "client_terms": 30, "supplier_terms": 30, "new_loan_amount": 0.0,
                    "new_loan_duration": 3, "espionnage": 0
                }
            
            with tab_dec:
                with st.expander("📖 GUIDE DU MARCHÉ & INDICATEURS DE BASE", expanded=True):
                    st.write(f"**Secteur :** {product['name']}")
                    st.write(f"**Taille Globale du Marché (100%) :** ~{fmt_num(product['base_market_size_per_team'] * num_teams)} {product['unit']}/an.")
                    st.write(f"**Part de marché équitable :** {100.0/num_teams:.1f}% (soit ~{fmt_num(product['base_market_size_per_team'])} ventes espérées si tout est moyen).")
                    st.write(f"**Prix repère moyen :** {product['benchmark_price']} €")

                with st.form(f"form_dec_{selected_team}"):
                    st.markdown("### 🛒 1. Commercial & Logistique")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        price = st.number_input("Prix de Vente (€)", min_value=1.0, value=st.session_state[sim_key]["price"])
                    with c2:
                        forecast_sales = st.number_input("Objectif Ventes Prévues", min_value=0, value=st.session_state[sim_key]["forecast_sales"], step=100)
                    with c3:
                        purchase_qty = st.number_input("Quantité à Produire/Acheter", min_value=0, value=st.session_state[sim_key]["purchase_qty"], step=100)

                    st.markdown("### 🏭 2. Production & RH")
                    st.caption("ℹ️ *1 Salarié = 1600h/an. La qualité rallonge le temps unitaire, la formation l'accélère.*")
                    p1, p2, p3 = st.columns(3)
                    with p1:
                        employees = st.number_input("Effectif (Salariés)", min_value=1, value=st.session_state[sim_key]["employees"])
                        salary = st.number_input("Salaire brut/an (€)", min_value=20000.0, value=st.session_state[sim_key]["salary"], step=1000.0)
                    with p2:
                        training = st.number_input("Budget Formation (€)", min_value=0.0, value=st.session_state[sim_key]["training"], step=500.0)
                        quality = st.number_input("Budget Qualité (€)", min_value=0.0, value=st.session_state[sim_key]["quality"], step=500.0)
                    with p3:
                        buy_machines = st.number_input("Acheter Machines (50K€/u)", min_value=0, value=st.session_state[sim_key]["buy_machines"], disabled=not is_prod_phase)
                        if is_prod_phase: st.caption("ℹ️ *1 Machine = 2500 unités/an.*")

                    st.markdown("### 🚀 3. Stratégie & Finance")
                    f1, f2, f3 = st.columns(3)
                    with f1:
                        marketing = st.number_input("Budget Pub (€)", min_value=0.0, value=st.session_state[sim_key]["marketing"], step=1000.0)
                        rd_budget = st.number_input("Budget R&D (€)", min_value=0.0, value=st.session_state[sim_key]["rd_budget"], step=1000.0)
                        rse_budget = st.number_input("Budget RSE (€)", min_value=0.0, value=st.session_state[sim_key]["rse_budget"], step=1000.0)
                    with f2:
                        client_terms = st.number_input("Délai Clients (jours)", min_value=0, max_value=120, value=st.session_state[sim_key]["client_terms"])
                        supplier_terms = st.number_input("Délai Fournisseurs (jours)", min_value=0, max_value=120, value=st.session_state[sim_key]["supplier_terms"])
                    with f3:
                        loan_amount = st.number_input("Emprunt Banque (€)", min_value=0.0, value=st.session_state[sim_key]["new_loan_amount"], step=5000.0)
                        loan_duration = st.slider("Durée emprunt", 1, 5, value=st.session_state[sim_key]["new_loan_duration"])
                        espionnage = st.selectbox("Niveau d'Espionnage", options=[0,1,2,3,4], index=st.session_state[sim_key]["espionnage"], format_func=lambda x: {0:"0€ - Aucun", 1:"5K€ - Performances", 2:"20K€ - Budgets", 3:"50K€ - Compte Résultat", 4:"100K€ - Audit Comparatif"}[x])

                    calc_btn = st.form_submit_button("🔄 Calculer mes prévisions")

                if calc_btn:
                    st.session_state[sim_key] = {
                        "price": price, "forecast_sales": forecast_sales, "purchase_qty": purchase_qty,
                        "buy_machines": buy_machines, "marketing": marketing, "rd_budget": rd_budget,
                        "rse_budget": rse_budget, "employees": employees, "salary": salary,
                        "quality": quality, "training": training, "client_terms": client_terms,
                        "supplier_terms": supplier_terms, "new_loan_amount": loan_amount,
                        "new_loan_duration": loan_duration, "espionnage": espionnage
                    }

                st.markdown("---")
                if st.button("🔒 VALIDER DÉFINITIVEMENT MES CHOIX", type="primary"):
                    room["companies"][selected_team]["current_decisions"] = st.session_state[sim_key]
                    room["ready_teams"].append(selected_team)
                    save_game_to_disk(room)
                    st.rerun()

            forecast = calculate_forecast(comp, st.session_state[sim_key], product, is_prod_phase, num_teams)
            
            with tab_sim:
                st.subheader("📊 Compte de Résultat (Prévisionnel)")
                df_pl = pd.DataFrame([
                    {"Poste": "Chiffre d'Affaires", "Prévu N": forecast["revenue"]},
                    {"Poste": "Coût Logistique/Prod", "Prévu N": forecast["cogs"]},
                    {"Poste": "Marge Brute", "Prévu N": forecast["revenue"] - forecast["cogs"]},
                    {"Poste": "Masse Salariale", "Prévu N": forecast["hr_cost"]},
                    {"Poste": "Total Charges Fixes", "Prévu N": forecast["expenses"] - forecast["hr_cost"] - forecast["depreciation"]},
                    {"Poste": "RÉSULTAT NET", "Prévu N": forecast["net_income"]}
                ])
                st.table(df_pl.style.format({"Prévu N": "{:,.0f} €"}))

                st.markdown("---")
                st.subheader("🎯 Indicateurs & Ratios")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Ventes Prévues", fmt_num(forecast["sales"]))
                r2.metric("Demande Théorique", fmt_num(forecast["theo_demand"]))
                r3.metric("PdM Estimée", f"{forecast['est_share']:.1f}%", delta=f"Objectif 100%: {forecast['target_share']:.1f}%")
                r4.metric("Trésorerie Finale", fmt_k(forecast["end_cash"]))

                st.markdown("---")
                st.subheader("⚙️ Capacité de Production")
                hrm = forecast["hr_metrics"]
                st.write(f"• **Temps unitaire actuel :** {hrm['time_per_unit']:.2f} h / unité *(Base: {product['base_time_per_unit']}h)*")
                st.write(f"• **Productivité RH :** `{hrm['productivity_pct']:.0f}%`")
                st.write(f"• **Capacité RH :** {fmt_num(hrm['hr_cap'])} unités.")
                if is_prod_phase: st.write(f"• **Capacité Machines :** {fmt_num(forecast['prod_cap'])} unités.")

            with tab_conseils:
                st.subheader("💡 Rapport du Conseil d'Administration (Audit N-1)")
                if not comp["history"]:
                    st.info("C'est votre première année. Le Conseil n'a pas encore de recul sur votre gestion. Bonne chance !")
                else:
                    last = comp["history"][-1]
                    rev = last["revenue"]
                    
                    # Intelligence Client & Prix
                    if last["price"] < product["benchmark_price"] * 0.4:
                        st.error("🚨 **INTELLIGENCE CLIENT :** Votre prix de l'an dernier était tellement anormalement bas que les consommateurs ont cru à une arnaque ou à une malfaçon. La demande s'est effondrée !")
                    elif last["price"] < last["unit_cost"]:
                        st.error("🚨 **RENTABILITÉ :** Vous avez vendu vos produits à perte l'année dernière. Augmentez votre prix ou baissez vos coûts !")
                    elif last["price"] > product["benchmark_price"] * 1.5:
                        st.warning("⚠️ **POSITIONNEMENT :** Votre produit est perçu comme très cher. Vous devez avoir des budgets marketing et qualité exceptionnels pour justifier ce prix.")

                    # Ruptures & Capacité
                    if last["sales"] < last["theo_demand"]:
                        if last["available_stock"] <= last["sales"]:
                            st.warning(f"⚠️ **RUPTURE DE STOCK :** Vous avez raté environ {int(last['theo_demand'] - last['sales'])} ventes car vous n'aviez pas produit ou acheté assez de marchandises.")
                        elif last["hr_cap"] <= last["sales"]:
                            st.warning(f"⚠️ **GOULOT D'ÉTRANGLEMENT RH :** La demande était là, mais vos employés n'ont pas pu suivre la cadence (Capacité max RH atteinte). Embauchez ou formez-les !")
                        elif is_prod_phase and last.get("prod_cap", 999999) <= last["sales"]:
                            st.warning("⚠️ **CAPACITÉ MACHINES :** Vous êtes bloqué par le nombre de vos machines.")

                    # Surstockage
                    if last["stock"] > last["sales"] * 0.5:
                        st.warning(f"📦 **SURSTOCKAGE :** Il vous reste {int(last['stock'])} unités sur les bras. Cela vous coûte 4€ par unité stockée. Vendez-les vite !")

                    # Ratios de gestion
                    if rev > 0:
                        if (last["mkt"] / rev) < 0.05:
                            st.info("📢 **VISIBILITÉ :** L'an dernier, votre budget pub était sous les 5% de votre CA. Vous perdez des parts de marché face à la concurrence.")
                        if (last["qual"] / rev) < 0.01:
                            st.info("⭐ **QUALITÉ :** Votre budget qualité est dangereusement bas. Les clients se tourneront vers de meilleurs produits.")
                    
                    if last["cash"] < rev * 0.10:
                        st.error("💸 **TRESORERIE :** Votre caisse est presque vide (moins de 10% du CA). Surveillez vos dépenses et vos délais clients !")
                    elif last["net_income"] > rev * 0.15:
                        st.success("✅ **EXCELLENTE GESTION :** Votre rentabilité (marge nette) était remarquable l'an dernier. Continuez ainsi !")

            with tab_bilan:
                st.subheader("🔍 Espionnage Concurrentiel (Données N-1)")
                if room["current_year"] == 1:
                    st.info("Aucun historique disponible pour l'Année 1.")
                else:
                    level = comp["history"][-1].get("espionnage_level", 0) if comp["history"] else 0
                    if level == 0: st.warning("Vous n'avez pas acheté d'espionnage. Données inaccessibles.")
                    
                    if level >= 1:
                        st.markdown("### 🟢 Niv 1 : Performances")
                        data_l1 = [{"Équipe": n, "PdM": f"{c['history'][-1]['real_market_share']*100:.1f}%", "Ventes (u)": f"{c['history'][-1]['sales']:.0f}", "Résultat Net (€)": f"{c['history'][-1]['net_income']:,.0f}"} for n, c in room["companies"].items() if c["history"]]
                        st.table(pd.DataFrame(data_l1))
                        
                    if level >= 2:
                        st.markdown("### 🟡 Niv 2 : Décisions Clés")
                        data_l2 = [{"Équipe": n, "Prix (€)": c['history'][-1]['price'], "Pub (€)": c['history'][-1]['mkt'], "Qualité (€)": c['history'][-1]['qual'], "Salaire (€)": c['history'][-1]['salary']} for n, c in room["companies"].items() if c["history"]]
                        st.table(pd.DataFrame(data_l2))
                        
                    if level >= 3:
                        st.markdown("### 🟠 Niv 3 : Compte de Résultat")
                        data_l3 = [{"Équipe": n, "CA (€)": c['history'][-1]['revenue'], "Coûts Achat (€)": c['history'][-1]['cogs'], "Frais RH (€)": c['history'][-1]['hr_cost'], "Total Charges (€)": c['history'][-1]['cogs']+c['history'][-1]['hr_cost']+c['history'][-1]['mkt']+c['history'][-1]['qual']+c['history'][-1]['rd']} for n, c in room["companies"].items() if c["history"]]
                        st.table(pd.DataFrame(data_l3))
                        
                    if level >= 4:
                        st.markdown("### 🔴 Niv 4 : Audit Comparatif")
                        all_prices = [c['history'][-1]['price'] for c in room["companies"].values() if c["history"]]
                        avg_price = sum(all_prices) / len(all_prices) if all_prices else 1
                        my_price = comp["history"][-1]["price"]
                        
                        if my_price > avg_price * 1.1: st.markdown("🔴 **Prix :** Vous êtes beaucoup plus cher que la moyenne du marché.")
                        elif my_price < avg_price * 0.9: st.markdown("🟢 **Prix :** Vous êtes agressif sur les prix, idéal pour les volumes.")
                        else: st.markdown("⚪ **Prix :** Vous êtes aligné sur la moyenne du marché.")

        st.sidebar.markdown("---")
        if room["status"] == "playing" and st.session_state.player_team == room["host"]:
            if st.sidebar.button("Forcer fin du tour", type="primary"):
                resolve_turn(room)
                st.rerun()
