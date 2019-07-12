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
import math
import textwrap
from pathlib import Path
from waitingspinnerwidget import QtWaitingSpinner


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

def trap_exc_during_debug(*args):
    # when app raises uncaught exception, print info
    print(args)

# install exception hook: without this, uncaught exception would cause application to exit
sys.excepthook = trap_exc_during_debug


class Worker(QObject):
        
    sig_msg = pyqtSignal(str)  # message to be shown to user
    sig_data = pyqtSignal(dict)

    def __init__(self, id, search_term, search=True, limit=[0,NUM_RESULTS], label=None):
        super().__init__()
        self.__id = id
        self.__abort = False
        self.search_term = search_term
        self.search = search
        self.limit = limit
        self.label = label


    @pyqtSlot()
    def grabData(self):
        
        if self.search:
            pl_url = 'https://www.youtube.com/results?search_query=' + self.search_term.replace(' ','+')

        else: # allow start page to be set by url rather than search term
            pl_url = self.search_term

        data = {'urls': [], 'titles': [], 'thumb_urls': [], 'thumb_paths': [], 
            'durations': [], 'views': [], 'ratings': [], 'dates': [], 
            'playlist_url': pl_url, 'total_videos': 0}


        meta_opts = {'extract_flat': True, 'quiet': True} 

        with youtube_dl.YoutubeDL(meta_opts) as ydl:
            meta = ydl.extract_info(pl_url, download=False)

        for e in meta['entries']:
            data['urls'].append('https://www.youtube.com/watch?v=' + e.get('url'))
            data['titles'].append(e.get('title'))

        data['total_videos'] = len(meta['entries'])
        data['urls'] = data['urls'][self.limit[0]:self.limit[1]]
        data['titles'] = data['titles'][self.limit[0]:self.limit[1]]

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

        self.sig_data.emit(data)

    def download(self):

        title_long = self.__id.replace(' ','-')

        #TODO: fix issue with videos containing single quotes at beginning

        self.label.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; font-family: "+FONT+";")

        ydl_opts = {
            'logger': MyLogger(),
            'progress_hooks': [self.my_hook],
            'outtmpl': DOWNLOAD_LOCATION + title_long
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.search_term])

        self.sig_msg.emit(title_long)

    def my_hook(self, d):
        if d['status'] == 'finished':
            self.label.setText('Converting...')
        if d['status'] == 'downloading':
            self.label.setText(d['_percent_str'] + ' ' + d['_eta_str'])


    def abort(self):
        self.sig_msg.emit('Worker {} notified to abort'.format(self.__id))
        self.__abort = True


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


class PageLabel(QLabel):
    def __init__(self, page, active, parent=None):
        super(QLabel, self).__init__(parent)

        self.page = page
        self.setText(str(self.page))

        if active:
            self.active = True
            self.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+"; font: bold")
            self.setCursor(Qt.PointingHandCursor)
            
        else:
            self.active = False
            self.setStyleSheet("color: "+INACTIVE_COLOR+"; font-family: "+FONT+"; font: bold")
            
    page_clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.active:
            self.page_clicked.emit()


# youtube-dl logging
class MyLogger(object):

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


