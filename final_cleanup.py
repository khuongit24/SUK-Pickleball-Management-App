#!/usr/bin/env python3
"""
SUK PICKLEBALL - FINAL CLEANUP SCRIPT
Rà soát và xóa tất cả files thừa sau khi chuyển đổi CSV
"""

import os
import shutil
import json
from datetime import datetime

def main():
    print("🧹 SUK PICKLEBALL - FINAL CLEANUP")
    print("=" * 50)
    
    # Files cần giữ lại (core application)
    essential_files = {
        'main.py',           # Core application
        'utils.py',          # Core utilities  
        'models.py',         # Data models
        'requirements.txt',  # Dependencies
        'icon_suk.ico',     # Application icon
        'README.md',        # Documentation
        # CSV data files
        'daily_records.csv',
        'monthly_stats.csv', 
        'monthly_subscriptions.csv',
        'profit_shares.csv',
        'water_items.csv',
        'water_sales.csv'
    }
    
    # Directories cần giữ lại
    essential_dirs = {
        'config',           # Config directory
        'logs',            # Log directory  
        'backups'          # Backup directory
    }
    
    # Files và directories cần xóa
    cleanup_targets = []
    
    # 1. Scan root directory
    print("\n📂 Scanning root directory...")
    for item in os.listdir('.'):
        if os.path.isfile(item):
            if item not in essential_files:
                cleanup_targets.append(('file', item))
                print(f"   🗑️  {item}")
        elif os.path.isdir(item):
            # Các thư mục cần xóa hoàn toàn
            if item.startswith('backup_') or item in [
                '__pycache__', '.pytest_cache', 'build', 'dist',
                '.venv', 'python', 'suk_pickleball'
            ]:
                cleanup_targets.append(('dir', item))
                print(f"   📁🗑️  {item}/")
    
    # 2. Cleanup __pycache__ if exists
    if os.path.exists('__pycache__'):
        print(f"\n🔍 Found __pycache__ directory")
        for pyc_file in os.listdir('__pycache__'):
            print(f"   🗑️  __pycache__/{pyc_file}")
    
    # 3. Cleanup config directory
    print(f"\n🔍 Scanning config directory...")
    if os.path.exists('config'):
        for item in os.listdir('config'):
            if item != 'app_config.json':  # Chỉ giữ file config chính
                cleanup_targets.append(('file', f'config/{item}'))
                print(f"   🗑️  config/{item}")
    
    # Summary
    print(f"\n📊 CLEANUP SUMMARY:")
    print(f"   Files to delete: {len([x for x in cleanup_targets if x[0] == 'file'])}")
    print(f"   Directories to delete: {len([x for x in cleanup_targets if x[0] == 'dir'])}")
    print(f"   Total items: {len(cleanup_targets)}")
    
    if not cleanup_targets:
        print("✅ No unnecessary files found - workspace is already clean!")
        return
    
    # Confirmation
    print(f"\n⚠️  WARNING: This will delete {len(cleanup_targets)} items!")
    response = input("Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ Cleanup cancelled")
        return
    
    # Execute cleanup
    print(f"\n🧹 Executing cleanup...")
    deleted_count = 0
    
    for item_type, item_path in cleanup_targets:
        try:
            if item_type == 'file':
                if os.path.exists(item_path):
                    os.remove(item_path)
                    print(f"   ✅ Deleted file: {item_path}")
                    deleted_count += 1
            elif item_type == 'dir':
                if os.path.exists(item_path):
                    shutil.rmtree(item_path)
                    print(f"   ✅ Deleted directory: {item_path}/")
                    deleted_count += 1
        except Exception as e:
            print(f"   ❌ Error deleting {item_path}: {e}")
    
    # Final verification
    print(f"\n🔍 Post-cleanup verification...")
    remaining_files = []
    remaining_dirs = []
    
    for item in os.listdir('.'):
        if os.path.isfile(item):
            remaining_files.append(item)
        elif os.path.isdir(item):
            remaining_dirs.append(item)
    
    print(f"\n📋 FINAL WORKSPACE STATE:")
    print(f"   Essential files remaining: {len([f for f in remaining_files if f in essential_files])}")
    print(f"   Essential dirs remaining: {len([d for d in remaining_dirs if d in essential_dirs])}")
    print(f"   Extra files remaining: {len([f for f in remaining_files if f not in essential_files])}")
    print(f"   Extra dirs remaining: {len([d for d in remaining_dirs if d not in essential_dirs and not d.startswith('backup')])}")
    
    # List remaining files
    print(f"\n📄 REMAINING FILES:")
    for file in sorted(remaining_files):
        status = "✅" if file in essential_files else "❓"
        print(f"   {status} {file}")
    
    print(f"\n📁 REMAINING DIRECTORIES:")
    for dir in sorted(remaining_dirs):
        if dir in essential_dirs:
            status = "✅"
        elif dir.startswith('backup'):
            status = "💾"
        else:
            status = "❓"
        print(f"   {status} {dir}/")
    
    # Generate cleanup report
    report = {
        'cleanup_date': datetime.now().isoformat(),
        'deleted_items': deleted_count,
        'remaining_files': remaining_files,
        'remaining_dirs': remaining_dirs,
        'essential_files_status': {f: f in remaining_files for f in essential_files},
        'workspace_status': 'clean' if len([f for f in remaining_files if f not in essential_files]) == 0 else 'needs_review'
    }
    
    with open('final_cleanup_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 CLEANUP COMPLETED!")
    print(f"   Items deleted: {deleted_count}")
    print(f"   Report saved: final_cleanup_report.json")
    print(f"   Workspace status: {report['workspace_status'].upper()}")

if __name__ == "__main__":
    main()
