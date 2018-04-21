import sys
from urllib.request import urlopen
from urllib.error import URLError
from argparse import ArgumentParser
from bs4 import BeautifulSoup
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import time

# Change User/Pass/Broker IP Below
MQBroker = "192.168.1.x"
MQPort = 1883
MQUser = "MYUSERNAME"
MQPass = "MYPASSWORD"
url = "http://192.168.100.1/cmconnectionstatus.html"
url2 = "http://192.168.100.1/cmswinfo.html"
table_results = []
# Do MQTT Publish - set to false for testing
dopublish = True
# Publish stats for all channels 
dopublishAllChan = False

mqttc = mqtt.Client("py_modemparse_pub")


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
    firstrow=True
    numlockchan_d=0
    numunlockchan_d=0
    down_snr_tot=0
    down_pwr_tot=0
    down_cor_tot=0
    down_uncor_tot=0
    numcorchan_d=0
    numuncorchan_d=0
    if dopublish : 
       mqttc.username_pw_set(MQUser, MQPass)
       mqttc.connect(MQBroker, MQPort)

    for row in rows:
        table_data = row.find_all('td')
        if table_data:
            n_rows+=1
            if n_rows > 1:
               dfreq = float(table_data[3].text.split(' ', 1)[0])
               dfreq = int(dfreq / 1000000)
               curpwr = float(table_data[4].text.split(' ', 1)[0])
               cursnr = float(table_data[5].text.split(' ', 1)[0])
               cur_cor = int(table_data[6].text)
               cur_uncor = int(table_data[7].text)
               if cur_cor > 0:
                   down_cor_tot += cur_cor
                   numcorchan_d += 1
               if cur_uncor > 0:
                   down_uncor_tot += cur_uncor
                   numuncorchan_d += 1
               if table_data[1].text == 'Locked':
                  numlockchan_d += 1
                  down_snr_tot += cursnr
                  down_pwr_tot += curpwr
                  if firstrow:
                     max_d_snr = cursnr
                     min_d_snr = cursnr
                     max_d_pwr = curpwr
                     min_d_pwr = curpwr
                     firstrow = False
                  else:
                     if max_d_snr < cursnr: max_d_snr = cursnr
                     if min_d_snr > cursnr: min_d_snr = cursnr
                     if max_d_pwr < cursnr: max_d_pwr = curpwr
                     if min_d_pwr > cursnr: min_d_pwr = curpwr
               else: numunlockchan_d += 1
               pub_topic = "docsis_d_chan"+str(n_rows-1)+"/stats"
               line = '{"id":"'+table_data[0].text+'","stat":"'+table_data[1].text+'","mod":"'+table_data[2].text+'","freq":"'+str(dfreq)+'","pwr":"'+str(curpwr)+'","snr":"'+str(cursnr)+'","cor":"'+table_data[6].text+'","uncor":"'+table_data[7].text            +'"}'
               if dopublish : 
                   if dopublishAllChan : 
                       mqttc.publish(pub_topic, line, 0, retain=True)
               if dopublishAllChan : 
                   print(line)
                   # issue with MQTT overloading - research QOS?
                   time.sleep(0.01)

################## DO UPSTREAM

    firstrow=True
    numlockchan_u=0
    numunlockchan_u=0
    up_pwr_tot=0

    # Get table
    try:
        table = soup.find_all('table')[2] # Grab the first table
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
               curpwr = float(table_data[6].text.split(' ', 1)[0])
               if table_data[2].text == 'Locked':
                  numlockchan_u += 1
                  up_pwr_tot += curpwr
                  if firstrow:
                     max_u_pwr = curpwr
                     min_u_pwr = curpwr
                     firstrow = False
                  else:
                     if max_u_pwr < cursnr: max_u_pwr = curpwr
                     if min_u_pwr > cursnr: min_u_pwr = curpwr
               else: numunlockchan_u += 1

               pub_topic = "docsis_u_chan"+str(n_rows-1)+"/stats"

               upfreq = float(table_data[4].text.split(' ', 1)[0])
               upfreq = upfreq / 1000000

               chanwide = float(table_data[5].text.split(' ', 1)[0])
               chanwide = chanwide / 1000000

               line = '{"chan":"'+table_data[0].text+'","id":"'+table_data[1].text+'","stat":"'+table_data[2].text+'","mod":"'+table_data[3].text+'","freq":"'+str(upfreq)+'","width":"'+str(chanwide)+'","pwr":"'+table_data[6].text.split(' ', 1)[0]+'"}'
               if dopublish : 
                  if dopublishAllChan : mqttc.publish(pub_topic, line, 0, retain=True)
               if dopublishAllChan : 
                  print(line)
                   # issue with MQTT overloading - research QOS?
                  time.sleep(0.01)


