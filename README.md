# Small-scale-Library-Management-System

> <p><strong>课程：</strong> 数据库基础 Lab5</p>
> <p><strong>作者：</strong> stu: iiiiiamabird </p>
> <p><strong>日期：</strong> 2025年11月7日</p>

[toc]   

## 0. 实验简介

本实验旨在连接opengauss实验数据库，通过python嵌入式SQL语句实现程序与数据库的交互，同时通过制作网页界面使得图书管理系统形象化，便于交互。该系统实现的功能有：

1. **图书查询**：通过输入正确的图书ID，查询到图书库里的图书，如果输入的的图书ID不正确，则刷新页面重新输入。
2. **添加新图书**：给出系统现有图书列表，方便进行查询已有图书，下方根据具体的图书所需字段一一填写，如果发现书名与现有图书列表里的图书书名重复，则简化为同一本书，不予以添加。
3. **编辑图书**：给出系统现有图书列表，每本书都设有编辑按钮，进行编辑时，给出该图书现有的信息字段，下方提供修改页面。
4. **采购、借阅、淘汰图书**：根据用户提供的图书ID进行查询，给出已有采购（借阅、淘汰）信息，下方给出对应功能，规定每次借阅最多借阅一本。


- 实验环境以及工具：vscode，python，Flask，psycopg2
- 采用 try-except-commit-rollback模式
- 采购/淘汰/借阅都有库存量校验

### 0.1 实验原理与具体步骤

```
├── project/                # 实验核心代码
│   ├── app.py              # Flask应用入口
│   ├── database.py         # 主要的ESQL函数
│   └── templates           # 网页视图层
│       ├── add_book.html         # 添加图书记录
│       ├── book_info.html        # 图书详情查询
│       ├── edit_book.html        # 图书信息编辑
│       ├── edit.html             # 采购、借阅、淘汰
│       └── index.html            # 主页，展示统计信息和快速操作入口   
└── report.md               # 实验流程报告
```

- **实验表格设计**：

  - 通过状态反映出书籍是否已经被淘汰
  - 通过总的书籍数量减去在库书籍数量反映借阅出去的数量
  - 在库书籍数量反映可借阅的数量
  - 如果淘汰的书籍数目达到在库书籍数量，则记录state为已淘汰
  - 如果淘汰的书籍有被借阅，则不允许淘汰
  - books表以title_id作为主键

`books`
|  title_id  |  title  | type | author_lname | author_fname | pub_id | pub_name | state | all_count | avai_count |
|---------|---------|---------|---------|---------|---------|---------|---------|---------|---------|
| 书籍id | 书名 | 书籍类型 | 作者姓 | 作者名 | 出版社id | 出版社名 | 状态（在库/淘汰） | 总的书籍数量 | 在库书籍数量 |


`procurement`
| title_id | count | datetime |
|---------|---------|---------|
| 书籍id | 采购数量 | 采购时间 |

`Eliminated_books`
| title_id | count | datetime |
|---------|---------|---------|
| 书籍id | 淘汰数量 | 淘汰时间 |

`rental`
| title_id | ID | out_time | back_time |
|---------|---------|---------|---------|
| 书籍id | 借阅人ID | 借出时间 | 归还时间 |




- **连接opengauss数据库**：
通过psycopg2模块，连接到课程实验数据库
```bash
    def connect_db():
        conn = psycopg2.connect(database="student", user="student", password="...", host="202.38.88.80", port="5432")
        return conn
```

- **编写具体ESQL函数**：`database.py`模块   
    + 统计图书信息：
        - 图书种类总数
        - 图书总册数
        - 可借图书册数
        - 已淘汰图书种类数
        - 已淘汰图书册数
        - 已采购图书册数
        - 已租借图书册数
  
    - 以淘汰书籍的函数为例：
```bash
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
```   


- **创建路由文件**：`app.py`模块
    - 七个部分：
```
@app.route('/') -> index() #显示主页，输出书籍的各项统计结果
@app.route('/edit_book', methods=['GET','POST']) -> edit_book() #编辑图书
@app.route('/add_book', methods=['GET','POST']) -> add_book() #添加新书
@app.route('/book_info', methods=['GET']) -> book_info() #显示书籍详细信息
@app.route('/procurement', ... ) -> procurement() #处理图书采购
@app.route('/delete', ...) -> delete() #图书淘汰
@app.route('/rent', ...) -> rent() #图书借阅
```

- **网页渲染**：`templates`文件夹
    - 所有模板统一采用马卡龙色系设计；使用Bootstrap 4.5.2和Front Awesome图标
    - `index.html`：主页页面，展示统计信息，和其他功能的操作入口按钮
    - `edit_book.html`：通过books_list获取图书系统的图书列表，每行操作按钮链接到编辑图书，上半部分展示当前图书信息，下半部分展示可编辑的表单（书名、类型、作者姓名、出版社id、出版社名称）
    - `add_book.html`：添加新图书记录，初始状态均为已淘汰，总数量和在库数量均为0。如果书名已经存在则拒绝添加
    - `book_info.html`：通过图书id查询图书具体信息，另外该页面还可以进入对应这本书籍的采购、淘汰、借阅页面
    - `edit.html`：根据URL的路径动态切换为采购/淘汰/借阅模式，



### 0.2 实验总结
- 反思：
  - 通过这个实验，掌握ESQL的函数编写，以及实现数据库和python程序的交互
  - 通过实现网页交互，掌握基础的网页编写方法
  - 通过设计数据表格，理清逻辑结构，以及合理的图书系统管理方法
- 不足：
  - 该系统没有实现借阅数量的多样化，默认一次只可借阅一本，不够便利
  - 系统没有设计书籍归还的数据统计，借阅出的书籍如果归还还需要页面记录数据，同时更新到数据库里；对应归还书籍后，可能还需要对借阅记录做一定的标注，如：添加属性：已归还/未归还
