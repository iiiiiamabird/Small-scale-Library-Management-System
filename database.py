import psycopg2

# connect to the PostgreSQL database
def connect_db():
    conn = psycopg2.connect(database="student", user="student", password="...", host="202.38.88.80", port="5432")
    return conn

#添加书籍
def add_book(conn, book_id, title, type, author_lname, author_fname, publisher_id, publisher):
    try:
        cur = conn.cursor()
        cur.execute("select title from books")
        if not (title in [row[0] for row in cur.fetchall()]):
            cur.execute("""
                INSERT INTO books (title_id, title, type, author_lname, author_fname, pub_id, pub_name, state, all_count, avai_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (book_id, title, type, author_lname, author_fname, publisher_id, publisher, "已淘汰", 0, 0))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()

# 修改图书信息
def edit_book(conn, book_id, title, type, author_lname, author_fname, publisher_id, publisher):
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE books
            SET title = %s,
                type = %s,
                author_lname = %s,
                author_fname = %s,
                pub_id = %s,
                pub_name = %s
            WHERE title_id = %s
        """, (title, type, author_lname, author_fname, publisher_id, publisher, book_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()


#采购
def procurement(conn,book_id,count,date):
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO procurement (title_id, count, datetime) VALUES (%s, %s, %s)", (book_id, count, date))
        cur.execute("UPDATE books SET state = '在库', all_count = all_count + %s, avai_count = avai_count + %s WHERE title_id = %s", (count, count, book_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()

#淘汰
def eliminate_book(conn,book_id,count,date):
    try:
        cur = conn.cursor()
        # 获取当前库存信息
        cur.execute("SELECT all_count, avai_count FROM books WHERE title_id = %s", (book_id,))
        result = cur.fetchone()
        if not result:
            raise Exception("图书不存在")
        
        all_count, avai_count = result

        if avai_count < all_count:
            raise Exception("无法淘汰已借出的图书")
        if avai_count - count < 0:
            raise Exception("淘汰数量超过可用库存")

        # 插入淘汰记录
        cur.execute("INSERT INTO Eliminated_books (title_id, count, datetime) VALUES (%s, %s, %s)", (book_id, count, date))
        
        # 更新图书状态
        if avai_count - count == 0:
            cur.execute("UPDATE books SET state = '已淘汰', all_count = 0, avai_count = 0 WHERE title_id = %s", (book_id,))
        else:
            cur.execute("UPDATE books SET all_count = all_count - %s, avai_count = avai_count - %s WHERE title_id = %s", (count, count, book_id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()

#租借
def rent_book(conn, book_id, user_id, rent_date, return_date):
    try:
        cur = conn.cursor()
        # 检查可用库存
        cur.execute("SELECT avai_count FROM books WHERE title_id = %s", (book_id,))
        result = cur.fetchone()
        if not result:
            raise Exception("图书不存在")
        
        avai_count = result[0]
        if avai_count <= 0:
            raise Exception("没有可借阅的库存")

        # 创建租借记录并更新库存
        cur.execute("INSERT INTO rental (title_id, id, out_time, back_time) VALUES (%s, %s, %s, %s)", 
                   (book_id, user_id, rent_date, return_date))
        cur.execute("UPDATE books SET avai_count = avai_count - 1 WHERE title_id = %s", (book_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()

# 3）实现图书信息、采购和淘汰、库存、和租借情况查询 

def query_book_info(conn, book_id):
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM books WHERE books.title_id = %s", (book_id,))
        book_info = cur.fetchone()
        return book_info
    finally:
        cur.close()

def procurement2(conn, book_id):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                title_id,
                datetime as procurement_date,
                count as procurement_count
            FROM procurement 
            WHERE title_id = %s
            ORDER BY datetime DESC
        """, (book_id,))
        procurement_info = cur.fetchall()
        return procurement_info
    finally:
        cur.close()

def eliminate_book2(conn, book_id):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                title_id,
                datetime as elimination_date,
                count as elimination_count
            FROM Eliminated_books 
            WHERE title_id = %s
            ORDER BY datetime DESC
        """, (book_id,))
        eliminate_info = cur.fetchall()
        return eliminate_info
    finally:
        cur.close()

def rental2(conn, book_id):
    cur = conn.cursor()
    try:
        # 获取租借记录
        cur.execute("""
            SELECT 
                title_id,
                id as user_id,
                out_time as rental_date,
                back_time as return_date
            FROM rental 
            WHERE title_id = %s
            ORDER BY out_time DESC
        """, (book_id,))
        rental_info = cur.fetchall()
        
        # 获取可用和已借出数量
        cur.execute("SELECT avai_count, all_count-avai_count FROM books WHERE title_id = %s", (book_id,))
        result = cur.fetchone()
        if result:
            available_count, rental_count = result
        else:
            available_count, rental_count = 0, 0
            
        return rental_info, available_count, rental_count
    finally:
        cur.close()


# 4）实现图书的采购、库存、淘汰、租借情况等统计

def statistics(conn):
    cur = conn.cursor()
    try:
        # 获取基本统计信息
        cur.execute("""
            SELECT 
                COUNT(*) as total_books,
                SUM(all_count) as total_copies,
                SUM(avai_count) as available_copies,
                COUNT(CASE WHEN state = '已淘汰' THEN 1 END) as eliminated_titles,
                SUM(all_count - avai_count) as rented_copies
            FROM books
        """)
        basic_stats = cur.fetchone()
        
        # 获取采购总数
        cur.execute("SELECT COALESCE(SUM(count), 0) FROM procurement")
        procured_copies = cur.fetchone()[0] or 0
        
        # 获取淘汰总数
        cur.execute("SELECT COALESCE(SUM(count), 0) FROM Eliminated_books")
        eliminated_copies = cur.fetchone()[0] or 0
        
        return {
            "图书种类总数": basic_stats[0] or 0,
            "图书总册数": basic_stats[1] or 0,
            "可借图书册数": basic_stats[2] or 0,
            "已淘汰图书种类数": basic_stats[3] or 0,
            "已淘汰图书册数": eliminated_copies,
            "已采购图书册数": procured_copies,
            "已租借图书册数": basic_stats[4] or 0
        }
    finally:
        cur.close()
