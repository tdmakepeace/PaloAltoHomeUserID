## TODO :
## need to clean up some of the display 
## force and reset are not currently needed.
## 


import threading
import time
import urllib
import urllib.request
import urllib.parse
import sys
import ssl
import xml.etree.ElementTree as ET
import pymysql
#import getpass
from datetime import datetime
from flask import Flask, render_template , flash, redirect, url_for, session, request , logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, IntegerField,PasswordField, BooleanField,  validators 
from wtforms.validators import DataRequired




try:
    from variables import *
except ImportError:
    print ("Run setup.py, to create the variables configuration file.")
    print ("you can manual edit the variables file once the file is created.")
    print ("variable.py")
    sys.exit(0)


app = Flask(__name__)
# config mysql #
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'PaloAltoNetworksUserIDRegister'

app.config['MYSQL_HOST'] = host
app.config['MYSQL_USER'] = user
app.config['MYSQL_PASSWORD'] = passwd
app.config['MYSQL_DB'] = db
app.config['MYSQL_PORT'] = port
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init mysql #


        
        

def dbmain():
# TODO:    A new section to act as a DB maintainence.
# still to be worked on.
# but will currently delete any records that have not updated in the last month.
# or 6 months if they have a display name. 
# All Static assigned Leases on the firewall will never be deleted by the script
# even if removed from the firewall.
    while True:
        time.sleep(dbMainDelay)

        conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db)
        state = ("delete from Group_User_Map where DHCP_UID in (select UID from DHCP where  LeaseTime <> '1970-01-01 00:00:01'  and  LeaseTime < (NOW() - INTERVAL %s month)  and DisplayName is null);") %(dbCleanDhcpNoDisplay)

        cur = conn.cursor()
        cur.execute(state)
        cur.close()

        state1 = ("Delete from DHCP where LeaseTime <> '1970-01-01 00:00:01'  and  LeaseTime < (NOW() - INTERVAL %s month)  and DisplayName is null;") %(dbCleanDhcpNoDisplay)

        cur1 = conn.cursor()
        cur1.execute(state1)
        cur1.close()

        state2 = ("delete from Group_User_Map where DHCP_UID in (select UID from DHCP where  LeaseTime <> '1970-01-01 00:00:01'  and  LeaseTime < (NOW() - INTERVAL %s month)  and DisplayName is not null);")  %(dbCleanDhcpDisplay)


        cur2 = conn.cursor()
        cur2.execute(state2)
        cur2.close()

        state3 = ("Delete from DHCP where LeaseTime <> '1970-01-01 00:00:01'  and  LeaseTime < (NOW() - INTERVAL %s month)  and DisplayName is not null;")  %(dbCleanDhcpDisplay)


        cur3 = conn.cursor()
        cur3.execute(state)
        cur3.close()

        conn.commit() 
        conn.close()  

    
def collectdhcp(): 
# This is the section of code that goes to the firewall and retrieves the DHCP
# data sessions based on variables in the variables.py file.
# the data it collects from the firewall is write into the SQL database.

    myssl = ssl.create_default_context();
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE
    conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db)
    
    typeop = "op"
# the XML path to retireve the data from the DHCP server on the firewall.
    cmd = "<show><dhcp><server><lease><interface>%s</interface></lease></server></dhcp></show>" %(interface)
    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
    req = urllib.request.Request(cmd1, data=None )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result = resp_str.read()
# The following lines extract the IP, MAC-Address and Hostname from the firewall
# result and convert it to variable to be used as part of the SQL insert.

    tree = ET.fromstring(result)
    for child in tree.iter('entry'):
        ip = child.find('ip').text
        
        mac =  child.find('mac')
        if mac is None:
            mac = 'blank'
        else:
            mac =  child.find('mac').text
             
        hostname =  child.find('hostname')
        if hostname is None:
            hostname = 'blank'
        else:
            hostname =  child.find('hostname').text

        
#        name = child.get('name')
        leasetime = child.find('leasetime')
        if leasetime is None:
            leasetime = 'Jan  1 00:00:01 1970'
            leasetime = datetime.strptime(leasetime, '%b %d %H:%M:%S %Y')
            
        else:
            leasetime =  child.find('leasetime').text
            leaselen = len(leasetime)
            leasetime = leasetime[:leaselen-1]
            leasetime = datetime.strptime(leasetime, '%a %b %d %H:%M:%S %Y')
        
