/* @ds-bundle: {"format":4,"namespace":"Pf500","components":[{"name":"Button"},{"name":"DecisionBadge"},{"name":"KpiCard"},{"name":"AlertBanner"},{"name":"AmountInput"},{"name":"StockCheckbox"},{"name":"ForecastBar"},{"name":"AdviceCard"}]} */
(function () {
  var React = window.React;
  var h = React.createElement;

  function cx() {
    return Array.prototype.filter.call(arguments, Boolean).join(' ');
  }
  function minus(s) { return s.replace(/-/g, '−'); }
  var fmtEur = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var fmtEur0 = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
  var fmtPct = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: 'always' });
  var fmtInt = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 });
  function eur(n, noDecimals) { return minus((noDecimals ? fmtEur0 : fmtEur).format(n)); }
  function eurSigned(n) { return (n > 0 ? '+' : '') + eur(n, true); }
  function pct(n) { return minus(fmtPct.format(n)) + ' %'; }
  function int(n) { return fmtInt.format(n); }

  function TriangleIcon() {
    return h('svg', { className: 'pf-alert-icon', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.75, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': 'true' },
      h('path', { d: 'M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z' }),
      h('path', { d: 'M12 9v4' }),
      h('path', { d: 'M12 17h.01' }));
  }

  function Button(props) {
    var variant = props.variant || 'secondary';
    var rest = Object.assign({}, props);
    delete rest.variant; delete rest.size; delete rest.className; delete rest.children;
    return h('button', Object.assign({ type: 'button' }, rest, {
      className: cx('pf-btn', 'pf-btn-' + variant, props.size === 'sm' && 'pf-btn-sm', props.className)
    }), props.children);
  }

  var GLYPH = { ACHAT: '▲', VENTE: '▼', RIEN: '■' };
  function DecisionBadge(props) {
    var d = props.decision || 'RIEN';
    return h('span', { className: cx('pf-badge', 'pf-badge-' + d, props.size === 'lg' && 'pf-badge-lg') },
      h('span', { 'aria-hidden': 'true' }, GLYPH[d]), d);
  }

  function KpiCard(props) {
    var d = props.delta;
    var cls = d == null ? null : d > 0 ? 'pf-up' : d < 0 ? 'pf-down' : 'pf-flat';
    var arrow = d == null ? '' : d > 0 ? '▲ ' : d < 0 ? '▼ ' : '';
    return h('div', { className: 'pf-card' },
      h('div', { className: 'pf-kpi-label' }, props.label),
      h('div', { className: 'pf-kpi-value' }, props.value),
      d == null ? (props.hint ? h('div', { className: 'pf-kpi-delta pf-flat' }, props.hint) : null)
        : h('div', { className: cx('pf-kpi-delta', cls) }, arrow + pct(d) + (props.deltaLabel ? ' ' + props.deltaLabel : '')));
  }

  function AlertBanner(props) {
    var level = props.level;
    if (!level || level === 'AUCUN') return null;
    var v = pct(props.variation);
    var body = level === 'ATTEINT'
      ? [h('strong', { key: 'a' }, 'Limite de perte atteinte : ' + v + ' cette semaine.'), ' La vente est conseillée sur les positions en baisse.']
      : [h('strong', { key: 'a' }, 'Perte de la semaine : ' + v + '.'), ' Vous approchez de la limite de −10 % : aucun achat n’est conseillé.'];
    return h('div', { className: cx('pf-alert', 'pf-alert-' + level), role: level === 'ATTEINT' ? 'alert' : 'status' },
      h(TriangleIcon), h('div', null, body));
  }

  function AmountInput(props) {
    var id = props.id || 'montant';
    return h('div', { className: 'pf-field' },
      h('label', { htmlFor: id }, props.label || 'Montant'),
      h('div', { className: cx('pf-input-wrap', props.error && 'pf-invalid') },
        h('input', { id: id, inputMode: 'decimal', value: props.value, placeholder: '0', onChange: props.onChange, readOnly: !props.onChange,'aria-invalid': props.error ? 'true' : undefined }),
        h('span', { className: 'pf-input-unit' }, '€')),
      props.error
        ? h('div', { className: 'pf-error', role: 'alert' }, props.error)
        : (props.cash != null ? h('div', { className: 'pf-help' }, 'Cash disponible : ' + eur(props.cash)) : null));
  }

  function StockCheckbox(props) {
    return h('label', { className: cx('pf-check', props.checked && 'pf-checked') },
      h('input', { type: 'checkbox', checked: !!props.checked, onChange: props.onChange || function () {} }),
      h('span', { className: 'pf-dot', style: { background: 'var(--' + (props.color || 'brand') + ')' }, 'aria-hidden': 'true' }),
      h('span', { className: 'pf-check-name' }, props.name),
      h('span', { className: 'pf-mono' }, props.ticker));
  }

  function ForecastBar(props) {
    var cells = [
      ['Défavorable', props.defavorable, false],
      ['Central', props.central, true],
      ['Favorable', props.favorable, false]
    ];
    return h('div', { className: 'pf-fc' }, cells.map(function (c) {
      var cls = c[1] > 0 ? 'pf-up' : c[1] < 0 ? 'pf-down' : 'pf-flat';
      return h('div', { key: c[0], className: cx('pf-fc-cell', c[2] && 'pf-fc-central') },
        h('div', { className: 'pf-fc-name' }, c[0]),
        h('div', { className: cx('pf-fc-pct', cls) }, pct(c[1])),
        props.montant != null ? h('div', { className: 'pf-fc-eur' }, eurSigned(Math.round(props.montant * c[1] / 100))) : null);
    }));
  }

  var VERDICT = {
    VALIDER: ['Vous pouvez valider', 'pf-up'],
    NE_RIEN_FAIRE: ['Ne rien faire pour l’instant', 'pf-flat'],
    PRIVILEGIER_VENTE: ['Privilégier la vente, ne pas acheter', 'pf-down'],
    CONSERVER: ['Conserver la position', 'pf-flat'],
    REFUSE: ['Opération refusée', 'pf-down']
  };
  function AdviceCard(props) {
    var v = VERDICT[props.verdict] || VERDICT.NE_RIEN_FAIRE;
    return h('div', { className: cx('pf-card', 'pf-advice') },
      h('div', { className: 'pf-advice-head' },
        h('div', null,
          h('h3', { className: 'pf-advice-title' }, props.nom),
          h('div', { className: 'pf-mono' }, props.ticker + ' · ' + eur(props.cours))),
        h(DecisionBadge, { decision: props.conseil, size: 'lg' })),
      h('div', { className: cx('pf-verdict', v[1]) }, v[0]),
      h('dl', { className: 'pf-facts' },
        h('div', null, h('dt', null, 'Actions'), h('dd', null, int(props.quantite))),
        h('div', null, h('dt', null, 'Montant investi'), h('dd', null, eur(props.montant))),
        h('div', null, h('dt', null, 'Reste en cash'), h('dd', null, eur(props.reliquat))),
        h('div', null, h('dt', null, 'Dividende estimé / an'), h('dd', null, eur(props.dividende)))),
      props.prevision ? h('div', null,
        h('div', { className: 'pf-sec' }, 'Prévision de la semaine'),
        h(ForecastBar, Object.assign({ montant: props.montant }, props.prevision))) : null,
      props.raisons && props.raisons.length ? h('div', null,
        h('div', { className: 'pf-sec' }, 'Pourquoi ce conseil'),
        h('ul', { className: 'pf-reasons' }, props.raisons.map(function (r, i) { return h('li', { key: i }, r); }))) : null,
      props.children);
  }

  window.Pf500 = Object.assign(window.Pf500 || {}, {
    Button: Button, DecisionBadge: DecisionBadge, KpiCard: KpiCard, AlertBanner: AlertBanner,
    AmountInput: AmountInput, StockCheckbox: StockCheckbox, ForecastBar: ForecastBar, AdviceCard: AdviceCard,
    format: { eur: eur, pct: pct, int: int }
  });
})();
