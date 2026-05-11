from flask import Flask, g, render_template, url_for, redirect
import sqlite3
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt


DATABASE = 'database.db'

#Creates the app
app = Flask(__name__)
bycrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'TsISisdsihihsieref'


login_manager = LoginManager() 
login_manager.init_app(app)
login_manager.login_view = "login"

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


class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password



@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.execute("SELECT * FROM user WHERE id = ?", (int(user_id),))
    row = cursor.fetchone()
    
    if row:
        return User(id=row['id'], username=row['username'])
    return None



class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired()], render_kw={"placeholder": "Username"})  #the other condition is that it must be between 4 to 20 letters
    
    password = PasswordField(validators=[InputRequired()], render_kw={"placeholder": "Password"})

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

@app.route("/questions")
#The page that displays all the questions after the user have logged in
def questions():
    db = get_db()
    cursor = db.cursor()
    sql = """
    SELECT 
    Questions.Question_ID, 
    Questions.Question, 
    Questions.Solution, 
    WhereFrom.Name AS SourceName, 
    Types.Name AS CategoryName
    FROM Questions
    JOIN WhereFrom ON Questions.Where_ID = WhereFrom.Where_ID
    JOIN Types ON Questions.Type_ID = Types.Type_ID;
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return render_template("questions.html", results=results)


@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM Users WHERE username = ?", (int(form.username.data, )))
        row = cursor.fetchone
        if row:
            user = User(id = row['id'], username = row['username'], password = row['password'])
        else:
            user = None
    
    return render_template('login.html', form = form)


@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bycrypt.generate_password_hash(form.password.data) #this hashes the password

        db = get_db() #connects to db 
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO Users (username, password) VALUES (?, ?)", #inserts the username and hashed password into the database
            (form.username.data, hashed_password)
        )

        db.commit() #saves the changes
        return redirect(url_for('login')) #redirects them to the login form after the user have registered
        
    return render_template('register.html', form = form)



@app.route("/question/<int:id>")
def question(id):
    sql = """
    SELECT * FROM Questions
    JOIN WhereFrom ON WhereFrom.Where_ID = Questions.Where_ID
    WHERE Questions.Question_ID = ?;
    """
    results = query_db(sql, (id,), True)
    return render_template("question.html", question=results)


@app.route('/dashboard', methods = ['GET','POST'])
@login_required
def dashboard():
    return render_template("dashboard.html")




if __name__ == "__main__":
    app.run(debug=True)

