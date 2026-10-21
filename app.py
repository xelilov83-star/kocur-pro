import os, io, csv, sqlite3, secrets, shutil
from datetime import datetime, date
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, g, abort, make_response
from werkzeug.security import generate_password_hash, check_password_hash

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('KOCUR_DATA_DIR', BASE / 'data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.environ.get('KOCUR_DB_PATH', DATA_DIR / 'kocur_pro.sqlite3'))
SECRET_KEY = os.environ.get('KOCUR_SECRET_KEY')
if not SECRET_KEY:
    secret_file = DATA_DIR / '.secret_key'
    if secret_file.exists():
        SECRET_KEY = secret_file.read_text().strip()
    else:
        SECRET_KEY = secrets.token_urlsafe(48)
        secret_file.write_text(SECRET_KEY)
        try: secret_file.chmod(0o600)
        except OSError: pass

app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '0') == '1', PERMANENT_SESSION_LIFETIME=60*60*8, MAX_CONTENT_LENGTH=10*1024*1024)

TRANSLATIONS = {
 'az': {'brand':'Köçür Pro','dashboard':'İdarə paneli','orders':'Sifarişlər','customers':'Müştərilər','partners':'Sürücü və fəhlələr','expenses':'Xərclər','payments':'Ödənişlər','reports':'Hesabatlar','users':'İstifadəçilər','backup':'Ehtiyat nüsxə','logout':'Çıxış','login':'Daxil ol','username':'Login','password':'Parol','welcome':'Xoş gəlmisiniz','new_order':'Yeni sifariş','order_no':'Sifariş №','customer':'Müştəri','phone':'Telefon','from_addr':'Haradan','to_addr':'Haraya','date':'Tarix','status':'Status','price':'Müştəri qiyməti (AZN)','partner_cost':'Tərəfdaş ödənişi (AZN)','notes':'Qeydlər','save':'Yadda saxla','cancel':'Ləğv et','actions':'Əməliyyatlar','edit':'Düzəliş et','delete':'Sil','confirm_delete':'Bu qeydi silmək istədiyinizə əminsiniz?','add_customer':'Müştəri əlavə et','name':'Ad / şirkət','type':'Növ','role':'Rol','admin':'Administrator','manager':'Menecer','worker':'İşçi','active':'Aktiv','pending':'Gözləyir','completed':'Tamamlandı','cancelled':'Ləğv edildi','total_revenue':'Müştəri ödənişləri','partner_payments':'Tərəfdaş ödənişləri','expenses_total':'Xərclər','outstanding':'Qalıq borc','gross_margin':'İlkin fərq','month':'Ay','filter':'Filtr','description':'Açıqlama','amount':'Məbləğ (AZN)','category':'Kateqoriya','paid':'Ödənilib','unpaid':'Ödənilməyib','payment_type':'Ödəniş növü','customer_payment':'Müştəridən ödəniş','partner_payment':'Tərəfdaşa ödəniş','expense':'Xərc','commission':'Komissiya','driver':'Sürücü','mover':'Fəhlə','customer_list':'Müştəri siyahısı','partner_list':'Tərəfdaş siyahısı','add_partner':'Tərəfdaş əlavə et','add_expense':'Xərc əlavə et','add_payment':'Ödəniş əlavə et','create_user':'İstifadəçi yarat','backup_done':'Ehtiyat nüsxə yaradıldı.','language':'Dil','no_data':'Hələ məlumat yoxdur.','access_denied':'Bu əməliyyat üçün icazəniz yoxdur.','password_change':'Parolu dəyiş','current_password':'Cari parol','new_password':'Yeni parol','repeat_password':'Yeni parol (təkrar)','update_password':'Parolu yenilə','created':'Yaradılma tarixi','order_details':'Sifariş detalları','dashboard_sub':'Bugünkü iş və maliyyə vəziyyəti','all':'Hamısı','search':'Axtar','export_csv':'CSV yüklə','backup_desc':'Verilənlər bazasının ehtiyat nüsxəsini endir. Faylı təhlükəsiz yerdə saxlayın.','user_desc':'İşçilərə yalnız vəzifələrinə uyğun giriş hüquqları verin.','minimum_password':'Parol ən azı 12 simvol olmalıdır.','invalid_login':'Login və ya parol yanlışdır.','required':'Bu sahə mütləqdir.','server_notice':'Bu ilkin versiyadır. İnternetdə yayımlamadan əvvəl HTTPS, güclü SECRET KEY, müntəzəm backup və server təhlükəsizliyini qurun.'},
 'ru': {'brand':'Köçür Pro','dashboard':'Панель управления','orders':'Заказы','customers':'Клиенты','partners':'Водители и грузчики','expenses':'Расходы','payments':'Платежи','reports':'Отчёты','users':'Пользователи','backup':'Резервная копия','logout':'Выйти','login':'Войти','username':'Логин','password':'Пароль','welcome':'Добро пожаловать','new_order':'Новый заказ','order_no':'Заказ №','customer':'Клиент','phone':'Телефон','from_addr':'Откуда','to_addr':'Куда','date':'Дата','status':'Статус','price':'Цена клиенту (AZN)','partner_cost':'Оплата партнёру (AZN)','notes':'Примечания','save':'Сохранить','cancel':'Отмена','actions':'Действия','edit':'Изменить','delete':'Удалить','confirm_delete':'Удалить эту запись?','add_customer':'Добавить клиента','name':'Имя / компания','type':'Тип','role':'Роль','admin':'Администратор','manager':'Менеджер','worker':'Сотрудник','active':'Активен','pending':'Ожидает','completed':'Завершён','cancelled':'Отменён','total_revenue':'Платежи клиентов','partner_payments':'Платежи партнёрам','expenses_total':'Расходы','outstanding':'Остаток долга','gross_margin':'Валовая разница','month':'Месяц','filter':'Фильтр','description':'Описание','amount':'Сумма (AZN)','category':'Категория','paid':'Оплачено','unpaid':'Не оплачено','payment_type':'Тип платежа','customer_payment':'Оплата клиента','partner_payment':'Оплата партнёру','expense':'Расход','commission':'Комиссия','driver':'Водитель','mover':'Грузчик','customer_list':'Список клиентов','partner_list':'Список партнёров','add_partner':'Добавить партнёра','add_expense':'Добавить расход','add_payment':'Добавить платёж','create_user':'Создать пользователя','backup_done':'Резервная копия создана.','language':'Язык','no_data':'Пока нет данных.','access_denied':'У вас нет прав для этого действия.','password_change':'Сменить пароль','current_password':'Текущий пароль','new_password':'Новый пароль','repeat_password':'Повторите пароль','update_password':'Обновить пароль','created':'Дата создания','order_details':'Детали заказа','dashboard_sub':'Работа и финансы на сегодня','all':'Все','search':'Поиск','export_csv':'Скачать CSV','backup_desc':'Скачайте резервную копию базы данных и храните её в безопасном месте.','user_desc':'Предоставляйте сотрудникам доступ только по их роли.','minimum_password':'Пароль должен содержать не менее 12 символов.','invalid_login':'Неверный логин или пароль.','required':'Это поле обязательно.','server_notice':'Это начальная версия. Перед публикацией в интернете настройте HTTPS, надёжный SECRET KEY, регулярные резервные копии и безопасность сервера.'}
}

