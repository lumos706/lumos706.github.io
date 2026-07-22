export type TripDays = 3 | 4 | 7;
export type BudgetLevel = 2500 | 3000 | 3500;

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

export const routePlans: Record<TripDays, RoutePlan> = {
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

export const defaultSelection = {
  days: 7 as TripDays,
  budget: 3500 as BudgetLevel,
};
