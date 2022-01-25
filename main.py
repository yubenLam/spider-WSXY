import requests
import time
import threading
import math
import random

from wsxy_course import Course
from wsxy_attempt import Attempt

# 自行更改必要信息
HOST = "http://wsxy.chinaunicom.cn"
subject_id = 49658011
headers_init = {
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Accept': 'application/json, text/plain, */*',
    'Cache-Control': 'no-cache',
    'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
cookies_init = {
    'XSRF-TOKEN': '52b80e92-ffbd-4c87-855c-fa8c14201192',
    'PRODSESSION': '6026214a-742d-4b01-8178-2ff256d2c80a',
}

# 全局对象
session = requests.session()
course_list = []
sem = threading.Semaphore(11)  # 线程限制，含main


# 填充课程信息
def fillCourseInfo(course_list):
    subject_url = '{}/api/learner/subject/{}/courses?status=&groupId=&page=0&size=100&name='.format(
        HOST, subject_id)
    subject_data = session.get(subject_url).json()
    for x in subject_data['content']:
        if x['progress'] != 100:
            course = Course(x['id'], x['name'], x['progress'],
                            x['offeringCourseId'], subject_id)
            course_list.append(course)
            print('加入课程：' + course.name)


# 填充视频信息
def fillRcoInfo(course_list):
    for x in course_list:
        course_url = '{}/api/learner/course/{}/outline/tree'.format(HOST, x.id)
        course_data = session.get(course_url).json()

        rco_list = []
        for y in course_data['children']:
            if y['status'] != 'C':
                rco_list.append(y['id'])
        x.setRcoList(rco_list)


# 刷新请求
def course_refresh(course):
    refresh_url = '{}/api/learner/course/strategy/refresh'.format(HOST)
    data = {
        'offeringId': course.subject_id,
        'courseId': course.id,
    }
    refresh_data = session.post(refresh_url, data=data).json()
    course.progress = refresh_data['studyProgress']
    print("【" + course.name + "】 进度 " + str(course.progress))


# 播放请求
def course_play(course, rco_id, attempt_id):
    play_url = '{}/learner/play/course/{};classroomId={};rcoId={};courseDetailId={};lookBack=true;isRecord=true;learnerAttemptId={}'.format(
        HOST, course.id, course.subject_id, rco_id, course.detail_id,
        attempt_id)
    session.get(play_url)


# 生成token
def genToken():
    s = []
    hex_digits = "0123456789abcdef"
    for index in range(36):
        s.append(hex_digits[math.floor(random.random() * 0x10)])
    s[14] = "4"
    s[19] = hex_digits[((hex_digits.index(s[19]) & 0x3) | 0x8)]
    s[8] = s[13] = s[18] = s[23] = "-"
    uuid = "".join(s)
    return uuid


# 保存请求
def course_save(attempt, nai):
    save_url = '{}/api/learner/play/course/{}/save'.format(
        HOST, attempt.course_id)
    data = {
        'rawStatus': attempt.rawStatus,
        'credit': attempt.credit,
        'learnerAttemptId': attempt.id,
        'course.id': attempt.course_id,
        'classroom.id': attempt.subject_id,
        'attemptToken': attempt.token,
        'rco.id': attempt.rco_id,
        'sessionTime': attempt.sessionTime,
        'terminalType': attempt.terminalType,
    }
    session.cookies.update({'nai': str(nai)})
    save_data = session.post(save_url, data=data).json()

    # 视频状态： C/已完成，I/待完成
    rco_status = 'I'
    for x in save_data:
        if x['id'] == attempt.rco_id:
            rco_status = x['status']

    return rco_status


# 刷课程
def study(course):
    print("【" + course.name + "】 课程 开始")
    attempt_id = int(round(time.time() * 1000))

    for x in course.rco_list:
        # 开始播放
        course_play(course, x, attempt_id)
        attempt = Attempt(attempt_id, course.subject_id, course.id, x,
                          genToken())

        # 定时保存，随机间隔
        total = h = m = s = 0
        while True:
            interval = random.randint(60, 90)
            time.sleep(interval + 1)
            total += interval

            h = total // 3600
            m = (total - h * 3600) // 60
            s = total % 60

            session_time = '{:0>2d}:{:0>2d}:{:0>2d}'.format(h, m, s)
            attempt.setSessionTime(session_time)

            status = course_save(attempt, int(time.time()) * 1000)
            if status == "I":
                course_refresh(course)
            else:
                break
    sem.release()  # 释放线程
    print("【" + course.name + "】 课程 结束！")


if __name__ == '__main__':
    # 伪造Session
    session.headers = headers_init
    requests.utils.add_dict_to_cookiejar(session.cookies, cookies_init)

    # 填充课程表
    fillCourseInfo(course_list)
    fillRcoInfo(course_list)
    print('待完成课程数量：' + str(len(course_list)))

    # 并行播放

    with sem:
        for x in course_list:
            time.sleep(1)
            sem.acquire()  # 获取线程
            threading.Thread(target=study, args=(x, )).start()