# the insert statement for the data, the update on duplicate key is used 
# to make sure we maintain the MAC address link relationship when the IP address
# changes for a device.
# the check has been added to deal wiht the same mac address on mulit VLAN
# and the XML not being orderable.
        state = ("Select 'Y' from DHCP where MacAddr = '%s' and Leasetime >  '%s'  ; ") %(mac,  leasetime)
        cur = conn.cursor()
        check = cur.execute(state)
        if check > 0:
            state1 = ("insert into DHCP (IPaddr, MacAddr, Hostname, Leasetime , Source) values (INET_ATON('%s'),'%s','%s','%s' , 'FW' ) ON DUPLICATE KEY UPDATE IPaddr=INET_ATON('%s'), Hostname='%s' , Leasetime='%s' ;") %(ip, mac,  hostname, leasetime, ip,  hostname, leasetime)
            cur1 = conn.cursor()
            cur1.execute(state1)
            cur1.close()
        else:
                state1 = ("")
        cur.close()        

# to be able to add the mac-vendor, we retrieve all records from the database 
# that do not have a vendor linked to them, and have been populated from the 
# FW. 
# We then take each entry and query the api.macvendors.com database, and write 
# it back to the table.
# this is a one of process.

    state2 = ("SELECT MacAddr FROM DHCP where `source`= 'FW' and Vendor is null;")

    cur2 = conn.cursor()
    cur2.execute(state2)
    results2 = cur2.fetchall()

    for row in results2: 
        mac = row[0]
#            print (mac)

        myssl = ssl.create_default_context();
        myssl.check_hostname=False
        myssl.verify_mode=ssl.CERT_NONE
        url = "https://api.macvendors.com/%s" %(mac)
        req = urllib.request.Request(url, data=None )
        try :

# due to a issue with the certain characters returned from the api.macvendor.com
# we use a replace to remove the special character
# if the update fails, run the collect process manually, and look at the python
# error, normally it will show you the character that is the issue. and you can 
# use a replace option to convert it to a space or blank.
# as per line :  result3 = result3.replace('\uff0c', '')

            resp_str = urllib.request.urlopen(req ,context=myssl)
            result3 = resp_str.read().decode('utf-8')
            result3 = result3.replace('\uff0c', '')

# Test: to display the info back to the screen before the update, uncomment the 
# following line. with the double ##
##            print(mac ,' = ' , result3 )            
        except urllib.error.HTTPError as error:
            print(error.code)
            result3 = 'Unknown'
        cur3 = conn.cursor()

# the update statement to right the result back to the DHCP table.
# using double quotes rather than single quotes as single quote are part of some
# of the string returns, hence the difference in structure of the statemnet line

        state3 = ("UPDATE DHCP set vendor = \"%s\" where MacAddr = \"%s\";") %(result3, mac)
        cur3.execute(state3)
        cur3.close()
# due to a limitation, on the macvendor api, we are only allowed to query the DB
# once a second, hence the sleep statement.
# also limited to 5000 queries a day. 
# if you are hitting that, then we need to consider what you are doing with this
# tool. We can address with either a commercial licnece for the macvendor.com db
# or do some local cache structure. I can not see this being needed.
        time.sleep(1)

        cur2.close()
# import, all the statements run above is this section are no commited until the
# following line, if you want to do a lot of testing without updateing the 
# database, you can temporay comment out the commit. (not recommended)
        conn.commit()         
        
