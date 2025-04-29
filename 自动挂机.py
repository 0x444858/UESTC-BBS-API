import WebAPI
import time

# 注意：其实用 curl + 系统定时器 更简单
# 示例：curl "https://bbs.uestc.edu.cn/member.php?mod=logging&action=login&loginsubmit=yes&inajax=1"
#           -d "loginfield=username" -d "username=your_username" -d "password=your_password"
# 提醒：在Windows上，curl要改成curl.exe

loginCycle = 60 * 60 * 24  # 重新登录周期，单位秒
freshInterval = 60 * 2  # 刷新周期，单位秒
account_info = {  # 支持多账户
    'account1': 'password1',
    'account2': 'password2'
}
account_dict = {}
for username, password in account_info.items():
    api = WebAPI.WebAPI(username, password)
    account_dict[username] = api
while True:
    t = int(loginCycle / freshInterval)
    for i in range(t):
        for username, api in account_dict.items():
            print(f'[{time.asctime()}] 更新用户 {username}')
            api.update_formhash()
            time.sleep(freshInterval)
    for username, api in account_dict.items():
        print(f'[{time.asctime()}] 重新登录用户 {username}')
        api.login()
