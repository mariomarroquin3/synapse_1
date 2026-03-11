import sys

with open('pages/admin_dashboard.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'with tab3:' in line:
        start_idx = i - 1  # include the comment
        break

for i, line in enumerate(lines[start_idx+1:], start=start_idx+1):
    if 'with tab5:' in line:
        end_idx = i - 1  # include the comment
        break

if start_idx == -1 or end_idx == -1:
    print(f"Could not find delimiters. Start: {start_idx}, End: {end_idx}")
    sys.exit(1)

new_content = """    # --- TAB 3: CONTROL DE CUENTAS Y TARJETAS ---
    with tab3:
        st.header("Control de Cuentas y Tarjetas")
        st.write("Gestiona el estado operativo (Activa, Bloqueada, Suspendida) de las cuentas y tarjetas.")

        tab3_clientes, tab3_personal = st.tabs(["👥 Cuentas de Clientes", "🏢 Cuentas de Personal"])

        def render_account_controls(user_list, search_query_val, is_staff_control=False):
            if search_query_val:
                user_list = [c for c in user_list if search_query_val in c['full_name'].lower() or search_query_val in c['email'].lower()]
            
            if is_staff_control:
                staff_with_accounts = []
                for u in user_list:
                    accs = get_accounts_by_user(u["Id_user"])
                    if accs:
                        staff_with_accounts.append(u)
                user_list = staff_with_accounts
            
            if not user_list:
                st.info("No hay usuarios en esta categoría con cuentas bancarias.")
                return

            prefix = "stf_ctrl" if is_staff_control else "cli_ctrl"

            for client in user_list:
                with st.expander(f"👤 {client['full_name']} | ✉️ {client['email']}"):
                    # 1. Obtener y renderizar la Cuenta
                    accounts = get_accounts_by_user(client["Id_user"])
                    accounts = [
                        acc for acc in accounts
                        if (acc.get("status_id", acc[4] if isinstance(acc, tuple) else None)) in [1,2,3]
                        ]
                    
                    if not accounts:
                         st.info("Este usuario no tiene cuentas bancarias operativas.")
                         continue
                         
                    st.markdown("#### 🏦 Cuentas Bancarias")
                    for acc_idx, account in enumerate(accounts):
                        ac_id = account.get("Id_account", account[0] if isinstance(account, tuple) else None)
                        if not ac_id: continue
                        
                        ac_num = account.get("account_number", account[2] if isinstance(account, tuple) else "N/A")
                        ac_status = account.get("status_id", account[4] if isinstance(account, tuple) else 1)
                        
                        col_acc1, col_acc2 = st.columns([2, 1])
                        with col_acc1:
                            st.write(f"**Número de Cuenta:** `{ac_num}`")
                            st.write(f"**Saldo Actual:** Pendiente a cargar en módulo")
                        
                        with col_acc2:
                            new_ac_status = st.selectbox(
                                "Estado de la Cuenta",
                                options=[1, 2, 3],
                                format_func=lambda x: "✅ Activa" if x == 1 else ("⚠️ Bloqueada" if x == 2 else "🚫 Suspendida"),
                                index=[1, 2, 3].index(ac_status) if ac_status in [1,2,3] else 0,
                                key=f"acc_status_{prefix}_{ac_id}"
                            )
                            
                            if new_ac_status != ac_status:
                                try:
                                     update_account_status(ac_id, new_ac_status)
                                     log_action(
                                          st.session_state["user_data"]["Id_user"],
                                          "CAMBIO_ESTADO_CUENTA",
                                          f"Admin cambió estado de la cuenta {ac_num} a {new_ac_status}"
                                          )
                                     st.cache_data.clear()
                                     st.success(f"Estado de cuenta {ac_num} actualizado correctamente.")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                                    
                        # 2. Obtener y renderizar las Tarjetas de esta cuenta
                        st.markdown(f"**💳 Tarjetas Vinculadas a {ac_num}**")
                        cards = get_cards_by_account(ac_id)
                        if cards:
                            for card in cards:
                                with st.container(border=True):
                                    c1, c2 = st.columns([3, 1])
                                    with c1:
                                        last4 = str(card["card_number"])[-4:]
                                        st.write(f"**Tarjeta:** `**** **** **** {last4}`")
                                        exp = card["expiration_date"].strftime("%m/%y") if card["expiration_date"] else "N/A"
                                        st.caption(f"Vence: {exp}")
                                    
                                    with c2:
                                        toggle_label = "Activa" if card["is_active"] else "Inactiva"
                                        is_active_new = st.toggle(
                                            toggle_label,
                                            value=bool(card["is_active"]),
                                            key=f"card_toggle_{prefix}_{card['Id_card']}"
                                        )
                                        
                                        if is_active_new != bool(card["is_active"]):
                                            try:
                                                update_card_status(card["Id_card"], is_active_new)
                                                log_action(
                                                    st.session_state["user_data"]["Id_user"],
                                                    "CAMBIO_ESTADO_TARJETA",
                                                    f"Admin cambió estado de la tarjeta ****{last4} a {'Activa' if is_active_new else 'Inactiva'}"
                                                    )
                                                st.cache_data.clear()
                                                st.toast(f"Estado de la tarjeta ...{last4} cambiado a {'Activa' if is_active_new else 'Inactiva'}", icon="✅")
                                            except Exception as e:
                                                st.error(f"Error: {str(e)}")
                        else:
                            st.info("No hay tarjetas vinculadas a esta cuenta.")
                        
                        if acc_idx < len(accounts) - 1:
                            st.divider()

        with tab3_clientes:
            st.subheader("Control de Cuentas de Clientes Regulares")
            clients_for_control = cached_get_users(is_staff=False)
            search_control_cli = st.text_input("🔍 Buscar cliente por nombre o correo", key="search_ctrl_cli").lower()
            render_account_controls(clients_for_control if clients_for_control else [], search_control_cli, is_staff_control=False)

        with tab3_personal:
            st.subheader("Control de Cuentas del Personal")
            staff_for_control = cached_get_users(is_staff=True)
            search_control_stf = st.text_input("🔍 Buscar personal por nombre o correo", key="search_ctrl_stf").lower()
            render_account_controls(staff_for_control if staff_for_control else [], search_control_stf, is_staff_control=True)

    @st.cache_data(ttl=60)
    def get_pending_approvals():
        query = \"\"\"
            SELECT 
                t.Id_transaction, t.description, t.transaction_date, 
                a.amount, a.from_account_id, a.to_account_id,
                tt.name AS type_name, u.full_name AS requester
            FROM (([transaction] t
            INNER JOIN transaction_approvals a ON t.Id_transaction = a.transaction_id)
            INNER JOIN transaction_type tt ON t.transaction_type_id = tt.Id_transaction_type)
            INNER JOIN [user] u ON t.created_by_user_id = u.Id_user
            WHERE t.status_id = 2
        \"\"\"
        with get_cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    # --- TAB 4: APROBACIONES ($10K+) ---
    with tab4:
        st.header("Transacciones Pendientes de Aprobación")
        st.write("Cualquier movimiento mayor o igual a $10,000 requiere autorización manual.")

        pendientes = get_pending_approvals()

        if pendientes:
            for p in pendientes:
                tx_id, desc, date, amount, from_acc, to_acc, type_name, req = p
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.markdown(f"**ID:** {tx_id} | **Tipo:** {type_name}")
                        st.markdown(f"**Solicitante:** {req}")
                        amt_display = float(amount or 0)
                        st.markdown(f"**Monto:** `${amt_display:,.2f}`")
                        date_str = date.strftime('%d/%m/%Y %H:%M') if date else "N/A"
                        st.caption(f"Fecha: {date_str}")

                    with c2:
                        st.info(f"De: {from_acc if from_acc else 'N/A'}\\nA: {to_acc if to_acc else 'N/A'}")

                    with c3:
                        note = st.text_input("Nota (opcional)", key=f"note_{tx_id}")
                        col_b1, col_b2 = st.columns(2)
                        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                        if col_b1.button("✅ Aprobar", key=f"app_{tx_id}", width="stretch", type="primary"):
                            res = review_transaction(tx_id, st.session_state['user_data']['Id_user'], True, note)
                            if res["success"]:
                                st.cache_data.clear()
                                st.success("Aprobada")
                            else: st.error(res["error"])
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                        if col_b2.button("❌ Rechazar", key=f"rej_{tx_id}", width="stretch", type="secondary"):
                            res = review_transaction(tx_id, st.session_state['user_data']['Id_user'], False, note)
                            if res["success"]:
                                st.cache_data.clear()
                                st.warning("Rechazada")
                            else: st.error(res["error"])
                        st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay transacciones pendientes de revisión.")

"""

lines[start_idx:end_idx] = [new_content]

with open('pages/admin_dashboard.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Replacement successful.")
