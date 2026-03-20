#!/usr/bin/env python
import os
import django
import shutil
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easybuy.easybuy.settings')
django.setup()

from django.conf import settings

print('MEDIA_ROOT:', settings.MEDIA_ROOT)
media_root = Path(settings.MEDIA_ROOT)
source_dir = media_root / 'products' / 'variants' / 'products' / 'variants'
target_dir = media_root / 'products' / 'variants'

print(f'Source dir: {source_dir}')
print(f'Target dir: {target_dir}')

if source_dir.exists() and source_dir.is_dir():
    copied = 0
    for file_path in source_dir.rglob('*'):
        if file_path.is_file():
            rel_path = file_path.relative_to(source_dir)
            target_file = target_dir / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            if not target_file.exists() or file_path.stat().st_size != target_file.stat().st_size:
                shutil.copy2(file_path, target_file)
                print(f'Copied: {file_path.name} → {target_file}')
                copied += 1
            else:
                print(f'Skipped (exists): {file_path.name}')
    
    print(f'Total copied/updated: {copied}')
    
    # Optional: remove nested dir after copy
    # import shutil
    # shutil.rmtree(source_dir)
    # print('Removed nested source dir')
else:
    print('No nested source dir found')

print('Flatten complete. Run fix_image_paths.py next.')

