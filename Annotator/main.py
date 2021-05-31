import numpy as np
import os, sys

# from collections import deque
import scipy.io as sio
from scipy import signal
import pathlib
import gc
from threading import Timer,Thread,Event

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkFont
from tkinter import Menu
from tkinter.filedialog import askopenfilename
from tkinter import messagebox as mb
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.backends.backend_tkagg as  backend_tkagg
from PIL import ImageTk ,Image

from historic import Historic
from annotation import *
from dialogBox import DialogBox

def display_cardiac_events(ax, cardiac_Events, t_end):
    ax.patches = []
    ax.texts = []

    ### cardiac events
    for i in range(len(cardiac_Events)):
        name_event = cardiac_Events[i][1]
        color_rec, color_text = EventColor(name_event)
        if i<len(cardiac_Events)-1:
            rect = patches.Rectangle((cardiac_Events[i][0],0),cardiac_Events[i+1][0]-cardiac_Events[i][0],1,linewidth=1,edgecolor=color_rec,facecolor=color_rec)
        else:
            rect = patches.Rectangle((cardiac_Events[i][0],0),t_end-cardiac_Events[i][0],1,linewidth=1,edgecolor=color_rec,facecolor=color_rec)
        ax.add_patch(rect)
        ax.text(cardiac_Events[i][0]+0.5, 0.4, name_event, color=color_text, fontsize=12)


class CardiacEventMover(object):
    def __init__(self, parent, ax, ax2, cardiac_Events_init, t_end):
        self.parent = parent
        self.ax = ax
        self.ax2 = ax2
        self.figcanvas = self.ax.figure.canvas
        self.figcanvas2 = self.ax2.figure.canvas
        self.cardiac_events = cardiac_Events_init
        self.t_end = t_end
        display_cardiac_events(self.ax, self.cardiac_events, self.t_end)

        # Parameters
        self.delta_min_cardiac = 0.5 # In s
        self.moved = None
        self.point = None
        self.pressed = False
        self.index_event = None
        self.figcanvas.mpl_connect('button_press_event', self.mouse_press)
        self.figcanvas.mpl_connect('button_release_event', self.mouse_release)
        self.figcanvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.figcanvas2.mpl_connect('button_press_event', self.mouse_press)
        self.figcanvas2.mpl_connect('button_release_event', self.mouse_release)
        self.figcanvas2.mpl_connect('motion_notify_event', self.mouse_move)
        self.start = False

    def update_CardEv_from_display(self):
        # Cardiac Events from Patches
        time = [p.xy[0] for p in self.ax.patches]
        cardiac =[t._text for t in self.ax.texts]
        self.cardiac_events = [list(tuple_card) for tuple_card in zip(time, cardiac)]
        self.parent._cardiac_Events = self.cardiac_events
        return

    def get_time_events(self):
        return [p.xy[0] for p in self.ax.patches]

    def mouse_release(self, event):
        if self.ax.get_navigate_mode()!= None: return
        if not event.inaxes: return
        if (event.inaxes != self.ax and event.inaxes != self.ax2): return
        if self.pressed:
            self.pressed = False
            self.start = False
            print('Released')            
            if (event.xdata - self.point):
                # Use timer threading in order to wait a minimum of time 
                # before deactivating led (otherwise user might not see the change)
                def deactivate_led(this):
                    this.parent.led_moving.configure(bg="gray")
                Timer(1.5,deactivate_led, args=(self,)).start() # 1second delay
                
                self.update_CardEv_from_display()
                print(self.cardiac_events)
                self.parent.historic_event.new_change(self.cardiac_events)
            self.point = None
            return

    def mouse_press(self, event):
        if self.ax.get_navigate_mode()!= None: return
        if not event.inaxes: return
        if (event.inaxes != self.ax and event.inaxes != self.ax2): return
        if self.start: return

        self.point = event.xdata
        if event.button==3: # Right Click
            print('Right Click')
            try:
                self.parent.m.tk_popup(self.parent.winfo_pointerx(), self.parent.winfo_pointery())
            finally:
                self.parent.m.grab_release()
            return
        
        if len(self.get_time_events())<2: # return because not possible to drag
            return
        self.point = event.xdata
        self.pressed = True
        self.index_event = np.argmin(np.abs(np.array(self.get_time_events())-self.point))
        if self.index_event==0:
            self.index_event=1

        self.x_init = self.ax.patches[self.index_event]._x0
        self.width_init = self.ax.patches[self.index_event]._width
        self.widthP_init = self.ax.patches[self.index_event-1]._width
        self.xt_init = self.ax.texts[self.index_event]._x       
        print('Pressed. Chosen X: '+str(self.x_init)+'. Index Event: '+str(self.index_event))

    def mouse_move(self, event):
        if self.ax.get_navigate_mode()!= None: return
        if not event.inaxes: return
        if (event.inaxes != self.ax and event.inaxes != self.ax2): return
        if not self.pressed: return

        self.start = True
        delta_x = event.xdata - self.point
        self.parent.led_moving.configure(bg="red")

        # Need to ensure that drag does not move more than previous or next event --> delta_min_cardiac
        if (self.widthP_init + delta_x > self.delta_min_cardiac and
            self.width_init - delta_x > self.delta_min_cardiac):
            self.ax.patches[self.index_event]._x0 = self.x_init + delta_x
            self.ax.patches[self.index_event]._width = self.width_init - delta_x
            self.ax.patches[self.index_event-1]._width = self.widthP_init + delta_x
            self.ax.texts[self.index_event]._x = self.xt_init + delta_x
            self.figcanvas.draw()
            print('Width '+str(self.width_init - delta_x))

