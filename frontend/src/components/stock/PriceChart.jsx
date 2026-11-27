import { AreaSeries, CandlestickSeries, createChart, HistogramSeries, LineSeries, LineStyle } from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import { useTheme } from '../../context/ThemeContext'
import { cssVar } from '../../lib/stocks'

// Graphique de la fiche action (UI §4.5, charte §7.7) avec TradingView Lightweight Charts :
// - bougies vertes / rouges (buy / sell), moyennes mobiles 20 / 50 / 200 jours en traits de 1,5 px,
//   bandes de Bollinger en zone brand-soft bordée de brand ;
// - deux panneaux de 96 px dessous : RSI 14 jours (repères 30 et 70 en pointillés) et MACD 12 / 26 / 9.
// Les trois graphiques défilent ensemble. Les couleurs sont lues dans les variables CSS de la charte.

function baseOptions(height) {
  return {
    height,
    autoSize: true,
    layout: { background: { color: cssVar('surface-card') }, textColor: cssVar('ink-muted'), fontFamily: 'Inter, system-ui, sans-serif', fontSize: 12, attributionLogo: false },
    grid: { vertLines: { color: cssVar('line') }, horzLines: { color: cssVar('line') } },
    rightPriceScale: { borderColor: cssVar('line') },
    timeScale: { borderColor: cssVar('line'), timeVisible: false },
    crosshair: { mode: 0 },
    localization: {
      locale: 'fr-FR',
      priceFormatter: (price) => price.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    },
    handleScroll: true,
    handleScale: true,
  }
}

// Bougies d'un jour : r.date ('2026-11-25') ; bougies intrajournalières : r.time (secondes).
const timeOf = (r) => r.time ?? r.date
const points = (rows, key) => rows.map((r) => (r[key] === null ? { time: timeOf(r) } : { time: timeOf(r), value: r[key] }))

export default function PriceChart({ series, show, rsiLabel, macdLabel, intraday = false, levels = null }) {
  const mainRef = useRef(null)
  const rsiRef = useRef(null)
  const macdRef = useRef(null)
  const { resolved: theme } = useTheme() // graphiques redessinés quand le thème change

  useEffect(() => {
    if (!series.length) return undefined
    const main = createChart(mainRef.current, baseOptions(300))
    main.applyOptions({ timeScale: { timeVisible: intraday, secondsVisible: false } })
    const rsi = createChart(rsiRef.current, {
      ...baseOptions(96),
      timeScale: { visible: false },
      localization: { locale: 'fr-FR', priceFormatter: (v) => Math.round(v).toString() },
    })
    const macd = createChart(macdRef.current, { ...baseOptions(96), timeScale: { visible: false } })

    const brand = cssVar('brand')
    const brandSoft = cssVar('brand-soft')
    const card = cssVar('surface-card')

    if (show.bollinger) {
      // Zone : on remplit sous la bande haute, puis on « efface » sous la bande basse.
      main.addSeries(AreaSeries, { lineColor: brand, lineWidth: 1, topColor: brandSoft, bottomColor: brandSoft, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
        .setData(points(series, 'boll_haut'))
      main.addSeries(AreaSeries, { lineColor: brand, lineWidth: 1, topColor: card, bottomColor: card, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
        .setData(points(series, 'boll_bas'))
    }
    const candles = main.addSeries(CandlestickSeries, {
      upColor: cssVar('buy'), downColor: cssVar('sell'), borderVisible: false,
      wickUpColor: cssVar('buy'), wickDownColor: cssVar('sell'),
    })
    candles.setData(series.map((r) => ({ time: timeOf(r), open: r.open, high: r.high, low: r.low, close: r.close })))
    if (show.sr && levels) {
      // Supports et résistances (D-24) : lignes pointillées horizontales avec leur nom sur l'axe.
      const muted = cssVar('ink-muted')
      levels.supports.forEach((lv) => candles.createPriceLine({ price: lv.niveau, color: muted, lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true, title: 'Support' }))
      levels.resistances.forEach((lv) => candles.createPriceLine({ price: lv.niveau, color: muted, lineStyle: LineStyle.Dotted, lineWidth: 1, axisLabelVisible: true, title: 'Résistance' }))
    }
    const lines = [['mm20', 'chart-ma20'], ['mm50', 'chart-ma50'], ['mm200', 'chart-ma200']]
    lines.filter(([key]) => show[key]).forEach(([key, color]) => {
      main.addSeries(LineSeries, { color: cssVar(color), lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
        .setData(points(series, key))
    })

    const rsiLine = rsi.addSeries(LineSeries, {
      color: brand, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false,
      priceFormat: { type: 'custom', formatter: (v) => Math.round(v).toString(), minMove: 1 },
      autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }),
    })
    rsiLine.setData(points(series, 'rsi'))
    ;[30, 70].forEach((price) => rsiLine.createPriceLine({ price, color: cssVar('line-strong'), lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false }))

    macd.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }).setData(
      series.map((r) => (r.macd_hist === null ? { time: timeOf(r) } : { time: timeOf(r), value: r.macd_hist, color: r.macd_hist >= 0 ? cssVar('buy-soft') : cssVar('sell-soft') })),
    )
    macd.addSeries(LineSeries, { color: brand, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false }).setData(points(series, 'macd'))
    macd.addSeries(LineSeries, { color: cssVar('chart-ma20'), lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false }).setData(points(series, 'macd_signal'))

    const charts = [main, rsi, macd]
    charts.forEach((chart) => chart.timeScale().fitContent())
    const sync = (source) => (range) => {
      if (!range) return
      charts.filter((c) => c !== source).forEach((c) => c.timeScale().setVisibleLogicalRange(range))
    }
    const handlers = charts.map((chart) => {
      const handler = sync(chart)
      chart.timeScale().subscribeVisibleLogicalRangeChange(handler)
      return [chart, handler]
    })
    return () => {
      handlers.forEach(([chart, handler]) => chart.timeScale().unsubscribeVisibleLogicalRangeChange(handler))
      charts.forEach((chart) => chart.remove())
    }
  }, [series, show, intraday, theme, levels])

  return (
    <div className="flex flex-col gap-0">
      <div ref={mainRef} className="h-[300px] w-full" aria-label="Graphique des cours" role="img" />
      <PanelTitle title={intraday ? 'RSI 14 bougies' : 'RSI 14 jours'} detail={intraday ? null : rsiLabel} />
      <div ref={rsiRef} className="h-24 w-full" aria-label="RSI 14 jours" role="img" />
      <PanelTitle title="MACD 12 / 26 / 9" detail={intraday ? null : macdLabel} />
      <div ref={macdRef} className="h-24 w-full" aria-label="MACD 12 / 26 / 9" role="img" />
    </div>
  )
}

function PanelTitle({ title, detail }) {
  return (
    <div className="mt-3 flex items-baseline justify-between border-t border-line pt-3">
      <span className="label-caps">{title}</span>
      {detail && <span className="text-[13px] text-muted">{detail}</span>}
    </div>
  )
}
