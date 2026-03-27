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
# 共享反干扰规则 — 注入所有 Agent 的 system message
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
2. 在搜索框输入：{hotel}
3. 设置入住：{checkin}，离店：{checkout}
4. 点击搜索
5. 在结果列表中，点击名称最匹配的酒店，进入【酒店详情页】
6. 在详情页找到房型列表，提取最低价格（数字）和房型名称
7. 如果详情页也显示"登录查看价格"，尝试向下滚动查看是否有不需要登录的价格

关键规则：
- 必须进入酒店详情页（不是停留在搜索列表页）
- 价格必须是人民币数字（如 358、1280），不是年份或日期
- 如果弹出登录框或广告，点击关闭按钮
- 同一操作最多重复2次，失败就跳过
- 如果最终无法获取价格，回复 {{"platform": "携程", "hotel_name": "", "lowest_price": 0, "room_type": "", "url": ""}}

成功时用JSON回复：
{{"platform": "携程", "hotel_name": "酒店名", "lowest_price": 价格数字, "room_type": "房型", "url": "当前URL"}}
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
4. 设置入住：{checkin}，离店：{checkout}
5. 点击搜索按钮
6. 在结果中找到名称最匹配的酒店，点击进入详情页
7. 提取最低价格和房型名称

关键规则：
- 不要去"商务合作"、"关于我们"等非搜索页面
- 如果看到的页面不是酒店搜索/结果页，回到第1步重试
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
4. 设置入住：{checkin}，离店：{checkout}
5. 点击搜索按钮
6. 在结果中找到名称最匹配的酒店，点击进入详情页
7. 提取最低价格和房型名称

关键规则：
- 不要直接访问 hotel.ly.com（会返回403）
- 价格必须是人民币酒店房价（如 358、1280），不是年份、不是日期、不是"起"字前面的数字以外的内容
- 注意区分价格和日期：2026是年份不是价格，4/15是日期不是价格
- 如果弹出广告，关闭它
- 遇到验证码直接放弃
- 同一操作最多重复2次
- 不要用搜索引擎绕行

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
