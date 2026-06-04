const palette = ['#2563EB', '#06B6D4', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6']

function baseOption(title) {
  return {
    backgroundColor: 'transparent',
    color: palette,
    title: {
      text: title || 'SmartLib 图表',
      left: 10,
      top: 8,
      textStyle: { fontSize: 15, fontWeight: 700, color: '#0f172a' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a' },
      extraCssText: 'box-shadow: 0 8px 24px rgba(15,23,42,0.12); border-radius: 8px;'
    },
    legend: { top: 8, right: 12, textStyle: { color: '#64748b' } },
    grid: { left: 56, right: 28, top: 66, bottom: 60 },
    textStyle: { fontFamily: 'PingFang SC, Microsoft YaHei, Arial' },
    toolbox: {
      feature: {
        saveAsImage: { title: '保存图片' },
        dataView: { title: '数据视图', readOnly: false },
        restore: { title: '还原' }
      },
      right: 20,
      top: 8
    }
  }
}

const styledItemTooltip = {
  backgroundColor: 'rgba(255,255,255,0.96)',
  borderColor: '#e2e8f0',
  borderWidth: 1,
  textStyle: { color: '#0f172a' },
  extraCssText: 'box-shadow: 0 8px 24px rgba(15,23,42,0.12); border-radius: 8px;'
}

export function buildFixedChartOption(chart) {
  if (!chart) return baseOption('空图表')

  if (chart.type === 'heatmap') {
    const rows = chart.data || []
    const xField = chart.x_field || 'x'
    const yField = chart.y_field || 'y'
    const valueField = chart.value_field || 'value'
    const xValues = chart.x || [...new Set(rows.map((row) => String(row[xField])))]
    const yValues = chart.y || [...new Set(rows.map((row) => String(row[yField])))]
    const values = rows.map((row) => [
      xValues.indexOf(String(row[xField])),
      yValues.indexOf(String(row[yField])),
      Number(row[valueField] || 0)
    ])

    return {
      ...baseOption(chart.title),
      tooltip: { position: 'top', ...styledItemTooltip },
      grid: { left: 88, right: 28, top: 66, bottom: 72 },
      xAxis: { type: 'category', data: xValues, splitArea: { show: true } },
      yAxis: { type: 'category', data: yValues, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max: values.length ? Math.max(...values.map((item) => item[2])) : 0,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 8,
        inRange: { color: ['#F0F9FF', '#7DD3FC', '#0284C7'] },
        textStyle: { color: '#64748b' }
      },
      series: [{ type: 'heatmap', data: values, label: { show: false } }]
    }
  }

  if (chart.type === 'pie') {
    const data = (chart.data || []).filter(d => d.name !== undefined && d.name !== null && d.name !== '')
    return {
      ...baseOption(chart.title),
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
        ...styledItemTooltip
      },
      legend: {
        bottom: 4,
        left: 'center',
        textStyle: { color: '#64748b', fontSize: 12 },
        itemWidth: 12,
        itemHeight: 12
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '65%'],
          center: ['50%', '44%'],
          data,
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: data.length <= 8,
            formatter: '{b}\n{d}%',
            color: '#64748b',
            fontSize: 12
          },
          labelLine: { show: data.length <= 8 },
          emphasis: {
            itemStyle: {
              shadowBlur: 12,
              shadowOffsetX: 0,
              shadowColor: 'rgba(15, 23, 42, 0.2)'
            }
          }
        }
      ]
    }
  }

  if (chart.type === 'funnel') {
    return {
      ...baseOption(chart.title),
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
        ...styledItemTooltip
      },
      series: [{
        type: 'funnel',
        left: '10%',
        top: 60,
        bottom: 60,
        width: '80%',
        min: 0,
        max: chart.data && chart.data.length ? Math.max(...chart.data.map(d => d.value)) : 100,
        sort: 'descending',
        gap: 2,
        label: { show: true, position: 'inside' },
        labelLine: { length: 10, lineStyle: { width: 1, type: 'solid' } },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        emphasis: { label: { fontSize: 20 } },
        data: chart.data || []
      }]
    }
  }

  if (chart.type === 'radar') {
    return {
      ...baseOption(chart.title),
      tooltip: { ...styledItemTooltip },
      radar: {
        indicator: chart.indicator || [],
        radius: '65%',
        axisName: { color: '#64748b' }
      },
      series: [{
        type: 'radar',
        data: chart.data || []
      }]
    }
  }

  if (chart.type === 'group_bar') {
    return {
      ...baseOption(chart.title),
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#0f172a' },
        extraCssText: 'box-shadow: 0 8px 24px rgba(15,23,42,0.12); border-radius: 8px;'
      },
      legend: {
        data: [chart.y1_name || '指标A', chart.y2_name || '指标B'],
        top: 8,
        right: 12,
        textStyle: { color: '#64748b' }
      },
      xAxis: {
        type: 'category',
        data: chart.x || [],
        axisLabel: {
          color: '#64748b',
          rotate: (chart.x || []).length > 8 ? 30 : 0,
          interval: (() => {
            const len = (chart.x || []).length
            if (len > 30) return Math.ceil(len / 8)
            if (len > 15) return 1
            return 0
          })(),
          formatter: (value) => {
            const s = String(value)
            if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.slice(5)
            return s.length > 10 ? s.slice(0, 8) + '…' : s
          }
        }
      },
      yAxis: [
        { type: 'value', name: chart.y1_name || '' },
        { type: 'value', name: chart.y2_name || '' }
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }
      ],
      series: [
        { name: chart.y1_name || '指标A', type: 'bar', data: chart.y1 || [] },
        { name: chart.y2_name || '指标B', type: 'bar', yAxisIndex: 1, data: chart.y2 || [] }
      ]
    }
  }

  const isLine = chart.type === 'line'
  return {
    ...baseOption(chart.title),
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 10 }
    ],
    xAxis: {
      type: 'category',
      data: chart.x || [],
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: {
        color: '#64748b',
        rotate: (chart.x || []).length > 8 ? 30 : 0,
        interval: (() => {
          const len = (chart.x || []).length
          if (len > 30) return Math.ceil(len / 8)
          if (len > 15) return 1
          return 0
        })(),
        formatter: (value) => {
          const s = String(value)
          if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.slice(5)
          return s.length > 10 ? s.slice(0, 8) + '…' : s
        }
      }
    },
    yAxis: {
      type: 'value',
      name: chart.unit || '',
      nameTextStyle: { color: '#94a3b8' },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#64748b',
        formatter: (value) => {
          if (value >= 10000) return (value / 10000).toFixed(1) + '万'
          if (value >= 1000) return (value / 1000).toFixed(1) + 'k'
          return value
        }
      },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
    },
    series: [
      {
        name: chart.unit || '指标',
        type: isLine ? 'line' : 'bar',
        data: chart.y || [],
        smooth: isLine,
        barWidth: '44%',
        areaStyle: isLine ? { opacity: 0.12 } : undefined,
        lineStyle: isLine ? { width: 3 } : undefined,
        symbolSize: isLine ? 6 : undefined,
        itemStyle: isLine
          ? {}
          : {
              borderRadius: [6, 6, 0, 0],
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: '#2563EB' },
                  { offset: 1, color: '#06B6D4' }
                ]
              }
            }
      }
    ]
  }
}

