import gdata.spreadsheet.service
import gdata.service
import gdata.spreadsheet
import os
import subprocess
import shlex
import sys
import argparse
from datetime import date
import cloud_sites_backup_config as config

def timestamp():
    from time import localtime, strftime
    return strftime("%Y-%m-%d %H:%M:%S", localtime())

parser = argparse.ArgumentParser(description='Make site backups with mysqldump and lftp')
parser.add_argument('--start-row', help='Number of the spreadsheet row to start at',
    nargs='?', default=0, type=int)

args = parser.parse_args()
start_row = args.start_row
    
spreadsheet_key = config.SPREADSHEET_KEY
worksheet_id = config.WORKSHEET_ID
conf_columns = ['dbexternalhost', 'dbuser', 'dbpw', 'dbname', 'ftpuser', 'ftppw', 'ftpip']
backup_folder_path = config.BACKUP_FOLDER_PATH
backup_base_path = backup_folder_path + ("/%s" % date.today().strftime('%A'))

print "{0} Starting spreadsheet connection.".format(timestamp())
gd_client = gdata.spreadsheet.service.SpreadsheetsService()
gd_client.email = config.GD_EMAIL
gd_client.password = config.GD_PASSWORD
gd_client.source = config.GD_SOURCE
gd_client.ProgrammaticLogin()
print "{0} Finished spreadsheet connection.".format(timestamp())

list_feed = gd_client.GetListFeed(spreadsheet_key, worksheet_id)

for i, row in enumerate(list_feed.entry):

    if i < start_row:
	if i == 0:
            print "Skipping rows before {0}".format(start_row)
        continue

    site = {}
    
    print "(row {0}) {1} Starting row".format(i, timestamp())

    for column in conf_columns:
        site[column] = row.custom[column].text
        
    site['backup_path'] = backup_base_path + os.sep + (site['ftpuser'] if site['ftpuser'] else  site['dbname'])
    
    if (not os.path.isdir(site['backup_path'])):
        print "(row {0}) {1} Making directory: {2}".format(i, timestamp(), site['backup_path'])
        os.makedirs(site['backup_path'])
    
    if (site['dbexternalhost'] and site['dbuser'] and site['dbpw'] and site['dbname']):
        print "(row {0}) {1} Running mysqldump for {2}...".format(i, timestamp(), site['dbuser'])
        cmd = 'mysqldump -u %(dbuser)s -p%(dbpw)s -h %(dbexternalhost)s %(dbname)s -r %(backup_path)s/%(dbname)s.sql' % site
        print cmd
        mysqldump_returncode = subprocess.call(shlex.split(cmd))
        if mysqldump_returncode != 0:
            sys.stderr.write("(row {0}) {1} mysqldump for {2} failed - check credentials\n".format(i, timestamp(), site['dbuser']))
    else:
        print "(row {0}) {1} No mysql creds supplied...skipping.".format(i, timestamp())
 
    if (site['ftpip'] and site['ftpuser'] and site['ftppw']):
        print "(row {0}) {1} Running ftp mirror for {2}...".format(i, timestamp(), site['ftpuser'])
        cmd = 'lftp -c "set mirror:parallel-directories true; set mirror:skip-noaccess true; set mirror:parallel-transfer-count 2; open sftp://%(ftpuser)s:%(ftppw)s@%(ftpip)s; mirror --delete / %(backup_path)s/site;"' % site
        print cmd
        lftp_returncode = subprocess.call(shlex.split(cmd))
        if lftp_returncode != 0:
            sys.stderr.write("(row {0}) {1} lftp for {2} failed - check credentials\n".format(i, timestamp(), site['ftpuser']))
    else:
        print "(row {0}) {1} No ftp creds supplied...skipping.".format(i, timestamp())

cmd = 'rsync -aq '+backup_base_path+'/ '+backup_folder_path+'/cumulative/'
print cmd
subprocess.call(shlex.split(cmd))

