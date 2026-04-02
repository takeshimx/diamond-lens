import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

// ===== セクション設定 =====
const SECTION_CONFIG = [
  { keywords: ['Executive', 'エグゼクティブ', 'サマリー'],   style: 'blue',   icon: '🎯', collapsible: false },
  { keywords: ['対戦サマリー', 'Matchup'],                    style: 'green',  icon: '⚔️', collapsible: false },
  { keywords: ['脆弱性'],                                      style: 'red',    icon: '⚠️', collapsible: true  },
  { keywords: ['強み'],                                        style: 'orange', icon: '💪', collapsible: true  },
  { keywords: ['推奨', '戦略推奨', 'Recommendation'],         style: 'purple', icon: '🏹', collapsible: false },
  { keywords: ['状況別'],                                      style: 'teal',   icon: '📋', collapsible: true  },
];

const COLOR_MAP = {
  blue:   { header: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700',   text: 'text-blue-700 dark:text-blue-300'   },
  green:  { header: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700', text: 'text-green-700 dark:text-green-300' },
  red:    { header: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700',         text: 'text-red-700 dark:text-red-300'     },
  orange: { header: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-700', text: 'text-orange-700 dark:text-orange-300' },
  purple: { header: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-700', text: 'text-purple-700 dark:text-purple-300' },
  teal:   { header: 'bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-700',     text: 'text-teal-700 dark:text-teal-300'   },
  default:{ header: 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700',     text: 'text-gray-700 dark:text-gray-300'   },
};

function getSectionMeta(title) {
  const config = SECTION_CONFIG.find(c => c.keywords.some(kw => title.includes(kw)));
  if (!config) return { style: 'default', icon: '📊', collapsible: false };
  return config;
}

// ===== Markdown パーサー =====
function parseSections(text) {
  if (!text) return [];
  const lines = text.split('\n');
  const sections = [];
  let current = null;

  for (const line of lines) {
    if (line.match(/^#{1,3}\s/)) {
      if (current) sections.push(current);
      current = { title: line.replace(/^#+\s*/, '').trim(), lines: [] };
    } else if (current) {
      current.lines.push(line);
    }
  }
  if (current) sections.push(current);
  return sections;
}

// ===== インライン太字を除去（シンプルレンダリング） =====
function stripBold(text) {
  return text.replace(/\*\*(.*?)\*\*/g, '$1');
}

// ===== セクションコンテンツ =====
function SectionContent({ lines }) {
  const items = [];
  let paragraph = [];

  const flushParagraph = () => {
    if (paragraph.length > 0) {
      items.push({ type: 'paragraph', lines: [...paragraph] });
      paragraph = [];
    }
  };

  for (const line of lines) {
    if (!line.trim()) {
      flushParagraph();
      continue;
    }
    if (line.match(/^[-*]\s/)) {
      flushParagraph();
      items.push({ type: 'bullet', text: stripBold(line.replace(/^[-*]\s/, '')) });
    } else if (line.match(/^-\s\*\*/)) {
      flushParagraph();
      const [label, ...rest] = line.replace(/^-\s/, '').split(':');
      items.push({ type: 'kv', label: stripBold(label), value: stripBold(rest.join(':').trim()) });
    } else {
      paragraph.push(line);
    }
  }
  flushParagraph();

  return (
    <div className="space-y-1.5 px-4 py-3">
      {items.map((item, i) => {
        if (item.type === 'bullet') {
          return (
            <div key={i} className="flex items-start gap-2">
              <span className="mt-2 w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500 flex-shrink-0" />
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{item.text}</p>
            </div>
          );
        }
        if (item.type === 'kv') {
          return (
            <div key={i} className="flex items-start gap-2">
              <span className="mt-2 w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500 flex-shrink-0" />
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                <span className="font-semibold text-gray-800 dark:text-gray-200">{item.label}:</span>
                {item.value && <span> {item.value}</span>}
              </p>
            </div>
          );
        }
        return (
          <p key={i} className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {item.lines.map(stripBold).join(' ')}
          </p>
        );
      })}
    </div>
  );
}

// ===== 個別セクション =====
function Section({ title, lines }) {
  const { style, icon, collapsible } = getSectionMeta(title);
  const colors = COLOR_MAP[style];
  const [open, setOpen] = useState(true);

  return (
    <div className={`rounded-xl border overflow-hidden ${colors.header.split(' ').filter(c => c.startsWith('border')).join(' ')}`}>
      {/* セクションヘッダー */}
      <button
        className={`w-full flex items-center justify-between px-4 py-2.5 ${colors.header.split(' ').filter(c => !c.startsWith('border')).join(' ')} ${collapsible ? 'cursor-pointer' : 'cursor-default'}`}
        onClick={() => collapsible && setOpen(o => !o)}
        disabled={!collapsible}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">{icon}</span>
          <span className={`text-sm font-bold ${colors.text}`}>{title}</span>
        </div>
        {collapsible && (
          open
            ? <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
            : <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
        )}
      </button>

      {/* セクション本文 */}
      {open && (
        <div className="bg-white dark:bg-gray-800/30">
          <SectionContent lines={lines} />
        </div>
      )}
    </div>
  );
}

// ===== メインコンポーネント =====
const StrategyReportCard = ({ finalAnswer }) => {
  const sections = parseSections(finalAnswer);
  if (sections.length === 0) return null;

  return (
    <div className="mt-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden transition-all duration-300 hover:shadow-md w-full max-w-2xl">

      {/* カードヘッダー */}
      <div className="flex items-center gap-3 px-5 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-700 dark:to-purple-700">
        <span className="text-2xl">🧠</span>
        <div>
          <h3 className="text-white font-bold text-lg leading-tight">STRATEGY REPORT</h3>
          <p className="text-indigo-200 text-xs font-semibold tracking-wider">MLB ADVANCED ANALYSIS</p>
        </div>
        <span className="ml-auto px-2 py-0.5 text-xs bg-white/20 text-white rounded-full font-bold tracking-wide">
          2025
        </span>
      </div>

      {/* セクション一覧 */}
      <div className="p-4 space-y-3">
        {sections.map((s, i) => (
          <Section key={i} title={s.title} lines={s.lines} />
        ))}
      </div>
    </div>
  );
};

export default StrategyReportCard;
