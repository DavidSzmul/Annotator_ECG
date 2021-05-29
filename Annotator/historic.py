from collections import deque

class Historic(object):
    # Class enabling to register changes and possibly cancel previous changes 
    def __init__(self, data_init, max_len=10):
        self._hist = deque(maxlen=max_len)
        self._hist.append(data_init.copy())
        self._ctr = 0

    def get_previous(self):
        self._ctr = max(0, self._ctr-1)
        return self._hist[self._ctr]

    def get_next(self):
        self._ctr = min(len(self._hist)-1, self._ctr+1)
        return self._hist[self._ctr]

    def get_current(self):
        return self._hist[self._ctr]

    def new_change(self, data):
        # Remove if change during previous state
        for i in range(self._ctr,len(self._hist)-1):
                self._hist.pop()
        self._hist.append(data.copy())            
        self._ctr = min(len(self._hist)-1, self._ctr+1)

if __name__=='__main__':
    init_state = 0
    Hist = Historic(init_state, max_len=4)

    # Add Recent
    for i in range(5):
        Hist.new_change(i)
        print(Hist._hist)
    print(Hist.get_current())

    # Get Previous
    print(Hist.get_previous())
    print(Hist.get_previous())
    print(Hist.get_previous())
    print(Hist.get_previous())
    print(Hist.get_previous())
    print(Hist.get_previous())
    print(Hist.get_previous())
    print(Hist.get_next())
    # Change during previous    
    Hist.new_change(12)
    print(Hist._hist)
    print(Hist.get_previous())