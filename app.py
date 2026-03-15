from flask import Flask, render_template, request, redirect, url_for
import database  # 导入数据库模块
from datetime import date

app = Flask(__name__)

@app.route('/')
def index():
    conn = database.connect_db()  # 连接数据库
    try:
        books = database.statistics(conn)  # 从数据库获取书籍
        return render_template('index.html', books=books)
    finally:
        conn.close()

@app.route('/edit_book', methods=['GET', 'POST'])
def edit_book():
    conn = database.connect_db()
    try:
        book_id = request.args.get('book_id')
        
        # GET请求且没有book_id，显示图书列表
        if request.method == 'GET' and not book_id:
            cur = conn.cursor()
            cur.execute("SELECT title_id, title, type, author_lname, author_fname FROM books ORDER BY title")
            books = cur.fetchall()
            return render_template('edit_book.html', books_list=books)
        
        # 如果提供了book_id，获取图书信息
        if book_id:
            book = database.query_book_info(conn, book_id)
            if not book:
                return render_template('edit_book.html', error="未找到图书")
            
            # 处理POST请求（编辑图书）
            if request.method == 'POST':
                try:
                    title = request.form['title']
                    book_type = request.form['type']
                    author_lname = request.form['author_lname']
                    author_fname = request.form['author_fname']
                    publisher_id = request.form['publisher_id']
                    publisher = request.form['publisher']
                    database.edit_book(conn, book_id, title, book_type, author_lname, author_fname, publisher_id, publisher)
                    return redirect(url_for('book_info', book_id=book_id))
                except Exception as e:
                    return render_template('edit_book.html', error=str(e), book=book)
            
            return render_template('edit_book.html', book=book)
        
        return render_template('edit_book.html', error="请选择要编辑的图书")
    finally:
        conn.close()



@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    conn = database.connect_db()
    error = None
    success = None
    try:
        # 获取所有现有的图书标题
        cur = conn.cursor()
        cur.execute("SELECT title_id, title, type, author_lname, author_fname, pub_id, pub_name FROM books ORDER BY title")
        existing_books = cur.fetchall()
        
        if request.method == 'POST':
            try:
                book_id = request.form['book_id']
                title = request.form['title']
                book_type = request.form['type']
                author_lname = request.form['author_lname']
                author_fname = request.form['author_fname']
                publisher_id = request.form['publisher_id']
                publisher = request.form['publisher']
                
                # 检查是否是重复的标题
                if title in [book[1] for book in existing_books]:
                    error = f"图书《{title}》已存在，请勿重复添加"
                else:
                    database.add_book(conn, book_id, title, book_type, 
                                    author_lname, author_fname, 
                                    publisher_id, publisher)
                    success = f"图书《{title}》添加成功！"
                    # 重新获取更新后的图书列表
                    cur.execute("SELECT title_id, title, type, author_lname, author_fname, pub_id, pub_name FROM books ORDER BY title")
                    existing_books = cur.fetchall()
            except Exception as e:
                error = f"添加图书失败：{str(e)}"
        
        return render_template('add_book.html', 
                             existing_books=existing_books,
                             error=error,
                             success=success)
    finally:
        conn.close()

@app.route('/book_info', methods=['GET'])
def book_info():
    book_id = request.args.get('book_id')
    if not book_id:
        return render_template('book_info.html')
    
    conn = database.connect_db()
    book = database.query_book_info(conn, book_id)
    if not book:
        return render_template('book_info.html', error="未找到图书")

    
    return render_template('book_info.html',
                         book=book,)


@app.route('/procurement', methods=['GET', 'POST'])
@app.route('/procurement/<string:book_id>', methods=['GET', 'POST'])
def procurement(book_id=None):
    conn = database.connect_db()
    try:
        if request.method == 'POST':
            # 从表单获取book_id（如果URL中没有提供）
            book_id = book_id or request.form.get('book_id')
            if not book_id:
                return render_template('edit.html', error="未提供图书ID")
            
            try:
                count = int(request.form['count'])
                date = request.form['datetime']
                database.procurement(conn, book_id, count, date)
                return redirect(url_for('book_info', book_id=book_id))
            except ValueError as e:
                return render_template('edit.html', error="输入数据格式错误")
            except Exception as e:
                return render_template('edit.html', error=str(e))
        else:
            # 从查询参数获取 book_id
            if not book_id:
                book_id = request.args.get('book_id')
            
            if not book_id:
                return render_template('edit.html')

            # 获取图书信息和采购记录
            book = database.query_book_info(conn, book_id)
            if book:
                procurement_records = database.procurement2(conn, book_id)
                return render_template('edit.html', 
                                    book=book, 
                                    procurement_records=procurement_records)
            else:
                return render_template('edit.html', error="未找到图书")
    except Exception as e:
        return render_template('edit.html', error=str(e))
    finally:
        conn.close()

@app.route('/delete', methods=['GET', 'POST'])
@app.route('/delete/<string:book_id>', methods=['GET', 'POST'])
def delete(book_id=None):
    conn = database.connect_db()
    try:
        if request.method == 'POST':
            # 从表单获取book_id（如果URL中没有提供）
            book_id = book_id or request.form.get('book_id')
            if not book_id:
                return render_template('edit.html', error="未提供图书ID")
            
            try:
                count = int(request.form['count'])
                date = request.form['datetime']
                database.eliminate_book(conn, book_id, count, date)
                return redirect(url_for('book_info', book_id=book_id))
            except ValueError as e:
                return render_template('edit.html', error="输入数据格式错误")
            except Exception as e:
                return render_template('edit.html', error=str(e))
        else:
            if not book_id:
                book_id = request.args.get('book_id')
            
            if not book_id:
                return render_template('edit.html')

            book = database.query_book_info(conn, book_id)
            if book:
                elimination_records = database.eliminate_book2(conn, book_id)
                return render_template('edit.html',
                                    book=book,
                                    elimination_records=elimination_records)
            else:
                return render_template('edit.html', error="未找到图书")
    except Exception as e:
        return render_template('edit.html', error=str(e))
    finally:
        conn.close()
    
@app.route('/rent', methods=['GET', 'POST'])
@app.route('/rent/<string:book_id>', methods=['GET', 'POST'])
def rent(book_id=None):
    conn = database.connect_db()
    try:
        if request.method == 'POST':
            # 从表单获取book_id（如果URL中没有提供）
            book_id = book_id or request.form.get('book_id')
            if not book_id:
                return render_template('edit.html', error="未提供图书ID")
            
            try:
                user_id = request.form['user_id']
                rent_date = request.form['rent_date']
                return_date = request.form['return_date']
                database.rent_book(conn, book_id, user_id, rent_date, return_date)
                return redirect(url_for('book_info', book_id=book_id))
            except ValueError as e:
                return render_template('edit.html', error="输入数据格式错误")
            except Exception as e:
                return render_template('edit.html', error=str(e))
        else:
            if not book_id:
                book_id = request.args.get('book_id')
            
            if not book_id:
                return render_template('edit.html')

            book = database.query_book_info(conn, book_id)
            if book:
                rental_records = database.rental2(conn, book_id)
                return render_template('edit.html',
                                    book=book,
                                    rental_records=rental_records[0],
                                    available_count=rental_records[1],
                                    rental_count=rental_records[2])
            else:
                return render_template('edit.html', error="未找到图书")
    except Exception as e:
        return render_template('edit.html', error=str(e))
    finally:
        conn.close()




if __name__ == '__main__':
    app.run(debug=True)
