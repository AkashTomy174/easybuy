@echo off
echo ========================================
echo Git History Cleanup Script
echo ========================================
echo.
echo WARNING: This will rewrite Git history!
echo Make sure you have a backup before proceeding.
echo.
pause

echo.
echo Step 1: Creating backup...
cd ..
if exist project-backup (
    echo Backup already exists. Skipping...
) else (
    xcopy project project-backup /E /I /H /Y
    echo Backup created at: project-backup
)
cd project

echo.
echo Step 2: Removing documentation files from history...

git filter-branch --force --index-filter ^
"git rm --cached --ignore-unmatch ACTION_PLAN_NOW.md AUTOCOMPLETE_IMPLEMENTATION.md FILTERING_ENHANCEMENT.md FIXES_SUMMARY.md PLATFORM_COMPLETION_CHECKLIST.md PROJECT_IMPROVEMENTS.md REVIEW_ENHANCEMENTS_COMPLETE.md REVIEW_ENHANCEMENTS.md REVIEW_SYSTEM_FIXES.md SETUP_COMPLETE.md TROUBLESHOOT_SHIPPED.md WHATSAPP_IMPLEMENTATION_SUMMARY.md WHATSAPP_INTEGRATION_GUIDE.md WHATSAPP_QUICK_START.md WHATSAPP_README.md DJANGO_ORM_STUDY_GUIDE.md" ^
--prune-empty --tag-name-filter cat -- --all

echo.
echo Step 3: Removing test files from history...

git filter-branch --force --index-filter ^
"git rm --cached --ignore-unmatch test_direct.py test_direct_status_change.py test_order_items.py test_order_notification.py test_settings.py test_shipped.py test_simple.py test_whatsapp.py check_order_owner.py create_test_order.py reset_order_to_pending.py populate_db.py main.py status_change_log.txt" ^
--prune-empty --tag-name-filter cat -- --all

echo.
echo Step 4: Cleaning up refs...
git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo.
echo ========================================
echo Cleanup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Verify the changes: git log --oneline
echo 2. If you have a remote repository, force push:
echo    git push origin --force --all
echo    git push origin --force --tags
echo.
echo WARNING: After force push, all collaborators must re-clone!
echo ========================================
pause
