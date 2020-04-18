
import os
import subprocess
import re
import shutil
import pymongo
import psutil
import socket
from datetime import datetime
import time

myclient = pymongo.MongoClient("mongodb+srv://testUser:<password>@cluster0-******.gcp.mongodb.net/HealthMonitor")
HealthMonitorDB = myclient["HealthMonitor"]
HMDataCollection = HealthMonitorDB["HMData"]
ServerStatusCollection = HealthMonitorDB["ServerStatus"]

def server_status():
    serverlistDistinct = HMDataCollection.distinct('server')
    oneminute = 1*60*1000   #miliseconds
    finalResult = {}
    finalResult['alive'] = {}
    finalResult['alive']['primary'] = []
    finalResult['alive']['secondary'] = []
    finalResult['notAlive'] = []
    for server in serverlistDistinct:
        uniqueserverRecords = HMDataCollection.find({"server":server}).sort([("date", -1)]).limit(1)    #getting last record in DB for given server
        for uniqueRecord in uniqueserverRecords:
            currenttime = time.time()*1000  #miliseconds
            if currenttime - uniqueRecord['date'] <= oneminute:
                print(uniqueRecord['server'])
                lastCollapseRecord = HMDataCollection.find({"server":uniqueRecord['server'], 'flaskserver': False}).sort([("date", -1)]).limit(1)
                tempAge = 0
                for lastRecord in lastCollapseRecord:
                    print("lastRecord", lastRecord)
                    print("age", uniqueRecord['date'] - lastRecord['date'])
                    age =  uniqueRecord['date'] - lastRecord['date']
                    if age > tempAge:
                        finalResult['alive']['primary'].append({"server" : lastRecord['server'], "age" : age})
                    else:
                        finalResult['alive']['secondary'].append({"server" : lastRecord['server'], "age" : age})
                    
            else:
                finalResult['notAlive'].append(uniqueRecord['server'])

    print(finalResult)
    x = ServerStatusCollection.insert_one(finalResult)
    print(x)

def is_up(name, port):
        up = False
        if name.startswith('ip'):
            for conn in psutil.net_connections():
                print(conn)
                #4200 for testing my angular app
                if conn.laddr.port == port:
                    up = True
                    break
        else:
            up = None
        return up

def get_statistics():

    # myclient = pymongo.MongoClient("mongodb+srv://testUser:<password>@cluster0-****.gcp.mongodb.net/HealthMonitor?retryWrites=true&w=majority")
    bashCommand = "dig +short myip.opendns.com @resolver1.opendns.com"
    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    server_name = socket.gethostname()
    print("server_name",server_name)
    doc = {
        'server': output.rstrip().decode('utf-8'),  #to strip the trailiing whitespace
        'date' : time.time()*1000, #to convert into miliseconds
        'cpu' : psutil.cpu_percent(interval=1),
        'disk_app' : psutil.disk_usage('/').free,
        'disk_root' : psutil.disk_usage('/').free,
        'memory' : psutil.virtual_memory().free,
        'flaskserver': is_up(server_name, 5001),
        'mongoserver': is_up(server_name, 27017)
    }
    x = HMDataCollection.insert_one(doc)
    server_status()


statistics = get_statistics()