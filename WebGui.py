from flask import Flask, render_template , flash, redirect, url_for, session, request , logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, IntegerField,PasswordField, BooleanField,  validators 
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'PaloAltoNetworksUserIDRegister'


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


@app.route("/system")
def system():
    cur = mysql.connection.cursor()
    state = ("SELECT * FROM FWdata ;")
    result = cur.execute(state)
    results = cur.fetchall()
    
    if result > 0:
        return render_template('system.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('system.html', msg=msg)


    cur.close()
        
    return render_template('system.html')


@app.route("/fwlist")
def fwlist():
    cur = mysql.connection.cursor()
    state = ("Select IFNULL(DisplayName, Hostname) as name, INET_NTOA(IPaddr) as ip  from DHCP where (Hostname <> 'blank' or DisplayName is not null) and LeaseTime in ( select MAX(LeaseTime)  from DHCP group by IPaddr desc)  and ( LeaseTime = '1970-01-01 00:00:01'  or LeaseTime > (NOW() - INTERVAL 1 WEEK)) order by IPaddr;")
    result = cur.execute(state)
    results = cur.fetchall()
    
    if result > 0:
        return render_template('fwlist.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('fwlist.html', msg=msg)


    cur.close()
        
    return render_template('fwlist.html')


@app.route("/force", methods=['GET','POST'])
def force():
    cur = mysql.connection.cursor()
    state = ("Select IFNULL(DisplayName, Hostname) as name, INET_NTOA(IPaddr) as ip  from DHCP where (Hostname <> 'blank' or DisplayName is not null) and LeaseTime in ( select MAX(LeaseTime)  from DHCP group by IPaddr desc) order by IPaddr;")
    result = cur.execute(state)
    results = cur.fetchall()
  
    if result > 0:
        return render_template('force.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('force.html', msg=msg)


    cur.close()
    
    check = request.form.get('check')
    print (check)
    
    form = Force(request.form)
    if request.method == 'POST' and form.validate():
        
    
    #and request.form.getlist('check') == "true":
        check = request.form.get('check')
        print (check)
        flash ('Firewall Update Requested', 'success')
        return redirect(url_for('fwlist'))
    else :
        print (check)
        
    return render_template('force.html')

@app.route("/userid")
def userid():
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IP ,`Hostname`,`DisplayName`,`LeaseTime`,`Source`FROM `DHCP` where Source = 'form' order by IPaddr asc;" )
    results = cur.fetchall()
    
    if result > 0:
        return render_template('userid.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('userid.html', msg=msg)


    cur.close()
        
    return render_template('userid.html')

@app.route("/group")
def group():
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, GName,  `Desc` FROM GROUPS  where UID >=1 order by UID asc;" )
    results = cur.fetchall()
    
    if result > 0:
        return render_template('group.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('group.html', msg=msg)


    cur.close()
        
    return render_template('group.html')

@app.route("/dhcpid")
def dhcpid():
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IP,`Hostname`,`DisplayName`,`LeaseTime`,`Source`FROM `DHCP` where Source = 'FW' order by IPaddr asc;" )
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

@app.route("/addgroup", methods=['GET', 'POST'])
def addgroup():
    form = AddGroup(request.form)
    if request.method == 'POST' and form.validate():
        displayname = form.displayname.data
        descript = form.descript.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" INSERT INTO GROUPS (GName, `Desc` )VALUES ( %s, %s) ", (displayname , descript ) )
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Group Added', 'success')
        return redirect(url_for('group'))
        
#        return render_template('adduser.html')
    return render_template('addgroup.html', form=form)

@app.route("/members/<string:id>/", methods=['GET','POST'])
def members(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT Group_User_Map.Group_UID as GUID, Group_User_Map.UID as UID, IFNULL(DHCP.DisplayName, DHCP.Hostname) as Hostname, INET_NTOA(DHCP.IPaddr) as IPaddr from DHCP INNER JOIN Group_User_Map ON DHCP.UID=Group_User_Map.DHCP_UID where Group_User_Map.Group_UID = %s order by Group_User_Map.UID asc ;" , [id] )
    results = cur.fetchall()
    
    if result > 0:
        return render_template('members.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('members.html', msg=msg)

    cur.close()
        
    return render_template('members.html')

@app.route("/addmembers/<string:id>/", methods=['GET','POST'])
def addmembers(id):
    cur = mysql.connection.cursor()
    result = cur.execute("Select %s as GUID , UID, IFNULL(DisplayName, Hostname) as name, INET_NTOA(IPaddr) as ip from DHCP where (Hostname <> 'blank' or DisplayName is not null) and UID not in (Select DHCP_UID from Group_User_Map where Group_UID = %s)order by IPaddr asc ;" , (id, id) )
    results = cur.fetchall()
    
    if result > 0:
        return render_template('addmembers.html', results=results )
    else:
        msg = 'No devices registered'
        return render_template('addmembers.html', msg=msg)

    cur.close()
        
    return render_template('addmembers.html')

@app.route("/addmember/", methods=['GET','POST'])
def addmember():
    GUID = int(request.args.get('GUID', None))
    DHCPUID = int(request.args.get('DHCPUID', None))
    cur = mysql.connection.cursor()
    result = cur.execute(" Select '%s' as GUID , UID ,IFNULL(DisplayName, Hostname) as DisplayName, INET_NTOA(IPaddr) as ip FROM `DHCP` where  UID = '%s';" , ( GUID , DHCPUID ) )
    results = cur.fetchone()

  
    form = addmemberForm(request.form)
    form.displayname.data = results['DisplayName']
    form.ip.data = results['ip']
    form.GUID.data = results['GUID']
    form.DUID.data = results['UID']
    
       
    if request.method == 'POST' and form.validate():
        GUID = form.GUID.data 
        DHCPIP = form.DUID.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" Insert into Group_User_Map (Group_UID, DHCP_UID) Values (%s,%s)"  , (GUID , DHCPIP))
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device Added', 'success')
        return redirect(url_for('addmembers', id=int(GUID)))


    cur.close()
        
    
    return render_template('addmember.html', form=form )

 
@app.route("/edituser/<string:id>/", methods=['GET','POST'])
def edituser(id):
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IP,`Hostname`,`DisplayName` ,`LeaseTime`,`Source`FROM `DHCP` where  UID = %s;" , [id] )
    results = cur.fetchone()
    
    form = EditForm(request.form)
    form.hostname.data = results['DisplayName']
    form.ipaddr.data = results['IP']
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
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IP,`Hostname`,`DisplayName` ,`LeaseTime`,`Source`FROM `DHCP` where  UID = %s;" , [id] )
    results = cur.fetchone()

  
    form = DeleteForm(request.form)
    form.hostname.data = results['DisplayName']
    form.ipaddr.data = results['IP']
    form.uid.data = results['UID']
    
    if request.method == 'POST' and form.validate():
        hostname = request.form['hostname']
        ipaddr = request.form['ipaddr']
        uid = form.uid.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" Delete from `DHCP` where UID = %s and DisplayName = %s and `IPaddr` = inet_aton(%s)"  , (uid , hostname , ipaddr , uid))
        cur.execute("delete from Group_User_Map where DHCP_UID = %s " , uid)
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device Deleted', 'success')
        return redirect(url_for('userid'))


    cur.close()
        
    
    return render_template('deleteuser.html', form=form )


 
@app.route("/deletemember/<string:id>/", methods=['GET','POST'])
def deletemember(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT Group_User_Map.UID as UID, IFNULL(DHCP.DisplayName, DHCP.Hostname) as Hostname, INET_NTOA(DHCP.IPaddr) as IP from DHCP INNER JOIN Group_User_Map ON DHCP.UID=Group_User_Map.DHCP_UID where Group_User_Map.UID = %s order by Group_User_Map.UID asc ;" , [id] )
    results = cur.fetchone()

  
    form = DeleteMemForm(request.form)
    form.hostname.data = results['Hostname']
    form.ipaddr.data = results['IP']
    form.uid.data = results['UID']
    
    if request.method == 'POST' and form.validate():
        hostname = request.form['hostname']
        ipaddr = request.form['ipaddr']
        uid = form.uid.data
        blank = 0
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" Delete from Group_User_Map where UID = %s and DHCP_UID <> %s; "  , ( uid , blank ))
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device Deleted', 'success')
        return redirect(url_for('group'))


    cur.close()
        
    
    return render_template('deletemember.html', form=form )

@app.route("/editdhcp/<string:id>/", methods=['GET','POST'])
def editdhcp(id):
    cur = mysql.connection.cursor()
    result = cur.execute(" SELECT `UID`, `MacAddr`, Vendor,  inet_ntoa(`IPaddr`) as IP,`Hostname`,`DisplayName` ,`LeaseTime`,`Source`FROM `DHCP` where  UID = %s;" , [id] )
    results = cur.fetchone()
    
    form = EditDhcp(request.form)
    form.displayname.data = results['DisplayName']
    form.vendor.data = results['Vendor']
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
    result = cur.execute(" SELECT `UID`, `MacAddr`, inet_ntoa(`IPaddr`) as IPaddr,`Hostname`,`DisplayName` ,`LeaseTime`,`Source`FROM `DHCP` where  UID = %s;" , [id] )
    results = cur.fetchone()

  
    form = DeleteDhcp(request.form)
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
        blank = 0 
        cur = mysql.connection.cursor()
        cur.execute(" Delete from Group_User_Map where  DHCP_UID = %s and Group_UID <> %s ; "  , ( uid , blank ))
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Device Deleted', 'success')
        return redirect(url_for('dhcpid'))


    cur.close()
        
    
    return render_template('deletedhcp.html', form=form )


@app.route("/editgroup/<string:id>/", methods=['GET','POST'])
def editgroup(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT `UID`, GName,  `Desc` as descript FROM GROUPS  where  UID = %s;" , [id] )
    results = cur.fetchone()
    
    form = EditGroup(request.form)
    form.displayname.data = results['GName']
    form.descript.data = results['descript']
    form.uid.data = results['UID']
    
    if request.method == 'POST' and form.validate():
        descript = request.form['descript']
        uid = form.uid.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" update GROUPS set `Desc` = %s  where UID = %s;", (descript,   uid) )
        
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        
        flash ('Group edited', 'success')
        return redirect(url_for('group'))


    cur.close()
        
    
    return render_template('editgroup.html', form=form )

@app.route("/deletegroup/<string:id>/", methods=['GET','POST'])
def deletegroup(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT `UID`, GName,  `Desc` as descript FROM GROUPS  where  UID = %s;" , [id] )
    results = cur.fetchone()

  
    form = DeleteGroup(request.form)
    form.displayname.data = results['GName']
    form.descript.data = results['descript']
    form.uid.data = results['UID']
    
    if request.method == 'POST' and form.validate():
        displayname = request.form['displayname']
        uid = form.uid.data
        ## cursor ##
        cur = mysql.connection.cursor()
        cur.execute(" Delete from GROUPS where UID = %s and GName = %s ;" , (uid , displayname))
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
        blank = 0 
        cur = mysql.connection.cursor()
        cur.execute(" Delete from Group_User_Map where Group_UID = %s and DHCP_UID <> %s; "  , ( uid , blank ))
        ## commit and close ##
        mysql.connection.commit()
        cur.close()
           
           
        flash ('Group Deleted', 'success')
        return redirect(url_for('group'))


    cur.close()
        
    
    return render_template('deletegroup.html', form=form )


 
 

@app.route("/reset")
def reset():
    return render_template('reset.html')

class AddForm(Form):
    hostname = StringField('Display Name', [validators.Length(min=1, max=50)])
    ipaddr = StringField('IP Address', [validators.IPAddress(ipv4=True , message="Enter a valid IP Address")])

    
class EditForm(Form):
    uid = IntegerField('UID', render_kw={'readonly': True})
    hostname = StringField('Display Name', [validators.Length(min=1, max=50)])
    ipaddr = StringField('IP Address', [validators.IPAddress(ipv4=True , message="Enter a valid IP Address")])

class DeleteForm(Form):
    uid = IntegerField('UID', render_kw={'readonly': True})
    hostname = StringField('Display Name', render_kw={'readonly': True})
    ipaddr = StringField('IP Address', render_kw={'readonly': True})

class DeleteMemForm(Form):
    uid = IntegerField('UID', render_kw={'readonly': True})
    hostname = StringField('Display Name', render_kw={'readonly': True})
    ipaddr = StringField('IP Address', render_kw={'readonly': True}) 
    
class EditDhcp(Form):
    uid = IntegerField('UID', render_kw={'readonly': True})
    hostname = StringField('Host Name', render_kw={'readonly': True} )
    vendor = StringField('Mac Vendor', render_kw={'readonly': True} )
    displayname = StringField('Display Name')
 
class DeleteDhcp(Form):
    uid = IntegerField('UID', render_kw={'readonly': True} )
    hostname = StringField('Host Name', render_kw={'readonly': True} )
    displayname = StringField('Display Name', render_kw={'readonly': True})   

class AddGroup(Form):
    descript = StringField('Description')
    displayname = StringField('Group Name', [validators.Length(min=1, max=50)])
    
class EditGroup(Form):
    uid = IntegerField('UID', render_kw={'readonly': True})
    descript = StringField('Description')
    displayname = StringField('Group Name', render_kw={'readonly': True})
 
class DeleteGroup(Form):
    uid = IntegerField('UID', render_kw={'readonly': True} )
    descript = StringField('Description', render_kw={'readonly': True} )
    displayname = StringField('Group Name', render_kw={'readonly': True})   
    
class addmemberForm(Form):
    displayname = StringField('Display Name', render_kw={'readonly': True})
    ip = StringField('IP Address', render_kw={'readonly': True})    
    DUID = IntegerField('DUID', render_kw={'readonly': True} )
    GUID = IntegerField('GUID', render_kw={'readonly': True} )   

class Force(Form):
     checkbox = BooleanField('Agree?', validators=[DataRequired(), ])
    
if __name__ == '__main__':
    app.secret_key='PaloAltoNetworksUserIDRegister'
    app.run(debug=True)