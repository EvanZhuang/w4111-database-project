#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, flash
from datetime import datetime

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = '123456'



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "sg3637"
DB_PASSWORD = "P0hwduNhVw"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print ("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
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
  cursor = g.conn.execute("SELECT group_name, group_id FROM groups WHERE created_by = '1'")
  mygroups = []
  for result in cursor:
    mygroups.append([result['group_name'], result['group_id']])  # can also be accessed using result[0]
  cursor.close()

  #
  # Flask uses Jinja templates, which is an extension to HTML where you can
  # pass data to a template and dynamically generate HTML based on the data
  # (you can think of it as simple PHP)
  # documentation: https://realpython.com/blog/python/primer-on-jinja-templating/
  #
  # You can see an example template in templates/index.html
  #
  # context are the variables that are passed to the template.
  # for example, "data" key in the context variable defined below will be 
  # accessible as a variable in index.html:
  #
  #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
  #     <div>{{data}}</div>
  #     
  #     # creates a <div> tag for each element in data
  #     # will print: 
  #     #
  #     #   <div>grace hopper</div>
  #     #   <div>alan turing</div>
  #     #   <div>ada lovelace</div>
  #     #
  #     {% for n in data %}
  #     <div>{{n}}</div>
  #     {% endfor %}
  #
  context = dict(my_groups = mygroups)

  # Getting data on groups
  cursor = g.conn.execute("SELECT * from user_join_groups as u join groups as g on u.group_id = g.group_id where user_id = '1' and created_by != '1'")
  groups = []
  for result in cursor:
    groups.append([result['group_name'], result['group_id']])
  cursor.close()

  group_context = dict(group_data = groups)

  reco_query="SELECT user_id, group_id, b.group as recommended_group from(select user_id, cuisine, n_visits, group_id, a.group, row_number() over(partition by user_id order by n_visits desc)  from(select v.user_id, r.cuisine, count(*) as n_visits, (select group_name from groups where group_type like concat('%%', r.cuisine, '%%')) as group, (select group_id from groups where group_type like concat('%%', r.cuisine, '%%')) as group_id from visits as v join users as u on v.user_id = u.user_id join restaurants as r on r.rest_id = v.rest_id where (select group_name from groups where group_type like concat('%%', r.cuisine, '%%')) is not null group by v.user_id, r.cuisine order by user_id) as a) as b where row_number = 1 and user_id = '1'  and (user_id, group_id) not in (select user_id, group_id from user_join_groups)"

  cursor = g.conn.execute(reco_query)
  

  # cursor = g.conn.execute("SELECT group_name FROM groups WHERE created_by != 1")

  reco_groups = []
  for result in cursor:
    reco_groups.append([result['recommended_group'], result['group_id']])
  cursor.close()

  reco_context = dict(reco_data = reco_groups)

  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html", **context, **group_context, **reco_context)
  # return render_template("index.html", **group_context)

#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the function name is another() rather than index()
# the functions for each app.route needs to have different names
#
@app.route('/another', methods=['POST'])
def another():
  gid = request.form['view']
  cmd = "SELECT * from group_posts where group_id = %s;"
  cursor = g.conn.execute(cmd, (gid));

  posts = []
  for result in cursor:
    posts.append(result['text'])
  cursor.close()

  cmd = "SELECT group_name, group_id from groups where group_id = %s;"
  cursor = g.conn.execute(cmd, (gid));

  gname = []
  for result in cursor:
    gname.append([result['group_name'], result['group_id']])
  cursor.close()

  cmd = "SELECT fname, lname, timestamp from group_posts as g join users as u on g.user_id = u.user_id where group_id = %s;"
  cursor = g.conn.execute(cmd, (gid));

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
  print (text)
  cmd = "INSERT INTO groups(group_name, group_type, created_by) VALUES (%s, %s, %s);"
  g.conn.execute(cmd, (gname, gtype, '1'));
  return redirect('/')

@app.route('/createPost', methods=['POST'])
def createPost():
  text = request.form['text']
  date = datetime.today().strftime('%Y-%m-%d')
  gid = request.form['view']
  cmd = "INSERT INTO group_posts(group_id, text, user_id, timestamp) VALUES (%s, %s, %s, %s);"
  g.conn.execute(cmd, (gid, text, '1', date));
  return redirect('/')

@app.route('/joinGroup', methods=['POST'])
def joinGroup():
  gid = request.form['gid']
  cmd = "INSERT INTO user_join_groups(user_id, group_id, since) VALUES (%s, %s, %s);"
  g.conn.execute(cmd, ('1', gid, "2018-03-04"));
  return redirect('/')
  # cmd = "INSERT INTO groups(group_name, group_type, created_by) VALUES (%s, %s, %s);"
  # g.conn.execute(cmd, (gname, gtype, 1));
  # return redirect('/')

@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print ("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
