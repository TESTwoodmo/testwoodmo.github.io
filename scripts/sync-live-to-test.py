#!/usr/bin/env python3
"""Stammdaten Live -> TEST. Python 3 und psycopg 3. Aufruf ohne --apply prüft nur."""
import argparse
import os
import re
import sys
from urllib.parse import unquote, urlsplit

LIVE_REF = 'tulndunkpsynkbbebenf'
LEGACY_REF = 'fsztsmnxbffanyfbytnr'
SOURCE_ROLE = 'woodmo_mirror_reader'
TARGET_ROLE = 'woodmo_mirror_writer'
IMAGE_PATH = '/storage/v1/object/public/article-images/'


def connect(ref, role, variable):
    import psycopg

    return psycopg.connect(
        host=f'db.{ref}.supabase.co', port=5432, dbname='postgres', user=role,
        password=os.environ[variable], sslmode='verify-full',
        sslrootcert=os.environ['WOODMO_CA_FILE'], connect_timeout=10,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    apply = parser.parse_args().apply
    target = os.environ.get('WOODMO_TEST_REF', '')
    if not re.fullmatch(r'[a-z0-9]{20}', target) or target in (LIVE_REF, LEGACY_REF):
        sys.exit('Abbruch: WOODMO_TEST_REF muss ein eigenes drittes Projekt sein.')

    from psycopg.types.json import Jsonb

    with connect(LIVE_REF, SOURCE_ROLE, 'WOODMO_LIVE_READER_PASSWORD') as live:
        live.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        role, mode, can_write = live.execute("""
            SELECT current_user, current_setting('transaction_read_only'),
                   EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                           WHERE n.nspname IN ('public','auth','storage') AND c.relkind IN ('r','p')
                             AND has_table_privilege(c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE'))
        """).fetchone()
        if role != SOURCE_ROLE or mode != 'on' or can_write:
            sys.exit('Abbruch: Live-Leserolle ist nicht schreibgeschützt.')
        catalog = live.execute('SELECT kind,id,data,updated_at,deleted FROM public.pos_catalog_items').fetchall()
        staff = live.execute("""
            SELECT id, data - ARRAY['passwordHash','passwordSalt','securityConfigured'], updated_at, deleted
            FROM public.pos_staff_users
        """).fetchall()
    if not catalog or not staff:
        sys.exit('Abbruch: Leerer Quellstand.')

    with connect(target, TARGET_ROLE, 'WOODMO_TEST_WRITER_PASSWORD') as test:
        identity = test.execute('SELECT current_user, project_ref FROM woodmo_test_guard.environment').fetchone()
        if identity != (TARGET_ROLE, target):
            sys.exit('Abbruch: Testprojekt konnte nicht bestätigt werden.')
        images = {row[0] for row in test.execute("SELECT name FROM storage.objects WHERE bucket_id='article-images'")}
        mapped = []
        for kind, key, data, stamp, deleted in catalog:
            url = urlsplit(data.get('imageUrl') or '')
            if url.netloc == f'{LIVE_REF}.supabase.co' and url.path.startswith(IMAGE_PATH):
                if not deleted and unquote(url.path[len(IMAGE_PATH):]) not in images:
                    sys.exit('Abbruch: Artikelbilder müssen zuerst im Testprojekt vorhanden sein.')
                data['imageUrl'] = url._replace(netloc=f'{target}.supabase.co').geturl()
            mapped.append((kind, key, Jsonb(data), stamp, deleted))
        if apply:
            with test.cursor() as cursor:
                cursor.executemany("""
                    INSERT INTO public.pos_catalog_items AS dest(kind,id,data,updated_at,deleted)
                    VALUES (%s,%s,%s,%s,%s) ON CONFLICT (kind,id) DO UPDATE SET
                      data=EXCLUDED.data, updated_at=greatest(EXCLUDED.updated_at,dest.updated_at+1), deleted=EXCLUDED.deleted
                """, mapped)
                cursor.executemany("""
                    INSERT INTO public.pos_staff_users AS dest(id,data,updated_at,deleted)
                    VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET
                      data=EXCLUDED.data || jsonb_build_object('passwordHash',dest.data->'passwordHash',
                        'passwordSalt',dest.data->'passwordSalt','securityConfigured',dest.data->'securityConfigured'),
                      updated_at=greatest(EXCLUDED.updated_at,dest.updated_at+1), deleted=EXCLUDED.deleted
                """, [(key, Jsonb(data), stamp, deleted) for key, data, stamp, deleted in staff])
    print(f'{len(catalog)} Katalog- und {len(staff)} Mitarbeitereinträge: ' + ('übernommen' if apply else 'geprüft'))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sys.exit(f'Abgleich fehlgeschlagen ({type(error).__name__}).')
