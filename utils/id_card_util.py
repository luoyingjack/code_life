import time
from id_validator import validator
# 生成出生当年所有日期


def dateRange(year):
    fmt = '%Y-%m-%d'
    bgn = int(time.mktime(time.strptime(year+'-01-01', fmt)))
    end = int(time.mktime(time.strptime(year+'-12-31', fmt)))
    list_date = [time.strftime(fmt, time.localtime(i)) for i in range(bgn, end+1, 3600*24)]
    return [i.replace('-', '') for i in list_date]


data_time = dateRange('1995')


# 遍历所有日期，print通过校验的身份证号码

def vali_dator(id1, id2, id3):
    n = 1
    for i in dateRange(id2):
        theid = id1 + i + id3
        if validator.is_valid(theid):
            print(n, theid)
            n += 1


vali_dator('410222', '1995', '5533')
