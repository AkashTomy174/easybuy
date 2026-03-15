import subprocess
import os
import shutil
from pathlib import Path

print("=" * 60)
print("Git History Cleanup Script")
print("=" * 60)
print("\nWARNING: This will rewrite Git history!")
print("Make sure you understand the consequences before proceeding.\n")

response = input("Do you want to continue? (yes/no): ").lower()
if response != 'yes':
    print("Aborted.")
    exit()

# Files to remove from history
doc_files = [
    "ACTION_PLAN_NOW.md",
    "AUTOCOMPLETE_IMPLEMENTATION.md",
    "FILTERING_ENHANCEMENT.md",
    "FIXES_SUMMARY.md",
    "PLATFORM_COMPLETION_CHECKLIST.md",
    "PROJECT_IMPROVEMENTS.md",
    "REVIEW_ENHANCEMENTS_COMPLETE.md",
    "REVIEW_ENHANCEMENTS.md",
    "REVIEW_SYSTEM_FIXES.md",
    "SETUP_COMPLETE.md",
    "TROUBLESHOOT_SHIPPED.md",
    "WHATSAPP_IMPLEMENTATION_SUMMARY.md",
    "WHATSAPP_INTEGRATION_GUIDE.md",
    "WHATSAPP_QUICK_START.md",
    "WHATSAPP_README.md",
    "DJANGO_ORM_STUDY_GUIDE.md",
]

test_files = [
    "test_direct.py",
    "test_direct_status_change.py",
    "test_order_items.py",
    "test_order_notification.py",
    "test_settings.py",
    "test_shipped.py",
    "test_simple.py",
    "test_whatsapp.py",
    "check_order_owner.py",
    "create_test_order.py",
    "reset_order_to_pending.py",
    "populate_db.py",
    "main.py",
    "status_change_log.txt",
]

all_files = doc_files + test_files

print("\n" + "=" * 60)
print("Step 1: Creating backup...")
print("=" * 60)

backup_path = Path("..") / "project-backup"
if backup_path.exists():
    print("Backup already exists. Skipping...")
else:
    try:
        shutil.copytree(".", backup_path, ignore=shutil.ignore_patterns('.git'))
        print(f"✓ Backup created at: {backup_path.absolute()}")
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        exit(1)

print("\n" + "=" * 60)
print("Step 2: Removing files from Git history...")
print("=" * 60)

# Create filter-branch command
files_str = " ".join(all_files)
filter_cmd = f'git filter-branch --force --index-filter "git rm --cached --ignore-unmatch {files_str}" --prune-empty --tag-name-filter cat -- --all'

try:
    print("\nRunning git filter-branch (this may take a while)...")
    result = subprocess.run(filter_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Files removed from history")
    else:
        print(f"✗ Error: {result.stderr}")
        exit(1)
except Exception as e:
    print(f"✗ Error running filter-branch: {e}")
    exit(1)

print("\n" + "=" * 60)
print("Step 3: Cleaning up refs and garbage collection...")
print("=" * 60)

commands = [
    'git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin',
    'git reflog expire --expire=now --all',
    'git gc --prune=now --aggressive',
]

for cmd in commands:
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
        print(f"✓ {cmd.split()[1]} completed")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error running {cmd}: {e}")

print("\n" + "=" * 60)
print("Cleanup Complete!")
print("=" * 60)

print("\n📊 Summary:")
print(f"  - Removed {len(all_files)} files from Git history")
print(f"  - Backup saved at: {backup_path.absolute()}")

print("\n🚀 Next Steps:")
print("  1. Verify changes: git log --oneline --all")
print("  2. Check repository size: git count-objects -vH")
print("  3. If you have a remote repository:")
print("     git remote add origin <your-repo-url>  (if not added)")
print("     git push origin --force --all")
print("     git push origin --force --tags")

print("\n⚠️  IMPORTANT:")
print("  - All commit hashes have changed")
print("  - Collaborators must re-clone the repository")
print("  - Open pull requests will be affected")

print("\n" + "=" * 60)
