"""flask application database utilities and route handlers"""

import sqlite3
from flask import Flask, g, redirect, render_template, request, url_for
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError


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
    """This function is responsible for connecting the database"""
    #This line sets g._database to none if it dosen't already exist
    db = getattr(g, '_database', None)
    if db is None: #if db is none, it then creates a new connection and stores it inside of g
        db = g._database = sqlite3.connect(DATABASE)
    return db



@app.teardown_appcontext #This runs automatically when the app context ends
def close_connection(exception):
    """Close the database connection at the end of the request context."""
    if exception:
        app.logger.error("Teardown error: %s", exception)
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
    """"This function is responsible for authenticating the user"""
    def __init__(self, id_, username, password):
        self.id = id_ # Unique database identifier for the user
        self.username = username #user's username
        self.password = password #user's password


#Figures out which user is currently logged in
@login_manager.user_loader
def load_user(user_id):
    """This function retrieves the logged-in user from the database using their ID"""
    row = query_db("SELECT * FROM Users WHERE id = ?", (int(user_id),), one=True)
    if row:
        return User(id_=row[0], username=row[1], password=row[2])
    return None


#For the Login form
class LoginForm(FlaskForm):
    """Form for handling user login"""
    #Input required means it must be filled out
    #the other condition is that it must be between 4 to 8 letters
    username = StringField(validators=[InputRequired(),Length(
        min=4, max=8)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(),Length(
        min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Login")


#For the register form
class RegisterForm(FlaskForm):
    """Form for handling user signing up"""
    username = StringField(validators=[InputRequired(),Length(min=4, max=8)],
    render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)],
    render_kw={"placeholder": "Password"})

    submit = SubmitField("Register")


    def validate_username(self, username):
        """This is the function for checking if the username already exist"""
        existing_user = query_db("SELECT * FROM Users WHERE username = ?",(username.data,),one=True)
        if existing_user:
        #if it returns a row with a matching username then it raises Validation error
            raise ValidationError()


#For the form displayed on each of the individual question page
class AnswerForm(FlaskForm):
    """This is the form responsible for the answers that the user submits for
    the individual questions"""
    answer = StringField(validators=[InputRequired(), Length( min=1, max=12)])
    submit = SubmitField('Answer')


@app.route("/")
#Homepage
def home():
    """Renders the homepage"""
    return render_template("home.html")


@app.route("/questions")
#The page that displays all the questions after the user have logged in
def questions():
    """Renders the page that displays all the questions"""
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
    """Renders the page for the user to log in"""
    form = LoginForm() #the form for the user to log into their account
    if form.validate_on_submit():
        row =query_db("SELECT * FROM Users WHERE username = ?", (form.username.data, ), one = True)
        #Checks if the username and password matches an existing user in the database
        if row: #if it matches
            user = User(id_ = row[0], username = row[1], password = row[2])
            if bycrypt.check_password_hash(user.password, form.password.data):
                #checks the entered password against the stored hashed password using Bcrypt
                login_user(user) #logs the user into the current session
                return redirect(url_for('dashboard')) #redirects the user to dashboard
        else:
            user = None #resets the user to none if existing user was found

    return render_template('login.html', form = form)


@app.route('/logout', methods = ['GET','POST'])
#This dosen't have a page but just logs the user out.
@login_required
def logout():
    """This function logs the user out"""
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard', methods = ['GET','POST'])
#The user dashboard page
@login_required
def dashboard():
    """This is responisble for displaying the user dashboard page"""
    #The initiall user_score is 0
    rows = query_db("SELECT * FROM UserProgress WHERE user_id = ?",(int(current_user.id), ),
    one = False)#Gets the numbers of questions that the user has solved
    user_score = 5*len(rows)#Since each question is worth 5 points
    return render_template("dashboard.html", user_score = user_score)



@app.route('/register', methods = ['GET', 'POST'])
def register():
    """This is responsible for displaying the register page"""
    form = RegisterForm()

    if form.validate_on_submit():
        #this hashes the password
        hashed_password = bycrypt.generate_password_hash(form.password.data)

        db = get_db() #connects to db
        cursor = db.cursor()

        #inserts the username and hashed password into the database
        cursor.execute(
            "INSERT INTO Users (username, password) VALUES (?, ?)",
            (form.username.data, hashed_password)
        )

        db.commit() #saves the changes
        #redirects them to the login form after the user have registered
        return redirect(url_for('login'))

    return render_template('register.html', form = form)



@app.route("/debug/<int:id>", methods = ['GET', 'POST'])
#This is the debug page I made for testing
#It displays some of the key element from the question page (You can ignore this page)
def debug(id_):
    """This is respobsible for displaying the debug page"""
    correct = ""
    form = AnswerForm()
    sql = """
        SELECT Answer FROM QUESTIONS WHERE QUESTION_ID = ?
        """
    result = query_db(sql,(id_,), one=True)
    correct_answer = result[0]
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


    return render_template("debug.html", correct_answer = correct_answer,
    correct = correct, form = form)



@app.route("/question/<int:id_>", methods = ['GET', 'POST'])
@login_required #The user needs to be logged in to access this page
#The page that displays each individual question
def question(id_):
    """This is responsible for displaying the page for each individual question"""
    print("Method:", request.method)
    solved = False
    display = ''
    solution = ''
    form = AnswerForm()
    if form.validate_on_submit(): #If the user have submitted an answer to the answer form
        sql = """
        SELECT Answer FROM QUESTIONS WHERE QUESTION_ID = ?
        """
        #This is to prevent sql injection
        result = query_db(sql,(id_,), one=True)
        if result: #Checks whether there is a answer for this in the database
            correct_answer = result[0]
            #if there is then the variable "correct_answer" is set to that result
        else:
            correct_answer = None
        if form.answer.data == correct_answer: #checks if the answer is correct
            current_user_id = current_user.id #Gets the user's id
            #Gets the solution only after the right answer is submitted
            sql = "SELECT Questions.Solution FROM Questions WHERE Questions.Question_ID = ?"
            solution = query_db(sql, (id_,), one=True)
            if solution:
                solution = solution[0]

            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM UserProgress WHERE user_id = ?", (int(current_user_id),))
            rows = cursor.fetchall() #gets the rows where the user id matches the current user's id
            current_tuple = (id_, current_user_id, 1)
            #The tuple including the current user id, question id, and completion
            if rows:
            #Checks through all of the questions that the user have solved
                print(rows)
                rows = list(rows)
                for item in rows:
                    print(f"item {item}")
                    print(f"current_tuple {current_tuple}")
                    print(current_tuple)
                    #if the user have already solved the question
                    #(current tuple matches one of the exsiting tuples)
                    if item == current_tuple:
                        solved = True
                if solved is True:
                    display = "You have already answered this question"
                #if the user have not already solved the question
                #(no row in user progress matches current tuple)
                else:
                    cursor.execute(
                    "INSERT INTO UserProgress (Question_ID, User_ID, Progress)"
                    "VALUES (?, ?, ?)",
                    current_tuple,
                    )
                    #Then adds this row to current tuple
                    db.commit()
                    display = "correct, scroll down for my solution :)"
                    #informs the user that their answer is correct
            else:
                #if there isnt a row in user that have the user's user_id
                #(The user have not solved any questions yet)
                cursor.execute( "INSERT INTO UserProgress (Question_ID, User_ID, Progress)"
                "VALUES (?,?,?)", 
                current_tuple,
                )
                #Add this row to the user_progress tbale
                db.commit()
                display = "correct, scroll down for my solution :)"
                #informs the user that their answer is right
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
    results = query_db(sql, (id_,), one=True) #grabs all the relevant information about the question

    if results is None: #if there are questions with this id
        return "Question not found", 404
        #tells the user that there is not a question with a matching id

    return render_template("question.html",
    question=results, form = form, display = display, solution = solution)



@app.route("/types/<int:id_>")
#The page that displays only the questions of a certain type
def _type(id_):
    """This is responbsible for diaplying all the questions with a certain type"""
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
    results = query_db(sql, (id_,), one=False)
    if results: #Checks if there is a type with this id
        result = results[0]
        return render_template("type.html", results=results, result = result)
    else: #if there isnt then returns 404
        return "No Types with this id is found", 404


@app.route("/about")
#The about page
def about():
    """This is responsible for rendering the about page"""
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True)

#<h1>DEBUG: {{ question }}</h1>
