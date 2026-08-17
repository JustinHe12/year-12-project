from flask import Flask, g, render_template, url_for, redirect, request
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
app.config['SECRET_KEY'] = 'secretkey123'


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
    cursor = db.execute("SELECT * FROM Users WHERE id = ?", (int(user_id),))
    row = cursor.fetchone()
    
    if row:
        return User(id=row[0], username=row[1], password=row[2])
    return None



class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(),Length(min=4, max=8)], render_kw={"placeholder": "Username"})  #the other condition is that it must be between 4 to 20 letters
    
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Register")

    def validate_username(self, username): 
        existing_user = query_db(
            "SELECT * FROM Users WHERE username = ?",
            (username.data,),
            one=True
        )

        if existing_user:   
            raise ValidationError()


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(),Length( #Input required means it must be filled out
        min=4, max=8)], render_kw={"placeholder": "Username"})  #the other condition is that it must be between 4 to 20 letters
    
    password = PasswordField(validators=[InputRequired(),Length(
        min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Login")



class AnswerForm(FlaskForm):
    answer = StringField(validators=[InputRequired(), Length( min=1, max=12)])
    submit = SubmitField('Answer')


@app.route("/")
#Homepage
def home():
    return render_template("home.html")

@app.route("/questions")
@login_required
#The page that displays all the questions after the user have logged in
def questions():
    db = get_db()
    cursor = db.cursor()
    sql = """
    SELECT 
    Questions.Question_ID, 
    Questions.Question, 
    Questions.Solution, 
    WhereFrom.Name, 
    Types.Name
    FROM Questions
    JOIN WhereFrom ON Questions.Where_ID = WhereFrom.Where_ID
    JOIN Types ON Questions.Type_ID = Types.Type_ID;
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return render_template("questions.html", results=results)

@app.route('/rough')
def rough():
    sql = """
    SELECT Rough FROM Questions
    """
    results = query_db(sql,(id,), one= True)
    return render_template("rough.html", results = results)



@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM Users WHERE username = ?", (form.username.data, ))
        row = cursor.fetchone()
        if row:
            user = User(id = row[0], username = row[1], password = row[2])
            if bycrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
        else:
            user = None
    
    return render_template('login.html', form = form)


@app.route('/logout', methods = ['GET','POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard', methods = ['GET','POST'])
@login_required
def dashboard():
    user_score = 0
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM UserProgress WHERE user_id = ?", (int(current_user.id),))
    rows = cursor.fetchall() 
    if rows: 
        for item in rows:
            user_score = user_score + 5
    return render_template("dashboard.html", user_score = user_score)



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



@app.route("/debug/<int:id>", methods = ['GET', 'POST'])
def debug(id):
    correct = ""
    form = AnswerForm()
    sql = """
        SELECT Answer FROM QUESTIONS WHERE QUESTION_ID = ?
        """
    result = query_db(sql,(id,), one=True)
    correct_answer = result[0]
    if correct_answer == None:
        correct_answer = "none"
    print("Method:", request.method)
    print("Validate:", form.validate_on_submit())
    print("Errors:", form.errors)
    if form.validate_on_submit():
        print("This form is working")
        if form.answer.data == correct_answer:
            correct = "correct"
        else:
            correct = "incorrect"
    else:
        print("this is not working")


    return render_template("debug.html", correct_answer = correct_answer, correct = correct, form = form)


@app.route("/question/<int:id>", methods = ['GET', 'POST'])
@login_required
def question(id):
    print("Method:", request.method)
    display = ''
    solution = ''
    form = AnswerForm()
    if form.validate_on_submit():
        sql = """
        SELECT Answer FROM QUESTIONS WHERE QUESTION_ID = ?
        """
        #This is to prevent sql injection
        result = query_db(sql,(id,), one=True)
        if result:
            correct_answer = result[0]
        else:
            correct_answer = None
        if form.answer.data == correct_answer: #checks if the answer is correct
            current_user_id = current_user.id #Gets the user's id
            #Gets the solution only after the right answer is submitted
            sql = "SELECT Questions.Solution FROM Questions WHERE Questions.Question_ID = ?"
            solution = query_db(sql, (id,), one=True)
            if solution:
                solution = solution[0]

            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM UserProgress WHERE user_id = ?", (int(current_user_id),))
            rows = cursor.fetchall() #gets the rows where the user id matches the current user's id
            solved = False
            current_tuple = (id, current_user_id, 1)  #The tupe including the current user id, question id, and completion
            if rows: 
                print(rows)
                rows = list(rows)
                for item in rows:
                    print(f"item {item}")
                    print(f"current_tuple {current_tuple}")
                    print(current_tuple)
                    if item == current_tuple:

                        solved = True
                if solved == True: 
                    display = "You have already answered this question"
                else:
                    cursor.execute( "INSERT INTO UserProgress (Question_ID, User_ID, Progress) VALUES (?,?,?)", current_tuple)
                    db.commit()
                    display = "correct"
            else:
                cursor.execute( "INSERT INTO UserProgress (Question_ID, User_ID, Progress) VALUES (?,?,?)", current_tuple)
                db.commit()
                display = "correct"
                    

        else:
            display = 'incorrect'
            print(display)
    
    # Added the WHERE clause andp placeholder
    sql = """
    SELECT 
        Questions.Question_ID, 
        Questions.Question,
        Questions.Description, 
        WhereFrom.Name, 
        Types.Name 
    FROM Questions
    JOIN WhereFrom ON Questions.Where_ID = WhereFrom.Where_ID
    JOIN Types ON Questions.Type_ID = Types.Type_ID
    WHERE Questions.Question_ID = ?;
    """
    
    # Pass the id in a tuple to prevent SQL Injection
    results = query_db(sql, (id,), one=True)
    
    if results is None:
        return "Question not found", 404
        
    return render_template("question.html", question=results, form = form, display = display, solution = solution)




if __name__ == "__main__":
    app.run(debug=True)

#<h1>DEBUG: {{ question }}</h1>

