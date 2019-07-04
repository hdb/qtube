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
FONT = 'Courier'
TEXT_LENGTH = 20
NUM_RESULTS = 15


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

    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def on_context_menu(self):
        self.contextMenu.exec(QCursor.pos()) 

    def on_action_play(self):
        self.clicked.emit()

    def on_action_download(self):

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])

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


ydl_opts = {
    'logger': MyLogger(),
    'progress_hooks': [my_hook],
    'outtmpl': str(Path.home()) + '/Desktop/%(title)s.%(ext)s',
}

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


        self.data=grabData('https://www.youtube.com/playlist?list=PL3ZQ5CpNulQldOL3T8g8k1mgWWysJfE9w', search=False)
        self.populate()
        groupbox = QGroupBox('Trending Stories')
        groupbox.setLayout(self.myform)
        groupbox.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+";font-style: italic")
        self.scroll.setWidget(groupbox)

        self.line = QLineEdit(self)
        self.line.returnPressed.connect(self.clickMethod)
        self.line.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")

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

        sublayout = QVBoxLayout()
        sublayout.addWidget(self.line)
        sublayout.addWidget(self.scroll)
        left = QWidget()
        left.setLayout(sublayout)
        left.setFixedWidth(LIST_WIDTH)

        biglayout = QHBoxLayout(self)
        biglayout.addWidget(left)
        biglayout.addWidget(self.container)


    def clickMethod(self):

        self.search = self.line.text()
        print('searching...')
        search_term = self.search
        data = grabData(search_term, limit=NUM_RESULTS)
        self.data = data
        self.populate()
        groupbox = QGroupBox('results for "' + self.search + '"')
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
            descLabel.clicked.connect(self.on_video_clicked)
            labellist.append(descLabel)
            
            imagelabel = ImageLabel(self.data['urls'][i], self.data['titles'][i])
            pixmap = QPixmap(img)
            pixmap = pixmap.scaled(THUMB_SIZE, FLAGS)
            imagelabel.setPixmap(pixmap)
            imagelabel.clicked.connect(self.on_video_clicked)
            combolist.append(imagelabel) #
            form.addRow(combolist[i], labellist[i])

        self.myform = form
        

    def exit_seq(self):
        sys.exit()

    def on_video_clicked(self):

        label = self.sender()
        self.url = label.url
        self.player.play(self.url)

def grabData(search_term, search=True, limit=10):
    
    data = {'urls': [], 'titles': [], 'thumb_urls': [], 'thumb_paths': [], 'durations': [], 'views': [], 'ratings': [], 'dates': []}

    if search:
        pl_url = 'https://www.youtube.com/results?search_query='+ search_term.replace(' ','+')

    else: # allow start page to be set by url rather than search term
        pl_url=search_term

    meta_opts = {'extract_flat': True, 'quiet': True} 

    thumb_opts = {'forcethumbnail': True, 'simulate': True}

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
    #sys.exit()
    #print(data['thumb_urls'])
    date = time.strftime("%d-%m-%Y--%H-%M-%S")
    image_dir = '/tmp/qt/yt-thumbs/'+date+'/'
    mktmpdir(image_dir)
    for i, image in enumerate(data['thumb_urls']):
        data['thumb_paths'].append(dl_image(image,image_dir, i))

    #[print(len(data[d]), ' ', data[d] ) for d in data]
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
