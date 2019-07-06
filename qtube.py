#! /usr/bin/python3

import mpv
import re
import sys
import time
import urllib.request
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import youtube_dl
import os
import textwrap
from pathlib import Path


# CUSTOMIZABLE SETTINGS

THUMB_SIZE = QSize(128,72)
FLAGS = Qt.KeepAspectRatioByExpanding
LIST_WIDTH = 400
BACKGROUND_COLOR = 'white'
FOREGROUND_COLOR = 'red'
INACTIVE_COLOR = 'grey'
FONT = 'Courier'
TEXT_LENGTH = 20
NUM_RESULTS = 10
HOME_URL = 'https://www.youtube.com/playlist?list=PL3ZQ5CpNulQldOL3T8g8k1mgWWysJfE9w'
DOWNLOAD_LOCATION = str(Path.home()) + '/Downloads/'


class ImageLabel(QLabel):
    def __init__(self, url, title, parent=None):
        super(QLabel, self).__init__(parent)

        self.url = url
        self.title=title
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("color: "+FOREGROUND_COLOR+";")

        # set button context menu policy
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        # create context menu
        self.contextMenu = QMenu(self)
        self.contextMenu.setCursor(Qt.PointingHandCursor)
        self.contextMenu.addAction('Play', self.on_action_play)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction('Download', self.on_action_download)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction('Copy Url', self.on_action_copy)

    video_clicked = pyqtSignal()

    download_clicked = pyqtSignal()


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.video_clicked.emit()

    def on_context_menu(self):
        self.contextMenu.exec(QCursor.pos()) 

    def on_action_play(self):
        self.video_clicked.emit()

    def on_action_download(self):
        self.download_clicked.emit()

    def on_action_copy(self):
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Clipboard )
        cb.setText(self.url, mode=cb.Clipboard)


class DescriptionLabel(ImageLabel):
    def __init__(self, url, title, parent=None):
        super(ImageLabel, self).__init__(parent)

        self.setToolTip(title) # class is same as ImageLabel but with ToolTip

        self.url = url
        self.title=title
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("color: "+FOREGROUND_COLOR+";")

        # set button context menu policy
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        # create context menu
        self.contextMenu = QMenu(self)
        self.contextMenu.setCursor(Qt.PointingHandCursor)
        self.contextMenu.addAction('Play', self.on_action_play)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction('Download', self.on_action_download)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction('Copy Url', self.on_action_copy)


# youtube-dl options for downloading video via context menu
class MyLogger(object):

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')
    if d['status'] == 'downloading':
        print(d['filename'], d['_percent_str'], d['_eta_str'], '\r', end='')


