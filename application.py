import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from jinja2 import Environment

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
env = Environment()
env.filters["usd"] = usd

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
    # Query database for cash user has
    cash = db.execute("SELECT cash FROM users WHERE id = :id",
                      id=session["user_id"])
    # Query database for track of purchase
    rows = db.execute("SELECT symbol, name, SUM(quantity) as quantity FROM trading WHERE user_id = :id GROUP BY symbol",
                      id=session["user_id"])

    # Find current price of each stock
    currents = []
    gtotal = 0
    for row in rows:
        current = {'symbol': row["symbol"], 'name': row["name"], 'quantity': row["quantity"], 'price': lookup(row["symbol"])["price"],
                    'total': lookup(row["symbol"])["price"] * row["quantity"] }
        currents.append(current)
        gtotal += lookup(row["symbol"])["price"] * row["quantity"]

    return render_template("index.html", cash= cash[0]["cash"], currents= currents, gtotal= gtotal + cash[0]["cash"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol", 403)

        stock = lookup(symbol)
        # Ensure symbol exists
        if not stock:
            return apology("The symbol does not exist", 403)

        shares = request.form.get("shares")
        # Ensure a number of shares is positive integer
        if not shares or int(shares) <= 0:
            return apology("must provide positive number in shares", 403)

        total = stock["price"] * int(shares)

         # Query database for cash user has
        cash = db.execute("SELECT cash FROM users WHERE id = :id",
                      id=session["user_id"])

         # Ensure the user has enough cash to buy it
        if total > cash[0]["cash"]:
            return apology("does not have enough cash to buy", 403)

        db.execute("INSERT INTO trading (user_id, symbol, name, unit_price, quantity, total) VALUES(:id, :symbol, :name, :unitprice, :quantity, :total)",
                id=session["user_id"], symbol=stock["symbol"], name=stock["name"], unitprice=stock["price"], quantity=int(shares), total=total)

        db.execute("UPDATE users SET cash = :cash WHERE id = :id",
                id=session["user_id"], cash=cash[0]["cash"]-total)

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
     # Query database for history of transaction
    trades = db.execute("SELECT * FROM trading WHERE user_id = :id",
                  id=session["user_id"])
    return render_template("history.html",trades=trades)


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
        if not symbol:
            return apology("must provide symbol", 403)

        result = lookup(symbol)
        # Ensure symbol exists
        if not result:
            return apology("The symbol does not exist", 403)
        return render_template("quoted.html", result = result)


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()

    if request.method == "GET":
        return render_template("register.html")
    else:
        name = request.form.get("username")
        if not name:
            return apology("must provide username", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :name", name=name)

        if len(rows) != 0:
            return apology("invalid username", 403)

        password = request.form.get("password")
        repassword = request.form.get("confirmation")
        if not password:
            return apology("must provide password", 403)
        if not repassword:
            return apology("must provide confirmation", 403)
        if password != repassword:
            return apology("Passwords do not match", 403)


        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES(:name, :hash)", name=name, hash=hash)


        rows = db.execute("SELECT * FROM users WHERE username = :name", name=name)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        # Query database for stocks user has
        rows = db.execute("SELECT symbol, name, SUM(quantity) as quantity FROM trading WHERE user_id = :id GROUP BY symbol",
                          id=session["user_id"])
        return render_template("sell.html",rows=rows)
    else:
        symbol = request.form.get("symbols")
        share = request.form.get("shares")
        if not symbol:
            return apology("must provide symbol", 403)
        if not share:
            return apology("must provide share", 403)

        # Query database for the stock user has
        row = db.execute("SELECT symbol, name, SUM(quantity) as quantity FROM trading WHERE user_id = :id and symbol= :symbol GROUP BY symbol",
                          id=session["user_id"], symbol=symbol)

        if int(share) > row[0]["quantity"]:
            return apology("does not have the number of stocks", 403)

        stock = lookup(symbol)
        total = int(share) * stock["price"]

        db.execute("INSERT INTO trading (user_id, symbol, name, unit_price, quantity, total) VALUES(:id, :symbol, :name, :unitprice, :quantity, :total)",
                id=session["user_id"], symbol=symbol, name=row[0]["name"], unitprice=stock["price"], quantity=-int(share), total=total)


         # Query database for cash user has
        cash = db.execute("SELECT cash FROM users WHERE id = :id",
                      id=session["user_id"])

        db.execute("UPDATE users SET cash = :cash WHERE id = :id",
                id=session["user_id"], cash=cash[0]["cash"]+total)

        # Redirect user to home page
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
