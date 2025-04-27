import WebAPI

username = 'your_username'
password = 'your_password'

# 旧版API
api = WebAPI.WebAPI(username, password)
tid = 2287221
print('获取帖子基本信息 :', api.get_thread_info(tid))
print('获取单页回复 :', api.get_reply_page(tid))
print('获取帖子所有回复，#1 :', api.get_reply_all(tid))  # 获取帖子所有回复，默认限制20页（400楼）
print('获取帖子所有回复，#2 :', api.get_reply_all(tid, 0))  # 获取帖子所有回复，显式取消限制
# 除了散水帖，一般帖子很难超过400楼，建议保留默认限制
print('获取旧版主页6个列表 :', api.get_top_10_post())  # 最新回复，最新发表，今日热门，河畔活动，生活专区，精华展示 前10帖
print('获取小黑屋信息 :', api.get_darkroom())
print('获取用户积分排行 :', api.get_user_rank('credit'))
print('获取最近24小时用户发帖数排行 :', api.get_user_rank('post', 'today'))
print('获取帖子今日回复排行 :', api.get_thread_rank('replies', 'today'))
print('获取投票帖今日热度排行 :', api.get_pool_rank('heats', 'today'))
print('获取近24小时发帖板块排行 ：', api.get_forum_rank('today'))