class Window(QWidget):
    def __init__(self, val, parent=None):
        super().__init__(parent)
        self.setMinimumSize(QSize(1800, 800))
        self.setWindowTitle("qtube")
        self.exitshortcut1=QShortcut(QKeySequence("Ctrl+Q"), self)
        self.exitshortcut2=QShortcut(QKeySequence("Ctrl+W"), self)
        self.exitshortcut1.activated.connect(self.exit_seq)
        self.exitshortcut2.activated.connect(self.exit_seq)
        self.setStyleSheet("background-color: "+BACKGROUND_COLOR+";")
        self.search=""
        self.url=''
        self.history={'urls': [HOME_URL], 'title_boxes': ['Trending Stories']}
        self.downloaded_videos=[]


        self.mygroupbox = QGroupBox('')
        self.mygroupbox.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+"; font-style: italic")
        self.myform = QFormLayout()
        labellist = []
        combolist = []

        self.mygroupbox.setLayout(self.myform)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.mygroupbox)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("color: "+FOREGROUND_COLOR+";")


        self.data=grabData(HOME_URL, search=False)
        self.populate()
        groupbox = QGroupBox('Trending Stories')
        groupbox.setLayout(self.myform)
        groupbox.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+";font-style: italic")
        self.scroll.setWidget(groupbox)

        self.line = QLineEdit(self)
        self.line.returnPressed.connect(self.clickMethod)
        self.line.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")

        active_buttons = []
        self.inactive_buttons = []

        self.search_button = QPushButton()
        self.search_button.setText('Search')
        self.search_button.clicked.connect(self.clickMethod)
        active_buttons.append(self.search_button)

        self.home_button = QPushButton()
        self.home_button.setText('Home')
        self.home_button.clicked.connect(self.on_home_clicked)
        self.inactive_buttons.append(self.home_button)

        self.play_playlist_button = QPushButton()
        self.play_playlist_button.setText('Play All')
        self.play_playlist_button.clicked.connect(self.on_play_playlist_clicked)
        active_buttons.append(self.play_playlist_button)

        self.back_button = QPushButton()
        self.back_button.setText('Back')
        self.back_button.clicked.connect(self.on_back_clicked)
        self.inactive_buttons.append(self.back_button)

        for b in active_buttons:
            b.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")
            b.setCursor(Qt.PointingHandCursor)

        for b in self.inactive_buttons:
            b.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+INACTIVE_COLOR+"; font-family: "+FONT+";")

        self.dl_progress = QLabel()
        self.dl_progress.setText('           0 downloads           ')
        self.dl_progress.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; font-family: "+FONT+";")

        self.play_downloaded_button = QPushButton()
        self.play_downloaded_button.setText('Play')
        self.play_downloaded_button.clicked.connect(self.on_play_downloaded)
        self.play_downloaded_button.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+INACTIVE_COLOR+"; font-family: "+FONT+";")


        self.container = QWidget()
        self.container.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.container.setAttribute(Qt.WA_NativeWindow)       
        self.player = mpv.MPV(wid=str(int(self.container.winId())),
                ytdl=True, 
                input_default_bindings=True, 
                input_vo_keyboard=True,
                scripts=str(Path.home())+'/.config/mpv/scripts/live-filters.lua', # option to add custom script / currently no way of importing multiple scripts with MPV API
        )

        # TODO: allow exit key sequences while mpv window is active
        self.player.register_key_binding('q', '')

        searchbarlayout = QHBoxLayout()
        searchbarlayout.addWidget(self.line)
        searchbarlayout.addWidget(self.search_button)
        searchbar = QWidget()
        searchbar.setLayout(searchbarlayout)

        buttonrowlayout = QHBoxLayout()
        buttonrowlayout.addWidget(self.back_button)
        buttonrowlayout.addWidget(self.home_button)
        buttonrowlayout.addWidget(self.play_playlist_button)
        buttonrow = QWidget()
        buttonrow.setLayout(buttonrowlayout)

        downloadrowlayout = QHBoxLayout()
        downloadrowlayout.addWidget(self.dl_progress)
        downloadrowlayout.addWidget(self.play_downloaded_button)
        downloadrow = QWidget()
        downloadrow.setLayout(downloadrowlayout)

        sublayout = QVBoxLayout()
        sublayout.addWidget(searchbar)
        sublayout.addWidget(buttonrow)
        sublayout.addWidget(self.scroll)
        sublayout.addWidget(downloadrow)
        left = QWidget()
        left.setLayout(sublayout)
        left.setFixedWidth(LIST_WIDTH)

        biglayout = QHBoxLayout(self)
        biglayout.addWidget(left)
        biglayout.addWidget(self.container)


    def clickMethod(self):

        self.search = self.line.text()
        print('searching "' + self.search + '"...')
        search_term = self.search
        title_box = 'results for "' + search_term + '"'

        self.data = grabData(search_term)
        self.history['title_boxes'].append(title_box)
        self.history['urls'].append(self.data['playlist_url'])
        for b in self.inactive_buttons:
            b.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")
            b.setCursor(Qt.PointingHandCursor)
        self.populate()
        groupbox = QGroupBox(title_box)
        groupbox.setLayout(self.myform)
        groupbox.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+";font-style: italic")
        self.scroll.setWidget(groupbox)


    def populate(self):

        labellist = []
        combolist = []
        form = QFormLayout()

        for i,img in enumerate(self.data['thumb_paths']):

            if self.data['titles'][i] is not None:
                title = '\n'.join(textwrap.wrap(self.data['titles'][i], TEXT_LENGTH)[:2])
                if len(self.data['titles'][i]) > TEXT_LENGTH*2: 
                    title = title + '...'
            else: # catch errors from youtube-dl failing to capture video title
                title = '[TITLE MISSING]'

            text =  title + '\n' + self.data['durations'][i] + ' | ' + self.data['dates'][i] + '\n' + self.data['views'][i] + ' views | rated ' + self.data['ratings'][i] 
            
            descLabel = DescriptionLabel(self.data['urls'][i], self.data['titles'][i])
            descLabel.setText(text)
            descLabel.video_clicked.connect(self.on_video_clicked)
            descLabel.download_clicked.connect(self.on_download_clicked)
            labellist.append(descLabel)
            
            imagelabel = ImageLabel(self.data['urls'][i], self.data['titles'][i])
            pixmap = QPixmap(img)
            pixmap = pixmap.scaled(THUMB_SIZE, FLAGS)
            imagelabel.setPixmap(pixmap)
            imagelabel.video_clicked.connect(self.on_video_clicked)
            imagelabel.download_clicked.connect(self.on_download_clicked)
            combolist.append(imagelabel) #
            form.addRow(combolist[i], labellist[i])

        self.myform = form
        

    def exit_seq(self):
        sys.exit()


    def on_video_clicked(self):

        label = self.sender()
        self.url = label.url
        self.player.play(self.url)


    def on_download_clicked(self):

        label = self.sender()

        title_long = label.title.replace(' ','-')
        title_short = title_long[:20]

        ydl_opts = {
            'logger': MyLogger(),
            'progress_hooks': [my_hook],
            'outtmpl': DOWNLOAD_LOCATION + title_long
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([label.url])

        self.dl_progress.setText('"' + title_short + '" downloaded.')
        self.dl_progress.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; font-family: "+FONT+";")
        self.play_downloaded_button.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")
        self.play_downloaded_button.setCursor(Qt.PointingHandCursor)

        vid_path = [DOWNLOAD_LOCATION + file for file in os.listdir(DOWNLOAD_LOCATION) if file.startswith(title_long)][0]
        self.downloaded_videos.append(vid_path)


    def on_home_clicked(self):

        if HOME_URL not in self.history['urls'][-1]:
            print('loading homepage...')
            self.search = ''
            self.data=grabData(HOME_URL, search=False)
            self.history['title_boxes'].append('Trending Stories')
            self.history['urls'].append(self.data['playlist_url'])
            self.populate()
            groupbox = QGroupBox('Trending Stories')
            groupbox.setLayout(self.myform)
            groupbox.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+";font-style: italic")
            self.scroll.setWidget(groupbox)

            self.home_button.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+INACTIVE_COLOR+"; font-family: "+FONT+";")
            self.home_button.setCursor(Qt.ArrowCursor)

        else:
            print('already home')


    def on_play_playlist_clicked(self):

        self.url = self.history['urls'][-1]
        self.player.play(self.url)

        #TODO: add mpv options to limit playlist items to number of search results


    def on_back_clicked(self):
        if len(self.history['urls'])>1:
            self.search = ''
            self.history['urls'].pop(-1)
            self.data = grabData(self.history['urls'][-1], search=False)
            self.populate()
            self.history['title_boxes'].pop(-1)
            groupbox = QGroupBox(self.history['title_boxes'][-1])
            groupbox.setLayout(self.myform)
            groupbox.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+";font-style: italic")
            self.scroll.setWidget(groupbox)
            print('returning to page ' + self.history['urls'][-1] + '...')

            if len(self.history['urls']) == 1:
                for b in self.inactive_buttons:
                    b.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+INACTIVE_COLOR+"; font-family: "+FONT+";")
                    b.setCursor(Qt.ArrowCursor)

        else:
            print('could not go back')


    def on_play_downloaded(self):

        if len(self.downloaded_videos) > 0:
            last_downloaded = self.downloaded_videos[-1]
            self.player.play(last_downloaded)

        else:
            print('no videos downloaded yet')


