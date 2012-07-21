from baseui import BaseUI
import chaofeng.ascii as ac
from chaofeng import sleep
from eventlet import spawn as lanuch
from itertools import cycle

class BaseTextBox(BaseUI):
    pass

class Animation(BaseTextBox):

    '''
    Call back self.frame.play_done wher playone is True.
    '''

    def init(self, data, start_line, pause=None, callback=None):
        self.data = data
        self.len = len(self.data)
        self.start_line = start_line
        self.pause = pause
        self.callback = callback

    def write(self, data):
        self.frame.write(''.join((ac.save,
                                  ac.move2(self.start_line, 1),
                                  data,
                                  ac.restore)))
        
    def prepare(self, playone=False):
        if playone:
            self.gener = iter(self.data)
        else:
            self.gener = cycle(self.data)
            
    def clear(self):
        if hasattr(self,'thread') :
            self.thread.kill()

    def go_one(self):
        while True:
            try:
                data, time = self.gener.next()
            except StopIteration:
                data = None
            if data is None:
                self.callback()
                return
            self.write(data)
            if time is True:
                self.pause()
            elif time is False:
                self.callback()
                return
            else:
                sleep(time)

    def run(self, playone=False):
        self.prepare(playone)
        while True :
            self.go_one()

    def launch(self, playone=False):
        self.thread = lanuch(self.run, playone)

class LongTextBox(BaseTextBox):

    '''
    Widget for view long text.
    When user try move_up in first line, callback(False)
    will be called, and callback(True) will be when
    move_down in last lin.
    '''

    def init(self, text, callback, height=23):
        self.h = height
        self.reset(text)
        self.callback = callback
        
    def set_text(self,text):
        self.buf = text.splitlines()
        self.s = 0
        self.len = len(self.buf)
        self.max = max(0,self.len - self.h)

    reset = set_text

    def getscreen(self):
        return '\r\n'.join(self.getlines(self.s, self.s+self.h))

    def getscreen_with_raw(self):
        buf = self.getlines(self.s, self.s+self.h)
        return ('\r\n'.join(buf), buf)
        
    def getlines(self,f,t):
        if t > self.len :
            return self.buf[f:t]+['~',]*(t-self.len)
        else:
            return self.buf[f:t]

    def set_start(self,start):
        if start == self.s:
            return
        if (self.s > start) and (self.s <= start + 10):
            offset = self.s - start
            self.write(ac.move0 + ac.insertn(offset) + '\r')
            self.write('\r\n'.join(self.getlines(start,self.s)))
            self.s = start
        elif (start > self.s) and (start <= self.s + 10):
            astart = self.s + self.h # Append Start
            self.write(ac.move2(self.h+1,0))
            self.write(ac.kill_line)
            self.write('\r\n'.join(self.getlines(astart, start + self.h)))
            self.write('\r\n')
            self.s = start
        else :
            self.s = start
            self.refresh_all()

    def move_up(self):
        if self.s :
            self.set_start(self.s-1)
        else:
            self.callback(False)
            
    def move_down(self):
        if self.s + self.h < self.len:
            self.set_start(self.s+1)
        else:
            self.callback(True)

    def go_line(self,num):
        if self.s == 0 and num < 0 :
            self.callback(True)
        if self.s == self.max and num > 0:
            self.callback(False)
        self.set_start(max(0,min(num,self.len-self.h)))
        
    def go_first(self):
        self.go_line(0)

    def go_last(self):
        self.go_line(self.len-self.h)

    def page_down(self):
        self.go_line(self.s - self.h)

    def page_up(self):
        self.go_line(self.s + self.h)

    def refresh_all(self):
        self.write(ac.move0 + ac.clear)
        self.write(self.getscreen())
        
    def write(self,data):
        self.frame.write(data)

