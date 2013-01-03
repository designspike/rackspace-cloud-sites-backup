import gdata.spreadsheet.service
import gdata.service
import gdata.spreadsheet
import os
import subprocess
import shlex
from datetime import date
import cloud_sites_backup_config as config

def timestamp():
    from time import localtime, strftime
    return strftime("%Y-%m-%d %H:%M:%S", localtime())

spreadsheet_key = config.SPREADSHEET_KEY
worksheet_id = config.WORKSHEET_ID
conf_columns = ['dbexternalhost', 'dbuser', 'dbpw', 'dbname', 'ftpuser', 'ftppw', 'ftpip']
backup_folder_path = config.BACKUP_FOLDER_PATH
backup_base_path = backup_folder_path + ("/%s" % date.today().strftime('%A'))

gd_client = gdata.spreadsheet.service.SpreadsheetsService()
gd_client.email = config.GD_EMAIL
gd_client.password = config.GD_PASSWORD
gd_client.source = config.GD_SOURCE
gd_client.ProgrammaticLogin()

list_feed = gd_client.GetListFeed(spreadsheet_key, worksheet_id)

for i, row in enumerate(list_feed.entry):
    site = {}
    
    for column in conf_columns:
        site[column] = row.custom[column].text
        
    if (not site['ftpuser']):
        print timestamp(), "No ftp user for row ", i, "...skipping."
        continue
    
    
    site['backup_path'] = backup_base_path + os.sep + site['ftpuser']
    
    if (not os.path.isdir(site['backup_path'])):
        print timestamp(), "Making directory:", site['backup_path']
        os.makedirs(site['backup_path'])
    
    if (site['dbexternalhost'] and site['dbuser'] and site['dbpw'] and site['dbname']):
        print timestamp(), "Running mysqldump for %s..." % site['ftpuser']
        cmd = 'mysqldump -u %(dbuser)s -p%(dbpw)s -h %(dbexternalhost)s %(dbname)s -r %(backup_path)s/%(dbname)s.sql' % site
        print cmd
        subprocess.call(shlex.split(cmd))

	print timestamp(), "Skipping mysql for", site['ftpuser']
 
    if (site['ftpip'] and site['ftpuser'] and site['ftppw']):
        print timestamp(), "Running ftp mirror for %s..." % site['ftpuser']
        cmd = 'lftp -c "set mirror:parallel-directories true; set mirror:skip-noaccess true; set mirror:parallel-transfer-count 2; open sftp://%(ftpuser)s:%(ftppw)s@%(ftpip)s; mirror --delete / %(backup_path)s/site;"' % site
        print cmd
        subprocess.call(shlex.split(cmd))

cmd = 'rsync -aq '+backup_base_path+'/ '+backup_folder_path+'/cumulative/'
print cmd
subprocess.call(shlex.split(cmd))

