const pptxgen = require("pptxgenjs");
const {
  svgToDataUri,
  safeOuterShadow,
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "OpenAI";
pptx.subject = "DR-Kube project presentation";
pptx.title = "DR-Kube 발표 자료";
pptx.lang = "ko-KR";
pptx.theme = {
  headFontFace: "Apple SD Gothic Neo",
  bodyFontFace: "Apple SD Gothic Neo",
  lang: "ko-KR",
};

const COLORS = {
  navy: "0F172A",
  ink: "18212F",
  slate: "475569",
  muted: "64748B",
  line: "CBD5E1",
  cloud: "E2E8F0",
  fog: "F8FAFC",
  mist: "EEF4F7",
  cyan: "06B6D4",
  cyanSoft: "CFFAFE",
  teal: "0F766E",
  green: "16A34A",
  amber: "F59E0B",
  red: "DC2626",
  blue: "2563EB",
  white: "FFFFFF",
};

function addBg(slide) {
  slide.background = { color: COLORS.fog };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5,
    fill: { color: COLORS.fog },
    line: { color: COLORS.fog },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.78,
    y: 0.92,
    w: 1.35,
    h: 0.05,
    fill: { color: COLORS.cyan },
    line: { color: COLORS.cyan },
  });
}

function addHeader(slide, title, subtitle) {
  addBg(slide);
  slide.addText(title, {
    x: 0.55,
    y: 0.48,
    w: 10.2,
    h: 0.5,
    fontFace: "Apple SD Gothic Neo",
    fontSize: 27,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.55,
      y: 1.04,
      w: 10.2,
      h: 0.26,
      fontFace: "Apple SD Gothic Neo",
      fontSize: 9,
      color: COLORS.muted,
      margin: 0,
    });
  }
}

function addFooter(slide, page) {
  slide.addText(String(page), {
    x: 12.55,
    y: 7.08,
    w: 0.3,
    h: 0.2,
    align: "right",
    fontSize: 9,
    color: COLORS.muted,
    margin: 0,
  });
}

function card(slide, x, y, w, h, title, body, accent = COLORS.blue) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: COLORS.white },
    line: { color: COLORS.cloud, pt: 1 },
    shadow: safeOuterShadow("000000", 0.12, 45, 1.5, 1),
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: x + 0.22,
    y: y + 0.18,
    w: 0.52,
    h: 0.16,
    rectRadius: 0.06,
    fill: { color: accent },
    line: { color: accent },
  });
  slide.addText(title, {
    x: x + 0.22,
    y: y + 0.44,
    w: w - 0.44,
    h: 0.25,
    fontSize: 14.5,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText(body, {
    x: x + 0.22,
    y: y + 0.8,
    w: w - 0.44,
    h: h - 0.98,
    fontSize: 10.5,
    color: COLORS.slate,
    valign: "top",
    margin: 0,
    breakLine: false,
  });
}

function pill(slide, x, y, w, text, fill, color = COLORS.white) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.34,
    rectRadius: 0.12,
    fill: { color: fill },
    line: { color: fill },
  });
  slide.addText(text, {
    x,
    y: y + 0.04,
    w,
    h: 0.2,
    align: "center",
    fontSize: 9,
    bold: true,
    color,
    margin: 0,
  });
}

function arrow(slide, x, y, w, color = COLORS.blue) {
  slide.addShape(pptx.ShapeType.chevron, {
    x,
    y,
    w,
    h: 0.28,
    fill: { color },
    line: { color },
  });
}

function box(slide, x, y, w, h, title, lines, opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.06,
    fill: { color: opts.fill || COLORS.white },
    line: { color: opts.line || COLORS.line, pt: 1 },
  });
  slide.addText(title, {
    x: x + 0.14,
    y: y + 0.12,
    w: w - 0.28,
    h: 0.2,
    fontSize: 11.5,
    bold: true,
    color: opts.titleColor || COLORS.ink,
    margin: 0,
    align: "center",
  });
  slide.addText(lines, {
    x: x + 0.16,
    y: y + 0.4,
    w: w - 0.32,
    h: h - 0.52,
    fontSize: 9.5,
    color: opts.bodyColor || COLORS.slate,
    align: "center",
    valign: "mid",
    margin: 0,
  });
}

