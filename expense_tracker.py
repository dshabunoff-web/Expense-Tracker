import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import json
import os

# ---------- Модели данных ---------- #

class Expense:
    def __init__(self, amount: float, category: str, date_str: str, note: str = ""):
        self.amount = float(amount)
        self.category = category
        # date_str в формате YYYY-MM-DD
        self.date = date.fromisoformat(date_str)
        self.note = note

    def to_dict(self):
        return {
            "amount": self.amount,
            "category": self.category,
            "date": self.date.isoformat(),
            "note": self.note
        }

    @staticmethod
    def from_dict(d):
        return Expense(d["amount"], d["category"], d["date"], d.get("note", ""))

# ---------- Приложение ---------- #

class ExpenseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Expense Tracker")
        self.root.geometry("900x600")

        self.expenses = []  # список Expense
        self.filtered_expenses = []  # текущий результат фильтрации

        self._setup_ui()
        self._load_sample_data_if_empty()

    def _setup_ui(self):
        # Левой панели: фильтры
        left_frame = ttk.Frame(self.root, padding=(10, 10))
        left_frame.pack(side="left", fill="y")

        # Категории
        ttk.Label(left_frame, text="Фильтры:", font=("Segoe UI", 12, "bold")).pack(anchor="nw", pady=(0,6))

        ttk.Label(left_frame, text="Категория:").pack(anchor="nw")
        self.category_var = tk.StringVar(value="Все")
        self.category_cb = ttk.Combobox(left_frame, textvariable=self.category_var, state="readonly")
        self.category_cb['values'] = ["Все", "Продукты", "Транспорт", "Развлечения", "Жилье", "Здоровье", "Другое"]
        self.category_cb.current(0)
        self.category_cb.pack(fill="x", pady=2)
        self.category_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Label(left_frame, text="Начальная дата (YYYY-MM-DD):").pack(anchor="nw", pady=(6,0))
        self.start_date_var = tk.StringVar()
        self.start_entry = ttk.Entry(left_frame, textvariable=self.start_date_var)
        self.start_entry.pack(fill="x", pady=2)

        ttk.Label(left_frame, text="Конечная дата (YYYY-MM-DD):").pack(anchor="nw", pady=(6,0))
        self.end_date_var = tk.StringVar()
        self.end_entry = ttk.Entry(left_frame, textvariable=self.end_date_var)
        self.end_entry.pack(fill="x", pady=2)

        # Кнопки фильтрации
        ttk.Button(left_frame, text="Применить фильтр", command=self.apply_filters).pack(fill="x", pady=(12,6))
        ttk.Button(left_frame, text="Сбросить фильтры", command=self.reset_filters).pack(fill="x")

        # Специальная кнопка для импорта/экспорта
        ttk.Separator(left_frame, orient="horizontal").pack(fill="x", pady=12)
        ttk.Label(left_frame, text="JSON-спорт/импорт:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0,4))
        ttk.Button(left_frame, text="Экспорт в JSON", command=self.export_json).pack(fill="x", pady=2)
        ttk.Button(left_frame, text="Импорт из JSON", command=self.import_json).pack(fill="x", pady=2)

        # Правая часть: список и статистика
        right_frame = ttk.Frame(self.root, padding=(10,10))
        right_frame.pack(side="left", fill="both", expand=True)

        # Список расходов
        columns = ("date", "category", "amount", "note")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("date", text="Дата")
        self.tree.heading("category", text="Категория")
        self.tree.heading("amount", text="Сумма")
        self.tree.heading("note", text="Примечание")
        self.tree.column("date", width=100)
        self.tree.column("category", width=120)
        self.tree.column("amount", width=100, anchor="e")
        self.tree.column("note", width=350)
        self.tree.pack(fill="both", expand=True)

        # Панель добавления нового расхода
        add_frame = ttk.Frame(right_frame, padding=(6,6))
        add_frame.pack(fill="x", pady=(8,0))

        ttk.Label(add_frame, text="Добавить расход").grid(row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(add_frame, text="Сумма:").grid(row=1, column=0, sticky="e")
        self.amount_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.amount_var, width=15).grid(row=1, column=1, sticky="w")

        ttk.Label(add_frame, text="Категория:").grid(row=1, column=2, sticky="e")
        self.add_category_var = tk.StringVar(value="Продукты")
        self.add_category_cb = ttk.Combobox(add_frame, textvariable=self.add_category_var, state="readonly")
        self.add_category_cb['values'] = ["Продукты", "Транспорт", "Развлечения", "Жилье", "Здоровье", "Другое"]
        self.add_category_cb.grid(row=1, column=3, sticky="w")
        self.add_category_cb.current(0)

        ttk.Label(add_frame, text="Дата (YYYY-MM-DD):").grid(row=2, column=0, sticky="e")
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(add_frame, textvariable=self.date_var, width=15).grid(row=2, column=1, sticky="w")

        ttk.Label(add_frame, text="Заметка:").grid(row=2, column=2, sticky="e")
        self.note_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.note_var, width=40).grid(row=2, column=3, sticky="w")

        ttk.Button(add_frame, text="Добавить", command=self.add_expense).grid(row=3, column=0, columnspan=4, pady=(6,0))

        # Подсчёт суммы за период
        summary_frame = ttk.Frame(right_frame, padding=(6,6))
        summary_frame.pack(fill="x", pady=(8,0))
        self.summary_var = tk.StringVar(value="Итого за период: 0.00")
        ttk.Label(summary_frame, textvariable=self.summary_var, font=("Segoe UI", 12, "bold")).pack(anchor="w")

        # Меню
        self._setup_menu()

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Сохранить как...", command=self.export_json)
        filemenu.add_command(label="Импорт из JSON", command=self.import_json)
        filemenu.add_separator()
        filemenu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="О программе", command=self._show_about)
        menubar.add_cascade(label="Справка", menu=helpmenu)

    def _show_about(self):
        messagebox.showinfo("О программе", "Expense Tracker\nПростой трекер расходов с фильтрацией и JSON-экспортом.")

    def _load_sample_data_if_empty(self):
        if not self.expenses:
            sample = [
                Expense(12.5, "Продукты", date.today().isoformat(), "молоко"),
                Expense(3.75, "Прочее", date.today().isoformat(), "газета"),
                Expense(50.0, "Транспорт", date.today().isoformat(), "автобус"),
            ]
            self.expenses.extend(sample)
        self.refresh_table()
        self.apply_filters()

    # ---------- Функции работы с данными ---------- #

    def add_expense(self):
        try:
            amount = float(self.amount_var.get())
            category = self.add_category_var.get()
            date_str = self.date_var.get()
            # валидация даты
            datetime.fromisoformat(date_str)
            note = self.note_var.get()
        except Exception as e:
            messagebox.showerror("Ошибка ввода", f"Неправильные данные: {e}")
            return

        exp = Expense(amount, category, date_str, note)
        self.expenses.append(exp)
        self.clear_add_form()
        self.refresh_table()
        self.apply_filters()

    def clear_add_form(self):
        self.amount_var.set("")
        self.date_var.set(date.today().isoformat())
        self.note_var.set("")

    def refresh_table(self):
        # очистить
        for row in self.tree.get_children():
            self.tree.delete(row)
        # заполнить
        for exp in self.expenses:
            self.tree.insert("", "end", values=(
                exp.date.isoformat(),
                exp.category,
                f"{exp.amount:.2f}",
                exp.note
            ))

    def apply_filters(self):
        cat = self.category_var.get()
        start = self.start_date_var.get()
        end = self.end_date_var.get()

        sdate = None
        edate = None
        if start:
            try:
                sdate = date.fromisoformat(start)
            except ValueError:
                messagebox.showerror("Ошибка", "Начальная дата должна быть в формате YYYY-MM-DD")
                return
        if end:
            try:
                edate = date.fromisoformat(end)
            except ValueError:
                messagebox.showerror("Ошибка", "Конечная дата должна быть в формате YYYY-MM-DD")
                return

        self.filtered_expenses = []
        for exp in self.expenses:
            if cat != "Все" and exp.category != cat:
                continue
            if sdate and exp.date < sdate:
                continue
            if edate and exp.date > edate:
                continue
            self.filtered_expenses.append(exp)

        # обновить таблицу с отбросами
        self._refresh_table_with_filtered()
        self._update_summary()

    def _refresh_table_with_filtered(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for exp in self.filtered_expenses:
            self.tree.insert("", "end", values=(
                exp.date.isoformat(),
                exp.category,
                f"{exp.amount:.2f}",
                exp.note
            ))

    def reset_filters(self):
        self.category_var.set("Все")
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.apply_filters()

    def _update_summary(self):
        total = sum(exp.amount for exp in self.filtered_expenses)
        self.summary_var.set(f"Итого за период: {total:.2f}")

    # ---------- JSON- импорт/экспорт ---------- #

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON files", "*.json")])
        if not path:
            return
        data = [exp.to_dict() for exp in self.expenses]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Успех", "Данные экспортированы в JSON.")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON должен содержать список объектов")
            self.expenses = [Expense.from_dict(d) for d in data]
            self.refresh_table()
            self.apply_filters()
            messagebox.showinfo("Успех", "Данные импортированы из JSON.")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

# ---------- запуск ---------- #

def main():
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()