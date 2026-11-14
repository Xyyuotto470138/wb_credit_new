"""Pack the saved live demo case into the repository, and restore it on another machine.

The saved Keppel REIT case (sections drafted with the live model) lives in runtime/demo_live/case, which git ignores,
and its database records absolute file paths. This script makes it portable:

  .venv/bin/python scripts/demo/saved_case.py restore                  the case as first drafted
  .venv/bin/python scripts/demo/saved_case.py restore --after-update   the case after the new information update
  .venv/bin/python scripts/demo/saved_case.py restore --replace        replace a case that is already there (it is moved aside, not deleted)
  .venv/bin/python scripts/demo/saved_case.py pack [--after-update]    project owner only: refresh the packed copy from runtime/

A packed copy is the database (gzip) plus the few stored files that are not already in the repository. Source documents
are not stored twice: on restore they are copied from demo/ and templates/ and matched by their SHA-256.
Restoring makes no model call and needs no key. Everything in the case is SYNTHETIC DEMO DATA or saved public documents.
"""
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import gzip
import shutil
import sqlite3
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / 'runtime/demo_live/case'
PACKED = ROOT / 'demo/saved_cases'
MARK = '/runtime/demo_live/case/'  # stored paths are rewritten from here on
PATH_COLUMNS = [('document', 'storage_path'), ('template_version', 'storage_path')]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def repository_files():
    """Every source file the repository already holds, by content hash."""
    return {digest(f): f for base in ('demo', 'templates') for f in sorted((ROOT / base).rglob('*')) if f.is_file() and PACKED not in f.parents}


def pack(name, source):
    if not (source / 'wb_credit.sqlite').is_file():
        sys.exit(f'No case at {source.relative_to(ROOT)}')
    target = PACKED / name
    target.mkdir(parents=True, exist_ok=True)
    with open(source / 'wb_credit.sqlite', 'rb') as raw, gzip.GzipFile(target / 'wb_credit.sqlite.gz', 'wb', mtime=0) as out:
        shutil.copyfileobj(raw, out)
    held, kept = repository_files(), 0
    with tarfile.open(target / 'files.tar.gz', 'w:gz') as archive:
        for folder in ('blobs', 'templates'):
            for f in sorted((source / folder).rglob('*')):
                if f.is_file() and f.name not in held:  # not a copy of a repository file: stored with the case
                    archive.add(f, arcname=str(f.relative_to(source)))
                    kept += 1
    size = sum(f.stat().st_size for f in target.iterdir()) / 1e6
    print(f'packed {source.relative_to(ROOT)} into {target.relative_to(ROOT)}: {size:.1f} MB, {kept} stored files (exports are not packed)')


def restore(name, replace):
    packed = PACKED / name
    if not (packed / 'wb_credit.sqlite.gz').is_file():
        sys.exit(f'No packed case at {packed.relative_to(ROOT)}')
    if CASE.exists():
        if not replace:
            sys.exit(f'{CASE.relative_to(ROOT)} already exists. Add --replace to move it aside and restore the packed case.')
        aside = CASE.with_name(f'case_replaced_{datetime.now():%Y%m%d_%H%M%S}')
        CASE.rename(aside)
        print(f'existing case moved to {aside.relative_to(ROOT)}')
    CASE.mkdir(parents=True)
    with gzip.open(packed / 'wb_credit.sqlite.gz', 'rb') as raw, open(CASE / 'wb_credit.sqlite', 'wb') as out:
        shutil.copyfileobj(raw, out)
    with tarfile.open(packed / 'files.tar.gz') as archive:
        archive.extractall(CASE, filter='data')
    held = repository_files()
    db = sqlite3.connect(CASE / 'wb_credit.sqlite')
    # Stored paths point at the machine the case was made on. The path columns sit behind "immutable" triggers,
    # so those triggers are lifted for this one relocation and put back unchanged.
    tables = {table for table, _ in PATH_COLUMNS}
    triggers = [(n, sql) for n, t, sql in db.execute("select name, tbl_name, sql from sqlite_master where type='trigger'") if t in tables]
    for trigger, _ in triggers:
        db.execute(f'drop trigger "{trigger}"')
    copied = missing = 0
    for table, column in PATH_COLUMNS:
        for row_id, stored in db.execute(f'select id, "{column}" from "{table}"').fetchall():
            if MARK not in stored:
                continue
            target = CASE / stored.split(MARK, 1)[1]
            if not target.exists():
                source = held.get(target.name)
                if source:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    copied += 1
                else:
                    missing += 1
            db.execute(f'update "{table}" set "{column}" = ? where id = ?', (str(target), row_id))
    for _, sql in triggers:
        db.execute(sql)
    db.commit()
    db.close()
    if missing:
        sys.exit(f'{missing} stored files were not found in the repository. The case is incomplete; check that demo/ and templates/ are unchanged.')
    print(f'restored {packed.relative_to(ROOT)} to {CASE.relative_to(ROOT)} ({copied} source files copied from the repository)')
    print('open it with: scripts/demo/serve.sh --keppel')


if __name__ == '__main__':
    args = sys.argv[1:]
    name = 'keppel_after_update' if '--after-update' in args else 'keppel_live'
    if args[:1] == ['pack']:
        pack(name, CASE.with_name('case_after_update') if '--after-update' in args else CASE)
    elif args[:1] == ['restore']:
        restore(name, '--replace' in args)
    else:
        sys.exit(__doc__)
