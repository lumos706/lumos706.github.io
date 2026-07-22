export type TripDays = 3 | 4 | 7;
export type BudgetLevel = 2500 | 3000 | 3500;
export type LocalTransportMode = 'drive' | 'public';

export interface DayPlan {
  day: number;
  route: string;
  summary: string;
  transport: string;
  stay: string;
  distance: string;
  caution?: string;
}

export interface BudgetBreakdown {
  lodging: number;
  transport: number;
  tickets: number;
  food: number;
  reserve: number;
}

export interface BudgetVariant {
  name: string;
  total: number;
  transportMode: string;
  lodgingStandard: string;
  note: string;
  breakdown: BudgetBreakdown;
}

export interface RoutePlan {
  days: TripDays;
  name: string;
  recommendation: string;
  description: string;
  entryExit: string;
  distance: string;
  highestStay: string;
  transportMix: string;
  routeCode: string;
  stations: string[];
  daysList: DayPlan[];
  budgetVariants: Record<BudgetLevel, BudgetVariant>;
}

export const budgetLabels: Record<BudgetLevel, string> = {
  2500: '轻省档',
  3000: '均衡档',
  3500: '舒展档',
};

export const transportLabels: Record<LocalTransportMode, { label: string; note: string }> = {
  drive: { label: '自驾（租车）', note: '四人分摊 · 偏远路段更自由' },
  public: { label: '公共交通', note: '动车 / 客运 / 公交 / 打车' },
};

