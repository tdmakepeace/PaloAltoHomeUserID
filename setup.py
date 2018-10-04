'''
 The purpose of this script is the initial setup and configuration of the SQL database.
 
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
    if arg == "variables":
        print (" ")
    else:
        print ("Run setup.py variables")
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

## variable file creation

    header = "## The master variable file \n# file can be edited directly after initial cretion \n#\n\n"
    key = "# The API key to be used to connect to the firewall. \n# key = 'LUFRPT10VGJKTEV6a0R4L1JXd0ZmbmNvdUEwa25wMlU9d0N5d292d2FXNXBBeEFBUW5pV2xoZz09' \nkey = '%s' \n\n" %(apikey)
    base = "# the Base url the script connects to. it is the https://<fw ip address/api/ \n#base ='https://192.168.55.10/api/' \nbase ='https://%s/api/'\n\n" %(Host)


# requests the user to input the details on the Flask server 
# if you need to edit, it is easier to edit the variables.py rather than run the
# the whole script again

    webhost = input("Enter the IP or host name you want the web service to run on: Default 'localhost'")
    if webhost:
        webhost = "webhost = '%s' \n" %(webhost)
    else:
        webhost = "webhost = 'localhost' \n"        
    webhost = "# the host the webservice is hosted on, FQDN or IP is required.\n#webhost = 'localhost' \n%s \n" %(webhost)

    webport = input("Enter the port you want the web service to run on: Default '5000'")
    if webport:
        webport = "webport = '%s' \n" %(webport)
    else:
        webport = "webport = '5000' \n"        
    webport = "# the port the webservice is hosted on, default flask is 5000..\n#webport = '5000'  \n%s \n" %(webport)

    
# requests the user to input the details on the Mysql server to connect to.
    dbHost = input("Enter the IP or host name of the Mysql Server: Default 'localhost'")
    if dbHost:
        dbHost = "host = '%s' \n" %(dbHost)
    else:
        dbHost = "host = 'localhost' \n"        
    dbHost = "# the host the MYSQL database is hosted on, FQDN or IP is required.\n#host = '192.168.102.6' \n%s \n" %(dbHost)
    
    dbPort = input("Enter the port number for the Mysql Server: Default '3306'")
    if dbPort:
        dbPort = "port = %s \n" %(dbPort)
    else:
        dbPort = "port = 3306 \n"
    dbPort = "# the default port that the MySQL database is running on. \n#port = 3306 \n%s \n" %(dbPort)
    
    dbUser = input("Enter the admin user for the Mysql Server: Default 'PANuser'")
    if dbUser:
        dbUser = "user = '%s' \n" %(dbUser)
    else:
        dbUser = "user = 'PANuser' \n"
    dbUser = "# The user to connect to the MySQL database. \n#user = 'PANuser' \n%s \n" %(dbUser)
    
    dbPass = input("Enter the admin password for the Mysql Server: Default 'Password'")
    if dbPass:
        dbPass = "passwd = '%s' \n" %(dbPass)
    else:
        dbPass = "passwd = 'password' \n"   
    dbPass = "# The Password of the user connecting to the MySQL database. \n #passwd = 'password' \n%s \n" %(dbPass)
    
    dbDb = input("Enter the name of the database: Default 'PaloAltoHomeUserID'")
    if dbDb:
        dbDb = "db = '%s' \n" %(dbDb)
    else:
        dbDb = "db = 'PaloAltoHomeUserID' \n"    
    dbDb = "# The Name of the database the data is to be store in. \n#db = 'PaloAltoHomeUserID'\n%s \n" %(dbDb)
    
    
# the name entered must be an exact match for the interdace name on the firewall
# or the word "all" in lower case.
# also can be edited in the variables.py file at a late date if required.
    interface = input("Enter the full name of the interface you want the DHCP data imported from e.g. ethernet1/2, ethernet1/2.2, all:")
    if interface:
        interface = "interface = '%s' \n" %(interface)
    else:
        interface = "interface = 'all' \n"   
    interface = "#   Enter the full name of the interface you want the DHCP data imported from e.g. ethernet1/2, ethernet1/2.2, all \n #interface = 'ethernet1/2' \n%s \n" %(interface)
    
# the following are DB maintainence parts. the defaults are defind based on my testing.

    dbCleanDhcpNoDisplay = input("Enter the database maintanence window for old records with no static name configured (value in months): Default '1'")
    if dbCleanDhcpNoDisplay:
        dbCleanDhcpNoDisplay = "dbCleanDhcpNoDisplay = %s \n" %(dbCleanDhcpNoDisplay)
    else:
        dbCleanDhcpNoDisplay = "dbCleanDhcpNoDisplay = 1 \n"   
    dbCleanDhcpNoDisplay = "# The maintaince clean up on the database, uses 2 variables to deciede what data to clean out of the database. \n\n# dbCleanDhcpNoDisplay value is the time in months that will be removed from the database is no static display name it set. \n#dbCleanDhcpNoDisplay = 1 \n%s \n" %(dbCleanDhcpNoDisplay)  
    
    dbCleanDhcpDisplay = input("Enter the database maintanence window for old records with static name configured (value in months): Default '6'")
    if dbCleanDhcpDisplay:
        dbCleanDhcpDisplay = "dbCleanDhcpDisplay = %s \n" %(dbCleanDhcpDisplay)
    else:
        dbCleanDhcpDisplay = "dbCleanDhcpDisplay = 6 \n"   
    dbCleanDhcpDisplay = "# dbCleanDhcpDisplay value is the time in months that will be removed from the database where a static display name it set.\n#dbCleanDhcpDisplay = 6 \n%s \n" %(dbCleanDhcpDisplay)  

# The length of the time to sleep between doing maintance on the database.
# currently set to every day 86400.
    dbMainDelay = input("How often do you want to run the DB maintainence (value in seconds): Default '86400'")
    if dbMainDelay:
        dbMainDelay = "dbMainDelay = %s \n" %(dbMainDelay)
    else:
        dbMainDelay = "dbMainDelay = 86400 \n"   
    dbMainDelay = "# The length of the time to sleep between doing maintance on the database. \n# currently set to every day 86400. \n#dbMainDelay = 86400 \n%s \n" %(dbMainDelay)  

# The lenght of the time to sleep between doing a firewall query and update.
# default value is 300 seconds every 5 minutes 
    dbUserDelay = input("How often do you want to run the firewall update (value in seconds): Default '300'")
    if dbUserDelay:
        dbUserDelay = "dbUserDelay = %s \n" %(dbUserDelay)
    else:
        dbUserDelay = "dbUserDelay = 300 \n"   
    dbUserDelay = "# The lenght of the time to sleep between doing a firewall query and update. \n# default value is 300 seconds every 5 minutes \n#dbUserDelay = 300 \n%s \n" %(dbUserDelay)  

# So as to only pull in the most upto date data, set the period of time you want to use to update the latest data.
# with a leaselife set to 1, it will only pull in data that has made a DHCP request in the last week. 
    LeaseLife = input("Based on your DHCP lease timer, only records newer than x weeks will be imported so as to avoid importing stale records. (value in weeks): Default '1'")
    if LeaseLife:
        LeaseLife = "LeaseLife = %s \n" %(LeaseLife)
    else:
        LeaseLife = "LeaseLife = 1 \n"   
    LeaseLife = "# So as to only pull in the most upto date data, set the period of time you want to use to update the latest data. \n# with a leaselife set to 1, it will only pull in data that has made a DHCP request in the last week.  \n# LeaseLife = 1\n%s \n" %(LeaseLife)  
    
    
    
# output all the variables to a file for future use
    resp_str.close
    f = open('variables.py', 'w')
    f.write(header)
    f.write(key)
    f.write(base)
    f.write(webhost)
    f.write(webport)
    f.write(dbHost)
    f.write(dbPort)
    f.write(dbUser)
    f.write(dbPass)
    f.write(dbDb)
    f.write(interface)
    f.write(dbCleanDhcpNoDisplay)
    f.write(dbCleanDhcpDisplay)
    f.write(dbMainDelay)
    f.write(dbUserDelay)
    f.write(LeaseLife)
    f.close()
    
    print ("\n\nVariables file created. \n\nTo edit variables, edit the variables.py file directly")
    print ("\n\nYou only need to re run the setup if you want to recreate the API key or recreate the file")
 
 
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

## this table is used to record the state information.
## uptime and DB updated from content updated.
#    state3 = """CREATE TABLE IF NOT EXISTS `FWdata` (
#  `UID` int(11) NOT NULL AUTO_INCREMENT,
#  `hostname` varchar(40) NOT NULL,
#  `uptime` varchar(20) DEFAULT NULL,
#  `model` varchar(50) DEFAULT NULL,
#  `serial` varchar(50) DEFAULT NULL,
#  `swversion` varchar(50) DEFAULT NULL,
#  `appversion` varchar(50) DEFAULT NULL,
#  `avversion` varchar(50) DEFAULT NULL,
#  `threatversion` varchar(50) DEFAULT NULL,
#  `wildfireversion` varchar(50) DEFAULT NULL,
#  `appdate` varchar(50) DEFAULT NULL,
#  `avdate` varchar(50) DEFAULT NULL,
#  `threatdate` varchar(50) DEFAULT NULL,
#  `wildfiredate` varchar(50) DEFAULT NULL,
#  PRIMARY KEY (`UID`)
# ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1;"""
#    
#    cur3 = conn.cursor()
#    cur3.execute(state3)
#    cur3.close()
#
## TODO: need a temp record, as a update is used by the collect process
## ideally will look at changing it to something cleaner, as did not want to
## add a load of indexes to the table.
#    state4 = """INSERT IGNORE  INTO `FWdata` (`uid`, `hostname`) VALUES (1, 'temp');"""
#    
#    cur4 = conn.cursor()
#    cur4.execute(state4)
#    cur4.close()
    
        
    conn.commit() 
    conn.close()  
    
def userguide():
    print ("still to be written")
    


if __name__ == '__main__':
    
    for arg in sys.argv: 1
# use the command line to call the function from a single script.
# the run option runs multiple function sequentionally.
    if arg == "help":
        userguide()
    elif arg == "variables":
        createvariables()
    elif arg == "db":
        dbsetup()
    else:
        userguide()
       
       