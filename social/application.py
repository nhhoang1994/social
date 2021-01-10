import os

import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from dateutil import tz

from helpers import apology, login_required

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

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Link SQLite database
conn = sqlite3.connect("social.db")
cursor = conn.cursor()

def astimezone(self, tz):
    if self.tzinfo is tz:
        return self
    # Convert self to UTC, and attach the new time zone object.
    utc = (self - self.utcoffset()).replace(tzinfo=tz)
    # Convert from UTC to tz's local time.
    return tz.fromutc(utc)

# homepage shows examples of posts in database
@app.route("/", methods=["GET", "POST"])
def index():
    """Show portfolio of stocks"""

    # if user uses search bar, search for all post titles containing users' searched terms
    if request.method == "POST":
        cursor.execute("SELECT * FROM posts WHERE title LIKE ? ORDER BY time DESC LIMIT 10", ("%" + request.form.get("search") + "%", ))

    # else search for top 10 recent topics
    else:
        cursor.execute("SELECT * FROM posts ORDER BY time DESC LIMIT 10")

    posts = cursor.fetchall()

    # convert tuple posts into array posts and pass to templates for display
    posts_output = [[] for i in range(len(posts))]

    topics = [] # array to hold lists of topics for each article
    count = 0
    links = [] # array to hold hyperlinks to each article

    # generate posts_output for display
    for post in posts:

        # copy tuple posts into list posts
        posts_output[count] = list(post) # posts_output([0]: post_id, [1]: user_id, [2]: title, [3]: content, [4]: time)

        # get user name from each post since posts database stores only user id
        cursor.execute("SELECT username FROM users WHERE id = ?", (post[1], ))
        user = cursor.fetchone()
        posts_output[count].append(user[0]) # posts_output([5] = username)

        # read topics for each of the post since one post can have multiple topics in topics database
        cursor.execute("SELECT topic FROM topics WHERE post_id = ?", (post[0], ))
        topic_holders = cursor.fetchall()

        # create an output string of all topics for each post
        i = 0
        for topic_holder in topic_holders:
            topics.append("") # first element

            topics[count] = topics[count] + str(topic_holder[0]) # add first topic

            # add comma between after each topic except for last topic
            if len(topic_holders) > 1 and i < len(topic_holders) - 1:
                topics[count] = topics[count] + ","
            i = i + 1

        # append the output string into the post tuples
        posts_output[count].append(topics[count]) # posts_output[6]: lists of topics

        count = count + 1

    if request.method == "POST":
        if request.form.get("search") == "":
            search = None
            return render_template("index.html", posts_output=posts_output, search=search)
        else:
            search = request.form.get("search").upper()
            # return portfolios
            return render_template("index.html", posts_output=posts_output, search = search, length = len(posts_output))
    else:
        search = None
        return render_template("index.html", posts_output=posts_output, search = search)

# register page
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # check if user enter username
        if not request.form.get("username"):
            return apology("register", "Must provide username", 403)

        # check if user enter password
        elif not request.form.get("password"):
            return apology("register", "Must provide password", 403)

        # check if user enter retype password
        elif not request.form.get("password_retype"):
            return apology("register", "Must retype password", 403)

        # check if user enter email
        elif not request.form.get("email"):
            return apology("register", "Must provide email", 403)

        # check if user correctly retype password
        elif request.form.get("password") != request.form.get("password_retype"):
            return apology("register", "Password do not match", 403)

        # check if user enter proper email
        elif request.form.get("email").find("@") == -1:
            return apology("register", "Invalid email", 403)

        # check user credentials from database
        else:
            # search database for username
            cursor.execute("SELECT username FROM users WHERE username = ?", (request.form.get("username"), ))
            rows = cursor.fetchone()

            # if username do not exist
            if rows == None:
                # insert user credentials into database
                cursor.execute("INSERT INTO users (username, hash, email) VALUES (?, ?, ?)", (
                    request.form.get("username"), generate_password_hash(request.form.get("password")), request.form.get("email")))
                conn.commit()

                # return to login page
                return render_template("register_success.html")

            # if username already exist
            else:
                return apology("register", "Username already exists", 403)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

