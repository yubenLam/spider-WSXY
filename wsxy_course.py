class Course:
    """ id          课程ID
        name        课程名称
        progress    课程进度
        detail_code 详情页id
    """

    def __init__(self, id, name, progress, detail_id, subject_id):
        self.id = id
        self.name = name
        self.progress = progress
        self.detail_id = detail_id
        self.subject_id = subject_id

        self.rco_list = None

    def setRcoList(self, rco_list):
        self.rco_list = rco_list

    def prn_obj(self):
        print('{\n\t', end='')
        print('\n\t'.join(['%s:%s' % item for item in self.__dict__.items()]))
        print('}')
