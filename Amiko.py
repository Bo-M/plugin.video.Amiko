
import urlparse
import sys,urllib
import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import os, json
import requests
import binascii
import time
import socket
import thread
import random
import re
from urlparse import urlparse as parse

import urlparse as parse
from urllib import urlencode

"""
## for python3
#from urllib import parse
#from parse import urlencode

"""
addon = xbmcaddon.Addon('plugin.video.Amiko')
ip = addon.getSetting('IP')#"192.168.3.111"  # IP address of your Amiko
ListServer = 'http://{}/lis'.format(addon.getSetting('listServer')) #za localhost ide: 127.0.0.1:6200
adr = "rtsp://{}".format(ip)  # username, passwd, etc.
clientports = [60784, 60785]  # the client ports we are going to use for receiving video
session = ''

addon_dir = xbmc.translatePath(addon.getAddonInfo('path'))
sys.path.append(os.path.join(addon_dir, 'resources', 'lib'))
m3uPath = os.path.join(addon_dir , "resources" , "m3u8" )
from bottle import route, run, redirect, request, HTTPResponse, Response


base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

dictinaryOfsatellites = {'ASTRA_19_2E': '8',
                         'Hot_Bird_13E': '6',
                         'Eutelsat_16A_16E': '7',
                         'ASTRA_3B_23_5E': '10',
                         'Astra_4A_4_8E':'52',
                         'Eutelsat_7E':'4',
                         'Eurobird_9E': '51',
                         'Eutelsat W2A 10E': '5'
                         }
                         
                         
                         
def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z
    
def getFeedChannel():
    ''' Get channel list from Amiko receiver and find last channel by freq (if 'freq=610000' in urlencode(i)) before DVB-T2
    and return list of [channel name, url], both string
    '''
    url = 'http://{}:8080/cfg/get_channel_list.cgi'.format(ip)

    data = requests.get(url).text
    
    D = {}
    channels = []
    channelsUrls = []
    
    for i in data.split('\n'):
        if i != '':
            currentDict = dict(parse.parse_qsl(i))
            if 'tpfreq' in list(currentDict.keys()):
                D[currentDict['tponid'].strip()] = currentDict
            elif 'svrnam' in list(currentDict.keys()):
                
                #d = {**D[currentDict['tponid']], **currentDict} #for python 3 this can be used instead of below line
                d = merge_two_dicts(D[currentDict['tponid']], currentDict)
                if d['tppola'] == '0':
                    d['pol'] = 'h'
                elif d['tppola'] == '1':
                    d['pol'] = 'v'
                channels.append(d)
    
    for i in channels:
        tempDict = {}
        try:
            tempDict['freq'] = i['tpfreq']
            tempDict['pol'] = i['pol']
            try:
                tempDict['mtype'] = i['tpmodu']
            except:
                tempDict['mtype'] = '8psk'
            tempDict['sr'] = i['tpsymb']
            APID = i['audpid'].split(',')[0]
            VPID = i['vidpid']
            PMT = i['pmtpid']
            tempDict['name'] = i['svrnam']
            tempDict['pids'] = ['0', '17', '18', VPID, APID, PMT]
            channelsUrls.append(tempDict)
        except:
            pass
    s = ''
    feedUrl = ''
    for i in channelsUrls:
        tempPids = ','.join(i['pids'])
        name = i['name']
        del i['pids']
        del i['name']
        if 'freq=610000' in urlencode(i):
            return [feedname, feedUrl]
        else:
            feedname = name
            feedUrl = urlencode(i) + '&pids=' + tempPids
            
def makeFeedList():
    """ Make m3u list with different satid inside, without satid stream wont work
    """
    feedFile = '#EXTM3U\n'
    channelname, url = getFeedChannel()
    for satellite in dictinaryOfsatellites:
        satid = dictinaryOfsatellites[satellite]
        feedUrl = 'rtsp://sat.ip/?alisatid={}&{}'.format(satid, url)
        cname = '{} - {}'.format(channelname, satellite)
        feedFile+= '#EXTINF:0,' + cname + '\n' + feedUrl + '\n'
    with open(os.path.join(m3uPath, 'feed.m3u'), 'w') as f:
        f.write(feedFile)


def getPorts(searchst, st):
  """ Searching port numbers from rtsp strings using regular expressions
  """
  pat = re.compile(searchst + "=\d*-\d*")
  pat2 = re.compile('\d+')
  mstring = pat.findall(st)[0]  # matched string .. "client_port=1000-1001"
  nums = pat2.findall(mstring)
  numas = []
  for num in nums:
    numas.append(int(num))
  return numas


def printrec(recst):
  """ Pretty-printing rtsp strings
  """
  recst = recst.decode()
  recs = recst.split('\r\n')
  for rec in recs:
    print (rec)


def sessionid(recst):
  """ Search session id from rtsp strings
  """
  recst = recst.decode()
  recs = recst.split('\r\n')
  for rec in recs:
    ss = rec.split()
    # print ">",ss
    if (ss[0].strip() == "Session:"):
        return ss[1].strip()


def streamid(recst):
  """ Search stream id from rtsp strings
  """
  recst = recst.decode()
  recs = recst.split('\r\n')
  for rec in recs:
    ss = rec.split()
    try:
        if (ss[0].strip() == "com.ses.streamID:"):
            return ss[1].strip()
    except:
        pass


def setsesid(recst, idn):
  """ Sets session id in an rtsp string
  """
  return recst


@route('/m3u')
def m3u():
	currentList = request.query.name
	print 'uytrg',currentList
	with open(os.path.join(m3uPath, currentList), 'r') as f:
		masterList = f.read()
	
	
	return masterList
  
