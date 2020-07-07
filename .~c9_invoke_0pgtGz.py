import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT * FROM current WHERE id = :userid", userid=session["user_id"])
    total = db.execute("SELECT SUM(total) FROM current WHERE id= :userid", userid=session["user_id"])

    if total[0]["SUM(total)"] == None:
        total[0]["SUM(total)"]=0

    balance = db.execute("SELECT cash FROM users WHERE id= :userid", userid=session["user_id"])
    return render_template("index.html", stocks=stocks, total=total, balance=balance)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    else:
        symbol = request.form.get("symbol")
        symbol = lookup(symbol)
        shares = int(request.form.get("shares"))
        price = int(symbol["price"])

        if symbol == None:
            return apology("Symbol is not vaild", 403)
        cash = db.execute("SELECT cash FROM users WHERE id = :name", name=session["user_id"])
        balance=int(cash[0]["cash"])

        if balance < price*shares:
            return render_template("apology.html", message="Insufficient Cash.")
        else:
            db.execute("INSERT INTO history (id, symbol, shares, price) VALUES (:userid, :symbol, :shares, :price)",userid=session["user_id"], symbol=symbol["symbol"], shares=shares, price=price)
            stock = db.execute("SELECT count(symbol) from current WHERE id=:userid AND symbol=:symbol",userid=session["user_id"], symbol=symbol["symbol"])
            return render_template("apology.html", message=stock*2)

            if stock["count(symbol)"] == 0:
                db.execute("INSERT INTO current (id, symbol, name, shares, price, total) VALUES (:userid, :symbol, :name, :shares, :price, :total) END",userid=session["user_id"], symbol=symbol["symbol"], name=symbol["name"], shares=shares, price=price, total=shares*price)

            else:
                shares += stock[0]["shares"]
                db.execute("UPDATE current SET shares = :shares WHERE id = :userid AND symbol = :symbol", shares=shares, userid=session["user_id"], symbol=symbol["symbol"])
            balance = balance - price*shares
            db.execute("UPDATE users SET cash = :cash WHERE id = :userid", cash=balance, userid = session["user_id"])
            flash("Bought!")
            return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return render_template("apology.html", message="sorry")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")

    else:
        symbol = request.form.get("symbol")
        symbol = lookup(symbol)
        if symbol != None:
            return render_template("quoted.html", quote=symbol)

        else:
            return render_template("apology.html", message="Sorry, Symbol doesn't exist.")





@app.route("/register", methods=["GET", "POST"])
def register():
    rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
    # """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        if not username:
            return render_template("apology.html", message="You must provide a username.")
        if username in rows:
            return render_template("apology.html", message="Sorry, this username is already taken.")
        password = request.form.get("password")
        if not password:
            return render_template("apology.html", message="You mus provide a password.")
        confirmation = request.form.get("confirmation")
        if password != confirmation:
            return render_template("apology.html", message="Password did not match.")

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username=username, password=generate_password_hash(password))
        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        symbol = db.execute("SELECT DISTINCT symbol FROM current WHERE id= :userid", userid=session["user_id"])
        return render_template("sell.html", symbol=symbol)

    else:
        return render_template("apology.html", message="sorry")



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
