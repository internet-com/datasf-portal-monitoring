# coding: utf-8
#!/usr/bin/env python

import requests
from Utils import *
from PostgresStuff import *
from ConfigUtils import *
from Emailer import *

def getMetadata(page, url):
    return requests.get(url, params={'page': page, 'limit': 1000}).json()


def parseDt(dt):
  dt = dt.replace("T", " ")
  dt = dt.split("+")
  dt = dt[0]
  return dt


def getDataFromWeb(configItems):
  results = []
  url = configItems['views_json_url']
  page = 1
  metadata = getMetadata(page, url)
  while len(metadata) > 0:
    results.extend(metadata)
    page += 1
    metadata = getMetadata(page, url)
    #print ()
    #print(metadata)
    #print ("********")
    #print (page)
    #print ()
  return results
  #  r = requests.get(configItems['views_json_url'])
  #  datasets = r.json()
  #  return datasets['results']

def getName(dataset):
  name = None
  #name = dataset["view"]['name']
  name = dataset['name']
  return name

def getCreatedAt(dataset, dt_format):
  created_at = None
  #created_at = DateUtils.convertEpochToStrTime( dataset["view"]['createdAt'], dt_format)
  created_at = parseDt(dataset['createdAt'])
  return created_at


def calculatePublishingHealth(dt_format, pub_freq, monitoring_time, last_updt):
  if ((monitoring_time == None) or (last_updt == None) or (pub_freq == None)): 
    return ["Unknown", "Unknown"]
  days_last_updt = DateUtils.daysBetween(last_updt, dt_format, monitoring_time, dt_format)
  pub_health = 'Unknown'
  health_thresholds = {
    'Streaming': [2,4],
    'Daily' : [2,4],
    'Weekly': [7,21],
    'Monthly': [32, 90],
    'Bi-annually': [60, 180],
    'Annually': [365,500],
    'Quarterly': [90, 270]
  }
  if pub_freq in health_thresholds.keys():
    time_intervals = health_thresholds[pub_freq]
    if int(days_last_updt <= time_intervals[0]):
      pub_health = 'On Time'
    elif ((int(days_last_updt) > time_intervals[0]) and (int(days_last_updt) <= time_intervals[1])):
      pub_health = 'Delayed'
    elif (int(days_last_updt) > time_intervals[1]):
      pub_health = 'Stale'
  elif not (pub_health is None):
    pub_health = 'On Time'
  return [pub_health, str(days_last_updt) ]

def getRowsUpdatedAt(dataset,  dt_format):
  rows_updated = None
  if 'dataUpdatedAt' in dataset.keys():
    if not(dataset['dataUpdatedAt'] is None):
      rows_updated = parseDt(dataset['dataUpdatedAt'])
  #if 'rowsUpdatedAt' in dataset["view"].keys():
  #  rows_updated =  DateUtils.convertEpochToStrTime( dataset["view"]['rowsUpdatedAt'], dt_format)
  return rows_updated

def getPubDept(dataset):
  pub_dept = None
  #pub_dept =  dataset['view']["metadata"]["custom_fields"]["Department Metrics"]["Publishing Department"]
  if not(dataset['customFields'] is None):
    if "Department Metrics" in dataset["customFields"].keys():
      if "Publishing Department" in dataset["customFields"]["Department Metrics"].keys():
        pub_dept =  dataset["customFields"]["Department Metrics"]["Publishing Department"]
  return pub_dept

def getPublishingDetails(dataset):
  pub_freq = None
  #if 'Publishing Details' in dataset['view']["metadata"]["custom_fields"].keys():
  if not (dataset['customFields'] is None):
    if 'Publishing Details' in dataset["customFields"].keys():
      if "Publishing frequency" in dataset["customFields"]["Publishing Details"].keys():
        #if "Publishing frequency" in dataset['view']["metadata"]["custom_fields"]["Publishing Details"].keys():
        #pub_freq =  dataset['view']["metadata"]["custom_fields"]["Publishing Details"]["Publishing frequency"]
        pub_freq =  dataset["customFields"]["Publishing Details"]["Publishing frequency"]
  return pub_freq

def parseResults(conn, datasets_tbl, dataset):
  dt_format=  '%Y-%m-%d %H:%M:%S'
  fields = []
  monitoring_time = DateUtils.getCurrentTimestampAnyFormat(dt_format)
  fields.append(monitoring_time)
  #fields.append(dataset["view"]['id'])
  fields.append(dataset['id'])
  fields.append(getName(dataset))
  fields.append(getCreatedAt(dataset, dt_format))
  last_updt = getRowsUpdatedAt(dataset, dt_format)
  fields.append(last_updt)
  pub_freq = None
  pub_dept = None
  if 'customFields' in dataset.keys():
  #if 'custom_fields' in dataset['view']["metadata"].keys():
    pub_dept = getPubDept(dataset)
    pub_freq = getPublishingDetails(dataset)
  fields.append(pub_dept)
  fields.append(pub_freq)
  pub_health  = calculatePublishingHealth(dt_format, pub_freq, monitoring_time, last_updt)
  days_last_updt = pub_health[1]
  fields.append(pub_health[0])
  fields.append(days_last_updt)
  #fields = [ "'" + str(field.encode('utf-8') ).replace('\'', '') + "'"  if not (field is None) else field for field in fields ]
  fields = [ "'" + str(field).replace('\'', '') + "'"  if not (field is None) else field for field in fields ]
  fields  = [ 'NULL' if (field is None) else field for field in fields ]
  fields[0] = "NOW() AT TIME ZONE 'UTC' "
  #print (fields)
  fields = [str(field) for field in fields  ]
  return fields

def dumpDatasetRecords(conn, datasets_tbl, fields):
  headers = ["time", "datasetid", "name", "created_at", "updated_at",  "pub_dept", "pub_freq", "pub_health", 'days_last_updt']
  row_inserted =  PostgresStuff.insertRecord(conn, datasets_tbl, headers, fields)
  return row_inserted

def sendEmailNotification(configItems, total_inserted_rows):
   em =  Emailer(configItems)
   subject_line =  "Updated the Data Portal Activity Log at " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
   msg_body = subject_line +  "</br></br></br> Inserted " + str(total_inserted_rows) + " Rows"
   em.sendEmails( subject_line, msg_body)

def main():
  curr_full_path = FileUtils.getCurrentDirFullPath()
  config_fn = 'portal_activity_job_config.yaml'
  cI =  ConfigUtils(curr_full_path+ "/configs/" ,config_fn)
  configItems = cI.getConfigs()
  configItems['config_dir'] = curr_full_path+ "/configs/"
  db_ini = configItems['config_dir'] + configItems['database_config']
  total_inserted_rows = 0
  conn_alq, meta_alq =PostgresStuff.connect_alq(db_ini)
  conn = PostgresStuff.connect(db_ini)
  db_tbl = configItems['activity_table']
  datasets = getDataFromWeb(configItems)
  print (len(datasets))
  for dataset in datasets:
    fields = parseResults(conn, db_tbl, dataset)
    inserted_rows = dumpDatasetRecords(conn, db_tbl, fields)
    if inserted_rows != 0:
      try:
        total_inserted_rows += inserted_rows
      except Exception as e:
        print ("ERROR: there was an error- did not load row")
        print (str(e))
  print (total_inserted_rows)
  sendEmailNotification(configItems, total_inserted_rows)



if __name__ == "__main__":
    main()
