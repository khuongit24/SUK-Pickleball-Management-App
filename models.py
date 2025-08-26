from __future__ import annotations
from dataclasses import dataclass

@dataclass
class DailyRecord:
    ngay: str
    san: str
    khung_gio: str
    gia_vnd: int
    loai: str = ""
    nguoi: str = ""
    row_index: int | None = None
    # record_id (additive, optional) – không bắt buộc cho các bản ghi cũ, dùng để định danh ổn định
    record_id: str | None = None

@dataclass
class MonthlyStat:
    thang: str
    tong_doanh_thu_vnd: int
    chi_phi_tru_hao_vnd: int
    loi_nhuan_vnd: int
    tu_tinh_tu_ngay: bool
