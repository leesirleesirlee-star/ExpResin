/**
 * 演示数据：取自 20250528 DHT Cl SO4.xlsx 的真实识别结果（Benchmark v0 样本）。
 * 用于验证 PortalJarvis 三栏工作台的信息架构与交互状态。
 */

export const experiment = {
  id: 'DHT-0305-600',
  project: 'DHT 动态离子交换',
  sourceFile: '20250528 DHT Cl SO4.xlsx',
  sheet: '0305-600',
  status: 'reviewing',
  lastSaved: '尚未保存',
}

export const STATUS_META = {
  draft: { label: '草稿', tone: 'neutral' },
  reviewing: { label: '待确认', tone: 'warning' },
  confirmed: { label: '已确认', tone: 'success' },
}

export const initialMessages = [
  {
    id: 1,
    role: 'user',
    text: '上传了《20250528 DHT Cl SO4.xlsx》，先处理 0305-600 这个 Sheet。',
  },
  {
    id: 2,
    role: 'jarvis',
    text: '解析完成：该 Sheet 含 3 个数据区、4 个列块 —— 2 个标定曲线块（SO4、Cl）与 2 个样品测量块（SO4、Cl）。共 22 列，其中 18 列已映射到标准字段，2 列判定为离子标签列，1 列低置信度待确认，1 列为空表头已忽略。',
    chips: ['4 个列块', '18 列已映射', '1 列待确认'],
  },
]

export const regions = [
  {
    id: '0305-600#R2',
    title: '40 mL A600, pass 100 mg/L SO4 using Na2SO4',
    kindLabel: '标定曲线',
    kind: 'calibration',
    blocks: [
      {
        id: '0305-600#R2-2/B1',
        analyte: 'SO4',
        confidence: 0.96,
        columns: [
          {
            col: 'A',
            raw: 'SO4',
            target: null,
            field: '离子标签列',
            value: 'SO4',
            conf: 0.2,
            unit: null,
            unitStd: null,
            evidence: '整列为常量文本 SO4，判定为离子标签列，不映射为数据字段',
          },
          {
            col: 'B',
            raw: 'area',
            target: 'signal_area',
            field: '峰面积',
            value: '12.46',
            conf: 0.98,
            unit: null,
            unitStd: null,
            evidence: '列名 area，数值范围 0–29，符合仪器信号特征',
          },
          {
            col: 'C',
            raw: 'ppm',
            target: 'concentration_standard',
            field: '标准浓度',
            value: '50',
            conf: 0.97,
            unit: 'ppm',
            unitStd: 'ppm',
            evidence: '列名 ppm，数值范围 0–100，与标准浓度定义一致',
          },
        ],
      },
      {
        id: '0305-600#R2-2/B2',
        analyte: 'Cl',
        confidence: 0.95,
        columns: [
          {
            col: 'E',
            raw: 'Cl',
            target: null,
            field: '离子标签列',
            value: 'Cl',
            conf: 0.2,
            unit: null,
            unitStd: null,
            evidence: '整列为常量文本 Cl，判定为离子标签列',
          },
          {
            col: 'F',
            raw: 'area',
            target: 'signal_area',
            field: '峰面积',
            value: '9.82',
            conf: 0.97,
            unit: null,
            unitStd: null,
            evidence: '列名 area，数值范围 0–21，符合仪器信号特征',
          },
          {
            col: 'G',
            raw: 'ppm',
            target: 'concentration_standard',
            field: '标准浓度',
            value: '50',
            conf: 0.95,
            unit: 'ppm',
            unitStd: 'ppm',
            evidence: '列名 ppm，与标准浓度定义一致',
          },
        ],
      },
    ],
  },
  {
    id: '0305-600#R13',
    title: '样品流出曲线（SO4）',
    kindLabel: '样品测量',
    kind: 'sample_measurement',
    blocks: [
      {
        id: '0305-600#R13-13/B1',
        analyte: 'SO4',
        confidence: 0.96,
        columns: [
          {
            col: 'A', raw: 'BV', target: 'bed_volume', field: '床层体积', value: '3.5',
            conf: 0.97, unit: 'BV', unitStd: 'BV', evidence: '列名 BV，范围 0–12，符合床层体积序列',
          },
          {
            col: 'B', raw: 'V', target: 'volume', field: '通过体积', value: '175',
            conf: 0.85, unit: 'mL', unitStd: 'mL', evidence: '单字母列名 V，结合数值量级判定为体积(mL)而非伏特',
          },
          {
            col: 'C', raw: 'number', target: 'sample_number', field: '样品序号', value: '7',
            conf: 0.95, unit: null, unitStd: null, evidence: '列名 number，为递增整数序列',
          },
          {
            col: 'D', raw: 'area', target: 'signal_area', field: '峰面积', value: '8.41',
            conf: 0.97, unit: null, unitStd: null, evidence: '列名 area，仪器信号',
          },
          {
            col: 'E', raw: 'calculated  ppm', target: 'concentration_ppm', field: '计算浓度',
            value: '42.30', conf: 0.98, unit: 'ppm', unitStd: 'ppm', evidence: '列名 calculated ppm，由标定曲线换算所得',
          },
          {
            col: 'F', raw: '稀释100倍(mol/L)', target: 'concentration_mol', field: '摩尔浓度',
            value: '0.000440', conf: 0.97, unit: 'mol/L', unitStd: 'mol/L', evidence: '括号内单位 mol/L，表头标注稀释 100 倍',
          },
          {
            col: 'G', raw: 'mg/L', target: 'concentration_mg_l', field: '质量浓度', value: '42.30',
            conf: 0.98, unit: 'mg/L', unitStd: 'mg/L', evidence: '列名 mg/L，与计算浓度数值一致',
          },
        ],
      },
    ],
  },
  {
    id: '0305-600#R44',
    title: '样品流出曲线（Cl）',
    kindLabel: '样品测量',
    kind: 'sample_measurement',
    blocks: [
      {
        id: '0305-600#R44-44/B1',
        analyte: 'Cl',
        confidence: 0.97,
        columns: [
          {
            col: 'A', raw: 'BV', target: 'bed_volume', field: '床层体积', value: '3.5',
            conf: 0.98, unit: 'BV', unitStd: 'BV', evidence: '列名 BV，符合床层体积序列',
          },
          {
            col: 'B', raw: 'V', target: 'volume', field: '通过体积', value: '175',
            conf: 0.9, unit: 'mL', unitStd: 'mL', evidence: '单字母列名 V，结合数值量级判定为体积(mL)',
          },
          {
            col: 'C', raw: 'number', target: 'sample_number', field: '样品序号', value: '7',
            conf: 0.9, unit: null, unitStd: null, evidence: '列名 number，为递增整数序列',
          },
          {
            col: 'D', raw: 'area', target: 'signal_area', field: '峰面积', value: '6.12',
            conf: 0.97, unit: null, unitStd: null, evidence: '列名 area，仪器信号',
          },
          {
            col: 'E', raw: 'calculated  ppm', target: 'concentration_ppm', field: '计算浓度',
            value: '22.40', conf: 0.98, unit: 'ppm', unitStd: 'ppm', evidence: '列名 calculated ppm，由标定曲线换算所得',
          },
          {
            col: 'F', raw: '稀释100倍(mol/L)', target: 'concentration_mol', field: '摩尔浓度',
            value: '0.000630', conf: 0.65, unit: 'mol/L', unitStd: 'mol/L',
            evidence: '表头同时包含稀释倍数与单位，语义歧义，需人工确认',
          },
          {
            col: 'G', raw: '', target: null, field: null, value: '',
            conf: 0.2, unit: null, unitStd: null, evidence: '空表头且整列为空，判定为幽灵列，已忽略',
          },
        ],
      },
    ],
  },
]

