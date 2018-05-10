from flask import Flask, render_template , flash, redirect, url_for, session, request , logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, IntegerField,PasswordField,  validators

app = Flask(__name__)


try:
    from variables import *
except ImportError:
    for arg in sys.argv: 1
# use the command line to call the function from a single script.
    if arg == "setup":
        print ("")
    else:
        print ("Run dhcpuserid.py setup")
        sys.exit(0)
        
# config mysql #
app.config['MYSQL_HOST'] = host
app.config['MYSQL_USER'] = user
app.config['MYSQL_PASSWORD'] = passwd
app.config['MYSQL_DB'] = db
app.config['MYSQL_PORT'] = port
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init mysql #

mysql =MySQL(app)


@app.route("/")
def index():
    return render_template('index.html')

@app.route("/register")
def register():
    return render_template('register.html')


@app.route("/fwlist")
def fwlist():
    cur = mysql.connection.cursor()
    result = cur.execute("Select IFNULL(DisplayName, Hostname) as name, INET_NTOA(IPaddr) as ip from DHCP where Hostname <> 'blank' or DisplayName is not null order by IPaddr asc" )
    results = cur.fetchall()
    
    if result > 0:
        return render_template('fwlist.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('fwlist.html', msg=msg)


    cur.close()
        
    return render_template('fwlist.html')


@app.route("/userid")
def userid():
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IPaddr,`Hostname`,`DisplayName`,`LeaseTime`,`Source`FROM `Python`.`DHCP` where Source = 'form';" )
    results = cur.fetchall()
    
    if result > 0:
        return render_template('userid.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('userid.html', msg=msg)


    cur.close()
        
    return render_template('userid.html')

@app.route("/dhcpid")
def dhcpid():
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IPaddr,`Hostname`,`DisplayName`,`LeaseTime`,`Source`FROM `Python`.`DHCP` where Source = 'FW';" )
    results = cur.fetchall()
    
    if result > 0:
        return render_template('dhcpid.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('dhcpid.html', msg=msg)


    cur.close()
        
    return render_template('dhcpid.html')


@app.route("/adduser", methods=['GET', 'POST'])
def adduser():
    form = AddForm(request.form)
    if request.method == 'POST' and form.validate():
        hostname = form.hostname.data
        ipaddr = form.ipaddr.data
        mac = "st%s" %(hostname)
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" INSERT INTO `DHCP` (`MacAddr`, `IPaddr`,`DisplayName`,`LeaseTime`,`Source`)VALUES ( %s,INET_ATON(%s),%s,sysdate(),'form') ", (mac , ipaddr, hostname) )
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device Added', 'success')
        return redirect(url_for('userid'))
        
#        return render_template('adduser.html')
    return render_template('adduser.html', form=form)

@app.route("/edituser/<string:id>/", methods=['GET','POST'])
def edituser(id):
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IPaddr,`Hostname`,`DisplayName` ,`LeaseTime`,`Source`FROM `Python`.`DHCP` where  UID = %s;" , [id] )
    results = cur.fetchone()
    
    form = EditForm(request.form)
    form.hostname.data = results['DisplayName']
    form.ipaddr.data = results['IPaddr']
    form.uid.data = results['UID']
    
    if request.method == 'POST' and form.validate():
        hostname = request.form['hostname']
        ipaddr = request.form['ipaddr']
        uid = form.uid.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" update `DHCP` set `DisplayName` = %s , `IPaddr` = INET_ATON(%s), LeaseTime = sysdate() where UID = %s;", (hostname , ipaddr,  uid) )
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device edited', 'success')
        return redirect(url_for('userid'))


    cur.close()
        
    
    return render_template('edituser.html', form=form )

@app.route("/deleteuser/<string:id>/", methods=['GET','POST'])
def deleteuser(id):
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IPaddr,`Hostname`,`DisplayName` ,`LeaseTime`,`Source`FROM `Python`.`DHCP` where  UID = %s;" , [id] )
    results = cur.fetchone()

  
    form = EditForm(request.form)
    form.hostname.data = results['DisplayName']
    form.ipaddr.data = results['IPaddr']
    form.uid.data = results['UID']
    
    if request.method == 'POST' and form.validate():
        hostname = request.form['hostname']
        ipaddr = request.form['ipaddr']
        uid = form.uid.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" Delete from `DHCP` where UID = %s and DisplayName = %s and `IPaddr` = inet_aton(%s)"  , (uid , hostname , ipaddr))
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device Deleted', 'success')
        return redirect(url_for('userid'))


    cur.close()
        
    
    return render_template('deleteuser.html', form=form )


 
 
 

@app.route("/editdhcp/<string:id>/", methods=['GET','POST'])
def editdhcp(id):
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IPaddr,`Hostname`,`DisplayName` ,`LeaseTime`,`Source`FROM `Python`.`DHCP` where  UID = %s;" , [id] )
    results = cur.fetchone()
    
    form = EditDhcp(request.form)
    form.displayname.data = results['DisplayName']
    form.hostname.data = results['Hostname']
    form.uid.data = results['UID']
    
    if request.method == 'POST' and form.validate():
        displayname = request.form['displayname']
        hostname = form.hostname.data
        uid = form.uid.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" update `DHCP` set `DisplayName` = %s  where UID = %s;", (displayname,   uid) )
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device edited', 'success')
        return redirect(url_for('dhcpid'))


    cur.close()
        
    
    return render_template('editdhcp.html', form=form )

@app.route("/deletedhcp/<string:id>/", methods=['GET','POST'])
def deletedhcp(id):
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IPaddr,`Hostname`,`DisplayName` ,`LeaseTime`,`Source`FROM `Python`.`DHCP` where  UID = %s;" , [id] )
    results = cur.fetchone()

  
    form = EditDhcp(request.form)
    form.displayname.data = results['DisplayName']
    form.hostname.data = results['Hostname']
    form.uid.data = results['UID']
    
    if request.method == 'POST' and form.validate():
        hostname = request.form['hostname']
        uid = form.uid.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" Delete from `DHCP` where UID = %s and Hostname = %s"  , (uid ,hostname))
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device Deleted', 'success')
        return redirect(url_for('dhcpid'))


    cur.close()
        
    
    return render_template('deletedhcp.html', form=form )


 
 

@app.route("/reset")
def reset():
    return render_template('reset.html')

class AddForm(Form):
    hostname = StringField('Display Name', [validators.Length(min=1, max=20)])
    ipaddr = StringField('IP Address', [validators.IPAddress(ipv4=True , message="Enter a valid IP Address")])

    
class EditForm(Form):
    uid = IntegerField('UID', [validators.required()])
    hostname = StringField('Display Name', [validators.Length(min=1, max=20)])
    ipaddr = StringField('IP Address', [validators.IPAddress(ipv4=True , message="Enter a valid IP Address")])

class EditDhcp(Form):
    uid = IntegerField('UID', [validators.required()])
    hostname = StringField('Host Name', [validators.Length(min=1, max=20)] )
    displayname = StringField('Display Name')
   
    
if __name__ == '__main__':
    app.secret_key='PaloAltoNetworksUserIDRegister'
    app.run(debug=False)