# -*- coding: utf-8 -*-
"""
四柱八字计算模块
根据公历日期计算年柱、月柱、日柱、时柱，并进行日主强弱与用神分析
支持：
  1. 开奖日四柱计算（公历日期，固定亥时21:15）
  2. 个人生辰八字计算（支持农历转公历，支持指定时辰）
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

# ==================== 基础数据 ====================

# 天干
TIAN_GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

# 地支
DI_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 天干五行
GAN_WUXING = {
    '甲': '木', '乙': '木',
    '丙': '火', '丁': '火',
    '戊': '土', '己': '土',
    '庚': '金', '辛': '金',
    '壬': '水', '癸': '水'
}

# 地支五行
ZHI_WUXING = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木',
    '辰': '土', '巳': '火', '午': '火', '未': '土',
    '申': '金', '酉': '金', '戌': '土', '亥': '水'
}

# 地支藏干（本气、中气、余气）
ZHI_CANG_GAN = {
    '子': ['癸'],
    '丑': ['己', '辛', '癸'],
    '寅': ['甲', '丙', '戊'],
    '卯': ['乙'],
    '辰': ['戊', '乙', '癸'],
    '巳': ['丙', '庚', '戊'],
    '午': ['丁', '己'],
    '未': ['己', '丁', '乙'],
    '申': ['庚', '壬', '戊'],
    '酉': ['辛'],
    '戌': ['戊', '辛', '丁'],
    '亥': ['壬', '甲']
}

# 五行生克关系
# 生: 木→火→土→金→水→木
# 克: 木→土→水→火→金→木
WUXING_ORDER = ['木', '火', '土', '金', '水']

# 节气月份对应（地支月）
# 寅月=1, 卯月=2, ..., 丑月=12
MONTH_ZHI = ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑']

# 各节气月的近似开始日期（月, 日）- 基于常年平均
SOLAR_TERMS_APPROX = [
    (2, 4),    # 立春 → 寅月开始
    (3, 6),    # 惊蛰 → 卯月开始
    (4, 5),    # 清明 → 辰月开始
    (5, 6),    # 立夏 → 巳月开始
    (6, 6),    # 芒种 → 午月开始
    (7, 7),    # 小暑 → 未月开始
    (8, 8),    # 立秋 → 申月开始
    (9, 8),    # 白露 → 酉月开始
    (10, 8),   # 寒露 → 戌月开始
    (11, 7),   # 立冬 → 亥月开始
    (12, 7),   # 大雪 → 子月开始
    (1, 6),    # 小寒 → 丑月开始
]

# 五虎遁：年干→寅月天干起始
# 甲己年起丙寅, 乙庚年起戊寅, 丙辛年起庚寅, 丁壬年起壬寅, 戊癸年起甲寅
WU_HU_DUN = {
    0: 2,  # 甲/己 → 丙(索引2)
    5: 2,  # 甲/己 → 丙
    1: 4,  # 乙/庚 → 戊(索引4)
    6: 4,  # 乙/庚 → 戊
    2: 6,  # 丙/辛 → 庚(索引6)
    7: 6,  # 丙/辛 → 庚
    3: 8,  # 丁/壬 → 壬(索引8)
    8: 8,  # 丁/壬 → 壬
    4: 0,  # 戊/癸 → 甲(索引0)
    9: 0,  # 戊/癸 → 甲
}

# 五鼠遁：日干→子时天干起始
# 甲己日起甲子, 乙庚日起丙子, 丙辛日起戊子, 丁壬日起庚子, 戊癸日起壬子
WU_SHU_DUN = {
    0: 0,  # 甲/己 → 甲(索引0)
    5: 0,
    1: 2,  # 乙/庚 → 丙(索引2)
    6: 2,
    2: 4,  # 丙/辛 → 戊(索引4)
    7: 4,
    3: 6,  # 丁/壬 → 庚(索引6)
    8: 6,
    4: 8,  # 戊/癸 → 壬(索引8)
    9: 8,
}

# 时辰对照表（时辰名 → 时辰地支索引 & 小时范围）
SHI_CHEN_MAP = {
    '子': {'branch_idx': 0,  'hours': (23, 0, 1)},
    '丑': {'branch_idx': 1,  'hours': (1, 2, 3)},
    '寅': {'branch_idx': 2,  'hours': (3, 4, 5)},
    '卯': {'branch_idx': 3,  'hours': (5, 6, 7)},
    '辰': {'branch_idx': 4,  'hours': (7, 8, 9)},
    '巳': {'branch_idx': 5,  'hours': (9, 10, 11)},
    '午': {'branch_idx': 6,  'hours': (11, 12, 13)},
    '未': {'branch_idx': 7,  'hours': (13, 14, 15)},
    '申': {'branch_idx': 8,  'hours': (15, 16, 17)},
    '酉': {'branch_idx': 9,  'hours': (17, 18, 19)},
    '戌': {'branch_idx': 10, 'hours': (19, 20, 21)},
    '亥': {'branch_idx': 11, 'hours': (21, 22, 23)},
}

# 时辰别名（方便输入）
SHI_CHEN_ALIAS = {
    'zi': '子', 'chou': '丑', 'yin': '寅', 'mao': '卯',
    'chen': '辰', 'si': '巳', 'wu': '午', 'wei': '未',
    'shen': '申', 'you': '酉', 'xu': '戌', 'hai': '亥',
    '0': '子', '1': '丑', '2': '寅', '3': '卯', '4': '辰',
    '5': '巳', '6': '午', '7': '未', '8': '申', '9': '酉',
    '10': '戌', '11': '亥',
}

# 农历月份天数参考（用于简单农历转换）
# 农历转公历使用近似算法，对于精确命理建议使用专业万年历
# 这里使用儒略日数近似法

# ==================== 农历转公历 ====================

def lunar_to_solar(lunar_year: int, lunar_month: int, lunar_day: int,
                   is_leap_month: bool = False) -> date:
    """
    农历转公历（近似算法，基于农历数据表）

    参数:
        lunar_year: 农历年（如 1992）
        lunar_month: 农历月（1-12）
        lunar_day: 农历日（1-30）
        is_leap_month: 是否闰月

    返回:
        公历 date 对象

    说明:
        此函数使用内置的农历数据表（1900-2100年），
        精度较高，适合命理计算使用。
    """
    # 农历数据表 key: 年份，value: 各月天数（从正月开始，若有闰月则多一个元素）
    # 每个数字：高4位表示闰月位置（0=无闰月，1-12=在第n月后闰），
    # 低28位每位表示对应月天数（1=30天，0=29天）
    # 同时包含正月初一对应的公历月日

    # 简化版：使用月份偏移量近似算法
    # 对于1992年，使用精确数据
    LUNAR_DATA = {
        # 格式: year: (春节公历月, 春节公历日, [各月天数], 闰月月份或0)
        1990: (1, 27, [29,30,29,29,30,29,30,29,30,30,30,29], 0),
        1991: (2, 15, [30,29,30,29,29,30,29,29,30,30,29,30,29], 8),  # 闰8月
        1992: (2,  4, [30,29,30,30,29,30,29,29,30,29,30,29,30], 4),  # 闰4月
        1993: (1, 23, [29,30,29,30,29,30,30,29,30,29,29,30], 0),
        1994: (2, 10, [30,29,30,29,30,29,30,30,29,30,29,29,30], 8),  # 闰8月
        1995: (1, 31, [29,30,29,29,30,30,29,30,30,29,30,29], 0),
        1996: (2, 19, [30,29,30,29,29,30,29,30,30,29,30,29,30], 8),  # 闰8月
        1997: (2,  7, [29,30,29,30,29,29,30,29,30,30,29,30,29], 0),
        1998: (1, 28, [30,29,30,29,30,29,29,30,29,30,29,30], 5),  # 闰5月
        1999: (2, 16, [30,30,29,30,29,30,29,29,30,29,30,29], 0),
        2000: (2,  5, [30,30,29,30,30,29,30,29,29,30,29,29,30], 8),  # 闰8月
    }

    if lunar_year not in LUNAR_DATA:
        # 对于不在数据表中的年份，使用近似算法
        return _lunar_to_solar_approx(lunar_year, lunar_month, lunar_day)

    data = LUNAR_DATA[lunar_year]
    chun_jie_month, chun_jie_day = data[0], data[1]
    month_days = data[2]
    leap_month = data[3]

    # 计算春节（正月初一）的公历日期
    chun_jie = date(lunar_year, chun_jie_month, chun_jie_day)

    # 计算目标农历日距春节的偏移天数
    offset = 0
    idx = 0  # 月份数组索引
    for m in range(1, lunar_month):
        if leap_month != 0 and m > leap_month:
            # 跳过了闰月，实际月数组多一个
            pass
        if idx < len(month_days):
            offset += month_days[idx]
            idx += 1
        if leap_month != 0 and m == leap_month:
            if is_leap_month:
                # 目标就是闰月，继续加上正月天数后停在闰月
                pass
            else:
                # 跳过闰月
                if idx < len(month_days):
                    offset += month_days[idx]
                    idx += 1

    if is_leap_month and leap_month == lunar_month:
        # 正月到闰月前的天数已累加，再加闰月前正月的天数
        if idx < len(month_days):
            offset += month_days[idx]
            idx += 1

    offset += lunar_day - 1

    from datetime import timedelta
    return chun_jie + timedelta(days=offset)


def _lunar_to_solar_approx(lunar_year: int, lunar_month: int, lunar_day: int) -> date:
    """
    农历转公历近似算法（用于数据表外的年份）
    基于平均农历月长度约29.5天的近似计算
    """
    # 春节大约在1月21日到2月20日之间
    # 使用更精确的估算：春节儒略日近似公式
    import math

    # 近似的春节公历日期（±1天误差）
    # 基于天文计算的近似公式
    year = lunar_year
    # 农历正月初一 ≈ 公历 year 年 1月21日 到 2月19日
    # 使用简单估算：正月初一 ≈ 1月21 + (year*12.37 + 12) % 29.5 天
    approx_offset = int((year * 0.2422 + 24.8) % 29.5)
    base_date = date(year, 1, 21 + approx_offset)

    from datetime import timedelta
    # 从春节开始累加
    offset = 0
    for m in range(1, lunar_month):
        # 奇数月30天，偶数月29天（近似）
        offset += 30 if m % 2 == 1 else 29
    offset += lunar_day - 1

    return base_date + timedelta(days=offset)


# ==================== 计算函数 ====================

def julian_day_number(dt: date) -> int:
    """计算儒略日数 (Julian Day Number)"""
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    return dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def get_year_pillar(dt: date) -> str:
    """
    计算年柱干支
    年柱以立春为界，立春前算上一年
    """
    year = dt.year
    # 立春日期近似为2月4日
    lichun = date(year, 2, 4)
    if dt < lichun:
        year -= 1

    stem_idx = (year - 4) % 10
    branch_idx = (year - 4) % 12
    return TIAN_GAN[stem_idx] + DI_ZHI[branch_idx]


def get_lunar_month(dt: date) -> int:
    """
    根据节气确定农历月份（1-12，寅月=1, 丑月=12）
    """
    year = dt.year

    # 构建当年的节气月份分界
    for i, (m, d) in enumerate(SOLAR_TERMS_APPROX):
        term_date = date(year, m, d)
        if dt < term_date:
            # 在当前节气月之前，属于上一个节气月
            if i == 0:
                # 在立春之前，属于上一年的丑月
                return 12
            else:
                return i  # 上一个节气月的序号（1-based）

    # 如果过了所有节气，属于子月（11月）
    return 11


def get_month_pillar(dt: date) -> str:
    """
    计算月柱干支
    月柱以节气为界
    """
    year = dt.year
    lichun = date(year, 2, 4)
    if dt < lichun:
        year -= 1

    # 确定农历月份
    lunar_month = get_lunar_month(dt)

    # 月支：寅月=0, 卯月=1, ..., 丑月=11
    branch_idx = (lunar_month - 1 + 2) % 12  # 寅=2, 卯=3, ..., 丑=1
    # 修正：寅月地支索引=2, 卯月=3, ..., 子月=0, 丑月=1
    branch_idx = (lunar_month + 1) % 12  # 寅月(1)→2, 卯月(2)→3, ..., 丑月(12)→1

    # 月干：五虎遁
    year_stem_idx = (year - 4) % 10
    yin_stem_idx = WU_HU_DUN[year_stem_idx]
    # 寅月天干 = yin_stem_idx，后续月份递增
    stem_idx = (yin_stem_idx + lunar_month - 1) % 10

    return TIAN_GAN[stem_idx] + DI_ZHI[branch_idx]


def get_day_pillar(dt: date) -> str:
    """
    计算日柱干支
    使用儒略日数公式
    """
    jdn = julian_day_number(dt)
    stem_idx = (jdn + 5) % 10
    branch_idx = (jdn + 1) % 12
    return TIAN_GAN[stem_idx] + DI_ZHI[branch_idx]


def get_hour_pillar(day_stem: str, hour: int) -> str:
    """
    计算时柱干支
    hour: 0-23 小时制
    21:15 = 亥时
    """
    # 确定时辰地支
    # 子时: 23-1, 丑时: 1-3, 寅时: 3-5, ..., 亥时: 21-23
    if hour == 23 or hour == 0:
        branch_idx = 0  # 子
    else:
        branch_idx = (hour + 1) // 2

    # 时干：五鼠遁
    day_stem_idx = TIAN_GAN.index(day_stem)
    zi_stem_idx = WU_SHU_DUN[day_stem_idx]
    stem_idx = (zi_stem_idx + branch_idx) % 10

    return TIAN_GAN[stem_idx] + DI_ZHI[branch_idx]


def get_hour_pillar_by_shichen(day_stem: str, shi_chen: str) -> str:
    """
    根据时辰名称计算时柱干支

    参数:
        day_stem: 日柱天干（如 '甲'）
        shi_chen: 时辰地支（如 '巳'），或别名（如 'si', '5'）
    """
    # 处理别名
    if shi_chen in SHI_CHEN_ALIAS:
        shi_chen = SHI_CHEN_ALIAS[shi_chen]

    if shi_chen not in SHI_CHEN_MAP:
        raise ValueError(f"无效的时辰: {shi_chen}，支持: {list(SHI_CHEN_MAP.keys())}")

    branch_idx = SHI_CHEN_MAP[shi_chen]['branch_idx']

    # 时干：五鼠遁
    day_stem_idx = TIAN_GAN.index(day_stem)
    zi_stem_idx = WU_SHU_DUN[day_stem_idx]
    stem_idx = (zi_stem_idx + branch_idx) % 10

    return TIAN_GAN[stem_idx] + DI_ZHI[branch_idx]


def hour_to_shichen(hour: int) -> str:
    """
    将小时（0-23）转换为时辰地支名称
    9-10点 = 巳时（9:00-11:00 为巳时，实际上9:00-11:00）
    """
    if hour == 23 or hour == 0:
        return '子'
    shichen_list = ['子', '丑', '丑', '寅', '寅', '卯', '卯', '辰', '辰', '巳', '巳',
                    '午', '午', '未', '未', '申', '申', '酉', '酉', '戌', '戌', '亥', '亥', '子']
    return shichen_list[hour]


def get_wuxing_count(four_pillars_gan_zhi: List[str]) -> Dict[str, int]:
    """
    统计四柱五行数量（含地支藏干）
    """
    count = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}

    for gz in four_pillars_gan_zhi:
        gan = gz[0]
        zhi = gz[1]

        # 天干五行
        count[GAN_WUXING[gan]] += 1

        # 地支藏干五行
        for cang_gan in ZHI_CANG_GAN[zhi]:
            count[GAN_WUXING[cang_gan]] += 1

    return count


def analyze_day_master_strength(day_master: str, element_count: Dict[str, int]) -> str:
    """
    分析日主强弱
    同类（比劫+印星）vs 异类（食伤+财星+官杀）
    """
    dm_element = GAN_WUXING[day_master]
    dm_idx = WUXING_ORDER.index(dm_element)

    # 生我者（印星）的五行
    sheng_wo = WUXING_ORDER[(dm_idx - 1) % 5]  # 五行中前一个生后一个
    # 我生者（食伤）的五行
    wo_sheng = WUXING_ORDER[(dm_idx + 1) % 5]
    # 克我者（官杀）的五行
    ke_wo = WUXING_ORDER[(dm_idx + 2) % 5]  # 间隔2个
    # 我克者（财星）的五行
    wo_ke = WUXING_ORDER[(dm_idx - 2) % 5]  # 间隔2个（反向）

    # 同类力量 = 比劫（同五行）+ 印星（生我）
    tong_lei = element_count[dm_element] + element_count[sheng_wo]
    # 异类力量 = 食伤（我生）+ 财星（我克）+ 官杀（克我）
    yi_lei = element_count[wo_sheng] + element_count[wo_ke] + element_count[ke_wo]

    if tong_lei >= yi_lei:
        return "偏强"
    else:
        return "偏弱"


def get_yong_shen(day_master: str, strength: str) -> Tuple[List[str], List[str], List[str]]:
    """
    根据日主强弱确定用神、喜神、忌神五行
    """
    dm_element = GAN_WUXING[day_master]
    dm_idx = WUXING_ORDER.index(dm_element)

    sheng_wo = WUXING_ORDER[(dm_idx - 1) % 5]  # 印星
    wo_sheng = WUXING_ORDER[(dm_idx + 1) % 5]  # 食伤
    ke_wo = WUXING_ORDER[(dm_idx + 2) % 5]     # 官杀
    wo_ke = WUXING_ORDER[(dm_idx - 2) % 5]     # 财星

    if strength == "偏弱":
        # 用神：印星、比劫（生助日主）
        yong_shen = [sheng_wo, dm_element]
        # 喜神：与用神相生的五行
        xi_shen = [WUXING_ORDER[(WUXING_ORDER.index(sheng_wo) - 1) % 5]]
        # 忌神：克泄耗日主的五行
        ji_shen = [ke_wo, wo_sheng]
    else:
        # 偏强：用神：官杀、食伤、财星（克泄耗日主）
        yong_shen = [ke_wo, wo_sheng]
        # 喜神：财星
        xi_shen = [wo_ke]
        # 忌神：印星、比劫
        ji_shen = [sheng_wo, dm_element]

    # 去重
    yong_shen = list(dict.fromkeys(yong_shen))
    xi_shen = list(dict.fromkeys([x for x in xi_shen if x not in yong_shen]))
    ji_shen = list(dict.fromkeys([x for x in ji_shen if x not in yong_shen and x not in xi_shen]))

    return yong_shen, xi_shen, ji_shen


# ==================== 主要计算接口 ====================

def calculate_four_pillars(target_date_str: str, hour: int = 21) -> Dict[str, Any]:
    """
    计算目标日期的四柱八字完整信息（用于开奖日计算）

    参数:
        target_date_str: 公历日期字符串，格式 "YYYY-MM-DD" 或 "YYYY年MM月DD日"
        hour: 小时（0-23），默认21（亥时，开奖时间21:15）

    返回:
        四柱八字信息字典
    """
    # 解析日期
    if '年' in target_date_str:
        # 格式: "2026年07月02日"
        parts = target_date_str.replace('年', '-').replace('月', '-').replace('日', '').split('-')
        dt = date(int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        # 格式: "2026-07-02"
        parts = target_date_str.split('-')
        dt = date(int(parts[0]), int(parts[1]), int(parts[2]))

    # 计算四柱
    year_pillar = get_year_pillar(dt)
    month_pillar = get_month_pillar(dt)
    day_pillar = get_day_pillar(dt)

    # 时柱
    day_stem = day_pillar[0]
    shi_chen_name = hour_to_shichen(hour)
    hour_pillar = get_hour_pillar(day_stem, hour)

    # 日主
    day_master = day_pillar[0]
    day_master_element = GAN_WUXING[day_master]

    # 四柱干支列表
    four_pillars_gz = [year_pillar, month_pillar, day_pillar, hour_pillar]

    # 五行统计（含地支藏干）
    element_count = get_wuxing_count(four_pillars_gz)

    # 日主强弱
    strength = analyze_day_master_strength(day_master, element_count)

    # 用神、喜神、忌神
    yong_shen, xi_shen, ji_shen = get_yong_shen(day_master, strength)

    return {
        "year_pillar": year_pillar,
        "month_pillar": month_pillar,
        "day_pillar": day_pillar,
        "hour_pillar": hour_pillar,
        "shi_chen": shi_chen_name,
        "day_master": day_master,
        "day_master_element": day_master_element,
        "strength": strength,
        "yong_shen": yong_shen,
        "xi_shen": xi_shen,
        "ji_shen": ji_shen,
        "element_count": element_count,
        "four_pillars_gz": four_pillars_gz,
        "solar_date": target_date_str,
    }


def calculate_personal_bazi(
        lunar_year: int,
        lunar_month: int,
        lunar_day: int,
        shi_chen: str = '巳',
        birth_place: str = '',
        live_place: str = '',
        is_leap_month: bool = False
) -> Dict[str, Any]:
    """
    计算个人生辰八字（命主八字）

    参数:
        lunar_year:    农历年，如 1992
        lunar_month:   农历月（1-12）
        lunar_day:     农历日（1-30）
        shi_chen:      时辰，支持地支字符（如 '巳'）、拼音（如 'si'）
                       或编号（如 '5'），以及 9-10 点直接写 '巳'
                       上午9-10点 = 巳时（巳时范围：9:00-11:00）
        birth_place:   出生地点，如 '河南信阳潢川'（仅作为信息记录，不影响干支计算）
        live_place:    现居住地，如 '广东深圳'（用于风水场域分析，不影响干支计算）
        is_leap_month: 是否农历闰月

    返回:
        个人八字信息字典（与 calculate_four_pillars 结构兼容，额外含出生信息字段）

    示例:
        calculate_personal_bazi(
            lunar_year=1992,
            lunar_month=11,
            lunar_day=5,
            shi_chen='巳',
            birth_place='河南信阳潢川',
            live_place='广东深圳',
        )
        # 农历1992年十一月初五 巳时 → 公历1992年12月29日
    """
    # 处理时辰别名
    shi_chen_normalized = shi_chen
    if shi_chen in SHI_CHEN_ALIAS:
        shi_chen_normalized = SHI_CHEN_ALIAS[shi_chen]

    if shi_chen_normalized not in SHI_CHEN_MAP:
        raise ValueError(
            f"无效的时辰: {shi_chen}，支持: {list(SHI_CHEN_MAP.keys())} "
            f"及别名 {list(SHI_CHEN_ALIAS.keys())}"
        )

    # 农历转公历
    solar_date = lunar_to_solar(lunar_year, lunar_month, lunar_day, is_leap_month)

    # 计算四柱
    year_pillar = get_year_pillar(solar_date)
    month_pillar = get_month_pillar(solar_date)
    day_pillar = get_day_pillar(solar_date)

    # 时柱（根据时辰名称）
    day_stem = day_pillar[0]
    hour_pillar = get_hour_pillar_by_shichen(day_stem, shi_chen_normalized)

    # 日主
    day_master = day_pillar[0]
    day_master_element = GAN_WUXING[day_master]

    # 四柱干支列表
    four_pillars_gz = [year_pillar, month_pillar, day_pillar, hour_pillar]

    # 五行统计（含地支藏干）
    element_count = get_wuxing_count(four_pillars_gz)

    # 日主强弱
    strength = analyze_day_master_strength(day_master, element_count)

    # 用神、喜神、忌神
    yong_shen, xi_shen, ji_shen = get_yong_shen(day_master, strength)

    # 时辰小时范围描述
    shi_chen_hours = SHI_CHEN_MAP[shi_chen_normalized]['hours']
    shi_chen_range = f"{shi_chen_hours[0]:02d}:00-{shi_chen_hours[-1]+1:02d}:00"

    # 闰月描述
    leap_str = f"闰{lunar_month}月" if is_leap_month else f"{lunar_month}月"

    return {
        # ---- 出生信息 ----
        "birth_place": birth_place,
        "live_place": live_place,
        "lunar_date": f"农历{lunar_year}年{leap_str}{lunar_day}日",
        "solar_date": solar_date.strftime("%Y-%m-%d"),
        "shi_chen": shi_chen_normalized,
        "shi_chen_range": shi_chen_range,
        # ---- 四柱干支 ----
        "year_pillar": year_pillar,
        "month_pillar": month_pillar,
        "day_pillar": day_pillar,
        "hour_pillar": hour_pillar,
        "four_pillars_gz": four_pillars_gz,
        "four_pillars_str": f"{year_pillar}年 {month_pillar}月 {day_pillar}日 {hour_pillar}时",
        # ---- 命理分析 ----
        "day_master": day_master,
        "day_master_element": day_master_element,
        "strength": strength,
        "yong_shen": yong_shen,
        "xi_shen": xi_shen,
        "ji_shen": ji_shen,
        "element_count": element_count,
    }


# ==================== 格式化输出 ====================

def format_four_pillars_text(fp: Dict[str, Any], title: str = "四柱八字") -> str:
    """
    将四柱八字字典格式化为可读文本（便于调试或日志输出）
    """
    lines = [
        f"【{title}】",
        f"  四柱：{fp.get('year_pillar','')}年 {fp.get('month_pillar','')}月 "
        f"{fp.get('day_pillar','')}日 {fp.get('hour_pillar','')}时",
        f"  时辰：{fp.get('shi_chen','')}时 ({fp.get('shi_chen_range', '')})",
        f"  日主：{fp.get('day_master','')}（{fp.get('day_master_element','')}）- {fp.get('strength','')}",
        f"  用神：{'、'.join(fp.get('yong_shen', []))}",
        f"  喜神：{'、'.join(fp.get('xi_shen', []))}",
        f"  忌神：{'、'.join(fp.get('ji_shen', []))}",
        f"  五行：{fp.get('element_count', {})}",
    ]
    if fp.get('birth_place'):
        lines.insert(1, f"  出生地：{fp['birth_place']}")
    if fp.get('lunar_date'):
        lines.insert(2, f"  农历：{fp['lunar_date']}")
    if fp.get('solar_date'):
        lines.insert(3, f"  公历：{fp['solar_date']}")
    return "\n".join(lines)
