"""GUI tkinter dla systemu DS1 — Scenariusze Działań.

Ultra-modern 2026 dark theme with custom widgets, gradients,
rounded corners, hover animations, glassmorphism cards.

Uruchom: python -m src.main --gui
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font as tkfont
import io
import contextlib

from src.models import (
    Domain, Scenario, Observation, ActionDeclaration,
    CausesStatement, DurationStatement, ReleasesStatement,
    TriggersStatement, StateTriggerStatement,
    ImpossibleIfStatement, ImpossibleAtStatement,
    AtomicFormula, Negation, Conjunction,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)
from src.solver import solve
from src.printers import (
    format_formula, format_model_table,
    print_domain, print_scenario, print_validation, print_queries,
    query_times,
)
from src.parser import parse_file, derive_fluents_actions, ParseError
from tkinter import filedialog
import os

# Sciezka do folderu z przykladami (relatywnie do tego pliku)
EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
)


# ═══════════════════════════════════════════════════════════════
# DESIGN SYSTEM 2026
# ═══════════════════════════════════════════════════════════════

class Theme:
    # Base — light theme
    BG = '#ffffff'
    BG_SECONDARY = '#f6f8fa'
    BG_TERTIARY = '#eaeef2'
    SURFACE = '#f0f3f6'
    SURFACE_HOVER = '#e1e4e8'

    # Accent
    PRIMARY = '#8b5cf6'
    PRIMARY_HOVER = '#a78bfa'
    PRIMARY_DIM = '#6d28d9'
    PRIMARY_GLOW = '#8b5cf620'

    # Semantic — przyciemnione na jasnym tle dla czytelnosci
    SUCCESS = '#10b981'
    SUCCESS_DIM = '#d1fae5'
    WARNING = '#f59e0b'
    ERROR = '#ef4444'
    INFO = '#3b82f6'

    # Text — odwrocone: ciemny na jasnym
    FG = '#0d1117'
    FG_MUTED = '#57606a'
    FG_SUBTLE = '#8c959f'

    # Border
    BORDER = '#d0d7de'
    BORDER_ACCENT = '#8b5cf640'
    
    # Fonts (FONT_MONO moze byc nadpisany przez _pick_mono_font na starcie)
    FONT_FAMILY: str = 'Segoe UI'
    FONT_MONO: str = 'Cascadia Code'
    FONT_SCALE = 1.35
    
    # Sizing
    RADIUS = 12
    PADDING = 16
    GAP = 12


# ═══════════════════════════════════════════════════════════════
# CUSTOM WIDGETS
# ═══════════════════════════════════════════════════════════════

class ModernButton(tk.Canvas):
    """Animated button with rounded corners, hover glow, and press effect."""
    
    def __init__(self, parent, text="", command=None, width=120, height=36,
                 bg=Theme.PRIMARY, hover_bg=Theme.PRIMARY_HOVER, fg='#fff',
                 font_size=13, radius=8, style='filled', **kwargs):
        super().__init__(parent, width=width, height=height, 
                        bg=parent.cget('bg') if hasattr(parent, 'cget') else Theme.BG,
                        highlightthickness=0, **kwargs)
        
        self._text = text
        self._command = command
        self._bg = bg
        self._hover_bg = hover_bg
        self._fg = fg
        self._radius = radius
        self._style = style
        self._hover = False
        self._pressed = False
        self._font = (Theme.FONT_FAMILY, font_size, 'bold')
        
        self._draw()
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
    
    def _draw(self):
        self.delete('all')
        w, h = int(self.cget('width')), int(self.cget('height'))
        r = self._radius
        
        if self._style == 'filled':
            color = self._hover_bg if self._hover else self._bg
            outline = ''
        elif self._style == 'outline':
            color = Theme.SURFACE_HOVER if self._hover else ''
            outline = self._bg
        elif self._style == 'ghost':
            color = Theme.SURFACE_HOVER if self._hover else ''
            outline = ''
        
        # Glow effect on hover
        if self._hover and self._style == 'filled':
            self._rounded_rect(0, 0, w, h, r+2, fill='', outline=self._bg, width=2)
        
        # Main button shape
        self._rounded_rect(2, 2, w-2, h-2, r, fill=color, outline=outline,
                          width=1 if outline else 0)
        
        # Text
        text_color = self._fg
        offset = 1 if self._pressed else 0
        self.create_text(w//2, h//2 + offset, text=self._text, fill=text_color,
                        font=self._font)
    
    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        self.create_polygon(points, smooth=True, **kwargs)
    
    def _on_enter(self, e):
        self._hover = True
        self._draw()
        
    def _on_leave(self, e):
        self._hover = False
        self._pressed = False
        self._draw()
    
    def _on_press(self, e):
        self._pressed = True
        self._draw()
    
    def _on_release(self, e):
        self._pressed = False
        self._draw()
        if self._hover and self._command:
            self._command()


class ModernEntry(tk.Frame):
    """Styled entry with focus glow."""
    
    def __init__(self, parent, placeholder="", width=20, **kwargs):
        super().__init__(parent, bg=parent.cget('bg') if hasattr(parent, 'cget') else Theme.BG)
        
        self._placeholder = placeholder
        
        self._border = tk.Frame(self, bg=Theme.BORDER, padx=1, pady=1)
        self._border.pack(fill='x')
        
        self._inner = tk.Frame(self._border, bg=Theme.SURFACE, padx=8, pady=5)
        self._inner.pack(fill='x')
        
        self._entry = tk.Entry(self._inner, bg=Theme.SURFACE, fg=Theme.FG,
                              insertbackground=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 13),
                              relief='flat', width=width, borderwidth=0)
        self._entry.pack(fill='x')
        
        self._entry.bind('<FocusIn>', self._on_focus_in)
        self._entry.bind('<FocusOut>', self._on_focus_out)
        
        if placeholder:
            self._entry.insert(0, placeholder)
            self._entry.config(fg=Theme.FG_MUTED)
            self._entry.bind('<FocusIn>', self._clear_placeholder)
            self._entry.bind('<FocusOut>', self._show_placeholder)
    
    def _on_focus_in(self, e):
        self._border.config(bg=Theme.PRIMARY)
        
    def _on_focus_out(self, e):
        self._border.config(bg=Theme.BORDER)
    
    def _clear_placeholder(self, e):
        if self._entry.get() == self._placeholder:
            self._entry.delete(0, 'end')
            self._entry.config(fg=Theme.FG)
        self._on_focus_in(e)
    
    def _show_placeholder(self, e):
        if not self._entry.get():
            self._entry.insert(0, self._placeholder)
            self._entry.config(fg=Theme.FG_MUTED)
        self._on_focus_out(e)
    
    def get(self):
        val = self._entry.get()
        return '' if val == self._placeholder else val
    
    def delete(self, first, last):
        self._entry.delete(first, last)
        if self._placeholder:
            self._show_placeholder(None)
    
    def bind_key(self, key, func):
        self._entry.bind(key, func)


class ModernListbox(tk.Frame):
    """Custom styled listbox with dark theme."""
    
    def __init__(self, parent, height=10, **kwargs):
        super().__init__(parent, bg=Theme.SURFACE, highlightthickness=1,
                        highlightbackground=Theme.BORDER, highlightcolor=Theme.PRIMARY)
        
        self._listbox = tk.Listbox(self, height=height, font=(Theme.FONT_MONO, 12),
                                  bg=Theme.SURFACE, fg=Theme.FG,
                                  selectbackground=Theme.PRIMARY,
                                  selectforeground='#fff',
                                  activestyle='none', relief='flat',
                                  borderwidth=0, highlightthickness=0)
        
        scrollbar = tk.Scrollbar(self, orient='vertical', command=self._listbox.yview,
                                bg=Theme.SURFACE, troughcolor=Theme.BG_SECONDARY,
                                activebackground=Theme.FG_SUBTLE, width=8)
        self._listbox.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y', padx=(0, 2), pady=4)
        self._listbox.pack(side='left', fill='both', expand=True, padx=8, pady=6)
    
    def insert(self, idx, item):
        self._listbox.insert(idx, f"  {item}")
    
    def delete(self, first, last=''):
        if last:
            self._listbox.delete(first, last)
        else:
            self._listbox.delete(first)
    
    def curselection(self):
        return self._listbox.curselection()


class TabBar(tk.Frame):
    """Custom modern tab bar with animated underline."""
    
    def __init__(self, parent, tabs, command=None):
        super().__init__(parent, bg=Theme.BG_SECONDARY, height=44)
        self.pack_propagate(False)
        self._tabs = tabs
        self._command = command
        self._active = 0
        self._tab_labels = []
        
        for i, (text, _) in enumerate(tabs):
            lbl = tk.Label(self, text=text, bg=Theme.BG_SECONDARY, 
                          fg=Theme.FG if i == 0 else Theme.FG_MUTED,
                          font=(Theme.FONT_FAMILY, 13, 'bold' if i == 0 else 'normal'),
                          padx=18, pady=11, cursor='hand2')
            lbl.pack(side='left')
            lbl.bind('<Button-1>', lambda e, idx=i: self._select(idx))
            lbl.bind('<Enter>', lambda e, l=lbl, idx=i: l.config(fg=Theme.PRIMARY_HOVER) if idx != self._active else None)
            lbl.bind('<Leave>', lambda e, l=lbl, idx=i: l.config(fg=Theme.FG if idx == self._active else Theme.FG_MUTED))
            self._tab_labels.append(lbl)
        
        # Underline indicator
        self._underline = tk.Frame(self, bg=Theme.PRIMARY, height=3)
        self._underline.place(x=0, y=41, width=100)
        self.after(50, self._update_underline)
    
    def _select(self, idx):
        old = self._active
        self._active = idx
        self._tab_labels[old].config(fg=Theme.FG_MUTED, font=(Theme.FONT_FAMILY, 13))
        self._tab_labels[idx].config(fg=Theme.FG, font=(Theme.FONT_FAMILY, 13, 'bold'))
        self._update_underline()
        if self._command:
            self._command(idx)
    
    def _update_underline(self):
        if self._tab_labels:
            lbl = self._tab_labels[self._active]
            x = lbl.winfo_x()
            w = lbl.winfo_width()
            if w > 1:
                self._underline.place(x=x, width=w)
            else:
                self.after(50, self._update_underline)


class ContentPanel(tk.Frame):
    """Panel that shows/hides frames based on tab selection."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Theme.BG, **kwargs)
        self._frames = []
        self._active = 0
    
    def add_frame(self, frame):
        self._frames.append(frame)
        if len(self._frames) == 1:
            frame.pack(fill='both', expand=True)
    
    def show(self, idx):
        self._frames[self._active].pack_forget()
        self._active = idx
        self._frames[idx].pack(fill='both', expand=True)


