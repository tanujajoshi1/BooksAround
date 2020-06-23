import os, json
import csv
from flask import Flask, session,render_template,request,redirect,flash,url_for,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
from helpers import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():	
    return render_template('index.html')



@app.route("/login")
def login():	
    return render_template('login.html')



@app.route("/check_login",methods=["POST"])
def check_login():
	session.clear()
	uname=request.form.get("id")
	pwd=request.form.get("password")

	if not uname:
		return render_template("error.html", message="Please provide the username")
	elif not pwd:
		return render_template("error.html", message="Please provide the password")
	user=db.execute("SELECT username FROM users WHERE username=:username AND password=:password",
		{"username":uname, "password":pwd}).fetchone()
	if user is None:
		return render_template("error.html", message="No such user found")
	session["user"]= user
	return redirect(url_for("user"))



@app.route("/user")

def user():
	
	if "user" in session:
		user=session["user"]
		user=str(user)
		user=user[2:-3]
		return render_template("search.html",user=user)
	else:
		return render_template("error.html", message="You need to login first")

@app.route("/search" , methods=["POST"])
@login_required
def search():	
	if "user" in session:
		user=session["user"]
		user=str(user)
		user=user[2:-3]
		book=request.form.get("books")	
		if not book:
			return render_template("error.html",message="Provide a book first")
		query="'%" + book + "%'"
		query=query.title()
		row = db.execute("SELECT * FROM books WHERE isbn LIKE" +query+"OR title LIKE"+query+"OR author LIKE"+query+"LIMIT 15" ).fetchall()


	
		if not row:
			return render_template("error.html", message="No results found. Try something different")
		else:
			return render_template("search.html",books=row,user=user)


@app.route("/book/<isbn>", methods=["GET", "POST"])
@login_required
def book(isbn):
	if "user" in session:
		user=session["user"]
		user=str(user)
		user=user[2:-3]
		if request.method=="POST":
		
			rating=request.form.get("rating")
			comment=request.form.get("comment")

			bookid=db.execute("SELECT id FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
			bookid=bookid[0]

			row=db.execute("SELECT * FROM reviews WHERE user_name=:user_name AND book_id=:book_id",{"user_name":user,"book_id":bookid})
			

			if row.rowcount==1:
				flash('You have already submitted review for this book', 'warning')
				return redirect("/book/" + isbn)

			rating=int(rating)

			db.execute("INSERT INTO reviews(user_name,book_id,comment,rating)VALUES \
				(:user_name, :book_id, :comment, :rating)",
				{"user_name":user,
				"book_id":bookid,
				"comment":comment,
				"rating":rating})
			db.commit()
			flash('Thanks for submitting the review!')
			return redirect("/book/"+ isbn)

		else:
			bookinfo=db.execute("SELECT * FROM books WHERE isbn= :isbn",{"isbn":isbn}).fetchall()
			#goodreads review

			response=requests.get("https://www.goodreads.com/book/review_counts.json",params={"key":'A3D8TXrW82vnrssWEcAAyQ',"isbns":isbn}).json()
		
			response=response['books'][0]
			bookinfo.append(response)
			##user review
			book=db.execute("SELECT id FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
			book=book[0]

			#Fetch book reviews
			reviews=db.execute("SELECT users.username, comment, rating FROM users INNER JOIN reviews ON users.username = reviews.user_name WHERE book_id = :book ORDER BY reviews.id",{"book": book}).fetchall()
			return render_template("review.html",bookinfo=bookinfo, reviews=reviews, user=user)


@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api_call(isbn):
	row=db.execute("SELECT title, author, year, isbn, \
                    COUNT(reviews.id) as review_count, \
                    AVG(reviews.rating) as average_score \
                    FROM books \
                    INNER JOIN reviews \
                    ON books.id = reviews.book_id \
                    WHERE isbn = :isbn \
                    GROUP BY title, author, year, isbn",
                    {"isbn": isbn})
	if row.rowcount!=1:
		return jsonify({"Error":"Invalid book isbn"}),422
	tmp=row.fetchone()
	result=dict(tmp.items())
	result['average_score']=float('%.2f'%(result['average_score']))
	return jsonify(result)





@app.route("/logout")
def logout():
	session.clear()
	return redirect(url_for('index'))

@app.route("/register")
def register():
	return render_template('register.html')



@app.route("/check_register",methods=["POST"])
def check_register():
	uname=request.form.get("id")
	pwd=request.form.get("password")
    ##Check if username is entered
	if not uname:				
		return render_template("error.html", message="Must provide username")
  
	userCheck=db.execute("SELECT * FROM users WHERE username=:username",{"username":uname}).fetchone()

	if userCheck:				
		return render_template("error.html", message="Username already exists!!")
	elif not pwd:		
		return render_template("error.html", message="Must provide password")

	elif not request.form.get("reconfirm"):
		return render_template("error.html", message="Confirm your password")
	elif not pwd == request.form.get("reconfirm"):
		return render_template("error.html", message="Password didn't match")
	else:
		db.execute("INSERT INTO users (username,password) VALUES(:username,:password)",{"username":uname, "password":pwd})
		db.commit()
		flash("You have successfully registered on BooksAround")	
		return redirect("/login")

	    
