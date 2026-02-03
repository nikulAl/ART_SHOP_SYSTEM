import sys, sqlite3
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

DB = "shop.db"

STYLE = """
QMainWindow { background: #121212; color: white; }

QWidget#card {
    background: #1e1e1e;
    border-radius: 14px;
    padding: 15px;
}

QPushButton {
    background: #4f46e5;
    color: white;
    border-radius: 10px;
    padding: 10px;
    font-size: 14px;
}

QPushButton:hover {
    background: #4338ca;
}

QPushButton:disabled {
    background: #333;
    color: #888;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QComboBox, QDateEdit {
    border: 1px solid #333;
    border-radius: 8px;
    padding: 6px;
    background: #2c2c2c;
    color: white;
}

QTableWidget {
    background: #1e1e1e;
    color: white;
    border-radius: 10px;
    gridline-color: #333;
}

QHeaderView::section {
    background: #2c2c2c;
    padding: 6px;
    border: none;
    font-weight: bold;
    color: white;
}

QLabel {
    color: white;
}

QComboBox QAbstractItemView {
    background: #2c2c2c;
    color: white;
    selection-background-color: #4f46e5;
}

QTableWidget QTableCornerButton::section {
    background: #2c2c2c;
    border: none;
}

/* Стили для боковой панели */
QWidget#sidebar {
    background: #1a1a1a;
    border-right: 1px solid #333;
}

QPushButton#navButton {
    background: transparent;
    color: #ccc;
    text-align: left;
    padding: 15px 20px;
    border-radius: 0;
    border: none;
    border-left: 4px solid transparent;
}

QPushButton#navButton:hover {
    background: #2a2a2a;
    color: white;
}

QPushButton#navButton.active {
    background: #2a2a2a;
    color: #4f46e5;
    border-left: 4px solid #4f46e5;
    font-weight: bold;
}
"""

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB)
        self.init()

    def init(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            quantity INTEGER,
            price REAL,
            article TEXT UNIQUE,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY,
            product_id INTEGER,
            quantity INTEGER,
            order_date TEXT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY,
            product_id INTEGER,
            quantity INTEGER,
            sale_date TEXT,
            price REAL
        );
        """)
        self.conn.commit()
        self.seed()

    def seed(self):
        c = self.conn.cursor()
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
            return

        cats = ["Краски", "Кисти", "Холсты", "Бумага", "Мольберты"]
        for cat in cats:
            c.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (cat,))

        data = [
            ("Краски 12цв", "Краски", 10, 1200, "ART001", "Набор масляных красок"),
            ("Кисть №5", "Кисти", 20, 450, "ART002", "Беличий ворс"),
            ("Холст 40x50", "Холсты", 5, 900, "ART003", "Хлопковый холст"),
        ]

        for p in data:
            c.execute("""
            INSERT INTO products(name,category,quantity,price,article,description)
            VALUES(?,?,?,?,?,?)
            """, p)

        self.conn.commit()

    def fetch(self, q, a=()):
        return self.conn.cursor().execute(q, a).fetchall()

    def exec(self, q, a=()):
        self.conn.cursor().execute(q, a)
        self.conn.commit()

    def products(self, key=""):
        if not key:
            return self.fetch("SELECT * FROM products ORDER BY id")
        k = f"%{key}%"
        return self.fetch("""
        SELECT * FROM products WHERE
        name LIKE ? OR article LIKE ? OR category LIKE ? OR description LIKE ?
        """, (k, k, k, k))

    def available_products(self):
        return self.fetch("SELECT * FROM products WHERE quantity > 0 ORDER BY name")

    def product_by_id(self, pid):
        result = self.fetch("SELECT * FROM products WHERE id=?", (pid,))
        return result[0] if result else None

    def add_product(self, d):
        self.exec("""
        INSERT INTO products(name,article,category,quantity,price,description)
        VALUES(?,?,?,?,?,?)
        """, d)

    def update_product(self, pid, d):
        self.exec("""
        UPDATE products SET
        name=?, article=?, category=?, quantity=?, price=?, description=?
        WHERE id=?
        """, (*d, pid))

    def delete_product(self, pid):
        self.exec("DELETE FROM products WHERE id=?", (pid,))

    def add_order(self, pid, qty):
        product = self.product_by_id(pid)
        if not product:
            raise ValueError("Товар не найден")
        
        if qty > product[3]:
            raise ValueError(f"Недостаточно товара. Доступно: {product[3]}")
        
        date = datetime.now().strftime("%Y-%m-%d")
        self.exec("INSERT INTO orders VALUES(NULL,?,?,?,?)",
                  (pid, qty, date, "ожидает"))
        self.exec("INSERT INTO sales VALUES(NULL,?,?,?,?)",
                  (pid, qty, date, product[4]))
        self.exec("UPDATE products SET quantity=quantity-? WHERE id=?",
                  (qty, pid))
        return True

    def orders(self):
        return self.fetch("""
        SELECT o.id, p.article, p.name,
               o.quantity, o.order_date, o.status
        FROM orders o
        LEFT JOIN products p ON p.id=o.product_id
        ORDER BY o.id DESC
        """)

    def set_status(self, oid, s):
        self.exec("UPDATE orders SET status=? WHERE id=?", (s, oid))

    def report(self, s, e):
        return self.fetch("""
        SELECT p.name, s.quantity, s.price, s.quantity*s.price
        FROM sales s
        LEFT JOIN products p ON p.id=s.product_id
        WHERE s.sale_date BETWEEN ? AND ?
        """, (s, e))

    def total(self, s, e):
        r = self.fetch("""
        SELECT SUM(quantity*price)
        FROM sales WHERE sale_date BETWEEN ? AND ?
        """, (s, e))[0][0]
        return r or 0

    def categories(self):
        return [c[0] for c in self.fetch(
            "SELECT name FROM categories ORDER BY name"
        )]

    def add_category(self, name):
        self.exec("INSERT OR IGNORE INTO categories(name) VALUES(?)", (name,))

class CardWindow(QMainWindow):
    def make_card(self):
        card = QWidget()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        return card, layout

    def fill_table(self, t, data):
        t.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, v in enumerate(row):
                t.setItem(r, c, QTableWidgetItem(str(v)))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.setWindowTitle("Учёт товаров художника")
        self.resize(1000, 700)
        self.setStyleSheet(STYLE)
        
        self.current_page = None
        self.nav_buttons = []
        
        self.init_ui()
        self.show_start_page()

    def init_ui(self):
        # Создаем центральный виджет с горизонтальным layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Боковая панель навигации
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)

        # Заголовок боковой панели
        title_label = QLabel("Меню")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #4f46e5;
            padding: 15px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 10px;
        """)
        sidebar_layout.addWidget(title_label)

        # Кнопки навигации
        nav_items = [
            ("📦 Каталог товаров", "catalog"),
            ("➕ Создать заказ", "create_order"),
            ("🛒 Список заказов", "orders"),
            ("📊 Отчёт по продажам", "report"),
        ]

        for text, page in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, p=page: self.show_page(p))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append((btn, page))

        sidebar_layout.addStretch()

        # Контейнер для страниц
        self.page_container = QStackedWidget()
        self.page_container.setStyleSheet("background: transparent;")

        # Создаем страницы
        self.pages = {
            "start": self.create_start_page(),
            "catalog": Catalog(self.db, self),
            "create_order": CreateOrder(self.db, self),
            "orders": OrderList(self.db, self),
            "report": Report(self.db, self),
        }

        # Добавляем страницы в контейнер
        for page in self.pages.values():
            self.page_container.addWidget(page)

        # Добавляем боковую панель и контейнер страниц в основной layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.page_container, 1)

    def create_start_page(self):
        card = QWidget()
        card.setObjectName("card")
        layout = QVBoxLayout(card)

        title = QLabel("УЧЁТ ТОВАРА")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:24px;font-weight:bold;color:#1e293b;")
        layout.addWidget(title)

        layout.addStretch()

        # Кнопки для быстрого доступа (как в исходной версии)
        for text, fn in [
            ("📦 Каталог товаров", lambda: self.show_page("catalog")),
            ("➕ Создать заказ", lambda: self.show_page("create_order")),
            ("🛒 Список заказов", lambda: self.show_page("orders")),
            ("📊 Отчёт по продажам", lambda: self.show_page("report"))
        ]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            b.setMinimumHeight(50)
            layout.addWidget(b)

        layout.addStretch()

        # Информация о приложении
        info_label = QLabel("Система учета товаров для художников\nВыберите раздел для работы")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 14px; color: #94a3b8; padding: 20px;")
        layout.addWidget(info_label)

        return card

    def show_start_page(self):
        # Показываем начальную страницу без выделения кнопок в боковой панели
        self.page_container.setCurrentWidget(self.pages["start"])
        self.setWindowTitle("Учёт товаров художника")
        
        # Сбрасываем выделение всех кнопок навигации
        for btn, _ in self.nav_buttons:
            btn.setProperty("active", False)
            btn.setStyleSheet(btn.styleSheet())

    def show_page(self, page_name):
        # Обновляем стиль кнопок навигации
        for btn, p in self.nav_buttons:
            if p == page_name:
                btn.setProperty("active", True)
            else:
                btn.setProperty("active", False)
            btn.setStyleSheet(btn.styleSheet())  # Обновляем стиль

        # Показываем выбранную страницу
        page = self.pages[page_name]
        self.page_container.setCurrentWidget(page)
        
        # Обновляем данные на странице, если она поддерживает метод load
        if hasattr(page, 'load'):
            page.load()
        
        self.setWindowTitle(f"Учёт товаров художника - {self.get_page_title(page_name)}")

    def get_page_title(self, page_name):
        titles = {
            "catalog": "Каталог товаров",
            "create_order": "Создание заказа",
            "orders": "Список заказов",
            "report": "Отчёт по продажам",
        }
        return titles.get(page_name, "Учёт товаров")