# ═══════════════════════════════════════════════════════════════
# FORMULA HELPERS
# ═══════════════════════════════════════════════════════════════

def _and_of_literals(literals):
    if not literals:
        return None
    def lit(name, pos):
        a = AtomicFormula(name)
        return a if pos else Negation(a)
    formula = lit(*literals[0])
    for name, pos in literals[1:]:
        formula = Conjunction(formula, lit(name, pos))
    return formula


# ═══════════════════════════════════════════════════════════════
# DIALOGS (Modern styled)
# ═══════════════════════════════════════════════════════════════

class FormulaDialog(tk.Toplevel):
    def __init__(self, parent, fluents, title="Zbuduj formule", required=True):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.configure(bg=Theme.BG)
        
        self.fluents = fluents
        self.required = required
        self.result = None
        self.choices = {}

        if not fluents:
            lbl = tk.Label(self, text="⚠️ Brak fluentów.\nDodaj w zakładce 'Fluenty i akcje'.",
                          fg=Theme.WARNING, bg=Theme.BG, font=(Theme.FONT_FAMILY, 13))
            lbl.pack(pady=30, padx=30)
            ModernButton(self, text="OK", command=self.cancel, width=80, height=32,
                        font_size=11).pack(pady=10)
            self.wait_window()
            return

        # Title
        tk.Label(self, text="Wybierz wartość fluentów:", fg=Theme.FG, bg=Theme.BG,
                font=(Theme.FONT_FAMILY, 14, 'bold')).pack(pady=(16, 12), padx=20, anchor='w')

        # Headers
        hdr = tk.Frame(self, bg=Theme.BG)
        hdr.pack(fill='x', padx=20)
        tk.Label(hdr, text="Fluent", fg=Theme.FG_MUTED, bg=Theme.BG, width=20, anchor='w',
                font=(Theme.FONT_FAMILY, 11, 'bold')).pack(side='left')
        for t in ['True', 'False', 'Pomiń']:
            tk.Label(hdr, text=t, fg=Theme.FG_MUTED, bg=Theme.BG, width=8,
                    font=(Theme.FONT_FAMILY, 11, 'bold')).pack(side='left')

        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill='x', padx=20, pady=6)

        # Rows
        for f in fluents:
            row = tk.Frame(self, bg=Theme.BG)
            row.pack(fill='x', padx=20, pady=3)
            var = tk.StringVar(value="skip")
            self.choices[f] = var
            tk.Label(row, text=f, fg=Theme.FG, bg=Theme.BG, width=20, anchor='w',
                    font=(Theme.FONT_MONO, 12)).pack(side='left')
            for val in ['true', 'false', 'skip']:
                tk.Radiobutton(row, variable=var, value=val, bg=Theme.BG,
                              fg=Theme.FG, selectcolor=Theme.PRIMARY_DIM,
                              activebackground=Theme.BG, activeforeground=Theme.FG,
                              highlightthickness=0, width=6).pack(side='left')

        # Buttons
        btn_frame = tk.Frame(self, bg=Theme.BG)
        btn_frame.pack(fill='x', padx=20, pady=16)
        ModernButton(btn_frame, text="✓ Zatwierdź", command=self.ok, width=110, height=34,
                    font_size=11).pack(side='right', padx=4)
        ModernButton(btn_frame, text="Anuluj", command=self.cancel, width=90, height=34,
                    bg=Theme.SURFACE, hover_bg=Theme.SURFACE_HOVER, fg=Theme.FG_MUTED,
                    font_size=11, style='outline').pack(side='right', padx=4)

        self.wait_window()

    def ok(self):
        literals = []
        for f, var in self.choices.items():
            val = var.get()
            if val == "true":
                literals.append((f, True))
            elif val == "false":
                literals.append((f, False))
        if self.required and not literals:
            messagebox.showerror("Błąd", "Wybierz co najmniej jeden literal.", parent=self)
            return
        self.result = _and_of_literals(literals)
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


