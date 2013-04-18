#encoding=utf-8
import base64
import datetime
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.escape
from tornado.options import define, options
import logging
import json
import re
import urlparse

define("port", default=18000, help="run on the given port", type = int)
DISPLAY_TOTAL_NUM = 120
DISPLAY_COUNT_PERPAGE = 30
SEASON_MAP = {'01' : '1', '02' : '1', '03' : '1', '04' : '2', '05' : '2', '06' : '2', '07' : '3', '08' : '3', '09' : '3', '10' : '4', '11' : '4', '12' : '4'}
UI_MAP = {'1' : u'一', '2' : u'二', '3' : u'三', '4' : u'四'}
pattern = re.compile('/statistic/(.*)')

class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)
        self.logout_url = '/statistic/logout'
    
    def check_authority(self):
        auth_cookie = self.get_cookie('auth')
        if auth_cookie == None:
            self.set_cookie('auth', 'bad_cookie')
            self.set_header("WWW-Authenticate",'Basic realm="Please input your account and password."')
            self.set_status(401)
        else:
            global pattern
            _type = re.match(pattern, self.request.uri.split('?')[0]).groups()[0]
            user = self.application.config["auth"][_type]
            is_cookie = False
            try:
                is_cookie = self._check_authorization(user, auth_cookie)
            except: pass
            if is_cookie == True:
                return True
            else:
                if "Authorization" in self.request.headers:
                    if self._check_authorization(user, self.request.headers["Authorization"][6:]):
                        self.set_cookie('auth', self.request.headers["Authorization"][6:])
                        return True
                    else:
                        self.set_header("WWW-Authenticate",'Basic realm="Please input your account and password."')
                        self.set_status(401)
                else:
                    self.set_header("WWW-Authenticate",'Basic realm="Please input your account and password."')
                    self.set_status(401)

    def _check_authorization(self, user, auth):
        ret = False
        userinfo = base64.decodestring(auth)
        account = userinfo.split(':')[0]
        passwd = userinfo.split(':')[1]
        if account in user and passwd == user[account]:
            return True
        return ret

class DailyBaseHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        BaseHandler.__init__(self, *args, **kwargs)
        self.table_header = \
    r'''
        <table align = "center" border = "1px" width = "800px" cellpadding = "0" cellspacing = "0">
            <tbody text align = "center">
                <tr>
                    <th width = "50%%">日期</th>
                    <th width = "50%%">新增用户</th>
                </tr>
    '''
        self.html1_first_page = \
    r'''
    <html>
        <head>
            <meta http-equiv = "content-type" content = "text/html; charset = UTF-8">
        </head>
        <body>
            <table align = "center" border = "0px" width = "800px" cellpadding = "0" cellspacing = "0">
                <tr>
                    <th align = "left"><a href="%s">退出</a></th>
                    <th align = "right"><a href="%s">下一页</a></th>
                </tr>
            </table>
    '''
        self.html1_middle = \
    r'''
    <html>
        <head>
            <meta http-equiv = "content-type" content = "text/html; charset = UTF-8">
        </head>
        <body>
            <table align = "center" border = "0px" width = "800px" cellpadding = "0" cellspacing = "0">
                <tr>
                    <th align = "left"><a href="%s">退出</a></th>
                    <th align = "right"><a href="%s">上一页</a><a href="%s">下一页</a></th>
                </tr>
            </table>
        
    '''
        self.html1_last_page = \
    r'''
    <html>
        <head>
            <meta http-equiv = "content-type" content = "text/html; charset = UTF-8">
        </head>
        <body>
            <table align = "center" border = "0px" width = "800px" cellpadding = "0" cellspacing = "0">
                <tr>
                    <th align = "left"><a href="%s">退出</a></th>
                    <th align = "right"><a href="%s">上一页</a></th>
                </tr>
            </table>
        
    '''
        self.html2 = \
    r'''
                </tbody>
            </table>
        </body>
    </html>
    '''
        self.pattern = \
    r'''
    <tr>
        <td>%s</td>
        <td>%s</td>
    </tr>
    '''

    def get(self):
        if self.check_authority() == True:
            page_num = int(self.get_argument('page', u'1'))
            f_r = open(self.data_path, "r")
            self.data_list = []
            #total_len = DISPLAY_TOTAL_NUM
            total_len = (datetime.date.today() - datetime.date(2012, 11, 30)).days 
            total_pages = total_len/DISPLAY_COUNT_PERPAGE if (total_len % DISPLAY_COUNT_PERPAGE) == 0 else total_len/DISPLAY_COUNT_PERPAGE + 1
            for i in xrange(total_len):
                self.data_list.append(f_r.readline())
            print 'total pages, total_length: ', total_pages, total_len
            if page_num > total_pages:
                raise tornado.web.HTTPError(400)
            self._show_content(total_pages, total_len, page_num)
            f_r.close()

    def _show_content(self, total_pages, total_len, page_num):
        if page_num == 1:
            head = (self.html1_first_page + self.table_header) % (self.logout_url, self.address + '?page=' + str(page_num + 1))
        elif page_num == total_pages:
            head = (self.html1_last_page + self.table_header) % (self.logout_url, self.address + '?page=' + str(page_num - 1))
        else:
            _last, _next = str(page_num - 1), str(page_num + 1)
            head = (self.html1_middle + self.table_header) % (self.logout_url, self.address + '?page=' + _last, self.address + '?page=' + _next)
        self.write(head) 
        begin, end = ((page_num - 1) * DISPLAY_COUNT_PERPAGE, page_num * DISPLAY_COUNT_PERPAGE - 1)
        data_list = [self.data_list[i] for i in xrange(total_len) if i >= begin and i <= end]
        print 'length of data_list: ', len(data_list), begin, end
        for i in data_list:
            if len(i) == 0: continue
            args = json.loads(i.strip())
            self.write(self.pattern % tuple(args[0:2]))
        self.write(self.html2)
    
class SeasonBaseHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        BaseHandler.__init__(self, *args, **kwargs)
        self.html1 = \
    r'''
        <table align = "center" border = "0px" width = "800px" cellpadding = "0" cellspacing = "0">
            <tr>
                <th align = "left"><a href="%s">退出</a></th>
            </tr>
        </table>
        <table align = "center" border = "1px" width = "800px" cellpadding = "0" cellspacing = "0">
            <tbody text align = "center">
                <tr>
                    <th width = "50%%">季度</th>
                    <th width = "50%%">新增用户</th>
                </tr>
    '''
        self.html2 = \
    r'''
                </tbody>
            </table>
        </body>
    </html>
    '''
        self.pattern = \
    r'''
    <tr>
        <td>%s</td>
        <td>%s</td>
    </tr>
    '''

    def get(self):
        if self.check_authority() == True:
            season_dict = {}
            f_r = open(self.data_path, "r")
            first_line = f_r.readline() 
            if first_line:
                first_line = json.loads(first_line.strip())
                s_pattern = self.get_season_pattern(first_line[0]) 
                for line in f_r:
                    line = json.loads(line.strip())
                    match = None
                    if len(s_pattern) == 2:
                        match = re.match(s_pattern[1], line[0])
                    if not match:
                        match = re.match(s_pattern[0], line[0])  
                    if match:
                        y, m = match.groups() 
                        s = SEASON_MAP[m]
                        if y not in season_dict:
                            season_dict[y] = {}
                        if s not in season_dict[y]:
                            season_dict[y][s] = 0
                        season_dict[y][s] += int(line[1]) 
            output = []
            for k, v in season_dict.items():
                for k_s, v_s in v.items():
                    output.append([u"%s年第%s季度" % (k, UI_MAP[k_s]), unicode(v_s), int(k + k_s)]) 
            output.sort(key = lambda x: x[2], reverse=True)
            self.write(self.html1 % self.logout_url)
            for i in output:
                self.write(self.pattern % (i[0], i[1]))
            self.write(self.html2)

    def get_season_pattern(self, s_day):
        recent_year, recent_mon = re.match('(201[2-9])-([01][0-9])-\d{2}', s_day).groups()        
        season = SEASON_MAP[recent_mon]
        a = str(int(recent_year[3]) - 1) 
        ret = []
        ret.append('(201[1-%s])-([01][0-9])-\d{2}' % a)
        if season == '2':
            ret.append('(%s)-(0[1-3])-\d{2}' % recent_year)
        elif season == '3':    
            ret.append('(%s)-(0[1-6])-\d{2}' % recent_year)
        elif season == '4':
            ret.append('(%s)-(0[1-9])-\d{2}' % recent_year)
        return ret

class LoginHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)

    def check_authority(self):
        auth_cookie = self.get_cookie('auth')
        if auth_cookie == None:
            self.set_cookie('auth', 'bad_cookie')
            self.set_header("WWW-Authenticate",'Basic realm="Please input your account and password."')
            self.set_status(401)
        else:
            user = self.application.config["auth"]
            is_cookie = False
            try:
                is_cookie = self._check_authorization(user, auth_cookie)
            except: pass
            if is_cookie == True:
                return True
            else:
                if "Authorization" in self.request.headers:
                    if self._check_authorization(user, self.request.headers["Authorization"][6:]):
                        self.set_cookie('auth', self.request.headers["Authorization"][6:])
                        return True
                    else:
                        self.set_header("WWW-Authenticate",'Basic realm="Please input your account and password."')
                        self.set_status(401)
                else:
                    self.set_header("WWW-Authenticate",'Basic realm="Please input your account and password."')
                    self.set_status(401)

    def _check_authorization(self, user, auth):
        ret = False
        userinfo = base64.decodestring(auth)
        account = userinfo.split(':')[0]
        passwd = userinfo.split(':')[1]
        for k, v in user.items():
            if account in v and passwd == v[account]:
                self.type = k
                ret = True
        return ret
                        
    def get(self):
        if self.check_authority() == True:
            url = '/statistic/' + self.type 
            self.redirect(url)

class LogoutHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        tornado.web.RequestHandler.__init__(self, *args, **kwargs)
        self.login_address = '<a href="%s">登录</a>' % '/statistic/login' 
    
    def get(self):
        self.clear_cookie('auth')
        self.write('Logout success.\n')
        self.write('Login address: %s' % self.login_address)

class AndroidMarketHandler(DailyBaseHandler):
    def __init__(self, *args, **kwargs):
        DailyBaseHandler.__init__(self, *args, **kwargs)
        self.address = '/statistic/android_market' 
        self.data_path = self.application.android_market 

class NinetyOneHandler(DailyBaseHandler):
    def __init__(self, *args, **kwargs):
        DailyBaseHandler.__init__(self, *args, **kwargs)
        self.address = '/statistic/91' 
        self.data_path = self.application.ninety_one 

class UCHandler(DailyBaseHandler):
    def __init__(self, *args, **kwargs):
        DailyBaseHandler.__init__(self, *args, **kwargs)
        self.address = '/statistic/UC' 
        self.data_path = self.application.uc 

class SeasonAndroidMarketHandler(SeasonBaseHandler):
    def __init__(self, *args, **kwargs):
        SeasonBaseHandler.__init__(self, *args, **kwargs)
        self.data_path = self.application.android_market 
        
class SeasonNinetyOneHandler(SeasonBaseHandler):
    def __init__(self, *args, **kwargs):
        SeasonBaseHandler.__init__(self, *args, **kwargs)
        self.data_path = self.application.ninety_one

class SeasonUCHandler(SeasonBaseHandler):
    def __init__(self, *args, **kwargs):
        SeasonBaseHandler.__init__(self, *args, **kwargs)
        self.data_path = self.application.uc

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/statistic/login", LoginHandler),
            (r"/statistic/logout", LogoutHandler),
            (r"/statistic/android_market", AndroidMarketHandler),
            (r"/statistic/91", NinetyOneHandler),
            (r"/statistic/UC", UCHandler),
            (r"/statistic/season/android_market", SeasonAndroidMarketHandler),
            (r"/statistic/season/91", SeasonNinetyOneHandler),
            (r"/statistic/season/UC", SeasonUCHandler),
        ]
        tornado.web.Application.__init__(self, handlers)
        self.config = {}
        execfile("config", self.config)
        self.android_market = "data.txt"
        self.ninety_one = "data1.txt"
        self.uc = "data2.txt"

def main():
    tornado.options.parse_command_line()
    logging.getLogger().setLevel(logging.DEBUG)
    io_loop = tornado.ioloop.IOLoop.instance()
    http_server = tornado.httpserver.HTTPServer(Application(), io_loop = io_loop, xheaders=True)
    http_server.listen(options.port)
    io_loop.start()

if __name__ == '__main__':
    main()