class CreateOrder(QWidget):
    def __init__(self, db, parent):
        super().__init__()
        self.db, self.parent_window = db, parent
        self.selected_product = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("НОВЫЙ ЗАКАЗ")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:20px;font-weight:bold;margin-bottom:20px;")
        layout.addWidget(title)

        # Информация о товаре
        info_group = QGroupBox("Выберите товар")
        info_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        info_layout = QVBoxLayout(info_group)
        
        self.product_combo = QComboBox()
        self.product_combo.currentIndexChanged.connect(self.on_product_selected)
        info_layout.addWidget(self.product_combo)

        self.info_widget = QWidget()
        self.info_layout = QFormLayout(self.info_widget)
        
        self.lbl_name = QLabel("-")
        self.lbl_article = QLabel("-")
        self.lbl_category = QLabel("-")
        self.lbl_price = QLabel("-")
        self.lbl_available = QLabel("-")
        
        for label, widget in [
            ("Название:", self.lbl_name),
            ("Артикул:", self.lbl_article),
            ("Категория:", self.lbl_category),
            ("Цена:", self.lbl_price),
            ("Доступно:", self.lbl_available)
        ]:
            self.info_layout.addRow(label, widget)
        
        info_layout.addWidget(self.info_widget)
        self.info_widget.hide()
        
        layout.addWidget(info_group)

        # Количество и итог
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel("Количество:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 1000)
        self.quantity_spin.valueChanged.connect(self.update_total)
        quantity_layout.addWidget(self.quantity_spin)
        quantity_layout.addStretch()
        layout.addLayout(quantity_layout)

        self.total_label = QLabel("Итого: 0 ₽")
        self.total_label.setStyleSheet("font-size:16px;font-weight:bold;color:#16a34a;")
        layout.addWidget(self.total_label)

        # Кнопка создания
        self.create_btn = QPushButton("✅ Создать заказ")
        self.create_btn.clicked.connect(self.create_order)
        self.create_btn.setEnabled(False)
        layout.addWidget(self.create_btn)

        layout.addStretch()

        self.load_products()

    def load_products(self):
        products = self.db.available_products()
        self.product_combo.clear()
        self.product_combo.addItem("-- Выберите товар --", None)
        
        for product in products:
            text = f"{product[1]} ({product[5]}) - {product[3]} шт. - {product[4]} ₽"
            self.product_combo.addItem(text, product[0])

    def on_product_selected(self, index):
        if index == 0:
            self.selected_product = None
            self.info_widget.hide()
            self.create_btn.setEnabled(False)
            return

        pid = self.product_combo.itemData(index)
        self.selected_product = self.db.product_by_id(pid)
        
        if self.selected_product:
            self.lbl_name.setText(self.selected_product[1])
            self.lbl_article.setText(self.selected_product[5])
            self.lbl_category.setText(self.selected_product[2])
            self.lbl_price.setText(f"{self.selected_product[4]} ₽")
            self.lbl_available.setText(f"{self.selected_product[3]} шт.")
            
            self.quantity_spin.setMaximum(self.selected_product[3])
            self.quantity_spin.setValue(1)
            
            self.info_widget.show()
            self.create_btn.setEnabled(True)
            self.update_total()

    def update_total(self):
        if self.selected_product:
            total = self.selected_product[4] * self.quantity_spin.value()
            self.total_label.setText(f"Итого: {total:.2f} ₽")

    def create_order(self):
        if not self.selected_product:
            QMessageBox.warning(self, "Ошибка", "Выберите товар!")
            return

        try:
            self.db.add_order(self.selected_product[0], self.quantity_spin.value())
            QMessageBox.information(self, "Успех", 
                f"Заказ успешно создан!\n"
                f"Товар: {self.selected_product[1]}\n"
                f"Количество: {self.quantity_spin.value()}\n"
                f"Сумма: {self.selected_product[4] * self.quantity_spin.value():.2f} ₽")
            
            self.load_products()
            self.selected_product = None
            self.product_combo.setCurrentIndex(0)
            self.info_widget.hide()
            self.create_btn.setEnabled(False)
            
        except ValueError as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")

    def load(self):
        self.load_products()
        self.selected_product = None
        self.product_combo.setCurrentIndex(0)
        self.info_widget.hide()
        self.create_btn.setEnabled(False)

class Catalog(QWidget):
    def __init__(self, db, parent):
        super().__init__()
        self.db, self.parent_window = db, parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Панель поиска и кнопок
        top_layout = QHBoxLayout()
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Поиск товара")
        self.search.textChanged.connect(self.load)
        top_layout.addWidget(self.search)
        
        top_layout.addStretch()
        
        create_btn = QPushButton("➕ Создать")
        create_btn.clicked.connect(self.create)
        top_layout.addWidget(create_btn)
        
        layout.addLayout(top_layout)

        # Таблица товаров
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["№", "Артикул", "Название", "Категория", "Кол-во", "Цена", "⚙"]
        )
        self.table.setColumnWidth(2, 200)
        layout.addWidget(self.table)

        self.load()

    def load(self):
        self.table.setRowCount(0)
        for i, p in enumerate(self.db.products(self.search.text()), 1):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(i)))
            for c, v in enumerate(p[5::-1][:5][::-1], 1):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))

            btns = QWidget()
            l = QHBoxLayout(btns)
            e = QPushButton("✏")
            d = QPushButton("🗑")
            e.clicked.connect(lambda _, x=p[0]: self.edit(x))
            d.clicked.connect(lambda _, x=p[0]: self.delete(x))
            l.addWidget(e)
            l.addWidget(d)
            l.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(r, 6, btns)

    def edit(self, pid):
        p = self.db.fetch("SELECT * FROM products WHERE id=?", (pid,))[0]
        dlg = ProductDialog(self.db, p)
        if dlg.exec():
            self.load()

    def create(self):
        dlg = ProductDialog(self.db)
        if dlg.exec():
            self.load()

    def delete(self, pid):
        if QMessageBox.question(self, "Удалить", "Удалить товар?") == QMessageBox.StandardButton.Yes:
            self.db.delete_product(pid)
            self.load()

