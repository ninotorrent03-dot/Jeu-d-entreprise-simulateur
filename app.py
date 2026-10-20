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
st.set_page_config(page_title="Business Simulator - Édition CEO", layout="wide")

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
        "name": "Vélos Électriques Urbains Eco-conçus",
        "unit": "vélos",
        "benchmark_price": 1200.0,
        "base_cost": 650.0,
        "base_market_size_per_team": 6000,
        "context": "Mobilité douce en forte croissance. Les citadins cherchent robustesse et design.",
        "keywords": ["velo", "bike", "eco", "green", "urbain", "cycle", "mobility", "electrique"]
    },
    {
        "name": "Smartphones Éco-reconditionnés Premium",
        "unit": "smartphones",
        "benchmark_price": 480.0,
        "base_cost": 240.0,
        "base_market_size_per_team": 12000,
        "context": "Forte sensibilité au prix et aux garanties de reconditionnement.",
        "keywords": ["phone", "smart", "tech", "eco", "repack", "mobile", "renew"]
    },
    {
        "name": "Enceintes Hi-Fi en Bois Recyclé",
        "unit": "enceintes",
        "benchmark_price": 340.0,
        "base_cost": 160.0,
        "base_market_size_per_team": 8000,
        "context": "Clientèle d'audiophiles exigeants. Qualité et finition priment.",
        "keywords": ["sound", "audio", "hifi", "wood", "music", "acoustic"]
    }
]

# ==========================================
# 3. MOTEUR DE CALCUL & KARMA
# ==========================================
def calculate_name_bonus(company_name, product):
    score = 0.0
    name_lower = company_name.lower()
    for kw in product["keywords"]:
        if kw in name_lower: score += 1.5
    if len(company_name) > 3: score += 0.5
    return min(3.0, score)

def fmt_k(amount):
    if amount is None: return "0,0 K€"
    return f"{amount / 1000.0:,.1f} K€".replace(",", " ").replace(".", ",")

def fmt_num(val):
    return f"{val:,.0f}".replace(",", " ")

def init_company(name, start_capital, product):
    bonus = calculate_name_bonus(name, product)
    return {
        "name": name, "cash": start_capital, "stock": 0, "employees": 2, "machines": 0,
        "brand_awareness": 10.0 + bonus, "rd_cumul": 0.0, "rse_cumul": 0.0, "loans": [],
        "pending_client_cash": 0.0, "pending_supplier_cash": 0.0, "history": [], "current_decisions": {}
    }

def get_unit_cost(base_cost, rd_total):
    discount = min(0.30, rd_total / 100000.0)
    return base_cost * (1.0 - discount)

def get_hr_capacity(employees, salary, quality, training, karma_penalty=1.0):
    qual_penalty = max(0.75, 1.0 - (quality / 40000.0))
    train_boost = min(1.35, 1.0 + (training / 15000.0))
    salary_boost = min(1.20, max(0.80, 1.0 + ((salary - 30000) / 30000.0)))
    return employees * 3000 * qual_penalty * train_boost * salary_boost * karma_penalty

def get_theo_demand(base_demand, price, bench_price, marketing, quality, rse, client_terms, brand_awareness, karma_bonus=1.0):
    price_factor = (bench_price / price) ** 2.2 if price > 0 else 1.0
    mkt_factor = 1.0 + (marketing / 25000.0)
    qual_factor = 1.0 + (quality / 20000.0)
    rse_factor = 1.0 + (rse / 30000.0)
    terms_factor = 1.0 + (client_terms / 180.0)
    brand_factor = 1.0 + (brand_awareness / 100.0)
    return base_demand * price_factor * mkt_factor * qual_factor * rse_factor * terms_factor * brand_factor * karma_bonus

