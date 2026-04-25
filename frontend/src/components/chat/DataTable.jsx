import React from 'react';

// 構造化されたテーブルデータを表示
const YEAR_COLUMNS = ['season', 'year', 'game_year', 'birth_year'];

const formatCell = (value, columnKey, decimalColumns) => {
  if (typeof value !== 'number') return value ?? '—';
  if (YEAR_COLUMNS.includes(columnKey)) return String(value); // 年はカンマなし
  if (decimalColumns.includes(columnKey)) {
    return value.toFixed(3);
  }
  return value.toLocaleString('ja-JP');
};

const DataTable = ({ tableData, columns, isTransposed, decimalColumns = [], grouping = null }) => {
  if (!tableData || !columns) return null;

  // 単一行結果の場合は縦表示（転置）
  if (isTransposed && tableData.length === 1) {
    const row = tableData[0];

    // Handle grouped display for career batting
    if (grouping && grouping.type === "career_batting_chunks") {
      return (
        <div className="mt-3 space-y-6">
          {grouping.groups.map((group, groupIndex) => {
            const groupColumns = columns.filter(col => group.columns.includes(col.key));
            if (groupColumns.length === 0) return null;

            return (
              <div key={groupIndex} className="overflow-x-auto">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-200">{group.name}</h4>
                <div className="inline-block min-w-full align-middle">
                  <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg transition-colors duration-200">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-800 transition-colors duration-200">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">
                            項目
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">
                            値
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600 transition-colors duration-200">
                        {groupColumns.map((column, index) => (
                          <tr key={column.key} className={index % 2 === 0 ? 'bg-white dark:bg-gray-700' : 'bg-gray-50 dark:bg-gray-600'}>
                            <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200">
                              {column.label}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200">
                              {formatCell(row[column.key], column.key, decimalColumns)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    // Default single table display（縦表示）
    return (
      <div className="mt-3 overflow-x-auto">
        <div className="inline-block min-w-full align-middle">
          <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg transition-colors duration-200">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800 transition-colors duration-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">
                    項目
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200">
                    値
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600 transition-colors duration-200">
                {columns.map((column, index) => (
                  <tr key={column.key} className={index % 2 === 0 ? 'bg-white dark:bg-gray-700' : 'bg-gray-50 dark:bg-gray-600'}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200">
                      {column.label}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200">
                      {formatCell(row[column.key], column.key, decimalColumns)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // 複数行結果の場合は通常の横表示
  return (
    <div className="mt-3 overflow-x-auto">
      <div className="inline-block min-w-full align-middle">
        <div className="overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg transition-colors duration-200">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800 transition-colors duration-200">
              <tr>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider transition-colors duration-200"
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600 transition-colors duration-200">
              {tableData.map((row, index) => (
                <tr key={index} className={index % 2 === 0 ? 'bg-white dark:bg-gray-700' : 'bg-gray-50 dark:bg-gray-600'}>
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className="px-4 py-3 text-sm text-gray-900 dark:text-white whitespace-nowrap transition-colors duration-200"
                    >
                      {formatCell(row[column.key], column.key, decimalColumns)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DataTable;