class ProductDialog(QDialog):
    def __init__(self, db, data=None):
        super().__init__()
        self.db = db
        self.data = data
        self.setWindowTitle("Информация о товаре")
        self.setStyleSheet(STYLE)

        card = QWidget(self)
        card.setObjectName("card")
        layout = QFormLayout(card)

        self.a = QLineEdit()
        self.n = QLineEdit()
        self.c = QComboBox()
        self.c.addItems(db.categories())
        self.q = QSpinBox()
        self.q.setRange(0, 9999)
        self.p = QDoubleSpinBox()
        self.p.setMaximum(999999)
        self.p.setSuffix(" ₽")
        self.d = QTextEdit()

        for t, w in [
            ("Артикул", self.a),
            ("Название", self.n),
            ("Категория", self.c),
            ("Количество", self.q),
            ("Цена", self.p),
            ("Описание", self.d),
        ]:
            layout.addRow(t, w)

        btns = QHBoxLayout()
        save = QPushButton("Подтвердить")
        cancel = QPushButton("Отменить")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.save)
        btns.addWidget(save)
        btns.addWidget(cancel)
        layout.addRow(btns)

        v = QVBoxLayout(self)
        v.addWidget(card)

        if data:
            self.a.setText(data[5])
            self.n.setText(data[1])
            self.c.setCurrentText(data[2])
            self.q.setValue(data[3])
            self.p.setValue(data[4])
            self.d.setText(data[6])

    def save(self):
        d = (
            self.n.text(),
            self.a.text(),
            self.c.currentText(),
            self.q.value(),
            self.p.value(),
            self.d.toPlainText()
        )
        try:
            if self.data:
                self.db.update_product(self.data[0], d)
            else:
                self.db.add_product(d)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