def resolve_karma_events(comp, dec, rev_est):
    event = None
    effects = {"hr_penalty": 1.0, "demand_bonus": 1.0, "cash_impact": 0.0, "stock_loss": 0.0, "supply_penalty": 1.0, "brand_impact": 0.0}
    proba_greve = 0.25 if dec.get("salary", 30000) < 25000 and dec.get("training", 0) < 500 else 0.02
    proba_boycott = 0.20 if float(dec.get("supplier_terms", 30)) > 60 else 0.01
    proba_scandale = 0.15 if rev_est > 0 and (dec.get("quality", 0) / rev_est) < 0.005 else 0.02
    proba_certif = 0.20 if rev_est > 0 and (dec.get("quality", 0) / rev_est) > 0.03 else 0.01
    proba_label = 0.20 if dec.get("salary", 30000) > 35000 and dec.get("training", 0) > 2000 else 0.01
    proba_rse = 0.25 if comp.get("rse_cumul", 0) + dec.get("rse_budget", 0) > 15000 else 0.05

    rand = random.random()
    if rand < proba_greve:
        event = "📉 GRÈVE GÉNÉRALE : Capacité RH divisée par 2 !"
        effects["hr_penalty"] = 0.5
    elif rand < proba_greve + proba_boycott:
        event = "🚫 BOYCOTT FOURNISSEUR : Vous ne recevez que 30% des commandes."
        effects["supply_penalty"] = 0.3
    elif rand < proba_greve + proba_boycott + proba_scandale:
        event = "🛑 SCANDALE QUALITÉ : Perte de 30% du stock."
        effects["stock_loss"] = 0.3
        effects["brand_impact"] = -10.0
    elif rand < proba_greve + proba_boycott + proba_scandale + proba_certif:
        event = "⭐ CERTIFICATION QUALITÉ : Attractivité augmentée (+15%)."
        effects["demand_bonus"] = 1.15
    elif rand < proba_greve + proba_boycott + proba_scandale + proba_certif + proba_label:
        event = "🏅 LABEL 'GREAT PLACE TO WORK' : Capacité RH boostée (+20%)."
        effects["hr_penalty"] = 1.20
    elif rand < proba_greve + proba_boycott + proba_scandale + proba_certif + proba_label + proba_rse:
        event = "🌿 SUBVENTION ÉCOLOGIQUE : Prime de l'État (+ 20 K€)."
        effects["cash_impact"] = 20000.0

    return event, effects

