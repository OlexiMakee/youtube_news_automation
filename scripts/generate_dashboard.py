#!/usr/bin/env python3
"""
generate_dashboard.py
Generates data/reports/dashboard.html — інтерактивний дашборд конкурентного аналізу UATV English.

Використання:
    python3 scripts/generate_dashboard.py
"""

import sqlite3
import json
import re
import os
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).parent.parent
DB_PATH = REPO / "data" / "youtube_news.db"
REPORTS_DIR = REPO / "data" / "reports" / "english"
OUTPUT_PATH = REPO / "data" / "reports" / "dashboard.html"

EXCLUDE = [
    'Français', 'Deutsch', 'polsku', 'Português', 'Español',
    'Arabic', 'magyarul', 'ТСН', 'FREEДОМ', 'INSIDE RUSSIA', 'FREEДOM'
]


def get_channel_metrics(date_str):
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    end_dt = datetime.strptime(date_str, '%Y-%m-%d')
    start_30d = (end_dt - timedelta(days=30)).strftime('%Y-%m-%d')
    start_month = end_dt.replace(day=1).strftime('%Y-%m-%d')
    qm = ((end_dt.month - 1) // 3) * 3 + 1
    start_quarter = end_dt.replace(month=qm, day=1).strftime('%Y-%m-%d')
    end_str = date_str + 'T23:59:59'

    excl = ' AND '.join([f"ch.channel_name NOT LIKE '%{e}%'" for e in EXCLUDE])

    # WHERE spans the full quarter so that month_views and quarter_views
    # are computed over their proper windows — not just the 30d slice.
    # All three aggregates use CASE WHEN to filter their own period.
    c.execute(f'''
        SELECT
            ch.channel_name,
            COUNT(CASE WHEN v.published_at >= ?  THEN 1 END)                              AS videos,
            ROUND(AVG(CASE WHEN v.published_at >= ?  THEN v.view_count END), 0)           AS avg_views,
            COALESCE(SUM(CASE WHEN v.published_at >= ?  THEN v.view_count ELSE 0 END), 0) AS total_30d,
            COALESCE(SUM(CASE WHEN v.published_at >= ?  THEN v.view_count ELSE 0 END), 0) AS month_views,
            COALESCE(SUM(CASE WHEN v.published_at >= ?  THEN v.view_count ELSE 0 END), 0) AS quarter_views,
            ROUND(AVG(CASE WHEN v.published_at >= ?
                          THEN CAST(v.like_count   AS FLOAT)/NULLIF(v.view_count,0) END)*100, 2) AS like_rate,
            ROUND(AVG(CASE WHEN v.published_at >= ?
                          THEN CAST(v.comment_count AS FLOAT)/NULLIF(v.view_count,0) END)*100, 2) AS comment_rate
        FROM videos v
        JOIN channels ch ON v.channel_id = ch.channel_id
        WHERE v.published_at >= ? AND v.published_at <= ?
          AND {excl}
        GROUP BY ch.channel_id
        HAVING videos >= 1
        ORDER BY avg_views DESC
    ''', (start_30d, start_30d, start_30d, start_month, start_quarter,
          start_30d, start_30d, start_quarter, end_str))

    rows = c.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            'channel':      r[0],
            'videos':       int(r[1]),
            'avg_views':    int(r[2]) if r[2] else 0,
            'total_30d':    int(r[3]),
            'month_views':  int(r[4]),
            'quarter_views':int(r[5]),
            'like_rate':    float(r[6] or 0),
            'comment_rate': float(r[7] or 0),
        })
    return result


def read_doc(date_str, doc_num):
    folder = REPORTS_DIR / date_str
    if not folder.exists():
        return ''
    files = list(folder.glob(f'doc{doc_num}_*.md'))
    if not files:
        return ''
    return files[0].read_text(encoding='utf-8')