################## Do UpTime/FW Ver

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
                pub_topic = "docsis_fw/ver"
                line = table_data[1].text
                print(line)
                if dopublish : mqttc.publish(pub_topic, line, 0, retain=True)
                   # issue with MQTT overloading - research QOS?
                time.sleep(0.01)


    try:
        table = soup.find_all('table')[1] # Grab the first table
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
                pub_topic = "docsis_fw/uptime"
                # drop all the minutes and other nonsense
                linetemp = table_data[1].text.split(' ', 1)[1]
                line = table_data[1].text.split(' ', 1)[0] + ' ' + linetemp.split(':', 1)[0]
                print(line)
                if dopublish : mqttc.publish(pub_topic, line, 0, retain=True)
                time.sleep(0.01)

    print("Locked Down Chan: "+str(numlockchan_d))
    print("UnLocked Down Chan: "+str(numunlockchan_d))
    print("Max DownSNR: "+str(max_d_snr))
    print("Min DownSNR: "+str(min_d_snr))
    print("Max DownPWR: "+str(max_d_pwr))
    print("Min DownPWR: "+str(min_d_pwr))
    if numlockchan_d > 0:
        avg_down_snr = down_snr_tot / numlockchan_d
        avg_down_pwr = down_pwr_tot / numlockchan_d
    else: 
        avg_down_snr = 0
        avg_down_pwr = 0
    print("Avg DownSNR: "+str(round(avg_down_snr,1)))
    print("Avg DownPWR: "+str(round(avg_down_pwr,1)))
    print("Tot Cors: "+str(down_cor_tot))
    print("Tot Uncors: "+str(down_uncor_tot))
    print("Tot Chan w/ cors: "+str(numcorchan_d))
    print("Tot Chan w/ uncors: "+str(numuncorchan_d))

    print("Locked Up Chan: "+str(numlockchan_u))
    print("UnLocked Up Chan: "+str(numunlockchan_u))
    print("Max UpPWR: "+str(max_u_pwr))
    print("Min UpPWR: "+str(min_u_pwr))
    if numlockchan_u > 0:
        avg_up_pwr = up_pwr_tot / numlockchan_u
    else: 
        avg_up_pwr = 0
    print("Avg UpPWR: "+str(round(avg_up_pwr,1)))

    pub_topic = "docsis_d_chan/stats"
    line = '{"lockdch":"'+str(numlockchan_d)+'","unlockdch":"'+str(numunlockchan_d)+'","maxdsnr":"'+str(max_d_snr)+'","mindsnr":"'+str(min_d_snr)+'","avgdsnr":"'+str(round(avg_down_snr,1))+'","maxdpwr":"'+str(max_d_pwr)+'","mindpwr":"'+str(min_d_pwr)+'","avgdpwr":"'+str(round(avg_down_pwr,1))+'","totcor":"'+str(down_cor_tot)+'","totuncor":"'+str(down_uncor_tot)+'","corchan":"'+str(numcorchan_d)+'","uncorchan":"'+str(numuncorchan_d)+'"}'
    if dopublish : mqttc.publish(pub_topic, line, 0, retain=True)
    print(line)
    time.sleep(0.01)
    pub_topic = "docsis_u_chan/stats"
    line = '{"lockuch":"'+str(numlockchan_u)+'","unlockuch":"'+str(numunlockchan_u)+'","maxupwr":"'+str(max_u_pwr)+'","minupwr":"'+str(min_u_pwr)+'","avgupwr":"'+str(round(avg_up_pwr,1))+'"}'
    if dopublish : mqttc.publish(pub_topic, line, 0, retain=True)
    print(line)
# issue with MQTT overloading - research QOS?
    time.sleep(0.01)
    
    
    if dopublish : mqttc.disconnect()

if __name__ == '__main__':
    status = main()
    sys.exit(status)