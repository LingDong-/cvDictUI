import cv2
import numpy as np

import os
import csv

KEY_UP = [0,91]
KEY_DOWN = [1,93]
KEY_RETURN = [13]
KEY_ESCAPE = [27]
KEY_BACKSPACE = [8,127]

MODE_VIEW = 0
MODE_ENTRY = 1
CV_FONT_WIDTH = 10

INT_STRING = "01234567890-"
FLOAT_STRING = "01234567890.-"
STR_STRING = "".join([chr(i) for i in range(33,127)])

THEME_DEFAULT = ((255,255,255),(0,0,0),(50,50,50))
THEME_NOTEBOOK = ((50,50,50),(240,245,250),(255,255,255))
THEME_DARK = ((200,200,100),(60,40,20),(70,80,70))
THEME_CONTRAST = ((255,255,0),(255,0,0),(0,0,255))
THEME_YELLOW = ((0,0,0),(230,230,230),(0,255,255))
THEME_HOTPINK = ((250,250,250),(10,10,10),(200,0,200))
THEME_SIMPLE = ((0,0,0),(255,255,255),(250,220,189))

def getDictEntryByPath(dict_obj,pth):
    sel = dict_obj
    for p in pth:
        sel = sel[p]
    return sel

def setDictEntryByPath(dict_obj,pth,val):
    sel = dict_obj
    for p in pth[:-1]:
        sel = sel[p]
    sel[pth[-1]] = val


def simulateKeystroke(keyname):
    os.system("""osascript -e ' tell application "System Events" to keystroke """
                +'"'+keyname+'"'+" ' ")

class UINode():
    def __init__(self,**kwargs):
        self.path = ""
        self.text = ""
        self.prefix = ""
        self.level = 0
        self.hide = False
        self.isHidden = False
        self.isLeaf = False
        self.render = lambda x: str(x)
        self.typ = None
        for x in kwargs:
            setattr(self,x,kwargs[x])
        if not self.isLeaf:
            r = self.render
            self.render = lambda x: (" [+] " if self.hide else " [-] ") + r(x)


