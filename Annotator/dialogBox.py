import tkinter as tk
import tkinter.ttk as ttk

class DialogBox(tk.Toplevel):

    val = []
    def __init__(self, parent, choicelist, text, position=(0, 0), icone=None):

        tk.Toplevel.__init__(self, parent)
        self.update_idletasks()
        self.geometry('+{}+{}'.format(position[0], position[1]))

        if icone is not None:
            self.iconbitmap(icone)

        self.parent = parent
        self.label = tk.Label(self, text=text).grid(row=0, column=0, sticky="W")

        self.var = tk.StringVar()
        self.var.set('') # default option
        self.popupMenu = ttk.Combobox(self, textvariable=self.var,
                                    values=choicelist,
                                    state='readonly')
        self.popupMenu.grid(sticky=tk.N + tk.S + tk.E + tk.W, row=1, column=0)
        self.popupMenu.bind('<<ComboboxSelected>>', self._select_choice)
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", lambda :self._cancel_choice())

    def _cancel_choice(self):
        self.var.set('')
        self.destroy()

    def _select_choice(self,event):
        self.destroy()

    def get_response(self):
        return self.var.get()

if __name__=='__main__':
    ICONE = 'img/icone.ico'
    CHOICE_LIST = ['hello', 'world', 'what a great day', '!!!']
    
    # Example of Main window
    root = tk.Tk()
    txt = tk.Text(root)#, state='disabled'

    def make_Choice():
        app=DialogBox(root, CHOICE_LIST, "Select your choice           ",
            position=(root.winfo_pointerx(),root.winfo_pointery()),
            icone=ICONE
        )
        root.wait_window(app)
        txt.delete(1.0,"end")
        txt.insert(1.0, app.get_response())

    button_choice = tk.Button(root,text='Make Choice', width=20, 
        command = make_Choice
    )

    button_choice.pack()
    txt.pack()

    root.mainloop()