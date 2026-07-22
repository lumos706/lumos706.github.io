export interface AttractionPlaybook {
  key: string;
  name: string;
  mapLinks: {
    label: string;
    query: string;
  }[];
  time: string;
  sequence: string;
  play: string;
  prepare: string[];
  avoid: string[];
}

export const attractionPlaybooks: AttractionPlaybook[] = [
  {
    key: 'qinghaiLake',
    name: '青海湖',
    mapLinks: [{ label: '二郎剑景区', query: '青海湖二郎剑景区' }],
    time: '半天 · 西宁早出发',
    sequence: '西宁 → 南岸正规入口 → 茶卡',
    play: '不要追求“绕湖一圈”。四人只选一个正规湖区，留出停车、散步和天气变化的时间，再继续去茶卡。',
    prepare: ['防晒、墨镜和挡风外套', '提前看降雨与大风预警', '只在正规停车区上下车'],
    avoid: ['进入私人牧场前不问价格', '为拍照停在路肩或碾压草场', '把两个收费湖区硬塞进同一天'],
  },
  {
    key: 'chakaSaltLake',
    name: '茶卡盐湖',
    mapLinks: [{ label: '天空之镜', query: '茶卡盐湖天空之镜景区' }],
    time: '3–4 小时 · 按预约时段',
    sequence: '茶卡镇 → 景区 → 德令哈方向',
    play: '把小火车当节省体力的选项，不当必打卡项目。天气比滤镜更重要，阴雨或大风时及时缩短停留。',
    prepare: ['墨镜、防晒和可替换袜子', '确认鞋套是否含在票内', '旺季住宿选可取消房型'],
    avoid: ['现场才研究票种和入口', '在盐水中长时间赤脚行走', '为等倒影拖到夜间赶路'],
  },
  {
    key: 'dachaidan',
    name: '大柴旦',
    mapLinks: [
      { label: '翡翠湖', query: '大柴旦翡翠湖旅游景区' },
      { label: '水上雅丹', query: '乌素特水上雅丹地质公园' },
    ],
    time: '半天 · 二选一',
    sequence: '茶卡 → 大柴旦 → 敦煌',
    play: '翡翠湖与水上雅丹二选一。七日路线的核心是安全抵达敦煌，不把盆地里的每个网红点都塞进同一天。',
    prepare: ['出发前加满油并补足水', '下载离线地图', '两位驾驶员轮换'],
    avoid: ['在 U 型公路中央停车拍照', '低估无人路段的距离与信号', '疲劳后继续赶夜路'],
  },
  {
    key: 'mogaoCaves',
    name: '莫高窟',
    mapLinks: [{ label: '数字展示中心', query: '莫高窟数字展示中心' }],
    time: '半天 · 先订票再排路线',
    sequence: '数字展示中心 → 洞窟参观 → 市区休息',
    play: '先锁定官方预约场次，再安排敦煌当天其他项目。到场时间按票面要求倒推，下午给鸣沙山留出休息间隔。',
    prepare: ['只认官方预约渠道', '证件与预约人信息一致', '遵守窟内禁拍与讲解秩序'],
    avoid: ['相信非官方“保证有票”', '把莫高窟和西线景点塞在同一时段', '迟到后再临时改全日路线'],
  },
  {
    key: 'mingshaMountain',
    name: '鸣沙山月牙泉',
    mapLinks: [{ label: '景区入口', query: '鸣沙山月牙泉景区' }],
    time: '傍晚至日落',
    sequence: '酒店休息 → 鸣沙山 → 敦煌夜间用餐',
    play: '避开午后最强日晒，把体力留给登沙坡和日落。骑骆驼、滑沙都是可选项，不影响主线观景。',
    prepare: ['手机和相机做好防沙', '带水但减少一次性垃圾', '入园前确认末班交通'],
    avoid: ['正午长时间暴晒', '在骆驼队行进线上停留拍照', '穿难以清理细沙的鞋袜'],
  },
  {
    key: 'jiayuPass',
    name: '嘉峪关',
    mapLinks: [{ label: '关城景区', query: '嘉峪关关城景区' }],
    time: '2–3 小时 · 只保留关城',
    sequence: '敦煌动车 → 嘉峪关关城 → 张掖',
    play: '七日路线把嘉峪关当河西走廊的中途停靠，只看一个核心点；悬壁长城等外围点留给时间更宽松的行程。',
    prepare: ['预留车站寄存与往返时间', '看清套票包含范围', '按张掖动车倒排行程'],
    avoid: ['为了“套票不浪费”奔波多个点', '低估市区、关城和车站距离', '把最后一班动车当唯一方案'],
  },
  {
    key: 'zhangyeDanxia',
    name: '张掖七彩丹霞',
    mapLinks: [{ label: '北入口', query: '张掖七彩丹霞旅游景区北入口' }],
    time: '3–4 小时 · 早场优先',
    sequence: '张掖市区 → 景区接驳环线 → 兰州',
    play: '按景区接驳顺序走，不逆向追观景台。早场温度更舒服，也更容易给当天回兰州留下缓冲。',
    prepare: ['确认入园口与回程车次', '防晒和补水', '至少留 4 小时衔接交通'],
    avoid: ['跳站后再折返找车', '为了光线赌最后一班接驳', '把阴天色彩当作行程失败'],
  },
];

export const foodRegions = [
  { key: 'xining', city: '西宁', dishes: '手抓羊肉、炕锅、青海酸奶、甜醅', note: '手抓按斤点，四人先问份量；酸奶先买小杯试味。' },
  { key: 'chaka', city: '茶卡', dishes: '炕锅羊肉、牦牛肉、尕面片', note: '旺季先问斤价和等位时间，不为网红店拖到夜间赶路。' },
  { key: 'dachaidan', city: '大柴旦', dishes: '牦牛肉干锅、炕锅、家常面食', note: '补给型城镇口碑波动较大，先核对当日菜单和总价。' },
  { key: 'dunhuang', city: '敦煌', dishes: '驴肉黄面、羊羔肉、合汁、杏皮水', note: '黄面和驴肉常分开计价，热门羊肉店先取号。' },
  { key: 'zhangye', city: '张掖', dishes: '炒炮、卷子鸡、搓鱼面、酿皮', note: '主食份量偏大，四个人先点小份；怕咸就提前说明。' },
  { key: 'lanzhou', city: '兰州', dishes: '牛肉面、酿皮、灰豆子、甜醅', note: '牛肉面安排在早餐或午餐，部分老店下午较早收档。' },
] as const;
