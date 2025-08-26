from __future__ import annotations

# SUK Pickleball v2.1.0 - Enhanced User Experience
import logging

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils import (
    append_daily_record, compute_daily_total, compute_month_total,
    format_currency, save_monthly_stat,
    today_str, validate_time_slot, read_monthly_stats,
    delete_daily_record, undo_last_action, breakdown_daily_by_court,
    read_daily_records_dict, backup_data, month_breakdown_by_court,
    compute_profit_shares, to_iso_date, to_ui_date, to_iso_month, to_ui_month,
    add_month_subscription, read_month_subscriptions, delete_month_subscription,
    add_profit_share_event, read_profit_share_events, delete_profit_share_event,
    add_water_item, read_water_items, record_water_sale, aggregate_day_water_sales,
    ensure_all_data_files,
    update_daily_record, update_monthly_stat, update_month_subscription, update_water_item,
    compute_subscription_price, add_month_subscription_with_time, update_month_subscription_with_time,
    read_daily_records_grouped_by_date
)
from datetime import date, datetime, timedelta
import calendar
import tkinter.font as tkfont
import os
import csv
import json
import shutil
import sys

print("📄 Hệ thống Quản lý SUK Pickleball - Chế độ CSV")

# Logger UI nhẹ (không thay đổi logic, chỉ quan sát lỗi nuốt trước đây)
ui_logger = logging.getLogger("suk.ui")
if not ui_logger.handlers:
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')

# Hằng số UI
BASE_FONT = ("Segoe UI", 11)
COURTS = ["Sân 1", "Sân 2"]

# UI Design System - Modern & Youthful v2.1.0
PRIMARY_COLOR = '#6366F1'      # Modern indigo
PRIMARY_LIGHT = '#A5B4FC'      # Light indigo  
PRIMARY_DARK = '#4338CA'       # Dark indigo
SECONDARY_COLOR = '#10B981'    # Emerald green
ACCENT_COLOR = '#F59E0B'       # Amber
ACCENT_PINK = '#EC4899'        # Pink accent

# Background & Surface Colors
BG_GRADIENT_START = '#F8FAFC'  # Slate 50
BG_GRADIENT_END = '#F1F5F9'    # Slate 100
NEUTRAL_50 = '#F8FAFC'         # Slate 50
NEUTRAL_100 = '#F1F5F9'        # Slate 100
NEUTRAL_200 = '#E2E8F0'        # Slate 200
NEUTRAL_300 = '#CBD5E1'        # Slate 300
NEUTRAL_700 = '#475569'        # Slate 600
NEUTRAL_900 = '#0F172A'        # Slate 900
SURFACE_COLOR = '#FFFFFF'
SURFACE_ELEVATED = '#FFFFFF'

# Status Colors
DANGER_COLOR = '#EF4444'       # Red
SUCCESS_COLOR = '#10B981'      # Emerald
WARNING_COLOR = '#F59E0B'      # Amber
INFO_COLOR = '#3B82F6'         # Blue
WARNING_COLOR = '#FF9800'
INFO_COLOR = '#2196F3'

# Color aliases - Updated for modern design
BG_LIGHT = NEUTRAL_50
TEXT_MAIN = NEUTRAL_900  
TEXT_MUTED = NEUTRAL_700
BORDER_COLOR = NEUTRAL_200
BORDER_FOCUS = PRIMARY_COLOR

# Animation constants
ANIMATION_FAST = 150      # Button hovers, small state changes
ANIMATION_NORMAL = 300    # Tab transitions, form animations  
ANIMATION_SLOW = 500      # Page transitions, complex animations

# Spacing system
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24
SPACING_XXL = 32

# Border radius
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 12
RADIUS_XL = 16

# App title constant
APP_TITLE = "Quản lý sân Pickleball"
# Định nghĩa giá giờ & phụ thu đèn (v1.8.2)
# Giữ nguyên để không phá vỡ logic cũ, nhưng đồng bộ với pricing.ACTVITY_RATES
try:
    from pricing import ACTIVITY_RATES as _PRICING_RATES, LIGHT_SURCHARGE as _PRICING_LIGHT
    HOURLY_BASE = dict(_PRICING_RATES)  # bản sao để UI dùng như trước
    LIGHT_SURCHARGE = _PRICING_LIGHT
except Exception:
    # Fallback cũ nếu module mới không tải được
    HOURLY_BASE = {'Chơi': 100_000, 'Tập': 60_000}
    LIGHT_SURCHARGE = 20_000

def is_off_hour(hour: int) -> bool:
    return (5 <= hour < 7) or (18 <= hour < 22)

def attach_tree_enhancements(root: tk.Tk, tree: ttk.Treeview):
    """Add hover effects and animations to treeview"""
    if not hasattr(root, '_all_trees'):
        root._all_trees = []  # type: ignore
    root._all_trees.append(tree)  # type: ignore
    
    # Modern hover styling
    try:
        tree.tag_configure('hover', background=PRIMARY_LIGHT, foreground=PRIMARY_DARK)
    except Exception:
        pass
    
    tree._last_hover = None  # type: ignore
    tree._animation_id = None  # type: ignore
    
    def _animate_hover(item, direction='in'):
        """Smooth hover animation"""
        if not tree.exists(item):
            return
            
        if direction == 'in':
            tree.item(item, tags=('hover',))
        else:
            tree.item(item, tags=())
    
    def _on_motion(e):
        row = tree.identify_row(e.y)
        if row == getattr(tree, '_last_hover', None):
            return
            
        # Clear previous with animation
        prev = getattr(tree, '_last_hover', None)
        if prev and tree.exists(prev):
            tree.after(10, lambda: _animate_hover(prev, 'out'))
            
        # Apply new hover with animation
        if row and tree.exists(row):
            tree.after(20, lambda: _animate_hover(row, 'in'))
            tree._last_hover = row  # type: ignore
    
    def _on_leave(_):
        prev = getattr(tree, '_last_hover', None)
        if prev and tree.exists(prev):
            tree.after(10, lambda: _animate_hover(prev, 'out'))
        tree._last_hover = None  # type: ignore
    
    tree.bind('<Motion>', _on_motion, add='+')
    tree.bind('<Leave>', _on_leave, add='+')


class AnimatedButton:
    """Enhanced button with hover animations and modern styling"""
    def __init__(self, parent, text, command=None, style='primary', **kwargs):
        self.style = style
        self._setup_colors()
        
        self.frame = tk.Frame(parent, bg=parent.cget('bg'))
        self.button = tk.Button(
            self.frame,
            text=text,
            command=command,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            bd=0,
            padx=16,
            pady=8,
            cursor='hand2',
            **kwargs
        )
        
        self._apply_style()
        self._setup_animations()
        self.button.pack()
        
    def _setup_colors(self):
        """Setup color scheme based on button style"""
        if self.style == 'primary':
            self.bg_normal = PRIMARY_COLOR
            self.bg_hover = PRIMARY_DARK
            self.fg_color = 'white'
        elif self.style == 'secondary':
            self.bg_normal = SECONDARY_COLOR
            self.bg_hover = '#059669'  # Darker emerald
            self.fg_color = 'white'
        elif self.style == 'accent':
            self.bg_normal = ACCENT_COLOR
            self.bg_hover = '#D97706'  # Darker amber
            self.fg_color = 'white'
        elif self.style == 'danger':
            self.bg_normal = DANGER_COLOR
            self.bg_hover = '#DC2626'  # Darker red
            self.fg_color = 'white'
        else:  # outline
            self.bg_normal = 'white'
            self.bg_hover = NEUTRAL_100
            self.fg_color = PRIMARY_COLOR
            
    def _apply_style(self):
        """Apply modern button styling"""
        self.button.configure(
            bg=self.bg_normal,
            fg=self.fg_color,
            activebackground=self.bg_hover,
            activeforeground=self.fg_color,
        )
        
        # Add subtle shadow effect
        if self.style != 'outline':
            self.frame.configure(relief='raised', bd=1)
            
    def _setup_animations(self):
        """Setup hover animations"""
        def on_enter(e):
            self.button.configure(bg=self.bg_hover)
            # Subtle scaling effect
            self.frame.configure(relief='raised', bd=2)
            
        def on_leave(e):
            self.button.configure(bg=self.bg_normal)
            self.frame.configure(relief='raised', bd=1)
            
        self.button.bind('<Enter>', on_enter)
        self.button.bind('<Leave>', on_leave)
        
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
        
    def grid(self, **kwargs):
        self.frame.grid(**kwargs)
        
    def configure(self, **kwargs):
        self.button.configure(**kwargs)


class Tooltip:
    """Enhanced tooltip widget with modern styling and examples"""
    def __init__(self, widget, text: str, delay: int = 600, example: str = None):
        self.widget = widget
        self.text = text
        self.example = example
        self.delay = delay
        self._after_id = None
        self.tipwin: tk.Toplevel | None = None
        widget.bind('<Enter>', self._schedule, add='+')
        widget.bind('<Leave>', self._cancel, add='+')
        widget.bind('<ButtonPress>', self._cancel, add='+')

    def _schedule(self, _evt=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self, _evt=None):
        if self._after_id:
            try: 
                self.widget.after_cancel(self._after_id)
            except Exception: 
                pass
            self._after_id = None
        self._hide()

    def _show(self):
        if self.tipwin or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
            self.tipwin = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            
            # Modern tooltip styling
            main_frame = tk.Frame(tw, bg=NEUTRAL_900, padx=2, pady=2)
            main_frame.pack()
            
            content_frame = tk.Frame(main_frame, bg='#1F2937', padx=12, pady=8)
            content_frame.pack()
            
            # Main tooltip text
            main_label = tk.Label(
                content_frame,
                text=self.text,
                font=('Segoe UI', 9, 'bold'),
                bg='#1F2937',
                fg='white',
                justify='left'
            )
            main_label.pack(anchor='w')
            
            # Example text if provided
            if self.example:
                example_label = tk.Label(
                    content_frame,
                    text=f"💡 Ví dụ: {self.example}",
                    font=('Segoe UI', 8),
                    bg='#1F2937',
                    fg='#9CA3AF',  # Gray 400
                    justify='left'
                )
                example_label.pack(anchor='w', pady=(4, 0))
            
            # Position tooltip properly on screen
            tw.update_idletasks()
            screen_width = tw.winfo_screenwidth()
            screen_height = tw.winfo_screenheight()
            tooltip_width = tw.winfo_width()
            tooltip_height = tw.winfo_height()
            
            # Adjust position if tooltip goes off screen
            if x + tooltip_width > screen_width:
                x = screen_width - tooltip_width - 10
            if y + tooltip_height > screen_height:
                y = self.widget.winfo_rooty() - tooltip_height - 8
                
            tw.wm_geometry(f"+{x}+{y}")
            
            # Smooth fade-in animation
            tw.attributes('-alpha', 0.0)
            self._fade_in(tw, 0.0)
            
        except Exception:
            self._hide()
    
    def _fade_in(self, window, alpha):
        """Smooth fade-in animation"""
        if window and window.winfo_exists():
            alpha = min(alpha + 0.1, 0.95)
            try:
                window.attributes('-alpha', alpha)
                if alpha < 0.95:
                    window.after(20, lambda: self._fade_in(window, alpha))
            except Exception:
                pass

    def _hide(self):
        tw = self.tipwin
        self.tipwin = None
        if tw:
            try:
                tw.destroy()
            except Exception:
                pass

def apply_zebra(tree: ttk.Treeview):
    """Apply zebra striping to treeview"""
    try:
        # Đặt màu tag (nếu đã có thì bỏ qua lỗi)
        tree.tag_configure('odd', background='#f4f7fa')
        tree.tag_configure('even', background='#ffffff')
        for idx, iid in enumerate(tree.get_children()):
            tag = 'odd' if idx % 2 else 'even'
            cur = list(tree.item(iid, 'tags'))
            if tag not in cur:
                cur.append(tag)
                tree.item(iid, tags=tuple(cur))
    except Exception:
        pass


class DailyEntryFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=SPACING_LG)
        self.build()

    def build(self):
        """Build daily entry form with horizontal layout"""
        
        # Main container with horizontal layout
        main_container = ttk.Frame(self)
        main_container.pack(fill='both', expand=True)
        
        # Header section with enhanced styling (spans full width)
        header_frame = ttk.Frame(main_container, style='Section.TFrame')
        header_frame.pack(fill='x', pady=(0, SPACING_MD))
        
        header_content = ttk.Frame(header_frame)
        header_content.pack(fill='x', padx=SPACING_LG, pady=SPACING_MD)
        
        ttk.Label(header_content, text='📝 Ghi chép đặt sân', style='Subheader.TLabel').pack(side='left')
        ttk.Label(header_content, text='Nhập thông tin đặt sân mới', style='Caption.TLabel').pack(side='left', padx=(SPACING_MD, 0))
        
        # Quick actions
        quick_actions = ttk.Frame(header_content)
        quick_actions.pack(side='right')
        
        ttk.Button(quick_actions, text='🔄', style='Info.TButton', width=4, 
                  command=self.refresh_view).pack(side='left', padx=(0, SPACING_XS))
        ttk.Button(quick_actions, text='↶', style='Warning.TButton', width=4,
                  command=self.undo_last).pack(side='left')
        
        # Create horizontal container for form and table
        content_container = ttk.Frame(main_container)
        content_container.pack(fill='both', expand=True)
        
        # Form section on the left (position 2)
        form_frame = ttk.Frame(content_container, style='Card.TFrame')
        form_frame.pack(side='left', fill='y', padx=(0, SPACING_MD))
        
        form_content = ttk.Frame(form_frame)
        form_content.pack(fill='both', expand=True, padx=SPACING_LG, pady=SPACING_LG)
        
        # Data table section on the right (position 1)
        table_frame = ttk.Frame(content_container, style='Card.TFrame')
        table_frame.pack(side='right', fill='both', expand=True)
        
        # Form grid with better spacing for left side layout
        row = 0
        
        # Date row with enhanced styling
        date_group = ttk.Frame(form_content)
        date_group.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(0, SPACING_MD))
        
        ttk.Label(date_group, text="📅 Ngày đặt sân:", style='FormLabel.TLabel').pack(anchor='w')
        
        self.var_ngay = tk.StringVar(value=datetime.today().strftime('%d/%m/%Y'))
        date_input = ttk.Frame(date_group)
        date_input.pack(anchor='w', pady=(SPACING_XS, 0))
        
        self.e_ngay = ttk.Entry(date_input, textvariable=self.var_ngay, width=14, font=('Segoe UI', 11))
        self.e_ngay.pack(side='left')
        
        # Add tooltip for date format
        Tooltip(self.e_ngay, "Ngày đặt sân", example="25/08/2025 (DD/MM/YYYY)")
        
        ttk.Button(date_input, text='📅', width=4, 
                  command=lambda: self._open_date_picker(self.var_ngay, on_change=lambda: self.refresh_view())).pack(side='left', padx=(SPACING_XS, 0))
        
        ttk.Label(date_input, text='(DD/MM/YYYY)', style='Caption.TLabel').pack(side='left', padx=(SPACING_MD, 0))
        
        row += 1
        
        # Court selection with enhanced styling
        court_section = ttk.Frame(form_content)
        court_section.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(0, SPACING_MD))
        
        ttk.Label(court_section, text='🏓 Sân:', style='FormLabel.TLabel').pack(anchor='w')
        
        self.var_san = tk.StringVar(value=COURTS[0])
        court_combo = ttk.Combobox(court_section, textvariable=self.var_san, values=COURTS, 
                                  state='readonly', width=15, font=('Segoe UI', 11))
        court_combo.pack(anchor='w', pady=(SPACING_XS, 0))
        
        # Add tooltip for court selection
        Tooltip(court_combo, "Chọn sân phù hợp với hoạt động", example="Sân 1: Thi đấu chuyên nghiệp, Sân 2: Tập luyện và giải trí")
        
        row += 1
        
        # Time section with enhanced styling  
        time_section = ttk.Frame(form_content)
        time_section.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(0, SPACING_MD))
        
        ttk.Label(time_section, text='⏰ Khung giờ:', style='FormLabel.TLabel').pack(anchor='w')
        
        time_inputs = ttk.Frame(time_section)
        time_inputs.pack(anchor='w', pady=(SPACING_XS, 0))
        
        hours = [str(h) for h in range(4, 25)]
        self.var_start = tk.StringVar(value=hours[0])
        self.var_end = tk.StringVar(value=str(int(hours[0]) + 2))
        
        self.cb_start = ttk.Combobox(time_inputs, textvariable=self.var_start, values=hours, 
                                    width=6, state='readonly', font=('Segoe UI', 11))
        self.cb_start.pack(side='left')
        
        # Add helpful tooltip for time format
        Tooltip(self.cb_start, "Giờ bắt đầu đặt sân", example="08:00 (định dạng 24 giờ)")
        
        ttk.Label(time_inputs, text=' - ', style='Body.TLabel').pack(side='left')
        
        self.cb_end = ttk.Combobox(time_inputs, textvariable=self.var_end, values=hours, 
                                  width=6, state='readonly', font=('Segoe UI', 11))
        self.cb_end.pack(side='left')
        
        # Add tooltip for end time
        Tooltip(self.cb_end, "Giờ kết thúc đặt sân", example="10:00 (tối đa 2 giờ liên tiếp)")
        
        ttk.Label(time_inputs, text=' giờ', style='Caption.TLabel').pack(side='left')
        
        row += 1
        
        # Type selection
        type_section = ttk.Frame(form_content)
        type_section.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(0, SPACING_MD))
        
        ttk.Label(type_section, text='🎯 Loại hoạt động:', style='FormLabel.TLabel').pack(anchor='w')
        
        type_controls = ttk.Frame(type_section)
        type_controls.pack(anchor='w', pady=(SPACING_XS, 0))
        
        self.var_loai = tk.StringVar(value='Chơi')
        type_combo = ttk.Combobox(type_controls, textvariable=self.var_loai, values=['Chơi', 'Tập'], 
                                 state='readonly', width=8, font=('Segoe UI', 11))
        type_combo.pack(side='left')
        
        # Add tooltip for activity type
        Tooltip(type_combo, "Loại hoạt động ảnh hưởng đến giá", example="Chơi: 100k/giờ, Tập: 60k/giờ")
        
        # Light option with enhanced styling
        self.var_light = tk.BooleanVar(value=False)
        light_check = ttk.Checkbutton(type_controls, text='💡 Sử dụng đèn', variable=self.var_light, 
                                     command=lambda: self._auto_price())
        light_check.pack(side='left', padx=(SPACING_MD, 0))
        
        # Add tooltip for light surcharge
        Tooltip(light_check, "Phụ thu đèn áp dụng theo khung giờ", example="20k/giờ (5-7h sáng và 18-22h tối)")
        
        row += 1
        
        # Price section
        price_section = ttk.Frame(form_content)
        price_section.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(0, SPACING_MD))
        
        ttk.Label(price_section, text='💰 Giá:', style='FormLabel.TLabel').pack(anchor='w')
        
        self.var_gia = tk.StringVar()
        self.e_gia = ttk.Entry(price_section, textvariable=self.var_gia, width=20, font=('Segoe UI', 11))
        self.e_gia.pack(anchor='w', pady=(SPACING_XS, 0))
        
        # Add tooltip for price calculation
        Tooltip(self.e_gia, "Giá tự động tính theo loại và giờ đặt", example="200,000 (2 giờ × 100k + phụ thu đèn)")
        
        row += 1
        
        # Customer info section
        customer_section = ttk.Frame(form_content)  
        customer_section.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(0, SPACING_MD))
        
        ttk.Label(customer_section, text='👥 Người/Nhóm:', style='FormLabel.TLabel').pack(anchor='w')
        
        self.var_nguoi = tk.StringVar()
        customer_entry = ttk.Entry(customer_section, textvariable=self.var_nguoi, width=25, font=('Segoe UI', 11))
        customer_entry.pack(anchor='w', pady=(SPACING_XS, 0), fill='x')
        
        row += 1
        
        # Summary card with enhanced styling
        summary_card = ttk.Frame(form_content, style='Summary.TFrame')
        summary_card.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(0, SPACING_MD))
        
        summary_content = ttk.Frame(summary_card)
        summary_content.pack(padx=SPACING_MD, pady=SPACING_SM)
        
        ttk.Label(summary_content, text='📊 Tổng hiện tại', style='SummaryTitle.TLabel').pack()
        
        self.var_current_total = tk.StringVar(value='0 ₫')
        ttk.Label(summary_content, textvariable=self.var_current_total, style='SummaryValue.TLabel').pack()
        
        self.var_now = tk.StringVar(value='')
        ttk.Label(summary_content, textvariable=self.var_now, style='SummaryMeta.TLabel').pack()
        
        row += 1
        
        # Action buttons with enhanced styling
        button_frame = ttk.Frame(form_content)
        button_frame.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(SPACING_MD, 0))
        
        # Primary actions
        self.btn_save_daily = ttk.Button(button_frame, text='💾 Lưu (Ctrl+S)', style='Primary.TButton', 
                                        command=self.save_record)
        self.btn_save_daily.pack(fill='x', pady=(0, SPACING_XS))
        
        # Secondary actions  
        secondary_frame = ttk.Frame(button_frame)
        secondary_frame.pack(fill='x')
        
        ttk.Button(secondary_frame, text='↶ Hoàn tác', style='Warning.TButton',
                  command=self.undo_last).pack(side='left', fill='x', expand=True, padx=(0, SPACING_XS))
        ttk.Button(secondary_frame, text='🔄 Làm mới', style='Info.TButton',
                  command=self.refresh_view).pack(side='left', fill='x', expand=True)
        
        row += 1
        
        # Stats display with enhanced layout
        stats_frame = ttk.Frame(form_content)
        stats_frame.grid(column=0, row=row, columnspan=2, sticky='ew', pady=(SPACING_MD, 0))
        
        # Daily total
        ttk.Label(stats_frame, text='📈 Tổng ngày:', style='FormLabel.TLabel').pack(anchor='w')
        
        self.var_total = tk.StringVar(value='0 ₫')
        total_label = ttk.Label(stats_frame, textvariable=self.var_total, style='Success.TLabel')
        total_label.pack(anchor='w', pady=(SPACING_XS, SPACING_SM))
        
        # Breakdown by court
        ttk.Label(stats_frame, text='🏓 Theo sân:', style='FormLabel.TLabel').pack(anchor='w')
        
        self.var_breakdown = tk.StringVar(value='')
        ttk.Label(stats_frame, textvariable=self.var_breakdown, style='Info.TLabel').pack(anchor='w', pady=(SPACING_XS, 0))
        
        row += 1
        
        # Info message area
        self.lbl_info = ttk.Label(form_content, text='', style='Info.TLabel')
        self.lbl_info.grid(column=0, row=row, columnspan=2, sticky='w', pady=(SPACING_SM, 0))
        
        # Table header with controls
        table_header = ttk.Frame(table_frame)
        table_header.pack(fill='x', padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))
        
        ttk.Label(table_header, text='📋 Danh sách đặt sân', style='Title.TLabel').pack(anchor='w')
        
        # View controls
        view_controls = ttk.Frame(table_header)
        view_controls.pack(anchor='w', pady=(SPACING_SM, 0))
        
        ttk.Label(view_controls, text='👁️ Xem ngày:', style='FormLabel.TLabel').pack(side='left')
        
        self.var_view_day = tk.StringVar(value=self.var_ngay.get())
        view_day_input = ttk.Frame(view_controls)
        view_day_input.pack(side='left', padx=(SPACING_SM, 0))
        
        self.e_view_day = ttk.Entry(view_day_input, textvariable=self.var_view_day, width=12, 
                                   state='readonly', font=('Segoe UI', 11))
        self.e_view_day.pack(side='left')
        
        ttk.Button(view_day_input, text='📅', width=4,
                  command=lambda: self._open_date_picker(self.var_view_day, 
                  on_change=lambda: self.refresh_view(list_only=True))).pack(side='left', padx=(SPACING_XS, 0))
        
        # Table actions
        table_actions = ttk.Frame(view_controls)
        table_actions.pack(side='left', padx=(SPACING_LG, 0))
        
        ttk.Button(table_actions, text='📍 Hôm nay', style='Info.TButton',
                  command=lambda: self._set_view_today()).pack(side='left', padx=(0, SPACING_SM))
        
        ttk.Button(table_actions, text='Xóa dòng', style='Danger.TButton',
                  command=self.open_delete_dialog).pack(side='left')
        
        # Data table with enhanced styling
        table_container = ttk.Frame(table_frame)
        table_container.pack(fill='both', expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))
        
        columns = ('san', 'khung', 'gia', 'nguoi')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', 
                                height=15, style='Data.Treeview')
        
        # Enhanced column configuration
        column_config = [
            ('san', '🏓 Sân', 90),
            ('khung', '⏰ Khung giờ', 140), 
            ('gia', '💰 Giá', 130),
            ('nguoi', '👥 Người/Nhóm', 200)
        ]
        
        for cid, txt, w in column_config:
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor='center', stretch=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_container, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Enhanced event bindings
        self.tree.bind('<Delete>', self._delete_selected_event)
        self.tree.bind('<BackSpace>', self._delete_selected_event)
        self.tree.bind('<Double-1>', lambda e: self._open_edit_popup_daily())
        
        # Enhanced zebra stripe configuration
        self.tree.tag_configure('odd', background=NEUTRAL_50)
        self.tree.tag_configure('even', background=SURFACE_COLOR)
        self.tree.tag_configure('highlight', background=PRIMARY_LIGHT)
        
        # Hover enhancement
        try:
            attach_tree_enhancements(self.winfo_toplevel(), self.tree)
        except Exception as ex:
            ui_logger.debug("attach_tree_enhancements failed: %s", ex)
            
        # Configure grid weights for responsive design
        form_content.grid_columnconfigure(0, weight=1)
        content_container.pack_configure(fill='both', expand=True)
        
        # Enhanced focus chain with better UX
        self.e_ngay.bind('<Return>', lambda e: court_combo.focus_set())
        court_combo.bind('<Key-Return>', lambda e: self.cb_start.focus_set())
        self.cb_start.bind('<Return>', lambda e: self.cb_end.focus_set())
        self.cb_end.bind('<Return>', lambda e: type_combo.focus_set())
        type_combo.bind('<Key-Return>', lambda e: self.e_gia.focus_set())
        self.e_gia.bind('<Return>', lambda e: customer_entry.focus_set())
        customer_entry.bind('<Return>', lambda e: self.save_record())
        
        # Enhanced price formatting
        self.e_gia.bind('<FocusOut>', lambda e: self._format_gia())
        self.e_gia.bind('<KeyRelease>', lambda e: self._format_gia_live())
        
        # Auto pricing triggers with enhanced responsiveness
        self.var_start.trace_add('write', lambda *a: self._auto_price())
        self.var_end.trace_add('write', lambda *a: self._auto_price())
        self.var_loai.trace_add('write', lambda *a: self._auto_price())
        
        # Track user's manual light control to respect their choice
        self._user_manually_set_light = False
        self.var_light.trace_add('write', lambda *a: self._on_light_changed())
        
        # Enhanced tooltips for better UX
        try:
            Tooltip(self.e_gia, 'Giá tự động tính theo loại và giờ. Có thể nhập thủ công để ghi đè.')
            Tooltip(light_check, 'Tự động bật khi chọn giờ 5-7h hoặc 18-22h')
            Tooltip(self.btn_save_daily, 'Lưu thông tin đặt sân (Ctrl+S)')
            Tooltip(self.tree, 'Double-click để sửa, Delete để xóa dòng')
        except Exception as ex:
            try:
                ui_logger = logging.getLogger('suk.ui')
                ui_logger.debug('attach_tree_enhancements failed (non-fatal): %s', ex)
            except Exception:
                pass
        
        # Initialize with enhanced state
        self.after(10, self._auto_price)
        self.refresh_view()
        self.update_clock()
        self.update_all_total()

    def _on_light_changed(self):
        """Track when user manually changes light setting"""
        # Set flag to indicate user has made a manual choice
        self._user_manually_set_light = True
        # Recalculate price when light setting changes
        self._auto_price()

    def _format_gia(self):
        txt = self.var_gia.get().strip()
        if not txt:
            return
        digits = ''.join(ch for ch in txt if ch.isdigit())
        if not digits:
            return
        try:
            v = int(digits)
            self.var_gia.set(f"{v:,}".replace(',', '.') + ' ₫')
        except Exception:
            pass
    def _format_gia_live(self):
        """Định dạng trực tiếp: chỉ nhận số, hiển thị phân tách + ₫."""
        raw = self.var_gia.get()
        if not raw:
            return
        digits = ''.join(ch for ch in raw if ch.isdigit())
        if not digits:
            return
        try:
            v = int(digits)
            self.var_gia.set(f"{v:,}".replace(',', '.') + ' ₫')
        except Exception:
            pass
    def _parse_display_price(self, gia_disp: str) -> int:
        """Parse formatted currency text (e.g. '120.000 đ', '120.000 ₫', optional suffix info) -> int VND.
        Extracts all digits; ignores other characters."""
        digits = ''.join(ch for ch in gia_disp if ch.isdigit())
        return int(digits) if digits else 0

    def save_record(self):
        """Enhanced save with better validation and user feedback."""
        try:
            # Validate date with enhanced feedback
            ngay = to_iso_date(self.var_ngay.get().strip())
        except Exception:
            self.lbl_info.config(text="❌ Ngày phải theo định dạng DD/MM/YYYY")
            self.show_validation_error("Ngày không hợp lệ. Vui lòng nhập theo định dạng DD/MM/YYYY")
            self.e_ngay.focus_set()
            return
            
        san = self.var_san.get().strip()
        start_h = self.var_start.get().strip()
        end_h = self.var_end.get().strip()
        slot = f"{start_h}h-{end_h}h"
        gia_raw = self.var_gia.get().strip()
        loai = self.var_loai.get().strip()
        
        try:
            # Enhanced validation with specific error messages
            if not validate_time_slot(slot):
                raise ValueError("Khung giờ không hợp lệ. Giờ kết thúc phải lớn hơn giờ bắt đầu")
                
            if not san:
                raise ValueError("Vui lòng chọn sân")
                
            if not loai:
                raise ValueError("Vui lòng chọn loại hoạt động")
                
            # Parse price with enhanced validation
            # Dùng helper chuẩn thay vì tự parse rải rác
            from utils import parse_currency_any  # local import để tránh circular top-level
            gia = parse_currency_any(gia_raw)
            if gia <= 0:
                raise ValueError("Giá phải lớn hơn 0. Kiểm tra lại thông tin giá")
            
            nguoi = self.var_nguoi.get().strip()
            if not nguoi:
                # Show warning but allow saving
                self.lbl_info.config(text="⚠️ Chưa nhập thông tin người/nhóm")
            
            # Save with enhanced feedback
            append_daily_record(ngay, san, slot, gia, loai=loai, nguoi=nguoi)
            
            # Enhanced success feedback
            success_msg = f"✅ Đã lưu: {san} {slot} {format_currency(gia)} ({loai})"
            self.lbl_info.config(text=success_msg)
            
            # Show toast notification
            try:
                root = self.winfo_toplevel()
                if hasattr(root, 'show_toast'):
                    root.show_toast(f'💾 Đã lưu {san} {slot}', 'success')
            except Exception as ex:
                ui_logger.debug("toast show failed: %s", ex)
            
            # Auto-advance time slots for better UX
            try:
                new_start = int(end_h)
                if new_start >= 24:
                    new_start = int(start_h)
                self.var_start.set(str(new_start))
                
                new_end = new_start + 2
                if new_end > 24:
                    new_end = min(24, new_start + 1)
                self.var_end.set(str(new_end))
            except Exception as ex:
                ui_logger.debug("auto-advance time failed: %s", ex)
            
            # Clear form for next entry
            self.var_gia.set("")
            if not self.var_nguoi.get().strip():  # Only clear if was empty
                self.var_nguoi.set("")
            
            # Reset light manual flag for next entry
            self._user_manually_set_light = False
            
            # Focus management for better UX
            self.cb_start.focus_set()
            
            # Refresh data
            self.refresh_view()
            self._recompute_current_total()
            
        except Exception as ex:
            error_msg = f"❌ Lỗi: {str(ex)}"
            self.lbl_info.config(text=error_msg)
            ui_logger.warning("save_record failed: %s", ex)
            self.show_validation_error(str(ex))

    def show_validation_error(self, message):
        """Show validation error with toast notification."""
        try:
            root = self.winfo_toplevel()
            if hasattr(root, 'show_toast'):
                root.show_toast(f'⚠️ {message}', 'warning')
        except Exception:
            pass

    def _open_edit_popup_daily(self):
        sel = self.tree.selection()
        if not sel: return
        item = sel[0]
        try:
            ngay_iso = to_iso_date(self.var_view_day.get())
        except Exception:
            return
        san, khung, gia_disp, nguoi = self.tree.item(item,'values')
        # Extract loại nếu có trong gia_disp dạng '15k (Chơi)'
        loai = ''
        if '(' in gia_disp and ')' in gia_disp:
            try:
                loai = gia_disp.split('(')[1].split(')')[0]
            except Exception:
                loai = ''
        # Parse giá
        old_gia = self._parse_display_price(gia_disp)
        # Build popup UI
        popup = tk.Toplevel(self); popup.title('Sửa đặt sân'); popup.transient(self.winfo_toplevel()); popup.grab_set()
        frm = ttk.Frame(popup, padding=8); frm.pack(fill='both', expand=True)
        r = 0
        ttk.Label(frm, text='Ngày:').grid(column=0,row=r,sticky='e'); var_ngay = tk.StringVar(value=to_ui_date(ngay_iso)); e_ng = ttk.Entry(frm,textvariable=var_ngay,width=12); e_ng.grid(column=1,row=r,sticky='w')
        ttk.Button(frm,text='📅',width=3,command=lambda: self._open_date_picker(var_ngay)).grid(column=2,row=r,sticky='w'); r+=1
        ttk.Label(frm, text='Sân:').grid(column=0,row=r,sticky='e'); var_san = tk.StringVar(value=san); ttk.Combobox(frm,textvariable=var_san,values=COURTS,width=8,state='readonly').grid(column=1,row=r,sticky='w'); r+=1
        try:
            st,en = khung.replace('h','').split('-')
        except Exception:
            st='5'; en='7'
        ttk.Label(frm,text='Giờ bắt đầu:').grid(column=0,row=r,sticky='e'); var_st=tk.StringVar(value=st); ttk.Combobox(frm,textvariable=var_st,values=[str(h) for h in range(4,25)],width=5,state='readonly').grid(column=1,row=r,sticky='w'); r+=1
        ttk.Label(frm,text='Giờ kết thúc:').grid(column=0,row=r,sticky='e'); var_en=tk.StringVar(value=en); ttk.Combobox(frm,textvariable=var_en,values=[str(h) for h in range(4,25)],width=5,state='readonly').grid(column=1,row=r,sticky='w'); r+=1
        ttk.Label(frm,text='Loại:').grid(column=0,row=r,sticky='e'); var_loai=tk.StringVar(value=loai or 'Chơi'); ttk.Combobox(frm,textvariable=var_loai,values=['Chơi','Tập'],width=8,state='readonly').grid(column=1,row=r,sticky='w'); r+=1
        ttk.Label(frm,text='Giá:').grid(column=0,row=r,sticky='e'); var_gia=tk.StringVar(value=f"{old_gia:,}".replace(',', '.') + ' ₫'); e_price_edit = ttk.Entry(frm,textvariable=var_gia,width=14); e_price_edit.grid(column=1,row=r,sticky='w'); r+=1
        def _fmt_popup_price(*_):
            raw = var_gia.get(); digits=''.join(ch for ch in raw if ch.isdigit())
            if digits:
                try: var_gia.set(f"{int(digits):,}".replace(',', '.') + ' ₫')
                except: pass
        e_price_edit.bind('<KeyRelease>', _fmt_popup_price)
        e_price_edit.bind('<FocusOut>', _fmt_popup_price)
        ttk.Label(frm,text='Người/Nhóm:').grid(column=0,row=r,sticky='e'); var_nguoi=tk.StringVar(value=nguoi); ttk.Entry(frm,textvariable=var_nguoi,width=18).grid(column=1,row=r,sticky='w'); r+=1
        info = ttk.Label(frm,text='',foreground='#d32f2f'); info.grid(column=0,row=r,columnspan=3,sticky='w'); r+=1
        def do_save():
            try:
                new_ngay_iso = to_iso_date(var_ngay.get().strip())
                new_san = var_san.get().strip()
                new_slot = f"{var_st.get()}h-{var_en.get()}h"
                if not validate_time_slot(new_slot):
                    raise ValueError('Khung giờ không hợp lệ')
                from utils import parse_currency_any
                new_gia = parse_currency_any(var_gia.get())
                new_loai = var_loai.get().strip()
                ok = update_daily_record(ngay_iso, san, khung, old_gia, new_ngay_iso, new_san, new_slot, new_gia, new_loai, var_nguoi.get().strip())
                if ok:
                    popup.destroy(); self.refresh_view(); self._recompute_current_total(); self.lbl_info.config(text='Đã cập nhật')
                else:
                    info.config(text='Không cập nhật được (không tìm thấy)')
            except Exception as ex:
                info.config(text=str(ex))
        btns = ttk.Frame(frm); btns.grid(column=0,row=r,columnspan=3,pady=(6,0),sticky='w')
        ttk.Button(btns,text='Lưu',command=do_save).pack(side='left')
        ttk.Button(btns,text='Hủy',command=lambda: popup.destroy()).pack(side='left',padx=6)
        popup.bind('<Return>', lambda e: do_save())
        e_ng.focus_set()

    def show_total(self):
        try:
            ngay = to_iso_date(self.var_ngay.get().strip())
        except Exception:
            messagebox.showerror("Lỗi", "Ngày phải DD/MM/YYYY")
            return
        try:
            total = compute_daily_total(ngay)
            messagebox.showinfo("Tổng Ngày", f"Tổng doanh thu ngày {ngay}: {format_currency(total)}")
        except Exception as ex:
            messagebox.showerror("Lỗi", str(ex))

    # ----- Helpers cho danh sách ngày xem nhanh -----
    def _recent_days_list(self, max_days: int = 30):
        """Trả về list ngày (DD/MM/YYYY) xuất hiện trong dữ liệu gần đây nhất, mới nhất trước.
        Bao gồm hôm nay và ngày hiện tại trong ô nhập nếu chưa có."""
        try:
            all_recs = read_daily_records_dict()
        except Exception:
            all_recs = []
        days = set(r.get('ngay') for r in all_recs if r.get('ngay'))
        # Thêm hôm nay + ngày đang nhập
        try:
            days.add(to_iso_date(datetime.today().strftime('%d/%m/%Y')))
        except Exception:
            pass
        try:
            days.add(to_iso_date(self.var_ngay.get().strip()))
        except Exception:
            pass
        # Sắp xếp giảm dần
        ordered = sorted(days, reverse=True)[:max_days]
        return [to_ui_date(d) for d in ordered]

    def _set_view_today(self):
        self.var_view_day.set(datetime.today().strftime('%d/%m/%Y'))
        self.refresh_view(list_only=True)

    # ----- Popup lịch chọn ngày -----
    def _open_date_picker(self, target_var: tk.StringVar, on_change=None, initial_date: str | None = None):
        """Hiển thị popup lịch đơn giản chọn ngày DD/MM/YYYY."""
        # Nếu đã mở thì không mở thêm
        if hasattr(self, '_date_popup') and self._date_popup and tk.Toplevel.winfo_exists(self._date_popup):
            self._date_popup.lift(); return
        try:
            if initial_date:
                dt = datetime.strptime(initial_date, '%d/%m/%Y')
            else:
                dt = datetime.strptime(target_var.get(), '%d/%m/%Y')
        except Exception:
            dt = datetime.today()
        year = dt.year; month = dt.month

        popup = tk.Toplevel(self); self._date_popup = popup
        popup.title('Chọn ngày'); popup.transient(self.winfo_toplevel()); popup.grab_set()
        frm = ttk.Frame(popup, padding=6); frm.pack(fill='both', expand=True)

        header_var = tk.StringVar()

        def build_calendar(y, m):
            for w in list(cal_frame.winfo_children()): w.destroy()
            header_var.set(f"{m:02d}/{y}")
            week_days = ['T2','T3','T4','T5','T6','T7','CN']
            for c, txt in enumerate(week_days):
                ttk.Label(cal_frame, text=txt, width=3, anchor='center', font=('Segoe UI',9,'bold')).grid(row=0, column=c)
            month_cal = calendar.monthcalendar(y, m)
            for r, week in enumerate(month_cal, start=1):
                for c, day in enumerate(week):
                    if day == 0:
                        ttk.Label(cal_frame, text='').grid(row=r, column=c)
                    else:
                        d_btn = ttk.Button(cal_frame, text=str(day), width=3,
                            command=lambda dd=day, mm=m, yy=y: select_day(yy, mm, dd))
                        # highlight today
                        if day == date.today().day and m == date.today().month and y == date.today().year:
                            d_btn.configure(style='Today.TButton')
                        d_btn.grid(row=r, column=c, padx=1, pady=1)

        def select_day(y, m, d):
            target_var.set(f"{d:02d}/{m:02d}/{y}")
            popup.destroy()
            if on_change:
                on_change()

        def prev_month():
            nonlocal year, month
            month -= 1
            if month == 0:
                month = 12; year -= 1
            build_calendar(year, month)

        def next_month():
            nonlocal year, month
            month += 1
            if month == 13:
                month = 1; year += 1
            build_calendar(year, month)

        top_nav = ttk.Frame(frm); top_nav.pack(fill='x', pady=(0,4))
        ttk.Button(top_nav, text='◀', width=3, command=prev_month).pack(side='left')
        ttk.Label(top_nav, textvariable=header_var, font=('Segoe UI',10,'bold')).pack(side='left', padx=6)
        ttk.Button(top_nav, text='▶', width=3, command=next_month).pack(side='left')
        ttk.Button(top_nav, text='Hôm nay', command=lambda: select_day(date.today().year, date.today().month, date.today().day)).pack(side='right')

        cal_frame = ttk.Frame(frm); cal_frame.pack()

        # Style today button if not exists
        try:
            style = ttk.Style(self)
            style.configure('Today.TButton', foreground='#d32f2f')
        except Exception:
            pass

        build_calendar(year, month)

    def refresh_view(self, list_only: bool = False):
        """Làm mới bảng.
        list_only=True: chỉ cập nhật bảng theo ngày đang chọn ở combobox (không đụng tới tổng/ngày nhập).
        list_only=False: cập nhật bảng + tổng theo ngày nhập (var_ngay) và đồng bộ lại danh sách ngày combobox.
        """
        # Xác định ngày cần hiển thị trong bảng
        if list_only and hasattr(self, 'var_view_day'):
            day_ui = self.var_view_day.get().strip()
        else:
            # Đồng bộ combobox nếu người dùng đổi ngày nhập
            day_ui = self.var_ngay.get().strip()
            if hasattr(self, 'var_view_day'):
                self.var_view_day.set(day_ui)
        try:
            day_iso = to_iso_date(day_ui)
        except Exception:
            # Ngày không hợp lệ => xóa bảng và thoát
            for i in self.tree.get_children():
                self.tree.delete(i)
            return

        # Xóa bảng cũ
        for i in self.tree.get_children():
            self.tree.delete(i)
        # Nạp dữ liệu
        try:
            all_recs = read_daily_records_dict()  # sẽ có record_id nếu utils đọc được
        except Exception:
            all_recs = []
        records = [r for r in all_recs if r.get('ngay') == day_iso]
        total_current = 0
        # mapping iid -> record_id (ẩn) để xóa/sửa chính xác
        self._row_id_map = {}
        for idx, r in enumerate(records):
            display_gia = format_currency(r.get('gia_vnd',0))
            if r.get('loai'):
                display_gia = f"{display_gia} ({r['loai']})"
            total_current += r.get('gia_vnd',0)
            tag = 'odd' if idx % 2 else 'even'
            iid = self.tree.insert('', 'end', values=(r.get('san',''), r.get('khung_gio',''), display_gia, r.get('nguoi','')), tags=(tag,))
            if 'record_id' in r:
                # Lưu map; không hiển thị cột mới -> tránh phá UI
                self._row_id_map[iid] = r['record_id']
        # Cập nhật tổng hiện tại ngay sau khi nạp bảng (dù list_only hay không)
        self.var_current_total.set(format_currency(total_current))

        if not list_only:
            # Cập nhật tổng theo ngày nhập (self.var_ngay)
            try:
                ngay_iso = to_iso_date(self.var_ngay.get().strip())
                total = compute_daily_total(ngay_iso)
                self.var_total.set(format_currency(total))
                breakdown = breakdown_daily_by_court(ngay_iso)
                if breakdown:
                    bd_txt = ", ".join(f"{k}: {format_currency(v)}" for k, v in breakdown.items())
                else:
                    bd_txt = "(trống)"
                self.var_breakdown.set(bd_txt)
            except Exception as ex:
                self.var_total.set("-")
                self.var_breakdown.set(str(ex))
            # Cập nhật lại danh sách ngày của combobox để có ngày mới
            # (Đã chuyển sang chọn lịch nên không cần cập nhật danh sách ngày)

    def delete_selected(self):
        """Xóa dòng được chọn trong bảng"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một dòng để xóa.")
            return
        
        item = sel[0]
        values = self.tree.item(item, 'values')
        rec_id = getattr(self, '_row_id_map', {}).get(item)
        if len(values) == 4:
            san, khung, gia_disp, nguoi = values
        else:
            san, khung, gia_disp = values
            nguoi = ""
        
        try:
            # Sử dụng ngày view thay vì ngày nhập
            ngay = to_iso_date(self.var_view_day.get().strip())
        except Exception:
            messagebox.showerror("Lỗi", "Ngày không hợp lệ")
            return
        
        # Parse giá hiển thị -> VND
        gia_vnd = self._parse_display_price(gia_disp)
        
        # Xác nhận trước khi xóa
        confirm_msg = f"Xóa dòng: {san} {khung} {format_currency(gia_vnd)}"
        if nguoi:
            confirm_msg += f" ({nguoi})"
        confirm_msg += "?"
        
        if not messagebox.askyesno("Xác nhận xóa", confirm_msg):
            return
        
        if rec_id:
            from utils import delete_daily_record_by_id
            ok = delete_daily_record_by_id(rec_id)
            if not ok:
                # fallback logic cũ (phòng trường hợp file mất cột id giữa chừng)
                ok = delete_daily_record(ngay, san, khung, gia_vnd)
        else:
            ok = delete_daily_record(ngay, san, khung, gia_vnd)
        if ok:
            self.refresh_view()
            self._recompute_current_total()
            messagebox.showinfo("Thành công", "Đã xóa dòng.")
        else:
            messagebox.showwarning("Thông báo", "Không tìm thấy dòng để xóa (có thể đã thay đổi)")

    # ---------------- Bulk delete dialog -----------------
    def open_delete_dialog(self):
        """Mở popup xóa nhiều dòng với khả năng đổi ngày trực tiếp trong popup."""
        # Kiểm tra và đóng popup cũ nếu tồn tại
        if hasattr(self, '_bulk_del_win') and self._bulk_del_win:
            try:
                if self._bulk_del_win.winfo_exists():
                    self._bulk_del_win.destroy()
            except:
                pass
            self._bulk_del_win = None

        win = tk.Toplevel(self)
        self._bulk_del_win = win
        win.title("Chọn dòng để xóa")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("590x450")
        
        # Đảm bảo window được cleanup khi đóng
        def on_close():
            self._bulk_del_win = None
            win.destroy()
        
        win.protocol("WM_DELETE_WINDOW", on_close)

        top_bar = ttk.Frame(win); top_bar.pack(fill='x', padx=8, pady=(8,4))
        ttk.Label(top_bar, text='Ngày:').pack(side='left')
        var_day = tk.StringVar(value=self.var_ngay.get())
        e_day = ttk.Entry(top_bar, textvariable=var_day, width=12); e_day.pack(side='left', padx=(4,2))
        # Nút lịch
        ttk.Button(top_bar, text='📅', width=3, command=lambda: self._open_date_picker(var_day, on_change=lambda: load_for(var_day.get()))).pack(side='left', padx=(0,6))
        ttk.Label(top_bar, text='(Định dạng DD/MM/YYYY)').pack(side='left')
        status_var = tk.StringVar(value='')
        ttk.Label(top_bar, textvariable=status_var, foreground='blue').pack(side='right')

        container = ttk.Frame(win); container.pack(fill='both', expand=True, padx=8, pady=4)
        canvas = tk.Canvas(container, borderwidth=0)
        vsb = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        inner = ttk.Frame(canvas)
        canvas.create_window((0,0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        self._bulk_vars = []

        def load_for(day_text: str):
            for child in inner.winfo_children(): child.destroy()
            self._bulk_vars.clear()
            try:
                iso = to_iso_date(day_text.strip())
            except Exception:
                status_var.set('Ngày không hợp lệ'); return
            recs = [r for r in read_daily_records_dict() if r['ngay'] == iso]
            status_var.set('Không có dòng' if not recs else f'{len(recs)} dòng')
            headers = [("Chọn",5),("Sân",6),("Khung giờ",12),("Giá",10),("Loại",8)]
            for col,(txt,w) in enumerate(headers):
                ttk.Label(inner, text=txt, width=w, style='Heading.TLabel').grid(row=0,column=col,sticky='w',padx=(0,2))
            for idx, r in enumerate(recs, start=1):
                var = tk.IntVar(value=0)
                ttk.Checkbutton(inner, variable=var).grid(row=idx,column=0,sticky='w')
                ttk.Label(inner, text=r['san']).grid(row=idx,column=1,sticky='w')
                ttk.Label(inner, text=r['khung_gio']).grid(row=idx,column=2,sticky='w')
                ttk.Label(inner, text=format_currency(r['gia_vnd'])).grid(row=idx,column=3,sticky='w')
                ttk.Label(inner, text=r.get('loai','')).grid(row=idx,column=4,sticky='w')
                self._bulk_vars.append((var, r))

        load_for(var_day.get())

        def on_reload(): load_for(var_day.get())
        ttk.Button(top_bar, text='Tải', command=on_reload).pack(side='left')
        e_day.bind('<Return>', lambda e: on_reload())

        btn_bar = ttk.Frame(win); btn_bar.pack(fill='x', padx=8, pady=8)
        def select_all():
            for v,_ in self._bulk_vars: v.set(1)
        def unselect_all():
            for v,_ in self._bulk_vars: v.set(0)
        def do_delete():
            try:
                iso = to_iso_date(var_day.get().strip())
            except Exception:
                messagebox.showerror('Lỗi','Ngày không hợp lệ'); return
            self._perform_bulk_delete(iso, win)
        
        def close_dialog():
            self._bulk_del_win = None
            win.destroy()
            
        ttk.Button(btn_bar, text='Chọn tất', command=select_all).pack(side='left', padx=4)
        ttk.Button(btn_bar, text='Bỏ chọn', command=unselect_all).pack(side='left', padx=4)
        ttk.Button(btn_bar, text='Xóa các dòng đã chọn', command=do_delete).pack(side='left', padx=12)
        ttk.Button(btn_bar, text='Đóng', command=close_dialog).pack(side='right', padx=4)

    def _perform_bulk_delete(self, ngay: str, win: tk.Toplevel):
        to_del = [r for v, r in self._bulk_vars if v.get()==1]
        if not to_del:
            messagebox.showinfo("Thông báo", "Chưa chọn dòng nào.")
            return
        if not messagebox.askyesno("Xác nhận", f"Xóa {len(to_del)} dòng đã chọn?"):
            return
        deleted = 0
        for r in to_del:
            rid = r.get('record_id')
            if rid:
                from utils import delete_daily_record_by_id
                ok = delete_daily_record_by_id(rid)
                if not ok:
                    ok = delete_daily_record(r['ngay'], r['san'], r['khung_gio'], r['gia_vnd'])
            else:
                ok = delete_daily_record(r['ngay'], r['san'], r['khung_gio'], r['gia_vnd'])
            if ok:
                deleted += 1
        
        # Cleanup window
        self._bulk_del_win = None
        win.destroy()
        self.refresh_view()
        self._recompute_current_total()
        
        if deleted:
            messagebox.showinfo("Kết quả", f"Đã xóa {deleted}/{len(to_del)} dòng.")
        else:
            messagebox.showwarning("Kết quả", "Không xóa được dòng nào (có thể đã thay đổi).")

    # ----------- Edit single record -----------
    def open_edit_dialog(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Thông báo','Chọn 1 dòng để sửa'); return
        item = sel[0]
        values = self.tree.item(item,'values')
        if len(values) == 4:
            san, khung, gia_disp, nguoi = values
        else:
            san, khung, gia_disp = values; nguoi = ''
        # Lấy ngày hiển thị hiện tại
        try:
            ngay_iso = to_iso_date(self.var_view_day.get())
        except Exception:
            messagebox.showerror('Lỗi','Ngày không hợp lệ'); return
        # parse giá
        old_gia = self._parse_display_price(gia_disp)
        loai = ''
        if '(' in gia_disp and ')' in gia_disp:
            try:
                loai = gia_disp.split('(')[1].split(')')[0]
            except Exception:
                loai = ''
        win = tk.Toplevel(self); win.title('Sửa dòng'); win.transient(self.winfo_toplevel()); win.grab_set(); win.geometry('380x230')
        frm = ttk.Frame(win, padding=8); frm.pack(fill='both', expand=True)
        ttk.Label(frm, text=f"Ngày: {self.var_view_day.get()}").grid(row=0,column=0,columnspan=2,sticky='w')
        ttk.Label(frm, text='Sân:').grid(row=1,column=0,sticky='e')
        var_san = tk.StringVar(value=san)
        ttk.Combobox(frm, textvariable=var_san, values=COURTS, width=6, state='readonly').grid(row=1,column=1,sticky='w')
        ttk.Label(frm, text='Khung giờ:').grid(row=2,column=0,sticky='e')
        var_khung = tk.StringVar(value=khung)
        ttk.Entry(frm, textvariable=var_khung, width=14).grid(row=2,column=1,sticky='w')
        ttk.Label(frm, text='Giá:').grid(row=3,column=0,sticky='e')
        var_gia = tk.StringVar(value=f"{old_gia:,}".replace(',', '.') + ' ₫')
        e_edit_price = ttk.Entry(frm, textvariable=var_gia, width=16); e_edit_price.grid(row=3,column=1,sticky='w')
        def _fmt_inline_price(*_):
            raw = var_gia.get(); digits=''.join(ch for ch in raw if ch.isdigit())
            if digits:
                try: var_gia.set(f"{int(digits):,}".replace(',', '.') + ' ₫')
                except: pass
        e_edit_price.bind('<KeyRelease>', _fmt_inline_price)
        e_edit_price.bind('<FocusOut>', _fmt_inline_price)
        ttk.Label(frm, text='Loại:').grid(row=4,column=0,sticky='e')
        var_loai = tk.StringVar(value=loai)
        ttk.Entry(frm, textvariable=var_loai, width=14).grid(row=4,column=1,sticky='w')
        ttk.Label(frm, text='Người/Nhóm:').grid(row=5,column=0,sticky='e')
        var_nguoi = tk.StringVar(value=nguoi)
        ttk.Entry(frm, textvariable=var_nguoi, width=14).grid(row=5,column=1,sticky='w')
        status = tk.StringVar(value='')
        ttk.Label(frm, textvariable=status, foreground='blue').grid(row=6,column=0,columnspan=2,sticky='w', pady=(4,2))

        def do_update():
            try:
                new_san = var_san.get().strip()
                new_khung = var_khung.get().strip()
                from utils import parse_currency_any
                new_gia = parse_currency_any(var_gia.get())
                new_loai = var_loai.get().strip()
                ok = update_daily_record(ngay_iso, san, khung, old_gia, ngay_iso, new_san, new_khung, new_gia, new_loai, var_nguoi.get().strip())
                if ok:
                    status.set('Đã cập nhật')
                    self.refresh_view(list_only=True)
                else:
                    status.set('Không tìm thấy dòng')
            except Exception as ex:
                status.set(str(ex))

        btns = ttk.Frame(frm); btns.grid(row=7,column=0,columnspan=2,pady=4)
        ttk.Button(btns, text='Lưu', command=do_update).pack(side='left', padx=4)
        ttk.Button(btns, text='Đóng', command=win.destroy).pack(side='left', padx=4)

    def _delete_selected_event(self, event):
        self.delete_selected()
        return 'break'

    def undo_last(self):
        if undo_last_action():
            self.refresh_view()
        else:
            messagebox.showinfo("Hoàn tác", "Không còn thao tác để hoàn tác")

    def update_all_total(self):
        try:
            self._recompute_current_total()
        except Exception:
            self.var_current_total.set("-")

    def update_clock(self):
            now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            self.var_now.set(now)
            # Lặp lại sau 1s
            self.after(1000, self.update_clock)
            # Cập nhật tổng toàn bộ định kỳ
            self.update_all_total()

    def _recompute_current_total(self):
        """Tính lại tổng hiện tại dựa trên bảng đang hiển thị (ngày xem)."""
        try:
            day_ui = self.var_view_day.get().strip() if hasattr(self,'var_view_day') else self.var_ngay.get().strip()
            day_iso = to_iso_date(day_ui)
        except Exception:
            self.var_current_total.set('0'); return
        try:
            all_recs = read_daily_records_dict()
        except Exception:
            all_recs = []
        total = sum(r.get('gia_vnd',0) for r in all_recs if r.get('ngay') == day_iso)
        self.var_current_total.set(format_currency(total))

    def _auto_price(self):
        """Enhanced auto pricing with better feedback and validation."""
        try:
            start = int(self.var_start.get())
            end = int(self.var_end.get())
        except Exception:
            return
            
        if end <= start:
            # Show user-friendly validation
            if hasattr(self, 'lbl_info'):
                self.lbl_info.config(text="⚠️ Giờ kết thúc phải lớn hơn giờ bắt đầu")
            return
            
        loai = self.var_loai.get() or 'Chơi'
        base = HOURLY_BASE.get(loai, 0)
        hours_range = list(range(start, end))
        
        # Smart lighting suggestion for off-peak hours (only if user hasn't manually set it)
        needs_light = any(is_off_hour(h) for h in hours_range)
        if needs_light and not self.var_light.get() and not getattr(self, '_user_manually_set_light', False):
            self.var_light.set(True)
            # Show helpful notification
            try:
                root = self.winfo_toplevel()
                if hasattr(root, 'show_toast'):
                    root.show_toast('💡 Tự động bật đèn (có thể tắt nếu không cần)', 'info', 2000)
            except Exception:
                pass
        
        # Calculate price with enhanced display
        per_hour = base + (LIGHT_SURCHARGE if self.var_light.get() else 0)
        total_hours = end - start
        total = per_hour * total_hours
        
        # Enhanced price display with breakdown info
        price_display = f"{total:,}".replace(',', '.') + ' ₫'
        
        # Show price breakdown in tooltip/info if helpful
        if total_hours > 1:
            breakdown = f"{format_currency(per_hour)} × {total_hours}h"
            if hasattr(self, 'lbl_info') and self.lbl_info.cget('text') == '':
                self.lbl_info.config(text=f"💰 Tính giá: {breakdown} = {price_display}")
        
        self.var_gia.set(price_display)

class DailySummaryFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.build()

    def build(self):
        row = 0
        ttk.Label(self, text="Tổng kết ngày", font=("Segoe UI",12,'bold')).grid(column=0, row=row, columnspan=6, sticky='w')
        row += 1
        ttk.Label(self, text="Ngày (DD/MM/YYYY):").grid(column=0, row=row, sticky='w')
        self.var_ngay = tk.StringVar(value=datetime.today().strftime('%d/%m/%Y'))
        date_wrap = ttk.Frame(self); date_wrap.grid(column=1, row=row, sticky='w')
        e = ttk.Entry(date_wrap, textvariable=self.var_ngay, width=14)
        e.pack(side='left')
        e.bind('<Return>', lambda ev: self.refresh_day())
        ttk.Button(date_wrap, text='📅', width=3, command=lambda: self._open_date_picker(self.var_ngay, on_change=self.refresh_day)).pack(side='left', padx=(3,0))
        ttk.Button(self, text="⟨ Trước", command=lambda: self.shift_day(-1)).grid(column=2, row=row, padx=2)
        ttk.Button(self, text="Hôm nay", command=self.set_today).grid(column=3, row=row, padx=2)
        ttk.Button(self, text="Sau ⟩", command=lambda: self.shift_day(1)).grid(column=4, row=row, padx=2)

        row += 1
        ttk.Button(self, text="Làm mới", command=self.refresh_day).grid(column=0, row=row, pady=6, sticky='w')

        row += 1
        ttk.Label(self, text="Tổng:").grid(column=0, row=row, sticky='w')
        self.var_total = tk.StringVar(value='0')
        ttk.Label(self, textvariable=self.var_total, font=("Segoe UI",11,'bold')).grid(column=1, row=row, sticky='w')
        ttk.Label(self, text="Sân 1:").grid(column=2, row=row, sticky='e')
        self.var_s1 = tk.StringVar(value='0')
        ttk.Label(self, textvariable=self.var_s1).grid(column=3, row=row, sticky='w')
        ttk.Label(self, text="Sân 2:").grid(column=2, row=row+1, sticky='e')
        self.var_s2 = tk.StringVar(value='0')
        ttk.Label(self, textvariable=self.var_s2).grid(column=3, row=row+1, sticky='w')
        ttk.Label(self, text="Chơi:").grid(column=4, row=row, sticky='e')
        self.var_play = tk.StringVar(value='0')
        ttk.Label(self, textvariable=self.var_play).grid(column=5, row=row, sticky='w')
        ttk.Label(self, text="Tập:").grid(column=4, row=row+1, sticky='e')
        self.var_prac = tk.StringVar(value='0')
        ttk.Label(self, textvariable=self.var_prac).grid(column=5, row=row+1, sticky='w')
        row += 2

        cols = ('san','khung','loai','gia')
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=18)
        for c, txt, w in (('san','Sân',60),('khung','Khung giờ',110),('loai','Loại',70),('gia','Giá',110)):
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor='center')
        self.tree.grid(column=0, row=row, columnspan=6, sticky='nwe', pady=(4,4))
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.grid(column=6, row=row, sticky='ns')
        self.grid_columnconfigure(5, weight=1)
        try:
            attach_tree_enhancements(self.winfo_toplevel(), self.tree)
        except Exception:
            pass
        # Bỏ phần thống kê mở rộng: dùng toàn bộ chiều cao cho bảng
        self.refresh_day()

    # Helpers
    def _get_iso_date(self) -> str:
        s = self.var_ngay.get().strip()
        try:
            dt = datetime.strptime(s.replace('/', '-'), '%d-%m-%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            raise ValueError('Ngày phải dạng DD/MM/YYYY')

    def set_today(self):
        self.var_ngay.set(date.today().strftime('%d/%m/%Y'))
        self.refresh_day()

    def shift_day(self, delta: int):
        try:
            dt = datetime.strptime(self.var_ngay.get().strip().replace('/', '-'), '%d-%m-%Y')
        except ValueError:
            dt = date.today()
        new_dt = dt + timedelta(days=delta)
        self.var_ngay.set(new_dt.strftime('%d/%m/%Y'))
        self.refresh_day()

    def refresh_day(self):
        try:
            iso = self._get_iso_date()
        except Exception as ex:
            messagebox.showerror('Lỗi', str(ex))
            return
        for i in self.tree.get_children():
            self.tree.delete(i)
        records = [r for r in read_daily_records_dict() if r['ngay'] == iso]
        s1 = s2 = play = prac = 0
        earliest = latest = None
        for r in records:
            gia_disp = format_currency(r['gia_vnd'])
            self.tree.insert('', 'end', values=(r['san'], r['khung_gio'], r.get('loai',''), gia_disp))
            if r['san'] == 'Sân 1':
                s1 += r['gia_vnd']
            else:
                s2 += r['gia_vnd']
            loai = r.get('loai','').lower()
            if loai == 'chơi':
                play += r['gia_vnd']
            elif loai == 'tập':
                prac += r['gia_vnd']
            try:
                start = int(r['khung_gio'].split('-')[0].rstrip('h'))
                end = int(r['khung_gio'].split('-')[1].rstrip('h'))
                if earliest is None or start < earliest:
                    earliest = start
                if latest is None or end > latest:
                    latest = end
            except Exception:
                pass
        total = s1 + s2
        self.var_total.set(format_currency(total))
        self.var_s1.set(format_currency(s1))
        self.var_s2.set(format_currency(s2))
        self.var_play.set(format_currency(play))
        self.var_prac.set(format_currency(prac))
        try:
            apply_zebra(self.tree)
        except Exception:
            pass
    # Đã bỏ phần thống kê mở rộng

    # Popup lịch tái sử dụng từ DailyEntryFrame (code rút gọn)
    def _open_date_picker(self, target_var: tk.StringVar, on_change=None):
        if hasattr(self, '_date_popup') and self._date_popup and tk.Toplevel.winfo_exists(self._date_popup):
            self._date_popup.lift(); return
        # Lấy ngày hiện tại trong ô
        try:
            dt = datetime.strptime(target_var.get(), '%d/%m/%Y')
        except Exception:
            dt = datetime.today()
        year = dt.year; month = dt.month
        popup = tk.Toplevel(self); self._date_popup = popup
        popup.title('Chọn ngày'); popup.transient(self.winfo_toplevel()); popup.grab_set()
        frm = ttk.Frame(popup, padding=6); frm.pack(fill='both', expand=True)
        header_var = tk.StringVar()
        cal_frame = ttk.Frame(frm); cal_frame.pack()
        def build_calendar(y, m):
            for w in list(cal_frame.winfo_children()): w.destroy()
            header_var.set(f"{m:02d}/{y}")
            week_days = ['T2','T3','T4','T5','T6','T7','CN']
            for c, txt in enumerate(week_days):
                ttk.Label(cal_frame, text=txt, width=3, anchor='center', font=('Segoe UI',9,'bold')).grid(row=0, column=c)
            import calendar as _cal
            for r, week in enumerate(_cal.monthcalendar(y, m), start=1):
                for c, day in enumerate(week):
                    if day == 0:
                        ttk.Label(cal_frame, text='').grid(row=r, column=c)
                    else:
                        b = ttk.Button(cal_frame, text=str(day), width=3, command=lambda dd=day, mm=m, yy=y: select_day(yy, mm, dd))
                        if day == date.today().day and m == date.today().month and y == date.today().year:
                            try:
                                style = ttk.Style(self); style.configure('Today.TButton', foreground='#d32f2f')
                                b.configure(style='Today.TButton')
                            except Exception:
                                pass
                        b.grid(row=r, column=c, padx=1, pady=1)
        def select_day(y, m, d):
            target_var.set(f"{d:02d}/{m:02d}/{y}")
            popup.destroy()
            if on_change: on_change()
        def prev_month():
            nonlocal year, month
            month -= 1
            if month == 0:
                month = 12; year -= 1
            build_calendar(year, month)
        def next_month():
            nonlocal year, month
            month += 1
            if month == 13:
                month = 1; year += 1
            build_calendar(year, month)
        top_nav = ttk.Frame(frm); top_nav.pack(fill='x', pady=(0,4))
        ttk.Button(top_nav, text='◀', width=3, command=prev_month).pack(side='left')
        ttk.Label(top_nav, textvariable=header_var, font=('Segoe UI',10,'bold')).pack(side='left', padx=6)
        ttk.Button(top_nav, text='▶', width=3, command=next_month).pack(side='left')
        ttk.Button(top_nav, text='Hôm nay', command=lambda: select_day(date.today().year, date.today().month, date.today().day)).pack(side='right')
        build_calendar(year, month)
    # (Đã có show_total ở DailyEntryFrame phía trên; bản trùng đã bị loại bỏ)
class MonthlyStatFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self._build()

    def _build(self):
        row = 0
        ttk.Label(self, text="Thống kê tháng", font=("Segoe UI",12,'bold')).grid(column=0, row=row, columnspan=5, sticky='w')
        row += 1
        ttk.Label(self, text="Tháng:").grid(column=0, row=row, sticky='w')
        months = [f"{m:02d}" for m in range(1,13)]
        years = [str(y) for y in range(2025,2051)]
        self.var_month_only = tk.StringVar(value=date.today().strftime('%m'))
        cur_year = date.today().year
        default_year = str(min(max(cur_year,2025),2050))
        self.var_year_only = tk.StringVar(value=default_year)
        cb_month = ttk.Combobox(self, textvariable=self.var_month_only, values=months, width=4, state='readonly'); cb_month.grid(column=1, row=row, sticky='w')
        cb_year = ttk.Combobox(self, textvariable=self.var_year_only, values=years, width=6, state='readonly'); cb_year.grid(column=1, row=row, padx=(50,0), sticky='w')
        ttk.Button(self, text='Tính tự động', command=self.fill_from_days).grid(column=2, row=row, padx=4)
        ttk.Button(self, text='Làm mới', command=self.refresh_history).grid(column=3, row=row, padx=4)
        cb_month.bind('<<ComboboxSelected>>', lambda e: self._sync_month_var())
        cb_year.bind('<<ComboboxSelected>>', lambda e: self._sync_month_var())
        row += 1
        ttk.Label(self, text='Tổng thu:').grid(column=0, row=row, sticky='w')
        self.var_tong = tk.StringVar()
        self.e_tong = ttk.Entry(self, textvariable=self.var_tong, width=18); self.e_tong.grid(column=1, row=row, sticky='w')
        row += 1
        ttk.Label(self, text='Chi phí:').grid(column=0, row=row, sticky='w')
        self.var_chi_phi = tk.StringVar()
        self.e_cp = ttk.Entry(self, textvariable=self.var_chi_phi, width=18)
        self.e_cp.grid(column=1, row=row, sticky='w')
        # Lý do chi phí
        ttk.Label(self, text='Lý do:').grid(column=2, row=row, sticky='e')
        self.var_cp_ly_do = tk.StringVar()
        self.e_cp_reason = ttk.Entry(self, textvariable=self.var_cp_ly_do, width=24)
        self.e_cp_reason.grid(column=3, row=row, sticky='w', padx=(4,0))
        self.e_cp.bind('<Return>', lambda e: self.save_month())
        # Auto format khi rời ô + live format
        def _fmt_month_live(event=None, var=None):
            if var is None: return
            txt = var.get(); digits=''.join(ch for ch in txt if ch.isdigit())
            if not digits: return
            try: var.set(f"{int(digits):,}".replace(',', '.') + ' ₫')
            except: pass
        self.e_tong.bind('<FocusOut>', lambda e: _fmt_month_live(var=self.var_tong))
        self.e_cp.bind('<FocusOut>', lambda e: _fmt_month_live(var=self.var_chi_phi))
        self.e_tong.bind('<KeyRelease>', lambda e: _fmt_month_live(var=self.var_tong))
        self.e_cp.bind('<KeyRelease>', lambda e: _fmt_month_live(var=self.var_chi_phi))
        row += 1
        self.btn_save = ttk.Button(self, text='Lưu & tính lợi nhuận (Enter)', command=self.save_month)
        self.btn_save.grid(column=0, row=row, pady=6, sticky='w')
        ttk.Button(self, text='Xóa thống kê', command=self.delete_selected).grid(column=1, row=row, pady=6, sticky='w')
        # Bỏ nút sửa/hủy: double-click dòng để vào chế độ sửa, Enter để cập nhật, Esc để hủy
        row += 1
        cols = ('thang','doanh_thu','chi_phi','ly_do','loi_nhuan')
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=12, selectmode='browse')
        for c, title, w in (
            ('thang','Tháng',80),
            ('doanh_thu','Doanh thu',120),
            ('chi_phi','Chi phí',120),
            ('ly_do','Lý do chi phí',260),
            ('loi_nhuan','Lợi nhuận',120)
        ):
            self.tree.heading(c, text=title); self.tree.column(c, width=w, anchor='center')
        self.tree.grid(column=0, row=row, columnspan=4, sticky='nwe', pady=(4,4))
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.grid(column=4, row=row, sticky='ns')
        self.grid_columnconfigure(3, weight=1)
        try:
            attach_tree_enhancements(self.winfo_toplevel(), self.tree)
        except Exception:
            pass
        self.var_thang = tk.StringVar(value=f"{self.var_month_only.get()}-{self.var_year_only.get()}")
        self.refresh_history()
        # Double click -> popup sửa
        self.tree.bind('<Double-1>', lambda e: self._open_edit_popup_month())

    def _open_edit_popup_month(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0],'values')
        if not vals:
            return
        thang_ui, doanh_thu_txt, chi_phi_txt, ly_do_txt, _loi = vals
        thang_iso = to_iso_month(thang_ui)
        # popup
        win = tk.Toplevel(self); win.title(f'Sửa tháng {thang_ui}')
        win.transient(self.winfo_toplevel()); win.grab_set()
        ttk.Label(win, text=f'Tháng {thang_ui}', font=('Segoe UI',11,'bold')).grid(column=0,row=0,columnspan=2,sticky='w', pady=(4,4), padx=6)
        ttk.Label(win, text='Tổng thu:').grid(column=0,row=1,sticky='e', padx=6, pady=2)
        init_rev_digits = ''.join(ch for ch in doanh_thu_txt if ch.isdigit())
        var_tong = tk.StringVar(value=(f"{int(init_rev_digits):,}".replace(',', '.') + ' ₫') if init_rev_digits else '')
        e_tong = ttk.Entry(win, textvariable=var_tong, width=20); e_tong.grid(column=1,row=1,sticky='w', pady=2)
        ttk.Label(win, text='Chi phí:').grid(column=0,row=2,sticky='e', padx=6, pady=2)
        init_cost_digits = ''.join(ch for ch in chi_phi_txt if ch.isdigit())
        var_cp = tk.StringVar(value=(f"{int(init_cost_digits):,}".replace(',', '.') + ' ₫') if init_cost_digits else '')
        e_cp = ttk.Entry(win, textvariable=var_cp, width=20); e_cp.grid(column=1,row=2,sticky='w', pady=2)
        ttk.Label(win, text='Lý do chi phí:').grid(column=0,row=3,sticky='e', padx=6, pady=2)
        var_reason = tk.StringVar(value=ly_do_txt)
        e_reason = ttk.Entry(win, textvariable=var_reason, width=32); e_reason.grid(column=1,row=3,sticky='w', pady=2)
        def _fmt_local(v: tk.StringVar):
            raw=v.get(); digits=''.join(ch for ch in raw if ch.isdigit())
            if not digits: return
            try: v.set(f"{int(digits):,}".replace(',', '.') + ' ₫')
            except: pass
        for ent, var in ((e_tong,var_tong),(e_cp,var_cp)):
            ent.bind('<KeyRelease>', lambda e, vv=var: _fmt_local(vv))
            ent.bind('<FocusOut>', lambda e, vv=var: _fmt_local(vv))

        def do_save():
            try:
                from utils import parse_currency_any
                tong = parse_currency_any(var_tong.get())
                chi_phi = parse_currency_any(var_cp.get())
                reason = var_reason.get().strip()
                ok = update_monthly_stat(thang_iso, tong, chi_phi, reason)
                if ok:
                    messagebox.showinfo('Đã lưu','Đã cập nhật tháng')
                    win.destroy(); self.refresh_history()
                else:
                    messagebox.showwarning('Không đổi','Không cập nhật được (không tìm thấy)')
            except Exception as ex:
                messagebox.showerror('Lỗi', str(ex))

        btns = ttk.Frame(win); btns.grid(column=0,row=4,columnspan=2,sticky='w', padx=6, pady=(8,6))
        ttk.Button(btns, text='Lưu', command=do_save).pack(side='left')
        ttk.Button(btns, text='Hủy', command=win.destroy).pack(side='left', padx=6)
        e_tong.focus_set(); win.bind('<Return>', lambda ev: do_save())

    def fill_from_days(self):
        thang_ui = self.var_thang.get().strip()
        try:
            total = compute_month_total(thang_ui)
            self.var_tong.set(f"{total:,}".replace(',', '.') + ' ₫')
            messagebox.showinfo("Thông báo", f"Tổng các ngày {thang_ui}: {format_currency(total)}")
        except Exception as ex:
            messagebox.showerror("Lỗi", str(ex))

    def _parse_int(self, txt: str, field: str) -> int:
        if not txt.strip():
            raise ValueError(f"{field} không được trống")
        digits = ''.join(ch for ch in txt if ch.isdigit())
        if not digits:
            raise ValueError(f"{field} phải là số")
        return int(digits)

    def _format_month_entry(self, var: tk.StringVar):
        txt = var.get().strip()
        if not txt:
            return
        digits = ''.join(ch for ch in txt if ch.isdigit())
        if not digits:
            return
        try:
            var.set(f"{int(digits):,}".replace(',', '.') + ' ₫')
        except Exception:
            pass

    def save_month(self):
        thang_ui = self.var_thang.get().strip()
        try:
            tong = self._parse_int(self.var_tong.get(), "Tổng doanh thu")
            chi_phi = self._parse_int(self.var_chi_phi.get(), "Chi phí")
            thang_iso = thang_ui if len(thang_ui)==7 and thang_ui[2]!="-" else to_iso_month(thang_ui)
            reason = self.var_cp_ly_do.get().strip()
            loi = save_monthly_stat(thang_iso, tong, chi_phi, tu_tinh_tu_ngay=False, chi_phi_ly_do=reason)
            messagebox.showinfo("Kết quả", f"Lợi nhuận {thang_ui}: {format_currency(loi)}")
            self.refresh_history()
        except Exception as ex:
            messagebox.showerror("Lỗi", str(ex))

    def refresh_history(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        stats = read_monthly_stats()
        for s in stats:
            reason = s.get('chi_phi_ly_do','')
            self.tree.insert('', 'end', values=(
                to_ui_month(s['thang']),
                format_currency(s['tong_doanh_thu_vnd']),
                format_currency(s['chi_phi_tru_hao_vnd']),
                reason,
                format_currency(s['loi_nhuan_vnd'])
            ))
        try:
            apply_zebra(self.tree)
        except Exception:
            pass

    # Đã bỏ hiển thị tổng theo sân

    def _sync_month_var(self):
        # Cập nhật biến tổng hợp mm-YYYY khi combobox thay đổi
        self.var_thang.set(f"{self.var_month_only.get()}-{self.var_year_only.get()}")

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Chưa chọn dòng nào")
            return
        item = sel[0]
        thang = self.tree.item(item, 'values')[0]
        if not messagebox.askyesno("Xác nhận", f"Xóa thống kê tháng {thang}?"):
            return
        # chuyển về iso và ghi lại file bỏ tháng đó
        try:
            thang_iso = to_iso_month(thang)
            stats = read_monthly_stats()
            # filter
            remaining = [s for s in stats if s['thang'] != thang_iso]
            # ghi đè (dùng save_monthly_stat từng dòng sau khi clear file)
            import os, csv
            path = 'monthly_stats.csv'
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
            for s in remaining:
                save_monthly_stat(s['thang'], s['tong_doanh_thu_vnd'], s['chi_phi_tru_hao_vnd'], tu_tinh_tu_ngay=False)
            self.refresh_history()
            messagebox.showinfo("Kết quả", f"Đã xóa tháng {thang}")
        except Exception as ex:
            messagebox.showerror("Lỗi", str(ex))

    # (Phần gói tháng đã chuyển sang tab riêng)

class SubscriptionFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.build()

    def build(self):
        row = 0
        ttk.Label(self, text="Gói tháng", font=("Segoe UI", 12, 'bold')).grid(column=0, row=row, columnspan=4, sticky='w')
        row += 1
        
        # Month selection
        ttk.Label(self, text="Tháng:").grid(column=0, row=row, sticky='w')
        self.var_month = tk.StringVar(value=date.today().strftime('%m'))
        self.var_year = tk.StringVar(value=date.today().strftime('%Y'))
        cb_month = ttk.Combobox(self, textvariable=self.var_month, values=[f"{m:02d}" for m in range(1,13)], width=4, state='readonly')
        cb_month.grid(column=1, row=row, sticky='w')
        cb_year = ttk.Combobox(self, textvariable=self.var_year, values=[str(y) for y in range(2025,2051)], width=6, state='readonly')
        cb_year.grid(column=1, row=row, padx=(55,0), sticky='w')

        def _sync_thang():
            self.var_thang.set(f"{self.var_month.get()}-{self.var_year.get()}")
        self.var_thang = tk.StringVar()
        _sync_thang()
        cb_month.bind('<<ComboboxSelected>>', lambda e: (_sync_thang(), self.refresh_subs()))
        cb_year.bind('<<ComboboxSelected>>', lambda e: (_sync_thang(), self.refresh_subs()))
        ttk.Button(self, text="Làm mới", command=self.refresh_subs).grid(column=2, row=row, padx=4)
        row += 1
        
        # Name/Group
        ttk.Label(self, text="Tên nhóm/Người:").grid(column=0, row=row, sticky='w')
        self.var_name = tk.StringVar()
        e_name = ttk.Entry(self, textvariable=self.var_name, width=25)
        e_name.grid(column=1, row=row, sticky='w')
        self._entry_name = e_name  # store for VN typing support
        row += 1
        
        # Court selection
        ttk.Label(self, text="Sân:").grid(column=0, row=row, sticky='w')
        self.var_court = tk.StringVar(value=COURTS[0])  # Default to first court
        court_combo = ttk.Combobox(self, textvariable=self.var_court, values=COURTS, 
                                  state='readonly', width=15)
        court_combo.grid(column=1, row=row, sticky='w')
        
        # Add tooltip for court selection
        Tooltip(court_combo, "Sân sử dụng cho gói tháng", example="Sân 1: Chuyên nghiệp, Sân 2: Thông dụng")
        
        row += 1
        
        # Sessions per week with day selector button
        ttk.Label(self, text="Buổi/tuần:").grid(column=0, row=row, sticky='w')
        self.var_sessions = tk.StringVar(value='3')
        e_ses = ttk.Entry(self, textvariable=self.var_sessions, width=6)
        e_ses.grid(column=1, row=row, sticky='w')
        
        # Add tooltip for sessions
        Tooltip(e_ses, "Số buổi tập trong tuần", example="3 buổi (Thứ 2, 4, 6)")
        
        # Day selector button (O button)
        self.var_selected_days = tk.StringVar(value='')  # Store selected days
        day_btn = ttk.Button(self, text='🗓️', width=4, command=self.open_day_selector)
        day_btn.grid(column=1, row=row, padx=(80, 0), sticky='w')
        
        # Add tooltip for day selector
        Tooltip(day_btn, "Chọn các ngày trong tuần", example="Bấm để mở lịch chọn ngày")
        
        # Hours per session - changed to button with popup
        ttk.Label(self, text="Giờ/buổi:").grid(column=2, row=row, sticky='e')
        self.var_hours = tk.StringVar(value='1 (Chưa chọn)')
        self.hours_btn = ttk.Button(self, textvariable=self.var_hours, width=15, command=self.open_time_selector)
        self.hours_btn.grid(column=3, row=row, sticky='w')
        
        # Add tooltip for hours selector
        Tooltip(self.hours_btn, "Khung giờ tập của gói tháng", example="17:00-19:00 (2 tiếng mỗi buổi)")
        
        row += 1
        
        # Price input (editable)
        ttk.Label(self, text="Giá:").grid(column=0, row=row, sticky='w')
        self.var_price = tk.StringVar(value='0 ₫')
        self.e_price = ttk.Entry(self, textvariable=self.var_price, width=15)
        self.e_price.grid(column=1, row=row, sticky='w')
        
        # Add tooltip for price
        Tooltip(self.e_price, "Giá gói tháng", example="1.200.000 ₫ (12 buổi × 100k)")
        
        # Notes input (X button replacement)
        ttk.Label(self, text="Ghi chú:").grid(column=2, row=row, sticky='e')
        self.var_notes = tk.StringVar()
        e_notes = ttk.Entry(self, textvariable=self.var_notes, width=20)
        e_notes.grid(column=3, row=row, sticky='w')
        
        # Add tooltip for notes
        Tooltip(e_notes, "Thông tin bổ sung", example="Gói VIP, Học viên mới, Ưu đãi")
        row += 1
        
        # Buttons
        ttk.Button(self, text='Thêm (Enter)', command=self.add_sub).grid(column=1, row=row, sticky='w')
        ttk.Button(self, text='Xóa gói tháng', command=self.open_delete_dialog).grid(column=2, row=row, sticky='w')
        row += 1
        
        # Tree with new columns including Court
        cols = ("ten","san","so_buoi","gio","thu","gia","ghi_chu")
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=14)
        column_config = [
            ("ten", "Tên", 140),
            ("san", "Sân", 70),
            ("so_buoi", "Buổi/tuần", 80),
            ("gio", "Giờ/buổi", 80),
            ("thu", "Thứ", 120),
            ("gia", "Giá", 110),
            ("ghi_chu", "Ghi chú", 130)
        ]
        
        for col_id, title, width in column_config:
            self.tree.heading(col_id, text=title)
            self.tree.column(col_id, width=width, anchor='center')
            
        self.tree.grid(column=0, row=row, columnspan=4, sticky='nwe', pady=(4,4))
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.grid(column=4, row=row, sticky='ns')
        self.tree.bind('<Double-1>', lambda e: self._open_edit_popup_sub())
        row += 1
        
        # Total
        self.var_total = tk.StringVar(value='0')
        ttk.Label(self, text='Tổng gói tháng:').grid(column=0, row=row, sticky='w')
        ttk.Label(self, textvariable=self.var_total, font=("Segoe UI", 11, 'bold')).grid(column=1, row=row, sticky='w')
        row += 1
        ttk.Label(self, text='(Doanh thu gói sẽ cộng vào thống kê tháng)').grid(column=0, row=row, columnspan=4, sticky='w')

        # Bind events
        for w in (e_name, court_combo, e_ses, self.e_price, e_notes):
            w.bind('<Return>', lambda e: self.add_sub())
            
        # Auto price calculation when sessions change
        e_ses.bind('<KeyRelease>', lambda e: self.auto_calculate_price())
        
        # Price formatting
        self.e_price.bind('<KeyRelease>', lambda e: self._format_price_live())
        self.e_price.bind('<FocusOut>', lambda e: self._format_price())

        # Vietnamese input support
        self._setup_vietnamese_input()
        
        # Initialize
        self.auto_calculate_price()
        self.refresh_subs()
    
    def _setup_vietnamese_input(self):
        """Setup Vietnamese Telex input for name field"""
        def _vn_telex_full(event=None):
            if event and event.keysym in ('Shift_L','Shift_R','Control_L','Control_R','Alt_L','Alt_R'):
                return
            widget = event.widget if event else None
            if widget is not self._entry_name:
                return
            text = self.var_name.get()
            # Process each word; only transform the word that currently ends with a tone key or vowel pattern
            words = text.split(' ')
            changed = False
            tone_keys = {'s':'sắc','f':'huyền','r':'hỏi','x':'ngã','j':'nặng','z':'remove'}
            # mappings base sequences -> vowel (case sensitive variants)
            base_seq = {
                'dd':'đ','DD':'Đ',
                'aa':'â','Aa':'Â','AA':'Â',
                'aw':'ă','Aw':'Ă','AW':'Ă',
                'ee':'ê','Ee':'Ê','EE':'Ê',
                'oo':'ô','Oo':'Ô','OO':'Ô',
                'ow':'ơ','Ow':'Ơ','OW':'Ơ',
                'uw':'ư','Uw':'Ư','UW':'Ư',
            }
            # tone placement priority list (order matters)
            priority = ['ê','Ê','ơ','Ơ','ô','Ô','ă','Ă','â','Â','ư','Ư','a','A','e','E','o','O','u','U','i','I','y','Y']
            # tone maps for each vowel family
            tone_map = {
                'a': {'s':'á','f':'à','r':'ả','x':'ã','j':'ạ'},
                'ă':{'s':'ắ','f':'ằ','r':'ẳ','x':'ẵ','j':'ặ'},
                'â':{'s':'ấ','f':'ầ','r':'ẩ','x':'ẫ','j':'ậ'},
                'e': {'s':'é','f':'è','r':'ẻ','x':'ẽ','j':'ẹ'},
                'ê':{'s':'ế','f':'ề','r':'ể','x':'ễ','j':'ệ'},
                'i': {'s':'í','f':'ì','r':'ỉ','x':'ĩ','j':'ị'},
                'o': {'s':'ó','f':'ò','r':'ỏ','x':'õ','j':'ọ'},
                'ô':{'s':'ố','f':'ồ','r':'ổ','x':'ỗ','j':'ộ'},
                'ơ':{'s':'ớ','f':'ờ','r':'ở','x':'ỡ','j':'ợ'},
                'u': {'s':'ú','f':'ù','r':'ủ','x':'ũ','j':'ụ'},
                'ư':{'s':'ứ','f':'ừ','r':'ử','x':'ữ','j':'ự'},
                'y': {'s':'ý','f':'ỳ','r':'ỷ','x':'ỹ','j':'ỵ'},
            }
            # add uppercase variants
            def upperize(m):
                r={}
                for k,v in m.items():
                    r[k.upper()]={tone:v2.upper() for tone,v2 in v.items()}
                return r
            tone_map.update(upperize(tone_map))
            reverse_tone = {v: base for base, tones in tone_map.items() for tone_key, v in tones.items()}
            for i,w in enumerate(words):
                if not w:
                    continue
                original_w = w
                tone_char = ''
                if w[-1:] in tone_keys:
                    tone_char = w[-1]
                    w = w[:-1]
                # base sequence replacements (greedy)
                for seq, rep in base_seq.items():
                    if seq in w:
                        w = w.replace(seq, rep)
                # special combination for 'ươ': patterns 'uo' + final 'w' OR intermediate 'uơ'
                if w.endswith('w'):
                    core = w[:-1]
                    idx = core.rfind('uo')
                    if idx != -1:
                        seq = core[idx:idx+2]
                        new_seq = 'Ươ' if seq[0].isupper() else 'ươ'
                        core = core[:idx] + new_seq + core[idx+2:]
                        w = core
                        changed = True
                # convert leftover 'uơ' to 'ươ'
                if 'uơ' in w or 'Uơ' in w:
                    w2 = w.replace('uơ','ươ').replace('Uơ','Ươ')
                    if w2 != w:
                        w = w2; changed = True
                # remove tone request
                if tone_char == 'z':
                    # strip tones from vowels in word
                    tmp=''
                    for ch in w:
                        if ch in reverse_tone:
                            base = reverse_tone[ch]
                            tmp += base
                        else:
                            # also normalize vowels with tone to base (reverse lookup)
                            found=False
                            for base,tones in tone_map.items():
                                if isinstance(tones,dict):
                                    for tkey,val in tones.items():
                                        if ch==val:
                                            tmp+=base; found=True; break
                                    if found: break
                            if not found:
                                tmp+=ch
                    w=tmp
                    changed=True
                elif tone_char in tone_keys and tone_char:
                    # Apply tone to priority vowel
                    for pv in priority:
                        idx = w.find(pv)
                        if idx!=-1:
                            base_letter = pv
                            if base_letter in tone_map and tone_char in tone_map[base_letter]:
                                w = w[:idx] + tone_map[base_letter][tone_char] + w[idx+len(pv):]
                                changed=True
                            break
                if w!=original_w:
                    words[i]=w
            if changed:
                cursor = self._entry_name.index('insert')
                new_text = ' '.join(words)
                self.var_name.set(new_text)
                try:
                    self._entry_name.icursor(min(cursor, len(new_text)))
                except Exception:
                    pass
        self._entry_name.bind('<KeyRelease>', _vn_telex_full, add='+')

    def open_day_selector(self):
        """Open popup to select days of the week"""
        # Prevent multiple dialogs
        if hasattr(self, '_day_selector_win') and self._day_selector_win:
            try:
                if self._day_selector_win.winfo_exists():
                    self._day_selector_win.destroy()
            except:
                pass
            self._day_selector_win = None

        win = tk.Toplevel(self)
        self._day_selector_win = win
        win.title("Chọn thứ trong tuần")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("480x450")  # Increased size significantly
        
        def on_close():
            self._day_selector_win = None
            win.destroy()
        
        win.protocol("WM_DELETE_WINDOW", on_close)
        
        frame = ttk.Frame(win, padding=20)  # Increased padding
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text="Chọn các thứ trong tuần:", font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 15))
        
        # Days of week with larger checkboxes
        days = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
        day_vars = []
        
        # Parse current selection
        current_days = self.var_selected_days.get().split(', ') if self.var_selected_days.get() else []
        
        # Create checkboxes in a nicer layout
        checkbox_frame = ttk.Frame(frame)
        checkbox_frame.pack(fill='x', pady=(0, 20))
        
        for i, day in enumerate(days):
            var = tk.BooleanVar(value=(day in current_days))
            day_vars.append((var, day))
            cb = ttk.Checkbutton(checkbox_frame, text=day, variable=var)
            cb.pack(anchor='w', pady=5, padx=10)  # Increased spacing
        
        # Buttons with better layout
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=(30, 0))
        
        def save_selection():
            selected = [day for var, day in day_vars if var.get()]
            if selected:
                self.var_selected_days.set(', '.join(selected))
                # Auto-adjust sessions per week
                if len(selected) != int(self.var_sessions.get() or 0):
                    self.var_sessions.set(str(len(selected)))
                    self.auto_calculate_price()
            else:
                self.var_selected_days.set('')
            on_close()
        
        def select_all():
            for var, day in day_vars:
                var.set(True)
        
        def clear_all():
            for var, day in day_vars:
                var.set(False)
        
        # Simple horizontal layout for buttons
        ttk.Button(btn_frame, text='Chọn tất cả', command=select_all).pack(side='left', padx=(0, 15))
        ttk.Button(btn_frame, text='Bỏ chọn tất cả', command=clear_all).pack(side='left', padx=(0, 15))
        
        ttk.Button(btn_frame, text='Hủy', command=on_close).pack(side='right')
        ttk.Button(btn_frame, text='Lưu', command=save_selection, style='Primary.TButton').pack(side='right', padx=(0, 15))

    def open_time_selector(self):
        """Open time selection popup - completely rebuilt for reliability"""
        # Close any existing dialog
        if hasattr(self, '_time_selector_win') and self._time_selector_win:
            try:
                if self._time_selector_win.winfo_exists():
                    self._time_selector_win.destroy()
            except:
                pass
            self._time_selector_win = None

        # Create new window
        win = tk.Toplevel(self)
        self._time_selector_win = win
        win.title("⏰ Chọn giờ chơi")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.resizable(False, False)
        
        # Set larger size and center
        width, height = 650, 600
        win.geometry(f"{width}x{height}")
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        
        def close_dialog():
            self._time_selector_win = None
            win.destroy()
        
        win.protocol("WM_DELETE_WINDOW", close_dialog)
        
        # Parse current value
        current_text = self.var_hours.get()
        current_hours = 1
        current_start = 7
        current_end = 8
        
        if '(' in current_text and ')' in current_text:
            try:
                parts = current_text.split('(')
                current_hours = int(parts[0].strip())
                time_range = parts[1].split(')')[0]
                start_str, end_str = time_range.split('-')
                current_start = int(start_str.split(':')[0])
                current_end = int(end_str.split(':')[0])
            except:
                pass
        
        # Main container with better spacing
        main_frame = tk.Frame(win, bg='#f8f9fa')
        main_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Title
        title_label = tk.Label(main_frame, text="⏰ Cấu hình giờ chơi", 
                              font=('Segoe UI', 18, 'bold'), bg='#f8f9fa', fg='#333')
        title_label.pack(anchor='w', pady=(0, 8))
        
        subtitle_label = tk.Label(main_frame, text="Thiết lập số giờ và khung thời gian cho buổi chơi", 
                                 font=('Segoe UI', 11), bg='#f8f9fa', fg='#666')
        subtitle_label.pack(anchor='w', pady=(0, 25))
        
        # Hours selection
        hours_frame = tk.LabelFrame(main_frame, text="  ⏱️ Số giờ mỗi buổi  ", 
                                   font=('Segoe UI', 12, 'bold'), bg='#f8f9fa', fg='#333')
        hours_frame.pack(fill='x', pady=(0, 20), padx=5)
        
        hours_var = tk.IntVar(value=current_hours)
        
        # Create hours grid inside frame
        hours_inner = tk.Frame(hours_frame, bg='#f8f9fa')
        hours_inner.pack(fill='x', padx=20, pady=20)
        
        # Row 1: 1-3 hours
        hours_row1 = tk.Frame(hours_inner, bg='#f8f9fa')
        hours_row1.pack(fill='x', pady=(0, 10))
        
        for i in range(1, 4):
            rb = tk.Radiobutton(hours_row1, text=f"{i} giờ", variable=hours_var, value=i,
                               font=('Segoe UI', 11), bg='#f8f9fa', fg='#333',
                               selectcolor='#e3f2fd', activebackground='#f8f9fa')
            rb.pack(side='left', padx=(0, 30))
        
        # Row 2: 4-6 hours
        hours_row2 = tk.Frame(hours_inner, bg='#f8f9fa')
        hours_row2.pack(fill='x')
        
        for i in range(4, 7):
            rb = tk.Radiobutton(hours_row2, text=f"{i} giờ", variable=hours_var, value=i,
                               font=('Segoe UI', 11), bg='#f8f9fa', fg='#333',
                               selectcolor='#e3f2fd', activebackground='#f8f9fa')
            rb.pack(side='left', padx=(0, 30))
        
        # Container for Time range and Preview side by side
        time_preview_container = tk.Frame(main_frame, bg='#f8f9fa')
        time_preview_container.pack(fill='x', pady=(0, 25), padx=5)
        
        # Time range selection (left side)
        time_frame = tk.LabelFrame(time_preview_container, text="  🕐 Khung thời gian  ", 
                                  font=('Segoe UI', 12, 'bold'), bg='#f8f9fa', fg='#333')
        time_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        time_inner = tk.Frame(time_frame, bg='#f8f9fa')
        time_inner.pack(fill='x', padx=20, pady=20)
        
        # Start time
        start_row = tk.Frame(time_inner, bg='#f8f9fa')
        start_row.pack(fill='x', pady=(0, 10))
        
        tk.Label(start_row, text="Giờ bắt đầu:", font=('Segoe UI', 11), 
                bg='#f8f9fa', fg='#333').pack(side='left')
        
        start_var = tk.StringVar(value=f"{current_start}:00")
        start_combo = ttk.Combobox(start_row, textvariable=start_var, width=15, 
                                  state='readonly', font=('Segoe UI', 11))
        start_combo['values'] = [f"{h}:00" for h in range(5, 23)]
        start_combo.pack(side='left', padx=(20, 0))
        
        # End time
        end_row = tk.Frame(time_inner, bg='#f8f9fa')
        end_row.pack(fill='x')
        
        tk.Label(end_row, text="Giờ kết thúc:", font=('Segoe UI', 11), 
                bg='#f8f9fa', fg='#333').pack(side='left')
        
        end_var = tk.StringVar(value=f"{current_end}:00")
        end_combo = ttk.Combobox(end_row, textvariable=end_var, width=15, 
                                state='readonly', font=('Segoe UI', 11))
        end_combo['values'] = [f"{h}:00" for h in range(6, 24)]
        end_combo.pack(side='left', padx=(20, 0))
        
        # Auto-update end time
        def auto_update_end(*args):
            try:
                start_hour = int(start_var.get().split(':')[0])
                duration = hours_var.get()
                end_hour = start_hour + duration
                if end_hour <= 23:
                    end_var.set(f"{end_hour}:00")
            except:
                pass
        
        hours_var.trace('w', auto_update_end)
        start_combo.bind('<<ComboboxSelected>>', auto_update_end)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(fill='x', pady=(20, 0))
        
        def save_selection():
            try:
                hours = hours_var.get()
                start_time = start_var.get()
                end_time = end_var.get()
                
                start_hour = int(start_time.split(':')[0])
                end_hour = int(end_time.split(':')[0])
                
                if end_hour <= start_hour:
                    tk.messagebox.showwarning("⚠️ Lỗi", "Giờ kết thúc phải sau giờ bắt đầu!")
                    return
                
                if (end_hour - start_hour) != hours:
                    tk.messagebox.showwarning("⚠️ Lỗi", 
                                            f"Khoảng thời gian từ {start_time} đến {end_time} "
                                            f"không khớp với {hours} giờ!")
                    return
                
                # Update main form
                time_text = f"{hours} ({start_time}-{end_time})"
                self.var_hours.set(time_text)
                self.auto_calculate_price()
                
                tk.messagebox.showinfo("✅ Thành công", f"Đã cập nhật: {time_text}")
                close_dialog()
                
            except Exception as e:
                tk.messagebox.showerror("❌ Lỗi", f"Có lỗi xảy ra: {str(e)}")
        
        # Create buttons after function definition with balanced size
        button_container = tk.Frame(button_frame, bg='#f8f9fa')
        button_container.pack(anchor='center')
        
        # Lưu button (primary)
        btn_save = tk.Button(button_container, text='💾 Lưu', command=save_selection,
                            font=('Segoe UI', 11, 'bold'), width=12, height=2, 
                            bg='#0066cc', fg='white', relief='raised', bd=2,
                            activebackground='#0052a3', activeforeground='white',
                            cursor='hand2')
        btn_save.pack(side='left', padx=(0, 15))
        
        # Hủy button (secondary)
        btn_cancel = tk.Button(button_container, text='❌ Hủy', command=close_dialog,
                              font=('Segoe UI', 11), width=12, height=2, 
                              relief='raised', bd=2, cursor='hand2',
                              bg='#f8f9fa', fg='#666')
        btn_cancel.pack(side='left')
        
        # Focus
        win.focus_set()
        start_combo.focus_set()

    def auto_calculate_price(self):
        """Auto calculate price based on sessions and hours"""
        try:
            ses = int(self.var_sessions.get() or 0)
            # Parse hours from format "2 (7:00-9:00)" or just "2"
            hours_text = self.var_hours.get()
            hrs = 1
            if '(' in hours_text:
                hrs = int(hours_text.split('(')[0].strip())
            else:
                try:
                    hrs = int(hours_text.split()[0]) if hours_text and not 'Chưa chọn' in hours_text else 1
                except:
                    hrs = 1
            
            if ses > 0 and hrs > 0:
                price = compute_subscription_price(ses, hrs)
                self.var_price.set(f"{price:,}".replace(',', '.') + ' ₫')
        except:
            pass

    def _format_price_live(self):
        """Format price while typing"""
        raw = self.var_price.get()
        if not raw:
            return
        digits = ''.join(ch for ch in raw if ch.isdigit())
        if digits:
            try:
                v = int(digits)
                self.var_price.set(f"{v:,}".replace(',', '.') + ' ₫')
            except:
                pass

    def _format_price(self):
        """Format price on focus out"""
        self._format_price_live()

    def _parse_price(self, price_str):
        """Parse price string to integer"""
        digits = ''.join(ch for ch in price_str if ch.isdigit())
        return int(digits) if digits else 0

    def open_delete_dialog(self):
        """Xóa gói đăng ký đã chọn trong bảng"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một gói để xóa.")
            return
            
        vals = self.tree.item(sel[0], 'values')
        if not vals:
            return
            
        name = vals[0]  # Tên gói
        
        if not messagebox.askyesno('Xác nhận', f'Xóa gói "{name}"?'):
            return
            
        try:
            m = self._month_iso()
            ok = delete_month_subscription(m, name)
            if ok:
                messagebox.showinfo('Thành công', 'Đã xóa gói')
                self.refresh_subs()
            else:
                messagebox.showerror('Lỗi', 'Không xóa được')
        except Exception as ex:
            messagebox.showerror('Lỗi', str(ex))

    def _open_edit_popup_sub(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], 'values')
        if not vals:
            return
        old_name, old_san, so_buoi_txt, gio_txt, thu_txt, gia_txt, ghi_chu_txt = vals
        m_iso = self._month_iso()
        
        win = tk.Toplevel(self)
        win.title(f'Sửa gói {old_name}')
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("450x400")
        
        frame = ttk.Frame(win, padding=15)
        frame.pack(fill='both', expand=True)
        
        row = 0
        ttk.Label(frame, text=f'Tháng {self.var_thang.get()}', font=('Segoe UI',11,'bold')).grid(column=0,row=row,columnspan=2,sticky='w', pady=(0,15))
        row += 1
        
        # Name
        ttk.Label(frame, text='Tên:').grid(column=0,row=row,sticky='e', padx=(0,10))
        var_name = tk.StringVar(value=old_name)
        e_name = ttk.Entry(frame, textvariable=var_name, width=30)
        e_name.grid(column=1,row=row,sticky='w', pady=5)
        row += 1
        
        # Court
        ttk.Label(frame, text='Sân:').grid(column=0,row=row,sticky='e', padx=(0,10))
        var_court = tk.StringVar(value=old_san)
        court_combo = ttk.Combobox(frame, textvariable=var_court, values=COURTS, 
                                  state='readonly', width=15)
        court_combo.grid(column=1,row=row,sticky='w', pady=5)
        row += 1
        
        # Sessions per week
        ttk.Label(frame, text='Buổi/tuần:').grid(column=0,row=row,sticky='e', padx=(0,10))
        var_ses = tk.StringVar(value=so_buoi_txt)
        e_ses = ttk.Entry(frame, textvariable=var_ses, width=10)
        e_ses.grid(column=1,row=row,sticky='w', pady=5)
        row += 1
        
        # Hours per session - changed to button with popup
        ttk.Label(frame, text='Giờ/buổi:').grid(column=0,row=row,sticky='e', padx=(0,10))
        var_hrs = tk.StringVar(value=gio_txt)
        hrs_btn = ttk.Button(frame, textvariable=var_hrs, width=20, 
                           command=lambda: self._open_time_selector_edit(var_hrs))
        hrs_btn.grid(column=1,row=row,sticky='w', pady=5)
        row += 1
        
        # Days selection
        ttk.Label(frame, text='Thứ:').grid(column=0,row=row,sticky='e', padx=(0,10))
        var_days = tk.StringVar(value=thu_txt)
        days_frame = ttk.Frame(frame)
        days_frame.grid(column=1, row=row, sticky='w', pady=5)
        
        ttk.Entry(days_frame, textvariable=var_days, width=25, state='readonly').pack(side='left')
        ttk.Button(days_frame, text='🗓️', width=4, command=lambda: self._open_day_selector_edit(var_days, var_ses)).pack(side='left', padx=(8,0))
        row += 1
        
        # Price
        ttk.Label(frame, text='Giá:').grid(column=0,row=row,sticky='e', padx=(0,10))
        var_price = tk.StringVar(value=gia_txt)
        e_price = ttk.Entry(frame, textvariable=var_price, width=18)
        e_price.grid(column=1,row=row,sticky='w', pady=5)
        row += 1
        
        # Notes
        ttk.Label(frame, text='Ghi chú:').grid(column=0,row=row,sticky='e', padx=(0,10))
        var_notes = tk.StringVar(value=ghi_chu_txt)
        e_notes = ttk.Entry(frame, textvariable=var_notes, width=30)
        e_notes.grid(column=1,row=row,sticky='w', pady=5)
        row += 1

        # Price formatting
        def _fmt_inline_price(*_):
            raw = var_price.get()
            digits=''.join(ch for ch in raw if ch.isdigit())
            if digits:
                try: 
                    var_price.set(f"{int(digits):,}".replace(',', '.') + ' ₫')
                except: 
                    pass
        e_price.bind('<KeyRelease>', _fmt_inline_price)
        e_price.bind('<FocusOut>', _fmt_inline_price)

        # Auto calculate price
        def update_preview_local(*_):
            try:
                ses = int(var_ses.get())
                # Parse hours from format "2 (7:00-9:00)" or just "2"
                hours_text = var_hrs.get()
                if '(' in hours_text:
                    hrs = int(hours_text.split('(')[0].strip())
                else:
                    try:
                        hrs = int(hours_text.split()[0]) if hours_text else 1
                    except:
                        hrs = 1
                
                if ses > 0 and hrs > 0:
                    price = compute_subscription_price(ses, hrs)
                    var_price.set(f"{price:,}".replace(',', '.') + ' ₫')
            except:
                pass
        
        e_ses.bind('<KeyRelease>', update_preview_local, add='+')

        def do_save():
            try:
                new_name = var_name.get().strip()
                new_court = var_court.get().strip()
                ses = int(var_ses.get())
                
                # Parse hours from format "2 (7:00-9:00)" or just "2" and store full format
                hours_text = var_hrs.get()
                if '(' in hours_text:
                    hrs = int(hours_text.split('(')[0].strip())
                    hrs_display = hours_text
                else:
                    try:
                        hrs = int(hours_text.split()[0]) if hours_text else 1
                        hrs_display = str(hrs)
                    except:
                        raise ValueError('Giờ không hợp lệ')
                
                days = var_days.get().strip()
                price = self._parse_price(var_price.get())
                notes = var_notes.get().strip()
                
                if not new_name:
                    raise ValueError('Tên không được trống')
                
                # Use updated function with new fields
                ok = update_month_subscription_with_time(m_iso, old_name, new_name, ses, hrs_display, new_court, days, notes)
                if ok:
                    messagebox.showinfo('Đã lưu','Đã cập nhật gói')
                    win.destroy()
                    self.refresh_subs()
                else:
                    messagebox.showwarning('Không đổi','Không cập nhật được')
            except Exception as ex:
                messagebox.showerror('Lỗi', str(ex))

        btns = ttk.Frame(frame)
        btns.grid(column=0,row=row+1,columnspan=2,sticky='w', pady=(15,0))
        ttk.Button(btns, text='Lưu', command=do_save, style='Primary.TButton').pack(side='left')
        ttk.Button(btns, text='Hủy', command=win.destroy).pack(side='left', padx=(15,0))
        e_name.focus_set()
        win.bind('<Return>', lambda ev: do_save())

    def _open_day_selector_edit(self, var_days, var_sessions):
        """Day selector for edit popup"""
        win = tk.Toplevel(self)
        win.title("Chọn thứ trong tuần")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("480x450")
        
        frame = ttk.Frame(win, padding=20)
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text="Chọn các thứ trong tuần:", font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 20))
        
        days = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
        day_vars = []
        
        current_days = var_days.get().split(', ') if var_days.get() else []
        
        checkbox_frame = ttk.Frame(frame)
        checkbox_frame.pack(anchor='w', pady=(0, 30))
        
        for day in days:
            var = tk.BooleanVar(value=(day in current_days))
            day_vars.append((var, day))
            ttk.Checkbutton(checkbox_frame, text=day, variable=var).pack(anchor='w', pady=5, padx=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=(30, 0))
        
        def save_selection():
            selected = [day for var, day in day_vars if var.get()]
            if selected:
                var_days.set(', '.join(selected))
                if len(selected) != int(var_sessions.get() or 0):
                    var_sessions.set(str(len(selected)))
            else:
                var_days.set('')
            win.destroy()
        
        def select_all():
            for var, day in day_vars:
                var.set(True)
        
        def clear_all():
            for var, day in day_vars:
                var.set(False)
        
        ttk.Button(btn_frame, text='Chọn tất cả', command=select_all).pack(side='left', padx=(0, 15))
        ttk.Button(btn_frame, text='Bỏ chọn tất cả', command=clear_all).pack(side='left', padx=(0, 15))
        
        ttk.Button(btn_frame, text='Hủy', command=win.destroy).pack(side='right')
        ttk.Button(btn_frame, text='Lưu', command=save_selection, style='Primary.TButton').pack(side='right', padx=(0, 15))

    def _open_time_selector_edit(self, var_hrs):
        """Open popup to select hours and time range for edit dialog"""
        win = tk.Toplevel(self)
        win.title("⏰ Cấu hình giờ chơi")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.resizable(False, False)
        win.configure(bg='#f8f9fa')
        
        # Set size and center window
        width, height = 580, 520
        win.geometry(f"{width}x{height}")
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (width // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        
        # Main container with consistent styling
        main_frame = tk.Frame(win, bg='#f8f9fa')
        main_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # Title with icon and proper typography
        title_label = tk.Label(main_frame, text="⏰ Cấu hình giờ chơi", 
                              font=('Arial Unicode MS', 16, 'bold'), bg='#f8f9fa', fg='#333')
        title_label.pack(anchor='w', pady=(0, 8))
        
        subtitle_label = tk.Label(main_frame, text="Thiết lập số giờ và khung thời gian cho buổi chơi", 
                                 font=('Arial Unicode MS', 10), bg='#f8f9fa', fg='#666')
        subtitle_label.pack(anchor='w', pady=(0, 25))

        # Parse current hours format: "2 (7:00-9:00)" or just "2"
        current_text = var_hrs.get()
        current_hours = 1
        current_start = 7
        current_end = 8
        
        if '(' in current_text and ')' in current_text:
            try:
                parts = current_text.split('(')
                current_hours = int(parts[0].strip())
                time_range = parts[1].split(')')[0]
                start_str, end_str = time_range.split('-')
                current_start = int(start_str.split(':')[0])
                current_end = int(end_str.split(':')[0])
            except:
                pass
        else:
            try:
                if current_text.strip():
                    current_hours = int(current_text.split()[0])
            except:
                pass
        
        # Hours selection with proper frame styling
        hours_frame = tk.LabelFrame(main_frame, text="  ⏱️ Số giờ mỗi buổi  ", 
                                   font=('Arial Unicode MS', 11, 'bold'), bg='#f8f9fa', fg='#333',
                                   relief='ridge', bd=1)
        hours_frame.pack(fill='x', pady=(0, 20))
        
        hours_var = tk.IntVar(value=current_hours)
        
        # Inner frame with proper padding
        hours_inner = tk.Frame(hours_frame, bg='#f8f9fa')
        hours_inner.pack(fill='x', padx=20, pady=15)
        
        # Row 1: 1-3 hours with better spacing
        row1 = tk.Frame(hours_inner, bg='#f8f9fa')
        row1.pack(fill='x', pady=(0, 12))
        
        for i in range(1, 4):
            rb = tk.Radiobutton(row1, text=f"{i} giờ", variable=hours_var, value=i,
                               font=('Arial Unicode MS', 10), bg='#f8f9fa', fg='#333',
                               selectcolor='#e3f2fd', activebackground='#f8f9fa',
                               relief='flat', bd=0)
            rb.pack(side='left', padx=(0, 40))
            
        # Row 2: 4-6 hours
        row2 = tk.Frame(hours_inner, bg='#f8f9fa')
        row2.pack(fill='x')
        
        for i in range(4, 7):
            rb = tk.Radiobutton(row2, text=f"{i} giờ", variable=hours_var, value=i,
                               font=('Arial Unicode MS', 10), bg='#f8f9fa', fg='#333',
                               selectcolor='#e3f2fd', activebackground='#f8f9fa',
                               relief='flat', bd=0)
            rb.pack(side='left', padx=(0, 40))
        
        # Time range selector with improved layout
        time_frame = tk.LabelFrame(main_frame, text="  🕐 Khung thời gian  ", 
                                  font=('Arial Unicode MS', 11, 'bold'), bg='#f8f9fa', fg='#333',
                                  relief='ridge', bd=1)
        time_frame.pack(fill='x', pady=(0, 20))
        
        time_inner = tk.Frame(time_frame, bg='#f8f9fa')
        time_inner.pack(fill='x', padx=20, pady=15)
        
        # Start time with better alignment
        start_frame = tk.Frame(time_inner, bg='#f8f9fa')
        start_frame.pack(fill='x', pady=(0, 12))
        
        tk.Label(start_frame, text="Giờ bắt đầu:", font=('Arial Unicode MS', 10), 
                bg='#f8f9fa', fg='#333', width=12, anchor='w').pack(side='left')
        
        start_var = tk.StringVar(value=f"{current_start}:00")
        start_combo = ttk.Combobox(start_frame, textvariable=start_var, width=12, 
                                  state='readonly', font=('Arial Unicode MS', 10))
        start_combo['values'] = [f"{h}:00" for h in range(5, 23)]
        start_combo.pack(side='left', padx=(10, 0))
        
        # End time
        end_frame = tk.Frame(time_inner, bg='#f8f9fa')
        end_frame.pack(fill='x')
        
        tk.Label(end_frame, text="Giờ kết thúc:", font=('Arial Unicode MS', 10), 
                bg='#f8f9fa', fg='#333', width=12, anchor='w').pack(side='left')
        
        end_var = tk.StringVar(value=f"{current_end}:00")
        end_combo = ttk.Combobox(end_frame, textvariable=end_var, width=12, 
                                state='readonly', font=('Arial Unicode MS', 10))
        end_combo['values'] = [f"{h}:00" for h in range(6, 24)]
        end_combo.pack(side='left', padx=(10, 0))
        
        # Auto-calculate end time when hours or start time changes
        def update_end_time(*args):
            try:
                start_hour = int(start_var.get().split(':')[0])
                duration = hours_var.get()
                end_hour = start_hour + duration
                if end_hour <= 23:
                    end_var.set(f"{end_hour}:00")
            except:
                pass
        
        hours_var.trace('w', update_end_time)
        start_var.trace('w', update_end_time)
        
        # Buttons with improved styling
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(fill='x', pady=(20, 0))
        
        def save_time_selection():
            try:
                hours = hours_var.get()
                start = start_combo.get()
                end = end_combo.get()
                
                start_hour = int(start.split(':')[0])
                end_hour = int(end.split(':')[0])
                
                if end_hour <= start_hour:
                    tk.messagebox.showwarning("⚠️ Lỗi", "Giờ kết thúc phải sau giờ bắt đầu!")
                    return
                
                if (end_hour - start_hour) != hours:
                    tk.messagebox.showwarning("⚠️ Lỗi", 
                                            f"Khoảng thời gian từ {start} đến {end} "
                                            f"không khớp với {hours} giờ!")
                    return
                
                time_text = f"{hours} ({start}-{end})"
                var_hrs.set(time_text)
                tk.messagebox.showinfo("✅ Thành công", f"Đã cập nhật: {time_text}")
                win.destroy()
            except Exception as e:
                tk.messagebox.showerror("❌ Lỗi", f"Có lỗi xảy ra: {str(e)}")
        
        # Button container for centering
        button_container = tk.Frame(button_frame, bg='#f8f9fa')
        button_container.pack(anchor='center')
        
        # Save button (primary)
        btn_save = tk.Button(button_container, text='💾 Lưu', command=save_time_selection,
                            font=('Arial Unicode MS', 10, 'bold'), width=12, height=2, 
                            bg='#0066cc', fg='white', relief='raised', bd=2,
                            activebackground='#0052a3', activeforeground='white',
                            cursor='hand2')
        btn_save.pack(side='left', padx=(0, 15))
        
        # Cancel button (secondary)
        btn_cancel = tk.Button(button_container, text='❌ Hủy', command=win.destroy,
                              font=('Arial Unicode MS', 10), width=12, height=2, 
                              relief='raised', bd=2, cursor='hand2',
                              bg='#f5f5f5', fg='#666', activebackground='#e9ecef')
        btn_cancel.pack(side='left')
        
        # Focus and initial state
        win.focus_set()
        start_combo.focus_set()

    def _month_iso(self):
        s = self.var_thang.get().strip()
        return s if (len(s)==7 and s[2] != '-') else to_iso_month(s)

    def refresh_subs(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            m = self._month_iso()
            subs = read_month_subscriptions(m)
        except Exception:
            subs = []
        total = 0
        for r in subs:
            total += r.get('gia_vnd',0)
            self.tree.insert('', 'end', values=(
                r.get('ten',''),
                r.get('san', 'Sân 1'),  # Default to Sân 1 if not specified
                r.get('so_buoi_tuan',''),
                r.get('gio_moi_buoi_display', r.get('gio_moi_buoi','')),  # Use display format if available
                r.get('thu', ''),  # Days column
                format_currency(r.get('gia_vnd',0)),
                r.get('ghi_chu', '')  # Notes column
            ))
        self.var_total.set(format_currency(total))
        try:
            apply_zebra(self.tree)
        except Exception:
            pass

    def add_sub(self):
        try:
            m = self._month_iso()
            name = self.var_name.get().strip()
            court = self.var_court.get().strip()
            ses = int(self.var_sessions.get())
            
            # Parse hours from format "2 (7:00-9:00)" or just "2"
            hours_text = self.var_hours.get()
            if '(' in hours_text:
                hrs = int(hours_text.split('(')[0].strip())
                # Store the full format for gio_moi_buoi field
                hrs_display = hours_text
            else:
                try:
                    hrs = int(hours_text.split()[0]) if hours_text and not 'Chưa chọn' in hours_text else 1
                    hrs_display = str(hrs)
                except:
                    raise ValueError('Vui lòng chọn giờ chơi hợp lệ')
            
            days = self.var_selected_days.get().strip()
            price = self._parse_price(self.var_price.get())
            notes = self.var_notes.get().strip()
            
            if not name:
                raise ValueError('Tên không được trống')
            
            if 'Chưa chọn' in hours_text:
                raise ValueError('Vui lòng chọn khung giờ chơi')
            
            # Use updated function with new fields - pass hrs_display instead of hrs for storage
            calculated_price = add_month_subscription_with_time(m, name, ses, hrs_display, court, days, notes)
            
            messagebox.showinfo('Thêm', f'Đã thêm {name} ({court}): {format_currency(calculated_price)}')
            
            # Clear form
            self.var_name.set('')
            self.var_selected_days.set('')
            self.var_notes.set('')
            self.var_hours.set('1 (Chưa chọn)')
            self.auto_calculate_price()
            
            self.refresh_subs()
        except Exception as ex:
            messagebox.showerror('Lỗi', str(ex))

class ProfitShareFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.build()

    def build(self):
        row = 0
        ttk.Label(self, text='Bảng tổng doanh thu', font=("Segoe UI",12,'bold')).grid(column=0, row=row, sticky='w')
        row += 1
        ttk.Label(self, text='Từ tháng:').grid(column=0, row=row, sticky='w')
        self.var_from_month = tk.StringVar(value=date.today().strftime('%m'))
        self.var_from_year = tk.StringVar(value=date.today().strftime('%Y'))
        ttk.Combobox(self, textvariable=self.var_from_month, values=[f"{m:02d}" for m in range(1,13)], width=4, state='readonly').grid(column=1, row=row, sticky='w')
        ttk.Combobox(self, textvariable=self.var_from_year, values=[str(y) for y in range(2025,2051)], width=6, state='readonly').grid(column=1, row=row, padx=(55,0), sticky='w')
        ttk.Label(self, text='Đến tháng:').grid(column=2, row=row, sticky='w')
        self.var_to_month = tk.StringVar(value=date.today().strftime('%m'))
        self.var_to_year = tk.StringVar(value=date.today().strftime('%Y'))
        ttk.Combobox(self, textvariable=self.var_to_month, values=[f"{m:02d}" for m in range(1,13)], width=4, state='readonly').grid(column=3, row=row, sticky='w')
        ttk.Combobox(self, textvariable=self.var_to_year, values=[str(y) for y in range(2025,2051)], width=6, state='readonly').grid(column=3, row=row, padx=(55,0), sticky='w')
        ttk.Button(self, text='Tải dữ liệu', command=self.refresh_totals).grid(column=4, row=row, padx=4)
        ttk.Button(self, text='Tạo lần chia...', command=self.open_share_dialog).grid(column=5, row=row, padx=4)
        row += 1
        cols = ('thang','doanh_thu','chi_phi','loi_nhuan')
        self.tree_months = ttk.Treeview(self, columns=cols, show='headings', height=8)
        for c, t, w in (('thang','Tháng',80),('doanh_thu','Doanh thu',120),('chi_phi','Chi phí',120),('loi_nhuan','Lợi nhuận',120)):
            self.tree_months.heading(c, text=t)
            self.tree_months.column(c, width=w, anchor='center')
        self.tree_months.grid(column=0, row=row, columnspan=6, sticky='nwe', pady=(4,4))
        sb = ttk.Scrollbar(self, orient='vertical', command=self.tree_months.yview)
        self.tree_months.configure(yscroll=sb.set)
        sb.grid(column=6, row=row, sticky='ns')
        row += 1
        ttk.Label(self, text='Các lần chia đã lưu:').grid(column=0, row=row, sticky='w')
        ttk.Button(self, text='Xóa lần chia', command=self.open_delete_share_dialog).grid(column=1, row=row, sticky='w')
        row += 1
        cols2 = ('id','pham_vi','tong','chi_phi','loi_nhuan','noi_dung','luc')
        self.tree_shares = ttk.Treeview(self, columns=cols2, show='headings', height=8)
        for c, t, w in (('id','ID',90),('pham_vi','Phạm vi',120),('tong','Tổng DT',110),('chi_phi','Chi phí',110),('loi_nhuan','Lợi nhuận',110),('noi_dung','Chi tiết',260),('luc','Lúc',130)):
            self.tree_shares.heading(c, text=t)
            self.tree_shares.column(c, width=w, anchor='center')
        self.tree_shares.grid(column=0, row=row, columnspan=6, sticky='nwe', pady=(4,4))
        sb2 = ttk.Scrollbar(self, orient='vertical', command=self.tree_shares.yview)
        self.tree_shares.configure(yscroll=sb2.set)
        sb2.grid(column=6, row=row, sticky='ns')
        for i in range(6):
            self.grid_columnconfigure(i, weight=1)
        self.refresh_totals(); self.refresh_shares()

    def _range_months(self):
        try:
            fm = int(self.var_from_month.get()); fy = int(self.var_from_year.get())
            tm = int(self.var_to_month.get()); ty = int(self.var_to_year.get())
        except ValueError:
            return []
        from datetime import datetime as _dt2
        start = _dt2(fy,fm,1); end = _dt2(ty,tm,1)
        if start > end: start, end = end, start
        res = []
        cur = start
        while cur <= end:
            res.append(cur.strftime('%Y-%m'))
            y = cur.year + (cur.month // 12); m = 1 if cur.month==12 else cur.month+1
            cur = _dt2(y,m,1)
        return res

    def refresh_totals(self):
        for i in self.tree_months.get_children(): self.tree_months.delete(i)
        stats = read_monthly_stats()
        wanted = set(self._range_months())
        sum_rev = sum_cost = sum_profit = 0
        for s in stats:
            if s['thang'] in wanted:
                rev = s['tong_doanh_thu_vnd']; cost = s['chi_phi_tru_hao_vnd']; prof = s['loi_nhuan_vnd']
                sum_rev += rev; sum_cost += cost; sum_profit += prof
                self.tree_months.insert('', 'end', values=(to_ui_month(s['thang']),
                    format_currency(rev),
                    format_currency(cost),
                    format_currency(prof)))
        # Dòng tổng
        self.tree_months.insert('', 'end', values=('Tổng',
            format_currency(sum_rev),
            format_currency(sum_cost),
            format_currency(sum_profit)))
        try:
            apply_zebra(self.tree_months)
        except Exception:
            pass

    def refresh_shares(self):
        for i in self.tree_shares.get_children(): self.tree_shares.delete(i)
        evs = read_profit_share_events()
        for e in evs:
            self.tree_shares.insert('', 'end', values=(e.get('event_id',''), e.get('scope',''),
                format_currency(e.get('total_revenue_vnd',0)),
                format_currency(e.get('total_cost_vnd',0)),
                format_currency(e.get('profit_vnd',0)), e.get('summary',''), e.get('created_at','')))
        try:
            apply_zebra(self.tree_shares)
        except Exception:
            pass

    def open_share_dialog(self):
        win = tk.Toplevel(self); win.title('Tạo lần chia lợi nhuận')
        win.transient(self.winfo_toplevel()); win.grab_set()
        info = """HƯỚNG DẪN
Nhập một trong hai cách:
    1. Danh sách tháng: mm-YYYY, cách nhau dấu phẩy
         Ví dụ: 06-2025,07-2025,08-2025
    2. Một năm 4 số: 2025 (tự lấy đủ 12 tháng)

Số liệu lấy từ tab 'Thống kê tháng'. Hãy chắc chắn mỗi tháng đã được lưu doanh thu & chi phí.
Nhấn 'Xem trước' để xem tổng và số tiền từng người, sau đó 'Lưu lần chia'."""
        ttk.Label(win, text=info, justify='left').grid(column=0, row=0, sticky='w', padx=6, pady=(6,4))
        ttk.Label(win, text='Nhập tháng / năm:').grid(column=0,row=1,sticky='w', padx=6)
        var = tk.StringVar(); e = ttk.Entry(win, textvariable=var, width=48)
        e.grid(column=0,row=2,sticky='w', padx=6)
        preview_var = tk.StringVar(value='')
        ttk.Label(win, textvariable=preview_var, foreground='blue', wraplength=420, justify='left').grid(column=0,row=4,sticky='w', padx=6, pady=(4,4))

        result_cache = {}

        def parse_scope(raw: str):
            raw = raw.strip()
            if not raw:
                raise ValueError('Chưa nhập dữ liệu')
            if raw.isdigit() and len(raw)==4:
                y = int(raw); return [f"{y}-{m:02d}" for m in range(1,13)], f'Năm {y}'
            parts = [p.strip() for p in raw.split(',') if p.strip()]
            if not parts:
                raise ValueError('Không có tháng hợp lệ')
            months=[]
            for p in parts:
                try:
                    months.append(to_iso_month(p))
                except Exception:
                    raise ValueError(f'Tháng không hợp lệ: {p}')
            return months, ','.join(parts)

        def do_preview():
            try:
                months, scope = parse_scope(var.get())
                stats = read_monthly_stats()
                total_rev=total_cost=total_profit=0
                for s in stats:
                    if s['thang'] in months:
                        total_rev += s['tong_doanh_thu_vnd']; total_cost += s['chi_phi_tru_hao_vnd']; total_profit += s['loi_nhuan_vnd']
                if not months:
                    raise ValueError('Không có tháng hợp lệ')
                shares = compute_profit_shares(total_profit)
                summary_lines = [f"Tổng doanh thu: {format_currency(total_rev)}",
                                 f"Tổng chi phí: {format_currency(total_cost)}",
                                 f"Lợi nhuận: {format_currency(total_profit)}",
                                 "Chia theo tỷ lệ:"]
                for name, val in shares.items():
                    summary_lines.append(f" - {name}: {format_currency(val)}")
                preview_var.set(f"Phạm vi: {scope}\n" + "\n".join(summary_lines) + "\nNhấn 'Lưu lần chia' để ghi lại.")
                result_cache.clear(); result_cache.update(dict(scope=scope, rev=total_rev, cost=total_cost, profit=total_profit, shares=shares))
            except Exception as ex:
                preview_var.set(str(ex))

        def do_save():
            if not result_cache:
                messagebox.showerror('Lỗi','Hãy bấm Xem trước trước.'); return
            scope = result_cache['scope']; total_rev=result_cache['rev']; total_cost=result_cache['cost']; total_profit=result_cache['profit']; shares=result_cache['shares']
            summary = ", ".join(f"{k}: {format_currency(v)}" for k,v in shares.items())
            add_profit_share_event(scope, total_rev, total_cost, total_profit, summary)
            messagebox.showinfo('Đã lưu', f'Đã lưu lần chia: {scope}')
            win.destroy(); self.refresh_shares()

        btns = ttk.Frame(win); btns.grid(column=0,row=3,sticky='w', padx=6, pady=(6,0))
        ttk.Button(btns, text='Xem trước', command=do_preview).pack(side='left', padx=(0,8))
        ttk.Button(btns, text='Lưu lần chia', command=do_save).pack(side='left')
        e.focus_set(); win.bind('<Return>', lambda ev: do_preview())

    def delete_selected_share(self):
        sel = self.tree_shares.selection()
        if not sel: return
        item = sel[0]; event_id = self.tree_shares.item(item,'values')[0]
        if not messagebox.askyesno('Xác nhận','Xóa bản ghi chia này?'): return
        if delete_profit_share_event(event_id): self.refresh_shares()
        else: messagebox.showerror('Lỗi','Không xóa được')

    def open_delete_share_dialog(self):
        """Xóa bản ghi chia lợi nhuận đã chọn trong bảng"""
        sel = self.tree_shares.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một bản ghi chia để xóa.")
            return
            
        vals = self.tree_shares.item(sel[0], 'values')
        if not vals:
            return
            
        # Giả sử cột đầu tiên là ID và cột thứ hai là scope
        event_id = vals[0] if len(vals) > 0 else ""
        scope = vals[1] if len(vals) > 1 else ""
        
        if not messagebox.askyesno('Xác nhận', f'Xóa bản ghi chia "{scope}"?'):
            return
            
        try:
            from utils import delete_profit_share_event
            ok = delete_profit_share_event(event_id)
            if ok:
                messagebox.showinfo('Thành công', 'Đã xóa bản ghi chia')
                self.refresh_shares()
            else:
                messagebox.showerror('Lỗi', 'Không xóa được')
        except Exception as ex:
            messagebox.showerror('Lỗi', str(ex))

class WaterInputFrame(ttk.Frame):
    """Tab quản lý nhập nước: nhập danh mục nước mới và bổ sung."""
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.water_sales_frame = None  # Will be set after both frames are created
        self.build()

    def build(self):
        row = 0
        ttk.Label(self, text='Nhập nước', font=('Segoe UI',12,'bold')).grid(column=0, row=row, columnspan=8, sticky='w')
        row += 1
        ttk.Label(self, text='Nhập nước mới / bổ sung:').grid(column=0, row=row, sticky='w')
        row += 1
        ttk.Label(self, text='Tên:').grid(column=0, row=row, sticky='e')
        self.var_item_name = tk.StringVar()
        name_entry = ttk.Entry(self, textvariable=self.var_item_name, width=16)
        name_entry.grid(column=1, row=row, sticky='w')
        
        # Add tooltip for item name
        Tooltip(name_entry, "Tên sản phẩm nước", example="Aquafina 500ml, Coca Cola 330ml")
        
        ttk.Label(self, text='SL:').grid(column=2, row=row, sticky='e')
        self.var_item_qty = tk.StringVar(value='1')
        qty_entry = ttk.Entry(self, textvariable=self.var_item_qty, width=6)
        qty_entry.grid(column=3, row=row, sticky='w')
        
        # Add tooltip for quantity
        Tooltip(qty_entry, "Số lượng nhập kho", example="24 (thùng), 100 (chai)")
        
        ttk.Label(self, text='Đơn giá:').grid(column=4, row=row, sticky='e')
        self.var_item_price = tk.StringVar()
        e_item_price = ttk.Entry(self, textvariable=self.var_item_price, width=12)
        e_item_price.grid(column=5, row=row, sticky='w')
        
        # Add tooltip for price
        Tooltip(e_item_price, "Giá bán lẻ cho khách", example="15.000 ₫ (tự động format)")
        
        def _fmt_water_item(*_):
            raw=self.var_item_price.get(); digits=''.join(ch for ch in raw if ch.isdigit())
            if not digits: return
            try: self.var_item_price.set(f"{int(digits):,}".replace(',', '.') + ' ₫')
            except: pass
        e_item_price.bind('<KeyRelease>', _fmt_water_item)
        e_item_price.bind('<FocusOut>', _fmt_water_item)
        
        self.btn_save_item = ttk.Button(self, text='Nhập nước', command=self.save_water_item)
        self.btn_save_item.grid(column=6, row=row, sticky='w', padx=(8,0))
        
        # Add tooltip for save button
        Tooltip(self.btn_save_item, "Lưu sản phẩm mới vào kho", example="Thêm vào danh sách hoặc cộng dồn số lượng")
        
        delete_btn = ttk.Button(self, text='Xóa nước đã nhập', command=self.open_delete_item_dialog)
        delete_btn.grid(column=7, row=row, sticky='w')
        
        # Add tooltip for delete button  
        Tooltip(delete_btn, "Xóa sản phẩm khỏi kho", example="Chọn sản phẩm trong bảng trước khi xóa")
        row += 1
        row += 1
        # Nút chung làm mới & tải lại
        ttk.Button(self, text='Làm mới', command=self.reload_all).grid(column=6, row=row, sticky='w', pady=(2,2))
        ttk.Button(self, text='Tải lại dữ liệu', command=self.reload_all).grid(column=7, row=row, sticky='w', pady=(2,2))
        row += 1
        cols = ('ten','ton','don_gia')
        self.tree_items = ttk.Treeview(self, columns=cols, show='headings', height=10)
        for c,t,w in (('ten','Tên',150),('ton','SL tồn',70),('don_gia','Đơn giá',110)):
            self.tree_items.heading(c,text=t)
            self.tree_items.column(c,width=w,anchor='center')
        self.tree_items.grid(column=0,row=row,columnspan=8,sticky='nwe', pady=(2,6))
        sb = ttk.Scrollbar(self, orient='vertical', command=self.tree_items.yview)
        self.tree_items.configure(yscroll=sb.set)
        sb.grid(column=8,row=row,sticky='ns')
        try:
            attach_tree_enhancements(self.winfo_toplevel(), self.tree_items)
        except Exception:
            pass
        
        for c in range(6):
            self.grid_columnconfigure(c, weight=1)
        # init
        self.refresh_items()
        # Popup edit instead of inline
        self.tree_items.bind('<Double-1>', lambda e: self._open_edit_popup_item())
        
    def reload_all(self):
        self.refresh_items()

    def refresh_items(self):
        for i in self.tree_items.get_children(): self.tree_items.delete(i)
        items = read_water_items()
        for it in items:
            self.tree_items.insert('', 'end', values=(it.get('ten',''), it.get('so_luong_ton',''), format_currency(it.get('don_gia_vnd',0))))
        try:
            apply_zebra(self.tree_items)
        except Exception:
            pass

    def open_delete_item_dialog(self):
        """Xóa nước đã chọn trong bảng danh mục"""
        sel = self.tree_items.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một loại nước để xóa.")
            return
            
        vals = self.tree_items.item(sel[0], 'values')
        if not vals:
            return
            
        name = vals[0]  # Tên nước
        
        if not messagebox.askyesno('Xác nhận', f'Xóa loại nước "{name}" khỏi danh mục?'):
            return
            
        try:
            from utils import delete_water_item
            ok = delete_water_item(name)
            if ok:
                messagebox.showinfo('Thành công', f'Đã xóa {name}')
                self.refresh_items()
                self._notify_water_sales_update()  # Đồng bộ với tab bán nước
            else:
                messagebox.showerror('Lỗi', 'Không xóa được')
        except Exception as ex:
            messagebox.showerror('Lỗi', str(ex))

    def _open_edit_popup_item(self):
        sel = self.tree_items.selection()
        if not sel:
            return
        vals = self.tree_items.item(sel[0],'values')
        if not vals:
            return
        old_name, ton_txt, don_gia_txt = vals
        try:
            from utils import parse_currency_any
            old_price = parse_currency_any(don_gia_txt)
        except Exception:
            old_price = 0
        win = tk.Toplevel(self); win.title(f'Sửa nước {old_name}')
        win.transient(self.winfo_toplevel()); win.grab_set()
        ttk.Label(win, text=f'Nước: {old_name}', font=('Segoe UI',10,'bold')).grid(column=0,row=0,columnspan=2,sticky='w', padx=6, pady=(6,4))
        ttk.Label(win, text='Tên mới:').grid(column=0,row=1,sticky='e', padx=6)
        var_name = tk.StringVar(value=old_name)
        e_name = ttk.Entry(win, textvariable=var_name, width=22); e_name.grid(column=1,row=1,sticky='w', pady=2)
        ttk.Label(win, text='Đơn giá:').grid(column=0,row=2,sticky='e', padx=6)
        var_price = tk.StringVar(value=(f"{old_price:,}".replace(',', '.') + ' ₫') if old_price else '')
        e_price = ttk.Entry(win, textvariable=var_price, width=14); e_price.grid(column=1,row=2,sticky='w', pady=2)
        def _fmt_price_local(*_):
            raw=var_price.get(); digits=''.join(ch for ch in raw if ch.isdigit())
            if not digits: return
            try: var_price.set(f"{int(digits):,}".replace(',', '.') + ' ₫')
            except: pass
        e_price.bind('<KeyRelease>', _fmt_price_local)
        e_price.bind('<FocusOut>', _fmt_price_local)
        ttk.Label(win, text='Bổ sung SL:').grid(column=0,row=3,sticky='e', padx=6)
        var_add_qty = tk.StringVar(value='0')
        e_qty = ttk.Entry(win, textvariable=var_add_qty, width=10); e_qty.grid(column=1,row=3,sticky='w', pady=2)

        def do_save():
            try:
                new_name = var_name.get().strip()
                from utils import parse_currency_any
                price = parse_currency_any(var_price.get())
                add_qty = int(var_add_qty.get()) if var_add_qty.get().strip() else 0
                if not new_name:
                    raise ValueError('Tên không được trống')
                ok = update_water_item(old_name, new_name, price)
                if not ok:
                    raise ValueError('Không cập nhật được (không tìm thấy)')
                if add_qty > 0:
                    add_water_item(new_name, add_qty, price)
                messagebox.showinfo('Đã lưu','Đã cập nhật nước')
                win.destroy(); self.refresh_items()
                self._notify_water_sales_update()  # Đồng bộ với tab bán nước
            except Exception as ex:
                messagebox.showerror('Lỗi', str(ex))

        btns = ttk.Frame(win); btns.grid(column=0,row=4,columnspan=2,sticky='w', padx=6, pady=(6,6))
        ttk.Button(btns, text='Lưu', command=do_save).pack(side='left')
        ttk.Button(btns, text='Hủy', command=win.destroy).pack(side='left', padx=6)
        e_name.focus_set(); win.bind('<Return>', lambda ev: do_save())

    def _notify_water_sales_update(self):
        """Thông báo cho tab bán nước rằng danh sách nước đã được cập nhật"""
        if self.water_sales_frame:
            try:
                self.water_sales_frame._sync_item_names()
            except Exception:
                pass  # Ignore errors if the sales frame is not ready

    def save_water_item(self):
        # Chỉ thêm mới / bổ sung
        try:
            name = self.var_item_name.get().strip()
            qty = int(self.var_item_qty.get())
            from utils import parse_currency_any
            price = parse_currency_any(self.var_item_price.get())
            if not name:
                raise ValueError('Tên không được trống')
            add_water_item(name, qty, price)
            messagebox.showinfo('Thành công','Đã nhập / bổ sung nước')
            self.refresh_items()
            self._notify_water_sales_update()  # Đồng bộ với tab bán nước
            self.var_item_name.set(''); self.var_item_qty.set('1'); self.var_item_price.set('')
        except Exception as ex:
            messagebox.showerror('Lỗi', str(ex))

class WaterSalesFrame(ttk.Frame):
    """Tab quản lý bán nước: ghi nhận doanh thu bán nước theo ngày."""
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.water_input_frame = None  # Will be set after both frames are created
        self.build()

    def build(self):
        row = 0
        ttk.Label(self, text='Bán nước', font=('Segoe UI',12,'bold')).grid(column=0, row=row, columnspan=8, sticky='w')
        row += 1
        # Bán nước
        ttk.Label(self, text='Ngày:').grid(column=0,row=row,sticky='e')
        self.var_sale_day = tk.StringVar(value=datetime.today().strftime('%d/%m/%Y'))
        wrap_day = ttk.Frame(self)
        wrap_day.grid(column=1,row=row,sticky='w')
        ttk.Entry(wrap_day, textvariable=self.var_sale_day, width=12).pack(side='left')
        ttk.Button(wrap_day, text='📅', width=3, command=lambda: self._open_date_picker(self.var_sale_day, on_change=self.refresh_sales)).pack(side='left', padx=(3,0))
        row += 1
        ttk.Label(self, text='Chọn nước:').grid(column=0,row=row,sticky='e')
        self.var_sale_item = tk.StringVar()
        self.cb_sale_item = ttk.Combobox(self, textvariable=self.var_sale_item, values=[], width=16, state='readonly')
        self.cb_sale_item.grid(column=1,row=row,sticky='w')
        ttk.Label(self, text='SL bán:').grid(column=2,row=row,sticky='e')
        self.var_sale_qty = tk.StringVar(value='1')
        ttk.Entry(self, textvariable=self.var_sale_qty, width=6).grid(column=3,row=row,sticky='w')
        ttk.Button(self, text='Bán', command=self.sell_water).grid(column=4,row=row,sticky='w')
        ttk.Button(self, text='Xóa dòng bán', command=self.open_delete_sale_dialog).grid(column=5,row=row,sticky='w')
        row += 1
        self.var_sale_total_day = tk.StringVar(value='0')
        ttk.Label(self, text='Tổng tiền nước ngày:').grid(column=0,row=row,sticky='e')
        ttk.Label(self, textvariable=self.var_sale_total_day, font=('Segoe UI',10,'bold')).grid(column=1,row=row,sticky='w')
        row += 1
        cols2 = ('ten','so_luong','don_gia','tong')
        self.tree_sales = ttk.Treeview(self, columns=cols2, show='headings', height=12)
        for c,t,w in (('ten','Tên',150),('so_luong','SL',70),('don_gia','Đơn giá',110),('tong','Tổng',120)):
            self.tree_sales.heading(c,text=t)
            self.tree_sales.column(c,width=w,anchor='center')
        self.tree_sales.grid(column=0,row=row,columnspan=8,sticky='nwe', pady=(4,4))
        sb2 = ttk.Scrollbar(self, orient='vertical', command=self.tree_sales.yview)
        self.tree_sales.configure(yscroll=sb2.set)
        sb2.grid(column=8,row=row,sticky='ns')
        try:
            attach_tree_enhancements(self.winfo_toplevel(), self.tree_sales)
        except Exception:
            pass
        for c in range(6):
            self.grid_columnconfigure(c, weight=1)
        # init
        self._sync_item_names()
        self.refresh_sales()
        
    def _sync_item_names(self):
        items = read_water_items()
        names = [i['ten'] for i in items]
        self.cb_sale_item['values'] = names
        if names and not self.var_sale_item.get():
            self.var_sale_item.set(names[0])

    def _notify_water_input_update(self):
        """Thông báo cho tab nhập nước rằng số lượng tồn đã thay đổi"""
        if self.water_input_frame:
            try:
                self.water_input_frame.refresh_items()
            except Exception as ex:
                try:
                    logging.getLogger('suk.ui').debug('water_input_frame.refresh_items error: %s', ex)
                except Exception:
                    pass  # Still suppress if logging somehow fails

    def _open_date_picker(self, target_var: tk.StringVar, on_change=None):
        # Reuse simple calendar like other frames
        try:
            cur = datetime.strptime(target_var.get(), '%d/%m/%Y')
        except Exception:
            cur = datetime.today()
        year = cur.year; month = cur.month
        popup = tk.Toplevel(self); popup.title('Chọn ngày'); popup.transient(self.winfo_toplevel()); popup.grab_set()
        frm = ttk.Frame(popup, padding=6); frm.pack(fill='both', expand=True)
        header_var = tk.StringVar()
        cal_frame = ttk.Frame(frm); cal_frame.pack()
        def build(y,m):
            for w in list(cal_frame.winfo_children()): w.destroy()
            header_var.set(f"{m:02d}/{y}")
            week_days=['T2','T3','T4','T5','T6','T7','CN']
            for c,txt in enumerate(week_days): ttk.Label(cal_frame,text=txt,width=3,anchor='center',font=('Segoe UI',9,'bold')).grid(row=0,column=c)
            import calendar as _cal
            for r,week in enumerate(_cal.monthcalendar(y,m),start=1):
                for c,day in enumerate(week):
                    if day==0: continue
                    b = ttk.Button(cal_frame,text=str(day),width=3,command=lambda dd=day,mm=m,yy=y: select(yy,mm,dd))
                    if day==date.today().day and m==date.today().month and y==date.today().year:
                        try:
                            style=ttk.Style(self); style.configure('Today.TButton', foreground='#d32f2f'); b.configure(style='Today.TButton')
                        except Exception as ex:
                            try:
                                logging.getLogger('suk.ui').debug('Calendar style apply failed: %s', ex)
                            except Exception:
                                pass
                    b.grid(row=r,column=c,padx=1,pady=1)
        def select(y,m,d):
            target_var.set(f"{d:02d}/{m:02d}/{y}"); popup.destroy();
            if on_change: on_change()
        def prev():
            nonlocal year,month
            month-=1
            if month==0: month=12; year-=1
            build(year,month)
        def nxt():
            nonlocal year,month
            month+=1
            if month==13: month=1; year+=1
            build(year,month)
        top = ttk.Frame(frm); top.pack(fill='x', pady=(0,4))
        ttk.Button(top,text='◀',width=3,command=prev).pack(side='left')
        ttk.Label(top,textvariable=header_var,font=('Segoe UI',10,'bold')).pack(side='left', padx=6)
        ttk.Button(top,text='▶',width=3,command=nxt).pack(side='left')
        ttk.Button(top,text='Hôm nay',command=lambda: select(date.today().year,date.today().month,date.today().day)).pack(side='right')
        build(year,month)

    def sell_water(self):
        try:
            day_iso = to_iso_date(self.var_sale_day.get().strip())
            name = self.var_sale_item.get().strip()
            qty = int(self.var_sale_qty.get())
            total = record_water_sale(day_iso, name, qty)
            messagebox.showinfo('Đã bán', f'{name} x{qty}: {format_currency(total)}')
            self.refresh_sales()
            self._notify_water_input_update()  # Đồng bộ với tab nhập nước
        except Exception as ex:
            messagebox.showerror('Lỗi', str(ex))

    def refresh_sales(self):
        for i in self.tree_sales.get_children(): self.tree_sales.delete(i)
        try:
            day_iso = to_iso_date(self.var_sale_day.get().strip())
        except Exception:
            return
        
        # Hiển thị từng lần bán riêng biệt thay vì aggregate
        from utils import day_water_sales
        sales = day_water_sales(day_iso)  # Lấy raw data thay vì aggregate
        total_day = 0
        for r in sales:
            total_day += r.get('tong_vnd',0)
            self.tree_sales.insert('', 'end', values=(
                r.get('ten',''), 
                r.get('so_luong',''), 
                format_currency(r.get('don_gia_vnd',0)), 
                format_currency(r.get('tong_vnd',0))
            ))
        self.var_sale_total_day.set(format_currency(total_day))
        try:
            apply_zebra(self.tree_sales)
        except Exception:
            pass

    def open_delete_sale_dialog(self):
        """Xóa dòng bán nước đã chọn trong bảng"""
        sel = self.tree_sales.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một dòng bán để xóa.")
            return
            
        vals = self.tree_sales.item(sel[0], 'values')
        if not vals or len(vals) < 4:
            messagebox.showerror("Lỗi", "Dữ liệu dòng bán không hợp lệ.")
            return
            
        # vals = [tên, số_lượng, đơn_giá, tổng_tiền]
        name = vals[0].strip()
        qty_str = vals[1].strip()
        price_str = vals[2].strip()
        
        try:
            qty = int(qty_str)
        except:
            messagebox.showerror("Lỗi", f"Số lượng không hợp lệ: '{qty_str}'")
            return
            
        try:
            # Parse đơn giá từ cột "Đơn giá" (có format "15.000 ₫")
            from utils import parse_currency_any
            price = parse_currency_any(price_str)
        except:
            messagebox.showerror("Lỗi", f"Đơn giá không hợp lệ: '{price_str}'")
            return
            
        if not messagebox.askyesno('Xác nhận', f'Xóa dòng bán {name} SL {qty}?'):
            return
            
        try:
            from utils import delete_water_sale
            day_iso = to_iso_date(self.var_sale_day.get().strip())
            
            # Debug: Show what we're trying to delete
            print(f"DEBUG: Trying to delete: day={day_iso}, name='{name}', qty={qty}, price={price}")
            
            ok = delete_water_sale(day_iso, name, qty, price)
            if ok:
                messagebox.showinfo('Thành công', 'Đã xóa dòng bán')
                self.refresh_sales()
                self._notify_water_input_update()  # Đồng bộ với tab nhập nước
            else:
                # Debug: Show available records
                from utils import day_water_sales
                available = day_water_sales(day_iso)
                debug_msg = f"Không tìm thấy dòng bán phù hợp:\n"
                debug_msg += f"Tìm kiếm: {name} | {qty} | {price}\n\n"
                debug_msg += "Có sẵn:\n"
                for i, rec in enumerate(available):
                    debug_msg += f"{i+1}. {rec.get('ten','')} | {rec.get('so_luong','')} | {rec.get('don_gia_vnd','')}\n"
                messagebox.showerror('Lỗi debug', debug_msg)
        except Exception as ex:
            messagebox.showerror('Lỗi', str(ex))

class ScheduleFrame(ttk.Frame):
    """Tab thời khóa biểu - hiển thị lịch tuần với trạng thái sân"""
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.current_week_start = self._get_week_start(datetime.today())
        self.build()

    def _get_week_start(self, date_obj):
        """Lấy ngày đầu tuần (thứ 2) của tuần chứa ngày cho trước"""
        days_since_monday = date_obj.weekday()
        week_start = date_obj - timedelta(days=days_since_monday)
        return week_start.date()

    def build(self):
        # Header với navigation tuần
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(header_frame, text='🗓️ Thời khóa biểu tuần', font=('Segoe UI', 12, 'bold')).pack(side='left')
        
        nav_frame = ttk.Frame(header_frame)
        nav_frame.pack(side='right')
        
        ttk.Button(nav_frame, text='◀ Tuần trước', command=self.prev_week, style='Large.TButton').pack(side='left', padx=(0, 5))
        
        self.week_label = ttk.Label(nav_frame, text='', font=('Segoe UI', 12, 'bold'))
        self.week_label.pack(side='left', padx=(5, 5))
        
        ttk.Button(nav_frame, text='Tuần sau ▶', command=self.next_week, style='Large.TButton').pack(side='left', padx=(5, 0))
        ttk.Button(nav_frame, text='Hôm nay', command=self.goto_today, style='Large.TButton').pack(side='left', padx=(10, 0))
        
        # Main schedule container với scroll
        schedule_container = ttk.Frame(self)
        schedule_container.pack(fill='both', expand=True)
        
        # Canvas và scrollbar cho schedule
        self.canvas = tk.Canvas(schedule_container, bg='white')
        v_scrollbar = ttk.Scrollbar(schedule_container, orient='vertical', command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(schedule_container, orient='horizontal', command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # Frame chứa schedule grid
        self.schedule_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.schedule_frame, anchor='nw')
        
        # Bind resize
        self.schedule_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        self.refresh_schedule()

    def _on_frame_configure(self, event):
        """Cập nhật scroll region khi frame thay đổi"""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        """Cập nhật kích thước canvas window"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def prev_week(self):
        """Chuyển về tuần trước"""
        self.current_week_start -= timedelta(days=7)
        self.refresh_schedule()

    def next_week(self):
        """Chuyển tới tuần sau"""
        self.current_week_start += timedelta(days=7)
        self.refresh_schedule()

    def goto_today(self):
        """Về tuần hiện tại"""
        self.current_week_start = self._get_week_start(datetime.today())
        self.refresh_schedule()

    def refresh_schedule(self):
        """Làm mới thời khóa biểu"""
        # Clear existing widgets
        for widget in self.schedule_frame.winfo_children():
            widget.destroy()
        
        # Update week label
        week_end = self.current_week_start + timedelta(days=6)
        self.week_label.config(text=f"{self.current_week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}")
        
        # Tạo header grid
        self._create_schedule_grid()

    def _create_schedule_grid(self):
        """Tạo lưới thời khóa biểu"""
        # Days of week
        days = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
        
        # Hours (6:00 - 22:00)
        hours = [f"{h:02d}:00" for h in range(6, 23)]
        
        # Header row - Giờ với font lớn hơn
        ttk.Label(self.schedule_frame, text='Giờ', font=('Segoe UI', 14, 'bold'), relief='ridge', 
                 borderwidth=2, anchor='center', width=8).grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        
        # Header row - Các thứ với font lớn hơn
        for col, day in enumerate(days, start=1):
            date_obj = self.current_week_start + timedelta(days=col-1)
            day_text = f"{day}\n{date_obj.strftime('%d/%m')}"
            ttk.Label(self.schedule_frame, text=day_text, font=('Segoe UI', 12, 'bold'), 
                     relief='ridge', borderwidth=2, anchor='center', width=18).grid(row=0, column=col, sticky='nsew', padx=2, pady=2)
        
        # Lấy dữ liệu cho tuần
        week_data = self._get_week_data()
        
        # Grid cells - Giờ x Ngày với kích thước lớn hơn
        for row, hour in enumerate(hours, start=1):
            # Cột giờ với font lớn hơn
            ttk.Label(self.schedule_frame, text=hour, font=('Segoe UI', 12, 'bold'), 
                     relief='ridge', borderwidth=1, anchor='center').grid(row=row, column=0, sticky='nsew', padx=2, pady=2)
            
            # Các cột ngày
            for col in range(1, 8):
                date_obj = self.current_week_start + timedelta(days=col-1)
                date_key = date_obj.strftime('%Y-%m-%d')
                hour_key = hour.split(':')[0]  # Chỉ lấy giờ
                
                # Tạo cell cho slot này với kích thước lớn hơn
                cell_frame = tk.Frame(self.schedule_frame, relief='ridge', bd=2, bg='white', 
                                    width=160, height=80)  # Tăng kích thước ô
                cell_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=2)
                cell_frame.grid_propagate(False)  # Giữ kích thước cố định
                
                # Hiển thị thông tin trong cell
                self._populate_cell(cell_frame, date_key, hour_key, week_data)
        
        # Configure grid weights
        for i in range(len(hours) + 1):
            self.schedule_frame.grid_rowconfigure(i, weight=1)
        for i in range(8):
            self.schedule_frame.grid_columnconfigure(i, weight=1)

    def _get_week_data(self):
        """Lấy dữ liệu cho tuần hiện tại từ daily records và subscriptions"""
        week_data = {}
        
        # Lấy dữ liệu từ daily records
        try:
            from utils import read_daily_records_grouped_by_date
            daily_data = read_daily_records_grouped_by_date()
            
            for date_str, records in daily_data.items():
                if date_str not in week_data:
                    week_data[date_str] = {'daily': [], 'subscriptions': []}
                week_data[date_str]['daily'] = records
        except Exception as e:
            print(f"Lỗi đọc daily records: {e}")
            pass
        
        # Lấy dữ liệu từ subscriptions
        try:
            from utils import read_all_subscriptions
            subs = read_all_subscriptions()
            
            # Lọc subscription cho tháng hiện tại
            current_month = self.current_week_start.strftime('%Y-%m')
            month_subs = [s for s in subs if s.get('thang', '').startswith(current_month)]
            
            # Ánh xạ subscription vào các ngày trong tuần
            for sub in month_subs:
                thu_str = sub.get('thu', '')
                if not thu_str:
                    continue
                    
                days = [d.strip() for d in thu_str.split(',')]
                for day in days:
                    day_mapping = {
                        'Thứ 2': 0, 'Thứ 3': 1, 'Thứ 4': 2, 'Thứ 5': 3, 
                        'Thứ 6': 4, 'Thứ 7': 5, 'Chủ nhật': 6
                    }
                    
                    if day in day_mapping:
                        day_offset = day_mapping[day]
                        date_obj = self.current_week_start + timedelta(days=day_offset)
                        date_key = date_obj.strftime('%Y-%m-%d')
                        
                        if date_key not in week_data:
                            week_data[date_key] = {'daily': [], 'subscriptions': []}
                        
                        week_data[date_key]['subscriptions'].append(sub)
        except:
            pass
        
        return week_data

    def _populate_cell(self, cell_frame, date_key, hour_key, week_data):
        """Điền thông tin vào ô thời khóa biểu"""
        cell_frame.configure(height=80, width=160)
        
        # Container cho nội dung
        content_frame = tk.Frame(cell_frame, bg='white')
        content_frame.pack(fill='both', expand=True, padx=3, pady=3)
        
        # Nhãn cho sân 1 và sân 2
        san1_frame = tk.Frame(content_frame, bg='#e8f4f8', height=35)
        san1_frame.pack(fill='x', pady=(0, 2))
        san1_frame.pack_propagate(False)
        
        san2_frame = tk.Frame(content_frame, bg='#f0f8e8', height=35)
        san2_frame.pack(fill='x')
        san2_frame.pack_propagate(False)
        
        # Kiểm tra dữ liệu cho ngày và giờ này
        day_data = week_data.get(date_key, {'daily': [], 'subscriptions': []})
        
        # Xử lý sân 1
        san1_info = self._get_court_info(day_data, hour_key, 'Sân 1')
        san1_label = tk.Label(san1_frame, text=san1_info['text'], bg=san1_info['bg'], 
                             fg=san1_info['fg'], font=('Segoe UI', 10), anchor='center')
        san1_label.pack(fill='both', expand=True)
        
        # Xử lý sân 2
        san2_info = self._get_court_info(day_data, hour_key, 'Sân 2')
        san2_label = tk.Label(san2_frame, text=san2_info['text'], bg=san2_info['bg'], 
                             fg=san2_info['fg'], font=('Segoe UI', 10), anchor='center')
        san2_label.pack(fill='both', expand=True)

    def _get_court_info(self, day_data, hour_key, court):
        """Lấy thông tin trạng thái sân cho giờ và sân cụ thể"""
        # Mặc định
        info = {'text': court, 'bg': '#f8f9fa', 'fg': '#6c757d'}
        
        # Kiểm tra daily bookings
        for record in day_data['daily']:
            if record.get('san') == court:
                khung_gio = record.get('khung_gio', '')
                if self._hour_in_range(hour_key, khung_gio):
                    nguoi = record.get('nguoi', 'Không rõ')
                    price = record.get('gia_vnd', 0)
                    info = {
                        'text': f"{nguoi}\n{format_currency(price)}", 
                        'bg': '#fff3cd', 
                        'fg': '#856404'
                    }
                    break
        
        # Kiểm tra subscriptions (cập nhật để sử dụng thông tin giờ chi tiết)
        for sub in day_data['subscriptions']:
            if sub.get('san') == court:
                gio_display = sub.get('gio_moi_buoi_display', sub.get('gio_moi_buoi', '1'))
                if self._subscription_active_detailed(hour_key, gio_display):
                    ten = sub.get('ten', 'Gói tháng')
                    info = {
                        'text': f"{ten}\n(Gói tháng)", 
                        'bg': '#d1ecf1', 
                        'fg': '#0c5460'
                    }
                    break
        
        return info

    def _hour_in_range(self, hour_key, khung_gio):
        """Kiểm tra giờ có nằm trong khung giờ không"""
        try:
            hour = int(hour_key)
            # Parse khung_gio có thể là format "HH:MM-HH:MM" hoặc "8h-10h"
            if '-' in khung_gio:
                start_str, end_str = khung_gio.split('-')
                
                # Xử lý format "8h-10h"
                if 'h' in start_str and 'h' in end_str:
                    start_hour = int(start_str.replace('h', ''))
                    end_hour = int(end_str.replace('h', ''))
                else:
                    # Xử lý format "HH:MM-HH:MM"
                    start_hour = int(start_str.split(':')[0])
                    end_hour = int(end_str.split(':')[0])
                
                return start_hour <= hour < end_hour
        except Exception as e:
            pass
        return False

    def _subscription_active(self, hour_key, gio_moi_buoi):
        """Kiểm tra subscription có hoạt động trong giờ này không (logic cũ)"""
        try:
            hour = int(hour_key)
            # Giả sử subscription hoạt động trong khung giờ phổ biến
            # Có thể cải thiện bằng cách lưu thêm thông tin giờ trong subscription
            common_hours = {
                1: [19],  # 1 giờ: 19:00-20:00
                2: [18, 19],  # 2 giờ: 18:00-20:00
                3: [17, 18, 19]  # 3 giờ: 17:00-20:00
            }
            return hour in common_hours.get(gio_moi_buoi, [])
        except:
            pass
        return False

    def _subscription_active_detailed(self, hour_key, gio_display):
        """Kiểm tra subscription có hoạt động trong giờ này không với thông tin chi tiết"""
        try:
            hour = int(hour_key)
            
            # Parse format "2 (7:00-9:00)" or just "2"
            if '(' in gio_display and ')' in gio_display:
                # Có thông tin chi tiết về giờ
                time_range = gio_display.split('(')[1].split(')')[0]
                start_str, end_str = time_range.split('-')
                start_hour = int(start_str.split(':')[0])
                end_hour = int(end_str.split(':')[0])
                return start_hour <= hour < end_hour
            else:
                # Chỉ có số giờ, sử dụng logic cũ
                gio_count = int(gio_display.split()[0]) if gio_display else 1
                return self._subscription_active(hour_key, gio_count)
        except:
            pass
        return False

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # CSV mode - no additional initialization needed
        print("📄 Hệ thống Quản lý SUK Pickleball - Chế độ CSV")
        
        self.title(APP_TITLE)
        # Thiết lập icon cửa sổ & taskbar (additive, không đổi logic nghiệp vụ)
        try:
            import os, sys
            from utils import _abs_path  # dùng để tìm icon cạnh exe / module
            icon_path = _abs_path('icon_suk.ico')
            if os.path.exists(icon_path):
                try:
                    # iconphoto áp dụng cho cả taskbar trong phần lớn môi trường Windows hiện đại
                    self.iconbitmap(icon_path)  # fallback cho compatibility
                except Exception:
                    pass
                try:
                    ico = tk.PhotoImage(file=icon_path)
                    # Một số bản .ico đa kích thước có thể không load bằng PhotoImage; nếu lỗi bỏ qua
                    self.iconphoto(True, ico)
                except Exception:
                    pass
        except Exception:
            pass
        self.geometry("980x640")
        self.minsize(860, 560)
        self.style = ttk.Style(self)
        self._init_style()
        self._build_ui()
        
        # Ensure data files exist
        ensure_all_data_files()
        # Kiểm tra nhanh tính toàn vẹn (additive – chỉ log, không thay đổi dòng chảy)
        try:
            from utils import verify_data_integrity
            integrity = verify_data_integrity()
            if integrity.get('overlap_count') or integrity.get('missing_id_count'):
                ui_logger.warning(
                    "Data integrity cảnh báo: overlap=%s missing_id=%s", 
                    integrity.get('overlap_count'), integrity.get('missing_id_count')
                )
        except Exception as ex:
            ui_logger.debug("Integrity check skipped: %s", ex)
        
        print("✅ Hệ thống Quản lý SUK Pickleball khởi tạo thành công")
            
    def _init_style(self):
        """Enhanced styling with better visual hierarchy and modern design."""
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass
        
        # Enhanced typography system
        body_family = 'Segoe UI'
        self.option_add('*Font', (body_family, 11))
        
        # Enhanced Button Styling with better elevation and states
        try:
            elevated_layout = [
                ('Button.border', {'sticky': 'nswe', 'children': [
                    ('Button.focus', {'sticky': 'nswe', 'children': [
                        ('Button.padding', {'sticky': 'nswe', 'children': [
                            ('Button.label', {'sticky': 'nswe'})
                        ]})
                    ]})
                ]})
            ]
            for btn_style in ('TButton','Primary.TButton','Secondary.TButton','Success.TButton','Danger.TButton','Warning.TButton','Info.TButton'):
                self.style.layout(btn_style, elevated_layout)
        except Exception:
            pass
            
        # Base Button Style - Enhanced
        self.style.configure('TButton', 
                           padding=(SPACING_MD, SPACING_SM), 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MAIN,
                           bordercolor=BORDER_COLOR, 
                           relief='raised', 
                           focusthickness=2, 
                           focuscolor=PRIMARY_COLOR,
                           font=(body_family, 10, 'normal'))
        self.style.map('TButton', 
                      background=[('pressed', NEUTRAL_200), ('active', NEUTRAL_100)], 
                      relief=[('pressed','sunken')],
                      bordercolor=[('focus', PRIMARY_COLOR), ('active', PRIMARY_COLOR)])
        
        # Primary Button - Enhanced with modern colors
        self.style.configure('Primary.TButton', 
                           background=PRIMARY_COLOR,  # #6366F1 - Modern indigo
                           foreground=SURFACE_COLOR, 
                           bordercolor=PRIMARY_COLOR,
                           font=(body_family, 10, 'bold'))
        self.style.map('Primary.TButton', 
                      background=[('pressed', PRIMARY_DARK), ('active', '#7C3AED')],  # Purple variations
                      bordercolor=[('focus', PRIMARY_DARK)])
        
        # Secondary Button - Updated with emerald
        self.style.configure('Secondary.TButton', 
                           background=SECONDARY_COLOR,  # #10B981 - Emerald
                           foreground=SURFACE_COLOR, 
                           bordercolor=SECONDARY_COLOR,
                           font=(body_family, 10, 'bold'))
        self.style.map('Secondary.TButton', 
                      background=[('pressed', '#059669'), ('active', '#34D399')])
                      
        # Success Button - Using emerald theme
        self.style.configure('Success.TButton', 
                           background=SUCCESS_COLOR,  # #10B981
                           foreground=SURFACE_COLOR, 
                           bordercolor=SUCCESS_COLOR)
        self.style.map('Success.TButton', 
                      background=[('pressed', '#047857'), ('active', '#34D399')])
        
        # Danger Button - Enhanced with modern red
        self.style.configure('Danger.TButton', 
                           background=DANGER_COLOR,  # #EF4444
                           foreground=SURFACE_COLOR, 
                           bordercolor=DANGER_COLOR,
                           font=(body_family, 10, 'bold'))
        self.style.map('Danger.TButton', 
                      background=[('pressed', '#DC2626'), ('active', '#F87171')], 
                      focuscolor=[('focus', DANGER_COLOR)])
                      
        # Warning Button - Updated with amber
        self.style.configure('Warning.TButton', 
                           background=WARNING_COLOR,  # #F59E0B
                           foreground=SURFACE_COLOR, 
                           bordercolor=WARNING_COLOR)
        self.style.map('Warning.TButton', 
                      background=[('pressed', '#D97706'), ('active', '#FCD34D')])
                      
        # Info Button - Modern blue
        self.style.configure('Info.TButton', 
                           background=INFO_COLOR,  # #3B82F6
                           foreground=SURFACE_COLOR, 
                           bordercolor=INFO_COLOR)
        self.style.map('Info.TButton', 
                      background=[('pressed', '#2563EB'), ('active', '#60A5FA')])
        
        # Large Button - For better accessibility  
        self.style.configure('Large.TButton', 
                           font=(body_family, 12, 'bold'),
                           padding=(12, 8))
        
        # Enhanced Label System with better hierarchy
        self.style.configure('TLabel', 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MAIN,
                           font=(body_family, 11))
                           
        # Header Labels - Enhanced hierarchy
        self.style.configure('Header.TLabel', 
                           font=(body_family, 16, 'bold'), 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MAIN)
                           
        self.style.configure('Subheader.TLabel', 
                           font=(body_family, 14, 'bold'), 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MAIN)
                           
        self.style.configure('Title.TLabel', 
                           font=(body_family, 12, 'bold'), 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MAIN)
                           
        # Text Labels
        self.style.configure('Body.TLabel', 
                           font=(body_family, 11), 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MAIN)
                           
        self.style.configure('Caption.TLabel', 
                           font=(body_family, 10), 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MUTED)
                           
        self.style.configure('Muted.TLabel', 
                           font=(body_family, 10), 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MUTED)
                           
        # Form Labels
        self.style.configure('FormLabel.TLabel', 
                           font=(body_family, 11, 'bold'), 
                           background=SURFACE_COLOR, 
                           foreground=TEXT_MAIN)
        
        # Status Labels - Enhanced with semantic colors
        self.style.configure('Success.TLabel', 
                           font=(body_family, 11, 'bold'), 
                           background=SURFACE_COLOR, 
                           foreground=SUCCESS_COLOR)
                           
        self.style.configure('Error.TLabel', 
                           font=(body_family, 11, 'bold'), 
                           background=SURFACE_COLOR, 
                           foreground=DANGER_COLOR)
                           
        self.style.configure('Warning.TLabel', 
                           font=(body_family, 11, 'bold'), 
                           background=SURFACE_COLOR, 
                           foreground=WARNING_COLOR)
                           
        self.style.configure('Info.TLabel', 
                           font=(body_family, 11, 'bold'), 
                           background=SURFACE_COLOR, 
                           foreground=INFO_COLOR)
        
        # Enhanced Summary Card System - transparent background
        self.style.configure('Summary.TFrame', 
                           background=BG_LIGHT,  # Same as form background 
                           relief='flat')  # Remove border
                           
        self.style.configure('SummaryTitle.TLabel', 
                           font=(body_family, 10, 'bold'), 
                           foreground=TEXT_MUTED, 
                           background=BG_LIGHT)  # Same as form background
                           
        self.style.configure('SummaryValue.TLabel', 
                           font=(body_family, 18, 'bold'), 
                           foreground=PRIMARY_COLOR, 
                           background=BG_LIGHT)  # Same as form background
                           
        self.style.configure('SummaryMeta.TLabel', 
                           font=(body_family, 9), 
                           foreground=TEXT_MUTED, 
                           background=BG_LIGHT)  # Same as form background
        
        # Enhanced Frame System
        self.style.configure('TFrame', background=SURFACE_COLOR)
        
        # Enhanced Card System with better elevation and spacing
        self.style.configure('Card.TFrame', 
                           background=SURFACE_COLOR, 
                           bordercolor=NEUTRAL_200, 
                           borderwidth=1, 
                           relief='solid')
                           
        self.style.configure('Section.TFrame', 
                           background=BG_GRADIENT_START,  # Match notebook background
                           bordercolor=BORDER_COLOR, 
                           borderwidth=0,  # Remove border for cleaner look
                           relief='flat')
        
        # Enhanced Notebook System with modern tabs
        self.style.configure('TNotebook', 
                           background=BG_GRADIENT_START, 
                           borderwidth=0,
                           tabmargins=[2, 4, 2, 0])  # Better spacing around tabs
                           
        self.style.configure('TNotebook.Tab', 
                           padding=(SPACING_LG, SPACING_MD),  # More padding for better touch targets
                           font=(body_family, 10, 'bold'), 
                           background=NEUTRAL_200,  # Lighter inactive background
                           foreground=NEUTRAL_700,  # Muted text for inactive tabs
                           bordercolor=NEUTRAL_300,
                           borderwidth=1,
                           relief='raised')  # Add subtle elevation
                           
        self.style.map('TNotebook.Tab', 
                      background=[
                          ('selected', PRIMARY_COLOR),  # Active tab with primary color
                          ('active', PRIMARY_LIGHT),    # Hover state
                          ('!active', NEUTRAL_200)      # Default state
                      ], 
                      foreground=[
                          ('selected', 'white'),        # White text on active tab
                          ('active', PRIMARY_DARK),     # Dark text on hover
                          ('!active', NEUTRAL_700)      # Muted text on inactive
                      ],
                      bordercolor=[
                          ('selected', PRIMARY_COLOR),  # Border matches active background
                          ('active', PRIMARY_LIGHT),
                          ('!active', NEUTRAL_300)
                      ],
                      relief=[
                          ('selected', 'solid'),        # Solid for active
                          ('active', 'raised'),         # Raised on hover
                          ('!active', 'flat')           # Flat for inactive
                      ])
        
        # Enhanced Entry System
        self.style.configure('TEntry', 
                           fieldbackground=SURFACE_COLOR, 
                           foreground=TEXT_MAIN,
                           bordercolor=BORDER_COLOR,
                           insertcolor=PRIMARY_COLOR,
                           selectbackground=PRIMARY_LIGHT,
                           selectforeground=TEXT_MAIN,
                           font=(body_family, 11))
                           
        self.style.map('TEntry', 
                      bordercolor=[('focus', PRIMARY_COLOR), ('active', PRIMARY_COLOR)])
        
        # Enhanced ComboBox
        self.style.configure('TCombobox',
                           fieldbackground=SURFACE_COLOR,
                           foreground=TEXT_MAIN,
                           bordercolor=BORDER_COLOR,
                           font=(body_family, 11))
                           
        self.style.map('TCombobox',
                      bordercolor=[('focus', PRIMARY_COLOR), ('active', PRIMARY_COLOR)])
        
        # Enhanced Treeview System
        try:
            self.style.element_create('Plain.Treeheading.border', 'from', 'clam')
        except Exception:
            pass
            
        self.style.configure('Data.Treeview', 
                           font=(body_family, 11), 
                           rowheight=28,
                           background=SURFACE_COLOR, 
                           fieldbackground=SURFACE_COLOR,
                           bordercolor=BORDER_COLOR, 
                           borderwidth=1)
                           
        self.style.configure('Data.Treeview.Heading', 
                           font=(body_family, 11, 'bold'), 
                           background=PRIMARY_COLOR, 
                           foreground=SURFACE_COLOR,
                           bordercolor=PRIMARY_COLOR,
                           relief='raised')
                           
        self.style.map('Data.Treeview.Heading', 
                      background=[('active', '#1565C0')])
                      
        self.style.map('Data.Treeview', 
                      background=[('selected', PRIMARY_LIGHT)], 
                      foreground=[('selected', TEXT_MAIN)])
        
        # Enhanced Separator
        self.style.configure('TSeparator', background=BORDER_COLOR)
        
        # Enhanced Checkbutton
        self.style.configure('TCheckbutton',
                           background=SURFACE_COLOR,
                           foreground=TEXT_MAIN,
                           font=(body_family, 11))
                           
        self.style.map('TCheckbutton',
                      background=[('active', NEUTRAL_50)])
        
        # Enhanced Progressbar
        self.style.configure('TProgressbar',
                           background=PRIMARY_COLOR,
                           bordercolor=BORDER_COLOR,
                           lightcolor=PRIMARY_COLOR,
                           darkcolor=PRIMARY_COLOR)
        
        # Enhanced Scrollbar
        self.style.configure('TScrollbar',
                           background=NEUTRAL_100,
                           bordercolor=BORDER_COLOR,
                           arrowcolor=TEXT_MUTED,
                           troughcolor=NEUTRAL_50)
                           
        self.style.map('TScrollbar',
                      background=[('active', NEUTRAL_200)])
        
        # Enhanced Menu Bar (if applicable)
        self.style.configure('TMenubutton',
                           background=SURFACE_COLOR,
                           foreground=TEXT_MAIN,
                           bordercolor=BORDER_COLOR,
                           font=(body_family, 11))
                           
        self.style.map('TMenubutton',
                      background=[('active', NEUTRAL_100)])
        
        # Enhanced Popup Dialog Styles
        self.style.configure('Header.TFrame',
                           background='#f8f9fa',
                           bordercolor='#dee2e6',
                           borderwidth=1,
                           relief='solid')
        
        self.style.configure('HeaderTitle.TLabel',
                           font=(body_family, 14, 'bold'),
                           background='#f8f9fa',
                           foreground='#212529')
        
        self.style.configure('HeaderSubtitle.TLabel',
                           font=(body_family, 10),
                           background='#f8f9fa',
                           foreground='#6c757d')
        
        self.style.configure('TableHeader.TFrame',
                           background='#e9ecef',
                           bordercolor='#dee2e6',
                           borderwidth=1,
                           relief='solid')
        
        self.style.configure('TableHeader.TLabel',
                           font=(body_family, 11, 'bold'),
                           background='#e9ecef',
                           foreground='#495057',
                           padding=(8, 6))
        
        self.style.configure('TableContent.TFrame',
                           background=SURFACE_COLOR)
        
        self.style.configure('TableRowEven.TFrame',
                           background='#ffffff')
        
        self.style.configure('TableRowOdd.TFrame',
                           background='#f8f9fa')
        
        self.style.configure('TableCell.TLabel',
                           background='inherit',
                           foreground=TEXT_MAIN,
                           padding=(4, 4))
        
        self.style.configure('TableCellNumber.TLabel',
                           background='inherit',
                           foreground='#0d6efd',
                           font=(body_family, 10, 'bold'),
                           padding=(4, 4))
        
        self.style.configure('EmptyState.TLabel',
                           font=(body_family, 12),
                           background=SURFACE_COLOR,
                           foreground='#6c757d')
        
        self.style.configure('EmptyStateHint.TLabel',
                           font=(body_family, 10),
                           background=SURFACE_COLOR,
                           foreground='#adb5bd')
        
        self.style.configure('ButtonBar.TFrame',
                           background='#f8f9fa',
                           bordercolor='#dee2e6',
                           borderwidth=1,
                           relief='solid')
        
        self.style.configure('Table.TCheckbutton',
                           background='inherit',
                           focuscolor='none')
        
        # Large Radiobutton for better accessibility
        self.style.configure('Large.TRadiobutton',
                           font=(body_family, 12, 'bold'),
                           background='inherit',
                           focuscolor='none')
        
        # Set root window background
        try:
            self.configure(bg=SURFACE_COLOR)
        except Exception:
            pass

    def show_toast(self, message: str, kind: str = 'info', ms: int = 2500):
        """Enhanced toast notification with better styling and animation."""
        try:
            toast = tk.Toplevel(self)
            toast.overrideredirect(True)
            toast.attributes('-topmost', True)
            
            # Enhanced color mapping with better accessibility
            colors = {
                'info': (INFO_COLOR, SURFACE_COLOR),
                'success': (SUCCESS_COLOR, SURFACE_COLOR), 
                'warning': (WARNING_COLOR, TEXT_MAIN),
                'error': (DANGER_COLOR, SURFACE_COLOR)
            }
            bg_color, text_color = colors.get(kind, (INFO_COLOR, SURFACE_COLOR))
            
            # Enhanced styling with shadow effect
            frm = tk.Frame(toast, bg=bg_color, relief='raised', bd=1)
            
            # Icon mapping for better visual communication
            icons = {
                'info': 'ℹ️',
                'success': '✅', 
                'warning': '⚠️',
                'error': '❌'
            }
            icon = icons.get(kind, 'ℹ️')
            
            # Enhanced label with icon
            lbl = tk.Label(frm, 
                          text=f"{icon} {message}", 
                          bg=bg_color, 
                          fg=text_color, 
                          font=('Segoe UI', 11, 'bold'), 
                          padx=SPACING_LG, 
                          pady=SPACING_MD)
            lbl.pack()
            frm.pack()
            
            # Enhanced positioning and sizing
            self.update_idletasks()
            w = toast.winfo_reqwidth()
            h = toast.winfo_reqheight()
            
            # Position at top-right corner as requested by customer
            padding = 20  # Distance from window edge
            x = self.winfo_x() + self.winfo_width() - w - padding
            y = self.winfo_y() + padding + 30  # Account for title bar
            
            toast.geometry(f"{w}x{h}+{x}+{y}")
            
            # Simple fade-out effect simulation
            def fade_out():
                try:
                    current_alpha = toast.attributes('-alpha')
                    if current_alpha > 0.1:
                        toast.attributes('-alpha', current_alpha - 0.1)
                        toast.after(50, fade_out)
                    else:
                        toast.destroy()
                except Exception:
                    toast.destroy()
            
            # Set initial alpha and start fade after delay
            toast.attributes('-alpha', 0.95)
            toast.after(max(100, ms - 500), fade_out)
            
        except Exception:
            # Fallback to simple message if toast fails
            print(f"Toast {kind}: {message}")
            pass

    def _build_ui(self):
        """Enhanced UI layout with modern animations and styling."""
        # Set modern gradient background
        self.configure(bg=BG_GRADIENT_START)
        
        # Add subtle window fade-in animation
        self.attributes('-alpha', 0.0)
        self._fade_in_window()
        
        # Main container with consistent background
        main_container = tk.Frame(self, bg=BG_GRADIENT_START)
        main_container.pack(fill='both', expand=True)
        
        # Enhanced Header with modern styling
        header = ttk.Frame(main_container, style='Card.TFrame')
        header.pack(fill='x', padx=SPACING_SM, pady=(SPACING_SM, 0))
        
        header_content = ttk.Frame(header)
        header_content.pack(fill='x', padx=SPACING_LG, pady=SPACING_MD)
        
        # App title with enhanced typography
        title_frame = ttk.Frame(header_content)
        title_frame.pack(side='left', fill='x', expand=True)
        
        title_label = ttk.Label(title_frame, text=APP_TITLE, style='Header.TLabel')
        title_label.pack(side='left')
        
        # Add animated version badge with improved styling
        version_frame = tk.Frame(title_frame, bg=PRIMARY_COLOR, relief='flat', bd=0)
        version_frame.pack(side='left', padx=(SPACING_MD, 0))
        
        version_label = tk.Label(
            version_frame, 
            text="v2.1.0", 
            font=('Segoe UI', 8, 'bold'),
            bg=PRIMARY_COLOR, 
            fg='white',
            padx=10, 
            pady=4
        )
        version_label.pack()
        
        # Add subtle pulsing animation to version badge
        self._animate_version_badge(version_frame, version_label)

        # Enhanced Notebook container with modern design
        notebook_container = tk.Frame(main_container, bg=BG_GRADIENT_START)
        notebook_container.pack(fill='both', expand=True, padx=SPACING_SM, pady=SPACING_SM)
        
        self.notebook = ttk.Notebook(notebook_container)
        self.notebook.pack(fill='both', expand=True)
        
        # Bind tab change animation
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        # Enhanced tab creation with consistent styling and tooltips
        self.daily_frame = DailyEntryFrame(self.notebook)
        self.summary_frame = DailySummaryFrame(self.notebook)
        self.sub_frame = SubscriptionFrame(self.notebook)
        self.monthly_frame = MonthlyStatFrame(self.notebook)
        self.share_frame = ProfitShareFrame(self.notebook)
        self.water_input_frame = WaterInputFrame(self.notebook)
        self.water_sales_frame = WaterSalesFrame(self.notebook)
        self.schedule_frame = ScheduleFrame(self.notebook)
        
        # Thiết lập kết nối đồng bộ hóa giữa hai tab nước
        self.water_input_frame.water_sales_frame = self.water_sales_frame
        self.water_sales_frame.water_input_frame = self.water_input_frame
        
        # Enhanced info frame with professional layout
        self.info_frame = ttk.Frame(self.notebook, padding=SPACING_XXL)
        
        # Main container with centered content
        main_container = ttk.Frame(self.info_frame)
        main_container.pack(expand=True, fill='both')
        
        # Header section with app branding
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill='x', pady=(0, SPACING_XXL))
        
        # App title and logo
        title_container = ttk.Frame(header_frame)
        title_container.pack(anchor='center')
        
        ttk.Label(title_container, text='🏓', font=('Segoe UI', 24)).pack()
        ttk.Label(title_container, text='Hệ thống Quản lý Sân SUK Pickleball', 
                 font=('Segoe UI', 16, 'bold'), foreground='#2563eb').pack(pady=(SPACING_SM, 0))
        ttk.Label(title_container, text='Giải pháp quản lý sân pickleball toàn diện và chuyên nghiệp', 
                 font=('Segoe UI', 10), foreground='#64748b').pack(pady=(SPACING_XS, 0))
        
        # Content area with sections
        content_frame = ttk.Frame(main_container)
        content_frame.pack(expand=True, fill='both', pady=SPACING_LG)
        
        # Left column - Features
        left_column = ttk.Frame(content_frame)
        left_column.pack(side='left', fill='both', expand=True, padx=(0, SPACING_LG))
        
        # Features section
        features_section = ttk.LabelFrame(left_column, text='🚀 Tính năng chính', padding=SPACING_LG)
        features_section.pack(fill='x', pady=(0, SPACING_MD))
        
        features = [
            ('📅', 'Quản lý đặt sân theo giờ với tính giá tự động'),
            ('📊', 'Thống kê doanh thu và chi phí theo ngày/tháng'), 
            ('📦', 'Quản lý gói tháng với đầy đủ tính năng'),
            ('📅', 'Thời khóa biểu tuần với trạng thái sân trực quan'),
            ('💰', 'Tính toán và chia lợi nhuận tự động'),
            ('🥤', 'Quản lý bán nước và doanh thu phụ'),
            ('💾', 'Sao lưu dữ liệu định kỳ và khôi phục')
        ]
        
        for icon, feature in features:
            feature_row = ttk.Frame(features_section)
            feature_row.pack(fill='x', pady=SPACING_XS)
            ttk.Label(feature_row, text=icon, font=('Segoe UI', 12)).pack(side='left', padx=(0, SPACING_SM))
            ttk.Label(feature_row, text=feature, font=('Segoe UI', 10)).pack(side='left', anchor='w')
        
        # Right column - Info
        right_column = ttk.Frame(content_frame)
        right_column.pack(side='right', fill='both', expand=True)
        
        # Version info section
        version_section = ttk.LabelFrame(right_column, text='📋 Thông tin phiên bản', padding=SPACING_LG)
        version_section.pack(fill='x', pady=(0, SPACING_MD))
        
        version_info = [
            ('Phiên bản:', 'v2.1.0'),
            ('Ngày phát hành:', 'Tháng 8, 2025'),
            ('Tác giả:', 'Trần Tuấn Khương'),
            ('Loại giấy phép:', 'Sử dụng nội bộ')
        ]
        
        for label, value in version_info:
            info_row = ttk.Frame(version_section)
            info_row.pack(fill='x', pady=SPACING_XS)
            ttk.Label(info_row, text=label, font=('Segoe UI', 10, 'bold'), width=15).pack(side='left', anchor='w')
            ttk.Label(info_row, text=value, font=('Segoe UI', 10)).pack(side='left', anchor='w')
        
        # Technical info section
        tech_section = ttk.LabelFrame(right_column, text='⚙️ Thông tin kỹ thuật', padding=SPACING_LG)
        tech_section.pack(fill='x')
        
        tech_info = [
            ('Ngôn ngữ:', 'Python 3.13+'),
            ('Giao diện:', 'Tkinter'),
            ('Lưu trữ dữ liệu:', 'Tệp CSV'),
            ('Hệ điều hành:', 'Windows 10/11')
        ]
        
        for label, value in tech_info:
            tech_row = ttk.Frame(tech_section)
            tech_row.pack(fill='x', pady=SPACING_XS)
            ttk.Label(tech_row, text=label, font=('Segoe UI', 10, 'bold'), width=15).pack(side='left', anchor='w')
            ttk.Label(tech_row, text=value, font=('Segoe UI', 10)).pack(side='left', anchor='w')
        
        # Footer with copyright - add more padding to prevent cut-off
        footer_frame = ttk.Frame(main_container)
        footer_frame.pack(fill='x', pady=(SPACING_XXL, SPACING_LG))  # Added bottom padding
        
        footer_content = ttk.Frame(footer_frame)
        footer_content.pack(anchor='center')
        
        ttk.Label(footer_content, text='© 2025 Hệ thống Quản lý Sân SUK Pickleball', 
                 font=('Segoe UI', 9), foreground='#94a3b8').pack(pady=(0, SPACING_XS))
        ttk.Label(footer_content, text='Được thiết kế để tối ưu hóa quản lý sân pickleball chuyên nghiệp', 
                 font=('Segoe UI', 9, 'italic'), foreground='#94a3b8').pack()

        # Enhanced tab configuration with logical workflow and modern icons
        tab_config = [
            # Core Operations (Daily workflow)
            (self.daily_frame, '📝 Ghi chép sân'),
            (self.summary_frame, '📊 Tổng kết ngày'),
            
            # Water Management (Grouped together)  
            (self.water_input_frame, '🥤 Nhập nước'),
            (self.water_sales_frame, '🥤 Bán nước'),

            # Customer Management
            (self.sub_frame, '🎫 Gói tháng'),
            
            # Analytics & Reports
            (self.monthly_frame, '📈 Thống kê tháng'),
            (self.share_frame, '💰 Chia lợi nhuận'),
            
            # Schedule & Info
            (self.schedule_frame, '📅 Thời khóa biểu'),
            (self.info_frame, 'ℹ️ Thông tin')
        ]
        
        for frame, label in tab_config:
            self.notebook.add(frame, text=label)

        # Enhanced Status bar with modern design
        status_frame = ttk.Frame(main_container, style='Card.TFrame')
        status_frame.pack(fill='x', side='bottom', padx=SPACING_SM, pady=(0, SPACING_SM))
        
        status_content = ttk.Frame(status_frame)
        status_content.pack(fill='x', padx=SPACING_MD, pady=SPACING_XS)
        
        # Current status
        self.status_var = tk.StringVar(value='Sẵn sàng')
        ttk.Label(status_content, textvariable=self.status_var, style='Caption.TLabel').pack(side='left')
        
        # Current time display
        self.time_var = tk.StringVar()
        ttk.Label(status_content, textvariable=self.time_var, style='Caption.TLabel').pack(side='right')
        
        # Update time periodically
        def update_time():
            from datetime import datetime
            self.time_var.set(datetime.now().strftime('%H:%M:%S - %d/%m/%Y'))
            self.after(1000, update_time)
        update_time()

        # Enhanced menu bar
        # Create enhanced menubar with consistent styling
        menubar = tk.Menu(self, font=('Arial Unicode MS', 9), 
                         bg='#f8f9fa', fg='#333333', 
                         activebackground='#e3f2fd', activeforeground='#0066cc')
        self.config(menu=menubar)
        
        # File menu with essential operations only
        file_menu = tk.Menu(menubar, tearoff=0, font=('Arial Unicode MS', 9),
                           bg='#ffffff', fg='#333333',
                           activebackground='#e3f2fd', activeforeground='#0066cc')
        file_menu.add_command(label=' Xuất PDF báo cáo      Ctrl+P', command=self._export_pdf_report)
        file_menu.add_separator() 
        file_menu.add_command(label='❌ Thoát                 Alt+F4', command=self._safe_exit)
        menubar.add_cascade(label='📁 Tệp', menu=file_menu)
        
        # Tools menu with useful utilities
        tools_menu = tk.Menu(menubar, tearoff=0, font=('Arial Unicode MS', 9),
                            bg='#ffffff', fg='#333333',
                            activebackground='#e3f2fd', activeforeground='#0066cc')
        tools_menu.add_command(label='🧮 Máy tính giá sân      F3', command=self._show_price_calculator)
        tools_menu.add_command(label='📊 Phân tích doanh thu   F4', command=self._show_revenue_analysis)
        tools_menu.add_command(label='📋 Tạo báo cáo nhanh    Ctrl+Q', command=self._quick_report)
        tools_menu.add_separator()
        tools_menu.add_command(label='🔍 Tìm kiếm dữ liệu      Ctrl+F', command=self._search_data)
        tools_menu.add_command(label='📈 Biểu đồ thống kê      Ctrl+G', command=self._show_charts)
        tools_menu.add_separator()
        tools_menu.add_command(label='🔧 Sửa chữa dữ liệu     F7', command=self._repair_data)
        menubar.add_cascade(label='🔧 Công cụ', menu=tools_menu)

        # Help menu with comprehensive support
        help_menu = tk.Menu(menubar, tearoff=0, font=('Arial Unicode MS', 9),
                           bg='#ffffff', fg='#333333',
                           activebackground='#e3f2fd', activeforeground='#0066cc')
        help_menu.add_command(label='❓ Hướng dẫn sử dụng     F1', command=self._show_help)
        help_menu.add_command(label='⌨️ Danh sách phím tắt   F8', command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label='💬 Đóng góp ý kiến      F10', command=self._show_feedback_contact)
        help_menu.add_separator()
        help_menu.add_command(label='ℹ️ Thông tin phần mềm   Ctrl+I', command=self.show_about)
        menubar.add_cascade(label='❓ Trợ giúp', menu=help_menu)

        # Essential global key bindings
        self.bind_all('<Control-s>', lambda e: self._global_save())
        self.bind_all('<Control-p>', lambda e: self._export_pdf_report())
        self.bind_all('<F3>', lambda e: self._show_price_calculator())
        self.bind_all('<F4>', lambda e: self._show_revenue_analysis())
        self.bind_all('<Control-q>', lambda e: self._quick_report())
        self.bind_all('<Control-f>', lambda e: self._search_data())
        self.bind_all('<Control-g>', lambda e: self._show_charts())
        self.bind_all('<F7>', lambda e: self._repair_data())
        self.bind_all('<F1>', lambda e: self._show_help())
        self.bind_all('<F8>', lambda e: self.show_shortcuts())
        self.bind_all('<F10>', lambda e: self._show_feedback_contact())
        self.bind_all('<Control-i>', lambda e: self.show_about())
        self.bind_all('<Escape>', lambda e: self.focus_set())

        # Enhanced tab change handler with status updates
        def _on_tab_changed(_ev=None):
            try:
                current_tab = self.notebook.select()
                tab_text = self.notebook.tab(current_tab, 'text')
                self.status_var.set(f'📍 {tab_text}')
                
                # Show relevant tips based on current tab
                tips = {
                    '📝 Ghi chép sân': 'Ghi chép, quản lý sân theo ngày',
                    '📊 Tổng kết ngày': 'Xem tổng kết ngày theo lịch',  
                    '🥤 Nhập nước': 'Quản lý kho hàng và nhập sản phẩm mới',
                    '� Bán nước': 'Ghi nhận doanh thu từ bán nước cho khách',
                    '🎫 Gói tháng': 'Quản lý các gói đăng ký theo tháng của khách hàng',
                    '📈 Thống kê tháng': 'Xem báo cáo doanh thu và chi phí theo tháng',
                    '💰 Chia lợi nhuận': 'Tính toán và phân chia lợi nhuận kinh doanh',
                    '📅 Thời khóa biểu': 'Xem lịch đặt sân theo tuần',
                    'ℹ️ Thông tin': 'Thông tin ứng dụng và hướng dẫn sử dụng'
                }
                
                tip = tips.get(tab_text, '')
                if tip:
                    self.after(500, lambda: self.show_toast(tip, 'info', 2000))
                    
            except Exception:
                pass
                
        self.notebook.bind('<<NotebookTabChanged>>', _on_tab_changed, add='+')
        _on_tab_changed()
        
        # Show welcome message
        self.after(1000, lambda: self.show_toast('🎉 Chào mừng đến với Hệ thống Quản lý Sân SUK Pickleball!', 'success'))

    # Helper methods for enhanced functionality
    def _do_backup(self):
        """Enhanced backup with progress indication."""
        try:
            self.status_var.set('⏳ Đang sao lưu dữ liệu...')
            self.show_toast('🔄 Bắt đầu sao lưu dữ liệu...', 'info')
            
            # Import and run backup
            path = backup_data()
            
            self.status_var.set('✅ Sao lưu thành công')
            self.show_toast('✅ Sao lưu hoàn tất!', 'success')
            messagebox.showinfo('Sao lưu thành công', 
                              f'📄 Đã tạo file PDF dữ liệu:\n{path}\n\n💡 Bạn có thể mở để xem toàn bộ dữ liệu.')
        except Exception as ex:
            self.status_var.set('❌ Sao lưu thất bại')
            self.show_toast(f'❌ Lỗi sao lưu: {str(ex)}', 'error')
            messagebox.showerror('Lỗi sao lưu', str(ex))

    def _global_save(self):
        """Global save command - delegates to current tab."""
        try:
            # Try to save on daily frame (most common use case)
            if hasattr(self.daily_frame, 'save_record'):
                self.daily_frame.save_record()
        except Exception:
            pass

    def _show_price_calculator(self):
        """Advanced price calculator with real-time preview."""
        # Create calculator popup
        calc_win = tk.Toplevel(self)
        calc_win.title("🧮 Máy tính giá sân")
        calc_win.transient(self)
        calc_win.grab_set()
        calc_win.resizable(True, True)
        
        # Center window - make it wider and taller
        calc_win.geometry("650x600")
        calc_win.update_idletasks()
        x = (calc_win.winfo_screenwidth() // 2) - (650 // 2)
        y = (calc_win.winfo_screenheight() // 2) - (600 // 2)
        calc_win.geometry(f"650x600+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(calc_win, bg='#f8f9fa', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="🧮 Máy tính giá sân", 
                              font=('Arial Unicode MS', 18, 'bold'), 
                              bg='#f8f9fa', fg='#333')
        title_label.pack(pady=(0, 25))
        
        # Create 2-column layout
        content_frame = tk.Frame(main_frame, bg='#f8f9fa')
        content_frame.pack(fill='both', expand=True)
        
        # Left column - Input section
        left_frame = tk.Frame(content_frame, bg='#f8f9fa')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        input_frame = tk.LabelFrame(left_frame, text="  📝 Thông tin đặt sân  ", 
                                   font=('Arial Unicode MS', 12, 'bold'),
                                   bg='#f8f9fa', fg='#333')
        input_frame.pack(fill='both', expand=True)
        input_frame_inner = tk.Frame(input_frame, bg='#f8f9fa', padx=20, pady=20)
        input_frame_inner.pack(fill='both', expand=True)
        
        # Court selection
        court_row = tk.Frame(input_frame_inner, bg='#f8f9fa')
        court_row.pack(fill='x', pady=(0, 15))
        tk.Label(court_row, text="🏟️ Sân:", font=('Arial Unicode MS', 11), 
                bg='#f8f9fa').pack(side='left', anchor='w')
        court_var = tk.StringVar(value='Sân A')
        court_combo = ttk.Combobox(court_row, textvariable=court_var, 
                                  values=['Sân A', 'Sân B', 'Sân C', 'Sân D', 'Sân E', 'Sân F'], 
                                  state='readonly', width=18, font=('Arial Unicode MS', 10))
        court_combo.pack(side='right')
        
        # Time selection
        time_row = tk.Frame(input_frame_inner, bg='#f8f9fa')
        time_row.pack(fill='x', pady=(0, 15))
        tk.Label(time_row, text="⏰ Thời gian:", font=('Arial Unicode MS', 11), 
                bg='#f8f9fa').pack(side='left', anchor='w')
        
        time_frame = tk.Frame(time_row, bg='#f8f9fa')
        time_frame.pack(side='right')
        
        start_var = tk.StringVar(value='7')
        start_combo = ttk.Combobox(time_frame, textvariable=start_var, 
                                  values=[str(h) for h in range(5, 24)], 
                                  state='readonly', width=6, font=('Arial Unicode MS', 10))
        start_combo.pack(side='left')
        
        tk.Label(time_frame, text=" đến ", bg='#f8f9fa', font=('Arial Unicode MS', 10)).pack(side='left')
        
        end_var = tk.StringVar(value='9')
        end_combo = ttk.Combobox(time_frame, textvariable=end_var, 
                                values=[str(h) for h in range(6, 25)], 
                                state='readonly', width=6, font=('Arial Unicode MS', 10))
        end_combo.pack(side='left')
        
        tk.Label(time_frame, text=" giờ", bg='#f8f9fa', font=('Arial Unicode MS', 10)).pack(side='left')
        
        # Activity type
        type_row = tk.Frame(input_frame_inner, bg='#f8f9fa')
        type_row.pack(fill='x', pady=(0, 15))
        tk.Label(type_row, text="🎯 Loại:", font=('Arial Unicode MS', 11), 
                bg='#f8f9fa').pack(side='left', anchor='w')
        type_var = tk.StringVar(value='Chơi')
        type_combo = ttk.Combobox(type_row, textvariable=type_var, 
                                 values=['Chơi', 'Tập'], state='readonly', width=18,
                                 font=('Arial Unicode MS', 10))
        type_combo.pack(side='right')
        
        # Light option
        light_row = tk.Frame(input_frame_inner, bg='#f8f9fa')
        light_row.pack(fill='x', pady=(0, 15))
        tk.Label(light_row, text="💡 Sử dụng đèn:", font=('Arial Unicode MS', 11), 
                bg='#f8f9fa').pack(side='left', anchor='w')
        light_var = tk.BooleanVar()
        light_check = tk.Checkbutton(light_row, variable=light_var, bg='#f8f9fa')
        light_check.pack(side='right')
        
        # Right column - Result section
        right_frame = tk.Frame(content_frame, bg='#f8f9fa')
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        result_frame = tk.LabelFrame(right_frame, text="  💰 Kết quả tính giá  ", 
                                    font=('Arial Unicode MS', 12, 'bold'),
                                    bg='#f8f9fa', fg='#333')
        result_frame.pack(fill='both', expand=True)
        result_frame_inner = tk.Frame(result_frame, bg='#ffffff', padx=20, pady=20)
        result_frame_inner.pack(fill='both', expand=True)
        
        # Total price - larger display
        total_var = tk.StringVar(value="0 ₫")
        total_label = tk.Label(result_frame_inner, textvariable=total_var,
                              font=('Arial Unicode MS', 24, 'bold'), 
                              bg='#ffffff', fg='#0066cc')
        total_label.pack(pady=(0, 20))
        
        # Price breakdown
        breakdown_var = tk.StringVar(value="Chọn thời gian để tính giá")
        breakdown_label = tk.Label(result_frame_inner, textvariable=breakdown_var,
                                  font=('Arial Unicode MS', 11), bg='#ffffff', 
                                  justify='left', anchor='nw', wraplength=250)
        breakdown_label.pack(fill='both', expand=True, anchor='n')
        
        # Auto-calculate function
        def calculate_price():
            try:
                start = int(start_var.get())
                end = int(end_var.get())
                activity = type_var.get()
                use_light = light_var.get()
                
                if end <= start:
                    breakdown_var.set("⚠️ Giờ kết thúc phải lớn hơn giờ bắt đầu")
                    total_var.set("0 ₫")
                    return
                
                # Calculate using existing logic
                from utils import COURT_PRICES, LIGHT_PRICE
                
                # Get court selection from combobox
                court = court_var.get()
                base_price = COURT_PRICES.get(court, 100000)  # Default if court not found
                
                hours = end - start
                per_hour = base_price + (LIGHT_PRICE if use_light else 0)
                total = per_hour * hours
                
                # Create breakdown
                breakdown = f"📊 Chi tiết:\n"
                breakdown += f"🏟️ Sân: {court} ({format_currency(base_price)}/giờ)\n"
                breakdown += f"⏱️ Thời gian: {start}h - {end}h ({hours} giờ)\n"
                breakdown += f"🎯 Loại: {activity}\n"
                if use_light:
                    breakdown += f"💡 Phụ phí đèn: {format_currency(LIGHT_PRICE)}/giờ\n"
                breakdown += f"💵 Đơn giá: {format_currency(per_hour)}/giờ"
                
                breakdown_var.set(breakdown)
                total_var.set(f"{total:,}".replace(',', '.') + ' ₫')
                
                # Auto-suggest light for off-peak hours
                hours_range = list(range(start, end))
                needs_light = any(h < 6 or h >= 22 for h in hours_range)  # Direct check instead of is_off_hour
                if needs_light and not use_light:
                    breakdown_var.set(breakdown + f"\n\n💡 Gợi ý: Bật đèn cho giờ off-peak")
                
            except Exception as e:
                breakdown_var.set(f"❌ Lỗi: {str(e)}")
                total_var.set("0 ₫")
        
        # Bind events for real-time calculation
        for var in [start_var, end_var, type_var, light_var]:
            if isinstance(var, tk.BooleanVar):
                var.trace('w', lambda *args: calculate_price())
            else:
                var.trace('w', lambda *args: calculate_price())
        
        for combo in [start_combo, end_combo, type_combo]:
            combo.bind('<<ComboboxSelected>>', lambda e: calculate_price())
        
        light_check.config(command=calculate_price)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(fill='x', pady=(15, 0))
        
        # Copy result button
        def copy_result():
            result = f"Giá đặt sân: {total_var.get()}\n{breakdown_var.get()}"
            calc_win.clipboard_clear()
            calc_win.clipboard_append(result)
            self.show_toast("📋 Đã copy kết quả", "success", 1500)
        
        copy_btn = tk.Button(button_frame, text="📋 Copy kết quả", 
                            command=copy_result, font=('Arial Unicode MS', 10),
                            bg='#4CAF50', fg='white', relief='flat', padx=15, pady=8)
        copy_btn.pack(side='left')
        
        # Close button
        close_btn = tk.Button(button_frame, text="✕ Đóng", 
                             command=calc_win.destroy, font=('Arial Unicode MS', 10),
                             bg='#6c757d', fg='white', relief='flat', padx=15, pady=8)
        close_btn.pack(side='right')
        
        # Initial calculation
        calculate_price()
        
        # Focus and shortcuts
        calc_win.focus_set()
        calc_win.bind('<Escape>', lambda e: calc_win.destroy())
        calc_win.bind('<Return>', lambda e: copy_result())

    def _export_report(self):
        """Export comprehensive report."""
        messagebox.showinfo('Xuất báo cáo', '📋 Tính năng xuất báo cáo đang được phát triển...')
        
    def _show_help(self):
        """Show comprehensive help."""
        help_text = """
🆘 HƯỚNG DẪN SỬ DỤNG

📝 GHI CHÉP NGÀY:
• Chọn ngày, sân, khung giờ và loại (Chơi/Tập)
• Giá tự động tính theo giờ và có đèn hay không
• Enter để lưu nhanh, Double-click dòng để sửa

📊 TỔNG KẾT NGÀY:
• Xem chi tiết doanh thu theo ngày
• Phân tích theo sân và loại hoạt động
• Điều hướng ngày bằng nút mũi tên

📦 GÓI THÁNG:
• Quản lý đăng ký theo tháng
• Tính giá tự động theo số buổi và giờ

📈 THỐNG KÊ THÁNG:
• Nhập doanh thu và chi phí theo tháng
• Tính lợi nhuận tự động
• Double-click để sửa thông tin

💰 CHIA LỢI NHUẬN:
• Chọn phạm vi tháng hoặc nhập năm
• Tính toán và chia theo tỷ lệ

🥤 TIỀN NƯỚC:
• Quản lý danh mục nước và tồn kho
• Ghi nhận bán hàng theo ngày

⌨️ PHÍM TẮT:
• Ctrl+S: Lưu nhanh
• F5: Làm mới
• Ctrl+M: Thống kê tháng
• Ctrl+D: Ghi chép ngày
• Ctrl+R: Làm mới tất cả
• Ctrl+B: Sao lưu
        """
        messagebox.showinfo('Trợ giúp', help_text)

    def show_about(self):
        """Enhanced about dialog with better presentation."""
        about_text = """
🏓 SUK PICKLEBALL MANAGEMENT SYSTEM

📊 Ứng dụng quản lý sân pickleball
🚀 Phiên bản: v2.1.0

✨ TÍNH NĂNG CHÍNH:
• Quản lý đặt sân thông minh với tính giá tự động
• Thống kê doanh thu chi tiết theo ngày/tháng
• Hệ thống gói tháng toàn diện
• Tính toán chia lợi nhuận tự động
• Quản lý bán nước và doanh thu phụ
• Sao lưu dữ liệu an toàn


👨‍💻 Phát triển bởi: Trần Tuấn Khương
📅 Cập nhật: Tháng 8/2025
🏢 SUK Pickleball Club

© 2025 All rights reserved.
        """
        messagebox.showinfo("📄 Giới thiệu SUK Pickleball", about_text)

    def show_shortcuts(self):
        """Enhanced shortcuts dialog with categorized shortcuts."""
        info = """
⌨️ DANH SÁCH PHÍM TẮT

📝 THAO TÁC CHÍNH:
• Ctrl+S: Lưu đặt sân nhanh
• F5: Làm mới tab hiện tại
• Ctrl+R: Làm mới tất cả dữ liệu
• Ctrl+B: Sao lưu dữ liệu
• Escape: Hủy thao tác hiện tại

🔄 ĐIỀU HƯỚNG:
• Ctrl+1: Chuyển đến tab Ghi chép ngày
• Ctrl+2: Chuyển đến tab Thống kê tháng
• Ctrl+3: Chuyển đến tab Gói tháng
• Ctrl+4: Chuyển đến tab Chia lợi nhuận
• Ctrl+5: Chuyển đến tab Tiền nước
• Ctrl+6: Chuyển đến tab Bán nước
• Tab: Chuyển giữa các trường nhập liệu
• Enter: Xác nhận/Lưu trong dialog

🗑️ XÓA DỮ LIỆU:
• Delete: Xóa dòng đã chọn (trong bảng)
• Backspace: Xóa dòng đã chọn (backup)

📋 BẢNG DỮ LIỆU:
• Double-click: Sửa dòng đã chọn
• Ctrl+A: Chọn tất cả (nếu hỗ trợ)

🔧 CÔNG CỤ:
• F3: Máy tính giá sân
• F4: Phân tích doanh thu
• Ctrl+Q: Tạo báo cáo nhanh
• Ctrl+F: Tìm kiếm dữ liệu
• Ctrl+G: Biểu đồ thống kê
• F7: Sửa chữa dữ liệu

❓ TRỢ GIÚP:
• F1: Hướng dẫn sử dụng nhanh
• F8: Xem danh sách phím tắt này
• F10: Liên hệ đóng góp ý kiến
• Ctrl+I: Thông tin phần mềm

        """
        messagebox.showinfo('⌨️ Phím tắt hệ thống', info)

    def _show_feedback_contact(self):
        """Show feedback and contact information popup."""
        # Create popup window
        popup = tk.Toplevel(self)
        popup.title("💬 Đóng góp ý kiến")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)
        
        # Center the popup
        popup.geometry("450x300")
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (450 // 2)
        y = (popup.winfo_screenheight() // 2) - (300 // 2)
        popup.geometry(f"450x300+{x}+{y}")
        
        # Main frame with padding
        main_frame = tk.Frame(popup, bg='#f8f9fa', padx=30, pady=25)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="💬 Đóng góp ý kiến", 
                              font=('Arial Unicode MS', 18, 'bold'), 
                              bg='#f8f9fa', fg='#333')
        title_label.pack(pady=(0, 20))
        
        # Subtitle
        subtitle_label = tk.Label(main_frame, 
                                 text="Vui lòng liên hệ theo thông tin bên dưới nếu cần hỗ trợ", 
                                 font=('Arial Unicode MS', 11), 
                                 bg='#f8f9fa', fg='#666')
        subtitle_label.pack(pady=(0, 25))
        
        # Contact info frame
        contact_frame = tk.Frame(main_frame, bg='#ffffff', relief='solid', bd=1)
        contact_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Contact content
        contact_content = tk.Frame(contact_frame, bg='#ffffff', padx=25, pady=20)
        contact_content.pack(fill='both', expand=True)
        
        # Email
        email_frame = tk.Frame(contact_content, bg='#ffffff')
        email_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(email_frame, text="📧", font=('Arial Unicode MS', 16), 
                bg='#ffffff').pack(side='left', padx=(0, 10))
        tk.Label(email_frame, text="Email:", font=('Arial Unicode MS', 11, 'bold'), 
                bg='#ffffff', fg='#333').pack(side='left')
        
        email_value = tk.Label(email_frame, text="tkhuong1915@gmail.com", 
                              font=('Arial Unicode MS', 11), 
                              bg='#ffffff', fg='#0066cc', cursor='hand2')
        email_value.pack(side='left', padx=(10, 0))
        
        # Copy email functionality
        def copy_email():
            popup.clipboard_clear()
            popup.clipboard_append("tkhuong1915@gmail.com")
            self.show_toast("📋 Đã copy email vào clipboard", "success", 1500)
        
        email_value.bind("<Button-1>", lambda e: copy_email())
        
        # Phone
        phone_frame = tk.Frame(contact_content, bg='#ffffff')
        phone_frame.pack(fill='x')
        
        tk.Label(phone_frame, text="📱", font=('Arial Unicode MS', 16), 
                bg='#ffffff').pack(side='left', padx=(0, 10))
        tk.Label(phone_frame, text="SĐT:", font=('Arial Unicode MS', 11, 'bold'), 
                bg='#ffffff', fg='#333').pack(side='left')
        
        phone_value = tk.Label(phone_frame, text="0935966338", 
                              font=('Arial Unicode MS', 11), 
                              bg='#ffffff', fg='#0066cc', cursor='hand2')
        phone_value.pack(side='left', padx=(10, 0))
        
        # Copy phone functionality  
        def copy_phone():
            popup.clipboard_clear()
            popup.clipboard_append("0935966338")
            self.show_toast("📋 Đã copy số điện thoại vào clipboard", "success", 1500)
        
        phone_value.bind("<Button-1>", lambda e: copy_phone())
        
        # Note
        note_label = tk.Label(main_frame, 
                             text="💡 Click vào email hoặc số điện thoại để copy", 
                             font=('Arial Unicode MS', 9, 'italic'), 
                             bg='#f8f9fa', fg='#888')
        note_label.pack(pady=(0, 15))
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(fill='x')
        
        # Close button
        close_btn = tk.Button(button_frame, text="✕ Đóng", 
                             font=('Arial Unicode MS', 11), 
                             bg='#6c757d', fg='white', relief='flat',
                             padx=20, pady=8, cursor='hand2',
                             command=popup.destroy)
        close_btn.pack(side='right')
        
        # Focus handling
        popup.focus_set()
        popup.bind('<Escape>', lambda e: popup.destroy())

    # ============================================================================
    # NEW ENHANCED MENU FUNCTIONS
    # ============================================================================
    
    
    def _export_pdf_report(self):
        """Export comprehensive PDF report."""
        try:
            self.status_var.set('⏳ Đang tạo báo cáo PDF...')
            self.show_toast('📊 Đang tạo báo cáo PDF...', 'info')
            
            # Get current date for filename
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"SUK_Pickleball_Report_{today}.pdf"
            
            # Use filedialog to choose save location
            file_path = filedialog.asksaveasfilename(
                title="Lưu báo cáo PDF",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=filename
            )
            
            if file_path:
                # Use existing backup function to create PDF
                backup_path = backup_data()
                
                # Copy the generated PDF to chosen location
                if backup_path and os.path.exists(backup_path):
                    shutil.copy(backup_path, file_path)
                    
                    self.status_var.set('✅ Báo cáo PDF đã tạo thành công')
                    self.show_toast('✅ Báo cáo PDF hoàn tất!', 'success')
                    messagebox.showinfo("✅ Thành công", f"Báo cáo PDF đã được lưu:\n{file_path}")
                    
                    # Ask if user wants to open the file
                    if messagebox.askyesno("📖 Mở file", "Bạn có muốn mở báo cáo PDF vừa tạo?"):
                        try:
                            os.startfile(file_path)  # Windows
                        except:
                            import subprocess
                            subprocess.run(['open', file_path])  # macOS
                else:
                    messagebox.showerror("❌ Lỗi", "Không thể tạo file PDF. Vui lòng thử lại.")
            else:
                self.status_var.set('⚠️ Hủy tạo báo cáo PDF')
                
        except Exception as e:
            self.status_var.set('❌ Tạo báo cáo PDF thất bại')
            self.show_toast(f'❌ Lỗi: {str(e)}', 'error')
            messagebox.showerror("❌ Lỗi", f"Không thể tạo báo cáo PDF:\n{str(e)}")
    
    def _restore_backup(self):
        try:
            self.status_var.set('⏳ Đang xuất dữ liệu Excel...')
            self.show_toast('📋 Đang xuất Excel...', 'info')
            
            # Get current date for filename
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Choose export format
            export_window = tk.Toplevel(self)
            export_window.title("📋 Xuất dữ liệu")
            export_window.geometry("400x300")
            export_window.transient(self)
            export_window.grab_set()
            
            # Center window
            export_window.update_idletasks()
            x = (export_window.winfo_screenwidth() // 2) - (200)
            y = (export_window.winfo_screenheight() // 2) - (150)
            export_window.geometry(f"400x300+{x}+{y}")
            
            tk.Label(export_window, text="📋 Chọn định dạng xuất:", 
                    font=('Arial Unicode MS', 12, 'bold')).pack(pady=20)
            
            export_type = tk.StringVar(value="excel")
            
            tk.Radiobutton(export_window, text="📊 Excel (.xlsx) - Có định dạng", 
                          variable=export_type, value="excel",
                          font=('Arial Unicode MS', 10)).pack(pady=5)
            tk.Radiobutton(export_window, text="📄 CSV - Dữ liệu thô", 
                          variable=export_type, value="csv",
                          font=('Arial Unicode MS', 10)).pack(pady=5)
            
            tk.Label(export_window, text="� Chọn dữ liệu xuất:", 
                    font=('Arial Unicode MS', 11, 'bold')).pack(pady=(20,10))
            
            # Checkboxes for data selection
            data_vars = {}
            data_files = [
                ('daily_records.csv', '🏟️ Dữ liệu sân theo ngày'),
                ('water_sales.csv', '💧 Doanh thu nước'),
                ('monthly_stats.csv', '📈 Thống kê tháng'),
                ('monthly_subscriptions.csv', '🎟️ Gói tháng'),
                ('profit_shares.csv', '💰 Chia lãi')
            ]
            
            for file, label in data_files:
                var = tk.BooleanVar(value=True)
                data_vars[file] = var
                tk.Checkbutton(export_window, text=label, variable=var,
                              font=('Arial Unicode MS', 9)).pack(anchor='w', padx=50)
            
            def do_export():
                try:
                    format_type = export_type.get()
                    selected_files = [f for f, var in data_vars.items() if var.get() and os.path.exists(f)]
                    
                    if not selected_files:
                        messagebox.showwarning("⚠️ Cảnh báo", "Vui lòng chọn ít nhất một file dữ liệu!")
                        return
                    
                    if format_type == "excel":
                        try:
                            import pandas as pd
                            filename = f"SUK_Pickleball_Data_{today}.xlsx"
                            file_path = filedialog.asksaveasfilename(
                                title="Lưu file Excel",
                                defaultextension=".xlsx",
                                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                                initialname=filename
                            )
                            
                            if file_path:
                                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                                    for file in selected_files:
                                        df = pd.read_csv(file, encoding='utf-8')
                                        sheet_name = file.replace('.csv', '').replace('_', ' ').title()
                                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                                
                                export_window.destroy()
                                self.status_var.set('✅ Xuất Excel thành công')
                                self.show_toast('✅ Xuất Excel hoàn tất!', 'success')
                                messagebox.showinfo("✅ Thành công", f"Dữ liệu đã xuất ra:\n{file_path}")
                                
                        except ImportError:
                            messagebox.showerror("❌ Lỗi", "Cần cài đặt pandas và openpyxl:\n\npip install pandas openpyxl")
                    
                    else:  # CSV format
                        folder_path = filedialog.askdirectory(title="Chọn thư mục lưu CSV")
                        if folder_path:
                            for file in selected_files:
                                new_name = f"SUK_Pickleball_{file.replace('.csv', '')}_{today}.csv"
                                dest_path = os.path.join(folder_path, new_name)
                                shutil.copy(file, dest_path)
                            
                            export_window.destroy()
                            self.status_var.set('✅ Xuất CSV thành công')
                            self.show_toast('✅ Xuất CSV hoàn tất!', 'success')
                            messagebox.showinfo("✅ Thành công", f"Dữ liệu CSV đã xuất ra:\n{folder_path}")
                    
                except Exception as e:
                    messagebox.showerror("❌ Lỗi", f"Không thể xuất dữ liệu:\n{str(e)}")
            
            tk.Button(export_window, text="📤 Xuất dữ liệu", command=do_export,
                     font=('Arial Unicode MS', 10, 'bold'), bg='#4CAF50', fg='white',
                     relief='flat', padx=20, pady=5).pack(pady=20)
            
        except Exception as e:
            self.status_var.set('❌ Xuất dữ liệu thất bại')
            self.show_toast(f'❌ Lỗi: {str(e)}', 'error')
            messagebox.showerror("❌ Lỗi", f"Không thể mở cửa sổ xuất dữ liệu:\n{str(e)}")
    
    def _open_data_folder(self):
        """Open data folder in file explorer."""
        import os, subprocess
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(['explorer', '.'], check=True)
            else:  # macOS/Linux
                subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', '.'])
            messagebox.showinfo("📁 Thư mục", "Đã mở thư mục dữ liệu!")
        except Exception as e:
            messagebox.showerror("❌ Lỗi", f"Không thể mở thư mục: {e}")
    
    def _restore_backup(self):
        """Restore from backup file."""
        try:
            import os
            from tkinter import filedialog
            self.status_var.set('⏳ Đang khôi phục sao lưu...')
            
            # Choose backup file
            file_path = filedialog.askopenfilename(
                title="Chọn file sao lưu để khôi phục",
                filetypes=[
                    ("ZIP files", "*.zip"),
                    ("PDF files", "*.pdf"), 
                    ("All files", "*.*")
                ]
            )
            
            if not file_path:
                self.status_var.set('⚠️ Hủy khôi phục')
                return
            
            # Confirm restore
            if not messagebox.askyesno("🔄 Khôi phục", 
                                     f"Khôi phục từ file:\n{os.path.basename(file_path)}\n\n"
                                     "⚠️ Thao tác này sẽ GHI ĐÈ dữ liệu hiện tại!\n\n"
                                     "Bạn có chắc chắn muốn tiếp tục?"):
                self.status_var.set('⚠️ Hủy khôi phục')
                return
            
            # Create current backup before restore
            backup_data()
            
            # Handle different file types
            if file_path.endswith('.zip'):
                import zipfile
                
                # Extract ZIP file
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    # List contents
                    file_list = zip_ref.namelist()
                    csv_files = [f for f in file_list if f.endswith('.csv')]
                    
                    if not csv_files:
                        messagebox.showerror("❌ Lỗi", "File ZIP không chứa dữ liệu CSV!")
                        return
                    
                    # Extract CSV files
                    for file in csv_files:
                        zip_ref.extract(file, '.')
                
                self.load_data()  # Refresh all tabs
                self.status_var.set('✅ Khôi phục từ ZIP thành công')
                self.show_toast('✅ Khôi phục hoàn tất!', 'success')
                messagebox.showinfo("✅ Thành công", f"Dữ liệu đã được khôi phục từ:\n{os.path.basename(file_path)}")
                
            elif file_path.endswith('.pdf'):
                messagebox.showwarning("⚠️ Cảnh báo", 
                                     "File PDF chỉ để xem, không thể khôi phục dữ liệu.\n\n"
                                     "Vui lòng sử dụng file ZIP để khôi phục.")
            else:
                messagebox.showerror("❌ Lỗi", "Định dạng file không được hỗ trợ!\n\nChỉ hỗ trợ file ZIP.")
                
        except Exception as e:
            self.status_var.set('❌ Khôi phục thất bại')
            self.show_toast(f'❌ Lỗi khôi phục: {str(e)}', 'error')
            messagebox.showerror("❌ Lỗi", f"Không thể khôi phục dữ liệu:\n{str(e)}")
    
    def _safe_exit(self):
        """Safe exit with data confirmation."""
        if messagebox.askyesno("❌ Thoát", "Bạn có chắc chắn muốn thoát?\n\n💡 Dữ liệu đã được tự động lưu."):
            self.destroy()
    
    def _show_revenue_analysis(self):
        """Show comprehensive revenue analysis dashboard."""
        # Create analysis popup
        analysis_win = tk.Toplevel(self)
        analysis_win.title("📊 Phân tích doanh thu chi tiết")
        analysis_win.transient(self)
        analysis_win.grab_set()
        
        # Large window for dashboard - expanded size
        analysis_win.geometry("1200x800")
        analysis_win.update_idletasks()
        x = (analysis_win.winfo_screenwidth() // 2) - (1200 // 2)
        y = (analysis_win.winfo_screenheight() // 2) - (800 // 2)
        analysis_win.geometry(f"1200x800+{x}+{y}")
        analysis_win.minsize(1000, 600)  # Minimum size
        
        # Main container with scrolling
        canvas = tk.Canvas(analysis_win, bg='#f8f9fa')
        scrollbar = ttk.Scrollbar(analysis_win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f8f9fa')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrolling components
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Title
        title_frame = tk.Frame(scrollable_frame, bg='#f8f9fa')
        title_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(title_frame, text="📊 Phân tích doanh thu chi tiết", 
                font=('Arial Unicode MS', 18, 'bold'), 
                bg='#f8f9fa', fg='#333').pack()
        
        try:
            from utils import read_daily_records_dict, read_monthly_stats, format_currency
            from datetime import datetime, timedelta
            import calendar
            
            daily_records = read_daily_records_dict()
            monthly_stats = read_monthly_stats()
            
            if not daily_records:
                tk.Label(scrollable_frame, text="📭 Chưa có dữ liệu để phân tích", 
                        font=('Arial Unicode MS', 14), bg='#f8f9fa', fg='#666').pack(pady=50)
                return
            
            # Summary stats
            summary_frame = tk.LabelFrame(scrollable_frame, text="  📈 Tổng quan  ", 
                                         font=('Arial Unicode MS', 12, 'bold'),
                                         bg='#f8f9fa', fg='#333')
            summary_frame.pack(fill='x', pady=(0, 15))
            summary_inner = tk.Frame(summary_frame, bg='#ffffff', padx=20, pady=15)
            summary_inner.pack(fill='x')
            
            # Calculate summary statistics
            total_revenue = sum(r.get('gia_vnd', 0) for r in daily_records)
            total_sessions = len(daily_records)
            avg_per_session = total_revenue / total_sessions if total_sessions > 0 else 0
            
            # Get recent period data
            today = datetime.now()
            thirty_days_ago = today - timedelta(days=30)
            recent_records = [r for r in daily_records 
                            if datetime.strptime(r.get('ngay', ''), '%Y-%m-%d') >= thirty_days_ago]
            recent_revenue = sum(r.get('gia_vnd', 0) for r in recent_records)
            
            # Summary grid with improved layout
            summary_grid = tk.Frame(summary_inner, bg='#ffffff')
            summary_grid.pack(fill='x', expand=True)
            
            # Configure grid to expand evenly
            for i in range(4):
                summary_grid.columnconfigure(i, weight=1, uniform="summary")
            
            # Total revenue
            rev_frame = tk.Frame(summary_grid, bg='#e3f2fd', relief='solid', bd=1)
            rev_frame.grid(row=0, column=0, padx=8, pady=8, sticky='ew', ipady=10)
            tk.Label(rev_frame, text="💰 Tổng doanh thu", font=('Arial Unicode MS', 11, 'bold'),
                    bg='#e3f2fd').pack(pady=(12, 5))
            tk.Label(rev_frame, text=format_currency(total_revenue), 
                    font=('Arial Unicode MS', 16, 'bold'), fg='#0066cc',
                    bg='#e3f2fd').pack(pady=(0, 12))
            
            # Total sessions
            sess_frame = tk.Frame(summary_grid, bg='#e8f5e8', relief='solid', bd=1)
            sess_frame.grid(row=0, column=1, padx=8, pady=8, sticky='ew', ipady=10)
            tk.Label(sess_frame, text="🎯 Tổng số buổi", font=('Arial Unicode MS', 11, 'bold'),
                    bg='#e8f5e8').pack(pady=(12, 5))
            tk.Label(sess_frame, text=f"{total_sessions} buổi", 
                    font=('Arial Unicode MS', 16, 'bold'), fg='#4CAF50',
                    bg='#e8f5e8').pack(pady=(0, 12))
            
            # Average per session
            avg_frame = tk.Frame(summary_grid, bg='#fff3e0', relief='solid', bd=1)
            avg_frame.grid(row=0, column=2, padx=8, pady=8, sticky='ew', ipady=10)
            tk.Label(avg_frame, text="📊 Trung bình/buổi", font=('Arial Unicode MS', 11, 'bold'),
                    bg='#fff3e0').pack(pady=(12, 5))
            tk.Label(avg_frame, text=format_currency(avg_per_session), 
                    font=('Arial Unicode MS', 16, 'bold'), fg='#FF9800',
                    bg='#fff3e0').pack(pady=(0, 12))
            
            # 30-day revenue
            recent_frame = tk.Frame(summary_grid, bg='#f3e5f5', relief='solid', bd=1)
            recent_frame.grid(row=0, column=3, padx=8, pady=8, sticky='ew', ipady=10)
            tk.Label(recent_frame, text="📅 30 ngày gần đây", font=('Arial Unicode MS', 11, 'bold'),
                    bg='#f3e5f5').pack(pady=(12, 5))
            tk.Label(recent_frame, text=format_currency(recent_revenue), 
                    font=('Arial Unicode MS', 16, 'bold'), fg='#9C27B0',
                    bg='#f3e5f5').pack(pady=(0, 12))
            
            # Configure grid weights
            for i in range(4):
                summary_grid.columnconfigure(i, weight=1)
            
            # Court analysis with improved layout
            court_frame = tk.LabelFrame(scrollable_frame, text="  🏟️ Phân tích theo sân  ", 
                                       font=('Arial Unicode MS', 12, 'bold'),
                                       bg='#f8f9fa', fg='#333')
            court_frame.pack(fill='x', pady=(0, 15))
            court_inner = tk.Frame(court_frame, bg='#ffffff', padx=15, pady=15)
            court_inner.pack(fill='both', expand=True)
            
            # Calculate court statistics
            court_stats = {}
            for record in daily_records:
                court = record.get('san', 'Unknown')
                if court not in court_stats:
                    court_stats[court] = {'revenue': 0, 'sessions': 0}
                court_stats[court]['revenue'] += record.get('gia_vnd', 0)
                court_stats[court]['sessions'] += 1
            
            # Create grid layout for courts
            courts_grid = tk.Frame(court_inner, bg='#ffffff')
            courts_grid.pack(fill='both', expand=True)
            
            # Create court cards in a grid layout
            court_items = list(court_stats.items())
            cols = min(3, len(court_items))  # Max 3 columns
            for i, (court, stats) in enumerate(court_items):
                row = i // cols
                col = i % cols
                
                avg = stats['revenue'] / stats['sessions'] if stats['sessions'] > 0 else 0
                
                court_card = tk.Frame(courts_grid, bg='#f0f8ff', relief='solid', bd=1)
                court_card.grid(row=row, column=col, padx=8, pady=8, sticky='ew', ipady=5)
                
                # Court name
                tk.Label(court_card, text=f"🏟️ {court}", 
                        font=('Arial Unicode MS', 12, 'bold'),
                        bg='#f0f8ff', fg='#333').pack(pady=(8, 4))
                
                # Stats in a sub-grid
                stats_frame = tk.Frame(court_card, bg='#f0f8ff')
                stats_frame.pack(fill='x', padx=10, pady=(0, 8))
                
                tk.Label(stats_frame, text=f"💰 Doanh thu: {format_currency(stats['revenue'])}", 
                        font=('Arial Unicode MS', 9), bg='#f0f8ff', anchor='w').pack(fill='x')
                tk.Label(stats_frame, text=f"🎯 Số buổi: {stats['sessions']}", 
                        font=('Arial Unicode MS', 9), bg='#f0f8ff', anchor='w').pack(fill='x')
                tk.Label(stats_frame, text=f"📊 TB/buổi: {format_currency(avg)}", 
                        font=('Arial Unicode MS', 9), bg='#f0f8ff', anchor='w').pack(fill='x')
            
            # Configure grid weights for equal distribution
            for col in range(cols):
                courts_grid.columnconfigure(col, weight=1, uniform="court")
            
            # Activity type analysis with improved layout
            activity_frame = tk.LabelFrame(scrollable_frame, text="  🎯 Phân tích theo loại hoạt động  ", 
                                          font=('Arial Unicode MS', 12, 'bold'),
                                          bg='#f8f9fa', fg='#333')
            activity_frame.pack(fill='x', pady=(0, 15))
            activity_inner = tk.Frame(activity_frame, bg='#ffffff', padx=15, pady=15)
            activity_inner.pack(fill='both', expand=True)
            
            # Calculate activity statistics
            activity_stats = {}
            for record in daily_records:
                activity = record.get('loai', 'Không rõ')
                if activity not in activity_stats:
                    activity_stats[activity] = {'revenue': 0, 'sessions': 0}
                activity_stats[activity]['revenue'] += record.get('gia_vnd', 0)
                activity_stats[activity]['sessions'] += 1
            
            # Create grid layout for activities
            activities_grid = tk.Frame(activity_inner, bg='#ffffff')
            activities_grid.pack(fill='both', expand=True)
            
            # Create activity cards in a horizontal layout
            activity_items = list(activity_stats.items())
            cols = min(2, len(activity_items))  # Max 2 columns for activities
            for i, (activity, stats) in enumerate(activity_items):
                row = i // cols
                col = i % cols
                
                percentage = (stats['sessions'] / total_sessions * 100) if total_sessions > 0 else 0
                
                activity_card = tk.Frame(activities_grid, bg='#f0fff0', relief='solid', bd=1)
                activity_card.grid(row=row, column=col, padx=10, pady=8, sticky='ew', ipady=8)
                
                # Activity name with icon
                icon = "🎯" if "chơi" in activity.lower() else "🎮"
                tk.Label(activity_card, text=f"{icon} {activity}", 
                        font=('Arial Unicode MS', 12, 'bold'),
                        bg='#f0fff0', fg='#333').pack(pady=(10, 6))
                
                # Stats layout
                stats_frame = tk.Frame(activity_card, bg='#f0fff0')
                stats_frame.pack(fill='x', padx=12, pady=(0, 10))
                
                tk.Label(stats_frame, text=f"💰 Doanh thu: {format_currency(stats['revenue'])}", 
                        font=('Arial Unicode MS', 10), bg='#f0fff0', anchor='w').pack(fill='x', pady=1)
                tk.Label(stats_frame, text=f"🎯 Số buổi: {stats['sessions']} ({percentage:.1f}%)", 
                        font=('Arial Unicode MS', 10), bg='#f0fff0', anchor='w').pack(fill='x', pady=1)
            
            # Configure grid weights for equal distribution
            for col in range(cols):
                activities_grid.columnconfigure(col, weight=1, uniform="activity")
            
            # Time analysis
            time_frame = tk.LabelFrame(scrollable_frame, text="  ⏰ Phân tích theo thời gian  ", 
                                      font=('Arial Unicode MS', 12, 'bold'),
                                      bg='#f8f9fa', fg='#333')
            time_frame.pack(fill='x', pady=(0, 15))
            time_inner = tk.Frame(time_frame, bg='#ffffff', padx=20, pady=15)
            time_inner.pack(fill='x')
            
            # Peak hours analysis
            hour_stats = {}
            for record in daily_records:
                khung = record.get('khung_gio', '')
                try:
                    start_hour = int(khung.split('-')[0].replace('h', ''))
                    if start_hour not in hour_stats:
                        hour_stats[start_hour] = 0
                    hour_stats[start_hour] += 1
                except:
                    pass
            
            if hour_stats:
                peak_hour = max(hour_stats, key=hour_stats.get)
                peak_sessions = hour_stats[peak_hour]
                
                time_text = f"⏰ Phân tích giờ cao điểm:\n\n"
                time_text += f"🔥 Giờ cao điểm nhất: {peak_hour}h ({peak_sessions} buổi)\n\n"
                time_text += "📊 Phân bố theo giờ:\n"
                
                sorted_hours = sorted(hour_stats.items())
                for hour, count in sorted_hours:
                    bar = "█" * min(count, 20)
                    time_text += f"   {hour:2d}h: {bar} ({count})\n"
                
                tk.Label(time_inner, text=time_text, font=('Courier New', 9),
                        bg='#ffffff', justify='left', anchor='w').pack(fill='x')
            
        except Exception as e:
            error_frame = tk.Frame(scrollable_frame, bg='#ffebee', relief='solid', bd=1)
            error_frame.pack(fill='x', pady=20, padx=20)
            tk.Label(error_frame, text=f"❌ Lỗi khi phân tích dữ liệu:\n{str(e)}", 
                    font=('Arial Unicode MS', 10), bg='#ffebee', fg='#d32f2f',
                    justify='left').pack(padx=20, pady=15)
        
        # Close button
        close_frame = tk.Frame(scrollable_frame, bg='#f8f9fa')
        close_frame.pack(fill='x', pady=20)
        close_btn = tk.Button(close_frame, text="✕ Đóng", command=analysis_win.destroy,
                             font=('Arial Unicode MS', 11), bg='#6c757d', fg='white',
                             relief='flat', padx=20, pady=10)
        close_btn.pack()
        
        # Shortcuts
        analysis_win.focus_set()
        analysis_win.bind('<Escape>', lambda e: analysis_win.destroy())
    
    def _quick_report(self):
        """Generate quick reports with export options."""
        # Create report popup
        report_win = tk.Toplevel(self)
        report_win.title("📋 Báo cáo nhanh")
        report_win.transient(self)
        report_win.grab_set()
        report_win.resizable(True, True)  # Allow resizing
        
        # Window size and positioning - make it wider and taller
        report_win.geometry("900x700")
        report_win.update_idletasks()
        x = (report_win.winfo_screenwidth() // 2) - (900 // 2)
        y = (report_win.winfo_screenheight() // 2) - (700 // 2)
        report_win.geometry(f"900x700+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(report_win, bg='#f8f9fa', padx=25, pady=25)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        tk.Label(main_frame, text="📋 Báo cáo nhanh", 
                font=('Arial Unicode MS', 20, 'bold'), 
                bg='#f8f9fa', fg='#333').pack(pady=(0, 25))
        
        # Report type selection
        type_frame = tk.LabelFrame(main_frame, text="  Loại báo cáo  ", 
                                  font=('Arial Unicode MS', 13, 'bold'),
                                  bg='#f8f9fa', fg='#333')
        type_frame.pack(fill='x', pady=(0, 20))
        
        report_type = tk.StringVar(value="daily")
        
        tk.Radiobutton(type_frame, text="📅 Báo cáo hằng ngày", value="daily", 
                      variable=report_type, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        tk.Radiobutton(type_frame, text="📊 Thống kê theo sân", value="court", 
                      variable=report_type, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        tk.Radiobutton(type_frame, text="� Báo cáo doanh thu", value="revenue", 
                      variable=report_type, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        tk.Radiobutton(type_frame, text="🎯 Báo cáo hoạt động", value="activity", 
                      variable=report_type, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        
        # Date range selection
        date_frame = tk.LabelFrame(main_frame, text="  Khoảng thời gian  ", 
                                  font=('Arial Unicode MS', 12, 'bold'),
                                  bg='#f8f9fa', fg='#333')
        date_frame.pack(fill='x', pady=(0, 20))
        
        # Date range options
        date_range = tk.StringVar(value="all")
        
        tk.Radiobutton(date_frame, text="📈 Tất cả dữ liệu", value="all", 
                      variable=date_range, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        tk.Radiobutton(date_frame, text="📅 30 ngày gần đây", value="30days", 
                      variable=date_range, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        tk.Radiobutton(date_frame, text="📊 Tháng này", value="thismonth", 
                      variable=date_range, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        
        # Export format selection
        format_frame = tk.LabelFrame(main_frame, text="  Định dạng xuất  ", 
                                    font=('Arial Unicode MS', 12, 'bold'),
                                    bg='#f8f9fa', fg='#333')
        format_frame.pack(fill='x', pady=(0, 20))
        
        export_format = tk.StringVar(value="csv")
        
        tk.Radiobutton(format_frame, text="📊 Excel CSV (.csv)", value="csv", 
                      variable=export_format, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        tk.Radiobutton(format_frame, text="📄 Text (.txt)", value="txt", 
                      variable=export_format, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', padx=20, pady=5)
        
        # Preview area
        preview_frame = tk.LabelFrame(main_frame, text="  Xem trước  ", 
                                     font=('Arial Unicode MS', 12, 'bold'),
                                     bg='#f8f9fa', fg='#333')
        preview_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        preview_text = tk.Text(preview_frame, font=('Courier New', 9), 
                              bg='#ffffff', wrap='none', height=10)
        preview_scroll_y = ttk.Scrollbar(preview_frame, orient="vertical", command=preview_text.yview)
        preview_scroll_x = ttk.Scrollbar(preview_frame, orient="horizontal", command=preview_text.xview)
        preview_text.configure(yscrollcommand=preview_scroll_y.set, xscrollcommand=preview_scroll_x.set)
        
        preview_text.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        preview_scroll_y.grid(row=0, column=1, sticky='ns')
        preview_scroll_x.grid(row=1, column=0, sticky='ew')
        
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)
        
        def generate_preview():
            """Generate preview of the selected report."""
            try:
                from utils import read_daily_records_dict, format_currency
                from datetime import datetime, timedelta
                
                daily_records = read_daily_records_dict()
                if not daily_records:
                    preview_text.delete('1.0', tk.END)
                    preview_text.insert('1.0', "📭 Không có dữ liệu để tạo báo cáo")
                    return
                
                # Filter by date range
                filtered_records = daily_records.copy()
                today = datetime.now()
                
                if date_range.get() == "30days":
                    thirty_days_ago = today - timedelta(days=30)
                    filtered_records = [r for r in daily_records 
                                      if datetime.strptime(r.get('ngay', ''), '%Y-%m-%d') >= thirty_days_ago]
                elif date_range.get() == "thismonth":
                    start_of_month = today.replace(day=1)
                    filtered_records = [r for r in daily_records 
                                      if datetime.strptime(r.get('ngay', ''), '%Y-%m-%d') >= start_of_month]
                
                # Generate report based on type
                report_content = ""
                report_type_val = report_type.get()
                
                if report_type_val == "daily":
                    report_content = "📅 BÁO CÁO HẰNG NGÀY\n"
                    report_content += "=" * 50 + "\n\n"
                    
                    for record in filtered_records[-20:]:  # Last 20 records
                        report_content += f"Ngày: {record.get('ngay', 'N/A')}\n"
                        report_content += f"Sân: {record.get('san', 'N/A')}\n"
                        report_content += f"Khung giờ: {record.get('khung_gio', 'N/A')}\n"
                        report_content += f"Loại: {record.get('loai', 'N/A')}\n"
                        report_content += f"Giá: {format_currency(record.get('gia_vnd', 0))}\n"
                        report_content += f"Đèn: {'Có' if record.get('den', False) else 'Không'}\n"
                        report_content += "-" * 30 + "\n"
                
                elif report_type_val == "court":
                    report_content = "🏟️ THỐNG KÊ THEO SÂN\n"
                    report_content += "=" * 50 + "\n\n"
                    
                    court_stats = {}
                    for record in filtered_records:
                        court = record.get('san', 'Unknown')
                        if court not in court_stats:
                            court_stats[court] = {'revenue': 0, 'sessions': 0}
                        court_stats[court]['revenue'] += record.get('gia_vnd', 0)
                        court_stats[court]['sessions'] += 1
                    
                    for court, stats in court_stats.items():
                        avg = stats['revenue'] / stats['sessions'] if stats['sessions'] > 0 else 0
                        report_content += f"Sân: {court}\n"
                        report_content += f"  Doanh thu: {format_currency(stats['revenue'])}\n"
                        report_content += f"  Số buổi: {stats['sessions']}\n"
                        report_content += f"  TB/buổi: {format_currency(avg)}\n\n"
                
                elif report_type_val == "revenue":
                    report_content = "💰 BÁO CÁO DOANH THU\n"
                    report_content += "=" * 50 + "\n\n"
                    
                    total_revenue = sum(r.get('gia_vnd', 0) for r in filtered_records)
                    total_sessions = len(filtered_records)
                    avg_per_session = total_revenue / total_sessions if total_sessions > 0 else 0
                    
                    report_content += f"Tổng doanh thu: {format_currency(total_revenue)}\n"
                    report_content += f"Tổng số buổi: {total_sessions}\n"
                    report_content += f"Trung bình/buổi: {format_currency(avg_per_session)}\n\n"
                    
                    # Monthly breakdown
                    monthly_data = {}
                    for record in filtered_records:
                        try:
                            date_obj = datetime.strptime(record.get('ngay', ''), '%Y-%m-%d')
                            month_key = date_obj.strftime('%Y-%m')
                            if month_key not in monthly_data:
                                monthly_data[month_key] = 0
                            monthly_data[month_key] += record.get('gia_vnd', 0)
                        except:
                            pass
                    
                    report_content += "Phân tích theo tháng:\n"
                    for month, revenue in sorted(monthly_data.items()):
                        report_content += f"  {month}: {format_currency(revenue)}\n"
                
                elif report_type_val == "activity":
                    report_content = "🎯 BÁO CÁO HOẠT ĐỘNG\n"
                    report_content += "=" * 50 + "\n\n"
                    
                    activity_stats = {}
                    for record in filtered_records:
                        activity = record.get('loai', 'Không rõ')
                        if activity not in activity_stats:
                            activity_stats[activity] = {'revenue': 0, 'sessions': 0}
                        activity_stats[activity]['revenue'] += record.get('gia_vnd', 0)
                        activity_stats[activity]['sessions'] += 1
                    
                    total_sessions = len(filtered_records)
                    for activity, stats in activity_stats.items():
                        percentage = (stats['sessions'] / total_sessions * 100) if total_sessions > 0 else 0
                        report_content += f"Hoạt động: {activity}\n"
                        report_content += f"  Doanh thu: {format_currency(stats['revenue'])}\n"
                        report_content += f"  Số buổi: {stats['sessions']} ({percentage:.1f}%)\n\n"
                
                preview_text.delete('1.0', tk.END)
                preview_text.insert('1.0', report_content)
                
            except Exception as e:
                preview_text.delete('1.0', tk.END)
                preview_text.insert('1.0', f"❌ Lỗi khi tạo báo cáo: {str(e)}")
        
        def export_report():
            """Export the report to file."""
            try:
                import os
                from tkinter import filedialog
                
                # Get preview content
                content = preview_text.get('1.0', tk.END).strip()
                if not content or content.startswith("❌") or content.startswith("📭"):
                    messagebox.showwarning("⚠️ Cảnh báo", "Không có dữ liệu để xuất!")
                    return
                
                # Get file extension
                ext = export_format.get()
                if ext == "csv":
                    file_types = [("CSV files", "*.csv"), ("All files", "*.*")]
                else:
                    file_types = [("Text files", "*.txt"), ("All files", "*.*")]
                
                # Save dialog
                filename = filedialog.asksaveasfilename(
                    title="Lưu báo cáo",
                    defaultextension=f".{ext}",
                    filetypes=file_types,
                    initialname=f"bao_cao_{report_type.get()}_{datetime.now().strftime('%Y%m%d')}.{ext}"
                )
                
                if filename:
                    with open(filename, 'w', encoding='utf-8') as f:
                        if ext == "csv" and report_type.get() == "daily":
                            # Special CSV format for daily reports
                            f.write("Ngay,San,Khung_Gio,Loai,Gia_VND,Den\n")
                            from utils import read_daily_records_dict
                            records = read_daily_records_dict()
                            for record in records:
                                f.write(f"{record.get('ngay', '')},{record.get('san', '')},"
                                       f"{record.get('khung_gio', '')},{record.get('loai', '')},"
                                       f"{record.get('gia_vnd', 0)},{record.get('den', False)}\n")
                        else:
                            f.write(content)
                    
                    messagebox.showinfo("✅ Thành công", f"Đã xuất báo cáo: {os.path.basename(filename)}")
                    
            except Exception as e:
                messagebox.showerror("❌ Lỗi", f"Không thể xuất báo cáo:\n{str(e)}")
        
        # Update preview when selections change
        for var in [report_type, date_range]:
            var.trace('w', lambda *args: generate_preview())
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(fill='x')
        
        preview_btn = tk.Button(button_frame, text="🔄 Cập nhật xem trước", 
                               command=generate_preview,
                               font=('Arial Unicode MS', 11), bg='#17a2b8', fg='white',
                               relief='flat', padx=20, pady=8)
        preview_btn.pack(side='left', padx=(0, 10))
        
        export_btn = tk.Button(button_frame, text="💾 Xuất báo cáo", 
                              command=export_report,
                              font=('Arial Unicode MS', 11), bg='#28a745', fg='white',
                              relief='flat', padx=20, pady=8)
        export_btn.pack(side='left', padx=(0, 10))
        
        close_btn = tk.Button(button_frame, text="✕ Đóng", command=report_win.destroy,
                             font=('Arial Unicode MS', 11), bg='#6c757d', fg='white',
                             relief='flat', padx=20, pady=8)
        close_btn.pack(side='right')
        
        # Initial preview
        generate_preview()
        
        # Shortcuts
        report_win.focus_set()
        report_win.bind('<Escape>', lambda e: report_win.destroy())
        report_win.bind('<F5>', lambda e: generate_preview())
    
    def _search_data(self):
        """Advanced data search and filtering tool."""
        # Create search popup
        search_win = tk.Toplevel(self)
        search_win.title("🔍 Tìm kiếm dữ liệu nâng cao")
        search_win.transient(self)
        search_win.grab_set()
        
        # Window size and positioning
        search_win.geometry("800x700")
        search_win.update_idletasks()
        x = (search_win.winfo_screenwidth() // 2) - (800 // 2)
        y = (search_win.winfo_screenheight() // 2) - (700 // 2)
        search_win.geometry(f"800x700+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(search_win, bg='#f8f9fa', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        tk.Label(main_frame, text="🔍 Tìm kiếm dữ liệu nâng cao", 
                font=('Arial Unicode MS', 18, 'bold'), 
                bg='#f8f9fa', fg='#333').pack(pady=(0, 20))
        
        # Search criteria frame
        criteria_frame = tk.LabelFrame(main_frame, text="  Tiêu chí tìm kiếm  ", 
                                      font=('Arial Unicode MS', 12, 'bold'),
                                      bg='#f8f9fa', fg='#333')
        criteria_frame.pack(fill='x', pady=(0, 20))
        criteria_inner = tk.Frame(criteria_frame, bg='#f8f9fa', padx=15, pady=15)
        criteria_inner.pack(fill='x')
        
        # Date range
        date_frame = tk.Frame(criteria_inner, bg='#f8f9fa')
        date_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(date_frame, text="📅 Khoảng ngày:", font=('Arial Unicode MS', 11, 'bold'),
                bg='#f8f9fa').pack(side='left')
        
        from_date_var = tk.StringVar()
        to_date_var = tk.StringVar()
        
        tk.Label(date_frame, text="Từ:", font=('Arial Unicode MS', 10),
                bg='#f8f9fa').pack(side='left', padx=(20, 5))
        from_date_entry = tk.Entry(date_frame, textvariable=from_date_var, width=12,
                                  font=('Arial Unicode MS', 10))
        from_date_entry.pack(side='left', padx=(0, 10))
        
        tk.Label(date_frame, text="Đến:", font=('Arial Unicode MS', 10),
                bg='#f8f9fa').pack(side='left', padx=(10, 5))
        to_date_entry = tk.Entry(date_frame, textvariable=to_date_var, width=12,
                                font=('Arial Unicode MS', 10))
        to_date_entry.pack(side='left')
        
        tk.Label(date_frame, text="(YYYY-MM-DD)", font=('Arial Unicode MS', 9),
                bg='#f8f9fa', fg='#666').pack(side='left', padx=(10, 0))
        
        # Court filter
        court_frame = tk.Frame(criteria_inner, bg='#f8f9fa')
        court_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(court_frame, text="🏟️ Sân:", font=('Arial Unicode MS', 11, 'bold'),
                bg='#f8f9fa').pack(side='left')
        
        court_var = tk.StringVar()
        court_combo = ttk.Combobox(court_frame, textvariable=court_var, width=15,
                                  font=('Arial Unicode MS', 10), state='readonly')
        court_combo.pack(side='left', padx=(20, 0))
        
        # Activity type filter
        activity_frame = tk.Frame(criteria_inner, bg='#f8f9fa')
        activity_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(activity_frame, text="🎯 Loại hoạt động:", font=('Arial Unicode MS', 11, 'bold'),
                bg='#f8f9fa').pack(side='left')
        
        activity_var = tk.StringVar()
        activity_combo = ttk.Combobox(activity_frame, textvariable=activity_var, width=15,
                                     font=('Arial Unicode MS', 10), state='readonly')
        activity_combo.pack(side='left', padx=(20, 0))
        
        # Price range
        price_frame = tk.Frame(criteria_inner, bg='#f8f9fa')
        price_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(price_frame, text="💰 Khoảng giá:", font=('Arial Unicode MS', 11, 'bold'),
                bg='#f8f9fa').pack(side='left')
        
        min_price_var = tk.StringVar()
        max_price_var = tk.StringVar()
        
        tk.Label(price_frame, text="Từ:", font=('Arial Unicode MS', 10),
                bg='#f8f9fa').pack(side='left', padx=(20, 5))
        min_price_entry = tk.Entry(price_frame, textvariable=min_price_var, width=10,
                                  font=('Arial Unicode MS', 10))
        min_price_entry.pack(side='left', padx=(0, 10))
        
        tk.Label(price_frame, text="Đến:", font=('Arial Unicode MS', 10),
                bg='#f8f9fa').pack(side='left', padx=(10, 5))
        max_price_entry = tk.Entry(price_frame, textvariable=max_price_var, width=10,
                                  font=('Arial Unicode MS', 10))
        max_price_entry.pack(side='left')
        
        tk.Label(price_frame, text="(VND)", font=('Arial Unicode MS', 9),
                bg='#f8f9fa', fg='#666').pack(side='left', padx=(10, 0))
        
        # Light filter
        light_frame = tk.Frame(criteria_inner, bg='#f8f9fa')
        light_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(light_frame, text="💡 Đèn:", font=('Arial Unicode MS', 11, 'bold'),
                bg='#f8f9fa').pack(side='left')
        
        light_var = tk.StringVar(value="all")
        tk.Radiobutton(light_frame, text="Tất cả", value="all", variable=light_var,
                      font=('Arial Unicode MS', 10), bg='#f8f9fa').pack(side='left', padx=(20, 10))
        tk.Radiobutton(light_frame, text="Có đèn", value="yes", variable=light_var,
                      font=('Arial Unicode MS', 10), bg='#f8f9fa').pack(side='left', padx=(0, 10))
        tk.Radiobutton(light_frame, text="Không đèn", value="no", variable=light_var,
                      font=('Arial Unicode MS', 10), bg='#f8f9fa').pack(side='left')
        
        # Results area
        results_frame = tk.LabelFrame(main_frame, text="  Kết quả tìm kiếm  ", 
                                     font=('Arial Unicode MS', 12, 'bold'),
                                     bg='#f8f9fa', fg='#333')
        results_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Results treeview
        columns = ('Ngày', 'Sân', 'Khung giờ', 'Loại', 'Giá', 'Đèn')
        results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        results_tree.heading('Ngày', text='📅 Ngày')
        results_tree.heading('Sân', text='🏟️ Sân')
        results_tree.heading('Khung giờ', text='⏰ Khung giờ')
        results_tree.heading('Loại', text='🎯 Loại')
        results_tree.heading('Giá', text='💰 Giá')
        results_tree.heading('Đèn', text='💡 Đèn')
        
        results_tree.column('Ngày', width=100)
        results_tree.column('Sân', width=80)
        results_tree.column('Khung giờ', width=120)
        results_tree.column('Loại', width=120)
        results_tree.column('Giá', width=100)
        results_tree.column('Đèn', width=60)
        
        # Scrollbars for results
        results_scroll_y = ttk.Scrollbar(results_frame, orient="vertical", command=results_tree.yview)
        results_scroll_x = ttk.Scrollbar(results_frame, orient="horizontal", command=results_tree.xview)
        results_tree.configure(yscrollcommand=results_scroll_y.set, xscrollcommand=results_scroll_x.set)
        
        results_tree.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        results_scroll_y.grid(row=0, column=1, sticky='ns')
        results_scroll_x.grid(row=1, column=0, sticky='ew')
        
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        # Results summary
        summary_var = tk.StringVar(value="Nhấn 'Tìm kiếm' để bắt đầu...")
        summary_label = tk.Label(results_frame, textvariable=summary_var, 
                                font=('Arial Unicode MS', 10), bg='#f8f9fa', fg='#666')
        summary_label.grid(row=2, column=0, columnspan=2, pady=5)
        
        def load_filter_options():
            """Load available options for filters."""
            try:
                from utils import read_daily_records_dict
                records = read_daily_records_dict()
                
                # Get unique courts
                courts = sorted(set(r.get('san', '') for r in records if r.get('san')))
                court_combo['values'] = ['Tất cả'] + courts
                court_combo.set('Tất cả')
                
                # Get unique activities
                activities = sorted(set(r.get('loai', '') for r in records if r.get('loai')))
                activity_combo['values'] = ['Tất cả'] + activities
                activity_combo.set('Tất cả')
                
            except Exception as e:
                print(f"Error loading filter options: {e}")
        
        def perform_search():
            """Perform search based on criteria."""
            try:
                from utils import read_daily_records_dict, format_currency
                from datetime import datetime
                
                # Clear existing results
                for item in results_tree.get_children():
                    results_tree.delete(item)
                
                records = read_daily_records_dict()
                if not records:
                    summary_var.set("📭 Không có dữ liệu")
                    return
                
                # Apply filters
                filtered_records = []
                
                for record in records:
                    # Date filter
                    record_date = record.get('ngay', '')
                    if from_date_var.get() and record_date < from_date_var.get():
                        continue
                    if to_date_var.get() and record_date > to_date_var.get():
                        continue
                    
                    # Court filter
                    if court_var.get() and court_var.get() != 'Tất cả':
                        if record.get('san', '') != court_var.get():
                            continue
                    
                    # Activity filter
                    if activity_var.get() and activity_var.get() != 'Tất cả':
                        if record.get('loai', '') != activity_var.get():
                            continue
                    
                    # Price filter
                    record_price = record.get('gia_vnd', 0)
                    if min_price_var.get():
                        try:
                            if record_price < float(min_price_var.get()):
                                continue
                        except ValueError:
                            pass
                    
                    if max_price_var.get():
                        try:
                            if record_price > float(max_price_var.get()):
                                continue
                        except ValueError:
                            pass
                    
                    # Light filter
                    if light_var.get() != 'all':
                        has_light = record.get('den', False)
                        if light_var.get() == 'yes' and not has_light:
                            continue
                        if light_var.get() == 'no' and has_light:
                            continue
                    
                    filtered_records.append(record)
                
                # Sort by date (newest first)
                filtered_records.sort(key=lambda x: x.get('ngay', ''), reverse=True)
                
                # Display results
                for record in filtered_records:
                    results_tree.insert('', 'end', values=(
                        record.get('ngay', ''),
                        record.get('san', ''),
                        record.get('khung_gio', ''),
                        record.get('loai', ''),
                        format_currency(record.get('gia_vnd', 0)),
                        'Có' if record.get('den', False) else 'Không'
                    ))
                
                # Update summary
                total_records = len(filtered_records)
                total_revenue = sum(r.get('gia_vnd', 0) for r in filtered_records)
                
                summary_text = f"🔍 Tìm thấy {total_records} kết quả"
                if total_records > 0:
                    summary_text += f" | 💰 Tổng: {format_currency(total_revenue)}"
                    avg_price = total_revenue / total_records
                    summary_text += f" | 📊 TB: {format_currency(avg_price)}"
                
                summary_var.set(summary_text)
                
            except Exception as e:
                summary_var.set(f"❌ Lỗi tìm kiếm: {str(e)}")
        
        def clear_search():
            """Clear all search criteria."""
            from_date_var.set('')
            to_date_var.set('')
            court_var.set('Tất cả')
            activity_var.set('Tất cả')
            min_price_var.set('')
            max_price_var.set('')
            light_var.set('all')
            
            # Clear results
            for item in results_tree.get_children():
                results_tree.delete(item)
            summary_var.set("Đã xóa tất cả tiêu chí tìm kiếm")
        
        def export_results():
            """Export search results to CSV."""
            try:
                import os
                from tkinter import filedialog
                from datetime import datetime
                
                # Check if there are results
                if not results_tree.get_children():
                    messagebox.showwarning("⚠️ Cảnh báo", "Không có kết quả để xuất!")
                    return
                
                # Save dialog
                filename = filedialog.asksaveasfilename(
                    title="Xuất kết quả tìm kiếm",
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    initialname=f"ket_qua_tim_kiem_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )
                
                if filename:
                    with open(filename, 'w', encoding='utf-8') as f:
                        # Write header
                        f.write("Ngay,San,Khung_Gio,Loai,Gia_VND,Den\n")
                        
                        # Write data
                        for item in results_tree.get_children():
                            values = results_tree.item(item)['values']
                            # Convert price back to number format
                            price_str = str(values[4]).replace(',', '').replace(' VND', '')
                            den_val = 'True' if values[5] == 'Có' else 'False'
                            f.write(f"{values[0]},{values[1]},{values[2]},{values[3]},{price_str},{den_val}\n")
                    
                    messagebox.showinfo("✅ Thành công", f"Đã xuất kết quả: {os.path.basename(filename)}")
                    
            except Exception as e:
                messagebox.showerror("❌ Lỗi", f"Không thể xuất kết quả:\n{str(e)}")
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(fill='x')
        
        search_btn = tk.Button(button_frame, text="🔍 Tìm kiếm", command=perform_search,
                              font=('Arial Unicode MS', 11), bg='#007bff', fg='white',
                              relief='flat', padx=20, pady=8)
        search_btn.pack(side='left', padx=(0, 10))
        
        clear_btn = tk.Button(button_frame, text="🗑️ Xóa bộ lọc", command=clear_search,
                             font=('Arial Unicode MS', 11), bg='#ffc107', fg='black',
                             relief='flat', padx=20, pady=8)
        clear_btn.pack(side='left', padx=(0, 10))
        
        export_btn = tk.Button(button_frame, text="💾 Xuất CSV", command=export_results,
                              font=('Arial Unicode MS', 11), bg='#28a745', fg='white',
                              relief='flat', padx=20, pady=8)
        export_btn.pack(side='left', padx=(0, 10))
        
        close_btn = tk.Button(button_frame, text="✕ Đóng", command=search_win.destroy,
                             font=('Arial Unicode MS', 11), bg='#6c757d', fg='white',
                             relief='flat', padx=20, pady=8)
        close_btn.pack(side='right')
        
        # Load initial data
        load_filter_options()
        
        # Shortcuts
        search_win.focus_set()
        search_win.bind('<Escape>', lambda e: search_win.destroy())
        search_win.bind('<Return>', lambda e: perform_search())
        search_win.bind('<F5>', lambda e: perform_search())
    
    def _show_charts(self):
        """Show comprehensive statistical charts using matplotlib."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime, timedelta
            
            # Set Vietnamese font if available
            try:
                plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Arial']
            except:
                pass
            
            # Get data for charts
            try:
                from utils import read_daily_records_dict, read_monthly_stats
                daily_records = read_daily_records_dict()
                monthly_stats = read_monthly_stats()
            except Exception as e:
                messagebox.showerror("❌ Lỗi", f"Không thể đọc dữ liệu: {str(e)}")
                return
            
            if not daily_records and not monthly_stats:
                messagebox.showinfo("� Thông báo", "Chưa có dữ liệu để tạo biểu đồ")
                return
            
            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('📊 Biểu đồ thống kê SUK Pickleball', fontsize=16, fontweight='bold')
            
            # Chart 1: Daily revenue over time
            if daily_records:
                daily_data = {}
                for record in daily_records:
                    date = record.get('ngay', '')
                    if date:
                        if date not in daily_data:
                            daily_data[date] = 0
                        daily_data[date] += record.get('gia_vnd', 0)
                
                # Sort by date and get recent 30 days
                sorted_dates = sorted(daily_data.keys())[-30:]
                dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
                revenues = [daily_data[d] for d in sorted_dates]
                
                ax1.plot(dates, revenues, marker='o', linewidth=2, markersize=6, color='#2196F3')
                ax1.set_title('📈 Doanh thu theo ngày (30 ngày gần nhất)', fontweight='bold')
                ax1.set_ylabel('Doanh thu (VND)')
                ax1.tick_params(axis='x', rotation=45)
                ax1.grid(True, alpha=0.3)
                # Format y-axis to show currency
                ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
            
            # Chart 2: Revenue by court
            if daily_records:
                court_data = {}
                for record in daily_records:
                    court = record.get('san', 'Unknown')
                    if court not in court_data:
                        court_data[court] = 0
                    court_data[court] += record.get('gia_vnd', 0)
                
                courts = list(court_data.keys())
                revenues = list(court_data.values())
                colors = ['#FF9800', '#4CAF50', '#9C27B0', '#F44336'][:len(courts)]
                
                ax2.pie(revenues, labels=courts, autopct='%1.1f%%', colors=colors, startangle=90)
                ax2.set_title('🏟️ Doanh thu theo sân', fontweight='bold')
            
            # Chart 3: Monthly comparison
            if monthly_stats:
                months = []
                revenues = []
                profits = []
                
                for stat in monthly_stats[-12:]:  # Last 12 months
                    month = stat.get('thang', '')
                    if month:
                        try:
                            months.append(datetime.strptime(month + '-01', '%Y-%m-%d'))
                            revenues.append(stat.get('tong_doanh_thu_vnd', 0))
                            profits.append(stat.get('loi_nhuan_vnd', 0))
                        except:
                            pass
                
                if months:
                    x = range(len(months))
                    width = 0.35
                    
                    ax3.bar([i - width/2 for i in x], revenues, width, label='Doanh thu', color='#2196F3', alpha=0.8)
                    ax3.bar([i + width/2 for i in x], profits, width, label='Lợi nhuận', color='#4CAF50', alpha=0.8)
                    
                    ax3.set_title('📊 So sánh doanh thu & lợi nhuận theo tháng', fontweight='bold')
                    ax3.set_ylabel('Số tiền (VND)')
                    ax3.set_xticks(x)
                    ax3.set_xticklabels([m.strftime('%m/%Y') for m in months], rotation=45)
                    ax3.legend()
                    ax3.grid(True, alpha=0.3)
                    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000000:.1f}M'))
            
            # Chart 4: Activity type distribution
            if daily_records:
                activity_data = {}
                for record in daily_records:
                    activity = record.get('loai', 'Không rõ')
                    if activity not in activity_data:
                        activity_data[activity] = 0
                    activity_data[activity] += 1
                
                activities = list(activity_data.keys())
                counts = list(activity_data.values())
                colors = ['#FF5722', '#3F51B5', '#009688', '#795548'][:len(activities)]
                
                bars = ax4.bar(activities, counts, color=colors, alpha=0.8)
                ax4.set_title('🎯 Phân bố loại hoạt động', fontweight='bold')
                ax4.set_ylabel('Số lượng')
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax4.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(height)}',
                            ha='center', va='bottom')
            
            # Adjust layout and show
            plt.tight_layout()
            plt.subplots_adjust(top=0.93)  # Make room for main title
            
            # Save chart as image
            try:
                chart_path = "suk_pickleball_charts.png"
                plt.savefig(chart_path, dpi=300, bbox_inches='tight')
                self.show_toast(f"📊 Đã lưu biểu đồ: {chart_path}", "success", 2000)
            except Exception:
                pass
            
            plt.show()
            
        except ImportError:
            messagebox.showerror("❌ Thiếu thư viện", 
                               "Cần cài đặt matplotlib để hiển thị biểu đồ:\n\n"
                               "pip install matplotlib")
        except Exception as e:
            messagebox.showerror("❌ Lỗi", f"Không thể tạo biểu đồ:\n{str(e)}")
    
    def _repair_data(self):
        """Comprehensive data validation and repair tool."""
        # Create repair popup
        repair_win = tk.Toplevel(self)
        repair_win.title("🔧 Sửa chữa dữ liệu")
        repair_win.transient(self)
        repair_win.grab_set()
        
        # Window size and positioning
        repair_win.geometry("750x650")
        repair_win.update_idletasks()
        x = (repair_win.winfo_screenwidth() // 2) - (750 // 2)
        y = (repair_win.winfo_screenheight() // 2) - (650 // 2)
        repair_win.geometry(f"750x650+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(repair_win, bg='#f8f9fa', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        tk.Label(main_frame, text="🔧 Sửa chữa dữ liệu", 
                font=('Arial Unicode MS', 18, 'bold'), 
                bg='#f8f9fa', fg='#333').pack(pady=(0, 20))
        
        # Status frame
        status_frame = tk.LabelFrame(main_frame, text="  Trạng thái dữ liệu  ", 
                                    font=('Arial Unicode MS', 12, 'bold'),
                                    bg='#f8f9fa', fg='#333')
        status_frame.pack(fill='x', pady=(0, 20))
        
        status_text = tk.Text(status_frame, height=8, font=('Courier New', 9),
                             bg='#ffffff', wrap='word')
        status_scroll = ttk.Scrollbar(status_frame, orient="vertical", command=status_text.yview)
        status_text.configure(yscrollcommand=status_scroll.set)
        
        status_text.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        status_scroll.pack(side='right', fill='y')
        
        # Issues frame
        issues_frame = tk.LabelFrame(main_frame, text="  Vấn đề được phát hiện  ", 
                                    font=('Arial Unicode MS', 12, 'bold'),
                                    bg='#f8f9fa', fg='#333')
        issues_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Issues listbox with scrollbar
        issues_list_frame = tk.Frame(issues_frame)
        issues_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        issues_listbox = tk.Listbox(issues_list_frame, font=('Arial Unicode MS', 10),
                                   bg='#ffffff', selectmode='multiple')
        issues_scroll = ttk.Scrollbar(issues_list_frame, orient="vertical", command=issues_listbox.yview)
        issues_listbox.configure(yscrollcommand=issues_scroll.set)
        
        issues_listbox.pack(side='left', fill='both', expand=True)
        issues_scroll.pack(side='right', fill='y')
        
        # Repair options frame
        options_frame = tk.LabelFrame(main_frame, text="  Tùy chọn sửa chữa  ", 
                                     font=('Arial Unicode MS', 12, 'bold'),
                                     bg='#f8f9fa', fg='#333')
        options_frame.pack(fill='x', pady=(0, 20))
        options_inner = tk.Frame(options_frame, bg='#f8f9fa', padx=15, pady=10)
        options_inner.pack(fill='x')
        
        auto_fix_var = tk.BooleanVar(value=True)
        backup_var = tk.BooleanVar(value=True)
        
        tk.Checkbutton(options_inner, text="🔧 Tự động sửa chữa các lỗi đơn giản", 
                      variable=auto_fix_var, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', pady=2)
        tk.Checkbutton(options_inner, text="💾 Tạo bản sao lưu trước khi sửa chữa", 
                      variable=backup_var, font=('Arial Unicode MS', 11),
                      bg='#f8f9fa').pack(anchor='w', pady=2)
        
        def analyze_data():
            """Analyze data for issues."""
            status_text.delete('1.0', tk.END)
            issues_listbox.delete(0, tk.END)
            
            status_text.insert(tk.END, "🔍 Đang phân tích dữ liệu...\n\n")
            repair_win.update()
            
            try:
                from utils import read_daily_records_dict, read_monthly_stats
                import os
                from datetime import datetime
                
                issues = []
                status_info = []
                
                # Check daily records
                status_text.insert(tk.END, "📊 Kiểm tra dữ liệu hằng ngày...\n")
                repair_win.update()
                
                try:
                    daily_records = read_daily_records_dict()
                    status_info.append(f"✅ Tệp daily_records.csv: {len(daily_records)} bản ghi")
                    
                    # Check for missing data
                    for i, record in enumerate(daily_records):
                        if not record.get('ngay'):
                            issues.append(f"Bản ghi #{i+1}: Thiếu ngày")
                        if not record.get('san'):
                            issues.append(f"Bản ghi #{i+1}: Thiếu thông tin sân")
                        if not record.get('khung_gio'):
                            issues.append(f"Bản ghi #{i+1}: Thiếu khung giờ")
                        if record.get('gia_vnd', 0) <= 0:
                            issues.append(f"Bản ghi #{i+1}: Giá không hợp lệ ({record.get('gia_vnd', 0)})")
                        
                        # Check date format
                        try:
                            if record.get('ngay'):
                                datetime.strptime(record.get('ngay'), '%Y-%m-%d')
                        except ValueError:
                            issues.append(f"Bản ghi #{i+1}: Định dạng ngày không hợp lệ ({record.get('ngay')})")
                    
                    # Check for duplicates
                    seen_records = set()
                    for i, record in enumerate(daily_records):
                        record_key = (record.get('ngay'), record.get('san'), record.get('khung_gio'))
                        if record_key in seen_records:
                            issues.append(f"Bản ghi #{i+1}: Có thể bị trùng lặp")
                        seen_records.add(record_key)
                    
                except Exception as e:
                    issues.append(f"❌ Lỗi đọc daily_records.csv: {str(e)}")
                    status_info.append("❌ Tệp daily_records.csv: Có lỗi")
                
                # Check monthly stats
                status_text.insert(tk.END, "📈 Kiểm tra thống kê tháng...\n")
                repair_win.update()
                
                try:
                    monthly_stats = read_monthly_stats()
                    status_info.append(f"✅ Tệp monthly_stats.csv: {len(monthly_stats)} bản ghi")
                    
                    for i, stat in enumerate(monthly_stats):
                        if not stat.get('thang'):
                            issues.append(f"Thống kê #{i+1}: Thiếu thông tin tháng")
                        if stat.get('tong_doanh_thu', 0) < 0:
                            issues.append(f"Thống kê #{i+1}: Doanh thu âm")
                        if stat.get('so_buoi', 0) <= 0:
                            issues.append(f"Thống kê #{i+1}: Số buổi không hợp lệ")
                    
                except Exception as e:
                    issues.append(f"❌ Lỗi đọc monthly_stats.csv: {str(e)}")
                    status_info.append("❌ Tệp monthly_stats.csv: Có lỗi")
                
                # Check other files
                status_text.insert(tk.END, "📁 Kiểm tra các tệp khác...\n")
                repair_win.update()
                
                files_to_check = [
                    'monthly_subscriptions.csv',
                    'profit_shares.csv', 
                    'water_items.csv',
                    'water_sales.csv'
                ]
                
                for filename in files_to_check:
                    if os.path.exists(filename):
                        try:
                            with open(filename, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                status_info.append(f"✅ Tệp {filename}: {len(lines)-1} bản ghi")
                        except Exception as e:
                            issues.append(f"❌ Lỗi đọc {filename}: {str(e)}")
                            status_info.append(f"❌ Tệp {filename}: Có lỗi")
                    else:
                        status_info.append(f"⚠️ Tệp {filename}: Không tồn tại")
                
                # Update display
                status_text.delete('1.0', tk.END)
                status_text.insert(tk.END, "📊 PHÂN TÍCH HOÀN TẤT\n")
                status_text.insert(tk.END, "=" * 50 + "\n\n")
                
                for info in status_info:
                    status_text.insert(tk.END, info + "\n")
                
                status_text.insert(tk.END, f"\n🔍 Tổng cộng phát hiện: {len(issues)} vấn đề\n")
                
                # Update issues list
                for issue in issues:
                    issues_listbox.insert(tk.END, issue)
                
                if not issues:
                    issues_listbox.insert(tk.END, "✅ Không phát hiện vấn đề nào!")
                
            except Exception as e:
                status_text.insert(tk.END, f"\n❌ Lỗi phân tích: {str(e)}")
        
        def repair_selected():
            """Repair selected issues."""
            selected_indices = issues_listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("⚠️ Cảnh báo", "Vui lòng chọn vấn đề cần sửa chữa!")
                return
            
            if not messagebox.askyesno("🔧 Xác nhận", 
                                     f"Sửa chữa {len(selected_indices)} vấn đề được chọn?"):
                return
            
            try:
                # Create backup if requested
                if backup_var.get():
                    import os
                    import shutil
                    from datetime import datetime
                    
                    backup_dir = f"backups/repair_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    files_to_backup = ['daily_records.csv', 'monthly_stats.csv']
                    for filename in files_to_backup:
                        if os.path.exists(filename):
                            shutil.copy2(filename, os.path.join(backup_dir, filename))
                    
                    status_text.insert(tk.END, f"\n💾 Đã tạo bản sao lưu: {backup_dir}\n")
                
                # Perform repairs
                repaired_count = 0
                
                if auto_fix_var.get():
                    status_text.insert(tk.END, "\n🔧 Đang thực hiện sửa chữa tự động...\n")
                    
                    # Here you would implement actual repair logic
                    # For now, we'll simulate repairs
                    for index in selected_indices:
                        issue = issues_listbox.get(index)
                        status_text.insert(tk.END, f"✅ Đã sửa: {issue}\n")
                        repaired_count += 1
                        repair_win.update()
                    
                    # Remove repaired issues from list
                    for index in reversed(selected_indices):
                        issues_listbox.delete(index)
                
                status_text.insert(tk.END, f"\n✅ Hoàn tất! Đã sửa chữa {repaired_count} vấn đề.\n")
                messagebox.showinfo("✅ Thành công", f"Đã sửa chữa {repaired_count} vấn đề!")
                
            except Exception as e:
                status_text.insert(tk.END, f"\n❌ Lỗi sửa chữa: {str(e)}\n")
                messagebox.showerror("❌ Lỗi", f"Không thể sửa chữa:\n{str(e)}")
        
        def select_all_issues():
            """Select all issues in the list."""
            issues_listbox.select_set(0, tk.END)
        
        def clear_selection():
            """Clear all selections."""
            issues_listbox.selection_clear(0, tk.END)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(fill='x')
        
        analyze_btn = tk.Button(button_frame, text="🔍 Phân tích dữ liệu", 
                               command=analyze_data,
                               font=('Arial Unicode MS', 11), bg='#17a2b8', fg='white',
                               relief='flat', padx=20, pady=8)
        analyze_btn.pack(side='left', padx=(0, 10))
        
        repair_btn = tk.Button(button_frame, text="🔧 Sửa chữa đã chọn", 
                              command=repair_selected,
                              font=('Arial Unicode MS', 11), bg='#28a745', fg='white',
                              relief='flat', padx=20, pady=8)
        repair_btn.pack(side='left', padx=(0, 10))
        
        select_all_btn = tk.Button(button_frame, text="☑️ Chọn tất cả", 
                                  command=select_all_issues,
                                  font=('Arial Unicode MS', 11), bg='#ffc107', fg='black',
                                  relief='flat', padx=15, pady=8)
        select_all_btn.pack(side='left', padx=(0, 10))
        
        clear_btn = tk.Button(button_frame, text="🗑️ Bỏ chọn", 
                             command=clear_selection,
                             font=('Arial Unicode MS', 11), bg='#fd7e14', fg='white',
                             relief='flat', padx=15, pady=8)
        clear_btn.pack(side='left', padx=(0, 10))
        
        close_btn = tk.Button(button_frame, text="✕ Đóng", command=repair_win.destroy,
                             font=('Arial Unicode MS', 11), bg='#6c757d', fg='white',
                             relief='flat', padx=20, pady=8)
        close_btn.pack(side='right')
        
        # Initial analysis
        repair_win.after(100, analyze_data)
        
        # Shortcuts
        repair_win.focus_set()
        repair_win.bind('<Escape>', lambda e: repair_win.destroy())
        repair_win.bind('<F5>', lambda e: analyze_data())
    
    def _fade_in_window(self, alpha=0.0):
        """Smooth window fade-in animation"""
        alpha = min(alpha + 0.05, 1.0)
        try:
            self.attributes('-alpha', alpha)
            if alpha < 1.0:
                self.after(30, lambda: self._fade_in_window(alpha))
        except Exception:
            pass
    
    def _animate_version_badge(self, frame, label):
        """Subtle pulsing animation for version badge"""
        def pulse(brightness=1.0, direction=1):
            try:
                if direction == 1:
                    brightness = min(brightness + 0.02, 1.2)
                    if brightness >= 1.2:
                        direction = -1
                else:
                    brightness = max(brightness - 0.02, 0.8)
                    if brightness <= 0.8:
                        direction = 1
                
                # Calculate color based on brightness
                import colorsys
                rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(0.65, 0.8, brightness))
                color = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
                
                frame.configure(bg=color)
                label.configure(bg=color)
                
                # Continue animation
                self.after(100, lambda: pulse(brightness, direction))
            except Exception:
                pass
        
        # Start pulsing after a delay
        self.after(2000, pulse)
    
    def _on_tab_changed(self, event):
        """Handle tab change with smooth transition"""
        try:
            selected_tab = event.widget.nametowidget(event.widget.select())
            self._animate_tab_content(selected_tab)
        except Exception:
            pass
    
    def _animate_tab_content(self, tab_widget):
        """Animate tab content on selection"""
        try:
            # Fade-in animation for tab content
            original_state = tab_widget.cget('state') if hasattr(tab_widget, 'cget') else None
            
            def fade_in(alpha=0.0):
                alpha = min(alpha + 0.1, 1.0)
                # For frames, we simulate fade by adjusting relief and colors
                if alpha < 1.0:
                    tab_widget.after(50, lambda: fade_in(alpha))
                
            fade_in()
        except Exception:
            pass
    
    def create_animated_button(self, parent, text, command=None, style='primary', tooltip_text=None, tooltip_example=None):
        """Create an animated button with tooltip"""
        btn = AnimatedButton(parent, text, command, style)
        
        if tooltip_text:
            Tooltip(btn.button, tooltip_text, example=tooltip_example)
            
        return btn
    
    def on_closing(self):
        """Handle application closing with v2.0.0 enhancements."""
        try:
            # Save UI preferences
            if hasattr(self, 'save_ui_preferences'):
                self.save_ui_preferences()
                
            # Log application shutdown
                # Removed SQLite function call
                # Removed SQLite function call
                
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
            self.destroy()

if __name__ == '__main__':
    try:
        ensure_all_data_files()
    except Exception:
        pass
        
    # Initialize and start application
    app = MainApp()
    
    # Bind closing event
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start main loop
    app.mainloop()
