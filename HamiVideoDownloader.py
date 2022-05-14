import os
import re
import csv
import time
import m3u8
import requests
from bs4 import BeautifulSoup


class CpblHamiVideoDownloader():
    def __init__(self, cookie):
        
        self.CPBL_video_list = []
        self.CPBL_video_last = []
        self.CPBL_video_new = []
        
        self.session = requests.session()

        self.cookie = cookie
        self.timeout = 5
        self.time_sleep = 0

    class HamiVideo():
        def __init__(self, id, date, name, url, oot_vod, m3u8_url):
            
            self.id = id
            self.date = date
            self.name = name
            self.play_url = url
            self.oot_vod = oot_vod
            self.m3u8_url = m3u8_url
            self.m3u8_file_name = id + "_" + date + "_" + name + ".m3u8"
        
        def __repr__(self):
            return self.id + "_" + self.date + "_" + self.name


    def update_CPBL_video_list(self):

        # 2022 四月完整賽事
        main_page_url = 'https://hamivideo.hinet.net/more.do?type=card_vod_horizontal&key=572&menuId=664&filterType=new'
        other_page_url = 'https://hamivideo.hinet.net/ui26_page.do'
        data = {
            'menuId': '664',
            'filterType': 'new',
            'getStr': '24',
            'key': '572',
            'type': 'card_vod_horizontal'
        }

        # 2022 五月完整賽事
        main_page_url = 'https://hamivideo.hinet.net/more.do?type=card_vod_horizontal&key=592&menuId=664&filterType=new'

        main_page = self.session.get(main_page_url, timeout=self.timeout)
        bs_main_page = BeautifulSoup(main_page.text, 'html.parser')
        main_page_video_path = bs_main_page.find_all("div", {"class": "vodListBlock sty2 ui26"})[
            0].find_all("div", {"class": "list_item"})

        # Other Page (動態加載頁面，取得其他)
        

        other_page = self.session.post(other_page_url, timeout=self.timeout, data=data)

        bs_other_page = BeautifulSoup(other_page.text, 'html.parser')
        other_page_video_path = bs_other_page.find_all(
            "div", {"class": "list_item"})

        
        self.append_video_to_CPBL_video_list(main_page_video_path)
        self.append_video_to_CPBL_video_list(other_page_video_path)
        
        self.CPBL_video_list.sort(key=lambda x: x.id)
        
    def find_HamiVideo_OTT(self, play_url):

        time.sleep(self.time_sleep)
        
        OOT_VOD = self.session.get(play_url, timeout=self.timeout)
        bs_OOT_VOD = BeautifulSoup(OOT_VOD.text, 'html.parser')
        OOT_VOD = bs_OOT_VOD.find_all('script')        
        OOT_VOD = str(OOT_VOD).split('now_contentPk=')[1][:20]
        
        return OOT_VOD
    
    
    def find_HamiVideo_m3u8(self, OOT_VOD):
        
        m3u8_url =  "https://hamivideo.hinet.net/api/play.do?id=" + OOT_VOD.replace("'","") + "&freeProduct=0"
        
        headers = {
            "Cookie" : self.cookie
        }
        
        m3u8_page = self.session.get(m3u8_url, timeout=self.timeout, headers=headers)
        m3u8_url = m3u8_page.json()['url']
        
        return m3u8_url
    
    
    def append_video_to_CPBL_video_list(self, video_path):
        
        for video_path in video_path:
            video_find = video_path.find_all("a")[0]
            video_name = video_find.get('onclick')[24:-2]
            video_href = video_find.get('href')

            id = video_name[:4]
            date = video_name[-8:]
            name = video_name[4:-8]
            play_url = "https://hamivideo.hinet.net/"+video_href.replace("product", "play")

            oot_vod = self.find_HamiVideo_OTT(play_url)
            m3u8_url = self.find_HamiVideo_m3u8(oot_vod)
            
            # 防止類別錯誤
            if date == "中華職棒開季宣傳":
                name = date
                date = "20220101"
                id = "G000"

            temp = self.HamiVideo(id, date, name, play_url, oot_vod, m3u8_url)
            

            self.CPBL_video_list.append(temp)
            print(temp.id, temp.oot_vod, temp.play_url, temp.date, temp.name)
            

                
    def read_list_csv(self):
        with open('hamivideo_list.csv', 'r', newline='',encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            headings = next(reader)
            
            for row in reader:
                temp = self.HamiVideo(row[0], row[1], row[2], row[3], row[4], row[5])
                self.CPBL_video_last.append(temp)
                # print(temp.id, temp.oot_vod, temp.play_url, temp.date, temp.name)

            # for video in self.CPBL_video_list:
            #     writer.writerow([video.id, video.date, video.name, video.play_url, video.oot_vod, video.m3u8_url])
    
    def write_list_csv(self):
        with open('hamivideo_list.csv', 'w', newline='',encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            writer.writerow(['Id', 'Date', 'Name', 'Play_url', 'Oot_vod', 'M3u8_url'])
            
            for video in self.CPBL_video_list:
                writer.writerow([video.id, video.date, video.name, video.play_url, video.oot_vod, video.m3u8_url])
    
    
    def has_new_video(self):
        return not(len(self.CPBL_video_list) == len(self.CPBL_video_last))
    
    def find_new_video(self):
        last_video_id = []
        
        for video in self.CPBL_video_last:
            last_video_id.append(video.id)
        
        for video in self.CPBL_video_list:
            if video.id not in last_video_id:
                self.CPBL_video_new.append(video)

        
        return self.CPBL_video_new

        
    def download_video(self, video):
        def create_command(Url, Type):
            return "N_m3u8DL-CLI_v2.9.9.exe " + '"'+ Url + '"'+ " --workDir " + '"' + str(video) + '"' +" --saveName " + '"' + str(video) + "_"+ Type + '"' + " --enableDelAfterDone"

        
        dirName = str(video)
        
        try:
            os.mkdir(dirName)
            print("Directory " , dirName ,  " Created ") 
        except FileExistsError:
            print("Directory " , dirName ,  " already exists")

        playlist = m3u8.load(video.m3u8_url)
        
        CMD = create_command(playlist.base_uri + playlist.media[0].uri , "audio")
        os.system(CMD)
        
        CMD = create_command(playlist.base_uri + playlist.playlists[2].uri , "video")
        os.system(CMD)
        
        print()
        print("下載完成 " + str(video))
        
        


if __name__ == "__main__":
    cookie = "uuid=6a476fc8-097e-474d-8404-1ea9fbf46dfd; __htid=6a476fc8-097e-474d-8404-1ea9fbf46dfd; __BWfp=c1650990764416x98a69c9d7; _gcl_au=1.1.176094014.1650990764; _ga=GA1.3.1370128725.1650990764; _fbp=fb.2.1650990764587.1482156319; _fbp=fb.1.1650990764587.1482156319; video_volume=1; _ht_hi=1; _gid=GA1.2.1563732173.1651406238; _gid=GA1.3.1563732173.1651406238; _ht_f4b8a7=1; BIGipServerrBtu5cKbUKuOQaGS4KMTNg=!hXXZDTXbCWxv2KYEzMM1clw1rVnGWaajdmwgPmbkbTo/CR0JeggGLn80LbG3kgth+URn/vF2yUDU09U=; ohu=c7058664da3a32d575be1fa287050c53349905dbda293d3af69faac42e249077aca45727cadba67f70e5fb5faa0a03e491c80932e350eb621920acdf6946d5aa087cdc6d9236064bc76f18036a428b87f083378065a57ff087502b45146df2598e59f59fdca971cb816c0c04bb70cb7a3cd264f63e22437a4fdfe7d2288848f2ab50dbddb0d17a64bc2cf01044870a1aae474ab8848d66c1bbcf6220fc443849510c48a9125579ddb808787f4938368af0b2424254428c56c7755ec35904845393c2059e19e7dd2016ecdb19fc26f3fb84904e6190408a247c29c626af465fe66682c40ac8ab06c5ecc854711b1cdead8b1a2c37ce6c94b35a74ac6a3c95a77caf580eecd43038f0c87eb5f1bbb8de7eabf49e123aed7f115a63230488d47a8a770fa2ccbdf1ebb9c0ac9e3dffd41108dc0adc44f5e0a7fb46678bb0e9d73f09c5b3248d7cefd8934d62ee09f141c7dc01a72fe2be3ddf0e9ecab2602461bd3ba0680cba75dc259ed011617d5a9d4442adc2cb0660b1c885dc6120a7a6fb4665a78ca3e877e334047701e2d7cf56b82b635c35d4a0de2b718e858301a8076ce6; JSESSIONID=751E762FA714A33E82AD39E5A94A6201; keepMenuId=; _ht_em=1; seconds=1; _gat_UA-49979189-1=1; csrftoken=ece44b69-f78c-4a3d-b1af-354d78018b22; _dc_gtm_UA-49979189-1=1; _ga=GA1.2.1370128725.1650990764; _ga_NCTT6HZ347=GS1.1.1651477374.15.1.1651477458.49"
    CPBL = CpblHamiVideoDownloader(cookie)
    
    CPBL.update_CPBL_video_list()
    CPBL.read_list_csv()
    
    
    if CPBL.has_new_video():
        print(CPBL.find_new_video())

        check = input("Download?")
        
        if check == 'Yes':
        
            for video in CPBL.find_new_video():
                CPBL.download_video(video)

        CPBL.write_list_csv()