#  
## the folllowing section just retrieves the latest status information of the 
## firewall, the Model, SN, and the software revisions. 
## writing this to the DB, but could easily be to a temp file if needed. 
#
#    typeop = "op"
#    cmd = "<show><system><info></info></system></show>" 
#    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
#    req = urllib.request.Request(cmd1, data=None )
#    resp_str = urllib.request.urlopen(req ,context=myssl)
#    result4 = resp_str.read()
##    print (result4)
#    tree = ET.fromstring(result4)
#    for child in tree.iter('system'):
#        hostname = child.find('hostname').text
#        uptime =  child.find('uptime').text
#        model =  child.find('model').text
#        serial =  child.find('serial').text
#        swversion =  child.find('sw-version').text
#        appversion =  child.find('app-version').text
#        avversion =  child.find('av-version').text
#        appversion =  child.find('app-version').text
#        threatversion =  child.find('threat-version').text
#        wildfireversion =  child.find('wildfire-version').text
#        appdate =  child.find('app-release-date').text
#        avdate =  child.find('av-release-date').text
#        threatdate =  child.find('threat-release-date').text
#        wildfiredate =  child.find('wildfire-release-date').text
#
#
## writes the data to the FWdata table as a update, so we only maintain a single
## record, would be easy to add a history, but changing this to a insert. 
## if we changed this to a insert, so as to maintain history, we would add a 
## foreign key on the combination of the  (swversion,appversion,avversion,
## appversion,wildfireversion)
#
##  TODO: add insert statement as a example and the SQL to add Foreign Key.
#
#        state4 = ("UPDATE FWdata SET `hostname` = \"%s\",  `uptime` = \"%s\", `model` = \"%s\", `serial` = \"%s\", `swversion` = \"%s\", `appversion` = \"%s\", `avversion` =\"%s\", `threatversion` = \"%s\", `wildfireversion` = \"%s\", `appdate` = \"%s\",    `avdate` = \"%s\",    `threatdate` = \"%s\",    `wildfiredate` = \"%s\"   ORDER BY UID DESC LIMIT 1;" ) %(hostname,  uptime, model, serial, swversion,  appversion, avversion, threatversion, wildfireversion, appdate, avdate ,threatdate, wildfiredate)
#
#        cur4 = conn.cursor()
#        cur4.execute(state4)
#        cur4.close()
#        conn.commit()  
        
    conn.close() 
    
    
def createxmlfile(): 
# This is the section of code created the xml file that is used to populate 
# the user-id database.
# the file XML structure is created as per Palo Alto Networks API documentation.
# the file structure adds both user and group entires.
# the default life of the user-id entries is controlled under the firewall.
# Device/User Identification/user-Mapping/Palo Alto Networks User-ID Agent setup
# change the user Identification Timeout to a value you determine to be acceptable
# it should be set to at least double the script time interval.
# Default timeout on user-ID is 45 Minutes.
## CLI command to set it to one hour.
## set user-id-collector setting ip-user-mapping-timeout 60


#<uid-message>
#	<type>update</type>
#	<payload>
#		<login>
#			<entry ip="192.168.1.1" name="test" />
#		</login>
#		<groups>
#			<entry name="admin">
#				<members>
#					<entry name="test" />
#				</members>
#			</entry>
#		</groups>
#	</payload>
#</uid-message>



    root = ET.Element("uid-message")
    ET.SubElement(root, "type").text = "update"
    payload = ET.SubElement(root, "payload")

    login = ET.SubElement(payload, "login")    
 
    conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db)

# Query is made to only pull back a single entry for each IP-address based upon 
# the most recent allocation. 
# it is possible that the DB contains multiple entries for the same IP, as DHCP 
# will reuse the IP-addresses. but the MAC addresses as hostnames are unique.

#    state = ("Select IFNULL(DisplayName, Hostname) as name, INET_NTOA(IPaddr) as ip  from DHCP where (Hostname <> 'blank' or DisplayName is not null) and LeaseTime in ( select MAX(LeaseTime)  from DHCP group by IPaddr desc)  and ( LeaseTime = '1970-01-01 00:00:01'  or LeaseTime > (NOW() - INTERVAL %s WEEK)) order by IPaddr;") %(LeaseLife)
    state = ("SELECT IFNULL(DisplayName, Hostname) AS name, INET_NTOA(IPaddr) AS ip FROM DHCP WHERE (Hostname <> 'blank' OR DisplayName IS NOT NULL)         AND LeaseTime IN (SELECT            MAX(LeaseTime)        FROM            DHCP        GROUP BY IPaddr DESC) AND ( LeaseTime > (NOW() - INTERVAL %s WEEK) and Source = 'fw')  or Source = 'form' or LeaseTime = '1970-01-01 00:00:01' ORDER BY IPaddr;")  %(LeaseLife)
    cur = conn.cursor()
    cur.execute(state)
    results = cur.fetchall()
    for row in results: 
        Name = row[0]
        IP = row[1]
        ET.SubElement(login, "entry", name=Name , ip=IP )