const driveRoutePlans: Record<TripDays, RoutePlan> = {
  3: {
    days: 3,
    name: '西宁短线',
    recommendation: '只看青海，不硬塞甘肃',
    description: '三天包含沈阳往返，只适合把西宁和青海湖走稳。茶卡、敦煌与张掖全部留到下一次，避免第二天往返六七百公里。',
    entryExit: '西宁进 / 西宁出',
    distance: '约 420 km',
    highestStay: '2,275 m',
    transportMix: '机场巴士 + 1 天租车',
    routeCode: 'QH / 03',
    stations: ['沈阳', '西宁', '青海湖', '塔尔寺', '沈阳'],
    daysList: [
      {
        day: 1,
        route: '沈阳 → 西宁',
        summary: '桃仙机场出发。若西宁直飞价格明显偏高，比较兰州落地后动车进西宁，但三天方案不要安排夜间长途自驾。',
        transport: '飞机 / 动车备选',
        stay: '住西宁',
        distance: '市内短途',
        caution: '抵达高原第一晚降低活动强度，少饮酒、及时补水。',
      },
      {
        day: 2,
        route: '西宁 → 青海湖 → 西宁',
        summary: '早取车，走青海湖南岸。只选一个收费湖区，把停车、散步与天气变化的时间留足，天黑前回西宁。',
        transport: '四人共享租车',
        stay: '住西宁',
        distance: '约 300 km / 5 h',
        caution: '湖边风大且紫外线强；不要把车停在非正规观景路肩。',
      },
      {
        day: 3,
        route: '塔尔寺 → 西宁机场 → 沈阳',
        summary: '按返程航班倒排塔尔寺时段。早班机则取消景点，直接去机场，不用最后半天赌堵车。',
        transport: '短途租车 / 机场巴士',
        stay: '行程结束',
        distance: '约 70 km',
        caution: '至少提前两小时到机场；异地还车规则必须在取车时确认。',
      },
    ],
    budgetVariants: {
      2500: {
        name: '轻省档',
        total: 1680,
        transportMode: '机场巴士 + 1 天经济型租车',
        lodgingStandard: '西宁 ¥180–240 / 间夜',
        note: '余量较大，可优先留给往返机票波动；不增加茶卡往返。',
        breakdown: { lodging: 350, transport: 610, tickets: 260, food: 300, reserve: 160 },
      },
      3000: {
        name: '均衡档',
        total: 2080,
        transportMode: '紧凑型轿车 + 机场接驳',
        lodgingStandard: '西宁 ¥240–320 / 间夜',
        note: '酒店位置和青海湖停车便利度更好，仍不建议临时增加茶卡。',
        breakdown: { lodging: 460, transport: 750, tickets: 320, food: 360, reserve: 190 },
      },
      3500: {
        name: '舒展档',
        total: 2440,
        transportMode: '舒适型轿车 + 弹性接送',
        lodgingStandard: '西宁 ¥320–420 / 间夜',
        note: '把预算用于更稳妥的航班时段和住宿，不用用新增景点填满行程。',
        breakdown: { lodging: 580, transport: 870, tickets: 360, food: 400, reserve: 230 },
      },
    },
  },
  4: {
    days: 4,
    name: '青海湖小环线',
    recommendation: '推荐 · 第一次看青海',
    description: '四天可以在青海湖与茶卡之间住一晚，再从容回西宁。仍不跨到敦煌，因为把甘肃塞进来只会变成长距离打卡。',
    entryExit: '西宁进 / 西宁出',
    distance: '约 720 km',
    highestStay: '3,100 m',
    transportMix: '2 天租车 + 机场接驳',
    routeCode: 'QH / 04',
    stations: ['沈阳', '西宁', '青海湖', '茶卡', '西宁'],
    daysList: [
      {
        day: 1,
        route: '沈阳 → 西宁',
        summary: '抵达后只安排东关一带散步与补给。当天确认租车证件、保险、轮胎和第二天的天气。',
        transport: '飞机 / 动车备选',
        stay: '住西宁',
        distance: '市内短途',
        caution: '不要在到达当晚洗过久的热水澡或剧烈运动。',
      },
      {
        day: 2,
        route: '西宁 → 青海湖 → 茶卡',
        summary: '沿青海湖南岸前进，下午继续到茶卡。日落是否停留看天气，不为拍照拖到夜间赶路。',
        transport: '四人共享租车',
        stay: '住茶卡',
        distance: '约 300 km / 5 h',
        caution: '茶卡住宿旺季波动大，优先选可取消房型并核对是否有电梯。',
      },
      {
        day: 3,
        route: '茶卡盐湖 → 西宁',
        summary: '按预约时段进盐湖，午后返回西宁。途中只设置一个正规服务区休息，不把网红路肩当景点。',
        transport: '四人共享租车',
        stay: '住西宁',
        distance: '约 300 km / 4.5 h',
        caution: '盐湖反光强，墨镜、防晒和鞋套都要提前准备。',
      },
      {
        day: 4,
        route: '塔尔寺 → 西宁机场 → 沈阳',
        summary: '中晚班机可安排塔尔寺；早班机直接返程。返程当天不进入偏远山区。',
        transport: '短途交通 + 飞机',
        stay: '行程结束',
        distance: '约 70 km',
        caution: '遇到降雨或航班变动，塔尔寺是第一项可删内容。',
      },
    ],
    budgetVariants: {
      2500: {
        name: '轻省档',
        total: 2180,
        transportMode: '2 天经济型轿车 + 机场巴士',
        lodgingStandard: '西宁 / 茶卡 ¥180–260 / 间夜',
        note: '能控制在档位内，但茶卡旺季房价一旦上涨，应先换可取消住宿而不是压缩安全预算。',
        breakdown: { lodging: 480, transport: 750, tickets: 300, food: 420, reserve: 230 },
      },
      3000: {
        name: '均衡档',
        total: 2680,
        transportMode: '2 天紧凑型轿车 + 灵活接驳',
        lodgingStandard: '西宁 / 茶卡 ¥240–340 / 间夜',
        note: '在预算内保留约 ¥320 余量，适合覆盖旺季住宿与停车费波动。',
        breakdown: { lodging: 650, transport: 900, tickets: 370, food: 480, reserve: 280 },
      },
      3500: {
        name: '舒展档',
        total: 3180,
        transportMode: '舒适型轿车 + 更宽松取还车',
        lodgingStandard: '西宁 / 茶卡 ¥320–450 / 间夜',
        note: '预算余量约 ¥320，优先升级茶卡住宿和航班时段，不增加夜路。',
        breakdown: { lodging: 840, transport: 1050, tickets: 400, food: 540, reserve: 350 },
      },
    },
  },
  7: {
    days: 7,
    name: '青甘走廊线',
    recommendation: '推荐 · 一头进一头出',
    description: '从西宁进入高原，在敦煌把节奏放慢，再沿河西走廊回到兰州。七天不硬塞祁连，避免每天都在赶路。',
    entryExit: '西宁进 / 兰州出',
    distance: '约 1,720 km',
    highestStay: '约 3,100 m',
    transportMix: '租车分段 + 动车',
    routeCode: 'QG / 07',
    stations: ['沈阳', '西宁', '茶卡', '大柴旦', '敦煌', '张掖', '兰州'],
    daysList: [
      {
        day: 1,
        route: '沈阳 → 兰州 → 西宁',
        summary: '桃仙机场出发；若西宁直飞价格偏高，优先比较兰州落地后动车进西宁。当天不取车跑长途。',
        transport: '飞机 + 动车',
        stay: '住西宁',
        distance: '城际接驳',
        caution: '晚到西宁时只完成入住与补给，取消夜间景点。',
      },
      {
        day: 2,
        route: '西宁 → 青海湖 → 茶卡',
        summary: '早取车，从青海湖南岸前往茶卡。日落前完成入住，不把两个收费湖区都塞进同一天。',
        transport: '四人共享租车',
        stay: '住茶卡',
        distance: '约 300 km / 5 h',
        caution: '湖边风大、温差大；只在正规停车区停留。',
      },
      {
        day: 3,
        route: '茶卡 → 德令哈 → 大柴旦',
        summary: '上午盐湖，下午穿过柴达木盆地。进入长距离路段前补足油、水、食物与离线地图。',
        transport: '四人共享租车',
        stay: '住大柴旦',
        distance: '约 410 km / 6 h',
        caution: '驾驶员至少两人轮换；疲劳时立即在正规服务区休息。',
      },
      {
        day: 4,
        route: '大柴旦 → 敦煌',
        summary: '翡翠湖与水上雅丹只选其一，把时间留给安全抵达敦煌。U 型公路只通过，不停车拍照。',
        transport: '四人共享租车',
        stay: '住敦煌',
        distance: '约 360 km / 5 h',
        caution: '无人路段信号不稳定，出发前下载离线导航并告知住宿方预计到达时间。',
      },
      {
        day: 5,
        route: '莫高窟 → 鸣沙山月牙泉',
        summary: '莫高窟按官方预约时段进场，午后回酒店休息，傍晚再去鸣沙山避开最强日晒。',
        transport: '市内公交 / 打车',
        stay: '住敦煌',
        distance: '约 50 km',
        caution: '先订莫高窟再锁定当天行程，不通过非官方渠道购买承诺票。',
      },
      {
        day: 6,
        route: '敦煌 → 嘉峪关 → 张掖',
        summary: '结束长途租车，换动车串联河西走廊。嘉峪关只保留一个核心点，晚上到张掖。',
        transport: '动车为主',
        stay: '住张掖',
        distance: '约 580 km 城际',
        caution: '单向还车费必须与动车票总价比较；费用过高时提前一天还车。',
      },
      {
        day: 7,
        route: '七彩丹霞 → 兰州 → 沈阳',
        summary: '早场看丹霞，午后动车回兰州。返程机票过早时，应在兰州多留一晚而不是压缩公路段。',
        transport: '动车 + 飞机',
        stay: '行程结束',
        distance: '约 520 km 城际',
        caution: '当天衔接至少留 4 小时；没有合适航班就把返程放到第 8 天。',
      },
    ],
    budgetVariants: {
      2500: {
        name: '轻省档',
        total: 2680,
        transportMode: '动车 + 正规拼车 / 短租组合',
        lodgingStandard: '¥180–260 / 间夜，可取消优先',
        note: '预计超出档位 ¥180，且对旺季房价很敏感。建议至少增加 ¥200–400，不能靠减少保险或夜间赶路省钱。',
        breakdown: { lodging: 780, transport: 720, tickets: 380, food: 560, reserve: 240 },
      },
      3000: {
        name: '均衡档',
        total: 3180,
        transportMode: '3 天租车 + 动车分段',
        lodgingStandard: '¥240–340 / 间夜，位置优先',
        note: '预计超出档位 ¥180。若每日快照显示茶卡或大柴旦房价上涨，优先加预算，不删安全余量。',
        breakdown: { lodging: 960, transport: 850, tickets: 450, food: 630, reserve: 290 },
      },
      3500: {
        name: '舒展档',
        total: 3480,
        transportMode: '5 天共享租车 + 河西动车',
        lodgingStandard: '¥320–450 / 间夜，停车便利',
        note: '推荐档位，预计余 ¥20。预算紧贴上限，往返机票与落地费用必须分开核算。',
        breakdown: { lodging: 1080, transport: 920, tickets: 520, food: 630, reserve: 330 },
      },
    },
  },
};

