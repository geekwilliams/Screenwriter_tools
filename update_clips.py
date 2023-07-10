#! /usr/bin/env python
#################################################################################
# Description:                                                                  #
#     Update a set of clips in all show playlists on a Screenwriter LMS at once #
#                                                                               #
# Usage:                                                                        #
#     update.py [old-cpl-uuid] [new-cpl-uuid]                                   #
#                                                                               #
#################################################################################

import sys
import time
import json
import argparse
import requests

__author__ = "Caleb Williams"
__copyright__ = "Copyright 2023, Movie Palace Inc."
__license__ = "GPL"
__version__ = "0.1.1"
__maintainer__ = "Caleb Williams"
__email__ = "caleb.williams@wyomovies.com"
__status__ = "Production"

localhost = "localhost"
uni_headers = {"Content-Type": "application/json", 'Connection': 'keep-alive', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'User-Agent': 'python-requests/2.9.1'}

# Use the same creds you would use on the web UI
host_username = "manager"
host_password = "password"

class clip: 
    def __init__(self, id, text, length, end_time_in_seconds, type):
        self.id = id
        self.length = length
        self.text = text
        self.end_time_in_seconds = end_time_in_seconds
        self.type = type

def get_playlists(session_cookie, id):
    session = requests.Session()
    session.cookies.set('tms2_80', session_cookie)
    session.headers = uni_headers
    response = session.post("http://localhost/core/paginated/get_datatables_playlists", data=json.dumps({"device_uuid": id}))
    if response.status_code != 200: 
        return False
    else: 
        return (json.loads(response.text))['aaData']

def get_playlist_detailed(session_cookie, id, playlist_id):
    session = requests.Session()
    session.cookies.set('tms2_80', session_cookie)
    session.headers = uni_headers
    response = session.post("http://localhost/tms/get_playlist_detailed", data=json.dumps({"device_uuid": id,"playlist_uuid": playlist_id}))
    if response.status_code != 200: 
        return False
    else: 
        return (json.loads(response.text))['data']

def get_clips_detail(session_cookie, uuids):
    session = requests.Session()
    session.cookies.set('tms2_80', session_cookie)
    session.headers = headers = uni_headers
    response = session.post("http://localhost/tms/get_content_detailed", data=json.dumps({"content_uuids": uuids}))
    if response.status_code != 200: 
        return False
    else: 
        return (json.loads(response.text))['data']

def get_server_details(session_cookie):
    # get LMS uuid for the rest of the requests
    session = requests.Session()
    session.cookies.set('tms2_80', session_cookie)
    response = session.post("http://localhost/core/device_infos/","{}")
    if response.status_code != 200: 
        return False
    else: 
        data = json.loads(response.text)
        dev_info = data["data"]
        for devs in dev_info["devices"]: 
            if dev_info["devices"][devs]["name"] == "LMS": 
                return dev_info["devices"][devs]

def save_playlist(session_cookie, playlist):
    # ..input json, send save request to server
    session = requests.Session()
    session.cookies.set('tms2_80', session_cookie)
    session.headers = uni_headers
    response = session.post("http://localhost/core/playlist/save", data=playlist)
    if response.status_code != 200: 
        return False
    else: 
        return json.loads(response.text)

def login():
    # get cookie and authenticate
    session = requests.Session(); 
    authString = "?username=" + host_username + "&password=" + host_password
    response = session.get("http://localhost/")
    session.get("http://localhost/login_user" + authString)
    check = session.get("http://localhost/tms/")
    if check.status_code == 200: 
        return session.cookies.get_dict()
    else: 
        return False

def logout(session_cookie):
    session = requests.Session()
    session.cookies.set('tms2_80', session_cookie)
    session.headers = uni_headers
    res = session.get("http://localhost/logout_user")
    return res.status_code 
    
def get_update_playlists(session_cookie, id, old_cpl_id):
    # from list of playlists make a list of spl's with outdated content and return it
    playlists = get_playlists(session_cookie, id)
    if playlists == False: 
        return False
    else: 
        playlist_uuids = []
        for spl in playlists: 
            events = spl["playlist"]["events"]
            for e in events: 
                if e["cpl_id"] == old_cpl_id:
                    playlist_uuids.append(spl["id"])

        return playlist_uuids

def check_content_availablilty(session_id, old_cpl_id, new_cpl_id):
    clips = get_clips_detail(session_id, [old_cpl_id, new_cpl_id])
    if clips == False: 
        return False
    else: 
        uuids = []
        for uuid in clips: 
            uuids.append(uuid)

        if old_cpl_id in uuids and new_cpl_id in uuids: 
            return clips
        else: 
            return False