def md_to_html(text):
    """Мінімальний markdown → HTML конвертер для відображення в дашборді."""
    lines = text.split('\n')
    out = []
    in_table = False
    in_list = False

    for line in lines:
        # Заголовки
        if line.startswith('### '):
            if in_table: out.append('</table>'); in_table = False
            if in_list:  out.append('</ul>');    in_list = False
            out.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('## '):
            if in_table: out.append('</table>'); in_table = False
            if in_list:  out.append('</ul>');    in_list = False
            out.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '):
            if in_table: out.append('</table>'); in_table = False
            if in_list:  out.append('</ul>');    in_list = False
            out.append(f'<h1>{line[2:]}</h1>')
        # Таблиця
        elif line.startswith('|'):
            if not in_table:
                out.append('<table class="md-table"><thead>')
                in_table = True
                cells = [c.strip() for c in line.strip('|').split('|')]
                out.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
                out.append('</thead><tbody>')
            elif re.match(r'^\|[-| :]+\|$', line):
                pass  # separator row
            else:
                cells = [c.strip() for c in line.strip('|').split('|')]
                # inline formatting
                row = '<tr>' + ''.join(f'<td>{inline_md(c)}</td>' for c in cells) + '</tr>'
                out.append(row)
        else:
            if in_table:
                out.append('</tbody></table>')
                in_table = False
            # Список
            if line.startswith('- ') or line.startswith('* '):
                if not in_list:
                    out.append('<ul>')
                    in_list = True
                out.append(f'<li>{inline_md(line[2:])}</li>')
            elif line.startswith(tuple(f'{i}. ' for i in range(1, 20))):
                if not in_list:
                    out.append('<ol>')
                    in_list = True
                text_part = re.sub(r'^\d+\. ', '', line)
                out.append(f'<li>{inline_md(text_part)}</li>')
            else:
                if in_list:
                    out.append('</ul>' if '<ul>' in '\n'.join(out[-20:]) else '</ol>')
                    in_list = False
                if line.strip():
                    out.append(f'<p>{inline_md(line)}</p>')
                else:
                    out.append('<br>')

    if in_table: out.append('</tbody></table>')
    if in_list:  out.append('</ul>')
    return '\n'.join(out)


def inline_md(text):
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    return text


def get_available_dates():
    if not REPORTS_DIR.exists():
        return []
    dates = []
    for d in sorted(REPORTS_DIR.iterdir()):
        if d.is_dir() and re.match(r'^\d{4}-\d{2}-\d{2}$', d.name):
            if any(d.glob('doc1_*.md')):
                dates.append(d.name)
    return sorted(dates)


def fmt(n):
    if n >= 1_000_000:
        return f'{n/1_000_000:.1f}M'
    if n >= 1_000:
        return f'{n/1_000:.1f}k'
    return str(n)


def build_payload(dates):
    payload = {}
    for date_str in dates:
        channels = get_channel_metrics(date_str)
        payload[date_str] = {
            'channels': channels,
            'doc1': md_to_html(read_doc(date_str, 1)),
            'doc2': md_to_html(read_doc(date_str, 2)),
            'doc3': md_to_html(read_doc(date_str, 3)),
            'doc4': md_to_html(read_doc(date_str, 4)),
        }
    return payload


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UATV Analytics Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface2: #232736;
  --border: #2e3347;
  --accent: #4f8ef7;
  --accent2: #f7934f;
  --green: #3ecf8e;
  --red: #f76f6f;
  --text: #e8eaf0;
  --muted: #8b91a8;
  --uatv: #f7934f;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; min-height: 100vh; }