#        print(Name , IP)
       
    cur.close()
    groups = ET.SubElement(payload, "groups")  

# query the groups that need to be imported.     
    state1 = ("select GName from GROUPS;")
    cur1 = conn.cursor()
    cur1.execute(state1)
    results1 = cur1.fetchall()
    for row in results1: 
        Group = row[0]
# query the users IDs linked to the group and then add them to the XML structure
# as members of the group
# 
        group = ET.SubElement(groups, "entry", name=Group )
        state2 = ("SELECT distinct(ifnull(DHCP.DisplayName,DHCP.Hostname)) FROM DHCP where UID in (select Group_User_Map.DHCP_UID from Group_User_Map where Group_User_Map.Group_UID = (select UID from GROUPS where GName= '%s'))") %(Group)
        cur2 = conn.cursor()
        cur2.execute(state2)
        results2 = cur2.fetchall()
        members = ET.SubElement(group , "members") 
        for row in results2: 
            Member = row[0]
            ET.SubElement(members, "entry", name=Member )
        
    
    cur2.close()
    cur1.close()

    conn.close() 
    
    
    tree = ET.ElementTree(root)
    tree.write("userID.xml")

    
def sendapi(): 
    # Section of the code, that takes the XML file already created, and sends it 
# to the firewall to be imported as the userID.
# by default the import life on any record is 45 minutes.
# see above section for how to edit the value.
# we do not delete user-id entries, we either let them expire
# or we over write them with a new entry.
    
    myssl = ssl.create_default_context();
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE
    


    fileN = open('userID.xml', 'r')
    # xml convert the file to a single URL #
    xml = urllib.parse.quote_plus(fileN.read())
    typeop = "user-id"
    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,xml)

    req = urllib.request.Request(cmd1, data=None )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result = resp_str.read()

## DEBUG: uncomment so as to be able    
##    print (result)


def dbuser():
    while True:
        collectdhcp()
        createxmlfile()
        sendapi()
        time.sleep(dbUserDelay)
        
def initBackgroundProcs():
    thread1 = threading.Thread(target=dbuser)
    thread2 = threading.Thread(target=dbmain)
    thread1.start()
    thread2.start()

    

mysql =MySQL(app)


###
# The web structure is defined from this point onwards.
#
###

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/register")
def register():
    return render_template('register.html')
        
        
@app.route("/upgrade")
def upgrade():
    myssl = ssl.create_default_context();
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE

    typeop = "op"
    cmd = "<show><system><info></info></system></show>" 
    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
    req = urllib.request.Request(cmd1, data=None )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result4 = resp_str.read()
#    print (result4)
    tree = ET.fromstring(result4)
    for child in tree.iter('system'):
        swversion =  child.find('sw-version').text

    
    cmd = "<request><system><software><check></check></software></system></request>"
    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
    req = urllib.request.Request(cmd1, data=None )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result5 = resp_str.read()
#    print (result5)
    tree = ET.fromstring(result5)
    for child in tree.iter('result'):
        latestversion = child.find('./sw-updates/versions/entry/version').text
    
    return render_template('upgrade.html',  swversion=swversion, latestversion=latestversion )
        
@app.route("/upgradestart/")
def upgradestart():
	  version = (request.args.get('version', None))
	  job = int(request.args.get('job', None))
