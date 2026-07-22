#!/usr/bin/env node

/**
 * Refresh the flight and hotel sections of the travel snapshot by orchestrating
 * the official FlyAI CLI. This file deliberately contains no Fliggy endpoint
 * or crawler implementation: every quote comes from `search-flight` or
 * `search-hotel`, as required by the installed FlyAI skill.
 */

import { spawn } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const CLI_PACKAGE = '@fly-ai/flyai-cli';
const CLI_VERSION = '1.0.16';
const SNAPSHOT_PATH = path.resolve(
  process.cwd(),
  process.env.TRAVEL_SNAPSHOT || 'src/data/travel/snapshot.json',
);
const QUERY_TIMEOUT_MS = Number(process.env.FLYAI_QUERY_TIMEOUT_MS || 90_000);
const TWO_DAYS_MS = 48 * 60 * 60 * 1_000;

const flightQueries = [
  {
    id: 'shenyang-xining-outbound',
    direction: '去程',
    origin: '沈阳',
    destination: '西宁',
    depDateStart: '2026-08-01',
    depDateEnd: '2026-08-04',
  },
  {
    id: 'shenyang-lanzhou-outbound',
    direction: '去程',
    origin: '沈阳',
    destination: '兰州',
    depDateStart: '2026-08-01',
    depDateEnd: '2026-08-04',
  },
  {
    id: 'xining-shenyang-return',
    direction: '返程',
    origin: '西宁',
    destination: '沈阳',
    depDateStart: '2026-08-04',
    depDateEnd: '2026-08-11',
  },
  {
    id: 'lanzhou-shenyang-return',
    direction: '返程',
    origin: '兰州',
    destination: '沈阳',
    depDateStart: '2026-08-04',
    depDateEnd: '2026-08-11',
  },
];

const hotelQueries = [
  { id: 'xining-0801', city: '西宁', destName: '西宁', checkIn: '2026-08-01', checkOut: '2026-08-02' },
  {
    id: 'chaka-0802',
    city: '茶卡',
    destName: '乌兰县',
    poiName: '茶卡盐湖',
    checkIn: '2026-08-02',
    checkOut: '2026-08-03',
  },
  {
    id: 'dachaidan-0803',
    city: '大柴旦',
    destName: '海西蒙古族藏族自治州',
    keyWords: '大柴旦',
    checkIn: '2026-08-03',
    checkOut: '2026-08-04',
  },
  { id: 'dunhuang-0804', city: '敦煌', destName: '敦煌市', checkIn: '2026-08-04', checkOut: '2026-08-06' },
  { id: 'zhangye-0806', city: '张掖', destName: '张掖市', checkIn: '2026-08-06', checkOut: '2026-08-07' },
];

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function cleanText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function publicUrl(value) {
  const candidate = cleanText(value);
  return /^https?:\/\//i.test(candidate) ? candidate : '';
}

function exactPrice(value) {
  const text = String(value ?? '').replaceAll(',', '').trim();
  if (!text || /[xX*＊]/.test(text)) return null;
  const match = text.match(/\d+(?:\.\d+)?/);
  if (!match) return null;
  const price = Math.round(Number(match[0]));
  return Number.isFinite(price) && price > 0 ? price : null;
}

function parseCliPayload(stdout) {
  const trimmed = stdout.trim();
  if (!trimmed) throw new Error('FlyAI CLI returned empty stdout.');
  const candidates = [trimmed, ...trimmed.split(/\r?\n/).reverse()];
  for (const candidate of candidates) {
    try {
      const payload = JSON.parse(candidate);
      if (payload && typeof payload === 'object') return payload;
    } catch {
      // Try the next complete line. The CLI contract is one-line JSON, but
      // this keeps the wrapper tolerant of package-manager notices.
    }
  }
  throw new Error('FlyAI CLI stdout did not contain valid JSON.');
}

function compactError(stderr, exitCode) {
  const withoutKey = process.env.FLYAI_API_KEY
    ? stderr.replaceAll(process.env.FLYAI_API_KEY, '[redacted]')
    : stderr;
  const useful = withoutKey
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.includes('Assertion failed'))
    .slice(0, 3)
    .join(' ');
  return useful || `FlyAI CLI exited with code ${String(exitCode)}.`;
}