export function buildResponseChartOption(payload) {
  const rows = payload?.data || []
  if (!rows.length) return null

  const type = payload.type || 'table'
  const chart = payload.chart || {}
  const columns = Object.keys(rows[0])

  if (['bar', 'bar_chart', 'line', 'line_chart'].includes(type)) {
    const xField = chart.x_field || columns[0]
    const yField = chart.y_field || columns[1]
    return buildFixedChartOption({
      type: type.includes('line') ? 'line' : 'bar',
      title: chart.title || '智能查询结果',
      x: rows.map((row) => String(row[xField])),
      y: rows.map((row) => row[yField]),
      unit: yField
    })
  }

  if (['pie', 'pie_chart'].includes(type)) {
    const nameField = chart.name_field || columns[0]
    const valueField = chart.value_field || columns[1]
    return buildFixedChartOption({
      type: 'pie',
      title: chart.title || '智能查询占比',
      data: rows.map((row) => ({ name: String(row[nameField]), value: row[valueField] }))
    })
  }

  if (['funnel', 'funnel_chart'].includes(type)) {
    const nameField = chart.name_field || columns[0]
    const valueField = chart.value_field || columns[1]
    return buildFixedChartOption({
      type: 'funnel',
      title: chart.title || '智能查询漏斗',
      data: rows.map((row) => ({ name: String(row[nameField]), value: row[valueField] }))
    })
  }

  if (['group_bar', 'group_bar_chart'].includes(type)) {
    const xField = chart.x_field || columns[0]
    const y1Field = chart.y1_field || columns[1]
    const y2Field = chart.y2_field || columns[2]
    return buildFixedChartOption({
      type: 'group_bar',
      title: chart.title || '智能查询对比',
      x: rows.map((row) => String(row[xField])),
      y1: rows.map((row) => row[y1Field]),
      y2: rows.map((row) => row[y2Field]),
      y1_name: y1Field,
      y2_name: y2Field
    })
  }

  if (['radar', 'radar_chart'].includes(type)) {
    return buildFixedChartOption({
      type: 'radar',
      title: chart.title || '智能查询雷达',
      indicator: chart.indicator || [],
      data: chart.data || rows
    })
  }

  if (['heatmap', 'heatmap_chart'].includes(type)) {
    const xField = chart.x_field || columns[1]
    const yField = chart.y_field || columns[0]
    const valueField = chart.value_field || columns[2]
    const xValues = [...new Set(rows.map((row) => String(row[xField])))]
    const yValues = [...new Set(rows.map((row) => String(row[yField])))]
    const values = rows.map((row) => [
      xValues.indexOf(String(row[xField])),
      yValues.indexOf(String(row[yField])),
      row[valueField]
    ])

    return {
      ...baseOption(chart.title || '智能查询热力图'),
      tooltip: { position: 'top', ...styledItemTooltip },
      grid: { left: 70, right: 28, top: 64, bottom: 42 },
      xAxis: { type: 'category', data: xValues, splitArea: { show: true } },
      yAxis: { type: 'category', data: yValues, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max: Math.max(...values.map((item) => item[2])),
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: { color: ['#F0F9FF', '#7DD3FC', '#0284C7'] }
      },
      series: [{ type: 'heatmap', data: values, label: { show: true, color: '#0f172a' } }]
    }
  }

  return null
}

