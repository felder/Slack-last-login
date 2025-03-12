#!/usr/bin/env python3
import csv
import json
import sys
import requests

from time import sleep
from datetime import datetime, timedelta
from tqdm import trange
from api_token import token


def write_dicts_to_csv(filename, dictionaries):
  if not dictionaries:
    raise ValueError('Dictionary is empty!')

  field_names = dictionaries[0].keys()
  with open(filename, 'w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=field_names, quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
 
    for dictionary in dictionaries:
      writer.writerow(dictionary)


def format_members(members):
  members_for_csv = [];
  
  for member in members:
    last_login_epoch = members[member]['last_login']
    if last_login_epoch == 0:
      last_login_date = "No logins found!"
    else:
      last_login_date = datetime.fromtimestamp(last_login_epoch).isoformat()
      
    members_for_csv.append({
      'id': members[member]['id'],
      'name': members[member]['name'],
      'display_name': members[member]['profile']['display_name'],
      'real_name': members[member]['profile']['real_name'],  
      'title': members[member]['profile']['title'], 
      'email': members[member]['profile']['email'],  
      'last_login': last_login_date
    })
    
  return members_for_csv


def get_last_logins(members, earliest_epoch):
  url = 'https://slack.com/api/team.accessLogs'
  headers = {"Authorization": f"Bearer {token}"}
  params = {'count': 1000}  # 1000 logs per page is maximum
  
  # oldest log entry
  # params['before'] = 1444070161
  
  current_date = datetime.today();
  current_epoch = int(current_date.timestamp())
  
  while True:
    print("  Retrieving logs starting from", datetime.fromtimestamp(current_epoch).strftime('%c'), file=sys.stderr)
    params['before'] = current_epoch
    
    for page in trange(1, 101):  # 100 pages is maximum
      params['page'] = page
      res = requests.get(url, headers=headers, params=params)
      res_data = res.json()

      if not res_data['ok']:
       raise ValueError('Something went wrong.', res.url, res_data['error'])
      elif not res_data['logins']:
       return members
    
      for log in res_data['logins']:
        current_epoch = log['date_first']
        if current_epoch < earliest_epoch:
          return members
        elif log['user_id'] in members and members[log['user_id']]['last_login'] < log['date_last']:
          members[log['user_id']]['last_login'] = log['date_last']
          
      sleep(3)  # Limit for Tier 2 is 20 req/min  


def get_all_members():
  url = 'https://slack.com/api/users.list'
  headers = {"Authorization": f"Bearer {token}"}
  #params = {'limit': 10}

  res = requests.get(url, headers=headers)
  res_data = res.json()

  if not res_data['ok']:
    raise ValueError('Something went wrong.', res.url, res_data['error'])
    
  for member in list(res_data['members']):
    if member['deleted'] or member['is_bot'] or member['id'] == "USLACKBOT":
      res_data['members'].remove(member)
    else:
      x = res_data['members'].index(member)
      res_data['members'][x]['last_login'] = 0
  
  members = {x['id']: x for x in res_data['members']}
  return members


def main():
  earliest_date = datetime.today() - timedelta(days=180)
  earliest_epoch = int(earliest_date.timestamp())
  
  #with open("members_new.txt", 'r') as file:
  #  members = json.load(file)
  #file.close()
  #print(json.dumps(members, indent=4, sort_keys=True))
  
  print("Downloading active non bot slack members …", file=sys.stderr)
  members = get_all_members()
  print(" ", len(members), "member(s) retrieved!", file=sys.stderr)
  
  print("Downloading access logs from now until", earliest_date, '…', file=sys.stderr)
  members = get_last_logins(members, earliest_epoch)
  
  print("Writing last login info to CSV …", file=sys.stderr)
  formatted_members = format_members(members)
  write_dicts_to_csv('last_logins.csv', formatted_members)
  
  print("  Done!", file=sys.stderr)


if __name__ == '__main__':
  main()