def generate_monthly_cashflow(comp, decs, revenue, purchases_value, expenses, utopia=False):
    # Génère 12 points de trésorerie pour le graphique
    c_terms = 0 if utopia else float(decs.get("client_terms", 0))
    s_terms = 120 if utopia else float(decs.get("supplier_terms", 0))
    
    monthly_rev = revenue / 12
    monthly_purch = purchases_value / 12
    monthly_exp = expenses / 12
    
    current_cash = comp["cash"]
    current_cash += comp.get("pending_client_cash", 0)
    current_cash -= comp.get("pending_supplier_cash", 0)
    current_cash += decs.get("new_loan_amount", 0)
    
    curve = [comp["cash"]] # Mois 0
    for m in range(1, 13):
        if m > (c_terms / 30): current_cash += monthly_rev
        if m > (s_terms / 30): current_cash -= monthly_purch
        current_cash -= monthly_exp
        curve.append(current_cash)
    return curve

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

    price_demand_boost = (product["benchmark_price"] - price) * 4.5
    market_size_est = max(1000, (product["base_market_size_per_team"] * num_teams) + price_demand_boost)

    base_demand = product["base_market_size_per_team"]
    theo_demand = get_theo_demand(base_demand, price, product["benchmark_price"], marketing, quality, rse_budget, client_terms, comp["brand_awareness"])
    
    hr_cap = get_hr_capacity(employees, salary, quality, training)
    prod_pct = (hr_cap / (employees * 3000)) * 100 if employees > 0 else 0
    
    if is_prod_phase:
        total_machines = comp["machines"] + decs.get("buy_machines", 0)
        prod_cap = total_machines * 2500
        max_possible_sales = min(hr_cap, prod_cap if total_machines > 0 else 0)
    else:
        max_possible_sales = hr_cap

    available_stock = comp["stock"] + purchase_qty
    sales = min(forecast_sales_input, available_stock, max_possible_sales, theo_demand)
    
    unit_cost = get_unit_cost(product["base_cost"], comp.get("rd_cumul", 0.0) + rd_budget)
    revenue = sales * price
    purchases_value = purchase_qty * unit_cost
    
    hr_cost = employees * salary * 1.45
    depreciation = (comp["machines"] + decs.get("buy_machines", 0)) * 10000.0 if is_prod_phase else 0.0
    machine_buy_cash = decs.get("buy_machines", 0) * 50000.0 if is_prod_phase else 0.0
    stock_final = available_stock - sales
    storage_cost = stock_final * 4.0
    
    market_study = 5000.0 if decs.get("buy_market_study") else 0.0
    expenses = hr_cost + marketing + quality + training + rd_budget + rse_budget + storage_cost + depreciation + market_study
    
    cash_delayed_clients = revenue * (min(client_terms, 365) / 365.0)
    cash_delayed_suppliers = purchases_value * (min(supplier_terms, 365) / 365.0)
    
    interest = sum([l["amount"] * 0.05 for l in comp.get("loans", [])])
    if decs.get("new_loan_amount", 0) > 0: interest += decs["new_loan_amount"] * 0.05
        
    net_before_tax = (revenue - purchases_value) - expenses - interest
    tax = net_before_tax * 0.25 if net_before_tax > 0 else 0.0
    net_income = net_before_tax - tax
    
    repayments = sum([l["annuity"] for l in comp.get("loans", []) if l["remaining_years"] > 0])
    
    # Génération des courbes pour graphique
    cf_curve = generate_monthly_cashflow(comp, decs, revenue, purchases_value, expenses + interest + tax + repayments + machine_buy_cash)
    
    # Courbe Utopique (Demande max sans retard RH, cash instantané)
    hr_cap_utopia = get_hr_capacity(employees, salary, 0, training) # 0 pénalité qualité
    sales_utopia = min(available_stock, hr_cap_utopia, theo_demand * 1.5)
    rev_utopia = sales_utopia * price
    cf_utopia = generate_monthly_cashflow(comp, decs, rev_utopia, purchases_value, expenses, utopia=True)
    
    total_market_size = product["base_market_size_per_team"] * num_teams
    est_share = (sales / total_market_size) * 100 if total_market_size > 0 else 0.0
    
    return {
        "sales": sales, "theo_demand": theo_demand, "revenue": revenue, "net_income": net_income,
        "end_cash": cf_curve[-1], "stock_final": stock_final, "unit_cost": unit_cost,
        "est_share": est_share, "hr_cap": hr_cap, "target_share": 100.0 / num_teams if num_teams > 0 else 100.0,
        "delayed_cash_impact": cash_delayed_clients, "prod_pct": prod_pct,
        "cf_curve": cf_curve, "cf_utopia": cf_utopia,
        "cogs": purchases_value, "hr_cost": hr_cost, "mkt": marketing, "qual": quality, "train": training, "rd": rd_budget, "rse": rse_budget
    }

