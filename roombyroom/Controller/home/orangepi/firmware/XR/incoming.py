class StringTable:

    def __init__(self):
        self._table = bytearray()
        self.count=0

    def getCount(self):
        return self.count
    
    def checkRange(self,idx):
        if idx>=self.getCount():
            raise IndexException(f'Index {idx} out of range')

    def get(self,idx):
        self.checkRange(idx)
        if idx>=self.getCount():
            raise IndexException(f'Index {idx} out of range')
        ptr=0
        for n in range(idx):
            ptr=ptr+1+self._table[ptr]
        stop=ptr+1+self._table[ptr]
        return self._table[ptr+1:stop].decode()

    def add(self,data):
        ptr=0
        for n in range(self.getCount()):
            ptr=ptr+1+self._table[ptr]
        size=len(self._table)
        b = data.encode()
        l=len(b)
        if ptr+l+1>size:
            print(f'+{ptr+l+1-size}')
            for n in range(ptr+l+1-size):
                self._table.append(0)
        self._table[ptr]=l
        self._table[ptr+1:ptr+1+l]=b
        self.count+=1
        return self.count

    def delete(self,idx):
        self.checkRange(idx)
        self.count-=1
        if idx<self.getCount():
            # Find the item
            ptr=0
            for n in range(idx):
                ptr=ptr+1+self._table[ptr]
            stop=ptr+1+self._table[ptr]
            tail=self._table[stop:len(self._table)]
            self._table[ptr:ptr+len(tail)]=tail

    def replace(self,idx,data):
        self.checkRange(idx)
        self.delete(idx)
        self.add(data)

class Devices:

    def __init__(self):
        self.table=StringTable()

    def getCount(self):
        return self.table.getCount()

    def addDevice(self,data):
        self.table.add(data)

    def getElement(self,idx):
        return self.table.get(idx)

    def getDevice(self,name):
        for idx in range(self.getCount()):
            data=self.table.get(idx).split(':')
            if data[0]==name:
                return data[1]
        return None

    def replace(self,name,data):
        for idx in range(self.getCount()):
            item=self.table.get(idx).split(':')
            if item[0]==name:
                self.table.replace(idx,data)
                return
        self.addDevice(data)

    def toString(self):
        v=''
        for n in range(self.getCount()):
            if n>0:
                v=f'{v}|'
            v=f'{v}{self.getElement(n)}'
        return v
