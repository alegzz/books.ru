import requests, urllib
from requests.adapters import HTTPAdapter
from sys import exit
import argparse
from bs4 import BeautifulSoup
import re
#import shutil
from datetime import datetime

MB = 1024 * 1024
MAINURL = 'https://www.books.ru/'

def parseArgs():
    urlPattern = r'https://(www\.)?books\.ru/((member/download_agreement\.php\?back_url=)|(order\.php\?order=))'

    parser = argparse.ArgumentParser(description='Books.ru downloader')
    parser.add_argument('-s', '--skip-first', type=int, default=0, help='Skip first N books from order (default 0)', dest='skip')
    parser.add_argument('-r', '--retries', type=int, default=1, help='How many times (default 1)', dest='retries')
    
    parser.add_argument('username', action="store", help="username for books.ru")
    parser.add_argument('password', action="store", help="password for books.ru")
    parser.add_argument('url', action="store", help="url to book")
    
    args = parser.parse_args()

    if re.match(urlPattern, args.url.lower()) == None:
        print('Invalid url')        
        return None
    
    return args

def getFilename(s):
    fname = re.findall("filename\*=([^;]+)", s, flags=re.IGNORECASE)
    if not fname:
        fname = re.findall("filename=([^;]+)", s, flags=re.IGNORECASE)
    if "utf-8''" in fname[0].lower():
        fname = re.sub("utf-8''", '', fname[0], flags=re.IGNORECASE)
        fname = urllib.unquote(fname).decode('utf8')
    else:
        fname = fname[0]
    return fname.strip().strip('"')

def getbook(s, url):
    data = {'agreed' : 'Y',
            'go' : "1"  
            }
    
    r = s.post(url, data = data, stream = True)
    
    filename = getFilename(r.headers['content-disposition'])
    size = 0
    chunk_size = 8192
    start_dl = datetime.now()
    padding = 0
    
    print('Downloading {} ...'.format(filename))
    
    with open(filename, 'wb') as book:
        for chunk in r.iter_content(chunk_size = chunk_size):
            if chunk:  # filter out keep-alive new chunks
                book.write(chunk)
                size += chunk_size
                if size // MB < 1:
                    size_string = '{} kB'.format(size)
                elif size // MB >= 1:
                    size_string = '{:.2f} MB'.format(size / MB)
            
                timedelta = (datetime.now() - start_dl).seconds
                
                if timedelta == 0:
                    timedelta = 1
                                
                speed = (size / 1024) / timedelta
            
                if speed // MB < 1:
                    speed_string = '{:.2f} kB/s'.format(speed)
                elif speed // MB >= 1:
                    speed_string = '{:.2f} MB/s'.format(speed / 1024)
                    
                s = 'Downloaded {} with speed {}'.format(size_string, speed_string)
                
                padding = max(padding, len(s))
                
                print('{:{width}}'.format(s, width = str(padding)), end='\r')
        book.close()
        if padding > 0:
            print()

def login(s, username, password):
    loginurl = 'https://www.books.ru/member/login.php'
    data = {'login' : username,
            'password' : password,
            'go': 'login',
            }
    r = s.post(loginurl, data = data)

    if 'неверный пароль' in r.text:
        return 'Incorrect login or password'

    if r.status_code != 200:
        return 'Server return error, error code: {}'.format(r.status_code)

    return None

def initSession(retries):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0',
        #'Referer': 'Referer: https://www.books.ru/order.php?order=2121041',
        #'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        #'accept-encoding': 'gzip, deflate, br',
        #'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    s = requests.Session()
    
    s.mount('https://', HTTPAdapter(max_retries=retries))

    #s.hooks = {
    #    'response': lambda r, *args, **kwargs: r.raise_for_status()
    #    }
    
    s.headers.update(headers)
    s.params.update({'timeout': 30})
    
    return s

def getbooks(s, url, skip):
    r = s.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    
    links = []
    
    for a in soup.find_all('a', href=True, class_='pdf'):
        links.append(MAINURL + a['href'])
    
    l = len(links)
    
    for i in range(skip, l):
        print('Downloading {} of {}'.format(i + 1, l))
        getbook(s, links[i])

config = parseArgs()

if config == None:
    exit(1)

s = initSession(config.retries)

r = login(s, config.username, config.password)

if r:
    print(r)
    exit(1)

if '/member/' in config.url: 
    r = getbook(s, config.url)
else:
    getbooks(s, config.url, config.skip)