def resolve_turn(room):
    product = room["product"]
    companies = room["companies"]
    num_teams = len(companies)
    is_prod_phase = (room["current_year"] >= 5)
    
    total_market_demand = product["base_market_size_per_team"] * num_teams * random.uniform(0.9, 1.1)
    
    events_by_team = {}
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        rev_est = dec.get("forecast_sales", 0) * dec.get("price", product["benchmark_price"])
        events_by_team[name] = resolve_karma_events(comp, dec, rev_est)

    scores = {}
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        price = dec.get("price", product["benchmark_price"])
        rse_tot = dec.get("rse_budget", 0.0) + comp.get("rse_cumul", 0.0)
        _, effects = events_by_team[name]
        
        scores[name] = get_theo_demand(1.0, price, product["benchmark_price"], dec.get("marketing", 0.0), 
                                       dec.get("quality", 0.0), rse_tot, float(dec.get("client_terms", 0)), 
                                       comp["brand_awareness"], effects["demand_bonus"])

    total_score = sum(scores.values()) if sum(scores.values()) > 0 else 1.0
    
    for name, comp in companies.items():
        dec = comp.get("current_decisions", {})
        event_msg, effects = events_by_team[name]
        
        rd_bud = dec.get("rd_budget", 0.0)
        comp["rd_cumul"] += rd_bud
        comp["rse_cumul"] += dec.get("rse_budget", 0.0)
        unit_cost = get_unit_cost(product["base_cost"], comp["rd_cumul"])
        
        if is_prod_phase:
            new_mach = dec.get("buy_machines", 0)
            comp["machines"] += new_mach
            comp["cash"] -= new_mach * 50000.0
            
        theo_share = scores[name] / total_score
        team_demand = total_market_demand * theo_share
        
        effective_purchase = dec.get("purchase_qty", 0) * effects["supply_penalty"]
        available_stock = comp["stock"] + effective_purchase
        
        hr_cap = get_hr_capacity(dec.get("employees", 1), dec.get("salary", 30000.0), dec.get("quality", 0.0), dec.get("training", 0.0), effects["hr_penalty"])
        
        if is_prod_phase:
            prod_cap = comp["machines"] * 2500
            actual_sales = min(team_demand, available_stock, hr_cap, prod_cap)
        else:
            actual_sales = min(team_demand, available_stock, hr_cap)
            
        real_market_share = actual_sales / total_market_demand
        revenue = actual_sales * dec.get("price", product["benchmark_price"])
        
        client_terms = float(dec.get("client_terms", 0))
        cash_delayed_clients = revenue * (min(client_terms, 365) / 365.0)
        cash_in_sales = revenue - cash_delayed_clients + comp.get("pending_client_cash", 0.0)
        comp["pending_client_cash"] = cash_delayed_clients
        
        purchases_value = effective_purchase * unit_cost
        supplier_terms = float(dec.get("supplier_terms", 0))
        cash_delayed_suppliers = purchases_value * (min(supplier_terms, 365) / 365.0)
        cash_out_purchases = purchases_value - cash_delayed_suppliers + comp.get("pending_supplier_cash", 0.0)
        comp["pending_supplier_cash"] = cash_delayed_suppliers
        
        hr_cost = dec.get("employees", 1) * dec.get("salary", 30000.0) * 1.45
        expenses = hr_cost + dec.get("marketing", 0.0) + dec.get("quality", 0.0) + dec.get("training", 0.0) + rd_bud + dec.get("rse_budget", 0.0)
        if dec.get("buy_market_study"): expenses += 5000.0
        
        depreciation = comp["machines"] * 10000.0 if is_prod_phase else 0.0
        
        comp["stock"] = (available_stock - actual_sales) * (1.0 - effects["stock_loss"])
        storage_cost = comp["stock"] * 4.0
        expenses += storage_cost
        
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
        
        net_before_tax = (revenue - (actual_sales * unit_cost)) - expenses - interest
        tax = net_before_tax * 0.25 if net_before_tax > 0 else 0.0
        net_income = net_before_tax - tax
        
        comp["cash"] += cash_in_sales - cash_out_purchases - (expenses - depreciation) - interest - tax - repayments + effects["cash_impact"]
        
        if comp["cash"] < 0:
            overdraft_fee = abs(comp["cash"]) * 0.12
            comp["cash"] -= overdraft_fee
            net_income -= overdraft_fee

        comp["employees"] = dec.get("employees", 1)
        comp["brand_awareness"] = max(1.0, min(100.0, comp["brand_awareness"] + (dec.get("marketing", 0.0) / 6000.0) - 0.8 + effects["brand_impact"]))
        comp["has_market_study"] = dec.get("buy_market_study", False)
        
        comp["history"].append({
            "year": room["current_year"], "sales": actual_sales, "real_market_share": real_market_share,
            "revenue": revenue, "cogs": purchases_value, "hr_cost": hr_cost, "mkt": dec.get("marketing", 0),
            "qual": dec.get("quality", 0), "train": dec.get("training", 0), "rd": rd_bud, "rse": dec.get("rse_budget", 0),
            "net_income": net_income, "cash": comp["cash"], "stock": comp["stock"],
            "price": dec.get("price", product["benchmark_price"]), "unit_cost": unit_cost, "hazard": event_msg
        })
        # Reset décisions
        comp["current_decisions"] = {}

    room["ready_teams"] = []
    room["current_year"] += 1
    if room["current_year"] > room["max_years"]:
        room["status"] = "ended"
        
    save_game_to_disk(room)

