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

        # Main Page (主要頁面，會有部分沒有)
        main_page_url = 'https://hamivideo.hinet.net/more.do?type=card_vod_horizontal&key=572&menuId=664&filterType=new'

        main_page = self.session.get(main_page_url, timeout=self.timeout)
        bs_main_page = BeautifulSoup(main_page.text, 'html.parser')
        main_page_video_path = bs_main_page.find_all("div", {"class": "vodListBlock sty2 ui26"})[
            0].find_all("div", {"class": "list_item"})

        # Other Page (動態加載頁面，取得其他)
        other_page_url = 'https://hamivideo.hinet.net/ui26_page.do'
        data = {
            'menuId': '664',
            'filterType': 'new',
            'getStr': '24',
            'key': '572',
            'type': 'card_vod_horizontal'
        }

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
    cookie = "Your Cookie"
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