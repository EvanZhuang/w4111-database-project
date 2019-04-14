import os, datetime
import ast
import random
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://sg3637:P0hwduNhVw@w4111.cisxo09blonu.us-east-1.rds.amazonaws.com/w4111"
db = SQLAlchemy(app)


@app.route('/')
def login():
	if session.get('logged_in'):
		dashboard()
	return render_template('index.html')

@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
	if session.get('logged_in'):
		result = db.engine.execute("SELECT * FROM RESTAURANTS")
		result = [r for r in result]
		recommendation = random.sample(result, 5)
		rec_list = []
		col_names = ["rest_id", "name", "rating", "opening_hours", "closing_hours", "location", "cuisine"]
		
		for _ in recommendation:
			rec = {}
			comments = db.engine.execute("SELECT user_id, stars, comment, timestamp FROM COMMENTS WHERE rest_id = %s" %(_[0]))
			comments = [r for r in comments]
			comments = random.choice(comments)
			username = db.engine.execute("SELECT fname, lname FROM USERS WHERE user_id = \'%s\'" %(comments[0])).first()
			pics = db.engine.execute("SELECT img_url FROM PICTURES WHERE rest_id = %s" %(_[0])).first()[0]
			visits = db.engine.execute("SELECT to_char(timestamp, 'YYYY-MM-DD') FROM VISITS WHERE rest_id = %s AND user_id = '%s' ORDER BY timestamp DESC"  %(_[0], session.get('user_id')))
			if visits.rowcount > 0:
				rec["last_visit"] = visits.first()[0]
				print(rec["last_visit"])
			else:
				rec["last_visit"] = False
			for i, col in enumerate(col_names):
				rec[col] = _[i]
			rec["pic_url"] = pics
			rec['fname'] = username[0]
			rec['lname'] = username[1]
			rec['userstar'] = comments[1]
			rec['comment'] = comments[2]
			rec['comment_ts'] = comments[3]
			rec_list.append(rec)
		return render_template('dashboard.html', user = session.get('user'), rests = rec_list)	
	return render_template('index.html')

@app.route('/login', methods=['POST'])
def home():
	username = request.form['username']
	password = request.form['password']
	result = db.engine.execute("SELECT password FROM USERS WHERE user_id = \'%s\'" %(username))
	if result.rowcount > 0:
		password = result.first()[0]
	else:
		flash('wrong username!')
		return home()
	if request.form['password'] == password and result is not None:
		session['user_id'] = request.form['username']
		session['logged_in'] = True
		result = db.engine.execute("SELECT fname, lname, member_since FROM USERS WHERE user_id = \'%s\'" %(username)).first()
		user = {'firstname': result[0], 'lastname': result[1], 'member_since': result[2]}
		session['user'] = user
		return dashboard()
	elif request.form['password'] != password:
		flash('wrong password!')
	return render_template('index.html')


@app.route('/reg')
def reg():
	return render_template('welcome.html')

@app.route('/register', methods=['POST','GET'])
def register():
	print("REGISTER REACHED")
	if request.method == 'POST':
		password = request.form['password']
		passwordrepeat = request.form['passwordrepeat']
		if password != passwordrepeat:
			return render_template('welcome.html')
		result = db.engine.execute("SELECT * FROM USERS WHERE user_id = \'%s\'" %(request.form['username']))
		if result.rowcount > 0:
			flash("Username Taken")
			return render_template('welcome.html')
		db.engine.execute("INSERT INTO USERS (user_id, fname, lname, password, member_since) VALUES (\'%s\', \'%s\', \'%s\', \'%s\', %s);" 
            %(request.form['username'], request.form['firstname'], request.form['lastname'], request.form['password'], "'" + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + "'"))
		session['user_id'] = request.form['username']
		session['logged_in'] = True
		user = {'firstname': request.form['firstname'], 'lastname': request.form['lastname'], 'member_since': "'" + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + "'"}
		return dashboard()
	else:
		return render_template('welcome.html')

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return login()

if __name__ == '__main__':
	app.secret_key = os.urandom(12)
	app.run(debug=True, host='0.0.0.0', port=4000)