# ==========================================
# 4. INTERFACE UTILISATEUR
# ==========================================
if "room_code" not in st.session_state: st.session_state.room_code = None
if "player_team" not in st.session_state: st.session_state.player_team = None

if not st.session_state.room_code:
    st.title("🚀 Business Simulator - Édition CEO")
    
    col_c, col_j = st.columns(2)
    
    with col_c:
        st.subheader("1️⃣ Créer un Salon (Hôte)")
        with st.form("create_form"):
            host_name = st.text_input("Nom de votre Entreprise")
            num_years = st.slider("Durée du jeu (années)", 4, 10, 8)
            capital_k = st.number_input("Capital de départ (K€)", min_value=50, max_value=500, value=150)
            
            if st.form_submit_button("Créer la partie", type="primary"):
                if not host_name.strip():
                    st.error("⚠️ Entrez un nom d'entreprise !")
                else:
                    room_code = f"SALON-{random.randint(1000,9999)}"
                    product = random.choice(PRODUCT_UNIVERSES)
                    room = {
                        "room_code": room_code, "host": host_name.strip(), "product": product,
                        "max_years": num_years, "current_year": 1, "status": "waiting",
                        "start_capital": capital_k * 1000.0, "companies": {}, "ready_teams": []
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
                    elif player_name.strip() in room["companies"]: st.error("Ce nom est déjà pris.")
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
        st.markdown("### 🔑 CODE À PARTAGER À VOS AMIS :")
        st.info(f"👉 **{room['room_code']}** 👈")
        
        st.subheader("🏢 Entreprises connectées :")
        for name in room["companies"].keys():
            st.write(f"• **{name}**" + (" *(Hôte)*" if name == room["host"] else ""))
            
        st.markdown("---")
        if st.session_state.player_team == room["host"]:
            if st.button("🚀 Lancer la Partie !", type="primary"):
                if len(room["companies"]) < 1: st.error("Attendez d'être prêt !")
                else:
                    room["status"] = "playing"
                    save_game_to_disk(room)
                    st.rerun()
        else:
            st.write("⏳ *En attente que l'hôte lance la partie...*")
            if st.button("Actualiser l'écran"): st.rerun()
            
        if st.button("🚪 Quitter le salon"):
            st.session_state.room_code = None
            st.rerun()

    else:
        st.sidebar.markdown(f"**🔑 Salon :** `{room['room_code']}`")
        st.sidebar.markdown(f"**📦 Produit :** {product['name']}")
        st.sidebar.markdown(f"**📅 Année :** {room['current_year']} / {room['max_years']}")
        st.sidebar.markdown(f"**🏭 Phase :** {'Production' if is_prod_phase else 'Négoce'}")
        
        if st.sidebar.button("Déconnexion"):
            st.session_state.room_code = None
            st.rerun()

        if st.session_state.player_team not in room["companies"]:
            st.session_state.player_team = list(room["companies"].keys())[0]
            
        selected_team = st.sidebar.selectbox("Changer de vue :", list(room["companies"].keys()), index=list(room["companies"].keys()).index(st.session_state.player_team))
        comp = room["companies"][selected_team]
        has_played = selected_team in room["ready_teams"]
        
        st.title(f"🏢 {selected_team}")
        
        if comp["history"]:
            last_hist = comp["history"][-1]
            st.success(f"**📰 BILAN ANNÉE {last_hist['year']} :** Ventes = **{fmt_num(last_hist['sales'])} unités** | PdM = **{last_hist['real_market_share']*100:.1f}%** | Résultat Net = **{fmt_k(last_hist['net_income'])}**.")
            if last_hist.get("hazard"):
                st.warning(f"**🔔 ÉVÉNEMENT :** {last_hist['hazard']}")

        if has_played and room["status"] == "playing":
            st.success("✅ Vos décisions sont validées. En attente des concurrents...")
            if st.button("Actualiser"): st.rerun()
            
        elif room["status"] == "ended":
            st.balloons()
            st.header("🏆 Classement Final")
            final_list = []
            for name, c in room["companies"].items():
                val = c["cash"] + (c["stock"] * product["base_cost"] * 0.5)
                final_list.append({"Équipe": name, "Valeur Totale Est.": val / 1000.0, "Trésorerie": c["cash"] / 1000.0})
            df_f = pd.DataFrame(final_list).sort_values(by="Valeur Totale Est.", ascending=False).reset_index(drop=True)
            df_f.index += 1
            st.table(df_f.style.format({"Valeur Totale Est.": "{:,.1f} K€", "Trésorerie": "{:,.1f} K€"}))

        else:
            tab_dec, tab_sim, tab_treso, tab_bilan = st.tabs(["✍️ Simulation & Choix", "📊 Compte de Résultat", "💸 Trésorerie", "🔍 Bilan Concurrentiel"])
            
            # Initialisation Session State pour la simulation
            sim_key = f"sim_{selected_team}_{room['current_year']}"
            if sim_key not in st.session_state:
                last_decs = comp.get("history", [{}])[-1] if comp.get("history") else {}
                st.session_state[sim_key] = {
                    "price": float(last_decs.get("price", product["benchmark_price"])),
                    "forecast_sales": int(last_decs.get("sales", 3000)),
                    "purchase_qty": int(last_decs.get("sales", 3000)),
                    "buy_machines": 0, "marketing": 10000.0, "rd_budget": 3000.0, "rse_budget": 2000.0,
                    "employees": int(comp.get("employees", 2)), "salary": 30000.0, "quality": 2500.0,
                    "training": 1500.0, "client_terms": 30, "supplier_terms": 30, "new_loan_amount": 0.0,
                    "new_loan_duration": 3, "buy_market_study": False
                }
            
            with tab_dec:
                st.info("💡 Fais tes modifications et clique sur **'Calculer'** pour voir les impacts, sans bloquer ton tour.")
                with st.form(f"form_dec_{selected_team}"):
                    c_c1, c_c2, c_c3 = st.columns(3)
                    with c_c1:
                        price = st.number_input("Prix de Vente (€)", min_value=1.0, value=st.session_state[sim_key]["price"])
                        forecast_sales = st.number_input("Objectif Vente (unités)", min_value=0, value=st.session_state[sim_key]["forecast_sales"], step=100)
                    with c_c2:
                        marketing = st.number_input("Budget Pub (€)", min_value=0.0, value=st.session_state[sim_key]["marketing"], step=1000.0)
                        quality = st.number_input("Budget Qualité (€)", min_value=0.0, value=st.session_state[sim_key]["quality"], step=500.0)
                    with c_c3:
                        client_terms = st.number_input("Délai Clients (jours)", min_value=0, max_value=120, value=st.session_state[sim_key]["client_terms"])
                        supplier_terms = st.number_input("Délai Fournisseurs (jours)", min_value=0, max_value=120, value=st.session_state[sim_key]["supplier_terms"])

                    c_a1, c_a2, c_a3 = st.columns(3)
                    with c_a1:
                        purchase_qty = st.number_input("Quantité Produite/Achetée", min_value=0, value=st.session_state[sim_key]["purchase_qty"], step=100)
                        buy_machines = st.number_input("Acheter Machines (50K€/u)", min_value=0, value=st.session_state[sim_key]["buy_machines"], disabled=not is_prod_phase)
                    with c_a2:
                        employees = st.number_input("Effectif (Salariés)", min_value=1, value=st.session_state[sim_key]["employees"])
                        salary = st.number_input("Salaire brut/an (€)", min_value=20000.0, value=st.session_state[sim_key]["salary"], step=1000.0)
                    with c_a3:
                        training = st.number_input("Budget Formation (€)", min_value=0.0, value=st.session_state[sim_key]["training"], step=500.0)
                        rd_budget = st.number_input("Budget R&D (€)", min_value=0.0, value=st.session_state[sim_key]["rd_budget"], step=1000.0)
                        rse_budget = st.number_input("Budget RSE Écologie (€)", min_value=0.0, value=st.session_state[sim_key]["rse_budget"], step=1000.0)

                    c_f1, c_f2 = st.columns(2)
                    with c_f1:
                        loan_amount = st.number_input("Emprunt Banque (€)", min_value=0.0, value=st.session_state[sim_key]["new_loan_amount"], step=5000.0)
                        loan_duration = st.slider("Durée emprunt (ans)", 1, 5, value=st.session_state[sim_key]["new_loan_duration"])
                    with c_f2:
                        buy_market_study = st.checkbox("🕵️ Acheter Étude de marché (5 K€)", value=st.session_state[sim_key]["buy_market_study"])

                    calc_btn = st.form_submit_button("🔄 Calculer mes prévisions")

                if calc_btn:
                    st.session_state[sim_key] = {
                        "price": price, "forecast_sales": forecast_sales, "purchase_qty": purchase_qty,
                        "buy_machines": buy_machines, "marketing": marketing, "rd_budget": rd_budget,
                        "rse_budget": rse_budget, "employees": employees, "salary": salary,
                        "quality": quality, "training": training, "client_terms": client_terms,
                        "supplier_terms": supplier_terms, "new_loan_amount": loan_amount,
                        "new_loan_duration": loan_duration, "buy_market_study": buy_market_study
                    }
                    # Sauvegarde pour courbe N-1 de treso
                    cf_key = f"cf_{selected_team}_{room['current_year']}"
                    if cf_key in st.session_state:
                        st.session_state[f"cf_prev_{selected_team}_{room['current_year']}"] = st.session_state[cf_key]
                    st.success("✅ Prévisions recalculées ! Consulte les onglets 'Compte de Résultat' et 'Trésorerie'.")

                st.markdown("---")
                if st.button("🔒 VALIDER DÉFINITIVEMENT MES CHOIX", type="primary"):
                    room["companies"][selected_team]["current_decisions"] = st.session_state[sim_key]
                    room["ready_teams"].append(selected_team)
                    save_game_to_disk(room)
                    st.rerun()

            # --- CALCUL DES PRÉVISIONS ---
            forecast = calculate_forecast(comp, st.session_state[sim_key], product, is_prod_phase, num_teams)
            st.session_state[f"cf_{selected_team}_{room['current_year']}"] = forecast["cf_curve"]

            with tab_sim:
                st.subheader("📊 Compte de Résultat (Prévisionnel vs N-1)")
                
                # Création du tableau comparatif
                prev_hist = comp["history"][-1] if comp["history"] else None
                pl_data = [
                    {"Poste": "Chiffre d'Affaires", "Réel N-1": prev_hist["revenue"] if prev_hist else 0, "Prévu N": forecast["revenue"]},
                    {"Poste": "Coût des Achats/Prod", "Réel N-1": prev_hist["cogs"] if prev_hist else 0, "Prévu N": forecast["cogs"]},
                    {"Poste": "Marge Brute", "Réel N-1": (prev_hist["revenue"] - prev_hist["cogs"]) if prev_hist else 0, "Prévu N": forecast["revenue"] - forecast["cogs"]},
                    {"Poste": "Masse Salariale", "Réel N-1": prev_hist["hr_cost"] if prev_hist else 0, "Prévu N": forecast["hr_cost"]},
                    {"Poste": "Budget Pub", "Réel N-1": prev_hist["mkt"] if prev_hist else 0, "Prévu N": forecast["mkt"]},
                    {"Poste": "Budget Qualité", "Réel N-1": prev_hist["qual"] if prev_hist else 0, "Prévu N": forecast["qual"]},
                    {"Poste": "Budget R&D", "Réel N-1": prev_hist["rd"] if prev_hist else 0, "Prévu N": forecast["rd"]},
                    {"Poste": "RSE & Formation", "Réel N-1": (prev_hist["rse"] + prev_hist["train"]) if prev_hist else 0, "Prévu N": forecast["rse"] + forecast["train"]},
                    {"Poste": "RÉSULTAT NET", "Réel N-1": prev_hist["net_income"] if prev_hist else 0, "Prévu N": forecast["net_income"]}
                ]
                df_pl = pd.DataFrame(pl_data)
                df_pl["Évolution"] = df_pl["Prévu N"] - df_pl["Réel N-1"]
                st.table(df_pl.style.format({"Réel N-1": "{:,.0f} €", "Prévu N": "{:,.0f} €", "Évolution": "{:+,.0f} €"}))

                st.markdown("---")
                r_h1, r_h2, r_h3 = st.columns(3)
                r_h1.metric("Productivité RH", f"{forecast['prod_pct']:.1f}%", help="100% = Normal. <100% = Ralentis (Qualité haute, salaire bas). >100% = Efficaces (Formation).")
                r_h2.metric("Capacité Max", f"{fmt_num(forecast['hr_cap'])} unités")
                r_h3.metric("Demande Théorique", f"{fmt_num(forecast['theo_demand'])} unités", help="Ce que le marché est prêt à t'acheter si tu as le stock.")

            with tab_treso:
                st.subheader("💸 Évolution de la Trésorerie sur 12 Mois")
                
                max_overdraft = st.slider("Ajuster la limite de découvert autorisé (€)", 
                                        min_value=0, 
                                        max_value=int((prev_hist["revenue"] if prev_hist else comp["cash"]) * 0.25), 
                                        value=10000, step=1000)
                
                months = list(range(0, 13))
                fig = go.Figure()
                
                # 1. Courbe Utopique (Verte)
                fig.add_trace(go.Scatter(x=months, y=forecast["cf_utopia"], mode='lines', name='Utopique (Parfait)', line=dict(color='green', dash='dot')))
                
                # 2. Courbe Simulation Précédente (Grise)
                prev_cf_key = f"cf_prev_{selected_team}_{room['current_year']}"
                if prev_cf_key in st.session_state:
                    fig.add_trace(go.Scatter(x=months, y=st.session_state[prev_cf_key], mode='lines', name='Dernier Calcul', line=dict(color='lightgrey')))
                
                # 3. Courbe Actuelle (Bleue)
                fig.add_trace(go.Scatter(x=months, y=forecast["cf_curve"], mode='lines+markers', name='Prévision Actuelle', line=dict(color='blue', width=3)))
                
                # 4. Courbe Découvert Autorisé (Rouge)
                fig.add_trace(go.Scatter(x=months, y=[-max_overdraft]*13, mode='lines', name='Limite Découvert', line=dict(color='red', dash='dash')))
                
                fig.update_layout(title="Impact des délais de paiement et dépenses sur la trésorerie", xaxis_title="Mois", yaxis_title="Trésorerie (€)", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

            with tab_bilan:
                st.subheader("🔍 Espionnage (N-1)")
                if comp["history"]:
                    has_study = comp.get("has_market_study", False)
                    comp_data = []
                    for name, c in room["companies"].items():
                        if c["history"]:
                            h = c["history"][-1]
                            comp_data.append({
                                "Équipe": name,
                                "PdM": f"{h['real_market_share']*100:.1f}%",
                                "Ventes": f"{h['sales']:.0f} u.",
                                "Prix": f"{h['price']:.0f} €",
                                "Pub": fmt_k(h["mkt"]) if has_study else "Masqué",
                                "Qualité": fmt_k(h["qual"]) if has_study else "Masqué",
                                "R&D": fmt_k(h["rd"]) if has_study else "Masqué"
                            })
                    st.table(pd.DataFrame(comp_data))

        st.sidebar.markdown("---")
        if room["status"] == "playing" and st.session_state.player_team == room["host"]:
            if st.sidebar.button("Forcer fin du tour", type="primary"):
                resolve_turn(room)
                st.rerun()