const publicRoutePlans: Record<TripDays, RoutePlan> = {
  3: {
    days: 3,
    name: '西宁轻装线',
    recommendation: '不开车 · 只保留稳妥接驳',
    description: '三天不租车时，把跨城变量压到最低：青海湖选择正规旅游直通车往返，市内用公交或打车补最后一段。茶卡与甘肃全部留到下一次。',
    entryExit: '西宁进 / 西宁出',
    distance: '约 300 km 城际接驳',
    highestStay: '2,275 m',
    transportMix: '景区直通车 + 公交 / 打车',
    routeCode: 'QH / 03 / PT',
    stations: ['沈阳', '西宁', '青海湖', '西宁', '沈阳'],
    daysList: [
      {
        day: 1,
        route: '沈阳 → 西宁',
        summary: '桃仙机场出发，抵达后乘机场巴士或正规网约车进城。入住后确认第二天青海湖直通车的集合点、返程时间和退改规则。',
        transport: '飞机 + 机场巴士 / 打车',
        stay: '住西宁',
        distance: '市内接驳',
        caution: '不要接受到达层拉客拼车；只用官方售票点或正规平台下单。',
      },
      {
        day: 2,
        route: '西宁 ⇄ 青海湖二郎剑',
        summary: '选择旅游集散中心或正规旅行社的往返直通车，只停一个正规湖区。订票时确认是否含门票、是否强制购物，以及返程集合时间。',
        transport: '景区直通车 / 正规一日团',
        stay: '住西宁',
        distance: '往返约 300 km',
        caution: '公共班次受季节和客流影响，前一晚再次核对集合点，不临时追私人牧场。',
      },
      {
        day: 3,
        route: '西宁市区 → 西宁机场 → 沈阳',
        summary: '中晚班机可用公交或打车安排东关街区短暂停留；早班机直接去机场，不再跨城或去塔尔寺。',
        transport: '公交 / 打车 + 飞机',
        stay: '行程结束',
        distance: '市内短途',
        caution: '公共交通换乘要比导航时间多留 30–45 分钟，至少提前两小时到机场。',
      },
    ],
    budgetVariants: {
      2500: {
        name: '轻省档',
        total: 1400,
        transportMode: '机场巴士 + 青海湖往返直通车 + 少量公交',
        lodgingStandard: '西宁 ¥180–240 / 间夜',
        note: '不含沈阳往返机票，余量优先留给直通车价格和航班波动。',
        breakdown: { lodging: 350, transport: 320, tickets: 260, food: 300, reserve: 170 },
      },
      3000: {
        name: '均衡档',
        total: 1780,
        transportMode: '正规直通车 + 机场接驳 + 市内打车分摊',
        lodgingStandard: '西宁 ¥240–320 / 间夜',
        note: '四人可在早晚接驳使用打车，减少拖行李换乘，但仍不增加茶卡。',
        breakdown: { lodging: 460, transport: 430, tickets: 320, food: 360, reserve: 210 },
      },
      3500: {
        name: '舒展档',
        total: 2160,
        transportMode: '小团直通车 + 市内打车 + 弹性接送',
        lodgingStandard: '西宁 ¥320–420 / 间夜',
        note: '预算用于更稳的接送和住宿位置，而不是临时购买来源不明的包车。',
        breakdown: { lodging: 580, transport: 560, tickets: 360, food: 400, reserve: 260 },
      },
    },
  },
  4: {
    days: 4,
    name: '西宁慢游线',
    recommendation: '不开车 · 青海湖当天往返',
    description: '四天公共交通方案不强行串茶卡：青海湖用正规直通车往返，塔尔寺和西宁市区用公交、打车衔接。少一个网红点，换来不追末班车的余量。',
    entryExit: '西宁进 / 西宁出',
    distance: '约 380 km 城际接驳',
    highestStay: '2,275 m',
    transportMix: '直通车 + 公交 / 打车',
    routeCode: 'QH / 04 / PT',
    stations: ['沈阳', '西宁', '青海湖', '塔尔寺', '西宁'],
    daysList: [
      {
        day: 1,
        route: '沈阳 → 西宁',
        summary: '抵达后用机场巴士或正规网约车进城，只安排入住和补给。前一晚确认青海湖直通车是否成团及集合位置。',
        transport: '飞机 + 机场巴士 / 打车',
        stay: '住西宁',
        distance: '市内接驳',
        caution: '高原第一晚不安排长距离步行，酒店优先选靠近次日集合点的位置。',
      },
      {
        day: 2,
        route: '西宁 ⇄ 青海湖二郎剑',
        summary: '乘正规景区直通车当天往返，只进一个官方收费景区。把集合点、返程时刻和是否含门票截图保存。',
        transport: '景区直通车 / 正规一日团',
        stay: '住西宁',
        distance: '往返约 300 km',
        caution: '不要购买承诺随停随拍、实际在公路路肩上下客的低价拼车。',
      },
      {
        day: 3,
        route: '塔尔寺 → 西宁市区',
        summary: '公交可到景区周边但耗时较长，四人更适合公交去、正规打车回，或直接往返打车分摊。下午回市区休息和吃饭。',
        transport: '公交 + 打车分摊',
        stay: '住西宁',
        distance: '往返约 60 km',
        caution: '导航给出的公交班次可能临时调整，返程不要卡最后一班。',
      },
      {
        day: 4,
        route: '西宁市区 → 西宁机场 → 沈阳',
        summary: '按航班时间选择机场巴士或打车。行李多时，四人打车分摊通常比多次公交换乘更省力。',
        transport: '机场巴士 / 打车 + 飞机',
        stay: '行程结束',
        distance: '市内接驳',
        caution: '给早高峰和机场安检留足缓冲，不把最后半天排成刚性景点。',
      },
    ],
    budgetVariants: {
      2500: {
        name: '轻省档',
        total: 1940,
        transportMode: '青海湖直通车 + 公交为主 + 两次打车分摊',
        lodgingStandard: '西宁 ¥180–260 / 间夜',
        note: '不含往返机票；茶卡不在公共交通四日方案中，避免为赶班次额外包车。',
        breakdown: { lodging: 480, transport: 520, tickets: 300, food: 420, reserve: 220 },
      },
      3000: {
        name: '均衡档',
        total: 2440,
        transportMode: '正规直通车 + 公交 / 打车灵活组合',
        lodgingStandard: '西宁 ¥240–340 / 间夜',
        note: '保留约 ¥560 余量，应对暑期直通车、打车和住宿涨价。',
        breakdown: { lodging: 650, transport: 680, tickets: 350, food: 480, reserve: 280 },
      },
      3500: {
        name: '舒展档',
        total: 2980,
        transportMode: '小团直通车 + 多段打车分摊 + 机场接送',
        lodgingStandard: '西宁 ¥320–450 / 间夜',
        note: '四人用正规打车补足最后一公里，仍比来源不明的全程包车更容易核对。',
        breakdown: { lodging: 840, transport: 860, tickets: 390, food: 540, reserve: 350 },
      },
    },
  },
  7: {
    days: 7,
    name: '河西公共交通线',
    recommendation: '不开车 · 用铁路替代柴达木长途',
    description: '公共交通七日线不进入班次稀疏的大柴旦：青海湖当天往返西宁，再用动车串联张掖、嘉峪关和敦煌。路线少走一段荒漠公路，也少看茶卡与大柴旦。',
    entryExit: '西宁进 / 兰州出',
    distance: '约 1,900 km 铁路与接驳',
    highestStay: '2,275 m',
    transportMix: '动车 / 火车 + 景区直通车 + 打车',
    routeCode: 'QG / 07 / PT',
    stations: ['沈阳', '西宁', '青海湖', '张掖', '嘉峪关', '敦煌', '兰州'],
    daysList: [
      {
        day: 1,
        route: '沈阳 → 兰州 / 西宁',
        summary: '优先比较直飞西宁与飞兰州后动车进西宁。晚到只入住，不在陌生城市继续追末班公交。',
        transport: '飞机 + 动车 / 机场接驳',
        stay: '住西宁',
        distance: '城际接驳',
        caution: '机票和动车分开购买时，至少留 3 小时衔接余量。',
      },
      {
        day: 2,
        route: '西宁 ⇄ 青海湖二郎剑',
        summary: '乘正规景区直通车往返，不安排茶卡过夜。回西宁后住在靠近车站的位置，为次日动车留余量。',
        transport: '景区直通车 / 正规一日团',
        stay: '住西宁',
        distance: '往返约 300 km',
        caution: '确认返程集合点和是否购物；若当天不发车，宁可改市内行程。',
      },
      {
        day: 3,
        route: '西宁 → 张掖 → 七彩丹霞',
        summary: '上午动车到张掖，寄存行李后用景区直通车或正规打车去丹霞。日落场可能错过市区末班接驳，提前准备返程方案。',
        transport: '动车 + 景区专线 / 打车',
        stay: '住张掖',
        distance: '约 350 km 城际',
        caution: '日落时间与返程班次冲突时，四人打车分摊比在景区外临时找车更稳。',
      },
      {
        day: 4,
        route: '张掖 → 嘉峪关关城',
        summary: '动车到嘉峪关后先寄存行李，再用公交或打车去关城。当天只看关城，不串悬壁长城等外围点。',
        transport: '动车 + 公交 / 打车',
        stay: '住嘉峪关',
        distance: '约 230 km 城际',
        caution: '嘉峪关站、嘉峪关南站和市区不是同一地点，下单前核对到达站。',
      },
      {
        day: 5,
        route: '嘉峪关 → 敦煌 → 鸣沙山',
        summary: '乘火车或客运到敦煌，入住后按体力决定是否去鸣沙山看日落。市区到景区优先公交，散场后可四人打车回。',
        transport: '火车 / 客运 + 公交 / 打车',
        stay: '住敦煌',
        distance: '约 370 km 城际',
        caution: '到敦煌较晚就取消鸣沙山，不把景区关门时间当成最后返程时间。',
      },
      {
        day: 6,
        route: '敦煌市区 → 莫高窟 → 兰州方向',
        summary: '按票面时间先到莫高窟数字展示中心，市区用官方直通车、公交或正规打车接驳。参观后回市区，再乘夜间列车前往兰州方向。',
        transport: '景区接驳 + 夜间火车',
        stay: '夜间列车 / 兰州',
        distance: '约 1,100 km 铁路',
        caution: '公交线路和班次按季节调整，不能只凭旧攻略写死车次；以当天地图与官方通知复核。',
      },
      {
        day: 7,
        route: '兰州 → 沈阳',
        summary: '夜间列车到兰州后给进站、取行李和机场接驳留足余量。若衔接过紧，就把返程顺延一天。',
        transport: '火车 + 机场接驳 + 飞机',
        stay: '行程结束',
        distance: '城际接驳',
        caution: '公共交通方案最怕连续延误，不购买无法改签的极限衔接组合。',
      },
    ],
    budgetVariants: {
      2500: {
        name: '轻省档',
        total: 2740,
        transportMode: '硬座 / 二等座 + 景区直通车 + 公交为主',
        lodgingStandard: '¥180–260 / 间夜，可取消优先',
        note: '预计超出档位 ¥240。公共交通不是四人出行的绝对低价方案，不能靠极限换乘压缩安全余量。',
        breakdown: { lodging: 780, transport: 780, tickets: 380, food: 560, reserve: 240 },
      },
      3000: {
        name: '均衡档',
        total: 3220,
        transportMode: '动车二等座 + 正规直通车 + 四人打车分摊',
        lodgingStandard: '¥240–340 / 间夜，车站接驳优先',
        note: '预计超出档位 ¥220。多城换乘的打车和行李寄存要单独留钱。',
        breakdown: { lodging: 960, transport: 880, tickets: 450, food: 630, reserve: 300 },
      },
      3500: {
        name: '舒展档',
        total: 3640,
        transportMode: '动车 / 卧铺 + 景区直通车 + 打车弹性',
        lodgingStandard: '¥320–450 / 间夜，靠近车站或集合点',
        note: '预计超出档位 ¥140。预算换来少拖行李和少追末班车，但仍需接受茶卡、大柴旦不在路线内。',
        breakdown: { lodging: 1080, transport: 1050, tickets: 520, food: 630, reserve: 360 },
      },
    },
  },
};

export const routePlans: Record<LocalTransportMode, Record<TripDays, RoutePlan>> = {
  drive: driveRoutePlans,
  public: publicRoutePlans,
};

export const defaultSelection = {
  days: 7 as TripDays,
  budget: 3500 as BudgetLevel,
  transport: 'drive' as LocalTransportMode,
};