class Window(QWidget):

    sig_abort_workers = pyqtSignal()

    def __init__(self, val, parent=None):
        super().__init__(parent)
        self.setMinimumSize(QSize(1800, 800))
        self.setWindowTitle("qtube")
        self.exitshortcut1=QShortcut(QKeySequence("Ctrl+Q"), self)
        self.exitshortcut2=QShortcut(QKeySequence("Ctrl+W"), self)
        self.exitshortcut1.activated.connect(self.exit_seq)
        self.exitshortcut2.activated.connect(self.exit_seq)
        self.setStyleSheet("background-color: "+BACKGROUND_COLOR+";")

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

        self.history={'urls': [], 'title_boxes': [], 'data': [], 'page_numbers': []}
        self.downloaded_videos = {'paths': [], 'short_titles': []}
        self.search = ''

        self.spinner = QtWaitingSpinner(self, False)
        self.spinner.setRoundness(70.0)
        self.spinner.setMinimumTrailOpacity(15.0)
        self.spinner.setTrailFadePercentage(70.0)
        self.spinner.setNumberOfLines(10)
        self.spinner.setLineLength(10)
        self.spinner.setLineWidth(4)
        self.spinner.setInnerRadius(4)
        self.spinner.setRevolutionsPerSecond(1.5)
        self.spinner.setColor(QColor(255, 0, 0))

        # multi-threading
        QThread.currentThread().setObjectName('main')  # threads can be named, useful for log output
        self.__workers_done = []
        self.__threads = []

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

        self.download_label = QLabel()
        self.download_label.setText('0 downloads')
        self.download_label.setMaximumSize(QSize(110,20))
        self.download_label.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; font-family: "+FONT+";")

        self.download_selector = QComboBox()
        self.download_selector.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; font-family: "+FONT+";")
        self.download_selector.currentIndexChanged.connect(self.select_download)

        self.download_to_play = ''

        self.play_downloaded_button = QPushButton()
        self.play_downloaded_button.setText('Play')
        self.play_downloaded_button.clicked.connect(self.on_play_downloaded)
        self.play_downloaded_button.setMaximumSize(QSize(50,20))
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

        # TODO: allow exit key sequences while mpv window is active; allow fullscreen mode
        self.player.register_key_binding('q', '')

        searchbarlayout = QHBoxLayout()
        searchbarlayout.addWidget(self.line)
        searchbarlayout.addWidget(self.search_button)
        searchbarlayout.addWidget(self.spinner)
        searchbar = QWidget()
        searchbar.setLayout(searchbarlayout)

        buttonrowlayout = QHBoxLayout()
        buttonrowlayout.addWidget(self.back_button)
        buttonrowlayout.addWidget(self.home_button)
        buttonrowlayout.addWidget(self.play_playlist_button)
        buttonrow = QWidget()
        buttonrow.setLayout(buttonrowlayout)

        downloadrowlayout = QHBoxLayout()
        downloadrowlayout.addWidget(self.download_label)
        downloadrowlayout.addWidget(self.download_selector)
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

        # load home page data
        self.spinner.start()

        idx = 'Home'
        worker = Worker(idx, HOME_URL, search=False)
        thread = QThread()
        thread.setObjectName('thread_' + idx)
        worker.moveToThread(thread)

        worker.sig_data.connect(self.on_click_data_received)

        self.sig_abort_workers.connect(worker.abort)

        thread.started.connect(worker.grabData)
        thread.start()
        self.__threads.append((thread, worker)) 



    def clickMethod(self):

        self.spinner.start()

        self.search = self.line.text()
        print('searching "' + self.search + '"...')

        idx = 'clickMethod'
        worker = Worker(idx, self.search)
        thread = QThread()
        thread.setObjectName('thread_' + idx)
        self.__threads.append((thread, worker)) 
        worker.moveToThread(thread)

        worker.sig_data.connect(self.on_click_data_received)

        self.sig_abort_workers.connect(worker.abort)

        thread.started.connect(worker.grabData)
        thread.start()  


    @pyqtSlot(dict)
    def on_click_data_received(self, data):

        self.data = data

        search_term = self.search

        if len(self.history['data']) == 0:
            title_box = 'Trending Stories'
        elif len(search_term) > 25:
            title_box = 'results: "' + search_term[:22] + '..."'
        else:
            title_box = 'results: "' + search_term + '"'

        if len(self.history['data']) > 0:
            for b in self.inactive_buttons:
                b.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")
                b.setCursor(Qt.PointingHandCursor)

        self.history['data'].append(self.data)
        self.history['title_boxes'].append(title_box)
        self.history['urls'].append(self.data['playlist_url'])
        self.history['page_numbers'].append(1)

        self.populate()
        groupbox = QGroupBox(title_box)
        groupbox.setLayout(self.myform)
        groupbox.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+";font-style: italic")
        self.scroll.setWidget(groupbox)
        self.spinner.stop()


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

        number_of_pages = math.ceil(self.data['total_videos']/NUM_RESULTS)

        if number_of_pages > 1:

            current_page = self.history['page_numbers'][-1]
            pages = []

            if current_page <= 3 or number_of_pages <= 5:
                page_range=['<']
                page_range.extend([i for i in range(1,number_of_pages+1)])
                page_range.append('>')

            else:
                page_range = ['<',1]
                if number_of_pages - current_page < 3: 
                    page_range.extend([i for i in range(number_of_pages-3, number_of_pages+1)])
                else:
                    page_range.extend([i+current_page-1 for i in range(4)])
                page_range.append('>')

            for i in page_range:
                active = (i!=current_page) and not (i=='<' and current_page==1) and not (i=='>' and current_page==number_of_pages)
                page = PageLabel(i, active)
                page.page_clicked.connect(self.get_next_page)
                pages.append(page)

            layout = QHBoxLayout()
            for p in pages:
                layout.addWidget(p)
            page_selector = QWidget()
            page_selector.setLayout(layout)
            form.addRow(QLabel('Pages: '), page_selector)

        self.myform = form
        

    def exit_seq(self):
        sys.exit()


    def on_video_clicked(self):

        label = self.sender()
        self.url = label.url
        self.player.play(self.url)


    def on_download_clicked(self):

        label = self.sender()

        idx = label.title
        worker = Worker(idx, label.url, label=self.download_label)
        thread = QThread()
        thread.setObjectName('thread_' + idx)
        self.__threads.append((thread, worker))  # need to store worker too otherwise will be gc'd
        worker.moveToThread(thread)

        worker.sig_msg.connect(self.on_download_complete)

        self.sig_abort_workers.connect(worker.abort)

        # get read to start worker:
        thread.started.connect(worker.download)
        thread.start()  # this will emit 'started' and start thread's event loop

    @pyqtSlot(str)
    def on_download_complete(self, title):

        title_short = title[:20]

        vid_path = [DOWNLOAD_LOCATION + file for file in os.listdir(DOWNLOAD_LOCATION) if file.startswith(title)][0]

        self.downloaded_videos['short_titles'].append(title_short)
        self.downloaded_videos['paths'].append(vid_path)

        self.download_label.setText(str(len(self.downloaded_videos['paths'])) + ' downloads')
        self.download_label.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; font-family: "+FONT+";")

        self.download_selector.insertItem(0,title_short, vid_path)
        self.download_selector.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; font-family: "+FONT+";")
        self.download_selector.setCurrentIndex(0)

        self.play_downloaded_button.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")
        self.play_downloaded_button.setCursor(Qt.PointingHandCursor)



    def on_home_clicked(self):

        if not (HOME_URL in self.history['urls'][-1] and self.history['page_numbers'][-1] == 1):
            print('loading homepage...')
            self.search = ''
            self.data=self.history['data'][0]
            self.history['data'].append(self.data)
            self.history['title_boxes'].append('Trending Stories')
            self.history['urls'].append(self.data['playlist_url'])
            self.history['page_numbers'].append(1)
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
            #self.search = ''
            self.history['urls'].pop(-1)
            self.history['page_numbers'].pop(-1)
            self.history['data'].pop(-1)
            self.data = self.history['data'][-1]
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
            elif HOME_URL not in self.history['urls'][-1]:
                self.home_button.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")
                self.home_button.setCursor(Qt.PointingHandCursor)
            else:
                self.home_button.setStyleSheet("color: "+INACTIVE_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+INACTIVE_COLOR+"; font-family: "+FONT+";")                
                self.home_button.setCursor(Qt.ArrowCursor)
        else:
            print('could not go back')


    def on_play_downloaded(self):

        if len(self.downloaded_videos['paths']) > 0:
            self.player.play(self.download_to_play)

        else:
            print('no videos downloaded yet')


    def select_download(self, index):

        print('queued ' + self.download_selector.itemData(index))
        self.download_to_play = self.download_selector.itemData(index)


    def get_next_page(self):

        self.spinner.start()

        search_term = self.search

        try:
            sender = self.sender()
            if sender.page == '<':
                next_page_number = self.history['page_numbers'][-1] - 1
            elif sender.page == '>':
                next_page_number = self.history['page_numbers'][-1] + 1
            else:
                next_page_number = sender.page

        except:
            next_page_number = self.history['page_numbers'][-1] + 1

        self.history['page_numbers'].append(next_page_number)

        url = self.history['urls'][-1]
        self.history['urls'].append(url)
        title_box = re.sub(r' page \d+$', '', self.history['title_boxes'][-1])
        if next_page_number > 1:
            title_box = title_box[:29] + ' page ' + str(next_page_number)

        self.history['title_boxes'].append(title_box)

        data_limits = [NUM_RESULTS * (next_page_number - 1), NUM_RESULTS * next_page_number ]
        
        idx = 'get_next_page'
        worker = Worker(idx, url, search=False, limit=data_limits)
        thread = QThread()
        thread.setObjectName('thread_' + idx)
        self.__threads.append((thread, worker)) 
        worker.moveToThread(thread)

        worker.sig_data.connect(self.on_next_page_received)

        self.sig_abort_workers.connect(worker.abort)

        thread.started.connect(worker.grabData)
        thread.start()  

    @pyqtSlot(dict)
    def on_next_page_received(self, data):

        search_term = self.search

        self.data = data

        self.history['data'].append(self.data)

        for b in self.inactive_buttons:
            b.setStyleSheet("color: "+FOREGROUND_COLOR+"; background-color: "+BACKGROUND_COLOR+"; border: 1px solid "+FOREGROUND_COLOR+"; font-family: "+FONT+";")
            b.setCursor(Qt.PointingHandCursor)

        self.populate()

        groupbox = QGroupBox(self.history['title_boxes'][-1])
        groupbox.setLayout(self.myform)
        groupbox.setStyleSheet("color: "+FOREGROUND_COLOR+"; font-family: "+FONT+";font-style: italic")
        self.scroll.setWidget(groupbox)
        self.spinner.stop()

    @pyqtSlot()
    def abort_workers(self):
        self.sig_abort_workers.emit()
        for thread, worker in self.__threads:  # note nice unpacking by Python, avoids indexing
            thread.quit()  # this will quit **as soon as thread event loop unblocks**
            thread.wait()  # <- so you need to wait for it to *actually* quit

        # even though threads have exited, there may still be messages on the main thread's
        # queue (messages that threads emitted before the abort):
        self.log.append('All threads exited')

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
