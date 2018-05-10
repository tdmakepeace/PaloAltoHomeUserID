# PaloAltoHomeUserID

The following is the user guide for the tool
--------------------------------------------
I have written the tool to be able to manage the UserID data for a home FW or SOHO deployment.
 
There are a number of dependency for getting the tool to work. 

Firstly the tool will require access to a MySQL database.
It has been written for Python3+ and requires the following modules. 
pip install flask
pip install pymysql
pip install flask-mysqldb
pip install flask-wtf

Once the dependency are installed, you can clone the git repo, and run the two main scripts.

	dhcpuser.py
	WebGui.py

	
dhcpuser.py is the main script that will talk to the firewall and the SQL database.

the script will extract the DHCP log from the firewall, and import it into a SQL table.
Once in the SQL table the script will then read the table and create a userID import file, and then post it to the firewall to maintain userID records.
As the name of the DHCP hostname, might not be the name you want to see in the LOG, you can change the name used via the WebGui.
Also as you might have a number of devices that use Static IP-Addresses, the WebGui will allow you to manage them as entries so they also get pushed out to the firewall.

Ideally you would set the dhcpuser script to update the firewall every 30 minutes, but that choice is up to you.

To run it under a crontab 
python dhcpuser.py run

However to set the environment up first, you need to run the "setup" to set the variables and then the "dbsetup" to create the table.

python dhcpuser.py setup
- the firewall admin details are not stored, they are just used to create the API key.
- all the questions are self explainatory as you go throught the process.
- if you have multiple DHCP interfaces, you can lock it down to one interface or set it to all.

python dhcpuser.py dbsetup
-creates the table to be used for storing the IP records in.

to be able to run the script in sections to validate its process. you can call the following options.

python dhcpuser.py dhcp
- collect the DHCP data and import it into the DB.
python dhcpuser.py xml
- Create the userID.xml file to be pushed to the firewall to update the records.
python dhcpuser.py update
- to push the XML file to the firewall.


WebGui.py is a flask WebGui on port 5000 that allows you to manage the DHCP data records, and add static records.
python WebGui.py
