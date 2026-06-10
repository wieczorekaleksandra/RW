"""GUI tkinter dla systemu DS1 — Scenariusze Dzialan.

Uruchom: python3 -m src.main --gui
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import io
import contextlib

# Styl kolorów
COLORS = {
    'bg': '#f0f0f0',
    'fg': '#333333',
    'primary': '#2E86AB',
    'accent': '#A23B72',
    'success': '#06A77D',
    'warning': '#F18F01',
    'error': '#C73E1D',
    'light_bg': '#ffffff',
    'border': '#cccccc',
}

from src.models import (
    Domain, Scenario, Observation, ActionDeclaration,
    CausesStatement, DurationStatement, ReleasesStatement,
    TriggersStatement, StateTriggerStatement,
    ImpossibleIfStatement, ImpossibleAtStatement,
    AtomicFormula, Negation, Conjunction,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)
from src.solver import solve
from src.validator import validate
from src.query_engine import execute_query
from src.examples.helpers import (
    format_formula, format_model_table,
    print_domain, print_scenario, print_validation, print_queries,
    query_times,
)


# ============================================================
# Pomocnicze: konstrukcja formul AND
# ============================================================

def _and_of_literals(literals):
    """Z listy par (fluent, is_positive) zwraca formule AND literalow."""
    if not literals:
        return None

    def lit(name, pos):
        a = AtomicFormula(name)
        return a if pos else Negation(a)

    formula = lit(*literals[0])
    for name, pos in literals[1:]:
        formula = Conjunction(formula, lit(name, pos))
    return formula


# ============================================================
# Dialog: zbuduj formule (AND literalow)
# ============================================================

class FormulaDialog(tk.Toplevel):
    """Dialog wyboru AND wybranych literalow.

    Dla kazdego fluentu wybierasz: True / False / Pomin.
    Wynik to AND wybranych literalow.
    """

    def __init__(self, parent, fluents, title="Zbuduj formule", required=True):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.configure(bg=COLORS['light_bg'])

        self.fluents = fluents
        self.required = required
        self.result = None
        self.choices = {}

        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)

        if not fluents:
            ttk.Label(
                body,
                text="Brak zdefiniowanych fluentow.\n"
                     "Dodaj fluenty w zakladce 'Fluenty i akcje'.",
                foreground=COLORS['error'],
                font=("", 10, "bold"),
            ).pack(pady=20)
            ttk.Button(body, text="OK", command=self.cancel).pack()
            self.wait_window()
            return

        ttk.Label(
            body,
            text="Wybierz wartosc kazdego fluentu (lub pomin):",
            font=("", 11, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))

        # Naglowki kolumn
        for col, text in enumerate(["Fluent", "True", "False", "Pomin"]):
            ttk.Label(body, text=text, font=("", 9, "bold")).grid(
                row=1, column=col, sticky="w" if col == 0 else "center",
                padx=8 if col == 0 else 4, pady=4
            )

        ttk.Separator(body, orient="horizontal").grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=6
        )

        for i, f in enumerate(fluents):
            var = tk.StringVar(value="skip")
            self.choices[f] = var
            ttk.Label(body, text=f, font=("", 9)).grid(
                row=3 + i, column=0, sticky="w", padx=8, pady=3
            )
            ttk.Radiobutton(body, variable=var, value="true").grid(row=3 + i, column=1, padx=4)
            ttk.Radiobutton(body, variable=var, value="false").grid(row=3 + i, column=2, padx=4)
            ttk.Radiobutton(body, variable=var, value="skip").grid(row=3 + i, column=3, padx=4)

        btns = ttk.Frame(self, padding=12)
        btns.pack(fill="x")
        ttk.Button(btns, text="✓ OK", command=self.ok).pack(side="right", padx=4)
        ttk.Button(btns, text="✗ Anuluj", command=self.cancel).pack(side="right", padx=4)

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
            messagebox.showerror(
                "Blad", "Wybierz co najmniej jeden literal.", parent=self
            )
            return

        self.result = _and_of_literals(literals)
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


# ============================================================
# Dialog: wybierz jeden literal (atom lub negacja)
# ============================================================

class LiteralDialog(tk.Toplevel):
    """Dialog wyboru pojedynczego literalu (atom albo negacja atomu)."""

    def __init__(self, parent, fluents, title="Wybierz literal"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.configure(bg=COLORS['light_bg'])

        self.result = None

        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)

        if not fluents:
            ttk.Label(
                body,
                text="Brak fluentow. Dodaj w zakladce 'Fluenty i akcje'.",
                foreground=COLORS['error'],
                font=("", 10, "bold"),
            ).pack(pady=20)
            ttk.Button(body, text="OK", command=self.cancel).pack()
            self.wait_window()
            return

        ttk.Label(body, text="Fluent:", font=("", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=6, pady=8
        )
        self.fluent_var = tk.StringVar(value=fluents[0])
        ttk.Combobox(
            body, textvariable=self.fluent_var, values=fluents, state="readonly", width=28,
            font=("", 10)
        ).grid(row=0, column=1, padx=6, pady=8)

        self.negated_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            body, text="Negacja (~)", variable=self.negated_var, font=("", 10)
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=8)

        btns = ttk.Frame(self, padding=12)
        btns.pack(fill="x")
        ttk.Button(btns, text="✓ OK", command=self.ok).pack(side="right", padx=4)
        ttk.Button(btns, text="✗ Anuluj", command=self.cancel).pack(side="right", padx=4)

        self.wait_window()

    def ok(self):
        f = self.fluent_var.get()
        atom = AtomicFormula(f)
        self.result = Negation(atom) if self.negated_var.get() else atom
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


# ============================================================
# Glowna aplikacja
# ============================================================

class DS1App:
    def __init__(self, root):
        self.root = root
        self.root.title("DS1 — Scenariusze Dzialan")
        self.root.geometry("1100x760")
        self.root.configure(bg=COLORS['bg'])

        # Stan: slownik (fluenty, akcje) + listy instrukcji
        self.fluents = []
        self.actions = []
        self.domain_items = []  # flat lista DurationStatement/CausesStatement/...
        self.observations = []  # lista Observation
        self.acs = []           # lista ActionDeclaration
        self.queries = []       # lista (label_string, query_obj)

        self._build_ui()

    # =============== Konstrukcja UI ===============

    def _build_ui(self):
        # Pasek narzedzi (gora)
        toolbar = ttk.Frame(self.root, padding=10)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(
            toolbar, text="📚 Wczytaj przyklad:", font=("", 10, "bold")
        ).pack(side="left", padx=(0, 8))
        
        examples = [
            (1, "📺 Projektor"),
            (2, "🏢 Serwerownia"),
            (3, "🐞 Bledny"),
            (4, "💨 Smoke wraca"),
            (5, "⚙️ Z5"),
        ]
        for n, name in examples:
            ttk.Button(
                toolbar, text=name,
                command=lambda nn=n: self.load_example(nn),
                width=12,
            ).pack(side="left", padx=2)

        ttk.Button(
            toolbar, text="🗑️ Wyczysc wszystko", command=self.clear_all
        ).pack(side="right", padx=2)

        # Glowne taby
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=4)

        self._build_setup_tab()
        self._build_domain_tab()
        self._build_scenario_tab()
        self._build_queries_tab()
        self._build_results_tab()

        # Dol: glowne przyciski
        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill="x", padx=8, pady=(4, 8))
        solve_btn = ttk.Button(
            bottom, text="▶ ROZWIAZ", command=self.solve_and_display, width=15
        )
        solve_btn.pack(side="right", padx=4)

    def _build_setup_tab(self):
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="1. Fluenty i akcje")

        ttk.Label(
            frame,
            text="Zdefiniuj fluenty (zmienne stanu) i akcje uzywane w dziedzinie.",
            font=("", 10, "italic"),
            foreground="#666666",
        ).pack(anchor="w", pady=(0, 10))

        cols = ttk.Frame(frame)
        cols.pack(fill="both", expand=True)

        # Lewa kolumna: fluenty
        left = ttk.LabelFrame(cols, text="📝 Fluenty", padding=10, labelanchor="n")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.fluents_listbox = tk.Listbox(
            left, height=14, font=("Courier", 10), bg=COLORS['light_bg'],
            activestyle='none', relief='solid', borderwidth=1
        )
        self.fluents_listbox.pack(fill="both", expand=True, pady=(0, 6))

        f_entry = ttk.Frame(left)
        f_entry.pack(fill="x")
        self.fluent_entry = ttk.Entry(f_entry, font=("", 10))
        self.fluent_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.fluent_entry.bind("<Return>", lambda e: self.add_fluent())
        ttk.Button(f_entry, text="➕ Dodaj", command=self.add_fluent, width=10).pack(side="left")
        ttk.Button(
            left, text="❌ Usun zaznaczony", command=self.del_fluent, width=20
        ).pack(fill="x", pady=(6, 0))

        # Prawa kolumna: akcje
        right = ttk.LabelFrame(cols, text="⚡ Akcje", padding=10, labelanchor="n")
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.actions_listbox = tk.Listbox(
            right, height=14, font=("Courier", 10), bg=COLORS['light_bg'],
            activestyle='none', relief='solid', borderwidth=1
        )
        self.actions_listbox.pack(fill="both", expand=True, pady=(0, 6))

        a_entry = ttk.Frame(right)
        a_entry.pack(fill="x")
        self.action_entry = ttk.Entry(a_entry, font=("", 10))
        self.action_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.action_entry.bind("<Return>", lambda e: self.add_action())
        ttk.Button(a_entry, text="➕ Dodaj", command=self.add_action, width=10).pack(side="left")
        ttk.Button(
            right, text="❌ Usun zaznaczona", command=self.del_action, width=20
        ).pack(fill="x", pady=(6, 0))

    def _build_domain_tab(self):
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="2. Dziedzina")

        ttk.Label(
            frame,
            text="Dodaj instrukcje opisu dziedziny.",
            font=("", 10, "italic"),
            foreground="#666666",
        ).pack(anchor="w", pady=(0, 10))

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(0, 10))

        domain_buttons = [
            ("⏱️ duration", self.add_duration),
            ("→ causes", self.add_causes),
            ("🔓 releases", self.add_releases),
            ("🔗 triggers", self.add_triggers),
            ("🎯 state trigger", self.add_state_trigger),
            ("🚫 impossible if", self.add_impossible_if),
            ("⛔ impossible at", self.add_impossible_at),
        ]
        for text, cmd in domain_buttons:
            ttk.Button(btns, text=text, command=cmd, width=14).pack(side="left", padx=2)

        # Lista instrukcji
        ttk.Label(frame, text="📋 Instrukcje dziedziny:", font=("", 10, "bold")).pack(
            anchor="w", pady=(8, 4)
        )
        self.domain_listbox = tk.Listbox(
            frame, height=14, font=("Courier", 9), bg=COLORS['light_bg'],
            activestyle='none', relief='solid', borderwidth=1
        )
        self.domain_listbox.pack(fill="both", expand=True)
        ttk.Button(
            frame, text="❌ Usun zaznaczona", command=self.del_domain_item
        ).pack(anchor="w", pady=(6, 0))

    def _build_scenario_tab(self):
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="3. Scenariusz")

        ttk.Label(
            frame,
            text="Obserwacje (OBS) i deklaracje akcji (ACS).",
            font=("", 10, "italic"),
            foreground="#666666",
        ).pack(anchor="w", pady=(0, 10))

        cols = ttk.Frame(frame)
        cols.pack(fill="both", expand=True)

        # OBS
        left = ttk.LabelFrame(cols, text="👁️ Obserwacje (OBS)", padding=10, labelanchor="n")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.obs_listbox = tk.Listbox(
            left, height=12, font=("Courier", 9), bg=COLORS['light_bg'],
            activestyle='none', relief='solid', borderwidth=1
        )
        self.obs_listbox.pack(fill="both", expand=True, pady=(0, 6))
        obs_btns = ttk.Frame(left)
        obs_btns.pack(fill="x")
        ttk.Button(obs_btns, text="➕ Obserwacja", command=self.add_obs, width=14).pack(side="left")
        ttk.Button(
            obs_btns, text="❌ Usun", command=self.del_obs, width=12
        ).pack(side="left", padx=4)

        # ACS
        right = ttk.LabelFrame(cols, text="🎬 Akcje (ACS)", padding=10, labelanchor="n")
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.acs_listbox = tk.Listbox(
            right, height=12, font=("Courier", 9), bg=COLORS['light_bg'],
            activestyle='none', relief='solid', borderwidth=1
        )
        self.acs_listbox.pack(fill="both", expand=True, pady=(0, 6))
        acs_btns = ttk.Frame(right)
        acs_btns.pack(fill="x")
        ttk.Button(
            acs_btns, text="➕ Deklaracja", command=self.add_acs, width=14
        ).pack(side="left")
        ttk.Button(
            acs_btns, text="❌ Usun", command=self.del_acs, width=12
        ).pack(side="left", padx=4)

    def _build_queries_tab(self):
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="4. Kwerendy")

        ttk.Label(
            frame,
            text="Dodaj kwerendy ktore beda wykonane po wygenerowaniu modeli.",
            font=("", 10, "italic"),
            foreground="#666666",
        ).pack(anchor="w", pady=(0, 10))

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(0, 10))

        ttk.Button(btns, text="🤔 possibly Sc", command=self.add_q_possibly_sc, width=14).pack(
            side="left", padx=2
        )
        ttk.Button(
            btns, text="⚙️ nec. performing", 
            command=lambda: self.add_q_performing("necessary"), width=14
        ).pack(side="left", padx=2)
        ttk.Button(
            btns, text="🤔 poss. performing",
            command=lambda: self.add_q_performing("possibly"), width=14
        ).pack(side="left", padx=2)
        ttk.Button(
            btns, text="⚙️ nec. γ", command=lambda: self.add_q_condition("necessary"), width=10
        ).pack(side="left", padx=2)
        ttk.Button(
            btns, text="🤔 poss. γ", command=lambda: self.add_q_condition("possibly"), width=10
        ).pack(side="left", padx=2)

        ttk.Label(frame, text="📌 Kwerendy:", font=("", 10, "bold")).pack(anchor="w", pady=(8, 4))
        self.queries_listbox = tk.Listbox(
            frame, height=14, font=("Courier", 9), bg=COLORS['light_bg'],
            activestyle='none', relief='solid', borderwidth=1
        )
        self.queries_listbox.pack(fill="both", expand=True)
        ttk.Button(
            frame, text="❌ Usun zaznaczona", command=self.del_query
        ).pack(anchor="w", pady=(6, 0))

    def _build_results_tab(self):
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="5. Wyniki")

        ttk.Label(
            frame,
            text="Wynik dzialania: walidacja, modele, odpowiedzi na kwerendy.",
            font=("", 10, "italic"),
            foreground="#666666",
        ).pack(anchor="w", pady=(0, 10))

        self.results_text = scrolledtext.ScrolledText(
            frame, font=("Courier", 10), wrap="none", bg=COLORS['light_bg'],
            relief='solid', borderwidth=1
        )
        self.results_text.pack(fill="both", expand=True)

    # =============== Fluenty i akcje ===============

    def add_fluent(self):
        name = self.fluent_entry.get().strip()
        if not name:
            return
        if name in self.fluents:
            messagebox.showerror("Blad", f"Fluent '{name}' juz istnieje.")
            return
        self.fluents.append(name)
        self.fluent_entry.delete(0, "end")
        self._refresh_fluents()

    def del_fluent(self):
        sel = self.fluents_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.fluents[idx]
        self._refresh_fluents()

    def add_action(self):
        name = self.action_entry.get().strip()
        if not name:
            return
        if name in self.actions:
            messagebox.showerror("Blad", f"Akcja '{name}' juz istnieje.")
            return
        self.actions.append(name)
        self.action_entry.delete(0, "end")
        self._refresh_actions()

    def del_action(self):
        sel = self.actions_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.actions[idx]
        self._refresh_actions()

    def _refresh_fluents(self):
        self.fluents_listbox.delete(0, "end")
        for f in self.fluents:
            self.fluents_listbox.insert("end", f)

    def _refresh_actions(self):
        self.actions_listbox.delete(0, "end")
        for a in self.actions:
            self.actions_listbox.insert("end", a)

    # =============== Dziedzina ===============

    def _ask_action(self, title):
        """Mini-dialog wyboru akcji z dropdownu."""
        if not self.actions:
            messagebox.showerror(
                "Blad", "Brak zdefiniowanych akcji. Dodaj w zakladce 1."
            )
            return None
        return self._ask_choice(title, "Akcja:", self.actions)

    def _ask_fluent(self, title):
        if not self.fluents:
            messagebox.showerror(
                "Blad", "Brak zdefiniowanych fluentow. Dodaj w zakladce 1."
            )
            return None
        return self._ask_choice(title, "Fluent:", self.fluents)

    def _ask_int(self, title, prompt, min_=0):
        v = simpledialog.askinteger(title, prompt, parent=self.root, minvalue=min_)
        return v

    def _ask_choice(self, title, prompt, choices):
        """Mini-dialog z dropdownem wyboru z listy."""
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.configure(bg=COLORS['light_bg'])
        
        ttk.Label(
            dlg, text=prompt, padding=10, font=("", 10, "bold")
        ).pack()
        var = tk.StringVar(value=choices[0])
        ttk.Combobox(
            dlg, textvariable=var, values=choices, state="readonly", width=30,
            font=("", 10)
        ).pack(padx=12, pady=8)
        result = [None]

        def ok():
            result[0] = var.get()
            dlg.destroy()

        btns = ttk.Frame(dlg, padding=10)
        btns.pack()
        ttk.Button(btns, text="✓ OK", command=ok, width=10).pack(side="left", padx=4)
        ttk.Button(btns, text="✗ Anuluj", command=dlg.destroy, width=10).pack(side="left", padx=4)
        dlg.wait_window()
        return result[0]

    def add_duration(self):
        action = self._ask_action("duration")
        if not action:
            return
        n = self._ask_int("duration", f"Czas trwania akcji '{action}' (>= 1):", min_=1)
        if n is None:
            return
        self.domain_items.append(DurationStatement(action, n))
        self._refresh_domain()

    def add_causes(self):
        action = self._ask_action("causes — akcja")
        if not action:
            return
        effect = LiteralDialog(
            self.root, self.fluents, "causes — efekt (literal)"
        ).result
        if effect is None:
            return
        delay = self._ask_int("causes", "Opoznienie δ (>= 1):", min_=1)
        if delay is None:
            return
        # Opcjonalny warunek
        add_cond = messagebox.askyesno(
            "causes — warunek",
            "Dodac warunek 'if π' do tej reguly?\n\n"
            "Tak: zbuduj formule (AND literalow)\n"
            "Nie: regula bezwarunkowa",
        )
        condition = None
        if add_cond:
            condition = FormulaDialog(
                self.root, self.fluents, "causes — warunek π", required=True
            ).result
            if condition is None:
                return
        self.domain_items.append(CausesStatement(action, effect, delay, condition))
        self._refresh_domain()

    def add_releases(self):
        action = self._ask_action("releases — akcja")
        if not action:
            return
        fluent = self._ask_fluent("releases — fluent")
        if not fluent:
            return
        a = self._ask_int("releases", "Poczatek przedzialu okluzji:", min_=0)
        if a is None:
            return
        b = self._ask_int("releases", "Koniec przedzialu okluzji:", min_=0)
        if b is None:
            return
        if b < a:
            messagebox.showerror("Blad", "Koniec przedzialu musi byc >= poczatek.")
            return
        self.domain_items.append(ReleasesStatement(action, fluent, a, b))
        self._refresh_domain()

    def add_triggers(self):
        cause = self._ask_action("triggers — akcja wyzwalajaca")
        if not cause:
            return
        triggered = self._ask_action("triggers — akcja wyzwalana")
        if not triggered:
            return
        delay = self._ask_int("triggers", "Opoznienie δ (>= 0):", min_=0)
        if delay is None:
            return
        self.domain_items.append(TriggersStatement(cause, triggered, delay))
        self._refresh_domain()

    def add_state_trigger(self):
        condition = FormulaDialog(
            self.root, self.fluents, "state trigger — warunek α", required=True
        ).result
        if condition is None:
            return
        action = self._ask_action("state trigger — akcja")
        if not action:
            return
        self.domain_items.append(StateTriggerStatement(condition, action))
        self._refresh_domain()

    def add_impossible_if(self):
        action = self._ask_action("impossible if — akcja")
        if not action:
            return
        condition = FormulaDialog(
            self.root, self.fluents, "impossible if — warunek α", required=True
        ).result
        if condition is None:
            return
        self.domain_items.append(ImpossibleIfStatement(action, condition))
        self._refresh_domain()

    def add_impossible_at(self):
        action = self._ask_action("impossible at — akcja")
        if not action:
            return
        t = self._ask_int("impossible at", "Punkt czasowy t:", min_=0)
        if t is None:
            return
        self.domain_items.append(ImpossibleAtStatement(action, t))
        self._refresh_domain()

    def del_domain_item(self):
        sel = self.domain_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.domain_items[idx]
        self._refresh_domain()

    def _refresh_domain(self):
        self.domain_listbox.delete(0, "end")
        for s in self.domain_items:
            self.domain_listbox.insert("end", self._format_domain_item(s))

    def _format_domain_item(self, s):
        if isinstance(s, DurationStatement):
            return f"{s.action} duration {s.duration}"
        if isinstance(s, CausesStatement):
            cond = f" if {format_formula(s.condition)}" if s.condition else ""
            return f"{s.action} causes {format_formula(s.effect)} after {s.delay}{cond}"
        if isinstance(s, ReleasesStatement):
            return f"{s.action} releases {s.fluent} during [{s.interval_start},{s.interval_end}]"
        if isinstance(s, TriggersStatement):
            return f"{s.cause_action} triggers {s.triggered_action} after {s.delay}"
        if isinstance(s, StateTriggerStatement):
            return f"{format_formula(s.condition)} causes {s.action}"
        if isinstance(s, ImpossibleIfStatement):
            return f"impossible {s.action} if {format_formula(s.condition)}"
        if isinstance(s, ImpossibleAtStatement):
            return f"impossible {s.action} at {s.time_point}"
        return repr(s)

    # =============== Scenariusz ===============

    def add_obs(self):
        formula = FormulaDialog(
            self.root, self.fluents, "OBS — formula obserwacji", required=True
        ).result
        if formula is None:
            return
        t = self._ask_int("OBS", "Chwila czasu t:", min_=0)
        if t is None:
            return
        self.observations.append(Observation(formula, t))
        self._refresh_scenario()

    def del_obs(self):
        sel = self.obs_listbox.curselection()
        if not sel:
            return
        del self.observations[sel[0]]
        self._refresh_scenario()

    def add_acs(self):
        action = self._ask_action("ACS — akcja")
        if not action:
            return
        t = self._ask_int("ACS", "Chwila startu t:", min_=0)
        if t is None:
            return
        self.acs.append(ActionDeclaration(action, t))
        self._refresh_scenario()

    def del_acs(self):
        sel = self.acs_listbox.curselection()
        if not sel:
            return
        del self.acs[sel[0]]
        self._refresh_scenario()

    def _refresh_scenario(self):
        self.obs_listbox.delete(0, "end")
        for obs in self.observations:
            self.obs_listbox.insert(
                "end", f"({format_formula(obs.formula)}, {obs.time})"
            )
        self.acs_listbox.delete(0, "end")
        for ad in self.acs:
            self.acs_listbox.insert("end", f"({ad.action}, {ad.time})")

    # =============== Kwerendy ===============

    def add_q_possibly_sc(self):
        self.queries.append(("possibly Sc", QueryPossiblyScenario()))
        self._refresh_queries()

    def add_q_performing(self, mode):
        action = self._ask_action(f"{mode} performing — akcja")
        if not action:
            return
        t = self._ask_int(f"{mode} performing", "Chwila t:", min_=0)
        if t is None:
            return
        label = f"{mode} performing {action} at {t} when Sc"
        self.queries.append((label, QueryPerforming(mode, action, t)))
        self._refresh_queries()

    def add_q_condition(self, mode):
        formula = FormulaDialog(
            self.root, self.fluents, f"{mode} γ — formula", required=True
        ).result
        if formula is None:
            return
        t = self._ask_int(f"{mode} γ", "Chwila t:", min_=0)
        if t is None:
            return
        label = f"{mode} {format_formula(formula)} at {t} when Sc"
        self.queries.append((label, QueryCondition(mode, formula, t)))
        self._refresh_queries()

    def del_query(self):
        sel = self.queries_listbox.curselection()
        if not sel:
            return
        del self.queries[sel[0]]
        self._refresh_queries()

    def _refresh_queries(self):
        self.queries_listbox.delete(0, "end")
        for label, _ in self.queries:
            self.queries_listbox.insert("end", label)

    # =============== Wyczysc / Wczytaj przyklad ===============

    def clear_all(self):
        if not messagebox.askyesno(
            "Wyczyscic", "Usunac caly stan (fluenty, akcje, dziedzine, scenariusz, kwerendy)?"
        ):
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

    def load_example(self, n):
        if any([
            self.fluents, self.actions, self.domain_items,
            self.observations, self.acs, self.queries,
        ]):
            if not messagebox.askyesno(
                "Wczytaj przyklad",
                "Aktualny stan zostanie nadpisany. Kontynuowac?",
            ):
                return

        self.fluents.clear()
        self.actions.clear()
        self.domain_items.clear()
        self.observations.clear()
        self.acs.clear()
        self.queries.clear()

        loaders = {
            1: self._load_projektor,
            2: self._load_serwerownia,
            3: self._load_bledny,
            4: self._load_smoke_wraca,
            5: self._load_z5,
        }
        loaders[n]()
        self._refresh_all()
        self.notebook.select(1)  # przejdz na zakladke "Dziedzina"

    def _load_projektor(self):
        self.fluents = ["projector_on"]
        self.actions = ["press_power"]
        self.domain_items = [
            DurationStatement("press_power", 1),
            ReleasesStatement("press_power", "projector_on", 0, 1),
            ImpossibleIfStatement("press_power", AtomicFormula("projector_on")),
        ]
        self.observations = [Observation(Negation(AtomicFormula("projector_on")), 0)]
        self.acs = [ActionDeclaration("press_power", 0)]
        self.queries = [
            ("possibly Sc", QueryPossiblyScenario()),
            ("necessary performing press_power at 0 when Sc",
             QueryPerforming("necessary", "press_power", 0)),
            ("necessary performing press_power at 1 when Sc",
             QueryPerforming("necessary", "press_power", 1)),
            ("necessary projector_on at 2 when Sc",
             QueryCondition("necessary", AtomicFormula("projector_on"), 2)),
            ("possibly projector_on at 2 when Sc",
             QueryCondition("possibly", AtomicFormula("projector_on"), 2)),
        ]

    def _load_serwerownia(self):
        self.fluents = ["smoke", "maintenance", "alarm_on", "ventilation_on"]
        self.actions = ["activate_alarm", "start_ventilation"]
        self.domain_items = [
            DurationStatement("activate_alarm", 1),
            DurationStatement("start_ventilation", 2),
            CausesStatement("activate_alarm", AtomicFormula("alarm_on"), 1,
                            AtomicFormula("smoke")),
            CausesStatement("start_ventilation", AtomicFormula("ventilation_on"), 2,
                            AtomicFormula("alarm_on")),
            ReleasesStatement("start_ventilation", "ventilation_on", 0, 2),
            TriggersStatement("activate_alarm", "start_ventilation", 1),
            StateTriggerStatement(AtomicFormula("smoke"), "activate_alarm"),
            ImpossibleIfStatement("activate_alarm", AtomicFormula("maintenance")),
        ]
        obs = Conjunction(
            Conjunction(
                Conjunction(
                    AtomicFormula("smoke"),
                    Negation(AtomicFormula("maintenance")),
                ),
                Negation(AtomicFormula("alarm_on")),
            ),
            Negation(AtomicFormula("ventilation_on")),
        )
        self.observations = [Observation(obs, 0)]
        self.acs = []
        self.queries = [
            ("possibly Sc", QueryPossiblyScenario()),
            ("necessary performing activate_alarm at 0 when Sc",
             QueryPerforming("necessary", "activate_alarm", 0)),
            ("necessary alarm_on at 1 when Sc",
             QueryCondition("necessary", AtomicFormula("alarm_on"), 1)),
            ("necessary performing start_ventilation at 2 when Sc",
             QueryPerforming("necessary", "start_ventilation", 2)),
            ("necessary ventilation_on at 4 when Sc",
             QueryCondition("necessary", AtomicFormula("ventilation_on"), 4)),
        ]

    def _load_bledny(self):
        self.fluents = ["broken", "system_on"]
        self.actions = ["repair", "reboot"]
        self.domain_items = [
            DurationStatement("repair", 3),
            DurationStatement("reboot", 2),
            CausesStatement("reboot", AtomicFormula("system_on"), 2,
                            Negation(AtomicFormula("broken"))),
            ImpossibleAtStatement("reboot", 0),
        ]
        self.observations = [
            Observation(AtomicFormula("broken"), 0),
            Observation(Negation(AtomicFormula("broken")), 0),
        ]
        self.acs = [
            ActionDeclaration("repair", 0),
            ActionDeclaration("reboot", 1),
            ActionDeclaration("reboot", 0),
        ]
        self.queries = []

    def _load_smoke_wraca(self):
        self.fluents = ["smoke", "alarm_on"]
        self.actions = ["activate_alarm"]
        self.domain_items = [
            DurationStatement("activate_alarm", 1),
            CausesStatement("activate_alarm", AtomicFormula("alarm_on"), 1,
                            AtomicFormula("smoke")),
            StateTriggerStatement(AtomicFormula("smoke"), "activate_alarm"),
        ]
        self.observations = [
            Observation(
                Conjunction(
                    AtomicFormula("smoke"),
                    Negation(AtomicFormula("alarm_on")),
                ),
                0,
            ),
            Observation(Negation(AtomicFormula("smoke")), 2),
            Observation(AtomicFormula("smoke"), 4),
        ]
        self.acs = []
        self.queries = [
            ("possibly Sc", QueryPossiblyScenario()),
            ("necessary performing activate_alarm at 0 when Sc",
             QueryPerforming("necessary", "activate_alarm", 0)),
            ("possibly performing activate_alarm at 2 when Sc",
             QueryPerforming("possibly", "activate_alarm", 2)),
            ("necessary performing activate_alarm at 4 when Sc",
             QueryPerforming("necessary", "activate_alarm", 4)),
            ("necessary alarm_on at 1 when Sc",
             QueryCondition("necessary", AtomicFormula("alarm_on"), 1)),
            ("necessary alarm_on at 5 when Sc",
             QueryCondition("necessary", AtomicFormula("alarm_on"), 5)),
        ]

    def _load_z5(self):
        self.fluents = ["broken", "system_on"]
        self.actions = ["reboot", "repair"]
        self.domain_items = [
            DurationStatement("reboot", 2),
            DurationStatement("repair", 3),
            CausesStatement("reboot", AtomicFormula("system_on"), 2,
                            Negation(AtomicFormula("broken"))),
            CausesStatement("repair", Negation(AtomicFormula("broken")), 3, None),
        ]
        self.observations = [Observation(AtomicFormula("broken"), 0)]
        self.acs = [ActionDeclaration("reboot", 0)]
        self.queries = [
            ("possibly Sc", QueryPossiblyScenario()),
            ("possibly performing reboot at 0 when Sc",
             QueryPerforming("possibly", "reboot", 0)),
            ("possibly system_on at 2 when Sc",
             QueryCondition("possibly", AtomicFormula("system_on"), 2)),
        ]

    # =============== Rozwiazywanie ===============

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
        return Scenario(
            observations=list(self.observations),
            action_declarations=list(self.acs),
        )

    def solve_and_display(self):
        domain = self.build_domain()
        scenario = self.build_scenario()

        # Przekieruj stdout do bufora — uzywamy istniejacych helperow drukujacych
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_domain(domain)
            print_scenario(scenario)

            if not print_validation(domain, scenario):
                print("\nScenariusz odrzucony — nie spelnia zalozen DS1.")
            else:
                print("\nGenerowanie modeli...")
                models = solve(domain, scenario, extra_times=query_times(self.queries))
                print(f"  Znaleziono {len(models)} model(i)")

                for i, m in enumerate(models):
                    print(f"\n  Model {i + 1}:")
                    print(format_model_table(m))

                print_queries(self.queries, models)

        # Wyswietl w panelu wynikow
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", buf.getvalue())
        # Przelacz na zakladke Wyniki
        self.notebook.select(4)


# ============================================================
# Entry point
# ============================================================

def main():
    root = tk.Tk()
    DS1App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