# login page
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("login", "must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("login", "must provide password", 403)

        # Query database for username
        cursor.execute("SELECT id, username, hash FROM users WHERE username = ?", (request.form.get("username"), ))
        rows = cursor.fetchone()

        # Ensure username exists and password is correct
        if rows == None:
            return apology("login", "Invalid username", 403)
        elif not check_password_hash(rows[2], request.form.get("password")):
            return apology("login", "invalid password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# logout page
@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# profile page shows user' profile
@app.route("/profile", methods=["GET"])
def profile():
    """Show user profile"""

    # Show username, email, change password link and post, topics, date, delete option
    cursor.execute("SELECT username, email FROM users WHERE id = ?", (session["user_id"], ))
    users = cursor.fetchone()

    # return portfolios
    return render_template("profile.html", users=users)

# change your password
@app.route("/pwchange", methods=["GET", "POST"])
@login_required
def pwchange():
    """Show user profile"""

    # # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # if missing old password
        if not request.form.get("oldpassword"):
            return apology("password_change", "Must provide old password", 403)
        # if missing new password
        elif not request.form.get("newpassword"):
            return apology("password_change", "Must provide new password", 403)
        # if missing retype new password
        elif not request.form.get("newpassword_retype"):
            return apology("password_change", "Must retype new password", 403)
        # if missing email
        elif not request.form.get("email"):
            return apology("password_change", "Must provide email", 403)
        # if missing new password and retype do not match
        elif request.form.get("newpassword") != request.form.get("newpassword_retype"):
            return apology("password_change", "Passwords and retyped passwords do not match", 403)

        # if all is well, allow password change
        else:
            # get user's current password
            cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"], ))
            users = cursor.fetchone()

            # check if user enter correct old password
            if not check_password_hash(users[2], request.form.get("oldpassword")):
                return apology("password_change", "You enter incorrect password", 403)
            # check if user enter correct email
            elif request.form.get("email") != users[3]:
                return apology("password_change", "You enter incorrect email", 403)
            # if new password is same as old password
            elif check_password_hash(user[2], request.form.get("newpassword")):
                return apology("password_change", "Your new password must be different", 403)

            # make change in users' database
            cursor.execute("UPDATE users SET hash = ? WHERE id = ?", (generate_password_hash(request.form.get("newpassword")), session["user_id"]))
            conn.commit()

            # return confirmation page
            return render_template("password_change_success.html")

    # User reached route via GET (as by clicking a link or redirect)
    else:
        # return form
        return render_template("password_change.html")

# history page displays users' post history
@app.route("/history", methods=["GET"])
@login_required
def history():
    # get user's post
    cursor.execute("SELECT * FROM posts WHERE user_id = ?", (session["user_id"], ))
    posts = cursor.fetchall()

    # output array to pass to template
    posts_output = [[] for i in range(len(posts))] # [0]: id, [1]: user_id, [2]: title, [3]: content, [4]: time
    count = 0
    topics = [] # holder for the lists of topics for each posts

    # convert tuple posts to array posts_output
    for post in posts:
        posts_output[count] = list(post)

        # read topics for each of the post since one post can have multiple topics in topics database
        cursor.execute("SELECT topic FROM topics WHERE post_id = ?", (post[0], ))
        topic_holders = cursor.fetchall()

        # create an output string of all topics for each post
        i = 0
        for topic_holder in topic_holders:
            topics.append("") # first element

            topics[count] = topics[count] + str(topic_holder[0]) # add first topic

            # add comma between after each topic except for last topic
            if len(topic_holders) > 1 and i < len(topic_holders) - 1:
                topics[count] = topics[count] + ","
            i = i + 1

        # append the output string into the post tuples
        posts_output[count].append(topics[count]) # posts_output[5]: lists of topics

        count = count + 1

    # get business posts
    cursor.execute("SELECT * FROM businesses WHERE user_id = ?", (session["user_id"], ))
    businesses = cursor.fetchall()

    businesses_output = [[] for i in range(len(businesses))]
    count_business = 0

    for business in businesses:
        businesses_output[count_business] = list(business) # [0]: id [1]:user_id [2] title [3] content [4] time [5] business
        count_business = count_business + 1

    return render_template("history.html", posts_output=posts_output, total_posts=len(posts_output), total_businesses=len(businesses_output), businesses_output=businesses_output)

# delete post
@app.route("/delete/<string:postid>", methods=["GET", "POST"])
@login_required
def delete(postid):

    # user reached routed via POST (as by submitting a FORM)
    if request.method == "POST":
        # check if user confirm deletion
        if not request.form.get("confirmation"):
            return apology("delete_post", "You did not confirm your deletion", 403)

        elif request.form.get("confirmation") != 'yes':
            return apology("delete_post", "You did not confirm your deletion correctly", 403)
        else:

            # proceed with deletion
            # get post title and user id
            cursor.execute("SELECT title, user_id FROM posts WHERE id = ?", (postid, ))
            title = cursor.fetchone()

            # delete from topics database
            cursor.execute("DELETE FROM topics WHERE post_id = ?", (postid, ))
            conn.commit()

            # delete from posts database
            cursor.execute("DELETE FROM posts WHERE id = ?", (postid, ))
            conn.commit()

            # remove file from memory
            filepath = "templates/uploads/" + title[0].lower() + "-" + str(title[1]) + ".html"
            os.remove(filepath)

            return render_template("delete_success.html", title=title[0])

    # user reached routed via GET (as by clicking a link or redicrect)
    else:
        # generate confirmation page
        cursor.execute("SELECT title, time FROM posts WHERE id = ?", (postid, ))
        posts = cursor.fetchone()

        return render_template("delete.html", title=posts[0], postid=postid, time=posts[1])

# delete post
@app.route("/delete_campaign/<string:postid>", methods=["GET", "POST"])
@login_required
def delete_campaign(postid):

    # user reached routed via POST (as by submitting a FORM)
    if request.method == "POST":
        # check if user confirm deletion
        if not request.form.get("confirmation"):
            return apology("delete_post", "You did not confirm your deletion", 403)

        elif request.form.get("confirmation") != 'yes':
            return apology("delete_post", "You did not confirm your deletion correctly", 403)
        else:

            # proceed with deletion
            # get post title and user id
            cursor.execute("SELECT title, user_id FROM businesses WHERE id = ?", (postid, ))
            title = cursor.fetchone()

            # delete from posts database
            cursor.execute("DELETE FROM businesses WHERE id = ?", (postid, ))
            conn.commit()

            # remove file from memory
            filepath = "templates/businesses/" + title[0].lower() + "-" + str(title[1]) + ".html"
            os.remove(filepath)

            return render_template("delete_success.html", title=title[0])

    # user reached routed via GET (as by clicking a link or redicrect)
    else:
        # generate confirmation page
        cursor.execute("SELECT title, time FROM businesses WHERE id = ?", (postid, ))
        businesses = cursor.fetchone()

        return render_template("delete_campaign.html", title=businesses[0], postid=postid, time=businesses[1])


# about page displays info about site
@app.route("/about", methods=["GET"])
def about():

    return render_template("about.html")

# individual page about each team member
@app.route("/members/<string:names>", methods=["GET"])
def members(names):

    # get email from database
    name = names.split("-")
    cursor.execute("SELECT email FROM users WHERE username = ?", (name[1], ))
    email = cursor.fetchone()

    link = "members/" + name[0] + ".html"
    if email == None:
        return render_template(link, name=name[0])
    else:
        return render_template(link, name=name[0], email=email[0])

# redirect user to corresponding upload page
@app.route("/post", methods=["GET", "POST"])
def post():

    # user reached route via POST (as by submitting a form)
    if request.method == "POST":
        if request.form.get("upload") == "social":
            return redirect("/socialupload")
        elif request.form.get("upload") == "business":
            return redirect("/businessupload")
    # user reached route via GET (as by clicking a link or redirect)
    else:
        return render_template("upload_choice.html")

# allow user to upload posts
@app.route("/socialupload", methods=["GET", "POST"])
@login_required
def socialupload():
    """User upload posts"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # check if user enter post title
        if not request.form.get("title"):
            return apology("upload", "Post title not provided", 403)

        # check if user enter post topics
        elif not request.form.get("topic"):
            return apology("upload", "Post topics not provided", 403)

        # check if user enter post
        elif not request.form.get("body"):
            return apology("upload", "You did not enter your post", 403)

        # if user type everything, proceed
        else:
            # check if user already has a post of the same name
            cursor.execute("SELECT title FROM posts WHERE user_id = ?", (session["user_id"], ))
            posts = cursor.fetchall()

            for post in posts:
                if post[0] == request.form.get("title").upper():
                    return apology("upload", "You already has another post with same title", 403)

            # else allow user to submit post
            # create new html link in uploads folder
            link = "templates/uploads/" + request.form.get("title").lower() + "-" + str(session["user_id"]) + ".html" # create file title

            # create new html file
            with open(link, "w") as f:
                if f == None:
                    return apology("upload", "Server can't process your upload", 403)

                # separate user uploads into paragraphs
                paragraphs = request.form.get("body").split('\r\n')

                # write headers
                f.write('{% extends "layout.html" %}\n {% block title %}\n')
                f.write(request.form.get("title").upper())
                f.write('{% endblock %}\n')

                # write body
                f.write('{% block main %}\n')
                # write title
                f.write('<p><strong>')
                f.write(request.form.get("title").upper())
                f.write('</strong></p>\n')

                # write each paragraph
                for paragraph in paragraphs:
                    f.write('<p style="text-align:left">')
                    f.write(paragraph)
                    f.write('</p>\n')

                # write remaining
                f.write('{% if session.user_id %}\n<p><a href = "/">Homepage</a></p>\n{% else %}')
                f.write('<p><a href = "/register">Register</a></p>\n<p><a href = "/login">Login</a></p>\n<p><a href = "/">Homepage</a></p>\n{% endif %}\n{% endblock %}')

                # close file
                f.close()

            # add post to posts database
            cursor.execute("INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)", (session["user_id"], request.form.get("title").upper(), request.form.get("body")))
            conn.commit()

            # add post topics to topics database
            cursor.execute("SELECT id FROM posts WHERE user_id = ? AND title = ?", (session["user_id"], request.form.get("title").upper()))
            post_id = cursor.fetchone()

            topics = request.form.get("topic").split(",")
            for topic in topics:
                cursor.execute("INSERT INTO topics (post_id, topic) VALUES (?, ?)", (post_id[0], topic.upper()))
                conn.commit()

            # confirm upload
            return render_template("social_upload_success.html", title=request.form.get("title").upper())

    # User reached route via GET (as by clicking a link or redirect)
    else:
        # give user their last inputs back if user made mistake
        return render_template("social_upload.html")

# allow user to upload posts
@app.route("/businessupload", methods=["GET", "POST"])
@login_required
def businessupload():
    """User upload posts"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # check if user enter post title
        if not request.form.get("title"):
            return apology("upload", "Campaign name not provided", 403)

        # check if user enter post topics
        elif not request.form.get("business"):
            return apology("upload", "Business name not provided", 403)

        # check if user enter post
        elif not request.form.get("body"):
            return apology("upload", "You did not enter your post", 403)

        # if user type everything, proceed
        else:
            # check if user already has a post of the same name
            cursor.execute("SELECT title FROM businesses WHERE user_id = ?", (session["user_id"], ))
            posts = cursor.fetchall()

            for post in posts:
                if post[0] == request.form.get("title").upper():
                    return apology("upload", "You already has another campaign with same title", 403)

            # else allow user to submit post
            # create new html link in uploads folder
            link = "templates/businesses/" + request.form.get("title").lower() + "-" + str(session["user_id"]) + ".html" # create file title

            # create new html file
            with open(link, "w") as f:
                if f == None:
                    return apology("upload", "Server can't process your upload", 403)

                # separate user uploads into paragraphs
                paragraphs = request.form.get("body").split('\r\n')

                # write headers
                f.write('{% extends "layout.html" %}\n {% block title %}\n')
                f.write(request.form.get("title").upper())
                f.write('{% endblock %}\n')

                # write body
                f.write('{% block main %}\n')
                # write title
                f.write('<p><strong>')
                f.write(request.form.get("title").upper())
                f.write('</strong></p>\n')

                # write each paragraph
                for paragraph in paragraphs:
                    f.write('<p style="text-align:left">')
                    f.write(paragraph)
                    f.write('</p>\n')

                # write remaining
                f.write('{% if session.user_id %}\n<p><a href = "/">Homepage</a></p>\n{% else %}')
                f.write('<p><a href = "/register">Register</a></p>\n<p><a href = "/login">Login</a></p>\n<p><a href = "/">Homepage</a></p>\n{% endif %}\n{% endblock %}')

                # close file
                f.close()

            # add campaign to posts database
            cursor.execute("INSERT INTO businesses (user_id, title, content, business) VALUES (?, ?, ?, ?)", (session["user_id"], request.form.get("title").upper(), request.form.get("body"), request.form.get("business").upper()))
            conn.commit()

            # confirm upload
            return render_template("business_upload_success.html", title=request.form.get("title").upper())

    # User reached route via GET (as by clicking a link or redirect)
    else:
        # give user their last inputs back if user made mistake
        return render_template("business_upload.html")

# generate social issues page
@app.route("/uploads/<string:title><string:userid>", methods=["GET", "POST"])
def uploads(title, userid):
    link = "uploads/"
    link = link + title.lower() + "-" + userid + ".html" # generate dynamic links that leads to corresponding post
    return render_template(link)

# generate social issues page
@app.route("/campaigns/<string:title><string:userid>", methods=["GET", "POST"])
def campaign(title, userid):
    link = "businesses/"
    link = link + title.lower() + "-" + userid + ".html" # generate dynamic links that leads to corresponding post
    return render_template(link)

# sell page to allow user to sell stocks
@app.route("/business", methods=["GET", "POST"])
def business():
    """Show business campaigns in order of time"""

    # if user uses search bar, search for all post titles containing users' searched terms
    if request.method == "POST":
        cursor.execute("SELECT * FROM businesses WHERE title LIKE ? ORDER BY time DESC LIMIT 10", ("%" + request.form.get("search") + "%", ))

    # else search for top 10 recent topics
    else:
        cursor.execute("SELECT * FROM businesses ORDER BY time DESC LIMIT 10")

    campaigns = cursor.fetchall()

    # convert tuple posts into array posts and pass to templates for display
    campaigns_output = [[] for i in range(len(campaigns))]

    count = 0
    links = [] # array to hold hyperlinks to each article

    # generate posts_output for display
    for campaign in campaigns:

        # copy tuple posts into list posts
        campaigns_output[count] = list(campaign) # campaigns_output([0]: id, [1]: user_id, [2]: title, [3]: content, [4]: time [5]: business

        # get user name from each post since posts database stores only user id
        cursor.execute("SELECT username FROM users WHERE id = ?", (campaign[1], ))
        user = cursor.fetchone()
        campaigns_output[count].append(user[0]) # posts_output([6] = username)

        count = count + 1

    # return portfolios
    if request.method == "POST":
        if request.form.get("search") == "":
            search = None
            return render_template("business_index.html", campaigns_output=campaigns_output, search=search)
        else:
            search = request.form.get("search").upper()
            # return portfolios
            return render_template("business_index.html", campaigns_output=campaigns_output, search = search, length = len(campaigns_output))
    else:
        search = None
        return render_template("business_index.html", campaigns_output=campaigns_output, search = search)

# check for errors
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
