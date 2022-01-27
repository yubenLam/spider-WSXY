class Attempt:
    """存储播放记录的类，用于发送播放和保存请求。

    Attributes:
        id: 记录id
        subject_id: 专题id
        course_id: 课程id
        rco_id: 视频id
        token: 验证token
    """

    def __init__(self, id, subject_id, course_id, rco_id, token):
        self.id = id
        self.subject_id = subject_id
        self.course_id = course_id
        self.rco_id = rco_id
        self.token = token  # 验证token

        self.sessionTime = "00.00.00"  # 播放时长
        self.rawStatus = "C"
        self.credit = "no-credit"
        self.terminalType = "PC"

    def setToken(self, token):
        self.token = token

    def setSessionTime(self, sessionTime):
        self.sessionTime = sessionTime

    def prn_obj(self):
        print('{\n\t', end='')
        print('\n\t'.join(['%s:%s' % item for item in self.__dict__.items()]))
        print('}')
