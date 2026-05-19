
import streamlit as st
import pandas as pd
import os
import time
from processor import RateProcessor
from exporter import TemplateExporter
from storage import load_mappings, save_mappings

st.set_page_config(page_title="Facility Rate Calculator", layout="wide", page_icon="💰")
st.title("💰 Facility Rate Calculator")

# --- SIDEBAR: Persistent Loading ---
st.sidebar.header("📁 Data Sources")
base_folder = "/Users/fengyuanshi/Desktop/rate calculation"
all_files = os.listdir(base_folder) if os.path.exists(base_folder) else []

finance_file = st.sidebar.selectbox("Finance Report", [f for f in all_files if "Financial Report" in f])
usage_file = st.sidebar.selectbox("iLab Usage Report", [f for f in all_files if "charges_report" in f])
template_file = st.sidebar.selectbox("Master Base Template", [f for f in all_files if "Rate Calc" in f or "Template" in f])
equip_file = st.sidebar.selectbox("Equipment List", [f for f in all_files if "equipment" in f])

if st.sidebar.button("Load & Process Data"):
    processor = RateProcessor(os.path.join(base_folder, finance_file), os.path.join(base_folder, usage_file), os.path.join(base_folder, equip_file))
    with st.spinner("Parsing reports..."):
        processor.load_data()
        st.session_state['processor'] = processor
        st.success("Data Loaded!")

