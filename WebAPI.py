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
        更新 formhash

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
        更新 authorization

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
        :raise:
            HepanException: pid与tid不匹配/formhash过期，或帖子不存在/被删除/无权访问
        """
        if update_formhash:  # 短时间大量评分时，建议手动更新formhash一次即可，不需要每次都更新
            self.update_formhash()
        url = 'https://bbs.uestc.edu.cn/forum.php?mod=misc&action=rate&ratesubmit=yes&inajax=1'
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

    def comment(self, tid, pid, content, update_formhash=True):
        """
        点评帖子

        :param tid: 帖子tid
        :param pid: 帖子pid
        :param content: 点评内容
        :param update_formhash: 是否先更新formhash，默认True

        :note:
            由于服务器返回更新后整个网页html，无法直接得知是否成功，因此没有返回值
        """
        url = f'https://bbs.uestc.edu.cn/forum.php?mod=post&action=reply&comment=yes&tid={tid}&pid={pid}&commentsubmit=yes'
        if update_formhash:  # 短时间大量点评时，建议手动更新formhash一次即可，不需要每次都更新
            self.update_formhash()
        data = {
            'formhash': self.formhash,
            'handlekey': 'comment',
            'message': content,
        }
        r = self.session.post(url, data=data)
        r.raise_for_status()

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
        :raise:
            HepanException: 帖子不存在/被删除，或无权访问
        """
        url = f'https://bbs.uestc.edu.cn/star/api/v1/post/list?thread_id={tid}&page=1&thread_details=1'
        try:
            r = self.session.get(url)
            r.raise_for_status()
            data = r.json()
            if data['code'] != 0:
                raise HepanException(f'{data["message"]} tid={tid}')
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
        """
        获取一页回复

        :param tid: 帖子tid
        :param page: 要获取第几页，默认1

        :return:
            dict:
                - hasNext (bool): 是否还有下一页
                - replies (list): 回复列表
                    - dict: 单个回复详细信息
                        - position (int): 楼层
                        - pid (int): 帖子pid
                        - author (str): 回复发送者用户名
                        - uid (int): 回复者uid
                        - time (int): 回复时间戳（秒）
                        - content (str): 回复具体内容
        :raise:
            HepanException: 帖子不存在/被删除，或无权访问
        :note:
            第一页第一个实际上为主帖
        """
        url = f'https://bbs.uestc.edu.cn/star/api/v1/post/list?thread_id={tid}&page={page}&thread_details=1'
        try:
            r = self.session.get(url)
            r.raise_for_status()
            data = r.json()
            if data['code'] != 0:
                raise HepanException(f'{data["message"]} tid={tid}')
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
        """
        获取指定主题帖所有回复

        :param tid: 帖子tid
        :param pageLimit: 最多获取几页，默认20，即400楼
        :return:
            list: 回复列表
                - dict: 存储单个回复信息的字典
                    - position (str): 楼层
                    - pid (int): 回复pid
                    - author (str): 回复者用户名
                    - uid (int): 回复者uid
                    - time (int): 回复时间戳（秒）
                    - content (str): 回复内容
        :raise:
            HepanException: 帖子不存在/被删除，或无权访问
        """
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

    def get_top_10_post(self):
        """
        获取旧版主页的最新回复，最新发表，今日热门，河畔活动，生活专区，精华展示 前10帖

        :return:
            dict: 数据集
                - new_reply (list): 最新回复列表
                    - tid (int): 帖子tid
                    - title (str): 帖子标题
                    - uid (int): 作者uid
                    - uname (str): 作者用户名
                - new_post (list): 最新回复列表
                    ! 同 new_reply
                - hot (list): 今日热门列表
                    ! 同 new_reply
                - activity (list): 河畔活动
                    ! 同 new_reply
                - live (list): 生活专区
                    ! 同 new_reply
                - show (list): 精华展示
                    ! 同 new_reply
        """
        url = 'https://bbs.uestc.edu.cn'
        r = self.session.get(url)
        modes = {'new_reply': 'portal_block_66_content',  # 最新回复
                 'new_post': 'portal_block_67_content',  # 最新发表
                 'hot': 'portal_block_68_content',  # 今日热门
                 'activity': 'portal_block_97_content',  # 河畔活动
                 'live': 'portal_block_96_content',  # 生活专区
                 'show': 'portal_block_95_content'  # 精华展示
                 }
        result = {}
        soup = BeautifulSoup(r.text, 'html.parser')
        for key, target in modes.items():
            li_elements = soup.find(id=target).find_all('li')
            temp = []
            for li in li_elements:
                em_tag = li.find('em')
                a_em = em_tag.find('a') if em_tag else None
                a_title = li.find('a', title=True)
                uid = int(a_em['href'].split('=')[-1]) if a_em else None
                uname = a_em.text.strip() if a_em else ''
                tid = int(a_title['href'].split('=')[-1])
                title = a_title['title']
                temp.append({
                    'tid': tid,
                    'title': title,
                    'uid': uid,
                    'uname': uname
                })
            result[key] = temp
        return result

    def get_darkroom(self):
        """
        获取小黑屋列表

        :return:
            list: 小黑屋用户列表
                - dict: 用户信息
                    - name (str): 用户名
                    - uid (int): 用户uid
                    - action (str): 操作行为
                    - expiration (str): 过期时间
                    - time (str): 操作时间
                    - reason (str): 操作理由
        """
        url = 'https://bbs.uestc.edu.cn/forum.php?mod=misc&action=showdarkroom'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table', id='darkroomtable')
        rows = table.select('tr[id^="darkroomuid_"]')
        result = []
        for i in rows:
            td = i.find_all('td')
            name = td[0].text.strip()
            uid = int(i['id'][12:])
            action = td[1].text.strip()
            expiration = td[2].text.strip()
            time = td[3].text.strip()
            reason = td[4].text.strip()
            result.append({
                'name': name,
                'uid': uid,
                'action': action,
                'expiration': expiration,
                'time': time,
                'reason': reason
            })
        return result

    def get_user_rank(self, sub_rank, order=''):
        """
        获取用户排行榜

        :param sub_rank: 子排行榜
        :param order: 排序方式/类别

        :return:
            dict:
                - notice (str): 提示信息
                - data (list): 排行榜
                    - dict: 单个用户数据
                        - rank (int): 排名
                        - name (str): 用户名
                        - uid (int): 用户uid
                        - msg (str): 相关信息
        """
        """
        常用值
        sub_rank
            = 'credit': 积分
                order
                    = 'all': 全部
                    = 1: 威望
                    = 2: 水滴
                    = 6: 奖励券
            = ‘post’: 发帖数
                order
                    = 'posts': 发帖
                    = 'digestposts': 精华
                    = 'thismonth': 最近30天发帖数
                    = 'today': 最近24小时发帖数
            = 'onlinetime': 在线时间
                order
                    = 'thismonth': 本月
                    = 'all': 全部
            = 'water': 人气
                order
                    = 30: 最近30天
                    = 202503: 2025年3月
                    = 202502: 2025年2月
                    ...
        """

        url = f'https://bbs.uestc.edu.cn/misc.php?mod=ranklist&type=member&view={sub_rank}&orderby={order}'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find_all(class_='bbda cl')
        data = []
        for i in rows:
            ranknum = i.find(class_='ranknum')
            if rank := ranknum.find('img'):
                rank = rank['alt']
            else:
                rank = ranknum.text.strip()
            user_dt = i.find('dt').find('a')
            name = i.contents[-4].text.strip()
            uid = int(user_dt['href'].split('=')[-1])
            msg = i.contents[-2].text.strip()
            data.append({
                'rank': int(rank),
                'name': name,
                'uid': uid,
                'msg': msg
            })
        notice = soup.find(class_='notice').text.strip()
        return {'notice': notice, 'data': data}

    def get_thread_rank(self, sub_rank, order='all'):
        """
        获取帖子排行榜

        :param sub_rank: 子排行榜
        :param order: 排序方式/类别

        :return:
            dict:
                - notice: 提示信息
                - data (list): 排行榜
                    - dict: 单个帖子数据
                        - rank (int): 排名
                        - title (str): 帖子标题
                        - forum (str): 帖子所在板块名称
                        - author (str): 发帖人
                        - uid (int): 发帖人uid
                        - time (str): 发帖时间
                        - count (int): 排序的数据
        :note:
            count: 按回复排时，count为回复数，以此类推
        """
        """
        常用值
        sub_rank
            = 'replies': 回复
                order
                    = 'all': 全部
                    = 'thisweek': 本周
                    = 'thismonth': 本月
                    = 'today': 今日
            = 'views': 查看
                order
                    同 sub_rank = 'replies'
            = 'favtimes': 收藏
                order
                    同 sub_rank = 'replies'
            = 'heats': 热度
                order
                    同 sub_rank = 'replies'
        """
        url = f'https://bbs.uestc.edu.cn/misc.php?mod=ranklist&type=thread&view={sub_rank}&orderby={order}'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find('table').find_all('tr')
        data = []
        for i in rows[1:]:
            ranknum = i.find('td', class_='icn')
            if rank := ranknum.find('img'):
                rank = rank['alt']
            else:
                rank = ranknum.text.strip()
            title = i.find('th').text.strip()
            forum = i.find('td', class_='frm').text.strip()
            thread_i = i.find('td', class_='by')
            auth_i = thread_i.find('a')
            author = auth_i.text.strip()
            uid = int(auth_i['href'].split('=')[-1])
            time = thread_i.find('em').text.strip()
            count = i.contents[-2].text.strip()
            data.append({
                'rank': int(rank),
                'title': title,
                'forum': forum,
                'author': author,
                'uid': uid,
                'time': time,
                'count': int(count)
            })
        notice = soup.find('div', class_='notice').text.strip()
        return {'notice': notice, 'data': data}

    def get_pool_rank(self, sub_rank, order=''):
        """
        获取投票贴排行榜

        :param sub_rank: 子排行榜
        :param order: 排序方式/类别

        :return:
            dict:
                - notice: 提示信息
                - data (list): 排行榜
                    - dict: 单个帖子数据
                        - rank (int): 排名
                        - author (str): 发帖人
                        - uid (int): 发帖人uid
                        - title (str): 帖子标题
                        - tid (int): 帖子tid
                        - count (int): 排序的数据
                        - time (str): 发帖时间
                        - voters (int): 投票人数
        :note:
            count: 按热度排时，count为热度值
        """
        """
        常用值
        sub_rank
            = 'heats': 热度
                order
                    = 'all': 全部
                    = 'thisweek': 本周
                    = 'thismonth': 本月
                    = 'today': 今日
        """
        url = f'https://bbs.uestc.edu.cn/misc.php?mod=ranklist&type=poll&view={sub_rank}&orderby={order}'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('ul', class_='el pll')
        rows = table.find_all('li')
        data = []
        for i in rows:
            ranknum = i.find('div', class_='t')
            if not ranknum:
                continue
            if rank := ranknum.find('img'):
                rank = rank['alt']
            else:
                rank = ranknum.text.strip()
            auth_i = i.find(class_='mtn').find('a')
            author = auth_i.text.strip()
            uid = int(auth_i['href'].split('=')[-1])
            thread_i = i.find(class_='h').find('a')
            title = thread_i.text.strip()
            tid = int(thread_i['href'].split('=')[-1])
            extra_info = i.find(class_='mtn xg1')
            count = extra_info.contents[0].strip()[3:]
            time = extra_info.contents[-1].strip()
            voters = i.find(class_='s y').find('span').text.strip()
            data.append({
                'rank': int(rank),
                'author': author,
                'uid': uid,
                'title': title,
                'tid': tid,
                'count': count,
                'time': time,
                'voters': int(voters)
            })
        notice = soup.find('div', class_='notice').text.strip()
        return {'notice': notice, 'data': data}

    def get_forum_rank(self, sub_rank):
        """
        获取板块排行榜

        :param sub_rank: 子排行榜

        :return:
            dict:
                - notice: 提示信息
                - data (list): 排行榜
                    - dict: 单个板块数据
                        - rank (int): 排名
                        - forum (str): 板块
                        - count (int): 排序的数据
        :note:
            count: 按发帖排时，count为发帖数，以此类推
        """
        """
        常用值
        sub_rank
            = 'threads': 发帖
            = 'post': 回复
            = 'today': 最近24小时发帖
        """
        url = f'https://bbs.uestc.edu.cn/misc.php?mod=ranklist&type=forum&view={sub_rank}'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find('table').find_all('tr')
        data = []
        for i in rows[1:]:
            ranknum = i.find('td', class_='icn')
            if rank := ranknum.find('img'):
                rank = rank['alt']
            else:
                rank = ranknum.text.strip()
            forum = i.find('th').text.strip()
            count = i.contents[-2].text.strip()
            data.append(
                {
                    'rank': int(rank),
                    'forum': forum,
                    'count': int(count)
                }
            )
        notice = soup.find('div', class_='notice').text.strip()
        return {'notice': notice, 'data': data}

    def get_task_list(self, mode='new'):
        """
        获取任务列表

        :param mode: 模式，new/doing/done，默认 new

        :return:
            list: 任务列表
                - dict: 单个任务信息
                    - name (str): 任务名称
                    - id (int): 任务id
                    - description (str): 任务描述
                    - reward (str): 任务奖励
        """
        url = f'https://bbs.uestc.edu.cn/home.php?mod=task&item={mode}'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('div', class_='bm bw0').find('table')
        if not table:
            return []
        rows = table.find_all('tr')
        result = []
        for i in rows:
            task_i = i.find('td', class_='bbda ptm pbm')
            task_i_a = task_i.find('a')
            name = task_i_a.text.strip()
            id = int(task_i_a['href'].split('=')[-1])
            task_i_p = task_i.find('p')
            description = task_i_p.text.strip()
            reward = i.find('td', class_='xi1 bbda hm').text.strip()
            result.append({
                'name': name,
                'id': id,
                'description': description,
                'reward': reward
            })
        return result

    def apply_task(self, task_id):
        """
        申请任务

        :param task_id: 任务id

        :return
            tuple:
                - bool: 是否成功
                - str: 提示信息
        """
        url = f'https://bbs.uestc.edu.cn/home.php?mod=task&do=apply&id={task_id}'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        if msg := soup.find('div', id='messagetext', class_='alert_info'):
            if '任务申请成功' in msg.text:
                return True, msg.text.strip()
            else:
                return False, msg.text.strip()

    def finish_task(self, task_id):
        """
        完成任务，领取奖励

        :param task_id: 任务id

        :return
            tuple:
                - bool: 是否成功
                - str: 提示信息
        """
        url = f'https://bbs.uestc.edu.cn/home.php?mod=task&do=draw&id={task_id}'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        if msg := soup.find('div', id='messagetext', class_='alert_info'):
            if '任务已成功完成' in msg.text:
                return True, msg.text.strip()
            else:
                return False, msg.text.strip()

    def get_task_info(self, task_id):
        """
        获取任务详细信息

        :param task_id: 任务id

        :return:
            dict: 任务详细信息
                - name (str): 任务名称
                - description (str): 任务描述
                - reward (str): 任务奖励
                - mission (str): 具体任务
                - requirement (str): 申请此任务所需条件
                - status (str): 任务状态 doing/done/applicable
                - progress (str): 任务进度
        :note:
            progress: 只有进行中的任务会返回具体进度

        """
        url = f'https://bbs.uestc.edu.cn/home.php?mod=task&do=view&id={task_id}'
        r = self.session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('div', class_='bm bw0').find('table')
        rows = table.find_all('tr')
        task_i = rows[0].find('td', class_='bbda')
        name = task_i.find('h1', class_='xs2 ptm pbm').text.strip()
        description = task_i.find_all('div')[-1].text.strip()
        sub_table = rows[1].find('table')
        sub_rows = sub_table.find_all('tr')
        reward = sub_rows[0].find('td', class_='bbda').text.strip()
        mission = sub_rows[1].find('td', class_='bbda').text.strip()
        requirement = sub_rows[2].find('td', class_='bbda').text.strip()
        img = rows[-2].find_all('img')[-1]
        if img:
            if img['src'] in ['static/image/task/cancel.gif', 'static/image/task/reward.gif']:
                status = 'doing'
                progress = rows[-2].find('span', id=f'csc_{task_id}').text.strip()
            else:
                status = 'applicable' if img['src'] == 'static/image/task/apply.gif' else 'not applicable'
                progress = rows[-2].find('p', class_='xg2 mbn').text.strip()
        else:
            status = 'done'
            progress = rows[-2].find('p', class_='xg2 mbn').text.strip()
        return {
            'name': name,
            'description': description,
            'reward': reward,
            'mission': mission,
            'requirement': requirement,
            'status': status,
            'progress': progress
        }