class LiteralDialog(tk.Toplevel):
    def __init__(self, parent, fluents, title="Wybierz literal"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.configure(bg=Theme.BG)
        self.result = None

        if not fluents:
            tk.Label(self, text="⚠️ Brak fluentów.", fg=Theme.WARNING, bg=Theme.BG,
                    font=(Theme.FONT_FAMILY, 13)).pack(pady=30, padx=30)
            ModernButton(self, text="OK", command=self.cancel, width=80, height=32).pack(pady=10)
            self.wait_window()
            return

        tk.Label(self, text="Wybierz fluent:", fg=Theme.FG, bg=Theme.BG,
                font=(Theme.FONT_FAMILY, 14, 'bold')).pack(pady=(16, 12), padx=20, anchor='w')

        # Combobox
        combo_frame = tk.Frame(self, bg=Theme.SURFACE, padx=8, pady=6)
        combo_frame.pack(fill='x', padx=20, pady=4)
        self.fluent_var = tk.StringVar(value=fluents[0])
        combo = ttk.Combobox(combo_frame, textvariable=self.fluent_var, values=fluents,
                           state="readonly", width=30, font=(Theme.FONT_FAMILY, 12))
        combo.pack()

        # Negation
        self.negated_var = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(self, text="  Negacja (~)", variable=self.negated_var,
                            bg=Theme.BG, fg=Theme.FG, selectcolor=Theme.PRIMARY_DIM,
                            activebackground=Theme.BG, activeforeground=Theme.FG,
                            font=(Theme.FONT_FAMILY, 12), highlightthickness=0)
        chk.pack(padx=20, pady=12, anchor='w')

        btn_frame = tk.Frame(self, bg=Theme.BG)
        btn_frame.pack(fill='x', padx=20, pady=14)
        ModernButton(btn_frame, text="✓ OK", command=self.ok, width=90, height=34,
                    font_size=11).pack(side='right', padx=4)
        ModernButton(btn_frame, text="Anuluj", command=self.cancel, width=90, height=34,
                    bg=Theme.SURFACE, hover_bg=Theme.SURFACE_HOVER, fg=Theme.FG_MUTED,
                    font_size=11, style='outline').pack(side='right', padx=4)

        self.wait_window()

    def ok(self):
        f = self.fluent_var.get()
        atom = AtomicFormula(f)
        self.result = Negation(atom) if self.negated_var.get() else atom
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


# ═══════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════

class DS1App:
    def __init__(self, root):
        self.root = root
        self.root.title("DS1 — Scenariusze Działań")
        self.root.geometry("1280x820")
        self.root.configure(bg=Theme.BG)
        self.root.minsize(1000, 700)

        self.fluents = []
        self.actions = []
        self.domain_items = []
        self.observations = []
        self.acs = []
        self.queries = []

        self._build_ui()

    def _build_ui(self):
        # ═══ HEADER ═══
        header = tk.Frame(self.root, bg=Theme.BG_SECONDARY, height=56)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        # Logo
        logo_frame = tk.Frame(header, bg=Theme.BG_SECONDARY)
        logo_frame.pack(side='left', padx=20, pady=10)
        
        tk.Label(logo_frame, text="◆", fg=Theme.PRIMARY, bg=Theme.BG_SECONDARY,
                font=(Theme.FONT_FAMILY, 20)).pack(side='left', padx=(0, 8))
        tk.Label(logo_frame, text="DS1", fg=Theme.FG, bg=Theme.BG_SECONDARY,
                font=(Theme.FONT_FAMILY, 16, 'bold')).pack(side='left')
        tk.Label(logo_frame, text="Scenariusze Działań", fg=Theme.FG_MUTED, 
                bg=Theme.BG_SECONDARY, font=(Theme.FONT_FAMILY, 12)).pack(side='left', padx=(8, 0))
        
        # Header buttons
        hdr_btns = tk.Frame(header, bg=Theme.BG_SECONDARY)
        hdr_btns.pack(side='right', padx=16, pady=10)
        
        ModernButton(hdr_btns, text="▶ Rozwiąż", command=self.solve_and_display,
                    width=120, height=38, font_size=12, bg=Theme.SUCCESS,
                    hover_bg='#4ade80').pack(side='right', padx=6)
        ModernButton(hdr_btns, text="🗑 Wyczyść", command=self.clear_all,
                    width=110, height=38, font_size=11, style='ghost',
                    bg=Theme.ERROR, hover_bg=Theme.SURFACE_HOVER, fg=Theme.FG_MUTED
                    ).pack(side='right', padx=4)

        # ═══ EXAMPLES BAR ═══
        examples_bar = tk.Frame(self.root, bg=Theme.BG, height=44)
        examples_bar.pack(fill='x', padx=20, pady=(8, 0))
        
        tk.Label(examples_bar, text="Przykłady:", fg=Theme.FG_MUTED, bg=Theme.BG,
                font=(Theme.FONT_FAMILY, 11)).pack(side='left', padx=(0, 10))
        
        ex_data = [
            (1, "📺 Projektor"), (2, "🏢 Serwerownia"), (3, "🐞 Błędny"),
            (4, "💨 Smoke"), (5, "⚙️ Z5"),
        ]
        for n, name in ex_data:
            ModernButton(examples_bar, text=name,
                        command=lambda nn=n: self.load_example(nn),
                        width=112, height=32, font_size=11,
                        bg=Theme.SURFACE, hover_bg=Theme.SURFACE_HOVER,
                        fg=Theme.FG_MUTED, style='outline', radius=6
                        ).pack(side='left', padx=3)

        # Przycisk "Inny przyklad..." — file picker
        ModernButton(examples_bar, text="📂 Inny przyklad…",
                     command=self.load_custom_example,
                     width=160, height=32, font_size=11,
                     bg=Theme.PRIMARY, hover_bg=Theme.PRIMARY_HOVER,
                     fg='#ffffff', style='filled', radius=6
                     ).pack(side='left', padx=(12, 3))

        # ═══ MAIN CONTENT ═══
        main = tk.Frame(self.root, bg=Theme.BG)
        main.pack(fill='both', expand=True, padx=16, pady=12)

        # Left: Tabs + Content
        left = tk.Frame(main, bg=Theme.BG)
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))

        tabs = [
            ("Fluenty & Akcje", None),
            ("Dziedzina", None),
            ("Scenariusz", None),
            ("Kwerendy", None),
        ]

        self._tab_bar = TabBar(left, tabs, command=self._on_tab_change)
        self._tab_bar.pack(fill='x')

        self._content = ContentPanel(left)
        self._content.pack(fill='both', expand=True, pady=(8, 0))

        self._build_tab_setup()
        self._build_tab_domain()
        self._build_tab_scenario()
        self._build_tab_queries()

        # Right: Results — rozszerza sie razem z oknem (jak lewa strona)
        right = tk.Frame(main, bg=Theme.BG)
        right.pack(side='right', fill='both', expand=True, padx=(8, 0))

        self._build_results_panel(right)

    def _on_tab_change(self, idx):
        self._content.show(idx)

    # ═══════════════════════════════════════════════════════════
    # TAB 1: FLUENTS & ACTIONS
    # ═══════════════════════════════════════════════════════════

    def _build_tab_setup(self):
        frame = tk.Frame(self._content, bg=Theme.BG)
        self._content.add_frame(frame)
        
        cols = tk.Frame(frame, bg=Theme.BG)
        cols.pack(fill='both', expand=True, pady=8)
        
        # Fluents card
        left_card = tk.Frame(cols, bg=Theme.SURFACE, highlightthickness=1,
                            highlightbackground=Theme.BORDER)
        left_card.pack(side='left', fill='both', expand=True, padx=(0, 6))
        
        hdr = tk.Frame(left_card, bg=Theme.SURFACE)
        hdr.pack(fill='x', padx=12, pady=(12, 8))
        tk.Label(hdr, text="📝 Fluenty", fg=Theme.FG, bg=Theme.SURFACE,
                font=(Theme.FONT_FAMILY, 13, 'bold')).pack(side='left')
        
        self.fluents_list = ModernListbox(left_card, height=12)
        self.fluents_list.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        
        entry_row = tk.Frame(left_card, bg=Theme.SURFACE)
        entry_row.pack(fill='x', padx=12, pady=(0, 8))
        self.fluent_entry = ModernEntry(entry_row, placeholder="Nazwa fluentu...", width=18)
        self.fluent_entry.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.fluent_entry.bind_key('<Return>', lambda e: self.add_fluent())
        ModernButton(entry_row, text="+ Dodaj", command=self.add_fluent, width=92, height=34,
                    font_size=11, radius=6).pack(side='left')
        
        del_row = tk.Frame(left_card, bg=Theme.SURFACE)
        del_row.pack(fill='x', padx=12, pady=(0, 12))
        ModernButton(del_row, text="Usuń", command=self.del_fluent, width=82, height=32,
                    bg=Theme.ERROR, hover_bg='#fca5a5', font_size=11, radius=6).pack(side='left')
        
        # Actions card
        right_card = tk.Frame(cols, bg=Theme.SURFACE, highlightthickness=1,
                             highlightbackground=Theme.BORDER)
        right_card.pack(side='left', fill='both', expand=True, padx=(6, 0))
        
        hdr2 = tk.Frame(right_card, bg=Theme.SURFACE)
        hdr2.pack(fill='x', padx=12, pady=(12, 8))
        tk.Label(hdr2, text="⚡ Akcje", fg=Theme.FG, bg=Theme.SURFACE,
                font=(Theme.FONT_FAMILY, 13, 'bold')).pack(side='left')
        
        self.actions_list = ModernListbox(right_card, height=12)
        self.actions_list.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        
        entry_row2 = tk.Frame(right_card, bg=Theme.SURFACE)
        entry_row2.pack(fill='x', padx=12, pady=(0, 8))
        self.action_entry = ModernEntry(entry_row2, placeholder="Nazwa akcji...", width=18)
        self.action_entry.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.action_entry.bind_key('<Return>', lambda e: self.add_action())
        ModernButton(entry_row2, text="+ Dodaj", command=self.add_action, width=92, height=34,
                    font_size=11, radius=6).pack(side='left')
        
        del_row2 = tk.Frame(right_card, bg=Theme.SURFACE)
        del_row2.pack(fill='x', padx=12, pady=(0, 12))
        ModernButton(del_row2, text="Usuń", command=self.del_action, width=82, height=32,
                    bg=Theme.ERROR, hover_bg='#fca5a5', font_size=11, radius=6).pack(side='left')

    # ═══════════════════════════════════════════════════════════
    # TAB 2: DOMAIN
    # ═══════════════════════════════════════════════════════════

    def _build_tab_domain(self):
        frame = tk.Frame(self._content, bg=Theme.BG)
        self._content.add_frame(frame)
        
        # Buttons row
        btns = tk.Frame(frame, bg=Theme.BG)
        btns.pack(fill='x', pady=(8, 10))
        
        domain_btns = [
            ("⏱ Duration", self.add_duration),
            ("→ Causes", self.add_causes),
            ("🔓 Releases", self.add_releases),
            ("🔗 Triggers", self.add_triggers),
            ("🎯 State", self.add_state_trigger),
            ("🚫 Imp. If", self.add_impossible_if),
            ("⛔ Imp. At", self.add_impossible_at),
        ]
        for text, cmd in domain_btns:
            ModernButton(btns, text=text, command=cmd, width=102, height=34,
                        font_size=10, radius=6, bg=Theme.SURFACE, hover_bg=Theme.SURFACE_HOVER,
                        fg=Theme.FG_MUTED, style='outline').pack(side='left', padx=2)
        
        # List card
        card = tk.Frame(frame, bg=Theme.SURFACE, highlightthickness=1,
                       highlightbackground=Theme.BORDER)
        card.pack(fill='both', expand=True)
        
        tk.Label(card, text="📋 Instrukcje dziedziny", fg=Theme.FG_MUTED, bg=Theme.SURFACE,
                font=(Theme.FONT_FAMILY, 11)).pack(anchor='w', padx=12, pady=(10, 4))
        
        self.domain_list = ModernListbox(card, height=14)
        self.domain_list.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        
        ModernButton(card, text="🗑 Usuń", command=self.del_domain_item, width=92, height=32,
                    bg=Theme.ERROR, hover_bg='#fca5a5', font_size=11, radius=6
                    ).pack(anchor='w', padx=12, pady=(0, 12))

    # ═══════════════════════════════════════════════════════════
    # TAB 3: SCENARIO
    # ═══════════════════════════════════════════════════════════

    def _build_tab_scenario(self):
        frame = tk.Frame(self._content, bg=Theme.BG)
        self._content.add_frame(frame)
        
        cols = tk.Frame(frame, bg=Theme.BG)
        cols.pack(fill='both', expand=True, pady=8)
        
        # OBS card
        left_card = tk.Frame(cols, bg=Theme.SURFACE, highlightthickness=1,
                            highlightbackground=Theme.BORDER)
        left_card.pack(side='left', fill='both', expand=True, padx=(0, 6))
        
        hdr = tk.Frame(left_card, bg=Theme.SURFACE)
        hdr.pack(fill='x', padx=12, pady=(12, 8))
        tk.Label(hdr, text="👁 Obserwacje", fg=Theme.FG, bg=Theme.SURFACE,
                font=(Theme.FONT_FAMILY, 13, 'bold')).pack(side='left')
        
        self.obs_list = ModernListbox(left_card, height=12)
        self.obs_list.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        
        obs_btns = tk.Frame(left_card, bg=Theme.SURFACE)
        obs_btns.pack(fill='x', padx=12, pady=(0, 12))
        ModernButton(obs_btns, text="+ Dodaj", command=self.add_obs, width=92, height=32,
                    font_size=11, radius=6).pack(side='left', padx=(0, 4))
        ModernButton(obs_btns, text="Usuń", command=self.del_obs, width=82, height=32,
                    bg=Theme.ERROR, hover_bg='#fca5a5', font_size=11, radius=6).pack(side='left')
        
        # ACS card
        right_card = tk.Frame(cols, bg=Theme.SURFACE, highlightthickness=1,
                             highlightbackground=Theme.BORDER)
        right_card.pack(side='left', fill='both', expand=True, padx=(6, 0))
        
        hdr2 = tk.Frame(right_card, bg=Theme.SURFACE)
        hdr2.pack(fill='x', padx=12, pady=(12, 8))
        tk.Label(hdr2, text="🎬 Deklaracje akcji", fg=Theme.FG, bg=Theme.SURFACE,
                font=(Theme.FONT_FAMILY, 13, 'bold')).pack(side='left')
        
        self.acs_list = ModernListbox(right_card, height=12)
        self.acs_list.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        
        acs_btns = tk.Frame(right_card, bg=Theme.SURFACE)
        acs_btns.pack(fill='x', padx=12, pady=(0, 12))
        ModernButton(acs_btns, text="+ Dodaj", command=self.add_acs, width=92, height=32,
                    font_size=11, radius=6).pack(side='left', padx=(0, 4))
        ModernButton(acs_btns, text="Usuń", command=self.del_acs, width=82, height=32,
                    bg=Theme.ERROR, hover_bg='#fca5a5', font_size=11, radius=6).pack(side='left')

    # ═══════════════════════════════════════════════════════════
    # TAB 4: QUERIES
    # ═══════════════════════════════════════════════════════════

    def _build_tab_queries(self):
        frame = tk.Frame(self._content, bg=Theme.BG)
        self._content.add_frame(frame)
        
        btns = tk.Frame(frame, bg=Theme.BG)
        btns.pack(fill='x', pady=(8, 10))
        
        query_btns = [
            ("🤔 possibly Sc", self.add_q_possibly_sc),
            ("⚙️ nec. perf.", lambda: self.add_q_performing("necessary")),
            ("🤔 poss. perf.", lambda: self.add_q_performing("possibly")),
            ("⚙️ nec. γ", lambda: self.add_q_condition("necessary")),
            ("🤔 poss. γ", lambda: self.add_q_condition("possibly")),
        ]
        for text, cmd in query_btns:
            ModernButton(btns, text=text, command=cmd, width=124, height=34,
                        font_size=10, radius=6, bg=Theme.SURFACE, hover_bg=Theme.SURFACE_HOVER,
                        fg=Theme.FG_MUTED, style='outline').pack(side='left', padx=2)
        
        card = tk.Frame(frame, bg=Theme.SURFACE, highlightthickness=1,
                       highlightbackground=Theme.BORDER)
        card.pack(fill='both', expand=True)
        
        tk.Label(card, text="📌 Lista kwerend", fg=Theme.FG_MUTED, bg=Theme.SURFACE,
                font=(Theme.FONT_FAMILY, 11)).pack(anchor='w', padx=12, pady=(10, 4))
        
        self.queries_list = ModernListbox(card, height=14)
        self.queries_list.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        
        ModernButton(card, text="🗑 Usuń", command=self.del_query, width=92, height=32,
                    bg=Theme.ERROR, hover_bg='#fca5a5', font_size=11, radius=6
                    ).pack(anchor='w', padx=12, pady=(0, 12))

    # ═══════════════════════════════════════════════════════════
    # RESULTS PANEL
    # ═══════════════════════════════════════════════════════════

    def _build_results_panel(self, parent):
        # Header
        hdr = tk.Frame(parent, bg=Theme.BG)
        hdr.pack(fill='x', pady=(0, 8))
        tk.Label(hdr, text="📊 Wyniki", fg=Theme.FG, bg=Theme.BG,
                font=(Theme.FONT_FAMILY, 14, 'bold')).pack(side='left')
        
        # Result card
        card = tk.Frame(parent, bg=Theme.SURFACE, highlightthickness=1,
                       highlightbackground=Theme.BORDER)
        card.pack(fill='both', expand=True)
        
        self.results_text = tk.Text(card, font=(Theme.FONT_MONO, 12), wrap='none',
                                   bg=Theme.SURFACE, fg=Theme.FG,
                                   insertbackground=Theme.PRIMARY,
                                   relief='flat', borderwidth=0, padx=12, pady=12,
                                   highlightthickness=0)
        
        scrolly = tk.Scrollbar(card, orient='vertical', command=self.results_text.yview,
                              bg=Theme.SURFACE, troughcolor=Theme.BG_SECONDARY,
                              activebackground=Theme.FG_SUBTLE, width=8)
        scrollx = tk.Scrollbar(card, orient='horizontal', command=self.results_text.xview,
                              bg=Theme.SURFACE, troughcolor=Theme.BG_SECONDARY, width=8)
        
        self.results_text.config(yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        
        scrolly.pack(side='right', fill='y', padx=(0, 2), pady=2)
        scrollx.pack(side='bottom', fill='x', padx=2, pady=(0, 2))
        self.results_text.pack(fill='both', expand=True)

    # ═══════════════════════════════════════════════════════════
    # LOGIC: Fluents & Actions
    # ═══════════════════════════════════════════════════════════

    def add_fluent(self):
        name = self.fluent_entry.get().strip()
        if not name:
            return
        if name in self.fluents:
            messagebox.showerror("Błąd", f"Fluent '{name}' już istnieje.")
            return
        self.fluents.append(name)
        self.fluent_entry.delete(0, 'end')
        self._refresh_fluents()

    def del_fluent(self):
        sel = self.fluents_list.curselection()
        if sel:
            del self.fluents[sel[0]]
            self._refresh_fluents()

    def add_action(self):
        name = self.action_entry.get().strip()
        if not name:
            return
        if name in self.actions:
            messagebox.showerror("Błąd", f"Akcja '{name}' już istnieje.")
            return
        self.actions.append(name)
        self.action_entry.delete(0, 'end')
        self._refresh_actions()

    def del_action(self):
        sel = self.actions_list.curselection()
        if sel:
            del self.actions[sel[0]]
            self._refresh_actions()

    def _refresh_fluents(self):
        self.fluents_list.delete(0, 'end')
        for f in self.fluents:
            self.fluents_list.insert('end', f)

    def _refresh_actions(self):
        self.actions_list.delete(0, 'end')
        for a in self.actions:
            self.actions_list.insert('end', a)

    # ═══════════════════════════════════════════════════════════
    # LOGIC: Domain
    # ═══════════════════════════════════════════════════════════

    def _ask_action(self, title):
        if not self.actions:
            messagebox.showerror("Błąd", "Brak akcji. Dodaj w zakładce 1.")
            return None
        return self._ask_choice(title, "Akcja:", self.actions)

    def _ask_fluent(self, title):
        if not self.fluents:
            messagebox.showerror("Błąd", "Brak fluentów. Dodaj w zakładce 1.")
            return None
        return self._ask_choice(title, "Fluent:", self.fluents)

    def _ask_int(self, title, prompt, min_=0):
        return simpledialog.askinteger(title, prompt, parent=self.root, minvalue=min_)

    def _ask_choice(self, title, prompt, choices):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.configure(bg=Theme.BG)
        
        tk.Label(dlg, text=prompt, fg=Theme.FG, bg=Theme.BG,
                font=(Theme.FONT_FAMILY, 13, 'bold')).pack(padx=20, pady=(16, 8))
        
        var = tk.StringVar(value=choices[0])
        combo_frame = tk.Frame(dlg, bg=Theme.SURFACE, padx=8, pady=6)
        combo_frame.pack(padx=20, pady=8)
        ttk.Combobox(combo_frame, textvariable=var, values=choices, state="readonly",
                    width=28, font=(Theme.FONT_FAMILY, 12)).pack()
        
        result = [None]
        def ok():
            result[0] = var.get()
            dlg.destroy()

        btn_frame = tk.Frame(dlg, bg=Theme.BG)
        btn_frame.pack(padx=20, pady=14)
        ModernButton(btn_frame, text="✓ OK", command=ok, width=90, height=32,
                    font_size=11).pack(side='left', padx=4)
        ModernButton(btn_frame, text="Anuluj", command=dlg.destroy, width=90, height=32,
                    bg=Theme.SURFACE, hover_bg=Theme.SURFACE_HOVER, fg=Theme.FG_MUTED,
                    font_size=11, style='outline').pack(side='left', padx=4)
        dlg.wait_window()
        return result[0]

    def add_duration(self):
        action = self._ask_action("Duration")
        if not action:
            return
        n = self._ask_int("Duration", f"Czas trwania '{action}' (>= 1):", min_=1)
        if n is None:
            return
        self.domain_items.append(DurationStatement(action, n))
        self._refresh_domain()

    def add_causes(self):
        action = self._ask_action("Causes")
        if not action:
            return
        effect = LiteralDialog(self.root, self.fluents, "Causes — efekt").result
        if effect is None:
            return
        delay = self._ask_int(
            "Causes",
            "Opóźnienie efektu (>= 0; 0 = natychmiastowy w start_time):",
            min_=0,
        )
        if delay is None:
            return
        add_cond = messagebox.askyesno("Causes", "Dodać warunek 'if'?")
        condition = None
        if add_cond:
            condition = FormulaDialog(self.root, self.fluents, "Causes — warunek", required=True).result
            if condition is None:
                return
        self.domain_items.append(CausesStatement(action, effect, delay, condition))
        self._refresh_domain()

    def add_releases(self):
        action = self._ask_action("Releases")
        if not action:
            return
        fluent = self._ask_fluent("Releases — fluent")
        if not fluent:
            return
        a = self._ask_int("Releases", "Początek przedziału:", min_=0)
        if a is None:
            return
        b = self._ask_int("Releases", "Koniec przedziału:", min_=0)
        if b is None:
            return
        if b < a:
            messagebox.showerror("Błąd", "Koniec >= początek.")
            return
        self.domain_items.append(ReleasesStatement(action, fluent, a, b))
        self._refresh_domain()

    def add_triggers(self):
        cause = self._ask_action("Triggers — wyzwalająca")
        if not cause:
            return
        triggered = self._ask_action("Triggers — wyzwalana")
        if not triggered:
            return
        delay = self._ask_int("Triggers", "Opóźnienie (>= 0):", min_=0)
        if delay is None:
            return
        self.domain_items.append(TriggersStatement(cause, triggered, delay))
        self._refresh_domain()

    def add_state_trigger(self):
        condition = FormulaDialog(self.root, self.fluents, "State Trigger — warunek", required=True).result
        if condition is None:
            return
        action = self._ask_action("State Trigger — akcja")
        if not action:
            return
        self.domain_items.append(StateTriggerStatement(condition, action))
        self._refresh_domain()

    def add_impossible_if(self):
        action = self._ask_action("Impossible If")
        if not action:
            return
        condition = FormulaDialog(self.root, self.fluents, "Impossible If — warunek", required=True).result
        if condition is None:
            return
        self.domain_items.append(ImpossibleIfStatement(action, condition))
        self._refresh_domain()

    def add_impossible_at(self):
        action = self._ask_action("Impossible At")
        if not action:
            return
        t = self._ask_int("Impossible At", "Punkt czasowy t:", min_=0)
        if t is None:
            return
        self.domain_items.append(ImpossibleAtStatement(action, t))
        self._refresh_domain()

    def del_domain_item(self):
        sel = self.domain_list.curselection()
        if sel:
            del self.domain_items[sel[0]]
            self._refresh_domain()

    def _refresh_domain(self):
        self.domain_list.delete(0, 'end')
        for s in self.domain_items:
            self.domain_list.insert('end', self._format_domain_item(s))

    def _format_domain_item(self, s):
        if isinstance(s, DurationStatement):
            return f"{s.action} duration {s.duration}"
        if isinstance(s, CausesStatement):
            cond = f" if {format_formula(s.condition)}" if s.condition else ""
            return f"{s.action} causes {format_formula(s.effect)} after {s.delay}{cond}"
        if isinstance(s, ReleasesStatement):
            return f"{s.action} releases {s.fluent} [{s.interval_start},{s.interval_end}]"
        if isinstance(s, TriggersStatement):
            return f"{s.cause_action} triggers {s.triggered_action} after {s.delay}"
        if isinstance(s, StateTriggerStatement):
            return f"{format_formula(s.condition)} causes {s.action}"
        if isinstance(s, ImpossibleIfStatement):
            return f"impossible {s.action} if {format_formula(s.condition)}"
        if isinstance(s, ImpossibleAtStatement):
            return f"impossible {s.action} at {s.time_point}"
        return repr(s)

    # ═══════════════════════════════════════════════════════════
    # LOGIC: Scenario
    # ═══════════════════════════════════════════════════════════

    def add_obs(self):
        formula = FormulaDialog(self.root, self.fluents, "Obserwacja — formuła", required=True).result
        if formula is None:
            return
        t = self._ask_int("Obserwacja", "Chwila t:", min_=0)
        if t is None:
            return
        self.observations.append(Observation(formula, t))
        self._refresh_scenario()

    def del_obs(self):
        sel = self.obs_list.curselection()
        if sel:
            del self.observations[sel[0]]
            self._refresh_scenario()

    def add_acs(self):
        action = self._ask_action("Deklaracja akcji")
        if not action:
            return
        t = self._ask_int("Deklaracja", "Chwila startu t:", min_=0)
        if t is None:
            return
        self.acs.append(ActionDeclaration(action, t))
        self._refresh_scenario()

    def del_acs(self):
        sel = self.acs_list.curselection()
        if sel:
            del self.acs[sel[0]]
            self._refresh_scenario()

    def _refresh_scenario(self):
        self.obs_list.delete(0, 'end')
        for obs in self.observations:
            self.obs_list.insert('end', f"({format_formula(obs.formula)}, t={obs.time})")
        self.acs_list.delete(0, 'end')
        for ad in self.acs:
            self.acs_list.insert('end', f"({ad.action}, t={ad.time})")

    # ═══════════════════════════════════════════════════════════
    # LOGIC: Queries
    # ═══════════════════════════════════════════════════════════

    def add_q_possibly_sc(self):
        self.queries.append(("possibly Sc", QueryPossiblyScenario()))
        self._refresh_queries()

    def add_q_performing(self, mode):
        action = self._ask_action(f"{mode} performing")
        if not action:
            return
        t = self._ask_int(f"{mode} performing", "Chwila t:", min_=0)
        if t is None:
            return
        self.queries.append((f"{mode} performing {action} at {t}", QueryPerforming(mode, action, t)))
        self._refresh_queries()

    def add_q_condition(self, mode):
        formula = FormulaDialog(self.root, self.fluents, f"{mode} γ", required=True).result
        if formula is None:
            return
        t = self._ask_int(f"{mode} γ", "Chwila t:", min_=0)
        if t is None:
            return
        self.queries.append((f"{mode} {format_formula(formula)} at {t}", QueryCondition(mode, formula, t)))
        self._refresh_queries()

    def del_query(self):
        sel = self.queries_list.curselection()
        if sel:
            del self.queries[sel[0]]
            self._refresh_queries()

    def _refresh_queries(self):
        self.queries_list.delete(0, 'end')
        for label, _ in self.queries:
            self.queries_list.insert('end', label)

    # ═══════════════════════════════════════════════════════════
    # EXAMPLES & CLEAR
    # ═══════════════════════════════════════════════════════════

    def clear_all(self):
        if not messagebox.askyesno("Wyczyść", "Usunąć cały stan?"):
            return
        self.fluents.clear()
        self.actions.clear()
        self.domain_items.clear()
        self.observations.clear()
        self.acs.clear()
        self.queries.clear()
        self.results_text.delete("1.0", "end")
        self._refresh_all()

    def _refresh_all(self):
        self._refresh_fluents()
        self._refresh_actions()
        self._refresh_domain()
        self._refresh_scenario()
        self._refresh_queries()

    # Mapowanie szybkich przyciskow #1..#5 -> plik w examples/
    EXAMPLE_FILES = {
        1: "projektor.txt",
        2: "serwerownia.txt",
        3: "bledny.txt",
        4: "smoke_wraca.txt",
        5: "precondition_z5.txt",
    }

    def load_example(self, n):
        """Wczytuje wbudowany przyklad #n z pliku examples/*.txt."""
        filename = self.EXAMPLE_FILES.get(n)
        if filename is None:
            messagebox.showerror("Blad", f"Nieznany przyklad #{n}")
            return
        path = os.path.join(EXAMPLES_DIR, filename)
        self._load_from_file(path)

    def load_custom_example(self):
        """Otwiera dialog wyboru pliku .txt i laduje go jako scenariusz."""
        path = filedialog.askopenfilename(
            title="Wybierz plik przykladu (.txt)",
            initialdir=EXAMPLES_DIR if os.path.isdir(EXAMPLES_DIR) else ".",
            filetypes=[("Pliki tekstowe DS1", "*.txt"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        self._load_from_file(path)

    def _load_from_file(self, path):
        """Wczytuje scenariusz z pliku .txt i wypelnia stan aplikacji."""
        if any([self.fluents, self.actions, self.domain_items,
                self.observations, self.acs, self.queries]):
            if not messagebox.askyesno("Wczytaj", "Nadpisać stan?"):
                return

        try:
            domain, scenario, queries = parse_file(path)
        except FileNotFoundError:
            messagebox.showerror("Blad", f"Nie znaleziono pliku:\n{path}")
            return
        except ParseError as e:
            messagebox.showerror(
                "Blad parsowania",
                f"Plik: {os.path.basename(path)}\n\n{e}",
            )
            return

        fluents, actions = derive_fluents_actions(domain, scenario, queries)

        # Wyczysc i wypelnij
        self.fluents.clear(); self.fluents.extend(fluents)
        self.actions.clear(); self.actions.extend(actions)
        self.domain_items.clear()
        self.domain_items.extend(domain.durations)
        self.domain_items.extend(domain.causes)
        self.domain_items.extend(domain.releases)
        self.domain_items.extend(domain.triggers)
        self.domain_items.extend(domain.state_triggers)
        self.domain_items.extend(domain.impossible_if)
        self.domain_items.extend(domain.impossible_at)
        self.observations.clear()
        self.observations.extend(scenario.observations)
        self.acs.clear()
        self.acs.extend(scenario.action_declarations)
        self.queries.clear()
        self.queries.extend(queries)

        self._refresh_all()
        # Tytul okna pokazuje aktualnie zaladowany plik
        self.root.title(f"DS1 — {os.path.basename(path)}")

    # ═══════════════════════════════════════════════════════════
    # SOLVE
    # ═══════════════════════════════════════════════════════════

    def build_domain(self):
        return Domain(
            durations=[s for s in self.domain_items if isinstance(s, DurationStatement)],
            causes=[s for s in self.domain_items if isinstance(s, CausesStatement)],
            releases=[s for s in self.domain_items if isinstance(s, ReleasesStatement)],
            triggers=[s for s in self.domain_items if isinstance(s, TriggersStatement)],
            state_triggers=[s for s in self.domain_items if isinstance(s, StateTriggerStatement)],
            impossible_if=[s for s in self.domain_items if isinstance(s, ImpossibleIfStatement)],
            impossible_at=[s for s in self.domain_items if isinstance(s, ImpossibleAtStatement)],
        )

    def build_scenario(self):
        return Scenario(observations=list(self.observations), action_declarations=list(self.acs))

    def solve_and_display(self):
        domain = self.build_domain()
        scenario = self.build_scenario()

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print("═" * 50)
            print("  DS1 — WYNIKI ANALIZY")
            print("═" * 50)
            print()
            print_domain(domain)
            print_scenario(scenario)

            if not print_validation(domain, scenario):
                print("\n❌ Scenariusz odrzucony — nie spełnia założeń DS1.")
            else:
                print("\n⏳ Generowanie modeli...")
                models = solve(domain, scenario, extra_times=query_times(self.queries))
                print(f"✅ Znaleziono {len(models)} model(i)\n")
                for i, m in enumerate(models):
                    print(f"{'─' * 40}")
                    print(f"  Model {i + 1}:")
                    print(f"{'─' * 40}")
                    print(format_model_table(m))
                print()
                print_queries(self.queries, models)

        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", buf.getvalue())


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def _pick_mono_font(root):
    """Wybiera pierwszy dostepny font monospace z listy preferencji.

    Dzieki temu tabele w wynikach zawsze beda mialy wyrownane kolumny
    niezaleznie od systemu (Cascadia nie wszedzie istnieje, Menlo jest
    domyslny na macOS, Consolas na Windows).
    """
    available = set(tkfont.families(root))
    candidates = (
        'Cascadia Code', 'JetBrains Mono', 'Fira Code',
        'Menlo', 'SF Mono', 'Monaco',
        'Consolas', 'Courier New', 'Courier',
    )
    for f in candidates:
        if f in available:
            return f
    return 'Courier'


def main():
    root = tk.Tk()
    current_scaling = float(root.tk.call('tk', 'scaling'))
    root.tk.call('tk', 'scaling', current_scaling * Theme.FONT_SCALE)

    # Wybierz prawdziwy monospace dostepny w systemie. Nadpisuje atrybut
    # klasowy Theme.FONT_MONO ZANIM widgety beda tworzone.
    Theme.FONT_MONO = _pick_mono_font(root)

    default_font = tkfont.nametofont('TkDefaultFont')
    default_font.configure(family=Theme.FONT_FAMILY, size=13)
    text_font = tkfont.nametofont('TkTextFont')
    text_font.configure(family=Theme.FONT_FAMILY, size=13)
    menu_font = tkfont.nametofont('TkMenuFont')
    menu_font.configure(family=Theme.FONT_FAMILY, size=13)
    fixed_font = tkfont.nametofont('TkFixedFont')
    fixed_font.configure(family=Theme.FONT_MONO, size=12)

    root.option_add('*Foreground', Theme.FG)
    root.option_add('*Label.Foreground', Theme.FG)
    root.option_add('*Button.Foreground', Theme.FG)
    root.option_add('*Checkbutton.Foreground', Theme.FG)
    root.option_add('*Radiobutton.Foreground', Theme.FG)
    root.option_add('*Entry.Foreground', Theme.FG)
    root.option_add('*Text.Foreground', Theme.FG)
    root.option_add('*Listbox.Foreground', Theme.FG)
    root.option_add('*TCombobox*Listbox.foreground', Theme.FG)
    root.option_add('*TCombobox*Listbox.background', Theme.SURFACE)
    root.option_add('*TCombobox*Listbox.selectForeground', Theme.FG)
    root.option_add('*TCombobox*Listbox.selectBackground', Theme.PRIMARY_DIM)
    
    # Configure ttk styles for comboboxes
    style = ttk.Style()
    style.theme_use('clam')
    style.configure(
        'TCombobox',
        fieldbackground=Theme.SURFACE,
        background=Theme.SURFACE,
        foreground=Theme.FG,
        arrowcolor=Theme.FG,
        bordercolor=Theme.BORDER,
        lightcolor=Theme.BORDER,
        darkcolor=Theme.BORDER,
        selectforeground=Theme.FG,
        selectbackground=Theme.PRIMARY_DIM,
        borderwidth=0,
    )
    style.map(
        'TCombobox',
        fieldbackground=[('readonly', Theme.SURFACE)],
        foreground=[('readonly', Theme.FG)],
        selectforeground=[('readonly', Theme.FG)],
        selectbackground=[('readonly', Theme.PRIMARY_DIM)],
        arrowcolor=[('readonly', Theme.FG)],
    )
    
    DS1App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