def grabData(search_term, search=True, limit=NUM_RESULTS):

    #TODO: fetch next page of results
    
    if search:
        pl_url = 'https://www.youtube.com/results?search_query='+ search_term.replace(' ','+')

    else: # allow start page to be set by url rather than search term
        pl_url=search_term

    data = {'urls': [], 'titles': [], 'thumb_urls': [], 'thumb_paths': [], 
        'durations': [], 'views': [], 'ratings': [], 'dates': [], 
        'playlist_url': pl_url}


    meta_opts = {'extract_flat': True, 'quiet': True} 

    with youtube_dl.YoutubeDL(meta_opts) as ydl:
        meta = ydl.extract_info(pl_url, download=False)

    for e in meta['entries']:
        data['urls'].append('https://www.youtube.com/watch?v=' + e.get('url'))
        data['titles'].append(e.get('title'))
    
    data['urls'] = data['urls'][:limit]
    data['titles'] = data['titles'][:limit]

    #TODO: create faster way of getting thumbnails using beautifulsoup

    for u in data['urls']:
        with youtube_dl.YoutubeDL(meta_opts) as ydl:
            try:
                d = ydl.extract_info(u, download=False)

            except: # youtube-dl playlists capture non-playable media such as paid videos. skip these items
                print('skipping ' + u)
                pass

            data['thumb_urls'].append(d['thumbnail'])

            if d['duration'] == 0.0: # live videos appear to give youtube-dl trouble
                duration = 'LIVE'
            elif d['duration'] < 3600:
                duration = str(int(d['duration']/60))+':'+"{0:0=2d}".format(d['duration']%60)
            else:
                duration = str(int(d['duration']/3600))+':'+"{0:0=2d}".format(int((d['duration']-3600)/60))+':'+"{0:0=2d}".format(d['duration']%60)
            #print(duration)
            data['durations'].append(duration)

            views = d['view_count']
            if views > 1000000:
                views_abbr = str(int(views/1000000))+'M'
            elif views > 1000:
                views_abbr = str(int(views/1000))+'K'
            else: 
                views_abbr = str(views)
            data['views'].append(views_abbr)
            try:
                rating=str(int(100*(d['like_count']/(d['like_count']+d['dislike_count']))))+'%'
            except:
                rating='100%'
            data['ratings'].append(rating)

            upload_date = d['upload_date']
            formatted_date = upload_date[4:6] + '-' + upload_date[-2:] + '-' + upload_date[:4]
            data['dates'].append(formatted_date)

        time.sleep(.05)

    date = time.strftime("%d-%m-%Y--%H-%M-%S")
    image_dir = '/tmp/qt/yt-thumbs/'+date+'/'
    mktmpdir(image_dir)
    for i, image in enumerate(data['thumb_urls']):
        data['thumb_paths'].append(dl_image(image,image_dir, i))

    return data

def dl_image(u, path, index):

    out = path + str(index) + '.jpg'
    urllib.request.urlretrieve(u, out)
    return out  


def mktmpdir(directory):

    if not os.path.exists(directory):
        os.makedirs(directory)


if __name__ == '__main__':

    import sys
    import locale
    app = QApplication(sys.argv)
    locale.setlocale(locale.LC_NUMERIC, 'C')

    window = Window(25)
    window.show()
    sys.exit(app.exec_())