function addDiagnostics(slide) {
  warnIfSlideHasOverlaps(slide, pptx);
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

function systemFlowSvg() {
  return `
  <svg xmlns="http://www.w3.org/2000/svg" width="1180" height="360" viewBox="0 0 1180 360">
    <defs>
      <marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
        <path d="M0,0 L8,4 L0,8 z" fill="#2563EB"/>
      </marker>
      <marker id="arr2" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
        <path d="M0,0 L8,4 L0,8 z" fill="#06B6D4"/>
      </marker>
    </defs>
    <rect x="0" y="0" width="1180" height="360" rx="30" fill="#F8FAFC"/>

    <rect x="24" y="26" width="248" height="190" rx="24" fill="#FFFFFF" stroke="#D8E3EA" stroke-width="2"/>
    <rect x="290" y="26" width="312" height="190" rx="24" fill="#ECFEFF" stroke="#A5F3FC" stroke-width="2"/>
    <rect x="620" y="26" width="250" height="190" rx="24" fill="#FFFFFF" stroke="#D8E3EA" stroke-width="2"/>
    <rect x="888" y="26" width="268" height="190" rx="24" fill="#FFFFFF" stroke="#D8E3EA" stroke-width="2"/>

    <text x="48" y="54" font-size="16" font-family="Arial" font-weight="700" fill="#0F172A">1. 장애 감지 / 근거 수집</text>
    <text x="314" y="54" font-size="16" font-family="Arial" font-weight="700" fill="#0F172A">2. AI 복구 판단</text>
    <text x="644" y="54" font-size="16" font-family="Arial" font-weight="700" fill="#0F172A">3. GitOps 반영</text>
    <text x="912" y="54" font-size="16" font-family="Arial" font-weight="700" fill="#0F172A">4. 복구 검증 / 알림</text>

    <rect x="42" y="78" width="92" height="58" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="88" y="102" text-anchor="middle" font-size="15" font-family="Arial" font-weight="700" fill="#0F172A">K8s</text>
    <text x="88" y="122" text-anchor="middle" font-size="12" font-family="Arial" fill="#475569">Cluster</text>

    <rect x="150" y="78" width="102" height="58" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="201" y="101" text-anchor="middle" font-size="14" font-family="Arial" font-weight="700" fill="#0F172A">Prometheus</text>
    <text x="201" y="122" text-anchor="middle" font-size="12" font-family="Arial" fill="#475569">Alert Rules</text>

    <rect x="314" y="80" width="82" height="54" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="355" y="101" text-anchor="middle" font-size="14" font-family="Arial" font-weight="700" fill="#0F172A">Alert</text>
    <text x="355" y="120" text-anchor="middle" font-size="12" font-family="Arial" fill="#475569">manager</text>

    <rect x="410" y="80" width="86" height="54" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="453" y="101" text-anchor="middle" font-size="14" font-family="Arial" font-weight="700" fill="#0F172A">Converter</text>
    <text x="453" y="120" text-anchor="middle" font-size="11" font-family="Arial" fill="#475569">Alert → Issue</text>

    <rect x="380" y="148" width="136" height="52" rx="18" fill="#06B6D4" stroke="#0891B2" stroke-width="2"/>
    <text x="448" y="171" text-anchor="middle" font-size="14" font-family="Arial" font-weight="700" fill="#FFFFFF">LLM</text>
    <text x="448" y="189" text-anchor="middle" font-size="11" font-family="Arial" fill="#E0F7FA">원인 분석 + 수정안</text>

    <rect x="512" y="72" width="72" height="136" rx="20" fill="#0F172A" stroke="#0F172A" stroke-width="2"/>
    <text x="548" y="102" text-anchor="middle" font-size="15" font-family="Arial" font-weight="700" fill="#FFFFFF">LangGraph</text>
    <text x="548" y="122" text-anchor="middle" font-size="15" font-family="Arial" font-weight="700" fill="#FFFFFF">Agent</text>
    <text x="548" y="152" text-anchor="middle" font-size="10" font-family="Arial" fill="#93C5FD">load_issue</text>
    <text x="548" y="168" text-anchor="middle" font-size="10" font-family="Arial" fill="#93C5FD">analyze_and_fix</text>
    <text x="548" y="184" text-anchor="middle" font-size="10" font-family="Arial" fill="#93C5FD">validate</text>
    <text x="548" y="199" text-anchor="middle" font-size="10" font-family="Arial" fill="#E0F2FE">retry loop</text>

    <rect x="644" y="78" width="76" height="58" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="682" y="102" text-anchor="middle" font-size="14" font-family="Arial" font-weight="700" fill="#0F172A">GitHub</text>
    <text x="682" y="122" text-anchor="middle" font-size="11" font-family="Arial" fill="#475569">PR</text>

    <rect x="736" y="78" width="88" height="58" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="780" y="102" text-anchor="middle" font-size="13" font-family="Arial" font-weight="700" fill="#0F172A">values/*.yaml</text>
    <text x="780" y="122" text-anchor="middle" font-size="11" font-family="Arial" fill="#475569">Git change</text>

    <rect x="740" y="148" width="82" height="52" rx="16" fill="#ECFDF5" stroke="#86EFAC" stroke-width="2"/>
    <text x="781" y="171" text-anchor="middle" font-size="14" font-family="Arial" font-weight="700" fill="#0F172A">ArgoCD</text>
    <text x="781" y="189" text-anchor="middle" font-size="11" font-family="Arial" fill="#166534">Sync</text>

    <rect x="914" y="78" width="96" height="58" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="962" y="101" text-anchor="middle" font-size="14" font-family="Arial" font-weight="700" fill="#0F172A">Verifier</text>
    <text x="962" y="122" text-anchor="middle" font-size="11" font-family="Arial" fill="#475569">Pod + Alert</text>

    <rect x="1030" y="78" width="102" height="58" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2"/>
    <text x="1081" y="101" text-anchor="middle" font-size="14" font-family="Arial" font-weight="700" fill="#0F172A">Slack</text>
    <text x="1081" y="122" text-anchor="middle" font-size="11" font-family="Arial" fill="#475569">Notifications</text>

    <line x1="134" y1="107" x2="150" y2="107" stroke="#2563EB" stroke-width="4" marker-end="url(#arr)"/>
    <line x1="252" y1="107" x2="314" y2="107" stroke="#2563EB" stroke-width="4" marker-end="url(#arr)"/>
    <line x1="396" y1="107" x2="410" y2="107" stroke="#2563EB" stroke-width="4" marker-end="url(#arr)"/>
    <line x1="496" y1="107" x2="512" y2="107" stroke="#2563EB" stroke-width="4" marker-end="url(#arr)"/>
    <line x1="584" y1="107" x2="644" y2="107" stroke="#2563EB" stroke-width="4" marker-end="url(#arr)"/>
    <line x1="720" y1="107" x2="736" y2="107" stroke="#2563EB" stroke-width="4" marker-end="url(#arr)"/>
    <line x1="824" y1="174" x2="914" y2="107" stroke="#16A34A" stroke-width="4" marker-end="url(#arr)"/>
    <line x1="1010" y1="107" x2="1030" y2="107" stroke="#16A34A" stroke-width="4" marker-end="url(#arr)"/>

    <line x1="448" y1="148" x2="512" y2="142" stroke="#06B6D4" stroke-width="3" stroke-dasharray="7 6" marker-end="url(#arr2)"/>
    <text x="406" y="162" font-size="11" font-family="Arial" fill="#0F766E">원인 분석 + 수정안 생성</text>

    <rect x="42" y="248" width="1090" height="78" rx="22" fill="#FFFFFF" stroke="#D8E3EA" stroke-width="2"/>
    <text x="72" y="276" font-size="15" font-family="Arial" font-weight="700" fill="#0F172A">Observability Evidence Layer</text>
    <text x="72" y="297" font-size="12" font-family="Arial" fill="#475569">메트릭, 로그, 트레이스, 프로파일이 에이전트 판단 근거를 제공</text>

    <rect x="334" y="268" width="118" height="34" rx="14" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.5"/>
    <text x="393" y="290" text-anchor="middle" font-size="12" font-family="Arial" font-weight="700" fill="#0F172A">Metrics</text>
    <rect x="470" y="268" width="102" height="34" rx="14" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.5"/>
    <text x="521" y="290" text-anchor="middle" font-size="12" font-family="Arial" font-weight="700" fill="#0F172A">Logs</text>
    <rect x="590" y="268" width="104" height="34" rx="14" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.5"/>
    <text x="642" y="290" text-anchor="middle" font-size="12" font-family="Arial" font-weight="700" fill="#0F172A">Traces</text>
    <rect x="712" y="268" width="114" height="34" rx="14" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.5"/>
    <text x="769" y="290" text-anchor="middle" font-size="12" font-family="Arial" font-weight="700" fill="#0F172A">Profiles</text>
    <rect x="844" y="268" width="124" height="34" rx="14" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.5"/>
    <text x="906" y="290" text-anchor="middle" font-size="12" font-family="Arial" font-weight="700" fill="#0F172A">Chaos Signals</text>

    <line x1="355" y1="248" x2="520" y2="210" stroke="#94A3B8" stroke-width="2.5" stroke-dasharray="6 5" marker-end="url(#arr2)"/>
    <line x1="642" y1="248" x2="548" y2="210" stroke="#94A3B8" stroke-width="2.5" stroke-dasharray="6 5" marker-end="url(#arr2)"/>
    <line x1="906" y1="248" x2="962" y2="136" stroke="#94A3B8" stroke-width="2.5" stroke-dasharray="6 5" marker-end="url(#arr2)"/>
  </svg>`;
}

// Slide 1
{
  const slide = pptx.addSlide();
  slide.background = { color: COLORS.navy };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5,
    fill: { color: COLORS.navy },
    line: { color: COLORS.navy },
  });
  slide.addShape(pptx.ShapeType.arc, {
    x: 9.45,
    y: 0.42,
    w: 2.55,
    h: 2.55,
    line: { color: "18314A", pt: 28 },
    fill: { color: COLORS.navy, transparency: 100 },
  });
  pill(slide, 0.72, 0.86, 1.78, "AI + GitOps", COLORS.cyan, COLORS.navy);
  slide.addText("DR-Kube", {
    x: 0.72,
    y: 1.45,
    w: 4.4,
    h: 0.78,
    fontSize: 28,
    bold: true,
    color: COLORS.white,
    margin: 0,
  });
  slide.addText("Kubernetes 장애 자동 감지·분석·복구를 위한 AI 기반 GitOps 시스템", {
    x: 0.72,
    y: 2.28,
    w: 7.2,
    h: 0.52,
    fontSize: 18,
    color: "D6E4F0",
    margin: 0,
  });
  slide.addText("Prometheus Alert → LangGraph Agent → GitHub PR → ArgoCD Sync", {
    x: 0.72,
    y: 2.92,
    w: 6.8,
    h: 0.28,
    fontSize: 11.5,
    color: "93C5FD",
    margin: 0,
  });
  card(
    slide,
    0.76,
    4.02,
    2.86,
    1.66,
    "왜 필요한가",
    "클러스터 장애 대응은 탐지, 원인 분석, 설정 수정, 배포 확인까지 사람이 여러 도구를 오가며 처리해야 합니다.",
    COLORS.red
  );
  card(
    slide,
    3.84,
    4.02,
    2.86,
    1.66,
    "핵심 아이디어",
    "장애 신호를 Issue로 변환하고, LLM이 values YAML 수정안을 만들어 PR까지 연결합니다.",
    COLORS.cyan
  );
  card(
    slide,
    6.92,
    4.02,
    2.86,
    1.66,
    "복구 원칙",
    "클러스터에 직접 쓰지 않고 Git 변경만 허용하는 GitOps 방식으로 안전성과 추적성을 확보합니다.",
    COLORS.green
  );
  slide.addText("DR-Kube | 프로젝트 발표", {
    x: 0.74,
    y: 6.78,
    w: 2.4,
    h: 0.2,
    fontSize: 9.5,
    color: "B6C2CF",
    margin: 0,
  });
  addDiagnostics(slide);
}