#	  complete = int(request.args.get('complete', None))

	  if job == 0:
	    myssl = ssl.create_default_context();
	    myssl.check_hostname=False
	    myssl.verify_mode=ssl.CERT_NONE	
		
	    typeop = "op"
	    cmd = "<request><system><software><download><version>" + version + "</version></download></software></system></request>"
	    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
	    req = urllib.request.Request(cmd1, data=None )
	    resp_str = urllib.request.urlopen(req ,context=myssl)
	    response = resp_str.read()
	    print (response)
	    if response:
	    	tree = ET.fromstring(response)
	    	job = tree.find('./result/job').text
	    	print ("Downloading version " + version + " in job " + job)	
	    	flash ('Downloading version', 'success')
	    	return redirect(url_for('upgradestart' ,  version=(version), job =(job) ))

	  complete = 0
	  if job is not None:
	    while complete != 1:
	    	myssl = ssl.create_default_context();
	    	myssl.check_hostname=False
	    	myssl.verify_mode=ssl.CERT_NONE
	    	typeop = "op"
	    	job = str(job)
	    	cmd = "<show><jobs><id>" + job + "</id></jobs></show>"
	    	cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
	    	req = urllib.request.Request(cmd1, data=None )
	    	resp_str = urllib.request.urlopen(req ,context=myssl)
	    	response = resp_str.read()
	    	if response:
   				tree = ET.fromstring(response)
   				if tree.find('./result/job/status').text == "ACT":
   					status = tree.find('./result/job/progress').text + "% complete"
   					print ('{0}\r'.format(status)),
   					return render_template('upgradedownload.html',  status=status ,version = version , job = job)

   				elif tree.find('./result/job/status').text == "FIN":
   					complete = 1
   					job = 0

	    return redirect(url_for('upgradeinstall' ,  version=(version), job =(job) ))


@app.route("/upgradeinstall/")
def upgradeinstall():
	  version = (request.args.get('version', None))
	  job = int(request.args.get('job', None))
#	  complete = int(request.args.get('complete', None))

	  if job == 0:
	    myssl = ssl.create_default_context();
	    myssl.check_hostname=False
	    myssl.verify_mode=ssl.CERT_NONE	
		
	    typeop = "op"
	    cmd = "<request><system><software><install><version>" + version + "</version></install></software></system></request>"
	    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
	    req = urllib.request.Request(cmd1, data=None )
	    resp_str = urllib.request.urlopen(req ,context=myssl)
	    response = resp_str.read()
	    print (response)
	    if response:
	    	tree = ET.fromstring(response)
	    	job = tree.find('./result/job').text
	    	print ("Downloading version " + version + " in job " + job)	
	    	flash ('Installing version', 'success')
	    	return redirect(url_for('upgradeinstall' ,  version=(version), job =(job) ))

	  complete = 0
	  if job is not None:
	    while complete != 1:
	    	myssl = ssl.create_default_context();
	    	myssl.check_hostname=False
	    	myssl.verify_mode=ssl.CERT_NONE
	    	typeop = "op"
	    	job = str(job)
	    	cmd = "<show><jobs><id>" + job + "</id></jobs></show>"
	    	cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
	    	req = urllib.request.Request(cmd1, data=None )
	    	resp_str = urllib.request.urlopen(req ,context=myssl)
	    	response = resp_str.read()
	    	if response:
   				tree = ET.fromstring(response)
   				if tree.find('./result/job/status').text == "ACT":
   					status = tree.find('./result/job/progress').text + "% complete"
   					print ('{0}\r'.format(status)),
   					return render_template('upgradeinstall.html',  status=status ,version = version , job = job)

   				elif tree.find('./result/job/status').text == "FIN":
   					complete = 1
   					job = 0

	    return redirect(url_for('upgradeconfirm', reboot=0))
		      
@app.route("/upgradeconfirm/")
def upgradeconfirm():
	  reboot = int(request.args.get('reboot', None))
	  myssl = ssl.create_default_context();
	  myssl.check_hostname=False
	  myssl.verify_mode=ssl.CERT_NONE
	    
	  if reboot == 0:
	  	return render_template('upgradeconfirm.html')
	  else:

	    typeop = "op"
	    cmd = "<request><restart><system></system></restart></request>"
	    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
	    req = urllib.request.Request(cmd1, data=None )
	    resp_str = urllib.request.urlopen(req ,context=myssl)
	    response = resp_str.read()
	    if response:
	    	tree = ET.fromstring(response)
	    	if tree.get('status') == "success":
	    		print ("Rebooting the firewall")
	    		flash ('Rebooting the firewall', 'success')
	    		return redirect(url_for('system'))

	  return redirect(url_for('system'))

