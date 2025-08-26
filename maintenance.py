"""Maintenance & Integrity Utilities (additive, non-invasive)

Mục tiêu:
- Cung cấp script dòng lệnh hỗ trợ kiểm tra nhanh tính toàn vẹn dữ liệu CSV
- Không thay đổi hoặc ghi dữ liệu (read-only trừ khi người dùng gọi chức năng mở rộng thủ công trong tương lai)
- Tách biệt khỏi GUI để có thể chạy theo lịch (Task Scheduler / cron) hoặc thủ công.

Sử dụng:
    python maintenance.py integrity
    python maintenance.py month-summary 2025-08
    python maintenance.py list-months

Tất cả hàm chỉ đọc dữ liệu và in báo cáo ra stdout.
"""
from __future__ import annotations
import sys
from typing import List
from datetime import datetime

import utils  # reuse existing logic (cache + migration)


def cmd_integrity():
    """Chạy kiểm tra toàn vẹn và in báo cáo thân thiện."""
    info = utils.verify_data_integrity()
    print("=== INTEGRITY REPORT ===")
    print(f"Total daily records       : {info['total_records']}")
    print(f"Overlap slot pairs         : {info['overlap_count']}")
    if info['overlap_count']:
        print("  Sample (tối đa 5):")
        for p in info['overlap_pairs'][:5]:
            print(f"   - {p['ngay']} {p['san']} {p['slot1']} vs {p['slot2']}")
    print(f"Has record_id header       : {info['has_record_id_header']}")
    if info['has_record_id_header']:
        print(f"Missing record_id rows     : {info['missing_id_count']}")
    # Thống kê nhanh theo ngày cao nhất
    recs = utils.get_daily_records()
    by_day = {}
    for r in recs:
        by_day.setdefault(r.ngay, 0)
        by_day[r.ngay] += r.gia_vnd
    if by_day:
        top = sorted(by_day.items(), key=lambda x: x[1], reverse=True)[:5]
        print("Top ngày doanh thu (tối đa 5):")
        for d, v in top:
            print(f"  {d}: {v:,} VND".replace(',', '.'))
    print("=== END ===")


def _normalize_month_arg(month_arg: str) -> str:
    """Chấp nhận 'YYYY-MM' hoặc 'MM-YYYY' trả về dạng chuẩn 'YYYY-MM'."""
    month_arg = month_arg.strip()
    if len(month_arg) != 7:
        raise ValueError("Tháng phải dạng YYYY-MM hoặc MM-YYYY")
    if month_arg[2] == '-':  # MM-YYYY
        dt = datetime.strptime(month_arg, '%m-%Y')
        return dt.strftime('%Y-%m')
    # assume YYYY-MM
    datetime.strptime(month_arg + '-01', '%Y-%m-%d')
    return month_arg


def cmd_month_summary(month_arg: str):
    thang = _normalize_month_arg(month_arg)
    total = utils.compute_month_total(thang)
    subs = utils.compute_month_subscription_total(thang)
    water = utils.compute_month_water_sales_total(thang)
    # daily portion = total - subs - water
    daily_part = total - subs - water
    print(f"=== MONTH SUMMARY {thang} ===")
    print(f"Daily records total : {daily_part:,} VND".replace(',', '.'))
    print(f"Subscriptions total : {subs:,} VND".replace(',', '.'))
    print(f"Water sales total   : {water:,} VND".replace(',', '.'))
    print(f"------------------------------")
    print(f"GRAND TOTAL         : {total:,} VND".replace(',', '.'))
    print(f"(Giá trị trên phản ánh cùng công thức trong ứng dụng GUI, không đổi logic)")
    print("=== END ===")


def cmd_list_months():
    """Liệt kê các tháng có trong daily_records (có ít nhất 1 dòng)."""
    recs = utils.get_daily_records()
    months = set(r.ngay[:7] for r in recs if len(r.ngay) >= 7)
    for m in sorted(months):
        print(m)
    if not months:
        print("(Chưa có dữ liệu)")


def main(argv: List[str]):
    if len(argv) < 2 or argv[1] in ('-h', '--help', 'help'):  # help
        print("Maintenance commands:")
        print("  integrity                 - Báo cáo toàn vẹn dữ liệu")
        print("  month-summary <THANG>     - Tổng hợp một tháng (YYYY-MM hoặc MM-YYYY)")
        print("  list-months               - Liệt kê các tháng có dữ liệu daily")
        print("Ví dụ: python maintenance.py month-summary 08-2025")
        return 0
    cmd = argv[1]
    try:
        if cmd == 'integrity':
            cmd_integrity()
        elif cmd == 'month-summary':
            if len(argv) < 3:
                raise ValueError('Thiếu tham số tháng')
            cmd_month_summary(argv[2])
        elif cmd == 'list-months':
            cmd_list_months()
        else:
            raise ValueError(f'Unknown command: {cmd}')
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
