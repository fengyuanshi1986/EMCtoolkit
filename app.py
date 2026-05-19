
import streamlit as st
import pandas as pd
from database import PublicationDB
from data_fetcher import DataFetcher
import time
import os

# Standalone Restoration with Year Range
st.set_page_config(page_title="EMC Publication Tracker", layout="wide", page_icon="🔭")

db = PublicationDB()
fetcher = DataFetcher()

st.title("🔭 EMC Publication Tracker")
st.markdown("Automated Facility Citation Discovery & Management")

# --- SIDEBAR: Settings & Researchers ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Semantic Scholar API Key (Optional)", type="password")
    if api_key: fetcher.set_api_key(api_key)
    
    with st.expander("🔧 Facility Keywords & Grants"):
        kws = db.get_keywords()
        c1, c2 = st.columns([3, 1])
        new_kw = c1.text_input("New Keyword")
        kw_type = c2.selectbox("Type", ["Specific", "General"])
        if st.button("Add"):
            if new_kw: db.add_keyword(new_kw, kw_type); st.rerun()
        st.dataframe(kws, hide_index=True)

    st.divider()
    st.header("👥 Researcher Management")
    authors = db.get_authors()
    
    with st.expander("🔍 Find & Add Author (Semantic Scholar)"):
        a_query = st.text_input("Search Name")
        if st.button("Search Authors"):
            res = fetcher.search_author(a_query)
            if isinstance(res, list):
                for a in res[:5]:
                    cols = st.columns([3, 1])
                    affil = a.get('affiliations', [])
                    affil_text = affil[0] if affil else "No Affiliation"
                    cols[0].write(f"**{a['name']}** ({affil_text})")
                    if cols[1].button("Add", key=f"add_s2_{a['authorId']}"):
                        db.add_author(a['authorId'], a['name'], affil_text)
                        st.success("Added!"); st.rerun()

    st.divider()
    st.write(f"Tracked PIs: {len(authors)}")
    for _, auth in authors.iterrows():
        c1, c2 = st.columns([4, 1])
        c1.caption(f"**{auth['name']}**")
        if c2.button("🗑️", key=f"del_auth_{auth['s2_id']}"):
            db.delete_author(auth['s2_id']); st.rerun()

# --- MAIN WORKSPACE ---
tabs = st.tabs(["🔍 Discovery Scan", "📝 Verification Queue", "✅ Confirmed Database", "📂 Manual Entry"])

with tabs[0]:
    st.subheader("Discovery Engine")
    st.write("Sync papers for all tracked researchers within a specific year range.")
    
    # NEW: YEAR RANGE FILTER
    c1, c2 = st.columns(2)
    start_year = c1.number_input("Start Year", value=2023, min_value=2000, max_value=2030)
    end_year = c2.number_input("End Year", value=2026, min_value=2000, max_value=2030)
    
    if st.button("Fetch Papers in Range", type="primary", use_container_width=True):
        for _, auth in authors.iterrows():
            st.write(f"Syncing **{auth['name']}**...")
            papers, stats = fetcher.fetch_semantic_scholar_data(auth['s2_id'])
            if isinstance(papers, pd.DataFrame) and not papers.empty:
                # Filter by year range
                filtered_papers = papers[(papers['year'] >= start_year) & (papers['year'] <= end_year)]
                st.caption(f"Found {len(filtered_papers)} papers in range.")
                db.save_publications(filtered_papers, auth['s2_id'])
        st.success("Sync Complete!")

with tabs[1]:
    st.subheader("Verification Queue")
    st.write("Automatically scan fetched papers for facility keywords/grants.")
    all_pubs = db.get_publications()
    queue = all_pubs[all_pubs['scan_notes'] == 'Not Scanned']
    st.write(f"Papers awaiting scan: {len(queue)}")
    
    if st.button("Scan All Pending Papers"):
        keywords_df = db.get_keywords()
        progress = st.progress(0)
        for idx, (_, pub) in enumerate(queue.iterrows()):
            found, kws, snippet, note = fetcher.verify_acknowledgment(pub['paper_id'], keywords_df)
            db.update_mention_status(pub['paper_id'], 1 if found else 0, snippet, note)
            progress.progress((idx + 1) / len(queue))
        st.success("Scan Complete!")
        st.rerun()

    # Display papers found by the scan
    found_pubs = all_pubs[all_pubs['facility_mentioned'] == 1]
    if not found_pubs.empty:
        st.write("### Potential Citations Identified")
        for _, row in found_pubs.iterrows():
            with st.expander(f"{row['title']} ({row['year']})"):
                st.write(f"**Snippet:** {row['mention_snippet']}")
                st.write(f"**Journal:** {row['journal']}")
                if st.button("Confirm This Citation", key=f"conf_pub_{row['paper_id']}"):
                    db.update_mention_status(row['paper_id'], 1, row['mention_snippet'], "Manually Verified")
                    st.success("Confirmed!")

with tabs[2]:
    st.subheader("Confirmed Facility Publications")
    confirmed = db.get_publications()
    confirmed = confirmed[confirmed['facility_mentioned'] == 1]
    if not confirmed.empty:
        st.dataframe(confirmed[['title', 'journal', 'year', 'citation_count', 'url']], use_container_width=True)
        if st.button("Export to CSV"):
            csv = confirmed.to_csv(index=False).encode('utf-8')
            st.download_button("Download Database", csv, "EMC_Confirmed_Citations.csv", "text/csv")
    else:
        st.info("No confirmed papers in database yet.")

with tabs[3]:
    st.subheader("Manual PDF Entry")
    with st.form("manual_form"):
        m_pi = st.selectbox("PI", authors['name'].tolist() if not authors.empty else ["N/A"])
        m_title = st.text_input("Title")
        m_url = st.text_input("DOI or URL")
        m_ack = st.text_area("Copy-paste Acknowledgment text here")
        if st.form_submit_button("Manually Add Citation"):
            aid = authors[authors['name'] == m_pi]['s2_id'].values[0] if not authors.empty else "manual"
            dummy_df = pd.DataFrame([{"paper_id": "m_" + str(time.time()), "title": m_title, "url": m_url, "year": 2026, "journal": "Manual", "citation_count": 0}])
            db.save_publications(dummy_df, aid)
            db.update_mention_status(dummy_df['paper_id'].values[0], 1, m_ack, "Manual Entry")
            st.success("Saved!")
