import requests
import time
import threading
import math
import random

from wsxy_course import Course
from wsxy_attempt import Attempt

# 常用信息
HOST = "http://wsxy.chinaunicom.cn"
subject_id = 49649837
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
    'XSRF-TOKEN': 'a936023c-8337-4683-bdd7-b88f26d6c1a2',
    'PRODSESSION': '650f2263-f3a1-4c83-ac4c-d2f4d3098ca1',
}

session = requests.session()
course_list = []

work_count = 4  # 并发任务数
sem = threading.Semaphore(work_count + 1)


def fillCourseInfo(course_list):
    """填充课程信息，默认数量100"""
    url = '{}/api/learner/subject/{}/courses?status=&groupId=&page=0&size=100&name='.format(
        HOST, subject_id)
    resp = session.get(url=url)

    rs = []
    try:
        rs = resp.json()['content']
    except Exception as e:
        print('请求失败 【课程表】 Status: {}, Url: {}, 异常信息: {}'.format(
            resp.status_code, resp.url, e))

    for x in rs:
        if x['progress'] != 100:
            course = Course(x['id'], x['name'], x['progress'],
                            x['offeringCourseId'], subject_id)
            course_list.append(course)
            print('新增课程 【{}】'.format(course.name))
    print('待完成课程数量：' + str(len(course_list)))


def fillRcoInfo(course_list):
    """填充视频信息"""
    for x in course_list:
        url = '{}/api/learner/course/{}/outline/tree'.format(HOST, x.id)
        resp = session.get(url=url)

        rs = []
        try:
            rs = resp.json()['children']
        except Exception as e:
            print('请求失败 【视频信息】 Status: {}, Url: {}, 异常信息: {}'.format(
                resp.status_code, resp.url, e))

        rco_list = []
        for y in rs:
            rco_list.append(y['id'])
        x.setRcoList(rco_list)


def course_refresh(course):
    """刷新请求"""
    url = '{}/api/learner/course/strategy/refresh'.format(HOST)
    data = {
        'offeringId': course.subject_id,
        'courseId': course.id,
    }
    resp = session.post(url=url, data=data)

    rs = resp.json()
    try:
        course.progress = rs['studyProgress']
    except Exception as e:
        print('请求失败 【刷新进度】 Status: {}, Url: {}, 异常信息: {}'.format(
            resp.status_code, resp.url, e))


def course_play(course, rco_id, attempt_id):
    """播放请求，一个rco对应一个attempt
    Args:
        course: 课程对象
        rco_id: 视频id
        attempt_id: “记录”id，由时间戳生成
    """
    url = '{}/learner/play/course/{};classroomId={};rcoId={};courseDetailId={};lookBack=true;isRecord=true;learnerAttemptId={}'.format(
        HOST, course.id, course.subject_id, rco_id, course.detail_id,
        attempt_id)
    resp = session.get(url=url)

    if resp.status_code != requests.codes.OK:
        print('请求失败 【播放】 Status: {}, Url: {}'.format(resp.status_code,
                                                     resp.url))
        return False
    return True


def course_save(attempt, nai):
    """保存请求
    Args:
        attempt: “记录”对象
        nai: 请求时刻，由时间戳生成
    """
    url = '{}/api/learner/play/course/{}/save'.format(HOST, attempt.course_id)
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
    resp = session.post(url=url, data=data)

    if resp.status_code != requests.codes.OK:
        print('请求失败 【保存】 Status: {}, Url: {}'.format(resp.status_code,
                                                     resp.url))


def genToken():
    """生成token，规则在js里"""
    s = []
    hex_digits = "0123456789abcdef"
    for index in range(36):
        s.append(hex_digits[math.floor(random.random() * 0x10)])
    s[14] = "4"
    s[19] = hex_digits[((hex_digits.index(s[19]) & 0x3) | 0x8)]
    s[8] = s[13] = s[18] = s[23] = "-"
    uuid = "".join(s)
    return uuid


def time_convert(seconds):
    """时间转换， 秒数--> 01:34:02"""
    h = seconds // 3600
    m = (seconds - h * 3600) // 60
    s = seconds % 60
    results = '{:0>2d}:{:0>2d}:{:0>2d}'.format(h, m, s)
    return results


def study(course):
    """学习某个课程，第一个视频刷完所有的进度，其他视频状态直接赋值 “C” """
    print('【{}】 课程 开始'.format(course.name))
    attempt_id = int(round(time.time() * 1000))

    for x in course.rco_list:
        attempt = Attempt(attempt_id, course.subject_id, course.id, x,
                          genToken())

        # 开始播放
        is_start = course_play(course, x, attempt_id)
        if is_start:
            # 定时保存
            total = 0
            while True:
                interval = random.randint(60, 90)  # 随机间隔，避免查账
                time.sleep(interval)
                total += interval
                attempt.setSessionTime(time_convert(total))

                course_save(attempt, int(time.time()) * 1000)

                course_refresh(course)
                if course.progress != 100.0:
                    print('【{}】进度 {}'.format(course.name, course.progress))
                else:
                    break

    print('【{}】 课程 结束'.format(course.name))
    sem.release()  # 释放线程


if __name__ == '__main__':
    # 伪造Session
    session.headers = headers_init
    requests.utils.add_dict_to_cookiejar(session.cookies, cookies_init)

    # 填充课程表
    fillCourseInfo(course_list)
    fillRcoInfo(course_list)

    # 并行播放
    with sem:
        for x in course_list:
            time.sleep(1)
            sem.acquire()  # 获取线程
            threading.Thread(target=study, args=(x, )).start()
