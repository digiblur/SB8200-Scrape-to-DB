import sys
from urllib.request import urlopen
from urllib.error import URLError
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from influxdb import InfluxDBClient

# Change settings below to your influxdb - database needs to be created or existing db
# creates 4 tables - downlink, uplink, fw_ver, uptime

influxip = "192.168.x.x"
influxport = 8086
influxdb = "cablemodem"
influxid = "root"
influxpass = "root"

# SB8200 URLs - leave these as is unless a firmware upgrade changes them

url = "http://192.168.100.1/cmconnectionstatus.html"
url2 = "http://192.168.100.1/cmswinfo.html"

table_results = []

def main():
    # Make soup
    try:
        resp = urlopen(url)
    except URLError as e:
        print ('An error occured fetching %s \n %s' % (url, e.reason))   
        return 1
    soup = BeautifulSoup(resp.read(),"lxml")

    # Get table
    try:
        table = soup.find_all('table')[1] # Grab the first table
#        table = soup.find('table')
    except AttributeError as e:
        print ('No tables found, exiting')
        return 1

    # Get rows
    try:
        rows = table.find_all('tr')
    except AttributeError as e:
        print ('No table rows found, exiting')
        return 1

    # Get data
    n_rows=0
    client = InfluxDBClient(influxip, influxport, influxid, influxpass, influxdb)

    for row in rows:
        
        table_data = row.find_all('td')
        if table_data:
            n_rows+=1
            if n_rows > 1:

               dfreq = float(table_data[3].text.split(' ', 1)[0])
               dfreq = int(dfreq / 1000000)
           
               json_body = [
                   {
                       "measurement": "downlink",
                       "tags": {
                           "host": "sb8200",
                           "syncnum": n_rows-1,
                           "chanid": table_data[0].text,
                           "freq": dfreq
                       },
                       "fields": {
                           "stat": table_data[1].text,
                           "mod": table_data[2].text,
                           "pwr": float(table_data[4].text.split(' ', 1)[0]),
                           "snr": float(table_data[5].text.split(' ', 1)[0]),
                           "cor": int(table_data[6].text),
                           "uncor": int(table_data[7].text),
                        }
                    }
               ]
               print(json_body)
               client.write_points(json_body)

################## DO UPSTREAM

    # Get table
    try:
        table = soup.find_all('table')[2] # Grab the first table
#        table = soup.find('table')
    except AttributeError as e:
        print ('No tables found, exiting')
        return 1

    # Get rows
    try:
        rows = table.find_all('tr')
    except AttributeError as e:
        print ('No table rows found, exiting')
        return 1

    # Get data
    n_rows=0

    for row in rows:
        table_data = row.find_all('td')
        if table_data:
            n_rows+=1
            if n_rows > 1:

               upfreq = float(table_data[4].text.split(' ', 1)[0])
               upfreq = upfreq / 1000000

               chanwide = float(table_data[5].text.split(' ', 1)[0])
               chanwide = chanwide / 1000000

               json_body = [
                   {
                       "measurement": "uplink",
                       "tags": {
                           "host": "sb8200",
                           "syncnum": table_data[0].text,
                           "chanid": table_data[1].text,
                           "freq": upfreq
                       },
                       "fields": {
                           "stat": table_data[2].text,
                           "mod": table_data[3].text,
                           "width": float(chanwide),
                           "pwr": float(table_data[6].text.split(' ', 1)[0])
                        }
                    }
               ]
               print(json_body)
               client.write_points(json_body)

    try:
        resp = urlopen(url2)
    except URLError as e:
        print ('An error occured fetching %s \n %s' % (url2, e.reason))   
        return 1
    soup = BeautifulSoup(resp.read(),"lxml")

    # Get table
    try:
        table = soup.find_all('table')[0] # Grab the first table
    except AttributeError as e:
        print ('No tables found, exiting')
        return 1

    # Get rows
    try:
        rows = table.find_all('tr')
    except AttributeError as e:
        print ('No table rows found, exiting')
        return 1

    # Get data
    n_rows=0

    for row in rows:
        table_data = row.find_all('td')
        if table_data:
            n_rows+=1
            if n_rows == 3:

                json_body = [
                    {
                        "measurement": "fw_ver",
                        "tags": {
                            "host": "sb8200"
                        },
                        "fields": {
                            "firmware": table_data[1].text,
                         }
                     }
                ]
                print(json_body)
                client.write_points(json_body)

    try:
        table = soup.find_all('table')[1] # Grab the first table
#        table = soup.find('table')
    except AttributeError as e:
        print ('No tables found, exiting')
        return 1

    # Get rows
    try:
        rows = table.find_all('tr')
    except AttributeError as e:
        print ('No table rows found, exiting')
        return 1

    # Get data
    n_rows=0

    for row in rows:
        table_data = row.find_all('td')
        if table_data:
            n_rows+=1
            if n_rows == 1:
                # drop all the minutes and other nonsense
                linetemp = table_data[1].text.split(' ', 1)[1]
                line = table_data[1].text.split(' ', 1)[0] + ' ' + linetemp.split(':', 1)[0] 
                print(line)

                json_body = [
                    {
                        "measurement": "uptime",
                        "tags": {
                            "host": "sb8200"
                        },
                        "fields": {
                            "uptime_d_h": line,
                            "uptime_full": table_data[1].text,
                         }
                     }
                ]
                client.write_points(json_body)





if __name__ == '__main__':
    status = main()
    sys.exit(status)