class FakeDevHandle(object):
    def __init__(self):
        self.data = []
    def controlRead(self, a, b, c, d, l):
        if not self.data:
            d = b"MOCK"
        else:
            d = self.data[0]
            self.data = self.data[1:]
        return d
    def bulkWrite(self, a, b):
        if not self.data:
            d = b"MOCK"
            raise Exception()
        else:
            d = self.data[0]
            self.data = self.data[1:]
        return d
    def bulkRead(self, infnum, l):
        if not self.data:
            d = b"MOCK"
            raise Exception()
        else:
            d = self.data[0]
            self.data = self.data[1:]
        return d

    def close(self):
        pass
    def addData(self, *datas):
        self.data += datas


class FakeDev(object):
    def open(self):
        return FakeDevHandle()