class OrderList(QWidget):
    def __init__(self, db, parent):
        super().__init__()
        self.db, self.parent_window = db, parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Кнопка создания нового заказа
        create_new = QPushButton("➕ Создать новый заказ")
        create_new.clicked.connect(self.create_new_order)
        layout.addWidget(create_new)

        # Таблица заказов
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["№", "Артикул", "Товар", "Кол-во", "Дата", "Статус", "⚙"]
        )
        self.table.setColumnWidth(2, 200)
        layout.addWidget(self.table)

        self.load()

    def load(self):
        self.table.setRowCount(0)
        for i, o in enumerate(self.db.orders(), 1):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(i)))
            for c, v in enumerate(o, 1):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))

            b = QPushButton("🔄")
            b.clicked.connect(lambda _, x=o[0]: self.change_status(x))
            self.table.setCellWidget(r, 6, b)

    def change_status(self, oid):
        s, ok = QInputDialog.getItem(
            self, "Статус",
            "Выберите статус",
            ["ожидает", "в обработке", "выполнен", "отменен"], 0, False
        )
        if ok:
            self.db.set_status(oid, s)
            self.load()

    def create_new_order(self):
        self.parent_window.show_page("create_order")

class Report(QWidget):
    def __init__(self, db, parent):
        super().__init__()
        self.db, self.parent_window = db, parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Период отчета
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("С:"))
        self.s = QDateEdit(QDate.currentDate().addDays(-30))
        self.s.setCalendarPopup(True)
        period_layout.addWidget(self.s)
        
        period_layout.addWidget(QLabel("По:"))
        self.e = QDateEdit(QDate.currentDate())
        self.e.setCalendarPopup(True)
        period_layout.addWidget(self.e)
        
        period_layout.addStretch()
        
        gen_btn = QPushButton("Сформировать отчет")
        gen_btn.clicked.connect(self.load)
        period_layout.addWidget(gen_btn)
        
        layout.addLayout(period_layout)

        # Итоговая сумма
        self.total = QLabel("Итог: 0 ₽")
        self.total.setStyleSheet("font-size:18px;font-weight:bold;color:#16a34a")
        layout.addWidget(self.total)

        # Таблица отчета
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Товар", "Кол-во", "Цена", "Сумма"]
        )
        self.table.setColumnWidth(0, 250)
        layout.addWidget(self.table)

        self.load()

    def load(self):
        s = self.s.date().toString("yyyy-MM-dd")
        e = self.e.date().toString("yyyy-MM-dd")
        data = self.db.report(s, e)
        
        self.table.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, v in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))
                
        self.total.setText(f"Итог: {self.db.total(s, e):.2f} ₽")

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()