function runFlyai(subcommand, args) {
  return new Promise((resolve, reject) => {
    const isWindows = process.platform === 'win32';
    const executable = isWindows ? process.env.ComSpec || 'cmd.exe' : 'npx';
    const commandArgs = isWindows
      ? ['/d', '/s', '/c', 'npx.cmd', '--yes', `${CLI_PACKAGE}@${CLI_VERSION}`, subcommand, ...args]
      : ['--yes', `${CLI_PACKAGE}@${CLI_VERSION}`, subcommand, ...args];
    const child = spawn(
      executable,
      commandArgs,
      {
        cwd: process.cwd(),
        env: process.env,
        windowsHide: true,
        shell: false,
      },
    );

    let stdout = '';
    let stderr = '';
    const timeout = setTimeout(() => child.kill(), QUERY_TIMEOUT_MS);
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    child.on('error', (error) => {
      clearTimeout(timeout);
      reject(error);
    });
    child.on('close', (exitCode) => {
      clearTimeout(timeout);
      try {
        const payload = parseCliPayload(stdout);
        // Node 24 on Windows can currently hit a libuv assertion after the
        // official CLI has already printed a valid success payload. The JSON
        // status is therefore authoritative; the process code is diagnostic.
        if (Number(payload.status) === 0) {
          resolve({ payload, exitCode, stderr });
          return;
        }
        reject(new Error(cleanText(payload.message) || compactError(stderr, exitCode)));
      } catch (error) {
        reject(new Error(`${error.message} ${compactError(stderr, exitCode)}`.trim()));
      }
    });
  });
}

function durationMinutes(value) {
  const text = cleanText(value);
  if (!text) return null;
  if (/^\d+$/.test(text)) return Number(text);
  const hours = Number(text.match(/(\d+(?:\.\d+)?)\s*(?:小时|h)/i)?.[1] || 0);
  const minutes = Number(text.match(/(\d+)\s*(?:分钟|min)/i)?.[1] || 0);
  const total = Math.round(hours * 60 + minutes);
  return total > 0 ? total : null;
}

function normalizeFlight(item, query) {
  const price = exactPrice(item?.ticketPrice ?? item?.adultPrice ?? item?.price);
  const journey = Array.isArray(item?.journeys) ? item.journeys[0] : null;
  const segments = Array.isArray(journey?.segments) ? journey.segments : [];
  const first = segments[0];
  const last = segments.at(-1);
  const jumpUrl = publicUrl(item?.jumpUrl);
  if (!price || !first || !last || !jumpUrl) return null;

  const flightNumbers = segments
    .map((segment) => cleanText(segment?.marketingTransportNo || segment?.transportNo))
    .filter(Boolean);
  const airlines = [...new Set(
    segments
      .map((segment) => cleanText(segment?.marketingTransportName))
      .filter(Boolean),
  )];
  const direct = segments.length === 1 || cleanText(journey?.journeyType).includes('直达');
  const duration = cleanText(item?.totalDuration || journey?.totalDuration || first?.duration);

  return {
    id: `${query.id}-${cleanText(first?.depDateTime)}-${flightNumbers.join('-') || price}`,
    routeId: query.id,
    direction: query.direction,
    origin: cleanText(first?.depCityName) || query.origin,
    destination: cleanText(last?.arrCityName) || query.destination,
    departureAirport: cleanText(first?.depStationName || first?.depStationShortName),
    arrivalAirport: cleanText(last?.arrStationName || last?.arrStationShortName),
    departureAt: cleanText(first?.depDateTime),
    arrivalAt: cleanText(last?.arrDateTime),
    flightNumbers,
    airlines,
    seatClass: cleanText(first?.seatClassName) || '经济舱',
    direct,
    stops: Math.max(0, segments.length - 1),
    duration,
    durationMinutes: durationMinutes(duration),
    price,
    jumpUrl,
  };
}

