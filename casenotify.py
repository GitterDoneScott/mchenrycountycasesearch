# -*- coding: utf-8 -*-

"""
Search McHenry County Public Records and Notify
~~~~~~~~~~~~~~~~~~~

Python script to notify a Discord server when certain information shows up in a McHenry County case search

"""

__title__ = 'mchenrycountycasenotifier'
__author__ = ''
__license__ = ''
__copyright__ = ''
__version__ = '0.1'

import sys
import time
import configparser
import requests
from requests_html import HTMLSession
import zc.lockfile
import schedule
from retrying import retry

discord_url = None
discord_message = None
lock = None


def config():
    print("Reading config file...")
    config_file = configparser.ConfigParser()
    config_file.read('config.ini')

    discord_config = {}
    try:
        discord_config = config_file['Discord']
    except:
        print('[Discord] section not found in config file. Please set values for [Discord] in config.ini')
        print('Take a look at config_example.ini for how config.ini should look.')
        sys.exit()

    global discord_url
    try:
        discord_url = discord_config['Url']
    except:
        print('Url not found in Discord section of config file. Please set Url under [Discord] in config.ini')
        print('This can be found by editing a Discord channel, selecting Webhooks, and creating a hook.')
        sys.exit()

    search_config = {}
    try:
        search_config = config_file['Search']
    except:
        print('[Search] section not found in config file. Please set values for [Search] in config.ini')
        print('Take a look at config_example.ini for how config.ini should look.')
        sys.exit()

    global search_terms
    try:
        search_terms = search_config['Terms']
    except:
        print('Terms not found in Search section of config file. Please set Terms under [Search] in config.ini')
        sys.exit()        

    global search_type
    try:
        search_type = search_config['searchtype']
    except:
        print('searchtype not found in Search section of config file. Please set Terms under [Search] in config.ini')
        sys.exit()        

    global search_exclude_list
    try:
        search_exclude_list = search_config['searchexcludelist'].split(',')
    except:
        print('searchexcludelist not found in Search section of config file. Please set Terms under [Search] in config.ini')
        sys.exit()        


def lock():
    try:
        print("Acquiring lock...")
        global lock
        lock = zc.lockfile.LockFile('lock.lock')
    except:
        print("Failed to acquire lock, terminating...")
        sys.exit()

def notify(message):
             discord_payload = {
                 "content": message,
#                 "embeds": [
#                     {
#                         "title: Results",
#                         "url": url_to_results
#                      }
#                 ]
             }
    
             status_code = 0
             while status_code != 204:
                 discord_request = requests.post(discord_url, json=discord_payload)
                 status_code = discord_request.status_code
    
                 if discord_request.status_code == 204:
                     print("Successfully called Discord API. Waiting 5 seconds...")
                     time.sleep(5)
                 else:
                     print("Failed to call Discord API. Waiting 5 seconds to retry...")
                     time.sleep(5)



@retry(wait_random_min=2000, wait_random_max=5000, stop_max_attempt_number=10)
def search():
    s = HTMLSession()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"}

    #accept terms and establish session
    url = "http://caseinfo.co.mchenry.il.us/pca/AcceptTermsServlet"
    r = s.post(url, headers=headers)
    #print(r.text)
    
    #create search and post
    data = {"party_name": search_terms, "SearchType": search_type}
    url = "http://caseinfo.co.mchenry.il.us/pca/PublicViewSearchServlet"
    r = s.post(url, data=data, headers=headers)
    #print(r.text)
    
    #find the results table via the embedded form
    results_table=r.html.find('form[action=GetCaseDataServlet]')
    
    #print(search_exclude_list)
    
    if results_table is not None:
        print("Results Found")
        for i in results_table:
            results_row_text = i.text
            #print(results_row_text, " ", i.attrs)
            #check for excluded terms
            if any(term in results_row_text for term in search_exclude_list):
                print("Result excluded")
            else:
                print("Result included")
                print(results_row_text)
                notify(results_row_text)
                #http://caseinfo.co.mchenry.il.us/pca/GetCaseDataServlet?case_number=18TR035183
                
def main():
    
    schedule.every(12).hours.do(search)
    
    while True:
        schedule.run_pending()
        time.sleep(10)

    
if __name__ == "__main__":
    config()
    lock()
    search()
    main()