export function buildQueryPanelOption(panel) {
  if (!panel || panel.type === 'table' || !panel.data?.length) return null

  if (panel.type === 'heatmap') {
    return buildFixedChartOption({
      type: 'heatmap',
      title: panel.title,
      data: panel.data,
      x_field: panel.x_field,
      y_field: panel.y_field,
      value_field: panel.value_field
    })
  }

  if (panel.type === 'pie') {
    return buildFixedChartOption({
      type: 'pie',
      title: panel.title,
      data: panel.data.map((row) => ({ name: String(row[panel.x_field]), value: row[panel.y_field] }))
    })
  }

  if (panel.type === 'funnel') {
    return buildFixedChartOption({
      type: 'funnel',
      title: panel.title,
      data: panel.data.map((row) => ({ name: String(row[panel.x_field]), value: row[panel.y_field] }))
    })
  }

  if (panel.type === 'radar') {
    return buildFixedChartOption({
      type: 'radar',
      title: panel.title,
      indicator: panel.indicator || [],
      data: panel.data || []
    })
  }

  if (panel.type === 'group_bar') {
    return buildFixedChartOption({
      type: 'group_bar',
      title: panel.title,
      x: panel.data.map((row) => String(row[panel.x_field])),
      y1: panel.data.map((row) => row[panel.y1_field]),
      y2: panel.data.map((row) => row[panel.y2_field]),
      y1_name: panel.y1_name || panel.y1_field || '指标A',
      y2_name: panel.y2_name || panel.y2_field || '指标B'
    })
  }

  return buildFixedChartOption({
    type: panel.type === 'line' ? 'line' : 'bar',
    title: panel.title,
    x: panel.data.map((row) => String(row[panel.x_field])),
    y: panel.data.map((row) => row[panel.y_field]),
    unit: panel.y_field
  })
}