class DisplayECGApp(tk.Tk):
    
    def __init__(self, *args, **kwargs):
        # Init Legacy
        tk.Tk.__init__(self, *args, **kwargs)
        tk.Tk.wm_title(self, "Display ECG")
        self.iconbitmap('img/icone.ico')

        self.state("zoomed")
        self.container = tk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frame = None
        self.set_new_frame()

        self.bind('<Escape>', self.quit_app)
        self.protocol("WM_DELETE_WINDOW", lambda e=None: self.quit_app(e))

    def quit_app(self, event):
        # Ask for last save before quitting signal
        response = mb.askyesnocancel(title='Quit', 
            message='You are going to quit application.\nDo you want to save changes before quitting ?')
        if response is None: #Cancel
            return
        if response: #Save Before
            save_Annot(self.frame.file_save, self.frame._cardiac_Events)
            mb.showinfo('Save', self.frame.file_save+'\nSAVED')

        # Real quit or New Signal
        response = mb.askyesno(title='New Study or Quit', 
            message='Do you want to study another patient ?')
        if response in [None, False]: #Cancel
            self.quit()
            return
        self.set_new_frame()
        
    def set_new_frame(self):
        if self.frame is not None:
            self.frame.destroy()
        data_Sig, cardiac_Events, file_save = self.study_new_signal()
        self.frame = MainPage(self.container, self, data_Sig=data_Sig, cardiac_Events=cardiac_Events, file_save=file_save)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.tkraise()

    def study_new_signal(self):
        ### File to open
        path_init = str(pathlib.Path().absolute()) #+ "/Events_Annot_Dr"
        root = tk.Tk()
        root.withdraw()
        file_mat = askopenfilename(title = "Select Patient", initialdir=path_init,filetypes = [("MAT files","*.mat")]) # show an "Open" dialog box and return the path to the selected file
        root.destroy()
        if file_mat=='':
            return False

        ### Determine IN/OUT
        path, name_mat = os.path.split(file_mat)
        file_annot = os.path.join(path, 'Annotation', name_mat[:-4]+'_Annot.mat')

        ### Get Annotations
        try:
            cardiac_Events = load_Annot(file_annot)
            data_Sig = sio.loadmat(file_mat)
            data_Sig['name_in']=name_mat
            return data_Sig, cardiac_Events, file_annot
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            mb.showerror(title='Error', message=str(e))
            root.destroy()
            quit()

