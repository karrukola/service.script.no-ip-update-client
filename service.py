"""
Main module of Kodi (XBMC) service addon to update your No-IP dynamic DNS entry

This module is executed at login and periodically sends an update signal.
The periodicity can be set by the user amongst 12, 24 or 48 hours.
Host, username and password are read from user's configuration.

This module uses abortRequested() and waitForAbort() that are new in Helix.
As such it does not work with older releases (Gotham...)
"""

# from http://kodi.wiki/view/Service_addons
# import time
import xbmc
import xbmcaddon
import xbmcgui
import base64
import urllib2


__addon__ = xbmcaddon.Addon()
__language__ = __addon__.getLocalizedString
addonName = __addon__.getAddonInfo('name')
addonVer = __addon__.getAddonInfo('version')
# User Agent and Update URL as defined on http://www.noip.com/integrate
UA = 'Kodi '+addonName+'/'+addonVer+' filippo.carra@gmail.com'

# If period == 0 there is an error in the configuration
period = -1


def doUpdate(myreq):
    """
    Function that calls the No-IP update API and reads out the response.
    """
    try:
        resp = urllib2.urlopen(myreq)
        content = resp.read()
        xbmc.log('Calling  update API', level=xbmc.LOGDEBUG);
    #urllib2 errors are a subclass of IOError
    except IOError as e_urllib2:
        xbmcgui.Dialog().ok(addonName,
            __language__(32030),
            __language__(32034),
            str(e_urllib2.reason))
        content = ''
        xbmc.log('Connection error: '+str(e_urllib2.reason),
            level=xbmc.LOGERROR);
    return content

def parseResponse(response):
    """
    Function parses the response from No-IP's update API.
    Returns the status (error yes/no) and its reason.
    """
    if response[0:4] == 'good':
        error = 0
        reason = 'DNS hostname update successful.'
    elif response[0:5] == 'nochg':
        error = 0
        reason = 'IP address is current, no update performed.'
    elif response == 'nohost':
        error = 1
        reason = 'Hostname supplied does not exist under specified account.'
    elif response == 'badauth':
        error = 1
        reason = 'Invalid username password combination'
    elif response == 'badagent':
        error = 1
        reason = 'Client disabled.'
    elif response == '!donator':
        error = 1
        reason = 'An update request was sent including a feature that is not available to that particular user such as offline options.'
    elif response == 'abuse':
        error = 1
        reason = 'Username is blocked due to abuse. Either for not following our update specifications or disabled due to violation of the No-IP terms of service.'
    elif response == '911':
        error = 1
        reason = 'A fatal error on No-IP side such as a database outage. Retry the update no sooner than 30 minutes.'
    else:
        error = 1
        reason = ''

    xbmc.log("error: "+str(error), level=xbmc.LOGDEBUG)
    if error:
        xbmc.log("response: "+str(response), level=xbmc.LOGERROR)
    else:
        xbmc.log("response: "+str(response), level=xbmc.LOGDEBUG)
    xbmc.log("reason:"+reason, level=xbmc.LOGDEBUG)

    return error, reason


def readSettings(__addon__, UA):
    """
    Read out the settings listed below.
    Requires User Agent string because it tests the connectivity details

    Settings being read out:
    - Time interval between two consecutive updates, expressed in seconds.
    - Host name, managed by No-IP.
    - Username and password to log on No-IP.
    """

    interval =  __addon__.getSetting( 'interval' )
    xbmc.log("Interval: "+interval, level=xbmc.LOGDEBUG)
    period = int( interval ) * 3600
    myhst = __addon__.getSetting( 'host' )
    xbmc.log("Host: "+myhst, level=xbmc.LOGDEBUG)

    # TODO!!! Not logging someone's username and password
    myusr = __addon__.getSetting( 'username' )
    # xbmc.log("usr: "+myusr, level=xbmc.LOGDEBUG)
    mypwd = __addon__.getSetting( 'password' )
    # xbmc.log("pwd: "+mypwd, level=xbmc.LOGDEBUG)

    if myhst != '' and myusr != '' and mypwd != '':
        # Avoid including usename and password in the request, use https auth.
        myupdurl = 'https://dynupdate.no-ip.com/nic/update?hostname='+myhst
        myreq = urllib2.Request(myupdurl)
        myreq.add_header( 'Authorization',
            'Basic ' +base64.encodestring(myusr+":"+mypwd).replace("\n",
                "") )
        # Add user agent
        myreq.add_header('User-Agent', UA)
        resp = doUpdate(myreq)
        error, reason = parseResponse(resp)
        if error:
            period = 0
            xbmcgui.Dialog().ok(addonName,
            __language__(32030),
            reason,
            __language__(32033)
            )
    else:
        period = -1
        myreq = ''

    return period, myreq


if __name__ == '__main__':
    while period <= 0:
        period, myreq = readSettings(__addon__, UA)
        xbmc.log("period: "+str(period), level=xbmc.LOGDEBUG)
        if period == -1:
            xbmcgui.Dialog().ok(addonName,
                __language__(32031),
                __language__(32032),
                __language__(32033)
                )
        if period <= 0:
            __addon__.openSettings()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():

        # Sleep/wait for abort for _period_ seconds
        if monitor.waitForAbort(period):
            # Abort was requested while waiting. We should exit
            break
        # xbmc.log("hello addon! %s" % time.time(), level=xbmc.LOGDEBUG)
        # No abort signal, thus update the IP address. Skeleton taken from
        # http://blog.hostonnet.com/python-script-to-update-noip-com
        # but here we do not read out our IP address; according to No-IP:
        # [...] If no IP address is supplied the WAN address connecting to our system will be used. Clients behind NAT, for example, would not need to supply an IP address.

        resp = doUpdate(myreq)
        error = parseResponse(resp)

        if __addon__.getSetting("shownotif") == "true":
            if error == 0:
                notif_ico = xbmcgui.NOTIFICATION_INFO
            else:
                notif_ico = xbmcgui.NOTIFICATION_ERROR
            xbmcgui.Dialog().notification(addonName,
                resp,
                notif_ico
                )