// Slide 2
{
  const slide = pptx.addSlide();
  addHeader(slide, "문제 정의와 해결 아이디어", "핵심은 장애 대응의 분절된 수작업 흐름을 검증 가능한 복구 루프로 바꾸는 것입니다.");
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.62,
    y: 1.38,
    w: 4.0,
    h: 4.26,
    rectRadius: 0.08,
    fill: { color: COLORS.white },
    line: { color: COLORS.cloud, pt: 1 },
    shadow: safeOuterShadow("000000", 0.12, 45, 1.5, 1),
  });
  slide.addText("운영자가 겪는 비효율", {
    x: 0.96,
    y: 1.7,
    w: 2.0,
    h: 0.22,
    fontSize: 15,
    bold: true,
    color: COLORS.red,
    margin: 0,
  });
  slide.addText("장애 탐지, 원인 분석, YAML 수정, PR 생성, 배포 확인까지 도구가 분절돼 있고 MTTR이 길어집니다.", {
    x: 0.96,
    y: 2.06,
    w: 3.2,
    h: 0.62,
    fontSize: 14,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText([
    { text: "장애 대응 품질이 운영자 숙련도에 크게 의존", options: { bullet: { indent: 10 } } },
    { text: "근거 수집과 변경 반영이 분리돼 반복 작업이 많음", options: { bullet: { indent: 10 } } },
    { text: "복구 과정 기록이 흩어져 회고와 감사가 어려움", options: { bullet: { indent: 10 } } },
  ], {
    x: 0.96,
    y: 3.05,
    w: 3.08,
    h: 1.38,
    fontSize: 10.8,
    color: COLORS.slate,
    breakLine: false,
    margin: 0,
  });
  pill(slide, 0.96, 4.92, 1.08, "Pain Point", COLORS.red);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 4.95,
    y: 1.38,
    w: 7.72,
    h: 4.54,
    rectRadius: 0.08,
    fill: { color: COLORS.white },
    line: { color: COLORS.cloud, pt: 1 },
  });
  slide.addText("DR-Kube의 해결 아이디어", {
    x: 5.22,
    y: 1.66,
    w: 2.8,
    h: 0.24,
    fontSize: 15,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  box(slide, 5.18, 2.28, 1.0, 0.95, "1. 감지", "Prometheus\nAlert");
  arrow(slide, 6.23, 2.62, 0.3);
  box(slide, 6.56, 2.28, 1.08, 0.95, "2. 수집", "Alertmanager\nWebhook");
  arrow(slide, 7.69, 2.62, 0.3);
  box(slide, 8.02, 2.28, 1.18, 0.95, "3. 분석", "LLM root cause\n+ fix");
  arrow(slide, 9.24, 2.62, 0.3);
  box(slide, 9.58, 2.28, 1.1, 0.95, "4. 변경", "values YAML\nPR 생성");
  arrow(slide, 10.72, 2.62, 0.3, COLORS.green);
  box(slide, 11.06, 2.28, 0.98, 0.95, "5. 복구", "ArgoCD\nSync", {
    fill: "ECFDF5",
    line: "86EFAC",
  });
  slide.addText([
    { text: "핵심 원칙: AI는 수정안을 제안하고, 실제 반영은 GitOps로만 수행", options: { bullet: { indent: 10 } } },
    { text: "프로토타입 범위: load_issue → analyze_and_fix → validate → create_pr", options: { bullet: { indent: 10 } } },
    { text: "복구 완료 알림은 에이전트가 아니라 ArgoCD Notifications가 담당", options: { bullet: { indent: 10 } } },
  ], {
    x: 5.26,
    y: 3.82,
    w: 6.92,
    h: 1.16,
    fontSize: 11,
    color: COLORS.slate,
    breakLine: false,
    margin: 0,
  });
  pill(slide, 5.24, 5.1, 1.1, "Solution", COLORS.green);
  addFooter(slide, 2);
  addDiagnostics(slide);
}

// Slide 3
{
  const slide = pptx.addSlide();
  addHeader(slide, "DR-Kube 시스템 아키텍처", "관측성으로 장애를 감지하고, 에이전트가 수정안을 만들고, GitOps가 안전하게 복구를 반영합니다.");
  slide.addImage({
    data: svgToDataUri(systemFlowSvg()),
    x: 0.62,
    y: 1.42,
    w: 12.0,
    h: 3.66,
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.82,
    y: 5.42,
    w: 11.66,
    h: 0.8,
    rectRadius: 0.08,
    fill: { color: COLORS.white },
    line: { color: COLORS.cloud, pt: 1 },
  });
  slide.addText("핵심 메시지", {
    x: 1.08,
    y: 5.68,
    w: 1.12,
    h: 0.18,
    fontSize: 12.5,
    bold: true,
    color: COLORS.teal,
    margin: 0,
  });
  slide.addText("이 아키텍처의 핵심은 '관측성 → 판단 → Git 변경 → 복구 검증'이 하나의 폐루프로 연결된다는 점입니다.", {
    x: 2.28,
    y: 5.64,
    w: 9.5,
    h: 0.22,
    fontSize: 13.5,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  addFooter(slide, 3);
  addDiagnostics(slide);
}

// Slide 4
{
  const slide = pptx.addSlide();
  addHeader(slide, "핵심 워크플로우", "현재 구조와 목표 구조의 차이는 LLM 호출 단순화와 validate 루프 도입입니다.");
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.65,
    y: 1.45,
    w: 5.9,
    h: 4.95,
    rectRadius: 0.08,
    fill: { color: COLORS.white },
    line: { color: COLORS.cloud, pt: 1 },
  });
  slide.addText("현재", {
    x: 0.95,
    y: 1.74,
    w: 1.0,
    h: 0.24,
    fontSize: 16,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  box(slide, 1.0, 2.2, 1.2, 0.9, "Load", "issue");
  arrow(slide, 2.32, 2.53, 0.42);
  box(slide, 2.78, 2.2, 1.2, 0.9, "Analyze", "LLM");
  arrow(slide, 4.1, 2.53, 0.42);
  box(slide, 4.56, 2.2, 1.2, 0.9, "Fix", "LLM");
  slide.addText([
    { text: "LLM 호출 2회", options: { bullet: { indent: 10 } } },
    { text: "사람 확인 중심", options: { bullet: { indent: 10 } } },
    { text: "복구 품질 편차 큼", options: { bullet: { indent: 10 } } },
  ], {
    x: 1.0,
    y: 3.45,
    w: 2.25,
    h: 1.0,
    fontSize: 11,
    color: COLORS.slate,
    margin: 0,
    breakLine: false,
  });
  card(slide, 3.55, 3.46, 2.0, 1.18, "현재의 한계", "분석과 수정이 분리돼 속도와 일관성이 떨어집니다.", COLORS.red);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 6.8,
    y: 1.45,
    w: 5.9,
    h: 4.95,
    rectRadius: 0.08,
    fill: { color: "F0FDF4" },
    line: { color: "86EFAC", pt: 1.4 },
  });
  slide.addText("목표 (#1194)", {
    x: 7.1,
    y: 1.74,
    w: 1.8,
    h: 0.24,
    fontSize: 16,
    bold: true,
    color: COLORS.green,
    margin: 0,
  });
  box(slide, 7.12, 2.2, 0.96, 0.9, "Load", "issue", { fill: COLORS.white });
  arrow(slide, 8.12, 2.53, 0.24, COLORS.green);
  box(slide, 8.38, 2.2, 1.45, 0.9, "Analyze + Fix", "LLM 1회", {
    fill: "DCFCE7",
    line: "16A34A",
  });
  arrow(slide, 9.9, 2.53, 0.24, COLORS.green);
  box(slide, 10.16, 2.2, 1.0, 0.9, "Validate", "retry ≤ 3", {
    fill: COLORS.white,
    line: COLORS.green,
  });
  slide.addShape(pptx.ShapeType.chevron, {
    x: 9.72,
    y: 3.22,
    w: 0.44,
    h: 0.34,
    rotate: 180,
    fill: { color: COLORS.amber },
    line: { color: COLORS.amber },
  });
  slide.addText("실패 시 재시도", {
    x: 8.34,
    y: 3.16,
    w: 0.98,
    h: 0.18,
    fontSize: 8.5,
    color: COLORS.amber,
    margin: 0,
  });
  arrow(slide, 11.22, 2.53, 0.24, COLORS.green);
  box(slide, 11.48, 2.2, 0.82, 0.9, "PR", "create", {
    fill: COLORS.white,
    line: COLORS.green,
  });
  slide.addText([
    { text: "LLM 호출 1회", options: { bullet: { indent: 10 } } },
    { text: "validate retry loop", options: { bullet: { indent: 10 } } },
    { text: "PR 품질 자동 보정", options: { bullet: { indent: 10 } } },
  ], {
    x: 7.12,
    y: 3.65,
    w: 2.22,
    h: 1.0,
    fontSize: 11,
    color: COLORS.slate,
    margin: 0,
    breakLine: false,
  });
  card(slide, 9.42, 3.76, 2.32, 1.0, "목표의 핵심", "한 번에 제안하고, 실패하면 최대 3회 스스로 보정합니다.", COLORS.green);
  pill(slide, 1.0, 5.58, 1.15, "2 calls", COLORS.red);
  pill(slide, 2.28, 5.58, 1.42, "Human check", COLORS.amber);
  pill(slide, 7.12, 5.58, 1.15, "1 call", COLORS.green);
  pill(slide, 8.4, 5.58, 1.55, "Retry validate", COLORS.blue);
  addFooter(slide, 4);
  addDiagnostics(slide);
}

// Slide 5
{
  const slide = pptx.addSlide();
  addHeader(slide, "데모 시나리오", "단계 설명보다 실제 결과물이 보이도록 OOMKilled 복구 예시를 중심에 둡니다.");
  slide.addText("OOMKilled 복구 데모", {
    x: 0.72,
    y: 1.45,
    w: 2.5,
    h: 0.25,
    fontSize: 16,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  const steps = [
    ["1", "장애 발생", "애플리케이션 Pod가 메모리 limit을 초과해 재시작됩니다.", COLORS.red],
    ["2", "알림 수집", "Prometheus가 Alert를 발생시키고 Alertmanager가 Agent 웹훅으로 전달합니다.", COLORS.amber],
    ["3", "AI 분석", "LLM이 root cause를 메모리 부족으로 판단하고 values YAML 수정안을 생성합니다.", COLORS.cyan],
    ["4", "PR 생성", "GitHub PR에 memory 512Mi → 1Gi 같은 변경안을 제안합니다.", COLORS.blue],
    ["5", "GitOps 복구", "리뷰 후 merge되면 ArgoCD가 동기화하고 Notifications가 완료를 알립니다.", COLORS.green],
  ];
  steps.forEach((s, idx) => {
    const y = 2.02 + idx * 0.95;
    slide.addShape(pptx.ShapeType.ellipse, {
      x: 0.84,
      y,
      w: 0.5,
      h: 0.5,
      fill: { color: s[3] },
      line: { color: s[3] },
    });
    slide.addText(s[0], {
      x: 0.84,
      y: y + 0.11,
      w: 0.5,
      h: 0.18,
      align: "center",
      fontSize: 12,
      bold: true,
      color: COLORS.white,
      margin: 0,
    });
    slide.addText(s[1], {
      x: 1.55,
      y: y + 0.02,
      w: 1.15,
      h: 0.18,
      fontSize: 12,
      bold: true,
      color: COLORS.ink,
      margin: 0,
    });
    slide.addText(s[2], {
      x: 2.98,
      y: y,
      w: 6.1,
      h: 0.36,
      fontSize: 10.5,
      color: COLORS.slate,
      margin: 0,
    });
    if (idx < steps.length - 1) {
      slide.addShape(pptx.ShapeType.line, {
        x: 1.08,
        y: y + 0.5,
        w: 0,
        h: 0.44,
        line: { color: COLORS.line, pt: 1.4 },
      });
    }
  });
  card(slide, 9.72, 1.96, 2.7, 1.2, "입력 이슈", "sample_oom.json\n또는 Alertmanager 웹훅 payload", COLORS.red);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 9.72,
    y: 3.34,
    w: 2.7,
    h: 1.42,
    rectRadius: 0.08,
    fill: { color: COLORS.navy },
    line: { color: COLORS.navy },
  });
  slide.addText("예시 수정안", {
    x: 9.98,
    y: 3.58,
    w: 1.1,
    h: 0.18,
    fontSize: 12.5,
    bold: true,
    color: COLORS.white,
    margin: 0,
  });
  slide.addText("memory\n512Mi → 1Gi", {
    x: 9.98,
    y: 3.94,
    w: 1.4,
    h: 0.5,
    fontSize: 15,
    bold: true,
    color: "93C5FD",
    margin: 0,
  });
  card(slide, 9.72, 4.98, 2.7, 1.42, "발표 포인트", "청중에게는 과정보다 '무엇을 바꿔 복구했는지'를 보여주는 것이 더 강합니다.", COLORS.green);
  addFooter(slide, 5);
  addDiagnostics(slide);
}

// Slide 6
{
  const slide = pptx.addSlide();
  addHeader(slide, "왜 안전한가: GitOps 원칙", "DR-Kube는 클러스터를 직접 고치지 않고, 검토 가능한 변경만 제안합니다.");
  card(slide, 0.72, 1.72, 3.82, 2.35, "1. 직접 변경 금지", "kubectl apply, patch 같은 쓰기 명령을 만들지 않고 values/*.yaml 수정을 우선합니다. 복구 행동은 항상 Git 변경으로 표현됩니다.", COLORS.red);
  card(slide, 4.76, 1.72, 3.82, 2.35, "2. 리뷰 가능한 PR", "수정안은 GitHub PR로 남기기 때문에 사람이 검토할 수 있고, 변경 근거와 diff가 그대로 기록됩니다.", COLORS.blue);
  card(slide, 8.8, 1.72, 3.82, 2.35, "3. 안전한 반영", "merge 이후에는 ArgoCD가 동기화합니다. 복구 완료 알림도 ArgoCD Notifications가 맡아 책임을 분리합니다.", COLORS.green);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 1.0,
    y: 4.6,
    w: 11.34,
    h: 1.2,
    rectRadius: 0.08,
    fill: { color: "ECFEFF" },
    line: { color: "67E8F9", pt: 1 },
  });
  slide.addText("핵심 메시지", {
    x: 1.28,
    y: 4.92,
    w: 1.1,
    h: 0.18,
    fontSize: 13,
    bold: true,
    color: COLORS.teal,
    margin: 0,
  });
  slide.addText("DR-Kube는 자동화의 속도보다 운영 변경의 안전성과 추적 가능성을 먼저 지키는 구조입니다.", {
    x: 2.55,
    y: 4.88,
    w: 8.95,
    h: 0.28,
    fontSize: 14,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  addFooter(slide, 6);
  addDiagnostics(slide);
}

// Slide 7
{
  const slide = pptx.addSlide();
  addHeader(slide, "개발하면서 어려웠던 부분", "커밋 흐름을 보면 이 프로젝트의 난점은 모델 성능 자체보다 운영 환경과 안전성 제약에 더 가깝습니다.");
  card(slide, 0.76, 1.62, 3.0, 1.42, "LLM 공급자 안정성", "Gemini, GitHub Models, Copilot을 오가며 실제로 호출 가능한 모델과 인증 방식을 맞추는 작업이 반복됐습니다.", COLORS.red);
  card(slide, 0.76, 3.28, 3.0, 1.42, "단순 리소스 증설의 위험", "crash/error 계열 장애에서 memory/cpu 상향은 쉬운 답이지만, 잘못된 자동복구가 될 가능성이 커서 정책적으로 막았습니다.", COLORS.amber);
  card(slide, 0.76, 4.94, 3.0, 1.42, "PR 스팸과 비용", "Alert가 연속 발생하면 같은 문제로 LLM을 여러 번 호출하고 PR을 남발할 수 있어서 dedup, 일일 예산, 그룹 쿨다운이 필요했습니다.", COLORS.blue);
  card(slide, 4.08, 1.62, 3.0, 1.42, "복합 장애 처리", "하나의 Alert만 보면 판단이 쉬워도 실제 장애는 여러 신호가 동시에 옵니다. 그래서 composite incident로 묶는 흐름이 추가됐습니다.", COLORS.cyan);
  card(slide, 4.08, 3.28, 3.0, 1.42, "사람과의 협업", "LLM이 한 번에 완벽한 PR을 만들지 못하므로 Slack에서 피드백을 받고 수정안을 다시 생성하는 HITL 흐름이 들어갔습니다.", COLORS.green);
  card(slide, 4.08, 4.94, 3.0, 1.42, "실행 환경 차이", "최근에는 Pod 안에 kubectl이 없어서 watcher를 kubernetes Python client로 바꾸는 수정까지 들어갔습니다.", COLORS.teal);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 7.42,
    y: 1.62,
    w: 5.1,
    h: 4.74,
    rectRadius: 0.08,
    fill: { color: COLORS.white },
    line: { color: COLORS.cloud, pt: 1 },
  });
  slide.addText("커밋으로 보이는 핵심 전환", {
    x: 7.72,
    y: 1.92,
    w: 2.4,
    h: 0.22,
    fontSize: 14.5,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText([
    { text: "`476170b` 비용 가드 도입", options: { bullet: { indent: 10 } } },
    { text: "`4dbad0d` crash/error 계열 리소스 튜닝 차단", options: { bullet: { indent: 10 } } },
    { text: "`6d01c37` 규칙 기반 최소 replica 패치 도입", options: { bullet: { indent: 10 } } },
    { text: "`d328c4a` 복합 인시던트 단일 PR 처리", options: { bullet: { indent: 10 } } },
    { text: "`a8f4e14` ArgoCD sync 이후 복구 검증 추가", options: { bullet: { indent: 10 } } },
    { text: "`4654531` Slack 수정 요청 기반 재생성", options: { bullet: { indent: 10 } } },
    { text: "`d3025c0` watcher를 kubectl 의존에서 탈피", options: { bullet: { indent: 10 } } },
  ], {
    x: 7.72,
    y: 2.34,
    w: 4.35,
    h: 2.95,
    fontSize: 10.4,
    color: COLORS.slate,
    margin: 0,
    breakLine: false,
  });
  addFooter(slide, 7);
  addDiagnostics(slide);
}

// Slide 8
{
  const slide = pptx.addSlide();
  addHeader(slide, "LLM 판단 정확도를 위해 한 것", "핵심은 모델을 더 똑똑하게 믿는 것이 아니라, 잘못된 제안을 못 내도록 입력·정책·검증을 겹겹이 두는 것입니다.");
  card(slide, 0.76, 1.68, 2.82, 1.86, "1. 입력을 좁힘", "converter가 alertname을 내부 issue type으로 정규화하고, target values 파일을 추론해 LLM에 전체 YAML과 로그를 함께 제공합니다.", COLORS.blue);
  card(slide, 3.82, 1.68, 2.82, 1.86, "2. 출력 형식을 강제", "prompts.py에서 근본 원인, 심각도, 해결책, 전체 YAML, 변경 설명 형식을 고정해 후처리 파싱 실패를 줄입니다.", COLORS.cyan);
  card(slide, 6.88, 1.68, 2.82, 1.86, "3. 위험한 답을 금지", "pod_crash/service_error 계열에는 memory/cpu 변경을 금지하고 replicas, retry, timeout 계열만 허용하는 정책을 둡니다.", COLORS.red);
  card(slide, 9.94, 1.68, 2.58, 1.86, "4. 룰 기반 우선 처리", "일부 장애는 LLM보다 규칙 기반 최소 수정이 더 안전하다고 보고 LLM 호출 자체를 건너뜁니다.", COLORS.green);
  card(slide, 0.76, 3.88, 3.94, 1.9, "5. validate + retry", "YAML 문법, 원본 대비 실제 변경 여부, dict 형식, 장애 타입별 정책 위반을 검사하고 실패하면 최대 3회 다시 생성합니다.", COLORS.amber);
  card(slide, 4.94, 3.88, 3.94, 1.9, "6. HITL 피드백 루프", "Slack 수정 요청을 `_review_comment`, `_previous_fix`로 프롬프트에 재주입해 더 나은 수정안을 다시 만들 수 있게 했습니다.", COLORS.teal);
  card(slide, 9.12, 3.88, 3.4, 1.9, "7. 사후 검증", "ArgoCD sync 이후 verifier가 Pod 상태와 Alert 해소 여부를 확인해 '제안'과 '실제 복구'를 분리합니다.", COLORS.green);
  pill(slide, 0.92, 6.18, 1.3, "Input Quality", COLORS.blue);
  pill(slide, 2.34, 6.18, 1.42, "Policy Guard", COLORS.red);
  pill(slide, 3.9, 6.18, 1.18, "Retry", COLORS.amber);
  pill(slide, 5.2, 6.18, 1.08, "HITL", COLORS.teal);
  pill(slide, 6.4, 6.18, 1.15, "Verify", COLORS.green);
  addFooter(slide, 8);
  addDiagnostics(slide);
}

// Slide 9
{
  const slide = pptx.addSlide();
  addHeader(slide, "로드맵", "숫자 우선순위보다 지금 무엇을 만들고, 다음에 무엇을 확장할지가 더 중요합니다.");
  card(slide, 0.86, 1.86, 3.72, 3.58, "현재 집중", "#1164 Converter 알림 타입 확장\n#1194 analyze_and_fix + validate 루프\n\n프로토타입 메시지의 핵심은 '한 번에 제안하고, 실패하면 다시 보정하는 복구 루프'를 완성하는 것입니다.", COLORS.red);
  card(slide, 4.82, 1.86, 3.72, 3.58, "다음 확장", "#1172 서비스 레벨 알림 규칙\n#1186 복합 Chaos 시나리오\n#1175 ArgoCD Notifications → Slack\n\n데모 범위를 넓혀 더 다양한 장애 유형과 복구 결과를 보여줄 수 있게 만듭니다.", COLORS.amber);
  card(slide, 8.78, 1.86, 3.72, 3.58, "제품형으로 가는 단계", "#1195 PR 댓글 기반 재생성\n#1196 Grafana 대시보드 확장\n#1167 E2E 통합 테스트\n\n사람-에이전트 협업과 검증 자동화를 강화해 실제 운영형 제품에 가깝게 발전시킵니다.", COLORS.green);
  slide.addText("목표 완료일: 2026-02-28", {
    x: 0.88,
    y: 5.9,
    w: 2.4,
    h: 0.18,
    fontSize: 11.5,
    bold: true,
    color: COLORS.navy,
    margin: 0,
  });
  addFooter(slide, 9);
  addDiagnostics(slide);
}

// Slide 10
{
  const slide = pptx.addSlide();
  addHeader(slide, "기대 효과와 마무리", "발표의 마지막은 기술 구현보다 운영 가치와 확장 가능성에 초점을 맞춥니다.");
  card(slide, 0.76, 1.58, 2.95, 1.7, "운영 효율", "장애 대응 시간을 줄이고, 사람마다 다른 대응 품질을 표준화할 수 있습니다.", COLORS.blue);
  card(slide, 3.98, 1.58, 2.95, 1.7, "안전한 자동화", "Git 기반 변경 이력과 리뷰 프로세스로 자동화의 위험을 통제합니다.", COLORS.green);
  card(slide, 7.2, 1.58, 2.95, 1.7, "확장성", "프롬프트, 알림 규칙, 시나리오를 추가해 더 많은 장애 유형으로 확장 가능합니다.", COLORS.cyan);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.76,
    y: 3.72,
    w: 9.34,
    h: 2.0,
    rectRadius: 0.08,
    fill: { color: COLORS.white },
    line: { color: COLORS.cloud, pt: 1 },
  });
  slide.addText("한 문장으로 정리하면", {
    x: 1.08,
    y: 4.05,
    w: 2.2,
    h: 0.24,
    fontSize: 16,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText("DR-Kube는 장애 대응을 수작업 운영에서 검증 가능한 GitOps 복구 루프로 전환하는 프로젝트입니다.", {
    x: 1.08,
    y: 4.45,
    w: 8.38,
    h: 0.72,
    fontSize: 16,
    bold: true,
    color: COLORS.navy,
    margin: 0,
    align: "left",
    valign: "mid",
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 10.42,
    y: 1.58,
    w: 2.1,
    h: 4.14,
    rectRadius: 0.08,
    fill: { color: COLORS.navy },
    line: { color: COLORS.navy },
  });
  slide.addText("Demo\nChecklist", {
    x: 10.78,
    y: 2.0,
    w: 1.4,
    h: 0.46,
    fontSize: 18,
    bold: true,
    color: COLORS.white,
    align: "center",
    margin: 0,
  });
  slide.addText([
    { text: "샘플 이슈 준비", options: { bullet: { indent: 10 } } },
    { text: "Alert 흐름 설명", options: { bullet: { indent: 10 } } },
    { text: "PR 생성 화면", options: { bullet: { indent: 10 } } },
    { text: "ArgoCD Sync", options: { bullet: { indent: 10 } } },
    { text: "복구 완료 알림", options: { bullet: { indent: 10 } } },
  ], {
    x: 10.72,
    y: 2.78,
    w: 1.52,
    h: 1.7,
    fontSize: 10.5,
    color: "E2E8F0",
    margin: 0,
    breakLine: false,
  });
  slide.addText("Q&A", {
    x: 10.72,
    y: 5.02,
    w: 1.5,
    h: 0.28,
    fontSize: 16,
    bold: true,
    color: "93C5FD",
    align: "center",
    margin: 0,
  });
  addFooter(slide, 10);
  addDiagnostics(slide);
}

async function main() {
  await pptx.writeFile({
    fileName: "/Users/jay/dr-kube/deck/dr-kube-presentation/DR-Kube_Project_Presentation.pptx",
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