class BaseBuffer(BaseUI):

    '''
    Loader is a function that like loader(start_line, limit),
    which will load [start_line:start_line+limit]

    @vis_height : the visable height line in screen
    @current    : current lines buffer display in screen
    @bufstr     : current text in screen
    
    '''

    seq_lines = '\r\n'+ac.kill_line
    empty_line = seq_lines

    def init(self):
        raise Exception('Cannot instance a basebuffer')

    def init_buf(self, loader, start_num, start_line, page_limit=20):
        '''
        Init the buf. It should be called before everything.
        '''
        self.start_line = start_line
        self.page_limit = page_limit
        self.loader = loader
        self.set_page_start(start_num)

    def fetch(self):
        return self.current

    def get_screen(self):
        return ''.join((ac.move2(self.start_line, 1),
                        self.seq_lines.join(self.current),
                        self.empty_line*(self.page_limit-self.vis_height)))

    def restore_screen(self):
        self.frame.write(self.bufstr)

    def set_page_start(self, start_num):
        '''
        Set the start_num as the first display line in the screen.
        If start_num<0 , it'wll display 0 as first line.
        If can't fetch any line, return False else return True.
        '''
        if start_num < 0 : start_num = 0
        current = self.loader(start_num, self.page_limit)
        if current :
            self.start_num = start_num
            self.vis_height = len(current)
            self.current = current
            self.bufstr = self.get_screen()
            return True
        else : return False
        
    def set_page_start_lazy_iter(self, start_num):
        if start_num < 0 : start_num = 0
        if start_num == self.start_num:
            return True
        if self.set_page_start(start_num) :
            self.restore_screen()
            return True
        else : return False

    def restore_screen(self):
        '''
        Restore the buffer, display it in screen.
        Notice that it will not reload the data, it just
        print the buffer's cache in buffstr.
        '''
        self.frame.write(ac.move2(self.start_line, 1) + ac.kill_line + \
                              ('\r\n'+ac.kill_line).join(self.current))

    def page_prev_iter(self):
        '''
        Set previous page as display. Return True while has at least one line,
        or return False while cannot fetch any things.
        '''
        return self.set_page_start_lazy_iter(self.start_num - self.page_limit)

    def page_next_iter(self):
        '''
        Set the next page as display. Return True while has fetch something,
        or return Flase whie it's out of range.
        '''
        return self.set_page_start_lazy_iter(self.start_num + self.page_limit)

    def go_first_iter(self):
        return self.set_page_start_lazy_iter(0)

class PagedTable(BaseBuffer):

    def init(self, loader, formater, start_num, start_line, page_limit=20):
        self.reset_loader(loader, formater)
        self.init_buf(self.get_wrapper, start_num, start_line, page_limit)
        self.hover = -1
        self.reset_cursor(start_num % page_limit)

    def reset_loader(self, loader, formater):
        self.table_loader = loader
        self.formater = formater

    def get_wrapper(self, start, limit):
        self.tabledata = self.table_loader(start, limit)
        return map(self.formater, self.tabledata)

    def reset_cursor(self, hover):
        if hover < 0 : hover = 0
        if hover < self.vis_height :
            self.hover = hover
            return True
        else : return False

    def restore_cursor(self):
        self.frame.write(ac.move2(self.start_line + self.hover, 1)
                         + '>')

    def reset_cursor_iter(self, hover):
        if self.reset_cursor(hover):
            self.frame.write(ac.movex_d + ' ' + ac.move2(self.start_line + self.hover, 1)
                             + '>')

    def restore_screen(self):
        super(PagedTable, self).restore_screen()
        self.restore_cursor()

    def page_prev_iter(self):
        super(PagedTable, self).page_prev_iter() and\
            (self.hover >= self.vis_height) and \
            self.reset_cursor_iter(self.vis_height-1)

    def page_next_iter(self):
        if super(PagedTable, self).page_next() :
            self.reset_cursor_iter(min(self.hover, self.vis_height-1))
        else:
            self.reset_cursor_iter(self.vis_height)

    def move_up_iter(self):
        if self.hover < 0 :
            self.hover = 0
        elif self.hover > 0:
            self.reset_cursor_iter(self.hover-1)

    def move_down_iter(self):
        if self.hover+1 <= self.vis_height :
            self.reset_cursor_iter(self.hover + 1)
        else:
            super(PagedTable, self).page_next_iter() and\
                self.reset_cursor_iter(0)

    def goto_iter(self, num):
        s, h = divmod(num, self.vis_height)
        self.set_page_start_iter(s) and\
            self.reset_cursor_iter(h)
