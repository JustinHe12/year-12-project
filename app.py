from flask import Flask, g, render_template
import sqlite3

DATABASE = 'database.db'

#Creates the app
app = Flask(__name__)

def get_db():
    db = getattr(g, '_database', None) #This line sets g._database to none if it dosen't already exist
    if db is None: #if db is none, it then creates a new connection and stores it inside of g
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext #This runs automatically when the app context ends
def close_connection(exception): 
    db = getattr(g, '_database', None) 
    if db is not None: #closes connection if there is still one active
        db.close()

def query_db(query, args=(), one=False): 
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv




@app.route("/")
#Homepage
def home():
    db = get_db()
    cursor = db.cursor()
    sql = """ 
        SELECT Questions.Question_ID, WhereFrom.Name, Questions.Question, Types.name
        FROM Questions
        LEFT JOIN WhereFrom ON WhereFrom.Where_ID = Questions.Where_ID
        LEFT JOIN Types ON Types.Type_ID = Questions.Type_ID;
"""
    cursor.execute(sql)
    results = cursor.fetchall()
    return render_template("home.html", results=results)


@app.route("/questions/<int:id>")
def questions(id):
    sql = """
    SELECT * FROM Questions
    JOIN WhereFrom ON WhereFrom.Where_ID = Questions.Where_ID
    WHERE Questions.Question_ID = ?;
    """
    results = query_db(sql, (id,), True)
    return render_template("question.html", question=results)

if __name__ == "__main__":
    app.run(debug=True)