/** 离子标签列白名单：这类列天然没有目标字段，不应被标记为问题。 */
const ION_LABELS = new Set([
  'so4', 'cl', 'nh4+', 'nh4', 'li+', 'li', 'ca', 'na', 'hpo4', 'po4', 'no3', 'f',
])

/** 字段状态判定，供表单与 Inspector 共用。 */
export function fieldState(col) {
  // 人工处置优先于自动判定：用户已确认/改判/忽略的列不应再反复报警
  if (col.review) {
    if (col.review.status === 'ignore') return 'ignored'
    if (col.review.status === 'remap') return 'remapped'
    return 'confirmed'
  }

  const raw = (col.raw || '').trim()

  if (!col.target) {
    if (!raw) {
      // 「幽灵列」严格指「空表头 **且** 整列为空」。
      // 空表头但有数据的列（如 0305-600#R44-44/B1 的 G 列：无表头却填满 22 个数值）
      // 是「未映射、待人工确认」，不能与空列混为一谈 —— 否则会把真实数据当噪声丢弃。
      const hasData = typeof col.nonNull === 'number' && col.nonNull > 0
      return hasData ? 'pending' : 'missing'
    }
    if (ION_LABELS.has(raw.toLowerCase())) return 'label'
    return 'pending'
  }
  if (col.unitStd && col.unit && col.unit !== col.unitStd) return 'unit-error'
  if (col.conf < 0.8) return 'low-confidence'
  return 'confirmed'
}

/** 汇总需要人工关注的问题项。 */
export function collectIssues(source, failedBlocks = []) {
  const pending = []
  const lowConfidence = []
  const unitErrors = []
  const missing = []
  const analyteConflicts = []

  for (const region of source) {
    for (const block of region.blocks ?? []) {
      // 离子判定与标签列文本矛盾：这是比低置信度更硬的错误信号（Benchmark v0 已复现）
      const ac = block.analyteConflict
      // 已人工处置过的列块不再重复提示
      if (ac && !block.analyteReviewed) {
        analyteConflicts.push({
          region: region.title,
          block: block.id,
          col: 'analyte',
          scope: 'block',
          analyte: ac.actual,
          expected: ac.expected,
          raw: `${ac.actual} vs 标签列 ${ac.expected}`,
          conf: block.confidence ?? 0,
          evidence: ac.evidence,
          field: '离子判定',
          target: null,
          state: 'analyte-conflict',
        })
      }

      for (const col of block.columns ?? []) {
        // 已人工处置的列不再进入待处理清单，否则用户做完判断仍被反复提示
        if (col.review) continue
        const state = fieldState(col)
        if (state === 'confirmed' || state === 'label') continue
        const item = { region: region.title, block: block.id, ...col, state }
        if (state === 'pending') pending.push(item)
        else if (state === 'low-confidence') lowConfidence.push(item)
        else if (state === 'unit-error') unitErrors.push(item)
        else if (state === 'missing') missing.push(item)
      }
    }
  }

  // 列块整体识别失败：没有可处置的列，不能走列级确认/改判/忽略通道，
  // 否则前端会把 col='block' 发给后端，命中「未找到列 {block}/block」的 404。
  const failed = (failedBlocks ?? []).map((f) => ({
    region: '',
    block: f.block ?? '（未知列块）',
    col: 'block',
    scope: 'block',
    raw: f.block ?? '',
    conf: 0,
    evidence: f.error || '该列块整体识别失败，无法通过列级判定修复，请重新上传或重试识别',
    field: '识别失败',
    target: null,
    state: 'block-failed',
  }))

  return { pending, lowConfidence, unitErrors, missing, analyteConflicts, failedBlocks: failed }
}