/* LAYOUT */
.app { display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: 220px; min-width: 220px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow-y: auto; }
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* SIDEBAR */
.sidebar-header { padding: 18px 16px 12px; border-bottom: 1px solid var(--border); }
.sidebar-header h2 { font-size: 13px; font-weight: 700; color: var(--accent); letter-spacing: .5px; text-transform: uppercase; }
.sidebar-header p { font-size: 11px; color: var(--muted); margin-top: 2px; }
.date-list { padding: 8px 0; flex: 1; }
.date-btn { display: block; width: 100%; text-align: left; padding: 9px 16px; background: none; border: none; color: var(--muted); cursor: pointer; font-size: 13px; border-left: 3px solid transparent; transition: all .15s; }
.date-btn:hover { background: var(--surface2); color: var(--text); }
.date-btn.active { background: var(--surface2); color: var(--accent); border-left-color: var(--accent); font-weight: 600; }

/* HEADER */
.topbar { padding: 14px 24px; border-bottom: 1px solid var(--border); background: var(--surface); display: flex; align-items: center; gap: 20px; flex-shrink: 0; }
.topbar h1 { font-size: 16px; font-weight: 700; }
.topbar .date-label { font-size: 13px; color: var(--muted); }
.tabs { display: flex; gap: 2px; margin-left: auto; }
.tab-btn { padding: 6px 14px; border-radius: 6px; border: none; background: none; color: var(--muted); cursor: pointer; font-size: 13px; font-weight: 500; transition: all .15s; }
.tab-btn:hover { background: var(--surface2); color: var(--text); }
.tab-btn.active { background: var(--accent); color: #fff; }

/* CONTENT */
.content { flex: 1; overflow-y: auto; padding: 20px 24px; }
.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* METRIC SWITCHER */
.metric-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.metric-bar label { font-size: 12px; color: var(--muted); margin-right: 4px; }
.metric-chip { padding: 5px 12px; border-radius: 20px; border: 1px solid var(--border); background: var(--surface2); color: var(--muted); cursor: pointer; font-size: 12px; font-weight: 500; transition: all .15s; }
.metric-chip:hover { border-color: var(--accent); color: var(--accent); }
.metric-chip.active { background: var(--accent); border-color: var(--accent); color: #fff; }

/* CHART */
.chart-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 20px; height: 340px; position: relative; }
.chart-wrap canvas { position: absolute; inset: 16px; }

/* TABLE */
.tbl-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
table.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
table.data-table thead th {
  padding: 10px 12px; text-align: right; white-space: nowrap;
  background: var(--surface2); color: var(--muted); font-weight: 600;
  cursor: pointer; user-select: none; border-bottom: 1px solid var(--border);
  position: relative; font-size: 12px; letter-spacing: .3px;
}
table.data-table thead th:first-child { text-align: left; }
table.data-table thead th.sorted { color: var(--accent); }
table.data-table thead th::after { content: ''; margin-left: 4px; }
table.data-table thead th.asc::after  { content: ' ↑'; }
table.data-table thead th.desc::after { content: ' ↓'; }
table.data-table tbody tr { border-bottom: 1px solid var(--border); transition: background .1s; }
table.data-table tbody tr:hover { background: var(--surface2); }
table.data-table tbody tr.uatv-row { background: rgba(247,147,79,.08); }
table.data-table tbody tr.uatv-row:hover { background: rgba(247,147,79,.14); }
table.data-table tbody td { padding: 9px 12px; text-align: right; color: var(--text); }
table.data-table tbody td:first-child { text-align: left; font-weight: 500; }
.uatv-badge { background: var(--uatv); color: #000; border-radius: 4px; padding: 1px 5px; font-size: 11px; font-weight: 700; margin-left: 6px; }
.num-pos { color: var(--green); }
.num-neg { color: var(--red); }
.num-neu { color: var(--muted); }

/* MD content */
.md-content { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px 24px; line-height: 1.7; }
.md-content h1 { font-size: 18px; font-weight: 700; margin-bottom: 16px; color: var(--text); }
.md-content h2 { font-size: 15px; font-weight: 600; margin: 20px 0 10px; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 6px; }
.md-content h3 { font-size: 14px; font-weight: 600; margin: 16px 0 8px; color: var(--accent2); }
.md-content p { margin-bottom: 10px; color: var(--text); }
.md-content ul, .md-content ol { margin: 8px 0 12px 20px; }
.md-content li { margin-bottom: 4px; }
.md-content code { background: var(--surface2); padding: 1px 5px; border-radius: 3px; font-family: monospace; font-size: 12px; color: var(--green); }
.md-content a { color: var(--accent); text-decoration: none; }
.md-content a:hover { text-decoration: underline; }
.md-content strong { color: var(--text); font-weight: 700; }
.md-content br { display: block; margin-bottom: 4px; }
table.md-table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
table.md-table th { background: var(--surface2); color: var(--muted); padding: 8px 10px; text-align: left; border: 1px solid var(--border); font-size: 12px; }
table.md-table td { padding: 7px 10px; border: 1px solid var(--border); }
table.md-table tr:hover td { background: var(--surface2); }

/* Empty state */
.empty { text-align: center; padding: 60px 20px; color: var(--muted); }
.empty svg { margin-bottom: 12px; opacity: .4; }
</style>
</head>
<body>
<div class="app">

  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <h2>UATV Analytics</h2>
      <p>Оберіть дату звіту</p>
    </div>
    <div class="date-list" id="dateList"></div>
  </aside>

  <!-- MAIN -->
  <div class="main">
    <div class="topbar">
      <div>
        <h1>Конкурентний аналіз</h1>
        <span class="date-label" id="topDate">—</span>
      </div>
      <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('table')">📊 Таблиця</button>
        <button class="tab-btn" onclick="switchTab('doc1')">📈 Аналітика</button>
        <button class="tab-btn" onclick="switchTab('doc2')">📁 Drive</button>
        <button class="tab-btn" onclick="switchTab('doc3')">📰 Новини</button>
        <button class="tab-btn" onclick="switchTab('doc4')">🎯 Рекомендації</button>
      </div>
    </div>

    <div class="content">

      <!-- TAB: TABLE / CHART -->
      <div class="tab-panel active" id="tab-table">
        <div class="metric-bar">
          <label>Сортувати графік за:</label>
          <button class="metric-chip active" onclick="setChartMetric('avg_views', this)">Avg Views</button>
          <button class="metric-chip" onclick="setChartMetric('total_30d', this)">Total 30d</button>
          <button class="metric-chip" onclick="setChartMetric('month_views', this)">Місяць</button>
          <button class="metric-chip" onclick="setChartMetric('quarter_views', this)">Квартал</button>
          <button class="metric-chip" onclick="setChartMetric('videos', this)">Відео</button>
          <button class="metric-chip" onclick="setChartMetric('like_rate', this)">Like Rate</button>
        </div>
        <div class="chart-wrap">
          <canvas id="channelChart"></canvas>
        </div>
        <div class="tbl-wrap">
          <table class="data-table" id="dataTable">
            <thead>
              <tr>
                <th onclick="sortTable('channel')">Канал</th>
                <th onclick="sortTable('videos')">Відео 30d</th>
                <th onclick="sortTable('avg_views')">Avg Views</th>
                <th onclick="sortTable('total_30d')">Total 30d</th>
                <th onclick="sortTable('month_views')" title="З 1-го числа поточного місяця">Пот. місяць</th>
                <th onclick="sortTable('quarter_views')">Квартал</th>
                <th onclick="sortTable('like_rate')">Like%</th>
                <th onclick="sortTable('comment_rate')">Cmnt%</th>
              </tr>
            </thead>
            <tbody id="tableBody"></tbody>
          </table>
        </div>
      </div>

      <!-- TAB: DOC1 -->
      <div class="tab-panel" id="tab-doc1">
        <div class="md-content" id="doc1Content"><div class="empty">Немає даних</div></div>
      </div>

      <!-- TAB: DOC2 -->
      <div class="tab-panel" id="tab-doc2">
        <div class="md-content" id="doc2Content"><div class="empty">Немає даних</div></div>
      </div>

      <!-- TAB: DOC3 -->
      <div class="tab-panel" id="tab-doc3">
        <div class="md-content" id="doc3Content"><div class="empty">Немає даних</div></div>
      </div>

      <!-- TAB: DOC4 -->
      <div class="tab-panel" id="tab-doc4">
        <div class="md-content" id="doc4Content"><div class="empty">Немає даних</div></div>
      </div>

    </div>
  </div>
</div>

<script>
// ── DATA (embedded by generate_dashboard.py) ──
const PAYLOAD = __PAYLOAD_JSON__;
const DATES   = __DATES_JSON__;

// ── STATE ──
let currentDate    = DATES[DATES.length - 1] || null;
let sortCol        = 'avg_views';
let sortDir        = 'desc';
let chartMetric    = 'avg_views';
let chartInstance  = null;

const METRIC_LABELS = {
  avg_views:     'Avg Views (30d)',
  total_30d:     'Total Views (30d)',
  month_views:   'Views (з 1-го числа місяця)',
  quarter_views: 'Views (квартал)',
  videos:        'Кількість відео',
  like_rate:     'Like Rate %',
  comment_rate:  'Comment Rate %',
};

// ── INIT ──
window.addEventListener('DOMContentLoaded', () => {
  buildSidebar();
  if (currentDate) loadDate(currentDate);
});

function buildSidebar() {
  const list = document.getElementById('dateList');
  list.innerHTML = '';
  [...DATES].reverse().forEach(d => {
    const btn = document.createElement('button');
    btn.className = 'date-btn' + (d === currentDate ? ' active' : '');
    btn.textContent = formatDate(d);
    btn.onclick = () => loadDate(d);
    btn.dataset.date = d;
    list.appendChild(btn);
  });
}

function formatDate(d) {
  const [y, m, day] = d.split('-');
  const months = ['Січ','Лют','Бер','Кві','Тра','Чер','Лип','Сер','Вер','Жов','Лис','Гру'];
  return `${parseInt(day)} ${months[parseInt(m)-1]} ${y}`;
}

function loadDate(date) {
  currentDate = date;
  document.getElementById('topDate').textContent = formatDate(date);

  // Sidebar highlight
  document.querySelectorAll('.date-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.date === date);
  });

  const data = PAYLOAD[date];
  if (!data) return;

  renderTable(data.channels);
  renderChart(data.channels);
  document.getElementById('doc1Content').innerHTML = data.doc1 || '<div class="empty">Файл не знайдено</div>';
  document.getElementById('doc2Content').innerHTML = data.doc2 || '<div class="empty">Файл не знайдено</div>';
  document.getElementById('doc3Content').innerHTML = data.doc3 || '<div class="empty">Файл не знайдено</div>';
  document.getElementById('doc4Content').innerHTML = data.doc4 || '<div class="empty">Файл не знайдено</div>';
}

// ── TABLE ──
function renderTable(channels) {
  const sorted = sortChannels(channels, sortCol, sortDir);
  const tbody = document.getElementById('tableBody');
  tbody.innerHTML = '';

  sorted.forEach(ch => {
    const isUatv = ch.channel.includes('UATV');
    const tr = document.createElement('tr');
    if (isUatv) tr.className = 'uatv-row';
    tr.innerHTML = `
      <td>${ch.channel}${isUatv ? '<span class="uatv-badge">UATV</span>' : ''}</td>
      <td>${ch.videos}</td>
      <td class="${viewClass(ch.avg_views)}">${fmtNum(ch.avg_views)}</td>
      <td>${fmtNum(ch.total_30d)}</td>
      <td>${fmtNum(ch.month_views)}</td>
      <td>${fmtNum(ch.quarter_views)}</td>
      <td>${ch.like_rate.toFixed(2)}%</td>
      <td>${ch.comment_rate.toFixed(2)}%</td>
    `;
    tbody.appendChild(tr);
  });

  // Update header sort indicators
  document.querySelectorAll('#dataTable thead th').forEach(th => {
    th.classList.remove('sorted', 'asc', 'desc');
  });
  const cols = ['channel','videos','avg_views','total_30d','month_views','quarter_views','like_rate','comment_rate'];
  const idx = cols.indexOf(sortCol);
  if (idx >= 0) {
    const ths = document.querySelectorAll('#dataTable thead th');
    ths[idx].classList.add('sorted', sortDir);
  }
}

function sortTable(col) {
  if (sortCol === col) {
    sortDir = sortDir === 'desc' ? 'asc' : 'desc';
  } else {
    sortCol = col;
    sortDir = col === 'channel' ? 'asc' : 'desc';
  }
  const data = PAYLOAD[currentDate];
  if (data) renderTable(data.channels);
}

function sortChannels(channels, col, dir) {
  return [...channels].sort((a, b) => {
    const va = a[col], vb = b[col];
    if (typeof va === 'string') return dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    return dir === 'asc' ? va - vb : vb - va;
  });
}

// ── CHART ──
function renderChart(channels) {
  const sorted = [...channels].sort((a, b) => b[chartMetric] - a[chartMetric]).slice(0, 20);
  const labels = sorted.map(c => c.channel.length > 22 ? c.channel.slice(0, 22) + '…' : c.channel);
  const values = sorted.map(c => c[chartMetric]);
  const colors = sorted.map(c => c.channel.includes('UATV') ? '#f7934f' : '#4f8ef7');

  if (chartInstance) chartInstance.destroy();
  const ctx = document.getElementById('channelChart').getContext('2d');
  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: METRIC_LABELS[chartMetric],
        data: values,
        backgroundColor: colors,
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${METRIC_LABELS[chartMetric]}: ${fmtNum(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#8b91a8', font: { size: 11 }, maxRotation: 35 },
          grid:  { color: '#2e3347' }
        },
        y: {
          ticks: {
            color: '#8b91a8',
            callback: v => fmtNum(v)
          },
          grid: { color: '#2e3347' }
        }
      }
    }
  });
}

