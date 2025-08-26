from __future__ import annotations
import csv
import io
import os
import sys
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from models import DailyRecord, MonthlyStat
import zipfile  # vẫn dùng ở chỗ khác nếu có
from datetime import datetime as _dt
import time
import logging
import random
from contextlib import contextmanager

# Lightweight module logger (không buộc cấu hình phức tạp)
logger = logging.getLogger("suk.utils")
if not logger.handlers:
    # Fallback basic config if host app chưa cấu hình
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')

DAILY_FILE = "daily_records.csv"
MONTHLY_FILE = "monthly_stats.csv"
SUBSCRIPTION_FILE = "monthly_subscriptions.csv"
PROFIT_SHARE_FILE = "profit_shares.csv"
WATER_ITEMS_FILE = "water_items.csv"  # Danh mục nước nhập (tên, số lượng tồn, đơn giá)
WATER_SALES_FILE = "water_sales.csv"  # Bán nước (ngày, tên, số lượng, đơn giá, thành tiền)
DATA_DIR_NAME = "data"  # Thư mục tập trung lưu CSV (additive, tự tạo nếu thiếu)

DAILY_HEADERS = ["ngay", "san", "khung_gio", "gia_vnd", "loai", "nguoi", "record_id"]  # record_id appended cuối (migrate mềm)
MONTHLY_HEADERS = [
    "thang", "tong_doanh_thu_vnd", "chi_phi_tru_hao_vnd", "chi_phi_ly_do", "loi_nhuan_vnd", "tu_tinh_tu_ngay"
]
SUBSCRIPTION_HEADERS = ["thang", "ten", "san", "so_buoi_tuan", "gio_moi_buoi", "thu", "he_so", "gia_vnd", "ghi_chu"]
PROFIT_SHARE_HEADERS = [
    "event_id",
    "scope",
    "total_revenue_vnd",
    "total_cost_vnd",
    "profit_vnd",
    "summary",
    "created_at"
]
WATER_ITEM_HEADERS = ["ten", "so_luong_ton", "don_gia_vnd"]
WATER_SALE_HEADERS = ["ngay", "ten", "so_luong", "don_gia_vnd", "tong_vnd"]

_daily_cache: List[DailyRecord] | None = None
_daily_cache_dirty: bool = True
_undo_stack: List[Tuple[str, List[str]]] = []
MAX_PRICE_WARN = 5_000_000
SAFE_WRITE_RETRY = 3
SAFE_WRITE_DELAY = 0.3
_month_total_cache: Dict[str, Dict[str, Any]] = {}  # { 'YYYY-MM': {'signature': str, 'value': int} }

# Price constants for calculator
COURT_PRICES = {
    "Sân A": 120000,
    "Sân B": 120000,
    "Sân C": 100000,
    "Sân D": 100000,
    "Sân E": 80000,
    "Sân F": 80000,
}

LIGHT_PRICE = 20000  # Price for lighting per hour
HOURLY_BASE = 100000  # Base hourly rate
LIGHT_SURCHARGE = 20000  # Light surcharge per hour

# ---------------------- INPUT / TEXT SAFETY HELPERS ----------------------
def _sanitize_text_cell(text: str) -> str:
    """Prevent simple CSV/Excel formula injection when opening exported CSV.
    If a cell begins with = + - @ we prefix an apostrophe. Keeps backward compatibility: UI still shows raw text after reading because we don't strip it on load (safe benign prefix in Excel).
    """
    if not text:
        return text
    if text[0] in ('=', '+', '-', '@'):
        return "'" + text
    return text

def parse_currency_any(raw: str) -> int:
    """Parse a human-entered VND string (may contain '.', ',', spaces, currency symbols) into int.
    Returns 0 if no digits. This central utility avoids scattered parsing logic.
    """
    if not raw:
        return 0
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if not digits:
        return 0
    try:
        return int(digits)
    except Exception:
        return 0


_CSV_FILE_SET = {
    DAILY_FILE,
    MONTHLY_FILE,
    SUBSCRIPTION_FILE,
    PROFIT_SHARE_FILE,
    WATER_ITEMS_FILE,
    WATER_SALES_FILE,
}

