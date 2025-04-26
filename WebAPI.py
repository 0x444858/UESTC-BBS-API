import requests
from bs4 import BeautifulSoup
from operator import itemgetter


class HepanException(Exception):
    """
    当因为论坛自身限制，导致函数失败时，会抛出此异常
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class WebAPI:
    """
    河畔网页API
    """
    formhash = ''

    def __init__(self, username, password, autoLogin=True):
        """
        初始化
        :param username: 用户名
        :param password: 密码
        :param autoLogin: 是否在初始化后自动登录，默认True
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        if autoLogin:
            self.login()

    def login(self):
        """
        登录并自动更新 authorization

        :return:
            成功 True，失败 False
        :raises:
            HepanException: 账号密码错误或账号被限制
        :warning: 连续登录失败5次会被限制登录，请仔细核对用户名和密码
        """
        url = 'https://bbs.uestc.edu.cn/member.php?mod=logging&action=login&loginsubmit=yes&loginhash=Lcefp&inajax=1'
        data = {'loginfield': 'username', 'username': self.username, 'password': self.password}
        try:
            r = self.session.post(url, data=data, timeout=10)
            r.raise_for_status()
            if '欢迎您回来' in r.text:
                return True and self.update_authorization()
            else:
                raise HepanException(f'登录失败 username={self.username}, password={self.password}\n{r.text}')
        except Exception as e:
            if isinstance(e, HepanException):
                raise
            else:
                print(e)
                return False

    def update_formhash(self):
        """
        更新formhash

        :return:
            成功 True，失败 False
        """
        url = 'https://bbs.uestc.edu.cn'
        try:
            r = self.session.get(url)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            self.formhash = soup.find('input', {'name': 'formhash'})['value']
            return True
        except Exception as e:
            print(e)
            return False

    def update_authorization(self):
        """
        更新authorization

        :return:
            bool: 成功 True，失败 False
        """
        url = 'https://bbs.uestc.edu.cn/star/api/v1/auth/adoptLegacyAuth'
        headers = {'X-Uestc-Bbs': '1'}
        try:
            r = self.session.post(url, headers=headers)
            r.raise_for_status()
            authorization = r.json()['data']['authorization']
            self.session.headers.update({"Authorization": authorization})
            return True
        except Exception as e:
            print(e)
            return False

    def rate(self, tid, pid, score, reason='', update_formhash=True):
        """
        对帖子或回复评分（加/扣水）

        :param tid: （回复所在）帖子tid
        :param pid: 帖子或回复pid
        :param score: 水滴数，负数表示扣水
        :param reason: 操作理由（默认空）
        :param update_formhash: 是否先更新formhash，默认True
        :return:
            bool: 成功 True，失败 False
        :raise: HepanException: formhash过期，或帖子不存在/被删除/无权访问
        """
        if update_formhash:  # 短时间大量评分时，建议手动更新formhash一次即可，不需要每次都更新
            self.update_formhash()
        url = 'https://bbs.uestc.edu.cn/forum.php?mod=misc&action=rate&ratesubmit=yes&infloat=yes&inajax=1'
        data = {
            'formhash': self.formhash,
            'tid': tid,
            'pid': pid,
            'score2': score,
            'reason': reason
        }
        try:
            r = self.session.post(url, data=data)
            r.raise_for_status()
            if '感谢您的参与' in r.text:
                return True
            else:
                raise HepanException(f'评价失败 tid={tid}, pid={pid}, score={score}, reason={reason}\n{r.text}')
        except Exception as e:
            if isinstance(e, HepanException):
                raise
            else:
                print(e)
                return False

    def get_thread_info(self, tid):
        """
        获取指定主题帖信息

        :param tid: 主题帖的tid
        :return:
            dict: 包含帖子信息的字典
                - tid (int): 主题帖tid
                - title (str): 帖子标题
                - pid (int): 主题帖pid
                - first_paragraph (str): 主题帖首段内容
                - reply_count (int): 回复总数
                - author (str): 楼主用户名
                - uid (int): 楼主uid
        :raise: HepanException: 帖子不存在/被删除，或无权访问
        :note:
            以下情况下，该函数与 Old.get_thread_info() 的返回值不同
            1. 当存在点评时， reply_count 的值不同。
                Old.get_thread_info()['reply_count'] 为评论和点评总数
                本函数 reply_count 仅为评论数
            2. 当首段不为无格式纯文本时，first_paragraph 可能不同
                一般而言，当不同时，本函数返回的内容更长
                当首段为无格式纯文本时，能保证两个函数返回的 first_paragraph 相同
        """
        url = f'https://bbs.uestc.edu.cn/star/api/v1/post/list?thread_id={tid}&page=1&thread_details=1'
        try:
            r = self.session.get(url)
            r.raise_for_status()
            data = r.json()
            if data['code'] != 0:
                raise HepanException(f'{data['message']} tid={tid}')
            data = data['data']
            thread = data['rows'][0]
            thread_info = {
                'tid': tid,
                'title': thread['subject'],
                'pid': thread['post_id'],
                'first_paragraph': thread['message'].split('\n')[0].strip(),
                'reply_count': data['total'] - 1,
                'author': thread['author'],
                'uid': thread['author_id']
            }
            return thread_info
        except Exception as e:
            if isinstance(e, HepanException):
                raise
            else:
                print(e)
                return None

    def get_reply_page(self, tid, page=1):
        url = f'https://bbs.uestc.edu.cn/star/api/v1/post/list?thread_id={tid}&page={page}&thread_details=1'
        try:
            r = self.session.get(url)
            r.raise_for_status()
            data = r.json()
            if data['code'] != 0:
                raise HepanException(f'{data['message']} tid={tid}')
            data = data['data']
            hasNext = data['total'] > data['page'] * data['page_size']
            rows = data['rows']
            key_map = {
                'position': 'position',
                'post_id': 'pid',
                'author': 'author',
                'author_id': 'uid',
                'dateline': 'time',
                'message': 'content'
            }
            source_keys = list(key_map.keys())
            getter = itemgetter(*source_keys)
            replies = [
                {
                    key_map[key]: value.strip() if key == 'message' else value
                    for key, value in zip(source_keys, getter(row))
                }
                for row in rows
            ]
            return {'hasNext': hasNext, 'replies': replies}
        except Exception as e:
            if isinstance(e, HepanException):
                raise
            else:
                print(e)
                return None

    def get_reply_all(self, tid, pageLimit=0):
        replies = []
        page = 1
        while True:
            result = self.get_reply_page(tid, page)
            hasNext = result['hasNext']
            replies.extend(result['replies'])
            if not hasNext or (pageLimit and page >= pageLimit):
                break
            page += 1
        return replies

