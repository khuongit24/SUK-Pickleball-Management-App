"""Centralized pricing constants & helpers.
Không thay đổi logic gốc: chỉ gom hằng số để tránh lệch giữa UI và utils.
Nếu muốn chỉnh giá giờ hoặc phụ thu đèn – sửa tại đây để toàn app đồng bộ.
"""
from __future__ import annotations

# Giá theo loại hoạt động (Chơi / Tập)
ACTIVITY_RATES = {
    'Chơi': 100_000,
    'Tập': 60_000,
}

# Phụ thu đèn mỗi giờ (áp dụng khi khung giờ thuộc off-hour logic tại UI)
LIGHT_SURCHARGE = 20_000

def get_hourly_base(loai: str) -> int:
    return ACTIVITY_RATES.get(loai, 0)

def compute_slot_price(loai: str, start_hour: int, end_hour: int, use_light: bool) -> int:
    if end_hour <= start_hour:
        return 0
    base = get_hourly_base(loai)
    per_hour = base + (LIGHT_SURCHARGE if use_light else 0)
    return per_hour * (end_hour - start_hour)

__all__ = [
    'ACTIVITY_RATES', 'LIGHT_SURCHARGE', 'get_hourly_base', 'compute_slot_price'
]