def tr(key): return TRANSLATIONS.get(session.get('lang','az'), TRANSLATIONS['az']).get(key, key)
app.jinja_env.globals['tr'] = tr

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','manager','worker')), active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, notes TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS partners(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, partner_type TEXT NOT NULL CHECK(partner_type IN ('driver','mover','team')), payment_notes TEXT, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, order_date TEXT NOT NULL, from_addr TEXT NOT NULL, to_addr TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', price REAL NOT NULL DEFAULT 0, partner_cost REAL NOT NULL DEFAULT 0, driver_id INTEGER, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(customer_id) REFERENCES customers(id), FOREIGN KEY(driver_id) REFERENCES partners(id));
CREATE TABLE IF NOT EXISTS order_movers(order_id INTEGER NOT NULL, partner_id INTEGER NOT NULL, PRIMARY KEY(order_id, partner_id), FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE, FOREIGN KEY(partner_id) REFERENCES partners(id));
CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY AUTOINCREMENT, expense_date TEXT NOT NULL, category TEXT NOT NULL, description TEXT, amount REAL NOT NULL CHECK(amount >= 0), created_by INTEGER, created_at TEXT NOT NULL, FOREIGN KEY(created_by) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, payment_date TEXT NOT NULL, payment_type TEXT NOT NULL CHECK(payment_type IN ('customer','partner','commission')), order_id INTEGER, partner_id INTEGER, amount REAL NOT NULL CHECK(amount >= 0), description TEXT, created_by INTEGER, created_at TEXT NOT NULL, FOREIGN KEY(order_id) REFERENCES orders(id), FOREIGN KEY(partner_id) REFERENCES partners(id), FOREIGN KEY(created_by) REFERENCES users(id));
'''

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None: db.close()

with sqlite3.connect(DB_PATH) as _db:
    _db.execute('PRAGMA foreign_keys=ON')
    _db.executescript(SCHEMA)
    _db.commit()

@app.before_request
def prepare_request():
    if request.endpoint == 'static': return
    if request.method == 'POST':
        token = session.get('_csrf_token')
        posted = request.form.get('_csrf_token', '')
        if not token or not secrets.compare_digest(token, posted): abort(400, 'Invalid CSRF token')

@app.context_processor
def inject_globals():
    if '_csrf_token' not in session: session['_csrf_token'] = secrets.token_urlsafe(32)
    return {'current_user': current_user(), 'lang': session.get('lang','az'), 'csrf_token': session['_csrf_token'], 'today': date.today().isoformat()}

def current_user():
    uid = session.get('user_id')
    if not uid: return None
    return get_db().execute('SELECT id, username, role, active FROM users WHERE id=?', (uid,)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or not user['active']:
            session.clear(); return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            user = current_user()
            if user['role'] not in roles: abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco

def as_float(v):
    try:
        n = float((v or '0').replace(',', '.'))
        if n < 0: raise ValueError()
        return round(n, 2)
    except (ValueError, AttributeError): raise ValueError('Məbləğ düzgün daxil edilməyib.')

def stamp(): return datetime.now().isoformat(timespec='seconds')

@app.route('/setup', methods=['GET','POST'])
def setup():
    db = get_db()
    if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] > 0: return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        repeat = request.form.get('repeat','')
        if len(username) < 4 or not username.replace('_','').isalnum(): flash('Login ən azı 4 simvol olmalı və yalnız hərf, rəqəm, _ içərməlidir.','error')
        elif len(password) < 12: flash(tr('minimum_password'),'error')
        elif password != repeat: flash('Parollar uyğun gəlmir.','error')
        else:
            db.execute('INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)',(username,generate_password_hash(password), 'admin',1,stamp())); db.commit()
            flash('Administrator yaradıldı. İndi daxil ola bilərsiniz.','success'); return redirect(url_for('login'))
    return render_template('setup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user(): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username=request.form.get('username','').strip(); password=request.form.get('password','')
        user=get_db().execute('SELECT * FROM users WHERE username=? AND active=1',(username,)).fetchone()
        if user and check_password_hash(user['password_hash'],password):
            session.clear(); session['user_id']=user['id']; session['lang']=request.form.get('lang','az') if request.form.get('lang') in ('az','ru') else 'az'; session.permanent=True; session['_csrf_token']=secrets.token_urlsafe(32)
            return redirect(url_for('dashboard'))
        flash(tr('invalid_login'),'error')
    return render_template('login.html')

@app.route('/lang/<code>')
@login_required
def set_lang(code):
    if code in ('az','ru'): session['lang']=code
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/logout', methods=['POST'])
@login_required
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    db=get_db(); month=request.args.get('month',date.today().strftime('%Y-%m'))
    stats = {
      'orders': db.execute("SELECT COUNT(*) FROM orders WHERE substr(order_date,1,7)=?",(month,)).fetchone()[0],
      'revenue': db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type='customer' AND substr(payment_date,1,7)=?",(month,)).fetchone()[0],
      'partner_payments': db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type='partner' AND substr(payment_date,1,7)=?",(month,)).fetchone()[0],
      'expenses': db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE substr(expense_date,1,7)=?",(month,)).fetchone()[0],
      'customer_debt': db.execute("SELECT COALESCE(SUM(o.price-COALESCE(p.paid,0)),0) FROM orders o LEFT JOIN (SELECT order_id,SUM(amount) paid FROM payments WHERE payment_type='customer' GROUP BY order_id) p ON p.order_id=o.id WHERE o.status!='cancelled' AND (o.price-COALESCE(p.paid,0))>0").fetchone()[0],
      'partner_debt': db.execute("SELECT COALESCE(SUM(o.partner_cost-COALESCE(p.paid,0)),0) FROM orders o LEFT JOIN (SELECT order_id,SUM(amount) paid FROM payments WHERE payment_type='partner' GROUP BY order_id) p ON p.order_id=o.id WHERE o.status!='cancelled' AND (o.partner_cost-COALESCE(p.paid,0))>0").fetchone()[0],
    }
    stats['margin']=stats['revenue']-stats['partner_payments']-stats['expenses']
    orders=db.execute('''SELECT o.*, c.name customer_name, c.phone customer_phone, p.name driver_name FROM orders o LEFT JOIN customers c ON c.id=o.customer_id LEFT JOIN partners p ON p.id=o.driver_id ORDER BY o.order_date DESC,o.id DESC LIMIT 8''').fetchall()
    return render_template('dashboard.html', stats=stats, orders=orders, month=month)

@app.route('/orders', methods=['GET','POST'])
@login_required
def orders():
    db=get_db()
    if request.method=='POST':
        if current_user()['role']=='worker': abort(403)
        try:
            customer_id=request.form.get('customer_id') or None
            order_date=request.form.get('order_date') or date.today().isoformat()
            from_addr=request.form.get('from_addr','').strip(); to_addr=request.form.get('to_addr','').strip()
            if not from_addr or not to_addr: raise ValueError('Ünvanlar mütləqdir.')
            status=request.form.get('status','pending')
            if status not in ('pending','completed','cancelled'): status='pending'
            price=as_float(request.form.get('price')); partner_cost=as_float(request.form.get('partner_cost'))
            driver_id=request.form.get('driver_id') or None
            db.execute('INSERT INTO orders(customer_id,order_date,from_addr,to_addr,status,price,partner_cost,driver_id,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(customer_id,order_date,from_addr,to_addr,status,price,partner_cost,driver_id,request.form.get('notes','').strip(),stamp()))
            oid=db.execute('SELECT last_insert_rowid()').fetchone()[0]; db.commit()
            flash(f'Sifariş #{oid} yadda saxlanıldı. Müştəri ödənişi və tərəfdaş ödənişi ayrıca “Ödənişlər” bölməsində qeyd edin.','success'); return redirect(url_for('orders'))
        except (ValueError, sqlite3.Error) as e: flash(str(e),'error')
    rows=db.execute('''SELECT o.*,c.name customer_name,c.phone customer_phone,p.name driver_name,COALESCE(cp.paid,0) customer_paid,COALESCE(pp.paid,0) partner_paid FROM orders o LEFT JOIN customers c ON c.id=o.customer_id LEFT JOIN partners p ON p.id=o.driver_id LEFT JOIN (SELECT order_id,SUM(amount) paid FROM payments WHERE payment_type='customer' GROUP BY order_id) cp ON cp.order_id=o.id LEFT JOIN (SELECT order_id,SUM(amount) paid FROM payments WHERE payment_type='partner' GROUP BY order_id) pp ON pp.order_id=o.id ORDER BY o.order_date DESC,o.id DESC''').fetchall()
    customers=db.execute('SELECT * FROM customers ORDER BY name').fetchall(); drivers=db.execute("SELECT * FROM partners WHERE active=1 AND partner_type IN ('driver','team') ORDER BY name").fetchall()
    return render_template('orders.html', orders=rows, customers=customers, drivers=drivers)

@app.route('/orders/<int:oid>/status', methods=['POST'])
@roles_required('admin','manager')
def order_status(oid):
    status=request.form.get('status')
    if status not in ('pending','completed','cancelled'): abort(400)
    db=get_db(); db.execute('UPDATE orders SET status=? WHERE id=?',(status,oid)); db.commit(); flash('Sifariş statusu yeniləndi.','success'); return redirect(url_for('orders'))

@app.route('/customers', methods=['GET','POST'])
@login_required
def customers():
    db=get_db()
    if request.method=='POST':
        if current_user()['role']=='worker': abort(403)
        name=request.form.get('name','').strip()
        if not name: flash('Müştəri adı mütləqdir.','error')
        else:
            db.execute('INSERT INTO customers(name,phone,notes,created_at) VALUES(?,?,?,?)',(name,request.form.get('phone','').strip(),request.form.get('notes','').strip(),stamp())); db.commit(); flash('Müştəri əlavə edildi.','success'); return redirect(url_for('customers'))
    rows=db.execute('SELECT c.*,COUNT(o.id) order_count FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY c.name').fetchall()
    return render_template('customers.html', customers=rows)

@app.route('/partners', methods=['GET','POST'])
@roles_required('admin','manager')
def partners():
    db=get_db()
    if request.method=='POST':
        name=request.form.get('name','').strip(); ptype=request.form.get('partner_type','driver')
        if not name or ptype not in ('driver','mover','team'): flash('Ad və düzgün növ daxil edin.','error')
        else:
            db.execute('INSERT INTO partners(name,phone,partner_type,payment_notes,created_at) VALUES(?,?,?,?,?)',(name,request.form.get('phone','').strip(),ptype,request.form.get('payment_notes','').strip(),stamp())); db.commit(); flash('Tərəfdaş əlavə edildi.','success'); return redirect(url_for('partners'))
    rows=db.execute('SELECT p.*,COUNT(DISTINCT o.id) orders_count FROM partners p LEFT JOIN orders o ON o.driver_id=p.id GROUP BY p.id ORDER BY p.name').fetchall()
    return render_template('partners.html', partners=rows)

@app.route('/expenses', methods=['GET','POST'])
@roles_required('admin','manager')
def expenses():
    db=get_db()
    if request.method=='POST':
        try:
            amount=as_float(request.form.get('amount')); category=request.form.get('category','').strip()
            if not category: raise ValueError('Kateqoriya mütləqdir.')
            db.execute('INSERT INTO expenses(expense_date,category,description,amount,created_by,created_at) VALUES(?,?,?,?,?,?)',(request.form.get('expense_date') or date.today().isoformat(),category,request.form.get('description','').strip(),amount,current_user()['id'],stamp())); db.commit(); flash('Xərc əlavə edildi.','success'); return redirect(url_for('expenses'))
        except (ValueError,sqlite3.Error) as e: flash(str(e),'error')
    rows=db.execute('SELECT e.*,u.username FROM expenses e LEFT JOIN users u ON u.id=e.created_by ORDER BY e.expense_date DESC,e.id DESC').fetchall()
    return render_template('expenses.html', expenses=rows)

@app.route('/payments', methods=['GET','POST'])
@roles_required('admin','manager')
def payments():
    db=get_db()
    if request.method=='POST':
        try:
            ptype=request.form.get('payment_type')
            if ptype not in ('customer','partner','commission'): raise ValueError('Ödəniş növü düzgün deyil.')
            amount=as_float(request.form.get('amount')); order_id=request.form.get('order_id') or None; partner_id=request.form.get('partner_id') or None
            if ptype in ('customer','partner') and not order_id: raise ValueError('Bu ödəniş üçün sifariş seçilməlidir.')
            if ptype=='partner' and not partner_id:
                oid=int(order_id); row=db.execute('SELECT driver_id FROM orders WHERE id=?',(oid,)).fetchone(); partner_id=row['driver_id'] if row and row['driver_id'] else None
            db.execute('INSERT INTO payments(payment_date,payment_type,order_id,partner_id,amount,description,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)',(request.form.get('payment_date') or date.today().isoformat(),ptype,order_id,partner_id,amount,request.form.get('description','').strip(),current_user()['id'],stamp())); db.commit(); flash('Ödəniş qeydə alındı.','success'); return redirect(url_for('payments'))
        except (ValueError,sqlite3.Error) as e: flash(str(e),'error')
    rows=db.execute('SELECT p.*,o.id order_no,c.name customer_name,pa.name partner_name,u.username FROM payments p LEFT JOIN orders o ON o.id=p.order_id LEFT JOIN customers c ON c.id=o.customer_id LEFT JOIN partners pa ON pa.id=p.partner_id LEFT JOIN users u ON u.id=p.created_by ORDER BY p.payment_date DESC,p.id DESC').fetchall()
    orders_list=db.execute('SELECT o.id,o.order_date,c.name customer_name FROM orders o LEFT JOIN customers c ON c.id=o.customer_id WHERE o.status != "cancelled" ORDER BY o.id DESC').fetchall()
    partners_list=db.execute('SELECT * FROM partners WHERE active=1 ORDER BY name').fetchall()
    return render_template('payments.html', payments=rows, orders=orders_list, partners=partners_list)

@app.route('/reports')
@roles_required('admin','manager')
def reports():
    month=request.args.get('month',date.today().strftime('%Y-%m')); db=get_db()
    row=db.execute('''SELECT (SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type='customer' AND substr(payment_date,1,7)=?) revenue,(SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type='partner' AND substr(payment_date,1,7)=?) partner_payments,(SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type='commission' AND substr(payment_date,1,7)=?) commissions,(SELECT COALESCE(SUM(amount),0) FROM expenses WHERE substr(expense_date,1,7)=?) expenses,(SELECT COUNT(*) FROM orders WHERE substr(order_date,1,7)=?) orders_count,(SELECT COUNT(*) FROM orders WHERE status='completed' AND substr(order_date,1,7)=?) completed''',(month,month,month,month,month,month)).fetchone()
    margin=row['revenue']-row['partner_payments']-row['expenses']
    daily=db.execute('''WITH RECURSIVE days(day) AS (SELECT date(?) UNION ALL SELECT date(day,'+1 day') FROM days WHERE day < date(?,'start of month','+1 month','-1 day')) SELECT d.day,COALESCE(r.revenue,0) revenue,COALESCE(p.cost,0) partner_payments,COALESCE(e.expense,0) expenses FROM days d LEFT JOIN (SELECT payment_date,SUM(amount) revenue FROM payments WHERE payment_type='customer' GROUP BY payment_date) r ON r.payment_date=d.day LEFT JOIN (SELECT payment_date,SUM(amount) cost FROM payments WHERE payment_type='partner' GROUP BY payment_date) p ON p.payment_date=d.day LEFT JOIN (SELECT expense_date,SUM(amount) expense FROM expenses GROUP BY expense_date) e ON e.expense_date=d.day ORDER BY d.day''',(month+'-01',month+'-01')).fetchall()
    return render_template('reports.html', month=month, totals=row, margin=margin, daily=daily)

@app.route('/users', methods=['GET','POST'])
@roles_required('admin')
def users():
    db=get_db()
    if request.method=='POST':
        username=request.form.get('username','').strip(); password=request.form.get('password',''); role=request.form.get('role','worker')
        if len(username)<4 or not username.replace('_','').isalnum(): flash('Login ən azı 4 simvol olmalı və hərf, rəqəm, _ içərməlidir.','error')
        elif len(password)<12: flash(tr('minimum_password'),'error')
        elif role not in ('admin','manager','worker'): flash('Rol düzgün deyil.','error')
        else:
            try: db.execute('INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)',(username,generate_password_hash(password),role,1,stamp())); db.commit(); flash('İstifadəçi yaradıldı.','success'); return redirect(url_for('users'))
            except sqlite3.IntegrityError: flash('Bu login artıq mövcuddur.','error')
    rows=db.execute('SELECT id,username,role,active,created_at FROM users ORDER BY id').fetchall()
    return render_template('users.html', users=rows)

@app.route('/users/<int:uid>/toggle', methods=['POST'])
@roles_required('admin')
def toggle_user(uid):
    if uid==current_user()['id']: flash('Öz hesabınızı bu səhifədən deaktiv edə bilməzsiniz.','error')
    else:
        db=get_db(); db.execute('UPDATE users SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?',(uid,)); db.commit(); flash('İstifadəçi statusu dəyişdirildi.','success')
    return redirect(url_for('users'))

@app.route('/password', methods=['GET','POST'])
@login_required
def change_password():
    if request.method=='POST':
        db=get_db(); user=db.execute('SELECT * FROM users WHERE id=?',(current_user()['id'],)).fetchone(); old=request.form.get('current_password',''); new=request.form.get('new_password',''); repeat=request.form.get('repeat_password','')
        if not check_password_hash(user['password_hash'],old): flash('Cari parol yanlışdır.','error')
        elif len(new)<12: flash(tr('minimum_password'),'error')
        elif new!=repeat: flash('Yeni parollar uyğun gəlmir.','error')
        else:
            db.execute('UPDATE users SET password_hash=? WHERE id=?',(generate_password_hash(new),user['id'])); db.commit(); session.clear(); flash('Parol dəyişdirildi. Yenidən daxil olun.','success'); return redirect(url_for('login'))
    return render_template('password.html')

@app.route('/backup', methods=['GET','POST'])
@roles_required('admin')
def backup():
    if request.method=='POST':
        DATA_DIR.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(DB_PATH) as source:
            # SQLite backup into a temporary file for a portable download.
            temp=DATA_DIR / f'backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}.sqlite3'
            with sqlite3.connect(temp) as target: source.backup(target)
        return send_file(temp, as_attachment=True, download_name=temp.name, mimetype='application/vnd.sqlite3')
    return render_template('backup.html')

@app.route('/export/<kind>')
@roles_required('admin','manager')
def export_csv(kind):
    db=get_db(); queries={'orders':("SELECT o.id,o.order_date,c.name customer,o.from_addr,o.to_addr,o.status,o.price,o.partner_cost,o.notes FROM orders o LEFT JOIN customers c ON c.id=o.customer_id ORDER BY o.id",['id','date','customer','from','to','status','price','partner_cost','notes']), 'payments':("SELECT id,payment_date,payment_type,order_id,partner_id,amount,description FROM payments ORDER BY id",['id','date','type','order_id','partner_id','amount','description']), 'expenses':("SELECT id,expense_date,category,description,amount FROM expenses ORDER BY id",['id','date','category','description','amount'])}
    if kind not in queries: abort(404)
    sql,headers=queries[kind]; output=io.StringIO(); writer=csv.writer(output); writer.writerow(headers)
    for row in db.execute(sql): writer.writerow(list(row))
    response=make_response('\ufeff'+output.getvalue()); response.headers['Content-Type']='text/csv; charset=utf-8'; response.headers['Content-Disposition']=f'attachment; filename=kocur-pro-{kind}-{date.today().isoformat()}.csv'; return response

@app.errorhandler(403)
def forbidden(e): return render_template('error.html', code=403, message=tr('access_denied')),403
@app.errorhandler(404)
def not_found(e): return render_template('error.html', code=404, message='Səhifə tapılmadı.'),404
@app.errorhandler(400)
def bad_request(e): return render_template('error.html', code=400, message='Sorğu qəbul edilmədi. Səhifəni yeniləyib yenidən cəhd edin.'),400

if __name__ == '__main__':
    print('Köçür Pro local server starting. Open http://127.0.0.1:5000/setup for first-time setup.')
    app.run(host=os.environ.get('HOST','127.0.0.1'), port=int(os.environ.get('PORT','5000')), debug=False)
