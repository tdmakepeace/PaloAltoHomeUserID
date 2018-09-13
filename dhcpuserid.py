'''
 The purpose of this tool is to allow the population of the User-ID database 
 on the firewall, the source for the data is either from the DHCP lease database
 or manually entered static IP-Address entries.
 In addition to the User-ID, group assignments are also supported for both dynamic
 and static data.
'''

import urllib
import urllib.request
import urllib.parse
import sys
import ssl
import xml.etree.ElementTree as ET
import pymysql
import time
import getpass
from datetime import datetime


# TODO:   Temp variables to be moved to the panrc file.
dbCleanDhcpNoDisplay = 1
dbCleanDhcpDisplay = 6



# Test to make sure a variables file exists.
# if file exist it will move onto the rest of the code.
# if it does not exist,  but the setup option is called.
# it will move on to the rest of the code.
# anything else it will print to screen and exit.

try:
    from variables import *
except ImportError:
    for arg in sys.argv: 1
# use the command line to call the function from a single script.
    if arg == "setup":
        print (" ")
    else:
        print ("Run dhcpuserid.py setup")
        sys.exit(0)
        

    
def createvariables(): 
# The Createvariables option is called by the "setup" argument being called.
# The option is used for the user to provide the variables to be used in a 
# interactive process, IP and username and password on the firewall.
# Database connection details.
# the DHCP interface you are intrested in managing.
# if you want more than one interface, but not all let me know and i will add 
# support for 2 or 3 interface options.

    Host = input("Enter the IP or host name of the Firewall: ")
    Admin = input("Enter the admin username: ")
    Password = getpass.getpass("Enter the admin password: ")

    myssl = ssl.create_default_context();
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE

# uses the admin username and password onetime to retrieve the APIKey.
# we do not store the admin account and password data.

    url = "https://%s/api/?type=keygen&user=%s&password=%s" %(Host,Admin,Password)
    req = urllib.request.Request(url, data=None )
    resp_str = urllib.request.urlopen(req ,context=myssl)
    result = resp_str.read()
    tree = ET.fromstring(result)
    for child in tree.iter('key'):
        apikey = child.text

    key = "key = '%s' \n" %(apikey)
    base = "base ='https://%s/api/'\n" %(Host)


# requests the user to input the details on the Mysql server to connect to.
# if you need to edit, it is easier to edit the variables.py rather than run the
# the whole script again
# Just hitting enter will result in the example value being used
    dbHost = input("Enter the IP or host name of the Mysql Server: Default 'localhost'")
    if dbHost:
        dbHost = "host = '%s' \n" %(dbHost)
    else:
        dbHost = "host = 'localhost' \n"

    dbPort = input("Enter the port number for the Mysql Server: Default '3306'")
    if dbPort:
        dbPort = "port = %s \n" %(dbPort)
    else:
        dbPort = "port = 3306 \n"

    dbUser = input("Enter the admin user for the Mysql Server: Default 'PANuser'")
    if dbUser:
        dbUser = "user = '%s' \n" %(dbUser)
    else:
        dbUser = "user = 'PANuser' \n"

    dbPass = input("Enter the admin password for the Mysql Server: Default 'password'")
    if dbPass:
        dbPass = "passwd = '%s' \n" %(dbPass)
    else:
        dbPass = "passwd = 'password' \n"

    dbDb = input("Enter the name of the database: Default 'PaloAltoHomeUserID'")
    if dbDb:
        dbDb = "db = '%s' \n" %(dbDb)
    else:
        dbDb = "db = 'PaloAltoHomeUserID' \n"
    
# the name entered must be an exact match for the interdace name on the firewall
# or the word "all" in lower case.
# also can be edited in the variables.py file at a late date if required.
    interface = input("Enter the full name of the interface you want the DHCP data imported from e.g. ethernet1/2, ethernet1/2.2, all:")
    interface = "interface = '%s' \n" %(interface)
    
# output all the variables to a file for future use
    resp_str.close
    f = open('variables.py', 'w')
    f.write(key)
    f.write(base)
    f.write(dbHost)
    f.write(dbPort)
    f.write(dbUser)
    f.write(dbPass)
    f.write(dbDb)
    f.write(interface)
    f.close()
    
    print ("\n\nvariables written to file")
 
 
def dbsetup():
# this is a one off process for the creation of the database tables to be used
# by the tool.

#'''
# the tool will use 4 DB tables to manage the system.
# 
# DHCP - storage of the DHCP and Static IP-Address Entries.
# GROUPS - the name of the groups and there local description.
# Group_User_Map - A mapping of the relationship of users to groups.
# FWdata - A status check from the firewall and it databases.
#'''

#Main DHCP data and Static IP-Address assignment table.
    conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db)
    state = """ CREATE TABLE IF NOT EXISTS `DHCP` (
  `UID` int(11) NOT NULL AUTO_INCREMENT,
  `MacAddr` varchar(20) NOT NULL,
  `Vendor` varchar(50) DEFAULT NULL,
  `IPaddr` decimal(11,0) DEFAULT NULL,
  `Hostname` varchar(50) DEFAULT NULL,
  `DisplayName` varchar(50) DEFAULT NULL,
  `LeaseTime` datetime DEFAULT NULL,
  `Source` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`UID`),
  UNIQUE KEY `MacAddr_UNIQUE` (`MacAddr`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;"""
    
    cur = conn.cursor()
    cur.execute(state)
    cur.close()

