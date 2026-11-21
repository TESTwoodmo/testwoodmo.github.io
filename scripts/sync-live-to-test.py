#!/usr/bin/env python3
"""Manueller Stammdatenabgleich. Abhaengigkeit: psycopg 3. Keine Ausgabe von Daten."""
import os
import re
import sys

LIVE_REF = 'tulndunkpsynkbbebenf'
V2_REF = 'fsztsmnxbffanyfbytnr'
SOURCE_ROLE = 'woodmo_mirror_reader'
TARGET_ROLE = 'woodmo_mirror_writer'
CATALOG = 'public.pos_catalog_items'
STAFF = 'public.pos_staff_users'


def connect(ref, role, password):
    import psycopg

    return psycopg.connect(
        host=f'db.{ref}.supabase.co', port=5432, dbname='postgres', user=role,
        password=password, sslmode='verify-full', sslrootcert=os.environ['WOODMO_CA_FILE'],
        connect_timeout=10,
    )


def main():
    test_ref = os.environ.get('WOODMO_TEST_REF', '')
    if not re.fullmatch('[a-z0-9]{20}', test_ref) or test_ref in {LIVE_REF, V2_REF}:
        raise SystemExit('Abbruch: Ziel muss ein separates WOODMO-TEST-Projekt sein.')

    from psycopg.types.json import Jsonb

    source_password = os.environ['WOODMO_LIVE_READER_PASSWORD']
    target_password = os.environ['WOODMO_TEST_WRITER_PASSWORD']
    if not source_password or not target_password or source_password == target_password:
        raise SystemExit('Abbruch: Getrennte Zugangsdaten sind erforderlich.')

    with connect(LIVE_REF, SOURCE_ROLE, source_password) as live:
        live.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        role, read_only, can_write = live.execute("""
            SELECT current_user, current_setting('transaction_read_only'),
                   EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                           WHERE n.nspname IN ('public', 'auth', 'storage') AND c.relkind IN ('r','p')
                             AND has_table_privilege(c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE'))
        """).fetchone()
        if role != SOURCE_ROLE or read_only != 'on' or can_write:
            raise SystemExit('Abbruch: Live-Zugang ist nicht schreibgeschuetzt.')
        catalog = live.execute(f'SELECT kind,id,data,updated_at,deleted FROM {CATALOG}').fetchall()
        staff = live.execute(f'SELECT id,data,updated_at,deleted FROM {STAFF}').fetchall()
        if not catalog or not staff:
            raise SystemExit('Abbruch: Live-Stammdaten fehlen oder sind nicht lesbar.')

    with connect(test_ref, TARGET_ROLE, target_password) as test:
        role, marker = test.execute('SELECT current_user, project_ref FROM woodmo_test_guard.environment').fetchone()
        if role != TARGET_ROLE or marker != test_ref:
            raise SystemExit('Abbruch: Testdatenbank konnte nicht bestaetigt werden.')
        test.execute(f'LOCK TABLE {CATALOG}, {STAFF} IN SHARE ROW EXCLUSIVE MODE')
        test.execute(f'DELETE FROM {CATALOG}')
        test.execute(f'DELETE FROM {STAFF}')
        with test.cursor() as cursor:
            cursor.executemany(f'INSERT INTO {CATALOG} (kind,id,data,updated_at,deleted) VALUES (%s,%s,%s,%s,%s)',
                               [(kind, key, Jsonb(data), stamp, deleted) for kind,key,data,stamp,deleted in catalog])
            cursor.executemany(f'INSERT INTO {STAFF} (id,data,updated_at,deleted) VALUES (%s,%s,%s,%s)',
                               [(key, Jsonb(data), stamp, deleted) for key,data,stamp,deleted in staff])
    print(f'WOODMO TEST: {len(catalog)} Katalog- und {len(staff)} Mitarbeitereintraege uebernommen.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sys.exit(f'Abgleich fehlgeschlagen ({type(error).__name__}). Keine Datenausgabe.')
