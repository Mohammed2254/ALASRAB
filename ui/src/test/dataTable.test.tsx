/**
 * @covers ق-٢٤٦
 *
 * `DataTable` يرسم **DOM واحدًا** لا اثنين.
 *
 * الضمانة ليست «يبدو صحيحًا» بل: فوق الحدّ يوجد `<table>` **ولا بطاقات
 * صفوف**، وتحته توجد البطاقات **ولا `<table>` إطلاقًا**. ولو رُسم التخطيطان
 * وأُخفي أحدهما بـCSS لمرّ الاختبار البصريّ ولدخلت عشراتُ عقد النصّ المخفية
 * مسارَ قياس التباين في كل تشغيل — وهذا الفحص يمنع ذلك بنيويًّا.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Column } from '../ui/DataTable'

afterEach(cleanup)

type Row = { id: number; name: string; pct: string }

const ROWS: Row[] = [
  { id: 1, name: 'سلمان الغفيص', pct: '406.5' },
  { id: 2, name: 'ثابت المقحم', pct: '0.0' },
]

const COLUMNS: Column<Row>[] = [
  { id: 'name', header: 'الطالب', cell: (r) => r.name, primary: true },
  { id: 'pct', header: 'تثبيت', numeric: true, cell: (r) => r.pct },
]

/** يُثبّت جواب `matchMedia` قبل أوّل رسم — `useDesk` يقرأه عند أوّل لقطة. */
function setDesk(matches: boolean) {
  vi.spyOn(window, 'matchMedia').mockImplementation(
    (query: string) =>
      ({
        matches,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as MediaQueryList
  )
  // المخزن وحيد ويُنشئ الاستعلام مرّة — فيُعاد تحميل الوحدة لكل حالة.
  vi.resetModules()
}

describe('DataTable — تخطيطان، DOM واحد', () => {
  it('فوق الحدّ: جدولٌ حقيقيّ بترويسات عمودية', async () => {
    setDesk(true)
    const { default: Fresh } = await import('../ui/DataTable')
    const { container } = render(
      <Fresh
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(r: Row) => r.id}
        caption="صفوف الملفّ"
        empty="لا صفوف."
      />
    )
    expect(container.querySelectorAll('table')).toHaveLength(1)
    expect(screen.getByRole('columnheader', { name: 'الطالب' })).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(3) // ترويسة + صفّان
  })

  it('تحت الحدّ: بطاقاتٌ **ولا `<table>` في المستند إطلاقًا**', async () => {
    setDesk(false)
    const { default: Fresh } = await import('../ui/DataTable')
    const { container } = render(
      <Fresh
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(r: Row) => r.id}
        caption="صفوف الملفّ"
        empty="لا صفوف."
      />
    )
    expect(container.querySelectorAll('table')).toHaveLength(0)
    expect(container.querySelectorAll('section')).toHaveLength(ROWS.length)
    // العمود الرئيس صار عنوان البطاقة، والبقيّة أزواج تسمية/قيمة.
    expect(screen.getByText('سلمان الغفيص')).toBeInTheDocument()
    expect(screen.getAllByText('تثبيت')).toHaveLength(ROWS.length)
  })

  it('لا صفوف ⇒ نصٌّ مصمَّم لا فراغ، في التخطيطين معًا', async () => {
    setDesk(false)
    const { default: Fresh } = await import('../ui/DataTable')
    render(
      <Fresh
        columns={COLUMNS}
        rows={[]}
        rowKey={(r: Row) => r.id}
        caption="صفوف الملفّ"
        empty="لا صفوف."
      />
    )
    expect(screen.getByText('لا صفوف.')).toBeInTheDocument()
  })
})