class UIHier():
    def __init__(self,dict_obj):
        self.data = UIHier.makeHier(dict_obj)
        self.visible_length = len(self.data)
        self.x_unit = 10
        self.y_unit = 20
        self.color = (255,255,0)

    @staticmethod
    def makeHier(obj):
        def _pprint(obj,indent=0,path=[],connects=[]):
            prims = [int, float, str, unicode, bool, type(None)]
            result = []
            pfx = ""
            for i in range(indent):
                pfx += (" "*4+[" ","|"][connects[i]]+" "*2)
            pfx += (" "*4+"L"+"-"*2)+"> "
            def p_prim(x):
                render = lambda x: str(x)
                if type(x) in [bool]:
                    render = lambda x: ["[ ]","[X]"][int(x)]
                elif type(x) in [int, float]:
                    render = lambda x: "["+str(x)+"]"
                elif type(x) in [unicode, str]:
                    render = lambda x: "["+str(x)+"]"
                return UINode(path=path,val=x,prefix=pfx,level=indent,isLeaf=True,typ=type(x),render=render)

            if type(obj) in prims:
                result.append(p_prim(obj))
            elif type(obj) in [list]:
                for i in range(len(obj)):
                    result+=_pprint(obj[i],indent=indent,path=path+[i],connects=connects+[1])
            elif type(obj) in [dict]:
                okeys = obj.keys()
                for i in range(len(okeys)):
                    k = okeys[i]
                    def closure():
                        typstr = "("+str(type(obj[k])).split("'")[1]+")"
                        return lambda x: str(x).upper()+" "+typstr
                    render = closure()
                    result.append(UINode(path=path,val=k,prefix=pfx,level=indent,render=render))
                    result+=_pprint(obj[k],indent=indent+1,path=path+[str(k)],connects=connects+[i!=len(okeys)-1])
            else:
                print("ERR:",type(obj),obj)
            return result
        return _pprint(obj)

    def update(self, dict_obj):
        for i in range(len(self.data)):
            got = getDictEntryByPath(dict_obj,self.data[i].path)
            if type(got) not in [dict, list]:
                self.data[i].val = got


    def get(self,idx):
        return self.data[idx]

    def hide(self,idx):
        if self.data[idx].isLeaf:
            return
        self.data[idx].hide = True
        lvl0 = self.data[idx].level
        for i in range(idx+1,len(self.data)):
            if self.data[i].level > lvl0:
                self.data[i].isHidden = True
            else:
                break
        self.visible_length = self.calc_vislen()

    def unhide(self,idx):
        if self.data[idx].isLeaf:
            return
        self.data[idx].hide = False
        lvl0 = self.data[idx].level
        for i in range(idx+1,len(self.data)):
            if self.data[i].level > lvl0:
                self.data[i].isHidden = False
                if not self.data[i].isLeaf:
                    self.data[i].hide = False
            else:
                break
        self.visible_length = self.calc_vislen()

    def calc_vislen(self):
        return len([x for x in self.data if not x.isHidden])


    def proj(self,idx):
        cnt = 0
        for i in range(0,len(self.data)):
            if not self.data[i].isHidden:
                cnt += 1
            if cnt-1 == idx:
                return i
        return None

    def unproj(self,idx):
        cnt = 0
        for i in range(0,idx):
            if not self.data[i].isHidden:
                cnt += 1
        return cnt

    def draw(self,im,xy=(0,0)):
        dx = self.x_unit
        dy = self.y_unit
        yof = xy[1]
        for i in range(len(self.data)):
            if not self.data[i].isHidden:
                yof += dy
                xof = xy[0]
                pfx,val,rend = self.data[i].prefix, self.data[i].val, self.data[i].render
                for s in pfx:
                    if s == ' ':
                        pass
                    elif s == '|':
                        cv2.line(im,(xof,yof-dy),(xof,yof),color=self.color)
                    elif s == '-':
                        cv2.line(im,(xof,yof), (xof+dx,yof), color=self.color)
                    elif s == 'L':
                        cv2.line(im,(xof,yof-dy), (xof,yof), color=self.color)
                        cv2.line(im,(xof,yof), (xof+dx,yof), color=self.color)
                    elif s == ">":
                        cv2.line(im,(xof,yof), (xof+dx//2,yof), color=self.color)
                        cv2.line(im,(xof+dx//2,yof), (xof,yof-dx//2), color=self.color)
                        cv2.line(im,(xof+dx//2,yof), (xof,yof+dx//2), color=self.color)
                    xof += dx

                cv2.putText(im, rend(val), (xof,yof),
                        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=0.5,
                        thickness=1,
                        color=self.color)

class DictUI():
    def __init__(self, name, dict_obj, position=(0,0), meta_file=None):
        self.data = dict_obj
        self.name = name
        self.hier = UIHier(self.data)
        self.canv = np.zeros((self.hier.y_unit*30,600,3),np.uint8)
        self.yoff = 0
        self.highlight = 0
        self.mode = MODE_VIEW
        self.drag = (-1,-1)
        self.mouse = (-1,-1)
        self.show = True
        self.setColors()

        cv2.namedWindow(self.name,cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.name,self.mouse_event)
        cv2.moveWindow(self.name,position[0],position[1])
       

        self.hidden_canv = np.zeros((50,self.canv.shape[1],3),np.uint8)
        cv2.putText(self.hidden_canv, "Press [G] to Toggle GUI", (10,25),
                        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=0.5,
                        thickness=1,
                        color=self.hier.color)

        if meta_file is not None:
            pass

    def setColors(self,fg=(255,255,255),bg=(0,0,0),hl=(50,50,50)):
        self.hier.color = fg
        self.color_background = bg
        self.color_highlight = hl

    def mouse_event(self,event,x,y,flags,param):
        self.mouse = (x,y)
        if self.mode == MODE_VIEW:
            if event == cv2.EVENT_LBUTTONUP:

                d = y-self.drag[1]
                self.drag = (-1,-1)

                if abs(d) > self.hier.y_unit:
                    self.yoff += d
                    return

                idx = self.hier.proj(self.highlight)
                if idx is None:
                    return
                if self.hier.get(idx).isLeaf:
                    newval = self.hier.get(idx).val
                    if self.hier.get(idx).typ in [bool]:
                        newval = not self.hier.get(idx).val
                    else:
                        ret = self.entry_mode(idx)
                        print(ret)
                        simulateKeystroke('a')
                        if ret is not None:
                            newval = ret

                    setDictEntryByPath(self.data,self.hier.get(idx).path, newval)
                    self.hier.update(self.data)
                else:
                    if self.hier.get(idx).hide == False:
                        self.hier.hide(idx)
                    else:
                        self.hier.unhide(idx)
            elif event == cv2.EVENT_MOUSEMOVE:
                self.highlight = (y-self.yoff)//self.hier.y_unit

            elif event == cv2.EVENT_LBUTTONDOWN:
                self.drag = (x,y)

        elif self.mode == MODE_ENTRY:
            if event == cv2.EVENT_LBUTTONUP:
                self.mode = MODE_VIEW

    def entry_mode(self,idx):
        print(idx, self.hier.get(idx).path)
        oldmode = self.mode
        self.mode = MODE_ENTRY

        result = ""
        while True:
            if self.mode != MODE_ENTRY:
                return None
            try:
                #self.hier.get(idx).val = self.hier.get(idx).typ(result)
                self.hier.get(idx).val = result
            except:
                self.hier.get(idx).val = "   "

            self.canv[:] = self.color_background
            self.drawHier()

            h,w,_ = self.canv.shape
            sh = 5
            csy = (self.hier.unproj(idx)+1)*self.hier.y_unit+self.yoff
            csx = len(self.hier.get(idx).prefix)*self.hier.x_unit
            csxr = csx+(len(str(self.hier.get(idx).val))+2)*CV_FONT_WIDTH
            self.canv[csy-self.hier.y_unit+sh:csy+sh,csx:csxr]=255-\
            self.canv[csy-self.hier.y_unit+sh:csy+sh,csx:csxr]

            cv2.imshow(self.name, self.canv)

            key = cv2.waitKey(1) & 0xFF 
            if key in KEY_ESCAPE:
                result = None
                break
            elif key in KEY_RETURN:
                break
            elif key in KEY_BACKSPACE:
                result = result[:-1]
            elif (self.hier.get(idx).typ == int and chr(key) in INT_STRING) or \
                 (self.hier.get(idx).typ == float and chr(key) in FLOAT_STRING) or \
                 (self.hier.get(idx).typ in [str,unicode] and chr(key) in STR_STRING):
                result += chr(key)

        self.mode = oldmode

        if result is None: return result
        try:
            return self.hier.get(idx).typ(result)
        except:
            return None

    def drawHier(self):
        d = self.mouse[1]-self.drag[1] if self.drag[0] != -1 else 0

        self.hier.draw(self.canv,(0,self.yoff+d))

    def drawHighlight(self):
        csy = (self.highlight+1)*self.hier.y_unit+self.yoff
        self.canv[csy-self.hier.y_unit+5:csy+5]=self.color_highlight      
        
    def drawScrollbar(self):
        h,w,_ = self.canv.shape
        vis_len = self.hier.visible_length
        d = self.mouse[1]-self.drag[1] if self.drag[0] != -1 else 0

        p = max(1,vis_len)*self.hier.y_unit
        p0 = float(-self.yoff-d)/p
        p1 = float(-self.yoff-d+self.canv.shape[0])/p
        i0 = int(p0*h)
        i1 = int(p1*h)
        #cv2.rectangle(self.canv,(w-10,0),(w,h),color=self.hier.color,thickness=1)
        cv2.rectangle(self.canv,(w-8,i0),(w-2,i1),color=self.hier.color,thickness=1)


    def update(self, key):
        if key == ord('g'):
            self.show = not self.show
        if not self.show:
            cv2.imshow(self.name, self.hidden_canv)
            return True

        self.canv[:] = self.color_background
        if self.drag[0] == -1:
            self.drawHighlight()
        else:
            pass
            #cv2.arrowedLine(self.canv,self.drag,self.mouse,color=(200,200,200),thickness=1)

        self.drawHier()
        self.drawScrollbar()
    
        cv2.imshow(self.name, self.canv)

        if key == ord('q'):
            return False
        elif key in KEY_UP:

            self.yoff += self.hier.y_unit
        elif key in KEY_DOWN:
            
            self.yoff -= self.hier.y_unit
        
        vis_len = self.hier.visible_length
        self.yoff = min(max(self.yoff,-(vis_len+1)*self.hier.y_unit+self.canv.shape[0]),0)

        return True

    def kill(self):
        cv2.destroyWindow(self.name)

if __name__ == "__main__":
    def demo1():
        dict_obj = {u'control': {u'affirmation_speed': 0.004, u'identity_threshold': 1.0, u'charge_max': 50, 
            u'discharge_max': 100}, u'log': {u'timer': False}, u'language': u'es', u'camera': {u'resolution': 480, 
            u'orientation': 90, u'deviceID': 0}, u'label': {u'candidate_name': {u'height': 100}, u'info_text': {u'height': 100}}, 
            u'tile': {u'progress_bar': {u'color': [100, 100, 200], u'width': 5}, u'label_height': 140, u'min_alpha': 0.2, 
            u'upsample': 2, u'margin': {u'column': 120, u'border': 300, u'row': 20}, u'background_color': [255, 255, 255], 
            u'display': {u'rewind': 0.1, u'zoom': 1, u'height': 1144, u'width': 1080, u'follow': 0.1, u'focus_frames': 100, 
            u'zoom_static': 0.025}, u'columns': 8}, u'window': {u'width': 1080, u'margin': {u'horizontal': 50, u'vertical': 30}, 
            u'height': 1920}, u'tracker': {u'disappoint_max': 30, u'detect_downsample': 0.5, u'algorithms': {u'HOG:default': False, 
            u'haar:default': False, u'haar:alt2': False, u'haar:alt': False, u'HOG:nearest': True}, u'display': {u'debug': True, 
            u'width': 467, u'follow': 0.1, u'zoom': 0.25, u'height': 676}}, u'debug': {u'camera': False, u'fps': True, 
            u'progress_bar': True}}
        ui = DictUI('panel',dict_obj)
        ui.setColors(*THEME_SIMPLE)
        while True:
            key = cv2.waitKey(1) & 0xFF
            if not ui.update(key):
                break
        ui.kill()
    
    def demo2():
        dict_obj = {'color':[0,0,255],"radius":50,"outline":True}
        ui = DictUI('panel',dict_obj)
        ui.setColors(*THEME_SIMPLE)

        while True:
            key = cv2.waitKey(1) & 0xFF

            im = np.zeros((256,256,3),np.uint8)
            cv2.circle(im,(128,128),dict_obj["radius"],color=tuple(dict_obj["color"]),thickness=dict_obj["outline"]*11-1)
            cv2.imshow("app",im)
            

            if not ui.update(key):
                break
        ui.kill()

    demo1()
    demo2()
