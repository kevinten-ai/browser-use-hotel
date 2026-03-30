"""
平台配置模块 — 数据驱动的多平台比价配置
==========================================
将携程、去哪儿、同程三个平台的配置从 hotel_compare.py 中抽取，
集中管理 URL、提示词模板、反干扰规则等。

使用方式：
    from platform_config import ALL_PLATFORMS, ROBUSTNESS_RULES
"""

from dataclasses import dataclass, field


@dataclass
class PlatformConfig:
    """单个平台的完整配置"""
    name: str               # "携程", "去哪儿", "同程"
    key: str                # "ctrip", "qunar", "tongcheng" (ASCII-safe for file paths)
    urls: list[str]         # primary + fallback URLs
    task_template: str      # prompt template with {hotel}, {checkin}, {checkout}, {url} placeholders
    robustness_hints: str   # platform-specific anti-detection tips


# ========================================
# 共享反干扰规则 — 注入 task prompt 末尾
# ========================================

ROBUSTNESS_RULES = """反干扰规则（高优先级）：
- 如果出现登录弹窗：先尝试点击"X"关闭按钮 → 点击弹窗外区域 → 按ESC键 → 如果仍在，忽略继续操作
- 如果出现验证码/滑块：立即放弃当前路径，报告 captcha 阻塞
- 如果出现"请登录查看价格"：向下滚动查找不需登录的房型价格
- 如果页面加载超过10秒无内容：刷新页面一次
- 不要重复点击同一个按钮超过2次
- 如果某个操作连续失败2次，尝试完全不同的路径
- 关闭所有广告弹窗和推广浮层"""


# ========================================
# 携程配置
# ========================================

CTRIP_CONFIG = PlatformConfig(
    name="携程",
    key="ctrip",
    urls=["https://hotels.ctrip.com/", "https://m.ctrip.com/hotel/"],
    task_template="""去携程搜索酒店价格。

操作步骤：
1. 打开 {url}
2. 在搜索框（目的地/酒店名）输入：{hotel}
3. 设置日期：点击日期区域打开日历，在日历上选择入住日期{checkin}和离店日期{checkout}。注意：不要在日期输入框中直接打字，而是点击日历上的日期数字来选择。
4. 点击搜索按钮
5. 在搜索结果中找到最匹配的酒店
6. 提取价格信息 — 可以从搜索结果列表中直接提取价格，也可以点击进入详情页提取

提取价格的两种方式（任选其一即可）：
- 方式A：搜索结果列表中通常会显示"¥xxx起"的价格，直接提取这个价格
- 方式B：点击酒店名称进入详情页，在房型列表中找最低价

关键规则：
- 如果搜索结果列表已经显示价格，直接提取即可，不必进入详情页
- 价格必须是人民币数字（如 358、1280），不是年份或日期
- 如果被重定向到登录页面，直接导航回 {url} 重新搜索
- 如果弹出登录框或广告，点击关闭按钮
- 同一操作最多重复2次，失败就跳过

成功时用JSON回复：
{{"platform": "携程", "hotel_name": "酒店名", "lowest_price": 价格数字, "room_type": "房型", "url": "当前URL"}}

失败时回复：
{{"platform": "携程", "hotel_name": "", "lowest_price": 0, "room_type": "", "url": ""}}
""",
    robustness_hints="携程经常弹出登录框，优先关闭；搜索框可能有默认文字需要清空",
)


# ========================================
# 去哪儿配置
# ========================================

QUNAR_CONFIG = PlatformConfig(
    name="去哪儿",
    key="qunar",
    urls=["https://hotel.qunar.com/", "https://www.qunar.com/", "https://touch.qunar.com/h5/hotel/"],
    task_template="""去去哪儿网搜索酒店价格。

操作步骤：
1. 打开 {url}
2. 如果页面无法加载或重定向到其他页面，改为打开 https://www.qunar.com/ 然后点击顶部导航栏的"酒店"
3. 在酒店搜索页面：清空搜索框，输入 {hotel}
4. 设置日期：点击日期区域打开日历，选择入住{checkin}和离店{checkout}。如果日历已经显示了默认日期，只需选择正确的日期即可。
5. 点击搜索按钮
6. 在搜索结果中找到最匹配的酒店，提取价格

提取价格的两种方式（任选其一即可）：
- 方式A：搜索结果列表中通常会显示"¥xxx"的价格，直接提取
- 方式B：点击酒店进入详情页提取

关键规则：
- 如果搜索结果列表已经显示价格，直接提取即可
- 价格必须是人民币数字（如 358、1280），不是年份或其他数字
- 搜索框可能有默认文字，先清空再输入
- 如果弹出广告或登录框，关闭它
- 同一操作最多重复2次
- 遇到验证码直接放弃

成功时用JSON回复：
{{"platform": "去哪儿", "hotel_name": "酒店名", "lowest_price": 价格数字, "room_type": "房型", "url": "当前URL"}}

失败时回复：
{{"platform": "去哪儿", "hotel_name": "", "lowest_price": 0, "room_type": "", "url": ""}}
""",
    robustness_hints="去哪儿首页可能重定向，准备多个入口；搜索框有默认城市需清空",
)


# ========================================
# 同程配置
# ========================================

TONGCHENG_CONFIG = PlatformConfig(
    name="同程",
    key="tongcheng",
    urls=["https://www.ly.com/", "https://m.ly.com/hotel/"],
    task_template="""去同程旅行搜索酒店价格。

操作步骤：
1. 打开 {url}
2. 在首页找到"酒店"入口并点击
3. 在酒店搜索页：输入酒店名称 {hotel}
4. 设置日期：点击日期区域，在日历上选择入住{checkin}和离店{checkout}
5. 点击搜索按钮
6. 在搜索结果中找到最匹配的酒店，提取价格

提取价格的两种方式（任选其一即可）：
- 方式A：搜索结果列表中通常会显示"¥xxx"的价格，直接提取
- 方式B：点击酒店进入详情页提取

关键规则：
- 不要直接访问 hotel.ly.com（会返回403）
- 如果搜索结果列表已经显示价格，直接提取即可
- 价格必须是人民币酒店房价（如 358、1280），不是年份、不是日期
- 注意区分价格和日期：2026是年份不是价格，4/15是日期不是价格
- 如果弹出广告，关闭它
- 遇到验证码直接放弃
- 同一操作最多重复2次

成功时用JSON回复：
{{"platform": "同程", "hotel_name": "酒店名", "lowest_price": 价格数字, "room_type": "房型", "url": "当前URL"}}

失败时回复：
{{"platform": "同程", "hotel_name": "", "lowest_price": 0, "room_type": "", "url": ""}}
""",
    robustness_hints="同程不能直接访问 hotel.ly.com（会403），必须从 ly.com 首页进入",
)


# ========================================
# 全部平台列表
# ========================================

ALL_PLATFORMS = [CTRIP_CONFIG, QUNAR_CONFIG, TONGCHENG_CONFIG]
