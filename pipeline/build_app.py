import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
SOURCE = STATE / "filings.json"
FIVE_YEAR_SOURCE = STATE / "five-year-filings.json"
FIVE_YEAR_DEALS = STATE / "french-deals-5-years.json"
EUROPE_SOURCE = STATE / "europe-filings.json"
LEGACY_ZODIAC_SOURCE = STATE / "zodiac-legacy-export.txt"
SHARE_CAPITAL_SOURCE = STATE / "share_capital.json"
OUT_DIR = ROOT.parent
OUT = OUT_DIR / "index.html"
ZODIAC_TARGET = "ZODIAC AEROSPACE"
ZODIAC_ISIN = "FR0000125684"
ZODIAC_FILER_ALIASES = {
    None: "BLACKROCK GROUP",
    "BlackRock, Inc.": "BLACKROCK GROUP",
    "Aviva Investors France": "AVIVA INVESTORS FRANCE",
    "Aviva France": "AVIVA INVESTORS FRANCE",
    "T. Rowe Price Associates, Inc.": "T. ROWE PRICE ASSOCIATES, INC. & ITS AFFILIATES",
    "T. Rowe Price": "T. ROWE PRICE ASSOCIATES, INC. & ITS AFFILIATES",
    "DNCA Finance": "NATIXIS GLOBAL ASSET MANAGEMENT",
    "Syquant Capital": "SYQUANT CAPITAL",
    "Magnetar Capital Partners LP": "MAGNETAR CAPITAL PARTNERS",
    "Boussard & Gavaudan": "BOUSSARD & GAVAUDAN",
    "Partners Limited": "BOUSSARD & GAVAUDAN",
    "LLC": "AQR CAPITAL MANAGEMENT, LLC.",
    "Farallon Capital Europe LLP": "FARALLON CAPITAL EUROPE",
    "PSquared Asset Management AG": "PSQUARED ASSET MANAGEMENT AG",
    "UBS Investment Bank": "UBS INVESTMENT BANK",
    "Polygon Global Partners": "POLYGON GLOBAL PARTNERS LLP",
    "Polygon Global Partners LLP": "POLYGON GLOBAL PARTNERS LLP",
}


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>French OPA Dealings Tracker</title>
  <style>
    :root {
      --blue: #426f9f;
      --blue-dark: #174f87;
      --link: #2f6fb4;
      --line: #cfcfcf;
      --header: #646464;
      --soft: #efefef;
      --menu: #f5f5f5;
      --text: #1f2933;
      --muted: #606b76;
      --warn-bg: #fde6e6;
      --warn: #cc3333;
      --green: #0f766e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--text);
      background: #fff;
      font-size: 14px;
      line-height: 1.28;
    }
    a {
      color: var(--link);
      text-decoration: underline;
      cursor: pointer;
    }
    button, input, select, textarea {
      font: inherit;
    }
    .shell {
      width: min(1504px, calc(100vw - 24px));
      margin: 14px auto 24px;
      border-top: 0;
    }
    .login {
      text-align: right;
      color: var(--muted);
      padding: 0 0 6px;
      font-size: 13px;
    }
    .masthead {
      background: var(--blue);
      color: #fff;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 1px;
      padding: 8px 16px;
      border-bottom: 7px solid #69a9cc;
    }
    .masthead em {
      font-weight: 400;
      font-style: italic;
      letter-spacing: 1px;
    }
    .layout {
      display: grid;
      grid-template-columns: 312px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    nav {
      border-right: 1px solid var(--line);
      background: #fff;
    }
    .menu-block {
      border-bottom: 1px solid var(--line);
      padding-bottom: 10px;
      margin-bottom: 18px;
    }
    .menu-title {
      background: #e1e3e1;
      font-weight: 700;
      letter-spacing: .5px;
      padding: 6px 8px;
    }
    .menu-link {
      display: block;
      padding: 3px 8px 3px 31px;
      color: #315da2;
      text-decoration: none;
      position: relative;
      font-size: 13px;
    }
    .menu-link::before {
      content: "›";
      position: absolute;
      left: 8px;
      top: 3px;
      width: 18px;
      height: 14px;
      border-radius: 2px;
      background: #9aa0a6;
      color: #fff;
      text-align: center;
      line-height: 14px;
      font-weight: 700;
    }
    main {
      padding: 34px 0 0;
      min-width: 0;
    }
    .content-top {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
      margin-bottom: 24px;
    }
    h1 {
      margin: 18px 0 12px;
      color: var(--blue-dark);
      font-size: 28px;
      letter-spacing: .3px;
    }
    h2 {
      color: var(--blue-dark);
      font-size: 18px;
      margin: 0 0 10px;
    }
    .stats {
      border: 1px solid var(--line);
      padding: 9px 12px;
      min-width: 272px;
      font-size: 18px;
      background: #fff;
    }
    .stats div {
      display: flex;
      justify-content: space-between;
      gap: 22px;
      padding: 3px 0;
    }
    .stats strong {
      font-size: 23px;
      letter-spacing: 1px;
    }
    .toolbar {
      display: grid;
      grid-template-columns: minmax(190px, 1.1fr) minmax(150px, .8fr) minmax(150px, .8fr) minmax(120px, .55fr) minmax(120px, .55fr) auto;
      gap: 8px;
      align-items: end;
      margin: 0 0 10px;
    }
    label {
      display: grid;
      gap: 3px;
      color: var(--muted);
      font-size: 12px;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      min-height: 28px;
      padding: 4px 6px;
      background: #fff;
      color: var(--text);
    }
    textarea {
      min-height: 92px;
      resize: vertical;
    }
    button {
      border: 1px solid #888;
      min-height: 28px;
      padding: 4px 10px;
      background: #f8f8f8;
      color: var(--text);
      cursor: pointer;
    }
    .button-primary {
      background: var(--green);
      border-color: #075f59;
      color: #fff;
      font-weight: 700;
    }
    .button-secondary {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 10px;
      border: 1px solid #888;
      background: #f8f8f8;
      color: var(--link);
      text-decoration: none;
    }
    .import-file {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 10px;
      border: 1px solid #888;
      background: #f8f8f8;
      color: var(--link);
      cursor: pointer;
    }
    .import-file input {
      display: none;
    }
    .table-meta {
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 13px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 13px;
      background: #fff;
    }
    th {
      background: var(--header);
      color: #fff;
      text-align: left;
      padding: 6px 5px;
      border: 1px solid #d7d7d7;
      font-weight: 700;
      cursor: pointer;
    }
    td {
      border: 1px solid #d9d9d9;
      padding: 5px;
      vertical-align: top;
      overflow-wrap: anywhere;
    }
    tbody tr:nth-child(even) td {
      background: #f3f3f3;
    }
    tbody tr:hover td {
      background: #eaf3ff;
    }
    .icon {
      display: inline-block;
      width: 17px;
      height: 17px;
      margin-right: 6px;
      border: 1px solid #aaa;
      color: #777;
      text-align: center;
      line-height: 15px;
      font-size: 12px;
      background: #f4f4f4;
    }
    .status {
      display: inline-block;
      min-width: 54px;
      text-align: center;
      padding: 1px 5px;
      border: 1px solid var(--line);
      background: #fff;
    }
    .status.review {
      border-color: #f2bd70;
      background: #fff5df;
      color: #8a5100;
    }
    .status.ok {
      border-color: #8ebd9a;
      background: #ecf8ef;
      color: #1f6f33;
    }
    .status.blocked {
      border-color: var(--warn);
      background: var(--warn-bg);
      color: #9b1c1c;
    }
    .status.no-results {
      border-color: #b8c1cc;
      background: #f4f7fb;
      color: #475569;
    }
    .toolbar.europe-toolbar {
      grid-template-columns: minmax(210px, 1.2fr) minmax(145px, .7fr) minmax(170px, .8fr) auto;
    }
    .manual-form {
      display: grid;
      grid-template-columns: repeat(3, minmax(180px, 1fr));
      gap: 10px;
      align-items: end;
    }
    .manual-form .wide {
      grid-column: 1 / -1;
    }
    .summary-note {
      max-width: 1100px;
      margin: 0 0 16px;
      color: var(--muted);
    }
    .notice-warning {
      border: 1px solid var(--warn);
      background: var(--warn-bg);
      padding: 12px 14px;
      font-size: 20px;
      font-weight: 700;
      margin: 14px 0 18px;
    }
    .detail-top {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: start;
      margin-bottom: 12px;
    }
    .detail-grid {
      display: grid;
      grid-template-columns: 140px minmax(220px, 1fr) 150px minmax(140px, .7fr) 160px minmax(140px, .7fr);
      gap: 10px 14px;
      align-items: center;
      max-width: 1060px;
    }
    .detail-grid b {
      color: var(--muted);
      text-align: right;
    }
    .detail-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .links-row {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 24px;
      margin: 14px 0 16px;
      font-size: 17px;
    }
    .tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      border-bottom: 1px solid #aaa;
      margin-top: 10px;
    }
    .tab {
      border: 1px solid #aaa;
      border-bottom: 0;
      background: #efefef;
      padding: 8px 16px;
      min-width: 130px;
      text-align: center;
      color: #1f2933;
      text-decoration: none;
    }
    .tab.active {
      background: #fff;
      border-top: 3px solid #ff7b22;
      padding-top: 6px;
    }
    .panel {
      border: 1px solid #ddd;
      border-top: 0;
      padding: 24px 28px;
      background: #fafafa;
      margin-bottom: 18px;
    }
    .box-title {
      display: inline-block;
      background: #fff;
      border: 1px solid #ddd;
      padding: 4px 10px;
      font-size: 20px;
      margin-bottom: 16px;
    }
    .kv {
      display: grid;
      grid-template-columns: 210px minmax(230px, 620px);
      gap: 10px 12px;
      align-items: center;
      margin-bottom: 12px;
    }
    .kv b {
      color: var(--muted);
      text-align: right;
    }
    .kv span {
      display: block;
      border: 1px solid #ccc;
      background: #fff;
      padding: 6px 8px;
      min-height: 30px;
    }
    .ps-title {
      font-weight: 700;
      margin: 8px 0 10px;
      font-size: 16px;
    }
    .ps-table {
      max-width: 930px;
    }
    .table-scroll {
      width: 100%;
      overflow-x: auto;
    }
    .register-table {
      min-width: 1625px;
      max-width: none;
      table-layout: fixed;
      font-variant-numeric: tabular-nums;
    }
    .register-table th {
      text-align: center;
    }
    .register-table td {
      text-align: right;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: clip;
    }
    .register-table td.left {
      text-align: left;
      white-space: normal;
    }
    .ownership-chart {
      max-width: 1050px;
      margin: 14px 0 18px;
      border: 1px solid var(--line);
      background: #fff;
      padding: 12px 14px;
    }
    .ownership-chart h2 {
      margin: 0 0 10px;
      font-size: 20px;
    }
    .ownership-row {
      display: grid;
      grid-template-columns: 185px minmax(220px, 1fr) 88px;
      gap: 10px;
      align-items: center;
      margin: 8px 0;
    }
    .ownership-label {
      color: var(--text);
      font-weight: 700;
    }
    .ownership-track {
      height: 18px;
      border: 1px solid #d5dce3;
      background: #eef1f4;
      overflow: hidden;
    }
    .ownership-fill {
      height: 100%;
      min-width: 0;
      background: var(--blue);
    }
    .ownership-fill.hedge {
      background: #b07d00;
    }
    .ownership-fill.institutional {
      background: var(--green);
    }
    .ownership-fill.other {
      background: #777;
    }
    .ownership-fill.unassigned {
      background: #b8c0c8;
    }
    .ownership-value {
      text-align: right;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }
    .ps-table th {
      background: #fff;
      color: var(--text);
      text-align: center;
      font-weight: 400;
    }
    .ps-table td {
      text-align: right;
      white-space: nowrap;
    }
    .ps-table td.left {
      text-align: left;
    }
    .negative {
      color: red;
    }
    .total-row td {
      font-weight: 700;
      border-top: 2px solid #777;
      background: #fff !important;
    }
    .export-bar {
      max-width: 930px;
      background: #666;
      color: #fff;
      padding: 5px;
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 8px;
      font-weight: 700;
    }
    .export-bar select {
      min-height: 24px;
      width: 260px;
    }
    .hidden {
      display: none !important;
    }
    .muted {
      color: var(--muted);
    }
    .empty {
      padding: 24px;
      text-align: center;
      color: var(--muted);
    }
    @media (max-width: 1120px) {
      .layout {
        grid-template-columns: 1fr;
      }
      nav {
        display: none;
      }
      main {
        padding-top: 16px;
      }
      .toolbar {
        grid-template-columns: 1fr 1fr;
      }
      .detail-grid {
        grid-template-columns: 130px 1fr;
      }
      .detail-actions {
        justify-content: flex-start;
      }
      .links-row {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 680px) {
      .shell {
        width: calc(100vw - 12px);
        margin-top: 6px;
      }
      .masthead {
        font-size: 20px;
      }
      .content-top,
      .detail-top {
        grid-template-columns: 1fr;
        display: grid;
      }
      .toolbar {
        grid-template-columns: 1fr;
      }
      table {
        min-width: 900px;
      }
      .table-scroll {
        overflow-x: auto;
      }
      .kv {
        grid-template-columns: 1fr;
      }
      .kv b,
      .detail-grid b {
        text-align: left;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="login">you are logged in as demo@ma-monitor.co.uk | <a>logout</a></div>
    <div class="masthead">french opa monitor <em>administration</em> - ADMIN</div>
    <div class="layout">
      <nav>
        <div class="menu-block">
          <div class="menu-title">Main Menu</div>
          <a class="menu-link" href="#/filings">Home</a>
          <a class="menu-link" href="#/filings">Edit Details</a>
          <a class="menu-link" href="#/filings">Logout</a>
        </div>
        <div class="menu-block">
          <div class="menu-title">Manage Deals</div>
          <a class="menu-link" href="#/filings">Search Deals</a>
          <a class="menu-link" href="#/filings">Deal Status</a>
          <a class="menu-link" href="#/filings">Data Statistics</a>
          <a class="menu-link" href="#/filings">Multiple export</a>
          <a class="menu-link" href="#/filings">Manage Advisors</a>
          <a class="menu-link" href="#/manage-companies">Manage Companies</a>
          <a class="menu-link" href="#/filings">Share Prices</a>
        </div>
        <div class="menu-block">
          <div class="menu-title">AMF OPA</div>
          <a class="menu-link" href="#/filings">Browse All</a>
          <a class="menu-link" href="#/filings">New Today</a>
          <a class="menu-link" href="#/filings">Requires Attention</a>
          <a class="menu-link" href="#/filings">Purchases & Sales</a>
          <a class="menu-link" href="#/share-register">Share register</a>
          <a class="menu-link" href="#/share-capital">Total share capital</a>
          <a class="menu-link" href="#/offers">Offer periods</a>
        </div>
        <div class="menu-block">
          <div class="menu-title">Europe</div>
          <a class="menu-link" href="#/europe-alerts">Alert desk</a>
          <a class="menu-link" href="#/europe-manual">Manual filing input</a>
          <a class="menu-link" href="#/europe-filings">European filings</a>
        </div>
      </nav>
      <main id="app"></main>
    </div>
  </div>

  <script>
    const DATA = __DATA__;
    const transactions = DATA.transactions || [];
    const notices = DATA.notice_summaries || [];
    const offers = DATA.offer_period_companies_from_amf_xlsx?.companies || [];
    const europe = DATA.europe_regulatory || {};
    const europeTargets = europe.current_targets || [];
    const europeFilings = europe.filings || [];
    const europeChecks = europe.source_checks || [];
    const europeRouteChecks = europe.route_checks || [];
    const europeUpdates = europe.updates || [];
    const europeSources = europe.regulatory_sources || [];
    const europeAlertTargets = europe.alert_targets || europeTargets;
    const app = document.querySelector("#app");
    const SHARE_CAPITAL_STORAGE_KEY = "frenchOpaShareCapital";
    const COMPANY_LINKS_STORAGE_KEY = "frenchOpaCompanyLinks";
    const EUROPE_FILINGS_STORAGE_KEY = "europeRegulatoryFilings";
    const EUROPE_MANUAL_FILINGS_STORAGE_KEY = "europeManualFilings";
    const EUROPE_ALERT_SETTINGS_STORAGE_KEY = "europeAlertSettings";
    const CONSOB_MAJOR_SHAREHOLDINGS_URL = "https://www.consob.it/web/consob-and-its-activities/listed-companies/major-shareholdings-list";
    const COMPANY_TYPES = ["Unassigned", "Hedge Fund", "Institutional Investor", "Other"];
    const importedShareCapitalEntries = buildImportedShareCapitalEntries();
    const shareCapitalEntries = mergeShareCapitalEntries(importedShareCapitalEntries, loadShareCapitalEntries());
    const companyLinks = loadCompanyLinks();
    const localEuropeFilings = loadLocalEuropeFilings();
    const manualEuropeFilings = loadManualEuropeFilings();
    const europeAlertSettings = loadEuropeAlertSettings();

    const state = {
      sortKey: "display_date",
      sortDir: "desc",
      search: "",
      target: "",
      filer: "",
      type: "",
      deal: "",
      shareCapitalTarget: "",
      companySearch: "",
      europeSearch: "",
      europeCountry: "",
      europeStatus: "",
      europeImportMessage: "",
      europeManualMessage: "",
    };

    const dealLabels = {
      buy: "Buy",
      sell: "Sell",
      transfer_in: "Transfer In",
      transfer_out: "Transfer Out",
      loan_return: "Loan Return",
      loan_setup: "Loan Setup",
      derivative_position: "Derivative position",
      legacy_position: "Position",
    };

    function noticeRows(number) {
      return transactions.filter((row) => row.amf_number === number);
    }

    function noticeMap() {
      return new Map(notices.map((notice) => [notice.amf_number, notice]));
    }

    function rowDisplayDate(row) {
      return row.date_information || row.online_at || row.published_at || "";
    }

    function noticeDisplayDate(notice) {
      return notice.document_date || notice.date_information || notice.online_at || notice.published_at || "";
    }

    function enrichedNotices() {
      const mapped = noticeMap();
      const numbers = [...new Set([
        ...notices.map((notice) => notice.amf_number),
        ...transactions.map((row) => row.amf_number),
      ].filter(Boolean))];
      return numbers.map((number) => {
        const rows = noticeRows(number);
        const notice = mapped.get(number) || {};
        const filers = unique(rows.map((row) => canonicalCompanyName(row.filer)));
        const rawFilers = unique(rows.map((row) => row.filer));
        const first = rows[0] || {};
        return {
          ...notice,
          amf_number: number,
          target: notice.target || first.target || "",
          filers,
          raw_filers: rawFilers,
          company_dealing: filers.join(", "),
          published_at: first.published_at || "",
          online_at: first.online_at || "",
          date_information: notice.date_information || first.date_information || "",
          display_date: noticeDisplayDate({ ...notice, ...first }),
          rows,
          row_count: rows.length,
        };
      });
    }

    function render() {
      const route = location.hash || "#/filings";
      if (route.startsWith("#/filing/")) {
        renderFiling(decodeURIComponent(route.replace("#/filing/", "")));
      } else if (route.startsWith("#/ps/")) {
        const [target = "", filer = ""] = route.replace("#/ps/", "").split("/");
        renderPS(decodeURIComponent(target), decodeURIComponent(filer));
      } else if (route.startsWith("#/share-register")) {
        const target = route.includes("#/share-register/")
          ? decodeURIComponent(route.replace("#/share-register/", ""))
          : "";
        renderShareRegister(target);
      } else if (route.startsWith("#/share-capital")) {
        const target = route.includes("#/share-capital/")
          ? decodeURIComponent(route.replace("#/share-capital/", ""))
          : "";
        renderShareCapital(target);
      } else if (route.startsWith("#/manage-companies")) {
        renderManageCompanies();
      } else if (route.startsWith("#/offers")) {
        renderOffers();
      } else if (route.startsWith("#/europe-filings")) {
        renderEuropeFilings();
      } else if (route.startsWith("#/europe-alerts")) {
        renderEuropeAlertDesk();
      } else if (route.startsWith("#/europe-manual")) {
        const target = route.includes("#/europe-manual/")
          ? decodeURIComponent(route.replace("#/europe-manual/", ""))
          : "";
        renderEuropeManualFiling(target);
      } else {
        renderFilings();
      }
    }

    function renderFilings() {
      const all = enrichedNotices();
      const filtered = all.filter((notice) => {
        const haystack = [notice.amf_number, notice.target, notice.company_dealing]
          .join(" ")
          .toLowerCase();
        return (!state.search || haystack.includes(state.search.toLowerCase()))
          && (!state.target || notice.target === state.target)
          && (!state.filer || notice.filers.includes(state.filer))
          && (!state.type || notice.rows.some((row) => row.instrument_type === state.type))
          && (!state.deal || notice.rows.some((row) => row.operation_type === state.deal));
      }).sort(compareBy(state.sortKey, state.sortDir));

      app.innerHTML = `
        <div class="content-top">
          <div>
            <h1>AMF OPA - All Filings</h1>
            <div class="muted">Reporting purchases and sales during a public offering</div>
          </div>
          <div class="stats">
            <div><span>Filings processed:</span><strong>${all.length}</strong></div>
            <div><span>Needs attention:</span><strong>${notices.filter((n) => n.parse_status !== "ok").length}</strong></div>
            <div><span>Transactions:</span><strong>${transactions.length}</strong></div>
            <div><span>Last generated:</span><strong>${formatDateTime(DATA.generated_at, true)}</strong></div>
          </div>
        </div>
        <div class="toolbar">
          <label>Search<input id="search" type="search" value="${escAttr(state.search)}" placeholder="Target, bidder, AMF ref"></label>
          <label>Target<select id="target">${options("All targets", unique(all.map((n) => n.target)), state.target)}</select></label>
          <label>Bidder / filer<select id="filer">${options("All bidders", unique(all.flatMap((n) => n.filers)), state.filer)}</select></label>
          <label>Type<select id="type">${options("All types", unique(transactions.map((r) => r.instrument_type)), state.type)}</select></label>
          <label>Deal<select id="deal">${options("All deals", unique(transactions.map((r) => r.operation_type)), state.deal, dealLabels)}</select></label>
          <button id="reset" type="button">Reset</button>
        </div>
        <div class="table-meta">${filtered.length} filings shown</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:150px" data-sort="display_date">Date</th>
                <th style="width:230px" data-sort="target">Title</th>
                <th data-sort="company_dealing">Company dealing</th>
                <th style="width:90px">Rows</th>
                <th style="width:100px">Processed</th>
                <th style="width:90px">Updated</th>
                <th style="width:110px">Attention</th>
              </tr>
            </thead>
            <tbody>
              ${filtered.map((notice) => filingRow(notice)).join("") || `<tr><td colspan="7" class="empty">No filings match these filters.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;

      bindFilingsControls();
    }

    function filingRow(notice) {
      const attention = notice.parse_status === "ok" ? "" : "Review";
      return `
        <tr>
          <td>${esc(formatDateTime(notice.display_date))}</td>
          <td><span class="icon">?</span><a href="#/filing/${encodeURIComponent(notice.amf_number)}">${esc(notice.target)}</a><br><span class="muted">${esc(notice.amf_number)}</span></td>
          <td>${esc(notice.company_dealing)}</td>
          <td>${notice.row_count}</td>
          <td>Yes</td>
          <td>Yes</td>
          <td>${attention ? `<span class="status review">${attention}</span>` : ""}</td>
        </tr>
      `;
    }

    function bindFilingsControls() {
      ["search", "target", "filer", "type", "deal"].forEach((id) => {
        document.querySelector(`#${id}`).addEventListener("input", (event) => {
          state[id] = event.target.value;
          renderFilings();
        });
      });
      document.querySelector("#reset").addEventListener("click", () => {
        Object.assign(state, { search: "", target: "", filer: "", type: "", deal: "" });
        renderFilings();
      });
      document.querySelectorAll("[data-sort]").forEach((header) => {
        header.addEventListener("click", () => {
          setSort(header.dataset.sort);
          renderFilings();
        });
      });
    }

    function renderFiling(number) {
      const notice = enrichedNotices().find((item) => item.amf_number === number);
      if (!notice) {
        app.innerHTML = `<p class="empty">Filing not found.</p>`;
        return;
      }

      const rows = notice.rows;
      const primaryFiler = notice.filers[0] || "";
      const bidderLinks = notice.filers.map((filer) =>
        `<a href="#/ps/${encodeURIComponent(notice.target)}/${encodeURIComponent(filer)}">Go to P/S for Target&Bidder »</a> <span class="muted">${esc(filer)}</span>`
      ).join("<br>");
      const shareRows = rows.filter((row) => row.instrument_type === "Shares");
      const derivativeRows = rows.filter((row) => row.instrument_type === "Derivative");

      app.innerHTML = `
        <div class="detail-top">
          <div class="detail-grid">
            <b>AMF Number:</b><span>${esc(notice.amf_number)}</span>
            <b>Processed:</b><span>☑</span>
            <b>Parser error:</b><span>☐</span>
            <b>Title:</b><span>${esc(notice.target)} : Purchases and sales</span>
            <b>Check required:</b><span>${notice.parse_status === "ok" ? "☐" : "☑"}</span>
            <b>Human error:</b><span>☐</span>
            <b>Date:</b><span>${esc(formatDateTime(notice.display_date))}</span>
            <b>Hidden:</b><span>☐</span>
            <b>Updated:</b><span>☑</span>
            <b>Company:</b><span>${esc(primaryFiler)}</span>
            <b>Split:</b><span>${notice.filers.length > 1 ? "Yes" : "No"}</span>
            <b>Class of relevant security:</b><span>Ordinary</span>
          </div>
          <div class="detail-actions">
            <button type="button">📝 Note</button>
            <button type="button" onclick="window.open('${escAttr(notice.document_url || "")}', '_blank')">View</button>
            <button class="button-primary" type="button">Update</button>
          </div>
        </div>
        ${notice.parse_status === "ok" ? "" : `<div class="notice-warning">Manual check Required!</div>`}
        <div class="links-row">
          <div>${bidderLinks || ""}</div>
          <div><a href="#/filings">Back to all filings »</a></div>
          <div>${notice.document_url ? `<a href="${escAttr(notice.document_url)}" target="_blank">Open original PDF »</a>` : ""}</div>
        </div>
        <div class="tabs">
          <a class="tab active">Main Information</a>
          <a class="tab">Purchases and Sales</a>
          <a class="tab">Derivatives transactions</a>
          <a class="tab">Supplemental</a>
        </div>
        <section class="panel">
          <div class="box-title">1. KEY INFORMATION</div>
          <div class="kv">
            <b>Trading company:</b><span>${esc(primaryFiler)}</span>
            <b>Company Dealt in:</b><span>${esc(notice.target)}</span>
            <b>Class of Relevant security:</b><span>Ordinary</span>
            <b>Dealing Date:</b><span>${esc(unique(rows.map((row) => row.transaction_date)).join(", "))}</span>
            <b>Deal No.:</b><span>${esc(notice.amf_number)}</span>
          </div>
          ${notice.parse_notes?.length ? `<div class="box-title">Review notes</div><ul>${notice.parse_notes.map((note) => `<li>${esc(note)}</li>`).join("")}</ul>` : ""}
        </section>
        <h2>3a. Purchases and Sales</h2>
        ${transactionTable(shareRows)}
        <h2>3b. Derivatives transactions</h2>
        ${transactionTable(derivativeRows)}
      `;
    }

    function transactionTable(rows) {
      if (!rows.length) return `<p class="muted">No rows in this section.</p>`;
      return `
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:110px">Dealing date</th>
                <th style="width:140px">Type</th>
                <th>Operation</th>
                <th style="width:100px">Quantity</th>
                <th style="width:90px">Price</th>
                <th style="width:250px">Resulting holding</th>
              </tr>
            </thead>
            <tbody>
              ${rows.map((row) => `
                <tr>
                  <td>${esc(row.transaction_date)}</td>
                  <td>${esc(row.instrument_type)}</td>
                  <td>${esc(dealLabels[row.operation_type] || row.operation)}</td>
                  <td>${fmtNumber(row.quantity)}</td>
                  <td>${esc(row.price_eur)}</td>
                  <td>${esc(row.resulting_holding)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }

    function renderPS(target, filer) {
      const rows = transactions
        .filter((row) => row.target === target && canonicalCompanyName(row.filer) === filer)
        .sort((a, b) => String(a.transaction_date).localeCompare(String(b.transaction_date)) || String(a.published_at).localeCompare(String(b.published_at)));
      const latestRow = rows[rows.length - 1] || {};
      const groups = collate(rows);
      const totals = groups.reduce((acc, row) => {
        acc.shares += row.sharesDelta;
        acc.derivatives += row.derivativeDelta;
        acc.net += row.net;
        return acc;
      }, { shares: 0, derivatives: 0, net: 0 });
      const purchaseVwap = tradeSideVwap(rows, "purchase");
      const saleVwap = tradeSideVwap(rows, "sale");

      app.innerHTML = `
        <div class="content-top">
          <div>
            <h1>Purchases & Sales</h1>
            <div><a href="#/filings">All filings</a> / <a href="#/filing/${encodeURIComponent(latestRow.amf_number || "")}">Latest filing detail</a></div>
          </div>
          <div class="stats">
            <div><span>Target:</span><strong>${esc(target)}</strong></div>
            <div><span>Bidder:</span><strong>${esc(filer)}</strong></div>
            <div><span>Rows:</span><strong>${rows.length}</strong></div>
          </div>
        </div>
        <div class="table-meta">Search Results</div>
        <p>Your search returned ${rows.length ? 1 : 0} results.</p>
        <div class="ps-title">⊟ ${esc(target)} - ${esc(filer)} [ORD]</div>
        <div class="table-scroll">
          <table class="ps-table">
            <thead>
              <tr>
                <th style="width:86px">Reported</th>
                <th style="width:86px">Dealing<br>date</th>
                <th style="width:96px">Purchases<br>and Sales<br>+/-</th>
                <th style="width:96px">Derivatives<br>and Options<br>+/-</th>
                <th style="width:92px">Long</th>
                <th style="width:92px">Calc. Long</th>
                <th style="width:92px">Difference</th>
                <th style="width:82px">Short</th>
                <th style="width:82px">Calc. Short</th>
                <th style="width:92px">Difference</th>
                <th style="width:82px">NET</th>
                <th style="width:70px"></th>
              </tr>
            </thead>
            <tbody>
              ${groups.map((row) => psRow(row)).join("") || `<tr><td colspan="12" class="empty">No collated rows for this target and bidder.</td></tr>`}
              <tr class="total-row">
                <td colspan="2">Total :</td>
                <td>${signed(totals.shares)}</td>
                <td>${signed(totals.derivatives)}</td>
                <td colspan="6"></td>
                <td>${signed(totals.net)}</td>
                <td></td>
              </tr>
              ${psVwapRow("VWAP purchases", purchaseVwap)}
              ${psVwapRow("VWAP sales", saleVwap)}
            </tbody>
          </table>
        </div>
        <div class="export-bar">
          <span>EXPORT</span>
          <span>format</span>
          <label><input type="radio"> XLS</label>
          <label><input type="radio" checked> CSV</label>
          <span>fields</span>
          <select><option>Please Select ...</option></select>
          <button class="button-primary" id="exportPs" type="button">Export trades + VWAP</button>
        </div>
      `;
      document.querySelector("#exportPs").addEventListener("click", () =>
        download(`${safeFilePart(target)}-${safeFilePart(filer)}-trades-vwap.csv`, psTradesCsv(target, filer, rows), "text/csv;charset=utf-8")
      );
    }

    function collate(rows) {
      const byKey = new Map();
      rows.forEach((row) => {
        const reported = noticeMap().get(row.amf_number)?.document_date || dateOnly(rowDisplayDate(row));
        const key = `${reported}|${row.transaction_date}`;
        if (!byKey.has(key)) {
          byKey.set(key, {
            reported,
            dealingDate: row.transaction_date,
            amfNumbers: new Set(),
            pdf: row.document_url,
            sharesDelta: 0,
            derivativeDelta: 0,
            reportedLong: null,
            reportedShort: null,
            calcLong: null,
            calcShort: 0,
            diffLong: null,
            diffShort: null,
            net: 0,
          });
        }
        const group = byKey.get(key);
        group.amfNumbers.add(row.amf_number);
        const qty = Number(row.quantity || 0);
        const signedQty = signedQuantity(row, qty);
        if (row.instrument_type === "Shares") group.sharesDelta += signedQty;
        if (row.instrument_type === "Derivative") group.derivativeDelta += signedQty;

        const holding = parseHolding(row.resulting_holding);
        if (holding.kind === "long") group.reportedLong = holding.value;
        if (holding.kind === "short") group.reportedShort = holding.value;
      });

      let previousLong = null;
      let previousShort = 0;
      return [...byKey.values()].sort((a, b) => String(a.dealingDate).localeCompare(String(b.dealingDate))).map((group) => {
        group.calcLong = previousLong == null
          ? group.reportedLong
          : previousLong + group.sharesDelta;
        group.calcShort = previousShort;
        group.diffLong = group.reportedLong == null || group.calcLong == null ? null : group.reportedLong - group.calcLong;
        group.diffShort = group.reportedShort == null ? null : group.reportedShort - group.calcShort;
        group.net = group.sharesDelta + group.derivativeDelta;
        if (group.reportedLong != null) previousLong = group.reportedLong;
        if (group.reportedShort != null) previousShort = group.reportedShort;
        return group;
      });
    }

    function psRow(row) {
      return `
        <tr>
          <td class="left"><span class="icon">?</span><a href="#/filing/${encodeURIComponent([...row.amfNumbers][0])}">${esc(shortDate(row.reported))}</a></td>
          <td class="left">${esc(shortDate(row.dealingDate))}</td>
          <td>${signed(row.sharesDelta)}</td>
          <td>${signed(row.derivativeDelta)}</td>
          <td>${fmtNumber(row.reportedLong)}</td>
          <td>${fmtNumber(row.calcLong)}</td>
          <td>${signed(row.diffLong)}</td>
          <td>${fmtNumber(row.reportedShort)}</td>
          <td>${fmtNumber(row.calcShort)}</td>
          <td>${signed(row.diffShort)}</td>
          <td>${signed(row.net)}</td>
          <td>${row.pdf ? `<a href="${escAttr(row.pdf)}" target="_blank">PDF</a>` : ""}</td>
        </tr>
      `;
    }

    function renderShareCapital(routeTarget) {
      const targets = shareCapitalTargets();
      const target = routeTarget || state.shareCapitalTarget || targets[0] || "";
      state.shareCapitalTarget = target;
      const entries = shareCapitalEntries
        .filter((entry) => entry.target === target)
        .sort((a, b) => String(b.date).localeCompare(String(a.date)));
      const latest = latestShareCapital(target);

      app.innerHTML = `
        <h1>Total Share Capital</h1>
        <div class="toolbar" style="grid-template-columns: 210px minmax(260px, 450px) 72px;">
          <label style="display:flex; align-items:center; justify-content:flex-end; color:var(--text); font-weight:700;">Company name or ticker:</label>
          <select id="capitalTarget">${options("", targets, target)}</select>
          <button id="findCapital" class="button-primary" type="button">Find</button>
        </div>
        <p><a href="#" id="capitalAdd">Add new total share capital value »</a></p>
        <section class="panel" style="max-width:850px;">
          <form id="capitalForm" class="toolbar" style="grid-template-columns: 150px 210px 180px 1fr 92px 70px; margin-bottom:0;">
            <input id="capitalEditId" type="hidden">
            <label>Effective date<input id="capitalDate" type="date" required></label>
            <label>Total share capital<input id="capitalTotal" type="text" inputmode="numeric" placeholder="e.g. 110,823,108" required></label>
            <label>Type<input id="capitalType" type="text" value="Ordinary shares"></label>
            <label>Check?<input id="capitalCheck" type="text" placeholder="Optional note"></label>
            <button class="button-primary" type="submit">Save</button>
            <button id="capitalReset" type="button">Clear</button>
          </form>
        </section>
        <h2>Search Results</h2>
        <div class="table-meta">Your search returned ${entries.length} result${entries.length === 1 ? "" : "s"}.
          ${latest ? `Latest share capital: <strong>${fmtNumber(latest.total)}</strong> as at ${esc(shortDate(latest.date))}` : "No share capital entered for this target yet."}
        </div>
        <div style="font-weight:700; margin:14px 0 8px;">⊟ [ORD] ${esc(target)}</div>
        <div class="table-scroll">
          <table style="max-width:850px;">
            <thead>
              <tr>
                <th style="width:140px">Dealing date</th>
                <th style="width:190px">Total Share Capital</th>
                <th style="width:180px">Type</th>
                <th>Check?</th>
                <th style="width:110px"></th>
              </tr>
            </thead>
            <tbody>
              ${entries.map(capitalRow).join("") || `<tr><td colspan="5" class="empty">No share-capital values have been entered for this target.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;

      document.querySelector("#findCapital").addEventListener("click", () => {
        const next = document.querySelector("#capitalTarget").value;
        location.hash = `#/share-capital/${encodeURIComponent(next)}`;
      });
      document.querySelector("#capitalTarget").addEventListener("change", (event) => {
        location.hash = `#/share-capital/${encodeURIComponent(event.target.value)}`;
      });
      document.querySelector("#capitalAdd").addEventListener("click", (event) => {
        event.preventDefault();
        clearCapitalForm();
        document.querySelector("#capitalDate").focus();
      });
      document.querySelector("#capitalReset").addEventListener("click", clearCapitalForm);
      document.querySelector("#capitalForm").addEventListener("submit", (event) => {
        event.preventDefault();
        saveCapitalForm(target);
      });
      document.querySelectorAll("[data-edit-capital]").forEach((link) => {
        link.addEventListener("click", (event) => {
          event.preventDefault();
          editCapitalEntry(link.dataset.editCapital);
        });
      });
    }

    function capitalRow(entry) {
      return `
        <tr>
          <td>${esc(shortDate(entry.date))}</td>
          <td>${fmtNumber(entry.total)}</td>
          <td>${esc(entry.type || "Ordinary shares")}</td>
          <td>${esc(entry.check || "")}</td>
          <td><a href="#" data-edit-capital="${escAttr(entry.id)}">Change »</a></td>
        </tr>
      `;
    }

    function clearCapitalForm() {
      document.querySelector("#capitalEditId").value = "";
      document.querySelector("#capitalDate").value = new Date().toISOString().slice(0, 10);
      document.querySelector("#capitalTotal").value = "";
      document.querySelector("#capitalType").value = "Ordinary shares";
      document.querySelector("#capitalCheck").value = "";
    }

    function editCapitalEntry(id) {
      const entry = shareCapitalEntries.find((item) => item.id === id);
      if (!entry) return;
      document.querySelector("#capitalEditId").value = entry.id;
      document.querySelector("#capitalDate").value = entry.date || "";
      document.querySelector("#capitalTotal").value = fmtNumber(entry.total);
      document.querySelector("#capitalType").value = entry.type || "Ordinary shares";
      document.querySelector("#capitalCheck").value = entry.check || "";
      document.querySelector("#capitalDate").focus();
    }

    function saveCapitalForm(target) {
      const id = document.querySelector("#capitalEditId").value || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const date = document.querySelector("#capitalDate").value;
      const total = parseShareCapitalNumber(document.querySelector("#capitalTotal").value);
      const type = document.querySelector("#capitalType").value.trim() || "Ordinary shares";
      const check = document.querySelector("#capitalCheck").value.trim();
      if (!target || !date || !Number.isFinite(total) || total <= 0) {
        window.alert("Please choose a target, date and valid total share capital.");
        return;
      }
      const next = { id, target, date, total, type, check };
      const index = shareCapitalEntries.findIndex((entry) => entry.id === id);
      if (index >= 0) shareCapitalEntries[index] = next;
      else shareCapitalEntries.push(next);
      saveShareCapitalEntries();
      renderShareCapital(target);
    }

    function renderManageCompanies() {
      const allRows = managedCompanyRows();
      const filtered = allRows.filter((row) => {
        const haystack = [row.sourceName, row.sharedName, row.type].join(" ").toLowerCase();
        return !state.companySearch || haystack.includes(state.companySearch.toLowerCase());
      });
      const linkedCount = allRows.filter((row) => normaliseCompanyKey(row.sourceName) !== normaliseCompanyKey(row.sharedName)).length;

      app.innerHTML = `
        <div class="content-top">
          <div>
            <h1>Manage Companies</h1>
          </div>
          <div class="stats">
            <div><span>Trading companies:</span><strong>${allRows.length}</strong></div>
            <div><span>Linked names:</span><strong>${linkedCount}</strong></div>
            <div><span>Saved records:</span><strong>${companyLinks.length}</strong></div>
          </div>
        </div>
        ${renderLinkReview()}
        <div class="toolbar" style="grid-template-columns: minmax(240px, 430px) 90px 220px;">
          <label>Search<input id="companySearch" type="search" value="${escAttr(state.companySearch)}" placeholder="Company or shared name"></label>
          <button id="companyReset" type="button">Reset</button>
          <button id="companyExport" type="button" title="Download company_links.json with the approved links, including any saved in this browser, to upload to pipeline/state/ in the admin repository">Export links file</button>
        </div>
        <div class="table-meta">${filtered.length} companies shown</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:260px">Trading company</th>
                <th style="width:280px">Shared name</th>
                <th style="width:190px">Company type</th>
                <th style="width:110px">Rows</th>
                <th>Linked with</th>
                <th style="width:120px"></th>
              </tr>
            </thead>
            <tbody>
              ${filtered.map(companyManageRow).join("") || `<tr><td colspan="6" class="empty">No companies match this search.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;

      document.querySelector("#companySearch").addEventListener("input", (event) => {
        state.companySearch = event.target.value;
        renderManageCompanies();
      });
      document.querySelector("#companyReset").addEventListener("click", () => {
        state.companySearch = "";
        renderManageCompanies();
      });
      document.querySelector("#companyExport").addEventListener("click", exportCompanyLinksFile);
      document.querySelectorAll("[data-accept-suggestion]").forEach((button) => {
        button.addEventListener("click", () => {
          const suggestion = openLinkSuggestions().find((item) => suggestionKey(item) === button.dataset.acceptSuggestion);
          if (!suggestion) return;
          suggestion.names
            .filter((name) => normaliseCompanyKey(name) !== normaliseCompanyKey(suggestion.shared))
            .forEach((name) => saveCompanyLink(name, suggestion.shared, companyTypeForSource(name)));
          renderManageCompanies();
        });
      });
      document.querySelectorAll("[data-reject-suggestion]").forEach((button) => {
        button.addEventListener("click", () => {
          const suggestion = openLinkSuggestions().find((item) => suggestionKey(item) === button.dataset.rejectSuggestion);
          if (!suggestion) return;
          const pairs = loadRejectedLinks();
          suggestion.names.forEach((a, i) => suggestion.names.slice(i + 1).forEach((b) => pairs.push([a, b])));
          saveRejectedLinks(pairs);
          renderManageCompanies();
        });
      });
      document.querySelectorAll("[data-save-company]").forEach((button) => {
        button.addEventListener("click", () => {
          const sourceName = button.dataset.saveCompany;
          const row = button.closest("tr");
          saveCompanyLink(
            sourceName,
            row.querySelector("[data-company-shared]").value.trim() || sourceName,
            row.querySelector("[data-company-type]").value || "Unassigned"
          );
          renderManageCompanies();
        });
      });
      document.querySelectorAll("[data-clear-company]").forEach((link) => {
        link.addEventListener("click", (event) => {
          event.preventDefault();
          clearCompanyLink(link.dataset.clearCompany);
          renderManageCompanies();
        });
      });
    }

    function renderLinkReview() {
      const suggestions = openLinkSuggestions();
      const fragments = DATA.company_link_review?.fragments || [];
      const autoCount = serverCompanyLinks.filter((entry) => !entry.rule.startsWith("approved")).length;
      const approvedCount = serverCompanyLinks.filter((entry) => entry.rule.startsWith("approved")).length;
      return `
        <div class="summary-note">
          ${fmtNumber(autoCount)} names are linked automatically (same name apart from case, punctuation or legal form, or a shortened name)
          and ${fmtNumber(approvedCount)} by approved links. Links saved here with <b>Save</b> apply in this browser only &mdash;
          use <b>Export links file</b> and upload it to <code>pipeline/state/company_links.json</code> to make them permanent.
        </div>
        ${suggestions.length ? `
        <div class="table-meta">Suggested links to review (${suggestions.length}) &mdash; same brand or an incomplete name; these may be different entities</div>
        <div class="table-scroll" style="margin-bottom:18px">
          <table>
            <thead><tr><th>Names</th><th style="width:260px">Would be shown as</th><th style="width:300px">Why suggested</th><th style="width:190px"></th></tr></thead>
            <tbody>
              ${suggestions.map((suggestion) => `
                <tr>
                  <td>${suggestion.names.map(esc).join("<br>")}</td>
                  <td>${esc(suggestion.shared)}</td>
                  <td class="muted">${esc(suggestion.reason)}</td>
                  <td>
                    <button class="button-primary" type="button" data-accept-suggestion="${escAttr(suggestionKey(suggestion))}">Link</button>
                    <button type="button" data-reject-suggestion="${escAttr(suggestionKey(suggestion))}">Not the same</button>
                  </td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>` : ""}
        ${fragments.length ? `
        <details style="margin-bottom:18px">
          <summary class="table-meta" style="cursor:pointer">Incomplete names from the filings (${fragments.length}) &mdash; the PDF reader cut these short, so they cannot be matched by name</summary>
          <div class="muted" style="padding:8px 0">${fragments.map((item) => `${esc(item.name)} (${fmtNumber(item.rows)})`).join(" &middot; ")}</div>
        </details>` : ""}
      `;
    }

    function companyManageRow(row) {
      const aliases = companyAliases(row.sourceName, row.sharedName);
      const rule = companyLinkRule(row.sourceName);
      return `
        <tr>
          <td>${esc(row.sourceName)}</td>
          <td><input data-company-shared value="${escAttr(row.sharedName)}"></td>
          <td><select data-company-type>${companyTypeOptions(row.type)}</select></td>
          <td>${fmtNumber(row.rows)}</td>
          <td>${aliases.length ? esc(aliases.join(", ")) : `<span class="muted">None</span>`}${rule ? `<div class="muted" style="font-size:12px">${esc(rule)}</div>` : ""}</td>
          <td>
            <button class="button-primary" type="button" data-save-company="${escAttr(row.sourceName)}">Save</button>
            <a href="#" data-clear-company="${escAttr(row.sourceName)}">Clear</a>
          </td>
        </tr>
      `;
    }

    function renderShareRegister(routeTarget) {
      const targetsByActivity = [...new Set(transactions.map((row) => row.target).filter(Boolean))]
        .sort((a, b) => transactions.filter((row) => row.target === b).length - transactions.filter((row) => row.target === a).length || a.localeCompare(b));
      const target = routeTarget || targetsByActivity[0] || "";
      const register = buildShareRegister(target);
      const baseline = register.baselineDate || "first observed filing";
      const shareCapital = register.shareCapital;
      const shareCapitalLabel = shareCapital
        ? `${fmtNumber(shareCapital.total)} as at ${shortDate(shareCapital.date)}`
        : `<a href="#/share-capital/${encodeURIComponent(target)}">Add share capital</a>`;

      app.innerHTML = `
        <div class="content-top">
          <div>
            <h1>Share Register</h1>
            <div class="muted">Current disclosed positions from AMF purchases and sales filings</div>
          </div>
          <div class="stats">
            <div><span>Investors:</span><strong>${register.rows.length}</strong></div>
            <div><span>Last updated:</span><strong>${formatDateTime(register.lastUpdated, true)}</strong></div>
            <div><span>Share capital:</span><strong>${shareCapital ? fmtNumber(shareCapital.total) : "n/a"}</strong></div>
          </div>
        </div>
        <div class="toolbar" style="grid-template-columns: 80px minmax(260px, 420px) 72px;">
          <label style="display:flex; align-items:center; justify-content:flex-end; color:var(--text); font-weight:700;">Target:</label>
          <select id="registerTarget">${options("", targetsByActivity, target)}</select>
          <button id="findRegister" class="button-primary" type="button">Find</button>
        </div>
        <div class="table-meta">Last Updated: ${esc(formatDateTime(register.lastUpdated, true))} | Total share capital: ${shareCapitalLabel}</div>
        <div class="table-scroll">
          <table class="register-table">
            <colgroup>
              <col style="width:64px">
              <col style="width:230px">
              <col style="width:130px">
              <col style="width:125px">
              <col style="width:72px">
              <col style="width:110px">
              <col style="width:72px">
              <col style="width:125px">
              <col style="width:72px">
              <col style="width:110px">
              <col style="width:72px">
              <col style="width:125px">
              <col style="width:72px">
              <col style="width:110px">
              <col style="width:72px">
              <col style="width:64px">
            </colgroup>
            <thead>
              <tr>
                <th style="width:62px"></th>
                <th style="width:210px"></th>
                <th style="width:112px"></th>
                <th colspan="4">Current</th>
                <th colspan="4">Change</th>
                <th colspan="4">Position as at: ${esc(baseline)}<br>if known</th>
                <th style="width:58px"></th>
              </tr>
              <tr>
                <th>Current<br>Rank</th>
                <th>Investor</th>
                <th>Processed</th>
                <th>Long incl.<br>derivs</th>
                <th>%</th>
                <th>Short</th>
                <th>%</th>
                <th>Long incl.<br>derivs</th>
                <th>%</th>
                <th>Short</th>
                <th>%</th>
                <th>Long incl.<br>derivs</th>
                <th>%</th>
                <th>Short</th>
                <th>%</th>
                <th>Initial<br>Rank</th>
              </tr>
            </thead>
            <tbody>
              ${register.rows.map((row, index) => registerRow(row, index)).join("") || `<tr><td colspan="16" class="empty">No holdings found for this target.</td></tr>`}
            </tbody>
          </table>
        </div>
        ${ownershipTypeChart(register)}
        <p style="max-width:1050px; text-align:right;"><a id="registerFilingsLink" href="#/filings">See filings for selected target</a></p>
      `;

      document.querySelector("#findRegister").addEventListener("click", () => {
        const next = document.querySelector("#registerTarget").value;
        location.hash = `#/share-register/${encodeURIComponent(next)}`;
      });
      document.querySelector("#registerTarget").addEventListener("change", (event) => {
        location.hash = `#/share-register/${encodeURIComponent(event.target.value)}`;
      });
      document.querySelector("#registerFilingsLink").addEventListener("click", () => {
        state.target = target;
        state.filer = "";
      });
    }

    function registerRow(row, index) {
      return `
        <tr>
          <td class="left">${index + 1}</td>
          <td class="left">${esc(row.investor)}</td>
          <td class="left">${esc(formatDateTime(row.processed))}</td>
          <td>${fmtNumber(row.currentLong)}</td>
          <td>${formatPercentCell(row.currentLongPct)}</td>
          <td>${fmtNumber(row.currentShort)}</td>
          <td>${formatPercentCell(row.currentShortPct)}</td>
          <td>${signedPlain(row.changeLong)}</td>
          <td>${signedPercent(row.changeLongPct)}</td>
          <td>${signedPlain(row.changeShort)}</td>
          <td>${signedPercent(row.changeShortPct)}</td>
          <td>${fmtNumber(row.initialLong)}</td>
          <td>${formatPercentCell(row.initialLongPct)}</td>
          <td>${fmtNumber(row.initialShort)}</td>
          <td>${formatPercentCell(row.initialShortPct)}</td>
          <td>${row.initialRank || ""}</td>
        </tr>
      `;
    }

    function ownershipTypeChart(register) {
      const rows = ownershipTypeRows(register.rows);
      const basis = register.shareCapital
        ? "Percentage of total share capital."
        : "Percentage of known disclosed long positions.";
      return `
        <section class="ownership-chart">
          <h2>Ownership by company type</h2>
          ${rows.map((row) => ownershipTypeBar(row)).join("")}
          <div class="table-meta">${esc(basis)}</div>
        </section>
      `;
    }

    function ownershipTypeRows(registerRows) {
      const hasKnownPercent = registerRows.some((row) => row.currentLongPct != null);
      const totalLong = registerRows.reduce((sum, row) => sum + Number(row.currentLong || 0), 0);
      return COMPANY_TYPES.map((type) => {
        const matching = registerRows.filter((row) => (row.companyType || "Unassigned") === type);
        const shares = matching.reduce((sum, row) => sum + Number(row.currentLong || 0), 0);
        const percent = hasKnownPercent
          ? matching.reduce((sum, row) => sum + Number(row.currentLongPct || 0), 0)
          : (totalLong ? shares / totalLong * 100 : 0);
        return { type, shares, percent, investors: matching.length };
      });
    }

    function ownershipTypeBar(row) {
      const width = Math.max(0, Math.min(100, Number(row.percent || 0)));
      return `
        <div class="ownership-row">
          <div class="ownership-label">${esc(row.type)}</div>
          <div class="ownership-track" title="${escAttr(row.type)}: ${escAttr(formatOwnershipPercent(row.percent))}">
            <div class="ownership-fill ${ownershipTypeClass(row.type)}" style="width:${width.toFixed(3)}%"></div>
          </div>
          <div class="ownership-value">${formatOwnershipPercent(row.percent)}</div>
        </div>
      `;
    }

    function ownershipTypeClass(type) {
      if (type === "Hedge Fund") return "hedge";
      if (type === "Institutional Investor") return "institutional";
      if (type === "Unassigned") return "unassigned";
      return "other";
    }

    function formatOwnershipPercent(value) {
      const number = Number(value || 0);
      if (!Number.isFinite(number)) return "0%";
      return `${number.toFixed(3).replace(/\.?0+$/, "")}%`;
    }

    function buildShareRegister(target) {
      const shareCapital = latestShareCapital(target, new Date().toISOString());
      const denominator = shareCapital?.total || null;
      const targetRows = transactions
        .filter((row) => row.target === target && row.filer)
        .sort((a, b) => String(rowDisplayDate(a)).localeCompare(String(rowDisplayDate(b))) || String(a.transaction_date).localeCompare(String(b.transaction_date)));
      const groupedRows = new Map();
      targetRows.forEach((row, index) => {
        const reported = rowDisplayDate(row) || "";
        const dealing = row.transaction_date || dateOnly(reported) || "";
        const filer = canonicalCompanyName(row.filer);
        const key = [filer, reported, dealing, row.amf_number || ""].join("||");
        if (!groupedRows.has(key)) {
          groupedRows.set(key, { filer, reported, dealing, index, rows: [] });
        }
        groupedRows.get(key).rows.push(row);
      });
      const groups = [...groupedRows.values()].sort((a, b) =>
        String(a.reported).localeCompare(String(b.reported)) ||
        String(a.dealing).localeCompare(String(b.dealing)) ||
        a.index - b.index
      );
      const investors = new Map();

      groups.forEach((group) => {
        const filer = group.filer;
        if (!filer) return;
        if (!investors.has(filer)) {
          investors.set(filer, {
            investor: filer,
            processed: null,
            firstDate: null,
            shareLong: null,
            derivativeLong: null,
            short: null,
            initialLong: null,
            initialShort: null,
            companyType: "Unassigned",
          });
        }
        const investor = investors.get(filer);
        investor.processed = group.reported || investor.processed;
        investor.firstDate = investor.firstDate || group.dealing || dateOnly(group.reported);
        const groupType = group.rows.map((row) => companyTypeForSource(row.filer)).find((type) => type && type !== "Unassigned")
          || group.rows.map((row) => companyTypeForSource(row.filer)).find(Boolean)
          || companyTypeForSource(filer);
        investor.companyType = groupType || investor.companyType || "Unassigned";

        // Each legal entity keeps its own latest position; entities linked by an
        // approved group (e.g. Fidera GP + Fidera Group) are added together.
        investor.entities = investor.entities || new Map();
        group.rows.forEach((row) => {
          const entityKey = registerEntityName(row.filer);
          if (!investor.entities.has(entityKey)) {
            investor.entities.set(entityKey, { shareLong: null, derivativeLong: null, short: null });
          }
          const entity = investor.entities.get(entityKey);
          const holding = parseHolding(row.resulting_holding);
          if (holding.value != null) {
            if (row.instrument_type === "Shares") {
              if (holding.kind === "short") entity.short = holding.value;
              else entity.shareLong = holding.value;
            } else if (row.instrument_type === "Derivative") {
              if (holding.kind === "short") entity.short = holding.value;
              else entity.derivativeLong = holding.value;
            }
          }
        });
        const sumEntities = (field) => {
          const values = [...investor.entities.values()].map((entity) => entity[field]).filter((value) => value != null);
          return values.length ? values.reduce((total, value) => total + Number(value), 0) : null;
        };
        investor.shareLong = sumEntities("shareLong");
        investor.derivativeLong = sumEntities("derivativeLong");
        investor.short = sumEntities("short");

        const snapshot = investorSnapshot(investor, denominator);
        if (investor.initialLong == null && (snapshot.currentLong || snapshot.currentShort)) {
          investor.initialLong = snapshot.currentLong;
          investor.initialShort = snapshot.currentShort;
        }
      });

      const rows = [...investors.values()].map((investor) => investorSnapshot(investor, denominator))
        .filter((row) => row.currentLong || row.currentShort || row.initialLong || row.initialShort)
        .sort((a, b) => (b.currentLong + b.currentShort) - (a.currentLong + a.currentShort) || a.investor.localeCompare(b.investor));

      const initialRanks = [...rows].sort((a, b) => (b.initialLong + b.initialShort) - (a.initialLong + a.initialShort));
      initialRanks.forEach((row, index) => {
        row.initialRank = index + 1;
      });

      return {
        rows,
        baselineDate: minDate(rows.map((row) => row.firstDate)),
        lastUpdated: maxDate(rows.map((row) => row.processed)),
        shareCapital,
      };
    }

    function investorSnapshot(investor, denominator = null) {
      const currentLong = Number(investor.shareLong || 0) + Number(investor.derivativeLong || 0);
      const currentShort = Number(investor.short || 0);
      const initialLong = Number(investor.initialLong || 0);
      const initialShort = Number(investor.initialShort || 0);
      return {
        investor: investor.investor,
        companyType: investor.companyType || "Unassigned",
        processed: investor.processed,
        firstDate: investor.firstDate,
        currentLong,
        currentShort,
        initialLong,
        initialShort,
        changeLong: currentLong - initialLong,
        changeShort: currentShort - initialShort,
        currentLongPct: percentOf(currentLong, denominator),
        currentShortPct: percentOf(currentShort, denominator),
        changeLongPct: percentOf(currentLong - initialLong, denominator),
        changeShortPct: percentOf(currentShort - initialShort, denominator),
        initialLongPct: percentOf(initialLong, denominator),
        initialShortPct: percentOf(initialShort, denominator),
      };
    }

    function renderOffers() {
      app.innerHTML = `
        <h1>Current Offer Periods</h1>
        <div class="table-meta">AMF offer-period list dated ${esc(DATA.offer_period_companies_from_amf_xlsx?.last_update || "")}</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Offeree</th>
                <th style="width:150px">ISIN</th>
                <th>Offeror</th>
                <th style="width:140px">Announced</th>
                <th style="width:140px">Filed</th>
              </tr>
            </thead>
            <tbody>
              ${offers.map((offer) => `
                <tr>
                  <td>${esc(offer.offeree)}</td>
                  <td>${esc(offer.isin)}</td>
                  <td>${esc(offer.offeror)}</td>
                  <td>${esc(offer.offer_announced)}</td>
                  <td>${esc(offer.draft_offer_filed)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }

    function renderEuropeFilings() {
      const allEuropeFilings = allStoredEuropeFilings();
      const localItalyCounts = localEuropeFilings.reduce((counts, row) => {
        if (row.country_code === "IT" || row.country === "Italy") counts[row.target] = (counts[row.target] || 0) + 1;
        return counts;
      }, {});
      const manualCounts = manualEuropeFilings.reduce((counts, row) => {
        counts[row.target] = (counts[row.target] || 0) + 1;
        return counts;
      }, {});
      const haystackMatch = (row) => {
        if (!state.europeSearch) return true;
        return [
          row.country,
          row.target,
          row.bidder,
          row.holder,
          row.declarant,
          row.source,
          row.label,
          row.url,
          row.notes,
          row.text,
        ].join(" ").toLowerCase().includes(state.europeSearch.toLowerCase());
      };
      const countryMatch = (row) => !state.europeCountry || row.country === state.europeCountry;
      const statusMatch = (row) => !state.europeStatus || row.status === state.europeStatus;
      const filings = allEuropeFilings.filter((row) => haystackMatch(row) && countryMatch(row));
      const checks = europeChecks
        .map((row) => localItalyCounts[row.target] ? {
          ...row,
          status: "checked",
          result_count: (Number(row.result_count) || 0) + localItalyCounts[row.target],
          notes: `Imported ${localItalyCounts[row.target]} CONSOB browser/session row${localItalyCounts[row.target] === 1 ? "" : "s"} in this browser.`,
        } : row)
        .map((row) => manualCounts[row.target] ? {
          ...row,
          status: "checked",
          result_count: (Number(row.result_count) || 0) + manualCounts[row.target],
          notes: `Manual filing row${manualCounts[row.target] === 1 ? "" : "s"} entered in this browser.`,
        } : row)
        .filter((row) => haystackMatch(row) && countryMatch(row) && statusMatch(row));
      const routeChecks = europeRouteChecks.filter((row) => haystackMatch(row) && countryMatch(row) && statusMatch(row));
      const targets = europeAlertTargets.filter((row) => haystackMatch(row) && countryMatch(row));
      const countries = unique(europeAlertTargets.map((row) => row.country));
      const statuses = unique([
        ...europeChecks.map((row) => row.status),
        ...europeRouteChecks.map((row) => row.status),
      ]);
      const awaitingCount = europeChecks.filter((row) => row.status === "requires_browser_capture" || row.status === "awaiting_import" || row.status === "manual_alert").length;
      const localImportCount = localEuropeFilings.filter((row) => row.country === "Italy" || row.country_code === "IT").length;
      const targetSource = europeSourceLink();

      app.innerHTML = `
        <div class="content-top">
          <div>
            <h1>Europe Regulatory Filings</h1>
            <div class="muted">Non-France offer-period filing watchlist and manually entered disclosures</div>
          </div>
          <div class="stats">
            <div><span>Offer targets:</span><strong>${europeAlertTargets.length}</strong></div>
            <div><span>Imported filings:</span><strong>${allEuropeFilings.length}</strong></div>
            <div><span>CONSOB captured:</span><strong>${localImportCount}</strong></div>
            <div><span>Manual filings:</span><strong>${manualEuropeFilings.length}</strong></div>
            <div><span>Manual alert mode:</span><strong>${awaitingCount}</strong></div>
            <div><span>Last generated:</span><strong>${formatDateTime(europe.generated_at, true)}</strong></div>
          </div>
        </div>
        <p class="summary-note">
          Current target universe is taken from ${targetSource}.
          Filing rows below combine any official imported rows with your manually entered non-France filings.
        </p>
        <p class="summary-note">
          <a class="button-secondary" href="#/europe-alerts">Open alert desk</a>
          <a class="button-secondary" href="#/europe-manual">Add manual filing</a>
        </p>
        <div class="toolbar europe-toolbar">
          <label>Search<input id="europeSearch" type="search" value="${escAttr(state.europeSearch)}" placeholder="Target, bidder, holder"></label>
          <label>Country<select id="europeCountry">${options("All countries", countries, state.europeCountry)}</select></label>
          <label>Source status<select id="europeStatus">${options("All statuses", statuses, state.europeStatus, sourceStatusLabels())}</select></label>
          <button id="resetEurope" type="button">Reset</button>
        </div>
        <h2>Official and manual filings</h2>
        <div class="table-meta">${filings.length} filing rows shown</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:90px">Country</th>
                <th style="width:130px">Published</th>
                <th>Target</th>
                <th>Holder / declarant</th>
                <th>Filing / holding</th>
                <th style="width:150px">Type</th>
                <th style="width:170px">Source</th>
              </tr>
            </thead>
            <tbody>
              ${filings.map(europeFilingRow).join("") || `<tr><td colspan="7" class="empty">No filing rows imported or entered yet. See the source-check table below.</td></tr>`}
            </tbody>
          </table>
        </div>
        <h2 style="margin-top:24px">Import CONSOB text</h2>
        <section class="panel">
          <p class="muted">Open CONSOB in your normal browser session, search or filter for a company, then capture or save the accepted page. The route-probe table below is diagnostic only; rows are imported from the accepted browser page.</p>
          <textarea id="consobImportText" placeholder="Paste CONSOB major-shareholding list or notice text here"></textarea>
          <div style="margin-top:8px; display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <a class="button-secondary" href="${escAttr(CONSOB_MAJOR_SHAREHOLDINGS_URL)}" target="_blank">Open CONSOB list</a>
            <a class="button-secondary" href="${escAttr(consobCaptureBookmarklet())}" title="Drag this to your bookmarks bar, then click it on a CONSOB page">CONSOB capture</a>
            <button id="copyConsobCapture" type="button">Copy capture link</button>
            <label class="import-file">Import saved CONSOB page<input id="consobFileImport" type="file" accept=".html,.htm,.txt"></label>
            <button class="button-primary" id="importConsobText" type="button">Import CONSOB rows</button>
            <button id="clearConsobRows" type="button">Clear pasted CONSOB rows</button>
            <span class="muted">${esc(state.europeImportMessage)}</span>
          </div>
        </section>
        <h2 style="margin-top:24px">CONSOB route probes</h2>
        <div class="table-meta">${routeChecks.length} official routes checked</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Route</th>
                <th style="width:150px">Status</th>
                <th style="width:90px">HTTP</th>
                <th>Useful content</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              ${routeChecks.map(routeCheckRow).join("") || `<tr><td colspan="5" class="empty">No CONSOB route checks match these filters.</td></tr>`}
            </tbody>
          </table>
        </div>
        <h2 style="margin-top:24px">Regulatory source checks</h2>
        <div class="table-meta">${checks.length} source checks shown</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:90px">Country</th>
                <th>Target</th>
                <th style="width:150px">Source</th>
                <th style="width:130px">Status</th>
                <th style="width:90px">Results</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              ${checks.map(sourceCheckRow).join("") || `<tr><td colspan="6" class="empty">No source checks match these filters.</td></tr>`}
            </tbody>
          </table>
        </div>
        <h2 style="margin-top:24px">Current non-France offer targets</h2>
        <div class="table-meta">${targets.length} monitored targets shown</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:90px">Country</th>
                <th>Target</th>
                <th>Bidder</th>
                <th style="width:130px">Deal type</th>
                <th style="width:140px">Announced</th>
                <th style="width:150px">Expected completion</th>
              </tr>
            </thead>
            <tbody>
              ${targets.map(europeTargetRow).join("") || `<tr><td colspan="6" class="empty">No monitored targets match these filters.</td></tr>`}
            </tbody>
          </table>
        </div>
        <h2 style="margin-top:24px">Arbinsight updates</h2>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:90px">Country</th>
                <th style="width:130px">Date</th>
                <th style="width:230px">Target</th>
                <th>Update</th>
              </tr>
            </thead>
            <tbody>
              ${europeUpdates.filter((row) => haystackMatch(row) && countryMatch(row)).map(europeUpdateRow).join("") || `<tr><td colspan="4" class="empty">No updates match these filters.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;
      bindEuropeControls();
    }

    function renderEuropeAlertDesk() {
      const allEuropeFilings = allStoredEuropeFilings();
      const countries = unique(europeAlertTargets.map((row) => row.country));
      const haystackMatch = (row) => {
        if (!state.europeSearch) return true;
        return [row.country, row.target, row.bidder, row.source, row.notes].join(" ").toLowerCase().includes(state.europeSearch.toLowerCase());
      };
      const countryMatch = (row) => !state.europeCountry || row.country === state.europeCountry;
      const targets = europeAlertTargets.filter((row) => haystackMatch(row) && countryMatch(row));
      const targetCountWithFilings = new Set(allEuropeFilings.map((row) => normaliseCompanyKey(row.target))).size;

      app.innerHTML = `
        <div class="content-top">
          <div>
            <h1>Europe Alert Desk</h1>
            <div class="muted">Manual monitoring queue for non-France offer-period companies</div>
          </div>
          <div class="stats">
            <div><span>Companies:</span><strong>${europeAlertTargets.length}</strong></div>
            <div><span>Countries:</span><strong>${countries.length}</strong></div>
            <div><span>Manual filings:</span><strong>${manualEuropeFilings.length}</strong></div>
            <div><span>Targets with filings:</span><strong>${targetCountWithFilings}</strong></div>
          </div>
        </div>
        <section class="panel" style="margin-bottom:18px">
          <div class="manual-form">
            <label>Alert email<input id="europeAlertEmail" type="email" value="${escAttr(europeAlertSettings.email || "")}" placeholder="name@example.com"></label>
            <label>Search<input id="europeSearch" type="search" value="${escAttr(state.europeSearch)}" placeholder="Target, bidder, country"></label>
            <label>Country<select id="europeCountry">${options("All countries", countries, state.europeCountry)}</select></label>
            <button class="button-primary" id="saveEuropeAlertSettings" type="button">Save alert email</button>
          </div>
        </section>
        <h2>Monitored offer targets</h2>
        <div class="table-meta">${targets.length} monitored targets shown</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:90px">Country</th>
                <th>Target</th>
                <th>Bidder</th>
                <th style="width:190px">Regulatory source</th>
                <th style="width:150px">Last filing</th>
                <th style="width:90px">Rows</th>
                <th style="width:210px">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${targets.map(europeAlertTargetRow).join("") || `<tr><td colspan="7" class="empty">No monitored targets match these filters.</td></tr>`}
            </tbody>
          </table>
        </div>
        <h2 style="margin-top:24px">Recent manual filings</h2>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:90px">Country</th>
                <th style="width:120px">Published</th>
                <th>Target</th>
                <th>Holder / declarant</th>
                <th>Filing / holding</th>
                <th style="width:150px">Type</th>
                <th style="width:80px"></th>
              </tr>
            </thead>
            <tbody>
              ${manualEuropeFilings.slice().reverse().map(manualEuropeFilingRow).join("") || `<tr><td colspan="7" class="empty">No manual filings have been entered yet.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;
      bindEuropeAlertDeskControls();
    }

    function renderEuropeManualFiling(routeTarget = "") {
      const selected = routeTarget ? findEuropeTargetByName(routeTarget) : (europeAlertTargets[0] || null);
      const selectedValue = selected ? europeTargetOptionValue(selected) : "";
      const selectedSource = selected ? sourceForEuropeTarget(selected) : {};
      const countries = unique(europeAlertTargets.map((row) => row.country));

      app.innerHTML = `
        <div class="content-top">
          <div>
            <h1>Manual Filing Input</h1>
            <div class="muted">Enter non-France filings after receiving an alert or checking the regulator page</div>
          </div>
          <div class="stats">
            <div><span>Manual filings:</span><strong>${manualEuropeFilings.length}</strong></div>
            <div><span>Countries:</span><strong>${countries.length}</strong></div>
          </div>
        </div>
        <section class="panel">
          <div class="manual-form">
            <label class="wide">Target<select id="manualEuropeTarget">${europeAlertTargets.map((row) => `<option value="${escAttr(europeTargetOptionValue(row))}" ${europeTargetOptionValue(row) === selectedValue ? "selected" : ""}>${esc(row.country)} - ${esc(row.target)}${row.bidder ? ` / ${esc(row.bidder)}` : ""}</option>`).join("")}</select></label>
            <label>Published date<input id="manualEuropePublished" type="date"></label>
            <label>Holder / declarant<input id="manualEuropeHolder" type="text" placeholder="Investor or declarant"></label>
            <label>% held<input id="manualEuropePercent" type="text" placeholder="e.g. 5.021"></label>
            <label>Filing type<select id="manualEuropeType">
              <option>Major shareholding</option>
              <option>Voting rights notification</option>
              <option>Short position</option>
              <option>Offer-period dealing</option>
              <option>Other</option>
            </select></label>
            <label>Source URL<input id="manualEuropeSourceUrl" type="url" value="${escAttr(selectedSource.source_url || "")}" placeholder="https://"></label>
            <label class="wide">Filing / holding text<input id="manualEuropeTitle" type="text" placeholder="e.g. Major shareholding: 5.021%"></label>
            <label class="wide">Notes<textarea id="manualEuropeNotes" placeholder="Paste the short source line or any notes here"></textarea></label>
            <button class="button-primary" id="saveManualEuropeFiling" type="button">Save filing</button>
            <a class="button-secondary" href="#/europe-alerts">Back to alert desk</a>
            <a class="button-secondary" href="${escAttr(selectedSource.source_url || "#/europe-alerts")}" target="_blank">Open source</a>
          </div>
          <p class="muted" style="margin-top:10px">${esc(state.europeManualMessage || (selectedSource.source ? `Source: ${selectedSource.source}. ${selectedSource.disclosure_type || ""}` : ""))}</p>
        </section>
        <h2 style="margin-top:24px">Recent manual filings</h2>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th style="width:90px">Country</th>
                <th style="width:120px">Published</th>
                <th>Target</th>
                <th>Holder / declarant</th>
                <th>Filing / holding</th>
                <th style="width:150px">Type</th>
                <th style="width:80px"></th>
              </tr>
            </thead>
            <tbody>
              ${manualEuropeFilings.slice().reverse().map(manualEuropeFilingRow).join("") || `<tr><td colspan="7" class="empty">No manual filings have been entered yet.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;
      bindEuropeManualControls();
    }

    function europeAlertTargetRow(row) {
      const filings = allStoredEuropeFilings().filter((filing) => normaliseCompanyKey(filing.target) === normaliseCompanyKey(row.target));
      const latest = filings.slice().sort((a, b) => String(b.published_date || "").localeCompare(String(a.published_date || "")))[0] || {};
      const source = sourceForEuropeTarget(row);
      return `
        <tr>
          <td>${esc(row.country)}</td>
          <td>${esc(row.target)}</td>
          <td>${esc(row.bidder)}</td>
          <td>${source.source_url ? `<a href="${escAttr(source.source_url)}" target="_blank">${esc(source.source || "")}</a>` : esc(source.source || "")}<br><span class="muted">${esc(source.disclosure_type || "")}</span></td>
          <td>${esc(latest.published_date || "")}${latest.holder ? `<br><span class="muted">${esc(latest.holder)}</span>` : ""}</td>
          <td>${filings.length}</td>
          <td>
            <a class="button-secondary" href="${escAttr(mailtoForEuropeTarget(row))}">Email template</a>
            <a class="button-secondary" href="#/europe-manual/${encodeURIComponent(row.target)}">Add filing</a>
          </td>
        </tr>
      `;
    }

    function manualEuropeFilingRow(row) {
      return `
        <tr>
          <td>${esc(row.country)}</td>
          <td>${esc(row.published_date || "")}</td>
          <td>${esc(row.target)}</td>
          <td>${esc(row.holder || row.declarant || "")}</td>
          <td>${esc(row.title || row.holding || row.details || "")}</td>
          <td>${esc(row.instrument_type || row.filing_type || "")}</td>
          <td><button type="button" data-delete-manual-europe="${escAttr(row.import_key || "")}">Delete</button></td>
        </tr>
      `;
    }

    function allStoredEuropeFilings() {
      return [...europeFilings, ...localEuropeFilings, ...manualEuropeFilings];
    }

    function europeSourceLink() {
      const source = europe.current_targets_source || "";
      const label = europe.current_targets_source_label || "European public tracker workbook";
      if (/^https?:\/\//i.test(source)) {
        return `<a href="${escAttr(source)}" target="_blank">${esc(label)}</a>`;
      }
      return esc(label);
    }

    function sourceForEuropeTarget(target) {
      return europeSources.find((row) => row.country_code === target.country_code || row.country === target.country) || {};
    }

    function europeTargetOptionValue(row) {
      return `${row.country_code || row.country}||${row.target}`;
    }

    function findEuropeTargetByValue(value) {
      return europeAlertTargets.find((row) => europeTargetOptionValue(row) === value) || null;
    }

    function findEuropeTargetByName(value) {
      const key = normaliseCompanyKey(value);
      return europeAlertTargets.find((row) => normaliseCompanyKey(row.target) === key) || null;
    }

    function mailtoForEuropeTarget(row) {
      const source = sourceForEuropeTarget(row);
      const subject = `Disclosure alert check: ${row.target}`;
      const body = [
        `Please check for new public-offer disclosure filings.`,
        ``,
        `Target: ${row.target}`,
        `Country: ${row.country}`,
        `Bidder: ${row.bidder || ""}`,
        `Source: ${source.source || ""}`,
        `Disclosure type: ${source.disclosure_type || ""}`,
        `Source URL: ${source.source_url || ""}`,
        ``,
        `If a new filing is found, enter it in the Europe Manual Filing Input screen.`,
      ].join("\n");
      const to = europeAlertSettings.email || "";
      return `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    }

    function europeFilingRow(row) {
      const sourceUrl = row.source_url || "";
      return `
        <tr>
          <td>${esc(row.country)}</td>
          <td>${esc(row.published_date || row.date || "")}</td>
          <td>${esc(row.target)}</td>
          <td>${esc(row.holder || row.declarant || row.company_dealing || "")}</td>
          <td>${esc(row.title || row.details || (row.percentage != null ? `${row.percentage}%` : row.holding || ""))}${row.isin ? `<br><span class="muted">${esc(row.isin)}</span>` : ""}</td>
          <td>${esc(row.instrument_type || row.filing_type || "")}</td>
          <td>${sourceUrl ? `<a href="${escAttr(sourceUrl)}" target="_blank">${esc(row.source || "Open source")}</a>` : esc(row.source || "")}</td>
        </tr>
      `;
    }

    function sourceCheckRow(row) {
      return `
        <tr>
          <td>${esc(row.country)}</td>
          <td>${esc(row.target)}</td>
          <td>${row.source_url ? `<a href="${escAttr(row.source_url)}" target="_blank">${esc(row.source)}</a>` : esc(row.source)}</td>
          <td>${sourceStatus(row.status)}</td>
          <td>${row.result_count == null ? "" : fmtNumber(row.result_count)}</td>
          <td>${esc(row.notes)}</td>
        </tr>
      `;
    }

    function routeCheckRow(row) {
      const url = row.url || row.final_url || "";
      const detail = row.raw_status === "automated_intercept" ? "Automated access cannot read this accepted browser session." : (row.location || row.response_title || "");
      return `
        <tr>
          <td>${url ? `<a href="${escAttr(url)}" target="_blank">${esc(row.label || row.kind || "CONSOB route")}</a>` : esc(row.label || row.kind || "CONSOB route")}</td>
          <td>${sourceStatus(row.status)}</td>
          <td>${row.http_status == null ? "" : esc(row.http_status)}</td>
          <td>${row.has_useful_content ? "Yes" : "No"}</td>
          <td>${esc(row.notes || "")}${detail ? `<br><span class="muted">${esc(detail)}</span>` : ""}</td>
        </tr>
      `;
    }

    function europeTargetRow(row) {
      return `
        <tr>
          <td>${esc(row.country)}</td>
          <td>${esc(row.target)}</td>
          <td>${esc(row.bidder)}</td>
          <td>${esc(row.deal_type)}</td>
          <td>${esc(row.announced)}</td>
          <td>${esc(row.expected_completion)}</td>
        </tr>
      `;
    }

    function europeUpdateRow(row) {
      return `
        <tr>
          <td>${esc(row.country)}</td>
          <td>${esc(row.date)}</td>
          <td>${esc(row.target)}</td>
          <td>${esc(row.text)}</td>
        </tr>
      `;
    }

    function bindEuropeControls() {
      ["europeSearch", "europeCountry", "europeStatus"].forEach((id) => {
        document.querySelector(`#${id}`).addEventListener("input", (event) => {
          state[id] = event.target.value;
          renderEuropeFilings();
        });
      });
      document.querySelector("#resetEurope").addEventListener("click", () => {
        Object.assign(state, { europeSearch: "", europeCountry: "", europeStatus: "" });
        renderEuropeFilings();
      });
      document.querySelector("#importConsobText").addEventListener("click", () => {
        const text = document.querySelector("#consobImportText").value;
        importConsobRows(text);
      });
      document.querySelector("#copyConsobCapture").addEventListener("click", async () => {
        const link = consobCaptureBookmarklet();
        try {
          if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error("Clipboard unavailable");
          await navigator.clipboard.writeText(link);
          state.europeImportMessage = "CONSOB capture link copied. Add it as a browser bookmark, then use it on the accepted CONSOB page.";
        } catch {
          document.querySelector("#consobImportText").value = link;
          state.europeImportMessage = "Capture link placed in the text box; copy it into a browser bookmark.";
        }
        renderEuropeFilings();
      });
      document.querySelector("#consobFileImport").addEventListener("change", async (event) => {
        const file = event.target.files && event.target.files[0];
        if (!file) return;
        try {
          const text = await file.text();
          importConsobRows(text);
        } catch {
          state.europeImportMessage = "Could not read that CONSOB file.";
          renderEuropeFilings();
        }
      });
      document.querySelector("#clearConsobRows").addEventListener("click", () => {
        localEuropeFilings.length = 0;
        saveLocalEuropeFilings();
        state.europeImportMessage = "Cleared pasted CONSOB rows.";
        renderEuropeFilings();
      });
    }

    function bindEuropeAlertDeskControls() {
      ["europeSearch", "europeCountry"].forEach((id) => {
        document.querySelector(`#${id}`)?.addEventListener("input", (event) => {
          state[id] = event.target.value;
          renderEuropeAlertDesk();
        });
      });
      document.querySelector("#saveEuropeAlertSettings")?.addEventListener("click", () => {
        europeAlertSettings.email = document.querySelector("#europeAlertEmail").value.trim();
        saveEuropeAlertSettings();
        state.europeManualMessage = "Alert email saved.";
        renderEuropeAlertDesk();
      });
      bindManualEuropeDeleteButtons(renderEuropeAlertDesk);
    }

    function bindEuropeManualControls() {
      document.querySelector("#manualEuropeTarget")?.addEventListener("change", (event) => {
        const row = findEuropeTargetByValue(event.target.value);
        if (!row) return;
        location.hash = `#/europe-manual/${encodeURIComponent(row.target)}`;
      });
      document.querySelector("#saveManualEuropeFiling")?.addEventListener("click", () => {
        const target = findEuropeTargetByValue(document.querySelector("#manualEuropeTarget").value);
        if (!target) {
          state.europeManualMessage = "Choose a monitored target first.";
          renderEuropeManualFiling();
          return;
        }
        const source = sourceForEuropeTarget(target);
        const holder = document.querySelector("#manualEuropeHolder").value.trim();
        const published = document.querySelector("#manualEuropePublished").value;
        const percentageText = document.querySelector("#manualEuropePercent").value.trim().replace(",", ".");
        const percentage = percentageText ? Number(percentageText) : null;
        const filingType = document.querySelector("#manualEuropeType").value;
        const sourceUrl = document.querySelector("#manualEuropeSourceUrl").value.trim() || source.source_url || "";
        const title = document.querySelector("#manualEuropeTitle").value.trim();
        const notes = document.querySelector("#manualEuropeNotes").value.trim();
        const importKey = [
          "manual",
          target.country_code || target.country,
          target.target,
          published,
          holder,
          title || percentageText,
          Date.now(),
        ].join("|");
        manualEuropeFilings.push({
          import_key: importKey,
          country: target.country,
          country_code: target.country_code,
          target: target.target,
          bidder: target.bidder || "",
          published_date: published,
          transaction_date: "",
          holder,
          declarant: holder,
          holding: percentageText ? `${percentageText}%` : "",
          percentage: Number.isFinite(percentage) ? percentage : null,
          filing_type: filingType,
          instrument_type: filingType,
          title: title || (percentageText ? `${filingType}: ${percentageText}%` : filingType),
          details: notes,
          source: source.source ? `${source.source} manual entry` : "Manual entry",
          source_url: sourceUrl,
          entry_mode: "manual",
          created_at: new Date().toISOString(),
        });
        saveManualEuropeFilings();
        state.europeManualMessage = `Saved manual filing for ${target.target}.`;
        state.europeImportMessage = state.europeManualMessage;
        renderEuropeManualFiling(target.target);
      });
      bindManualEuropeDeleteButtons(() => renderEuropeManualFiling());
    }

    function bindManualEuropeDeleteButtons(afterDelete) {
      document.querySelectorAll("[data-delete-manual-europe]").forEach((button) => {
        button.addEventListener("click", () => {
          const key = button.getAttribute("data-delete-manual-europe");
          const index = manualEuropeFilings.findIndex((row) => row.import_key === key);
          if (index >= 0) {
            manualEuropeFilings.splice(index, 1);
            saveManualEuropeFilings();
            state.europeManualMessage = "Manual filing deleted.";
          }
          afterDelete();
        });
      });
    }

    function importConsobRows(text) {
      if (looksLikeRadware(text)) {
        state.europeImportMessage = "That file is the CAPTCHA/intercept page. Open CONSOB normally, then use CONSOB capture or save the accepted page.";
        renderEuropeFilings();
        return;
      }
      const rows = parseConsobImport(text);
      const existing = new Set(localEuropeFilings.map((row) => row.import_key));
      const fresh = rows.filter((row) => !existing.has(row.import_key));
      localEuropeFilings.push(...fresh);
      saveLocalEuropeFilings();
      state.europeCountry = fresh.length ? "Italy" : state.europeCountry;
      state.europeImportMessage = fresh.length
        ? `Imported ${fresh.length} CONSOB row${fresh.length === 1 ? "" : "s"}.`
        : "No new matching Italian offer-target rows found.";
      renderEuropeFilings();
    }

    function looksLikeRadware(text) {
      return /Radware Captcha Page|captcha\.perfdrive\.com|validate\.perfdrive\.com|botmanager_support@radware\.com/i.test(String(text || ""));
    }

    function loadLocalEuropeFilings() {
      try {
        const raw = typeof localStorage === "undefined" ? "[]" : localStorage.getItem(EUROPE_FILINGS_STORAGE_KEY) || "[]";
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }

    function saveLocalEuropeFilings() {
      if (typeof localStorage === "undefined") return;
      localStorage.setItem(EUROPE_FILINGS_STORAGE_KEY, JSON.stringify(localEuropeFilings));
    }

    function loadManualEuropeFilings() {
      try {
        const raw = typeof localStorage === "undefined" ? "[]" : localStorage.getItem(EUROPE_MANUAL_FILINGS_STORAGE_KEY) || "[]";
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }

    function saveManualEuropeFilings() {
      if (typeof localStorage === "undefined") return;
      localStorage.setItem(EUROPE_MANUAL_FILINGS_STORAGE_KEY, JSON.stringify(manualEuropeFilings));
    }

    function loadEuropeAlertSettings() {
      try {
        const raw = typeof localStorage === "undefined" ? "{}" : localStorage.getItem(EUROPE_ALERT_SETTINGS_STORAGE_KEY) || "{}";
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch {
        return {};
      }
    }

    function saveEuropeAlertSettings() {
      if (typeof localStorage === "undefined") return;
      localStorage.setItem(EUROPE_ALERT_SETTINGS_STORAGE_KEY, JSON.stringify(europeAlertSettings));
    }

    function consobCaptureBookmarklet() {
      const code = `(() => {
        const text = document.body ? document.body.innerText : "";
        const done = () => alert("CONSOB page text copied. Return to the tracker and paste/import it.");
        const fallback = () => {
          const area = document.createElement("textarea");
          area.value = text;
          area.style.position = "fixed";
          area.style.left = "-9999px";
          document.body.appendChild(area);
          area.select();
          document.execCommand("copy");
          area.remove();
          done();
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done).catch(fallback);
        } else {
          fallback();
        }
      })();`;
      return `javascript:${encodeURIComponent(code)}`;
    }

    function parseConsobImport(text) {
      const sourceText = normaliseConsobImportText(text);
      const published = sourceText.match(/PUBLISHED ON\s+(\d{2}\/\d{2}\/\d{4})/i)?.[1] || "";
      const italyTargets = europeTargets.filter((target) => target.country_code === "IT");
      const rows = [];
      const seen = new Set();
      let section = "";
      const lines = sourceText.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      const candidates = [];

      lines.forEach((line, index) => {
        const upper = line.toUpperCase();
        if (upper.includes("HOLDINGS IN SHARES")) section = "Shares";
        if (upper.includes("INVESTMENTS IN FINANCIAL INSTRUMENTS")) section = "Financial instruments";
        candidates.push({ line, section });
        if (findConsobTarget(line, italyTargets) && !/(\d+(?:[.,]\d+)?)\s*%/.test(line)) {
          candidates.push({
            line: lines.slice(Math.max(0, index - 4), index + 9).join(" "),
            section,
          });
        }
      });

      candidates.forEach(({ line, section }) => {
        const parsed = parseConsobCandidate(line, section, published, italyTargets);
        if (!parsed || seen.has(parsed.import_key)) return;
        seen.add(parsed.import_key);
        rows.push(parsed);
      });
      return rows;
    }

    function normaliseConsobImportText(text) {
      return String(text || "")
        .replace(/<\s*(br|\/p|\/div|\/tr|\/li|h[1-6]|\/h[1-6])\b[^>]*>/gi, "\n")
        .replace(/<[^>]+>/g, " ")
        .replace(/&nbsp;/gi, " ")
        .replace(/&amp;/gi, "&")
        .replace(/&quot;/gi, '"')
        .replace(/&#39;|&apos;/gi, "'")
        .replace(/\u00a0/g, " ");
    }

    function parseConsobCandidate(line, section, published, italyTargets) {
      const targetMatch = findConsobTarget(line, italyTargets);
      const percentage = line.match(/(\d+(?:[.,]\d+)?)\s*%/);
      if (!targetMatch || !percentage) return null;

      const afterTargetStart = targetMatch.index + targetMatch.variant.length;
      const beforeTarget = line.slice(0, targetMatch.index).trim();
      const details = line.slice(afterTargetStart).trim();
      const dateMatch = line.match(/\b(\d{2}\/\d{2}\/\d{4})\b/);
      const transactionDate = dateMatch ? dateMatch[1] : "";
      const datePrefix = beforeTarget.match(/^(\d{2}\/\d{2}\/\d{4})\s+(.*)$/);
      const afterBeforePercent = line.slice(
        afterTargetStart,
        percentage.index > afterTargetStart ? percentage.index : afterTargetStart
      ).trim();
      let declarant = datePrefix ? datePrefix[2].trim() : cleanConsobHolder(afterBeforePercent) || cleanConsobHolder(beforeTarget);
      if (!declarant || declarant.length < 2) declarant = "Unknown";

      const holding = `${percentage[1].replace(",", ".")}%`;
      const sectionLabel = section || "Major shareholding";
      const publishedDate = published || "";
      const importKey = [
        "CONSOB",
        targetMatch.target.target,
        publishedDate,
        transactionDate,
        declarant,
        holding,
        sectionLabel,
      ].join("|");

      return {
        import_key: importKey,
        country: "Italy",
        country_code: "IT",
        target: targetMatch.target.target,
        bidder: targetMatch.target.bidder || "",
        published_date: publishedDate,
        transaction_date: transactionDate,
        holder: declarant,
        declarant,
        holding,
        percentage: Number(percentage[1].replace(",", ".")),
        filing_type: "Major shareholding",
        instrument_type: sectionLabel,
        title: `${sectionLabel}: ${holding}`,
        details,
        source: "CONSOB browser/session import",
        source_url: CONSOB_MAJOR_SHAREHOLDINGS_URL,
      };
    }

    function cleanConsobHolder(value) {
      return String(value || "")
        .replace(/\b(ISSUER|INVESTEE COMPANY|LISTED COMPANY|SHAREHOLDER|DECLARANT|HOLDER|PERCENTAGE|VOTING RIGHTS|DIRECT|INDIRECT)\b:?/gi, " ")
        .replace(/\s+/g, " ")
        .replace(/^[^A-Z0-9]+|[^A-Z0-9.]+$/gi, "")
        .trim();
    }

    function findConsobTarget(line, targets) {
      const upper = line.toUpperCase();
      const variants = targets.flatMap((target) =>
        consobTargetVariants(target.target).map((variant) => ({ target, variant }))
      ).sort((a, b) => b.variant.length - a.variant.length);
      for (const item of variants) {
        const index = upper.indexOf(item.variant);
        if (index >= 0) return { ...item, index };
      }
      return null;
    }

    function consobTargetVariants(target) {
      const cleanTarget = String(target || "").toUpperCase().replace(/\([^)]*\)/g, " ").replace(/\s+/g, " ").trim();
      const base = cleanTarget
        .replace(/\bS\.?P\.?A\.?\b/g, "")
        .replace(/\bN\.?V\.?\b/g, "")
        .replace(/\bSA\b/g, "")
        .replace(/\s+/g, " ")
        .trim();
      return unique([
        cleanTarget,
        `${cleanTarget} SPA`,
        `${cleanTarget} S.P.A.`,
        base,
        `${base} SPA`,
        `${base} S.P.A.`,
      ].filter((value) => value.length > 3));
    }

    function sourceStatusLabels() {
      return {
        awaiting_import: "Awaiting import",
        blocked: "Blocked",
        checked: "Checked",
        manual_alert: "Manual alert mode",
        no_results: "No results",
        not_checked: "Not checked",
        requires_browser_capture: "Requires browser capture",
        automated_intercept: "Browser capture needed",
        "requires session": "Requires session",
        works: "Works",
        "not found": "Not found",
      };
    }

    function sourceStatus(status) {
      const labels = sourceStatusLabels();
      const className = status === "blocked" || status === "awaiting_import" || status === "requires_browser_capture" || status === "automated_intercept" || status === "requires session"
        ? "blocked"
        : status === "no_results" || status === "not found" || status === "not_checked" || status === "manual_alert"
          ? "no-results"
          : "ok";
      return `<span class="status ${className}">${esc(labels[status] || status || "Unknown")}</span>`;
    }

    function signedQuantity(row, qty) {
      const operation = String(row.operation || "").toLowerCase();
      if (row.operation_type === "sell" || row.operation_type === "transfer_out" || row.operation_type === "loan_setup") return -qty;
      if (row.operation_type === "other" && operation.includes("apport")) return -qty;
      if (row.operation_type === "buy" || row.operation_type === "transfer_in" || row.operation_type === "loan_return") return qty;
      if (row.operation_type === "legacy_position") return 0;
      if (row.operation_type === "derivative_position") {
        if (operation.includes("réduction") || operation.includes("reduction")) return -qty;
        if (operation.includes("decrease")) return -qty;
        if (operation.includes("accroissement")) return qty;
        if (operation.includes("increase")) return qty;
      }
      return qty;
    }

    function parseHolding(value) {
      const text = String(value || "").replace(/\u00a0/g, " ").replace(/[−–—]/g, "-");
      const match = text.match(/(-)?\s*([0-9][0-9 .,]*)/);
      if (!match) return { kind: null, value: null };
      const valueNumber = Number(match[2].replace(/[ .,\u00a0]/g, ""));
      if (!Number.isFinite(valueNumber)) return { kind: null, value: null };
      return { kind: match[1] ? "short" : "long", value: valueNumber };
    }

    function bindGlobalClicks() {
      window.addEventListener("hashchange", render);
    }

    function setSort(key) {
      if (state.sortKey === key) state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      else {
        state.sortKey = key;
        state.sortDir = "asc";
      }
    }

    function compareBy(key, direction) {
      return (a, b) => {
        const left = a[key] ?? "";
        const right = b[key] ?? "";
        const result = String(left).localeCompare(String(right), undefined, { numeric: true });
        return direction === "asc" ? result : -result;
      };
    }

    function options(label, values, selected, labels = {}) {
      return `<option value="">${esc(label)}</option>` + values.map((value) =>
        `<option value="${escAttr(value)}" ${value === selected ? "selected" : ""}>${esc(labels[value] || value)}</option>`
      ).join("");
    }

    function unique(values) {
      return [...new Set(values.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b)));
    }

    function normaliseCompanyKey(value) {
      return String(value || "").replace(/\s+/g, " ").trim().toUpperCase();
    }

    function loadCompanyLinks() {
      try {
        const raw = typeof localStorage === "undefined" ? "[]" : localStorage.getItem(COMPANY_LINKS_STORAGE_KEY) || "[]";
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed)
          ? parsed.map((entry) => ({
              sourceName: String(entry.sourceName || "").trim(),
              sharedName: String(entry.sharedName || entry.sourceName || "").trim(),
              type: COMPANY_TYPES.includes(entry.type) ? entry.type : "Unassigned",
            })).filter((entry) => entry.sourceName && entry.sharedName)
          : [];
      } catch {
        return [];
      }
    }

    function saveCompanyLinks() {
      if (typeof localStorage === "undefined") return;
      localStorage.setItem(COMPANY_LINKS_STORAGE_KEY, JSON.stringify(companyLinks));
    }

    // Links saved in the site data (pipeline/state/company_links.json) apply for
    // everyone; links saved with the Save button in this browser override them.
    const serverCompanyLinks = (DATA.company_links || []).map((entry) => ({
      sourceName: String(entry.sourceName || "").trim(),
      sharedName: String(entry.sharedName || entry.sourceName || "").trim(),
      type: "Unassigned",
      rule: entry.rule || "auto",
    })).filter((entry) => entry.sourceName && entry.sharedName);
    const REJECTED_LINKS_STORAGE_KEY = "frenchOpaRejectedCompanyLinks";

    function companyLinkForSource(sourceName) {
      const key = normaliseCompanyKey(sourceName);
      return companyLinks.find((entry) => normaliseCompanyKey(entry.sourceName) === key)
        || serverCompanyLinks.find((entry) => normaliseCompanyKey(entry.sourceName) === key)
        || null;
    }

    // Name used to keep separate legal entities apart inside one register row:
    // spelling variants count as one filer (latest filing wins); names in an
    // approved group marked "separate entities" (e.g. Fidera GP + Fidera Group)
    // each keep their own position and are added together.
    function registerEntityName(sourceName) {
      const key = normaliseCompanyKey(sourceName);
      const server = serverCompanyLinks.find((entry) => normaliseCompanyKey(entry.sourceName) === key);
      if (server && server.rule === "approved (separate entities)") return sourceName;
      return canonicalCompanyName(sourceName);
    }

    function companyLinkRule(sourceName) {
      const key = normaliseCompanyKey(sourceName);
      if (companyLinks.some((entry) => normaliseCompanyKey(entry.sourceName) === key)) return "Saved in this browser";
      const server = serverCompanyLinks.find((entry) => normaliseCompanyKey(entry.sourceName) === key);
      if (!server) return "";
      if (server.rule === "approved (separate entities)") return "Approved (separate entities, positions added)";
      return server.rule === "approved" ? "Approved" : `Auto: ${server.rule}`;
    }

    function loadRejectedLinks() {
      try {
        const parsed = JSON.parse(localStorage.getItem(REJECTED_LINKS_STORAGE_KEY) || "[]");
        return Array.isArray(parsed) ? parsed.filter((pair) => Array.isArray(pair) && pair.length === 2) : [];
      } catch {
        return [];
      }
    }

    function saveRejectedLinks(pairs) {
      try { localStorage.setItem(REJECTED_LINKS_STORAGE_KEY, JSON.stringify(pairs)); } catch {}
    }

    function suggestionKey(suggestion) {
      return [...suggestion.names].sort().join("||");
    }

    function openLinkSuggestions() {
      const rejected = new Set(loadRejectedLinks().map((pair) => [...pair].sort().join("||")));
      return (DATA.company_link_review?.suggestions || []).filter((suggestion) => {
        const shared = new Set(suggestion.names.map((name) => normaliseCompanyKey(canonicalCompanyName(name))));
        if (shared.size < 2) return false;
        const pairs = [];
        suggestion.names.forEach((a, i) => suggestion.names.slice(i + 1).forEach((b) => pairs.push([a, b].sort().join("||"))));
        return !pairs.every((pair) => rejected.has(pair));
      });
    }

    function exportCompanyLinksFile() {
      const review = DATA.company_link_review || {};
      const approved = (review.approved || []).map((group) => ({
        names: [...group.names],
        shared: group.shared,
        ...(group.separate_entities ? { separate_entities: true } : {}),
      }));
      const byShared = new Map();
      companyLinks
        .filter((entry) => normaliseCompanyKey(entry.sourceName) !== normaliseCompanyKey(entry.sharedName))
        .forEach((entry) => {
          const key = normaliseCompanyKey(entry.sharedName);
          if (!byShared.has(key)) byShared.set(key, { names: new Set(), shared: entry.sharedName });
          byShared.get(key).names.add(entry.sourceName);
          if (managedCompanyRows().some((row) => normaliseCompanyKey(row.sourceName) === key)) {
            byShared.get(key).names.add(entry.sharedName);
          }
        });
      byShared.forEach((group) => {
        const names = [...group.names];
        const existing = approved.find((item) =>
          normaliseCompanyKey(item.shared) === normaliseCompanyKey(group.shared)
          || item.names.some((name) => names.includes(name))
        );
        if (existing) {
          names.forEach((name) => { if (!existing.names.includes(name)) existing.names.push(name); });
          existing.shared = group.shared;
        } else if (names.length) {
          approved.push({ names: names.includes(group.shared) ? names : [...names], shared: group.shared });
        }
      });
      const rejectedKeys = new Set();
      const rejected = [...(review.rejected || []), ...loadRejectedLinks()].filter((pair) => {
        const key = [...pair].sort().join("||");
        if (rejectedKeys.has(key)) return false;
        rejectedKeys.add(key);
        return true;
      });
      const payload = {
        _note: "Upload to pipeline/state/company_links.json in the french-opa-admin repository. "
          + "'approved' and 'rejected' are kept; the daily build recomputes the rest.",
        approved,
        rejected,
      };
      download("company_links.json", JSON.stringify(payload, null, 2), "application/json");
    }

    function canonicalCompanyName(sourceName) {
      if (!sourceName) return "";
      return companyLinkForSource(sourceName)?.sharedName || sourceName;
    }

    function companyTypeForSource(sourceName) {
      return companyLinkForSource(sourceName)?.type || "Unassigned";
    }

    function saveCompanyLink(sourceName, sharedName, type) {
      const source = String(sourceName || "").trim();
      if (!source) return;
      const next = {
        sourceName: source,
        sharedName: String(sharedName || source).trim() || source,
        type: COMPANY_TYPES.includes(type) ? type : "Unassigned",
      };
      const key = normaliseCompanyKey(source);
      const index = companyLinks.findIndex((entry) => normaliseCompanyKey(entry.sourceName) === key);
      if (index >= 0) companyLinks[index] = next;
      else companyLinks.push(next);
      saveCompanyLinks();
    }

    function clearCompanyLink(sourceName) {
      const key = normaliseCompanyKey(sourceName);
      const index = companyLinks.findIndex((entry) => normaliseCompanyKey(entry.sourceName) === key);
      if (index >= 0) companyLinks.splice(index, 1);
      saveCompanyLinks();
    }

    function managedCompanyRows() {
      const counts = new Map();
      transactions.forEach((row) => {
        if (!row.filer) return;
        counts.set(row.filer, (counts.get(row.filer) || 0) + 1);
      });
      const sourceNames = unique([
        ...counts.keys(),
        ...companyLinks.map((entry) => entry.sourceName),
      ].filter((name) => counts.has(name) || companyLinks.some((entry) => entry.sourceName === name)));
      return sourceNames.map((sourceName) => ({
        sourceName,
        sharedName: canonicalCompanyName(sourceName),
        type: companyTypeForSource(sourceName),
        rows: counts.get(sourceName) || 0,
      }));
    }

    function companyAliases(sourceName, sharedName) {
      const sharedKey = normaliseCompanyKey(sharedName);
      return managedCompanyRows()
        .filter((row) => normaliseCompanyKey(row.sourceName) !== normaliseCompanyKey(sourceName))
        .filter((row) => normaliseCompanyKey(row.sharedName) === sharedKey)
        .map((row) => row.sourceName);
    }

    function companyTypeOptions(selected) {
      return COMPANY_TYPES.map((value) =>
        `<option value="${escAttr(value)}" ${value === selected ? "selected" : ""}>${esc(value)}</option>`
      ).join("");
    }

    function loadShareCapitalEntries() {
      try {
        const raw = typeof localStorage === "undefined" ? "[]" : localStorage.getItem(SHARE_CAPITAL_STORAGE_KEY) || "[]";
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed)
          ? parsed.map((entry) => ({
              id: entry.id || `${entry.target}-${entry.date}-${entry.total}`,
              target: entry.target || "",
              date: entry.date || "",
              total: parseShareCapitalNumber(entry.total),
              type: entry.type || "Ordinary shares",
              check: entry.check || "",
            })).filter((entry) => entry.target && entry.date && Number.isFinite(entry.total) && entry.total > 0)
          : [];
      } catch {
        return [];
      }
    }

    function buildImportedShareCapitalEntries() {
      const fileEntries = (DATA.share_capital_entries || []).map((entry) => {
        const total = parseShareCapitalNumber(entry.total);
        const target = canonicalShareCapitalTarget(entry.target);
        const date = entry.date || DATA.generated_at?.slice(0, 10) || "";
        if (!target || !date || !Number.isFinite(total) || total <= 0) return null;
        return {
          id: `capfile-${normaliseTargetKey(target)}-${date}-${total}`,
          target,
          date,
          total,
          type: "Ordinary shares",
          check: entry.check || "Imported from share_capital.json",
          source: "spreadsheet",
        };
      }).filter(Boolean);
      const deals = DATA.french_public_offer_deals_last_five_years?.deals || [];
      const dealEntries = deals.map((deal) => {
        const total = parseShareCapitalNumber(deal.target_ordinary_shares);
        const target = canonicalShareCapitalTarget(deal.target);
        const date = deal.date_announced || deal.date_completed || DATA.generated_at?.slice(0, 10) || "";
        if (!target || !date || !Number.isFinite(total) || total <= 0) return null;
        return {
          id: `xlsx-${normaliseTargetKey(target)}-${date}-${total}`,
          target,
          date,
          total,
          type: "Ordinary shares",
          check: "Imported from French deals spreadsheet",
          source: "spreadsheet",
        };
      }).filter(Boolean);
      return [...dealEntries, ...fileEntries];
    }

    function mergeShareCapitalEntries(importedEntries, manualEntries) {
      const byId = new Map();
      [...importedEntries, ...manualEntries].forEach((entry) => {
        if (!entry || !entry.id) return;
        byId.set(entry.id, entry);
      });
      return [...byId.values()];
    }

    function saveShareCapitalEntries() {
      if (typeof localStorage === "undefined") return;
      const manualEntries = shareCapitalEntries.filter((entry) => entry.source !== "spreadsheet");
      localStorage.setItem(SHARE_CAPITAL_STORAGE_KEY, JSON.stringify(manualEntries));
    }

    function shareCapitalTargets() {
      return unique([
        ...transactions.map((row) => row.target),
        ...offers.map((offer) => offer.offeree),
        ...importedShareCapitalEntries.map((entry) => entry.target),
        ...shareCapitalEntries.map((entry) => entry.target),
      ]);
    }

    function latestShareCapital(target, asOf = "") {
      const limit = asOf ? dateOnly(asOf) : "";
      return shareCapitalEntries
        .filter((entry) => entry.target === target && Number.isFinite(entry.total) && (!limit || entry.date <= limit))
        .sort((a, b) => String(b.date).localeCompare(String(a.date)) || String(b.id).localeCompare(String(a.id)))[0] || null;
    }

    function knownShareCapitalTargets() {
      return unique([
        ...transactions.map((row) => row.target),
        ...notices.map((notice) => notice.target),
        ...offers.map((offer) => offer.offeree),
      ]);
    }

    function canonicalShareCapitalTarget(value) {
      const text = String(value || "").trim();
      if (!text) return "";
      const key = normaliseTargetKey(text);
      return knownShareCapitalTargets().find((target) => normaliseTargetKey(target) === key) || text;
    }

    function normaliseTargetKey(value) {
      return String(value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toUpperCase()
        .replace(/\([^)]*\)/g, " ")
        .replace(/\b(SOCIETE ANONYME FRANCAISE|SOCIETE ANONYME|SOCIETE|ANONYME|FRANCAISE|SA|SAS|SCA|SE|PLC|LTD|NV|SPA|AG|AB)\b/g, " ")
        .replace(/[^A-Z0-9]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    }

    function parseShareCapitalNumber(value) {
      const cleaned = String(value ?? "").replace(/[,\s]/g, "");
      const number = Number(cleaned);
      return Number.isFinite(number) ? number : NaN;
    }

    function percentOf(value, denominator) {
      const total = Number(denominator);
      const amount = Number(value);
      if (!Number.isFinite(total) || total <= 0 || !Number.isFinite(amount)) return null;
      return amount / total * 100;
    }

    function formatPercentCell(value) {
      if (value == null || !Number.isFinite(Number(value))) return `<span class="muted">n/a</span>`;
      return Number(value).toFixed(3);
    }

    function signedPercent(value) {
      if (value == null || !Number.isFinite(Number(value))) return `<span class="muted">n/a</span>`;
      const num = Number(value);
      const text = Math.abs(num).toFixed(3);
      if (num < 0) return `<span class="negative">-${text}</span>`;
      if (num > 0) return `+${text}`;
      return "0.000";
    }

    function formatDateTime(value, timeOnly = false) {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return timeOnly
        ? date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" })
        : date.toLocaleString(undefined, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
    }

    function dateOnly(value) {
      return value ? String(value).slice(0, 10) : "";
    }

    function shortDate(value) {
      if (!value) return "";
      const parts = String(value).slice(0, 10).split("-");
      return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0].slice(2)}` : value;
    }

    function minDate(values) {
      return values.filter(Boolean).sort()[0] || "";
    }

    function maxDate(values) {
      return values.filter(Boolean).sort().at(-1) || "";
    }

    function fmtNumber(value) {
      if (value == null || value === "") return "";
      const num = Number(value);
      return Number.isFinite(num) ? Math.abs(num).toLocaleString() : esc(value);
    }

    function signed(value) {
      if (value == null || value === "") return "";
      const num = Number(value);
      if (!Number.isFinite(num)) return esc(value);
      const text = Math.abs(num).toLocaleString();
      if (num < 0) return `<span class="negative">-${text}</span>`;
      if (num > 0) return `+${text}`;
      return "0";
    }

    function signedPlain(value) {
      return signed(value);
    }

    function parseTradePrice(value) {
      const text = String(value || "").replace(/\u00a0/g, " ").trim();
      if (!text || text === "-" || /^n\/a$/i.test(text)) return null;
      const match = text.match(/[0-9]+(?:[.,][0-9]+)?/);
      if (!match) return null;
      const valueNumber = Number(match[0].replace(",", "."));
      return Number.isFinite(valueNumber) ? valueNumber : null;
    }

    function tradeSideVwap(rows, side) {
      return rows.reduce((acc, row) => {
        const qty = Number(row.quantity || 0);
        const signedQty = signedQuantity(row, qty);
        const price = parseTradePrice(row.price_eur);
        if (!Number.isFinite(qty) || qty <= 0 || price == null) return acc;
        if (side === "purchase" && signedQty <= 0) return acc;
        if (side === "sale" && signedQty >= 0) return acc;
        const volume = Math.abs(qty);
        acc.qty += volume;
        acc.value += volume * price;
        acc.count += 1;
        acc.vwap = acc.qty ? acc.value / acc.qty : null;
        return acc;
      }, { qty: 0, value: 0, count: 0, vwap: null });
    }

    function formatVwap(summary) {
      if (!summary || summary.vwap == null) return `<span class="muted">-</span>`;
      return `<strong>${summary.vwap.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}</strong>`;
    }

    function vwapBasis(summary) {
      if (!summary || !summary.count) return "No priced trades";
      return `${summary.count} priced trades / ${summary.qty.toLocaleString()} qty`;
    }

    function psVwapRow(label, summary) {
      return `
        <tr class="total-row">
          <td colspan="10">${esc(label)}</td>
          <td>${formatVwap(summary)}</td>
          <td>${esc(vwapBasis(summary))}</td>
        </tr>
      `;
    }

    function csvNumber(value, decimals = 6) {
      const num = Number(value);
      if (!Number.isFinite(num)) return "";
      return num.toFixed(decimals).replace(/\.?0+$/, "") || "0";
    }

    function safeFilePart(value) {
      return String(value || "")
        .trim()
        .replace(/[^A-Za-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 80) || "export";
    }

    function psTradesCsv(target, filer, rows) {
      const fields = [
        "Section",
        "Target",
        "Buyer/seller",
        "Source filer",
        "AMF reference",
        "Reported date",
        "Dealing date",
        "Instrument",
        "Operation type",
        "Operation",
        "Quantity",
        "Signed quantity",
        "Price EUR",
        "VWAP quantity",
        "Trade value EUR",
        "Resulting holding",
        "Source URL",
      ];
      const lines = [fields.map(csvCell).join(",")];
      const daily = new Map();
      const sorted = [...rows].sort((a, b) =>
        String(a.transaction_date || "").localeCompare(String(b.transaction_date || "")) ||
        String(rowDisplayDate(a)).localeCompare(String(rowDisplayDate(b))) ||
        String(a.amf_number || "").localeCompare(String(b.amf_number || ""))
      );

      sorted.forEach((row) => {
        const reported = noticeMap().get(row.amf_number)?.document_date || dateOnly(rowDisplayDate(row));
        const qty = Number(row.quantity || 0);
        const signedQty = signedQuantity(row, qty);
        const price = parseTradePrice(row.price_eur);
        const vwapQty = Number.isFinite(qty) && qty > 0 && price != null ? Math.abs(qty) : null;
        const tradeValue = vwapQty != null ? vwapQty * price : null;
        if (vwapQty != null) {
          const key = row.transaction_date || "";
          if (!daily.has(key)) daily.set(key, { qty: 0, value: 0 });
          const acc = daily.get(key);
          acc.qty += vwapQty;
          acc.value += tradeValue;
        }
        lines.push([
          "Trade",
          target,
          filer,
          row.filer || "",
          row.amf_number || "",
          reported,
          row.transaction_date || "",
          row.instrument_type || "",
          row.operation_type || "",
          row.operation || "",
          qty || "",
          signedQty || 0,
          price == null ? "" : csvNumber(price, 6),
          vwapQty == null ? "" : csvNumber(vwapQty, 0),
          tradeValue == null ? "" : csvNumber(tradeValue, 6),
          row.resulting_holding || "",
          row.document_url || "",
        ].map(csvCell).join(","));
      });

      lines.push("");
      lines.push(["Daily VWAP rows", "", "", "", "", "", "Dealing date", "", "", "", "", "", "VWAP EUR", "VWAP quantity", "Trade value EUR", "", ""].map(csvCell).join(","));

      let totalQty = 0;
      let totalValue = 0;
      [...daily.entries()].sort((a, b) => String(a[0]).localeCompare(String(b[0]))).forEach(([dealingDate, acc]) => {
        const vwap = acc.qty ? acc.value / acc.qty : null;
        totalQty += acc.qty;
        totalValue += acc.value;
        lines.push([
          "Daily VWAP",
          target,
          filer,
          "",
          "",
          "",
          dealingDate,
          "",
          "",
          "",
          "",
          "",
          vwap == null ? "" : csvNumber(vwap, 6),
          csvNumber(acc.qty, 0),
          csvNumber(acc.value, 6),
          "",
          "",
        ].map(csvCell).join(","));
      });

      const totalVwap = totalQty ? totalValue / totalQty : null;
      lines.push([
        "Total VWAP",
        target,
        filer,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        totalVwap == null ? "" : csvNumber(totalVwap, 6),
        csvNumber(totalQty, 0),
        csvNumber(totalValue, 6),
        "",
        "",
      ].map(csvCell).join(","));

      return "\ufeff" + lines.join("\r\n");
    }

    function psCsv(groups) {
      const fields = ["reported", "dealingDate", "sharesDelta", "derivativeDelta", "reportedLong", "calcLong", "diffLong", "reportedShort", "calcShort", "diffShort", "net"];
      return [fields.join(","), ...groups.map((row) => fields.map((field) => csvCell(row[field])).join(","))].join("\n");
    }

    function csvCell(value) {
      const text = value == null ? "" : String(value);
      return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
    }

    function download(filename, content, type) {
      const blob = new Blob([content], { type });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    }

    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char]);
    }

    function escAttr(value) {
      return esc(value).replace(/`/g, "&#96;");
    }

    bindGlobalClicks();
    render();
  </script>
