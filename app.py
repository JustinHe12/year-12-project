from flask import Flask, g, render_template, url_for
import sqlite3
from flask_login import UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError

DATABASE = 'database.db'

#Creates the app
app = Flask(__name__)

app.config['SECRET_KEY'] = 'TsISisdsihihsieref'


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




class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(),Length( #Input required means it must be filled out
        min=4, max=20)], render_kw={"placeholder": "Username"})  #the other condition is that it must be between 4 to 20 letters
    
    password = PasswordField(validators=[InputRequired(),Length(
        min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Register")

    def validate_username(self, username): #Checks whether the username already exixts in the database Users
        existing_user = query_db(
            "SELECT * FROM Users WHERE username = ?",
            (username.data,),
            one=True
        )

        if existing_user:   
            raise ValidationError("That username is already taken.")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(),Length( #Input required means it must be filled out
        min=4, max=20)], render_kw={"placeholder": "Username"})  #the other condition is that it must be between 4 to 20 letters
    
    password = PasswordField(validators=[InputRequired(),Length(
        min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Login")



@app.route("/")
#Homepage
def home():
    return render_template("home.html")



@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    return render_template('login.html', form = form)


@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm()
    return render_template('register.html', form = form)



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

"""   db = get_db()
    cursor = db.cursor()
    sql =  
        SELECT Questions.Question_ID, WhereFrom.Name, Questions.Question, Types.name
        FROM Questions
        LEFT JOIN WhereFrom ON WhereFrom.Where_ID = Questions.Where_ID
        LEFT JOIN Types ON Types.Type_ID = Questions.Type_ID;

    cursor.execute(sql)
    results = cursor.fetchall()
    return render_template("home.html", results=results)"""


