import requests
import pandas as pd
import xml.etree.ElementTree as ET
import time
import fitz # PyMuPDF
from scholarly import scholarly
import io
import os
import random
import re
from bs4 import BeautifulSoup

class DataFetcher:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.s2_api_base = "https://api.semanticscholar.org/graph/v1"
        self.orcid_api_base = "https://pub.orcid.org/v3.0"
        self.crossref_api_base = "https://api.crossref.org/works/"
        
        self.browser_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.session = requests.Session()

    def set_api_key(self, api_key):
        self.api_key = api_key

    def _get_with_retry(self, url, headers=None, retries=3, delay=5):
        h = headers.copy() if headers else self.browser_headers.copy()
        if self.api_key:
            h['x-api-key'] = self.api_key

        response = None
        for i in range(retries):
            try:
                response = self.session.get(url, headers=h, timeout=25, allow_redirects=True)
                if response.status_code == 200:
                    return response
                if response.status_code == 429:
                    wait = delay * (i + 1) * 2
                    time.sleep(wait)
                    continue
                if response.status_code == 403:
                    time.sleep(delay * 2)
                    continue
                return response
            except Exception:
                time.sleep(delay)
        return response

    def _exact_match(self, text, keyword):
        """Ultra-strict matching ensuring keywords are standalone tokens."""
        # Ensure keyword is not surrounded by alphanumeric characters or common delimiters like dashes
        # Regex explanation: 
        # (?<![a-zA-Z0-9\-])  -> No alphanumeric or dash before
        # (?![a-zA-Z0-9\-])   -> No alphanumeric or dash after
        pattern = r'(?<![a-zA-Z0-9\-])' + re.escape(keyword.lower()) + r'(?![a-zA-Z0-9\-])'
        match = re.search(pattern, text.lower())
        if match:
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 150)
            return True, text[start:end]
        return False, None

    def search_author(self, query):
        if not query or len(query.strip()) < 3:
            return "Query too short"
        url = f"{self.s2_api_base}/author/search?query={query}&fields=name,hIndex,citationCount,affiliations"
        response = self._get_with_retry(url)
        if response and response.status_code == 200:
            return response.json().get('data', [])
        if response is None: return "Connection Timeout"
        return f"Error {response.status_code}"

    def fetch_author_by_orcid(self, orcid_id):
        url = f"{self.s2_api_base}/author/ORCID:{orcid_id}?fields=authorId,name"
        response = self._get_with_retry(url)
        return response.json() if response and response.status_code == 200 else None

    def fetch_semantic_scholar_data(self, author_id):
        url = f"{self.s2_api_base}/author/{author_id}?fields=name,hIndex,citationCount,papers.title,papers.year,papers.citationCount,papers.externalIds,papers.venue,papers.journal,papers.openAccessPdf,papers.publicationTypes"
        response = self._get_with_retry(url)
        if response and response.status_code == 200:
            data = response.json()
            papers = data.get('papers', [])
            processed_papers = []
            for p in papers:
                if not p: continue
                ext = p.get('externalIds') or {}
                oa = p.get('openAccessPdf') or {}
                journal_info = p.get('journal') or {}
                venue = (p.get('venue') or journal_info.get('name') or '').lower()
                p_types = p.get('publicationTypes', []) or []
                pub_type = "Journal Article"
                if "conference" in [t.lower() for t in p_types] or "microscopy and microanalysis" in venue or "ecs meeting abstracts" in venue: 
                    pub_type = "Conference Paper"
                elif "Review" in p_types: pub_type = "Review"
                processed_papers.append({
                    'paper_id': p.get('paperId'),
                    'doi': ext.get('DOI'),
                    'title': p.get('title'),
                    'year': p.get('year'),
                    'journal': p.get('venue') or journal_info.get('name') or 'Unknown',
                    'citation_count': p.get('citationCount'),
                    'url': f"https://doi.org/{ext.get('DOI')}" if ext.get('DOI') else "",
                    'oa_pdf_url': oa.get('url') if oa else None,
                    'scan_notes': 'Not Scanned',
                    'pub_type': pub_type
                })
            affiliations = data.get('affiliations', [])
            primary_aff = affiliations[0] if affiliations else None
            return pd.DataFrame(processed_papers), {
                'name': data.get('name'), 
                'h_index': data.get('hIndex'), 
                'total_citations': data.get('citationCount'),
                'affiliation': primary_aff
            }
        return "RATE_LIMIT" if response and response.status_code == 429 else "ERROR", {}

    def verify_acknowledgment(self, paper_id, keywords_df):
        url = f"{self.s2_api_base}/paper/{paper_id}/snippets"
        response = self._get_with_retry(url)
        found_kws = []
        if response and response.status_code == 200:
            snippets = response.json().get('data', []) or []
            for s in snippets:
                text = s.get('text', '')
                for _, kw_row in keywords_df.iterrows():
                    kw = kw_row['keyword']
                    found, excerpt = self._exact_match(text, kw)
                    if found:
                        found_kws.append(kw)
            if found_kws:
                return True, list(set(found_kws)), excerpt, f"Found in Snippets"
        return False, [], None, "Keywords not found in snippets"

    def verify_via_web(self, url, keywords_df):
        try:
            response = self.session.get(url, headers=self.browser_headers, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                ack_found = False
                scan_text = ""
                for heading in soup.find_all(['h2', 'h3', 'h4', 'div']):
                    h_text = heading.get_text().lower()
                    if 'acknowledg' in h_text or 'funding' in h_text or 'support' in h_text:
                        scan_text += heading.get_text() + " "
                        for sibling in heading.find_next_siblings():
                            if sibling.name in ['h1', 'h2', 'h3']: break
                            scan_text += sibling.get_text() + " "
                        ack_found = True
                
                if not ack_found:
                    for tag in soup(['header', 'nav', 'footer', 'script', 'style']):
                        tag.decompose()
                    scan_text = soup.get_text()

                found_kws = []
                excerpt = None
                for _, kw_row in keywords_df.iterrows():
                    kw = kw_row['keyword']
                    found, ex = self._exact_match(scan_text, kw)
                    if found:
                        found_kws.append(kw)
                        excerpt = ex
                
                if found_kws:
                    source = "Webpage (Ack Section)" if ack_found else "Webpage (Full Scan)"
                    return True, list(set(found_kws)), excerpt, f"Found via {source}"
                
                return False, [], None, "Webpage reached but keywords not found"
            return False, [], None, f"Web Scan failed ({response.status_code})"
        except Exception: return False, [], None, "Web access error"

    def verify_via_pdf(self, pdf_url, keywords_df):
        try:
            response = self.session.get(pdf_url, headers=self.browser_headers, timeout=30)
            if response.status_code == 200:
                return self.scan_pdf_content(response.content, keywords_df)
            return False, [], None, "PDF blocked"
        except Exception: return False, [], None, "PDF error"

    def scan_pdf_content(self, pdf_bytes, keywords_df):
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                text = ""
                for page in doc: text += page.get_text() + " "
                found_kws = []
                excerpt = None
                for _, kw_row in keywords_df.iterrows():
                    kw = kw_row['keyword']
                    found, ex = self._exact_match(text, kw)
                    if found:
                        found_kws.append(kw)
                        excerpt = ex
                if found_kws:
                    return True, list(set(found_kws)), excerpt, f"Found via PDF"
            return False, [], None, "Keywords not found in PDF"
        except Exception as e: return False, [], None, str(e)

    def verify_via_crossref(self, doi, keywords_df):
        try:
            url = f"{self.crossref_api_base}{doi}"
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json().get('message', {})
                text = str(data.get('funder', [])) + " " + str(data.get('abstract', ''))
                found_kws = []
                excerpt = None
                for _, kw_row in keywords_df.iterrows():
                    kw = kw_row['keyword']
                    found, ex = self._exact_match(text, kw)
                    if found:
                        found_kws.append(kw)
                        excerpt = ex
                if found_kws:
                    return True, list(set(found_kws)), excerpt, "Found via Crossref"
        except Exception: pass
        return False, [], None, "Not found in Crossref"

    def find_mentions_in_bulk(self, author_name, keywords_df):
        mentioned_ids = set()
        clean_name = author_name.replace('"', '')
        # Only search for Specific or General keywords to find candidates
        # Context keywords like "TEM" are too common on their own
        target_kws = keywords_df[keywords_df['type'].isin(['Specific', 'General'])]['keyword'].tolist()
        
        for kw in target_kws:
            query = f'{clean_name} "{kw}"'
            url = f"{self.s2_api_base}/paper/search?query={query}&limit=100&fields=paperId"
            response = self._get_with_retry(url)
            if response and response.status_code == 200:
                for p in response.json().get('data', []): mentioned_ids.add(p['paperId'])
            time.sleep(1)
        return mentioned_ids

    def fetch_arxiv_data(self, author_name):
        try:
            url = f"http://export.arxiv.org/api/query?search_query=au:\"{author_name}\"&max_results=10"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                papers = []
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('atom:entry', ns):
                    papers.append({
                        'title': entry.find('atom:title', ns).text.strip(),
                        'year': entry.find('atom:published', ns).text[:4],
                        'journal': 'arXiv Pre-print',
                        'url': entry.find('atom:id', ns).text
                    })
                return pd.DataFrame(papers)
        except Exception: pass
        return pd.DataFrame()
