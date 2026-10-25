2000000].index(st.session_state[sim_key]["defense_level"]), format_func=lambda x: {0:"0€ (Pas de bouclier)", 500000:"500 K€ (25% chance blocage)", 1000000:"1 M€ (50% chance)", 1500000:"1.5 M€ (75% chance)", 2000000:"2 M€ (Imparable)"}[x])
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
