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


# Initialize Flask-Login to handle user session management
login_manager = LoginManager() 
#Binds the LoginManager instance to the main Flask application
login_manager.init_app(app)
#specifies where the users who are not logged in are being redirected
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
    """
    query: SQL command string to execute
    args: Tuple of values to pass into query parameters
    one: if True, returns only the first result instead of a list
    """
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


# User class model for authentication
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id # Unique database identifier for the user
        self.username = username #user's username
        self.password = password #user's password


#Figures out which user is currently logged in
@login_manager.user_loader
# Retrieves the logged-in user from the database using their ID
def load_user(user_id):
    row = query_db("SELECT * FROM Users WHERE id = ?", (int(user_id),), one=True)
    if row:
        return User(id=row[0], username=row[1], password=row[2])
    return None


#For the Login form
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(),Length( #Input required means it must be filled out
        min=4, max=8)], render_kw={"placeholder": "Username"})  #the other condition is that it must be between 4 to 8 letters
    
    password = PasswordField(validators=[InputRequired(),Length(
        min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Login")


#For the register form
class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(),Length(min=4, max=8)], render_kw={"placeholder": "Username"})  
    
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Register")

    #Checks if the there is currently another username in the database
    def validate_username(self, username): 
        existing_user = query_db("SELECT * FROM Users WHERE username = ?",(username.data,),one=True)
        if existing_user:  #if it returns a row with a matching username then it raises Validation error 
            raise ValidationError()


#For the form displayed on each of the individual question page
class AnswerForm(FlaskForm):
    answer = StringField(validators=[InputRequired(), Length( min=1, max=12)])
    submit = SubmitField('Answer')


@app.route("/")
#Homepage
def home():
    return render_template("home.html")


@app.route("/questions")
#The page that displays all the questions after the user have logged in
def questions():

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
    results = query_db(sql, (), one = False)
    return render_template("questions.html", results=results)



@app.route('/login', methods = ['GET', 'POST'])
#The login page
def login():
    form = LoginForm() #the form for the user to log into their account
    if form.validate_on_submit():
        row =query_db("SELECT * FROM Users WHERE username = ?", (form.username.data, ), one = True)
        if row: #Checks if the username and password that the user put in the form matches an existing user in the database
            user = User(id = row[0], username = row[1], password = row[2])
            if bycrypt.check_password_hash(user.password, form.password.data): # Securely checking the entered password against the stored hashed password using Bcrypt
                login_user(user) #logs the user into the current session
                return redirect(url_for('dashboard')) #redirects the user to dashboard
        else:
            user = None #resets the user to none if existing user was found
    
    return render_template('login.html', form = form)


@app.route('/logout', methods = ['GET','POST'])
#This dosen't have a page but just logs the user out.
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard', methods = ['GET','POST'])
#The user dashboard page
@login_required
def dashboard():
    #The initiall user_score is 0
    rows = query_db("SELECT * FROM UserProgress WHERE user_id = ?",(int(current_user.id), ),one = False)
    user_score = 5*len(rows)
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
#This is the debug page I made for testing
#It displays some of the key element from the question page
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
@login_required #The user needs to be logged in to access this page
#The page that displays each individual question
def question(id):
    print("Method:", request.method)
    display = ''
    solution = ''
    form = AnswerForm()
    if form.validate_on_submit(): #If the user have submitted an answer to the answer form
        sql = """
        SELECT Answer FROM QUESTIONS WHERE QUESTION_ID = ?
        """
        #This is to prevent sql injection
        result = query_db(sql,(id,), one=True)
        if result: #Checks whether there is a answer for this in the database
            correct_answer = result[0] #if there is then the variable "correct_answer" is set to that result
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
            current_tuple = (id, current_user_id, 1)  #The tuple including the current user id, question id, and completion
            if rows: #Checks through all of the questions that the user have solved
                print(rows) 
                rows = list(rows)
                for item in rows:
                    print(f"item {item}")
                    print(f"current_tuple {current_tuple}")
                    print(current_tuple)
                    if item == current_tuple: #if the user have already solved the question (current tuple matches one of the exsiting tuples)
                        display = "You have already answered this question" 
                    else: #if the user have not already solved the question (no row in user progress matches current tuple)
                        cursor.execute( "INSERT INTO UserProgress (Question_ID, User_ID, Progress) VALUES (?,?,?)", current_tuple) #Then adds this row to current tuple
                        db.commit()
                        display = "correct, scroll down for my solution :)" #informs the user that their answer is correct
                else: #if there isnt a row in user that have the user's user_id (The user have not solved any questions yet)
                    cursor.execute( "INSERT INTO UserProgress (Question_ID, User_ID, Progress) VALUES (?,?,?)", current_tuple) #Add this row to the user_progress tbale
                    db.commit()
                    display = "correct, scroll down for my solution :)" #informs the user that their answer is right
        else: #if the user's answer dosent match the correct answer
            display = 'incorrect' #Then it tells the user that their answer is wrong
            print(display)
    
    # Added the WHERE clause andp placeholder
    sql = """
    SELECT 
        Questions.Question_ID, 
        Questions.Question,
        Questions.Description, 
        WhereFrom.Name, 
        Types.Name,
        Types.Type_ID 
    FROM Questions
    JOIN WhereFrom ON Questions.Where_ID = WhereFrom.Where_ID
    JOIN Types ON Questions.Type_ID = Types.Type_ID
    WHERE Questions.Question_ID = ?;
    """
    
    # Pass the id in a tuple to prevent SQL Injection
    results = query_db(sql, (id,), one=True) #grabs all the relevant information about the question
    
    if results is None: # if there are questions with this id
        return "Question not found", 404 #tells the user that there is not a question with a matching id
        
    return render_template("question.html", question=results, form = form, display = display, solution = solution)



@app.route("/types/<int:id>")
#The page that displays only the questions of a certain type
def type(id):
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
        WHERE Types.Type_ID = ?"""
    results = query_db(sql, (id,), one=False) 
    if results: #Checks if there is a type with this id
        result = results[0]
        return render_template("type.html", results=results, result = result)
    else: #if there isnt then returns 404
        return "No Types with this id is found, Currently the ids are 1 for calculus, 2 for geometry, 3 for algebra, 4 for counting, and 5 for number theory ", 404
    


@app.route("/about")
#The about page
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True)

#<h1>DEBUG: {{ question }}</h1>