@route('/lis')
def lis():
	global session
	channelurl = request.query_string
	print 'uytrggthj',channelurl
	randomPort = random.randint(11000,20000)
	
	setu = "SETUP " + adr + ":554/?" + channelurl + " RTSP/1.0\r\nCSeq: 0\r\nUser-Agent: RTSPClientLib/Java\r\nTransport: RTP/AVP;unicast;client_port={port1}-{port2}\r\n\r\n"
	setu = setu.format(port1 = randomPort, port2 = randomPort + 1)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((ip, 554))  # RTSP should peek out from port 554

	
	print
	print ("*** SENDING SETUP ***")
	print
	s.send(setu.encode())
	recst = s.recv(4096)
	print
	print ("*** GOT ****")
	print
	printrec(recst)
	idn = sessionid(recst)
	session = idn
	streamID = streamid(recst)
	print(idn)
	recst = recst.decode()
	serverports = getPorts("server_port", recst)
	clientports = getPorts("client_port", recst)
	print
	print ("*** SENDING PLAY ***")
	print
	play = "PLAY " + adr + ":554/stream=3 RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: RTSPClientLib/Java\r\nSession: {Session}\r\n\r\n"
	play = setsesid(play, idn)
	play = play.format(Session=idn).encode()

	s.send(play)
	recst = s.recv(4096)
	print
	print ("*** GOT ****")
	print
	printrec(recst)
	responsestring = '''rtp://127.0.0.1:{rtpport}'''
	return HTTPResponse(status=200, body=responsestring.format(rtpport = clientports[0]))
	
def runserver():
	run(host='localhost', port=6200, debug=True)
	print('server started')



def build_url(query):
    return base_url + '?' + urllib.urlencode(query)


def build_url1(id):
	'''
	you can put here to select quality, if you know
	'''
	url = id
	r = requests.get(url)
	data = r.text
	return data.strip()

def play_video(path):

	play_item = xbmcgui.ListItem(path=path)
	vid_url = play_item.getfilename()
	stream_url = build_url1(vid_url)
	print 'poytrgjf', stream_url
	if stream_url:
		play_item.setPath(stream_url)
    # Pass the item to the Kodi player.
	xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

def sendOptions():
	print 'gfdsgier'

	counter = 1
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((ip, 554))  # RTSP should peek out from port 554
	Finished = False
	while True:
		if Finished == True:
			break
		time.sleep(10)
		if session != '':
			counter += 1
			req = 'OPTIONS * RTSP/1.0\r\nCSeq: {}\r\nSession: {}\r\nUser-Agent: RTSPClientLib/Java\r\n\r\n'
			r = req.format(counter, session)
			try:
				s.send(r.encode())
				recst = s.recv(4096)
				print(recst)
			except Exception as e:
				print 'cannot socket', str(e)
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.connect((ip, 554))
		print 'kklikioiop', session
		print xbmc.getCondVisibility('Player.HasVideo')
		if xbmc.getCondVisibility('Player.HasVideo') == False  and counter > 3:
			try:
				teardown = "TEARDOWN " + adr + "/stream=3 RTSP/1.0\r\nCSeq: 1\r\nSession: {}\r\nUser-Agent: RTSPClientLib/Java\r\n\r\n"
				s.send(teardown.format(session).encode())
				print(s.recv(4096))
			except:
				pass
			counter = 0


def my_inline_function():
	thread.start_new_thread(sendOptions, ())




mode = args.get('mode', None)

def addDir(name, video_play_url, mode=None,  plot = ''):
		url = build_url({'mode': mode, 'playlink': video_play_url})
		li = xbmcgui.ListItem(name, iconImage= 'DefaultVideo.png')
		li.setInfo("video", {"Plot" : plot})
		xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
	                                listitem=li, isFolder=True)	
									
def add_ch(name,video_play_url, mode):

	url = build_url({'mode' :mode, 'playlink' : video_play_url})
	li = xbmcgui.ListItem(name, iconImage='DefaultVideo.png')
	li.setProperty('IsPlayable' , 'true')
	li.setInfo('video',' ')
	xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)

def parsem3ulist(m3u):
	channelList = []
	channelName = ''
	for line in m3u.split('\n'):
		if '#EXTINF' in line:
			channelName = line.split(',')
			del channelName[0]
			channelName = ','.join(channelName)
		elif '//' in line:
			url = line
			channelList.append([channelName,url])
	return channelList
			
		
if mode is None:
	makeFeedList()
	thread.start_new_thread(runserver, ())
	my_inline_function()
	url = 'http://127.0.0.1:6200/m3u?name=MasterList.m3u'
	r = requests.get(url)
	data = r.text
	listchannel = parsem3ulist(data)
	#print data
	for i in listchannel:
		ch_name = i[0]
		url = i[1]
		addDir(ch_name, url, 'masterlist')

	xbmcplugin.endOfDirectory(addon_handle)

elif mode[0] == 'masterlist':
	url = args['playlink'][0]
	print 'uytro', url
	r = requests.get(url)
	data = r.text
	listchannel = parsem3ulist(data)
	#print data
	for i in listchannel:
		ch_name = i[0]
		url = i[1].replace('rtsp://sat.ip/',ListServer)
		add_ch(ch_name, url, 'finallist')
		try: pass# print ch_name.encode(), url
		except: pass
	xbmcplugin.endOfDirectory(addon_handle)
elif mode[0] == 'finallist':
	url = args['playlink'][0]
	play_video(url)