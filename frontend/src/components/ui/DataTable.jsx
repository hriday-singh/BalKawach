import React from 'react';

/**
 * DataTable component
 * @param {Object} props
 * @param {Array<{key: string, label: string}>} props.columns - Column definitions
 * @param {Array<Object>} props.data - Data rows
 * @param {string} [props.searchPlaceholder] - Search input placeholder
 * @param {Array<{value: string, label: string}>} [props.filters] - Filter options
 * @param {Function} [props.onRowClick] - Callback when a row is clicked
 */
export function DataTable({ 
  columns = [], 
  data = [], 
  searchPlaceholder = 'Search...', 
  filters = [],
  onRowClick
}) {
  return (
    <div>
      <div className="table-controls">
        <input 
          type="text" 
          className="search-input" 
          placeholder={searchPlaceholder} 
        />
        {filters.length > 0 && (
          <select className="filter-select">
            {filters.map((f, i) => (
              <option key={i} value={f.value}>{f.label}</option>
            ))}
          </select>
        )}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((col, index) => (
                <th key={index}>{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ textAlign: 'center' }}>
                  No data available
                </td>
              </tr>
            ) : (
              data.map((row, rowIndex) => (
                <tr 
                  key={rowIndex} 
                  className={onRowClick ? 'clickable' : ''}
                  onClick={() => onRowClick && onRowClick(row)}
                >
                  {columns.map((col, colIndex) => (
                    <td key={colIndex}>
                      {row[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