def _base_dir() -> str:
    if getattr(sys, 'frozen', False):  # PyInstaller
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _ensure_data_dir(base: str) -> str:
    data_dir = os.path.join(base, DATA_DIR_NAME)
    try:
        if not os.path.isdir(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    except Exception:
        # Fail-open: nếu không tạo được thì vẫn dùng base
        return base
    return data_dir

def _abs_path(filename: str) -> str:
    """Trả về đường dẫn tuyệt đối tới file.

    Thay đổi (additive): Từ phiên bản này, các CSV chính được ưu tiên đặt trong thư mục con 'data/'.
    - Nếu 'data/filename' tồn tại: dùng luôn.
    - Nếu chưa tồn tại nhưng bản cũ nằm ở root: di chuyển (os.replace) vào data để tập trung.
    - Nếu cả hai chưa có: trả về đường dẫn trong data (sẽ được create bởi ensure_*).
    Các file không thuộc danh sách CSV vẫn ở root để tránh ảnh hưởng hành vi hiện tại.
    Logic tính toán dữ liệu không đổi – chỉ thay đổi vị trí lưu vật lý có kiểm soát.
    """
    base = _base_dir()
    if filename in _CSV_FILE_SET:
        data_dir = _ensure_data_dir(base)
        data_path = os.path.join(data_dir, filename)
        if os.path.exists(data_path):
            return data_path
        root_path = os.path.join(base, filename)
        if os.path.exists(root_path):
            # Thử migrate sang data/ (an toàn: os.replace là atomic trên cùng ổ)
            try:
                os.replace(root_path, data_path)
                return data_path
            except Exception:
                # Nếu di chuyển thất bại, tiếp tục dùng file cũ ở root để không gián đoạn
                return root_path
        # Chưa có ở đâu -> sẽ được tạo mới trong data
        return data_path
    # File không thuộc nhóm CSV: hành vi cũ (root)
    return os.path.join(base, filename)

_record_id_counter = int(time.time())  # seed đơn giản tránh trùng trong phiên

def _generate_record_id() -> str:
    """Sinh ID ngắn, độc lập CSV: R + epoch_ms + 3 hex + counter mod 1000.
    Không bảo đảm tuyệt đối nhưng xác suất trùng thấp cho quy mô hiện tại."""
    global _record_id_counter
    _record_id_counter += 1
    millis = int(time.time() * 1000)
    rand = f"{random.randint(0, 0xFFF):03x}"
    return f"R{millis}{rand}{_record_id_counter%1000:03d}"

def ensure_daily_file():
    path = _abs_path(DAILY_FILE)
    if not os.path.exists(path):
        # Tạo mới với header mới có record_id
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(DAILY_HEADERS)
        return
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if not rows:
            return
        header = rows[0]
        if header == ["ngay", "san", "khung_gio", "gia_vnd"]:
            # V1 -> V3 (thêm loai, nguoi, record_id)
            new_rows = [DAILY_HEADERS]
            for r in rows[1:]:
                if len(r) == 4:
                    r.append("")  # loai
                    r.append("")  # nguoi
                r.append(_generate_record_id())  # record_id
                new_rows.append(r)
            tmp = path + ".tmp"
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(new_rows)
            os.replace(tmp, path)
        # migrate thiếu cột nguoi (phiên bản trước có 5 cột)
        elif header == ["ngay", "san", "khung_gio", "gia_vnd", "loai"]:
            # V2 thiếu nguoi -> thêm nguoi & record_id
            new_rows = [DAILY_HEADERS]
            for r in rows[1:]:
                if len(r) == 5:
                    r.append("")  # nguoi
                r.append(_generate_record_id())
                new_rows.append(r)
            tmp = path + ".tmp"
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(new_rows)
            os.replace(tmp, path)
        # V3: đủ 6 cột (có loai, nguoi) nhưng chưa có record_id
        elif "record_id" not in header:
            new_header = header + ["record_id"]
            new_rows = [new_header]
            for r in rows[1:]:
                r2 = list(r)
                r2.append(_generate_record_id())
                new_rows.append(r2)
            tmp = path + '.tmp'
            with open(tmp, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerows(new_rows)
            os.replace(tmp, path)
    except Exception as ex:
        logger.warning("ensure_daily_file migration failed: %s", ex)


def ensure_monthly_file():
    """Đảm bảo file monthly_stats.csv tồn tại và có cột lý do chi phí.

    Nếu là file cũ (thiếu cột chi_phi_ly_do) sẽ migrate bằng cách chèn cột rỗng.
    """
    path = _abs_path(MONTHLY_FILE)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(MONTHLY_HEADERS)
        return
    # migrate
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if not rows:
            return
        header = rows[0]
        if "chi_phi_ly_do" not in header:
            # header cũ dạng: thang, tong_doanh_thu_vnd, chi_phi_tru_hao_vnd, loi_nhuan_vnd, tu_tinh_tu_ngay
            # Ta chèn 'chi_phi_ly_do' sau chi_phi_tru_hao_vnd
            try:
                idx = header.index("chi_phi_tru_hao_vnd") + 1
            except ValueError:
                idx = 3
            new_header = header[:idx] + ["chi_phi_ly_do"] + header[idx:]
            new_rows = [new_header]
            for r in rows[1:]:
                # Chèn phần tử rỗng tại idx
                if len(r) < len(header):
                    # bỏ qua dòng lỗi
                    continue
                r2 = r[:idx] + [""] + r[idx:]
                new_rows.append(r2)
            tmp = path + ".tmp"
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerows(new_rows)
            os.replace(tmp, path)
    except Exception as ex:
        logger.warning("ensure_monthly_file migration failed: %s", ex)

def ensure_subscription_file():
    path = _abs_path(SUBSCRIPTION_FILE)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(SUBSCRIPTION_HEADERS)

def ensure_profit_share_file():
    path = _abs_path(PROFIT_SHARE_FILE)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(PROFIT_SHARE_HEADERS)

def ensure_water_items_file():
    path = _abs_path(WATER_ITEMS_FILE)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(WATER_ITEM_HEADERS)

def ensure_water_sales_file():
    path = _abs_path(WATER_SALES_FILE)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(WATER_SALE_HEADERS)


def ensure_all_data_files():
    """Tạo toàn bộ các file CSV nếu chưa tồn tại.

    Gọi hàm này ngay khi khởi động app (kể cả trong bản đóng gói .exe) để đảm bảo
    người dùng mở lần đầu đã có sẵn các file trống nằm cạnh file thực thi.
    """
    # Thứ tự đảm bảo thư mục data được tạo trước qua _abs_path()
    ensure_daily_file()
    ensure_monthly_file()
    ensure_subscription_file()
    ensure_profit_share_file()
    ensure_water_items_file()
    ensure_water_sales_file()


def _invalidate_cache():
    global _daily_cache_dirty
    _daily_cache_dirty = True
    _invalidate_month_cache()

def _invalidate_month_cache():
    _month_total_cache.clear()

def _file_mtime_or_0(filename: str) -> int:
    try:
        return int(os.path.getmtime(_abs_path(filename)))
    except Exception:
        return 0


def append_daily_record(ngay: str, san: str, khung_gio: str, gia_vnd: int, allow_overlap: bool = False, loai: str = "", nguoi: str = ""):
    ensure_daily_file()
    try:
        datetime.strptime(ngay, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Ngày phải ở định dạng YYYY-MM-DD (vd: 2025-08-23)")
    if san not in ("Sân 1", "Sân 2"):
        raise ValueError("Sân không hợp lệ (chỉ Sân 1 hoặc Sân 2)")
    if gia_vnd <= 0:
        raise ValueError("Giá phải là số dương")

    path = _abs_path(DAILY_FILE)
    norm_slot = normalize_time_slot(khung_gio)
    if not allow_overlap:
        existing = get_daily_records()
        for r in existing:
            if r.ngay == ngay and r.san == san and _time_overlap(r.khung_gio, norm_slot):
                raise ValueError(f"Khung giờ chồng chéo với bản ghi đã có: {r.khung_gio}")

    loai_norm = loai.strip().title() if loai else ""
    # Sanitize free-text fields to reduce risk when user opens CSV in spreadsheet apps.
    safe_loai = _sanitize_text_cell(loai_norm)
    safe_nguoi = _sanitize_text_cell(nguoi.strip())
    # record_id cuối cùng nếu header hỗ trợ
    record_id = _generate_record_id()
    if gia_vnd > MAX_PRICE_WARN:
        logger.warning("append_daily_record: giá bất thường %s VND (>%s) ngay=%s san=%s slot=%s", gia_vnd, MAX_PRICE_WARN, ngay, san, norm_slot)
    row = [ngay, san, norm_slot, str(gia_vnd), safe_loai, safe_nguoi, record_id]
    _safe_append_csv(path, row)
    _undo_stack.append((path, row))
    _invalidate_cache()
    _invalidate_month_cache()


def read_daily_records_dict(include_id: bool = True) -> List[Dict[str, Any]]:
    """Trả về list dict bản ghi ngày.
    include_id=True => thêm record_id nếu tồn tại (additive, không phá UI cũ)."""
    out: List[Dict[str, Any]] = []
    for r in get_daily_records():
        item = {"ngay": r.ngay, "san": r.san, "khung_gio": r.khung_gio, "gia_vnd": r.gia_vnd, "loai": r.loai, "nguoi": r.nguoi}
        if include_id and getattr(r, 'record_id', None):
            item['record_id'] = r.record_id  # type: ignore[attr-defined]
        out.append(item)
    return out

def read_daily_records_grouped_by_date() -> Dict[str, List[Dict[str, Any]]]:
    """Nhóm dữ liệu daily records theo ngày cho thời khóa biểu"""
    grouped = {}
    records = read_daily_records_dict()
    
    for record in records:
        date_key = record['ngay']  # Đã ở định dạng YYYY-MM-DD
        if date_key not in grouped:
            grouped[date_key] = []
        grouped[date_key].append(record)
    
    return grouped


def get_daily_records(force_reload: bool = False) -> List[DailyRecord]:
    global _daily_cache, _daily_cache_dirty
    ensure_daily_file()
    if _daily_cache is not None and not _daily_cache_dirty and not force_reload:
        return _daily_cache
    path = _abs_path(DAILY_FILE)
    recs: List[DailyRecord] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        has_id = bool(header and 'record_id' in header)
        idx = 0
        for row in reader:
            if len(row) < 4:
                continue
            try:
                gia = int(row[3])
            except ValueError:
                gia = 0
            loai = row[4] if len(row) > 4 else ""
            nguoi = row[5] if len(row) > 5 else ""
            rec_id = row[6] if has_id and len(row) > 6 else None
            recs.append(DailyRecord(row[0], row[1], row[2], gia, loai=loai, nguoi=nguoi, row_index=idx, record_id=rec_id))
            idx += 1
    _daily_cache = recs
    _daily_cache_dirty = False
    return recs

def delete_daily_record_by_id(record_id: str) -> bool:
    """Xóa bản ghi theo record_id (nếu file có cột). Không thay thế hàm cũ – chỉ chính xác hơn.
    Trả True nếu xóa."""
    if not record_id:
        return False
    ensure_daily_file()
    path = _abs_path(DAILY_FILE)
    with open(path, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows:
        return False
    header = rows[0]
    if 'record_id' not in header:
        return False
    id_idx = header.index('record_id')
    new_rows = [header]
    removed = None
    for r in rows[1:]:
        if removed is None and len(r) > id_idx and r[id_idx] == record_id:
            removed = r
            continue
        new_rows.append(r)
    if removed is None:
        return False
    tmp = path + '.tmp'
    with _file_lock(path):
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(new_rows)
        os.replace(tmp, path)
    _invalidate_cache()
    return True

def find_daily_record_by_id(record_id: str) -> Optional[DailyRecord]:
    if not record_id:
        return None
    for r in get_daily_records():
        if getattr(r, 'record_id', None) == record_id:
            return r
    return None


def delete_daily_record(ngay: str, san: str, khung_gio: str, gia_vnd: int) -> bool:
    """Xóa bản ghi khớp đầu tiên. Trả True nếu xóa."""
    ensure_daily_file()
    path = _abs_path(DAILY_FILE)
    with open(path, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return False
    header = rows[0]
    changed = False
    new_rows = [header]
    removed: Optional[List[str]] = None
    for r in rows[1:]:
        if not changed and len(r) >= 4 and r[0] == ngay and r[1] == san and r[2] == khung_gio:
            # so khớp giá nếu parse được, nếu không bỏ qua so giá
            try:
                if int(r[3]) != gia_vnd:
                    new_rows.append(r)
                    continue
            except ValueError:
                pass
            removed = r
            changed = True
            continue
        new_rows.append(r)
    if changed:
        tmp = path + ".tmp"
        with _file_lock(path):
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(new_rows)
            os.replace(tmp, path)
        if removed:
            _undo_stack.append((path, removed))
        _invalidate_cache()
    _invalidate_month_cache()
    return changed

def update_daily_record(old_ngay: str, old_san: str, old_khung: str, old_gia_vnd: int,
                        new_ngay: str, new_san: str, new_khung: str, new_gia_vnd: int, new_loai: str, new_nguoi: str = "",
                        check_overlap: bool = False) -> bool:
    """Cập nhật 1 bản ghi ngày.
    - Mặc định giữ hành vi cũ (không check chồng khung) để không phá luồng hiện tại.
    - Nếu check_overlap=True: kiểm tra chồng khung giờ với các dòng khác cùng (ngày,sân) trước khi ghi.
    """
    ensure_daily_file()
    path = _abs_path(DAILY_FILE)
    with open(path, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows:
        return False
    header = rows[0]
    changed = False
    new_rows = [header]
    has_id = 'record_id' in header
    # Overlap pre-check (additive, optional)
    if check_overlap:
        try:
            norm_new_khung = normalize_time_slot(new_khung)
            for r in rows[1:]:
                if len(r) >= 4 and r[0]==new_ngay and r[1]==new_san:
                    if r[2] != old_khung or r[0] != old_ngay or r[1] != old_san:  # exclude the one being updated
                        if _time_overlap(r[2], norm_new_khung):
                            raise ValueError(f"Khung giờ mới chồng với: {r[2]}")
            new_khung = norm_new_khung
        except Exception as ex:
            logger.warning("update_daily_record overlap check failed: %s", ex)
    for r in rows[1:]:
        if (not changed and len(r) >= 4 and r[0]==old_ngay and r[1]==old_san and r[2]==old_khung):
            # so giá nếu parse được
            match_price = True
            try:
                match_price = int(r[3]) == old_gia_vnd
            except Exception as ex:
                logger.warning("delete_daily_record error: %s", ex)
            if match_price:
                record_id = r[-1] if has_id and len(r) >= 7 else None
                if new_gia_vnd > MAX_PRICE_WARN:
                    logger.warning("update_daily_record: giá bất thường %s VND (>%s) ngay=%s san=%s slot=%s", new_gia_vnd, MAX_PRICE_WARN, new_ngay, new_san, new_khung)
                new_row = [new_ngay, new_san, new_khung, str(new_gia_vnd), new_loai.strip().title() if new_loai else "", new_nguoi.strip()]
                if has_id:
                    new_row.append(record_id or '')
                new_rows.append(new_row)
                changed = True
                continue
        new_rows.append(r)
    if changed:
        tmp = path + '.tmp'
        with _file_lock(path):
            with open(tmp, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerows(new_rows)
            os.replace(tmp, path)
        _invalidate_cache()
    _invalidate_month_cache()
    return changed


def undo_last_action() -> bool:
    if not _undo_stack:
        return False
    filename, row = _undo_stack.pop()
    # Undo append: nếu row tồn tại cuối file -> xóa; nếu undo xóa -> thêm lại
    path = filename
    if not os.path.exists(path):
        return False
    with open(path, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return False
    header = rows[0]
    data_rows = rows[1:]
    # Nếu hàng cuối bằng row -> pop (undo append)
    if data_rows and data_rows[-1] == row:
        data_rows = data_rows[:-1]
    else:
        # coi như undo delete -> thêm lại cuối
        data_rows.append(row)
    tmp = path + ".tmp"
    with _file_lock(path):
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(data_rows)
        os.replace(tmp, path)
    _invalidate_cache()
    return True


def save_monthly_stat(thang: str, tong: int, chi_phi: int, tu_tinh_tu_ngay: bool, chi_phi_ly_do: str = ""):
    ensure_monthly_file()
    # thang format YYYY-MM
    try:
        datetime.strptime(thang + "-01", "%Y-%m-%d")
    except ValueError:
        raise ValueError("Tháng phải ở định dạng YYYY-MM (vd: 2025-08)")
    if tong < 0 or chi_phi < 0:
        raise ValueError("Số tiền không được âm")

    loi_nhuan = compute_profit(tong, chi_phi)

    # Ghi nối thêm (không ghi đè) để lưu lịch sử
    path = _abs_path(MONTHLY_FILE)
    ensure_monthly_file()  # đảm bảo migration đã chạy
    # kiểm tra xem header có cột lý do không
    try:
        with open(path, "r", newline="", encoding="utf-8") as rf:
            first = rf.readline().strip().split(',')
        has_reason = 'chi_phi_ly_do' in first
    except Exception:
        has_reason = True
    row = [thang, tong, chi_phi]
    if has_reason:
        row.append(chi_phi_ly_do.strip())
    row.extend([loi_nhuan, "1" if tu_tinh_tu_ngay else "0"])
    _safe_append_csv(path, row)
    return loi_nhuan

def update_monthly_stat(thang: str, new_tong: int, new_chi_phi: int, new_reason: str) -> bool:
    """Cập nhật bản ghi tháng đầu tiên khớp thang. Trả True nếu cập nhật."""
    ensure_monthly_file()
    path = _abs_path(MONTHLY_FILE)
    with open(path, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows: return False
    header = rows[0]
    has_reason = 'chi_phi_ly_do' in header
    # xác định index
    try:
        idx_thang = header.index('thang')
        idx_tong = header.index('tong_doanh_thu_vnd')
        idx_cp = header.index('chi_phi_tru_hao_vnd')
        if has_reason:
            idx_reason = header.index('chi_phi_ly_do')
        idx_loi = header.index('loi_nhuan_vnd')
        idx_flag = header.index('tu_tinh_tu_ngay')
    except ValueError:
        return False
    changed = False
    for i in range(1, len(rows)):
        r = rows[i]
        if len(r) < len(header):
            continue
        if r[idx_thang] == thang and not changed:
            loi = compute_profit(new_tong, new_chi_phi)
            r[idx_tong] = str(new_tong)
            r[idx_cp] = str(new_chi_phi)
            if has_reason:
                r[idx_reason] = new_reason.strip()
            r[idx_loi] = str(loi)
            r[idx_flag] = r[idx_flag] or '0'
            changed = True
    if changed:
        tmp = path + '.tmp'
        with _file_lock(path):
            with open(tmp, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerows(rows)
            os.replace(tmp, path)
    return changed


def read_monthly_stats() -> List[Dict[str, Any]]:
    ensure_monthly_file()
    path = _abs_path(MONTHLY_FILE)
    rows: List[Dict[str, Any]] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            for k in ("tong_doanh_thu_vnd", "chi_phi_tru_hao_vnd", "loi_nhuan_vnd"):
                try:
                    r[k] = int(r[k]) if r.get(k) else 0
                except ValueError:
                    r[k] = 0
            r["tu_tinh_tu_ngay"] = r.get("tu_tinh_tu_ngay") in ("1", "True", "true")
            rows.append(r)
    return rows

# ---------------------- HÀM TÍNH TOÁN ----------------------

def compute_daily_total(ngay: str) -> int:
    records = get_daily_records()
    return sum(r.gia_vnd for r in records if r.ngay == ngay)


def compute_month_total(thang: str) -> int:
    # Chấp nhận 'YYYY-MM' hoặc 'MM-YYYY'
    if len(thang) != 7:
        raise ValueError("Tháng phải có dạng YYYY-MM hoặc MM-YYYY")
    if thang[2] == '-':  # MM-YYYY
        try:
            dt = datetime.strptime(thang, '%m-%Y')
            thang_iso = dt.strftime('%Y-%m')
        except ValueError:
            raise ValueError("Tháng không hợp lệ (MM-YYYY)")
    else:
        # assume YYYY-MM
        try:
            datetime.strptime(thang + '-01', '%Y-%m-%d')
        except ValueError:
            raise ValueError("Tháng không hợp lệ (YYYY-MM)")
        thang_iso = thang
    # Cache key = month iso
    key = thang_iso
    # Build a simple signature from mtime of involved files (daily, subscriptions, water sales)
    sig_parts = [
        str(_file_mtime_or_0(DAILY_FILE)),
        str(_file_mtime_or_0(SUBSCRIPTION_FILE)),
        str(_file_mtime_or_0(WATER_SALES_FILE)),
    ]
    signature = '|'.join(sig_parts)
    cached = _month_total_cache.get(key)
    if cached and cached.get('signature') == signature:
        logger.debug("compute_month_total cache hit %s", thang_iso)
        return cached.get('value', 0)
    logger.debug("compute_month_total cache miss %s (recompute)", thang_iso)
    # Compute fresh (logic giữ nguyên)
    records = get_daily_records()
    daily_sum = sum(r.gia_vnd for r in records if r.ngay.startswith(thang_iso + "-"))
    subs_sum = compute_month_subscription_total(thang_iso)
    water_sum = compute_month_water_sales_total(thang_iso)
    total = daily_sum + subs_sum + water_sum
    _month_total_cache[key] = {'signature': signature, 'value': total}
    return total


def compute_profit(tong_doanh_thu: int, chi_phi_tru_hao: int) -> int:
    return tong_doanh_thu - chi_phi_tru_hao

# ---------------------- CHIA LỢI NHUẬN ----------------------
# Tỷ lệ phần trăm: tổng = 100%
PROFIT_SHARES = [
    ("Uyên", 0.1120),
    ("Khoa", 0.4148),
    ("Sang", 0.4732),
]

def compute_profit_shares(loi_nhuan: int) -> Dict[str, int]:
    """Chia lợi nhuận theo phần trăm cố định.
    Trả về dict tên -> số tiền (VND) đã làm tròn, đảm bảo tổng bằng lợi nhuận.
    """
    if not isinstance(loi_nhuan, int):
        raise ValueError("Lợi nhuận phải là số nguyên VND")
    allocations = []
    for name, pct in PROFIT_SHARES:
        raw = loi_nhuan * pct
        rounded = int(round(raw))
        allocations.append((name, pct, raw, rounded))
    total_rounded = sum(a[3] for a in allocations)
    diff = loi_nhuan - total_rounded
    if diff != 0:
        # Sắp xếp theo phần thập phân giảm dần để điều chỉnh
        # Nếu diff > 0: cộng 1 vào các phần đầu cho đến hết diff
        # Nếu diff < 0: trừ 1 tương tự
        allocations.sort(key=lambda x: (x[2] - int(x[2])), reverse=(diff > 0))
        i = 0
        step = 1 if diff > 0 else -1
        while diff != 0 and i < len(allocations):
            name, pct, raw, rounded = allocations[i]
            allocations[i] = (name, pct, raw, rounded + step)
            diff -= step
            i = (i + 1) if i + 1 < len(allocations) else 0
    return {a[0]: a[3] for a in allocations}

# ---------------------- LƯU & ĐỌC SỰ KIỆN CHIA LỢI NHUẬN ----------------------

def add_profit_share_event(scope: str, total_revenue: int, total_cost: int, profit: int, summary: str) -> str:
    """Lưu một sự kiện chia lợi nhuận.
    Trả về event_id (chuỗi)."""
    ensure_profit_share_file()
    event_id = str(int(time.time()*1000))
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    path = _abs_path(PROFIT_SHARE_FILE)
    _safe_append_csv(path, [event_id, scope, total_revenue, total_cost, profit, summary, created_at])
    return event_id

def read_profit_share_events() -> List[Dict[str, Any]]:
    ensure_profit_share_file()
    path = _abs_path(PROFIT_SHARE_FILE)
    events: List[Dict[str, Any]] = []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                r['total_revenue_vnd'] = int(r.get('total_revenue_vnd',0) or 0)
                r['total_cost_vnd'] = int(r.get('total_cost_vnd',0) or 0)
                r['profit_vnd'] = int(r.get('profit_vnd',0) or 0)
            except ValueError:
                r['total_revenue_vnd'] = r.get('total_revenue_vnd',0)
            events.append(r)
    return events

def delete_profit_share_event(event_id: str) -> bool:
    ensure_profit_share_file()
    path = _abs_path(PROFIT_SHARE_FILE)
    with open(path, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows:
        return False
    header = rows[0]
    new_rows = [header]
    removed = False
    for r in rows[1:]:
        if len(r) >= 1 and r[0] == event_id:
            removed = True
            continue
        new_rows.append(r)
    if removed:
        tmp = path + '.tmp'
        with _file_lock(path):
            with open(tmp, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerows(new_rows)
            os.replace(tmp, path)
    return removed

# ĐÃ LOẠI BỎ: parse_price / analyze_price_input
# Lý do: UI giờ luôn nhập & hiển thị đầy đủ số VND với phân tách nghìn.
# Nếu cần tái sử dụng logic cũ, xem lại lịch sử Git trước phiên bản v1.8.0.


def format_currency(vnd: int) -> str:
    return f"{vnd:,.0f} đ".replace(",", ".")

def is_off_hour(time_str: str) -> bool:
    """Check if the given time is during off-peak hours (before 6 AM or after 10 PM)."""
    try:
        if '-' in time_str:
            start_time = time_str.split('-')[0].replace('h', '').strip()
            hour = int(start_time)
            return hour < 6 or hour >= 22
        return False
    except (ValueError, IndexError):
        return False

# ---------------------- TIỆN ÍCH KHÁC ----------------------

def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")

def to_ui_date(iso_date: str) -> str:
    """YYYY-MM-DD -> DD-MM-YYYY"""
    try:
        return datetime.strptime(iso_date, '%Y-%m-%d').strftime('%d-%m-%Y')
    except ValueError:
        return iso_date

def to_iso_date(ui_date: str) -> str:
    """DD-MM-YYYY hoặc DD/MM/YYYY -> YYYY-MM-DD"""
    ui_date = ui_date.replace('/', '-')
    return datetime.strptime(ui_date, '%d-%m-%Y').strftime('%Y-%m-%d')

def to_ui_month(iso_month: str) -> str:
    try:
        return datetime.strptime(iso_month + '-01', '%Y-%m-%d').strftime('%m-%Y')
    except ValueError:
        return iso_month

def to_iso_month(ui_month: str) -> str:
    if ui_month[2] == '-':  # MM-YYYY
        return datetime.strptime(ui_month, '%m-%Y').strftime('%Y-%m')
    return ui_month  # assume already


def validate_time_slot(slot: str) -> bool:
    """Kiểm tra mẫu '5h-7h' và đảm bảo start < end."""
    try:
        _ = normalize_time_slot(slot)
        return True
    except Exception:
        return False


def normalize_time_slot(slot: str) -> str:
    """Chuẩn hóa khung giờ.
    '05h-07h' -> '5h-7h'
    Kiểm tra start < end.
    Raises ValueError nếu sai.
    """
    if not slot or '-' not in slot:
        raise ValueError("Khung giờ không hợp lệ")
    a, b = slot.split('-', 1)
    a = a.strip().lower().rstrip('h')
    b = b.strip().lower().rstrip('h')
    if not (a.isdigit() and b.isdigit()):
        raise ValueError("Khung giờ không hợp lệ")
    sa, sb = int(a), int(b)
    if not (0 <= sa <= 23 and 0 <= sb <= 23):
        raise ValueError("Giờ phải trong 0-23")
    if sa >= sb:
        raise ValueError("Giờ bắt đầu phải nhỏ hơn giờ kết thúc")
    return f"{sa}h-{sb}h"


def _time_overlap(a: str, b: str) -> bool:
    def conv(s: str) -> Tuple[int, int]:
        s = s.lower().strip()
        if '-' not in s:
            return (0, 0)
        p1, p2 = s.split('-', 1)
        p1 = p1.strip().rstrip('h')
        p2 = p2.strip().rstrip('h')
        try:
            return (int(p1), int(p2))
        except ValueError:
            return (0, 0)
    a1, a2 = conv(a)
    b1, b2 = conv(b)
    if a1 >= a2 or b1 >= b2:
        return False
    return not (a2 <= b1 or b2 <= a1)


def breakdown_daily_by_court(ngay: str) -> Dict[str, int]:
    result = defaultdict(int)
    for r in get_daily_records():
        if r.ngay == ngay:
            result[r.san] += r.gia_vnd
    return dict(result)


def backup_data(dest_dir: Optional[str] = None) -> str:
    """Xuất 1 file PDF tổng hợp tất cả dữ liệu (tiếng Việt đầy đủ). Trả về đường dẫn file.

    Yêu cầu thư viện bên ngoài: fpdf2 (cài: pip install fpdf2)
    Tự động tìm một font Unicode phổ biến trong Windows (Arial / Tahoma / Segoe UI)."""
    try:
        from fpdf import FPDF  # type: ignore
    except Exception:
        raise RuntimeError("Chưa cài thư viện fpdf2. Hãy chạy: pip install fpdf2")

    # Thu thập dữ liệu
    sections: List[Tuple[str, List[str], List[List[str]], List[float]]] = []

    # Helper đọc file CSV nếu tồn tại
    def read_csv_dict(path: str) -> List[Dict[str, str]]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', newline='', encoding='utf-8') as f:
                return list(csv.DictReader(f))
        except Exception:
            return []

    daily = read_csv_dict(_abs_path(DAILY_FILE))
    if daily:
        headers = ["Ngày", "Sân", "Khung giờ", "Giá (VND)", "Loại"]
        rows = [[d.get('ngay',''), d.get('san',''), d.get('khung_gio',''), d.get('gia_vnd',''), d.get('loai','')] for d in daily]
        widths = [22, 18, 32, 28, 28]  # mm
        sections.append(("1. Ghi chép ngày", headers, rows, widths))

    monthly = read_csv_dict(_abs_path(MONTHLY_FILE))
    if monthly:
        headers = ["Tháng", "Tổng doanh thu", "Chi phí trừ hao", "Lợi nhuận", "Tự tính?"]
        rows = [[m.get('thang',''), m.get('tong_doanh_thu_vnd',''), m.get('chi_phi_tru_hao_vnd',''), m.get('loi_nhuan_vnd',''), m.get('tu_tinh_tu_ngay','')] for m in monthly]
        widths = [25, 38, 38, 30, 18]
        sections.append(("2. Thống kê tháng", headers, rows, widths))

    subs = read_csv_dict(_abs_path(SUBSCRIPTION_FILE))
    if subs:
        headers = ["Tháng", "Tên", "Số buổi/tuần", "Giờ mỗi buổi", "Hệ số", "Giá (VND)"]
        rows = [[s.get('thang',''), s.get('ten',''), s.get('so_buoi_tuan',''), s.get('gio_moi_buoi',''), s.get('he_so',''), s.get('gia_vnd','')] for s in subs]
        widths = [20, 40, 26, 26, 18, 30]
        sections.append(("3. Gói tháng", headers, rows, widths))

    shares = read_csv_dict(_abs_path(PROFIT_SHARE_FILE))
    if shares:
        headers = ["Mã", "Phạm vi", "Doanh thu", "Chi phí", "Lợi nhuận", "Tạo lúc", "Tóm tắt (rút gọn)"]
        rows = []
        for s in shares:
            summary = s.get('summary','')
            if len(summary) > 60:
                summary = summary[:57] + '...'
            rows.append([
                s.get('event_id',''), s.get('scope',''), s.get('total_revenue_vnd',''),
                s.get('total_cost_vnd',''), s.get('profit_vnd',''), s.get('created_at',''), summary
            ])
        widths = [16, 36, 28, 26, 26, 30, 40]
        sections.append(("4. Chia lợi nhuận", headers, rows, widths))

    # Nước nhập & bán (thêm sau cùng)
    water_items = read_csv_dict(_abs_path(WATER_ITEMS_FILE))
    if water_items:
        headers = ["Tên", "SL tồn", "Đơn giá"]
        rows = [[w.get('ten',''), w.get('so_luong_ton',''), w.get('don_gia_vnd','')] for w in water_items]
        widths = [50, 22, 28]
        sections.append(("5. Danh mục nước", headers, rows, widths))
    water_sales = read_csv_dict(_abs_path(WATER_SALES_FILE))
    if water_sales:
        headers = ["Ngày", "Tên", "SL", "Đơn giá", "Thành tiền"]
        rows = [[s.get('ngay',''), s.get('ten',''), s.get('so_luong',''), s.get('don_gia_vnd',''), s.get('tong_vnd','')] for s in water_sales]
        widths = [22, 40, 14, 28, 30]
        sections.append(("6. Bán nước", headers, rows, widths))

    if not sections:
        raise FileNotFoundError("Chưa có dữ liệu để xuất")

    # Chuẩn bị font Unicode
    font_candidates = [
        r"C:\\Windows\\Fonts\\arial.ttf",
        r"C:\\Windows\\Fonts\\tahoma.ttf",
        r"C:\\Windows\\Fonts\\segoeui.ttf",
        r"C:\\Windows\\Fonts\\verdana.ttf",
    ]
    font_path = None
    for fp in font_candidates:
        if os.path.exists(fp):
            font_path = fp
            break
    if not font_path:
        raise RuntimeError("Không tìm thấy font Unicode (Arial/Tahoma/SegoeUI/Verdana). Hãy chỉnh sửa hàm backup_data.")

    class PDF(FPDF):
        def header(self):  # type: ignore
            self.set_font('VN', '', 11)
            self.cell(0, 6, "BÁO CÁO DỮ LIỆU SÂN PICKLEBALL", ln=1, align='C')
            self.set_font('VN','',8)
            self.cell(0,5, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ln=1, align='C')
            self.ln(2)
        def footer(self):  # type: ignore
            self.set_y(-12)
            self.set_font('VN','',8)
            self.cell(0,5, f"Trang {self.page_no()}", align='C')

    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_font('VN','', font_path, uni=True)  # type: ignore
    pdf.add_page()
    pdf.set_font('VN','',10)

    def add_section(title: str, headers: List[str], rows: List[List[str]], widths: List[float]):
        pdf.set_font('VN','',11)
        pdf.set_text_color(0,0,128)
        pdf.cell(0,7, title, ln=1)
        pdf.set_text_color(0,0,0)
        # Header row
        pdf.set_font('VN','',9.5)
        for h, w in zip(headers, widths):
            pdf.set_fill_color(230,230,230)
            pdf.cell(w, 7, h, border=1, align='C', fill=True)
        pdf.ln()
        pdf.set_font('VN','',9)
        for r in rows:
            # Kiểm tra còn chỗ trang không (simple heuristic)
            if pdf.get_y() > 265:  # gần đáy trang
                pdf.add_page(); pdf.set_font('VN','',9)
                for h, w in zip(headers, widths):
                    pdf.set_fill_color(230,230,230)
                    pdf.cell(w, 7, h, border=1, align='C', fill=True)
                pdf.ln()
            for val, w in zip(r, widths):
                # Đảm bảo chuỗi không quá dài
                text = str(val)
                if len(text) > 28:
                    text = text[:25] + '…'
                pdf.cell(w, 6, text, border=1)
            pdf.ln()
        pdf.ln(2)

    for title, headers, rows, widths in sections:
        add_section(title, headers, rows, widths)

    if dest_dir is None:
        dest_dir = _abs_path('backups')
    os.makedirs(dest_dir, exist_ok=True)
    ts = _dt.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(dest_dir, f"Bao_cao_du_lieu_{ts}.pdf")
    pdf.output(out_path)
    return out_path


def month_breakdown_by_court(thang: str) -> Dict[str, int]:
    """Tổng doanh thu từng sân trong tháng (YYYY-MM)."""
    bd = defaultdict(int)
    for r in get_daily_records():
        if r.ngay.startswith(thang + "-"):
            bd[r.san] += r.gia_vnd
    # Cộng thêm mục 'Gói tháng' & 'Nước'
    subs_total = compute_month_subscription_total(thang)
    if subs_total:
        bd['Gói tháng'] += subs_total
    water_total = compute_month_water_sales_total(thang)
    if water_total:
        bd['Nước'] += water_total
    return dict(bd)

# ---------------------- GÓI THÁNG (SUBSCRIPTIONS) ----------------------
BASE_SUB_PRICE = 1_150_000  # Giá chuẩn 3 buổi/tuần * 1 giờ/buổi
BASE_UNITS = 3  # 3 buổi * 1 giờ

def compute_subscription_price(so_buoi_tuan: int, gio_moi_buoi: int) -> int:
    if so_buoi_tuan <= 0 or so_buoi_tuan > 14:
        raise ValueError("Số buổi/tuần không hợp lệ")
    if gio_moi_buoi <= 0 or gio_moi_buoi > 6:
        raise ValueError("Giờ mỗi buổi không hợp lệ")
    units = so_buoi_tuan * gio_moi_buoi
    factor = units / BASE_UNITS
    price = int(round(BASE_SUB_PRICE * factor))
    return price

def add_month_subscription(thang: str, ten: str, so_buoi_tuan: int, gio_moi_buoi: int, san: str = "Sân 1", thu: str = "", ghi_chu: str = "") -> int:
    """Thêm gói tháng cho một nhóm/người.
    thang: YYYY-MM
    san: Sân 1 hoặc Sân 2
    thu: Các thứ trong tuần (ví dụ: "Thứ 2, Thứ 4")
    ghi_chu: Ghi chú thêm
    Trả về giá tính (VND)."""
    ensure_subscription_file()
    try:
        datetime.strptime(thang + '-01', '%Y-%m-%d')
    except ValueError:
        raise ValueError("Tháng phải YYYY-MM")
    ten = _sanitize_text_cell(ten.strip())
    if not ten:
        raise ValueError("Tên nhóm không được trống")
    gia = compute_subscription_price(so_buoi_tuan, gio_moi_buoi)
    he_so = round((so_buoi_tuan * gio_moi_buoi) / BASE_UNITS, 2)
    path = _abs_path(SUBSCRIPTION_FILE)
    safe_thu = _sanitize_text_cell(thu)
    safe_note = _sanitize_text_cell(ghi_chu)
    _safe_append_csv(path, [thang, ten, san, str(so_buoi_tuan), str(gio_moi_buoi), safe_thu, str(he_so), str(gia), safe_note])
    # Month total cache may include subscription revenue -> invalidate
    _invalidate_month_cache()
    return gia

def add_month_subscription_with_time(thang: str, ten: str, so_buoi_tuan: int, gio_moi_buoi_text: str, san: str = "Sân 1", thu: str = "", ghi_chu: str = "") -> int:
    """Thêm gói tháng với format giờ mới (ví dụ: "2 (7:00-9:00)").
    thang: YYYY-MM
    san: Sân 1 hoặc Sân 2
    thu: Các thứ trong tuần (ví dụ: "Thứ 2, Thứ 4")
    gio_moi_buoi_text: Format "2 (7:00-9:00)" hoặc "2"
    ghi_chu: Ghi chú thêm
    Trả về giá tính (VND)."""
    ensure_subscription_file()
    try:
        datetime.strptime(thang + '-01', '%Y-%m-%d')
    except ValueError:
        raise ValueError("Tháng phải YYYY-MM")
    ten = _sanitize_text_cell(ten.strip())
    if not ten:
        raise ValueError("Tên nhóm không được trống")
    
    # Parse số giờ từ text format
    if '(' in gio_moi_buoi_text:
        gio_moi_buoi = int(gio_moi_buoi_text.split('(')[0].strip())
    else:
        gio_moi_buoi = int(gio_moi_buoi_text.split()[0]) if gio_moi_buoi_text else 1
    
    gia = compute_subscription_price(so_buoi_tuan, gio_moi_buoi)
    he_so = round((so_buoi_tuan * gio_moi_buoi) / BASE_UNITS, 2)
    path = _abs_path(SUBSCRIPTION_FILE)
    # Lưu gio_moi_buoi_text với format đầy đủ
    safe_thu = _sanitize_text_cell(thu)
    safe_note = _sanitize_text_cell(ghi_chu)
    _safe_append_csv(path, [thang, ten, san, str(so_buoi_tuan), gio_moi_buoi_text, safe_thu, str(he_so), str(gia), safe_note])
    _invalidate_month_cache()
    return gia

def update_month_subscription(thang: str, old_ten: str, new_ten: str, so_buoi_tuan: int, gio_moi_buoi: int, san: str = "Sân 1", thu: str = "", ghi_chu: str = "") -> bool:
    """Cập nhật gói tháng: tìm dòng đầu tiên khớp thang & old_ten."""
    ensure_subscription_file()
    path = _abs_path(SUBSCRIPTION_FILE)
    with open(path,'r',newline='',encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows: return False
    header = rows[0]; changed=False
    new_rows=[header]
    gia = compute_subscription_price(so_buoi_tuan, gio_moi_buoi)
    safe_new_ten = _sanitize_text_cell(new_ten.strip())
    safe_thu = _sanitize_text_cell(thu)
    safe_note = _sanitize_text_cell(ghi_chu)
    he_so = round((so_buoi_tuan * gio_moi_buoi) / BASE_UNITS, 2)
    for r in rows[1:]:
        if (not changed and len(r)>=2 and r[0]==thang and r[1]==old_ten):
            # Update with new structure: thang, ten, san, so_buoi_tuan, gio_moi_buoi, thu, he_so, gia_vnd, ghi_chu
            new_rows.append([thang, safe_new_ten, san, str(so_buoi_tuan), str(gio_moi_buoi), safe_thu, str(he_so), str(gia), safe_note])
            changed=True; continue
        new_rows.append(r)
    if changed:
        tmp=path+'.tmp'
        with _file_lock(path):
            with open(tmp,'w',newline='',encoding='utf-8') as f:
                csv.writer(f).writerows(new_rows)
            os.replace(tmp,path)
        _invalidate_month_cache()
    return changed

def update_month_subscription_with_time(thang: str, old_ten: str, new_ten: str, so_buoi_tuan: int, gio_moi_buoi_text: str, san: str = "Sân 1", thu: str = "", ghi_chu: str = "") -> bool:
    """Cập nhật gói tháng với format giờ mới."""
    ensure_subscription_file()
    path = _abs_path(SUBSCRIPTION_FILE)
    with open(path,'r',newline='',encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows: return False
    header = rows[0]; changed=False
    new_rows=[header]
    
    # Parse số giờ từ text format để tính giá
    if '(' in gio_moi_buoi_text:
        gio_moi_buoi = int(gio_moi_buoi_text.split('(')[0].strip())
    else:
        gio_moi_buoi = int(gio_moi_buoi_text.split()[0]) if gio_moi_buoi_text else 1
    
    gia = compute_subscription_price(so_buoi_tuan, gio_moi_buoi)
    safe_new_ten = _sanitize_text_cell(new_ten.strip())
    safe_thu = _sanitize_text_cell(thu)
    safe_note = _sanitize_text_cell(ghi_chu)
    he_so = round((so_buoi_tuan * gio_moi_buoi) / BASE_UNITS, 2)
    for r in rows[1:]:
        if (not changed and len(r)>=2 and r[0]==thang and r[1]==old_ten):
            # Update with new structure: thang, ten, san, so_buoi_tuan, gio_moi_buoi, thu, he_so, gia_vnd, ghi_chu
            new_rows.append([thang, safe_new_ten, san, str(so_buoi_tuan), gio_moi_buoi_text, safe_thu, str(he_so), str(gia), safe_note])
            changed=True; continue
        new_rows.append(r)
    if changed:
        tmp=path+'.tmp'
        with _file_lock(path):
            with open(tmp,'w',newline='',encoding='utf-8') as f:
                csv.writer(f).writerows(new_rows)
            os.replace(tmp,path)
        _invalidate_month_cache()
    return changed

def read_all_subscriptions() -> List[Dict[str, Any]]:
    ensure_subscription_file()
    path = _abs_path(SUBSCRIPTION_FILE)
    res: List[Dict[str, Any]] = []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                r['so_buoi_tuan'] = int(r.get('so_buoi_tuan', '0'))
            except ValueError:
                r['so_buoi_tuan'] = 0
            
            # Handle gio_moi_buoi which can be text format "2 (7:00-9:00)" or just "2"
            gio_text = r.get('gio_moi_buoi', '0')
            try:
                if '(' in gio_text:
                    # Parse "2 (7:00-9:00)" format - extract just the number for calculations
                    r['gio_moi_buoi'] = int(gio_text.split('(')[0].strip())
                    r['gio_moi_buoi_display'] = gio_text  # Keep full format for display
                else:
                    # Just a number
                    r['gio_moi_buoi'] = int(gio_text)
                    r['gio_moi_buoi_display'] = gio_text
            except ValueError:
                r['gio_moi_buoi'] = 0
                r['gio_moi_buoi_display'] = '0'
            
            try:
                r['gia_vnd'] = int(r.get('gia_vnd', '0'))
            except ValueError:
                r['gia_vnd'] = 0
            res.append(r)
    return res

def read_month_subscriptions(thang: str) -> List[Dict[str, Any]]:
    return [r for r in read_all_subscriptions() if r.get('thang') == thang]

def compute_month_subscription_total(thang: str) -> int:
    return sum(r['gia_vnd'] for r in read_month_subscriptions(thang))

def compute_month_water_sales_total(thang: str) -> int:
    """Tổng tiền bán nước tháng (YYYY-MM)."""
    try:
        ensure_water_sales_file()
    except Exception:
        return 0
    total = 0
    for r in read_water_sales():
        ngay = r.get('ngay','')
        if isinstance(ngay, str) and ngay.startswith(thang + '-'):
            total += r.get('tong_vnd',0)
    return total

def delete_month_subscription(thang: str, ten: str) -> bool:
    """Xóa gói tháng đầu tiên khớp thang & tên. Trả True nếu xóa."""
    ensure_subscription_file()
    path = _abs_path(SUBSCRIPTION_FILE)
    with open(path, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows:
        return False
    header = rows[0]
    new_rows = [header]
    removed = False
    for r in rows[1:]:
        if (not removed and len(r) >= 6 and r[0] == thang and r[1] == ten):
            removed = True
            continue
        new_rows.append(r)
    if removed:
        tmp = path + '.tmp'
        with _file_lock(path):
            with open(tmp, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerows(new_rows)
            os.replace(tmp, path)
        _invalidate_month_cache()
    return removed

# ---------------------- NƯỚC (BEVERAGE MANAGEMENT) ----------------------
def add_water_item(ten: str, so_luong_ton: int, don_gia_vnd: int):
    """Thêm hoặc cập nhật một loại nước trong danh mục.
    Nếu tên đã tồn tại -> cộng dồn số lượng (có thể âm để trừ) và cập nhật đơn giá mới.
    Nếu chưa tồn tại và số lượng âm -> lỗi.
    """
    ten = _sanitize_text_cell(ten.strip())
    if not ten:
        raise ValueError("Tên nước không được trống")
    if so_luong_ton == 0:
        raise ValueError("Số lượng thay đổi phải khác 0")
    if don_gia_vnd <= 0:
        raise ValueError("Đơn giá phải > 0")
    ensure_water_items_file()
    path = _abs_path(WATER_ITEMS_FILE)
    with open(path, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    header = rows[0] if rows else WATER_ITEM_HEADERS
    data = rows[1:]
    updated = False
    new_rows = [header]
    for r in data:
        if len(r) >= 3 and r[0].strip().lower() == ten.lower():
            try:
                old_qty = int(r[1])
            except Exception:
                old_qty = 0
            new_qty = old_qty + so_luong_ton
            new_rows.append([ten, str(new_qty), str(don_gia_vnd)])
            updated = True
        else:
            new_rows.append(r)
    if not updated:
        if so_luong_ton < 0:
            raise ValueError("Không thể tạo mới với số lượng âm")
        new_rows.append([ten, str(so_luong_ton), str(don_gia_vnd)])
    tmp = path + '.tmp'
    with _file_lock(path):
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(new_rows)
        os.replace(tmp, path)
    _invalidate_month_cache()  # Water item price/quantity can affect future sales summaries

def update_water_item(old_ten: str, new_ten: str, don_gia_vnd: int) -> bool:
    """Đổi tên và/hoặc đơn giá nước, giữ nguyên số lượng tồn."""
    ensure_water_items_file()
    path = _abs_path(WATER_ITEMS_FILE)
    with open(path,'r',newline='',encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if not rows: return False
    header = rows[0]; changed=False
    new_rows=[header]
    for r in rows[1:]:
        if len(r)>=3 and (not changed) and r[0].strip().lower()==old_ten.strip().lower():
            # giữ số lượng tồn hiện tại
            qty = r[1]
            new_rows.append([_sanitize_text_cell(new_ten.strip()), qty, str(don_gia_vnd)])
            changed=True; continue
        new_rows.append(r)
    if changed:
        tmp=path+'.tmp'
        with _file_lock(path):
            with open(tmp,'w',newline='',encoding='utf-8') as f:
                csv.writer(f).writerows(new_rows)
            os.replace(tmp,path)
        _invalidate_month_cache()
    return changed

def read_water_items() -> List[Dict[str, Any]]:
    ensure_water_items_file()
    path = _abs_path(WATER_ITEMS_FILE)
    res: List[Dict[str, Any]] = []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                r['so_luong_ton'] = int(r.get('so_luong_ton','0') or 0)
            except ValueError:
                r['so_luong_ton'] = 0
            try:
                r['don_gia_vnd'] = int(r.get('don_gia_vnd','0') or 0)
            except ValueError:
                r['don_gia_vnd'] = 0
            res.append(r)
    return res

def delete_water_item(ten: str) -> bool:
    """Xóa hẳn 1 loại nước khỏi danh mục (nếu không còn xuất hiện trong bán hàng).
    Trả về True nếu xóa, False nếu không tìm thấy.
    Nếu vẫn còn bản ghi bán nước của loại này thì vẫn cho xóa (chỉ ảnh hưởng danh mục tương lai)."""
    ensure_water_items_file()
    ten = ten.strip().lower()
    if not ten:
        return False
    path = _abs_path(WATER_ITEMS_FILE)
    new_rows = []
    removed = False
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get('ten','').strip().lower() == ten:
                removed = True
                continue
            new_rows.append([r.get('ten',''), r.get('so_luong_ton','0'), r.get('don_gia_vnd','0')])
    if removed:
        tmp = path + '.tmp'
        with _file_lock(path):
            with open(tmp, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(WATER_ITEM_HEADERS)
                writer.writerows(new_rows)
            os.replace(tmp, path)
        _invalidate_month_cache()
    return removed

def record_water_sale(ngay: str, ten: str, so_luong: int):
    """Ghi nhận bán nước. Lấy đơn giá từ danh mục.
    Trả về thành tiền.
    """
    ten = _sanitize_text_cell(ten.strip())
    if not ten:
        raise ValueError("Chưa chọn loại nước")
    if so_luong <= 0:
        raise ValueError("Số lượng bán phải > 0")
    # ngày iso
    try:
        datetime.strptime(ngay, '%Y-%m-%d')
    except ValueError:
        raise ValueError('Ngày phải YYYY-MM-DD')
    items = read_water_items()
    match = None
    for i in items:
        if i.get('ten','').strip().lower() == ten.lower():
            match = i; break
    if not match:
        raise ValueError('Loại nước không tồn tại trong danh mục')
    if match['so_luong_ton'] < so_luong:
        raise ValueError('Không đủ số lượng tồn (còn %d)' % match['so_luong_ton'])
    don_gia = match['don_gia_vnd']
    tong = don_gia * so_luong
    # cập nhật tồn
    add_water_item(ten, -so_luong, don_gia)  # dùng cộng dồn với số âm
    ensure_water_sales_file()
    path = _abs_path(WATER_SALES_FILE)
    _safe_append_csv(path, [ngay, ten, str(so_luong), str(don_gia), str(tong)])
    _invalidate_month_cache()
    return tong

def read_water_sales() -> List[Dict[str, Any]]:
    ensure_water_sales_file()
    path = _abs_path(WATER_SALES_FILE)
    res: List[Dict[str, Any]] = []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            for k in ('so_luong','don_gia_vnd','tong_vnd'):
                try:
                    r[k] = int(r.get(k,'0') or 0)
                except ValueError:
                    r[k] = 0
            res.append(r)
    return res

def delete_water_sale(ngay: str, ten: str, so_luong: int, don_gia_vnd: int) -> bool:
    """Xóa 1 dòng bán nước chính xác (match đủ 4 trường). Đồng thời hoàn lại tồn kho.
    Trả về True nếu xóa."""
    ensure_water_sales_file(); ensure_water_items_file()
    path = _abs_path(WATER_SALES_FILE)
    rows = []
    removed = False
    target = (ngay, ten.strip(), str(so_luong), str(don_gia_vnd), str(so_luong*don_gia_vnd))
    # đọc và lọc
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if tuple(row) == target and not removed:
                removed = True
                continue
            rows.append(row)
    if removed:
        # hoàn kho
        add_water_item(ten, so_luong, don_gia_vnd)
        tmp = path + '.tmp'
        with _file_lock(path):
            with open(tmp, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(WATER_SALE_HEADERS)
                writer.writerows(rows)
            os.replace(tmp, path)
        _invalidate_month_cache()
    return removed

def day_water_sales(ngay: str) -> List[Dict[str, Any]]:
    return [r for r in read_water_sales() if r.get('ngay') == ngay]

def aggregate_day_water_sales(ngay: str) -> List[Dict[str, Any]]:
    aggr: Dict[str, Dict[str, Any]] = {}
    for r in day_water_sales(ngay):
        name = r.get('ten','')
        if name not in aggr:
            aggr[name] = {'ten': name, 'so_luong': 0, 'don_gia_vnd': r.get('don_gia_vnd',0), 'tong_vnd': 0}
        aggr[name]['so_luong'] += r.get('so_luong',0)
        aggr[name]['tong_vnd'] += r.get('tong_vnd',0)
    return list(aggr.values())


# ---------------------- SAFE FILE OPS ----------------------
@contextmanager
def _file_lock(path: str, retries: int = 12, delay: float = 0.1):
    """Khóa file đơn giản bằng .lock cạnh file.
    Không tuyệt đối an toàn nhưng giảm race khi 2 tiến trình ghi.
    Nếu không lock được sau retries -> cảnh báo & tiếp tục (fail-open)."""
    lock_path = path + '.lock'
    acquired = False
    for _ in range(retries):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            time.sleep(delay)
    if not acquired:
        logger.warning("_file_lock: không acquire được lock %s (tiếp tục không khóa)", lock_path)
    try:
        yield
    finally:
        if acquired:
            try:
                os.remove(lock_path)
            except OSError:
                pass

def _safe_append_csv(path: str, row: List[str]):
    for attempt in range(SAFE_WRITE_RETRY):
        try:
            with _file_lock(path):
                with open(path, "a", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(row)
            return
        except PermissionError:
            if attempt == SAFE_WRITE_RETRY - 1:
                raise PermissionError("Không thể ghi file (có thể đang mở trong Excel). Hãy đóng file và thử lại.")
            time.sleep(SAFE_WRITE_DELAY)

def verify_data_integrity() -> Dict[str, Any]:
    """Kiểm tra nhanh tình trạng dữ liệu (read-only).
    Trả về dict gồm:
      - total_records
      - overlap_count & overlap_pairs
      - missing_id_count (nếu header có record_id)
      - has_record_id_header
    Không chỉnh sửa dữ liệu."""
    recs = get_daily_records(force_reload=True)
    overlaps = []
    by_key: Dict[Tuple[str,str], List[DailyRecord]] = defaultdict(list)
    # Kiểm tra thiếu id khi header có record_id
    missing_id = 0
    path = _abs_path(DAILY_FILE)
    has_id_header = False
    try:
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, [])
            has_id_header = 'record_id' in header
            if has_id_header:
                for row in reader:
                    if len(row) >= len(header) and row and row[-1].strip() == '':
                        missing_id += 1
    except Exception:
        pass
    for r in recs:
        by_key[(r.ngay, r.san)].append(r)
    for (ngay, san), lst in by_key.items():
        slots = [x.khung_gio for x in lst]
        for i in range(len(slots)):
            for j in range(i+1, len(slots)):
                if _time_overlap(slots[i], slots[j]):
                    overlaps.append({'ngay': ngay, 'san': san, 'slot1': slots[i], 'slot2': slots[j]})
    return {
        'total_records': len(recs),
        'overlap_count': len(overlaps),
        'overlap_pairs': overlaps,
        'missing_id_count': missing_id,
        'has_record_id_header': has_id_header,
    }

__all__ = [
    # -------- Daily core --------
    "append_daily_record", "read_daily_records_dict", "compute_daily_total", "compute_month_total",
    # -------- Financial & Monthly --------
    "format_currency", "compute_profit", "save_monthly_stat", "read_monthly_stats",
    # -------- Safety / Helpers (additive) --------
    "parse_currency_any", "_sanitize_text_cell", "verify_data_integrity",
    # -------- Date / Slot utilities --------
    "today_str", "validate_time_slot", "normalize_time_slot", "delete_daily_record", "undo_last_action", "breakdown_daily_by_court", "backup_data", "month_breakdown_by_court", "compute_profit_shares",
    # -------- Date conversions --------
    "to_ui_date", "to_iso_date", "to_ui_month", "to_iso_month",
    # -------- Subscriptions --------
    "compute_subscription_price", "add_month_subscription", "read_month_subscriptions", "compute_month_subscription_total", "delete_month_subscription",
    # -------- Water sales --------
    "add_water_item","read_water_items","record_water_sale","read_water_sales","aggregate_day_water_sales","day_water_sales","compute_month_water_sales_total",
    # -------- Edit helpers --------
    "update_daily_record","update_monthly_stat","update_month_subscription","update_water_item",
    # --- ID precise helpers (additive) ---
    "delete_daily_record_by_id","find_daily_record_by_id"
]

# ---------------------- GỢI Ý GIÁ THEO BẢNG ----------------------
# Bảng giá (đơn vị VND) (thứ 2-6). Tạm áp dụng cho mọi ngày nếu chưa quy định cuối tuần.
WEEKDAY_PLAY_DAY = 100_000
WEEKDAY_PLAY_EVE = 120_000
WEEKDAY_PRACTICE_DAY = 60_000
WEEKDAY_PRACTICE_EVE = 80_000

def suggest_price(ngay: str, khung_gio: str, loai: str) -> Optional[int]:
    try:
        datetime.strptime(ngay, "%Y-%m-%d")
    except Exception:
        return None
    try:
        slot = normalize_time_slot(khung_gio)
    except Exception:
        return None
    start = int(slot.split('-')[0].rstrip('h'))
    is_evening = start >= 17
    l = loai.strip().lower()
    if l == 'chơi':
        return WEEKDAY_PLAY_EVE if is_evening else WEEKDAY_PLAY_DAY
    if l == 'tập':
        return WEEKDAY_PRACTICE_EVE if is_evening else WEEKDAY_PRACTICE_DAY
    return None

__all__.append('suggest_price')
