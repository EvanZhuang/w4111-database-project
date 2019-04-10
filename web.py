from flask import Flask
from flask import Flask, flash, redirect, render_template, request, session, abort
import os
 
app = Flask(__name__)
 
@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return main_page()
        #return 'Hello Boss!  <a href="/logout">Logout</a>'
 
@app.route('/login', methods=['POST'])
def do_admin_login():
    if request.form['password'] == 'password' and request.form['username'] == 'admin':
        session['logged_in'] = True
    else:
        flash('wrong password!')
    return home()
 
@app.route("/logout")
def logout():
    session['logged_in'] = False
    return home()

@app.route("/main")
def main_page():
    #GET DATA FROM DATABASE
    user = {'username': 'custudent'}
    restaurant  = {'rest_name' : "McDonald", "rest_description": "They make fried chicken"}
    return(render_template('main_page.html', user = user, rest = restaurant))


    
if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True,host='0.0.0.0', port=4000)
