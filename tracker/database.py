import sqlite3
import pandas as pd
from datetime import datetime
import os

class PublicationDB:
    def __init__(self, db_path=None, config_db_path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = db_path if db_path else os.path.join(base_dir, 'publications.db')
        self.config_db_path = config_db_path if config_db_path else os.path.join(base_dir, 'config.db')
        self.init_db()

    def init_db(self):
        # 1. Initialize main data DB
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS authors (
                    s2_id TEXT PRIMARY KEY,
                    name TEXT,
                    affiliation TEXT,
                    last_sync DATETIME
                )
            ''')
            # Ensure the authors table has the affiliation column
            try:
                cursor.execute('ALTER TABLE authors ADD COLUMN affiliation TEXT')
            except: pass # Column already exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS publications (
                    paper_id TEXT PRIMARY KEY,
                    author_id TEXT,
                    doi TEXT,
                    title TEXT,
                    year INTEGER,
                    journal TEXT,
                    citation_count INTEGER,
                    url TEXT,
                    oa_pdf_url TEXT,
                    facility_mentioned BOOLEAN DEFAULT 0,
                    mention_snippet TEXT,
                    scan_notes TEXT DEFAULT 'Not Scanned',
                    pub_type TEXT,
                    FOREIGN KEY(author_id) REFERENCES authors(s2_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS citation_history (
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    author_id TEXT,
                    total_citations INTEGER,
                    FOREIGN KEY(author_id) REFERENCES authors(s2_id)
                )
            ''')
            conn.commit()

        # 2. Initialize separate Config DB (Persistence during Resets)
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    s2_id TEXT PRIMARY KEY,
                    name TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS facility_keywords (
                    keyword TEXT PRIMARY KEY,
                    type TEXT DEFAULT 'Specific'
                )
            ''')
            try:
                cursor.execute('ALTER TABLE facility_keywords ADD COLUMN type TEXT DEFAULT "Specific"')
            except: pass
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_ilab_names (
                    name TEXT PRIMARY KEY,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discovered_pis (
                    name TEXT PRIMARY KEY,
                    institution TEXT
                )
            ''')
            conn.commit()

    def reset_main_db(self):
        """Wipes only the publication data, keeping keywords and bookmarks."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.init_db()

    # --- CONFIG OPERATIONS (on config.db) ---
    def set_setting(self, key, value):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
            conn.commit()

    def get_setting(self, key, default=None):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def add_favorite(self, s2_id, name):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO favorites (s2_id, name) VALUES (?, ?)', (s2_id, name))
            conn.commit()

    def remove_favorite(self, s2_id):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM favorites WHERE s2_id = ?', (s2_id,))
            conn.commit()

    def get_favorites(self):
        with sqlite3.connect(self.config_db_path) as conn:
            return pd.read_sql('SELECT * FROM favorites', conn)

    def add_keyword(self, keyword, k_type='Specific'):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO facility_keywords (keyword, type) VALUES (?, ?)', (keyword, k_type))
            conn.commit()

    def get_keywords(self):
        with sqlite3.connect(self.config_db_path) as conn:
            return pd.read_sql('SELECT * FROM facility_keywords', conn)

    def delete_keyword(self, keyword):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM facility_keywords WHERE keyword = ?', (keyword,))
            conn.commit()

    def mark_pi_processed(self, name, status='processed'):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO processed_ilab_names (name, status) VALUES (?, ?)', (name, status))
            conn.commit()

    def get_processed_pi_names(self):
        with sqlite3.connect(self.config_db_path) as conn:
            df = pd.read_sql('SELECT name FROM processed_ilab_names', conn)
            return df['name'].tolist()

    def add_discovered_pis(self, pi_dict):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            for name, inst in pi_dict.items():
                cursor.execute('INSERT OR REPLACE INTO discovered_pis (name, institution) VALUES (?, ?)', (name, inst))
            conn.commit()

    def get_all_discovered_pis(self):
        with sqlite3.connect(self.config_db_path) as conn:
            return pd.read_sql('SELECT * FROM discovered_pis', conn)

    def clear_discovered_pis(self):
        with sqlite3.connect(self.config_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM discovered_pis')
            cursor.execute('DELETE FROM processed_ilab_names')
            conn.commit()

    def get_processed_pi_names(self):
        with sqlite3.connect(self.config_db_path) as conn:
            df = pd.read_sql('SELECT name FROM processed_ilab_names', conn)
            return df['name'].tolist()

    # --- DATA OPERATIONS (on publications.db) ---
    def add_author(self, s2_id, name, affiliation=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO authors (s2_id, name, affiliation) VALUES (?, ?, ?)', (s2_id, name, affiliation))
            conn.commit()
            conn.commit()

    def delete_author(self, s2_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM citation_history WHERE author_id = ?', (s2_id,))
            cursor.execute('DELETE FROM publications WHERE author_id = ?', (s2_id,))
            cursor.execute('DELETE FROM authors WHERE s2_id = ?', (s2_id,))
            conn.commit()

    def save_publications(self, papers_df, author_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Ensure the table has the last_scan_check column
            try:
                cursor.execute('ALTER TABLE publications ADD COLUMN last_scan_check DATETIME')
            except: pass # Column already exists
            
            for _, row in papers_df.iterrows():
                cursor.execute('''
                    INSERT INTO publications 
                    (paper_id, author_id, doi, title, year, journal, citation_count, url, oa_pdf_url, scan_notes, pub_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(paper_id) DO UPDATE SET
                        citation_count = excluded.citation_count,
                        oa_pdf_url = excluded.oa_pdf_url,
                        pub_type = excluded.pub_type
                ''', (row['paper_id'], author_id, row.get('doi'), row['title'], row['year'], row['journal'], row['citation_count'], row['url'], row.get('oa_pdf_url'), row.get('scan_notes', 'Not Scanned'), row.get('pub_type')))
            conn.commit()

    def update_mention_status(self, paper_id, mentioned, snippet=None, notes=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE publications SET 
                    facility_mentioned = ?, 
                    mention_snippet = ?, 
                    scan_notes = ?,
                    last_scan_check = CURRENT_TIMESTAMP 
                WHERE paper_id = ?
            ''', (mentioned, snippet, notes, paper_id))
            conn.commit()

    def delete_publication(self, paper_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM publications WHERE paper_id = ?', (paper_id,))
            conn.commit()

    def get_authors(self):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql('SELECT * FROM authors', conn)

    def record_citation_total(self, author_id, total_citations):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO citation_history (author_id, total_citations) VALUES (?, ?)', (author_id, total_citations))
            conn.commit()

    def get_publications(self, author_id=None):
        with sqlite3.connect(self.db_path) as conn:
            if author_id:
                return pd.read_sql('SELECT * FROM publications WHERE author_id = ?', conn, params=(author_id,))
            return pd.read_sql('SELECT * FROM publications', conn)

    def get_citation_history(self, author_id):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql('SELECT * FROM citation_history WHERE author_id = ?', conn, params=(author_id,))