if 'processor' in st.session_state:
    proc = st.session_state['processor']
    saved = load_mappings()
    
    # PEAK UX: Horizontal radio for stable navigation
    st.divider()
    views = ["🏗️ Instrument Definition", "📊 Usage Summary", "👥 Labor Costs", "🛠️ Service Contracts", "💸 General Expenses", "🔮 Equip Projections", "🔭 Equipment & Depr", "📈 Final Rates"]
    active_view = st.radio("Tool Section:", views, horizontal=True)
    st.divider()
    
    groups = saved.get('groups', {})
    reported_inst_list = sorted(list(groups.keys()))

    if active_view == "🏗️ Instrument Definition":
        st.subheader("Define Reporting Instruments")
        raw_services = sorted(proc.usage['Instrument'].tolist())
        new_inst = st.text_input("New Reporting Instrument (e.g. 'JEOL ARM')")
        if st.button("Add Instrument"):
            if new_inst and new_inst not in groups:
                groups[new_inst] = []; save_mappings(saved.get('labor',{}), saved.get('depreciation',{}), groups, saved.get('expenses',{}), saved.get('projections',[]), saved.get('contracts',{})); st.rerun()
        for inst in reported_inst_list:
            with st.expander(f"Group: {inst}", expanded=True):
                c1, c2 = st.columns([3, 1])
                selected = c1.multiselect(f"Services", raw_services, default=[s for s in groups[inst] if s in raw_services], key=f"g_{inst}")
                groups[inst] = selected
                if c2.button("Delete", key=f"d_{inst}"): del groups[inst]; save_mappings(saved.get('labor',{}), saved.get('depreciation',{}), groups, saved.get('expenses',{}), saved.get('projections',[]), saved.get('contracts',{})); st.rerun()
        if st.button("Save All Definitions", type="primary"):
            save_mappings(saved.get('labor',{}), saved.get('depreciation',{}), groups, saved.get('expenses',{}), saved.get('projections',[]), saved.get('contracts',{}))
            st.success("Definitions Saved!")

    elif active_view == "📊 Usage Summary":
        st.subheader("Billable Hours by Instrument")
        grouped_usage_data = [{"Instrument": r_inst, "Hours": proc.usage[proc.usage['Instrument'].isin(groups[r_inst])]['Hours'].sum()} for r_inst in reported_inst_list]
        st.dataframe(pd.DataFrame(grouped_usage_data), use_container_width=True)

    elif active_view == "👥 Labor Costs":
        st.subheader("Staff Salary Allocation")
        instruments = ["Shared"] + reported_inst_list
        labor_mapping = {}
        for i, row in proc.salaries.iterrows():
            key = f"{row['Employee Name']}_{row['Position Title']}"
            idx = instruments.index(saved["labor"].get(key, "Shared")) if saved["labor"].get(key, "Shared") in instruments else 0
            labor_mapping[key] = st.selectbox(f"Allocation for {row['Employee Name']}", instruments, index=idx, key=f"sal_{i}")
        if st.button("Save Labor"):
            save_mappings(labor_mapping, saved.get('depreciation',{}), groups, saved.get('expenses',{}), saved.get('projections',[]), saved.get('contracts',{}))
            st.success("Labor Saved!")

    elif active_view == "🛠️ Service Contracts":
        st.subheader("Service Contract Allocation")
        contracts_df = proc.service_contracts.copy()
        with st.form("contract_form"):
            new_con_map = {}
            for i, row in contracts_df.iterrows():
                k = f"{row['Account']}_{row['Description']}_{row['Amount']}"
                default = saved["contracts"].get(k, ["Shared"])
                c_info, c_sel = st.columns([3, 1])
                c_info.write(f"**{row['Description']}** (${row['Amount']:.2f})")
                new_con_map[k] = c_sel.multiselect("Allocation", ["Shared", "Exclude"] + reported_inst_list, default=default, key=f"con_{i}")
            if st.form_submit_button("Save Service Contracts"):
                save_mappings(saved.get('labor',{}), saved.get('depreciation',{}), groups, saved.get('expenses',{}), saved.get('projections',[]), new_con_map)
                st.success("Saved!"); st.rerun()

    elif active_view == "💸 General Expenses":
        st.subheader("General Expenditures (Summary Level)")
        exp_df = proc.expenses_detail.copy()
        with st.form("exp_form"):
            new_exp_map = {}
            for i, row in exp_df.iterrows():
                k = f"{row['Account']}_{row['Description']}_{row['Amount']}"
                default = saved["expenses"].get(k, ["Shared"])
                c_info, c_sel = st.columns([3, 1])
                c_info.write(f"**{row['Account']}**: {row['Description']} (${row['Amount']:.2f})")
                new_exp_map[k] = c_sel.multiselect("Allocation", ["Shared", "Exclude"] + reported_inst_list, default=default, key=f"exp_{i}")
            if st.form_submit_button("Save Expenses"):
                save_mappings(saved.get('labor',{}), saved.get('depreciation',{}), groups, new_exp_map, saved.get('projections',[]), saved.get('contracts',{}))
                st.success("Saved!"); st.rerun()

    elif active_view == "🔮 Equip Projections":
        st.subheader("Future Equipment Projections")
        current_projs = saved.get('projections', [])
        with st.form("proj_form"):
            c1, c2, c3 = st.columns([3, 1, 2])
            desc = c1.text_input("Asset Description")
            amt = c2.number_input("Annual Depreciation ($)", value=0.0)
            alloc = c3.multiselect("Allocate to", ["Shared"] + reported_inst_list)
            if st.form_submit_button("Add Projection"):
                if desc and amt > 0:
                    current_projs.append({"description": desc, "amount": amt, "allocation": alloc})
                    save_mappings(saved.get('labor',{}), saved.get('depreciation',{}), groups, saved.get('expenses',{}), current_projs, saved.get('contracts',{}))
                    st.rerun()
        for i, p in enumerate(current_projs):
            c1, c2, c3, c4 = st.columns([3,1,2,1])
            c1.write(p['description']); c2.write(f"${p['amount']:,.2f}"); c3.caption(f"Target: {', '.join(p['allocation'])}")
            if c4.button("🗑️", key=f"dp_{i}"):
                current_projs.pop(i); save_mappings(saved.get('labor',{}), saved.get('depreciation',{}), groups, saved.get('expenses',{}), current_projs, saved.get('contracts',{})); st.rerun()

    elif active_view == "🔭 Equipment & Depr":
        st.subheader("Asset Mapping")
        dep_df = proc.depreciation.copy()
        if dep_df.empty: st.warning("No data.")
        else:
            depr_mapping = {}
            options = ["Skip"] + reported_inst_list
            for i, row in dep_df.iterrows():
                idx = options.index(saved["depreciation"].get(row['Asset Description'], "Skip")) if saved["depreciation"].get(row['Asset Description']) in options else 0
                depr_mapping[row['Asset Description']] = st.selectbox(f"Map: {row['Asset Description']}", options, index=idx, key=f"dep_{i}")
            if st.button("Save Depreciation"):
                save_mappings(saved.get('labor',{}), depr_mapping, groups, saved.get('expenses',{}), saved.get('projections',[]), saved.get('contracts',{}))
                st.success("Mapping Saved!")

    elif active_view == "📈 Final Rates":
        st.subheader("Calculated Internal Rates")
        grouped_usage = {inst: float(proc.usage[proc.usage['Instrument'].isin(groups[inst])]['Hours'].sum()) for inst in reported_inst_list}
        if 'adj_usage' not in st.session_state: st.session_state['adj_usage'] = grouped_usage
        
        with st.expander("🛠️ Hours Overrides"):
            for inst in reported_inst_list:
                st.session_state['adj_usage'][inst] = st.number_input(f"Hours: {inst}", value=st.session_state['adj_usage'].get(inst, 0.0), key=f"ah_{inst}")
        
        if st.button("Calculate Final Rates", type="primary"):
            s = load_mappings(); adj_u = st.session_state['adj_usage']; total_h = sum(adj_u.values())
            def allocate_pool(df, mapping, k):
                alloc = {inst: 0.0 for inst in reported_inst_list}
                for _, row in df.iterrows():
                    key = f"{row['Account']}_{row['Description']}_{row[k]}"
                    targets = mapping.get(key, ["Shared"])
                    if "Exclude" in targets: continue
                    if "Shared" in targets: targets = reported_inst_list
                    gh = sum([adj_u[t] for t in targets])
                    for t in targets:
                        if gh > 0: alloc[t] += (adj_u[t] / gh) * row[k]
                return alloc
            a_exp = allocate_pool(proc.expenses_detail, s.get('expenses', {}), 'Amount')
            a_con = allocate_pool(proc.service_contracts, s.get('contracts', {}), 'Amount')
            results = []
            for inst in reported_inst_list:
                mapped = [a for a, target in s.get('depreciation',{}).items() if target == inst]
                i_dep = proc.dep_full[proc.dep_full['Asset Description'].isin(mapped)]
                d3e = i_dep[i_dep['Fund Type'] == '3E']['Depreciation Amount'].sum()
                dnon = i_dep[i_dep['Fund Type'] == 'Non-3E']['Depreciation Amount'].sum()
                d_lab = sum([proc.salaries[proc.salaries['Employee Name'] == k.split('_')[0]]['Payroll Expense Amount'].sum() for k, target in s.get('labor',{}).items() if target == inst])
                s_lab = sum([proc.salaries[proc.salaries['Employee Name'] == k.split('_')[0]]['Payroll Expense Amount'].sum() for k, target in s.get('labor',{}).items() if target == "Shared"])
                pct = adj_u[inst] / total_h if total_h > 0 else 0
                total = d3e + dnon + d_lab + a_exp[inst] + a_con[inst] + (s_lab * pct)
                results.append({"Instrument": inst, "Total Cost": total, "Hours": adj_u[inst], "Rate": total / adj_u[inst] if adj_u[inst] > 0 else 0})
            st.session_state['last_calc'] = pd.DataFrame(results)

        if 'last_calc' in st.session_state:
            st.dataframe(st.session_state['last_calc'], use_container_width=True)
            st.divider()
            if st.button("Generate Master Rate Calculation (.xlsx)", type="primary"):
                try:
                    s = load_mappings()
                    exporter = TemplateExporter(os.path.join(base_folder, template_file))
                    out = os.path.join(base_folder, "EMC_FY26_Master_Rate_Calculation.xlsx")
                    exporter.generate_master_calculation(proc, st.session_state['adj_usage'], s.get('depreciation',{}), s.get('groups',{}), s.get('projections',[]), s.get('contracts', {}), out)
                    st.success(f"Generated: {out}")
                    st.balloons()
                except Exception as e: st.error(f"Error: {e}")

else: st.info("Please load data from the sidebar to begin.")
