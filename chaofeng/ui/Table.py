import chaofeng.ascii as ac
from baseui import BaseUI

__metaclass__ = type

class SimpleTable(BaseUI):

    def __init__(self, start_line=0, page_limit=20):
        self.start_line = start_line
        self.page_limit = page_limit

    def init(self, data, format ,default=0):
        self.data = data
        self.format = format
        self.hover = self.start = -1
        h = default % self.page_limit
        s = default - h
        self._goto(h, s)

    def fetch(self):
        return self.data[self.hover]

    def _goto(self, start, hover):
        if start == self.start :
            hover = max(0,min(hover,self.max))
            if hover == self.hover :
                return
            self.hover = hover
            self.refresh_cursor()
            return
        # hover = which % self.page_limit
        # start = which - hover
        buf = map(self.format,
                  self.data[start:start+self.page_limit])
        maxo = len(buf)
        if maxo == 0 :
            return
        self.buf = buf
        self.hover = hover
        self.start = start
        self.max = maxo
        if maxo < self.page_limit:
            buf.extend(['']*(self.page_limit-maxo))
        return True
    
    def restore(self):
        self.frame.write(ac.move2(self.start_line, 1)+ac.kill_line)
        self.frame.write(('\r\n'+ac.kill_line).join(self.buf))
        self.refresh_cursor()

    def refresh_cursor(self):
        if self.hover < 0 : self.hover = 0
        if self.hover+1 > self.max : self.hover = self.max - 1
        self.frame.write(ac.movex_d + ' ' +
                         ac.move2(self.start_line + self.hover, 1) + '>')

    def move_down(self):
        if self.hover+1 >= self.max:
            self._goto(self.start+self.page_limit, 0) and self.restore()
        else:
            self.hover += 1
            self.refresh_cursor()

    def move_up(self):
        if self.hover <= 0:
            self._goto(self.start-self.page_limit, self.page_limit -1) and self.restore()
        else:
            self.hover -= 1
            self.refresh_cursor()

    def page_up(self):
        self._goto(self.start-self.page_limit, self.hover) and self.restore()

    def page_down(self):
        self._goto(self.start+self.page_limit, self.hover) and self.restore()

    def goto(self, which):
        h = which % self.page_limit
        s = which - h
        self._goto(s, h) and self.restore()

    def goto_first(self):
        self._goto(0,0) and self.restore()
        
class AppendTable(BaseUI):

    def __init__(self, key, start_line=0, page_limit=20):
        self.start_line = start_line
        self.page_limit = page_limit
        self.key = key

    def init(self, get_data, format):
        self.get_data = get_data
        self.format = format
        self.data = []
        self.max = 0
        
    def fetch(self):
        return self.data[self.hover]

    def get_page_upper(self):
        return self.data[self.max-1][self.key]

    def get_page_lower(self):
        return self.data[0][self.key]

    def load_with_upper(self, upper):
        if upper <= 0 :
            return
        data = self.get_data(upper, -self.page_limit)
        hover = len(data)
        if hover > 0 :
            self.hover = hover
            if hover < self.page_limit:
                data += self.data[:self.page_limit - hover]
                hover = len(data)
            self.max = hover
            self.data = data
            return True

    def load_with_lower(self, lower):
        data = self.get_data(lower, self.page_limit)
        hover = len(data)
        if hover > 0 :
            self.data = data
            self.max = hover
            self.hover = 0
            return True

    def goto(self, which):
        self.load_with_lower(which)
        self.restore()

    def refresh_cursor(self):
        if self.hover < 0 : self.hover = 0
        if self.hover+1 >= self.max : self.hover = self.max - 1
        self.frame.write(ac.movex_d + ' ' +
                         ac.move2(self.start_line + self.hover, 1) + '>')

    def restore(self):
        buf = map(self.format,self.data)
        if self.max == 0 :
            return
        if self.max < self.page_limit:
            buf.extend(['']*(self.page_limit-self.max))
        self.frame.write(ac.move2(self.start_line, 1)+ac.kill_line)
        self.frame.write(('\r\n'+ac.kill_line).join(buf))
        self.refresh_cursor()

    def move_up(self):
        if self.hover-1 < 0:
            self.load_with_upper(self.get_page_lower()-1) and self.restore()
        else:
            self.hover -= 1
            self.refresh_cursor()

    def move_down(self):
        if self.hover+1 >= self.max:
            self.load_with_lower(self.get_page_upper()+1) and self.restore()
        else:
            self.hover += 1
            self.refresh_cursor()

    def page_up(self):
        h = self.hover
        if self.load_with_uppder(self.get_page_lower()+1):
            self.hover = h
            self.restore()

    def page_down(self):
        h = self.hover
        if self.load_with_lower(self.get_page_upper()+1):
            self.hover = h
            self.restore()

    key_maps = {
        ac.k_up : "move_up",
        ac.k_down : "move_down",
        ac.k_page_down : "page_down",
        ac.k_page_up : "page_up",
        ac.k_home : "go_first",
        }
    
    def send(self,data):
        if data in self.key_maps :
            getattr(self,self.key_maps[data])()

    def go_first(self):
        self.goto(0)

# class DataLoader:

#     def __init__(self,get_raw,format, get_upper):
#         self.get_raw = get_raw
#         self.format = format
#         self.get_upper = get_upper
        
#     def fix_range(self,x):
#         upper = self.get_upper()-1
#         return min(upper,max(0,x))

#     def get(self, start, limit):
#         self.raw_data = self.get_raw(start, limit)
#         data = map(self.format,
#                    self.raw_data)
#         l = len(data)
#         if l < limit:
#             data.extend(['']*(limit-l))
#         return data

#     def item(self,key):
#         return self.raw_data[key]

class ModeAppendTable(AppendTable):

    def init(self, *data_loader):
        self.data_loader = data_loader

    def set_mode(self, mode):
        super(ModeAppendTable, self).init(*self.data_loader[mode])

