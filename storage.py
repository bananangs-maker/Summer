"""Supabase Postgres in production; SQLite only for local development."""
import json
import os
import sqlite3
from pathlib import Path
from contextlib import closing

EMPTY = {'profile': None, 'logs': [], 'routines': {}}

class Conflict(Exception):
    pass

class Store:
    def __init__(self):
        self.url = os.environ.get('DATABASE_URL', '').strip()
        # Never silently put production data on Render's ephemeral filesystem.
        if os.environ.get('RENDER') and not self.url:
            raise RuntimeError('Render requires DATABASE_URL. Set the Supabase Session pooler connection string.')
        self.path = Path(os.environ.get('DATA_DIR', Path(__file__).parent / 'data')) / 'motion.sqlite3'
        if not self.url:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        if self.url:
            import psycopg
            return psycopg.connect(self.url, sslmode='require', connect_timeout=15,
                                   prepare_threshold=None, options='-c statement_timeout=15000')
        return sqlite3.connect(self.path, timeout=15)

    def initialize(self):
        if self.url:
            with closing(self.connect()) as c, c:
                c.execute('CREATE SCHEMA IF NOT EXISTS motion_private')
                c.execute('REVOKE ALL ON SCHEMA motion_private FROM PUBLIC')
                c.execute('CREATE TABLE IF NOT EXISTS motion_private.state (id INTEGER PRIMARY KEY CHECK(id=1), revision BIGINT NOT NULL, payload JSONB NOT NULL)')
                c.execute('ALTER TABLE motion_private.state ENABLE ROW LEVEL SECURITY')
                c.execute('CREATE TABLE IF NOT EXISTS motion_private.weather_cache (id INTEGER PRIMARY KEY, payload JSONB NOT NULL)')
                c.execute('ALTER TABLE motion_private.weather_cache ENABLE ROW LEVEL SECURITY')
                c.execute('INSERT INTO motion_private.state (id, revision, payload) VALUES (1,0,%s::jsonb) ON CONFLICT (id) DO NOTHING', (json.dumps(EMPTY),))
        else:
            with closing(self.connect()) as c, c:
                c.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL)')
                c.execute('CREATE TABLE IF NOT EXISTS weather_cache (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
                c.execute('INSERT OR IGNORE INTO state VALUES (1,0,?)', (json.dumps(EMPTY),))

    def read(self):
        c = self.connect()
        try:
            row = c.execute('SELECT revision,payload FROM '+('motion_private.state' if self.url else 'state')+' WHERE id=1').fetchone()
            return row[0], row[1] if isinstance(row[1], dict) else json.loads(row[1])
        finally:
            c.close()

    def write(self, expected_revision, state):
        # Compare-and-swap is one atomic UPDATE. A second client cannot overwrite a newer revision.
        with closing(self.connect()) as c, c:
            if self.url:
                row = c.execute('UPDATE motion_private.state SET revision=revision+1,payload=%s::jsonb WHERE id=1 AND revision=%s RETURNING revision',
                                (json.dumps(state, ensure_ascii=False), expected_revision)).fetchone()
                if row is None:
                    raise Conflict()
                return row[0]
            else:
                result = c.execute('UPDATE state SET revision=revision+1,payload=? WHERE id=1 AND revision=?',
                                   (json.dumps(state, ensure_ascii=False), expected_revision))
                if result.rowcount != 1:
                    raise Conflict()
                return expected_revision + 1

    def weather_read(self):
        with closing(self.connect()) as c, c:
            row=c.execute('SELECT payload FROM '+('motion_private.weather_cache' if self.url else 'weather_cache')+' WHERE id=1').fetchone()
            return (row[0] if isinstance(row[0],dict) else json.loads(row[0])) if row else {}

    def weather_write(self,weather):
        with closing(self.connect()) as c, c:
            raw=json.dumps(weather)
            if self.url:
                c.execute('INSERT INTO motion_private.weather_cache VALUES (1,%s::jsonb) ON CONFLICT(id) DO UPDATE SET payload=EXCLUDED.payload',(raw,))
            else:
                c.execute('INSERT INTO weather_cache VALUES (1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(raw,))
