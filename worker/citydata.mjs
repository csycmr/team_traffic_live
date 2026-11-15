const areaCode = 'POI009';
const endpoint = 'http://openapi.seoul.go.kr:8088';
const cacheTimeMs = 60_000;
let cached;

const entities = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" };

function field(xml, tag) {
  const value = xml.match(new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>`))?.[1]?.trim();
  if (!value) return null;
  if (value.startsWith('<![CDATA[') && value.endsWith(']]>')) return value.slice(9, -3);
  return value.replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (original, entity) => {
    if (!entity.startsWith('#')) return entities[entity] ?? original;
    const code = entity.startsWith('#x') ? parseInt(entity.slice(2), 16) : Number(entity.slice(1));
    return code <= 0x10ffff ? String.fromCodePoint(code) : original;
  });
}

function numericField(xml, tag) {
  const value = field(xml, tag);
  return value !== null && /^-?\d+(?:\.\d+)?$/.test(value) ? Number(value) : null;
}

function section(xml, tag, firstField) {
  const start = xml.indexOf(`<${tag}>`);
  if (start === -1) return '';
  const end = xml.indexOf(`</${tag}>`, start);
  const first = xml.indexOf(`<${firstField}>`, start);
  return first !== -1 && first < end ? xml.slice(first, end) : '';
}

export function parseCitydata(xml) {
  if (field(xml, 'RESULT\\.CODE') !== 'INFO-000' || field(xml, 'AREA_CD') !== areaCode) {
    throw new Error('Unexpected Seoul Citydata response');
  }
  const road = section(xml, 'ROAD_TRAFFIC_STTS', 'ROAD_TRAFFIC_SPD');
  const weather = section(xml, 'WEATHER_STTS', 'TEMP').split('<FCST24HOURS>')[0];
  // The XML may repeat the same wrapper name for the list and its entries.
  const incidentXml = [...xml.matchAll(/<ACDNT_CNTRL_STTS>(?:(?!<ACDNT_CNTRL_STTS>)[\s\S])*?<\/ACDNT_CNTRL_STTS>/g)];
  const incidents = incidentXml.flatMap(([item]) => {
    const detail = field(item, 'ACDNT_INFO');
    const occurredAt = field(item, 'ACDNT_OCCR_DT');
    if (!detail && !occurredAt) return [];
    return [{
      occurredAt,
      expectedEndAt: field(item, 'EXP_CLR_DT'),
      type: field(item, 'ACDNT_TYPE'),
      subtype: field(item, 'ACDNT_DTYPE'),
      detail,
      updatedAt: field(item, 'ACDNT_TIME'),
    }];
  });
  return {
    source: '서울 열린데이터광장 · 서울시 실시간 도시데이터',
    area: { code: areaCode, name: '광화문·덕수궁' },
    fetchedAt: new Date().toISOString(),
    traffic: road ? {
      status: field(road, 'ROAD_TRAFFIC_IDX'),
      averageSpeedKmh: numericField(road, 'ROAD_TRAFFIC_SPD'),
      message: field(road, 'ROAD_MSG'),
      updatedAt: field(road, 'ROAD_TRAFFIC_TIME'),
    } : null,
    weather: weather ? {
      temperatureC: numericField(weather, 'TEMP'),
      humidityPercent: numericField(weather, 'HUMIDITY'),
      precipitationType: field(weather, 'PRECPT_TYPE'),
      updatedAt: field(weather, 'WEATHER_TIME'),
    } : null,
    incidents: /<ACDNT_CNTRL_STTS(?:\s|>|\/)/.test(xml) ? incidents : null,
  };
}

function citydataJson(body, status, headers = {}) {
  return Response.json(body, {
    status,
    headers: { 'cache-control': 'no-store', ...headers },
  });
}

export async function citydata(request, env) {
  if (request.method !== 'GET') {
    return citydataJson({ error: 'method_not_allowed' }, 405, { allow: 'GET' });
  }
  const key = env.SEOUL_CITYDATA_API_KEY?.trim();
  if (!key) {
    return citydataJson({ error: 'citydata_not_configured' }, 503);
  }
  if (cached?.key === key && Date.now() < cached.expiresAt) {
    return citydataJson(cached.data, 200, { 'cache-control': 'private, max-age=60' });
  }
  let upstream;
  let xml;
  try {
    const url = `${endpoint}/${encodeURIComponent(key)}/xml/citydata/1/5/${areaCode}`;
    upstream = await fetch(url, {
      signal: AbortSignal.timeout(8_000),
      redirect: 'manual',
      headers: { accept: 'application/xml' },
    });
    if (!upstream.ok) {
      return citydataJson({ error: 'citydata_upstream_http', status: upstream.status }, 502);
    }
    xml = await upstream.text();
  } catch (error) {
    const code = error?.name === 'TimeoutError' ? 'citydata_upstream_timeout' : 'citydata_upstream_connection';
    return citydataJson({ error: code }, 502);
  }

  const resultCode = field(xml, 'RESULT\\.CODE') ?? field(xml, 'CODE');
  if (resultCode !== 'INFO-000' && /^(?:ERROR|INFO)-[0-9]{3}$/.test(resultCode ?? '')) {
    return citydataJson({ error: 'citydata_upstream_api', code: resultCode }, 502);
  }
  try {
    const data = parseCitydata(xml);
    cached = { key, data, expiresAt: Date.now() + cacheTimeMs };
    return citydataJson(data, 200, { 'cache-control': 'private, max-age=60' });
  } catch {
    return citydataJson({ error: 'citydata_upstream_response' }, 502);
  }
}