function setChartMetric(metric, btn) {
  chartMetric = metric;
  document.querySelectorAll('.metric-chip').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const data = PAYLOAD[currentDate];
  if (data) renderChart(data.channels);
}

// ── TABS ──
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}

// ── HELPERS ──
function fmtNum(n) {
  if (!n && n !== 0) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k';
  return n.toString();
}

function viewClass(n) {
  if (n >= 50000) return 'num-pos';
  if (n >= 10000) return '';
  if (n < 5000)   return 'num-neg';
  return 'num-neu';
}
</script>
</body>
</html>
"""


def generate():
    dates = get_available_dates()
    if not dates:
        print("⚠️  Не знайдено жодної дати з doc1_*.md у data/reports/")
        print("    Перевірте що папки мають формат YYYY-MM-DD і містять doc1_*.md")
        return

    print(f"Знайдено дат: {len(dates)} → {', '.join(dates)}")
    print("Збираю дані...")

    payload = build_payload(dates)

    payload_json = json.dumps(payload, ensure_ascii=False, indent=None)
    dates_json   = json.dumps(dates,   ensure_ascii=False)

    html = HTML_TEMPLATE \
        .replace('__PAYLOAD_JSON__', payload_json) \
        .replace('__DATES_JSON__',   dates_json)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding='utf-8')
    size_kb = OUTPUT_PATH.stat().st_size // 1024
    print(f"✅ Дашборд збережено: {OUTPUT_PATH}")
    print(f"   Розмір: {size_kb} KB | Дати: {', '.join(dates)}")


if __name__ == '__main__':
    generate()
