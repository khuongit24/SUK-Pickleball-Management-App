"""Simple smoke test (manual run) to validate core flows without changing app data semantics.
Run: python smoke_check.py
It will:
 1. Append a temp daily record.
 2. Update that record.
 3. Run integrity check.
 4. Undo last action (update isn't on stack; we test append/delete via manual delete + undo append restore pattern).
All created records are tagged with a unique marker in 'nguoi'.
"""
from datetime import datetime
import random
from utils import (
    append_daily_record, update_daily_record, delete_daily_record, get_daily_records,
    verify_data_integrity, to_iso_date, normalize_time_slot, parse_currency_any
)

MARK = f"_SMOKE_{int(datetime.now().timestamp())}_{random.randint(100,999)}"

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    slot = '5h-6h'
    price = 123000
    # 1. Append
    append_daily_record(today, 'Sân 1', slot, price, loai='Chơi', nguoi=MARK)
    print('[1] Append OK')
    # 2. Update (change price + type)
    new_price = price + 1000
    ok = update_daily_record(today, 'Sân 1', slot, price, today, 'Sân 1', slot, new_price, 'Chơi', MARK)
    print('[2] Update result:', ok)
    # 3. Integrity
    integ = verify_data_integrity()
    print('[3] Integrity:', integ)
    # 4. Clean up: delete the row we added (using new price)
    deleted = delete_daily_record(today, 'Sân 1', slot, new_price)
    print('[4] Cleanup delete:', deleted)
    # Show last 3 relevant records of today for manual eyeball
    recs = [r for r in get_daily_records(force_reload=True) if r.ngay == today][-3:]
    for r in recs:
        print('   REC:', r)
    print('Smoke check done.')

if __name__ == '__main__':
    main()
