import os, datetime
import ast
import random
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import *
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
                session['user'] = user
		return dashboard()
	else:
		return render_template('welcome.html')

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return login()

@app.route('/group')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print (request.args)


  #
  # example of a database query
  #
  cursor = db.engine.execute("SELECT group_name, group_id FROM groups WHERE created_by = %s" , (session.get('user_id')))
  mygroups = []
  for result in cursor:
    mygroups.append([result['group_name'], result['group_id']])  # can also be accessed using result[0]
  cursor.close()


  context = dict(my_groups = mygroups)

  # Getting data on groups
  cursor = db.engine.execute("SELECT * from user_join_groups as u join groups as g on u.group_id = g.group_id where user_id = '%s' and created_by != '%s'" %(session.get('user_id'), session.get('user_id')))
  groups = []
  for result in cursor:
    groups.append([result['group_name'], result['group_id']])
  cursor.close()

  group_context = dict(group_data = groups)

  reco_query="SELECT user_id, group_id, b.group as recommended_group from(select user_id, cuisine, n_visits, group_id, a.group, row_number() over(partition by user_id order by n_visits desc)  from(select v.user_id, r.cuisine, count(*) as n_visits, (select group_name from groups where group_type like concat('%%', r.cuisine, '%%')) as group, (select group_id from groups where group_type like concat('%%', r.cuisine, '%%')) as group_id from visits as v join users as u on v.user_id = u.user_id join restaurants as r on r.rest_id = v.rest_id where (select group_name from groups where group_type like concat('%%', r.cuisine, '%%')) is not null group by v.user_id, r.cuisine order by user_id) as a) as b where row_number = 1 and user_id = %s  and (user_id, group_id) not in (select user_id, group_id from user_join_groups)" 

  cursor = db.engine.execute(reco_query, (session.get('user_id')))
  

  # cursor = db.engine.execute("SELECT group_name FROM groups WHERE created_by != 1")

  reco_groups = []
  for result in cursor:
    reco_groups.append([result['recommended_group'], result['group_id']])
  cursor.close()

  reco_context = dict(reco_data = reco_groups)

  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("group.html", **context, **group_context, **reco_context)
  # return render_template("index.html", **group_context)

@app.route('/another', methods=['POST'])
def another():
  gid = request.form['view']
  cmd = "SELECT * from group_posts where group_id = %s;"
  cursor = db.engine.execute(cmd, (gid));

  posts = []
  for result in cursor:
    posts.append(result['text'])
  cursor.close()

  cmd = "SELECT group_name, group_id from groups where group_id = %s;"
  cursor = db.engine.execute(cmd, (gid));

  gname = []
  for result in cursor:
    gname.append([result['group_name'], result['group_id']])
  cursor.close()

  cmd = "SELECT fname, lname, timestamp from group_posts as g join users as u on g.user_id = u.user_id where group_id = %s;"
  cursor = db.engine.execute(cmd, (gid));

  post_details = []
  for result in cursor:
    post_details.append([result['fname'], result['lname'], result['timestamp']])
  cursor.close()

  for i in range(0, len(post_details)):
    post_details[i].append(posts[i])

  # postDet_context = dict(postsDet_data = post_details)
  posts_context = dict(posts_data = post_details)
  group_name = dict(group_name = gname)

  return render_template("anotherfile.html", **posts_context, **group_name)


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  gname = request.form['gname']
  gtype = request.form['gtype']
  cmd = "INSERT INTO groups(group_name, group_type, created_by) VALUES (%s, %s, %s);"
  db.engine.execute(cmd, (gname, gtype, '1'));
  return redirect('/group')

@app.route('/createPost', methods=['POST'])
def createPost():
  text = request.form['text']
  date = datetime.datetime.today().strftime('%Y-%m-%d')
  gid = request.form['view']
  cmd = "INSERT INTO group_posts(group_id, text, user_id, timestamp) VALUES (%s, %s, %s, %s);"
  db.engine.execute(cmd, (gid, text, '1', date));
  return redirect('/group')

@app.route('/joinGroup', methods=['POST'])
def joinGroup():
  gid = request.form['gid']
  cmd = "INSERT INTO user_join_groups(user_id, group_id, since) VALUES (%s, %s, %s);"
  db.engine.execute(cmd, ('1', gid, "2018-03-04"));
  return redirect('/group')
  # cmd = "INSERT INTO groups(group_name, group_type, created_by) VALUES (%s, %s, %s);"
  # db.engine.execute(cmd, (gname, gtype, 1));
  # return redirect('/')

if __name__ == '__main__':
	app.secret_key = os.urandom(12)
	app.run(debug=True, host='0.0.0.0', port=8111)