# The name of the groups to be updated on the firewall.

    state1 = """ CREATE TABLE IF NOT EXISTS `GROUPS` (
  `UID` int(11) NOT NULL AUTO_INCREMENT,
  `GName` varchar(50) DEFAULT NULL,
  `Desc` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`UID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1; """
    
    cur1 = conn.cursor()
    cur1.execute(state1)
    cur1.close()

# the DHCP to Group mapping table
# it is possible to be a memeber of mutliple groups, and the UID values are 
# recorded in this table.

    state2 = """CREATE TABLE IF NOT EXISTS `Group_User_Map` (
  `UID` int(11) NOT NULL AUTO_INCREMENT,
  `DHCP_UID` int(11) DEFAULT NULL,
  `Group_UID` int(11) DEFAULT NULL,
  PRIMARY KEY (`UID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;"""
    
    cur2 = conn.cursor()
    cur2.execute(state2)
    cur2.close()

# this table is used to record the state information.
# uptime and DB updated from content updated.
    state3 = """CREATE TABLE IF NOT EXISTS `FWdata` (
  `UID` int(11) NOT NULL AUTO_INCREMENT,
  `hostname` varchar(40) NOT NULL,
  `uptime` varchar(20) DEFAULT NULL,
  `model` varchar(50) DEFAULT NULL,
  `serial` varchar(50) DEFAULT NULL,
  `swversion` varchar(50) DEFAULT NULL,
  `appversion` varchar(50) DEFAULT NULL,
  `avversion` varchar(50) DEFAULT NULL,
  `threatversion` varchar(50) DEFAULT NULL,
  `wildfireversion` varchar(50) DEFAULT NULL,
  `appdate` varchar(50) DEFAULT NULL,
  `avdate` varchar(50) DEFAULT NULL,
  `threatdate` varchar(50) DEFAULT NULL,
  `wildfiredate` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`UID`)
 ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;"""
    
    cur3 = conn.cursor()
    cur3.execute(state3)
    cur3.close()

# TODO: need a temp record, as a update is used by the collect process
# ideally will look at changing it to something cleaner, as did not want to
# add a load of indexes to the table.
    state4 = """INSERT IGNORE  INTO `FWdata` (`uid`, `hostname`) VALUES (1, 'temp');"""
    
    cur4 = conn.cursor()
    cur4.execute(state4)
    cur4.close()
    
        
    conn.commit() 
    conn.close()  

def dbmain():
# TODO:    A new section to act as a DB maintainence.
# still to be worked on.
# but will currently delete any records that have not updated in the last month.
# or 6 months if they have a display name. 
# All Static assigned Leases on the firewall will never be deleted by the script
# even if removed from the firewall.

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
        
  
# the folllowing section just retrieves the latest status information of the 
# firewall, the Model, SN, and the software revisions. 
# writing this to the DB, but could easily be to a temp file if needed. 

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


# writes the data to the FWdata table as a update, so we only maintain a single
# record, would be easy to add a history, but changing this to a insert. 
# if we changed this to a insert, so as to maintain history, we would add a 
# foreign key on the combination of the  (swversion,appversion,avversion,
# appversion,wildfireversion)

#  TODO: add insert statement as a example and the SQL to add Foreign Key.

        state4 = ("UPDATE FWdata SET `hostname` = \"%s\",  `uptime` = \"%s\", `model` = \"%s\", `serial` = \"%s\", `swversion` = \"%s\", `appversion` = \"%s\", `avversion` =\"%s\", `threatversion` = \"%s\", `wildfireversion` = \"%s\", `appdate` = \"%s\",    `avdate` = \"%s\",    `threatdate` = \"%s\",    `wildfiredate` = \"%s\"   ORDER BY UID DESC LIMIT 1;" ) %(hostname,  uptime, model, serial, swversion,  appversion, avversion, threatversion, wildfireversion, appdate, avdate ,threatdate, wildfiredate)

        cur4 = conn.cursor()
        cur4.execute(state4)
        cur4.close()
        conn.commit()  
        
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

    state = ("Select IFNULL(DisplayName, Hostname) as name, INET_NTOA(IPaddr) as ip  from DHCP where (Hostname <> 'blank' or DisplayName is not null) and LeaseTime in ( select MAX(LeaseTime)  from DHCP group by IPaddr desc)  and ( LeaseTime = '1970-01-01 00:00:01'  or LeaseTime > (NOW() - INTERVAL 1 WEEK)) order by IPaddr;")
    cur = conn.cursor()
    cur.execute(state)
    results = cur.fetchall()
    for row in results: 
        Name = row[0]
        IP = row[1]
        ET.SubElement(login, "entry", name=Name , ip=IP )
        #    print(Name , IP)
       
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
    
    
    
    
def userguide():   
    
    print (" The following is the user guide for the tool")
    print (" --------------------------------------------")
    print (" https://github.com/tdmakepeace/PaloAltoHomeUserID/wiki")
    
    

if __name__ == '__main__':
    
    for arg in sys.argv: 1
# use the command line to call the function from a single script.
# the run option runs multiple function sequentionally.
    if arg == "help":
        userguide()
    elif arg == "setup":
        createvariables()
    elif arg == "dbsetup":
        dbsetup()
    elif arg == "dbmain":
        dbmain() 
    elif arg == "dhcp":
        collectdhcp()
    elif arg == "xml":
        createxmlfile()
    elif arg == "update":
        sendapi()
    elif arg == "run":
        collectdhcp()
        createxmlfile()
        sendapi()
    else:
        userguide()
       
