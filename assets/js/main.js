(function () {
  const header = document.querySelector("[data-header]");
  const toggle = document.querySelector("[data-nav-toggle]");
  const nav = document.querySelector("[data-nav]");
  const headerActions = document.querySelector(".header-actions");
  const siteData = { hero_slides: [], home_metrics: [], vehicles: [], parts: [], catalog_terms: [], forum_posts: [], settings: {}, page_sections: [], page_media: [], exchangeRate: null, currentForumPost: null };
  const backgroundVideoControllers = new WeakMap();
  const deferredMediaLoads = new WeakMap();
  const deferredMediaTargets = new WeakMap();
  const mediaLoadObserver = window.IntersectionObserver ? new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      mediaLoadObserver.unobserve(entry.target);
      const load = deferredMediaLoads.get(entry.target);
      deferredMediaLoads.delete(entry.target);
      if (load) load();
    });
  }, { rootMargin: "240px 0px" }) : null;

  function whenMediaNearViewport(node, load) {
    // Moving photo walls need their offscreen tiles ready before scrolling.
    if (node.closest("[data-page-media-eager]")) {
      load();
      return;
    }
    const target = node.hidden ? (node.parentElement || node) : node;
    const rect = target.getBoundingClientRect();
    if (!mediaLoadObserver || (rect.top < window.innerHeight + 240 && rect.bottom > -240)) {
      load();
    } else {
      // Observe the layout container: hidden images have no intersection box.
      deferredMediaLoads.set(target, load);
      deferredMediaTargets.set(node, target);
      mediaLoadObserver.observe(target);
    }
  }
  const publicAuth = {
    token: "",
    user: null
  };
  const DEFAULT_LANG = "zh";
  const supportedLangs = ["ru", "zh", "en"];

  function getInitialLang() {
    const stored = localStorage.getItem("tlhdd-lang");
    const userSelected = localStorage.getItem("tlhdd-lang-user-set") === "true";
    if (userSelected && supportedLangs.includes(stored)) return stored;
    return DEFAULT_LANG;
  }

  let activeLang = getInitialLang();
  let accountMenu;
  let usedPage = Math.max(1, parseInt(new URLSearchParams(location.search).get("page"), 10) || 1);
  let newPage = Math.max(1, parseInt(new URLSearchParams(location.search).get("page"), 10) || 1);
  let partPage = Math.max(1, parseInt(new URLSearchParams(location.search).get("page"), 10) || 1);
  let partListState = { items: [], total: 0, page: partPage, pageSize: 12, totalPages: 1, loading: false, error: "", loaded: false, requestId: 0 };
  const usedFilters = { brand: "", model: "", id: "", price: "", year: "", mileage: "" };
  let userCenterState = { token: "", loading: false, inquiries: [], posts: [], threads: [], error: "" };
  const VEHICLE_PAGE_SIZE = 12;
  const PART_PAGE_SIZE = 12;
  const partCategoryCopy = {
    engine: { zh: "发动机件", en: "Engine Parts", ru: "Детали двигателя" },
    chassis: { zh: "底盘件", en: "Chassis Parts", ru: "Детали шасси" },
    body: { zh: "车身件", en: "Body Parts", ru: "Кузовные детали" },
    electric: { zh: "电器件", en: "Electrical Parts", ru: "Электрика" },
    service: { zh: "保养易损件", en: "Service Parts", ru: "Расходники" },
    accessory: { zh: "汽车用品", en: "Accessories", ru: "Аксессуары" }
  };
  const forumCategoryCopy = {
    general: { zh: "选车咨询", en: "Model Advice", ru: "Подбор авто" },
    used: { zh: "二手车", en: "Used Cars", ru: "Авто с пробегом" },
    new: { zh: "新车", en: "New Cars", ru: "Новые авто" },
    logistics: { zh: "物流出口", en: "Logistics", ru: "Логистика" },
    options: { zh: "配置选装", en: "Options", ru: "Опции" },
    faq: { zh: "常见问题", en: "FAQ", ru: "Вопросы" }
  };
  const forumCategoryOrder = ["general", "used", "new", "logistics", "options", "faq"];
  const forumUploadTypes = ["image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm", "video/quicktime"];
  const forumUploadExts = [".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm", ".mov"];
  const FORUM_UPLOAD_MAX_BYTES = 50 * 1024 * 1024;

  async function requestJson(url, options = {}, errorMessage = "请求失败") {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || errorMessage);
    return payload;
  }

  const pageIndex = [
    { href: "news.html", zh: "新闻中心", en: "News Center", ru: "Новости", descZh: "公司资讯、汽车业务与服务介绍", descEn: "Company articles and automotive services", descRu: "Статьи о компании и автомобильных услугах", keys: "新闻 资讯 news articles новости" },
    { href: "index.html", zh: "首页", en: "Home", ru: "Главная", descZh: "公司首页、轮播图、业务概览", descEn: "Homepage, carousel and services", descRu: "Главная, слайдер и услуги", keys: "首页 home главная 轮播 业务" },
    { href: "about.html", zh: "走进通利华", en: "About", ru: "О нас", descZh: "公司介绍、发展历程、服务网络和企业文化", descEn: "Company profile, history, network and values", descRu: "О компании, истории, сети и принципах сервиса", keys: "关于 公司 通利华汽车集团 about о нас" },
    { href: "new-cars.html", zh: "新车出口", en: "New Car Export", ru: "Экспорт новых авто", descZh: "新车采购、车型匹配、订单、单证与交付", descEn: "New car sourcing, matching, export documents and delivery", descRu: "Подбор, закупка, документы и доставка новых авто", keys: "新车 销售 出口 new car новый автомобиль" },
    { href: "used-cars.html", zh: "二手车出口", en: "Used Car Export", ru: "Экспорт авто", descZh: "二手车收购、评估、销售与出口车源组织", descEn: "Used car acquisition, appraisal, sales and export sourcing", descRu: "Выкуп, оценка, продажа и экспорт авто с пробегом", keys: "二手车 业务 出口 used car 检测 подержанный автомобиль" },
    { href: "car-options.html", zh: "汽车选装", en: "Car Options", ru: "Опции автомобиля", descZh: "雪地胎、电动侧踏、电动尾门和车衣选装", descEn: "Winter tires, power steps, tailgates and wraps", descRu: "Зимние шины, подножки, багажник и пленка", keys: "汽车选装 配置 雪地胎 车衣 options аксессуары" },
    { href: "transportation.html", zh: "物流运输", en: "Logistics", ru: "Логистика", descZh: "汽运、海运、铁运、运输追踪与保险", descEn: "Road, sea and rail shipping, tracking and insurance", descRu: "Авто, морские и железнодорожные перевозки, отслеживание", keys: "物流 运输 汽运 海运 铁运 logistics транспорт" },
    { href: "purchase-plan.html", zh: "购买方案", en: "Purchase Plan", ru: "План покупки", descZh: "从报价、合同、付款到出口与交付的购买流程", descEn: "Quotation, contract, payment, export and delivery", descRu: "Цена, договор, оплата, экспорт и доставка", keys: "购买方案 购车 流程 付款 purchase plan покупка" },
    { href: "service-center.html", zh: "服务中心", en: "Service Center", ru: "Сервисный центр", descZh: "售后维修、保养、零配件和服务咨询", descEn: "After-sales, maintenance, parts and support", descRu: "Сервис, ремонт, запчасти и консультации", keys: "服务中心 售后 保养 维修 service center сервис" },
  ];

  const primaryNavHrefs = [
    "index.html",
    "about.html",
    "new-cars.html",
    "used-cars.html",
    "car-options.html",
    "transportation.html",
    "purchase-plan.html"
  ];

  const primaryNavIcons = {
    "index.html": "house",
    "about.html": "building-2",
    "new-cars.html": "car-front",
    "used-cars.html": "badge-check",
    "car-options.html": "wrench",
    "transportation.html": "truck",
    "purchase-plan.html": "clipboard-list"
  };

  const langLabels = { ru: "Русский", zh: "中文", en: "English" };
  const dataSuffix = { zh: "Zh", en: "En", ru: "Ru" };
  const pageTitles = {
    home: {
      zh: "通利华汽车集团 | 首页",
      en: "Tonglihua Automotive Group | Home",
      ru: "Автомобильная группа Tonglihua | Главная"
    },
    about: {
      zh: "走进通利华汽车集团 | 通利华汽车集团",
      en: "About Tonglihua Automotive Group",
      ru: "О группе Tonglihua"
    },
    "new-cars": {
      zh: "新车销售与出口 | 通利华汽车集团",
      en: "New Car Sales and Export | Tonglihua",
      ru: "Продажа и экспорт новых авто | Tonglihua"
    },
    "new-car-detail": {
      zh: "新车详情 | 通利华汽车集团",
      en: "New Car Detail | Tonglihua Automotive Group",
      ru: "Детали нового авто | Tonglihua"
    },
    "used-cars": {
      zh: "二手车收购与销售 | 通利华汽车集团",
      en: "Used Car Acquisition and Sales | Tonglihua",
      ru: "Выкуп и продажа авто с пробегом | Tonglihua"
    },
    "used-car-detail": {
      zh: "二手车详情 | 通利华汽车集团",
      en: "Used Car Detail | Tonglihua Automotive Group",
      ru: "Детали авто с пробегом | Tonglihua"
    },
    "car-options": { zh: "汽车选装 | 通利华汽车集团", en: "Car Options | Tonglihua", ru: "Опции автомобиля | Tonglihua" },
    transportation: { zh: "物流运输 | 通利华汽车集团", en: "Logistics | Tonglihua", ru: "Логистика | Tonglihua" },
    "purchase-plan": { zh: "购买方案 | 通利华汽车集团", en: "Purchase Plan | Tonglihua", ru: "План покупки | Tonglihua" },
    "service-center": { zh: "服务中心 | 通利华汽车集团", en: "Service Center | Tonglihua", ru: "Сервисный центр | Tonglihua" },
    "part-detail": {
      zh: "配件详情 | 通利华汽车集团",
      en: "Part Detail | Tonglihua Automotive Group",
      ru: "Детали запчасти | Tonglihua"
    },
    contact: {
      zh: "联系我们 | 通利华汽车集团",
      en: "Contact | Tonglihua Automotive Group",
      ru: "Контакты | Tonglihua"
    },
    "user-center": {
      zh: "用户中心 | 通利华汽车集团",
      en: "User Center | Tonglihua Automotive Group",
      ru: "Центр пользователя | Tonglihua"
    }
  };

  const staticCopy = {
    "通利华叮叮": { en: "Tonglihua Automotive Group", ru: "Автомобильная группа Tonglihua" },
    "通利华汽车集团": { en: "Tonglihua Automotive Group", ru: "Автомобильная группа Tonglihua" },
    "汽车出口公司": { en: "Tonglihua Automotive Group", ru: "Автомобильная группа Tonglihua" },
    "可对接车型资源": { en: "Available vehicle resources", ru: "Доступные автомобильные ресурсы" },
    "需求响应与方案确认": { en: "Fast request response and plan confirmation", ru: "Быстрый ответ и подтверждение плана" },
    "集团成立年份": { en: "Group founded", ru: "Год основания группы" },
    "注册资本（元）": { en: "Registered capital (RMB)", ru: "Уставный капитал (юани)" },
    "直营服务网络": { en: "Direct service network", ru: "Прямая сеть сервисов" },
    "专业服务人才": { en: "Professional employees", ru: "Профессиональные сотрудники" },
    "我们的业务": { en: "Our Services", ru: "Наши услуги" },
    "新车销售": { en: "New Car Sales", ru: "Продажа новых авто" },
    "二手车业务": { en: "Used Car Services", ru: "Авто с пробегом" },
    "新闻中心": { en: "News Center", ru: "Новости" },
    "服务中心": { en: "Service Center", ru: "Сервисный центр" },
    "具体车型配置以经销商实车为准": { en: "Vehicle specifications are subject to the actual vehicle at the dealership.", ru: "Комплектация уточняется по фактическому автомобилю у дилера." },
    "集团动态与汽车服务资讯": { en: "Group updates and automotive service news", ru: "Новости группы и автомобильного сервиса" },
    "售后维修、保养与零配件支持": { en: "After-sales, maintenance and parts support", ru: "Сервис, обслуживание и запчасти" },
    "零配件供应": { en: "Parts Supply", ru: "Поставка запчастей" },
    "汽车进出口": { en: "Vehicle Import and Export", ru: "Импорт и экспорт автомобилей" },
    "出行与充电": { en: "Mobility and Charging", ru: "Мобильность и зарядка" },
    "新车出口": { en: "New Car Export", ru: "Экспорт новых авто" },
    "二手车出口": { en: "Used Car Export", ru: "Экспорт авто с пробегом" },
    "二手车服务": { en: "Used Car Services", ru: "Авто с пробегом" },
    "汽车选装": { en: "Car Options", ru: "Опции автомобиля" },
    "物流运输": { en: "Logistics", ru: "Логистика" },
    "购买方案": { en: "Purchase Plan", ru: "План покупки" },
    "二手车产品专区": { en: "Used Vehicle Catalog", ru: "Каталог авто с пробегом" },
    "询盘服务": { en: "Inquiry Service", ru: "Сервис запросов" },
    "以汽车服务为核心，打造人、车、生活、科技一体化服务平台": { en: "An integrated platform for people, vehicles, life and technology", ru: "Единая платформа для людей, автомобилей, жизни и технологий" },
    "通利华汽车集团以汽车服务为核心，覆盖新车销售、售后服务、零配件供应、二手车、汽车进出口、出行与充电服务。": { en: "Tonglihua Automotive Group covers new-car sales, after-sales, parts supply, used cars, vehicle import and export, mobility and charging services.", ru: "Группа Tonglihua развивает продажи новых авто, сервис, запчасти, автомобили с пробегом, импорт и экспорт, мобильность и зарядку." },
    "客户为中心": { en: "Customer First", ru: "Клиент в центре" },
    "专业服务": { en: "Professional Service", ru: "Профессиональный сервис" },
    "持续成长": { en: "Continuous Growth", ru: "Постоянный рост" },
    "把车型、预算和目的地发给我们，先给你一版可执行方案。": { en: "Send us the model, budget and destination, and we will prepare an actionable plan.", ru: "Отправьте модель, бюджет и пункт назначения, мы подготовим рабочий план." },
    "立即咨询": { en: "Contact Now", ru: "Связаться сейчас" },
    "走进通利华叮叮": { en: "About Tonglihua Automotive Group", ru: "О группе Tonglihua" },
    "走进通利华汽车集团": { en: "About Tonglihua Automotive Group", ru: "О группе Tonglihua" },
    "通利华汽车集团成立于1994年，注册资本5440万元，是以汽车服务为核心的综合汽车服务企业。": { en: "Founded in 1994 with registered capital of RMB 54.4 million, Tonglihua Automotive Group is an integrated automotive service company.", ru: "Основанная в 1994 году с уставным капиталом 54,4 млн юаней группа Tonglihua является комплексной автомобильной сервисной компанией." },
    "通利华汽车集团拥有40余家直营服务网络和超过2000名专业员工，平均年龄28岁。": { en: "The group operates more than 40 direct service locations with over 2,000 professionals and an average employee age of 28.", ru: "Группа имеет более 40 прямых сервисных площадок и более 2000 специалистов, средний возраст сотрудников - 28 лет." },
    "公司业务覆盖新车销售、售后服务、零配件供应、二手车收购与销售、汽车进出口、出行、充电和司机之家。": { en: "Business covers new-car sales, after-sales, parts supply, used-car acquisition and sales, vehicle import and export, mobility, charging and driver services.", ru: "Бизнес включает продажи новых авто, сервис, запчасти, выкуп и продажу авто с пробегом, импорт и экспорт, мобильность, зарядку и сервис для водителей." },
    "我们的服务原则": { en: "Our Service Principles", ru: "Наши принципы сервиса" },
    "真实车况": { en: "Real Vehicle Condition", ru: "Реальное состояние авто" },
    "流程透明": { en: "Transparent Process", ru: "Прозрачный процесс" },
    "长期合作": { en: "Long-term Cooperation", ru: "Долгосрочное сотрудничество" },
    "从需求到交付的协同能力": { en: "Coordination from request to delivery", ru: "Координация от запроса до выдачи" },
    "联系我们": { en: "Contact Us", ru: "Контакты" },
    "欢迎提交车型、数量、目的地和预算，我们会根据需求回复出口方案。": { en: "Send the model, quantity, destination and budget. We will reply with an export plan.", ru: "Отправьте модель, количество, пункт назначения и бюджет. Мы подготовим экспортное предложение." },
    "把你的需求": { en: "Send Your", ru: "Отправьте" },
    "发给通利华叮叮": { en: "Request to Tonglihua Automotive Group", ru: "запрос в группу Tonglihua" },
    "为了更快给到报价，请尽量提供车型、配置、数量、目的地、期望交付时间和是否需要选装或物流服务。": { en: "For a faster quote, provide model, configuration, quantity, destination, delivery time and whether options or logistics are needed.", ru: "Для быстрой цены укажите модель, комплектацию, количество, пункт назначения, срок выдачи, опции и логистику." },
    "姓名 / 称呼": { en: "Name", ru: "Имя" },
    "联系方式": { en: "Contact", ru: "Контакты" },
    "目的地": { en: "Destination", ru: "Пункт назначения" },
    "预算范围": { en: "Budget Range", ru: "Бюджет" },
    "意向车型 / 服务": { en: "Vehicle / Service", ru: "Авто / услуга" },
    "需求说明": { en: "Message", ru: "Сообщение" },
    "提交询盘": { en: "Submit Inquiry", ru: "Отправить запрос" },
    "提交后会进入后台询盘管理，业务人员可跟进状态和备注。": { en: "After submission, our team can follow up in the inquiry system.", ru: "После отправки запрос попадет в систему, менеджер сможет продолжить работу." },
    "绥芬河口岸服务区域": { en: "Suifenhe Port Service Area", ru: "Зона обслуживания порта Суйфэньхэ" },
    "可在此处替换为企业地图、门店照片或仓储口岸实景图。": { en: "This area can be replaced with a map, office photo or warehouse/port image.", ru: "Здесь можно разместить карту, фото офиса, склада или порта." },
    "业务导航": { en: "Navigation", ru: "Навигация" },
    "联系信息": { en: "Contact Info", ru: "Контакты" },
    "专注汽车出口采购、选装、物流和交付服务。": { en: "Making car life better through vehicle sales, after-sales, parts, used cars, import and export, mobility and charging.", ru: "Делаем автомобильную жизнь лучше: продажи, сервис, запчасти, авто с пробегом, импорт и экспорт, мобильность и зарядка." },
    "电话：请补充实际号码": { en: "Phone: +8615323454449 Mr. Zhang", ru: "Телефон: +8615323454449, г-н Чжан" },
    "地址：黑龙江省绥芬河市": { en: "Address: Shenzhen, with 40+ direct service locations nationwide", ru: "Адрес: Шэньчжэнь, более 40 собственных площадок по стране" },
    "邮箱：请补充企业邮箱": { en: "Email: zhangxiandong@szddcx.cn", ru: "Email: zhangxiandong@szddcx.cn" },
    "服务时间：周一至周六 09:00-18:00": { en: "Hours: Mon-Sat 09:00-18:00", ru: "Время работы: Пн-Сб 09:00-18:00" },
    "车型论坛": { en: "Vehicle Forum", ru: "Форум автомобилей" },
    "发布车型": { en: "Publish Vehicle", ru: "Опубликовать авто" },
    "登录后可以发布自己的车型": { en: "Sign in to publish your vehicle", ru: "Войдите, чтобы опубликовать автомобиль" },
    "登录后发布": { en: "Sign in to publish", ru: "Войти для публикации" },
    "登录后发布车型": { en: "Sign in to publish", ru: "Войти для публикации" },
    "用户中心": { en: "User Center", ru: "Центр пользователя" },
    "请先登录账户": { en: "Please sign in first", ru: "Сначала войдите в аккаунт" },
    "登录后可以管理个人资料、查看询盘记录和车型论坛内容。": { en: "After signing in, you can manage profile, inquiries and forum posts.", ru: "После входа можно управлять профилем, запросами и публикациями." }
  };

  const placeholderCopy = {
    "搜索品牌、车型、排量、公里数": { en: "Search brand, model, engine, mileage", ru: "Поиск: бренд, модель, двигатель, пробег" },
    "搜索标题、品牌、车型、作者": { en: "Search title, brand, model, author", ru: "Поиск: заголовок, бренд, модель, автор" },
    "搜索标题、品牌、车型、作者或出口问题": { en: "Search title, brand, model, author or export question", ru: "Поиск: заголовок, бренд, модель, автор или вопрос" },
    "请输入联系人称呼": { en: "Enter contact name", ru: "Введите имя" },
    "电话、微信或邮箱": { en: "Phone, WeChat or email", ru: "Телефон, WeChat или email" },
    "国家 / 城市": { en: "Country / City", ru: "Страна / город" },
    "例如 20-30 万": { en: "e.g. 200,000-300,000", ru: "например 200-300 тыс." },
    "车型、新车出口、二手车出口、选装或物流": { en: "Model, new/used car export, options or logistics", ru: "Модель, новые/б/у авто, опции или логистика" },
    "车型、数量、目的地、预算、交付时间等": { en: "Model, quantity, destination, budget, delivery time", ru: "Модель, количество, пункт назначения, бюджет, срок" },
    "例如：Toyota RAV4 2.0L 车型体验": { en: "e.g. Toyota RAV4 2.0L review", ru: "например: опыт Toyota RAV4 2.0L" },
    "写下车辆配置、车况、使用场景、采购需求或出口经验": { en: "Describe configuration, condition, use case, sourcing or export experience", ru: "Опишите комплектацию, состояние, задачу, закупку или опыт экспорта" },
    "写下车辆配置、车况、采购需求或出口经验": { en: "Describe configuration, condition, sourcing needs or export experience", ru: "Опишите комплектацию, состояние, запрос или опыт экспорта" },
    "输入车型、物流、选装或栏目名称": { en: "Search cars, parts, logistics or pages", ru: "Введите авто, запчасти, логистику или раздел" },
    "目的地、预算、数量或配置需求": { en: "Destination, budget, quantity or configuration needs", ru: "Пункт назначения, бюджет, количество или комплектация" }
  };

  function pickLang(source, base) {
    if (!source) return "";
    const key = base ? `${base}${dataSuffix[activeLang]}` : activeLang;
    const fallback = base ? `${base}Zh` : "zh";
    return source[key] || source[fallback] || "";
  }

  function sectionValue(section, field) {
    if (!section) return "";
    return section[`${field}_${activeLang}`] || section[`${field}_zh`] || "";
  }

  function setCmsText(node, section, field) {
    if (!node || !section) return;
    [["zh", "Zh"], ["en", "En"], ["ru", "Ru"]].forEach(function ([lang, suffix]) {
      const value = section[`${field}_${lang}`] || "";
      if (value) node.dataset[`text${suffix}`] = value;
    });
    const text = sectionValue(section, field);
    if (text) node.textContent = text;
  }

  function localizedValue(source, fallback = "") {
    if (!source) return fallback;
    return source[activeLang] || source.zh || fallback;
  }

  function forumCategoryLabel(category) {
    const key = forumCategoryCopy[category] ? category : "general";
    return localizedValue(forumCategoryCopy[key], forumCategoryCopy.general.zh);
  }

  function forumCategoryOptions(current = "general") {
    return forumCategoryOrder.map(function (category) {
      const selected = category === current ? " selected" : "";
      return `<option value="${category}"${selected}>${escapeHtml(forumCategoryLabel(category))}</option>`;
    }).join("");
  }

  function activeForumCategory() {
    return document.querySelector("[data-forum-category].is-active")?.dataset.forumCategory || "";
  }

  function setActiveForumCategory(category) {
    document.querySelectorAll("[data-forum-category]").forEach(function (button) {
      const active = (button.dataset.forumCategory || "") === category;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  function forumUploadCopy(key) {
    const copy = {
      uploading: { zh: "正在上传", en: "Uploading", ru: "Загрузка" },
      uploaded: { zh: "已上传", en: "Uploaded", ru: "Загружено" },
      remove: { zh: "移除", en: "Remove", ru: "Удалить" },
      image: { zh: "图片", en: "Photo", ru: "Фото" },
      video: { zh: "视频", en: "Video", ru: "Видео" },
      tooLarge: { zh: "单个文件不能超过 50MB", en: "Each file must be under 50MB", ru: "Файл должен быть до 50MB" },
      invalid: { zh: "仅支持 jpg、png、webp 图片和 mp4、webm、mov 视频", en: "Only jpg, png, webp images and mp4, webm, mov videos are supported", ru: "Поддерживаются jpg, png, webp и видео mp4, webm, mov" },
      signIn: { zh: "登录后可以上传图片和视频", en: "Sign in to upload photos and videos", ru: "Войдите, чтобы загрузить фото и видео" }
    };
    return localizedValue(copy[key], copy[key]?.zh || "");
  }

  function parseForumMedia(form) {
    const field = form?.elements?.media_json;
    if (!field) return [];
    try {
      const value = JSON.parse(field.value || "[]");
      return Array.isArray(value) ? value.filter((item) => item && item.url) : [];
    } catch (error) {
      return [];
    }
  }

  function writeForumMedia(form, media) {
    const field = form?.elements?.media_json;
    if (field) field.value = JSON.stringify(media || []);
    renderForumMediaPreview(form);
  }

  function renderForumMediaPreview(form) {
    if (!form) return;
    const list = form.querySelector("[data-forum-media-list]");
    if (!list) return;
    const media = parseForumMedia(form);
    list.innerHTML = media.map(function (item, index) {
      const isVideo = item.type === "video";
      const label = isVideo ? forumUploadCopy("video") : forumUploadCopy("image");
      const name = item.name || item.url.split("/").pop() || label;
      return `
        <article class="forum-media-item">
          ${isVideo
            ? `<video src="${escapeHtml(item.url)}" muted playsinline preload="metadata"></video>`
            : `<img alt="" src="${escapeHtml(item.url)}">`}
          <div><strong>${escapeHtml(label)}</strong><span>${escapeHtml(name)}</span></div>
          <button type="button" data-forum-media-remove="${index}" aria-label="${escapeHtml(forumUploadCopy("remove"))}">${icon("x")}</button>
        </article>
      `;
    }).join("");
    if (window.lucide) window.lucide.createIcons();
  }

  async function uploadForumMediaFile(file) {
    if (!publicAuth.user) {
      openAccountLogin();
      throw new Error(forumUploadCopy("signIn"));
    }
    const ext = `.${(file.name || "").split(".").pop() || ""}`.toLowerCase();
    if (!forumUploadTypes.includes(file.type) && !forumUploadExts.includes(ext)) throw new Error(forumUploadCopy("invalid"));
    if (file.size > FORUM_UPLOAD_MAX_BYTES) throw new Error(forumUploadCopy("tooLarge"));
    const body = new FormData();
    body.append("file", file);
    return requestJson("/api/forum/uploads", {
      method: "POST",
      credentials: "same-origin",
      body
    });
  }

  async function handleForumMediaUpload(input) {
    const form = input.closest("form");
    const note = form?.querySelector("[data-forum-media-note]");
    const files = Array.from(input.files || []);
    if (!form || !files.length) return;
    try {
      if (note) {
        note.classList.remove("is-success");
        note.textContent = `${forumUploadCopy("uploading")} ${files.length}`;
      }
      const current = parseForumMedia(form);
      const uploaded = [];
      for (const file of files) {
        uploaded.push(await uploadForumMediaFile(file));
      }
      writeForumMedia(form, current.concat(uploaded));
      if (note) {
        note.classList.add("is-success");
        note.textContent = `${forumUploadCopy("uploaded")} ${uploaded.length}`;
      }
    } catch (error) {
      if (note) {
        note.classList.remove("is-success");
        note.textContent = error.message;
      }
    } finally {
      input.value = "";
    }
  }

  function forumMediaUploaderHtml() {
    return ''
      + '<div class="forum-media-uploader" data-forum-media-uploader>'
      + '<input type="hidden" name="media_json" value="[]">'
      + '<input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime" multiple data-forum-media-upload>'
      + '<div class="forum-upload-head"><div>'
      + '<strong>' + escapeHtml(({ zh: "上传图片 / 视频", en: "Upload Photos / Videos", ru: "Загрузить фото / видео" })[activeLang]) + '</strong>'
      + '<p>' + escapeHtml(({ zh: "支持多张图片和视频，单个文件不超过 50MB，每日额度 200MB。", en: "Multiple photos and videos are supported. Max 50MB per file and 200MB per day.", ru: "Фото и видео: до 50MB на файл и до 200MB в день." })[activeLang]) + '</p>'
      + '</div><button type="button" data-forum-media-trigger>' + icon("upload-cloud") + '<span>'
      + escapeHtml(({ zh: "选择文件", en: "Select Files", ru: "Выбрать файлы" })[activeLang])
      + '</span></button></div>'
      + '<div class="forum-media-preview" data-forum-media-list></div>'
      + '<p class="form-note" data-forum-media-note></p>'
      + '</div>';
  }

  function rememberOriginalText(node) {
    const key = node.dataset.staticTextKey || node.textContent.trim();
    if (staticCopy[key]) {
      node.dataset.staticTextKey = key;
      return key;
    }
    return "";
  }

  function translateStaticCopy() {
    document.querySelectorAll("h1,h2,h3,p,span,a,button,label span,li").forEach(function (node) {
      if (node.children.length || node.closest("[data-no-auto-translate]")) return;
      if (node.closest(".site-nav")) return;
      if (node.dataset.textZh || node.dataset.langLabel || node.dataset.accountBadge) return;
      const key = rememberOriginalText(node);
      if (!key) return;
      node.textContent = localizedValue(staticCopy[key], key);
    });
  }

  function applyTranslatedDataAttributes() {
    document.querySelectorAll("[data-text-zh]").forEach(function (node) {
      const value = node.dataset[`text${dataSuffix[activeLang]}`] || node.dataset.textZh;
      if (value) node.textContent = value;
    });
  }

  function setDynamicLocalizedText(node, value) {
    if (!node) return;
    node.dataset.textZh = value;
    node.dataset.textEn = value;
    node.dataset.textRu = value;
    node.textContent = value;
  }

  function translatePlaceholders() {
    document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach(function (field) {
      const key = field.dataset.placeholderKey || field.getAttribute("placeholder");
      if (!placeholderCopy[key]) return;
      field.dataset.placeholderKey = key;
      field.setAttribute("placeholder", localizedValue(placeholderCopy[key], key));
    });
  }

  function updatePageTitle() {
    const pageKey = document.body.dataset.page || "home";
    const title = pageTitles[pageKey];
    const isDynamicDetail = ["new-car-detail", "used-car-detail", "part-detail"].includes(pageKey);
    if (title && !(isDynamicDetail && document.querySelector("[data-current-vehicle-title], [data-current-forum-title], [data-current-part-title]")?.textContent?.trim())) {
      document.title = localizedValue(title, document.title);
    }
  }

  function icon(name) {
    return `<i data-lucide="${name}"></i>`;
  }

  function syncPrimaryNav() {
    if (!nav) return;
    nav.innerHTML = primaryNavHrefs.map(function (href) {
      const item = pageIndex.find(function (page) { return page.href === href; });
      return `<a href="${href}"><i class="nav-item-icon" data-lucide="${primaryNavIcons[href]}" aria-hidden="true"></i><span class="nav-item-label">${item ? item.zh : href}</span></a>`;
    }).join("");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function cssImage(value) {
    const url = String(value || "").trim();
    if (!url) return "none";
    return `url('${url.replaceAll("\\", "\\\\").replaceAll("'", "\\'")}')`;
  }

  function isVideoMediaUrl(value) {
    return /\.(mp4|webm)(?:[?#].*)?$/i.test(String(value || "").trim());
  }

  function syncBackgroundVideoPlayback(video, container, activeOnly = false) {
    let controller = backgroundVideoControllers.get(video);
    if (!controller) {
      controller = { visible: !window.IntersectionObserver, observer: null, update: null };
      controller.update = function () {
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const isActive = !activeOnly || container.classList.contains("is-active");
        if (controller.visible && !document.hidden && !reducedMotion && isActive && video.isConnected) {
          const playback = video.play();
          if (playback && typeof playback.catch === "function") playback.catch(function () {});
        } else {
          video.pause();
        }
      };
      if (window.IntersectionObserver) {
        controller.observer = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.target !== video) return;
            controller.visible = entry.isIntersecting;
            controller.update();
          });
        }, { threshold: 0.12 });
        controller.observer.observe(video);
      }
      document.addEventListener("visibilitychange", controller.update);
      video.addEventListener("loadeddata", controller.update);
      backgroundVideoControllers.set(video, controller);
    }
    controller.update();
  }

  function removeManagedBackgroundVideo(video) {
    const controller = backgroundVideoControllers.get(video);
    if (controller) {
      controller.observer?.disconnect();
      document.removeEventListener("visibilitychange", controller.update);
      video.removeEventListener("loadeddata", controller.update);
      backgroundVideoControllers.delete(video);
    }
    video.pause();
    video.removeAttribute("src");
    video.load();
    video.remove();
  }

  function createBackgroundVideo(url, poster, className, marker) {
    const video = document.createElement("video");
    video.className = className;
    video.dataset[marker] = "true";
    video.src = url;
    if (poster) video.poster = poster;
    video.muted = true;
    video.defaultMuted = true;
    video.loop = true;
    video.playsInline = true;
    video.preload = "metadata";
    video.setAttribute("aria-hidden", "true");
    video.setAttribute("tabindex", "-1");
    return video;
  }

  function derivativeImageUrl(url, suffix) {
    const text = String(url || "").trim();
    // CDN URLs retain the uploads path (optionally below a storage prefix).
    if (!text || !/^(?:\/uploads\/|https:\/\/[^?#]+\/uploads\/)/i.test(text)) return "";
    if (/-thumb\.webp$|-optimized\.webp$/i.test(text)) return text;
    if (!/\.(jpe?g|png|webp)$/i.test(text)) return "";
    return text.replace(/\.(jpe?g|png|webp)$/i, "-" + suffix + ".webp");
  }

  function cardImageUrl(item) {
    return item?.thumb_url || derivativeImageUrl(item?.image_url, "thumb") || item?.image_url || "";
  }

  function optimizedImageUrl(url) {
    return derivativeImageUrl(url, "optimized") || url || "";
  }

  function thumbImageUrl(url) {
    return derivativeImageUrl(url, "thumb") || url || "";
  }

  function renderRichText(value) {
    const text = String(value || "").trim();
    if (!text) return "";
    return text
      .split(/\n{2,}/)
      .map(function (paragraph) {
        return `<p>${escapeHtml(paragraph.trim()).replace(/\n/g, "<br>")}</p>`;
      })
      .join("");
  }

  function imageUrlFromCss(value) {
    const match = String(value || "").match(/url\((['"]?)(.*?)\1\)/);
    return match ? match[2] : "";
  }

  function hydrateImageFallbacks(root = document) {
    root.querySelectorAll("[style*='--car-image'], [style*='--gallery-image'], [style*='--thumb-image']").forEach(function (node) {
      const value = node.style.getPropertyValue("--car-image")
        || node.style.getPropertyValue("--gallery-image")
        || node.style.getPropertyValue("--thumb-image");
      const url = imageUrlFromCss(value);
      if (!url || url.startsWith("data:")) return;
      node.classList.add("is-image-loading");
      const probe = new Image();
      probe.onload = function () {
        node.classList.remove("is-image-loading");
        node.classList.remove("is-image-missing");
      };
      probe.onerror = function () {
        const fallback = node.dataset.fallbackImage;
        if (fallback && fallback !== url) {
          node.dataset.fallbackImage = "";
          if (node.style.getPropertyValue("--car-image")) node.style.setProperty("--car-image", cssImage(fallback));
          if (node.style.getPropertyValue("--gallery-image")) node.style.setProperty("--gallery-image", cssImage(fallback));
          if (node.style.getPropertyValue("--thumb-image")) node.style.setProperty("--thumb-image", cssImage(fallback));
          hydrateImageFallbacks(node.parentElement || node);
          return;
        }
        node.classList.remove("is-image-loading");
        node.classList.add("is-image-missing");
      };
      probe.src = url;
    });
  }

  function usableSetting(value) {
    const text = String(value || "").trim();
    return text && !text.includes("请补充") ? text : "";
  }

  function whatsappHref(value) {
    const text = usableSetting(value);
    if (!text) return "";
    if (/^https?:\/\//i.test(text)) return text;
    const digits = text.replace(/[^\d]/g, "");
    return digits ? `https://wa.me/${digits}` : "";
  }

  function applySiteSettings() {
    const settings = siteData.settings || {};
    const companyName = settings.company_name || "通利华汽车集团";
    const phone = settings.phone || "+8615323454449 张先生";
    const email = settings.email || "zhangxiandong@szddcx.cn";
    const address = settings.address || "深圳市（全国40余家直营网络）";
    const serviceHours = settings.service_hours || "周一至周六 09:00-18:00";
    const contactLabels = {
      zh: { phone: "电话", email: "邮箱", address: "地址", hours: "服务时间" },
      en: { phone: "Phone", email: "Email", address: "Address", hours: "Hours" },
      ru: { phone: "Телефон", email: "Email", address: "Адрес", hours: "Время работы" }
    }[activeLang];
    const settingDefaults = {
      "请补充实际号码": { en: "+8615323454449 Mr. Zhang", ru: "+8615323454449, г-н Чжан" },
      "请补充企业邮箱": { en: "zhangxiandong@szddcx.cn", ru: "zhangxiandong@szddcx.cn" },
      "黑龙江省绥芬河市": { en: "Shenzhen, 40+ direct service locations nationwide", ru: "Шэньчжэнь, более 40 собственных площадок по стране" },
      "周一至周六 09:00-18:00": { en: "Mon-Sat 09:00-18:00", ru: "Пн-Сб 09:00-18:00" }
    };
    const phoneText = localizedValue(settingDefaults[phone], phone);
    const emailText = localizedValue(settingDefaults[email], email);
    const addressText = localizedValue(settingDefaults[address], address);
    const serviceHoursText = localizedValue(settingDefaults[serviceHours], serviceHours);

    let customStyle = document.querySelector("#tlhdd-custom-css");
    if (!customStyle) {
      customStyle = document.createElement("style");
      customStyle.id = "tlhdd-custom-css";
      document.head.appendChild(customStyle);
    }
    customStyle.textContent = settings.custom_css || "";

    let notice = document.querySelector("[data-site-notice]");
    if (settings.site_notice) {
      if (!notice) {
        notice = document.createElement("div");
        notice.className = "site-notice";
        notice.setAttribute("data-site-notice", "");
        document.body.insertBefore(notice, document.body.firstElementChild);
      }
      notice.textContent = settings.site_notice;
    } else if (notice) {
      notice.remove();
    }

    if (document.body.dataset.page === "index" && settings.seo_title) {
      document.title = settings.seo_title;
    }
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription && settings.seo_description) {
      metaDescription.setAttribute("content", settings.seo_description);
    }

    document.querySelectorAll(".site-footer .footer-grid > div:first-child p").forEach(function (node) {
      node.textContent = settings.footer_note || "让车生活更精彩。通利华汽车集团覆盖新车、售后、零配件、二手车、汽车进出口、出行、充电和司机之家。";
    });
    document.querySelectorAll(".site-footer .footer-grid > div:last-child").forEach(function (column) {
      const lines = column.querySelectorAll("p");
      if (lines[0]) lines[0].textContent = `${contactLabels.phone}: ${phoneText}`;
      if (lines[1]) lines[1].textContent = `${contactLabels.address}: ${addressText}`;
      if (lines[2]) lines[2].textContent = `${contactLabels.email}: ${emailText}`;
    });
    const contactValues = { phone: phoneText, email: emailText, address: addressText };
    document.querySelectorAll("[data-site-contact]").forEach(function (node) {
      const value = contactValues[node.dataset.siteContact];
      if (value) node.textContent = value;
    });
    document.querySelectorAll(".footer-bottom span:first-child").forEach(function (node) {
      node.textContent = `© ${new Date().getFullYear()} ${companyName}`;
    });
    document.querySelectorAll(".brand-text strong").forEach(function (node) {
      node.textContent = companyName;
    });
    document.querySelectorAll(".brand-text small").forEach(function (node) {
      node.textContent = "TONGLIHUA AUTOMOTIVE GROUP";
    });

    document.querySelectorAll("[data-used-catalog-title]").forEach(function (node) {
      node.textContent = settings.used_catalog_title || "二手车产品专区";
    });
    document.querySelectorAll("[data-used-catalog-intro]").forEach(function (node) {
      node.textContent = settings.used_catalog_intro || "";
    });

    const methods = document.querySelectorAll(".contact-methods div span");
    if (methods[0]) methods[0].textContent = `${contactLabels.phone}: ${phoneText}`;
    if (methods[1]) methods[1].textContent = `${contactLabels.email}: ${emailText}`;
    if (methods[2]) methods[2].textContent = `${contactLabels.address}: ${addressText}`;
    if (methods[3]) methods[3].textContent = `${contactLabels.hours}: ${serviceHoursText}`;

    document.querySelectorAll(".header-contact").forEach(function (link) {
      link.href = "contact.html";
    });
    document.querySelectorAll(".floating-contact").forEach(function (link) {
      link.href = whatsappHref(settings.whatsapp) || "contact.html";
      link.setAttribute("aria-label", `联系${companyName}`);
    });

    const params = new URLSearchParams(location.search);
    const vehicleFromUrl = params.get("vehicle") || params.get("model") || "";
    if (vehicleFromUrl) {
      document.querySelectorAll("[data-contact-form] [name='vehicle_interest']").forEach(function (field) {
        if (!field.value) field.value = vehicleFromUrl;
      });
    }
  }

  function applyPageSections() {
    const pageKey = document.body.dataset.page || "index";
    const sections = (siteData.page_sections || []).filter(function (section) {
      return section.page_key === pageKey && section.is_active !== false;
    });
    if (!sections.length) return;
    const byKey = {};
    sections.forEach(function (section) {
      byKey[section.section_key] = section;
    });

    const hero = byKey.hero;
    if (hero) {
      const heroNode = document.querySelector(".page-hero");
      const eyebrow = heroNode ? heroNode.querySelector(".eyebrow") : null;
      const title = heroNode ? heroNode.querySelector("h1") : null;
      const lead = heroNode ? heroNode.querySelector(".hero-lead") : null;
      if (eyebrow && hero.eyebrow) eyebrow.textContent = hero.eyebrow;
      setCmsText(title, hero, "title");
      setCmsText(lead, hero, "body");
      if (heroNode && hero.image_url) {
        const existingVideo = heroNode.querySelector(":scope > [data-cms-hero-video]");
        if (isVideoMediaUrl(hero.image_url)) {
          heroNode.style.setProperty("--hero-image", "none");
          let video = existingVideo;
          if (!video || video.dataset.source !== hero.image_url) {
            if (video) removeManagedBackgroundVideo(video);
            video = createBackgroundVideo(hero.image_url, "/assets/images/hero-placeholder.webp", "cms-hero-video", "cmsHeroVideo");
            video.dataset.source = hero.image_url;
            heroNode.insertBefore(video, heroNode.firstElementChild);
          }
          syncBackgroundVideoPlayback(video, heroNode);
        } else {
          if (existingVideo) removeManagedBackgroundVideo(existingVideo);
          heroNode.style.setProperty("--hero-image", cssImage(hero.image_url));
        }
      }
    }

    const catalog = byKey.catalog;
    if (catalog) {
      document.querySelectorAll("[data-used-catalog-title]").forEach(function (node) {
        setCmsText(node, catalog, "title");
      });
    }
  }

  function applyPageMedia() {
    const pageKey = document.body.dataset.page || "home";
    const waitForAboutMedia = pageKey === "about";
    const media = new Map((siteData.page_media || [])
      .filter(function (item) { return item.page_key === pageKey; })
      .map(function (item) { return [item.media_key, item]; }));
    document.querySelectorAll("[data-page-media]").forEach(function (node) {
      const target = deferredMediaTargets.get(node) || node;
      mediaLoadObserver?.unobserve(target);
      deferredMediaLoads.delete(target);
      deferredMediaTargets.delete(node);
      delete node.dataset.pageMediaPending;
      const item = media.get(node.dataset.pageMedia);
      const property = node.dataset.pageMediaProperty || (node.tagName === "IMG" ? "src" : "background-image");
      if (!item) {
        node.classList.add("is-page-media-empty");
        node.dataset.pageMediaApplied = "true";
        const missingItemVideo = node.querySelector(":scope > [data-page-media-video]");
        if (missingItemVideo) removeManagedBackgroundVideo(missingItemVideo);
        if (property === "src") {
          node.removeAttribute("src");
          node.hidden = true;
        } else if (property.startsWith("--")) {
          node.style.setProperty(property, "none");
        } else {
          node.style.backgroundImage = "none";
        }
        return;
      }
      const active = ![false, 0, "0"].includes(item.is_active) && Boolean(String(item.image_url || "").trim());
      const imageUrl = item.optimized_url || item.image_url;
      node.classList.toggle("is-page-media-empty", !active);
      node.dataset.pageMediaApplied = "true";
      const currentVideo = node.querySelector(":scope > [data-page-media-video]");
      const videoActive = active && item.media_type === "video" && item.allow_video && property === "background-image";
      if (videoActive) {
        node.style.backgroundImage = "none";
        let video = currentVideo;
        if (!video || video.dataset.source !== item.image_url) {
          if (video) removeManagedBackgroundVideo(video);
          video = createBackgroundVideo(item.image_url, waitForAboutMedia ? "" : (item.default_url || ""), "page-media-background-video", "pageMediaVideo");
          video.dataset.source = item.image_url;
          if (waitForAboutMedia) {
            video.preload = "auto";
            video.addEventListener("loadeddata", function () { video.classList.add("is-media-loaded"); }, { once: true });
            if (video.readyState >= 2) video.classList.add("is-media-loaded");
          }
          node.insertBefore(video, node.firstElementChild);
        }
        syncBackgroundVideoPlayback(video, node);
        return;
      }
      if (currentVideo) removeManagedBackgroundVideo(currentVideo);
      if (active) {
        node.dataset.pageMediaPending = imageUrl;
        node.classList.add("is-page-media-empty");
        if (property === "src") {
          node.removeAttribute("src");
          node.hidden = true;
        } else if (property.startsWith("--")) {
          node.style.setProperty(property, "none");
        } else {
          node.style.backgroundImage = "none";
        }
        whenMediaNearViewport(node, function () {
          const preload = new Image();
          if (item.media_key === "hero") preload.fetchPriority = "high";
          preload.onload = function () {
            if (node.dataset.pageMediaPending !== imageUrl) return;
            if (property === "src") {
              node.src = imageUrl;
              node.hidden = false;
            } else if (property.startsWith("--")) {
              node.style.setProperty(property, cssImage(imageUrl));
            } else {
              node.style.backgroundImage = cssImage(imageUrl);
            }
            node.classList.remove("is-page-media-empty");
          };
          preload.onerror = function () {
            if (node.dataset.pageMediaPending === imageUrl) node.classList.add("is-page-media-empty");
          };
          preload.src = imageUrl;
        });
        return;
      }
      if (property === "src") {
        if (active) {
          node.src = imageUrl;
          node.hidden = false;
        } else {
          node.removeAttribute("src");
          node.hidden = true;
        }
        return;
      }
      if (property.startsWith("--")) {
        node.style.setProperty(property, active ? cssImage(imageUrl) : "none");
        return;
      }
      node.style.backgroundImage = active ? cssImage(imageUrl) : "none";
    });
  }

  function exchangeRateCopy(key) {
    const copy = {
      label: { zh: "实时汇率", en: "Live rate", ru: "Текущий курс" },
      source: { zh: "来源", en: "Source", ru: "Источник" },
      updated: { zh: "更新时间", en: "Updated", ru: "Обновлено" },
      cached: { zh: "缓存", en: "cached", ru: "кэш" },
      stale: { zh: "外部接口暂不可用，显示最近一次成功结果", en: "External rate feed is unavailable. Showing the latest saved result.", ru: "Внешний источник недоступен. Показан последний сохраненный курс." },
      loading: { zh: "正在获取...", en: "Loading...", ru: "Загрузка..." },
      unavailable: { zh: "暂时无法获取汇率", en: "Rate temporarily unavailable", ru: "Курс временно недоступен" },
      beijing: { zh: "北京", en: "Beijing", ru: "Пекин" }
    };
    return (copy[key] && (copy[key][activeLang] || copy[key].zh)) || "";
  }

  function formatBeijingTime(value) {
    const date = new Date(value || "");
    if (Number.isNaN(date.getTime())) return value || "-";
    if (activeLang === "zh") {
      const parts = new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
        timeZone: "Asia/Shanghai"
      }).formatToParts(date).reduce(function (acc, part) {
        acc[part.type] = part.value;
        return acc;
      }, {});
      return parts.year + "年" + parts.month + "月" + parts.day + "日 " + parts.hour + ":" + parts.minute + ":" + parts.second;
    }
    const locale = ({ zh: "zh-CN", en: "en-US", ru: "ru-RU" })[activeLang] || "ru-RU";
    return new Intl.DateTimeFormat(locale, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      timeZone: "Asia/Shanghai"
    }).format(date);
  }

  function readableExchangeSource(value) {
    const text = String(value || "").trim();
    if (!text) return "ExchangeRate-API";
    try {
      const host = new URL(text).hostname.replace(/^www\./, "");
      return host.includes("exchangerate-api") ? "ExchangeRate-API" : host;
    } catch (error) {
      return text;
    }
  }

  function exchangeCurrencyName(code) {
    const names = {
      RUB: { zh: "卢布", en: "RUB", ru: "руб." },
      USD: { zh: "美元", en: "USD", ru: "долл." },
      EUR: { zh: "欧元", en: "EUR", ru: "евро" }
    };
    return (names[code] && (names[code][activeLang] || names[code].zh)) || code;
  }

  function exchangeRateLine(rate) {
    const code = rate.target || "";
    const value = Number(rate.rate);
    const formatted = Number.isFinite(value) ? value.toFixed(2) : "-";
    if (activeLang === "zh") return "1元人民币 = " + formatted + exchangeCurrencyName(code);
    if (activeLang === "en") return "1 CNY = " + formatted + " " + exchangeCurrencyName(code);
    return "1 юань = " + formatted + " " + exchangeCurrencyName(code);
  }

  function exchangeRatesList(data) {
    const raw = Array.isArray(data?.rates) ? data.rates : (data?.target ? [data] : []);
    const order = ["RUB", "USD", "EUR"];
    return order.map(function (code) {
      return raw.find(function (rate) { return rate.target === code; });
    }).filter(Boolean);
  }

  function renderExchangeRateStrip() {
    const strip = document.querySelector("[data-exchange-rate-strip]");
    if (!strip) return;
    const data = siteData.exchangeRate;
    if (!data) {
      strip.innerHTML = '<strong>' + exchangeRateCopy("loading") + '</strong>';
      return;
    }
    if (data.error) {
      strip.innerHTML = '<strong>' + escapeHtml(data.error || exchangeRateCopy("unavailable")) + '</strong>';
      return;
    }
    const rates = exchangeRatesList(data);
    const sourceName = readableExchangeSource(data.source || data.source_url);
    const source = data.source_url
      ? '<a href="' + escapeHtml(data.source_url) + '" target="_blank" rel="noopener">' + escapeHtml(sourceName) + '</a>'
      : escapeHtml(sourceName);
    const note = data.stale ? '<em>' + exchangeRateCopy("stale") + '</em>' : (data.cached ? '<em>' + exchangeRateCopy("cached") + '</em>' : "");
    const time = data.fetched_at || (rates[0] && rates[0].fetched_at) || data.updated_at || (rates[0] && rates[0].updated_at) || "";
    strip.innerHTML = ''
      + '<strong>' + rates.map(exchangeRateLine).map(escapeHtml).join(' <b>|</b> ') + '</strong>'
      + '<small>' + exchangeRateCopy("beijing") + ': ' + escapeHtml(formatBeijingTime(time)) + ' (UTC+8)' + ' · ' + exchangeRateCopy("source") + ': ' + source + '</small>'
      + note;
  }

  async function loadExchangeRate() {
    if (!document.querySelector("[data-exchange-rate-strip]")) return;
    renderExchangeRateStrip();
    try {
      const payload = await requestJson("/api/exchange-rate?base=CNY&targets=RUB,USD,EUR", { cache: "no-store" }, exchangeRateCopy("unavailable"));
      siteData.exchangeRate = payload.rates || payload.rate || payload;
    } catch (error) {
      siteData.exchangeRate = { error: error.message || exchangeRateCopy("unavailable") };
    }
    renderExchangeRateStrip();
  }

  async function loadSiteData() {
    try {
      const response = await fetch("/api/site", { cache: "no-store" });
      if (!response.ok) { window.TlhNews?.finishLoading(); return; }
      const data = await response.json();
      siteData.hero_slides = data.hero_slides || [];
      siteData.home_metrics = data.home_metrics || [];
      siteData.vehicles = data.vehicles || siteData.vehicles || [];
      siteData.parts = data.parts || siteData.parts || [];
      siteData.catalog_terms = data.catalog_terms || [];
      siteData.forum_posts = data.forum_posts || siteData.forum_posts;
      siteData.settings = data.settings || {};
      siteData.page_sections = data.page_sections || [];
      siteData.page_media = data.page_media || [];
      renderDynamicHome();
      applyPageSections();
      applyPageMedia();
      applySiteSettings();
      window.TlhNews?.updateData(data);
    } catch (error) {
      console.warn("Site API unavailable, using static content.", error);
      window.TlhNews?.finishLoading();
    }
  }

  async function loadVehiclesForCurrentPage() {
    const page = document.body.dataset.page || "";
    const needsNewList = Boolean(document.querySelector("[data-vehicle-grid='new']"));
    const needsUsedList = Boolean(document.querySelector("[data-used-product-grid]"));
    const detailContainer = document.querySelector("[data-vehicle-detail], [data-used-detail]");
    if (!needsNewList && !needsUsedList && !detailContainer) return;
    try {
      if (detailContainer) {
        const id = parseInt(new URLSearchParams(location.search).get("id"), 10);
        if (!id) return;
        const type = page === "new-car-detail" ? "new" : "used";
        const payload = await requestJson(`/api/vehicles/${encodeURIComponent(id)}?type=${encodeURIComponent(type)}`, { cache: "no-store" }, "车辆加载失败");
        siteData.vehicles = payload.vehicle ? [payload.vehicle] : [];
        renderVehicleDetail();
        return;
      }
      const type = needsUsedList ? "used" : "new";
      const payload = await requestJson(`/api/vehicles?type=${encodeURIComponent(type)}&page_size=1000`, { cache: "no-store" }, "车辆加载失败");
      const loaded = payload.vehicles || payload.items || [];
      siteData.vehicles = siteData.vehicles.filter(function (vehicle) { return vehicle.vehicle_type !== type; }).concat(loaded);
      renderDynamicVehicles();
    } catch (error) {
      console.warn("Vehicle API unavailable.", error);
      renderDynamicVehicles();
      renderVehicleDetail();
    }
  }

  async function loadPartsForCurrentPage(options = {}) {
    const needsList = Boolean(document.querySelector("[data-part-grid]"));
    const detailContainer = document.querySelector("[data-part-detail]");
    if (!needsList && !detailContainer) return;
    if (detailContainer) {
      await loadPartDetailForCurrentPage();
      return;
    }
    await loadPartListPage(options);
  }

  async function loadPartDetailForCurrentPage() {
    const id = parseInt(new URLSearchParams(location.search).get("id"), 10);
    if (!id) return;
    try {
      const payload = await requestJson(`/api/parts/${encodeURIComponent(id)}`, { cache: "no-store" }, "配件加载失败");
      siteData.parts = payload.part ? [payload.part] : [];
      renderPartDetail();
      loadRelatedPartsForDetail(payload.part).catch(function (error) {
        console.warn("Related parts unavailable.", error);
      });
    } catch (error) {
      console.warn("Parts API unavailable.", error);
      renderPartDetail();
    }
  }

  function partSearchQuery() {
    return (document.querySelector("[data-part-search]")?.value || "").trim();
  }

  async function loadPartListPage(options = {}) {
    if (!document.querySelector("[data-part-grid]")) return;
    if (Number.isFinite(options.page)) partPage = Math.max(1, options.page);
    const requestId = partListState.requestId + 1;
    partListState = {
      ...partListState,
      loading: true,
      error: "",
      page: partPage,
      pageSize: PART_PAGE_SIZE,
      requestId
    };
    renderDynamicParts();
    try {
      const params = new URLSearchParams({ page: String(partPage), page_size: String(PART_PAGE_SIZE) });
      const category = activePartCategory();
      const q = partSearchQuery();
      if (category) params.set("category", category);
      if (q) params.set("q", q);
      const requestedPage = partPage;
      const payload = await requestJson(`/api/parts?${params.toString()}`, { cache: "no-store" }, "配件加载失败");
      if (requestId !== partListState.requestId) return;
      const total = Number.parseInt(payload.total, 10) || 0;
      const totalPages = Math.max(1, Number.parseInt(payload.total_pages, 10) || Math.ceil(total / PART_PAGE_SIZE) || 1);
      if (total > 0 && requestedPage > totalPages) {
        partPage = totalPages;
        await loadPartListPage({ page: totalPages });
        return;
      }
      partPage = Math.min(Math.max(1, Number.parseInt(payload.page, 10) || partPage), totalPages);
      partListState = {
        items: payload.parts || payload.items || [],
        total,
        page: partPage,
        pageSize: Number.parseInt(payload.page_size, 10) || PART_PAGE_SIZE,
        totalPages,
        loading: false,
        error: "",
        loaded: true,
        requestId
      };
      siteData.parts = partListState.items;
      renderDynamicParts();
    } catch (error) {
      if (requestId !== partListState.requestId) return;
      partListState = { ...partListState, loading: false, error: error.message || "配件加载失败", loaded: true, requestId };
      console.warn("Parts API unavailable.", error);
      renderDynamicParts();
    }
  }

  async function loadRelatedPartsForDetail(part) {
    const relatedGrid = document.querySelector("[data-related-parts]");
    if (!relatedGrid || !part || !part.category_key) return;
    const params = new URLSearchParams({ category: part.category_key, page_size: "9" });
    const payload = await requestJson(`/api/parts?${params.toString()}`, { cache: "no-store" }, "相关配件加载失败");
    const related = (payload.parts || payload.items || []).filter(function (item) { return item.id !== part.id; }).slice(0, 8);
    renderRelatedParts(related);
  }

  function renderDynamicHome() {
    const carousel = document.querySelector("[data-hero-carousel]");
    if (carousel && siteData.hero_slides.length) {
      carousel.querySelectorAll("[data-hero-slide]").forEach((slide) => slide.remove());
      siteData.hero_slides.forEach((slide, index) => {
        const node = document.createElement("div");
        node.className = `hero-slide${index === 0 ? " is-active" : ""}`;
        node.setAttribute("data-hero-slide", "");
        if (isVideoMediaUrl(slide.image_url)) {
          node.classList.add("has-background-video");
          const video = createBackgroundVideo(slide.image_url, "/assets/images/hero-placeholder.webp", "hero-slide-video", "heroVideo");
          video.dataset.source = slide.image_url;
          node.appendChild(video);
        } else {
          node.style.setProperty("--slide-image", cssImage(slide.optimized_url || slide.image_url));
        }
        node.dataset.titleZh = slide.title_zh || "";
        node.dataset.titleEn = slide.title_en || "";
        node.dataset.titleRu = slide.title_ru || "";
        node.dataset.leadZh = slide.lead_zh || "";
        node.dataset.leadEn = slide.lead_en || "";
        node.dataset.leadRu = slide.lead_ru || "";
        carousel.insertBefore(node, carousel.firstElementChild);
      });
    }

    const metricsWrap = document.querySelector("[data-home-metrics]");
    if (metricsWrap && siteData.home_metrics.length) {
      metricsWrap.innerHTML = siteData.home_metrics.map((metric) => `
        <div>
          <strong>${escapeHtml(metric.value)}</strong>
          <span data-text-zh="${escapeHtml(metric.label_zh)}" data-text-en="${escapeHtml(metric.label_en)}" data-text-ru="${escapeHtml(metric.label_ru)}">${escapeHtml(metric.label_zh)}</span>
        </div>
      `).join("");
    }
  }

  function vehicleDetailHref(vehicle) {
    const page = vehicle && vehicle.vehicle_type === "used" ? "used-car-detail.html" : "new-car-detail.html";
    return `${page}?id=${encodeURIComponent(vehicle.id)}`;
  }

  function catalogTerms(scope, termType, includeAll) {
    const terms = (siteData.catalog_terms || []).filter(function (term) {
      return term.scope === scope && term.term_type === termType && term.is_active !== false && (includeAll || term.term_key !== "all");
    });
    return terms.sort(function (a, b) {
      return (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0) || Number(a.id) - Number(b.id);
    });
  }

  function termLabel(term) {
    if (!term) return "";
    return term["label_" + activeLang] || term.label_ru || term.label_zh || term.label_en || term.term_key || "";
  }

  function termDescription(term) {
    if (!term) return "";
    return term["description_" + activeLang] || term.description_ru || term.description_zh || term.description_en || "";
  }

  function catalogTermByKey(scope, termType, key) {
    return (siteData.catalog_terms || []).find(function (term) {
      return term.scope === scope && term.term_type === termType && term.term_key === key && term.is_active !== false;
    });
  }

  function productTagsHtml(scope, keys) {
    const tagKeys = Array.isArray(keys) ? keys : [];
    const tags = tagKeys.map(function (key) { return catalogTermByKey(scope, "tag", key); }).filter(Boolean).slice(0, 3);
    if (!tags.length) return "";
    return '<div class="catalog-tags">' + tags.map(function (tag) {
      return '<span>' + escapeHtml(termLabel(tag)) + '</span>';
    }).join("") + '</div>';
  }

  function chatAttrs(product) {
    return 'data-chat-open'
      + ' data-product-type="' + escapeHtml(product.type || "") + '"'
      + ' data-product-id="' + escapeHtml(product.id || "") + '"'
      + ' data-product-title="' + escapeHtml(product.title || "") + '"'
      + ' data-product-url="' + escapeHtml(product.url || "") + '"'
      + ' data-product-image="' + escapeHtml(product.image || "") + '"';
  }

  function productPriceText(value) {
    const text = String(value || "").trim();
    if (!text || text === "询价") {
      return ({ zh: "询价", en: "On request", ru: "по запросу" })[activeLang] || "询价";
    }
    return text;
  }

  function vehicleCard(vehicle) {
    const detailHref = vehicleDetailHref(vehicle);
    const productType = vehicle.vehicle_type === "used" ? "used_vehicle" : "new_vehicle";
    const image = cardImageUrl(vehicle);
    return `
      <article class="catalog-card" data-reveal>
        <a class="catalog-image" href="${detailHref}" style="--car-image: ${escapeHtml(cssImage(image))};" data-fallback-image="${escapeHtml(vehicle.image_url || "")}"><span>${escapeHtml(vehicle.vehicle_type === "new" ? "NEW" : "USED")}</span></a>
        <div class="catalog-body">
          <h3>${escapeHtml(vehicle.title)}</h3>
          ${productTagsHtml("new_vehicle", vehicle.tag_keys)}
          <div class="catalog-specs">
            <p><span>Brand</span><strong>${escapeHtml(vehicle.brand)}</strong></p>
            <p><span>Mileage</span><strong>${escapeHtml(vehicle.mileage || "0 km")}</strong></p>
          </div>
        </div>
      </article>
    `;
  }

  function renderDynamicVehicles() {
    const newGrid = document.querySelector("[data-vehicle-grid='new']");
    if (newGrid) {
      renderNewCategoryToolbar();
      const newVehicles = filteredNewVehicles();
      renderNewProductGrid(newVehicles);
    }
    const usedVehicles = siteData.vehicles.filter((vehicle) => vehicle.vehicle_type === "used" && vehicle.is_active !== false);
    renderUsedFilterPanel(usedVehicles);
    renderUsedProductGrid(usedVehicles);


    setupReveal();
    applyLanguage(activeLang);
    hydrateImageFallbacks();
    if (window.lucide) window.lucide.createIcons();
  }

  function activeNewCategory() {
    return document.querySelector("[data-new-category].is-active")?.dataset.newCategory || "";
  }

  function vehicleMatchesNewCategory(vehicle, categoryKey) {
    if (!categoryKey) return true;
    if (vehicle.catalog_category_key === categoryKey) return true;
    const term = catalogTermByKey("new_vehicle", "category", categoryKey);
    const labels = term ? [term.term_key, term.label_zh, term.label_en, term.label_ru] : [categoryKey];
    const haystack = [vehicle.category_zh, vehicle.category_en, vehicle.category_ru].join(" ").toLowerCase();
    return labels.filter(Boolean).some(function (label) { return haystack.includes(String(label).toLowerCase()); });
  }

  function filteredNewVehicles() {
    const category = activeNewCategory();
    return siteData.vehicles.filter(function (vehicle) {
      return vehicle.vehicle_type === "new" && vehicle.is_active !== false && vehicleMatchesNewCategory(vehicle, category);
    });
  }

  function usedFilterCopy(key) {
    const copy = {
      allBrands: { zh: "选择品牌", en: "Select Brand", ru: "Выберите марку" },
      allModels: { zh: "选择型号", en: "Select Model", ru: "Выберите модель" },
      allPrices: { zh: "所有价格", en: "All Prices", ru: "Все цены" },
      allYears: { zh: "所有这些年", en: "All Years", ru: "Все годы" },
      allMileage: { zh: "任何里程", en: "Any Mileage", ru: "Любой пробег" },
      idPlaceholder: { zh: "输入ID", en: "Enter ID", ru: "Введите ID" },
      noMatch: { zh: "暂无匹配车辆", en: "No matched vehicles", ru: "Автомобили не найдены" },
      below100k: { zh: "10万以下", en: "Under 100,000", ru: "До 100 000" },
      price100150: { zh: "10万 - 15万", en: "100,000 - 150,000", ru: "100 000 - 150 000" },
      price150200: { zh: "15万 - 20万", en: "150,000 - 200,000", ru: "150 000 - 200 000" },
      above200k: { zh: "20万以上", en: "Over 200,000", ru: "От 200 000" },
      mileage10k: { zh: "1万公里以内", en: "Under 10,000 km", ru: "До 10 000 км" },
      mileage30k: { zh: "1万 - 3万公里", en: "10,000 - 30,000 km", ru: "10 000 - 30 000 км" },
      mileage50k: { zh: "3万 - 5万公里", en: "30,000 - 50,000 km", ru: "30 000 - 50 000 км" },
      mileageOver50k: { zh: "5万公里以上", en: "Over 50,000 km", ru: "От 50 000 км" }
    };
    return (copy[key] && (copy[key][activeLang] || copy[key].zh)) || "";
  }

  function vehicleYear(vehicle) {
    const direct = String(vehicle.model_year || "").trim();
    if (direct) return direct;
    const match = String(vehicle.title || "").match(/\b(19[8-9]\d|20[0-4]\d)\b/);
    return match ? match[1] : "";
  }

  function numericValue(value) {
    const text = String(value || "").replace(/[^\d.]/g, "");
    const number = parseFloat(text);
    return Number.isFinite(number) ? number : NaN;
  }

  function vehiclePriceNumber(vehicle) {
    return numericValue(vehicle.price);
  }

  function vehicleMileageNumber(vehicle) {
    return numericValue(vehicle.mileage);
  }

  function usedRangeMatches(value, range) {
    if (!range) return true;
    if (!Number.isFinite(value)) return false;
    const parts = range.split("-");
    const min = parts[0] ? Number(parts[0]) : -Infinity;
    const max = parts[1] ? Number(parts[1]) : Infinity;
    return value >= min && value < max;
  }

  function usedFilterOptions(items, getter) {
    return Array.from(new Set(items.map(getter).map(function (value) {
      return String(value || "").trim();
    }).filter(Boolean))).sort(function (a, b) {
      return a.localeCompare(b, "zh-Hans-CN");
    });
  }

  function writeSelectOptions(select, options, current, placeholder) {
    if (!select) return;
    select.innerHTML = '<option value="">' + escapeHtml(placeholder) + '</option>'
      + options.map(function (option) {
        return '<option value="' + escapeHtml(option) + '">' + escapeHtml(option) + '</option>';
      }).join("");
    select.value = options.includes(current) ? current : "";
  }

  function renderUsedFilterPanel(vehicles) {
    if (document.body.dataset.page !== "used-cars") return;
    const brandSelect = document.querySelector("[data-used-filter='brand']");
    const modelSelect = document.querySelector("[data-used-filter='model']");
    const priceSelect = document.querySelector("[data-used-filter='price']");
    const yearSelect = document.querySelector("[data-used-filter='year']");
    const mileageSelect = document.querySelector("[data-used-filter='mileage']");
    const idInput = document.querySelector("[data-used-filter='id']");
    if (!brandSelect || !modelSelect || !priceSelect || !yearSelect || !mileageSelect) return;

    const brands = usedFilterOptions(vehicles, function (vehicle) { return vehicle.brand; });
    writeSelectOptions(brandSelect, brands, usedFilters.brand, usedFilterCopy("allBrands"));
    usedFilters.brand = brandSelect.value;

    const brandScoped = usedFilters.brand ? vehicles.filter(function (vehicle) { return vehicle.brand === usedFilters.brand; }) : vehicles;
    const models = usedFilterOptions(brandScoped, function (vehicle) { return vehicle.model; });
    writeSelectOptions(modelSelect, models, usedFilters.model, usedFilterCopy("allModels"));
    usedFilters.model = modelSelect.value;

    const years = usedFilterOptions(vehicles, vehicleYear).sort(function (a, b) { return Number(b) - Number(a); });
    writeSelectOptions(yearSelect, years, usedFilters.year, usedFilterCopy("allYears"));
    usedFilters.year = yearSelect.value;

    const priceOptions = [
      { value: "0-100000", label: usedFilterCopy("below100k") },
      { value: "100000-150000", label: usedFilterCopy("price100150") },
      { value: "150000-200000", label: usedFilterCopy("price150200") },
      { value: "200000-", label: usedFilterCopy("above200k") }
    ];
    priceSelect.innerHTML = '<option value="">' + escapeHtml(usedFilterCopy("allPrices")) + '</option>'
      + priceOptions.map(function (option) {
        return '<option value="' + option.value + '">' + escapeHtml(option.label) + '</option>';
      }).join("");
    priceSelect.value = priceOptions.some(function (option) { return option.value === usedFilters.price; }) ? usedFilters.price : "";
    usedFilters.price = priceSelect.value;

    const mileageOptions = [
      { value: "0-10000", label: usedFilterCopy("mileage10k") },
      { value: "10000-30000", label: usedFilterCopy("mileage30k") },
      { value: "30000-50000", label: usedFilterCopy("mileage50k") },
      { value: "50000-", label: usedFilterCopy("mileageOver50k") }
    ];
    mileageSelect.innerHTML = '<option value="">' + escapeHtml(usedFilterCopy("allMileage")) + '</option>'
      + mileageOptions.map(function (option) {
        return '<option value="' + option.value + '">' + escapeHtml(option.label) + '</option>';
      }).join("");
    mileageSelect.value = mileageOptions.some(function (option) { return option.value === usedFilters.mileage; }) ? usedFilters.mileage : "";
    usedFilters.mileage = mileageSelect.value;

    if (idInput) {
      idInput.placeholder = usedFilterCopy("idPlaceholder");
      idInput.value = usedFilters.id;
    }
  }

  function filteredUsedVehicles(vehicles) {
    return vehicles.filter(function (vehicle) {
      if (usedFilters.id && String(vehicle.id) !== usedFilters.id) return false;
      if (usedFilters.brand && vehicle.brand !== usedFilters.brand) return false;
      if (usedFilters.model && vehicle.model !== usedFilters.model) return false;
      if (usedFilters.year && vehicleYear(vehicle) !== usedFilters.year) return false;
      if (!usedRangeMatches(vehiclePriceNumber(vehicle), usedFilters.price)) return false;
      if (!usedRangeMatches(vehicleMileageNumber(vehicle), usedFilters.mileage)) return false;
      return true;
    });
  }

  function renderNewCategoryToolbar() {
    const toolbar = document.querySelector(".catalog-toolbar");
    if (!toolbar || document.body.dataset.page !== "new-cars") return;
    const current = activeNewCategory();
    let terms = catalogTerms("new_vehicle", "category", true);
    if (!terms.length) {
      terms = [{ term_key: "all", label_zh: "全部车型", label_en: "All Models", label_ru: "Все модели", sort_order: 0 }];
    }
    const hasCurrent = terms.some(function (term) { return (term.term_key === "all" ? "" : term.term_key) === current; });
    toolbar.innerHTML = terms.map(function (term, index) {
      const key = term.term_key === "all" ? "" : term.term_key;
      const active = (hasCurrent ? key === current : index === 0) ? " is-active" : "";
      return '<button class="' + active + '" type="button" data-new-category="' + escapeHtml(key) + '">' + escapeHtml(termLabel(term) || term.term_key) + '</button>';
    }).join("");
  }

  function usedProductCard(vehicle) {
    const detailHref = vehicleDetailHref(vehicle);
    const price = productPriceText(vehicle.price);
    const image = cardImageUrl(vehicle);
    return `
      <article class="used-product-card">
        <a class="used-product-image" href="${detailHref}" style="--car-image: ${escapeHtml(cssImage(image))};" data-fallback-image="${escapeHtml(vehicle.image_url || "")}"></a>
        <div class="used-product-body">
          <h3>${escapeHtml(vehicle.title)}</h3>
          <div class="used-product-specs">
            <p><span data-text-zh="公里数" data-text-en="Mileage" data-text-ru="Пробег">公里数</span><strong>${escapeHtml(vehicle.mileage || "-")}</strong></p>
            <p><span data-text-zh="价格" data-text-en="Price" data-text-ru="Цена">价格</span><strong>${escapeHtml(price)}</strong></p>
          </div>
        </div>
      </article>
    `;
  }

  function renderNewProductGrid(vehicles) {
    const grid = document.querySelector("[data-vehicle-grid='new']");
    if (!grid) return;
    const totalPages = Math.max(1, Math.ceil(vehicles.length / VEHICLE_PAGE_SIZE));
    newPage = Math.min(Math.max(1, newPage), totalPages);
    const start = (newPage - 1) * VEHICLE_PAGE_SIZE;
    const pageItems = vehicles.slice(start, start + VEHICLE_PAGE_SIZE);
    grid.innerHTML = pageItems.map(vehicleCard).join("") || `<p class="form-note">暂无新车资源</p>`;
    renderNewPagination(vehicles.length, totalPages);
    hydrateImageFallbacks(grid);
  }

  function renderUsedProductGrid(vehicles) {
    const grid = document.querySelector("[data-used-product-grid]");
    if (!grid) return;
    const filtered = filteredUsedVehicles(vehicles);
    const totalPages = Math.max(1, Math.ceil(filtered.length / VEHICLE_PAGE_SIZE));
    usedPage = Math.min(Math.max(1, usedPage), totalPages);
    const start = (usedPage - 1) * VEHICLE_PAGE_SIZE;
    const pageItems = filtered.slice(start, start + VEHICLE_PAGE_SIZE);
    grid.innerHTML = pageItems.map(usedProductCard).join("") || `<p class="form-note">${escapeHtml(usedFilterCopy("noMatch"))}</p>`;
    renderUsedPagination(filtered.length, totalPages);
    hydrateImageFallbacks(grid);
  }

  function renderNewPagination(total, totalPages) {
    const pager = document.querySelector("[data-new-pagination]");
    if (!pager) return;
    if (!total) {
      pager.innerHTML = "";
      return;
    }
    const buttons = [];
    buttons.push(`<button type="button" data-new-page="1"${newPage === 1 ? " disabled" : ""}>第一页</button>`);
    buttons.push(`<button type="button" data-new-page="${Math.max(1, newPage - 1)}"${newPage === 1 ? " disabled" : ""}>上一页</button>`);
    for (let page = 1; page <= totalPages; page += 1) {
      buttons.push(`<button type="button" data-new-page="${page}"${page === newPage ? ' class="is-active" aria-current="page"' : ""}>${page}</button>`);
    }
    buttons.push(`<button type="button" data-new-page="${Math.min(totalPages, newPage + 1)}"${newPage === totalPages ? " disabled" : ""}>下一页</button>`);
    buttons.push(`<button type="button" data-new-page="${totalPages}"${newPage === totalPages ? " disabled" : ""}>最后一页</button>`);
    pager.innerHTML = `<span>共 ${total} 台车 · 第 ${newPage} / ${totalPages} 页</span><nav aria-label="新车分页">${buttons.join("")}</nav>`;
  }

  function renderUsedPagination(total, totalPages) {
    const pager = document.querySelector("[data-used-pagination]");
    if (!pager) return;
    if (!total) {
      pager.innerHTML = "";
      return;
    }
    const buttons = [];
    buttons.push(`<button type="button" data-used-page="1"${usedPage === 1 ? " disabled" : ""}>第一页</button>`);
    buttons.push(`<button type="button" data-used-page="${Math.max(1, usedPage - 1)}"${usedPage === 1 ? " disabled" : ""}>上一页</button>`);
    for (let page = 1; page <= totalPages; page += 1) {
      buttons.push(`<button type="button" data-used-page="${page}"${page === usedPage ? ' class="is-active" aria-current="page"' : ""}>${page}</button>`);
    }
    buttons.push(`<button type="button" data-used-page="${Math.min(totalPages, usedPage + 1)}"${usedPage === totalPages ? " disabled" : ""}>下一页</button>`);
    buttons.push(`<button type="button" data-used-page="${totalPages}"${usedPage === totalPages ? " disabled" : ""}>最后一页</button>`);
    pager.innerHTML = `<span>共 ${total} 台车 · 第 ${usedPage} / ${totalPages} 页</span><nav aria-label="二手车分页">${buttons.join("")}</nav>`;
  }

  function updateUsedPageUrl() {
    if (document.body.dataset.page !== "used-cars") return;
    const url = new URL(location.href);
    if (usedPage > 1) url.searchParams.set("page", String(usedPage));
    else url.searchParams.delete("page");
    history.replaceState(null, "", url);
  }

  function updateNewPageUrl() {
    if (document.body.dataset.page !== "new-cars") return;
    const url = new URL(location.href);
    if (newPage > 1) url.searchParams.set("page", String(newPage));
    else url.searchParams.delete("page");
    history.replaceState(null, "", url);
  }

  function partCategoryLabel(key) {
    const term = catalogTermByKey("part", "category", key);
    if (term) return termLabel(term);
    const copy = partCategoryCopy[key] || partCategoryCopy.engine;
    return copy[activeLang] || copy.zh;
  }

  function activePartCategory() {
    return document.querySelector("[data-part-category].is-active")?.dataset.partCategory || "";
  }

  function partDetailHref(part) {
    return `part-detail.html?id=${encodeURIComponent(part.id)}`;
  }

  function renderPartCategoryBoard() {
    const grid = document.querySelector("[data-part-category-grid]");
    if (!grid) return;
    const currentCategory = activePartCategory();
    let terms = catalogTerms("part", "category", true);
    if (!terms.length) {
      terms = [{ term_key: "all", label_zh: "全部配件", label_en: "All Parts", label_ru: "Все запчасти", description_zh: "查看全部可出口配件产品", icon: "layout-grid" }]
        .concat(Object.keys(partCategoryCopy).map(function (key, index) {
          const copy = partCategoryCopy[key];
          return { term_key: key, label_zh: copy.zh, label_en: copy.en, label_ru: copy.ru, description_zh: "", icon: "boxes", sort_order: index + 1 };
        }));
    }
    grid.innerHTML = terms.map(function (term, index) {
      const categoryKey = term.term_key === "all" ? "" : term.term_key;
      const desc = termDescription(term) || ({ zh: "可按清单、车型和编号匹配出口", en: "Match by list, model or part number", ru: "Подбор по списку, модели или артикулу" })[activeLang];
      const label = termLabel(term);
      const active = currentCategory ? categoryKey === currentCategory : index === 0;
      return `
        <button type="button" class="parts-category-card${active ? " is-active" : ""}" data-part-category="${escapeHtml(categoryKey)}"${partListState.loading ? " disabled" : ""}>
          ${icon(term.icon || "boxes")}
          <span>${escapeHtml(label)}</span>
          <small>${escapeHtml(desc)}</small>
        </button>
      `;
    }).join("");
  }

  function partCard(part) {
    const detailHref = partDetailHref(part);
    const category = partCategoryLabel(part.category_key);
    const desc = part["description_" + activeLang] || part.description_zh || "";
    const image = cardImageUrl(part);
    return `
      <article class="part-product-card">
        <a class="part-product-image" href="${detailHref}" style="--car-image: ${escapeHtml(cssImage(image))};" data-fallback-image="${escapeHtml(part.image_url || "")}"><span>${escapeHtml(category)}</span></a>
        <div class="part-product-body">
          <h3><a href="${detailHref}">${escapeHtml(part.title)}</a></h3>
          ${productTagsHtml("part", part.tag_keys)}
          <div class="part-specs">
            <p><span data-text-zh="品牌" data-text-en="Brand" data-text-ru="Бренд">品牌</span><strong>${escapeHtml(part.brand || "-")}</strong></p>
            <p><span data-text-zh="编号" data-text-en="Part No." data-text-ru="Артикул">编号</span><strong>${escapeHtml(part.part_no || "-")}</strong></p>
          </div>
          <p class="part-summary">${escapeHtml(desc || part.compatible_models || "")}</p>
        </div>
      </article>
    `;
  }

  function renderDynamicParts() {
    if (!document.querySelector("[data-part-grid]")) return;
    renderPartCategoryBoard();
    renderPartProductGrid();
  }

  function partListMessage(key) {
    const copy = {
      loading: { zh: "正在加载配件...", en: "Loading parts...", ru: "Загрузка запчастей..." },
      empty: { zh: "暂无匹配配件", en: "No matched parts", ru: "Запчасти не найдены" },
      retry: { zh: "重新加载", en: "Retry", ru: "Повторить" }
    };
    return (copy[key] && copy[key][activeLang]) || (copy[key] && copy[key].zh) || "";
  }

  function renderPartProductGrid() {
    const grid = document.querySelector("[data-part-grid]");
    if (!grid) return;
    grid.classList.toggle("is-loading", partListState.loading);
    if (partListState.loading) {
      grid.innerHTML = `<div class="parts-loading"><span></span><p>${escapeHtml(partListMessage("loading"))}</p></div>`;
      renderPartPagination(partListState.total, partListState.totalPages);
    } else if (partListState.error) {
      grid.innerHTML = `<div class="parts-state"><p>${escapeHtml(partListState.error)}</p><button type="button" data-part-retry>${escapeHtml(partListMessage("retry"))}</button></div>`;
      renderPartPagination(partListState.total, partListState.totalPages);
    } else {
      const parts = partListState.items || [];
      grid.innerHTML = parts.map(partCard).join("") || `<p class="form-note" data-text-zh="暂无匹配配件" data-text-en="No matched parts" data-text-ru="Запчасти не найдены">${escapeHtml(partListMessage("empty"))}</p>`;
      renderPartPagination(partListState.total, partListState.totalPages);
      hydrateImageFallbacks(grid);
    }
    applyTranslatedDataAttributes();
    if (window.lucide) window.lucide.createIcons();
  }

  function renderPartPagination(total, totalPages) {
    const pager = document.querySelector("[data-part-pagination]");
    if (!pager) return;
    const hasTotal = Number.isFinite(total) && total > 0;
    const current = Math.min(Math.max(1, partPage), Math.max(1, totalPages || 1));
    if (!hasTotal && !partListState.loading) {
      pager.innerHTML = "";
      updatePartPageUrl();
      return;
    }
    const pages = Math.max(1, totalPages || 1);
    const pageItems = compactPageItems(current, pages);
    const buttons = pageItems.map(function (item) {
      if (item === "...") {
        return '<span class="pagination-ellipsis" aria-hidden="true">...</span>';
      }
      return `<button type="button" class="${item === current ? "is-active" : ""}" data-part-page="${item}"${partListState.loading ? " disabled" : ""}>${item}</button>`;
    }).join("");
    const label = ({ zh: `共 ${total || 0} 个配件`, en: `${total || 0} parts`, ru: `${total || 0} запчастей` })[activeLang];
    pager.classList.toggle("is-loading", partListState.loading);
    pager.innerHTML = `
      <span>${escapeHtml(label)}</span>
      <nav>
        <button type="button" data-part-page="${current - 1}" ${current <= 1 || partListState.loading ? "disabled" : ""}>&lt;</button>
        ${buttons}
        <button type="button" data-part-page="${current + 1}" ${current >= pages || partListState.loading ? "disabled" : ""}>&gt;</button>
      </nav>
    `;
    updatePartPageUrl();
  }

  function compactPageItems(current, pages) {
    if (pages <= 7) {
      return Array.from({ length: pages }, function (_, index) { return index + 1; });
    }
    const keep = new Set([1, pages]);
    for (let page = current - 2; page <= current + 2; page += 1) {
      if (page >= 1 && page <= pages) keep.add(page);
    }
    const sorted = Array.from(keep).sort(function (a, b) { return a - b; });
    const result = [];
    sorted.forEach(function (page, index) {
      const previous = sorted[index - 1];
      if (index > 0 && page - previous > 1) result.push("...");
      result.push(page);
    });
    return result;
  }

  function updatePartPageUrl() {
    if (!document.querySelector("[data-part-pagination]")) return;
    const url = new URL(location.href);
    if (partPage > 1) url.searchParams.set("page", String(partPage));
    else url.searchParams.delete("page");
    history.replaceState(null, "", url);
  }

  function renderPartDetail() {
    const container = document.querySelector("[data-part-detail]");
    if (!container) return;
    const id = parseInt(new URLSearchParams(location.search).get("id"), 10);
    if (!id) return;
    const part = (siteData.parts || []).find(function (item) { return item.id === id; });
    if (!part) {
      container.innerHTML = '<p class="form-note">配件未找到</p>';
      return;
    }
    var galleryUrls = [];
    try { galleryUrls = Array.isArray(part.gallery) ? part.gallery : JSON.parse(part.gallery_json || "[]"); } catch (e) {}
    var allImages = [part.image_url].concat(galleryUrls).filter(Boolean);
    if (!allImages.length) allImages = ["/assets/images/parts-placeholder.webp"];
    var mainImage = optimizedImageUrl(allImages[0]);
    var thumbsHtml = allImages.map(function (url, idx) {
      var active = idx === 0 ? " is-active" : "";
      return '<button type="button" data-gallery-thumb data-image="' + escapeHtml(optimizedImageUrl(url)) + '" data-fallback-image="' + escapeHtml(url) + '" class="' + active + '" style="--thumb-image: ' + escapeHtml(cssImage(thumbImageUrl(url))) + ';"></button>';
    }).join("");
    container.innerHTML = ''
      + '<div class="vehicle-gallery">'
      + '<div class="gallery-main" data-gallery-main data-fallback-image="' + escapeHtml(allImages[0] || "") + '" style="--gallery-image: ' + escapeHtml(cssImage(mainImage)) + ';"><span>' + escapeHtml(partCategoryLabel(part.category_key)) + '</span></div>'
      + '<div class="gallery-thumbs">' + thumbsHtml + '</div>'
      + '</div>'
      + '<div class="detail-info-panel">'
      + '<h2>' + escapeHtml(part.title) + '</h2>'
      + '<ul class="detail-spec-list">'
      + '<li><span data-text-zh="分类" data-text-en="Category" data-text-ru="Категория">分类</span><strong>' + escapeHtml(partCategoryLabel(part.category_key)) + '</strong></li>'
      + '<li><span data-text-zh="品牌" data-text-en="Brand" data-text-ru="Бренд">品牌</span><strong>' + escapeHtml(part.brand || "") + '</strong></li>'
      + '<li><span data-text-zh="编号" data-text-en="Part No." data-text-ru="Артикул">编号</span><strong>' + escapeHtml(part.part_no || "") + '</strong></li>'
      + '<li><span data-text-zh="适配车型" data-text-en="Compatible" data-text-ru="Совместимость">适配车型</span><strong>' + escapeHtml(part.compatible_models || "") + '</strong></li>'
      + '<li><span data-text-zh="价格" data-text-en="Price" data-text-ru="Цена">价格</span><strong>' + escapeHtml(part.price || "询价") + '</strong></li>'
      + '</ul>'
      + '<div class="detail-actions" style="margin-top:22px;">'
      + '<a href="#" class="cta-primary" ' + chatAttrs({ type: "part", id: part.id, title: part.title, url: partDetailHref(part), image: part.image_url }) + ' data-text-zh="在线询价" data-text-en="Online Quote" data-text-ru="Запрос цены">在线询价</a>'
      + '</div>'
      + '</div>';
    hydrateImageFallbacks(container);
    const descCopy = document.querySelector("[data-part-detail-copy]");
    if (descCopy) {
      const description = part["description_" + activeLang] || part.description_zh || "配件描述待补充。";
      descCopy.innerHTML = renderRichText(description);
    }
    document.title = part.title + " | 通利华汽车集团";
    document.querySelectorAll("[data-current-part-title]").forEach(function (node) {
      node.setAttribute("data-current-part-title", part.title);
      setDynamicLocalizedText(node, part.title);
    });
    const relatedGrid = document.querySelector("[data-related-parts]");
    if (relatedGrid) {
      relatedGrid.innerHTML = `<div class="parts-loading parts-loading-compact"><span></span><p>${escapeHtml(partListMessage("loading"))}</p></div>`;
    }
    applyTranslatedDataAttributes();
  }

  function renderRelatedParts(related) {
    const relatedGrid = document.querySelector("[data-related-parts]");
    if (!relatedGrid) return;
    relatedGrid.innerHTML = (related || []).map(function (item) {
      const image = cardImageUrl(item);
      return '<article class="mini-vehicle-card">'
        + '<a href="' + partDetailHref(item) + '" class="mini-vehicle-image" style="--car-image: ' + escapeHtml(cssImage(image)) + ';" data-fallback-image="' + escapeHtml(item.image_url || "") + '"></a>'
        + '<div><h3>' + escapeHtml(item.title) + '</h3><p>' + escapeHtml(item.brand || "") + ' / ' + escapeHtml(item.part_no || "") + '</p><a href="' + partDetailHref(item) + '" data-text-zh="查看详情" data-text-en="View Detail" data-text-ru="Подробнее">查看详情</a></div>'
        + '</article>';
    }).join("") || '<p class="form-note" data-text-zh="暂无相关配件" data-text-en="No related parts" data-text-ru="Нет похожих запчастей">暂无相关配件</p>';
    hydrateImageFallbacks(relatedGrid);
    applyTranslatedDataAttributes();
  }



  function getVehicleGalleryUrls(vehicle) {
    if (!vehicle) return [];
    if (Array.isArray(vehicle.gallery)) return vehicle.gallery.filter(Boolean);
    if (Array.isArray(vehicle.gallery_json)) return vehicle.gallery_json.filter(Boolean);
    var raw = typeof vehicle.gallery_json === "string"
      ? vehicle.gallery_json
      : (typeof vehicle.gallery === "string" ? vehicle.gallery : "");
    if (!raw) return [];
    try {
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
    } catch (e) {
      return [];
    }
  }

  function renderVehicleDetail() {
    const pageKey = document.body.dataset.page || "";
    const expectedType = pageKey === "new-car-detail" ? "new" : "used";
    const container = document.querySelector("[data-vehicle-detail]") || document.querySelector("[data-used-detail]");
    if (!container) return;
    const params = new URLSearchParams(location.search);
    const id = parseInt(params.get("id"), 10);
    if (!id) return;
    const vehicle = siteData.vehicles.find(function (v) { return v.id === id && v.vehicle_type === expectedType; });
    if (!vehicle) {
      container.innerHTML = '<p class="form-note">车辆未找到</p>';
      return;
    }
    var galleryUrls = getVehicleGalleryUrls(vehicle);
    var allImages = [vehicle.image_url].concat(galleryUrls).filter(Boolean);
    if (!allImages.length) allImages = ["/assets/images/vehicle-placeholder.webp"];
    var mainImage = optimizedImageUrl(allImages[0]);
    var thumbsHtml = allImages.map(function (url, idx) {
      var active = idx === 0 ? " is-active" : "";
      return '<button type="button" data-gallery-thumb data-image="' + escapeHtml(optimizedImageUrl(url)) + '" data-fallback-image="' + escapeHtml(url) + '" class="' + active + '" style="--thumb-image: ' + escapeHtml(cssImage(thumbImageUrl(url))) + ';"></button>';
    }).join("");
    var typeLabel = vehicle.vehicle_type === "new" ? "NEW" : "USED";
    var productType = vehicle.vehicle_type === "used" ? "used_vehicle" : "new_vehicle";
    container.innerHTML = ''
      + '<div class="vehicle-gallery">'
      + '<div class="gallery-main" data-gallery-main data-fallback-image="' + escapeHtml(allImages[0] || "") + '" style="--gallery-image: ' + escapeHtml(cssImage(mainImage)) + ';"><span>' + escapeHtml(typeLabel) + '</span></div>'
      + '<div class="gallery-thumbs">' + thumbsHtml + '</div>'
      + '</div>'
      + '<div class="detail-info-panel">'
      + '<h2>' + escapeHtml(vehicle.title) + '</h2>'
      + '<ul class="detail-spec-list">'
      + '<li><span data-text-zh="品牌" data-text-en="Brand" data-text-ru="Бренд">品牌</span><strong>' + escapeHtml(vehicle.brand || "") + '</strong></li>'
      + '<li><span data-text-zh="型号" data-text-en="Model" data-text-ru="Модель">型号</span><strong>' + escapeHtml(vehicle.model || "") + '</strong></li>'
      + '<li><span data-text-zh="发动机" data-text-en="Engine" data-text-ru="Двигатель">发动机</span><strong>' + escapeHtml(vehicle.engine || "") + '</strong></li>'
      + '<li><span data-text-zh="里程" data-text-en="Mileage" data-text-ru="Пробег">里程</span><strong>' + escapeHtml(vehicle.mileage || "") + '</strong></li>'
      + '<li><span data-text-zh="价格" data-text-en="Price" data-text-ru="Цена">价格</span><strong>' + escapeHtml(vehicle.price || "询价") + '</strong></li>'
      + '</ul>'
      + '<div class="detail-actions" style="margin-top:22px;">'
      + '<a href="#" class="cta-primary" ' + chatAttrs({ type: productType, id: vehicle.id, title: vehicle.title, url: vehicleDetailHref(vehicle), image: vehicle.image_url }) + ' data-text-zh="在线询价" data-text-en="Online Quote" data-text-ru="Запрос цены">在线询价</a>'
      + '</div>'
      + '</div>'
    + '';
    hydrateImageFallbacks(container);

    var descSection = document.querySelector(".detail-description");
    if (descSection) {
      var descTitle = descSection.querySelector("[data-detail-description-title]");
      if (descTitle) {
        descTitle.textContent = (expectedType === "new"
          ? siteData.settings.new_detail_description_title
          : siteData.settings.used_detail_description_title) || "产品描述";
      }
      var descCopy = descSection.querySelector(".detail-copy");
      if (descCopy) {
        var fallbackDescription = expectedType === "new"
          ? siteData.settings.new_detail_fallback_description
          : siteData.settings.used_detail_fallback_description;
        var description = vehicle["description_" + activeLang] || vehicle.description_zh || fallbackDescription || "车辆描述待补充。";
        descCopy.innerHTML = renderRichText(description);
      }
    }

    document.title = vehicle.title + " | 通利华汽车集团";
    var breadcrumbCurrent = document.querySelector(".breadcrumb-line .current[data-current-vehicle-title]");
    if (breadcrumbCurrent) {
      breadcrumbCurrent.setAttribute("data-current-vehicle-title", vehicle.title);
      setDynamicLocalizedText(breadcrumbCurrent, vehicle.title);
    }

    var heroTitle = document.querySelector("h1[data-current-vehicle-title]");
    if (heroTitle) {
      heroTitle.setAttribute("data-current-vehicle-title", vehicle.title);
      setDynamicLocalizedText(heroTitle, vehicle.title);
    }
  }

  function renderUsedCarDetail() {
    renderVehicleDetail();
  }


  function createHeaderTools() {
    syncPrimaryNav();
    if (!headerActions) return;

    headerActions.querySelectorAll(".account-button, [data-account-menu], .nav-mobile-actions").forEach(function (node) {
      node.remove();
    });
    accountMenu = undefined;

    let searchButton = headerActions.querySelector("[data-search-open]");
    if (!searchButton) {
      searchButton = document.createElement("button");
      searchButton.className = "header-tool";
      searchButton.type = "button";
      searchButton.setAttribute("data-search-open", "");
      searchButton.setAttribute("aria-label", "搜索");
      searchButton.innerHTML = icon("search");
    }

    const contactLink = headerActions.querySelector(".header-contact");
    if (contactLink) {
      contactLink.href = "contact.html";
      contactLink.innerHTML = `${icon("headset")}<span>联系我们</span>`;
    }

    let languageBox = headerActions.querySelector("[data-language-menu]");
    let langButton = headerActions.querySelector(".language-switch");
    if (!langButton) {
      langButton = document.createElement("button");
      langButton.className = "language-switch";
      langButton.type = "button";
    }
    langButton.removeAttribute("data-lang-switch");
    langButton.setAttribute("data-lang-toggle", "");
    langButton.setAttribute("aria-label", "切换语言");
    langButton.setAttribute("aria-haspopup", "menu");
    langButton.setAttribute("aria-expanded", "false");
    langButton.innerHTML = `<span data-lang-label>${langLabels[activeLang]}</span><span class="language-chevron" aria-hidden="true"></span>`;

    if (!languageBox) {
      languageBox = document.createElement("div");
      languageBox.className = "language-menu";
      languageBox.setAttribute("data-language-menu", "");
      headerActions.insertBefore(languageBox, toggle);
    }
    languageBox.appendChild(langButton);

    let languageOptions = languageBox.querySelector("[data-lang-menu]");
    if (!languageOptions) {
      languageOptions = document.createElement("div");
      languageOptions.className = "language-options";
      languageOptions.setAttribute("data-lang-menu", "");
      languageOptions.setAttribute("role", "menu");
      languageOptions.hidden = true;
      languageOptions.innerHTML = `
        <button type="button" role="menuitemradio" data-lang-option="zh">中文</button>
        <button type="button" role="menuitemradio" data-lang-option="en">English</button>
        <button type="button" role="menuitemradio" data-lang-option="ru">Русский</button>
      `;
      languageBox.appendChild(languageOptions);
    }

    if (contactLink) headerActions.insertBefore(searchButton, contactLink);
    else headerActions.insertBefore(searchButton, languageBox);
    if (contactLink) headerActions.insertBefore(contactLink, languageBox);
    headerActions.insertBefore(languageBox, toggle);
  }

  function updateHeader() {
    if (!header) return;
    const currentY = window.scrollY;
    header.classList.toggle("is-scrolled", currentY > 12);
    header.classList.remove("is-hidden");
  }

  function closeLanguageMenu() {
    const languageBox = headerActions?.querySelector("[data-language-menu]");
    const languageOptions = languageBox?.querySelector("[data-lang-menu]");
    const langButton = languageBox?.querySelector("[data-lang-toggle]");
    if (languageOptions) languageOptions.hidden = true;
    if (langButton) langButton.setAttribute("aria-expanded", "false");
    languageBox?.classList.remove("is-open");
  }

  function toggleLanguageMenu() {
    const languageBox = headerActions?.querySelector("[data-language-menu]");
    const languageOptions = languageBox?.querySelector("[data-lang-menu]");
    const langButton = languageBox?.querySelector("[data-lang-toggle]");
    if (!languageBox || !languageOptions || !langButton) return;
    const opened = languageOptions.hidden;
    languageOptions.hidden = !opened;
    langButton.setAttribute("aria-expanded", String(opened));
    languageBox.classList.toggle("is-open", opened);
  }

  function closeNav() {
    const returnFocus = document.body.classList.contains("nav-open") && nav?.contains(document.activeElement);
    document.body.classList.remove("nav-open");
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "打开导航");
      toggle.innerHTML = icon("menu");
    }
    if (window.lucide) window.lucide.createIcons();
    if (returnFocus && toggle?.getClientRects().length) toggle.focus();
  }

  function applyLanguage(lang, options = {}) {
    if (!supportedLangs.includes(lang)) lang = DEFAULT_LANG;
    activeLang = lang;
    localStorage.setItem("tlhdd-lang", lang);
    if (options.userSelected) localStorage.setItem("tlhdd-lang-user-set", "true");
    document.documentElement.lang = ({ zh: "zh-CN", en: "en", ru: "ru" })[lang] || "ru";
    document.body.classList.toggle("lang-en", lang === "en");
    document.body.classList.toggle("lang-ru", lang === "ru");

    if (document.body.dataset.page === "used-car-detail" || document.body.dataset.page === "new-car-detail") {
      renderVehicleDetail();
    }
    if (document.body.dataset.page === "part-detail") {
      renderPartDetail();
    }
    if (document.body.dataset.page === "used-cars") {
      const usedVehicles = siteData.vehicles.filter(function (vehicle) { return vehicle.vehicle_type === "used" && vehicle.is_active !== false; });
      renderUsedFilterPanel(usedVehicles);
      renderUsedProductGrid(usedVehicles);
    }
    renderExchangeRateStrip();

    document.querySelectorAll(".site-nav > a").forEach(function (link) {
      const item = pageIndex.find(function (page) {
        return page.href === link.getAttribute("href");
      });
      const label = link.querySelector(".nav-item-label");
      if (item && label) label.textContent = item[lang] || item.zh;
    });

    document.querySelectorAll("[data-lang-label]").forEach(function (label) {
      label.textContent = langLabels[lang] || langLabels.zh;
    });

    document.querySelectorAll("[data-lang-option]").forEach(function (option) {
      const selected = option.dataset.langOption === lang;
      option.classList.toggle("is-active", selected);
      option.setAttribute("aria-checked", String(selected));
    });

    updatePublicAuthUI();

    document.querySelectorAll(".header-contact span").forEach(function (label) {
      label.textContent = ({ zh: "联系我们", en: "Contact Us", ru: "Связаться" })[lang] || "联系我们";
      label.closest("a")?.setAttribute("aria-label", label.textContent);
    });

    applyTranslatedDataAttributes();

    document.querySelectorAll("[data-placeholder-zh]").forEach(function (node) {
      const value = node.dataset[`placeholder${dataSuffix[lang]}`] || node.dataset.placeholderZh;
      if (value) node.placeholder = value;
    });

    renderActiveHeroCopy();
    renderSearchResults();
    updateAuthCopy();
    applySiteSettings();
    applyTranslatedDataAttributes();
    translateStaticCopy();
    translatePlaceholders();
    updatePageTitle();
    window.TlhNews?.setLanguage(lang);
  }

  function setActiveNav() {
    const current = location.pathname.split("/").pop() || "index.html";
    const navTarget = {
      "new-car-detail.html": "new-cars.html",
      "used-car-detail.html": "used-cars.html"
    }[current] || current;
    document.querySelectorAll(".site-nav a").forEach(function (link) {
      const href = link.getAttribute("href");
      if (href === navTarget || (navTarget === "" && href === "index.html") ) {
        link.classList.add("is-active");
        link.setAttribute("aria-current", "page");
      }
    });
  }

  const carousel = document.querySelector("[data-hero-carousel]");
  let slides = carousel ? Array.from(carousel.querySelectorAll("[data-hero-slide]")) : [];
  const heroTitle = document.querySelector("[data-hero-title]");
  const heroLead = document.querySelector("[data-hero-lead]");
  const heroDots = document.querySelector("[data-hero-dots]");
  let activeSlide = 0;
  let heroTimer = null;

  function writeHeroTitle(value) {
    if (!heroTitle || !value) return;
    heroTitle.textContent = "";
    value.split("|").forEach(function (line) {
      const span = document.createElement("span");
      span.className = "title-line";
      span.textContent = line;
      heroTitle.appendChild(span);
    });
  }

  function renderActiveHeroCopy() {
    if (!slides.length) return;
    const slide = slides[activeSlide];
    const suffix = dataSuffix[activeLang] || "Zh";
    writeHeroTitle(slide.dataset[`title${suffix}`]);
    if (heroLead) heroLead.textContent = slide.dataset[`lead${suffix}`] || "";
  }

  function showSlide(index) {
    if (!slides.length) return;
    activeSlide = (index + slides.length) % slides.length;
    slides.forEach(function (slide, slideIndex) {
      const isActive = slideIndex === activeSlide;
      const video = slide.querySelector(":scope > [data-hero-video]");
      if (isActive && slide.dataset.image) {
        slide.style.backgroundImage = `linear-gradient(90deg, rgba(10, 14, 18, 0.74), rgba(10, 14, 18, 0.34) 54%, rgba(10, 14, 18, 0.12)), ${slide.dataset.image}`;
      }
      slide.classList.toggle("is-active", isActive);
      if (video) syncBackgroundVideoPlayback(video, slide, true);
      if (!isActive) {
        window.setTimeout(function () {
          if (!slide.classList.contains("is-active")) {
            slide.style.backgroundImage = "";
          }
        }, 900);
      }
    });
    if (heroDots) {
      heroDots.querySelectorAll("button").forEach(function (button, buttonIndex) {
        button.classList.toggle("is-active", buttonIndex === activeSlide);
      });
    }
    renderActiveHeroCopy();
  }

  function startCarousel() {
    if (slides.length < 2 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    window.clearInterval(heroTimer);
    heroTimer = window.setInterval(function () {
      showSlide(activeSlide + 1);
    }, document.body.classList.contains("home-redesign") ? 3000 : 5200);
  }

  function setupCarousel() {
    slides = carousel ? Array.from(carousel.querySelectorAll("[data-hero-slide]")) : [];
    if (!slides.length || !heroDots) return;
    slides.forEach(function (slide) {
      const image = slide.style.getPropertyValue("--slide-image");
      if (image) {
        slide.dataset.image = image.trim();
        slide.style.removeProperty("--slide-image");
      }
    });
    heroDots.textContent = "";
    slides.forEach(function (_, index) {
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("aria-label", `切换到第 ${index + 1} 张轮播图`);
      button.addEventListener("click", function () {
        showSlide(index);
        startCarousel();
      });
      heroDots.appendChild(button);
    });
    carousel.addEventListener("mouseenter", function () {
      window.clearInterval(heroTimer);
    });
    carousel.addEventListener("mouseleave", startCarousel);
    showSlide(0);
    startCarousel();
  }

  let searchOverlay;
  let searchInput;
  let searchResults;
  let inquiryOverlay;
  let chatOverlay;
  let activeChat = { product: null, thread: null, messages: [] };
  let chatPollTimer = null;

  function createSearchOverlay() {
    if (searchOverlay) return;
    searchOverlay = document.createElement("div");
    searchOverlay.className = "overlay-panel";
    searchOverlay.setAttribute("data-search-overlay", "");
    searchOverlay.innerHTML = `
      <div class="search-dialog" role="dialog" aria-modal="true" aria-labelledby="search-title">
        <div class="overlay-head">
          <h2 id="search-title" data-search-title>站内搜索</h2>
          <button class="overlay-close" type="button" data-overlay-close aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="search-box">
          <label class="search-input-wrap">
            ${icon("search")}
            <input type="search" data-search-input placeholder="输入车型、配件、物流或栏目名称">
          </label>
          <div class="search-results" data-search-results></div>
        </div>
      </div>
    `;
    document.body.appendChild(searchOverlay);
    searchInput = searchOverlay.querySelector("[data-search-input]");
    searchResults = searchOverlay.querySelector("[data-search-results]");
    searchInput.addEventListener("input", renderSearchResults);
    searchOverlay.addEventListener("click", function (event) {
      if (event.target === searchOverlay || event.target.closest("[data-overlay-close]") || event.target.closest(".search-results a")) {
        closeOverlay(searchOverlay);
      }
    });
  }

  function createInquiryOverlay() {
    if (inquiryOverlay) return;
    inquiryOverlay = document.createElement("div");
    inquiryOverlay.className = "overlay-panel";
    inquiryOverlay.setAttribute("data-inquiry-overlay", "");
    inquiryOverlay.innerHTML = `
      <div class="inquiry-dialog" role="dialog" aria-modal="true" aria-labelledby="inquiry-title">
        <div class="overlay-head">
          <h2 id="inquiry-title" data-text-zh="快速咨询" data-text-en="Quick Inquiry" data-text-ru="Быстрый запрос">快速咨询</h2>
          <button class="overlay-close" type="button" data-overlay-close aria-label="关闭">${icon("x")}</button>
        </div>
        <form class="contact-form inquiry-form" data-contact-form>
          <div class="compact-form-row">
            <label>
              <span data-text-zh="称呼" data-text-en="Name" data-text-ru="Имя">称呼</span>
              <input name="name" placeholder="Name">
            </label>
            <label>
              <span data-text-zh="手机 / 邮箱" data-text-en="Phone / Email" data-text-ru="Телефон / Email">手机 / 邮箱</span>
              <input name="contact" required placeholder="Phone / Email">
            </label>
          </div>
          <label>
            <span data-text-zh="意向车型 / 服务" data-text-en="Vehicle / Service" data-text-ru="Авто / услуга">意向车型 / 服务</span>
            <input name="vehicle_interest" required placeholder="新车、售后、二手车、零配件、汽车进出口或出行服务">
          </label>
          <label>
            <span data-text-zh="需求说明" data-text-en="Message" data-text-ru="Сообщение">需求说明</span>
            <textarea name="message" rows="4" placeholder="目的地、预算、数量或配置需求"></textarea>
          </label>
          <button class="btn btn-primary form-submit" type="submit"><span data-text-zh="提交询盘" data-text-en="Submit Inquiry" data-text-ru="Отправить запрос">提交询盘</span>${icon("send")}</button>
          <p class="form-note" data-form-note></p>
        </form>
      </div>
    `;
    document.body.appendChild(inquiryOverlay);
    inquiryOverlay.addEventListener("click", function (event) {
      if (event.target === inquiryOverlay || event.target.closest("[data-overlay-close]")) {
        closeOverlay(inquiryOverlay);
      }
    });
  }

  function chatGuestToken() {
    return localStorage.getItem("tlhdd-guest-token") || "";
  }

  function setChatGuestToken(token) {
    if (token) localStorage.setItem("tlhdd-guest-token", token);
  }

  function productTypeLabel(type) {
    const labels = {
      new_vehicle: { zh: "新车出口", en: "New Car", ru: "Новое авто" },
      used_vehicle: { zh: "二手车出口", en: "Used Car", ru: "Авто с пробегом" },
      part: { zh: "配件出口", en: "Part", ru: "Запчасти" }
    };
    return (labels[type] || labels.new_vehicle)[activeLang];
  }

  function chatProductFromButton(button) {
    return {
      type: button.dataset.productType || "new_vehicle",
      id: button.dataset.productId || "",
      title: button.dataset.productTitle || "在线询价",
      url: button.dataset.productUrl || location.pathname,
      image: button.dataset.productImage || ""
    };
  }

  function createChatOverlay() {
    if (chatOverlay) return;
    chatOverlay = document.createElement("div");
    chatOverlay.className = "overlay-panel";
    chatOverlay.setAttribute("data-chat-overlay", "");
    chatOverlay.innerHTML = `
      <div class="seller-chat-dialog" role="dialog" aria-modal="true" aria-labelledby="seller-chat-title">
        <div class="seller-chat-head">
          <div>
            <span data-chat-product-type>Auto Export</span>
            <h2 id="seller-chat-title" data-text-zh="联系卖家" data-text-en="Contact Seller" data-text-ru="Связаться с продавцом">联系卖家</h2>
          </div>
          <button class="overlay-close" type="button" data-overlay-close aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="seller-product-strip">
          <div class="seller-product-image" data-chat-product-image></div>
          <div>
            <strong data-chat-product-title>在线询价</strong>
            <a href="#" data-chat-product-link data-text-zh="查看商品详情" data-text-en="View Detail" data-text-ru="Подробнее">查看商品详情</a>
          </div>
        </div>
        <div class="seller-chat-body" data-chat-messages></div>
        <div class="seller-quick-prompts">
          <button type="button" data-chat-prompt data-text-zh="请报价和库存" data-text-en="Please quote price and stock" data-text-ru="Цена и наличие?">请报价和库存</button>
          <button type="button" data-chat-prompt data-text-zh="到俄罗斯运费多少" data-text-en="Shipping cost to Russia?" data-text-ru="Доставка в Россию?">到俄罗斯运费多少</button>
          <button type="button" data-chat-prompt data-text-zh="支持批量采购吗" data-text-en="Bulk order available?" data-text-ru="Есть оптовая поставка?">支持批量采购吗</button>
        </div>
        <form class="seller-chat-form" data-chat-form>
          <div class="compact-form-row">
            <label><span data-text-zh="称呼" data-text-en="Name" data-text-ru="Имя">称呼</span><input name="contact_name" placeholder="Name"></label>
            <label><span data-text-zh="联系方式" data-text-en="Contact" data-text-ru="Контакт">联系方式</span><input name="contact_info" placeholder="WhatsApp / Phone / Email"></label>
          </div>
          <label><span data-text-zh="消息" data-text-en="Message" data-text-ru="Сообщение">消息</span><textarea name="message" rows="3" required placeholder="请输入咨询内容"></textarea></label>
          <button class="btn btn-primary form-submit" type="submit"><span data-text-zh="发送消息" data-text-en="Send Message" data-text-ru="Отправить">发送消息</span>${icon("send")}</button>
          <p class="form-note" data-chat-note></p>
        </form>
      </div>
    `;
    document.body.appendChild(chatOverlay);
    chatOverlay.addEventListener("click", function (event) {
      if (event.target === chatOverlay || event.target.closest("[data-overlay-close]")) {
        stopChatPolling();
        closeOverlay(chatOverlay);
      }
      const prompt = event.target.closest("[data-chat-prompt]");
      if (prompt) {
        const message = chatOverlay.querySelector("[data-chat-form] textarea[name='message']");
        if (message) message.value = prompt.textContent.trim();
      }
    });
  }

  function renderChatOverlay() {
    if (!chatOverlay || !activeChat.product) return;
    const product = activeChat.product;
    const image = chatOverlay.querySelector("[data-chat-product-image]");
    const title = chatOverlay.querySelector("[data-chat-product-title]");
    const type = chatOverlay.querySelector("[data-chat-product-type]");
    const link = chatOverlay.querySelector("[data-chat-product-link]");
    const messages = chatOverlay.querySelector("[data-chat-messages]");
    if (image) image.style.setProperty("--chat-product-image", cssImage(product.image || "/assets/images/vehicle-placeholder.webp"));
    if (title) title.textContent = product.title || "在线询价";
    if (type) type.textContent = productTypeLabel(product.type);
    if (link) link.href = product.url || "#";
    const rows = activeChat.messages || [];
    messages.innerHTML = rows.length ? rows.map(function (message) {
      const isAdmin = message.sender_kind === "admin";
      return '<article class="seller-message ' + (isAdmin ? "is-admin" : "is-user") + '">'
        + '<strong>' + escapeHtml(message.sender_name || (isAdmin ? "Tonglihua Automotive Group" : "Customer")) + '</strong>'
        + '<p>' + escapeHtml(message.body || "") + '</p>'
        + '<small>' + escapeHtml(message.created_at || "") + '</small>'
        + '</article>';
    }).join("") : '<article class="seller-message is-admin"><strong>Tonglihua Automotive Group</strong><p>' + escapeHtml(({ zh: "您好，请留下车型、数量、目的地或配件清单，我们会尽快回复。", en: "Hello, please send model, quantity, destination or parts list. We will reply soon.", ru: "Здравствуйте! Напишите модель, количество, пункт назначения или список запчастей. Мы скоро ответим." })[activeLang]) + '</p></article>';
    messages.scrollTop = messages.scrollHeight;
    const form = chatOverlay.querySelector("[data-chat-form]");
    if (form && publicAuth.user) {
      form.elements.contact_name.value = form.elements.contact_name.value || accountName();
      form.elements.contact_info.value = form.elements.contact_info.value || publicAuth.user.phone || publicAuth.user.email || publicAuth.user.account || "";
    }
    applyTranslatedDataAttributes();
    if (window.lucide) window.lucide.createIcons();
  }

  function openProductChat(product) {
    createChatOverlay();
    activeChat = { product, thread: null, messages: [] };
    renderChatOverlay();
    openOverlay(chatOverlay);
    window.setTimeout(function () {
      chatOverlay?.querySelector("textarea[name='message']")?.focus();
    }, 50);
  }

  function chatHeaders() {
    return {
      "Content-Type": "application/json",
      ...(!publicAuth.user && chatGuestToken() ? { "X-Guest-Token": chatGuestToken() } : {})
    };
  }

  async function refreshActiveChat() {
    if (!activeChat.thread) return;
    const response = await fetch(`/api/messages/threads/${activeChat.thread.id}`, {
      headers: chatHeaders(),
      credentials: "same-origin",
      cache: "no-store"
    });
    const payload = await response.json().catch(function () { return {}; });
    if (!response.ok) return;
    activeChat.thread = payload.thread;
    activeChat.messages = payload.messages || [];
    renderChatOverlay();
  }

  function startChatPolling() {
    stopChatPolling();
    chatPollTimer = window.setInterval(refreshActiveChat, 15000);
  }

  function stopChatPolling() {
    if (chatPollTimer) window.clearInterval(chatPollTimer);
    chatPollTimer = null;
  }

  async function submitChatMessage(form) {
    const note = form.querySelector("[data-chat-note]");
    const data = Object.fromEntries(new FormData(form).entries());
    data.product_type = activeChat.product?.type || "new_vehicle";
    data.product_id = activeChat.product?.id || "";
    data.product_title = activeChat.product?.title || "在线询价";
    data.product_url = activeChat.product?.url || location.pathname;
    data.product_image = activeChat.product?.image || "";
    if (note) {
      note.classList.remove("is-success");
      note.textContent = ({ zh: "正在发送消息...", en: "Sending message...", ru: "Отправка сообщения..." })[activeLang];
    }
    const url = activeChat.thread ? `/api/messages/threads/${activeChat.thread.id}/messages` : "/api/messages/threads";
    const payload = await requestJson(url, {
      method: "POST",
      headers: chatHeaders(),
      credentials: "same-origin",
      body: JSON.stringify(data)
    }, "发送失败");
    if (payload.thread?.guest_token) setChatGuestToken(payload.thread.guest_token);
    activeChat.thread = payload.thread;
    activeChat.messages = payload.messages || [];
    form.elements.message.value = "";
    if (note) {
      note.classList.add("is-success");
      note.textContent = ({ zh: "消息已发送，后台会在这里回复。", en: "Message sent. Replies will appear here.", ru: "Сообщение отправлено. Ответ появится здесь." })[activeLang];
    }
    renderChatOverlay();
    startChatPolling();
    userCenterState.token = "";
  }

  function matchingPages(query) {
    const normalized = query.toLowerCase();
    return pageIndex.filter(function (item) {
      const text = `${item.zh} ${item.en} ${item.ru} ${item.descZh} ${item.descEn} ${item.descRu} ${item.keys}`.toLowerCase();
      return text.includes(normalized);
    });
  }

  function pageSearchHtml(matches) {
    return matches.map(function (item) {
      const title = item[activeLang] || item.zh;
      const desc = item[`desc${dataSuffix[activeLang]}`] || item.descZh;
      return `<a href="${item.href}"><span>${escapeHtml(title)}<small>${escapeHtml(desc)}</small></span>${icon("arrow-right")}</a>`;
    }).join("");
  }

  function renderSearchMatches(vehicleMatches, partMatches, pageMatches = []) {
    const vehicleHtml = vehicleMatches.map(function (vehicle) {
      const typeLabel = vehicle.vehicle_type === "new"
        ? ({ zh: "新车", en: "New Car", ru: "Новый автомобиль" })[activeLang]
        : ({ zh: "二手车", en: "Used Car", ru: "Авто с пробегом" })[activeLang];
      return `
        <a href="${vehicleDetailHref(vehicle)}">
          <span>${escapeHtml(vehicle.title)}<small>${escapeHtml(typeLabel)} · ${escapeHtml(vehicle.brand)} · ${escapeHtml(vehicle.mileage || "")}</small></span>
          ${icon("arrow-right")}
        </a>
      `;
    }).join("");
    const partHtml = partMatches.map(function (part) {
      const typeLabel = ({ zh: "配件", en: "Part", ru: "Запчасть" })[activeLang];
      return `
        <a href="${partDetailHref(part)}">
          <span>${escapeHtml(part.title)}<small>${escapeHtml(typeLabel)} · ${escapeHtml(partCategoryLabel(part.category_key))} · ${escapeHtml(part.part_no || "")}</small></span>
          ${icon("arrow-right")}
        </a>
      `;
    }).join("");
    searchResults.innerHTML = pageSearchHtml(pageMatches) + vehicleHtml + partHtml;
    if (!pageMatches.length && !vehicleMatches.length && !partMatches.length) {
      searchResults.innerHTML = `<p class="form-note">${({ zh: "没有匹配的内容。", en: "No matches found.", ru: "Ничего не найдено." })[activeLang]}</p>`;
    }
    if (window.lucide) window.lucide.createIcons();
  }

  function renderSearchResults() {
    if (!searchResults) return;
    const query = (searchInput ? searchInput.value : "").trim();
    if (searchOverlay) {
      const title = searchOverlay.querySelector("[data-search-title]");
      if (title) title.textContent = ({ zh: "站内搜索", en: "Site Search", ru: "Поиск по сайту" })[activeLang];
      if (searchInput) searchInput.placeholder = ({
        zh: "输入车型、配件或栏目名称",
        en: "Search cars, parts or pages",
        ru: "Введите авто, запчасти или раздел"
      })[activeLang];
    }
    const pageMatches = matchingPages(query);
    if (!query) {
      globalSearchRequestId += 1;
      clearTimeout(globalSearchTimer);
      searchResults.innerHTML = pageSearchHtml(pageMatches);
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    const requestId = ++globalSearchRequestId;
    clearTimeout(globalSearchTimer);
    searchResults.innerHTML = pageSearchHtml(pageMatches) + `<p class="form-note">${({ zh: "正在搜索…", en: "Searching…", ru: "Поиск…" })[activeLang]}</p>`;
    globalSearchTimer = window.setTimeout(async function () {
      try {
        const payload = await requestJson(`/api/search?q=${encodeURIComponent(query)}`, { cache: "no-store" }, "搜索失败");
        if (requestId !== globalSearchRequestId) return;
        renderSearchMatches(payload.vehicles || [], payload.parts || [], pageMatches);
      } catch (error) {
        if (requestId !== globalSearchRequestId) return;
        searchResults.innerHTML = pageSearchHtml(pageMatches) + `<p class="form-note">${escapeHtml(error.message || "搜索失败")}</p>`;
      }
    }, 220);
  }

  let authOverlay;
  let authMode = "login";
  let forumSearchTimer = null;
  let forumSearchRequestId = 0;
  let globalSearchTimer = null;
  let globalSearchRequestId = 0;

  function createAuthOverlay() {
    if (authOverlay) return;
    authOverlay = document.createElement("div");
    authOverlay.className = "overlay-panel";
    authOverlay.setAttribute("data-auth-overlay", "");
    authOverlay.innerHTML = `
      <div class="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <div class="overlay-head">
          <h2 id="auth-title" data-auth-title>登录</h2>
          <button class="overlay-close" type="button" data-overlay-close aria-label="关闭">${icon("x")}</button>
        </div>
        <form class="auth-form" data-auth-form>
          <label>
            <span data-auth-name-label>手机 / 用户名 / 邮箱</span>
            <input type="text" required placeholder="请输入手机、用户名或邮箱" data-auth-account>
          </label>
          <label>
            <span data-auth-password-label>密码</span>
            <input type="password" required placeholder="请输入密码" data-auth-password>
          </label>
          <button class="btn btn-primary" type="submit" data-auth-submit>登录</button>
          <p class="auth-switch"><span data-auth-switch-text>还没有账号？</span><button type="button" data-auth-switch>立即注册</button></p>
          <p class="form-note" data-auth-note>注册后可用于车辆询价和后续客户跟进。</p>
        </form>
      </div>
    `;
    document.body.appendChild(authOverlay);
    authOverlay.addEventListener("click", function (event) {
      if (event.target === authOverlay || event.target.closest("[data-overlay-close]")) {
        closeOverlay(authOverlay);
      }
      if (event.target.closest("[data-auth-switch]")) {
        setAuthMode(authMode === "login" ? "register" : "login");
      }
    });
    authOverlay.querySelector("[data-auth-form]").addEventListener("submit", async function (event) {
      event.preventDefault();
      const note = authOverlay.querySelector("[data-auth-note]");
      const account = authOverlay.querySelector("[data-auth-account]").value.trim();
      const password = authOverlay.querySelector("[data-auth-password]").value;
      try {
        const payload = await requestJson(authMode === "login" ? "/api/auth/login" : "/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ account, password, display_name: "" })
        }, "操作失败");
        publicAuth.token = "";
        publicAuth.user = payload.user;
        localStorage.removeItem("tlhdd-public-token");
        localStorage.removeItem("tlhdd-session-token");
        updatePublicAuthUI();
        if (note) {
          note.classList.add("is-success");
          note.textContent = ({
            zh: authMode === "login" ? "登录成功，欢迎回来。" : "注册成功，已自动登录。",
            en: authMode === "login" ? "Signed in successfully." : "Registered and signed in.",
            ru: authMode === "login" ? "Вход выполнен." : "Регистрация завершена, вход выполнен."
          })[activeLang];
        }
        window.setTimeout(function () {
          closeOverlay(authOverlay);
        }, 700);
      } catch (error) {
        if (note) {
          note.classList.remove("is-success");
          note.textContent = error.message;
        }
      }
    });
  }

  function setAuthMode(mode) {
    authMode = mode;
    if (authOverlay) {
      const note = authOverlay.querySelector("[data-auth-note]");
      if (note) note.classList.remove("is-success");
    }
    updateAuthCopy();
  }

  function updateAuthCopy() {
    if (!authOverlay) return;
    const isLogin = authMode === "login";
    const copy = {
      zh: {
        title: isLogin ? "登录" : "注册",
        account: "手机 / 用户名 / 邮箱",
        password: "密码",
        accountPlaceholder: "请输入手机、用户名或邮箱",
        passwordPlaceholder: isLogin ? "请输入密码" : "至少输入 12 位密码",
        submit: isLogin ? "登录" : "注册",
        switchText: isLogin ? "还没有账号？" : "已有账号？",
        switchButton: isLogin ? "立即注册" : "去登录",
        note: isLogin ? "登录后可继续询价和查看客户跟进信息。" : "注册后可用于车辆询价和后续客户跟进。"
      },
      en: {
        title: isLogin ? "Log In" : "Register",
        account: "Phone / Username / Email",
        password: "Password",
        accountPlaceholder: "Enter phone, username or email",
        passwordPlaceholder: isLogin ? "Enter password" : "At least 12 characters",
        submit: isLogin ? "Log In" : "Create Account",
        switchText: isLogin ? "No account yet?" : "Already have an account?",
        switchButton: isLogin ? "Register" : "Log In",
        note: isLogin ? "Sign in to continue inquiries and follow-up." : "Register for vehicle inquiries and follow-up."
      },
      ru: {
        title: isLogin ? "Войти" : "Регистрация",
        account: "Телефон / Логин / Email",
        password: "Пароль",
        accountPlaceholder: "Введите телефон, логин или email",
        passwordPlaceholder: isLogin ? "Введите пароль" : "Не менее 12 символов",
        submit: isLogin ? "Войти" : "Создать аккаунт",
        switchText: isLogin ? "Нет аккаунта?" : "Уже есть аккаунт?",
        switchButton: isLogin ? "Регистрация" : "Войти",
        note: isLogin ? "Войдите, чтобы продолжить запросы." : "Зарегистрируйтесь для запросов по автомобилям."
      }
    }[activeLang];
    authOverlay.querySelector("[data-auth-title]").textContent = copy.title;
    authOverlay.querySelector("[data-auth-name-label]").textContent = copy.account;
    authOverlay.querySelector("[data-auth-password-label]").textContent = copy.password;
    authOverlay.querySelector("[data-auth-account]").placeholder = copy.accountPlaceholder;
    const passwordInput = authOverlay.querySelector("[data-auth-password]");
    passwordInput.placeholder = copy.passwordPlaceholder;
    passwordInput.minLength = isLogin ? 0 : 12;
    authOverlay.querySelector("[data-auth-submit]").textContent = copy.submit;
    authOverlay.querySelector("[data-auth-switch-text]").textContent = copy.switchText;
    authOverlay.querySelector("[data-auth-switch]").textContent = copy.switchButton;
    const note = authOverlay.querySelector("[data-auth-note]");
    if (note && !note.classList.contains("is-success")) note.textContent = copy.note;
  }

  function isAdminUser() {
    const user = publicAuth.user;
    return Boolean(user && (user.permission === "admin" || user.kind === "admin" || String(user.role || "").toLowerCase().includes("admin") || user.role === "超级管理员"));
  }

  function accountName() {
    if (!publicAuth.user) return "";
    return publicAuth.user.display_name || publicAuth.user.account || publicAuth.user.username || "用户";
  }

  function accountLabels() {
    return {
      zh: {
        login: "登录",
        account: "账户",
        userCenter: "用户中心",
        admin: "管理后台",
        logout: "退出登录",
        normalRole: "普通用户",
        adminRole: "管理员",
        signedIn: "已登录"
      },
      en: {
        login: "Log In",
        account: "Account",
        userCenter: "User Center",
        admin: "Admin Console",
        logout: "Log Out",
        normalRole: "User",
        adminRole: "Admin",
        signedIn: "Signed in"
      },
      ru: {
        login: "Войти",
        account: "Аккаунт",
        userCenter: "Центр пользователя",
        admin: "Админ-панель",
        logout: "Выйти",
        normalRole: "Пользователь",
        adminRole: "Админ",
        signedIn: "Вход выполнен"
      }
    }[activeLang] || {};
  }

  function closeAccountMenu() {
    if (accountMenu) {
      accountMenu.hidden = true;
      accountMenu.classList.remove("is-open");
    }
    document.querySelectorAll("[data-account-toggle]").forEach(function (button) {
      button.setAttribute("aria-expanded", "false");
    });
  }

  function renderAccountMenu() {
    if (!accountMenu) return;
    if (!publicAuth.user) {
      accountMenu.innerHTML = "";
      closeAccountMenu();
      return;
    }
    const labels = accountLabels();
    const name = accountName();
    const admin = isAdminUser();
    const initial = name.trim().slice(0, 1).toUpperCase() || "U";
    accountMenu.innerHTML = `
      <div class="account-menu-head">
        <span>${escapeHtml(initial)}</span>
        <div>
          <strong>${escapeHtml(name)}</strong>
          <small>${escapeHtml(labels.signedIn)} · ${escapeHtml(admin ? labels.adminRole : labels.normalRole)}</small>
        </div>
      </div>
      <div class="account-menu-list">
        ${admin ? `<a href="admin/" data-menu-link>${icon("layout-dashboard")}<span>${escapeHtml(labels.admin)}</span></a>` : ""}
        <a href="user-center.html" data-menu-link>${icon("circle-user-round")}<span>${escapeHtml(labels.userCenter)}</span></a>
        <button type="button" data-auth-logout>${icon("log-out")}<span>${escapeHtml(labels.logout)}</span></button>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
  }

  function openAccountLogin() {
    closeAccountMenu();
    closeNav();
    createAuthOverlay();
    setAuthMode("login");
    authOverlay?.querySelector("[data-auth-form]")?.reset();
    const note = authOverlay?.querySelector("[data-auth-note]");
    if (note) {
      note.classList.remove("is-success");
      updateAuthCopy();
    }
    openOverlay(authOverlay);
    window.setTimeout(function () {
      authOverlay?.querySelector("[data-auth-account]")?.focus();
    }, 50);
  }

  function toggleAccountEntry() {
    if (!publicAuth.user) {
      openAccountLogin();
      return;
    }
    renderAccountMenu();
    const nextOpen = accountMenu.hidden;
    accountMenu.hidden = !nextOpen;
    accountMenu.classList.toggle("is-open", nextOpen);
    document.querySelectorAll("[data-account-toggle]").forEach(function (button) {
      button.setAttribute("aria-expanded", String(nextOpen));
    });
    header && header.classList.remove("is-hidden");
  }

  function updatePublicAuthUI() {
    const isLoggedIn = Boolean(publicAuth.user);
    const labels = accountLabels();
    const name = accountName();
    document.querySelectorAll("[data-account-toggle]").forEach(function (button) {
      button.setAttribute("aria-label", isLoggedIn ? `${labels.account}: ${name}` : labels.login);
      button.setAttribute("aria-haspopup", "true");
      button.setAttribute("aria-expanded", "false");
      button.classList.toggle("is-logged-in", isLoggedIn);
    });
    document.querySelectorAll("[data-account-badge]").forEach(function (badge) {
      badge.hidden = !isLoggedIn;
      badge.textContent = isLoggedIn ? (name.trim().slice(0, 1).toUpperCase() || "U") : "";
    });
    document.querySelectorAll("[data-account-action]").forEach(function (label) {
      label.textContent = isLoggedIn ? name : labels.login;
    });
    renderAccountMenu();
    renderUserCenter();
    updateForumAuthState();
  }

  async function checkPublicSession() {
    try {
      const response = await fetch("/api/auth/me", {
        credentials: "same-origin",
        cache: "no-store"
      });
      if (!response.ok) throw new Error("session expired");
      const payload = await response.json();
      publicAuth.user = payload.user;
    } catch {
      localStorage.removeItem("tlhdd-public-token");
      localStorage.removeItem("tlhdd-session-token");
      publicAuth.token = "";
      publicAuth.user = null;
    }
    updatePublicAuthUI();
  }

  async function logoutPublicUser() {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin"
    }).catch(function () {});
    localStorage.removeItem("tlhdd-public-token");
    localStorage.removeItem("tlhdd-session-token");
    publicAuth.token = "";
    publicAuth.user = null;
    closeAccountMenu();
    updatePublicAuthUI();
  }

  function forumDetailHref(post) {
    return "user-center.html#user-forum-publish";
  }

  function forumInquiryHref(post) {
    const topic = [post.brand, post.model, post.title].filter(Boolean).join(" ");
    return `contact.html?vehicle=${encodeURIComponent(topic || "车型论坛咨询")}`;
  }

  function forumPostMedia(post) {
    const media = Array.isArray(post.media) ? post.media.filter((item) => item && item.url) : [];
    if (media.length) return media;
    return post.image_url ? [{ type: "image", url: post.image_url }] : [];
  }

  function renderForumPosts(posts) {
    const grid = document.querySelector("[data-forum-posts]");
    if (!grid) return;
    const query = (document.querySelector("[data-forum-search]")?.value || "").trim();
    const category = activeForumCategory();
    if (!posts || !posts.length) {
      const message = query || category
        ? ({ zh: "暂无匹配的论坛内容。", en: "No matched forum posts.", ru: "Публикации не найдены." })[activeLang]
        : ({ zh: "暂无论坛内容，登录后可以发布第一条车型动态。", en: "No forum posts yet. Sign in to publish the first vehicle post.", ru: "Пока нет публикаций. Войдите, чтобы добавить первый автомобиль." })[activeLang];
      const publishLabel = ({ zh: "发布问题", en: "Publish Question", ru: "Опубликовать вопрос" })[activeLang];
      const inquiryLabel = ({ zh: "提交询盘", en: "Submit Inquiry", ru: "Отправить запрос" })[activeLang];
      grid.innerHTML = `
        <div class="forum-empty">
          ${icon("messages-square")}
          <div>
            <p>${escapeHtml(message)}</p>
            <div class="forum-empty-actions">
              <button type="button" data-forum-publish-toggle>${escapeHtml(publishLabel)}</button>
              <a href="contact.html">${escapeHtml(inquiryLabel)}</a>
            </div>
          </div>
        </div>
      `;
      return;
    }
    const featuredLabel = ({ zh: "精选", en: "Featured", ru: "Рекомендуем" })[activeLang];
    const detailLabel = ({ zh: "查看详情", en: "View Detail", ru: "Подробнее" })[activeLang];
    const inquiryLabel = ({ zh: "咨询类似车型", en: "Ask About Similar Cars", ru: "Запросить похожее авто" })[activeLang];
    grid.innerHTML = posts.map(function (post) {
      const media = forumPostMedia(post);
      const cover = media.find((item) => item.type === "image") || media[0] || null;
      const originalImage = cover && cover.type === "image" ? cover.url : (post.image_url || "");
      const image = thumbImageUrl(originalImage);
      const video = cover && cover.type === "video" ? cover.url : "";
      const meta = [post.brand, post.model, post.model_year].filter(Boolean).join(" · ") || "Vehicle Talk";
      const date = post.created_at ? String(post.created_at).slice(0, 10) : "";
      const categoryLabel = forumCategoryLabel(post.topic_category);
      const mediaCount = media.length;
      const mediaLabel = mediaCount > 1 ? ({ zh: `${mediaCount} 个媒体`, en: `${mediaCount} media`, ru: `${mediaCount} медиа` })[activeLang] : "";
      const detailHref = forumDetailHref(post);
      const inquiryHref = forumInquiryHref(post);
      return `
        <article class="forum-card">
          <a class="forum-card-image${image || video ? "" : " is-image-missing"}${video ? " is-video" : ""}" href="${detailHref}" data-fallback-image="${escapeHtml(originalImage || "")}" style="${image ? `--car-image: ${escapeHtml(cssImage(image))};` : ""}">
            ${video ? `<video src="${escapeHtml(video)}" muted playsinline preload="metadata"></video>` : ""}
            <span>${escapeHtml(meta)}</span>
            ${mediaLabel ? `<em>${escapeHtml(mediaLabel)}</em>` : ""}
          </a>
          <div class="forum-card-body">
            <div class="forum-card-tags">
              <span>${escapeHtml(categoryLabel)}</span>
              ${post.is_featured ? `<strong>${escapeHtml(featuredLabel)}</strong>` : ""}
            </div>
            <div class="forum-author">
              <span>${escapeHtml((post.author_name || post.account || "用户").slice(0, 1).toUpperCase())}</span>
              <small>${escapeHtml(post.author_name || post.account || "用户")}${date ? ` · ${escapeHtml(date)}` : ""}</small>
            </div>
            <h3><a class="forum-card-title-link" href="${detailHref}">${escapeHtml(post.title)}</a></h3>
            <p>${escapeHtml(post.content)}</p>
            <div class="forum-card-actions">
              <a class="forum-card-link" href="${detailHref}">${escapeHtml(detailLabel)} ${icon("arrow-right")}</a>
              <a class="forum-card-link" href="${inquiryHref}">${escapeHtml(inquiryLabel)} ${icon("message-circle")}</a>
            </div>
          </div>
        </article>
      `;
    }).join("");
    hydrateImageFallbacks(grid);
  }

  function renderForumDetail() {
    const container = document.querySelector("[data-forum-detail]");
    if (!container || !siteData.currentForumPost) return;
    const post = siteData.currentForumPost;
    const media = forumPostMedia(post);
    const date = post.created_at ? String(post.created_at).slice(0, 10) : "";
    const meta = [post.brand, post.model, post.model_year].filter(Boolean).join(" · ");
    const featuredLabel = ({ zh: "精选", en: "Featured", ru: "Рекомендуем" })[activeLang];
    const categoryLabel = forumCategoryLabel(post.topic_category);
    const inquiryLabel = ({ zh: "提交出口询盘", en: "Submit Export Inquiry", ru: "Отправить запрос" })[activeLang];
    const backLabel = ({ zh: "返回用户中心", en: "Back to User Center", ru: "Вернуться в центр пользователя" })[activeLang];
    const relatedTitle = ({ zh: "相关讨论", en: "Related Posts", ru: "Похожие публикации" })[activeLang];
    const mediaTitle = ({ zh: "图片 / 视频", en: "Photos / Videos", ru: "Фото / видео" })[activeLang];
    const authorName = post.author_name || post.account || "用户";
    const detailMedia = media.length ? media : [{ type: "image", url: "" }];
    const relatedPool = (siteData.forum_posts || []).filter(function (item) { return item.id !== post.id; });
    const related = relatedPool
      .filter(function (item) { return item.topic_category === post.topic_category; })
      .concat(relatedPool.filter(function (item) { return item.topic_category !== post.topic_category; }))
      .slice(0, 5);
    const relatedHtml = related.map(function (item) {
      return `<a href="${forumDetailHref(item)}"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(forumCategoryLabel(item.topic_category))}</span></a>`;
    }).join("") || `<p class="form-note">${({ zh: "暂无相关讨论", en: "No related posts yet.", ru: "Пока нет похожих публикаций." })[activeLang]}</p>`;

    container.innerHTML = `
      <article class="forum-detail-main">
        <div class="forum-card-tags">
          <span>${escapeHtml(categoryLabel)}</span>
          ${post.is_featured ? `<strong>${escapeHtml(featuredLabel)}</strong>` : ""}
        </div>
        <h2>${escapeHtml(post.title)}</h2>
        <div class="forum-author">
          <span>${escapeHtml(authorName.slice(0, 1).toUpperCase())}</span>
          <small>${escapeHtml(authorName)}${date ? ` · ${escapeHtml(date)}` : ""}</small>
        </div>
        ${meta ? `<div class="forum-detail-specs"><span>${escapeHtml(meta)}</span></div>` : ""}
        <div class="forum-detail-copy">${renderRichText(post.content)}</div>
        <div class="forum-detail-media">
          <h3>${escapeHtml(mediaTitle)}</h3>
          <div class="forum-detail-media-grid">
            ${detailMedia.map(function (item) {
              if (item.type === "video") {
                return `<video class="forum-detail-video" src="${escapeHtml(item.url)}" controls preload="metadata"></video>`;
              }
              const image = optimizedImageUrl(item.url);
              return `<a class="forum-detail-image${item.url ? "" : " is-image-missing"}" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener" data-fallback-image="${escapeHtml(item.url || "")}" style="${item.url ? `--car-image: ${escapeHtml(cssImage(image))};` : ""}"></a>`;
            }).join("")}
          </div>
        </div>
      </article>
      <aside class="forum-detail-aside">
        <div class="forum-detail-cta">
          <h3>${escapeHtml(inquiryLabel)}</h3>
          <p>${escapeHtml(({ zh: "把目标车型、数量和目的地发给我们，业务人员会按出口流程跟进。", en: "Send the target model, quantity and destination. Our team will follow up with an export plan.", ru: "Отправьте модель, количество и пункт назначения. Мы подготовим экспортное предложение." })[activeLang])}</p>
          <a class="btn btn-primary" href="${forumInquiryHref(post)}">${escapeHtml(inquiryLabel)} ${icon("arrow-right")}</a>
          <a class="btn btn-outline-dark" href="user-center.html#user-forum-publish">${escapeHtml(backLabel)}</a>
        </div>
        <div class="forum-related-list">
          <h3>${escapeHtml(relatedTitle)}</h3>
          ${relatedHtml}
        </div>
      </aside>
    `;

    document.title = `${post.title} | 通利华汽车集团`;
    document.querySelectorAll("[data-current-forum-title]").forEach(function (node) {
      node.setAttribute("data-current-forum-title", post.title);
      setDynamicLocalizedText(node, post.title);
    });
    hydrateImageFallbacks(container);
    if (window.lucide) window.lucide.createIcons();
  }

  async function loadForumDetail() {
    const container = document.querySelector("[data-forum-detail]");
    if (!container) return;
    const id = parseInt(new URLSearchParams(location.search).get("id"), 10);
    if (!id) {
      container.innerHTML = `<p class="form-note">${({ zh: "帖子不存在", en: "Post not found.", ru: "Публикация не найдена." })[activeLang]}</p>`;
      return;
    }
    container.innerHTML = `<p class="form-note">${({ zh: "正在加载帖子详情...", en: "Loading post detail...", ru: "Загрузка публикации..." })[activeLang]}</p>`;
    try {
      const payload = await requestJson(`/api/forum/posts/${encodeURIComponent(id)}`, { cache: "no-store" }, "加载失败");
      siteData.currentForumPost = payload.post;
      renderForumDetail();
    } catch (error) {
      siteData.currentForumPost = null;
      container.innerHTML = `<p class="form-note">${escapeHtml(({ zh: "帖子不存在或暂未通过审核。", en: "This post is unavailable or not approved yet.", ru: "Публикация недоступна или еще не одобрена." })[activeLang])}</p>`;
    }
  }

  async function loadForumPosts() {
    const grid = document.querySelector("[data-forum-posts]");
    if (!grid) return;
    const input = document.querySelector("[data-forum-search]");
    const query = input ? input.value.trim() : "";
    const category = activeForumCategory();
    const requestId = ++forumSearchRequestId;
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (category) params.set("category", category);
    const queryString = params.toString();
    grid.innerHTML = `<p class="form-note">${({ zh: "正在加载论坛内容...", en: "Loading forum posts...", ru: "Загрузка форума..." })[activeLang]}</p>`;
    try {
      const payload = await requestJson(`/api/forum/posts${queryString ? `?${queryString}` : ""}`, { cache: "no-store" }, "加载失败");
      if (requestId !== forumSearchRequestId) return;
      siteData.forum_posts = payload.posts || [];
      renderForumPosts(siteData.forum_posts);
    } catch (error) {
      if (requestId !== forumSearchRequestId) return;
      renderForumPosts(siteData.forum_posts);
    }
    if (window.lucide) window.lucide.createIcons();
  }

  function updateForumAuthState() {
    const panel = document.querySelector("[data-forum-auth-state]");
    const submit = document.querySelector("[data-forum-submit]");
    const toggle = document.querySelector("[data-forum-publish-toggle]");
    if (!panel && !submit) return;
    const loggedIn = Boolean(publicAuth.user);
    const labels = {
      zh: {
        allowed: `${accountName()} 可以发布车型内容`,
        locked: "登录后可以发布自己的车型",
        submit: "发布车型",
        submitLocked: "登录后发布",
        toggle: "发布车型",
        toggleLocked: "登录后发布车型"
      },
      en: {
        allowed: `${accountName()} can publish vehicle posts`,
        locked: "Sign in to publish your vehicle",
        submit: "Publish Vehicle",
        submitLocked: "Sign in to publish",
        toggle: "Publish Vehicle",
        toggleLocked: "Sign in to publish"
      },
      ru: {
        allowed: `${accountName()} может публиковать автомобили`,
        locked: "Войдите, чтобы опубликовать автомобиль",
        submit: "Опубликовать авто",
        submitLocked: "Войти для публикации",
        toggle: "Опубликовать авто",
        toggleLocked: "Войти для публикации"
      }
    }[activeLang];
    if (panel) {
      panel.innerHTML = loggedIn
        ? `${icon("circle-check")}<span>${escapeHtml(labels.allowed)}</span>`
        : `${icon("lock-keyhole")}<span>${escapeHtml(labels.locked)}</span>`;
    }
    if (submit) {
      submit.querySelector("span").textContent = loggedIn ? labels.submit : labels.submitLocked;
    }
    if (toggle) {
      const label = toggle.querySelector("span");
      if (label) label.textContent = loggedIn ? labels.toggle : labels.toggleLocked;
    }
    if (window.lucide) window.lucide.createIcons();
  }

  function toggleForumPublishPanel(forceOpen) {
    const panel = document.querySelector("[data-forum-publish-panel]");
    const toggle = document.querySelector("[data-forum-publish-toggle]");
    if (!panel) return;
    const shouldOpen = typeof forceOpen === "boolean" ? forceOpen : panel.hidden;
    panel.hidden = !shouldOpen;
    if (toggle) toggle.setAttribute("aria-expanded", String(shouldOpen));
    if (shouldOpen) {
      updateForumAuthState();
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function setupForumPage() {
    if (!document.querySelector("[data-forum-posts]")) return;
    setActiveForumCategory(activeForumCategory());
    loadForumPosts();
    updateForumAuthState();
    const form = document.querySelector("[data-forum-form]");
    if (!form || form.dataset.ready) return;
    form.dataset.ready = "true";
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      if (!publicAuth.user) {
        openAccountLogin();
        return;
      }
      const note = form.querySelector("[data-forum-note]");
      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());
      try {
        const response = await fetch("/api/forum/posts", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(data)
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || "发布失败");
        form.reset();
        writeForumMedia(form, []);
        if (note) {
          note.classList.add("is-success");
          note.textContent = payload.post && payload.post.moderation_status === "approved"
            ? "发布成功，已加入车型论坛。"
            : "已提交，审核后展示。";
        }
        await loadForumPosts();
      } catch (error) {
        if (note) {
          note.classList.remove("is-success");
          note.textContent = error.message;
        }
      }
    });
  }

  function renderUserCenter() {
    var panel = document.querySelector("[data-user-center]");
    if (!panel) return;
    if (!publicAuth.user) {
      panel.innerHTML = '<div class="user-center-empty">'
        + icon("lock-keyhole")
        + '<h2>请先登录账户</h2>'
        + '<p>登录后可以管理个人信息、查看帖子和询价记录。</p>'
        + '<button class="btn btn-primary" type="button" data-account-toggle><span>登录账户</span>' + icon("arrow-right") + '</button>'
        + '</div>';
      if (window.lucide) window.lucide.createIcons();
      return;
    }
    if (userCenterState.token !== accountName() && !userCenterState.loading) {
      panel.innerHTML = '<div class="user-center-empty">'
        + icon("loader-circle")
        + '<h2>正在加载账户信息</h2>'
        + '<p>正在读取你的询盘和车型论坛记录。</p>'
        + '</div>';
      loadUserCenterData();
      if (window.lucide) window.lucide.createIcons();
      return;
    }
    var user = publicAuth.user;
    var name = accountName();
    var initial = name.trim().slice(0, 1).toUpperCase() || "U";
    var inquiries = userCenterState.inquiries || [];
    var posts = userCenterState.posts || [];
    var threads = userCenterState.threads || [];
    var adminLink = isAdminUser()
      ? '<a href="admin/">' + icon("layout-dashboard") + '<strong>进入管理后台</strong><span>管理员可以维护车辆、轮播图、页面区块和系统设置。</span></a>'
      : "";
    var inquiryHtml = inquiries.map(function (item) {
      return '<article class="user-record">'
        + '<strong>' + escapeHtml(item.vehicle_interest || "未填写意向车型") + '</strong>'
        + '<p>' + escapeHtml(item.status || "新询盘") + ' · ' + escapeHtml(item.destination || "目的地待确认") + ' · ' + escapeHtml(item.created_at || "") + '</p>'
        + '<span>' + escapeHtml(item.message || item.budget || "暂无备注") + '</span>'
        + '</article>';
    }).join("") || '<p class="form-note">暂无询盘记录。</p>';
    var postHtml = posts.map(function (post) {
      var status = { pending: "待审核", approved: "已通过", rejected: "已驳回", hidden: "已隐藏" }[post.moderation_status] || post.moderation_status || "待审核";
      return '<article class="user-record">'
        + '<strong>' + escapeHtml(post.title || "未命名帖子") + '</strong>'
        + '<p>' + escapeHtml(status) + ' · ' + escapeHtml([post.brand, post.model, post.model_year].filter(Boolean).join(" / ") || "车型待补充") + '</p>'
        + '<span>' + escapeHtml(post.content || "暂无内容") + '</span>'
        + '</article>';
    }).join("") || '<p class="form-note">暂无论坛内容。</p>';
    var messages = [];
    if (userCenterState.error) {
      messages.push({ title: "账户消息", meta: "系统提示", body: userCenterState.error });
    }
    inquiries.slice(0, 4).forEach(function (item) {
      messages.push({
        title: item.vehicle_interest || "询盘跟进",
        meta: item.status || "新询盘",
        body: item.admin_note || item.message || "业务人员会根据询盘继续跟进。"
      });
    });
    posts.slice(0, 4).forEach(function (post) {
      var status = { pending: "待审核", approved: "已通过", rejected: "已驳回", hidden: "已隐藏" }[post.moderation_status] || post.moderation_status || "待审核";
      messages.push({
        title: post.title || "论坛内容",
        meta: "论坛审核：" + status,
        body: post.admin_note || "内容状态有变化时会在这里提示。"
      });
    });
    threads.slice(0, 6).forEach(function (thread) {
      messages.push({
        title: thread.product_title || "在线消息",
        meta: ({ open: "待回复", follow_up: "跟进中", closed: "已处理" })[thread.status] || "在线消息",
        body: thread.last_message || "后台回复会显示在这里。"
      });
    });
    var messageHtml = messages.map(function (message) {
      return '<article class="user-record">'
        + '<strong>' + escapeHtml(message.title) + '</strong>'
        + '<p>' + escapeHtml(message.meta) + '</p>'
        + '<span>' + escapeHtml(message.body) + '</span>'
        + '</article>';
    }).join("") || '<p class="form-note">暂无消息。</p>';
    panel.innerHTML = ''
      + '<div class="user-profile-panel">'
      + '<div class="user-avatar-large">' + escapeHtml(initial) + '</div>'
      + '<div><h2>' + escapeHtml(name) + '</h2><p>' + escapeHtml(user.account || "") + ' · ' + escapeHtml(user.role || "普通用户") + '</p><p>这里可以维护你的联系资料，方便业务人员跟进询价和论坛内容。</p></div>'
      + '</div>'
      + '<form class="user-profile-form" data-profile-form>'
      + '<div class="form-row"><label>显示名称<input name="display_name" value="' + escapeHtml(user.display_name || "") + '"></label><label>邮箱<input name="email" value="' + escapeHtml(user.email || "") + '"></label></div>'
      + '<div class="form-row"><label>电话 / WhatsApp<input name="phone" value="' + escapeHtml(user.phone || "") + '"></label><label>所在地区<input name="region" value="' + escapeHtml(user.region || "") + '"></label></div>'
      + '<label>公司 / 身份<input name="company" value="' + escapeHtml(user.company || "") + '"></label>'
      + '<label>头像 URL<input name="avatar_url" value="' + escapeHtml(user.avatar_url || "") + '"></label>'
      + '<div class="form-actions"><button class="btn btn-primary" type="submit"><span>保存资料</span>' + icon("save") + '</button><span class="form-note" data-profile-note></span></div>'
      + '</form>'
      + '<div class="user-center-grid">'
      + '<a href="contact.html">' + icon("send") + '<strong>发起新询盘</strong><span>提交车型、数量、目的地和预算。</span></a>'
      + '<a href="#user-messages">' + icon("bell") + '<strong>消息中心</strong><span>查看询盘跟进、论坛审核和系统提示。</span></a>'
      + '<a href="#user-forum-publish">' + icon("messages-square") + '<strong>发布车辆到论坛</strong><span>在用户中心直接提交车辆内容。</span></a>'
      + adminLink
      + '</div>'
      + '<div class="user-center-records">'
      + '<section class="user-center-card" id="user-messages"><h2>消息中心</h2><div class="user-record-list">' + messageHtml + '</div></section>'
      + '<section class="user-center-card"><h2>我的询盘</h2><div class="user-record-list">' + inquiryHtml + '</div></section>'
      + '<section class="user-center-card"><h2>我的论坛内容</h2><div class="user-record-list">' + postHtml + '</div></section>'
      + '<section class="user-center-card user-center-card-wide" id="user-forum-publish"><h2>论坛车辆发布</h2>'
      + '<form class="forum-form user-forum-form" data-user-forum-form>'
      + '<label><span>标题</span><input type="text" name="title" required placeholder="例如：Toyota RAV4 2.0L 车型体验"></label>'
      + '<label><span>内容分类</span><select name="topic_category">' + forumCategoryOptions("general") + '</select></label>'
      + '<div class="forum-form-grid"><label><span>品牌</span><input type="text" name="brand" placeholder="Toyota"></label><label><span>车型</span><input type="text" name="model" placeholder="RAV4"></label></div>'
      + '<div class="forum-form-grid"><label><span>年份</span><input type="text" name="model_year" placeholder="2024"></label><label><span>图片链接</span><input type="url" name="image_url" placeholder="https://..."></label></div>'
      + forumMediaUploaderHtml()
      + '<label><span>车辆描述</span><textarea name="content" rows="5" required placeholder="写下车辆配置、车况、采购需求或出口经验"></textarea></label>'
      + '<button class="btn btn-primary form-submit" type="submit"><span>提交到车型论坛</span>' + icon("send") + '</button>'
      + '<p class="form-note" data-user-forum-note>提交后会进入论坛审核流程。</p>'
      + '</form></section>'
      + '</div>';
    if (window.lucide) window.lucide.createIcons();
  }

  async function loadUserCenterData() {
    if (!publicAuth.user || userCenterState.loading) return;
    userCenterState.loading = true;
    try {
      const [inquiryResponse, postResponse, messageResponse] = await Promise.all([
        fetch("/api/auth/inquiries", { credentials: "same-origin", cache: "no-store" }),
        fetch("/api/auth/forum-posts", { credentials: "same-origin", cache: "no-store" }),
        fetch("/api/auth/messages", { credentials: "same-origin", cache: "no-store" })
      ]);
      const inquiryPayload = await inquiryResponse.json().catch(function () { return {}; });
      const postPayload = await postResponse.json().catch(function () { return {}; });
      const messagePayload = await messageResponse.json().catch(function () { return {}; });
      if (!inquiryResponse.ok) throw new Error(inquiryPayload.error || "询盘加载失败");
      if (!postResponse.ok) throw new Error(postPayload.error || "论坛内容加载失败");
      if (!messageResponse.ok) throw new Error(messagePayload.error || "消息加载失败");
      userCenterState = {
        token: accountName(),
        loading: false,
        inquiries: inquiryPayload.inquiries || [],
        posts: postPayload.posts || [],
        threads: messagePayload.threads || [],
        error: ""
      };
    } catch (error) {
      userCenterState = { token: accountName(), loading: false, inquiries: [], posts: [], threads: [], error: error.message };
    }
    renderUserCenter();
  }

  function openOverlay(overlay) {
    if (!overlay) return;
    overlay.classList.add("is-open");
    document.body.classList.add("modal-open");
    header && header.classList.remove("is-hidden");
  }

  function closeOverlay(overlay) {
    if (!overlay) return;
    overlay.classList.remove("is-open");
    document.body.classList.remove("modal-open");
  }

  function setupReveal() {
    const items = document.querySelectorAll("[data-reveal]");
    if (!items.length) return;
    if (!("IntersectionObserver" in window)) {
      items.forEach(function (item) { item.classList.add("is-visible"); });
      return;
    }
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.18 });
    items.forEach(function (item, index) {
      item.style.transitionDelay = `${Math.min(index * 70, 280)}ms`;
      observer.observe(item);
    });
  }

  async function boot() {
    createHeaderTools();
    setActiveNav();
    applyLanguage(activeLang);

    // Public content can load while the account session is being checked.
    await Promise.all([checkPublicSession(), loadSiteData()]);
    await loadVehiclesForCurrentPage();
    await loadPartsForCurrentPage();
    loadExchangeRate();
    await loadForumDetail();
    setupForumPage();
    renderUserCenter();
    setupCarousel();
    setupReveal();
    applyLanguage(activeLang);
    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
    if (window.lucide) window.lucide.createIcons();
  }

  if (toggle && nav) {
    nav.id = nav.id || "site-navigation";
    toggle.setAttribute("aria-controls", nav.id);
    toggle.addEventListener("click", function () {
      closeLanguageMenu();
      const opened = document.body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(opened));
      toggle.setAttribute("aria-label", opened ? "关闭导航" : "打开导航");
      toggle.innerHTML = icon(opened ? "x" : "menu");
      header && header.classList.remove("is-hidden");
      if (window.lucide) window.lucide.createIcons();
      if (opened) {
        window.setTimeout(function () {
          if (document.body.classList.contains("nav-open")) nav.querySelector("a")?.focus();
        }, 180);
      }
    });

    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) closeNav();
    });

    document.addEventListener("click", function (event) {
      if (document.body.classList.contains("nav-open") && !event.composedPath().includes(header)) closeNav();
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth >= 1280) closeNav();
    });
  }

  document.addEventListener("click", function (event) {
    const chatOpen = event.target.closest("[data-chat-open]");
    if (chatOpen) {
      event.preventDefault();
      openProductChat(chatProductFromButton(chatOpen));
      return;
    }

    const accountToggle = event.target.closest("[data-account-toggle]");
    if (accountToggle) {
      event.preventDefault();
      toggleAccountEntry();
      return;
    }

    if (accountMenu && !accountMenu.hidden && !event.target.closest("[data-account-menu]")) {
      closeAccountMenu();
    }

    if (!event.target.closest("[data-language-menu]")) {
      closeLanguageMenu();
    }

    const galleryThumb = event.target.closest("[data-gallery-thumb]");
    if (galleryThumb) {
      const gallery = galleryThumb.closest(".vehicle-gallery");
      const main = gallery ? gallery.querySelector("[data-gallery-main]") : null;
      if (main && galleryThumb.dataset.image) {
        main.style.setProperty("--gallery-image", cssImage(galleryThumb.dataset.image));
        main.dataset.fallbackImage = galleryThumb.dataset.fallbackImage || "";
        gallery.querySelectorAll("[data-gallery-thumb]").forEach(function (button) {
          button.classList.toggle("is-active", button === galleryThumb);
        });
        hydrateImageFallbacks(gallery);
      }
    }

    const usedPageButton = event.target.closest("[data-used-page]");
    if (usedPageButton) {
      usedPage = parseInt(usedPageButton.dataset.usedPage, 10) || 1;
      updateUsedPageUrl();
      renderDynamicVehicles();
      applyLanguage(activeLang);
      if (window.lucide) window.lucide.createIcons();
      document.querySelector(".used-product-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    const newPageButton = event.target.closest("[data-new-page]");
    if (newPageButton) {
      newPage = parseInt(newPageButton.dataset.newPage, 10) || 1;
      updateNewPageUrl();
      renderDynamicVehicles();
      applyLanguage(activeLang);
      if (window.lucide) window.lucide.createIcons();
      document.querySelector(".catalog-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    const newCategoryButton = event.target.closest("[data-new-category]");
    if (newCategoryButton) {
      document.querySelectorAll("[data-new-category]").forEach(function (button) {
        button.classList.toggle("is-active", button === newCategoryButton);
      });
      newPage = 1;
      updateNewPageUrl();
      renderNewProductGrid(filteredNewVehicles());
      applyLanguage(activeLang);
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    if (event.target.closest("[data-forum-publish-toggle]")) {
      toggleForumPublishPanel();
      return;
    }

    const forumMediaTrigger = event.target.closest("[data-forum-media-trigger]");
    if (forumMediaTrigger) {
      const form = forumMediaTrigger.closest("form");
      if (!publicAuth.user) {
        openAccountLogin();
        return;
      }
      form?.querySelector("[data-forum-media-upload]")?.click();
      return;
    }

    const forumMediaRemove = event.target.closest("[data-forum-media-remove]");
    if (forumMediaRemove) {
      const form = forumMediaRemove.closest("form");
      const index = Number(forumMediaRemove.dataset.forumMediaRemove);
      const media = parseForumMedia(form);
      media.splice(index, 1);
      writeForumMedia(form, media);
      return;
    }

    const forumCategoryButton = event.target.closest("[data-forum-category]");
    if (forumCategoryButton) {
      setActiveForumCategory(forumCategoryButton.dataset.forumCategory || "");
      loadForumPosts();
      return;
    }

    const langOption = event.target.closest("[data-lang-option]");
    if (langOption) {
      applyLanguage(langOption.dataset.langOption, { userSelected: true });
      closeLanguageMenu();
      return;
    }

    if (event.target.closest("[data-lang-toggle]")) {
      toggleLanguageMenu();
      return;
    }

    if (event.target.closest("[data-search-open]")) {
      createSearchOverlay();
      renderSearchResults();
      openOverlay(searchOverlay);
      window.setTimeout(function () {
        searchInput && searchInput.focus();
      }, 50);
    }

    const floatingContact = event.target.closest(".floating-contact");
    if (floatingContact) {
      event.preventDefault();
      createInquiryOverlay();
      applyLanguage(activeLang);
      openOverlay(inquiryOverlay);
      window.setTimeout(function () {
        inquiryOverlay?.querySelector("[name='contact']")?.focus();
      }, 50);
    }

    const authTarget = event.target.closest("[data-auth-open]");
    if (authTarget) {
      closeAccountMenu();
      createAuthOverlay();
      setAuthMode(authTarget.getAttribute("data-auth-open") || "login");
      openOverlay(authOverlay);
    }

    if (event.target.closest("[data-menu-link]")) {
      closeAccountMenu();
      closeNav();
    }

    const partCategoryButton = event.target.closest("[data-part-category]");
    if (partCategoryButton && !partCategoryButton.disabled) {
      document.querySelectorAll("[data-part-category]").forEach(function (button) {
        button.classList.toggle("is-active", button === partCategoryButton);
      });
      partPage = 1;
      loadPartListPage({ page: 1 });
    }

    const partPageButton = event.target.closest("[data-part-page]");
    if (partPageButton && !partPageButton.disabled) {
      partPage = parseInt(partPageButton.dataset.partPage, 10) || 1;
      loadPartListPage({ page: partPage });
      document.querySelector("[data-part-grid]")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    const partRetryButton = event.target.closest("[data-part-retry]");
    if (partRetryButton) {
      loadPartListPage({ page: partPage });
    }

    const usedIdSearch = event.target.closest("[data-used-id-search]");
    if (usedIdSearch) {
      const idInput = document.querySelector("[data-used-filter='id']");
      usedFilters.id = (idInput?.value || "").trim();
      ["brand", "model", "price", "year", "mileage"].forEach(function (key) { usedFilters[key] = ""; });
      usedPage = 1;
      updateUsedPageUrl();
      const usedVehicles = siteData.vehicles.filter((vehicle) => vehicle.vehicle_type === "used" && vehicle.is_active !== false);
      renderUsedFilterPanel(usedVehicles);
      renderUsedProductGrid(usedVehicles);
      applyTranslatedDataAttributes();
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    const usedFilterReset = event.target.closest("[data-used-filter-reset]");
    if (usedFilterReset) {
      Object.keys(usedFilters).forEach(function (key) { usedFilters[key] = ""; });
      usedPage = 1;
      updateUsedPageUrl();
      const usedVehicles = siteData.vehicles.filter((vehicle) => vehicle.vehicle_type === "used" && vehicle.is_active !== false);
      renderUsedFilterPanel(usedVehicles);
      renderUsedProductGrid(usedVehicles);
      applyTranslatedDataAttributes();
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    if (event.target.closest("[data-auth-logout]")) {
      logoutPublicUser();
    }
  });

  document.addEventListener("input", function (event) {
    if (event.target.matches("[data-used-filter='id']")) {
      usedFilters.id = event.target.value.trim();
    }

    if (event.target.matches("[data-part-search]")) {
      partPage = 1;
      clearTimeout(loadPartListPage.searchTimer);
      loadPartListPage.searchTimer = setTimeout(function () {
        loadPartListPage({ page: 1 });
      }, 260);
    }

    if (event.target.matches("[data-forum-search]")) {
      clearTimeout(forumSearchTimer);
      forumSearchTimer = window.setTimeout(loadForumPosts, 240);
    }
  });

  document.addEventListener("change", function (event) {
    const filter = event.target.closest("[data-used-filter]");
    if (!filter || filter.dataset.usedFilter === "id") return;
    usedFilters[filter.dataset.usedFilter] = filter.value;
    if (filter.dataset.usedFilter === "brand") usedFilters.model = "";
    usedPage = 1;
    updateUsedPageUrl();
    const usedVehicles = siteData.vehicles.filter((vehicle) => vehicle.vehicle_type === "used" && vehicle.is_active !== false);
    renderUsedFilterPanel(usedVehicles);
    renderUsedProductGrid(usedVehicles);
    applyTranslatedDataAttributes();
    if (window.lucide) window.lucide.createIcons();
  });

  document.addEventListener("change", function (event) {
    const forumUploadInput = event.target.closest("[data-forum-media-upload]");
    if (forumUploadInput) {
      handleForumMediaUpload(forumUploadInput);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeOverlay(searchOverlay);
      closeOverlay(authOverlay);
      closeOverlay(inquiryOverlay);
      stopChatPolling();
      closeOverlay(chatOverlay);
      closeAccountMenu();
      closeLanguageMenu();
      closeNav();
    }
  });

  document.addEventListener("submit", async function (event) {
    const chatForm = event.target.closest("[data-chat-form]");
    if (chatForm) {
      event.preventDefault();
      try {
        await submitChatMessage(chatForm);
      } catch (error) {
        const note = chatForm.querySelector("[data-chat-note]");
        if (note) {
          note.classList.remove("is-success");
          note.textContent = error.message;
        }
      }
      return;
    }

    const userForumForm = event.target.closest("[data-user-forum-form]");
    if (userForumForm) {
      event.preventDefault();
      if (!publicAuth.user) {
        openAccountLogin();
        return;
      }
      const note = userForumForm.querySelector("[data-user-forum-note]");
      try {
        if (note) {
          note.classList.remove("is-success");
          note.textContent = "正在提交论坛内容...";
        }
        const payload = await requestJson("/api/forum/posts", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(Object.fromEntries(new FormData(userForumForm).entries()))
        }, "发布失败");
        userForumForm.reset();
        writeForumMedia(userForumForm, []);
        if (note) {
          note.classList.add("is-success");
          note.textContent = payload.post && payload.post.moderation_status === "approved"
            ? "发布成功，已加入车型论坛。"
            : "已提交，审核后展示。";
        }
        window.setTimeout(function () {
          userCenterState.token = "";
          loadUserCenterData();
        }, 900);
      } catch (error) {
        if (note) {
          note.classList.remove("is-success");
          note.textContent = error.message;
        }
      }
      return;
    }

    const profileForm = event.target.closest("[data-profile-form]");
    if (profileForm) {
      event.preventDefault();
      if (!publicAuth.user) {
        openAccountLogin();
        return;
      }
      const note = profileForm.querySelector("[data-profile-note]");
      try {
        if (note) note.textContent = "正在保存资料...";
        const payload = await requestJson("/api/auth/profile", {
          method: "PATCH",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(Object.fromEntries(new FormData(profileForm).entries()))
        }, "资料保存失败");
        publicAuth.user = payload.user;
        if (note) {
          note.classList.add("is-success");
          note.textContent = "资料已保存。";
        }
        updatePublicAuthUI();
      } catch (error) {
        if (note) {
          note.classList.remove("is-success");
          note.textContent = error.message;
        }
      }
      return;
    }

    const form = event.target.closest("[data-contact-form]");
    if (!form) return;
    event.preventDefault();
    if (form.dataset.submitting === "true") return;
    form.dataset.submitting = "true";
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    const note = form.querySelector("[data-form-note]");
    const data = Object.fromEntries(new FormData(form).entries());
    if (!data.vehicle_interest) data.vehicle_interest = data.service || "";
    data.source_page = `${location.pathname}${location.search}`;
    if (publicAuth.user) {
      data.name = data.name || accountName();
    }
    try {
      if (note) {
        note.classList.remove("is-success");
        note.textContent = ({ zh: "正在提交询盘...", en: "Submitting inquiry...", ru: "Отправка запроса..." })[activeLang];
      }
      await requestJson("/api/inquiries", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
      }, "提交失败");
      if (note) {
        note.classList.add("is-success");
        note.textContent = ({
          zh: "询盘已提交，业务人员会尽快联系你。",
          en: "Inquiry submitted. Our team will contact you soon.",
          ru: "Запрос отправлен. Менеджер скоро свяжется с вами."
        })[activeLang];
      }
      form.reset();
      userCenterState.token = "";
    } catch (error) {
      if (note) {
        note.classList.remove("is-success");
        note.textContent = error.message;
      }
    } finally {
      delete form.dataset.submitting;
      if (submitButton) submitButton.disabled = false;
    }
  });

  window.addEventListener("load", function () {
    if (window.lucide) window.lucide.createIcons();
  });

  boot();
})();