</body>
</html>
"""


def normalize_zodiac_filers(payload):
    for row in payload.get("transactions", []):
        if row.get("target") == ZODIAC_TARGET and row.get("filer") in ZODIAC_FILER_ALIASES:
            row["filer"] = ZODIAC_FILER_ALIASES[row.get("filer")]


def parse_legacy_date(value):
    text = str(value or "").strip().replace("*", "")
    if not text:
        return ""
    try:
        day, month, year = text.split("/")
        year_number = int(year)
        year_number += 2000 if year_number < 50 else 1900
        return f"{year_number:04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        return text


def parse_legacy_int(value):
    text = str(value or "").strip().replace("*", "").replace(",", "")
    if text in {"", "-"}:
        return 0
    return int(text.replace("+", ""))


def format_legacy_number(value):
    return f"{abs(int(value)):,}".replace(",", " ")


def legacy_holding_text(row, instrument_type):
    if row["short"]:
        return f"- {format_legacy_number(row['short'])} short position"
    if row["long"]:
        suffix = "actions et droits de vote" if instrument_type == "Shares" else "derivatives"
        return f"{format_legacy_number(row['long'])} {suffix}"
    return None


def legacy_share_holding_text(row):
    if not row["long"]:
        return None
    return f"{format_legacy_number(row['long'])} actions et droits de vote"


def legacy_short_holding_text(row):
    return f"- {format_legacy_number(row['short'])} short position"


def parse_legacy_zodiac_export(path):
    if not path.exists():
        return []
    rows = []
    holder = None
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        match = re.match(r"^ZODIAC AEROSPACE SA - (.*?) \[ORD\]$", line.strip())
        if match:
            holder = match.group(1).strip()
            continue
        if not holder or not re.match(r"^\s*\d{2}/\d{2}/\d{2}\t", line):
            continue
        parts = line.split("\t")
        if len(parts) < 11:
            continue
        rows.append({
            "holder": holder,
            "reported": parse_legacy_date(parts[0]),
            "dealing": parse_legacy_date(parts[1]),
            "shares_delta": parse_legacy_int(parts[2]),
            "derivatives_delta": parse_legacy_int(parts[3]),
            "long": parse_legacy_int(parts[4]),
            "short": parse_legacy_int(parts[7]),
        })
    return rows


def existing_zodiac_dealing_keys(payload):
    keys = set()
    for row in payload.get("transactions", []):
        if row.get("target") != ZODIAC_TARGET or not row.get("filer"):
            continue
        keys.add((row.get("filer"), row.get("transaction_date") or ""))
    return keys


def make_legacy_notice(amf_number, row):
    reported_at = f"{row['reported']}T00:00:00" if row["reported"] else ""
    return {
        "document_date": row["reported"],
        "parse_status": "legacy",
        "parse_notes": ["Backfilled from manually entered legacy Zodiac 8.3 export."],
        "notice_level_resulting_holdings": [],
        "amf_number": amf_number,
        "target": ZODIAC_TARGET,
        "document_url": "",
        "published_at": reported_at,
        "online_at": reported_at,
        "date_information": reported_at,
    }


def make_legacy_transaction(amf_number, row, instrument_type, delta, sequence, holding_text):
    quantity = abs(int(delta))
    if instrument_type == "Shares":
        operation_type = "buy" if delta > 0 else "sell" if delta < 0 else "legacy_position"
        operation = "Legacy backfill: purchase" if delta > 0 else "Legacy backfill: sale" if delta < 0 else "Legacy backfill: position"
        security = "actions"
    else:
        operation_type = "derivative_position" if delta else "legacy_position"
        operation = "Legacy backfill: derivative increase" if delta > 0 else "Legacy backfill: derivative decrease" if delta < 0 else "Legacy backfill: position"
        security = "derivatives"
    reported_at = f"{row['reported']}T00:00:00" if row["reported"] else ""
    return {
        "amf_number": amf_number,
        "target": ZODIAC_TARGET,
        "filer": row["holder"],
        "operation": operation,
        "operation_type": operation_type,
        "transaction_date": row["dealing"],
        "published_at": reported_at,
        "online_at": reported_at,
        "date_information": reported_at,
        "isin": ZODIAC_ISIN,
        "instrument_type": instrument_type,
        "quantity": quantity,
        "quantity_text": format_legacy_number(quantity),
        "security": security,
        "price_eur": "-",
        "resulting_holding": holding_text,
        "document_url": "",
        "document_file": "",
        "source": "legacy_zodiac_backfill",
        "legacy_sequence": sequence,
    }


def add_legacy_zodiac_backfill(payload):
    normalize_zodiac_filers(payload)
    existing_metadata = payload.get("source", {}).get("zodiac_legacy_backfill")
    legacy_rows = parse_legacy_zodiac_export(LEGACY_ZODIAC_SOURCE)
    if not legacy_rows:
        return {"rows_added": 0, "notices_added": 0, "source": str(LEGACY_ZODIAC_SOURCE)}

    existing_keys = existing_zodiac_dealing_keys(payload)
    rows_added = 0
    notices_added = 0
    for index, row in enumerate(legacy_rows, start=1):
        if (row["holder"], row["dealing"]) in existing_keys:
            continue
        amf_number = f"ZOD-LEGACY-{index:04d}"
        payload.setdefault("notice_summaries", []).append(make_legacy_notice(amf_number, row))
        notices_added += 1
        holding_attached = False
        for instrument_type, delta in (("Shares", row["shares_delta"]), ("Derivative", row["derivatives_delta"])):
            if not delta:
                continue
            holding_text = legacy_holding_text(row, instrument_type) if not holding_attached else None
            holding_attached = holding_attached or bool(holding_text)
            payload.setdefault("transactions", []).append(make_legacy_transaction(amf_number, row, instrument_type, delta, rows_added + 1, holding_text))
            rows_added += 1
        if not row["shares_delta"] and not row["derivatives_delta"]:
            share_holding = legacy_share_holding_text(row)
            if share_holding:
                payload.setdefault("transactions", []).append(make_legacy_transaction(amf_number, row, "Shares", 0, rows_added + 1, share_holding))
                rows_added += 1
            payload.setdefault("transactions", []).append(make_legacy_transaction(amf_number, row, "Derivative", 0, rows_added + 1, legacy_short_holding_text(row)))
            rows_added += 1
        existing_keys.add((row["holder"], row["dealing"]))

    if existing_metadata and not rows_added and not notices_added:
        return existing_metadata

    payload.setdefault("source", {})["zodiac_legacy_backfill"] = {
        "source_file": str(LEGACY_ZODIAC_SOURCE),
        "rows_added": rows_added,
        "notices_added": notices_added,
        "mode": "holder_and_dealing_date_gap_fill",
    }
    return payload["source"]["zodiac_legacy_backfill"]


def fill_notice_level_resulting_holdings(payload):
    notices = {
        notice.get("amf_number"): notice
        for notice in payload.get("notice_summaries", [])
        if notice.get("amf_number")
    }
    rows_by_notice = {}
    for row in payload.get("transactions", []):
        amf_number = row.get("amf_number")
        if amf_number:
            rows_by_notice.setdefault(amf_number, []).append(row)

    notices_repaired = 0
    rows_repaired = 0
    for amf_number, notice in notices.items():
        holdings = [
            str(value).strip()
            for value in notice.get("notice_level_resulting_holdings", [])
            if str(value or "").strip()
        ]
        rows = rows_by_notice.get(amf_number, [])
        if not holdings or not rows or any(row.get("resulting_holding") for row in rows):
            continue

        date_groups = []
        groups_by_date = {}
        for row in rows:
            transaction_date = row.get("transaction_date") or ""
            if transaction_date not in groups_by_date:
                groups_by_date[transaction_date] = []
                date_groups.append(groups_by_date[transaction_date])
            groups_by_date[transaction_date].append(row)

        repaired_here = 0
        if len(holdings) == len(date_groups):
            for holding, group in zip(holdings, date_groups):
                group[-1]["resulting_holding"] = holding
                repaired_here += 1
        elif len(holdings) == 1:
            rows[-1]["resulting_holding"] = holdings[0]
            repaired_here += 1

        if repaired_here:
            notices_repaired += 1
            rows_repaired += repaired_here
            note = "Assigned notice-level resulting holdings to final transaction rows by dealing date."
            if note not in notice.setdefault("parse_notes", []):
                notice["parse_notes"].append(note)

    payload.setdefault("source", {})["notice_level_resulting_holding_repair"] = {
        "notices_repaired": notices_repaired,
        "rows_repaired": rows_repaired,
        "mode": "notice_level_holdings_to_final_rows_by_dealing_date",
    }
    return rows_repaired


def transaction_key(row):
    return (
        row.get("amf_number") or "",
        row.get("target") or "",
        row.get("filer") or "",
        row.get("transaction_date") or "",
        row.get("instrument_type") or "",
        row.get("operation") or "",
        str(row.get("quantity") or ""),
        row.get("resulting_holding") or "",
    )


def merge_extra_filings(payload, extra_path, label):
    if not extra_path.exists():
        return {"source_file": str(extra_path), "status": "not_found", "notices_added": 0, "transactions_added": 0}

    extra = json.loads(extra_path.read_text(encoding="utf-8"))
    notice_ids = {row.get("amf_number") for row in payload.get("notice_summaries", [])}
    transaction_ids = {transaction_key(row) for row in payload.get("transactions", [])}

    notices_added = 0
    for notice in extra.get("notice_summaries", []):
        amf_number = notice.get("amf_number")
        if amf_number in notice_ids:
            continue
        payload.setdefault("notice_summaries", []).append(notice)
        notice_ids.add(amf_number)
        notices_added += 1

    transactions_added = 0
    for row in extra.get("transactions", []):
        key = transaction_key(row)
        if key in transaction_ids:
            continue
        payload.setdefault("transactions", []).append(row)
        transaction_ids.add(key)
        transactions_added += 1

    merge_report = {
        "label": label,
        "source_file": str(extra_path),
        "status": "merged",
        "notices_added": notices_added,
        "transactions_added": transactions_added,
        "generated_at": extra.get("generated_at"),
        "source": extra.get("source"),
        "filter": extra.get("filter"),
    }
    payload.setdefault("source", {}).setdefault("merged_sources", []).append(merge_report)
    return merge_report


def normalise_target_key(value):
    import unicodedata
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(
        r"\b(SOCIETE ANONYME FRANCAISE|SOCIETE ANONYME|SOCIETE|ANONYME|FRANCAISE|"
        r"SA|SAS|SCA|SE|PLC|LTD|NV|SPA|AG|AB)\b",
        " ",
        text,
    )
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_share_capital_entries(payload):
    """Read state/share_capital.json and map each name onto the canonical BDIF
    target name used by transactions / notices / the offer-period list, so the
    admin app can show percentages for live deals."""
    if not SHARE_CAPITAL_SOURCE.exists():
        return []
    raw = json.loads(SHARE_CAPITAL_SOURCE.read_text(encoding="utf-8"))

    known = []
    seen = set()
    def add_known(name):
        text = str(name or "").strip()
        if text and text not in seen:
            seen.add(text)
            known.append(text)
    for row in payload.get("transactions") or []:
        add_known(row.get("target"))
    for row in payload.get("notice_summaries") or []:
        add_known(row.get("target"))
    offer_list = payload.get("offer_period_companies_from_amf_xlsx") or {}
    for company in offer_list.get("companies") or []:
        add_known(company.get("offeree"))
    known_keys = [(normalise_target_key(name), name) for name in known]

    entries = []
    for name, info in raw.items():
        if str(name).startswith("_") or not info:
            continue
        total = info.get("total") if isinstance(info, dict) else info
        date = (info.get("date") if isinstance(info, dict) else "") or ""
        try:
            total = int(str(total).replace(",", "").replace(" ", ""))
        except (TypeError, ValueError):
            continue
        if total <= 0:
            continue
        key = normalise_target_key(name)
        target = next((orig for k, orig in known_keys if k and k == key), None)
        if target is None:
            target = next(
                (orig for k, orig in known_keys if k and key and (k in key or key in k)),
                None,
            )
        entries.append({
            "target": target or str(name).strip(),
            "date": str(date)[:10],
            "total": total,
            "check": "Imported from share_capital.json",
            "matched_known_target": bool(target),
        })
        # Dated capital history from AMF 223-16 declarations (drives
        # as-at-date percentages in the historical share register).
        if isinstance(info, dict):
            seen_points = {(str(date)[:10], total)}
            for point in info.get("history") or []:
                try:
                    h_total = int(str(point.get("total")).replace(",", "").replace(" ", ""))
                except (TypeError, ValueError):
                    continue
                h_date = str(point.get("as_at") or point.get("date") or "")[:10]
                if h_total <= 0 or not h_date or (h_date, h_total) in seen_points:
                    continue
                seen_points.add((h_date, h_total))
                entries.append({
                    "target": target or str(name).strip(),
                    "date": h_date,
                    "total": h_total,
                    "check": "AMF 223-16 declaration",
                    "matched_known_target": bool(target),
                })
    return entries


def add_company_links(payload):
    """Link filer names that are the same firm written differently (see
    pipeline/company_links.py and state/company_links.json)."""
    from collections import Counter, defaultdict
    import company_links

    counts = Counter(row.get("filer") for row in payload.get("transactions", []) if row.get("filer"))
    targets = defaultdict(set)
    for row in payload.get("transactions", []):
        if row.get("filer") and row.get("target"):
            targets[row["filer"]].add(row["target"])
    result = company_links.refresh_state(counts, targets)
    payload["company_links"] = result["links"]
    payload["company_link_review"] = {
        "approved": company_links.load_state().get("approved", []),
        "rejected": company_links.load_state().get("rejected", []),
        "suggestions": result["suggestions"],
        "fragments": result["fragments"],
    }


def main():
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    if FIVE_YEAR_DEALS.exists():
        payload["french_public_offer_deals_last_five_years"] = json.loads(
            FIVE_YEAR_DEALS.read_text(encoding="utf-8")
        )
    merge_extra_filings(payload, FIVE_YEAR_SOURCE, "french_public_offers_last_five_years")
    add_legacy_zodiac_backfill(payload)
    fill_notice_level_resulting_holdings(payload)
    if EUROPE_SOURCE.exists():
        payload["europe_regulatory"] = json.loads(EUROPE_SOURCE.read_text(encoding="utf-8"))
    payload["share_capital_entries"] = build_share_capital_entries(payload)
    add_company_links(payload)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False)), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