function chooseFlightOffers(items) {
  const seen = new Set();
  return items
    .filter((item) => item.durationMinutes === null || item.durationMinutes <= 12 * 60)
    .sort((a, b) => {
      const aScore = a.price + (a.direct ? 0 : 220) + Math.max(0, (a.durationMinutes || 0) - 300) * 0.45;
      const bScore = b.price + (b.direct ? 0 : 220) + Math.max(0, (b.durationMinutes || 0) - 300) * 0.45;
      return aScore - bScore;
    })
    .filter((item) => {
      const key = `${item.departureAt}|${item.flightNumbers.join('-')}|${item.price}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 3);
}

function nightsBetween(checkIn, checkOut) {
  return Math.max(1, Math.round((Date.parse(checkOut) - Date.parse(checkIn)) / 86_400_000));
}

function normalizeHotel(item, query) {
  const price = exactPrice(item?.price);
  const name = cleanText(item?.name);
  const detailUrl = publicUrl(item?.detailUrl);
  const mainPic = publicUrl(item?.mainPic);
  if (!price || !name || !detailUrl || !mainPic) return null;
  return {
    id: `${query.id}-${cleanText(item?.shId) || name}`,
    stayId: query.id,
    city: query.city,
    checkIn: query.checkIn,
    checkOut: query.checkOut,
    nights: nightsBetween(query.checkIn, query.checkOut),
    name,
    pricePerRoomNight: price,
    twoRoomsPerNight: price * 2,
    twoRoomStayTotal: price * 2 * nightsBetween(query.checkIn, query.checkOut),
    score: cleanText(item?.score),
    scoreDesc: cleanText(item?.scoreDesc),
    star: cleanText(item?.star),
    address: cleanText(item?.address),
    nearby: cleanText(item?.interestsPoi),
    mainPic,
    detailUrl,
  };
}

function chooseHotelOffers(items) {
  const excluded = /小时房|钟点房|青年旅舍|青旅|招待所|旅社|露营|营地|沙漠/;
  const practical = items.filter(
    (item) => item.pricePerRoomNight >= 120
      && item.pricePerRoomNight <= 1_200
      && !excluded.test(item.name),
  );
  const pool = practical.length ? practical : items.filter((item) => !excluded.test(item.name));
  return pool.slice(0, 3);
}

function priceRange(values) {
  const prices = values.filter((value) => Number.isFinite(value) && value > 0);
  if (!prices.length) return null;
  return { min: Math.min(...prices), max: Math.max(...prices) };
}

function dedupeMessages(messages) {
  return [...new Set(messages.map(cleanText).filter(Boolean))];
}

async function collectFlights(priorFlyai, failures, messages) {
  const priorRoutes = new Map(
    (priorFlyai?.flights?.routes || []).map((route) => [route.id, route]),
  );
  const routes = [];
  let freshCount = 0;

  for (const query of flightQueries) {
    try {
      const { payload, exitCode } = await runFlyai('search-flight', [
        '--origin', query.origin,
        '--destination', query.destination,
        '--dep-date-start', query.depDateStart,
        '--dep-date-end', query.depDateEnd,
        '--journey-type', '1',
        '--seat-class-name', '经济舱',
        '--sort-type', '3',
      ]);
      messages.push(payload.systemMessage);
      const normalized = (Array.isArray(payload?.data?.itemList) ? payload.data.itemList : [])
        .map((item) => normalizeFlight(item, query))
        .filter(Boolean);
      const offers = chooseFlightOffers(normalized);
      if (!offers.length) throw new Error('No exact, bookable flight quote was returned.');
      routes.push({
        ...query,
        status: 'ok',
        bestPrice: Math.min(...offers.map((offer) => offer.price)),
        offers,
        cliExitCode: exitCode,
      });
      freshCount += 1;
    } catch (error) {
      failures.push({ key: query.id, category: 'flights', message: error.message });
      const prior = priorRoutes.get(query.id);
      routes.push(prior ? { ...prior, status: 'stale' } : { ...query, status: 'error', offers: [] });
    }
    await wait(350);
  }

  const featured = routes.flatMap((route) => route.offers?.slice(0, 1) || []);
  return {
    status: freshCount === flightQueries.length ? 'ok' : freshCount > 0 ? 'partial' : featured.length ? 'stale' : 'error',
    queryWindow: {
      outbound: '2026-08-01—08-04',
      return: '2026-08-04—08-11',
    },
    priceUnit: '每位成人单程',
    priceRange: priceRange(featured.map((offer) => offer.price)),
    routes,
    featured,
    freshQueries: freshCount,
    totalQueries: flightQueries.length,
  };
}

async function collectHotels(priorFlyai, failures, messages) {
  const priorStays = new Map(
    (priorFlyai?.hotels?.stays || []).map((stay) => [stay.id, stay]),
  );
  const stays = [];
  let freshCount = 0;

  for (const query of hotelQueries) {
    try {
      const queryArgs = [
        '--dest-name', query.destName,
        '--check-in-date', query.checkIn,
        '--check-out-date', query.checkOut,
        '--hotel-bed-types', '双床房',
        '--sort', 'rate_desc',
        '--max-price', '1200',
      ];
      if (query.poiName) queryArgs.push('--poi-name', query.poiName);
      if (query.keyWords) queryArgs.push('--key-words', query.keyWords);
      const { payload, exitCode } = await runFlyai('search-hotel', queryArgs);
      messages.push(payload.systemMessage);
      const normalized = (Array.isArray(payload?.data?.itemList) ? payload.data.itemList : [])
        .map((item) => normalizeHotel(item, query))
        .filter(Boolean);
      const offers = chooseHotelOffers(normalized);
      if (!offers.length) throw new Error('No exact hotel quote with an image and booking link was returned.');
      stays.push({
        ...query,
        nights: nightsBetween(query.checkIn, query.checkOut),
        status: 'ok',
        offers,
        cliExitCode: exitCode,
      });
      freshCount += 1;
    } catch (error) {
      failures.push({ key: query.id, category: 'hotels', message: error.message });
      const prior = priorStays.get(query.id);
      stays.push(prior ? { ...prior, status: 'stale' } : { ...query, status: 'error', offers: [] });
    }
    await wait(350);
  }

  const featured = stays.flatMap((stay) => stay.offers?.slice(0, 1) || []);
  return {
    status: freshCount === hotelQueries.length ? 'ok' : freshCount > 0 ? 'partial' : featured.length ? 'stale' : 'error',
    priceUnit: '两间房每晚合计',
    singleRoomNightRange: priceRange(featured.map((offer) => offer.pricePerRoomNight)),
    priceRange: priceRange(featured.map((offer) => offer.twoRoomsPerNight)),
    sevenDayTwoRoomEstimate: featured.reduce((sum, offer) => sum + offer.twoRoomStayTotal, 0),
    roomsRequested: 2,
    roomTypeRequested: '双床房',
    inventoryConfirmed: false,
    stays,
    featured,
    freshQueries: freshCount,
    totalQueries: hotelQueries.length,
  };
}

function mergeCategory(category, live, label) {
  const range = live.priceRange;
  return {
    ...(category || {}),
    label,
    priceStatus: range ? 'flyai-live' : category?.priceStatus || 'insufficient',
    priceRange: range || category?.priceRange || null,
    priceUnit: live.priceUnit,
    liveSource: 'fly.ai / 飞猪',
    flyaiStatus: live.status,
  };
}

async function main() {
  const snapshot = JSON.parse(await readFile(SNAPSHOT_PATH, 'utf8'));
  const priorFlyai = snapshot.flyai || null;
  const failures = [];
  const messages = [];
  const generatedAt = new Date();

  const flights = await collectFlights(priorFlyai, failures, messages);
  const hotels = await collectHotels(priorFlyai, failures, messages);
  const freshQueries = flights.freshQueries + hotels.freshQueries;
  const totalQueries = flights.totalQueries + hotels.totalQueries;
  const hasUsableData = Boolean(flights.featured.length || hotels.featured.length);
  const status = freshQueries === totalQueries
    ? 'ok'
    : freshQueries > 0
      ? 'partial'
      : hasUsableData
        ? 'stale'
        : 'error';
  const systemMessages = dedupeMessages(messages);

  snapshot.schemaVersion = Math.max(Number(snapshot.schemaVersion || 0), 3);
  snapshot.flyai = {
    status,
    generatedAt: generatedAt.toISOString(),
    expiresAt: new Date(generatedAt.getTime() + TWO_DAYS_MS).toISOString(),
    lastSuccessfulAt: freshQueries > 0
      ? generatedAt.toISOString()
      : priorFlyai?.lastSuccessfulAt || null,
    mode: systemMessages.length ? 'trial' : 'api-enhanced',
    skill: {
      name: 'flyai',
      repository: 'https://github.com/alibaba-flyai/flyai-skill',
      cliPackage: CLI_PACKAGE,
      cliVersion: CLI_VERSION,
    },
    flights,
    hotels,
    systemMessages,
    failures,
  };
  snapshot.categories ||= {};
  snapshot.categories.flights = mergeCategory(snapshot.categories.flights, flights, '机票');
  snapshot.categories.hotels = mergeCategory(snapshot.categories.hotels, hotels, '住宿');

  await writeFile(SNAPSHOT_PATH, `${JSON.stringify(snapshot, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    output: SNAPSHOT_PATH,
    status,
    mode: snapshot.flyai.mode,
    freshQueries,
    totalQueries,
    flightOffers: flights.featured.length,
    hotelStays: hotels.featured.length,
    failures: failures.map(({ key, category }) => ({ key, category })),
  }));

  if (!hasUsableData) process.exitCode = 1;
}

main().catch((error) => {
  console.error(`FlyAI refresh failed: ${error.message}`);
  process.exitCode = 1;
});