class MainPage(tk.Frame):
    def __init__(self, parent, controller, data_Sig=None, cardiac_Events=None, file_save=None):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.data_Sig = data_Sig
        self.current_part = 1
        self.nb_parts = data_Sig['nb_parts'][0][0]
        self.Fs = data_Sig['Fs'][0][0]
        self.gain_mV = data_Sig['Factor_mV'][0][0]
        self._cardiac_Events = cardiac_Events
        self.historic_event = Historic(self._cardiac_Events, max_len=20)
        self.all_Events = ['Sinus Rhythm', 'AF', 'SVT', 'VT', 'VF', 'SHOCK', 'NOISE']
        self.file_save=file_save
        #########################################
        #### TOOLBAR LEFT
        #########################################
        # Init Frame for indication
        self.ind_frame = tk.Frame(master=self)
        self.ind_frame.pack(side=tk.LEFT, fill=tk.Y)
        # Init Image
        img_obj = Image.open("img/icone.png")
        img_obj = img_obj.resize((193, 75), Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(img_obj)
        self.lab = tk.Label(self.ind_frame, image=self.img)
        
        # Init Shortcut indication
        message_shortcut =  'Shortcuts : \n\
    \'r\':          home (reset view)\n\
    \'o\':          zoom\n\
    \'p\':          pan\n\
    \'left\':       previous zoom\n\
    \'right\':      next zoom\n\n\
    \'ctrl+z\':     cancel modif\n\
    \'ctrl+y\':     uncancel modif\n\
    \'ctrl+left\':  Part +1\n\
    \'ctrl+right\': Part -1\n\n\
When no icon selected:\n\
    \'right click\': add/modify/remove event\n\
    \'drag mouse\':  move closest event\n\n\
    \'escape\':     Exit\
    '
        self.text_shortcut = tk.Message(self.ind_frame, text=message_shortcut)
        # Init Change Part Plot
        self.text_part = tk.Message(self.ind_frame, text='Part '+str(self.current_part), width=100,
                font=("Courier", 16))
        self.ctr_part_frame = tk.Frame(master=self.ind_frame)

        Name_Btn_ctr = {'+': 'plus_ctr_btn', '-': 'minus_ctr_btn'}
        def update_ctr(event):
            if (hasattr(event, 'widget') and event.widget._name==Name_Btn_ctr['+'] or 
                    hasattr(event, 'key') and event.key=='ctrl+right'):
                self.current_part=min(self.current_part+1,self.nb_parts)

            elif (hasattr(event, 'widget') and event.widget._name==Name_Btn_ctr['-'] or 
                    hasattr(event, 'key') and event.key=='ctrl+left'):
                self.current_part=max(self.current_part-1,1)
            self.text_part.configure(text='Part '+str(self.current_part))
            self.reset_display()
            return

        self.button_ctrM = tk.Button(self.ctr_part_frame,name=Name_Btn_ctr['-'], text='-1',command=None, width=10,font=("Courier", 12))
        self.button_ctrP = tk.Button(self.ctr_part_frame,name=Name_Btn_ctr['+'], text='+1',command=None, width=10,font=("Courier", 12))
        self.button_ctrM.pack(side=tk.LEFT, padx=5,pady=5)
        self.button_ctrP.pack(side=tk.LEFT, padx=5,pady=5)
        self.button_ctrM.bind("<ButtonPress-1>", update_ctr)
        self.button_ctrP.bind("<ButtonPress-1>", update_ctr)

        # Save Button
        self.button_save = tk.Button(self.ind_frame,text='Save Event',command=None, width=20, font=("Courier", 12, "bold"))
        def save_fcn(event):
            save_Annot(self.file_save, self._cardiac_Events)
            mb.showinfo('Save', self.file_save+'\nSAVED')
        self.button_save.bind("<ButtonPress-1>", save_fcn)

        # Add Led to inform user of modifications
        self.led_moving = tk.Label(self.ind_frame, text="Event Moving", bg="gray", font=("Courier", 16))

        # Package
        self.lab.pack(padx=5,pady=5)
        self.text_shortcut.pack(padx=5,pady=5)
        self.text_part.pack(padx=5,pady=5)
        self.ctr_part_frame.pack(padx=5,pady=5)
        self.button_save.pack(padx=5,pady=40)
        self.led_moving.pack(padx=5,pady=5)

        #########################################
        #### DISPLAY 
        #########################################
        ### Init Display
        NB_SP = 2
        self.fig, self.ax = plt.subplots(nrows=NB_SP, ncols=1, sharex = 'all', gridspec_kw={'height_ratios': [3, 1]})
        self.fig.subplots_adjust(left=0.075, bottom=0.08, right=0.95, top=0.95, wspace=0, hspace=0.05)
        self.canvas = backend_tkagg.FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, expand=True) #, fill=tk.BOTH
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Init Toolbar from Matplotlib
        self.toolbar=backend_tkagg.NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.fig._toolbar = self.toolbar
        self.toolbar.pack(side=tk.LEFT,fill=tk.X)
        self.canvas.draw()
        
        # Init
        self.ax[0].set_xlabel("Time (s)")
        self.ax[0].set_ylabel("mV")
        self.ax[1].axes.get_yaxis().set_visible(False)
        self.ax[0].grid() 
        self.title_ax_start = 'Patient : '+self.data_Sig['name_in'][:-4]+' Part '
        self.reset_display()        

        self.m = Menu(self, tearoff=0)
        self.m.add_command(label="Add", command=self.add_cardiac)
        self.m.add_command(label="Modify", command=self.modify_cardiac)
        self.m.add_command(label="Delete", command=self.delete_cardiac)

        # Add Historic connection
        def key_pressed(event):
            if event.key=='ctrl+z':
                self.previous_cardiac()
            elif event.key=='ctrl+y':
                self.next_cardiac()
            elif event.key in ['ctrl+left', 'ctrl+right']:
                update_ctr(event)
        self.fig.canvas.mpl_connect('key_press_event', key_pressed)


    def adapt_signal_2_plot(self, data_Sig):
        
        SIZE_MAX_PART = 1e6
        t_offset_per_part = SIZE_MAX_PART/self.Fs

        val = data_Sig['val']
        t = np.arange(0,(len(val[0]))/self.Fs,1/self.Fs, dtype = np.float32) + (self.current_part-1)*t_offset_per_part

        delta_offset = -2
        raw_sig = np.zeros((len(val), len(val[0]))) #, dtype=np.int16
        for i in range(len(raw_sig)):
            raw_sig[i,:] = val[i,:]/self.gain_mV  + delta_offset*(i-1)  
        return t, raw_sig

    def reset_display(self, keep_margins=False):

        if keep_margins:
            marginx = self.fig.axes[0].get_xlim()
            marginy = self.fig.axes[0].get_ylim()
        else:
            self.toolbar.update() # In order to avoid problem using 'reset view' when changing part

        # Remove previous plot
        for i in range(len(self.fig.axes)):
            self.fig.axes[i].lines=[]
        self.ax = self.fig.axes

        ### Adapt Dipslay
        t, raw_sig = self.adapt_signal_2_plot(self.data_Sig)
        n_sample = 2
        color = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        for i in range(len(raw_sig)):
            self.ax[0].plot(t[::n_sample],raw_sig[i,::n_sample],color=color[i], linewidth=1.1)
        self.ax[0].set_xlim([t[0], t[-1]])
        self.ax[0].set_title(self.title_ax_start+str(self.current_part)+'/'+str(self.nb_parts))

        self.cardiac_Obj = CardiacEventMover(self, self.ax[1],self.ax[0], self._cardiac_Events, t[-1])

        if keep_margins:
            self.fig.axes[0].set_xlim(marginx)
            self.fig.axes[0].set_ylim(marginy)
        self.fig.canvas.draw()

    def add_cardiac(self):
        print('Add')
        app = DialogBox(self.parent, self.all_Events ,"Select the cardiac event:          ",
                position=(self.winfo_pointerx(),self.winfo_pointery()), 
                icone='img/icone.ico'
                )
        self.parent.wait_window(app)
        new_event = app.get_response()
        ### Return in case of canceling
        if new_event == '': return

        ### Find where to insert the new event
        time_events = [c[0] for c in self._cardiac_Events]
        indx_add = np.nonzero(time_events <= self.cardiac_Obj.point)
        indx_add = indx_add[0].item(-1)+1
        self._cardiac_Events.insert(indx_add, [self.cardiac_Obj.point, new_event])
        print(self._cardiac_Events)
        self.historic_event.new_change(self._cardiac_Events)
        self.reset_display(keep_margins=True)

    def modify_cardiac(self):
        print('Modify')
        time_events = [c[0] for c in self._cardiac_Events]
        indx_modify = np.nonzero(time_events <= self.cardiac_Obj.point)
        indx_modify = indx_modify[0].item(-1)

        app = DialogBox(self.parent, self.all_Events ,"Select the cardiac event:          ",
                position=(self.winfo_pointerx(),self.winfo_pointery()),
                icone='img/icone.ico'
        )
        self.parent.wait_window(app)

        modify_event = app.get_response()
        ### Return in case of canceling
        if modify_event == '': return
        self._cardiac_Events[indx_modify][1] = modify_event
        print(self._cardiac_Events)
        self.historic_event.new_change(self._cardiac_Events)
        self.reset_display(keep_margins=True)

    def delete_cardiac(self):
        print('Delete')
        ### At least one registered Event
        if len(self._cardiac_Events)==1: return

        ### Find where to delete the closest event
        time_events = [c[0] for c in self._cardiac_Events]
        indx_delete = np.nonzero(time_events <= self.cardiac_Obj.point)
        indx_delete = indx_delete[0].item(-1)
        self._cardiac_Events.pop(indx_delete)

        ### Change time event if the 1rst one was deleted
        if indx_delete == 0:
            self._cardiac_Events[0][0] = 0
        print(self._cardiac_Events)
        self.historic_event.new_change(self._cardiac_Events)
        self.reset_display(keep_margins=True)

    def previous_cardiac(self):
        print('set previous modification')
        # In case of retractation from user
        self._cardiac_Events = self.historic_event.get_previous()
        self.reset_display(keep_margins=True)

    def next_cardiac(self):
        print('set next modification')
        # In case of retractation from user
        self._cardiac_Events = self.historic_event.get_next()
        self.reset_display(keep_margins=True)


if __name__=='__main__':
    app = DisplayECGApp()
    app.mainloop()
