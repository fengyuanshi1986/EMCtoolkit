
import sys
import os
sys.path.append('/Users/fengyuanshi/publication_tracker')
from data_fetcher import DataFetcher
from database import PublicationDB

def test_paper_scan():
    fetcher = DataFetcher()
    db = PublicationDB()
    keywords = db.get_keywords()
    
    paper_id = "bdbca912f0e82eac9e0f1d4c5091423dfa7a33c2"
    doi = "10.1126/sciadv.adg5858"
    pdf_url = "https://www.science.org/doi/pdf/10.1126/sciadv.adg5858?download=true"
    
    print(f"Keywords: {keywords}")
    
    print("\n--- Testing Snippets ---")
    is_ack, snippet, reason = fetcher.verify_acknowledgment(paper_id, keywords)
    print(f"Ack: {is_ack}, Reason: {reason}")
    
    print("\n--- Testing PDF (Current Logic: Last 3 Pages) ---")
    is_ack, snippet, reason = fetcher.verify_via_pdf(pdf_url, keywords)
    print(f"Ack: {is_ack}, Reason: {reason}")

    print("\n--- Testing Crossref ---")
    is_ack, snippet, reason = fetcher.verify_via_crossref(doi, keywords)
    print(f"Ack: {is_ack}, Reason: {reason}")

if __name__ == "__main__":
    test_paper_scan()
