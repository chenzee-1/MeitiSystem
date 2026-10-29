import csv
import io
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
app = Flask(__name__)
app.secret_key = 'meiti_secret_key_123' # 用于保持登录状态
DATABASE = 'meiti.db'
# --- 数据库初始化 ---
def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # 创建用户表
        cursor.execute('''CREATE TABLE users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE,
                            password TEXT,
                            role TEXT)''')
        # 创建员工表
        cursor.execute('''CREATE TABLE employees (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            department TEXT,
                            hourly_wage REAL)''')
        # 创建排班表
        cursor.execute('''CREATE TABLE schedules (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            employee_id INTEGER,
                            date TEXT,
                            shift_type TEXT)''')
        # 插入一个默认的 HR 账号 (账号: admin, 密码: 123)
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', '123', 'HR')")

        cursor.execute("INSERT INTO users (username, password, role) VALUES ('manager', '123', 'WorkflowManager')")
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('employee', '123', 'Employee')")
        conn.commit()
        conn.close()
        print("数据库初始化完成！")
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # 让查询结果可以通过字典方式访问
    return conn
# --- 路由功能 ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误，请重试！', 'danger')
            
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    # 查员工总数
    emp_count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    # 查排班总数
    shift_count = conn.execute("SELECT COUNT(*) FROM schedules").fetchone()[0]
    conn.close()
    
    # 把这两个数字传给前端
    return render_template('dashboard.html', emp_count=emp_count, shift_count=shift_count)
@app.route('/employees')
def employees():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '')
    conn = get_db()
    if search_query:
        emps = conn.execute("SELECT * FROM employees WHERE name LIKE ?", ('%' + search_query + '%',)).fetchall()
    else:
        emps = conn.execute("SELECT * FROM employees").fetchall()
    conn.close()
    return render_template('employees.html', employees=emps)
@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') != 'HR':
        flash('权限不足：只有 HR 可以添加员工！', 'danger')
        return redirect(url_for('dashboard'))

    # 👇 下面是你缺失的代码 👇
    if request.method == 'POST':
        name = request.form['name']
        dept = request.form['department']
        wage = request.form['hourly_wage']
        
        conn = get_db()
        conn.execute("INSERT INTO employees (name, department, hourly_wage) VALUES (?, ?, ?)", (name, dept, wage))
        conn.commit()
        conn.close()
        
        flash('员工添加成功！', 'success')
        return redirect(url_for('employees'))
        
    return render_template('add_employee.html')
@app.route('/view_employee/<int:id>')
def view_employee(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    # 把该员工的信息查出来
    emp = conn.execute("SELECT * FROM employees WHERE id = ?", (id,)).fetchone()
    
    # 顺便查一下他的排班情况（显得更专业）
    schedules = conn.execute("SELECT * FROM schedules WHERE employee_id = ?", (id,)).fetchall()
    conn.close()
    
    if not emp:
        flash('员工不存在', 'danger')
        return redirect(url_for('employees'))
        
    return render_template('view_employee.html', emp=emp, schedules=schedules)

# @app.route('/add_employee', methods=['GET', 'POST'])
# def add_employee():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
        
#     if session.get('role') != 'HR':
#         flash('权限不足：只有 HR 可以添加员工！', 'danger')
#         return redirect(url_for('dashboard'))

@app.route('/edit_employee/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        dept = request.form['department']
        wage = request.form['hourly_wage']
        
        conn.execute("UPDATE employees SET name=?, department=?, hourly_wage=? WHERE id=?", (name, dept, wage, id))
        conn.commit()
        conn.close()
        
        flash('员工信息修改成功！', 'success')
        return redirect(url_for('employees'))
    
    emp = conn.execute("SELECT * FROM employees WHERE id = ?", (id,)).fetchone()
    conn.close()
    
    return render_template('edit_employee.html', emp=emp)
@app.route('/delete_employee/<int:id>')
def delete_employee(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute("DELETE FROM employees WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('员工已删除', 'warning')
    return redirect(url_for('employees'))

@app.route('/schedule')
def schedule():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    # 查出所有员工，留着给下拉菜单用
    employees = conn.execute("SELECT * FROM employees").fetchall()
    
    # 👇 核心权限拦截 👇
    if session.get('role') == 'Employee':
        # 如果是普通员工，只能查到他自己的名字
        current_user = session.get('username')
        schedules = conn.execute('''SELECT s.id, e.name, s.date, s.shift_type 
                                    FROM schedules s 
                                    JOIN employees e ON s.employee_id = e.id
                                    WHERE e.name = ?''', (current_user,)).fetchall()
    else:
        # 如果是 HR 或 Manager，查全店
        schedules = conn.execute('''SELECT s.id, e.name, s.date, s.shift_type 
                                    FROM schedules s 
                                    JOIN employees e ON s.employee_id = e.id''').fetchall()
    
    conn.close()
    
    # 把 employees 传给前端做下拉框，把 schedules 传给前端做表格
    return render_template('schedule.html', schedules=schedules, employees=employees)
@app.route('/export_schedule')
def export_schedule():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    # 查出全店排班
    schedules = conn.execute('''SELECT e.name, s.date, s.shift_type 
                                FROM schedules s 
                                JOIN employees e ON s.employee_id = e.id''').fetchall()
    conn.close()

    # 创建一个内存中的文本流
    si = io.StringIO()
    cw = csv.writer(si)
    
    # 写入表头
    cw.writerow(['Employee Name', 'Date', 'Shift Type'])
    
    # 写入数据
    for row in schedules:
        cw.writerow([row['name'], row['date'], row['shift_type']])
    
    # 准备返回响应（让浏览器下载）
    output = si.getvalue()
    return app.response_class(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=store_schedule.csv"}
    )
@app.route('/add_schedule', methods=['POST'])
def add_schedule():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    emp_id = request.form['employee_id']
    date = request.form['date']
    shift = request.form['shift_type']
    
    conn = get_db()
    conn.execute("INSERT INTO schedules (employee_id, date, shift_type) VALUES (?, ?, ?)", (emp_id, date, shift))
    conn.commit()
    conn.close()
    
    flash('Shift assigned successfully!', 'success')
    return redirect(url_for('schedule'))
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        old_pwd = request.form['old_password']
        new_pwd = request.form['new_password']
        confirm_pwd = request.form['confirm_password']
        
        if new_pwd != confirm_pwd:
            flash('两次输入的新密码不一致！', 'danger')
            return redirect(url_for('change_password'))
            
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ? AND password = ?", (session['user_id'], old_pwd)).fetchone()
        
        if user:
            conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_pwd, session['user_id']))
            conn.commit()
            conn.close()
            flash('密码修改成功，请重新登录！', 'success')
            session.clear() # 改完密码强制退出重登
            return redirect(url_for('login'))
        else:
            conn.close()
            flash('旧密码错误！', 'danger')
            
    return render_template('change_password.html')
if __name__ == '__main__':
    init_db() # 运行前自动建表
    app.run(debug=True, port=5000)

    # zzz
    # ct-fz
    # Mr.cao
