import WebAPI
import time
import config

username = 'Range6'
password = config.account_info[username]

tid = 0  # tid一定要正确
score = 5  # 单次奖励
user_times_limit = 1  # 单用户最多奖励次数
check_interval = 3  # 检查间隔，秒
max_reward_times = 80  # 总最大奖励次数
time_limit = 60 * 60 * 1  # 时间限制，秒（与帖子创建时间差值）

if score * max_reward_times > 400:
    print('单用户最多单日评分400')
    exit()
if tid == 0:
    print('请输入帖子ID')
    exit()


def check(reply):
    """
    回复需满足的条件，根据需求定制
    检查楼层数、回复等
    """
    position = reply['position']  # 楼层
    content = reply['content']  # 内容
    uid = reply['uid']  # uid
    author = reply['author']  # 用户名
    timestamp = reply['time']  # 时间戳
    if author == username:  # 是本人
        return False
    # 以下逻辑根据需要编写，可使用上面5个变量
    if position % 3 == 0:  # 3的倍数
        return True
    return False


api = WebAPI.WebAPI(username, password)
thread_info = api.get_thread_info(tid)
start_time = thread_info['create_time']
title = thread_info['title']
pid = thread_info['pid']
page = 1
done_positions = [1]
user_limit = {}
reward_times_count = 0
while True:
    r = api.get_reply_page(tid, page)
    replies = r['replies']
    for i in replies:
        if i['position'] not in done_positions:
            if not check(i):
                continue
            if i['author'] not in user_limit:
                user_limit[i['author']] = 0
            if user_limit[i['author']] >= user_times_limit:
                print(f'[{time.asctime()}] {i["position"]}，用户 {i["author"]} 已超过最大奖励次数: {user_times_limit}')
                done_positions.append(i['position'])
                continue
            user_limit[i['author']] += 1
            reward_times_count += 1
            api.rate(tid, i['pid'], score,
                     f'[{reward_times_count}] {i["position"]}楼奖励，当前用户已奖励{user_limit[i["author"]] * score}水滴')
            print(f'[{time.asctime()}] 已奖励{i}')
            if reward_times_count >= max_reward_times:
                print(f'[{time.asctime()}] 已达到最大总奖励次数')
                exit()
    if r['hasNext']:
        page += 1
    if time.time() - start_time > time_limit:
        print(f'[{time.asctime()}] 已达到时间限制')
        exit()
    else:
        print(f'[{time.asctime()}] 已检查{page}页，已奖励{reward_times_count}次')
        print(f'[{time.asctime()}] 剩余时间{time_limit - (time.time() - start_time)}秒')
    time.sleep(check_interval)