def updateSPL(id, playlist, oldcpl, newcpl, clipdetails):
    oldduration = playlist["duration_in_seconds"]
    cplindex = 0
    new_duration = 0
    events = playlist["events"]
    cpl_automation = []
    # get replacement cpl index in events
    for idx, cpl in enumerate(events):
        new_duration += cpl["duration_in_seconds"]
        if cpl['cpl_id'] == oldcpl: 
            # preserve automation events
            cpl_automationautomation = cpl["automation"]
            cplindex = idx
    
    new_cpl_obj = {
        "type": "composition",
        "cpl_id": clipdetails[newcpl]['uuid'],
        "duration_in_seconds": clipdetails[newcpl]["duration_in_seconds"],
        "duration_in_frames": clipdetails[newcpl]["duration_in_frames"],
        "cpl_start_time_in_seconds": clipdetails[newcpl]["cpl_start_time_in_seconds"],
        "cpl_start_time_in_frames": clipdetails[newcpl]["cpl_start_time_in_frames"],
        "edit_rate": clipdetails[newcpl]["edit_rate"],
        "text": clipdetails[newcpl]["content_title_text"],
        "playback_mode": clipdetails[newcpl]["playback_mode"],
        "content_kind": clipdetails[newcpl]["content_kind"],
        "automation": cpl_automation 
    }



    # replace cpl
    playlist["events"][cplindex] = new_cpl_obj

    # get rid of some junk
    new_playlist = {
        "device_id": id,
        "playlist": {
            "id": playlist["id"],
            "duration_in_seconds": playlist["duration_in_seconds"],
            "title": playlist["title"],
            "events": playlist["events"],
            "is_3d": playlist["is_3d"],
            "is_hfr": playlist["is_hfr"],
            "is_4k": playlist["is_4k"],
            "automation": playlist["automation"]
        }
    }

    # fix duration if necessary
    if oldduration != new_duration:
        new_playlist["playlist"]["duration_in_seconds"] = new_duration
    else: 
        print("Warning: Duration not updated for " + playlist["title"])

    # save playlist has this value so we'll add it
    new_playlist["device_id"] = id

    return new_playlist

    


print("\033[1;31mWARNING: This script only works if assets only have one MainPicture asset!")
print("         Any other usage will have undefined behavior.  Use at your own risk")
print("         Creating a backup of show playlists is recommended.\033[0m")
parser = argparse.ArgumentParser(description='Change one clip to another in an show playlist on Screenwriter')
parser.add_argument('Old_CPL', help='Old CPL uuid')
parser.add_argument('New_CPL', help='New CPL uuid')
args = parser.parse_args()

# basics first
cookie_obj = login()

if cookie_obj == False: 
    raise Exception("Error: Unable to authenticate to server")
else: 
    cookie_string = cookie_obj['tms2_80']
    server_info = get_server_details(cookie_string)
    server_uuid = server_info['id']
    clips = check_content_availablilty(cookie_string, args.Old_CPL, args.New_CPL)
    
    if clips == False:
        raise Exception("Error: One or more clips is not available on this server")
    else: 
        update_spl_list = get_update_playlists(cookie_string, server_uuid, args.Old_CPL)
        if len(update_spl_list) == 0: 
            print("Nothing to replace. Have a nice day :)")
            sys.exit(0)
        else: 
            # raw_input() was renamed to input() in python v3 but we have to target v2
            r = raw_input(str(len(update_spl_list)) + " show playlists contain old clip. OK to replace?")
            if r is 'y' or 'yes': 
                # this is the actual work area of the script 
                error_spl = []
                good_spl = []
                for uuid in update_spl_list: 
                    old_playlist = get_playlist_detailed(cookie_string, server_uuid, uuid)
                    if old_playlist == False: 
                        print("\033[31m Error: \033[0m There was an issue retrieving playlist contents")
                        continue
                    new_playlist = updateSPL(server_uuid, old_playlist, args.Old_CPL, args.New_CPL, clips)
                    print("Saving playlist: " + new_playlist["playlist"]["title"])
                    response = save_playlist(cookie_string, json.dumps(new_playlist))
                    if response == False: 
                        print("Error: There was an error saving " + new_playlist["playlist"]["title"])
                        error_spl.append(new_playlist["playlist"]["title"])
                        continue
                    good_spl.append(new_playlist["playlist"]["title"])
                    # wait for a second here to avoid hitting rate limits
                    time.sleep(1)

                print(str(len(good_spl)) + " playlists updated.")
                if len(error_spl) != 0: 
                    print("\033[1;31mThe following playlists need attention: \033[0m")
                    for spl in error_spl: 
                        print(spl)

                print("Logging Out...")
                logout_response = logout(cookie_string)
                if logout_response != 200: 
                    print("There was an error logging out but we can be irresponsible with our cookie just this once...")
                
            else: 
                print("Nothing changed.")

                    
        

        