@app.route("/reboot/")
def reboot():
	  reboot = int(request.args.get('reboot', None))
	  myssl = ssl.create_default_context();
	  myssl.check_hostname=False
	  myssl.verify_mode=ssl.CERT_NONE
	    
	  if reboot == 0:
	  	return render_template('reboot.html')
	  else:

	    typeop = "op"
	    cmd = "<request><restart><system></system></restart></request>"
	    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
	    req = urllib.request.Request(cmd1, data=None )
	    resp_str = urllib.request.urlopen(req ,context=myssl)
	    response = resp_str.read()
	    if response:
	    	tree = ET.fromstring(response)
	    	if tree.get('status') == "success":
	    		print ("Rebooting the firewall")
	    		flash ('Rebooting the firewall', 'success')
	    		return redirect(url_for('system'))

	  return redirect(url_for('system'))
	  

@app.route("/system")
def system():
    myssl = ssl.create_default_context();
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE

    typeop = "op"
    cmd = "<show><system><info></info></system></show>" 
    cmd1 = "%s?key=%s&type=%s&cmd=%s" %(base,key,typeop,cmd)
    req = urllib.request.Request(cmd1, data=None )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result4 = resp_str.read()
#    print (result4)
    tree = ET.fromstring(result4)
    for child in tree.iter('system'):
        hostname = child.find('hostname').text
        uptime =  child.find('uptime').text
        model =  child.find('model').text
        serial =  child.find('serial').text
        swversion =  child.find('sw-version').text
        appversion =  child.find('app-version').text
        avversion =  child.find('av-version').text
        appversion =  child.find('app-version').text
        threatversion =  child.find('threat-version').text
        wildfireversion =  child.find('wildfire-version').text
        appdate =  child.find('app-release-date').text
        avdate =  child.find('av-release-date').text
        threatdate =  child.find('threat-release-date').text
        wildfiredate =  child.find('wildfire-release-date').text
    

    return render_template('system.html',  hostname=hostname , uptime=uptime, model=model, serial=serial,
            swversion=swversion, appversion=appversion, avversion=avversion,
            threatversion =  threatversion,  wildfireversion =  wildfireversion, appdate =  appdate, avdate =  avdate,
            threatdate =  threatdate, wildfiredate=wildfiredate)
            
	


@app.route("/fwlist")
def fwlist():
    cur = mysql.connection.cursor()
    state = ("SELECT IFNULL(DisplayName, Hostname) AS name, INET_NTOA(IPaddr) AS ip FROM DHCP WHERE (Hostname <> 'blank' OR DisplayName IS NOT NULL)         AND LeaseTime IN (SELECT            MAX(LeaseTime)        FROM            DHCP        GROUP BY IPaddr DESC) AND ( LeaseTime > (NOW() - INTERVAL %s WEEK) and Source = 'fw')  or Source = 'form' or LeaseTime = '1970-01-01 00:00:01' ORDER BY IPaddr;")  %(LeaseLife)
    result = cur.execute(state)
    results = cur.fetchall()
    
    if result > 0:
        return render_template('fwlist.html', results=results)
    else:
        msg = 'No devices registered'
        return render_template('fwlist.html', msg=msg)


    cur.close()
        
    return render_template('fwlist.html')


@app.route("/force")
def force():
    createxmlfile()
    sendapi()

    cur = mysql.connection.cursor()
    state = ("SELECT IFNULL(DisplayName, Hostname) AS name, INET_NTOA(IPaddr) AS ip FROM DHCP WHERE (Hostname <> 'blank' OR DisplayName IS NOT NULL)         AND LeaseTime IN (SELECT            MAX(LeaseTime)        FROM            DHCP        GROUP BY IPaddr DESC) AND ( LeaseTime > (NOW() - INTERVAL %s WEEK) and Source = 'fw')  or Source = 'form' or LeaseTime = '1970-01-01 00:00:01' ORDER BY IPaddr;")  %(LeaseLife)
    result = cur.execute(state)
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
    initBackgroundProcs()
    app.secret_key='PaloAltoNetworksUserIDRegister'
    app.run(debug=True , host=webhost , port=webport)

    